"""Ollama service launcher and manager ensuring OLLAMA_MODELS is always on Drive X:."""
import os
import sys
import subprocess
import time
import httpx

MODELS_DIR = r"X:\asraa project\models\ollama"
OLLAMA_EXE = r"X:\asraa project\tools\Ollama\ollama.exe"
HOST = "127.0.0.1:11434"

def is_running() -> bool:
    try:
        r = httpx.get(f"http://{HOST}/api/tags", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False

def start_service():
    os.makedirs(MODELS_DIR, exist_ok=True)
    if is_running():
        print(f"Ollama is already running and reachable at http://{HOST}")
        return

    env = os.environ.copy()
    env["OLLAMA_MODELS"] = MODELS_DIR
    env["OLLAMA_HOST"] = HOST

    print(f"Starting {OLLAMA_EXE} serve with OLLAMA_MODELS={MODELS_DIR}...")
    proc = subprocess.Popen(
        [OLLAMA_EXE, "serve"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    print(f"Spawned Ollama serve process with PID {proc.pid}")

    for attempt in range(15):
        time.sleep(1)
        if is_running():
            print(f"Ollama successfully started and listening on http://{HOST}")
            return
        print(f"Waiting for Ollama to become ready... ({attempt + 1}/15)")

    if is_running():
        print("Ollama is ready!")
    else:
        print("WARNING: Timed out waiting for Ollama to report ready.")

if __name__ == "__main__":
    start_service()
