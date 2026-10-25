"""TTS Adapter using Piper (ar_JO-kareem-medium ONNX) with pace adjustment and optional Azure Iraqi voice."""
from __future__ import annotations

import base64
import io
import json
import re
import time
import wave
from pathlib import Path
from typing import Optional

from app.config import TTSConfig
from app.schemas import SpeakResponse
from app.adapters.azure_speech_adapter import AzureSpeechAdapter

# Curated pronunciation dictionary for recurring interface phrases
# Prevents mispronunciation of technical abbreviations and interface keywords
PRONUNCIATION_MAP = {
    "AMAV": "أَمَاف",
    "YOLO": "يُولُو",
    "EasyOCR": "إِيزِي أُو سِي آر",
    "VLM": "فِي إِل إِم",
    "ASR": "إِيه إِس آر",
    "TTS": "تِي تِي إِس",
    "مساعدك البصري": "مُسَاعِدُكَ البَصَرِيّ",
    "المشهد": "المَشْهَد",
    "القنينة": "القَنِينَة",
    "اللابتوب": "اللَّابْتُوب",
    "الحاسوب": "الحَاسُوب",
    "الكاميرا": "الكَّامِيرَا",
}

class TTSAdapter:
    def __init__(self, config: Optional[TTSConfig] = None):
        self.config = config or TTSConfig()
        self.voice = None
        self._loaded = False
        self._load_error: Optional[str] = None
        self._sample_rate: int = 22050
        self.azure_adapter = AzureSpeechAdapter(self.config)

    def load_model(self) -> bool:
        if self._loaded and self.voice is not None:
            return True

        onnx_path = Path(self.config.onnx_path)
        json_path = Path(self.config.json_path)

        if not onnx_path.exists():
            self._load_error = f"Piper voice ONNX model not found at {onnx_path}"
            return False
        if not json_path.exists():
            self._load_error = f"Piper voice JSON config not found at {json_path}"
            return False

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                voice_cfg = json.load(f)
                self._sample_rate = voice_cfg.get("audio", {}).get("sample_rate", 22050)
        except Exception:
            self._sample_rate = 22050

        try:
            from piper.voice import PiperVoice
            self.voice = PiperVoice.load(str(onnx_path), config_path=str(json_path))
            self._loaded = True
            self._load_error = None
            return True
        except Exception as e:
            self._load_error = f"Failed to load piper voice: {str(e)}"
            return False

    def is_ready(self) -> bool:
        return self._loaded and self.voice is not None

    @staticmethod
    def prepare_arabic_text(text: str) -> str:
        """Applies pronunciation dictionary and natural punctuation pauses."""
        cleaned = text.strip()
        if not cleaned:
            return ""

        # Apply dictionary replacements
        for term, phonetic in PRONUNCIATION_MAP.items():
            cleaned = re.sub(rf"\b{re.escape(term)}\b", phonetic, cleaned)

        # Ensure sentence ends with punctuation for natural Piper pause cadence
        if not cleaned.endswith((".", "!", "؟", "?", ":")):
            cleaned += "."

        return cleaned

    def speak(
        self,
        text: str,
        length_scale: Optional[float] = None,
        use_cloud: Optional[bool] = None,
    ) -> SpeakResponse:
        t0 = time.perf_counter()
        clean_text = self.prepare_arabic_text(text)
        if not clean_text:
            return SpeakResponse(
                audio_base64="",
                sample_rate=self._sample_rate,
                duration_s=0.0,
                status="empty_text",
                latency_ms=0.0,
            )

        # Check if optional Azure cloud synthesis is explicitly enabled
        allow_cloud = use_cloud if use_cloud is not None else self.config.azure_enabled
        if allow_cloud and self.azure_adapter.is_configured:
            cloud_res = self.azure_adapter.speak(clean_text)
            if cloud_res.status == "ok":
                return cloud_res

        # Offline Piper Path (Default, dependable local engine)
        if not self.is_ready():
            ok = self.load_model()
            if not ok:
                return SpeakResponse(
                    audio_base64="",
                    sample_rate=self._sample_rate,
                    duration_s=0.0,
                    status="model_not_ready",
                    error=self._load_error or "Piper voice model not loaded",
                    latency_ms=round((time.perf_counter() - t0) * 1000, 2),
                )

        effective_pace = length_scale or self.config.length_scale

        try:
            from piper.config import SynthesisConfig
            syn_config = SynthesisConfig(
                length_scale=effective_pace,
                volume=1.0,
                normalize_audio=True,
            )
        except Exception:
            syn_config = None

        try:
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wav_file:
                if syn_config is not None:
                    self.voice.synthesize_wav(clean_text, wav_file, syn_config=syn_config, set_wav_format=True)
                else:
                    self.voice.synthesize_wav(clean_text, wav_file, set_wav_format=True)

            wav_bytes = wav_buffer.getvalue()
            if not wav_bytes or len(wav_bytes) < 44:
                return SpeakResponse(
                    audio_base64="",
                    sample_rate=self._sample_rate,
                    duration_s=0.0,
                    status="synthesis_empty",
                    error="Synthesizer produced empty audio stream",
                    latency_ms=round((time.perf_counter() - t0) * 1000, 2),
                )

            with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                duration = round(frames / float(rate), 2) if rate > 0 else 0.0

            audio_b64 = base64.b64encode(wav_bytes).decode("utf-8")
            latency = round((time.perf_counter() - t0) * 1000, 2)

            return SpeakResponse(
                audio_base64=audio_b64,
                sample_rate=self._sample_rate,
                duration_s=duration,
                status="ok",
                latency_ms=latency,
            )
        except Exception as e:
            return SpeakResponse(
                audio_base64="",
                sample_rate=self._sample_rate,
                duration_s=0.0,
                status="synthesis_error",
                error=f"Piper synthesis error: {str(e)}",
                latency_ms=round((time.perf_counter() - t0) * 1000, 2),
            )
