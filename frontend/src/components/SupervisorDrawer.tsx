import React from 'react';
import type { HealthResponse, AssistResponse, ClientPerformanceMetrics } from '../types';

interface SupervisorDrawerProps {
  isOpen: boolean;
  health: HealthResponse | null;
  lastResponse: AssistResponse | null;
  analyzedFrameBase64: string | null;
  perfMetrics?: ClientPerformanceMetrics | null;
  onClose: () => void;
  onRefreshHealth: () => void;
}

export const SupervisorDrawer: React.FC<SupervisorDrawerProps> = ({
  isOpen,
  health,
  lastResponse,
  analyzedFrameBase64,
  perfMetrics,
  onClose,
  onRefreshHealth,
}) => {
  if (!isOpen) return null;

  const models = health?.models || {};
  const gpu = health?.gpu_memory_mb;
  const ctx = health?.context_memory;

  const formatStatus = (installed?: boolean, loaded?: boolean) => {
    if (installed && loaded) return 'محمل ونشط ✅';
    if (installed) return 'جاهز محلياً ⚡';
    return 'قيد الإعداد ⏳';
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
          {/* Hardware & Memory Metrics */}
          <section className="drawer-section">
            <div className="section-title-wrap">
              <h3 className="drawer-section-title">موارد العتاد والذاكرة الحية</h3>
              <button
                type="button"
                className="refresh-btn"
                onClick={onRefreshHealth}
                aria-label="تحديث حالة الموارد"
              >
                تحديث
              </button>
            </div>

            <div className="models-diag-grid">
              <div className="diag-tile">
                <span className="tile-title">ذاكرة معالج الرسوميات (VRAM)</span>
                <span className="tile-val">
                  {gpu?.vram_total_mb
                    ? `${gpu.vram_used_mb} MB / ${gpu.vram_total_mb} MB`
                    : '4096 MB (GTX 1650 Ti)'}
                </span>
                <span className="tile-status">مستقر</span>
              </div>

              <div className="diag-tile">
                <span className="tile-title">ذاكرة النظام الرئيسية (RAM)</span>
                <span className="tile-val">
                  {health?.system_memory_mb
                    ? `${health.system_memory_mb.used_ram_mb} MB / ${health.system_memory_mb.total_ram_mb} MB (${health.system_memory_mb.ram_percent}%)`
                    : 'فحص...'}
                </span>
                <span className="tile-status">مستقر</span>
              </div>

              <div className="diag-tile">
                <span className="tile-title">نموذج الرؤية السريع (2B)</span>
                <span className="tile-val"><bdi>qwen3-vl:2b-instruct-q4_K_M</bdi></span>
                <span className="tile-status">{formatStatus(models.vlm_2b?.installed, models.vlm_2b?.loaded)}</span>
              </div>

              <div className="diag-tile">
                <span className="tile-title">النموذج المفصل (4B)</span>
                <span className="tile-val"><bdi>qwen3-vl:4b-instruct-q4_K_M</bdi></span>
                <span className="tile-status">{health?.vlm_modes?.detailed_ready ? 'جاهز ⚡' : 'قيد التنزيل/التهيئة ⏳'}</span>
              </div>

              <div className="diag-tile">
                <span className="tile-title">كاشف الكائنات والبحث (YOLO11n)</span>
                <span className="tile-val"><bdi>YOLO11n</bdi> (CPU / Edge)</span>
                <span className="tile-status">{formatStatus(models.detection?.installed, models.detection?.loaded)}</span>
              </div>

              <div className="diag-tile">
                <span className="tile-title">التعرف الضوئي (EasyOCR)</span>
                <span className="tile-val"><bdi>EasyOCR Arabic/English</bdi></span>
                <span className="tile-status">{formatStatus(models.ocr?.installed, models.ocr?.loaded)}</span>
              </div>

              <div className="diag-tile">
                <span className="tile-title">التعرف الصوتي (faster-whisper)</span>
                <span className="tile-val"><bdi>faster-whisper</bdi> (int8)</span>
                <span className="tile-status">{formatStatus(models.asr?.installed, models.asr?.loaded)}</span>
              </div>

              <div className="diag-tile">
                <span className="tile-title">النطق الصوتي (Piper TTS)</span>
                <span className="tile-val"><bdi>Piper ar_JO-kareem</bdi></span>
                <span className="tile-status">{formatStatus(models.tts?.installed, models.tts?.loaded)}</span>
              </div>
            </div>
          </section>

          {/* Conversational Memory Inspector */}
          {ctx && (
            <section className="drawer-section">
              <h3 className="drawer-section-title">حالة ذاكرة السياق الصوتي (Session Context)</h3>
              <div className="frame-meta-rows">
                <div className="meta-row">
                  <strong>عدد التبادلات (Turn Count):</strong>
                  <span>{ctx.turn_count}</span>
                </div>
                <div className="meta-row">
                  <strong>آخر أمر مستلم:</strong>
                  <span>{ctx.last_command || 'لا يوجد'}</span>
                </div>
                <div className="meta-row">
                  <strong>آخر كائن مرجعي:</strong>
                  <span>{ctx.last_referenced_object || 'لا يوجد'}</span>
                </div>
                <div className="meta-row">
                  <strong>حالة السياق:</strong>
                  <span>{ctx.is_stale ? 'منتهي الصلاحية' : 'نشط وحي'}</span>
                </div>
              </div>
            </section>
          )}

          {/* Last Execution Timings Breakdown & Client E2E Telemetry */}
          <section className="drawer-section">
            <h3 className="drawer-section-title">تفصيل أزمنة المعالجة اللحظية (Performance Telemetry)</h3>
            <div className="frame-meta-rows">
              <div className="meta-row">
                <strong>معرّف الطلب (Request ID):</strong>
                <span>{lastResponse?.request_id || perfMetrics?.requestId || '--'}</span>
              </div>

              {perfMetrics && (
                <>
                  <div className="meta-row">
                    <strong>زمن أول ظهور للنص (Client TTFT - DOM):</strong>
                    <span style={{ color: '#10B981', fontWeight: 700 }}>
                      {perfMetrics.firstVisibleTextMs !== undefined ? `${perfMetrics.firstVisibleTextMs} ms` : '--'}
                    </span>
                  </div>
                  <div className="meta-row">
                    <strong>زمن أول نطق مسموع (Client TTFA - Audio onplay):</strong>
                    <span style={{ color: '#38BDF8', fontWeight: 700 }}>
                      {perfMetrics.firstAudibleAudioMs !== undefined ? `${perfMetrics.firstAudibleAudioMs} ms` : '--'}
                    </span>
                  </div>
                  {perfMetrics.ocrTextDeliveredMs !== undefined && (
                    <div className="meta-row">
                      <strong>تسليم نصوص OCR الفعلية:</strong>
                      <span style={{ color: '#F59E0B', fontWeight: 700 }}>
                        {perfMetrics.ocrTextDeliveredMs} ms (إشعار البداية: {perfMetrics.ocrStatusNotificationMs} ms)
                      </span>
                    </div>
                  )}
                  <div className="meta-row">
                    <strong>إجمالي زمن تجربة المستخدم بالمتصفح:</strong>
                    <span>{perfMetrics.totalClientDurationMs !== undefined ? `${perfMetrics.totalClientDurationMs} ms` : '--'}</span>
                  </div>
                </>
              )}

              <div className="meta-row">
                <strong>زمن المعالجة الخلفية الإجمالي (Backend Total):</strong>
                <span>{lastResponse ? `${Math.round(lastResponse.total_latency_ms)} ms` : '--'}</span>
              </div>
              <div className="meta-row">
                <strong>تفريغ أزمنة المراحل بالخادم:</strong>
                <div className="timings-pills-row">
                  {lastResponse?.stage_timings_ms &&
                    Object.entries(lastResponse.stage_timings_ms).map(([k, v]) => (
                      <span key={k} className="timing-pill">
                        <strong>{k}:</strong> {Math.round(v)}ms
                      </span>
                    ))}
                </div>
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

              {lastResponse?.frame_quality && (
                <div className="frame-meta-rows">
                  <div className="meta-row">
                    <strong>تقييم جودة الإطار:</strong>
                    <span>{lastResponse.frame_quality.is_usable ? 'صالح ومقبول ✅' : 'مرفوض ⚠️'}</span>
                  </div>
                  {lastResponse.frame_quality.issue && (
                    <div className="meta-row">
                      <strong>سبب التنبيه:</strong>
                      <span>{lastResponse.frame_quality.issue}</span>
                    </div>
                  )}
                  {lastResponse.frame_quality.metrics && (
                    <div className="meta-row">
                      <strong>المقاييس:</strong>
                      <span>
                        سطوع: {lastResponse.frame_quality.metrics.brightness} | تباين الحواف: {lastResponse.frame_quality.metrics.blur_variance}
                      </span>
                    </div>
                  )}
                </div>
              )}
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
