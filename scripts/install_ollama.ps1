$ErrorActionPreference = "Stop"

$installer = "X:\asraa project\models\OllamaSetup.exe"
$logFile = "X:\asraa project\install_ollama.log"
$installDir = "X:\asraa project\tools\Ollama"

if (-not (Test-Path $installDir)) {
    New-Item -ItemType Directory -Path $installDir -Force | Out-Null
}

$installerArgs = "/VERYSILENT /NORESTART /SUPPRESSMSGBOXES /DIR=`"$installDir`" /LOG=`"$logFile`""
Write-Host "Installing Ollama to $installDir..."

$proc = Start-Process -FilePath $installer -ArgumentList $installerArgs -PassThru
$proc.WaitForExit()

Write-Host "Installer finished with exit code: $($proc.ExitCode)"
if (Test-Path "$installDir\ollama.exe") {
    Write-Host "SUCCESS: ollama.exe is ready at $installDir\ollama.exe"
} else {
    Write-Host "Checking log tail..."
    if (Test-Path $logFile) {
        Get-Content $logFile -Tail 25
    }
}
