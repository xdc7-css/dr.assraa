$ollamaExe = "X:\asraa project\tools\Ollama\ollama.exe"
$modelsDir = "X:\asraa project\models\ollama"

if (-not (Test-Path $modelsDir)) {
    New-Item -ItemType Directory -Path $modelsDir -Force | Out-Null
}

$env:OLLAMA_MODELS = $modelsDir
$env:OLLAMA_HOST = "127.0.0.1:11434"

$isOpen = Test-NetConnection -ComputerName 127.0.0.1 -Port 11434 -InformationLevel Quiet
if ($isOpen) {
    Write-Host "Ollama service is already listening on 127.0.0.1:11434"
} else {
    Write-Host "Starting Ollama serve from $ollamaExe with models at $modelsDir..."
    $proc = Start-Process -FilePath $ollamaExe -ArgumentList "serve" -PassThru -NoNewWindow
    Write-Host "Started Ollama serve with PID: $($proc.Id)"
    
    # Wait up to 15 seconds for port to open
    $retries = 15
    while ($retries -gt 0) {
        Start-Sleep -Seconds 1
        if (Test-NetConnection -ComputerName 127.0.0.1 -Port 11434 -InformationLevel Quiet) {
            Write-Host "Ollama service is now listening on 127.0.0.1:11434"
            break
        }
        $retries--
    }
}
