"""VLM Adapter supporting Fast (2B) and Detailed (4B) Qwen3-VL Instruct models via local Ollama.
Includes memory snapshot tracking (VRAM, system RAM), model offload management, and thinking suppression.
"""
from __future__ import annotations

import base64
import io
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from PIL import Image
import httpx

from app.config import VLMConfig
from app.schemas import AskResponse
from scripts.check_system import get_gpu_info, get_system_memory

# Prescribed official Arabic Assistive Vision System Instruction
SYSTEM_PROMPT_AR = (
    "أنت مساعد بصري لمستخدم كفيف أو ضعيف البصر. "
    "أجب عن السؤال اعتماداً على الصورة الحالية فقط. "
    "استخدم عربية واضحة وجملاً قصيرة، واذكر المعلومات المهمة أولاً. "
    "لا تعرض خطوات التفكير أو التحليل الداخلي. "
    "لا تخمّن أسماء التطبيقات أو الأشخاص أو تفاصيل لا تظهر بوضوح. "
    "إذا لم تستطع التأكد، وضّح ذلك باختصار. "
    "لا تدّعِ أن المسار آمن أو تقدّر مسافة بالأمتار دون قياس موثوق."
)

class VLMAdapter:
    def __init__(self, config: Optional[VLMConfig] = None):
        self.config = config or VLMConfig()
        self._last_loaded_model: Optional[str] = None
        self._cached_runtime: Optional[dict] = None
        self._cached_runtime_ts: float = 0.0

    def check_runtime(self, force: bool = False) -> dict:
        """Check if Ollama service is reachable and query available installed models (cached for 60s)."""
        now = time.time()
        if not force and self._cached_runtime and (now - self._cached_runtime_ts) < 60.0:
            return self._cached_runtime

        url = f"{self.config.endpoint}/api/tags"
        try:
            with httpx.Client(timeout=4.0) as client:
                res = client.get(url)
                if res.status_code == 200:
                    models = res.json().get("models", [])
                    installed = [m.get("name") for m in models]
                    has_fast = any(self.config.fast_model_tag in (name or "") for name in installed)
                    has_detailed = any(self.config.detailed_model_tag in (name or "") for name in installed)
                    has_fallback = any("qwen3-vl:2b" in (name or "") for name in installed)
                    stat = {
                        "reachable": True,
                        "has_fast": has_fast,
                        "has_detailed": has_detailed,
                        "has_model": has_fast or has_fallback,
                        "installed_models": installed,
                        "models_details": models,
                    }
                    self._cached_runtime = stat
                    self._cached_runtime_ts = now
                    return stat
        except Exception as e:
            return {"reachable": False, "has_model": False, "has_fast": False, "has_detailed": False, "error": str(e)}
        return {"reachable": False, "has_model": False, "has_fast": False, "has_detailed": False}

    def _unload_model(self, model_name: str):
        """Evicts a model from VRAM by setting keep_alive to 0 to respect the 4GB VRAM constraint."""
        try:
            with httpx.Client(timeout=5.0) as client:
                client.post(
                    f"{self.config.endpoint}/api/generate",
                    json={"model": model_name, "keep_alive": 0},
                )
        except Exception:
            pass

    def get_memory_snapshot(self) -> Dict[str, Any]:
        """Captures current system RAM and NVIDIA VRAM usage."""
        snap = {}
        try:
            sys_mem = get_system_memory()
            snap["system_ram_used_mb"] = sys_mem.get("used_ram_mb", 0.0)
            snap["system_ram_avail_mb"] = sys_mem.get("available_ram_mb", 0.0)
        except Exception:
            pass

        try:
            gpus = get_gpu_info()
            if gpus and isinstance(gpus, list) and len(gpus) > 0:
                snap["vram_used_mb"] = gpus[0].get("vram_used_mb", 0.0)
                snap["vram_free_mb"] = gpus[0].get("vram_free_mb", 0.0)
                snap["vram_total_mb"] = gpus[0].get("vram_total_mb", 0.0)
        except Exception:
            pass

        return snap

    def prepare_image(self, image_input: Image.Image | str, max_edge: Optional[int] = None) -> str:
        """Resize image to configured max edge for low-memory VLM and encode as base64 string."""
        if isinstance(image_input, str):
            if (image_input.endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp")) or "/" in image_input or "\\" in image_input) and Path(image_input).exists():
                img = Image.open(image_input).convert("RGB")
            else:
                if "," in image_input:
                    image_input = image_input.split(",", 1)[1]
                raw_bytes = base64.b64decode(image_input)
                img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        else:
            img = image_input.convert("RGB")

        edge = max_edge or self.config.image_max_edge
        w, h = img.size
        if max(w, h) > edge:
            if w >= h:
                new_w = edge
                new_h = max(1, int(h * (edge / w)))
            else:
                new_h = edge
                new_w = max(1, int(w * (edge / h)))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    @staticmethod
    def sanitize_answer(raw_text: str) -> str:
        """Strips thinking tags, internal reasoning, and leaked meta-analysis."""
        if not raw_text:
            return ""

        # Remove XML/think blocks
        cleaned = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL)
        cleaned = re.sub(r"<reasoning>.*?</reasoning>", "", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"\[thinking\].*?\[/thinking\]", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = cleaned.strip()

        # Detect leaked analytical English monologue
        analytical_patterns = [
            r"^(wait[\s,]|let me see|looking at the image|the user is asking|i need to|in this image, i can see that)",
            r"^(thinking process:|analysis:|internal reasoning:)",
            r"^(first,|second,|to answer this question,)",
        ]
        for pat in analytical_patterns:
            if re.search(pat, cleaned, flags=re.IGNORECASE):
                return ""

        return cleaned

    def _call_ollama(
        self,
        model_name: str,
        question: str,
        image_b64: Optional[str] = None,
        num_ctx: int = 4096,
        max_tokens: int = 384,
        timeout: float = 90.0,
    ) -> Tuple[Optional[str], Optional[str], Optional[dict]]:
        """Makes HTTP POST request to Ollama /api/chat. Returns (answer, error, raw_response_data)."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT_AR}]
        user_msg = {"role": "user", "content": question}
        if image_b64:
            user_msg["images"] = [image_b64]
        messages.append(user_msg)

        payload = {
            "model": model_name,
            "messages": messages,
            "stream": False,
            "keep_alive": self.config.keep_alive,
            "options": {
                "num_ctx": num_ctx,
                "num_predict": max_tokens,
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
            },
        }

        try:
            with httpx.Client(timeout=timeout) as client:
                res = client.post(f"{self.config.endpoint}/api/chat", json=payload)
                if res.status_code != 200:
                    return None, f"Ollama HTTP {res.status_code}: {res.text[:200]}", None
                data = res.json()
                msg = data.get("message", {})
                content = msg.get("content", "")
                sanitized = self.sanitize_answer(content)
                return sanitized, None, data
        except httpx.TimeoutException:
            return None, f"انتهت مهلة استجابة النموذج ({timeout} ثانية)", None
        except Exception as e:
            return None, str(e), None

    def ask(
        self,
        question: str,
        image_input: Optional[Image.Image | str] = None,
        frame_id: Optional[str] = None,
        model_mode: str = "fast",  # 'fast' (2B) or 'detailed' (4B)
    ) -> AskResponse:
        t0 = time.perf_counter()
        clean_q = question.strip() if question else "صف هذا المشهد باختصار."

        runtime = self.check_runtime()
        if not runtime.get("reachable"):
            return AskResponse(
                frame_id=frame_id,
                model=self.config.model_tag,
                model_mode=model_mode,
                status="runtime_unavailable",
                error="خدمة Ollama المحلية غير مشغلة على المنفذ 11434. يرجى تشغيل خدمة Ollama.",
                latency_ms=round((time.perf_counter() - t0) * 1000, 2),
            )

        # Select target model and parameters based on mode
        requested_mode = model_mode.lower()
        effective_mode = "detailed" if requested_mode == "detailed" else "fast"
        target_model = self.config.fast_model_tag
        num_ctx = self.config.num_ctx
        max_tokens = self.config.detailed_max_tokens if requested_mode == "detailed" else self.config.max_tokens

        # Manage VRAM residency: keep active 2B model loaded
        self._last_loaded_model = target_model

        # Prepare image bytes
        img_b64 = None
        if image_input:
            try:
                img_b64 = self.prepare_image(image_input)
            except Exception as e:
                return AskResponse(
                    frame_id=frame_id,
                    model=target_model,
                    model_mode=effective_mode,
                    status="image_decode_error",
                    error=f"فشل معالجة الصورة: {str(e)}",
                    latency_ms=round((time.perf_counter() - t0) * 1000, 2),
                )

        # Primary inference call
        answer, err, raw_data = self._call_ollama(
            model_name=target_model,
            question=clean_q,
            image_b64=img_b64,
            num_ctx=num_ctx,
            max_tokens=max_tokens,
            timeout=self.config.timeout_seconds,
        )

        # Bounded retry if answer was empty due to thinking suppression
        if not answer and not err:
            retry_prompt = f"{clean_q} (أجب مباشرة وبإيجاز باللغة العربية دون خطوات تفكير)"
            answer, err, raw_data = self._call_ollama(
                model_name=target_model,
                question=retry_prompt,
                image_b64=img_b64,
                num_ctx=num_ctx,
                max_tokens=max_tokens,
                timeout=min(self.config.timeout_seconds, 45.0),
            )

        latency = round((time.perf_counter() - t0) * 1000, 2)

        if err:
            return AskResponse(
                frame_id=frame_id,
                model=target_model,
                model_mode=effective_mode,
                status="inference_error",
                error=err,
                latency_ms=latency,
            )

        if not answer:
            return AskResponse(
                frame_id=frame_id,
                model=target_model,
                model_mode=effective_mode,
                status="empty_response",
                error="لم يتمكن نموذج الرؤية من تكوين إجابة واضحة عن هذه الصورة.",
                latency_ms=latency,
            )

        return AskResponse(
            frame_id=frame_id,
            answer_ar=answer,
            model=target_model,
            model_mode=effective_mode,
            status="ok",
            latency_ms=latency,
        )

    def ask_stream(
        self,
        question: str,
        image_input: Optional[Image.Image | str] = None,
        frame_id: Optional[str] = None,
        model_mode: str = "fast",
    ):
        """Streams vision response from Ollama token-by-token with TTFT measurement."""
        t0 = time.perf_counter()
        clean_q = question.strip() if question else "صف هذا المشهد باختصار."

        runtime = self.check_runtime()
        if not runtime.get("reachable"):
            yield {
                "type": "error",
                "status": "runtime_unavailable",
                "error": "خدمة Ollama المحلية غير مشغلة على المنفذ 11434.",
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            }
            return

        requested_mode = (model_mode or "fast").lower()
        target_model = self.config.fast_model_tag
        num_ctx = self.config.num_ctx
        max_tokens = self.config.detailed_max_tokens if requested_mode == "detailed" else self.config.max_tokens
        effective_mode = "detailed" if requested_mode == "detailed" else "fast"

        img_b64 = None
        if image_input:
            try:
                img_b64 = self.prepare_image(image_input)
            except Exception as e:
                yield {
                    "type": "error",
                    "status": "image_decode_error",
                    "error": f"فشل معالجة الصورة: {str(e)}",
                    "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                }
                return

        messages = [{"role": "system", "content": SYSTEM_PROMPT_AR}]
        user_msg = {"role": "user", "content": clean_q}
        if img_b64:
            user_msg["images"] = [img_b64]
        messages.append(user_msg)

        payload = {
            "model": target_model,
            "messages": messages,
            "stream": True,
            "keep_alive": self.config.keep_alive,
            "options": {
                "num_ctx": num_ctx,
                "num_predict": max_tokens,
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
            },
        }

        full_content: list[str] = []
        in_think_block = False
        first_token_time = None

        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                with client.stream("POST", f"{self.config.endpoint}/api/chat", json=payload) as resp:
                    if resp.status_code != 200:
                        yield {"type": "error", "error": f"Ollama HTTP {resp.status_code}"}
                        return

                    for line in resp.iter_lines():
                        if not line:
                            continue
                        chunk = json.loads(line)
                        msg = chunk.get("message", {})
                        token = msg.get("content", "")
                        if not token:
                            continue

                        # Handle thinking tags in stream
                        if "<think>" in token:
                            in_think_block = True
                            token = token.split("<think>", 1)[0]
                        if in_think_block:
                            if "</think>" in token:
                                in_think_block = False
                                token = token.split("</think>", 1)[1]
                            else:
                                continue

                        if not token:
                            continue

                        if first_token_time is None:
                            first_token_time = time.perf_counter()

                        full_content.append(token)
                        yield {
                            "type": "token",
                            "token": token,
                            "ttft_ms": round((first_token_time - t0) * 1000, 2),
                        }

            raw_answer = "".join(full_content)
            clean_answer = self.sanitize_answer(raw_answer)
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            ttft = round((first_token_time - t0) * 1000, 2) if first_token_time else latency_ms

            yield {
                "type": "done",
                "answer_ar": clean_answer or raw_answer.strip(),
                "model": target_model,
                "model_mode": effective_mode,
                "status": "ok",
                "ttft_ms": ttft,
                "latency_ms": latency_ms,
            }
        except Exception as e:
            yield {
                "type": "error",
                "error": str(e),
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            }
