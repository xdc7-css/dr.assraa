"""FastAPI Application entrypoint for Arabic Multimodal Assistive Vision."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

# Prevent CPU thread saturation & lockup across PyTorch and OpenMP
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"
try:
    import torch
    torch.set_num_threads(4)
    torch.set_num_interop_threads(2)
except Exception:
    pass

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.config import PROJECT_ROOT, get_config
from app.orchestrator import Orchestrator
from app.schemas import (
    AskRequest,
    AskResponse,
    AssistRequest,
    AssistResponse,
    DetectRequest,
    DetectResponse,
    HealthResponse,
    ModelComponentStatus,
    OCRRequest,
    OCRResponse,
    SearchSessionRequest,
    SearchSessionState,
    SpeakRequest,
    SpeakResponse,
    TranscribeRequest,
    TranscribeResponse,
)
from scripts.check_system import get_system_memory

app = FastAPI(
    title="Arabic Multimodal Assistive Vision",
    description="Multimodal Intelligent Assistant for Blind and Visually Impaired Individuals",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize single orchestrator instance
orchestrator = Orchestrator()

# Mount static web directory and audio samples
STATIC_DIR = PROJECT_ROOT / "app" / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

AUDIO_DIR = PROJECT_ROOT / "data" / "audio_samples"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/data/audio_samples", StaticFiles(directory=str(AUDIO_DIR)), name="audio_samples")

@app.get("/")
def read_root():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse({"status": "running", "message": "Arabic Multimodal Assistive Vision API"})

@app.get("/api/health", response_model=HealthResponse)
def get_health():
    mem = get_system_memory()
    gpu_snap = orchestrator.vlm.get_memory_snapshot()
    config = orchestrator.config

    # Probe models status safely
    vlm_stat = orchestrator.vlm.check_runtime()
    manifest_path = PROJECT_ROOT / "models_manifest.json"
    manifest = {}
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f).get("models", {})
        except Exception:
            pass

    models_status = {
        "vlm_2b": ModelComponentStatus(
            installed=vlm_stat.get("has_fast", False) or vlm_stat.get("has_model", False),
            loaded=orchestrator.vlm.config.keep_alive > 0,
            device="gpu (GTX 1650 Ti / Ollama)",
            version_or_digest=manifest.get("vlm", {}).get("revision_or_digest", "qwen3-vl:2b-instruct-q4_K_M"),
            path=config.vlm.endpoint,
            error=vlm_stat.get("error"),
        ),
        "vlm_4b": ModelComponentStatus(
            installed=vlm_stat.get("has_detailed", False),
            loaded=False,
            device="gpu_offload_managed",
            version_or_digest="qwen3-vl:4b-instruct-q4_K_M",
            path=config.vlm.endpoint,
            error=None if vlm_stat.get("has_detailed") else "Model 4B not yet fully downloaded or loaded",
        ),
        "detection": ModelComponentStatus(
            installed=config.detection.model_path.exists(),
            loaded=orchestrator.detection.is_ready(),
            device=config.detection.device,
            path=str(config.detection.model_path),
            error=orchestrator.detection._load_error,
        ),
        "ocr": ModelComponentStatus(
            installed=config.ocr.model_dir.exists(),
            loaded=orchestrator.ocr.is_ready(),
            device="cpu",
            path=str(config.ocr.model_dir),
            error=orchestrator.ocr._load_error,
        ),
        "asr": ModelComponentStatus(
            installed=config.asr.download_root.exists(),
            loaded=orchestrator.asr.is_ready(),
            device=getattr(orchestrator.asr, "effective_device", config.asr.device),
            path=str(config.asr.download_root),
            error=orchestrator.asr._load_error,
        ),
        "tts": ModelComponentStatus(
            installed=config.tts.onnx_path.exists(),
            loaded=orchestrator.tts.is_ready(),
            device=config.tts.device,
            path=str(config.tts.onnx_path),
            error=orchestrator.tts._load_error,
        ),
    }

    return HealthResponse(
        status="ok",
        profile=config.profile,
        system_memory_mb=mem,
        gpu_memory_mb=gpu_snap,
        models=models_status,
        vlm_modes={
            "fast_model": config.vlm.fast_model_tag,
            "detailed_model": config.vlm.detailed_model_tag,
            "detailed_ready": vlm_stat.get("has_detailed", False),
            "fast_ready": vlm_stat.get("has_fast", False) or vlm_stat.get("has_model", False),
            "current_mode": config.vlm.active_mode,
        },
        context_memory={
            "turn_count": orchestrator.context.turn_count,
            "last_command": orchestrator.context.last_user_command,
            "last_referenced_object": orchestrator.context.last_referenced_object,
            "is_stale": orchestrator.context.is_stale(),
            "active_search_session": orchestrator.context.active_search_session_id,
        },
    )

@app.get("/api/models")
def get_models_manifest():
    manifest_path = PROJECT_ROOT / "models_manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="models_manifest.json not found")
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.post("/api/transcribe", response_model=TranscribeResponse)
def transcribe_audio(req: TranscribeRequest):
    return orchestrator.asr.transcribe(
        audio_base64=req.audio_base64,
        audio_format=req.audio_format,
        language=req.language,
    )

@app.post("/api/detect", response_model=DetectResponse)
def detect_objects(req: DetectRequest):
    return orchestrator.detection.detect(
        image_input=req.image_base64,
        target_object_ar=req.target_object_ar,
        frame_id=req.frame_id,
        confidence_threshold=req.confidence_threshold,
        mirrored=bool(req.mirrored),
    )

@app.post("/api/search_session", response_model=SearchSessionState)
def handle_search_session(req: SearchSessionRequest):
    if req.action == "start":
        if not req.target_object_ar:
            raise HTTPException(status_code=400, detail="target_object_ar required to start search")
        return orchestrator.detection.start_search_session(req.target_object_ar)
    elif req.action == "update":
        if not req.session_id or not req.image_base64:
            raise HTTPException(status_code=400, detail="session_id and image_base64 required for update")
        return orchestrator.detection.step_search_session(
            session_id=req.session_id,
            image_input=req.image_base64,
            mirrored=bool(req.mirrored),
        )
    elif req.action == "stop":
        session_id = req.session_id or orchestrator.context.active_search_session_id or "default"
        return orchestrator.detection.stop_search_session(session_id)
    raise HTTPException(status_code=400, detail="Invalid action")

@app.post("/api/context/reset")
def reset_context():
    orchestrator.context.reset()
    orchestrator.quality_analyzer.reset_cooldowns()
    return {"status": "ok", "message": "تم مسح الذاكرة بنجاح."}

@app.post("/api/ocr", response_model=OCRResponse)
def perform_ocr(req: OCRRequest):
    return orchestrator.ocr.recognize(
        image_input=req.image_base64,
        frame_id=req.frame_id,
    )

@app.post("/api/ask", response_model=AskResponse)
def ask_vlm(req: AskRequest):
    return orchestrator.vlm.ask(
        question=req.question,
        image_input=req.image_base64,
        frame_id=req.frame_id,
        model_mode=req.model_mode or "fast",
    )

@app.post("/api/speak", response_model=SpeakResponse)
def synthesize_speech(req: SpeakRequest):
    speed = req.speech_speed or 1.0
    effective_length_scale = orchestrator.config.tts.length_scale / max(0.5, speed)
    return orchestrator.tts.speak(req.text, length_scale=effective_length_scale)

@app.on_event("startup")
def startup_warmup():
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        def _silent_winerror_handler(loop, context):
            exc = context.get("exception")
            if isinstance(exc, (ConnectionResetError, BrokenPipeError)) or "10054" in str(context.get("message", "")):
                return
            loop.default_exception_handler(context)
        loop.set_exception_handler(_silent_winerror_handler)
    except Exception:
        pass

    try:
        orchestrator.tts.load_model()
    except Exception:
        pass
    try:
        orchestrator.asr.load_model()
    except Exception:
        pass

@app.post("/api/assist", response_model=AssistResponse)
def assist_user(req: AssistRequest):
    return orchestrator.execute_assist(req)

@app.post("/api/assist/stream")
def assist_user_stream(req: AssistRequest):
    return StreamingResponse(
        orchestrator.execute_assist_stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@app.post("/api/cancel")
def cancel_pending(req: dict):
    req_id = req.get("request_id")
    if req_id:
        orchestrator.cancel_request(req_id)
        return {"status": "cancelled", "request_id": req_id}
    return {"status": "missing_request_id"}
