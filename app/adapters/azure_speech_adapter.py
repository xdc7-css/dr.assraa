"""Azure Cognitive Speech TTS Adapter with official Iraqi Arabic voices (ar-IQ).
Disabled by default; requires zero paid credentials to run the application offline.
"""
from __future__ import annotations

import base64
import time
from typing import Optional
import httpx

from app.config import TTSConfig
from app.schemas import SpeakResponse

# Official Iraqi Neural Voices per Microsoft Azure Speech Reference
# https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=tts
AZURE_IRAQI_VOICES = {
    "bassel": "ar-IQ-BasselNeural",  # Male Iraqi voice
    "rana": "ar-IQ-RanaNeural",      # Female Iraqi voice
}

class AzureSpeechAdapter:
    def __init__(self, config: Optional[TTSConfig] = None):
        self.config = config or TTSConfig()

    @property
    def is_configured(self) -> bool:
        """Returns True only if Azure is explicitly enabled and credentials are provided."""
        return (
            bool(self.config.azure_enabled)
            and bool(self.config.azure_key)
            and bool(self.config.azure_region)
        )

    def speak(self, text: str, voice_name: Optional[str] = None) -> SpeakResponse:
        t0 = time.perf_counter()
        clean_text = text.strip()
        if not clean_text:
            return SpeakResponse(
                audio_base64="",
                sample_rate=24000,
                duration_s=0.0,
                status="empty_text",
                latency_ms=0.0,
            )

        if not self.is_configured:
            return SpeakResponse(
                audio_base64="",
                sample_rate=24000,
                duration_s=0.0,
                status="azure_not_configured",
                error="خدمة Azure Speech غير مفعلة أو لم يتم إدخال مفتاح الخدمة والمنطقة (الوضع الافتراضي غير المتصل يعمل عبر Piper).",
                latency_ms=0.0,
            )

        selected_voice = voice_name or self.config.azure_voice or AZURE_IRAQI_VOICES["bassel"]
        region = self.config.azure_region
        url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"

        # SSML payload for Iraqi neural voice
        ssml = (
            f"<speak version='1.0' xml:lang='ar-IQ'>"
            f"<voice name='{selected_voice}'>"
            f"<prosody rate='{self.config.length_scale:.2f}'>"
            f"{clean_text}"
            f"</prosody>"
            f"</voice>"
            f"</speak>"
        )

        headers = {
            "Ocp-Apim-Subscription-Key": self.config.azure_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm",
            "User-Agent": "AMAV-Assistive-Vision/1.0",
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, headers=headers, content=ssml.encode("utf-8"))
                if res.status_code == 200:
                    wav_bytes = res.content
                    audio_b64 = base64.b64encode(wav_bytes).decode("utf-8")
                    duration_s = max(0.5, len(wav_bytes) / (24000 * 2))
                    latency = round((time.perf_counter() - t0) * 1000, 2)
                    return SpeakResponse(
                        audio_base64=audio_b64,
                        sample_rate=24000,
                        duration_s=round(duration_s, 2),
                        status="ok",
                        latency_ms=latency,
                    )
                else:
                    return SpeakResponse(
                        audio_base64="",
                        sample_rate=24000,
                        duration_s=0.0,
                        status="azure_error",
                        error=f"Azure Speech returned HTTP {res.status_code}: {res.text[:150]}",
                        latency_ms=round((time.perf_counter() - t0) * 1000, 2),
                    )
        except Exception as e:
            return SpeakResponse(
                audio_base64="",
                sample_rate=24000,
                duration_s=0.0,
                status="request_error",
                error=f"فشل الاتصال بـ Azure Speech: {str(e)}",
                latency_ms=round((time.perf_counter() - t0) * 1000, 2),
            )
