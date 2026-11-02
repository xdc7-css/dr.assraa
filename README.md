# مساعد بصري ذكي متعدد الوسائط (AMAV)
### Arabic Multimodal Assistive Vision

> **مشروع تخرج لنيل درجة البكالوريوس في هندسة الحاسوب**  
> **جامعة البصرة — كلية الهندسة — قسم هندسة الحاسوب**  
> **العام الدراسي:** 2026 - 2027

---

## 🎓 العنوان الأكاديمي المعتمد (Project Title)

**العنوان العربي:**  
مساعد بصري ذكي للتعرف على البيئة وقراءة النصوص والتفاعل الصوتي لمساعدة المكفوفين وضعاف البصر

**English Formal Title:**  
*Design and Development of an AI-Based Multimodal Intelligent Assistant for Assisting Blind and Visually Impaired Individuals in Real-Time Environment Recognition and Voice Interaction*

---

### إعداد الطالبات:
1. **نور عباس عبد الحسين** 
2. **نور رمزي صبيح قاسم**
3. **غدير علاء كامل حسين**

### بإشراف:
- **م.د. اسراء حبيب**

---

## 📌 نبذة عن المشروع (Overview)

نظام مساعد بصري وتفاعلي ذكي مخصص لدعم وتمكين المكفوفين وضعاف البصر في استكشاف محيطهم والتفاعل معه صوتياً ولحظياً.  
يعتمد المشروع بنية **حوسبة الحافة المحلية بالكامل (100% Offline Edge Architecture)**، حيث تعمل كافة نماذج الذكاء الاصطناعي محلياً على حاسوب المستخدم دون إرسال أي إطارات كاميرا أو تسجيلات صوتية إلى خوادم خارجية، مما يضمن أعلى درجات الخصوصية والاستجابة السريعة دون الحاجة للاتصال بالإنترنت.

---

## ⚙️ بنية النماذج والتقنيات (Architecture & Pipeline)

1. **نموذج الرؤية واللغة (VLM):**
   - `Qwen3-VL-2B-Instruct` (مُدار محلياً عبر Ollama مع كبح التفكير الداخلي وتوجيهه نحو الردود الوصفية الإرشادية المباشرة بالعربية). محمل بنسبة 100% داخل ذاكرة كرت الشاشة GPU VRAM (~1.9 GB).
2. **كشف الكائنات وتحديد المواقع (Object Detection):**
   - `YOLO11n` (خفيف وسريع، مع تنعيم زمني ودعم تحديد اتجاهات اليمين/الوسط/اليسار).
3. **التعرف الضوئي على النصوص (OCR):**
   - `EasyOCR` (ثنائي اللغة: عربي / إنجليزي مع ضبط اتجاه الأحرف العربية وتشكيلها).
4. **التعرف الآلي على الكلام (ASR):**
   - `faster-whisper` (تفريغ صوتي سريع محلي على CUDA يدعم اللهجة العراقية والعربية الفصحى).
5. **توليد النطق الصوتي (TTS):**
   - `Piper TTS` (النموذج العربي `ar_JO-kareem-medium` بنطق طبيعي فوري ومؤشرات صوتية).
6. **التدفق اللحظي والاستجابة التراكمية (Real-Time SSE Streaming):**
   - استجابة فورية عبر Server-Sent Events (SSE)؛ يظهر النص للمستخدم فور توليد أول رمز (TTFT < 1s)، مع تشغيل الصوت التزايدي بمجرد اكتمال أول جملة عربية مفيدة دون انتظار انتهاء كامل الرد.
7. **لوحة مراقبة الأداء للمطورين (Performance Monitor):**
   - لوحة قياس حية مدمجة بالواجهة تقيس التوقيت الحقيقي من نقرة المستخدم حتى أول حرف، وأول صوت، والتكلفة الزمنية لكل نموذج (ASR, YOLO, OCR, VLM, TTS).
8. **الواجهة الأمامية (Frontend):**
   - `React 18` + `TypeScript` + `Vite` مع خط `IBM Plex Sans Arabic`، ونمط التباين العالي (`High Contrast Mode`)، والتحكم الصوتي واللوحي الكامل.
9. **الواجهة الخلفية (Backend):**
   - `FastAPI` (Python 3.12) لمعالجة الطلبات وإدارة التزامن، والذاكرة المؤقتة، والإلغاء الفوري.

---

## 🚀 تثبيت مشروع AMAV من الصفر — للمبتدئين (One-Paste Windows Installation)

إذا كنت طالباً أو باحثاً أو مقيّماً، وليس لديك أي خبرة برمجية سابقة أو حساب على GitHub، يمكنك تثبيت وتشغيل نظام **AMAV** بالكامل على حاسوبك بنقرة واحدة وبأمر واحد فقط.

كل ما تحتاجه هو حاسوب يعمل بنظام **Windows 10** أو **Windows 11** ومثبت عليه برنامج **VS Code**.

---

### 📝 خطوات التثبيت البسيطة للمبتدئين:

1. **افتح برنامج VS Code.**
2. **من القائمة الفوگ (شريط القوائم العلوي)، اختار `Terminal` وبعدين اختار `New Terminal`.**
3. **انسخ كود التثبيت الموضح في الصندوق أدناه بالكامل (اضغط على زر النسخ في الزاوية)، والصقه في شاشة التيرمنال، ثم اضغط `Enter`.**
4. **ماذا سيحدث بعد الضغط على Enter؟**
   - سيقوم الكود بفحص جهازك بدقة؛ وإذا لاحظ أن برنامجاً أساسياً مثل **Git** أو **Python 3.12** أو **Ollama** غير متوفر، سيسألك بأدب ويطلب موافقتك:
     `"برنامج Git مو موجود بجهازك، وهو ضروري لسحب ملفات المشروع من GitHub. تريد نثبّته هسه تلقائياً؟ (Y/N)"`
   - اكتب حرف `Y` واضغط `Enter` للموافقة، وسيقوم بتثبيت البرنامج تلقائياً وبأمان عبر مدير حزم ويندوز الرسمي (`winget`).
   - سيتم استنساخ ملفات المشروع تلقائياً وتثبيتها في المجلد: **`C:\AMAV`**
   - سيقوم بإنشاء بيئة بايثون المعزولة وتنزيل نماذج الذكاء الاصطناعي الأوفلاين (Piper TTS، YOLO11n، Whisper، EasyOCR، Qwen3-VL 2B).
   - **ملاحظة حول الإنترنت:** التثبيت لأول مرة فقط يحتاج اتصالاً بالإنترنت لتنزيل النماذج والمكتبات (~2 إلى 3 GB). وبمجرد اكتمال التثبيت، سيعمل النظام محلياً 100% أوفلاين دون الحاجة للإنترنت نهائياً.

---

### ⚡ كود التثبيت الشامل المباشر (انسخ هذا الكود بالكامل):

```powershell
# ==============================================================================
# تثبيت مشروع AMAV بالكامل بنقرة واحدة (للمبتدئين) — نظام ويندوز
# University of Basrah — Computer Engineering (2026 - 2027)
# ==============================================================================
$ErrorActionPreference = "Stop"

try {
    $OutputEncoding = [System.Text.Encoding]::UTF8
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch {}

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

function Prompt-User {
    param([string]$Message)
    Write-Host ""
    Write-Host "[?] $Message" -ForegroundColor Yellow
    $ans = Read-Host "     اكتب Y للموافقة، أو N للإلغاء [Y/N]"
    if ($ans -and ($ans.Trim().ToUpper() -eq "Y" -or $ans.Trim().ToUpper() -eq "YES" -or $ans.Trim() -eq "نعم" -or $ans.Trim() -eq "ي")) {
        return $true
    }
    return $false
}

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  AMAV — تثبيت المساعد البصري الذكي على ويندوز (C:\AMAV)                " -ForegroundColor White
Write-Host "  جامعة البصرة — كلية الهندسة — قسم هندسة الحاسوب (2026 - 2027)         " -ForegroundColor DarkGray
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

# [1/8] فحص توافق النظام ومدير الحزم WinGet
Write-Host "[1/8] فحص متطلبات النظام ومدير الحزم WinGet..." -ForegroundColor Cyan
$wingetCmd = Get-Command "winget" -ErrorAction SilentlyContinue
if (-not $wingetCmd) {
    Write-Host "[تنبيه] مدير الحزم winget مو متوفر بحاسوبك." -ForegroundColor Yellow
    Write-Host "لتثبيته بسهولة: افتح متجر مايكروسوفت (Microsoft Store) وثبّت تطبيق 'App Installer'." -ForegroundColor White
    Write-Host "أو نزله مباشرة من: https://aka.ms/getwinget" -ForegroundColor DarkGray
    throw "يرجى تثبيت App Installer أولاً ثم إعادة تشغيل هذا الأمر."
}
Write-Host "  [تم / OK] مدير الحزم WinGet متوفر وجاهز." -ForegroundColor Green

# [2/8] فحص وتجهيز Git و Python 3.12 و Ollama بموافقة المستخدم
Write-Host ""
Write-Host "[2/8] فحص وتجهيز البرامج الأساسية (Git, Python 3.12, Ollama)..." -ForegroundColor Cyan
Refresh-ProcessEnv

# فحص Git
$gitCmd = Get-Command "git" -ErrorAction SilentlyContinue
if (-not $gitCmd) {
    if (Prompt-User "برنامج Git مو موجود بجهازك، وهو ضروري لسحب وتحديث ملفات المشروع من GitHub. تريد نثبّته هسه تلقائياً؟") {
        Write-Host "  [*] جاري تثبيت Git عبر WinGet..." -ForegroundColor Cyan
        & winget install --id Git.Git -e --source winget --accept-source-agreements --accept-package-agreements
        Refresh-ProcessEnv
        $gitCmd = Get-Command "git" -ErrorAction SilentlyContinue
        if (-not $gitCmd) {
            throw "تم تثبيت Git ولكن يتطلب إعادة فتح نافذة التيرمنال للتعرف عليه."
        }
        Write-Host "  [تم / OK] تم تثبيت Git بنجاح!" -ForegroundColor Green
    } else {
        throw "تم إيقاف التثبيت: برنامج Git إلزامي لمتابعة سحب المشروع."
    }
} else {
    Write-Host "  [تم / OK] برنامج Git متوفر مسبقاً: $((& git --version))" -ForegroundColor Green
}

# فحص Python 3.12
$pyFound = $false
$pyCheck = Get-Command "py" -ErrorAction SilentlyContinue
if ($pyCheck) {
    $v = & py -3.12 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
    if ($v -and $v.Trim() -eq "3.12") { $pyFound = $true }
}
if (-not $pyFound) {
    $sysPy = Get-Command "python" -ErrorAction SilentlyContinue
    if ($sysPy) {
        $v = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($v -and $v.Trim() -eq "3.12") { $pyFound = $true }
    }
}
if (-not $pyFound) {
    $stdPaths = @("$env:LOCALAPPDATA\Programs\Python\Python312\python.exe", "C:\Program Files\Python312\python.exe")
    foreach ($p in $stdPaths) {
        if (Test-Path $p) { $pyFound = $true; break }
    }
}

if (-not $pyFound) {
    if (Prompt-User "بايثون الإصدار 3.12 (Python 3.12) مو موجود بجهازك، والمشروع يحتاجه حصراً لتشغيل نماذج الذكاء الاصطناعي. تريد نثبّته هسه تلقائياً؟") {
        Write-Host "  [*] جاري تثبيت Python 3.12 عبر WinGet..." -ForegroundColor Cyan
        & winget install --id Python.Python.3.12 -e --source winget --accept-source-agreements --accept-package-agreements
        Refresh-ProcessEnv
        Write-Host "  [تم / OK] تم تثبيت Python 3.12 بنجاح!" -ForegroundColor Green
    } else {
        throw "تم إيقاف التثبيت: Python 3.12 إلزامي لتشغيل AMAV."
    }
} else {
    Write-Host "  [تم / OK] مفسر Python 3.12 متوفر وجاهز." -ForegroundColor Green
}

# فحص Ollama
$ollamaCmd = Get-Command "ollama" -ErrorAction SilentlyContinue
$ollamaPaths = @(
    "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
    "C:\Program Files\Ollama\ollama.exe"
)
$hasOllama = ($null -ne $ollamaCmd)
if (-not $hasOllama) {
    foreach ($op in $ollamaPaths) {
        if (Test-Path $op) { $hasOllama = $true; break }
    }
}
if (-not $hasOllama) {
    if (Prompt-User "محرك Ollama مو موجود بجهازك، وهو المحرك اللي يشغل نموذج الرؤية Qwen3-VL محلياً بدون إنترنت. تريد نثبّته هسه؟") {
        Write-Host "  [*] جاري تثبيت Ollama عبر WinGet..." -ForegroundColor Cyan
        & winget install --id Ollama.Ollama -e --source winget --accept-source-agreements --accept-package-agreements
        Refresh-ProcessEnv
        Write-Host "  [تم / OK] تم تثبيت Ollama بنجاح!" -ForegroundColor Green
    } else {
        Write-Host "  [تنبيه] تم تخطي تثبيت Ollama. يمكنك تثبيته لاحقاً من https://ollama.com" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [تم / OK] محرك Ollama متوفر مسبقاً." -ForegroundColor Green
}

# [3/8] تنزيل واستنساخ المشروع في C:\AMAV
Write-Host ""
Write-Host "[3/8] تنزيل ملفات مشروع AMAV من GitHub في C:\AMAV..." -ForegroundColor Cyan
$installDir = "C:\AMAV"
if (Test-Path $installDir) {
    if (Test-Path (Join-Path $installDir ".git")) {
        Write-Host "  [تم / OK] مجلد AMAV موجود مسبقاً في C:\AMAV." -ForegroundColor Green
        Set-Location $installDir
        $localChanges = (& git status --porcelain 2>$null)
        if ($localChanges) {
            Write-Host "  [تنبيه] توجد تعديلات محلية في المجلد C:\AMAV. لن يتم التحديث التلقائي حفاظاً على عملك." -ForegroundColor Yellow
        } else {
            if (Prompt-User "المجلد C:\AMAV موجود مسبقاً ومطابق للمستودع. هل تريد تحديثه عبر git pull لآخر إصدار؟") {
                Write-Host "  [*] جاري تحديث الملفات عبر git pull..." -ForegroundColor Cyan
                try { & git pull } catch { Write-Host "  [تنبيه] تعذر التحديث عبر git pull، سيتم الاستمرار بالملفات الموجودة." -ForegroundColor Yellow }
            } else {
                Write-Host "  [ملاحظة] تم تخطي التحديث والاستمرار بالملفات الحالية." -ForegroundColor DarkGray
            }
        }
    } else {
        throw "المجلد C:\AMAV موجود مسبقاً ولكن لا يحتوي على مستودع AMAV! لحماية ملفاتك، تم إيقاف العملية. يرجى إفراغ المجلد أو اختيار مسار آخر."
    }
} else {
    Write-Host "  [*] استنساخ المستودع من GitHub إلى C:\AMAV..." -ForegroundColor Cyan
    & git clone https://github.com/xdc7-css/dr.assraa.git $installDir
    Set-Location $installDir
    Write-Host "  [تم / OK] تم تنزيل مشروع AMAV بنجاح في C:\AMAV." -ForegroundColor Green
}

# [4/8 إلى 8/8] تشغيل سكربت الإعداد الشامل
Write-Host ""
Write-Host "الانتقال إلى مراحل الإعداد الداخلي والنماذج..." -ForegroundColor Cyan
$setupScript = Join-Path $installDir "scripts\setup_windows.ps1"
if (-not (Test-Path $setupScript)) {
    throw "لم يتم العثور على سكربت الإعداد: $setupScript"
}

powershell.exe -NoProfile -ExecutionPolicy Bypass -File $setupScript
```

---

### 📋 متطلبات النظام والعتاد (System Requirements)

| المكوّن | الحد الأدنى | المواصفات المستحسنة | ملاحظات فنية |
| :--- | :--- | :--- | :--- |
| **نظام التشغيل** | Windows 10 (64-bit) | Windows 11 (64-bit) | مدعوم بنظام ملفات NTFS |
| **المعالج (CPU)** | Intel Core i5 / AMD Ryzen 5 | Intel Core i7-10750H أو أحدث | للاستدلال السريع لنماذج الصوت والنصوص |
| **الذاكرة (RAM)** | 8 GB | 16 GB DDR4/DDR5 | لتشغيل البيئة الافتراضية والذاكرة المؤقتة |
| **كرت الشاشة (GPU)** | كرت مدمج أو منفصل | NVIDIA GTX 1650 Ti (4GB VRAM) فما فوق | يدعم تسريع CUDA مع استهلاك ~1.9 GB VRAM فقط |
| **مساحة التخزين** | 8 GB فارغة (حد أدنى) | 12 إلى 15 GB فارغة | للبيئة الافتراضية (~1.5GB)، والنماذج الأوفلاين (~2.7GB)، وكاش التنزيل (~3.5GB) |
| **مفسر بايثون** | **Python 3.12** حصراً | **Python 3.12.x** (64-bit) | *إلزامي:* لضمان توافق مكتبات PyTorch و CTranslate2 و OnnxRuntime |
| **أداة Git** | Git for Windows | أحدث إصدار من Git | ضروري لعملية الاستنساخ والتحديث |
| **محرك Ollama** | Ollama for Windows | أحدث إصدار محلي | يقوم سكربت التثبيت بفحصه وتثبيته تلقائياً |
| **Node.js / NPM** | *غير مطلوب* | Node.js 18+ (اختياري) | حزم الواجهة الأمامية React مبنية مسبقاً في `app/static/assets` |

---

### 🎛️ الخيارات التشغيلية للذكاء الاصطناعي (Operating AI Modes)

يوفر المشروع خيارين للتشغيل، الخيار الأول هو النواة الأساسية والافتراضية للمشروع:

#### 1. النمط الأساسي والافتراضي: نظام محلي بالكامل 100% أوفلاين (Local Full Offline AI)
- **لا يتطلب إنترنت أو اشتراكات:** كافة نماذج الذكاء الاصطناعي تعمل محلياً داخل الحاسوب.
- **نموذج الرؤية واللغة (VLM):** `Qwen3-VL-2B-Instruct` عبر محرك Ollama (`qwen3-vl:2b-instruct-q4_K_M`) مستهلكاً ~1.9 GB VRAM.
- **التعرف الآلي على الكلام (ASR):** `Faster-Whisper Base` محلياً لتفريغ أوامر المستخدم الصوتية.
- **كشف الكائنات والمواقع (Detection):** `YOLO11n` محلياً مع تصنيف الاتجاهات (يمين/وسط/يسار).
- **التعرف الضوئي على النصوص (OCR):** `EasyOCR` محلياً للغتين العربية والإنجليزية.
- **توليد النطق الصوتي (TTS):** `Piper TTS` محلياً بصوت كريم العربي الطبيعي (`ar_JO-kareem-medium`).
- **أعلى درجات الخصوصية:** لا تُرفع أي صورة أو تسجيل صوتي خارج الجهاز نهائياً.

#### 2. النمط الاختياري الإضافي: النطق الصوتي باللهجة العراقية عبر السحابة (Optional Cloud Azure Speech)
- ميزة إضافية مخصصة **للصوت فقط** لمن يمتلك مفتاح Azure Speech ويرغب بتفعيل صوت طبيعي فائق الجودة باللهجة العراقية (`ar-IQ-BasselNeural`).
- يتم تفعيله ببساطة عبر إنشاء ملف `.env` ووضع المفتاح:
  ```env
  AZURE_SPEECH_KEY="your_azure_speech_key_here"
  AZURE_SPEECH_REGION="eastus"
  ```
- **تنبيه أكاديمي صريح ومهم:** لا يوجد نموذج VLM سحابي متاح أو مدعوم حالياً في المشروع؛ نموذج الرؤية والاستدلال البصري يعمل دائماً ومحصوراً محلياً عبر `Qwen3-VL 2B` على جهاز المستخدم لضمان سرعة الاستجابة والخصوصية.

---

### 🚀 كيفية تشغيل النظام وإيقافه (Daily Usage)

بعد انتهاء سكربت التثبيت بنجاح:

1. **تشغيل النظام بأمر واحد:**
   ```powershell
   cd C:\AMAV
   python run
   ```
   *(أو عبر المسار المباشر للبيئة: `.\.venv\Scripts\python.exe run`)*

2. **الواجهة التفاعلية للمستخدم:**
   يقوم المشغل الذكي بفحص توفر المنفذ وخدمة Ollama، ثم يفتح المتصفح الافتراضي تلقائياً على الرابط:  
   👉 **`http://127.0.0.1:8000`**

3. **إيقاف النظام بأمان:**
   لإيقاف الخادم وكافة العمليات التابعة، اضغط اختصار **`Ctrl + C`** داخل نافذة الطرفية، ليقوم النظام بإيقاف العمليات وتحرير الموارد والذاكرة بأمان تام.

---

### 🔧 دليل حل المشكلات الشائعة (Troubleshooting & FAQs)

* **مشكلة تصاريح تشغيل السكربتات (Execution Policy Error):**  
  إذا ظهرت رسالة خطأ تمنع تشغيل ملفات `.ps1` في PowerShell، قم بتمكين تشغيل السكربتات للمستخدم الحالي بالأمر:
  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
  ```
  أو شغل السكربت متجاوزاً السياسة:
  ```powershell
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\setup_windows.ps1"
  ```

* **مشكلة خدمة Ollama أو المنفذ 11434:**  
  إذا لم يستجب محرك Ollama، تأكد من تشغيل تطبيق Ollama أو تشغيل الأمر `ollama serve` في نافذة مستقلة، وتحقق من عدم حجب المنفذ `11434` بواسطة برامج الحماية.

* **مشكلة تعارض منفذ الواجهة 8000:**  
  إذا كان المنفذ `8000` مشغولاً بتطبيق آخر، سيقوم مشغل `python run` بإعلامك فوراً. إذا كان الخادم الحالي هو خادم AMAV نفسه، سيقوم المشغل بفتح المتصفح مباشرة دون تكرار تشغيل الخادم.

* **إدارة ذاكرة كرت الشاشة (CUDA Out of Memory):**  
  تم ضبط المشروع افتراضياً على البروفايل الخفيف (`low_memory`) للعمل باستقرار على كروت الشاشة بذاكرة 4GB VRAM (مثل GTX 1650 Ti). إذا واجهت بطئاً أو كنت تستخدم جهازاً بدون كرت NVIDIA منفصل، سيعمل النظام تلقائياً عبر المعالج المركزي (CPU).

---

### 🔄 تحديث المشروع لاحقاً (Updating an Existing Installation)

لتحديث الكود المصدري لآخر إصدار من المستودع مستقبلاً:
```powershell
cd C:\AMAV
git pull
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
python run
```

---

## 🚀 التشغيل السريع اليدوي (Manual Quick Start)

### 1. المتطلبات الأساسية:
- نظام تشغيل: **Windows 10 / 11** (أو Linux).
- بطاقة رسوميات: **NVIDIA GPU** تدعم CUDA (مثل GTX 1650 Ti 4GB VRAM أو أحدث).
- **Python 3.12** مثبت ومفعل داخل بيئة افتراضية `.venv`.
- **Node.js** (v18+) لبناء واجهة React عند الحاجة.
- **Ollama** مثبت محلياً مع نموذج `qwen3-vl:2b-instruct-q4_K_M`.

### 2. التثبيت اليدوي التقليدي (كخيار بديل):
إذا واجهتك أي مشكلة في التثبيت التلقائي وأردت تثبيت المشروع خطوة بخطوة يدوياً:
```powershell
# 1. استنساخ المستودع والدخول للمجلد
git clone https://github.com/xdc7-css/dr.assraa.git C:\AMAV
cd C:\AMAV

# 2. إنشاء البيئة الافتراضية المستقلة وتثبيت المكتبات
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# 3. تنزيل نماذج الذكاء الاصطناعي الأوفلاين
python -m scripts.download_models --profile low_memory

# 4. تشغيل النظام
python run
```

### 3. إطلاق التطبيق بأمر واحد (Standard Launch):
يمكن إطلاق التطبيق وسيرفر النماذج بالكامل بأمر واحد فقط:
```powershell
cd C:\AMAV   # (أو مجلد المشروع)
python run
```
أو:
```powershell
python run.py
```
*(أو عبر السكربتات المساعدة: `.\run_app.ps1` أو `run_app.bat`)*

**ما يقوم به مشغل `python run` تلقائياً:**
1. يتحقق من البيئة الافتراضية `.venv` ويعيد توجيه التنفيذ إليها ذاتياً.
2. يتأكد من تشغيل خدمة Ollama المحلية على المنفذ `11434` وجاهزية نموذج Qwen3-VL 2B.
3. يكتشف أي تعارض في المنافذ ويمنع تكرار فتح خوادم متعددة.
4. يشغّل خادم FastAPI ومحركات الذكاء الاصطناعي باستقرار كامل داخل العملية الرئيسية.
5. يفتح واجهة الويب تلقائياً في المتصفح الافتراضي على الرابط:  
   👉 **`http://127.0.0.1:8000`**
6. يظل قيد العمل حتى يضغط المستخدم `Ctrl+C`، حيث يقوم بإيقاف العمليات التابعة بأمان.

---

## ✨ الترقيات والميزات المعتمدة (Graduation Upgrades)

### 1. الإرشاد الذكي لجودة الصورة (Smart Image-Quality Guidance):
- **فحص سريع قبل النماذج الثقيلة:** فحص فوري خلال **~4.7 مللي ثانية**.
- **كشف حالات الإضاءة والتشويش:**
  - إضاءة خافتة: *«الإضاءة قليلة، جرّب مكان أضوى.»*
  - إضاءة ساطعة/وهج: *«الإضاءة ساطعة جداً، عدّل زاوية الكاميرا.»*
  - اهتزاز وضبابية: *«ثبّت الكاميرا لحظة.»*
  - إطار فارغ أو انقطاع الكاميرا: *«الكاميرا غير متصلة أو الإطار فارغ.»*
- **إرشاد موضعة المستندات (OCR):** توجيه المستخدم لتقريب الورقة أو تعديل الزاوية (*«قرّب الورقة شوي»*).
- **كبح التحذيرات المكررة والتجاوز اليدوي:** مؤقت زمني لعدم إزعاج المستخدم، مع زر لتجاوز الفحص (*تجاهل التحذير واستمر*).

### 2. جلسة البحث المستمر عن الأغراض (Continuous Object Search):
- تحويل أمر «ابحث عن غرض» إلى جلسة تفاعلية متصلة قابلة للإلغاء.
- **تحديث اتجاهات الكائن بصرياً:** تحديد الاتجاه بالنسبة للمستخدم (*«يمين الصورة»*، *«وسط الصورة»*، *«يسار الصورة»*).
- **إعلان الاختفاء عند الثبات:** إذا غاب الكائن لمدة إطارين متتاليين يعلن النظام: *«هسه ما أشوفها.»*
- **قاموس مرادفات اللهجة العراقية:** دعم مسميات مثل:
  - `بطل`، `دولكة`، `ماي` -> قنينة (Bottle).
  - `قنفة`، `تخم` -> أريكة (Couch).
  - `استكان`، `قلاص` -> كوب (Cup).
  - `شاشة` -> تلفزيون (TV).
  - `حاسبة`، `لابتوب` -> حاسوب (Laptop).
  - `بزونة` -> قطة (Cat).
- **شرح الأغراض غير المدعومة بأمان:** توضيح عدم قدرة النموذج على كشف عناصر الحركة كالأبواب والأدراج دون ادعاء صلاحيته للتوجيه الحركي الحرج.

### 3. سياق المحادثة القصير والذاكرة المؤقتة (Short Conversational Context):
- ذاكرة جلسة مؤقتة في الرام (5 دقائق صلاحية) تحفظ آخر استجابة، آخر كائن، ومهمة المستخدم.
- **التكرار الفوري دون إعادة استدلال:** أمر «كرر» أو «عيد الجواب» يعيد القراءة الصوتية للنص السابق فوراً دون تشغيل الكاميرا أو النماذج.
- **اختصار الجواب:** أمر «اختصر الجواب» يكثّف الإجابة دون اختلاق حقائق جديدة.
- **حل الضمائر:** مثل «وينها؟» تشير تلقائياً لآخر كائن تم الاستفسار عنه.
- **مسح الذاكرة:** أمر «امسح الذاكرة» يفرغ السياق مباشرة لضمان الخصوصية.

### 4. الوضع المزدوج للرؤية واللغة (Fast 2B vs Detailed 4B):
- **الوضع الافتراضي السريع (Fast - 2B):**
  - نموذج `qwen3-vl:2b-instruct-q4_K_M` محلي 100% داخل ذاكرة كارت الشاشة (GPU VRAM ~1.9 GB).
  - استجابة سريعة وتدفق فوري مناسب للتفاعل الصوتي الحي.
- **الوضع المفصّل الاختياري (Detailed - 4B):**
  - نموذج `qwen3-vl:4b-instruct-q4_K_M` بحجم 3.3 GB.
  - يعمل مع تفريغ الذاكرة التلقائي وإدارة الحصص بين كرت الشاشة وذاكرة النظام.

### 5. إمكانية الوصول ولوحة قياس الأداء (Accessibility & Performance Telemetry):
- نغمات Web Audio API محلية خفيفة عند بدء الاستماع ونهايته وتأكيد كشف الكائنات.
- أزرار التحكم بسرعة النطق (0.75x، 1.0x، 1.25x، 1.5x) متوافقة مع محرك Piper TTS.
- تحكم كامل بلوحة المفاتيح: `Esc` للإلغاء الفوري وتفريغ قوائم النطق، `Space` للمايكروفون، `R` للتكرار، `S` للاختصار.
- واجهة تباين فائق (High Contrast Mode) مع تركيز مرئي واضح لقارئات الشاشة.
- **لوحة مراقبة الأداء (Performance Monitor):** يمكن تفعيلها بضغط `Alt+P` أو `Ctrl+Shift+D` أو عبر الرابط `?dev=true` لعرض القياسات اللحظية لـ TTFT وزمن أول صوت وأوقات النماذج الفردية.

---

## 📊 نتائج التقييم الشامل (Evaluation Benchmark)

تم قياس الأداء عبر سكربت الاختبار المطور `python scripts/evaluate.py --save-report`:

| المحور القياسي (Benchmark) | النتيجة المحققة | الحالة |
| :--- | :--- | :--- |
| **توجيه النوايا واللهجة العراقية** | **96.3%** (26/27 تجربة) | **PASS** |
| **معدل الرفض الخاطئ لجودة الصورة** | **0.0%** (الهدف: أقل من 5%) | **PASS** |
| **كشف الإطارات غير الصالحة** | **100.0%** (خافت، ساطع، فارغ) | **PASS** |
| **زمن استجابة فحص الجودة** | **4.69 مللي ثانية** (Median) | **PASS** |
| **معدل خطأ قراءة النصوص (OCR CER)** | **3.28%** (عربي/إنجليزي) | **PASS** |
| **التحقق من أرقام المستندات** | **100%** (204, 2026, 5000) | **PASS** |
| **كشف وتحديد مواقع الأغراض (YOLO)** | **65.59 مللي ثانية** (Median) | **PASS** |
| **جلسة البحث المستمر وإعلان الفقد** | انتقال دقيق وإعلان «هسه ما أشوفها» | **PASS** |
| **زمن استجابة النموذج السريع (2B VLM)** | تدفق لحظي وتوليد فوري للرموز الأولى | **PASS** |
| **العمل بدون إنترنت (100% Offline)** | محلي بالكامل على قرص X: | **PASS** |

---

## 📂 هيكل المشروع المعتمد (Project Directory Tree)

هيكل المجلدات والملفات الفعلي لمشروع AMAV، مصحوباً بوصف مختصر لدور كل ملف ومكوّن:

```text
asraa-project/
├── app/                                        # الحزمة البرمجية الرئيسية لخادم التطبيق الخلفي
│   ├── main.py                                 # خادم FastAPI، مسارات API، ونقاط النهاية والتدفق
│   ├── orchestrator.py                         # المنسق العام لتوجيه النوايا، إدارة النماذج، والذاكرة
│   ├── quality_analyzer.py                     # محلل جودة الصورة وإرشاد موضعة المستندات والتباين
│   ├── schemas.py                              # نماذج البيانات والتحقق من صحة الطلبات (Pydantic)
│   ├── config.py                               # الإعدادات العامة ومسارات النماذج والبيئة التشغيلية
│   ├── adapters/                               # محولات التكامل مع نماذج الذكاء الاصطناعي المحلية
│   │   ├── asr_adapter.py                      # محول التعرف الآلي على الكلام (faster-whisper)
│   │   ├── detection_adapter.py                # محول كشف الكائنات والبحث المستمر (YOLO11n)
│   │   ├── ocr_adapter.py                      # محول قراءة النصوص الضوئية ثنائية اللغة (EasyOCR)
│   │   ├── tts_adapter.py                      # محول توليد النطق الصوتي العربي الفوري (Piper TTS)
│   │   └── vlm_adapter.py                      # محول نموذج الرؤية واللغة والتدفق (Qwen3-VL 2B)
│   └── static/                                 # الأصول الثابتة المجمعة لخدمة الواجهة في بيئة الإنتاج
│       ├── index.html                          # صفحة الويب الرئيسية للمستخدم
│       ├── project_identity.js                 # بيانات الهوية الأكاديمية وأسماء الطالبات
│       ├── assets/                             # حزم جافاسكربت وCSS المبنية لإنتاج الواجهة (Vite)
│       └── fonts/                              # خطوط IBM Plex Sans Arabic المضمنة محلياً ورخصتها
├── frontend/                                   # الكود المصدري للواجهة الأمامية (React + TypeScript)
│   ├── src/                                    # مجلد كود المكونات ومنطق التفاعل الصوتي والبصري
│   │   ├── App.tsx                             # المكون الجذري لإدارة دورة حياة التطبيق والأحداث
│   │   ├── App.css                             # الأنماط والتصميم ووضع التباين العالي (High Contrast)
│   │   ├── main.tsx                            # نقطة انطلاق تطبيق React وربط شجرة العناصر بالصفحة
│   │   ├── components/                         # عناصر واجهة المستخدم المستقلة
│   │   │   ├── AboutModal.tsx                  # نافذة التعريف الأكاديمي بالمشروع وأسماء الفريق
│   │   │   ├── CameraWorkspace.tsx             # مساحة معاينة الكاميرا وتراكب صناديق الكشف
│   │   │   ├── Header.tsx                      # شريط الترويسة وأزرار التحكم بالتباين واللغة
│   │   │   ├── InteractionPanel.tsx            # لوحة التفاعل بالأزرار الكبيرة والمايكروفون
│   │   │   ├── PerformanceMonitor.tsx          # لوحة قياس الأداء الحية وتوقيتات TTFT للمطورين
│   │   │   ├── ResponseCard.tsx                # بطاقة عرض الإجابات المقروءة والتحكم الصوتي
│   │   │   └── SupervisorDrawer.tsx            # درج الإشراف الأكاديمي لعرض حالة النماذج المباشرة
│   │   ├── config/                             # ملفات التكوين والهوية
│   │   │   └── identity.ts                     # الهوية الأكاديمية الرسمية وأسماء الطالبات
│   │   ├── types/                              # تعريفات الأنواع البرمجية (TypeScript Interfaces)
│   │   │   └── index.ts                        # تعريفات نماذج الطلبات وحالات الاستجابة والقياسات
│   │   └── utils/                              # الدوال المساعدة
│   │       └── audioCues.ts                    # النغمات والمؤشرات الصوتية التفاعلية (Web Audio)
│   ├── public/                                 # الملفات العامة وأيقونات التبويب
│   └── package.json                            # تعريف حزم ومكتبات الواجهة الأمامية (NPM)
├── data/                                       # البيانات المعيارية، القواميس، وعينات الفحص
│   ├── dialects/                               # قواميس اللهجات المحلية
│   │   └── iraqi_synonyms.json                 # قاموس مرادفات اللهجة العراقية لكشف الكائنات
│   ├── fixtures/                               # عينات صور معيارية خفيفة للاختبار والتكامل
│   │   ├── arabic_heldout_notice.jpg           # عينة مستند إعلاني عربي لاختبار القراءة
│   │   ├── arabic_printed_notice.jpg           # عينة لافتة مطبوعة للتحقق من أداء OCR
│   │   ├── scene_objects.jpg                   # عينة مشهد عناصر متنوعة لاختبار YOLO و VLM
│   │   └── fixtures_ground_truth.json          # الحقيقة الأرضية المعيارية للتحقق من النتائج
│   └── eval_results.json                       # السجل الرقمي الموثق لنتائج التقييم الشامل
├── docs/                                       # التوثيق الأكاديمي والبروتوكولات الفنية
│   ├── ARCHITECTURE.md                         # التوثيق التفصيلي لبنية الأنظمة وتدفق البيانات
│   ├── EVALUATION.md                           # منهجية التقييم والقياسات المعيارية
│   ├── BEFORE_AFTER_REPORT.md                  # تقرير المقارنة قبل وبعد تحسينات المشروع
│   ├── iraqi_arabic_protocol.md                # بروتوكول جمع بيانات الكلام العراقي والموافقة
│   └── THIRD_PARTY_NOTICES.md                  # إشعارات وتراخيص البرمجيات والمكتبات المستخدمة
├── scripts/                                    # سكربتات التشغيل والتقييم والاختبارات المساعدة
│   ├── setup_windows.ps1                       # سكربت الإعداد والتثبيت الآلي الشامل لأجهزة ويندوز الجديدة (أمر واحد)
│   ├── check_system.py                         # فحص مواصفات الجهاز والعتاد وتوفر CUDA
│   ├── evaluate.py                             # سكربت التقييم والقياس المعياري الشامل للمشروع
│   ├── generate_fixtures.py                    # توليد وتجهيز عينات الاختبار الموزونة
│   ├── download_models.py                      # تنزيل وفحص اكتمال النماذج المحلية عند الحاجة
│   ├── run_ollama_service.py                   # التحقق من خدمة Ollama وتشغيلها محلياً
│   ├── benchmark_performance.py                # قياس أزمنة الاستدلال والتدفق والـ TTFT
│   ├── run_optimization_benchmark.py           # اختبار ومقارنة استجابة التدفق ومحرك النطق
│   └── custom_detector/                        # خط أنابيب تدريب كاشف الكائنات المخصص المقترح
│       ├── candidate_classes.json              # الفئات المقترحة للمكفوفين (أبواب، أدراج، ممرات)
│       ├── dataset_validator.py                # التحقق من سلامة تنسيق بيانات تدريب YOLO
│       ├── evaluate_custom_yolo.py             # تقييم دقة الكاشف المخصص على العينات
│       └── train_custom_yolo.py                # سكربت بدء تدريب كاشف الكائنات المساعد
├── tests/                                      # حزمة الاختبارات الآلية (Pytest)
│   ├── conftest.py                             # إعداد بيئة الاختبارات وحقن المنسق العام
│   ├── test_orchestrator.py                    # اختبارات تكامل المنسق وتوجيه النوايا والاستدلال
│   └── test_upgrades.py                        # اختبارات الميزات المطورة (الجودة، البحث، الذاكرة)
├── models_manifest.json                        # وثيقة البصمات والإصدارات الرسمية للنماذج
├── requirements.txt                            # متطلبات ومكتبات بايثون المعتمدة للبيئة الافتراضية
├── run                                         # مشغل النظام المباشر بالأمر: python run
├── run.py                                      # مشغل النظام البديل بالأمر: python run.py
├── run_app.ps1                                 # سكربت إطلاق PowerShell البديل
├── run_app.bat                                 # سكربت إطلاق Windows Batch البديل
├── FINAL_AMAV_PERFORMANCE_VERIFICATION.md      # تقرير التحقق النهائي من الأداء والتدفق اللحظي
├── PERFORMANCE_DIAGNOSTIC_REPORT.md            # تقرير التشخيص وحل مشكلات زمن الاستجابة
└── README.md                                   # الدليل الشامل والموثق للمشروع
```

> **ملاحظة حول المجلدات المستبعدة من شجرة الكود:**  
> تم استبعاد المجلدات المؤقتة والضخمة بطبيعتها من التتبع والعرض (مثل `.venv/` للبيئة الافتراضية، و `models/` لأوزان النماذج والملفات الثنائية الضخمة، و `node_modules/` لحزم NPM، و `scratch/` للملفات التجريبية، و `.git/` لإدارة النسخ)، حيث تُدار هذه المجلدات محلياً طبقاً لقواعد ملف `.gitignore`.

---

## 🛡️ الخصوصية والأمان (Privacy & Ethics)

النظام مصمم خصيصاً لمراعاة أعلى معايير الخصوصية للمكفوفين وضعاف البصر:
- لا تُحفظ الصور أو التسجيلات الصوتية دون إذن صريح.
- لا يتم الاتصال بأي خوادم سحابية مدفوعة أو خارجية نهائياً.
- كافة العمليات تتم محلياً 100% داخل حاسوب المستخدم على مسار المشروع المستنسخ (دون أي اعتماد على خوادم خارجية).
- **تنبيه صريح:** النظام مساعد بصري وإرشادي للتعرف على البيئة وقراءة النصوص، وليس بديلاً عن العصا البيضاء أو كلب التوجيه ولا يُعتمد للملاحة الحركية الحرجة.

---

**إعداد الطالبات:**  
1. **نور عباس عبد الحسين** — 2. **نور رمزي صبيح قاسم** — 3. **غدير علاء كامل حسين**  
**بإشراف:** **م.د. اسراء حبيب**  
**جامعة البصرة — كلية الهندسة — قسم هندسة الحاسوب (2026 - 2027)**
