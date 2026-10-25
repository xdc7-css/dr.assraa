"""Generate audio comparison samples across pace settings (length_scale 1.0, 1.05, 1.10).
Outputs WAV files and a JSON catalog for verification.
"""
from __future__ import annotations

import base64
import json
import time
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.adapters.tts_adapter import TTSAdapter
from app.config import get_config
OUTPUT_DIR = PROJECT_ROOT / "data" / "audio_samples"

TEST_SENTENCES = [
    {
        "id": "directions",
        "category": "Directions / Spatial Guidance",
        "text": "توجه إلى الأمام بحذر، ثم انعطف نحو اليمين بعد خطوتين.",
    },
    {
        "id": "numbers",
        "category": "Numbers / Numerical Values",
        "text": "رقم القاعة هو 204، وتاريخ اليوم هو 25 تشرين الأول 2026.",
    },
    {
        "id": "objects",
        "category": "Object Names",
        "text": "أمامك طاولة عليها حاسوب محمول، وقنينة ماء زرقاء، وكوب قهوة.",
    },
    {
        "id": "mixed_script",
        "category": "Mixed Arabic and English Script",
        "text": "مختبر الحاسوب والذكاء الاصطناعي في مبنى AMAV Room 102.",
    },
    {
        "id": "paragraph",
        "category": "Short Assistive Paragraph",
        "text": "أهلاً بك في نظام المساعد البصري الذكي. يمكنك سؤالي عما يوجد أمامك، أو طلب قراءة النصوص، أو البحث عن الأشياء.",
    },
]

PACE_SETTINGS = [
    (1.0, "normal_pace"),
    (1.05, "assistive_optimal"),
    (1.10, "deliberate_slow"),
]

def generate_comparison_suite():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cfg = get_config()
    tts = TTSAdapter(cfg.tts)
    print("Loading Piper TTS voice model...")
    if not tts.load_model():
        print(f"Failed to load Piper model: {tts._load_error}")
        return

    catalog = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model": "ar_JO-kareem-medium (ONNX)",
        "sample_rate_hz": tts._sample_rate,
        "listening_verification": "files_generated_pending_human_ear_audit",
        "note": "A non-empty WAV confirms successful synthesis, headers, and duration; human ear evaluation determines subjective prosodic naturalness.",
        "samples": [],
    }

    print("\n--- Generating Audio Comparison Samples ---")
    for s in TEST_SENTENCES:
        s_id = s["id"]
        text = s["text"]
        print(f"\nSentence [{s['category']}]: '{text}'")

        sentence_record = {
            "sentence_id": s_id,
            "category": s["category"],
            "text": text,
            "variants": [],
        }

        for pace, pace_name in PACE_SETTINGS:
            res = tts.speak(text, length_scale=pace)
            if res.status != "ok" or not res.audio_base64:
                print(f"  [FAIL] pace={pace} error: {res.error}")
                continue

            wav_filename = f"{s_id}_{pace_name}_{pace:.2f}.wav"
            wav_path = OUTPUT_DIR / wav_filename
            wav_bytes = base64.b64decode(res.audio_base64)
            with open(wav_path, "wb") as f:
                f.write(wav_bytes)

            print(f"  [OK] Saved {wav_filename} (duration: {res.duration_s}s, latency: {res.latency_ms}ms, size: {len(wav_bytes)} bytes)")

            sentence_record["variants"].append({
                "pace_length_scale": pace,
                "pace_label": pace_name,
                "filename": wav_filename,
                "relative_path": f"data/audio_samples/{wav_filename}",
                "duration_seconds": res.duration_s,
                "latency_ms": res.latency_ms,
                "file_size_bytes": len(wav_bytes),
                "sample_rate": res.sample_rate,
            })

        catalog["samples"].append(sentence_record)

    catalog_path = OUTPUT_DIR / "comparison_catalog.json"
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    print(f"\n[DONE] Audio comparison catalog saved to {catalog_path}")

if __name__ == "__main__":
    generate_comparison_suite()
