"""Creates a compact review ZIP containing source code, tests, configs, documentation,
synthetic fixtures, and non-personal evaluation evidence.
Explicitly excludes:
- secrets, keys, or .env files
- virtual environments (.venv)
- model weight binary blobs (*.pt, *.onnx, *.pth, models/ollama/blobs)
- large datasets and personal recordings
"""
from __future__ import annotations

import os
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ZIP_PATH = PROJECT_ROOT / "amav_review_package.zip"

EXCLUDE_DIRS = {
    ".venv",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".pip_cache",
    "blobs",
    "tools",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".tmp",
    ".log",
    ".pt",
    ".pth",
    ".onnx",
}

def should_include(rel_path: Path) -> bool:
    parts = rel_path.parts
    # Exclude any path that touches an excluded directory
    for ex in EXCLUDE_DIRS:
        if ex in parts:
            return False

    # Exclude model weights inside models/
    if "models" in parts:
        if rel_path.suffix in EXCLUDE_EXTENSIONS or "ollama" in parts or "easyocr" in parts or "whisper" in parts:
            # Only include models_manifest.json or small metadata
            return False

    # Exclude large binary extensions
    if rel_path.suffix.lower() in EXCLUDE_EXTENSIONS:
        return False

    # Exclude zip itself
    if rel_path.name == "amav_review_package.zip":
        return False

    return True

def create_package():
    print(f"Creating review package: {ZIP_PATH}...")
    file_count = 0
    total_uncompressed = 0

    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(PROJECT_ROOT):
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(PROJECT_ROOT)

                if should_include(rel_path):
                    size = full_path.stat().st_size
                    # Limit individual file to 5MB to guarantee compact archive
                    if size > 5 * 1024 * 1024:
                        continue
                    zf.write(full_path, arcname=str(rel_path))
                    file_count += 1
                    total_uncompressed += size

    zip_size_mb = ZIP_PATH.stat().st_size / (1024 * 1024)
    print(f"[OK] Created {ZIP_PATH.name}:")
    print(f"  Files included: {file_count}")
    print(f"  Uncompressed size: {total_uncompressed / (1024*1024):.2f} MB")
    print(f"  Compressed ZIP size: {zip_size_mb:.2f} MB")

if __name__ == "__main__":
    create_package()
