"""Comprehensive smoke tests and verification probes for all AMAV model adapters."""
from __future__ import annotations

import argparse
import base64
import json
import time
import sys
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_config
from app.orchestrator import Orchestrator
from scripts.generate_fixtures import generate_arabic_text_fixture, generate_objects_fixture

def update_probe_status(component_key: str, status: str):
    manifest_path = PROJECT_ROOT / "models_manifest.json"
    if not manifest_path.exists():
        return
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        if component_key in manifest.get("models", {}):
            manifest["models"][component_key]["probe_status"] = status
            manifest["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%S+03:00")
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Failed to update probe status for {component_key}: {e}")

def probe_yolo(orchestrator: Orchestrator) -> bool:
    print("\n[PROBE 1/5] Testing YOLO11 Object Detector...")
    fixture_path = generate_objects_fixture()
    try:
        with open(fixture_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        res = orchestrator.detection.detect(img_b64)
        print(f"  Status: {res.status}")
        print(f"  Latency: {res.latency_ms} ms")
        print(f"  Detections count: {len(res.detections)}")
        print(f"  Summary: {res.summary_ar}")

        # Also test target query with Arabic alias "قنينة"
        res_find = orchestrator.detection.detect(img_b64, target_object_ar="قنينة")
        print(f"  Find 'قنينة' result: {res_find.summary_ar}")

        if res.status == "ok":
            update_probe_status("detection", "passed_real_inference")
            return True
        else:
            update_probe_status("detection", f"failed_{res.status}")
            return False
    except Exception as e:
        print(f"  [ERROR] YOLO probe failed: {e}")
        update_probe_status("detection", f"exception_{str(e)[:30]}")
        return False

def probe_ocr(orchestrator: Orchestrator) -> bool:
    print("\n[PROBE 2/5] Testing EasyOCR Arabic/English Recognition...")
    fixture_path = generate_arabic_text_fixture()
    try:
        with open(fixture_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        res = orchestrator.ocr.recognize(img_b64)
        print(f"  Status: {res.status}")
        print(f"  Latency: {res.latency_ms} ms")
        print(f"  Recognized items: {len(res.items)}")
        if res.text_combined:
            print(f"  Text Output:\n    {res.text_combined.replace(chr(10), ' | ')}")

        if res.status == "ok":
            update_probe_status("ocr", "passed_real_inference")
            return True
        else:
            update_probe_status("ocr", f"failed_{res.status}")
            return False
    except Exception as e:
        print(f"  [ERROR] OCR probe failed: {e}")
        update_probe_status("ocr", f"exception_{str(e)[:30]}")
        return False

def probe_tts(orchestrator: Orchestrator) -> tuple[bool, str]:
    print("\n[PROBE 3/5] Testing Piper Arabic TTS (ar_JO-kareem-medium)...")
    test_phrase = "مرحباً بك، المساعد البصري الذكي جاهز لمساعدتك."
    try:
        res = orchestrator.tts.speak(test_phrase)
        print(f"  Status: {res.status}")
        print(f"  Latency: {res.latency_ms} ms")
        print(f"  Audio duration: {res.duration_s} seconds")
        print(f"  Sample rate: {res.sample_rate} Hz")

        if res.status == "ok" and res.audio_base64:
            update_probe_status("tts", "passed_real_inference")
            # Save sample WAV to data/fixtures/tts_smoke.wav
            wav_bytes = base64.b64decode(res.audio_base64)
            out_wav = PROJECT_ROOT / "data" / "fixtures" / "tts_smoke.wav"
            out_wav.parent.mkdir(parents=True, exist_ok=True)
            with open(out_wav, "wb") as f:
                f.write(wav_bytes)
            print(f"  Saved generated sample audio to {out_wav.name} ({len(wav_bytes)} bytes)")
            return True, res.audio_base64
        else:
            update_probe_status("tts", f"failed_{res.status}")
            return False, ""
    except Exception as e:
        print(f"  [ERROR] TTS probe failed: {e}")
        update_probe_status("tts", f"exception_{str(e)[:30]}")
        return False, ""

def probe_asr(orchestrator: Orchestrator, audio_b64: str) -> bool:
    print("\n[PROBE 4/5] Testing faster-whisper Arabic ASR...")
    if not audio_b64:
        print("  [SKIP] No synthetic audio available from TTS to test ASR plumbing.")
        update_probe_status("asr", "pending_audio_sample")
        return False

    try:
        res = orchestrator.asr.transcribe(audio_b64, audio_format="wav", language="ar")
        print(f"  Status: {res.status}")
        print(f"  Latency: {res.latency_ms} ms")
        print(f"  Transcribed: '{res.transcript}'")
        print(f"  Detected language: {res.language}")

        if res.status == "ok":
            update_probe_status("asr", "passed_real_inference")
            return True
        else:
            update_probe_status("asr", f"failed_{res.status}")
            return False
    except Exception as e:
        print(f"  [ERROR] ASR probe failed: {e}")
        update_probe_status("asr", f"exception_{str(e)[:30]}")
        return False

def probe_vlm(orchestrator: Orchestrator) -> bool:
    model_tag = orchestrator.vlm.config.model_tag
    print(f"\n[PROBE 5/5] Testing Ollama VLM ({model_tag}) Visual Q&A...")
    runtime = orchestrator.vlm.check_runtime()
    print(f"  Ollama Reachable: {runtime.get('reachable')}")
    print(f"  Has {model_tag}: {runtime.get('has_model')}")

    if not runtime.get("reachable"):
        print("  [NOTE] Ollama local service is not running or not installed.")
        update_probe_status("vlm", "runtime_unavailable")
        return False

    if not runtime.get("has_model"):
        print(f"  [NOTE] Model {model_tag} is not pulled in Ollama.")
        update_probe_status("vlm", "model_not_pulled")
        return False

    fixture_path = generate_objects_fixture()
    try:
        with open(fixture_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        # Ask question 1
        q1 = "صف هذا المشهد باختصار."
        res1 = orchestrator.vlm.ask(q1, image_input=img_b64)
        print(f"  Q1: '{q1}' -> Status: {res1.status}, Latency: {res1.latency_ms} ms")
        print(f"  A1: {res1.answer_ar}")

        # Ask question 2 to verify distinct grounded answer
        q2 = "ما هي الألوان الموجودة في الصورة؟"
        res2 = orchestrator.vlm.ask(q2, image_input=img_b64)
        print(f"  Q2: '{q2}' -> Status: {res2.status}, Latency: {res2.latency_ms} ms")
        print(f"  A2: {res2.answer_ar}")

        if res1.status == "ok" and res2.status == "ok":
            update_probe_status("vlm", "passed_real_inference")
            return True
        else:
            update_probe_status("vlm", f"failed_{res1.status}")
            return False
    except Exception as e:
        print(f"  [ERROR] VLM probe failed: {e}")
        update_probe_status("vlm", f"exception_{str(e)[:30]}")
        return False

def main():
    print("=" * 65)
    print(" AMAV REAL MODEL SMOKE TEST & PROBE SUITE")
    print("=" * 65)

    orchestrator = Orchestrator()

    yolo_ok = probe_yolo(orchestrator)
    ocr_ok = probe_ocr(orchestrator)
    tts_ok, audio_b64 = probe_tts(orchestrator)
    asr_ok = probe_asr(orchestrator, audio_b64)
    vlm_ok = probe_vlm(orchestrator)

    print("\n" + "=" * 65)
    print(" SMOKE TEST SUMMARY")
    print("=" * 65)
    print(f"  YOLO11 Detection: {'PASSED' if yolo_ok else 'FAILED/UNTESTED'}")
    print(f"  EasyOCR Text Rec: {'PASSED' if ocr_ok else 'FAILED/UNTESTED'}")
    print(f"  Piper Arabic TTS: {'PASSED' if tts_ok else 'FAILED/UNTESTED'}")
    print(f"  Whisper ASR:      {'PASSED' if asr_ok else 'FAILED/UNTESTED'}")
    print(f"  Qwen3-VL 2B:      {'PASSED' if vlm_ok else 'UNAVAILABLE (Ollama required)'}")
    print("=" * 65)

if __name__ == "__main__":
    main()
