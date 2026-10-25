"""FastAPI Application entrypoint for Arabic Multimodal Assistive Vision."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
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
    SpeakRequest,
    SpeakResponse,
    TranscribeRequest,
    TranscribeResponse,
)
from scripts.check_system import get_system_memory

app = FastAPI(
    title="Arabic Multimodal Assistive Vision",
    description="Multimodal Intelligent Assistant for Blind and Visually Impaired Individuals",
    version="1.0.0",
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
        "vlm": ModelComponentStatus(
            installed=vlm_stat.get("reachable", False) and vlm_stat.get("has_model", False),
            loaded=orchestrator.vlm.config.keep_alive > 0,
            device="ollama_managed",
            version_or_digest=manifest.get("vlm", {}).get("revision_or_digest", "qwen3-vl:2b"),
            path=config.vlm.endpoint,
            error=vlm_stat.get("error"),
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
            device=config.asr.device,
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
        models=models_status,
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
    )

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
    )

@app.post("/api/speak", response_model=SpeakResponse)
def synthesize_speech(req: SpeakRequest):
    return orchestrator.tts.speak(req.text)

@app.post("/api/assist", response_model=AssistResponse)
def assist_user(req: AssistRequest):
    return orchestrator.execute_assist(req)

@app.post("/api/cancel")
def cancel_pending(req: dict):
    req_id = req.get("request_id")
    if req_id:
        orchestrator.cancel_request(req_id)
        return {"status": "cancelled", "request_id": req_id}
    return {"status": "missing_request_id"}
