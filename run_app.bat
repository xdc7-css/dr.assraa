@echo off
title Arabic Multimodal Assistive Vision Launcher
cd /d "%~dp0"

echo ==========================================================
echo  Arabic Multimodal Assistive Vision (AMAV)
echo  Local Offline Edge Assistive Prototype
echo ==========================================================

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment not found in .venv!
    echo Please run: py -3.12 -m venv .venv
    pause
    exit /b 1
)

set "OLLAMA_MODELS=%~dp0models\ollama"
set "OLLAMA_HOST=127.0.0.1:11434"

echo Ensuring local Ollama service is active...
".venv\Scripts\python.exe" "scripts\run_ollama_service.py"

if not exist "app\static\assets" (
    echo [INFO] Building React frontend assets...
    pushd frontend
    if not exist "node_modules" call npm install
    call npm run build
    popd
)

echo.
echo Starting AMAV Server on http://localhost:8000 ...
start "" http://localhost:8000
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

pause
