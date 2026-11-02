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
    mirrored: Optional[bool] = False

class DetectResponse(BaseModel):
    frame_id: Optional[str] = None
    detections: List[DetectionItem] = Field(default_factory=list)
    image_width: int = 0
    image_height: int = 0
    target_object_ar: Optional[str] = None
    target_found: bool = False
    target_position: Optional[str] = None
    target_direction_ar: Optional[str] = None
    instance_count: int = 0
    summary_ar: str = ""
    latency_ms: float = 0.0
    status: str = "ok"
    error: Optional[str] = None

class SearchSessionState(BaseModel):
    session_id: str
    target_query_ar: str
    target_class_en: Optional[str] = None
    status: Literal["active", "tracking", "lost", "stopped", "timeout"] = "active"
    direction_relative: Optional[Literal["left", "center", "right"]] = None
    direction_text_ar: str = ""
    instance_count: int = 0
    stable_lost_count: int = 0
    should_announce: bool = False
    announcement_text_ar: Optional[str] = None
    elapsed_seconds: float = 0.0
    max_duration_seconds: float = 45.0

class SearchSessionRequest(BaseModel):
    action: Literal["start", "update", "stop"]
    target_object_ar: Optional[str] = None
    session_id: Optional[str] = None
    image_base64: Optional[str] = None
    mirrored: Optional[bool] = False

class OCRItem(BaseModel):
    text: str
    confidence: float
    bbox: List[List[float]]

class OCRRequest(BaseModel):
    image_base64: str
    frame_id: Optional[str] = None
    force_override: Optional[bool] = False

class OCRResponse(BaseModel):
    frame_id: Optional[str] = None
    text_combined: str = ""
    raw_text: Optional[str] = None
    preprocessing_applied: bool = False
    items: List[OCRItem] = Field(default_factory=list)
    guidance: Optional[Dict[str, Any]] = None
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
    speech_speed: Optional[float] = 1.0  # 0.75, 1.0, 1.25, 1.5

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
    model_mode: Optional[Literal["fast", "detailed"]] = "fast"
    override_quality: Optional[bool] = False

class AskResponse(BaseModel):
    frame_id: Optional[str] = None
    answer_ar: str = ""
    model: str = "qwen3-vl:2b-instruct-q4_K_M"
    model_mode: str = "fast"
    latency_ms: float = 0.0
    status: str = "ok"
    error: Optional[str] = None

class AssistRequest(BaseModel):
    query_text: Optional[str] = None
    audio_base64: Optional[str] = None
    audio_format: Optional[str] = "webm"
    image_base64: Optional[str] = None
    frame_id: Optional[str] = None
    frame_timestamp_ms: Optional[float] = None
    mode: Optional[Literal["auto", "describe", "read", "find", "ask", "repeat", "shorten", "reset", "search_session"]] = "auto"
    target_object_ar: Optional[str] = None
    model_mode: Optional[Literal["fast", "detailed"]] = "fast"
    override_quality: Optional[bool] = False
    mirrored: Optional[bool] = False
    speech_speed: Optional[float] = 1.0
    search_session_id: Optional[str] = None
    search_action: Optional[Literal["start", "update", "stop"]] = None

class AssistResponse(BaseModel):
    request_id: str
    timestamp: str = ""
    frame_id: Optional[str] = None
    mode: str
    model_mode: str = "fast"
    query_text: str = ""
    answer_ar: str = ""
    audio_base64: Optional[str] = None
    status: str = "ok"
    source_components: List[str] = Field(default_factory=list)
    stage_timings_ms: Dict[str, float] = Field(default_factory=dict)
    total_latency_ms: float = 0.0
    search_session: Optional[SearchSessionState] = None
    frame_quality: Optional[Dict[str, Any]] = None
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
    gpu_memory_mb: Optional[Dict[str, float]] = None
    models: Dict[str, ModelComponentStatus]
    vlm_modes: Dict[str, Any] = Field(default_factory=dict)
    context_memory: Dict[str, Any] = Field(default_factory=dict)
