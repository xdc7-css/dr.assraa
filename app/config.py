"""Application configuration and hardware memory profile definitions."""
from __future__ import annotations

import os
from pathlib import Path
from pydantic import BaseModel, Field

# Base directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
DATA_DIR = PROJECT_ROOT / "data"

class DetectionConfig(BaseModel):
    model_name: str = "yolo11n.pt"
    model_path: Path = MODELS_DIR / "yolo11n.pt"
    confidence_threshold: float = 0.35
    device: str = "cpu"
    iou_threshold: float = 0.45
    input_size: int = 640

class OCRConfig(BaseModel):
    model_dir: Path = MODELS_DIR / "easyocr"
    languages: list[str] = Field(default_factory=lambda: ["ar", "en"])
    gpu: bool = False
    detail: int = 1
    min_confidence: float = 0.2

class ASRConfig(BaseModel):
    model_id_or_path: str = "Systran/faster-whisper-base"
    download_root: Path = MODELS_DIR / "whisper"
    device: str = "cpu"
    compute_type: str = "int8"
    default_language: str = "ar"
    vad_filter: bool = True

class TTSConfig(BaseModel):
    onnx_path: Path = MODELS_DIR / "piper" / "ar_JO-kareem-medium.onnx"
    json_path: Path = MODELS_DIR / "piper" / "ar_JO-kareem-medium.onnx.json"
    device: str = "cpu"
    sentence_silence: float = 0.2
    length_scale: float = 1.05  # Optimized pace for assistive clarity (1.0 - 1.15)
    # Optional Cloud Iraqi Voice Configuration (Disabled by default, zero paid requirement)
    azure_enabled: bool = False
    azure_region: str = os.environ.get("AZURE_SPEECH_REGION", "")
    azure_key: str = os.environ.get("AZURE_SPEECH_KEY", "")
    azure_voice: str = os.environ.get("AZURE_SPEECH_VOICE", "ar-IQ-BasselNeural")  # or ar-IQ-RanaNeural

class VLMConfig(BaseModel):
    endpoint: str = "http://127.0.0.1:11434"
    model_tag: str = "qwen3-vl:2b-instruct-q4_K_M"
    timeout_seconds: float = 90.0
    num_ctx: int = 4096
    max_tokens: int = 384
    keep_alive: int = 180  # Keeps model resident in VRAM for 3 minutes
    image_max_edge: int = 640
    temperature: float = 0.2
    top_p: float = 0.8

class AppConfig(BaseModel):
    app_name: str = "Arabic Multimodal Assistive Vision"
    host: str = "127.0.0.1"
    port: int = 8000
    profile: str = "low_memory"  # 'low_memory' or 'balanced'
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    ocr: OCRConfig = Field(default_factory=OCRConfig)
    asr: ASRConfig = Field(default_factory=ASRConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    vlm: VLMConfig = Field(default_factory=VLMConfig)

    def apply_profile(self, profile: str):
        self.profile = profile.lower()
        if self.profile == "low_memory":
            self.vlm.keep_alive = 120  # Keeps model loaded for 2m to avoid constant 30s re-loads
            self.vlm.image_max_edge = 640
            self.vlm.max_tokens = 512  # Sufficient for thinking + complete Arabic answer
            self.asr.compute_type = "int8"
            self.ocr.gpu = False
            self.detection.device = "cpu"
        elif self.profile == "balanced":
            self.vlm.keep_alive = 300  # keep resident for 5 minutes
            self.vlm.image_max_edge = 800
            self.vlm.max_tokens = 1024
            self.asr.compute_type = "default"
            # detection can remain CPU or GPU if verified

def get_config() -> AppConfig:
    profile = os.environ.get("AMAV_PROFILE", "low_memory")
    cfg = AppConfig()
    cfg.apply_profile(profile)
    return cfg
