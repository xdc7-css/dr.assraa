"""Automatic Speech Recognition adapter using faster-whisper (multilingual base, CPU INT8)."""
from __future__ import annotations

import base64
import io
import os
import tempfile
import time
from pathlib import Path
from typing import Optional

from app.config import ASRConfig
from app.schemas import TranscribeResponse

class ASRAdapter:
    def __init__(self, config: Optional[ASRConfig] = None):
        self.config = config or ASRConfig()
        self.model = None
        self._loaded = False
        self._load_error: Optional[str] = None
        self.effective_device: str = "cpu"
        self.effective_compute_type: str = "int8"

    def _setup_cuda_env(self):
        """Discovers local bundled CUDA 12 runtime DLLs (e.g. from Ollama distribution) if available."""
        try:
            from app.config import PROJECT_ROOT
            cuda_dir = PROJECT_ROOT / "tools" / "Ollama" / "lib" / "ollama" / "cuda_v12"
            if cuda_dir.exists():
                cuda_str = str(cuda_dir)
                if hasattr(os, "add_dll_directory"):
                    try:
                        os.add_dll_directory(cuda_str)
                    except Exception:
                        pass
                if cuda_str not in os.environ.get("PATH", ""):
                    os.environ["PATH"] = f"{cuda_str};" + os.environ.get("PATH", "")
        except Exception:
            pass

    def load_model(self) -> bool:
        if self._loaded and self.model is not None:
            return True
        try:
            from faster_whisper import WhisperModel
            download_root = Path(self.config.download_root)
            download_root.mkdir(parents=True, exist_ok=True)

            self._setup_cuda_env()

            # Attempt GPU / CUDA acceleration if requested
            if self.config.device == "cuda":
                try:
                    self.model = WhisperModel(
                        model_size_or_path=self.config.model_id_or_path,
                        device="cuda",
                        compute_type=self.config.compute_type or "float16",
                        download_root=str(download_root),
                    )
                    self._loaded = True
                    self._load_error = None
                    self.effective_device = "cuda"
                    self.effective_compute_type = self.config.compute_type or "float16"
                    return True
                except Exception as cuda_err:
                    # Honest, graceful fallback to CPU
                    self._load_error = f"CUDA init failed ({cuda_err}), falling back to CPU."
                    self.model = WhisperModel(
                        model_size_or_path=self.config.model_id_or_path,
                        device="cpu",
                        compute_type="int8",
                        download_root=str(download_root),
                        cpu_threads=4,
                    )
                    self._loaded = True
                    self.effective_device = "cpu"
                    self.effective_compute_type = "int8"
                    return True
            else:
                self.model = WhisperModel(
                    model_size_or_path=self.config.model_id_or_path,
                    device="cpu",
                    compute_type="int8",
                    download_root=str(download_root),
                    cpu_threads=4,
                )
                self._loaded = True
                self._load_error = None
                self.effective_device = "cpu"
                self.effective_compute_type = "int8"
                return True
        except Exception as e:
            self._load_error = str(e)
            self._loaded = False
            return False

    def is_ready(self) -> bool:
        return self._loaded and self.model is not None

    def transcribe(
        self,
        audio_base64: str,
        audio_format: str = "webm",
        language: Optional[str] = "ar",
    ) -> TranscribeResponse:
        t0 = time.perf_counter()

        if not audio_base64:
            return TranscribeResponse(
                transcript="",
                language=language or "ar",
                duration_s=0.0,
                status="empty_audio",
                latency_ms=0.0,
                error="لم يتم إرسال أي تسجيل صوتي",
            )

        if not self.is_ready():
            ok = self.load_model()
            if not ok:
                return TranscribeResponse(
                    transcript="",
                    language=language or "ar",
                    status="model_not_ready",
                    error=self._load_error or "faster-whisper model not loaded",
                    latency_ms=round((time.perf_counter() - t0) * 1000, 2),
                )

        try:
            if "," in audio_base64:
                audio_base64 = audio_base64.split(",", 1)[1]
            audio_bytes = base64.b64decode(audio_base64)
            if len(audio_bytes) < 100:
                return TranscribeResponse(
                    transcript="",
                    language=language or "ar",
                    status="audio_too_short",
                    error="التسجيل الصوتي فارغ أو قصير جداً",
                    latency_ms=round((time.perf_counter() - t0) * 1000, 2),
                )
        except Exception as e:
            return TranscribeResponse(
                transcript="",
                language=language or "ar",
                status="decode_error",
                error=f"فشل فك تشفير الصوت: {str(e)}",
                latency_ms=round((time.perf_counter() - t0) * 1000, 2),
            )

        # Write to temporary file for PyAV / faster-whisper decoding
        suffix = f".{audio_format}" if audio_format in ("webm", "wav", "ogg", "mp3") else ".webm"
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        try:
            temp_file.write(audio_bytes)
            temp_file.flush()
            temp_file.close()

            lang_arg = language if language and language != "auto" else None
            # Explicitly use task="transcribe" so we do NOT accidentally translate Arabic into English
            segments, info = self.model.transcribe(
                temp_file.name,
                language=lang_arg,
                task="transcribe",
                vad_filter=self.config.vad_filter,
                beam_size=1,
            )

            # Consume the entire iterator to complete decoding and measure full latency
            transcript_parts = []
            for seg in segments:
                clean_seg = seg.text.strip()
                if clean_seg:
                    transcript_parts.append(clean_seg)

            full_transcript = " ".join(transcript_parts).strip()
            duration = round(getattr(info, "duration", 0.0), 2)
            detected_lang = getattr(info, "language", language or "ar")
            latency = round((time.perf_counter() - t0) * 1000, 2)

            return TranscribeResponse(
                transcript=full_transcript,
                language=detected_lang,
                duration_s=duration,
                status="ok",
                latency_ms=latency,
            )
        except Exception as e:
            return TranscribeResponse(
                transcript="",
                language=language or "ar",
                status="transcribe_error",
                error=f"خطأ أثناء تحويل الصوت إلى نص: {str(e)}",
                latency_ms=round((time.perf_counter() - t0) * 1000, 2),
            )
        finally:
            try:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
            except Exception:
                pass
