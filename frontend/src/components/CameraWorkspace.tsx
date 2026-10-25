import React, { useEffect, useRef } from 'react';
import type { DetectionItem } from '../types';

interface CameraWorkspaceProps {
  cameraActive: boolean;
  videoRef: React.RefObject<HTMLVideoElement>;
  canvasRef: React.RefObject<HTMLCanvasElement>;
  devices: MediaDeviceInfo[];
  selectedDeviceId: string;
  showOverlay: boolean;
  detections: DetectionItem[];
  onToggleCamera: () => void;
  onSelectDevice: (deviceId: string) => void;
  onToggleOverlay: (show: boolean) => void;
}

export const CameraWorkspace: React.FC<CameraWorkspaceProps> = ({
  cameraActive,
  videoRef,
  canvasRef,
  devices,
  selectedDeviceId,
  showOverlay,
  detections,
  onToggleCamera,
  onSelectDevice,
  onToggleOverlay,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  // Redraw bounding boxes whenever detections, overlay setting, or dimensions change
  useEffect(() => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!showOverlay || !cameraActive || !detections.length) return;

    ctx.lineWidth = 3;
    ctx.font = 'bold 16px "IBM Plex Sans Arabic", sans-serif';

    detections.forEach((item) => {
      const box = item.bbox;
      const w = box.x2 - box.x1;
      const h = box.y2 - box.y1;

      // Box stroke
      ctx.strokeStyle = '#234D43';
      ctx.strokeRect(box.x1, box.y1, w, h);

      // Label background
      const label = `${item.class_name_ar} (${Math.round(item.confidence * 100)}%)`;
      const textWidth = ctx.measureText(label).width;
      ctx.fillStyle = 'rgba(23, 37, 34, 0.88)';
      ctx.fillRect(box.x1, Math.max(0, box.y1 - 26), textWidth + 14, 26);

      // Label text
      ctx.fillStyle = '#FFFFFF';
      ctx.fillText(label, box.x1 + 6, Math.max(18, box.y1 - 7));
    });
  }, [detections, showOverlay, cameraActive, canvasRef, videoRef]);

  return (
    <section className="camera-workspace-card" aria-label="نافذة المعاينة البصرية والكاميرا">
      <div className="card-top-bar">
        <div className="card-heading-group">
          <svg className="app-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
            <circle cx="12" cy="13" r="4"></circle>
          </svg>
          <h2 className="card-heading">معاينة المشهد البصري</h2>
        </div>

        <div className="card-badges-row">
          <span className={`status-pill ${cameraActive ? 'pill-active' : 'pill-inactive'}`}>
            {cameraActive ? 'الكاميرا نشطة' : 'الكاميرا متوقفة'}
          </span>
          <span className="status-pill pill-subtle">المعالجة محلية</span>
        </div>
      </div>

      {/* Main Preview Surface with 16:9 Aspect Ratio and Dark Background */}
      <div className="camera-surface-container" ref={containerRef}>
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className={`camera-video-feed ${cameraActive ? 'is-visible' : 'is-hidden'}`}
          aria-label="بث الكاميرا المباشر"
        />

        <canvas
          ref={canvasRef}
          className={`camera-overlay-canvas ${cameraActive && showOverlay ? 'is-visible' : 'is-hidden'}`}
          aria-hidden="true"
        />

        {!cameraActive && (
          <div className="camera-empty-state">
            <svg className="empty-state-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
              <circle cx="12" cy="12" r="3"></circle>
            </svg>
            <p className="empty-state-text">
              الكاميرا متوقفة حالياً. اضغط «تشغيل الكاميرا» للمعاينة المباشرة أو ارفع صورة لتحليلها.
            </p>
          </div>
        )}
      </div>

      {/* Quiet Toolbar */}
      <div className="camera-controls-toolbar">
        <div className="toolbar-source-select">
          <label htmlFor="camera-device-select" className="sr-only">اختر مصدر الكاميرا</label>
          <select
            id="camera-device-select"
            className="device-select"
            value={selectedDeviceId}
            onChange={(e) => onSelectDevice(e.target.value)}
            disabled={devices.length <= 1}
            aria-label="اختر الكاميرا المتاحة"
          >
            {devices.length === 0 && <option value="">الكاميرا الافتراضية</option>}
            {devices.map((d, idx) => (
              <option key={d.deviceId || idx} value={d.deviceId}>
                {d.label || `الكاميرا ${idx + 1}`}
              </option>
            ))}
          </select>
        </div>

        <div className="toolbar-actions-group">
          <button
            type="button"
            className={`cam-toggle-btn ${cameraActive ? 'btn-active' : ''}`}
            onClick={onToggleCamera}
            aria-pressed={cameraActive}
          >
            <svg className="app-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <polygon points="23 7 16 12 23 17 23 7"></polygon>
              <rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect>
            </svg>
            <span>{cameraActive ? 'إيقاف الكاميرا (C)' : 'تشغيل الكاميرا (C)'}</span>
          </button>

          <label className="checkbox-toggle" htmlFor="chk-detection-overlay">
            <input
              type="checkbox"
              id="chk-detection-overlay"
              checked={showOverlay}
              onChange={(e) => onToggleOverlay(e.target.checked)}
            />
            <span>مربعات الكشف</span>
          </label>
        </div>
      </div>
    </section>
  );
};
