"""Model acquisition, caching, and manifest verification tool for AMAV.
Downloads and verifies approved checkpoints for YOLO11n, Piper Arabic voice,
faster-whisper multilingual base, and pulls Ollama qwen3-vl:2b.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
MANIFEST_PATH = PROJECT_ROOT / "models_manifest.json"

PIPER_VOICE_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/ar/ar_JO/kareem/medium"
PIPER_FILES = [
    ("ar_JO-kareem-medium.onnx", f"{PIPER_VOICE_BASE}/ar_JO-kareem-medium.onnx"),
    ("ar_JO-kareem-medium.onnx.json", f"{PIPER_VOICE_BASE}/ar_JO-kareem-medium.onnx.json"),
]

def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()

def update_manifest(component_key: str, **kwargs):
    if not MANIFEST_PATH.exists():
        return
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        if component_key in manifest.get("models", {}):
            manifest["models"][component_key].update(kwargs)
            manifest["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%S+03:00")
            with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Failed to update manifest for {component_key}: {e}", file=sys.stderr)

def download_file_atomic(url: str, dest_path: Path, max_retries: int = 3) -> bool:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if dest_path.exists() and dest_path.stat().st_size > 0:
        print(f"  [CACHE] File already exists: {dest_path.name} ({dest_path.stat().st_size} bytes)")
        return True

    temp_path = dest_path.with_suffix(f"{dest_path.suffix}.tmp.{os.getpid()}")
    print(f"  [DOWNLOADING] {url} -> {dest_path.name}...")

    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AMAV-ModelDownloader/1.0"}
            )
            with urllib.request.urlopen(req, timeout=60.0) as resp, open(temp_path, "wb") as out_f:
                total_size = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                block_size = 1024 * 1024
                while True:
                    chunk = resp.read(block_size)
                    if not chunk:
                        break
                    out_f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        pct = (downloaded / total_size) * 100
                        print(f"\r    Progress: {downloaded / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB ({pct:.1f}%)", end="")
            print()
            if temp_path.exists() and temp_path.stat().st_size > 0:
                temp_path.replace(dest_path)
                print(f"  [OK] Saved {dest_path.name} ({dest_path.stat().st_size} bytes)")
                return True
        except Exception as e:
            print(f"\n  [RETRY {attempt}/{max_retries}] Download failed: {e}")
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            time.sleep(2.0 * attempt)

    print(f"  [FAILED] Could not download {url} after {max_retries} attempts.")
    return False

def acquire_piper():
    print("\n--- 1. Acquiring Piper Arabic Voice (ar_JO-kareem-medium) ---")
    piper_dir = MODELS_DIR / "piper"
    success = True
    onnx_file = piper_dir / "ar_JO-kareem-medium.onnx"
    for fname, url in PIPER_FILES:
        target = piper_dir / fname
        ok = download_file_atomic(url, target)
        if not ok:
            success = False

    if success and onnx_file.exists():
        size = onnx_file.stat().st_size
        sha = compute_sha256(onnx_file)
        update_manifest(
            "tts",
            download_status="downloaded",
            storage_path=str(onnx_file.relative_to(PROJECT_ROOT)),
            size_bytes_if_known=size,
            checksum_if_available=f"sha256:{sha}",
        )
        print(f"Piper voice ready. SHA256: {sha[:12]}...")
    else:
        update_manifest("tts", download_status="failed")

def acquire_yolo():
    print("\n--- 2. Acquiring YOLO11n Object Detector ---")
    yolo_dest = MODELS_DIR / "yolo11n.pt"
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    if yolo_dest.exists() and yolo_dest.stat().st_size > 1000000:
        print(f"  [CACHE] YOLO11n already cached at {yolo_dest.name}")
        sha = compute_sha256(yolo_dest)
        update_manifest(
            "detection",
            download_status="downloaded",
            storage_path=str(yolo_dest.relative_to(PROJECT_ROOT)),
            size_bytes_if_known=yolo_dest.stat().st_size,
            checksum_if_available=f"sha256:{sha}",
        )
        return

    try:
        from ultralytics import YOLO
        print("  Using official Ultralytics loader to fetch yolo11n.pt...")
        # Ultralytics downloads yolo11n.pt into current dir or cache
        model = YOLO("yolo11n.pt")
        # Ensure it is placed in models/yolo11n.pt
        src = Path("yolo11n.pt")
        if src.exists() and src != yolo_dest:
            shutil.copy2(src, yolo_dest)
            try:
                src.unlink()
            except Exception:
                pass
        if yolo_dest.exists():
            sha = compute_sha256(yolo_dest)
            update_manifest(
                "detection",
                download_status="downloaded",
                storage_path=str(yolo_dest.relative_to(PROJECT_ROOT)),
                size_bytes_if_known=yolo_dest.stat().st_size,
                checksum_if_available=f"sha256:{sha}",
            )
            print(f"  [OK] YOLO11n ready. SHA256: {sha[:12]}...")
    except Exception as e:
        print(f"  [FALLBACK] Ultralytics direct download: {e}")
        official_yolo_url = "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt"
        if download_file_atomic(official_yolo_url, yolo_dest):
            sha = compute_sha256(yolo_dest)
            update_manifest(
                "detection",
                download_status="downloaded",
                storage_path=str(yolo_dest.relative_to(PROJECT_ROOT)),
                size_bytes_if_known=yolo_dest.stat().st_size,
                checksum_if_available=f"sha256:{sha}",
            )

def acquire_faster_whisper():
    print("\n--- 3. Acquiring faster-whisper (Systran/faster-whisper-base) ---")
    whisper_dir = MODELS_DIR / "whisper"
    whisper_dir.mkdir(parents=True, exist_ok=True)
    try:
        from faster_whisper import WhisperModel
        print("  Downloading faster-whisper-base multilingual checkpoint into models/whisper...")
        model = WhisperModel(
            "Systran/faster-whisper-base",
            device="cpu",
            compute_type="int8",
            download_root=str(whisper_dir),
        )
        update_manifest(
            "asr",
            download_status="downloaded",
            storage_path=str(whisper_dir.relative_to(PROJECT_ROOT)),
        )
        print("  [OK] faster-whisper base checkpoint cached.")
    except Exception as e:
        print(f"  [ERROR] faster-whisper download failed: {e}")
        update_manifest("asr", download_status="failed")

def acquire_easyocr():
    print("\n--- 4. Acquiring EasyOCR Models (Arabic & English) ---")
    ocr_dir = MODELS_DIR / "easyocr"
    ocr_dir.mkdir(parents=True, exist_ok=True)
    try:
        import easyocr
        print("  Initializing EasyOCR Reader to download detector & recognizer weights...")
        reader = easyocr.Reader(["ar", "en"], gpu=False, model_storage_directory=str(ocr_dir), download_enabled=True)
        update_manifest(
            "ocr",
            download_status="downloaded",
            storage_path=str(ocr_dir.relative_to(PROJECT_ROOT)),
        )
        print("  [OK] EasyOCR models ready.")
    except Exception as e:
        print(f"  [ERROR] EasyOCR acquisition failed: {e}")
        update_manifest("ocr", download_status="failed")

def acquire_ollama_vlm():
    model_tag = "qwen3-vl:2b-instruct-q4_K_M"
    print(f"\n--- 5. Acquiring Ollama VLM ({model_tag}) ---")
    x_ollama = Path("X:/asraa project/tools/Ollama/ollama.exe")
    ollama_bin = str(x_ollama) if x_ollama.exists() else shutil.which("ollama")
    if not ollama_bin:
        user_local = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
        if user_local.exists():
            ollama_bin = str(user_local)

    if not ollama_bin:
        print("  [INFO] Ollama runtime executable not found in PATH or standard directory.")
        print("  Please install Ollama from https://ollama.com/download/windows or run:")
        print("  winget install Ollama.Ollama")
        update_manifest("vlm", download_status="blocked_missing_runtime")
        return

    print(f"  Running 'ollama pull {model_tag}' via {ollama_bin}...")
    try:
        env = os.environ.copy()
        env["OLLAMA_MODELS"] = r"X:\asraa project\models\ollama"
        proc = subprocess.run([ollama_bin, "pull", model_tag], env=env, check=True)
        if proc.returncode == 0:
            print(f"  [OK] {model_tag} successfully pulled into Ollama.")
            update_manifest("vlm", download_status="downloaded", model_id=model_tag)
    except Exception as e:
        print(f"  [WARNING] Ollama pull failed: {e}")
        print("  Ensure Ollama service is active. You can run 'ollama serve' or start the Ollama application.")
        update_manifest("vlm", download_status="failed")

def main():
    parser = argparse.ArgumentParser(description="Download and verify AMAV models")
    parser.add_argument("--profile", choices=["low_memory", "balanced"], default="low_memory")
    parser.add_argument("--skip-vlm", action="store_true", help="Skip Ollama VLM pull")
    args = parser.parse_args()

    print("=" * 65)
    print(f" AMAV MODEL ACQUISITION ENGINE (Profile: {args.profile.upper()})")
    print(f" Target models directory: {MODELS_DIR}")
    print("=" * 65)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    acquire_piper()
    acquire_yolo()
    acquire_faster_whisper()
    acquire_easyocr()

    if not args.skip_vlm:
        acquire_ollama_vlm()

    print("\n" + "=" * 65)
    print(" Acquisition process finished. Review models_manifest.json for inventory status.")
    print("=" * 65)

if __name__ == "__main__":
    main()
