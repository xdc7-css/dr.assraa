"""Central Orchestrator integrating ASR, Intent Routing, Detection, OCR, VLM, and TTS."""
from __future__ import annotations

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
    AskResponse,
    AssistRequest,
    AssistResponse,
    DetectResponse,
    OCRResponse,
    SpeakResponse,
    TranscribeResponse,
)

class Orchestrator:
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or get_config()
        self.asr = ASRAdapter(self.config.asr)
        self.detection = DetectionAdapter(self.config.detection)
        self.ocr = OCRAdapter(self.config.ocr)
        self.vlm = VLMAdapter(self.config.vlm)
        self.tts = TTSAdapter(self.config.tts)
        self.quality_analyzer = FrameQualityAnalyzer()

        # In-memory session state for latest response and repeat functionality
        self.last_valid_answer_ar: str = "لا توجد إجابة سابقة لإعادتها بعد."
        self.last_request_id: Optional[str] = None
        self._active_cancelled_request_ids: set[str] = set()

    def cancel_request(self, request_id: str):
        self._active_cancelled_request_ids.add(request_id)

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
        Modes: 'repeat', 'read', 'find', 'describe', 'greeting', 'ask'
        """
        norm = self.normalize_arabic(query)
        if not norm:
            return "unknown", None
        words = norm.split()

        # 0. Greetings / Conversational pleasantries
        greetings = ["مرحبا", "اهلا", "السلام عليكم", "صباح الخير", "مساء الخير", "شكرا", "تسلم", "عاشت ايدك", "يعطيك العافيه", "hello", "hi"]
        if any(norm == g or norm.startswith(g + " ") for g in greetings):
            return "greeting", None

        # 1. Repeat check (Iraqi & Fusha)
        repeat_patterns = ["كرر", "عيد", "اعد", "شنو كلت", "شنو قلت", "ما سمعتك", "كرر الجواب", "عيد الجواب", "عيد الكلام", "اعد ما قلته", "repeat", "again"]
        if any(p in norm for p in repeat_patterns):
            return "repeat", None

        # 2. Read / OCR check
        read_patterns = ["اقرا", "قراءه", "المكتوب", "شنو مكتوب", "ماذا كتب", "ايش مكتوب", "شكو مكتوب", "النص", "اقرا النص", "اقرالي", "قراءة النص", "read"]
        if any(p in norm for p in read_patterns):
            return "read", None

        # 3. Find / Locate object check (Iraqi: "وين القنينة", "شوفلي وين الكرسي", "تلكالي الكوب", "دورلي على اللابتوب")
        find_triggers = ["وين صايرة", "وين صاير", "وين", "اين", "دورلي على", "دور على", "دور", "ابحث عن", "شوفلي وين", "شوفلي", "تلكالي", "تلقالي", "لقيت", "find", "where is", "where"]
        for trigger in find_triggers:
            if trigger in words or norm.startswith(trigger) or trigger in norm:
                # Extract the object query after the trigger
                pattern = rf"(?:^|\s){re.escape(trigger)}\s+(.*)"
                m = re.search(pattern, norm)
                target = m.group(1).strip() if m else ""
                # Strip leading articles like 'ال'
                target_clean = re.sub(r"^(ال|ا)", "", target).strip()
                if not target_clean:
                    target_clean = target
                return "find", target_clean or None

        # 4. Describe scene check (Iraqi & Fusha: "شنو كدامي", "شنو قدامي", "شكو كدامي", "ايش كدامي", "صف المشهد", "ماذا أمامي", "ماذا يوجد أمامي")
        describe_patterns = ["قدامي", "كدامي", "امامي", "صف المشهد", "صف ما ترى", "ايش في قدامي", "ايش كدامي", "شنو اكو", "شنو موجود", "شكو كدامي", "شكو قدامي", "بينلي المشهد", "describe"]
        if any(p in norm for p in describe_patterns):
            return "describe", None

        # 5. Default to VQA / Multimodal question
        return "ask", None

    def execute_assist(self, request: AssistRequest) -> AssistResponse:
        t_total_start = time.perf_counter()
        req_id = str(uuid.uuid4())[:8]
        timings: Dict[str, float] = {}
        source_components: list[str] = []
        details: Dict[str, Any] = {}

        # 1. Speech Transcription (if audio provided)
        query_text = (request.query_text or "").strip()
        if request.audio_base64:
            t_asr = time.perf_counter()
            asr_res = self.asr.transcribe(
                audio_base64=request.audio_base64,
                audio_format=request.audio_format or "webm",
            )
            timings["asr_ms"] = asr_res.latency_ms
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

        if not query_text and request.mode == "auto":
            # No text and no audio: default to describe scene if image is present
            mode = "describe"
            target_obj = None
        elif request.mode and request.mode != "auto":
            mode = request.mode
            target_obj = request.target_object_ar
        else:
            mode, target_obj = self.route_intent(query_text)

        details["resolved_mode"] = mode
        if target_obj:
            details["target_object_ar"] = target_obj

        # Check cancellation
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

        # Check empty input
        if not query_text and not request.image_base64 and mode not in ("repeat", "greeting"):
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

        # Run frame quality analysis if an image is provided
        quality_report = None
        if request.image_base64:
            quality_report = self.quality_analyzer.analyze(request.image_base64)
            details["frame_quality"] = quality_report.to_dict()

        answer_ar = ""

        # 2. Execute selected pipeline mode
        if mode == "greeting":
            answer_ar = "أهلاً وسهلاً بك. أنا مساعدك البصري الذكي. يمكنك سؤالي عما يوجد أمامك، أو طلب قراءة نص، أو البحث عن كائن معين."
            source_components.append("intent_router")

        elif mode == "repeat":
            answer_ar = self.last_valid_answer_ar
            source_components.append("memory_cache")

        elif mode == "read":
            if not request.image_base64:
                answer_ar = "يرجى تشغيل الكاميرا أو التقاط صورة لقراءة النص."
            elif quality_report and quality_report.issue == "underexposed":
                answer_ar = f"تنبيه: الصورة معتمة جداً. {quality_report.advice_ar}"
            else:
                source_components.append("easyocr")
                ocr_res = self.ocr.recognize(request.image_base64, frame_id=request.frame_id)
                timings["ocr_ms"] = ocr_res.latency_ms
                details["ocr"] = ocr_res.model_dump()
                if ocr_res.status == "ok":
                    if ocr_res.text_combined.strip():
                        prefix = "(تنبيه: الصورة مشوشة). " if (quality_report and quality_report.issue == "blurry") else ""
                        answer_ar = f"{prefix}النص المكتوب هو: {ocr_res.text_combined}"
                    else:
                        if quality_report and quality_report.issue == "blurry":
                            answer_ar = f"لم يتم العثور على نص واضح. {quality_report.advice_ar}"
                        else:
                            answer_ar = "لم يتم العثور على أي نص مقروء في هذه الصورة."
                else:
                    answer_ar = f"تعذر قراءة النص: {ocr_res.error or 'خطأ في التعرف الضوئي'}"

        elif mode == "find":
            if not request.image_base64:
                answer_ar = "يرجى تشغيل الكاميرا لتحديد موقع الكائن."
            else:
                source_components.append("yolo11n")
                det_res = self.detection.detect(
                    image_input=request.image_base64,
                    target_object_ar=target_obj,
                    frame_id=request.frame_id,
                )
                timings["detection_ms"] = det_res.latency_ms
                details["detection"] = det_res.model_dump()
                answer_ar = det_res.summary_ar

        elif mode in ("describe", "ask"):
            # If pitch black, warn immediately with retake guidance
            if request.image_base64 and quality_report and quality_report.issue == "underexposed":
                answer_ar = f"تنبيه: الصورة معتمة ومظلمة جداً. {quality_report.advice_ar}"
            else:
                # Route to VLM (Qwen3-VL 2B Instruct via Ollama)
                prompt = query_text if mode == "ask" else "صف ما تراه في هذا المشهد باختصار ودقة."
                source_components.append(self.vlm.config.model_tag)
                vlm_res = self.vlm.ask(
                    question=prompt,
                    image_input=request.image_base64,
                    frame_id=request.frame_id,
                )
                timings["vlm_ms"] = vlm_res.latency_ms
                details["vlm"] = vlm_res.model_dump()

                if vlm_res.status == "ok" and vlm_res.answer_ar:
                    answer_ar = vlm_res.answer_ar
                else:
                    # Graceful degraded fallback mode with clear labeling
                    vlm_err = vlm_res.error or "نموذج الرؤية غير متصل"
                    if request.image_base64:
                        det_fallback = self.detection.detect(request.image_base64, frame_id=request.frame_id)
                        timings["detection_fallback_ms"] = det_fallback.latency_ms
                        answer_ar = f"(وضع محدود: {vlm_err}). {det_fallback.summary_ar}"
                        source_components.append("yolo11n_fallback")
                    else:
                        answer_ar = f"تعذر إكمال الوصف البصري: {vlm_err}"

        # Update latest valid answer memory if answer is valid
        if answer_ar and mode != "repeat":
            self.last_valid_answer_ar = answer_ar
            self.last_request_id = req_id

        # 3. Speech Synthesis (TTS via Piper)
        audio_b64 = None
        if answer_ar:
            source_components.append("piper-tts")
            tts_res = self.tts.speak(answer_ar)
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
            query_text=query_text,
            answer_ar=answer_ar,
            audio_base64=audio_b64,
            status="ok",
            source_components=source_components,
            stage_timings_ms=timings,
            total_latency_ms=total_latency,
            details=details,
        )
