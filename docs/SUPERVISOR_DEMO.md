# AMAV — Supervisor Demonstration & Academic Defense Guide

**Project:** Arabic Multimodal Assistive Vision (AMAV)  
**Target:** Live demonstration during project review and academic viva  
**Local URL:** `http://localhost:8000`  
**Audio Comparison URL:** `http://localhost:8000/static/audio_comparison.html`

---

## 1. Quick Startup Procedure

Open PowerShell on the host machine and execute:

```powershell
Set-Location "X:\asraa project"
.\run_app.ps1
```

Or double-click:
`X:\asraa project\run_app.bat`

This will automatically:
1. Verify the Python virtual environment at `X:\asraa project\.venv`.
2. Set `OLLAMA_MODELS="X:\asraa project\models\ollama"`.
3. Verify that the local Ollama service is listening on `127.0.0.1:11434`.
4. Run system diagnostics.
5. Launch Uvicorn on `http://127.0.0.1:8000`.

---

## 2. Recommended Demonstration Flow (Step-by-Step)

### Step 1: Camera Preview & Mirroring Verification
1. Click **"تشغيل الكاميرا (C)"** or press `C`.
2. Move a hand or object (e.g. water bottle or cup) in front of the lens.
3. Check the checkbox **"إظهار مربعات الكشف"** to display real-time YOLO11n bounding boxes and labels in Arabic.

### Step 2: Voice Interaction & Iraqi Dialect Understanding
1. Hold down the **Space** key or click the central microphone button.
2. Speak in Iraqi dialect or Modern Standard Arabic:
   - *"شنو قدامي؟"* (Describe mode)
   - *"وين القنينة؟"* (Find mode)
   - *"اقرأ المكتوب"* (Read mode)
3. Release the button or press Space again to finish recording.
4. Observe the state indicator transitioning from **"جاري الاستماع"** to **"جاري تحليل المشهد"** to **"المساعد يتحدث"**.
5. Listen to the generated Piper speech output (`length_scale 1.05`).

### Step 3: Pure Arabic Vision-Language Description (Zero Thinking Leakage)
1. Point camera at a desk scene or use the file upload option with `data/fixtures/scene_objects.jpg`.
2. Click **"صف المشهد (D)"** or press `D`.
3. Notice that the answer is concise, grounded Modern Standard Arabic:
   *"الصورة تُظهر مكتبًا بسيطًا يحتوي على: لابتوب مفتوح، كوب أبيض، وزجاجة مياه."*
4. Confirm there is **ZERO** internal reasoning or English analytical text (*"Wait, the user..."*).

### Step 4: Text Reading (OCR) on Printed Notice
1. Point camera at printed text or upload `data/fixtures/arabic_printed_notice.jpg`.
2. Click **"اقرأ النص (R)"** or press `R`.
3. Observe literal text recognition preserving logical Unicode Arabic and English text (*"جمهورية العراق - وزارة التعليم العالي / قسم هندسة الحاسوب / ROOM 204"*).

### Step 5: Object Localization with Directional Guidance
1. Click **"أين الكائن؟ (F)"** or press `F`.
2. When prompted, type *"قنينة"* or *"لابتوب"*.
3. Notice the relative positional answer:
   *"تم رصد قنينة على اليسار أمام الكاميرا."*

### Step 6: Unsupported Object Handling
1. Ask for an object outside COCO80 (e.g., *"وين الباب؟"*).
2. Observe the honest, calibrated response:
   *"الأبواب ليست ضمن فئات كشف الكائنات المدعومة حالياً (COCO80)، وتتطلب نموذجاً مخصصاً."*

### Step 7: Emergency Stop & Repeat
1. While the assistant is speaking, press **Esc** or click **"إيقاف فوري (Esc)"**. Audio stops immediately.
2. Click **"كرر الجواب (A)"** or press `A`. The previous answer is replayed instantly from memory cache without running models again.

### Step 8: Supervisor Diagnostics & Exact Frame Inspector
1. Expand the bottom panel: **"لوحة التشخيص الهندسي وحالة النماذج"**.
2. Inspect:
   - **VLM Model:** `qwen3-vl:2b-instruct-q4_K_M`
   - **Digest:** `afc393e3572c07db0bc84aa460d928a16c75f3fbb9ca9e0dccc4fbd2dafb573e`
   - **Exact Analyzed Frame:** Displays the exact image analyzed for the latest request, including timestamp and request ID.
   - **Timing breakdown:** ASR, VLM, OCR, Detection, and TTS latencies.

---

## 3. Audio Pace & Quality Comparison Page
Navigate to: `http://localhost:8000/static/audio_comparison.html`
Demonstrates 15 pre-generated audio files comparing pace settings (`1.00x`, `1.05x`, `1.10x`) across spatial directions, numbers, everyday objects, mixed script, and continuous paragraphs.
