/**
 * AMAV — Arabic Multimodal Assistive Vision
 * Client Application Logic: Restrained Academic Design, Accessible, Offline-Edge
 */

// Application State
const state = {
  cameraActive: false,
  stream: null,
  mediaRecorder: null,
  audioChunks: [],
  isRecording: false,
  isPlayingAudio: false,
  currentRequestId: null,
  history: [],
  maxHistory: 5,
};

// DOM Elements
const video = document.getElementById('camera-stream');
const canvas = document.getElementById('detection-canvas');
const ctx = canvas ? canvas.getContext('2d') : null;
const cameraPlaceholder = document.getElementById('camera-placeholder');
const cameraSelect = document.getElementById('camera-select');
const btnCamera = document.getElementById('btn-camera');
const chkOverlay = document.getElementById('chk-overlay');
const camStatusBadge = document.getElementById('cam-status-badge');

const btnPtt = document.getElementById('btn-ptt');
const lblPttTitle = document.getElementById('lbl-ptt-title');
const lblPttStatus = document.getElementById('lbl-ptt-status');

const btnDescribe = document.getElementById('btn-describe');
const btnRead = document.getElementById('btn-read');
const btnRepeat = document.getElementById('btn-repeat');
const btnStop = document.getElementById('btn-stop');

const searchObjectInput = document.getElementById('search-object-input');
const btnFind = document.getElementById('btn-find');

const statusRegion = document.getElementById('status-region');
const statusText = document.getElementById('status-text');
const answerBox = document.getElementById('answer-box');
const btnReplayAudio = document.getElementById('btn-replay-audio');
const btnCopyText = document.getElementById('btn-copy-text');
const lblCopy = document.getElementById('lbl-copy');
const audioPlayer = document.getElementById('audio-player');

// Supervisor Inspector Elements
const analyzedFrameImg = document.getElementById('analyzed-frame-img');
const analyzedFramePlaceholder = document.getElementById('analyzed-frame-placeholder');
const inspReqId = document.getElementById('insp-req-id');
const inspFrameId = document.getElementById('insp-frame-id');
const inspTimestamp = document.getElementById('insp-timestamp');
const inspQuality = document.getElementById('insp-quality');
const inspStages = document.getElementById('insp-stages');

const textQueryInput = document.getElementById('text-query-input');
const btnSendText = document.getElementById('btn-send-text');
const fileImageInput = document.getElementById('file-image-input');

const btnRefreshHealth = document.getElementById('btn-refresh-health');
const historyList = document.getElementById('history-list');
const btnThemeToggle = document.getElementById('btn-theme-toggle');
const lblTheme = document.getElementById('lbl-theme');

// About Modal Elements
const modalAbout = document.getElementById('modal-about');
const btnAboutModal = document.getElementById('btn-about-modal');
const btnCloseAbout = document.getElementById('btn-close-about');
const btnAboutOk = document.getElementById('btn-about-ok');

// ----------------------------------------------------
// UI State & Announcement Handling
// ----------------------------------------------------
function setStatus(type, message) {
  if (!statusRegion || !statusText) return;
  statusRegion.className = `status-strip status-${type}`;
  statusText.textContent = message;

  // Update primary button sub-text accordingly
  if (lblPttStatus) {
    if (type === 'listening') {
      lblPttStatus.textContent = 'أستمع إليك... تحدث بوضوح';
    } else if (type === 'processing') {
      lblPttStatus.textContent = 'أحلل الصورة والمشهد...';
    } else if (type === 'speaking') {
      lblPttStatus.textContent = 'أتحدث...';
    } else {
      lblPttStatus.textContent = 'جاهز للاستماع (المسافة)';
    }
  }
}

// ----------------------------------------------------
// 1. Camera Handling (Aspect Ratio Preserved)
// ----------------------------------------------------
async function listCameras() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoDevices = devices.filter(d => d.kind === 'videoinput');
    cameraSelect.innerHTML = '';
    videoDevices.forEach((dev, idx) => {
      const opt = document.createElement('option');
      opt.value = dev.deviceId;
      opt.text = dev.label || `الكاميرا ${idx + 1}`;
      cameraSelect.appendChild(opt);
    });
  } catch (err) {
    console.warn('Could not enumerate cameras:', err);
  }
}

async function startCamera() {
  stopAudioPlayback();
  const deviceId = cameraSelect.value ? { exact: cameraSelect.value } : undefined;
  try {
    state.stream = await navigator.mediaDevices.getUserMedia({
      video: { deviceId, width: { ideal: 1280 }, height: { ideal: 720 } }
    });
    video.srcObject = state.stream;
    video.style.display = 'block';
    if (cameraPlaceholder) cameraPlaceholder.style.display = 'none';
    state.cameraActive = true;
    
    btnCamera.classList.add('btn-cam-active');
    document.getElementById('lbl-camera').textContent = 'إيقاف الكاميرا (C)';
    btnCamera.setAttribute('aria-pressed', 'true');
    
    if (camStatusBadge) {
      camStatusBadge.textContent = 'الكاميرا نشطة';
      camStatusBadge.className = 'status-badge badge-on';
    }
    setStatus('ready', 'تم تشغيل الكاميرا بنجاح.');

    video.onloadedmetadata = () => {
      if (canvas) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
      }
    };
  } catch (err) {
    console.error('Camera access error:', err);
    setStatus('ready', 'تنبيه: تعذر فتح الكاميرا (' + err.message + '). يرجى التحقق من إذن المتصفح.');
  }
}

function stopCamera() {
  if (state.stream) {
    state.stream.getTracks().forEach(track => track.stop());
    state.stream = null;
  }
  video.style.display = 'none';
  if (cameraPlaceholder) cameraPlaceholder.style.display = 'flex';
  state.cameraActive = false;
  
  btnCamera.classList.remove('btn-cam-active');
  document.getElementById('lbl-camera').textContent = 'تشغيل الكاميرا (C)';
  btnCamera.setAttribute('aria-pressed', 'false');
  
  if (camStatusBadge) {
    camStatusBadge.textContent = 'الكاميرا متوقفة';
    camStatusBadge.className = 'status-badge badge-off';
  }
  clearCanvas();
  setStatus('ready', 'المساعد جاهز للاستخدام. اضغط «تحدث مع المساعد» أو مفتاح المسافة للبدء.');
}

btnCamera.addEventListener('click', () => {
  if (state.cameraActive) stopCamera();
  else startCamera();
});

function captureCurrentFrame() {
  if (!state.cameraActive) return null;
  const offCanvas = document.createElement('canvas');
  offCanvas.width = video.videoWidth || 640;
  offCanvas.height = video.videoHeight || 480;
  const offCtx = offCanvas.getContext('2d');
  offCtx.drawImage(video, 0, 0, offCanvas.width, offCanvas.height);
  return offCanvas.toDataURL('image/jpeg', 0.85);
}

function clearCanvas() {
  if (!canvas || !ctx) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
}

function drawDetections(detections) {
  clearCanvas();
  if (!chkOverlay.checked || !detections || !detections.length || !ctx) return;

  ctx.lineWidth = 3;
  ctx.font = 'bold 16px IBM Plex Sans Arabic, Cairo, sans-serif';

  detections.forEach(d => {
    const box = d.bbox;
    const w = box.x2 - box.x1;
    const h = box.y2 - box.y1;

    // Detection box
    ctx.strokeStyle = '#286D70';
    ctx.strokeRect(box.x1, box.y1, w, h);

    // Label background
    const label = `${d.class_name_ar} (${Math.round(d.confidence * 100)}%)`;
    const textWidth = ctx.measureText(label).width;
    ctx.fillStyle = 'rgba(20, 34, 52, 0.9)';
    ctx.fillRect(box.x1, Math.max(0, box.y1 - 26), textWidth + 14, 26);

    // Label text
    ctx.fillStyle = '#FFFFFF';
    ctx.fillText(label, box.x1 + 6, Math.max(18, box.y1 - 7));
  });
}

// ----------------------------------------------------
// 2. Microphone & Audio Recording (Push-to-Talk)
// ----------------------------------------------------
async function startRecording() {
  stopAudioPlayback(); // CRITICAL: Prevent audio feedback loop
  try {
    const audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.audioChunks = [];
    state.mediaRecorder = new MediaRecorder(audioStream, { mimeType: 'audio/webm' });

    state.mediaRecorder.ondataavailable = e => {
      if (e.data.size > 0) state.audioChunks.push(e.data);
    };

    state.mediaRecorder.onstop = async () => {
      audioStream.getTracks().forEach(t => t.stop());
      if (state.audioChunks.length > 0) {
        const audioBlob = new Blob(state.audioChunks, { type: 'audio/webm' });
        const reader = new FileReader();
        reader.readAsDataURL(audioBlob);
        reader.onloadend = () => {
          const audioB64 = reader.result;
          sendAssistRequest({ audio_base64: audioB64, mode: 'auto' });
        };
      }
    };

    state.mediaRecorder.start();
    state.isRecording = true;
    btnPtt.classList.add('active-recording');
    btnPtt.setAttribute('aria-pressed', 'true');
    setStatus('listening', 'جاري الاستماع... تحدث بوضوح الآن.');
  } catch (err) {
    console.error('Microphone error:', err);
    setStatus('ready', 'تنبيه: تعذر فتح الميكروفون (' + err.message + '). اضغط سماح في المتصفح.');
  }
}

function stopRecording() {
  if (state.mediaRecorder && state.isRecording) {
    state.mediaRecorder.stop();
    state.isRecording = false;
    btnPtt.classList.remove('active-recording');
    btnPtt.setAttribute('aria-pressed', 'false');
    setStatus('processing', 'جاري تحليل المشهد بواسطة النماذج المحلية...');
  }
}

// Push to Talk Events
btnPtt.addEventListener('mousedown', startRecording);
btnPtt.addEventListener('mouseup', stopRecording);
btnPtt.addEventListener('mouseleave', () => { if (state.isRecording) stopRecording(); });
btnPtt.addEventListener('touchstart', e => { e.preventDefault(); startRecording(); });
btnPtt.addEventListener('touchend', e => { e.preventDefault(); stopRecording(); });

// ----------------------------------------------------
// 3. Audio Playback (Piper WAV) & Instant Stop
// ----------------------------------------------------
function playAudioBase64(base64Data) {
  if (!base64Data) return;
  stopAudioPlayback();

  try {
    const binary = atob(base64Data);
    const len = binary.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    const blob = new Blob([bytes], { type: 'audio/wav' });
    const url = URL.createObjectURL(blob);

    audioPlayer.src = url;
    state.isPlayingAudio = true;
    setStatus('speaking', 'المساعد يتحدث الآن...');

    audioPlayer.play().catch(err => {
      console.warn('Autoplay blocked:', err);
      btnReplayAudio.style.display = 'inline-flex';
      setStatus('ready', 'تم تجهيز الإجابة الصوتية. اضغط «استمع للإجابة» للتشغيل.');
    });

    audioPlayer.onended = () => {
      state.isPlayingAudio = false;
      setStatus('ready', 'المساعد جاهز للاستخدام. اضغط «تحدث مع المساعد» أو مفتاح المسافة للبدء.');
    };
  } catch (err) {
    console.error('Audio decode error:', err);
  }
}

function stopAudioPlayback() {
  if (audioPlayer) {
    audioPlayer.pause();
    audioPlayer.currentTime = 0;
  }
  state.isPlayingAudio = false;
  if (state.currentRequestId) {
    fetch('/api/cancel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ request_id: state.currentRequestId })
    }).catch(() => {});
  }
}

function handleStopAction() {
  stopAudioPlayback();
  if (state.isRecording) stopRecording();
  setStatus('ready', 'تم إيقاف الصوت وإلغاء أي طلب جاري.');
}

btnStop.addEventListener('click', handleStopAction);

btnReplayAudio.addEventListener('click', () => {
  if (audioPlayer.src) {
    audioPlayer.play();
    state.isPlayingAudio = true;
    setStatus('speaking', 'المساعد يتحدث الآن...');
  }
});

// Copy Answer Text
btnCopyText.addEventListener('click', async () => {
  const text = answerBox.textContent.trim();
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    lblCopy.textContent = 'تم النسخ ✓';
    setTimeout(() => { lblCopy.textContent = 'نسخ النص'; }, 2000);
  } catch (err) {
    console.warn('Clipboard write error:', err);
  }
});

// ----------------------------------------------------
// 4. Send Orchestrated Assist Request
// ----------------------------------------------------
async function sendAssistRequest(options = {}) {
  stopAudioPlayback();
  setStatus('processing', 'جاري معالجة الطلب بالنماذج المحلية...');

  let imageB64 = null;
  if (fileImageInput.files && fileImageInput.files[0]) {
    imageB64 = await fileToBase64(fileImageInput.files[0]);
  } else if (state.cameraActive) {
    imageB64 = captureCurrentFrame();
  }

  const frameId = 'frame_' + Date.now();
  const payload = {
    mode: options.mode || 'auto',
    query_text: options.query_text || null,
    audio_base64: options.audio_base64 || null,
    image_base64: imageB64,
    frame_id: frameId,
    target_object_ar: options.target_object_ar || null,
  };

  // Immediate frame preview in inspector
  if (imageB64 && analyzedFrameImg) {
    analyzedFrameImg.src = imageB64;
    analyzedFrameImg.style.display = 'block';
    if (analyzedFramePlaceholder) analyzedFramePlaceholder.style.display = 'none';
  }

  try {
    const res = await fetch('/api/assist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    state.currentRequestId = data.request_id;

    // Display Grounded Answer
    answerBox.textContent = data.answer_ar || 'لم يتم استلام إجابة واضحة.';
    answerBox.focus();

    // Populate Inspector Diagnostics
    if (inspReqId) inspReqId.textContent = data.request_id || '--';
    if (inspFrameId) inspFrameId.textContent = data.frame_id || frameId;
    if (inspTimestamp) inspTimestamp.textContent = data.timestamp || new Date().toLocaleTimeString('ar-EG');
    if (inspStages) {
      const timings = Object.entries(data.stage_timings_ms || {})
        .map(([k, v]) => `${k}: ${v}ms`)
        .join(', ');
      inspStages.textContent = timings || `${data.total_latency_ms}ms total`;
    }
    if (inspQuality && data.details && data.details.frame_quality) {
      const q = data.details.frame_quality;
      inspQuality.textContent = q.is_usable ? 'ممتازة ومقبولة ✅' : `تنبيه: ${q.issue} ⚠️`;
    }

    // Overlays if detections exist
    if (data.details && data.details.detection && data.details.detection.detections) {
      drawDetections(data.details.detection.detections);
    } else {
      clearCanvas();
    }

    // Play Synthesized Voice
    if (data.audio_base64) {
      btnReplayAudio.style.display = 'inline-flex';
      playAudioBase64(data.audio_base64);
    } else {
      btnReplayAudio.style.display = 'none';
      setStatus('ready', 'المساعد جاهز للاستخدام.');
    }

    // Append to interaction history
    addHistoryEntry(data.query_text || data.mode, data.answer_ar);
  } catch (err) {
    console.error('Assist request error:', err);
    answerBox.textContent = 'حدث خطأ أثناء معالجة الطلب: ' + err.message;
    setStatus('ready', 'تعذر استكمال الطلب. تأكد من عمل الخادم المحلي.');
  }
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => resolve(reader.result);
    reader.onerror = error => reject(error);
  });
}

// ----------------------------------------------------
// 5. Action Button Listeners
// ----------------------------------------------------
btnDescribe.addEventListener('click', () => {
  if (!state.cameraActive && !fileImageInput.files.length) {
    setStatus('ready', 'تنبيه: يرجى تشغيل الكاميرا أولاً لمعاينة المشهد.');
    return;
  }
  sendAssistRequest({ mode: 'describe' });
});

btnRead.addEventListener('click', () => {
  if (!state.cameraActive && !fileImageInput.files.length) {
    setStatus('ready', 'تنبيه: يرجى تشغيل الكاميرا أولاً لتوجيهها نحو النص.');
    return;
  }
  sendAssistRequest({ mode: 'read' });
});

btnFind.addEventListener('click', () => {
  if (!state.cameraActive && !fileImageInput.files.length) {
    setStatus('ready', 'تنبيه: يرجى تشغيل الكاميرا أولاً للبحث عن الكائن.');
    return;
  }
  const term = searchObjectInput.value.trim() || 'قنينة';
  sendAssistRequest({ mode: 'find', target_object_ar: term });
});

searchObjectInput.addEventListener('keydown', e => {
  if (e.key === 'Enter') {
    btnFind.click();
  }
});

btnRepeat.addEventListener('click', () => {
  sendAssistRequest({ mode: 'repeat' });
});

btnSendText.addEventListener('click', () => {
  const q = textQueryInput.value.trim();
  if (q) {
    sendAssistRequest({ query_text: q, mode: 'auto' });
  }
});

textQueryInput.addEventListener('keydown', e => {
  if (e.key === 'Enter') {
    btnSendText.click();
  }
});

// ----------------------------------------------------
// 6. Keyboard Accessibility Shortcuts
// ----------------------------------------------------
window.addEventListener('keydown', e => {
  // CRITICAL: NEVER activate shortcuts while typing in input or textarea
  const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
  if (activeTag === 'input' || activeTag === 'textarea' || activeTag === 'select' || document.activeElement.isContentEditable) {
    return;
  }

  if (e.key === ' ' || e.code === 'Space') {
    e.preventDefault();
    if (!state.isRecording) startRecording();
  } else if (e.key === 'Escape') {
    e.preventDefault();
    handleStopAction();
  } else if (e.key === 'c' || e.key === 'C') {
    e.preventDefault();
    btnCamera.click();
  } else if (e.key === 'd' || e.key === 'D') {
    e.preventDefault();
    btnDescribe.click();
  } else if (e.key === 'r' || e.key === 'R') {
    e.preventDefault();
    btnRead.click();
  } else if (e.key === 'f' || e.key === 'F') {
    e.preventDefault();
    searchObjectInput.focus();
  } else if (e.key === 'a' || e.key === 'A') {
    e.preventDefault();
    btnRepeat.click();
  }
});

window.addEventListener('keyup', e => {
  const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
  if (activeTag === 'input' || activeTag === 'textarea' || activeTag === 'select' || document.activeElement.isContentEditable) {
    return;
  }

  if ((e.key === ' ' || e.code === 'Space') && state.isRecording) {
    e.preventDefault();
    stopRecording();
  }
});

// ----------------------------------------------------
// 7. History & Health Diagnostics
// ----------------------------------------------------
function addHistoryEntry(query, answer) {
  const now = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
  state.history.unshift({ query, answer, time: now });
  if (state.history.length > state.maxHistory) {
    state.history.pop();
  }
  renderHistory();
}

function renderHistory() {
  if (!historyList) return;
  if (!state.history.length) {
    historyList.innerHTML = '<li class="history-empty-item">لا توجد تفاعلات سابقة في هذه الجلسة بعد.</li>';
    return;
  }
  historyList.innerHTML = '';
  state.history.forEach(item => {
    const li = document.createElement('li');
    li.className = 'history-item-clean';
    li.innerHTML = `<div><strong>${item.query}:</strong> ${item.answer}</div> <span class="diag-card-title">[${item.time}]</span>`;
    historyList.appendChild(li);
  });
}

async function refreshHealth() {
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    const models = data.models || {};

    const formatStatus = m => {
      if (!m) return 'غير متاح';
      if (m.installed && m.loaded) return 'جاهز ومحمل ✅';
      if (m.installed) return 'مثبت (محلي) ⚡';
      return 'غير مثبت ❌';
    };

    const vlmEl = document.getElementById('diag-vlm');
    if (vlmEl) vlmEl.innerHTML = `<bdi>${models.vlm ? models.vlm.version_or_digest : 'qwen3-vl:2b-instruct-q4_K_M'}</bdi> (${formatStatus(models.vlm)})`;

    const detEl = document.getElementById('diag-det');
    if (detEl) detEl.innerHTML = `<bdi>YOLO11n</bdi> (${formatStatus(models.detection)})`;

    const ocrEl = document.getElementById('diag-ocr');
    if (ocrEl) ocrEl.innerHTML = `<bdi>EasyOCR Arabic/English</bdi> (${formatStatus(models.ocr)})`;

    const asrEl = document.getElementById('diag-asr');
    if (asrEl) asrEl.innerHTML = `<bdi>faster-whisper</bdi> (${formatStatus(models.asr)})`;

    const ttsEl = document.getElementById('diag-tts');
    if (ttsEl) ttsEl.innerHTML = `<bdi>Piper ar_JO-kareem-medium</bdi> (${formatStatus(models.tts)})`;

    const mem = data.system_memory_mb || {};
    const ramEl = document.getElementById('diag-ram');
    if (ramEl) ramEl.textContent = `${mem.used_ram_mb || 0} MB / ${mem.total_ram_mb || 0} MB (${mem.ram_percent || 0}%)`;
  } catch (err) {
    console.warn('Could not fetch health:', err);
  }
}

btnRefreshHealth.addEventListener('click', refreshHealth);

// Theme Toggle (Warm Light <-> High Contrast)
btnThemeToggle.addEventListener('click', () => {
  const currentTheme = document.body.getAttribute('data-theme') || 'warm-light';
  const newTheme = currentTheme === 'high-contrast' ? 'warm-light' : 'high-contrast';
  document.body.setAttribute('data-theme', newTheme);
  lblTheme.textContent = newTheme === 'high-contrast' ? 'وضع طبيعي' : 'تباين فائق';
});

// About Modal Handlers
btnAboutModal.addEventListener('click', () => {
  if (modalAbout && typeof modalAbout.showModal === 'function') {
    modalAbout.showModal();
  }
});

btnCloseAbout.addEventListener('click', () => {
  if (modalAbout) modalAbout.close();
});

btnAboutOk.addEventListener('click', () => {
  if (modalAbout) modalAbout.close();
});

// Initial Setup
window.addEventListener('DOMContentLoaded', () => {
  listCameras();
  refreshHealth();
});
