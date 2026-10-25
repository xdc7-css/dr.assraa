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
  | 'cancelled'
  | 'error'
  | 'service_unavailable';

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
}

export interface DetectionResult {
  detections: DetectionItem[];
  annotated_image_base64?: string;
  count: number;
}

export interface AssistDetails {
  transcription?: {
    text: string;
    language: string;
    duration_s?: number;
  };
  detection?: DetectionResult;
  ocr?: {
    extracted_text: string;
    line_count: number;
  };
  vlm?: {
    answer: string;
    model: string;
  };
  frame_quality?: {
    is_usable: boolean;
    brightness_score?: number;
    issue?: string;
  };
}

export interface AssistResponse {
  request_id: string;
  mode: string;
  query_text?: string;
  answer_ar: string;
  audio_base64?: string;
  source_components: string[];
  total_latency_ms: number;
  stage_timings_ms: Record<string, number>;
  frame_id?: string;
  details?: AssistDetails;
  timestamp?: string;
}

export interface ModelComponentStatus {
  installed: boolean;
  loaded: boolean;
  device: string;
  version_or_digest?: string;
  path?: string;
  error?: string;
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
  models: {
    vlm?: ModelComponentStatus;
    detection?: ModelComponentStatus;
    ocr?: ModelComponentStatus;
    asr?: ModelComponentStatus;
    tts?: ModelComponentStatus;
  };
}

export interface HistoryItem {
  id: string;
  query: string;
  answer: string;
  time: string;
  mode: string;
}
