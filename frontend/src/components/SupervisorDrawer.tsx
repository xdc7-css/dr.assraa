import React from 'react';
import type { HealthResponse, AssistResponse } from '../types';

interface SupervisorDrawerProps {
  isOpen: boolean;
  health: HealthResponse | null;
  lastResponse: AssistResponse | null;
  analyzedFrameBase64: string | null;
  onClose: () => void;
  onRefreshHealth: () => void;
}

export const SupervisorDrawer: React.FC<SupervisorDrawerProps> = ({
  isOpen,
  health,
  lastResponse,
  analyzedFrameBase64,
  onClose,
  onRefreshHealth,
}) => {
  if (!isOpen) return null;

  const models = health?.models || {};

  const formatStatus = (installed?: boolean, loaded?: boolean) => {
    if (installed && loaded) return 'محمل ونشط ✅';
    if (installed) return 'مثبت (محلي) ⚡';
    return 'غير مثبت ❌';
  };

  return (
    <div className="drawer-backdrop" onClick={onClose} role="presentation">
      <div
        className="supervisor-drawer-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="supervisor-drawer-heading"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="drawer-header-row">
          <div className="drawer-title-group">
            <svg className="app-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <circle cx="12" cy="12" r="3"></circle>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
            </svg>
            <h2 id="supervisor-drawer-heading" className="drawer-heading-text">
              لوحة التشخيص الهندسي وحالة النماذج
            </h2>
          </div>

          <button
            type="button"
            className="modal-close-icon-btn"
            onClick={onClose}
            aria-label="إغلاق لوحة التشخيص"
          >
            <svg className="app-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <div className="drawer-scroll-body">
          {/* Models Health Matrix */}
          <section className="drawer-section">
            <div className="section-title-wrap">
              <h3 className="drawer-section-title">حالة النماذج المحلية العاملة</h3>
              <button
                type="button"
                className="refresh-btn"
                onClick={onRefreshHealth}
                aria-label="تحديث حالة النماذج"
              >
                تحديث
              </button>
            </div>

            <div className="models-diag-grid">
              <div className="diag-tile">
                <span className="tile-title">نموذج الرؤية واللغة (VLM)</span>
                <span className="tile-val"><bdi>qwen3-vl:2b-instruct-q4_K_M</bdi></span>
                <span className="tile-status">{formatStatus(models.vlm?.installed, models.vlm?.loaded)}</span>
              </div>

              <div className="diag-tile">
                <span className="tile-title">كاشف الكائنات (Detector)</span>
                <span className="tile-val"><bdi>YOLO11n</bdi> (CPU / Edge)</span>
                <span className="tile-status">{formatStatus(models.detection?.installed, models.detection?.loaded)}</span>
              </div>

              <div className="diag-tile">
                <span className="tile-title">التعرف الضوئي (OCR)</span>
                <span className="tile-val"><bdi>EasyOCR Arabic/English</bdi></span>
                <span className="tile-status">{formatStatus(models.ocr?.installed, models.ocr?.loaded)}</span>
              </div>

              <div className="diag-tile">
                <span className="tile-title">التعرف الصوتي (ASR)</span>
                <span className="tile-val"><bdi>faster-whisper</bdi> (int8)</span>
                <span className="tile-status">{formatStatus(models.asr?.installed, models.asr?.loaded)}</span>
              </div>

              <div className="diag-tile">
                <span className="tile-title">النطق الآلي (TTS)</span>
                <span className="tile-val"><bdi>Piper ar_JO-kareem</bdi></span>
                <span className="tile-status">{formatStatus(models.tts?.installed, models.tts?.loaded)}</span>
              </div>

              <div className="diag-tile">
                <span className="tile-title">ذاكرة النظام المتاحة (RAM)</span>
                <span className="tile-val">
                  {health?.system_memory_mb
                    ? `${health.system_memory_mb.used_ram_mb} MB / ${health.system_memory_mb.total_ram_mb} MB (${health.system_memory_mb.ram_percent}%)`
                    : 'فحص...'}
                </span>
                <span className="tile-status">مستقر</span>
              </div>
            </div>
          </section>

          {/* Exact Analyzed Frame Inspector */}
          <section className="drawer-section">
            <h3 className="drawer-section-title">الإطار البصري الفعلي المحلل بالطلب الأخير</h3>
            <div className="frame-inspector-container">
              <div className="frame-preview-box">
                {analyzedFrameBase64 ? (
                  <img
                    src={analyzedFrameBase64}
                    alt="الإطار البصري الفعلي المحلل بالطلب الأخير"
                    className="inspected-frame-img"
                  />
                ) : (
                  <div className="frame-placeholder-txt">
                    لم يتم التقاط أو تحليل إطار بعد.
                  </div>
                )}
              </div>

              <div className="frame-meta-rows">
                <div className="meta-row">
                  <strong>معرّف الطلب (Request ID):</strong>
                  <span>{lastResponse?.request_id || '--'}</span>
                </div>
                <div className="meta-row">
                  <strong>معرّف الإطار (Frame ID):</strong>
                  <span>{lastResponse?.frame_id || '--'}</span>
                </div>
                <div className="meta-row">
                  <strong>توقيت المعالجة:</strong>
                  <span>{lastResponse?.timestamp || '--'}</span>
                </div>
                <div className="meta-row">
                  <strong>زمن المعالجة الإجمالي:</strong>
                  <span>{lastResponse ? `${lastResponse.total_latency_ms} ms` : '--'}</span>
                </div>
                <div className="meta-row">
                  <strong>تفصيل أزمنة المراحل:</strong>
                  <span>
                    {lastResponse?.stage_timings_ms
                      ? Object.entries(lastResponse.stage_timings_ms)
                          .map(([k, v]) => `${k}: ${v}ms`)
                          .join(', ')
                      : '--'}
                  </span>
                </div>
              </div>
            </div>
          </section>

          {/* Direct API Verification Endpoints */}
          <section className="drawer-section">
            <h3 className="drawer-section-title">روابط التحقق الرسمية (JSON Endpoints)</h3>
            <div className="api-links-row">
              <a href="/api/health" target="_blank" rel="noreferrer" className="api-link-btn">
                فحص صحة النظام (/api/health)
              </a>
              <a href="/api/models" target="_blank" rel="noreferrer" className="api-link-btn">
                سجل النماذج المعتمدة (/api/models)
              </a>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};
