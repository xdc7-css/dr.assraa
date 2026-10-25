"""Pydantic schemas and typed models for API and pipeline orchestration."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float

class DetectionItem(BaseModel):
    class_id: int
    class_name_en: str
    class_name_ar: str
    confidence: float
    bbox: BoundingBox
    center_x: float
    center_y: float
    position: Literal["left", "center", "right"]

class DetectRequest(BaseModel):
    image_base64: str
    frame_id: Optional[str] = None
    target_object_ar: Optional[str] = None
    confidence_threshold: Optional[float] = None

class DetectResponse(BaseModel):
    frame_id: Optional[str] = None
    detections: List[DetectionItem] = Field(default_factory=list)
    image_width: int = 0
    image_height: int = 0
    target_object_ar: Optional[str] = None
    target_found: bool = False
    target_position: Optional[str] = None
    summary_ar: str = ""
    latency_ms: float = 0.0
    status: str = "ok"
    error: Optional[str] = None

class OCRItem(BaseModel):
    text: str
    confidence: float
    bbox: List[List[float]]

class OCRRequest(BaseModel):
    image_base64: str
    frame_id: Optional[str] = None

class OCRResponse(BaseModel):
    frame_id: Optional[str] = None
    text_combined: str = ""
    raw_text: Optional[str] = None
    preprocessing_applied: bool = False
    items: List[OCRItem] = Field(default_factory=list)
    latency_ms: float = 0.0
    status: str = "ok"
    error: Optional[str] = None

class TranscribeRequest(BaseModel):
    audio_base64: str
    audio_format: str = "webm"  # 'webm' or 'wav'
    language: Optional[str] = "ar"

class TranscribeResponse(BaseModel):
    transcript: str = ""
    language: str = "ar"
    duration_s: float = 0.0
    latency_ms: float = 0.0
    status: str = "ok"
    error: Optional[str] = None

class SpeakRequest(BaseModel):
    text: str

class SpeakResponse(BaseModel):
    audio_base64: str
    sample_rate: int = 22050
    duration_s: float = 0.0
    latency_ms: float = 0.0
    status: str = "ok"
    error: Optional[str] = None

class AskRequest(BaseModel):
    question: str
    image_base64: Optional[str] = None
    frame_id: Optional[str] = None

class AskResponse(BaseModel):
    frame_id: Optional[str] = None
    answer_ar: str = ""
    model: str = "qwen3-vl:2b-instruct-q4_K_M"
    latency_ms: float = 0.0
    status: str = "ok"
    error: Optional[str] = None

class AssistRequest(BaseModel):
    query_text: Optional[str] = None
    audio_base64: Optional[str] = None
    audio_format: Optional[str] = "webm"
    image_base64: Optional[str] = None
    frame_id: Optional[str] = None
    mode: Optional[Literal["auto", "describe", "read", "find", "ask", "repeat"]] = "auto"
    target_object_ar: Optional[str] = None

class AssistResponse(BaseModel):
    request_id: str
    timestamp: str = ""
    frame_id: Optional[str] = None
    mode: str
    query_text: str = ""
    answer_ar: str = ""
    audio_base64: Optional[str] = None
    status: str = "ok"
    source_components: List[str] = Field(default_factory=list)
    stage_timings_ms: Dict[str, float] = Field(default_factory=dict)
    total_latency_ms: float = 0.0
    details: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

class ModelComponentStatus(BaseModel):
    installed: bool = False
    loaded: bool = False
    device: str = "cpu"
    version_or_digest: Optional[str] = None
    path: Optional[str] = None
    error: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    profile: str
    system_memory_mb: Dict[str, float]
    models: Dict[str, ModelComponentStatus]
