"""Central Orchestrator integrating ASR, Intent Routing, Detection, OCR, VLM, and TTS.
Features:
- Short conversational context (in-memory, 5-minute TTL, repeat, shorten, reset, ambiguous referent resolution)
- Smart image-quality checks with Arabic retake guidance and VLM bypass
- Continuous object search sessions with direction stabilization and Iraqi synonyms
- Optional Fast (2B) vs Detailed (4B) vision modes with fair fallback
- Complete stage timings and bounded concurrency
"""
from __future__ import annotations

import json
import re
import time
import uuid
from typing import Any, Dict, Optional, Tuple

from app.adapters.asr_adapter import ASRAdapter
from app.adapters.detection_adapter import DetectionAdapter
from app.adapters.ocr_adapter import OCRAdapter
from app.adapters.tts_adapter import TTSAdapter
from app.adapters.vlm_adapter import VLMAdapter
from app.config import AppConfig, get_config
from app.quality_analyzer import FrameQualityAnalyzer
from app.schemas import (
    AssistRequest,
    AssistResponse,
    SearchSessionState,
)

class SessionContext:
    def __init__(self, ttl_seconds: float = 300.0):
        self.ttl_seconds = ttl_seconds
        self.last_user_command: Optional[str] = None
        self.last_completed_answer: Optional[str] = None
        self.last_referenced_object: Optional[str] = None
        self.last_task_mode: Optional[str] = None
        self.last_timestamp: float = 0.0
        self.active_search_session_id: Optional[str] = None
        self.turn_count: int = 0

    def is_stale(self) -> bool:
        if self.last_timestamp == 0.0:
            return True
        return (time.time() - self.last_timestamp) > self.ttl_seconds

    def update(self, command: str, answer: str, mode: str, target_obj: Optional[str] = None):
        self.last_user_command = command
        self.last_completed_answer = answer
        self.last_task_mode = mode
        if target_obj:
            self.last_referenced_object = target_obj
        self.last_timestamp = time.time()
        self.turn_count += 1

    def reset(self):
        self.last_user_command = None
        self.last_completed_answer = None
        self.last_referenced_object = None
        self.last_task_mode = None
        self.last_timestamp = 0.0
        self.active_search_session_id = None
        self.turn_count = 0

class Orchestrator:
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or get_config()
        self.asr = ASRAdapter(self.config.asr)
        self.detection = DetectionAdapter(self.config.detection)
        self.ocr = OCRAdapter(self.config.ocr)
        self.vlm = VLMAdapter(self.config.vlm)
        self.tts = TTSAdapter(self.config.tts)
        self.quality_analyzer = FrameQualityAnalyzer(
            min_brightness=self.config.quality.min_brightness,
            max_brightness=self.config.quality.max_brightness,
            min_blur_var=self.config.quality.min_blur_var,
            cooldown_seconds=self.config.quality.cooldown_seconds,
            max_frame_age_s=self.config.quality.max_frame_age_s,
        )

        self.context = SessionContext(ttl_seconds=self.config.context_ttl_seconds)
        self._active_cancelled_request_ids: set[str] = set()

    @property
    def last_valid_answer_ar(self) -> str:
        return self.context.last_completed_answer or "لا توجد إجابة سابقة لإعادتها بعد."

    @last_valid_answer_ar.setter
    def last_valid_answer_ar(self, val: str):
        self.context.last_completed_answer = val
        self.context.last_timestamp = time.time()

    def cancel_request(self, request_id: str):
        self._active_cancelled_request_ids.add(request_id)
        if self.context.active_search_session_id:
            self.detection.stop_search_session(self.context.active_search_session_id)
            self.context.active_search_session_id = None

    def is_cancelled(self, request_id: str) -> bool:
        return request_id in self._active_cancelled_request_ids

    def normalize_arabic(self, text: str) -> str:
        """Normalizes Arabic text solely for intent classification without altering original input."""
        t = text.strip().lower()
        t = re.sub(r"[إأآا]", "ا", t)
        t = re.sub(r"ة", "ه", t)
        t = re.sub(r"[\u064B-\u065F]", "", t)  # Tashkeel removal
        t = re.sub(r"[!؟?.,،]", " ", t)
        return " ".join(t.split())

    def route_intent(self, query: str) -> Tuple[str, Optional[str]]:
        """Determines pipeline mode and target object from user query.
        Returns (mode, target_object_ar).
        Modes: 'repeat', 'shorten', 'reset', 'read', 'find', 'describe', 'greeting', 'ask'
        """
        norm = self.normalize_arabic(query)
        if not norm:
            return "unknown", None
        words = norm.split()

        # 0. Conversational greetings
        greetings = ["مرحبا", "اهلا", "السلام عليكم", "صباح الخير", "مساء الخير", "شكرا", "تسلم", "عاشت ايدك", "يعطيك العافيه", "hello", "hi"]
        if any(norm == g or norm.startswith(g + " ") for g in greetings):
            return "greeting", None

        # 1. Reset / Clear memory
        reset_patterns = ["اعادة ضبط", "امسح الذاكرة", "امسح الذاكره", "ابدأ من جديد", "ابدا من جديد", "فرمت", "reset"]
        if any(p in norm for p in reset_patterns):
            return "reset", None

        # 2. Shorten answer (no re-analysis, summarize previous answer)
        shorten_patterns = ["اختصر", "باختصار", "اختصر الجواب", "اختصر الكلام", "قصر الجواب", "قلل الكلام", "shorten", "brief"]
        if any(norm == p or norm.startswith(p + " ") for p in shorten_patterns):
            return "shorten", None

        # 3. Repeat check (Iraqi & Fusha)
        repeat_patterns = ["كرر", "عيد", "اعد", "شنو كلت", "شنو قلت", "ما سمعتك", "كرر الجواب", "عيد الجواب", "عيد الكلام", "اعد ما قلته", "repeat", "again"]
        if any(norm == p or norm.startswith(p + " ") for p in repeat_patterns):
            return "repeat", None

        # 4. Read / OCR check
        read_patterns = ["اقرا", "قراءه", "المكتوب", "شنو مكتوب", "ماذا كتب", "ايش مكتوب", "شكو مكتوب", "النص", "اقرا النص", "اقرالي", "قراءة النص", "read"]
        if any(p in norm for p in read_patterns):
            return "read", None

        # 5. Continuous search session triggers: "ابحث عن غرض", "ابحث عن كائن", "جلسة بحث"
        search_session_triggers = ["ابحث عن غرض", "ابحث عن كائن", "بدء البحث", "جلسة بحث", "ابحث باستمرار"]
        for trigger in search_session_triggers:
            if trigger in norm:
                target = norm.replace(trigger, "").strip()
                target_clean = re.sub(r"^(ال|ا)", "", target).strip()
                return "search_session", target_clean or None

        # 6. Find / Locate object check (Iraqi & Fusha)
        # Handle ambiguous pronoun referents: "وينها", "وينه", "وين صار"
        pronoun_finds = ["وينها", "وينه", "وين صايرة", "وين صاير", "وين صار"]
        for pf in pronoun_finds:
            if norm == pf or norm.startswith(pf + " "):
                # Resolve from context if available
                if not self.context.is_stale() and self.context.last_referenced_object:
                    return "find", self.context.last_referenced_object
                return "find_ambiguous", None

        # Check patterns like "شوفلي [كائن] وين" or "شوف [كائن] وين"
        m_surround = re.search(r"^(?:شوفلي|شوف|تلكالي|تلقالي)\s+(.*?)\s+(?:وين|اين)(?:\s+صاير|\s+صايرة)?$", norm)
        if m_surround:
            target = m_surround.group(1).strip()
            target_clean = re.sub(r"^(ال|ا)", "", target).strip()
            return "find", target_clean or None

        find_triggers = ["وين صايرة", "وين صاير", "وين", "اين", "دورلي على", "دور على", "دور", "ابحث عن", "شوفلي وين", "شوفلي", "تلكالي", "تلقالي", "لقيت", "find", "where is", "where"]
        for trigger in find_triggers:
            if trigger in words or norm.startswith(trigger) or trigger in norm:
                pattern = rf"(?:^|\s){re.escape(trigger)}\s+(.*)"
                m = re.search(pattern, norm)
                target = m.group(1).strip() if m else ""
                # Strip trailing interrogatives like "وين" or "صاير"
                target = re.sub(r"\s+(وين|اين|صاير|صايرة)$", "", target).strip()
                target_clean = re.sub(r"^(ال|ا)", "", target).strip()
                if not target_clean:
                    target_clean = target
                return "find", target_clean or None

        # 7. Describe scene check (Iraqi & Fusha: شنو قدامي، شكو كدامي، صف المشهد)
        describe_patterns = ["قدامي", "كدامي", "امامي", "صف المشهد", "صف ما ترى", "ايش في قدامي", "ايش كدامي", "شنو اكو", "شنو موجود", "شكو كدامي", "شكو قدامي", "بينلي المشهد", "describe"]
        if any(p in norm for p in describe_patterns):
            return "describe", None

        # 8. Default to VQA question
        return "ask", None

    def condense_answer(self, full_answer: str) -> str:
        """Shortens previous answer to a concise summary without introducing new factual claims."""
        if not full_answer:
            return "لا توجد إجابة سابقة لاختصارها."
        # Split sentences by Arabic and Latin delimiters
        sentences = re.split(r"[.!\n؟?]+", full_answer)
        cleaned_sentences = [s.strip() for s in sentences if s.strip()]
        if not cleaned_sentences:
            return full_answer
        # Return the most salient first sentence
        first = cleaned_sentences[0]
        if len(cleaned_sentences) > 1 and len(first) < 40:
            return f"{first}. {cleaned_sentences[1]}."
        return f"{first}."

    def execute_assist(self, request: AssistRequest) -> AssistResponse:
        t_total_start = time.perf_counter()
        req_id = str(uuid.uuid4())[:8]
        timings: Dict[str, float] = {}
        source_components: list[str] = []
        details: Dict[str, Any] = {}

        # 1. Speech Transcription (if audio provided)
        query_text = (request.query_text or "").strip()
        if request.audio_base64:
            asr_res = self.asr.transcribe(
                audio_base64=request.audio_base64,
                audio_format=request.audio_format or "webm",
            )
            timings["transcription_ms"] = asr_res.latency_ms
            source_components.append("faster-whisper")
            if asr_res.status == "ok" and asr_res.transcript:
                query_text = asr_res.transcript
                details["transcription"] = asr_res.model_dump()
            else:
                return AssistResponse(
                    request_id=req_id,
                    frame_id=request.frame_id,
                    mode="transcribe_failed",
                    query_text="",
                    answer_ar="لم أتمكن من سماع سؤالك بوضوح، يرجى إعادة التحدث أو كتابة السؤال.",
                    status="asr_empty_or_failed",
                    source_components=source_components,
                    stage_timings_ms=timings,
                    total_latency_ms=round((time.perf_counter() - t_total_start) * 1000, 2),
                    error=asr_res.error,
                )

        # Spoken cancel/stop command check: "توقف", "بس", "اسكت", "وقف"
        norm_q = self.normalize_arabic(query_text)
        stop_commands = ["توقف", "بس", "اسكت", "وقف", "كافي", "stop"]
        if any(norm_q == cmd for cmd in stop_commands):
            if self.context.active_search_session_id:
                self.detection.stop_search_session(self.context.active_search_session_id)
                self.context.active_search_session_id = None
            return AssistResponse(
                request_id=req_id,
                frame_id=request.frame_id,
                mode="stop",
                query_text=query_text,
                answer_ar="تم التوقف.",
                status="cancelled",
                stage_timings_ms=timings,
                total_latency_ms=round((time.perf_counter() - t_total_start) * 1000, 2),
            )

        # 2. Intent Routing
        t_route_start = time.perf_counter()
        if not query_text and request.mode == "auto":
            mode = "describe"
            target_obj = None
        elif request.mode and request.mode != "auto":
            mode = request.mode
            target_obj = request.target_object_ar
        else:
            mode, target_obj = self.route_intent(query_text)
        timings["intent_routing_ms"] = round((time.perf_counter() - t_route_start) * 1000, 2)

        details["resolved_mode"] = mode
        if target_obj:
            details["target_object_ar"] = target_obj

        # Check in-flight cancellation
        if self.is_cancelled(req_id):
            return AssistResponse(
                request_id=req_id,
                frame_id=request.frame_id,
                mode=mode,
                query_text=query_text,
                answer_ar="",
                status="cancelled",
                stage_timings_ms=timings,
                total_latency_ms=round((time.perf_counter() - t_total_start) * 1000, 2),
            )

        # If entering a non-search task, pause/cancel any active search session to avoid overlapping jobs
        if mode != "search_session" and self.context.active_search_session_id:
            self.detection.stop_search_session(self.context.active_search_session_id)
            self.context.active_search_session_id = None

        # Handle empty input
        if not query_text and not request.image_base64 and mode not in ("repeat", "shorten", "reset", "greeting"):
            return AssistResponse(
                request_id=req_id,
                frame_id=request.frame_id,
                mode=mode,
                query_text="",
                answer_ar="لم أسمع أي سؤال أو أمر، كما أن الكاميرا متوقفة. يرجى التحدث بوضوح أو تشغيل الكاميرا.",
                status="empty_input",
                source_components=source_components,
                stage_timings_ms=timings,
                total_latency_ms=round((time.perf_counter() - t_total_start) * 1000, 2),
            )

        # 3. Smart Frame Quality Analysis (Lightweight local stage before expensive stages)
        quality_report = None
        if request.image_base64 and mode not in ("repeat", "shorten", "reset", "greeting"):
            t_qual_start = time.perf_counter()
            quality_report = self.quality_analyzer.analyze(
                image_input=request.image_base64,
                frame_timestamp=request.frame_timestamp_ms / 1000.0 if request.frame_timestamp_ms else None,
                force_override=bool(request.override_quality),
            )
            timings["quality_check_ms"] = quality_report.duration_ms
            details["frame_quality"] = quality_report.to_dict()

            # Guard: If frame is clearly unusable and not manually overridden, bypass expensive VLM/detection
            if not quality_report.is_usable and not request.override_quality:
                guidance_answer = quality_report.advice_ar or "الصورة غير واضحة، يرجى ضبط الكاميرا."
                # Synthesize guidance speech if cooldown allows
                audio_b64 = None
                if quality_report.should_speak:
                    tts_res = self.tts.speak(guidance_answer)
                    timings["tts_ms"] = tts_res.latency_ms
                    audio_b64 = tts_res.audio_base64 if tts_res.status == "ok" else None

                return AssistResponse(
                    request_id=req_id,
                    frame_id=request.frame_id,
                    mode="quality_guidance",
                    query_text=query_text,
                    answer_ar=guidance_answer,
                    audio_base64=audio_b64,
                    status="frame_unusable",
                    frame_quality=quality_report.to_dict(),
                    source_components=["quality_analyzer", "piper-tts"] if audio_b64 else ["quality_analyzer"],
                    stage_timings_ms=timings,
                    total_latency_ms=round((time.perf_counter() - t_total_start) * 1000, 2),
                )

        answer_ar = ""
        search_session_state: Optional[SearchSessionState] = None
        model_mode_used = request.model_mode or "fast"

        # 4. Pipeline Execution
        if mode == "greeting":
            answer_ar = "أهلاً وسهلاً بك. أنا مساعدك البصري الذكي. يمكنك سؤالي عما يوجد أمامك، أو طلب قراءة نص، أو البحث المستمر عن كائن معين."
            source_components.append("intent_router")

        elif mode == "reset":
            self.context.reset()
            self.quality_analyzer.reset_cooldowns()
            answer_ar = "تم مسح الذاكرة والبدء من جديد."
            source_components.append("memory_cache")

        elif mode == "repeat":
            if not self.context.is_stale() and self.context.last_completed_answer:
                answer_ar = self.context.last_completed_answer
            else:
                answer_ar = "لا توجد إجابة سابقة لإعادتها بعد."
            source_components.append("memory_cache")

        elif mode == "shorten":
            if not self.context.is_stale() and self.context.last_completed_answer:
                answer_ar = self.condense_answer(self.context.last_completed_answer)
            else:
                answer_ar = "لا توجد إجابة سابقة لاختصارها."
            source_components.append("memory_cache")

        elif mode == "find_ambiguous":
            answer_ar = "عن أي غرض تسأل؟ يمكنك تحديد اسم الكائن مثل القنينة أو الكوب أو المفاتيح."
            source_components.append("intent_router")

        elif mode == "search_session":
            action = request.search_action or "start"
            session_id = request.search_session_id or self.context.active_search_session_id
            target = target_obj or (self.context.last_referenced_object if not self.context.is_stale() else None)

            if action == "start":
                if not target:
                    answer_ar = "ما هو الغرض الذي تريد مني البحث عنه؟"
                else:
                    search_session_state = self.detection.start_search_session(target)
                    self.context.active_search_session_id = search_session_state.session_id
                    self.context.last_referenced_object = target
                    answer_ar = search_session_state.direction_text_ar
            elif action == "update":
                if not session_id or not request.image_base64:
                    answer_ar = "جلسة البحث غير نشطة أو لا توجد صورة للكاميرا."
                else:
                    search_session_state = self.detection.step_search_session(
                        session_id=session_id,
                        image_input=request.image_base64,
                        mirrored=bool(request.mirrored),
                    )
                    answer_ar = search_session_state.direction_text_ar
            elif action == "stop":
                if session_id:
                    search_session_state = self.detection.stop_search_session(session_id)
                    self.context.active_search_session_id = None
                answer_ar = "تم إيقاف البحث."
            source_components.append("yolo11n_continuous_search")

        elif mode == "find":
            if not request.image_base64:
                answer_ar = "يرجى تشغيل الكاميرا لتحديد موقع الكائن."
            else:
                source_components.append("yolo11n")
                t_det_start = time.perf_counter()
                det_res = self.detection.detect(
                    image_input=request.image_base64,
                    target_object_ar=target_obj,
                    frame_id=request.frame_id,
                    mirrored=bool(request.mirrored),
                )
                timings["inference_ms"] = det_res.latency_ms
                timings["detection_ms"] = det_res.latency_ms
                timings["yolo_ms"] = det_res.latency_ms
                details["detection"] = det_res.model_dump()
                answer_ar = det_res.summary_ar
                if target_obj and det_res.target_found:
                    self.context.last_referenced_object = target_obj

        elif mode == "read":
            if not request.image_base64:
                answer_ar = "يرجى تشغيل الكاميرا أو التقاط صورة لقراءة النص."
            else:
                source_components.append("easyocr")
                ocr_res = self.ocr.recognize(request.image_base64, frame_id=request.frame_id)
                timings["inference_ms"] = ocr_res.latency_ms
                timings["ocr_ms"] = ocr_res.latency_ms
                details["ocr"] = ocr_res.model_dump()

                if ocr_res.status == "ok":
                    # Check document positioning & text size guidance
                    try:
                        import numpy as np
                        from PIL import Image
                        raw_bytes = base64.b64decode(request.image_base64.split(",", 1)[-1])
                        img_dim = Image.open(io.BytesIO(raw_bytes)).size  # (w, h)
                        guidance = self.quality_analyzer.analyze_ocr_guidance((img_dim[1], img_dim[0]), ocr_res.items)
                    except Exception:
                        guidance = None

                    if guidance:
                        details["ocr_guidance"] = guidance

                    if ocr_res.text_combined.strip():
                        guidance_prefix = f"({guidance['advice_ar']}) " if guidance else ""
                        answer_ar = f"{guidance_prefix}النص المكتوب هو: {ocr_res.text_combined}"
                    else:
                        if guidance:
                            answer_ar = f"لم يتم العثور على نص واضح. {guidance['advice_ar']}"
                        else:
                            answer_ar = "لم يتم العثور على أي نص مقروء في هذه الصورة."
                else:
                    answer_ar = f"تعذر قراءة النص: {ocr_res.error or 'خطأ في التعرف الضوئي'}"

        elif mode in ("describe", "ask"):
            if mode == "ask":
                prompt = f"{query_text} (أجب بتفصيل ودقة باللغة العربية)" if model_mode_used == "detailed" else query_text
            else:
                prompt = "صف ما تراه في هذا المشهد بتفصيل دقيق واذكر كافة الأغراض ومواقعها بالنسبة للمستخدم." if model_mode_used == "detailed" else "صف ما تراه في هذا المشهد باختصار ودقة."
            source_components.append(f"vlm_{model_mode_used}")
            t_vlm_start = time.perf_counter()
            vlm_res = self.vlm.ask(
                question=prompt,
                image_input=request.image_base64,
                frame_id=request.frame_id,
                model_mode=model_mode_used,
            )
            timings["inference_ms"] = vlm_res.latency_ms
            timings["vlm_ms"] = vlm_res.latency_ms
            timings["vlm_ttft_ms"] = vlm_res.latency_ms
            details["vlm"] = vlm_res.model_dump()
            model_mode_used = vlm_res.model_mode

            if vlm_res.status == "ok" and vlm_res.answer_ar:
                answer_ar = vlm_res.answer_ar
            else:
                # Degraded fallback with clear labeling
                vlm_err = vlm_res.error or "نموذج الرؤية غير متصل"
                if request.image_base64:
                    det_fallback = self.detection.detect(request.image_base64, frame_id=request.frame_id)
                    timings["detection_fallback_ms"] = det_fallback.latency_ms
                    answer_ar = f"(وضع محدود: {vlm_err}). {det_fallback.summary_ar}"
                    source_components.append("yolo11n_fallback")
                else:
                    answer_ar = f"تعذر إكمال الوصف البصري: {vlm_err}"

        # Update in-memory conversational session context
        if answer_ar and mode not in ("repeat", "shorten", "reset", "search_session"):
            self.context.update(
                command=query_text or mode,
                answer=answer_ar,
                mode=mode,
                target_obj=target_obj,
            )

        # Check in-flight cancellation before synthesis
        if self.is_cancelled(req_id):
            return AssistResponse(
                request_id=req_id,
                frame_id=request.frame_id,
                mode=mode,
                query_text=query_text,
                answer_ar="",
                status="cancelled",
                stage_timings_ms=timings,
                total_latency_ms=round((time.perf_counter() - t_total_start) * 1000, 2),
            )

        # 5. Speech Synthesis (Piper TTS)
        audio_b64 = None
        should_speak = True
        # For continuous search updates, only speak if direction changed or disappeared
        if search_session_state and not search_session_state.should_announce:
            should_speak = False

        if answer_ar and should_speak:
            speech_text = search_session_state.announcement_text_ar if search_session_state and search_session_state.announcement_text_ar else answer_ar
            source_components.append("piper-tts")
            speed = request.speech_speed or 1.0
            # Piper length_scale is inverse of speed
            effective_length_scale = self.config.tts.length_scale / max(0.5, speed)
            tts_res = self.tts.speak(speech_text, length_scale=effective_length_scale)
            timings["tts_ms"] = tts_res.latency_ms
            if tts_res.status == "ok":
                audio_b64 = tts_res.audio_base64
            else:
                details["tts_error"] = tts_res.error

        total_latency = round((time.perf_counter() - t_total_start) * 1000, 2)

        return AssistResponse(
            request_id=req_id,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S+03:00"),
            frame_id=request.frame_id,
            mode=mode,
            model_mode=model_mode_used,
            query_text=query_text,
            answer_ar=answer_ar,
            audio_base64=audio_b64,
            status="ok",
            source_components=source_components,
            stage_timings_ms=timings,
            total_latency_ms=total_latency,
            search_session=search_session_state,
            frame_quality=quality_report.to_dict() if quality_report else None,
            details=details,
        )

    def execute_assist_stream(self, request: AssistRequest):
        """Yields Server-Sent Events (SSE) for immediate TTFT and incremental sentence TTS playback."""
        t_total_start = time.perf_counter()
        req_id = str(uuid.uuid4())[:8]
        timings: Dict[str, float] = {}
        source_components: list[str] = []
        details: Dict[str, Any] = {}

        def sse_event(data: dict) -> str:
            return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        # 1. Speech Transcription (if audio provided)
        query_text = (request.query_text or "").strip()
        if request.audio_base64:
            asr_res = self.asr.transcribe(
                audio_base64=request.audio_base64,
                audio_format=request.audio_format or "webm",
            )
            timings["transcription_ms"] = asr_res.latency_ms
            timings["asr_ms"] = asr_res.latency_ms
            source_components.append("faster-whisper")
            if asr_res.status == "ok" and asr_res.transcript:
                query_text = asr_res.transcript
                details["transcription"] = asr_res.model_dump()
                yield sse_event({"type": "transcription", "query_text": query_text, "latency_ms": asr_res.latency_ms})
            else:
                resp = AssistResponse(
                    request_id=req_id,
                    frame_id=request.frame_id,
                    mode="transcribe_failed",
                    query_text="",
                    answer_ar="لم أتمكن من سماع سؤالك بوضوح، يرجى إعادة التحدث أو كتابة السؤال.",
                    status="asr_empty_or_failed",
                    source_components=source_components,
                    stage_timings_ms=timings,
                    total_latency_ms=round((time.perf_counter() - t_total_start) * 1000, 2),
                    error=asr_res.error,
                )
                yield sse_event({"type": "done", "response": resp.model_dump()})
                return

        # Spoken cancel/stop command check
        norm_q = self.normalize_arabic(query_text)
        stop_commands = ["توقف", "بس", "اسكت", "وقف", "كافي", "stop"]
        if any(norm_q == cmd for cmd in stop_commands):
            if self.context.active_search_session_id:
                self.detection.stop_search_session(self.context.active_search_session_id)
                self.context.active_search_session_id = None
            resp = AssistResponse(
                request_id=req_id,
                frame_id=request.frame_id,
                mode="stop",
                query_text=query_text,
                answer_ar="تم التوقف.",
                status="cancelled",
                stage_timings_ms=timings,
                total_latency_ms=round((time.perf_counter() - t_total_start) * 1000, 2),
            )
            yield sse_event({"type": "done", "response": resp.model_dump()})
            return

        # 2. Intent Routing
        t_route_start = time.perf_counter()
        if not query_text and request.mode == "auto":
            mode = "describe"
            target_obj = None
        elif request.mode and request.mode != "auto":
            mode = request.mode
            target_obj = request.target_object_ar
        else:
            mode, target_obj = self.route_intent(query_text)
        timings["intent_routing_ms"] = round((time.perf_counter() - t_route_start) * 1000, 2)
        details["resolved_mode"] = mode
        if target_obj:
            details["target_object_ar"] = target_obj

        yield sse_event({
            "type": "init",
            "request_id": req_id,
            "mode": mode,
            "query_text": query_text,
            "target_object_ar": target_obj,
        })

        if self.is_cancelled(req_id):
            return

        if mode != "search_session" and self.context.active_search_session_id:
            self.detection.stop_search_session(self.context.active_search_session_id)
            self.context.active_search_session_id = None

        # 3. Smart Frame Quality Analysis
        quality_report = None
        if request.image_base64 and mode not in ("repeat", "shorten", "reset", "greeting"):
            quality_report = self.quality_analyzer.analyze(
                image_input=request.image_base64,
                frame_timestamp=request.frame_timestamp_ms / 1000.0 if request.frame_timestamp_ms else None,
                force_override=bool(request.override_quality),
            )
            timings["quality_check_ms"] = quality_report.duration_ms
            details["frame_quality"] = quality_report.to_dict()

            if not quality_report.is_usable and not request.override_quality:
                guidance_answer = quality_report.advice_ar or "الصورة غير واضحة، يرجى ضبط الكاميرا."
                audio_b64 = None
                if quality_report.should_speak:
                    tts_res = self.tts.speak(guidance_answer)
                    timings["tts_ms"] = tts_res.latency_ms
                    audio_b64 = tts_res.audio_base64 if tts_res.status == "ok" else None

                resp = AssistResponse(
                    request_id=req_id,
                    frame_id=request.frame_id,
                    mode="quality_guidance",
                    query_text=query_text,
                    answer_ar=guidance_answer,
                    audio_base64=audio_b64,
                    status="frame_unusable",
                    frame_quality=quality_report.to_dict(),
                    source_components=["quality_analyzer", "piper-tts"] if audio_b64 else ["quality_analyzer"],
                    stage_timings_ms=timings,
                    total_latency_ms=round((time.perf_counter() - t_total_start) * 1000, 2),
                )
                yield sse_event({
                    "type": "quality_guidance",
                    "guidance": quality_report.to_dict(),
                    "answer_ar": guidance_answer,
                    "audio_base64": audio_b64,
                })
                yield sse_event({"type": "done", "response": resp.model_dump()})
                return

        # 4. Mode Routing
        speed = request.speech_speed or 1.0
        effective_length_scale = self.config.tts.length_scale / max(0.5, speed)

        # For VLM modes ("describe", "ask"):
        if mode in ("describe", "ask"):
            requested_vlm_mode = (request.model_mode or "fast").lower()
            if mode == "ask":
                prompt = f"{query_text} (أجب بتفصيل ودقة باللغة العربية)" if requested_vlm_mode == "detailed" else query_text
            else:
                prompt = "صف ما تراه في هذا المشهد بتفصيل دقيق واذكر كافة الأغراض ومواقعها بالنسبة للمستخدم." if requested_vlm_mode == "detailed" else "صف ما تراه في هذا المشهد باختصار ودقة."
            source_components.append("vlm_fast" if requested_vlm_mode == "fast" else "vlm_detailed")

            sentence_buffer = ""
            full_answer_list: list[str] = []
            sentence_idx = 0
            first_ttft_ms = None

            for stream_item in self.vlm.ask_stream(
                question=prompt,
                image_input=request.image_base64,
                frame_id=request.frame_id,
                model_mode=requested_vlm_mode,
            ):
                if self.is_cancelled(req_id):
                    return

                if stream_item["type"] == "token":
                    tok = stream_item["token"]
                    full_answer_list.append(tok)
                    sentence_buffer += tok
                    if first_ttft_ms is None and "ttft_ms" in stream_item:
                        first_ttft_ms = stream_item["ttft_ms"]

                    yield sse_event({
                        "type": "token",
                        "token": tok,
                        "ttft_ms": stream_item.get("ttft_ms"),
                    })

                    # Natural Arabic clause & sentence delimiter chunking for ultra-fast TTFA (<2s)
                    candidate = sentence_buffer.strip()
                    words = candidate.split()
                    word_count = len(words)

                    should_chunk = False
                    if re.search(r"[.!؟\n]", sentence_buffer) and word_count >= 2:
                        should_chunk = True
                    elif re.search(r"[،,؛:]", sentence_buffer) and word_count >= 3:
                        should_chunk = True
                    elif word_count >= 6 and (tok.endswith(" ") or tok.endswith("\n") or tok.endswith("،") or tok.endswith(".")):
                        should_chunk = True

                    if should_chunk:
                        cleaned = re.sub(r"[\*_#`]+", "", candidate)
                        sentence_to_speak = re.sub(r"^[-*•\s]+", "", cleaned).strip()
                        sentence_buffer = ""
                        has_ar = bool(re.search(r"[\u0600-\u06FF]", sentence_to_speak))
                        if sentence_to_speak and has_ar:
                            tts_res = self.tts.speak(sentence_to_speak, length_scale=effective_length_scale)
                            if tts_res.status == "ok" and tts_res.audio_base64:
                                timings["tts_ms"] = round(timings.get("tts_ms", 0.0) + tts_res.latency_ms, 2)
                                yield sse_event({
                                    "type": "audio_chunk",
                                    "audio_base64": tts_res.audio_base64,
                                    "sentence": sentence_to_speak,
                                    "sentence_index": sentence_idx,
                                    "latency_ms": tts_res.latency_ms,
                                })
                                sentence_idx += 1

                elif stream_item["type"] == "error":
                    det_fallback = self.detection.detect(request.image_base64, frame_id=request.frame_id) if request.image_base64 else None
                    fb_text = f"(وضع محدود: {stream_item.get('error')}). {det_fallback.summary_ar}" if det_fallback else f"تعذر إكمال الوصف: {stream_item.get('error')}"
                    fb_tts = self.tts.speak(fb_text, length_scale=effective_length_scale)
                    timings["tts_ms"] = round(timings.get("tts_ms", 0.0) + fb_tts.latency_ms, 2)
                    yield sse_event({"type": "token", "token": fb_text})
                    yield sse_event({"type": "audio_chunk", "audio_base64": fb_tts.audio_base64, "sentence": fb_text, "sentence_index": 0, "latency_ms": fb_tts.latency_ms})
                    resp = AssistResponse(
                        request_id=req_id,
                        frame_id=request.frame_id,
                        mode=mode,
                        query_text=query_text,
                        answer_ar=fb_text,
                        audio_base64=fb_tts.audio_base64,
                        status="vlm_fallback",
                        stage_timings_ms=timings,
                        total_latency_ms=round((time.perf_counter() - t_total_start) * 1000, 2),
                    )
                    yield sse_event({"type": "done", "response": resp.model_dump()})
                    return

                elif stream_item["type"] == "done":
                    timings["inference_ms"] = stream_item.get("latency_ms", 0.0)
                    timings["vlm_ms"] = stream_item.get("latency_ms", 0.0)
                    timings["ttft_ms"] = stream_item.get("ttft_ms", 0.0)
                    timings["vlm_ttft_ms"] = stream_item.get("ttft_ms", 0.0)
                    final_answer = stream_item.get("answer_ar") or "".join(full_answer_list).strip()

                    # Flush remaining sentence buffer
                    candidate = sentence_buffer.strip()
                    cleaned = re.sub(r"[\*_#`]+", "", candidate)
                    sentence_to_speak = re.sub(r"^[-*•\s]+", "", cleaned).strip()
                    sentence_buffer = ""
                    has_ar = bool(re.search(r"[\u0600-\u06FF]", sentence_to_speak))
                    if sentence_to_speak and has_ar:
                        tts_res = self.tts.speak(sentence_to_speak, length_scale=effective_length_scale)
                        if tts_res.status == "ok" and tts_res.audio_base64:
                            timings["tts_ms"] = round(timings.get("tts_ms", 0.0) + tts_res.latency_ms, 2)
                            yield sse_event({
                                "type": "audio_chunk",
                                "audio_base64": tts_res.audio_base64,
                                "sentence": sentence_to_speak,
                                "sentence_index": sentence_idx,
                                "latency_ms": tts_res.latency_ms,
                            })
                            sentence_idx += 1

                    # Update context memory
                    self.context.update(
                        command=query_text or mode,
                        answer=final_answer,
                        mode=mode,
                        target_obj=target_obj,
                    )

                    resp = AssistResponse(
                        request_id=req_id,
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S+03:00"),
                        frame_id=request.frame_id,
                        mode=mode,
                        model_mode=requested_vlm_mode,
                        query_text=query_text,
                        answer_ar=final_answer,
                        audio_base64=None,
                        status="ok",
                        source_components=source_components,
                        stage_timings_ms=timings,
                        total_latency_ms=round((time.perf_counter() - t_total_start) * 1000, 2),
                        frame_quality=quality_report.to_dict() if quality_report else None,
                        details=details,
                    )
                    yield sse_event({"type": "done", "response": resp.model_dump()})
                    return

        # For OCR Read Mode: Stream line-by-line immediately without waiting for full page synthesis
        if mode == "read":
            if not request.image_base64:
                msg = "يرجى تشغيل الكاميرا أو التقاط صورة لقراءة النص."
                yield sse_event({"type": "token", "token": msg})
                fb_tts = self.tts.speak(msg, length_scale=effective_length_scale)
                if fb_tts.status == "ok" and fb_tts.audio_base64:
                    yield sse_event({"type": "audio_chunk", "audio_base64": fb_tts.audio_base64, "sentence": msg, "sentence_index": 0})
                resp = AssistResponse(
                    request_id=req_id,
                    frame_id=request.frame_id,
                    mode=mode,
                    query_text=query_text,
                    answer_ar=msg,
                    status="empty_image",
                    stage_timings_ms=timings,
                    total_latency_ms=round((time.perf_counter() - t_total_start) * 1000, 2),
                )
                yield sse_event({"type": "done", "response": resp.model_dump()})
                return

            # 1. Immediate generic processing notification
            yield sse_event({
                "type": "ocr_status",
                "stage": "processing_notice",
                "message": "جاري فحص وقراءة النصوص في الصورة...",
            })
            yield sse_event({"type": "token", "token": "جاري قراءة النصوص في الصورة...\n\n", "is_ocr_notice": True})
            source_components.append("easyocr")
            t_ocr_start = time.perf_counter()
            ocr_res = self.ocr.recognize(request.image_base64, frame_id=request.frame_id)
            timings["inference_ms"] = ocr_res.latency_ms
            timings["ocr_ms"] = ocr_res.latency_ms
            details["ocr"] = ocr_res.model_dump()

            if ocr_res.status == "ok" and ocr_res.text_combined.strip():
                # Document placement guidance
                guidance = None
                try:
                    import io
                    raw_bytes = base64.b64decode(request.image_base64.split(",", 1)[-1])
                    img_dim = Image.open(io.BytesIO(raw_bytes)).size
                    guidance = self.quality_analyzer.analyze_ocr_guidance((img_dim[1], img_dim[0]), ocr_res.items)
                except Exception:
                    pass

                guidance_prefix = f"({guidance['advice_ar']}) " if guidance else ""
                full_text = f"{guidance_prefix}النص المكتوب هو:\n{ocr_res.text_combined}"
                lines = [line.strip() for line in ocr_res.text_combined.split("\n") if line.strip()]

                # 2. Distinct actual OCR text delivery event!
                yield sse_event({
                    "type": "ocr_delivered",
                    "stage": "text_delivered",
                    "ocr_latency_ms": ocr_res.latency_ms,
                    "lines_count": len(lines),
                    "text_combined": ocr_res.text_combined,
                })
                
                # Yield preamble and text tokens, signaling to replace generic notice
                yield sse_event({
                    "type": "token",
                    "token": f"{guidance_prefix}النص المكتوب هو:\n",
                    "is_ocr_delivered": True,
                    "replace_notice": True,
                })
                for line in lines:
                    yield sse_event({
                        "type": "token",
                        "token": f"{line}\n",
                        "is_ocr_delivered": True,
                    })

                # First audible chunk: read preamble and first line immediately!
                first_sentence = f"{guidance_prefix}النص المكتوب هو: {lines[0]}" if lines else full_text
                tts_line1 = self.tts.speak(first_sentence, length_scale=effective_length_scale)
                if tts_line1.status == "ok" and tts_line1.audio_base64:
                    timings["tts_ms"] = round(timings.get("tts_ms", 0.0) + tts_line1.latency_ms, 2)
                    yield sse_event({
                        "type": "audio_chunk",
                        "audio_base64": tts_line1.audio_base64,
                        "sentence": first_sentence,
                        "sentence_index": 0,
                        "latency_ms": tts_line1.latency_ms,
                    })

                # Stream remaining lines as subsequent audio chunks
                for s_idx, line in enumerate(lines[1:], start=1):
                    if len(line.split()) >= 1:
                        tts_line = self.tts.speak(line, length_scale=effective_length_scale)
                        if tts_line.status == "ok" and tts_line.audio_base64:
                            timings["tts_ms"] = round(timings.get("tts_ms", 0.0) + tts_line.latency_ms, 2)
                            yield sse_event({
                                "type": "audio_chunk",
                                "audio_base64": tts_line.audio_base64,
                                "sentence": line,
                                "sentence_index": s_idx,
                                "latency_ms": tts_line.latency_ms,
                            })

                self.context.update(command=query_text or "اقرأ النص", answer=full_text, mode="read")
                resp = AssistResponse(
                    request_id=req_id,
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%S+03:00"),
                    frame_id=request.frame_id,
                    mode=mode,
                    model_mode="fast",
                    query_text=query_text,
                    answer_ar=full_text,
                    status="ok",
                    source_components=source_components,
                    stage_timings_ms=timings,
                    total_latency_ms=round((time.perf_counter() - t_total_start) * 1000, 2),
                    details=details,
                )
                yield sse_event({"type": "done", "response": resp.model_dump()})
                return
            else:
                empty_msg = "لم يتم العثور على أي نص مقروء في هذه الصورة."
                yield sse_event({
                    "type": "ocr_delivered",
                    "stage": "empty",
                    "ocr_latency_ms": ocr_res.latency_ms,
                    "lines_count": 0,
                })
                yield sse_event({
                    "type": "token",
                    "token": empty_msg,
                    "is_ocr_delivered": True,
                    "replace_notice": True,
                })
                fb_tts = self.tts.speak(empty_msg, length_scale=effective_length_scale)
                if fb_tts.status == "ok" and fb_tts.audio_base64:
                    timings["tts_ms"] = round(timings.get("tts_ms", 0.0) + fb_tts.latency_ms, 2)
                    yield sse_event({
                        "type": "audio_chunk",
                        "audio_base64": fb_tts.audio_base64,
                        "sentence": empty_msg,
                        "sentence_index": 0,
                        "latency_ms": fb_tts.latency_ms,
                    })
                resp = AssistResponse(
                    request_id=req_id,
                    frame_id=request.frame_id,
                    mode=mode,
                    query_text=query_text,
                    answer_ar=empty_msg,
                    status="ocr_empty",
                    source_components=source_components,
                    stage_timings_ms=timings,
                    total_latency_ms=round((time.perf_counter() - t_total_start) * 1000, 2),
                )
                yield sse_event({"type": "done", "response": resp.model_dump()})
                return

        # For remaining non-VLM modes (find, greeting, repeat, shorten, reset), execute standard logic
        standard_resp = self.execute_assist(request)
        yield sse_event({"type": "token", "token": standard_resp.answer_ar})
        if standard_resp.audio_base64:
            yield sse_event({
                "type": "audio_chunk",
                "audio_base64": standard_resp.audio_base64,
                "sentence": standard_resp.answer_ar,
                "sentence_index": 0,
            })
        yield sse_event({"type": "done", "response": standard_resp.model_dump()})
