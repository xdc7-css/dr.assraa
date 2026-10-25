"""Automated installer and runner for Ollama on Windows."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
INSTALLER_PATH = MODELS_DIR / "OllamaSetup.exe"
OLLAMA_EXE_DEFAULT = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"

def is_ollama_installed() -> tuple[bool, Optional[Path]]:
    p = shutil.which("ollama")
    if p:
        return True, Path(p)
    if OLLAMA_EXE_DEFAULT.exists():
        return True, OLLAMA_EXE_DEFAULT
    return False, None

def download_installer() -> bool:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    if INSTALLER_PATH.exists() and INSTALLER_PATH.stat().st_size > 10000000:
        print(f"Installer already downloaded at {INSTALLER_PATH} ({INSTALLER_PATH.stat().st_size} bytes)")
        return True

    # Use official download link
    url = "https://ollama.com/download/OllamaSetup.exe"
    print(f"Downloading {url} to {INSTALLER_PATH}...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AMAV-OllamaInstaller/1.0"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp, open(INSTALLER_PATH, "wb") as f:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            while chunk := resp.read(1024 * 1024):
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = (downloaded / total) * 100
                    print(f"\r  Progress: {downloaded / (1024*1024):.1f} MB / {total / (1024*1024):.1f} MB ({pct:.1f}%)", end="")
        print()
        print(f"Successfully downloaded OllamaSetup.exe ({INSTALLER_PATH.stat().st_size} bytes)")
        return True
    except Exception as e:
        print(f"Failed to download installer: {e}")
        return False

def install_ollama() -> bool:
    installed, path = is_ollama_installed()
    if installed:
        print(f"Ollama is already installed at: {path}")
        return True

    ok = download_installer()
    if not ok:
        return False

    print("Executing silent installation of OllamaSetup.exe (/VERYSILENT /NORESTART)...")
    try:
        cmd = [str(INSTALLER_PATH), "/VERYSILENT", "/NORESTART"]
        res = subprocess.run(cmd, check=True)
        time.sleep(3)
        installed, path = is_ollama_installed()
        if installed:
            print(f"Ollama successfully installed at {path}")
            return True
        else:
            print(f"Installer finished with code {res.returncode}, but executable not found at default path.")
            return False
    except Exception as e:
        print(f"Installation execution failed: {e}")
        return False

if __name__ == "__main__":
    success = install_ollama()
    sys.exit(0 if success else 1)
