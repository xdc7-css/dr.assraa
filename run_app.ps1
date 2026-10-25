# PowerShell Launch Script for Arabic Multimodal Assistive Vision (AMAV)
$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Arabic Multimodal Assistive Vision (AMAV)" -ForegroundColor Yellow
Write-Host " Local Offline Edge Assistive Prototype" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Virtual Environment Check
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "[ERROR] Python virtual environment not found at $VenvPython" -ForegroundColor Red
    Write-Host "Please create it using: py -3.12 -m venv .venv" -ForegroundColor Yellow
    exit 1
}

# 2. Configure Local Offline Model & Ollama Paths (Drive X:)
$env:OLLAMA_MODELS = Join-Path $ProjectRoot "models\ollama"
$env:OLLAMA_HOST = "127.0.0.1:11434"
if (-not (Test-Path $env:OLLAMA_MODELS)) {
    New-Item -ItemType Directory -Path $env:OLLAMA_MODELS -Force | Out-Null
}

# 3. Ensure Local Ollama Service is Listening
$OllamaPortOpen = Test-NetConnection -ComputerName 127.0.0.1 -Port 11434 -InformationLevel Quiet
if (-not $OllamaPortOpen) {
    Write-Host "[INFO] Ollama service not detected on 127.0.0.1:11434. Launching local Ollama..." -ForegroundColor Yellow
    & $VenvPython "scripts\run_ollama_service.py"
} else {
    Write-Host "[OK] Local Ollama service is active on 127.0.0.1:11434" -ForegroundColor Green
}

# 4. Check Required Pretrained Offline Models
$RequiredModels = @(
    "models\yolo11n.pt",
    "models\piper\ar_JO-kareem-medium.onnx"
)
foreach ($m in $RequiredModels) {
    $fullPath = Join-Path $ProjectRoot $m
    if (-not (Test-Path $fullPath)) {
        Write-Host "[WARN] Model file $m is missing. Running model download script..." -ForegroundColor Yellow
        & $VenvPython -m scripts.download_models --profile low_memory
        break
    }
}

# 5. Check Built Frontend Assets (React + TypeScript)
$FrontendBuild = Join-Path $ProjectRoot "app\static\assets"
if (-not (Test-Path $FrontendBuild)) {
    Write-Host "[INFO] Built frontend assets not found. Building React/TypeScript frontend..." -ForegroundColor Yellow
    Push-Location (Join-Path $ProjectRoot "frontend")
    if (-not (Test-Path "node_modules")) {
        npm install
    }
    npm run build
    Pop-Location
} else {
    Write-Host "[OK] Built React frontend assets verified in app/static/assets" -ForegroundColor Green
}

# 6. Launch System Diagnostics Check
Write-Host "`nRunning system diagnostic check..." -ForegroundColor Green
& $VenvPython -m scripts.check_system

# 7. Start Application Server
Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host " Starting AMAV Server on http://localhost:8000" -ForegroundColor Green
Write-Host " Secure Context (Camera & Mic enabled) at: http://localhost:8000" -ForegroundColor Yellow
Write-Host " Press Ctrl+C to stop the application." -ForegroundColor Gray
Write-Host "==========================================================" -ForegroundColor Cyan

& $VenvPython -m uvicorn app.main:app --host 127.0.0.1 --port 8000
