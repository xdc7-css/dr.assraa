import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Header } from './components/Header';
import { CameraWorkspace } from './components/CameraWorkspace';
import { InteractionPanel } from './components/InteractionPanel';
import { ResponseCard } from './components/ResponseCard';
import { AboutModal } from './components/AboutModal';
import { SupervisorDrawer } from './components/SupervisorDrawer';
import { PerformanceMonitor } from './components/PerformanceMonitor';
import type {
  AppLifecycleState,
  AssistResponse,
  HealthResponse,
  DetectionItem,
  SearchSessionState,
  VLMMode,
  ClientPerformanceMetrics,
} from './types';
import {
  playListeningStartChime,
  playListeningEndChime,
  playSearchFoundChime,
  playAlertChime,
} from './utils/audioCues';
import './App.css';

export const App: React.FC = () => {
  // Theme & Modals State
  const [highContrast, setHighContrast] = useState(false);
  const [showAbout, setShowAbout] = useState(false);
  const [showDiagnostics, setShowDiagnostics] = useState(false);

  // Developer Mode & Performance Telemetry
  const [devMode, setDevMode] = useState<boolean>(() => {
    try {
      return (
        window.location.search.includes('dev=true') ||
        localStorage.getItem('amav_dev_mode') === 'true'
      );
    } catch {
      return false;
    }
  });
  const [perfMetrics, setPerfMetrics] = useState<ClientPerformanceMetrics | null>(null);
  const [perfHistory, setPerfHistory] = useState<ClientPerformanceMetrics[]>([]);
  const [ocrStage, setOcrStage] = useState<'none' | 'processing_notice' | 'text_delivered'>('none');

  // Application Lifecycle State
  const [lifecycleState, setLifecycleState] = useState<AppLifecycleState>('ready');
  const [isRecording, setIsRecording] = useState(false);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [currentRequestId, setCurrentRequestId] = useState<string | null>(null);

  // Upgrade Model & Session States
  const [modelMode, setModelMode] = useState<VLMMode>('fast');
  const [speechSpeed, setSpeechSpeed] = useState<number>(1.0);
  const [activeSearchSession, setActiveSearchSession] = useState<SearchSessionState | null>(null);

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
  const searchIntervalRef = useRef<any>(null);
  const isSearchStepBusyRef = useRef<boolean>(false);
  const audioChunkQueueRef = useRef<string[]>([]);
  const isPlayingChunkRef = useRef<boolean>(false);

  // Precision Telemetry Refs
  const interactionStartRef = useRef<number>(0);
  const firstVisibleTextCapturedRef = useRef<boolean>(false);
  const firstAudioPlaybackCapturedRef = useRef<boolean>(false);

  // Toggle Dev Mode
  const handleToggleDevMode = useCallback(() => {
    setDevMode((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('amav_dev_mode', next ? 'true' : 'false');
      } catch {}
      return next;
    });
  }, []);

  // Keyboard shortcut Ctrl+Shift+D or Alt+P for Dev Mode
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'd') ||
        (e.altKey && e.key.toLowerCase() === 'p')
      ) {
        e.preventDefault();
        handleToggleDevMode();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleToggleDevMode]);

  // Expose metrics to window for automated verification and inspection
  useEffect(() => {
    (window as any).__amav_perf_metrics = perfMetrics;
    (window as any).__amav_perf_history = perfHistory;
  }, [perfMetrics, perfHistory]);

  // Toggle Theme
  const handleToggleTheme = useCallback(() => {
    setHighContrast((prev) => {
      const next = !prev;
      document.documentElement.setAttribute('data-theme', next ? 'high-contrast' : 'warm-light');
      return next;
    });
  }, []);

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
    audioChunkQueueRef.current = [];
    isPlayingChunkRef.current = false;
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
      audioPlayerRef.current.currentTime = 0;
    }
    setIsPlayingAudio(false);
  }, []);

  // Stop Continuous Search Loop
  const stopContinuousSearch = useCallback(async () => {
    if (searchIntervalRef.current) {
      clearInterval(searchIntervalRef.current);
      searchIntervalRef.current = null;
    }
    if (activeSearchSession) {
      try {
        await fetch('/api/search_session', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'stop', session_id: activeSearchSession.session_id }),
        });
      } catch (e) {
        // ignore network error on stop
      }
    }
    setActiveSearchSession(null);
    if (lifecycleState === 'searching') {
      setLifecycleState('ready');
    }
  }, [activeSearchSession, lifecycleState]);

  // Stop All Active Operations (Emergency Stop Esc)
  const handleStopAll = useCallback(() => {
    activeRequestTokenRef.current += 1; // Invalidate any in-flight response
    stopAudio();
    stopContinuousSearch();

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
  }, [stopAudio, stopContinuousSearch, isRecording, currentRequestId]);

  // Start Camera Stream
  const startCamera = useCallback(
    async (deviceIdToUse?: string) => {
      stopAudio();
      const targetDevice = deviceIdToUse || selectedDeviceId;
      const constraints: MediaStreamConstraints = {
        video: targetDevice
          ? { deviceId: { exact: targetDevice }, width: { ideal: 1280 }, height: { ideal: 720 } }
          : { width: { ideal: 1280 }, height: { ideal: 720 } },
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
    },
    [selectedDeviceId, stopAudio, listCameras]
  );

  // Stop Camera Stream
  const stopCamera = useCallback(() => {
    stopContinuousSearch();
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
  }, [stopContinuousSearch]);

  const handleToggleCamera = useCallback(() => {
    if (cameraActive) {
      stopCamera();
    } else {
      startCamera();
    }
  }, [cameraActive, stopCamera, startCamera]);

  const handleSelectDevice = useCallback(
    (devId: string) => {
      setSelectedDeviceId(devId);
      if (cameraActive) {
        startCamera(devId);
      }
    },
    [cameraActive, startCamera]
  );

  // Capture Frame as JPEG Base64
  const captureFrame = useCallback((): string | null => {
    if (!videoRef.current || !canvasRef.current) return null;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (video.videoWidth === 0 || video.videoHeight === 0) return null;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg', 0.85);
  }, []);

  // Incremental Audio Chunk Queue Player with Precise TTFA onplay Measurement
  const playNextAudioChunk = useCallback(() => {
    if (audioChunkQueueRef.current.length === 0) {
      isPlayingChunkRef.current = false;
      setIsPlayingAudio(false);
      setLifecycleState('ready');
      return;
    }

    const b64 = audioChunkQueueRef.current.shift();
    if (!b64) {
      playNextAudioChunk();
      return;
    }

    isPlayingChunkRef.current = true;
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
      player.playbackRate = speechSpeed;
      setIsPlayingAudio(true);
      setLifecycleState('speaking');

      // Real browser audio playback event measurement (TTFA)
      player.onplay = () => {
        if (!firstAudioPlaybackCapturedRef.current && interactionStartRef.current > 0) {
          firstAudioPlaybackCapturedRef.current = true;
          const t_audio = performance.now();
          const ttfa = Math.round(t_audio - interactionStartRef.current);
          setPerfMetrics((prev) =>
            prev
              ? {
                  ...prev,
                  firstAudibleAudioTime: t_audio,
                  firstAudibleAudioMs: ttfa,
                }
              : prev
          );
        }
      };

      player.play().catch((err) => {
        console.warn('Autoplay prevented:', err);
        playNextAudioChunk();
      });

      player.onended = () => {
        playNextAudioChunk();
      };
    } catch (err) {
      console.error('Audio chunk decode error:', err);
      playNextAudioChunk();
    }
  }, [speechSpeed]);

  const enqueueAudioChunk = useCallback(
    (b64: string) => {
      if (!b64) return;
      audioChunkQueueRef.current.push(b64);
      if (!isPlayingChunkRef.current) {
        playNextAudioChunk();
      }
    },
    [playNextAudioChunk]
  );

  // Play Synthesized WAV Audio (Standalone / Replay)
  const playAudioBase64 = useCallback(
    (b64: string) => {
      if (!b64) return;
      stopAudio();
      enqueueAudioChunk(b64);
    },
    [stopAudio, enqueueAudioChunk]
  );

  // Execute Core Assist Request with Real-Time Token Streaming & Sentence Audio
  const executeAssist = useCallback(
    async (options: {
      mode: string;
      query_text?: string;
      audio_base64?: string;
      target_object_ar?: string;
      override_quality?: boolean;
    }) => {
      stopAudio();
      stopContinuousSearch();

      const thisToken = ++activeRequestTokenRef.current;
      setLifecycleState('analyzing');

      // Client E2E Real-Time Performance Measurement Init
      const t0 = performance.now();
      interactionStartRef.current = t0;
      firstVisibleTextCapturedRef.current = false;
      firstAudioPlaybackCapturedRef.current = false;

      const initialMetrics: ClientPerformanceMetrics = {
        requestId: '',
        mode: options.mode || 'auto',
        interactionStartTime: t0,
        backendTimings: {},
        sourceComponents: [],
        activeModel: 'qwen3-vl:2b-instruct-q4_K_M',
        ocrState: options.mode === 'read' ? 'processing_notice' : 'none',
      };
      setPerfMetrics(initialMetrics);
      setOcrStage(options.mode === 'read' ? 'processing_notice' : 'none');

      const isConversationalMode = ['repeat', 'shorten', 'reset', 'greeting'].includes(
        options.mode
      );
      let frameImg: string | null = null;
      if (!isConversationalMode) {
        frameImg = uploadedFileBase64 || captureFrame();
        if (frameImg) {
          setAnalyzedFrameBase64(frameImg);
        }
      }

      const frameId = `frame_${Date.now()}`;
      const payload = {
        mode: options.mode || 'auto',
        query_text: options.query_text || null,
        audio_base64: options.audio_base64 || null,
        image_base64: frameImg,
        frame_id: frameId,
        target_object_ar: options.target_object_ar || null,
        model_mode: modelMode,
        override_quality: Boolean(options.override_quality),
        speech_speed: speechSpeed,
      };

      try {
        const res = await fetch('/api/assist/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        if (!res.ok || !res.body) {
          throw new Error(`HTTP error ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        let accumulatedText = '';
        const allAudioChunks: string[] = [];

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          if (thisToken !== activeRequestTokenRef.current) {
            reader.cancel();
            return;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed.startsWith('data: ')) continue;
            try {
              const event = JSON.parse(trimmed.slice(6));

              if (event.type === 'init') {
                setCurrentRequestId(event.request_id);
                setPerfMetrics((prev) =>
                  prev
                    ? {
                        ...prev,
                        requestId: event.request_id,
                        serverConnectedTime: performance.now(),
                        mode: event.mode || prev.mode,
                      }
                    : prev
                );
                setResponse({
                  request_id: event.request_id,
                  mode: event.mode,
                  query_text: event.query_text || options.query_text,
                  answer_ar: '',
                  status: 'processing',
                  source_components: [],
                  stage_timings_ms: {},
                  total_latency_ms: 0,
                });
              } else if (event.type === 'transcription') {
                if (event.query_text) {
                  setRecognizedQuery(event.query_text);
                }
                if (event.latency_ms) {
                  setPerfMetrics((prev) =>
                    prev
                      ? {
                          ...prev,
                          backendTimings: { ...prev.backendTimings, asr_ms: event.latency_ms },
                        }
                      : prev
                  );
                }
              } else if (event.type === 'ocr_status') {
                const noticeMs = Math.round(performance.now() - interactionStartRef.current);
                setOcrStage('processing_notice');
                setPerfMetrics((prev) =>
                  prev
                    ? {
                        ...prev,
                        ocrStatusNotificationMs: noticeMs,
                        ocrState: 'processing_notice',
                      }
                    : prev
                );
              } else if (event.type === 'ocr_delivered') {
                const delivMs = Math.round(performance.now() - interactionStartRef.current);
                setOcrStage('text_delivered');
                setPerfMetrics((prev) =>
                  prev
                    ? {
                        ...prev,
                        ocrTextDeliveredMs: delivMs,
                        ocrTextLinesCount: event.lines_count,
                        ocrState: 'text_delivered',
                        backendTimings: {
                          ...prev.backendTimings,
                          ocr_ms: event.ocr_latency_ms,
                        },
                      }
                    : prev
                );
              } else if (event.type === 'token') {
                if (event.replace_notice) {
                  accumulatedText = event.token;
                } else {
                  accumulatedText += event.token;
                }

                // First visible text rendered in DOM measurement (Client TTFT)
                if (!firstVisibleTextCapturedRef.current && accumulatedText.trim().length > 0) {
                  firstVisibleTextCapturedRef.current = true;
                  const t_vis = performance.now();
                  const ttft = Math.round(t_vis - interactionStartRef.current);
                  setPerfMetrics((prev) =>
                    prev
                      ? {
                          ...prev,
                          firstVisibleTextTime: t_vis,
                          firstVisibleTextMs: ttft,
                          isColdLoad: ttft > 10000,
                        }
                      : prev
                  );
                }

                setResponse((prev) =>
                  prev
                    ? {
                        ...prev,
                        answer_ar: accumulatedText,
                      }
                    : {
                        request_id: currentRequestId || 'stream',
                        answer_ar: accumulatedText,
                        status: 'streaming',
                        stage_timings_ms: event.ttft_ms ? { ttft_ms: event.ttft_ms } : {},
                        total_latency_ms: 0,
                        source_components: ['vlm_streaming'],
                      }
                );
              } else if (event.type === 'audio_chunk') {
                if (event.latency_ms) {
                  setPerfMetrics((prev) =>
                    prev
                      ? {
                          ...prev,
                          backendTimings: {
                            ...prev.backendTimings,
                            piper_tts_ms:
                              (prev.backendTimings.piper_tts_ms || 0) + event.latency_ms,
                          },
                        }
                      : prev
                  );
                }
                if (event.audio_base64) {
                  allAudioChunks.push(event.audio_base64);
                  enqueueAudioChunk(event.audio_base64);
                }
              } else if (event.type === 'quality_guidance') {
                if (event.guidance && !event.guidance.is_usable) {
                  playAlertChime();
                }
                if (event.audio_base64) {
                  allAudioChunks.push(event.audio_base64);
                  enqueueAudioChunk(event.audio_base64);
                }
              } else if (event.type === 'done') {
                const finalData: AssistResponse = event.response;
                const t_done = performance.now();
                const totalE2E = Math.round(t_done - interactionStartRef.current);

                setPerfMetrics((prev) => {
                  if (!prev) return null;
                  const updated: ClientPerformanceMetrics = {
                    ...prev,
                    requestId: finalData.request_id || prev.requestId,
                    fullCompletionTime: t_done,
                    totalClientDurationMs: totalE2E,
                    backendTimings: {
                      asr_ms:
                        finalData.stage_timings_ms?.asr_ms ||
                        finalData.stage_timings_ms?.transcription_ms,
                      quality_check_ms: finalData.stage_timings_ms?.quality_check_ms,
                      yolo_ms:
                        finalData.stage_timings_ms?.detection_ms ||
                        finalData.stage_timings_ms?.yolo_ms,
                      ocr_ms:
                        finalData.stage_timings_ms?.ocr_ms ||
                        (finalData.mode === 'read'
                          ? finalData.stage_timings_ms?.inference_ms
                          : undefined),
                      vlm_ttft_ms:
                        finalData.stage_timings_ms?.vlm_ttft_ms ||
                        finalData.stage_timings_ms?.ttft_ms,
                      vlm_inference_ms:
                        finalData.stage_timings_ms?.vlm_ms ||
                        finalData.stage_timings_ms?.inference_ms,
                      piper_tts_ms:
                        finalData.stage_timings_ms?.tts_ms || prev.backendTimings.piper_tts_ms,
                      total_backend_ms: finalData.total_latency_ms,
                    },
                    sourceComponents: finalData.source_components || prev.sourceComponents,
                    isColdLoad: (prev.firstVisibleTextMs || totalE2E) > 10000,
                  };
                  setPerfHistory((h) => [...h.slice(-19), updated]);
                  return updated;
                });

                if (thisToken === activeRequestTokenRef.current) {
                  setCurrentRequestId(finalData.request_id);
                  if (allAudioChunks.length > 0 && !finalData.audio_base64) {
                    finalData.audio_base64 = allAudioChunks[0];
                  }
                  setResponse(finalData);

                  if (finalData.details?.transcription?.text) {
                    setRecognizedQuery(finalData.details.transcription.text);
                  } else if (options.query_text) {
                    setRecognizedQuery(options.query_text);
                  }

                  if (finalData.details?.detection?.detections) {
                    setDetections(finalData.details.detection.detections);
                  } else {
                    setDetections([]);
                  }

                  if (finalData.status === 'frame_unusable') {
                    playAlertChime();
                  }

                  if (allAudioChunks.length === 0 && !finalData.audio_base64) {
                    setLifecycleState('ready');
                  }
                }
              }
            } catch (jsonErr) {
              console.warn('Failed to parse SSE event:', jsonErr);
            }
          }
        }
      } catch (err: any) {
        if (thisToken === activeRequestTokenRef.current) {
          console.warn('Assist streaming error, falling back to standard endpoint:', err);
          try {
            const fallbackRes = await fetch('/api/assist', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload),
            });
            if (fallbackRes.ok) {
              const data: AssistResponse = await fallbackRes.json();
              setCurrentRequestId(data.request_id);
              setResponse(data);
              if (data.audio_base64) {
                playAudioBase64(data.audio_base64);
              } else {
                setLifecycleState('ready');
              }
              return;
            }
          } catch (fallbackErr) {
            console.error('Fallback assist also failed:', fallbackErr);
          }
          setLifecycleState('error');
        }
      }
    },
    [
      stopAudio,
      stopContinuousSearch,
      uploadedFileBase64,
      captureFrame,
      modelMode,
      speechSpeed,
      enqueueAudioChunk,
      playAudioBase64,
      currentRequestId,
    ]
  );

  // Start Continuous Object Search Session
  const startContinuousSearch = useCallback(
    async (targetObject: string) => {
      stopAudio();
      stopContinuousSearch();

      if (!cameraActive) {
        await startCamera();
      }

      try {
        const res = await fetch('/api/search_session', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'start', target_object_ar: targetObject }),
        });
        if (res.ok) {
          const sessionState: SearchSessionState = await res.json();
          setActiveSearchSession(sessionState);
          setLifecycleState('searching');
          if (sessionState.announcement_text_ar) {
            playAudioBase64(
              (
                await (
                  await fetch('/api/speak', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      text: sessionState.announcement_text_ar,
                      speed: speechSpeed,
                    }),
                  })
                ).json()
              ).audio_base64
            );
          }

          // Launch periodic frame analysis interval (approx 800ms)
          searchIntervalRef.current = setInterval(async () => {
            if (isSearchStepBusyRef.current) return;
            const currentFrame = captureFrame();
            if (!currentFrame) return;

            isSearchStepBusyRef.current = true;
            try {
              const stepRes = await fetch('/api/search_session', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  action: 'update',
                  session_id: sessionState.session_id,
                  image_base64: currentFrame,
                  mirrored: false,
                }),
              });
              if (stepRes.ok) {
                const stepState: SearchSessionState = await stepRes.json();
                setActiveSearchSession(stepState);
                if (stepState.should_announce && stepState.announcement_text_ar) {
                  playSearchFoundChime();
                  const speakRes = await fetch('/api/speak', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      text: stepState.announcement_text_ar,
                      speed: speechSpeed,
                    }),
                  });
                  if (speakRes.ok) {
                    const spkData = await speakRes.json();
                    if (spkData.audio_base64) playAudioBase64(spkData.audio_base64);
                  }
                }
              }
            } catch (stepErr) {
              console.warn('Search step tick failed:', stepErr);
            } finally {
              isSearchStepBusyRef.current = false;
            }
          }, 800);
        }
      } catch (err) {
        console.error('Failed to start continuous search session:', err);
      }
    },
    [stopAudio, stopContinuousSearch, cameraActive, startCamera, speechSpeed, captureFrame, playAudioBase64]
  );

  // Quick Action Buttons
  const handleQuickAction = useCallback(
    (action: string) => {
      executeAssist({ mode: action });
    },
    [executeAssist]
  );

  // Send Typed Text Query
  const handleSendTextQuery = useCallback(
    (text: string) => {
      if (!text.trim()) return;
      executeAssist({ mode: 'ask', query_text: text.trim() });
    },
    [executeAssist]
  );

  // Override Quality Warning
  const handleOverrideQuality = useCallback(() => {
    executeAssist({ mode: response?.mode || 'describe', override_quality: true });
  }, [executeAssist, response]);

  // Audio Recording (ASR)
  const startRecording = useCallback(async () => {
    stopAudio();
    stopContinuousSearch();

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      audioRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstart = () => {
        setIsRecording(true);
        setLifecycleState('listening');
        playListeningStartChime();
      };

      mediaRecorder.onstop = async () => {
        setIsRecording(false);
        setLifecycleState('transcribing');
        playListeningEndChime();

        stream.getTracks().forEach((track) => track.stop());

        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const reader = new FileReader();
        reader.onloadend = () => {
          const b64 = reader.result as string;
          executeAssist({ mode: 'auto', audio_base64: b64 });
        };
        reader.readAsDataURL(audioBlob);
      };

      mediaRecorder.start();
    } catch (err) {
      console.error('Failed to start microphone recording:', err);
      setLifecycleState('permission_required');
    }
  }, [stopAudio, stopContinuousSearch, executeAssist]);

  const stopRecording = useCallback(() => {
    if (audioRecorderRef.current && isRecording) {
      audioRecorderRef.current.stop();
    }
  }, [isRecording]);

  // Handle Static Image File Upload
  const handleFileUpload = useCallback(
    (file: File) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const b64 = reader.result as string;
        setUploadedFileBase64(b64);
        setAnalyzedFrameBase64(b64);
      };
      reader.readAsDataURL(file);
    },
    []
  );

  // Keyboard Accessibility
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeTag = document.activeElement?.tagName.toLowerCase();
      if (
        activeTag === 'input' ||
        activeTag === 'textarea' ||
        activeTag === 'select' ||
        (document.activeElement as HTMLElement)?.isContentEditable
      ) {
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
      } else if (e.key === 's' || e.key === 'S') {
        e.preventDefault();
        stopAudio();
      } else if (e.key === 'm' || e.key === 'M') {
        e.preventDefault();
        setModelMode((prev) => (prev === 'fast' ? 'detailed' : 'fast'));
      } else if (e.key === 'h' || e.key === 'H') {
        e.preventDefault();
        handleToggleTheme();
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      const activeTag = document.activeElement?.tagName.toLowerCase();
      if (
        activeTag === 'input' ||
        activeTag === 'textarea' ||
        activeTag === 'select' ||
        (document.activeElement as HTMLElement)?.isContentEditable
      ) {
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
  }, [
    isRecording,
    startRecording,
    stopRecording,
    handleStopAll,
    handleToggleCamera,
    handleQuickAction,
    stopAudio,
    handleToggleTheme,
  ]);

  // Initial load
  useEffect(() => {
    listCameras();
    fetchHealth();
    return () => {
      if (searchIntervalRef.current) clearInterval(searchIntervalRef.current);
    };
  }, [listCameras, fetchHealth]);

  return (
    <div className="amav-app-root">
      <a href="#main-workspace-content" className="skip-nav">
        انتقل مباشرة إلى منطقة العمل وأوامر المساعد
      </a>

      {/* Spacious, Compact Academic Header */}
      <Header
        highContrast={highContrast}
        devMode={devMode}
        onToggleTheme={handleToggleTheme}
        onOpenAbout={() => setShowAbout(true)}
        onOpenDiagnostics={() => setShowDiagnostics(true)}
        onToggleDevMode={handleToggleDevMode}
      />

      {/* Main Workspace (2 balanced columns) */}
      <main id="main-workspace-content" className="app-container main-workspace-layout" role="main">
        <div className="workspace-two-columns">
          {/* Right Column: Camera Workspace */}
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

          {/* Left Column: Interaction & Response */}
          <div className="workspace-column-interaction">
            <InteractionPanel
              lifecycleState={lifecycleState}
              isRecording={isRecording}
              isPlayingAudio={isPlayingAudio}
              recognizedQuery={recognizedQuery}
              modelMode={modelMode}
              speechSpeed={speechSpeed}
              activeSearchSession={activeSearchSession}
              onStartVoice={startRecording}
              onStopVoice={stopRecording}
              onQuickAction={handleQuickAction}
              onSendTextQuery={handleSendTextQuery}
              onStartContinuousSearch={startContinuousSearch}
              onStopContinuousSearch={stopContinuousSearch}
              onToggleModelMode={setModelMode}
              onChangeSpeechSpeed={setSpeechSpeed}
              onStopAll={handleStopAll}
              onFileUpload={handleFileUpload}
            />

            <ResponseCard
              lifecycleState={lifecycleState}
              response={response}
              hasAudio={Boolean(response?.audio_base64)}
              isPlayingAudio={isPlayingAudio}
              ocrState={ocrStage}
              onReplayAudio={() => response?.audio_base64 && playAudioBase64(response.audio_base64)}
              onRepeatAnswer={() => handleQuickAction('repeat')}
              onShortenAnswer={() => handleQuickAction('shorten')}
              onOverrideQuality={handleOverrideQuality}
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
        perfMetrics={perfMetrics}
        onClose={() => setShowDiagnostics(false)}
        onRefreshHealth={fetchHealth}
      />

      {/* Developer-Only Performance Monitor Panel */}
      <PerformanceMonitor
        metrics={perfMetrics}
        history={perfHistory}
        health={health}
        isVisible={devMode}
        onToggleVisible={handleToggleDevMode}
        onClearHistory={() => setPerfHistory([])}
      />
    </div>
  );
};

export default App;
