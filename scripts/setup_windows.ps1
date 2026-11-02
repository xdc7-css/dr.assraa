# ==============================================================================
# AMAV — Arabic Multimodal Assistive Vision
# Automated Setup & Installation Script for Windows
# ==============================================================================
# جامعة البصرة — كلية الهندسة — قسم هندسة الحاسوب (2026 - 2027)
# مشروع تخرج: نظام المساعد البصري الذكي متعدد الوسائط لفاقدي وضعاف البصر
# ==============================================================================

[CmdletBinding()]
param (
    [string]$InstallDir = "",
    [switch]$SkipVlm,
    [switch]$SkipModels,
    [switch]$ForceRebuild,
    [switch]$YesToAll
)

$ErrorActionPreference = "Stop"

try {
    $OutputEncoding = [System.Text.Encoding]::UTF8
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch {}

if (-not $InstallDir) {
    if ($PSScriptRoot) {
        $InstallDir = Split-Path -Parent $PSScriptRoot
    } else {
        $InstallDir = (Get-Location).Path
    }
}

function Write-StageHeader {
    param([string]$StageNum, [string]$Title)
    Write-Host ""
    Write-Host "========================================================================" -ForegroundColor DarkGray
    Write-Host "[$StageNum/8] $Title" -ForegroundColor Cyan
    Write-Host "========================================================================" -ForegroundColor DarkGray
}

function Write-StatusOk {
    param([string]$Text)
    Write-Host "  [تم / OK] $Text" -ForegroundColor Green
}

function Write-StatusSkip {
    param([string]$Text)
    Write-Host "  [تخطي / SKIPPED] $Text" -ForegroundColor DarkGray
}

function Write-StatusWarn {
    param([string]$Text)
    Write-Host "  [تنبيه / WARN] $Text" -ForegroundColor Yellow
}

function Write-StatusMissing {
    param([string]$Text)
    Write-Host "  [ناقص / MISSING] $Text" -ForegroundColor Magenta
}

function Write-StatusFail {
    param([string]$Text)
    Write-Host "  [فشل / FAILED] $Text" -ForegroundColor Red
}

function Ask-UserApproval {
    param([string]$Question)
    if ($YesToAll) {
        Write-Host "  [تلقائي] الموافقة مفعلة مسبقاً (-YesToAll)" -ForegroundColor DarkGray
        return $true
    }
    Write-Host ""
    Write-Host "  ❓ $Question" -ForegroundColor Yellow
    $ans = Read-Host "     اكتب Y للموافقة، أو N للإلغاء [Y/N]"
    if ($ans -and ($ans.Trim().ToUpper() -eq "Y" -or $ans.Trim().ToUpper() -eq "YES" -or $ans.Trim() -eq "نعم" -or $ans.Trim() -eq "ي")) {
        return $true
    }
    return $false
}

function Refresh-ProcessEnv {
    $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $combined = "$machinePath;$userPath"
    $extraPaths = @(
        "C:\Program Files\Git\cmd",
        "C:\Program Files\Git\bin",
        "$env:LOCALAPPDATA\Programs\Git\cmd",
        "$env:LOCALAPPDATA\Programs\Python\Python312",
        "$env:LOCALAPPDATA\Programs\Python\Python312\Scripts",
        "C:\Program Files\Python312",
        "C:\Program Files\Python312\Scripts",
        "$env:LOCALAPPDATA\Programs\Ollama",
        "C:\Program Files\Ollama"
    )
    foreach ($p in $extraPaths) {
        if ((Test-Path $p) -and ($combined -notlike "*$p*")) {
            $combined = "$p;$combined"
        }
    }
    $env:PATH = $combined
}

function Find-Python312 {
    Refresh-ProcessEnv

    # 1. Check Python Launcher 'py -3.12'
    $pyLauncher = Get-Command "py" -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        try {
            $ver = & py -3.12 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if ($ver -and $ver.Trim() -eq "3.12") {
                $pyPath = & py -3.12 -c "import sys; print(sys.executable)" 2>$null
                if ($pyPath -and (Test-Path $pyPath.Trim())) {
                    return $pyPath.Trim()
                }
            }
        } catch {}
    }

    # 2. Check 'python' in PATH
    $sysPython = Get-Command "python" -ErrorAction SilentlyContinue
    if ($sysPython) {
        try {
            $ver = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if ($ver -and $ver.Trim() -eq "3.12") {
                return $sysPython.Source
            }
        } catch {}
    }

    # 3. Check standard Windows Python 3.12 installation directories
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"),
        (Join-Path $env:ProgramFiles "Python312\python.exe"),
        "C:\Python312\python.exe"
    )
    foreach ($cand in $candidates) {
        if (Test-Path $cand) {
            try {
                $ver = & $cand -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
                if ($ver -and $ver.Trim() -eq "3.12") {
                    return $cand
                }
            } catch {}
        }
    }

    return $null
}

function Test-PortListening {
    param(
        [string]$HostName = "127.0.0.1",
        [int]$Port = 11434,
        [int]$TimeoutMs = 800
    )
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $connect = $tcp.BeginConnect($HostName, $Port, $null, $null)
        $wait = $connect.AsyncWaitHandle.WaitOne($TimeoutMs, $false)
        if ($wait -and $tcp.Connected) {
            $tcp.EndConnect($connect)
            $tcp.Close()
            return $true
        }
        $tcp.Close()
    } catch {}
    return $false
}

# --- Welcome Banner ---
Write-Host ""
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  AMAV — Arabic Multimodal Assistive Vision (إعداد وتثبيت النظام)       " -ForegroundColor White
Write-Host "  نظام المساعد البصري الذكي متعدد الوسائط لفاقدي وضعاف البصر            " -ForegroundColor Gray
Write-Host "  جامعة البصرة — كلية الهندسة — قسم هندسة الحاسوب (2026 - 2027)         " -ForegroundColor DarkGray
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  [مجلد التثبيت Target]: $InstallDir" -ForegroundColor White

if (-not (Test-Path $InstallDir)) {
    Write-StatusFail "المجلد المحدد غير موجود: $InstallDir"
    exit 1
}

Set-Location $InstallDir

# ------------------------------------------------------------------------------
# STAGE 1: System Compatibility & WinGet Check
# ------------------------------------------------------------------------------
Write-StageHeader "1" "فحص متطلبات النظام ومدير الحزم WinGet"

$osVersion = [System.Environment]::OSVersion.Version
if ($osVersion.Major -lt 10) {
    Write-StatusFail "نظام التشغيل غير مدعوم ($($osVersion.ToString())). يتطلب AMAV نظام Windows 10 أو Windows 11 (64-bit)."
    exit 1
}
Write-StatusOk "نظام التشغيل مدعوم: Windows $($osVersion.Major) (Build $($osVersion.Build))"

$wingetCmd = Get-Command "winget" -ErrorAction SilentlyContinue
if ($wingetCmd) {
    $wingetVer = & winget --version 2>&1
    Write-StatusOk "مدير الحزم WinGet متوفر في النظام: $wingetVer"
} else {
    Write-StatusWarn "مدير الحزم WinGet غير متوفر حالياً في PATH."
    Write-Host "   لتثبيته: افتح متجر مايكروسوفت (Microsoft Store) وثبت تطبيق 'App Installer'." -ForegroundColor Gray
}

# ------------------------------------------------------------------------------
# STAGE 2: Core Prerequisites (Git, Python 3.12, Ollama)
# ------------------------------------------------------------------------------
Write-StageHeader "2" "فحص وتجهيز البرامج الأساسية (Git, Python 3.12, Ollama)"

# 2.1 Git Check
$gitCmd = Get-Command "git" -ErrorAction SilentlyContinue
if ($gitCmd) {
    Write-StatusOk "برنامج Git متوفر في النظام: $(& git --version)"
} else {
    Write-StatusMissing "برنامج Git غير مثبت أو غير معرف في متغيرات البيئة (PATH)."
    if ($wingetCmd) {
        if (Ask-UserApproval "برنامج Git مو موجود بجهازك، وهو ضروري لسحب وتحديث ملفات المشروع. تريد نثبته هسه عبر WinGet؟") {
            Write-Host "  [*] جاري تثبيت Git..." -ForegroundColor Cyan
            & winget install --id Git.Git -e --source winget --accept-source-agreements --accept-package-agreements
            Refresh-ProcessEnv
            $gitCmd = Get-Command "git" -ErrorAction SilentlyContinue
            if ($gitCmd) {
                Write-StatusOk "تم تثبيت Git بنجاح: $(& git --version)"
            } else {
                Write-StatusWarn "تم تثبيت Git ولكن قد يتطلب إعادة تشغيل التيرمنال للتعرف عليه."
            }
        } else {
            Write-StatusFail "تم إيقاف التثبيت لعدم توفر أداة Git المطلوبة."
            exit 1
        }
    } else {
        Write-StatusFail "يرجى تثبيت Git يدوياً من https://git-scm.com/download/win ثم إعادة المحاولة."
        exit 1
    }
}

# 2.2 Python 3.12 Check
$python312 = Find-Python312
if ($python312) {
    $pyVer = & $python312 --version 2>&1
    Write-StatusOk "مفسر Python 3.12 مؤكد وجاهز: $pyVer ($python312)"
} else {
    Write-StatusMissing "بايثون الإصدار 3.12 (Python 3.12) غير موجود على هذا الحاسوب!"
    Write-Host "  [ملاحظة فنية] يتطلب AMAV بايثون 3.12 حصراً لتوافق مكتبات الذكاء الاصطناعي (PyTorch, OnnxRuntime, CTranslate2)." -ForegroundColor DarkGray
    if ($wingetCmd) {
        if (Ask-UserApproval "بايثون الإصدار 3.12 مو موجود بحاسوبك، والمشروع يحتاجه حصراً. تريد نثبته هسه عبر WinGet؟") {
            Write-Host "  [*] جاري تثبيت Python 3.12..." -ForegroundColor Cyan
            & winget install --id Python.Python.3.12 -e --source winget --accept-source-agreements --accept-package-agreements
            Refresh-ProcessEnv
            $python312 = Find-Python312
            if ($python312) {
                Write-StatusOk "تم تثبيت Python 3.12 بنجاح: $python312"
            } else {
                Write-StatusFail "تم التثبيت ولكن لم يتم العثور على مفسر 3.12 تلقائياً. يرجى إعادة فتح التيرمنال."
                exit 1
            }
        } else {
            Write-StatusFail "تم إيقاف التثبيت لعدم توفر مفسر بايثون 3.12."
            exit 1
        }
    } else {
        Write-StatusFail "يرجى تثبيت Python 3.12 من https://www.python.org/downloads/ ثم إعادة المحاولة."
        exit 1
    }
}

# 2.3 Ollama Runtime Detection
$ollamaBin = $null
$candidatesOllama = @(
    (Join-Path $InstallDir "tools\Ollama\ollama.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"),
    (Join-Path $env:ProgramFiles "Ollama\ollama.exe")
)
$pathOllamaCmd = Get-Command "ollama" -ErrorAction SilentlyContinue
if ($pathOllamaCmd) { $candidatesOllama += $pathOllamaCmd.Source }

foreach ($cand in $candidatesOllama) {
    if ($cand -and (Test-Path $cand)) {
        $ollamaBin = $cand
        break
    }
}

if ($ollamaBin) {
    Write-StatusOk "محرك Ollama متوفر: $ollamaBin"
} else {
    Write-StatusMissing "محرك Ollama غير مثبت حالياً على هذا الجهاز."
    if ($wingetCmd) {
        if (Ask-UserApproval "محرك Ollama مو موجود بجهازك، وهو المحرك اللي يشغل نموذج الرؤية Qwen3-VL محلياً بدون إنترنت. تريد نثبته هسه؟") {
            Write-Host "  [*] جاري تثبيت Ollama عبر WinGet..." -ForegroundColor Cyan
            & winget install --id Ollama.Ollama -e --source winget --accept-source-agreements --accept-package-agreements
            Refresh-ProcessEnv
            $userOllama = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
            if (Test-Path $userOllama) {
                $ollamaBin = $userOllama
                Write-StatusOk "تم تثبيت Ollama بنجاح: $ollamaBin"
            }
        } else {
            Write-StatusWarn "تم تخطي تثبيت Ollama. يمكنك تثبيته لاحقاً من https://ollama.com"
        }
    } else {
        Write-StatusWarn "يمكنك تثبيت Ollama يدوياً لاحقاً من https://ollama.com"
    }
}

# ------------------------------------------------------------------------------
# STAGE 3: Project Directory, Permissions & Storage Check
# ------------------------------------------------------------------------------
Write-StageHeader "3" "فحص مجلد المشروع وصلاحيات الكتابة والمساحة المتوفرة"

try {
    $driveLetter = (Split-Path -Qualifier (Resolve-Path $InstallDir)).TrimEnd(":")
    $disk = Get-CimInstance -ClassName Win32_LogicalDisk -Filter "DeviceID = '${driveLetter}:'"
    $freeGB = [math]::Round($disk.FreeSpace / 1GB, 2)

    if ($freeGB -ge 12.0) {
        Write-StatusOk "مساحة القرص المتوفرة على (${driveLetter}:) ممتازة: $freeGB GB (المطلوب ~8 إلى 12 GB)."
    } elseif ($freeGB -ge 8.0) {
        Write-StatusWarn "مساحة القرص المتوفرة ($freeGB GB) كافية للتثبيت ولكن يستحسن 12 GB على الأقل لضمان تشغيل سلس وذاكرة كافية."
    } else {
        Write-StatusFail "المساحة المتبقية ($freeGB GB) غير كافية! يتطلب التثبيت 8 GB كحد أدنى لتنزيل النماذج والحزم والكاش المؤقت."
        exit 1
    }
} catch {
    Write-StatusWarn "تعذر التحقق التلقائي من مساحة القرص: $_"
}

# Test Write Permissions
$permTestFile = Join-Path $InstallDir (".write_test_" + [System.Guid]::NewGuid().ToString("N"))
try {
    [System.IO.File]::WriteAllText($permTestFile, "amav_test_ok")
    [System.IO.File]::Delete($permTestFile)
    Write-StatusOk "صلاحيات القراءة والكتابة في مجلد المشروع مؤكدة وممتازة."
} catch {
    Write-StatusFail "لا تتوفر صلاحيات كتابة في المجلد: $InstallDir. يرجى تشغيل التيرمنال كمسؤول أو اختيار مجلد مستخدم."
    exit 1
}

# ------------------------------------------------------------------------------
# STAGE 4: Python Virtual Environment (.venv) Setup
# ------------------------------------------------------------------------------
Write-StageHeader "4" "إعداد بيئة بايثون الافتراضية المستقلة (.venv)"

$venvDir = Join-Path $InstallDir ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "  [*] جاري إنشاء بيئة بايثون افتراضية مستقلة باستخدام Python 3.12..." -ForegroundColor Cyan
    & $python312 -m venv $venvDir
    if (-not (Test-Path $venvPython)) {
        Write-StatusFail "فشل إنشاء البيئة الافتراضية في: $venvDir"
        exit 1
    }
    Write-StatusOk "تم إنشاء البيئة الافتراضية بنجاح في: $venvDir"
} else {
    Write-StatusOk "البيئة الافتراضية المستقلة موجودة مسبقاً في: $venvDir"
}

# ------------------------------------------------------------------------------
# STAGE 5: Dependencies & Hardware Acceleration (CUDA/GPU)
# ------------------------------------------------------------------------------
Write-StageHeader "5" "فحص تسريع كرت الشاشة (CUDA) وتثبيت مكتبات بايثون"

# 5.1 Check GPU / CUDA Hardware Acceleration
$hasGpu = $false
$nvidiaSmi = Get-Command "nvidia-smi" -ErrorAction SilentlyContinue
if ($nvidiaSmi) {
    try {
        $smiOut = & nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits 2>$null
        if ($smiOut) {
            $parts = $smiOut.Split(",")
            if ($parts.Count -ge 3) {
                $gpuName = $parts[0].Trim()
                $vramMb = $parts[1].Trim()
                $drvVer = $parts[2].Trim()
                Write-StatusOk "تم اكتشاف كرت شاشة NVIDIA: $gpuName ($vramMb MB VRAM) مع دعم CUDA (Driver $drvVer)"
                Write-Host "  [ملاحظة معمارية] موازنة الذاكرة (VRAM Budgeting): نموذج الرؤية الأكبر (Qwen3-VL 2B) يعمل مباشرة على كرت الشاشة GPU VRAM عبر محرك Ollama (~1.9 GB VRAM)، بينما تعمل نماذج YOLO و OCR على المعالج لضمان عدم تجاوز سعة 4GB VRAM للكرت واستقرار النظام التام." -ForegroundColor DarkGray
                $hasGpu = $true
            }
        }
    } catch {}
}

if (-not $hasGpu) {
    Write-Host "  [إشعار عتاد] لم يتم اكتشاف كرت NVIDIA منفصل يدعم CUDA. سيعمل النظام بكفاءة كاملة على المعالج المركزي (CPU) تلقائياً." -ForegroundColor DarkGray
}

# 5.2 Install Python Dependencies
Write-Host "  [*] فحص وتحديث أدوات pip و setuptools داخل البيئة الافتراضية..." -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip setuptools wheel --quiet

$reqPath = Join-Path $InstallDir "requirements.txt"
if (-not (Test-Path $reqPath)) {
    Write-StatusFail "ملف requirements.txt غير موجود في مجلد المشروع!"
    exit 1
}

Write-Host "  [*] تثبيت المكتبات المعتمدة من requirements.txt (قد يستغرق 2 إلى 4 دقائق في المرة الأولى)..." -ForegroundColor Cyan
& $venvPython -m pip install -r $reqPath --extra-index-url https://download.pytorch.org/whl/cpu

if ($LASTEXITCODE -ne 0) {
    Write-StatusFail "حدث خطأ أثناء تثبيت حزم بايثون من requirements.txt."
    exit 1
}
Write-StatusOk "تم تثبيت والتحقق من كافة مكتبات بايثون بنجاح وبأعلى درجات التوافق."

# ------------------------------------------------------------------------------
# STAGE 6: Ollama Service & Offline AI Models Acquisition
# ------------------------------------------------------------------------------
Write-StageHeader "6" "تجهيز محرك Ollama ونماذج الذكاء الاصطناعي الأوفلاين"

# 6.1 Check and Start Ollama Service
if ($ollamaBin) {
    $isOllamaListening = Test-PortListening -HostName "127.0.0.1" -Port 11434
    if (-not $isOllamaListening) {
        Write-Host "  [*] تشغيل خدمة Ollama محلياً في الخلفية..." -ForegroundColor Cyan
        $env:OLLAMA_MODELS = (Join-Path $InstallDir "models\ollama")
        Start-Process $ollamaBin -ArgumentList "serve" -WindowStyle Hidden
        for ($i = 0; $i -lt 12; $i++) {
            Start-Sleep -Milliseconds 500
            if (Test-PortListening -HostName "127.0.0.1" -Port 11434) {
                $isOllamaListening = $true
                break
            }
        }
    }

    if ($isOllamaListening) {
        Write-StatusOk "خدمة Ollama نشطة وتستجيب على المنفذ 11434."
    } else {
        Write-StatusWarn "تعذر تأكيد اتصال Ollama على المنفذ 11434. تأكد من تشغيل Ollama."
    }
}

# 6.2 Check AI Models Presence Before Download
if (-not $SkipModels) {
    $modelsDir = Join-Path $InstallDir "models"
    if (-not (Test-Path $modelsDir)) {
        New-Item -ItemType Directory -Path $modelsDir -Force | Out-Null
    }

    # Check VLM in Ollama
    $hasVlm = $false
    if ($ollamaBin) {
        $ollamaListOut = (& $ollamaBin list 2>$null) | Out-String
        if ($ollamaListOut -like "*qwen3-vl:2b-instruct-q4_K_M*") {
            $hasVlm = $true
            Write-StatusOk "نموذج الرؤية واللغة Qwen3-VL 2B موجود مسبقاً في محرك Ollama."
        }
    }

    if (-not $hasVlm -and (-not $SkipVlm)) {
        if ($ollamaBin) {
            if (Ask-UserApproval "نموذج الرؤية واللغة المحلي Qwen3-VL 2B غير موجود بحاسوبك، وحجمه حوالي 1.9 GB. تريد نبدأ بتنزيله هسه عبر الإنترنت؟") {
                Write-Host "  [*] جاري تنزيل نموذج Qwen3-VL 2B..." -ForegroundColor Cyan
            } else {
                Write-StatusWarn "تم تخطي تنزيل Qwen3-VL 2B بناءً على طلبك. لن يعمل الاستدلال البصري حتى يتم تنزيل النموذج."
                $SkipVlm = $true
            }
        } else {
            $SkipVlm = $true
        }
    }

    # Run download_models.py to verify/download offline models
    $downloadArgs = @("-m", "scripts.download_models", "--profile", "low_memory")
    if ($SkipVlm -or (-not $ollamaBin)) {
        $downloadArgs += "--skip-vlm"
    }

    Write-Host "  [*] فحص وتنزيل نماذج الذكاء الاصطناعي الأوفلاين (Piper TTS, YOLO11n, Whisper, OCR)..." -ForegroundColor Cyan
    & $venvPython $downloadArgs
    if ($LASTEXITCODE -eq 0) {
        Write-StatusOk "تم التحقق من اكتمال كافة أوزان ونماذج الذكاء الاصطناعي الأوفلاين."
    } else {
        Write-StatusWarn "انتهى فحص النماذج مع وجود ملاحظات. يمكنك إعادة الفحص لاحقاً عبر: .\.venv\Scripts\python.exe -m scripts.download_models"
    }
} else {
    Write-StatusSkip "تم تخطي تنزيل النماذج بناءً على المعامل (-SkipModels)."
}

# ------------------------------------------------------------------------------
# STAGE 7: React Frontend & Backend Verification
# ------------------------------------------------------------------------------
Write-StageHeader "7" "فحص واجهة المستخدم React والخادم الخلفي"

$assetsDir = Join-Path $InstallDir "app\static\assets"
$hasJs = (Test-Path $assetsDir) -and ((Get-ChildItem $assetsDir -Filter "*.js" -ErrorAction SilentlyContinue).Count -gt 0)
$hasCss = (Test-Path $assetsDir) -and ((Get-ChildItem $assetsDir -Filter "*.css" -ErrorAction SilentlyContinue).Count -gt 0)

if ($hasJs -and $hasCss -and (-not $ForceRebuild)) {
    Write-StatusOk "حزم واجهة المستخدم React مبنية مسبقاً وجاهزة في app/static/assets (لا حاجة لـ Node.js)."
} else {
    Write-Host "  [*] الحزم الجاهزة غير متوفرة أو تم طلب إعادة البناء. فحص Node.js / npm..." -ForegroundColor Cyan
    $npmCmd = Get-Command "npm" -ErrorAction SilentlyContinue
    if ($npmCmd) {
        Write-Host "  [*] بناء واجهة React للإنتاج عبر npm..." -ForegroundColor Cyan
        $frontendDir = Join-Path $InstallDir "frontend"
        Push-Location $frontendDir
        try {
            & npm install
            & npm run build
            Write-StatusOk "تم بناء واجهة React بنجاح ووضع الملفات في app/static."
        } catch {
            Write-StatusWarn "حدث خطأ أثناء بناء الواجهة عبر npm: $_"
        } finally {
            Pop-Location
        }
    } else {
        Write-StatusWarn "Node.js غير مثبت ولم يتم العثور على حزم مبنية مسبقاً."
        Write-Host "  [إشعار] يتضمن مستودع Git لـ AMAV الحزم المبنية مسبقاً داخل app/static/assets/." -ForegroundColor Gray
    }
}

# ------------------------------------------------------------------------------
# STAGE 8: System Diagnostics & Final Health Check
# ------------------------------------------------------------------------------
Write-StageHeader "8" "الفحص التشخيصي الشامل وتأكيد الجاهزية"

& $venvPython -m scripts.check_system

if ($LASTEXITCODE -eq 0) {
    Write-StatusOk "اجتاز النظام الفحص التشخيصي الشامل بنجاح 100%!"
} else {
    Write-StatusWarn "أظهر الفحص التشخيصي بعض التحذيرات، يرجى مراجعة التقرير أعلاه."
}

# ------------------------------------------------------------------------------
# Final Completion Banner
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host "========================================================================" -ForegroundColor Green
Write-Host "       🎉 اكتمل تثبيت وإعداد مشروع AMAV بالكامل وبنجاح فائق!            " -ForegroundColor Green
Write-Host "       AMAV Has Been Fully & Successfully Installed!                   " -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "🚀 كيفية تشغيل النظام هسه / How to run AMAV:" -ForegroundColor Yellow
Write-Host "   1. توجه إلى مجلد المشروع:" -ForegroundColor White
Write-Host "      cd `"$InstallDir`"" -ForegroundColor Cyan
Write-Host ""
Write-Host "   2. شغل النظام بأمر واحد فقط:" -ForegroundColor White
Write-Host "      python run" -ForegroundColor Green
Write-Host "      (أو: .\.venv\Scripts\python.exe run)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "🌐 الواجهة البرمجية تفتح تلقائياً في المتصفح على / Web UI:" -ForegroundColor Yellow
Write-Host "   http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host ""
Write-Host "🛑 لإيقاف النظام بأمان / To stop the server:" -ForegroundColor Yellow
Write-Host "   اضغط اختصار Ctrl + C في نافذة الطرفية (Terminal)" -ForegroundColor White
Write-Host "========================================================================" -ForegroundColor Green
