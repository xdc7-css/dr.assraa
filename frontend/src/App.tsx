import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Header } from './components/Header';
import { CameraWorkspace } from './components/CameraWorkspace';
import { InteractionPanel } from './components/InteractionPanel';
import { ResponseCard } from './components/ResponseCard';
import { AboutModal } from './components/AboutModal';
import { SupervisorDrawer } from './components/SupervisorDrawer';
import type { AppLifecycleState, AssistResponse, HealthResponse, DetectionItem } from './types';
import './App.css';

export const App: React.FC = () => {
  // Theme & Modals State
  const [highContrast, setHighContrast] = useState(false);
  const [showAbout, setShowAbout] = useState(false);
  const [showDiagnostics, setShowDiagnostics] = useState(false);

  // Application Lifecycle State
  const [lifecycleState, setLifecycleState] = useState<AppLifecycleState>('ready');
  const [isRecording, setIsRecording] = useState(false);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [currentRequestId, setCurrentRequestId] = useState<string | null>(null);

  // Data & Results
  const [response, setResponse] = useState<AssistResponse | null>(null);
  const [recognizedQuery, setRecognizedQuery] = useState<string | null>(null);
  const [detections, setDetections] = useState<DetectionItem[]>([]);
  const [analyzedFrameBase64, setAnalyzedFrameBase64] = useState<string | null>(null);
  const [uploadedFileBase64, setUploadedFileBase64] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);

  // Camera State
  const [cameraActive, setCameraActive] = useState(false);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('');
  const [showOverlay, setShowOverlay] = useState(true);

  // Refs
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);
  const activeRequestTokenRef = useRef<number>(0);

  // Toggle Theme
  const handleToggleTheme = () => {
    const next = !highContrast;
    setHighContrast(next);
    document.documentElement.setAttribute('data-theme', next ? 'high-contrast' : 'warm-light');
  };

  // Fetch Health Diagnostics
  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch('/api/health');
      if (res.ok) {
        const data = await res.json();
        setHealth(data);
      }
    } catch (err) {
      console.warn('Could not fetch health:', err);
    }
  }, []);

  // List Camera Devices
  const listCameras = useCallback(async () => {
    if (!navigator.mediaDevices?.enumerateDevices) return;
    try {
      const allDevices = await navigator.mediaDevices.enumerateDevices();
      const videoDevs = allDevices.filter((d) => d.kind === 'videoinput');
      setDevices(videoDevs);
      if (videoDevs.length > 0 && !selectedDeviceId) {
        setSelectedDeviceId(videoDevs[0].deviceId);
      }
    } catch (err) {
      console.warn('Could not list cameras:', err);
    }
  }, [selectedDeviceId]);

  // Stop Audio Playback Immediately
  const stopAudio = useCallback(() => {
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
      audioPlayerRef.current.currentTime = 0;
    }
    setIsPlayingAudio(false);
  }, []);

  // Stop All Active Operations (Emergency Stop)
  const handleStopAll = useCallback(() => {
    activeRequestTokenRef.current += 1; // Invalidate any in-flight response
    stopAudio();

    if (audioRecorderRef.current && isRecording) {
      audioRecorderRef.current.stop();
      setIsRecording(false);
    }

    if (currentRequestId) {
      fetch('/api/cancel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request_id: currentRequestId }),
      }).catch(() => {});
    }

    setLifecycleState('cancelled');
  }, [stopAudio, isRecording, currentRequestId]);

  // Start Camera Stream
  const startCamera = useCallback(async (deviceIdToUse?: string) => {
    stopAudio();
    const targetDevice = deviceIdToUse || selectedDeviceId;
    const constraints: MediaStreamConstraints = {
      video: targetDevice ? { deviceId: { exact: targetDevice }, width: { ideal: 1280 }, height: { ideal: 720 } } : { width: { ideal: 1280 }, height: { ideal: 720 } },
    };

    try {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.onloadedmetadata = () => {
          if (canvasRef.current && videoRef.current) {
            canvasRef.current.width = videoRef.current.videoWidth;
            canvasRef.current.height = videoRef.current.videoHeight;
          }
        };
      }

      setCameraActive(true);
      setLifecycleState('ready');
      listCameras();
    } catch (err: any) {
      console.error('Camera access failed:', err);
      setLifecycleState('permission_required');
    }
  }, [selectedDeviceId, stopAudio, listCameras]);

  // Stop Camera Stream
  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    if (canvasRef.current) {
      const ctx = canvasRef.current.getContext('2d');
      if (ctx) ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
    }
    setCameraActive(false);
    setDetections([]);
    setLifecycleState('ready');
  }, []);

  const handleToggleCamera = () => {
    if (cameraActive) {
      stopCamera();
    } else {
      startCamera();
    }
  };

  const handleSelectDevice = (devId: string) => {
    setSelectedDeviceId(devId);
    if (cameraActive) {
      startCamera(devId);
    }
  };

  // Capture Current Frame from Video Feed
  const captureFrame = useCallback((): string | null => {
    if (!videoRef.current || !cameraActive) return null;
    const video = videoRef.current;
    if (video.videoWidth === 0 || video.videoHeight === 0) return null;

    const off = document.createElement('canvas');
    off.width = video.videoWidth;
    off.height = video.videoHeight;
    const offCtx = off.getContext('2d');
    if (!offCtx) return null;
    offCtx.drawImage(video, 0, 0, off.width, off.height);
    return off.toDataURL('image/jpeg', 0.85);
  }, [cameraActive]);

  // Play Synthesized WAV Audio
  const playAudioBase64 = useCallback((b64: string) => {
    if (!b64) return;
    stopAudio();

    try {
      const binary = atob(b64);
      const len = binary.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) {
        bytes[i] = binary.charCodeAt(i);
      }
      const blob = new Blob([bytes], { type: 'audio/wav' });
      const url = URL.createObjectURL(blob);

      if (!audioPlayerRef.current) {
        audioPlayerRef.current = new Audio();
      }
      const player = audioPlayerRef.current;
      player.src = url;
      setIsPlayingAudio(true);
      setLifecycleState('speaking');

      player.play().catch((err) => {
        console.warn('Autoplay prevented:', err);
        setLifecycleState('ready');
      });

      player.onended = () => {
        setIsPlayingAudio(false);
        setLifecycleState('ready');
      };
    } catch (err) {
      console.error('Audio decode error:', err);
      setLifecycleState('ready');
    }
  }, [stopAudio]);

  // Execute Core Assist Request
  const executeAssist = useCallback(
    async (options: { mode: string; query_text?: string; audio_base64?: string; target_object_ar?: string }) => {
      stopAudio();
      const thisToken = ++activeRequestTokenRef.current;
      setLifecycleState('analyzing');

      let frameImg = uploadedFileBase64 || captureFrame();
      if (frameImg) {
        setAnalyzedFrameBase64(frameImg);
      }

      const frameId = `frame_${Date.now()}`;
      const payload = {
        mode: options.mode || 'auto',
        query_text: options.query_text || null,
        audio_base64: options.audio_base64 || null,
        image_base64: frameImg,
        frame_id: frameId,
        target_object_ar: options.target_object_ar || null,
      };

      try {
        const res = await fetch('/api/assist', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          throw new Error(`HTTP error ${res.status}`);
        }

        const data: AssistResponse = await res.json();

        // Discard if user stopped or cancelled during request
        if (thisToken !== activeRequestTokenRef.current) {
          return;
        }

        setCurrentRequestId(data.request_id);
        setResponse(data);

        // Update recognized query if present
        if (data.details?.transcription?.text) {
          setRecognizedQuery(data.details.transcription.text);
        } else if (options.query_text) {
          setRecognizedQuery(options.query_text);
        }

        // Overlays
        if (data.details?.detection?.detections) {
          setDetections(data.details.detection.detections);
        } else {
          setDetections([]);
        }

        // Voice playback
        if (data.audio_base64) {
          playAudioBase64(data.audio_base64);
        } else {
          setLifecycleState('ready');
        }
      } catch (err: any) {
        if (thisToken === activeRequestTokenRef.current) {
          console.error('Assist request error:', err);
          setLifecycleState('error');
        }
      }
    },
    [stopAudio, uploadedFileBase64, captureFrame, playAudioBase64]
  );

  // Microphone Push-to-Talk Handling
  const startRecording = useCallback(async () => {
    stopAudio(); // CRITICAL: prevent audio feedback loop
    try {
      const audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const recorder = new MediaRecorder(audioStream, { mimeType: 'audio/webm' });
      audioRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        audioStream.getTracks().forEach((t) => t.stop());
        if (audioChunksRef.current.length > 0) {
          const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          const reader = new FileReader();
          reader.readAsDataURL(blob);
          reader.onloadend = () => {
            const b64 = reader.result as string;
            setLifecycleState('transcribing');
            executeAssist({ mode: 'auto', audio_base64: b64 });
          };
        }
      };

      recorder.start();
      setIsRecording(true);
      setLifecycleState('listening');
    } catch (err: any) {
      console.error('Microphone access failed:', err);
      setLifecycleState('permission_required');
    }
  }, [stopAudio, executeAssist]);

  const stopRecording = useCallback(() => {
    if (audioRecorderRef.current && isRecording) {
      audioRecorderRef.current.stop();
      setIsRecording(false);
    }
  }, [isRecording]);

  // Secondary Action Triggers
  const handleQuickAction = useCallback(
    (mode: 'describe' | 'read' | 'find' | 'repeat', param?: string) => {
      if (mode === 'repeat') {
        if (response?.audio_base64) {
          playAudioBase64(response.audio_base64);
        } else {
          executeAssist({ mode: 'repeat' });
        }
        return;
      }
      executeAssist({ mode, target_object_ar: param });
    },
    [response, playAudioBase64, executeAssist]
  );

  const handleSendTextQuery = useCallback(
    (text: string) => {
      setRecognizedQuery(text);
      executeAssist({ mode: 'auto', query_text: text });
    },
    [executeAssist]
  );

  const handleFileUpload = useCallback((file: File) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onloadend = () => {
      setUploadedFileBase64(reader.result as string);
      setAnalyzedFrameBase64(reader.result as string);
    };
  }, []);

  // Keyboard Accessibility
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeTag = document.activeElement?.tagName.toLowerCase();
      if (activeTag === 'input' || activeTag === 'textarea' || activeTag === 'select' || (document.activeElement as HTMLElement)?.isContentEditable) {
        return;
      }

      if (e.key === 'Escape') {
        e.preventDefault();
        handleStopAll();
      } else if (e.key === ' ' || e.code === 'Space') {
        e.preventDefault();
        if (!isRecording) startRecording();
      } else if (e.key === 'c' || e.key === 'C') {
        e.preventDefault();
        handleToggleCamera();
      } else if (e.key === 'd' || e.key === 'D') {
        e.preventDefault();
        handleQuickAction('describe');
      } else if (e.key === 'r' || e.key === 'R') {
        e.preventDefault();
        handleQuickAction('read');
      } else if (e.key === 'f' || e.key === 'F') {
        e.preventDefault();
        const searchInput = document.getElementById('search-object-field');
        if (searchInput) searchInput.focus();
      } else if (e.key === 'a' || e.key === 'A') {
        e.preventDefault();
        handleQuickAction('repeat');
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      const activeTag = document.activeElement?.tagName.toLowerCase();
      if (activeTag === 'input' || activeTag === 'textarea' || activeTag === 'select' || (document.activeElement as HTMLElement)?.isContentEditable) {
        return;
      }
      if ((e.key === ' ' || e.code === 'Space') && isRecording) {
        e.preventDefault();
        stopRecording();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [isRecording, startRecording, stopRecording, handleStopAll, handleToggleCamera, handleQuickAction]);

  // Initial load
  useEffect(() => {
    listCameras();
    fetchHealth();
  }, [listCameras, fetchHealth]);

  return (
    <div className="amav-app-root">
      <a href="#main-workspace-content" className="skip-nav">
        انتقل مباشرة إلى منطقة العمل وأوامر المساعد
      </a>

      {/* Spacious, Compact Academic Header */}
      <Header
        highContrast={highContrast}
        onToggleTheme={handleToggleTheme}
        onOpenAbout={() => setShowAbout(true)}
        onOpenDiagnostics={() => setShowDiagnostics(true)}
      />

      {/* Main Workspace (1320-1440px container, 2 balanced columns) */}
      <main id="main-workspace-content" className="app-container main-workspace-layout" role="main">
        <div className="workspace-two-columns">
          {/* Right Column: Camera Workspace (~56-60%) */}
          <div className="workspace-column-camera">
            <CameraWorkspace
              cameraActive={cameraActive}
              videoRef={videoRef}
              canvasRef={canvasRef}
              devices={devices}
              selectedDeviceId={selectedDeviceId}
              showOverlay={showOverlay}
              detections={detections}
              onToggleCamera={handleToggleCamera}
              onSelectDevice={handleSelectDevice}
              onToggleOverlay={setShowOverlay}
            />
          </div>

          {/* Left Column: Interaction & Response (~40-44%) */}
          <div className="workspace-column-interaction">
            <InteractionPanel
              lifecycleState={lifecycleState}
              isRecording={isRecording}
              isPlayingAudio={isPlayingAudio}
              recognizedQuery={recognizedQuery}
              onStartVoice={startRecording}
              onStopVoice={stopRecording}
              onQuickAction={handleQuickAction}
              onSendTextQuery={handleSendTextQuery}
              onStopAll={handleStopAll}
              onFileUpload={handleFileUpload}
            />

            <ResponseCard
              lifecycleState={lifecycleState}
              response={response}
              hasAudio={Boolean(response?.audio_base64)}
              isPlayingAudio={isPlayingAudio}
              onReplayAudio={() => response?.audio_base64 && playAudioBase64(response.audio_base64)}
              onRepeatAnswer={() => handleQuickAction('repeat')}
            />
          </div>
        </div>
      </main>

      {/* Modals & Drawers */}
      <AboutModal isOpen={showAbout} onClose={() => setShowAbout(false)} />
      <SupervisorDrawer
        isOpen={showDiagnostics}
        health={health}
        lastResponse={response}
        analyzedFrameBase64={analyzedFrameBase64}
        onClose={() => setShowDiagnostics(false)}
        onRefreshHealth={fetchHealth}
      />
    </div>
  );
};

export default App;
