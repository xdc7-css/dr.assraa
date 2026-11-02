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
    canvas_size: int = 1280
    mag_ratio: float = 1.0
    batch_size: int = 4

class ASRConfig(BaseModel):
    model_id_or_path: str = "Systran/faster-whisper-base"
    download_root: Path = MODELS_DIR / "whisper"
    device: str = "cuda"
    compute_type: str = "float16"
    default_language: str = "ar"
    vad_filter: bool = True

class TTSConfig(BaseModel):
    onnx_path: Path = MODELS_DIR / "piper" / "ar_JO-kareem-medium.onnx"
    json_path: Path = MODELS_DIR / "piper" / "ar_JO-kareem-medium.onnx.json"
    device: str = "cpu"
    sentence_silence: float = 0.2
    length_scale: float = 1.05  # Base scale for normal speech pace
    # Optional Cloud Iraqi Voice Configuration (Disabled by default, zero paid requirement)
    azure_enabled: bool = False
    azure_region: str = os.environ.get("AZURE_SPEECH_REGION", "")
    azure_key: str = os.environ.get("AZURE_SPEECH_KEY", "")
    azure_voice: str = os.environ.get("AZURE_SPEECH_VOICE", "ar-IQ-BasselNeural")

class VLMConfig(BaseModel):
    endpoint: str = "http://127.0.0.1:11434"
    fast_model_tag: str = "qwen3-vl:2b-instruct-q4_K_M"
    detailed_model_tag: str = "qwen3-vl:4b-instruct-q4_K_M"
    model_tag: str = "qwen3-vl:2b-instruct-q4_K_M"  # Default active tag
    active_mode: str = "fast"  # 'fast' (2B) or 'detailed' (4B)
    timeout_seconds: float = 180.0
    num_ctx: int = 2048
    max_tokens: int = 256
    detailed_num_ctx: int = 2048  # Unified context to prevent model re-init
    detailed_max_tokens: int = 256
    keep_alive: int = 600  # 10 minutes warm residency in VRAM
    image_max_edge: int = 512
    temperature: float = 0.2
    top_p: float = 0.8

class QualityConfig(BaseModel):
    min_brightness: float = 30.0
    max_brightness: float = 235.0
    min_blur_var: float = 35.0
    cooldown_seconds: float = 8.0
    max_frame_age_s: float = 5.0

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
    quality: QualityConfig = Field(default_factory=QualityConfig)
    search_session_max_duration: float = 45.0
    context_ttl_seconds: float = 300.0  # 5 minutes conversational context memory

    def apply_profile(self, profile: str):
        self.profile = profile.lower()
        if self.profile == "low_memory":
            self.vlm.keep_alive = 600
            self.vlm.num_ctx = 2048
            self.vlm.detailed_num_ctx = 2048
            self.vlm.image_max_edge = 512
            self.vlm.max_tokens = 256
            self.asr.device = "cuda"
            self.asr.compute_type = "float16"
            self.ocr.gpu = False
            self.detection.device = "cpu"
        elif self.profile == "balanced":
            self.vlm.keep_alive = 600
            self.vlm.num_ctx = 2048
            self.vlm.detailed_num_ctx = 2048
            self.vlm.image_max_edge = 512
            self.vlm.max_tokens = 256
            self.asr.device = "cuda"
            self.asr.compute_type = "float16"

def get_config() -> AppConfig:
    profile = os.environ.get("AMAV_PROFILE", "low_memory")
    cfg = AppConfig()
    cfg.apply_profile(profile)
    return cfg

