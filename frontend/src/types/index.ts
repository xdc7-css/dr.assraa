/**
 * AMAV Type Definitions
 */

export type AppLifecycleState =
  | 'camera_off'
  | 'permission_required'
  | 'ready'
  | 'listening'
  | 'transcribing'
  | 'analyzing'
  | 'speaking'
  | 'searching'
  | 'cancelled'
  | 'error'
  | 'service_unavailable';

export type VLMMode = 'fast' | 'detailed';

export interface BoundingBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface DetectionItem {
  class_name_en: string;
  class_name_ar: string;
  confidence: number;
  bbox: BoundingBox;
  position?: 'left' | 'center' | 'right';
  center_x?: number;
  center_y?: number;
}

export interface SearchSessionState {
  session_id: string;
  target_query_ar: string;
  target_class_en?: string;
  status: 'active' | 'tracking' | 'lost' | 'stopped' | 'timeout';
  direction_relative?: 'left' | 'center' | 'right';
  direction_text_ar: string;
  instance_count: number;
  stable_lost_count: number;
  should_announce: boolean;
  announcement_text_ar?: string;
  elapsed_seconds: number;
  max_duration_seconds: number;
}

export interface FrameQualityInfo {
  is_usable: boolean;
  issue?: string | null;
  advice_ar?: string | null;
  metrics?: Record<string, any>;
  should_speak?: boolean;
  duration_ms?: number;
}

export interface DetectionResult {
  detections: DetectionItem[];
  annotated_image_base64?: string;
  count?: number;
  summary_ar?: string;
}

export interface AssistDetails {
  transcription?: {
    text: string;
    language: string;
    duration_s?: number;
  };
  detection?: DetectionResult;
  ocr?: {
    text_combined?: string;
    items?: any[];
  };
  ocr_guidance?: {
    issue: string;
    advice_ar: string;
    median_height?: number;
  };
  vlm?: {
    answer_ar?: string;
    model?: string;
    model_mode?: string;
  };
  frame_quality?: FrameQualityInfo;
}

export interface AssistResponse {
  request_id: string;
  mode: string;
  model_mode?: string;
  query_text?: string;
  answer_ar: string;
  audio_base64?: string;
  source_components: string[];
  total_latency_ms: number;
  stage_timings_ms: Record<string, number>;
  frame_id?: string;
  search_session?: SearchSessionState;
  frame_quality?: FrameQualityInfo;
  details?: AssistDetails;
  timestamp?: string;
  error?: string;
}

export interface ModelComponentStatus {
  installed: boolean;
  loaded: boolean;
  device: string;
  version_or_digest?: string;
  path?: string;
  error?: string | null;
}

export interface HealthResponse {
  status: string;
  profile: string;
  system_memory_mb: {
    total_ram_mb: number;
    available_ram_mb: number;
    used_ram_mb: number;
    ram_percent: number;
  };
  gpu_memory_mb?: {
    vram_used_mb?: number;
    vram_free_mb?: number;
    vram_total_mb?: number;
  };
  models: {
    vlm_2b?: ModelComponentStatus;
    vlm_4b?: ModelComponentStatus;
    detection?: ModelComponentStatus;
    ocr?: ModelComponentStatus;
    asr?: ModelComponentStatus;
    tts?: ModelComponentStatus;
  };
  vlm_modes?: {
    fast_model: string;
    detailed_model: string;
    detailed_ready: boolean;
    fast_ready: boolean;
    current_mode: string;
  };
  context_memory?: {
    turn_count: number;
    last_command?: string;
    last_referenced_object?: string;
    is_stale: boolean;
    active_search_session?: string;
  };
}

export interface HistoryItem {
  id: string;
  query: string;
  answer: string;
  time: string;
  mode: string;
}

export interface ClientPerformanceMetrics {
  requestId: string;
  mode: string;
  interactionStartTime: number; // performance.now()
  requestSentTime?: number;
  serverConnectedTime?: number;
  firstVisibleTextTime?: number;
  firstAudibleAudioTime?: number;
  fullCompletionTime?: number;
  
  // Real browser measured latencies
  firstVisibleTextMs?: number;
  firstAudibleAudioMs?: number;
  totalClientDurationMs?: number;
  
  // OCR Milestone Differentiation
  ocrStatusNotificationMs?: number;
  ocrTextDeliveredMs?: number;
  ocrTextLinesCount?: number;
  ocrState?: 'none' | 'processing_notice' | 'text_delivered';
  
  // Subsystem Backend Timings (ms)
  backendTimings: {
    asr_ms?: number;
    quality_check_ms?: number;
    yolo_ms?: number;
    ocr_ms?: number;
    vlm_ttft_ms?: number;
    vlm_inference_ms?: number;
    piper_tts_ms?: number;
    total_backend_ms?: number;
  };
  
  sourceComponents: string[];
  activeModel: string;
  isColdLoad?: boolean;
}
