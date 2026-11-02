#!/usr/bin/env python3
"""
AMAV Project One-Command Launcher
Usage:
    python run
    python run.py
"""

import os
import sys
import time
import socket
import urllib.request
import json
import webbrowser
import threading
import subprocess

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)
os.chdir(PROJECT_DIR)

VENV_PYTHON = os.path.join(PROJECT_DIR, ".venv", "Scripts", "python.exe")
OLLAMA_EXE = os.path.join(PROJECT_DIR, "tools", "Ollama", "ollama.exe")
OLLAMA_MODELS = os.path.join(PROJECT_DIR, "models", "ollama")
OLLAMA_HOST = "127.0.0.1:11434"
SERVER_URL = "http://127.0.0.1:8000"
HEALTH_URL = f"{SERVER_URL}/api/health"

# 1. Automatic .venv Python Environment Redirection
if os.path.isfile(VENV_PYTHON):
    current_py = os.path.abspath(sys.executable).lower()
    target_py = os.path.abspath(VENV_PYTHON).lower()
    if current_py != target_py:
        # Re-execute under the virtual environment's Python and wait indefinitely
        cmd = [VENV_PYTHON, os.path.abspath(__file__)] + sys.argv[1:]
        try:
            sub = subprocess.Popen(cmd)
            exit_code = sub.wait()
            sys.exit(exit_code)
        except KeyboardInterrupt:
            try:
                sub.wait(timeout=5)
            except Exception:
                try:
                    sub.terminate()
                except Exception:
                    pass
            sys.exit(0)

def is_port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex((host, port)) == 0

def check_amav_running() -> bool:
    try:
        req = urllib.request.Request(HEALTH_URL, headers={"User-Agent": "AMAV-Launcher/1.0"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("status") == "ok"
    except Exception:
        return False

def check_ollama_model(model_name: str = "qwen3-vl:2b-instruct-q4_K_M") -> bool:
    try:
        req = urllib.request.Request(f"http://{OLLAMA_HOST}/api/tags", headers={"User-Agent": "AMAV-Launcher/1.0"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name") for m in data.get("models", [])]
            return any(model_name in m for m in models)
    except Exception:
        return False

def open_browser_when_ready(stop_event: threading.Event):
    """Background thread that verifies server health and launches the browser once ready."""
    for _ in range(60):
        if stop_event.is_set():
            return
        time.sleep(0.4)
        if check_amav_running():
            print("\n[OK] AMAV server is ready and healthy!")
            print(f"[+] Opening default browser at {SERVER_URL} ...\n")
            try:
                webbrowser.open(SERVER_URL)
            except Exception as e:
                print(f"[WARN] Failed to open browser automatically: {e}")
                print(f"[+] Please open your browser manually at: {SERVER_URL}")
            return

def main():
    print("==========================================================")
    print(" AMAV — Arabic Multimodal Assistive Vision")
    print(" Local Edge Assistive Assistant (100% Offline)")
    print(" University of Basrah — Computer Engineering (2026-2027)")
    print("==========================================================")

    # 2. Port Conflict & Duplicate Instance Detection
    if is_port_open(8000):
        if check_amav_running():
            print("[OK] AMAV server is already active on http://127.0.0.1:8000")
            print("[+] Opening application in default browser...")
            webbrowser.open(SERVER_URL)
            print("Done! Application opened in your browser.")
            sys.exit(0)
        else:
            print("[ERROR] Port 8000 is occupied by another application.")
            print("Please close the application using port 8000 and try again.")
            sys.exit(1)

    # 3. Configure Ollama Environment & Start Service if Necessary
    os.environ["OLLAMA_MODELS"] = OLLAMA_MODELS
    os.environ["OLLAMA_HOST"] = OLLAMA_HOST
    os.makedirs(OLLAMA_MODELS, exist_ok=True)

    ollama_proc = None
    if not is_port_open(11434):
        print("[*] Ollama service not detected. Starting local Ollama...")
        ollama_bin = OLLAMA_EXE if os.path.isfile(OLLAMA_EXE) else "ollama"
        try:
            ollama_proc = subprocess.Popen(
                [ollama_bin, "serve"],
                env=os.environ.copy(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
            )
            for _ in range(16):
                time.sleep(0.5)
                if is_port_open(11434):
                    break
        except Exception as e:
            print(f"[WARN] Failed to auto-launch Ollama: {e}")

    if is_port_open(11434):
        print("[OK] Local Ollama service is active on 127.0.0.1:11434")
        if check_ollama_model("qwen3-vl:2b-instruct-q4_K_M"):
            print("[OK] Required model verified: qwen3-vl:2b-instruct-q4_K_M")
        else:
            print("[INFO] Model will load from local storage on first use.")
    else:
        print("[WARN] Ollama service not reachable on port 11434.")

    # 4. Verify Built Frontend Assets
    frontend_assets = os.path.join(PROJECT_DIR, "app", "static", "assets")
    if not os.path.isdir(frontend_assets) or not os.listdir(frontend_assets):
        print("[INFO] Built React frontend assets missing. Building frontend once...")
        try:
            subprocess.run(["npm", "--prefix", "frontend", "run", "build"], cwd=PROJECT_DIR, check=True)
            print("[OK] Frontend built successfully.")
        except Exception as e:
            print(f"[ERROR] Frontend build failed: {e}")
            sys.exit(1)
    else:
        print("[OK] Production frontend verified in app/static")

    # 5. Start Background Browser Opener
    stop_event = threading.Event()
    browser_thread = threading.Thread(target=open_browser_when_ready, args=(stop_event,), daemon=True)
    browser_thread.start()

    # 6. Start FastAPI / Uvicorn Server IN-PROCESS (Reliable Lifetime)
    print("\n[*] Starting AMAV backend on http://127.0.0.1:8000 ...")
    print("Press Ctrl+C at any time to stop the server.\n")

    try:
        import uvicorn
        from app.main import app

        config = uvicorn.Config(
            app=app,
            host="127.0.0.1",
            port=8000,
            log_level="info",
            access_log=True,
        )
        server = uvicorn.Server(config)
        server.run()
    except KeyboardInterrupt:
        print("\n\n[INFO] Stopping AMAV application gracefully...")
    except Exception as e:
        print(f"\n[ERROR] Server encountered an error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        stop_event.set()
        if ollama_proc:
            print("[*] Stopping launcher-started Ollama service...")
            try:
                ollama_proc.terminate()
                ollama_proc.wait(timeout=2)
            except Exception:
                try:
                    ollama_proc.kill()
                except Exception:
                    pass

        print("[OK] AMAV stopped cleanly. Goodbye!\n")

if __name__ == "__main__":
    main()
