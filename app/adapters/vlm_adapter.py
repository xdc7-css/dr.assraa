"""VLM Adapter for Qwen3-VL 2B Instruct variant via local Ollama REST API (/api/chat)."""
from __future__ import annotations

import base64
import io
import re
import time
from pathlib import Path
from typing import Optional
from PIL import Image
import httpx

from app.config import VLMConfig
from app.schemas import AskResponse

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

    def check_runtime(self) -> dict:
        """Check if Ollama service is reachable and if target model or previous model is available."""
        url = f"{self.config.endpoint}/api/tags"
        try:
            with httpx.Client(timeout=4.0) as client:
                res = client.get(url)
                if res.status_code == 200:
                    models = res.json().get("models", [])
                    installed = [m.get("name") for m in models]
                    # Check exact or prefix match
                    has_model = any(self.config.model_tag in (name or "") for name in installed)
                    # Also keep track if previous model is available
                    has_fallback = any("qwen3-vl:2b" in (name or "") for name in installed)
                    return {
                        "reachable": True,
                        "has_model": has_model,
                        "has_fallback": has_fallback,
                        "installed_models": installed,
                        "models_details": models,
                    }
        except Exception as e:
            return {"reachable": False, "has_model": False, "error": str(e)}
        return {"reachable": False, "has_model": False}

    def prepare_image(self, image_input: Image.Image | str) -> str:
        """Resize image to configured max edge for low-memory VLM and encode as base64 string without data prefix."""
        if isinstance(image_input, str):
            # Check if it is a file path
            if (image_input.endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp")) or "/" in image_input or "\\" in image_input) and Path(image_input).exists():
                img = Image.open(image_input).convert("RGB")
            else:
                if "," in image_input:
                    image_input = image_input.split(",", 1)[1]
                raw_bytes = base64.b64decode(image_input)
                img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        else:
            img = image_input.convert("RGB")

        # Resize preserving aspect ratio
        max_edge = self.config.image_max_edge
        w, h = img.size
        if max(w, h) > max_edge:
            if w >= h:
                new_w = max_edge
                new_h = max(1, int(h * (max_edge / w)))
            else:
                new_h = max_edge
                new_w = max(1, int(w * (max_edge / h)))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    @staticmethod
    def sanitize_answer(raw_text: str) -> str:
        """Strips thinking tags, internal reasoning, and leaked meta-analysis."""
        if not raw_text:
            return ""

        # 1. Remove XML/think blocks if present in content
        cleaned = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL)
        cleaned = re.sub(r"<reasoning>.*?</reasoning>", "", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"\[thinking\].*?\[/thinking\]", "", cleaned, flags=re.DOTALL | re.IGNORECASE)

        # 2. Strip leading / trailing whitespace
        cleaned = cleaned.strip()

        # 3. Detect and reject English analytical / chain-of-thought leaked narration
        # Examples: "Wait, the user provided...", "Looking at the image, I should...", "Thinking Process:"
        analytical_patterns = [
            r"^(wait[\s,]|let me see|looking at the image|the user is asking|i need to|in this image, i can see that)",
            r"^(thinking process:|analysis:|internal reasoning:)",
            r"^(first,|second,|to answer this question,)",
        ]
        for pat in analytical_patterns:
            if re.search(pat, cleaned, flags=re.IGNORECASE):
                # Leaked analytical monologue detected - reject
                return ""

        return cleaned

    def _call_ollama(
        self,
        model_name: str,
        question: str,
        image_b64: Optional[str] = None,
        timeout: float = 90.0,
    ) -> tuple[Optional[str], Optional[str]]:
        """Makes direct HTTP POST request to Ollama /api/chat. Returns (answer, error)."""
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
                "num_ctx": self.config.num_ctx,
                "num_predict": self.config.max_tokens,
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
            },
        }

        try:
            with httpx.Client(timeout=timeout) as client:
                res = client.post(f"{self.config.endpoint}/api/chat", json=payload)
                if res.status_code != 200:
                    return None, f"Ollama HTTP {res.status_code}: {res.text[:200]}"
                data = res.json()
                msg = data.get("message", {})
                # Strictly extract message.content only; never use thinking/reasoning field!
                content = msg.get("content", "")
                sanitized = self.sanitize_answer(content)
                return sanitized, None
        except httpx.TimeoutException:
            return None, f"انتهت مهلة استجابة النموذج ({timeout} ثانية)"
        except Exception as e:
            return None, str(e)

    def ask(
        self,
        question: str,
        image_input: Optional[Image.Image | str] = None,
        frame_id: Optional[str] = None,
    ) -> AskResponse:
        t0 = time.perf_counter()
        clean_q = question.strip() if question else "صف هذا المشهد باختصار."

        runtime = self.check_runtime()
        if not runtime.get("reachable"):
            return AskResponse(
                frame_id=frame_id,
                model=self.config.model_tag,
                status="runtime_unavailable",
                error="خدمة Ollama المحلية غير مشغلة على المنفذ 11434. يرجى تشغيل خدمة Ollama.",
                latency_ms=round((time.perf_counter() - t0) * 1000, 2),
            )

        # Determine target model
        target_model = self.config.model_tag
        if not runtime.get("has_model"):
            if runtime.get("has_fallback"):
                target_model = "qwen3-vl:2b"
            else:
                return AskResponse(
                    frame_id=frame_id,
                    model=self.config.model_tag,
                    status="model_not_found",
                    error=f"نموذج الرؤية {self.config.model_tag} غير منزل في Ollama.",
                    latency_ms=round((time.perf_counter() - t0) * 1000, 2),
                )

        # Prepare image bytes
        img_b64 = None
        if image_input:
            try:
                img_b64 = self.prepare_image(image_input)
            except Exception as e:
                return AskResponse(
                    frame_id=frame_id,
                    model=target_model,
                    status="image_decode_error",
                    error=f"فشل معالجة الصورة: {str(e)}",
                    latency_ms=round((time.perf_counter() - t0) * 1000, 2),
                )

        # Attempt 1: Primary call
        answer, err = self._call_ollama(
            model_name=target_model,
            question=clean_q,
            image_b64=img_b64,
            timeout=self.config.timeout_seconds,
        )

        # Attempt 2: Bounded retry if answer was empty or suppressed due to leaked thinking
        if not answer and not err:
            retry_prompt = f"{clean_q} (أجب مباشرة وبإيجاز باللغة العربية دون خطوات تفكير)"
            answer, err = self._call_ollama(
                model_name=target_model,
                question=retry_prompt,
                image_b64=img_b64,
                timeout=min(self.config.timeout_seconds, 45.0),
            )

        latency = round((time.perf_counter() - t0) * 1000, 2)

        if err:
            return AskResponse(
                frame_id=frame_id,
                model=target_model,
                status="inference_error",
                error=err,
                latency_ms=latency,
            )

        if not answer:
            # Honest failure response: analysis or empty content is never returned as answer
            return AskResponse(
                frame_id=frame_id,
                model=target_model,
                status="empty_response",
                error="لم يتمكن نموذج الرؤية من تكوين إجابة واضحة عن هذه الصورة.",
                latency_ms=latency,
            )

        return AskResponse(
            frame_id=frame_id,
            answer_ar=answer,
            model=target_model,
            status="ok",
            latency_ms=latency,
        )
