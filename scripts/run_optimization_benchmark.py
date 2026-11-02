"""AMAV Comprehensive TTFT & Latency Optimization Benchmark Script.
Measures Before vs After metrics across all components.
"""
from __future__ import annotations
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import time
import json
import base64
import urllib.request
from PIL import Image

from app.config import get_config
from app.adapters.vlm_adapter import VLMAdapter
from app.adapters.detection_adapter import DetectionAdapter
from app.adapters.ocr_adapter import OCRAdapter
from app.adapters.tts_adapter import TTSAdapter
from app.adapters.asr_adapter import ASRAdapter
from app.quality_analyzer import FrameQualityAnalyzer
from scripts.check_system import get_gpu_info, get_system_memory

def run_benchmark():
    cfg = get_config()
    print("=" * 60)
    print(" AMAV SYSTEM PERFORMANCE BENCHMARK (EMPIRICAL MEASUREMENTS)")
    print("=" * 60)

    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hardware": {},
        "components": {},
        "streaming_vs_blocking": {},
    }

    # 1. Hardware Snapshot
    mem = get_system_memory()
    gpus = get_gpu_info()
    gpu = gpus[0] if gpus else {}
    results["hardware"] = {
        "ram_total_mb": mem.get("total_ram_mb"),
        "ram_used_mb": mem.get("used_ram_mb"),
        "vram_total_mb": gpu.get("vram_total_mb"),
        "vram_used_mb": gpu.get("vram_used_mb"),
        "vram_free_mb": gpu.get("vram_free_mb"),
        "gpu_name": gpu.get("name"),
    }
    print(f"GPU: {gpu.get('name')} | VRAM Used: {gpu.get('vram_used_mb')}MB / {gpu.get('vram_total_mb')}MB")
    print(f"RAM Available: {mem.get('available_ram_mb')}MB / {mem.get('total_ram_mb')}MB")

    # 2. Quality Analyzer & Image Preprocessing
    qa = FrameQualityAnalyzer()
    with open(PROJECT_ROOT / "data/fixtures/kitchen_scene.jpg", "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    t0 = time.perf_counter()
    qa_res = qa.analyze(img_b64)
    qa_ms = (time.perf_counter() - t0) * 1000

    vlm = VLMAdapter(cfg.vlm)
    t0 = time.perf_counter()
    prep_b64 = vlm.prepare_image(img_b64)
    prep_ms = (time.perf_counter() - t0) * 1000

    results["components"]["quality_analyzer"] = {"latency_ms": round(qa_ms, 2)}
    results["components"]["image_preprocessing"] = {"latency_ms": round(prep_ms, 2)}
    print(f"Quality Analyzer: {qa_ms:.2f} ms")
    print(f"Image Preprocessing & Resize: {prep_ms:.2f} ms")

    # 3. YOLO11n Detection
    det = DetectionAdapter(cfg.detection)
    t0 = time.perf_counter()
    det_res = det.detect(img_b64)
    det_ms = (time.perf_counter() - t0) * 1000
    results["components"]["yolo11n"] = {"latency_ms": round(det_ms, 2)}
    print(f"YOLO11n Detection: {det_ms:.2f} ms")

    # 4. Piper TTS Single Sentence
    tts = TTSAdapter(cfg.tts)
    test_sent = "أرى في هذا المشهد مطبخاً مرتباً ومجهزاً بالكامل."
    t0 = time.perf_counter()
    tts_res = tts.speak(test_sent)
    tts_ms = (time.perf_counter() - t0) * 1000
    results["components"]["piper_tts_sentence"] = {"latency_ms": round(tts_ms, 2)}
    print(f"Piper TTS (Sentence ~8 words): {tts_ms:.2f} ms")

    # 5. EasyOCR
    ocr = OCRAdapter(cfg.ocr)
    t0 = time.perf_counter()
    ocr_res = ocr.recognize(img_b64)
    ocr_ms = (time.perf_counter() - t0) * 1000
    results["components"]["easyocr"] = {"latency_ms": round(ocr_ms, 2)}
    print(f"EasyOCR Text Recognition: {ocr_ms:.2f} ms")

    # 6. faster-whisper ASR
    asr = ASRAdapter(cfg.asr)
    sample_wav = PROJECT_ROOT / "data/audio_samples/kareem_speed_1.00.wav"
    if sample_wav.exists():
        with open(sample_wav, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode()
        t0 = time.perf_counter()
        asr_res = asr.transcribe(audio_b64, audio_format="wav")
        asr_ms = (time.perf_counter() - t0) * 1000
        results["components"]["faster_whisper"] = {"latency_ms": round(asr_ms, 2)}
        print(f"faster-whisper ASR: {asr_ms:.2f} ms")

    # 7. Streaming vs Blocking VLM Time-to-First-Response
    print("\n--- Live Server Comparison: Blocking vs Streaming ---")
    payload = {
        "query_text": "صف ما تراه في هذا المشهد.",
        "image_base64": img_b64,
        "model_mode": "fast",
    }
    payload_bytes = json.dumps(payload).encode("utf-8")

    # A) Blocking Endpoint (/api/assist)
    req_block = urllib.request.Request(
        "http://127.0.0.1:8000/api/assist",
        data=payload_bytes,
        headers={"Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req_block, timeout=60.0) as resp:
        block_data = json.loads(resp.read().decode("utf-8"))
    block_total_ms = (time.perf_counter() - t0) * 1000
    block_ttft_ms = block_total_ms  # In blocking mode, user sees 0 tokens until total completion!
    block_ttfa_ms = block_total_ms  # User hears 0 audio until total completion!

    results["streaming_vs_blocking"]["blocking"] = {
        "time_to_first_token_ms": round(block_ttft_ms, 2),
        "time_to_first_audio_ms": round(block_ttfa_ms, 2),
        "total_latency_ms": round(block_total_ms, 2),
        "answer_length_chars": len(block_data.get("answer_ar", "")),
    }
    print(f"Blocking (/api/assist):")
    print(f"  Time-To-First-Token (Visual): {block_ttft_ms:.1f} ms")
    print(f"  Time-To-First-Audio (Voice):  {block_ttfa_ms:.1f} ms")
    print(f"  Total Roundtrip Latency:      {block_total_ms:.1f} ms")

    # B) Streaming Endpoint (/api/assist/stream)
    req_stream = urllib.request.Request(
        "http://127.0.0.1:8000/api/assist/stream",
        data=payload_bytes,
        headers={"Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    stream_ttft_ms = None
    stream_ttfa_ms = None
    tokens_count = 0
    audio_chunks_count = 0

    with urllib.request.urlopen(req_stream, timeout=60.0) as resp:
        buffer = ""
        while True:
            chunk = resp.read(512)
            if not chunk:
                break
            buffer += chunk.decode("utf-8", errors="ignore")
            events = buffer.split("\n\n")
            buffer = events.pop()
            for ev in events:
                ev = ev.strip()
                if not ev.startswith("data: "):
                    continue
                d = json.loads(ev[6:])
                if d.get("type") == "token":
                    if stream_ttft_ms is None:
                        stream_ttft_ms = (time.perf_counter() - t0) * 1000
                    tokens_count += 1
                elif d.get("type") == "audio_chunk":
                    if stream_ttfa_ms is None:
                        stream_ttfa_ms = (time.perf_counter() - t0) * 1000
                    audio_chunks_count += 1
                elif d.get("type") == "done":
                    stream_total_ms = (time.perf_counter() - t0) * 1000

    results["streaming_vs_blocking"]["streaming"] = {
        "time_to_first_token_ms": round(stream_ttft_ms or 0, 2),
        "time_to_first_audio_ms": round(stream_ttfa_ms or 0, 2),
        "total_latency_ms": round(stream_total_ms, 2),
        "tokens_count": tokens_count,
        "audio_chunks_count": audio_chunks_count,
    }
    print(f"Streaming (/api/assist/stream):")
    print(f"  Time-To-First-Token (Visual): {stream_ttft_ms:.1f} ms")
    print(f"  Time-To-First-Audio (Voice):  {stream_ttfa_ms:.1f} ms")
    print(f"  Total Roundtrip Latency:      {stream_total_ms:.1f} ms")
    print(f"  Speedup to First Token:       {block_ttft_ms / max(1, stream_ttft_ms):.1f}x faster!")
    print(f"  Speedup to First Audio:       {block_ttfa_ms / max(1, stream_ttfa_ms):.1f}x faster!")

    # Save benchmark results
    out_file = PROJECT_ROOT / "data/empirical_ttft_benchmark.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved empirical benchmark results to: {out_file}")

if __name__ == "__main__":
    run_benchmark()

