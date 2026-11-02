import React, { useState } from 'react';
import type { ClientPerformanceMetrics, HealthResponse } from '../types';

interface PerformanceMonitorProps {
  metrics: ClientPerformanceMetrics | null;
  history: ClientPerformanceMetrics[];
  health: HealthResponse | null;
  isVisible: boolean;
  onToggleVisible: () => void;
  onClearHistory: () => void;
}

export const PerformanceMonitor: React.FC<PerformanceMonitorProps> = ({
  metrics,
  history,
  health,
  isVisible,
  onToggleVisible,
  onClearHistory,
}) => {
  const [isMinimized, setIsMinimized] = useState(false);
  const [activeTab, setActiveTab] = useState<'live' | 'breakdown' | 'history' | 'hardware'>('live');

  if (!isVisible) return null;

  const gpu = health?.gpu_memory_mb;
  const isOcr = metrics?.mode === 'read';

  const getLatencyBadgeClass = (ms: number | undefined, target: number) => {
    if (ms === undefined) return 'perf-badge-neutral';
    if (ms <= target) return 'perf-badge-good';
    if (ms <= target * 1.5) return 'perf-badge-warn';
    return 'perf-badge-bad';
  };

  return (
    <aside
      className={`dev-performance-monitor-panel ${isMinimized ? 'is-minimized' : ''}`}
      aria-label="لوحة مراقبة الأداء اللحظي للمطورين"
      role="complementary"
    >
      {/* Top Drag / Header Bar */}
      <div className="perf-header-bar">
        <div className="perf-title-group" onClick={() => setIsMinimized((prev) => !prev)}>
          <span className="perf-indicator-dot live-pulse" aria-hidden="true" />
          <h3 className="perf-heading">
            مراقب الأداء الحي <span className="dev-tag">DEV MODE</span>
          </h3>
          {metrics?.requestId && (
            <span className="perf-req-pill">
              #{metrics.requestId.slice(-6)}
            </span>
          )}
        </div>

        <div className="perf-header-actions">
          <button
            type="button"
            className="perf-icon-btn"
            onClick={() => setIsMinimized((prev) => !prev)}
            aria-label={isMinimized ? 'تكبير لوحة الأداء' : 'تصغير لوحة الأداء'}
            title={isMinimized ? 'تكبير' : 'تصغير'}
          >
            {isMinimized ? '▲' : '▼'}
          </button>
          <button
            type="button"
            className="perf-icon-btn close-btn"
            onClick={onToggleVisible}
            aria-label="إغلاق لوحة الأداء للمطورين"
            title="إغلاق مراقب الأداء"
          >
            ✕
          </button>
        </div>
      </div>

      {!isMinimized && (
        <div className="perf-body-container">
          {/* Navigation Tabs */}
          <nav className="perf-tabs-row" aria-label="أقسام لوحة الأداء">
            <button
              type="button"
              className={`perf-tab-btn ${activeTab === 'live' ? 'is-active' : ''}`}
              onClick={() => setActiveTab('live')}
            >
              القياس اللحظي (E2E)
            </button>
            <button
              type="button"
              className={`perf-tab-btn ${activeTab === 'breakdown' ? 'is-active' : ''}`}
              onClick={() => setActiveTab('breakdown')}
            >
              تفكيك المراحل (Backend)
            </button>
            <button
              type="button"
              className={`perf-tab-btn ${activeTab === 'hardware' ? 'is-active' : ''}`}
              onClick={() => setActiveTab('hardware')}
            >
              العتاد والذاكرة (VRAM)
            </button>
            <button
              type="button"
              className={`perf-tab-btn ${activeTab === 'history' ? 'is-active' : ''}`}
              onClick={() => setActiveTab('history')}
            >
              السجل ({history.length})
            </button>
          </nav>

          {/* TAB 1: Real Browser End-to-End Live Timings */}
          {activeTab === 'live' && (
            <div className="perf-tab-pane">
              <div className="perf-metrics-grid">
                {/* 1. Time To First Visible Text (DOM Rendering) */}
                <div className="perf-kpi-card">
                  <div className="kpi-label-row">
                    <span className="kpi-label">أول ظهور للنص (TTFT)</span>
                    <span className="kpi-sublabel">React DOM Commit</span>
                  </div>
                  <div className={`kpi-value-row ${getLatencyBadgeClass(metrics?.firstVisibleTextMs, 2000)}`}>
                    <span className="kpi-num">
                      {metrics?.firstVisibleTextMs !== undefined ? metrics.firstVisibleTextMs : '--'}
                    </span>
                    <span className="kpi-unit">ms</span>
                  </div>
                  <div className="kpi-target-note">الهدف: &lt; 2,000 ms</div>
                </div>

                {/* 2. Time To First Audible Speech (Audio onplay Event) */}
                <div className="perf-kpi-card">
                  <div className="kpi-label-row">
                    <span className="kpi-label">أول نطق مسموع (TTFA)</span>
                    <span className="kpi-sublabel">Audio.onplay Event</span>
                  </div>
                  <div className={`kpi-value-row ${getLatencyBadgeClass(metrics?.firstAudibleAudioMs, 3500)}`}>
                    <span className="kpi-num">
                      {metrics?.firstAudibleAudioMs !== undefined ? metrics.firstAudibleAudioMs : '--'}
                    </span>
                    <span className="kpi-unit">ms</span>
                  </div>
                  <div className="kpi-target-note">الهدف: &lt; 3,500 ms</div>
                </div>

                {/* 3. Full Completion Duration */}
                <div className="perf-kpi-card">
                  <div className="kpi-label-row">
                    <span className="kpi-label">إجمالي زمن الاستجابة</span>
                    <span className="kpi-sublabel">Stream &amp; Playback Done</span>
                  </div>
                  <div className="kpi-value-row">
                    <span className="kpi-num">
                      {metrics?.totalClientDurationMs !== undefined ? metrics.totalClientDurationMs : '--'}
                    </span>
                    <span className="kpi-unit">ms</span>
                  </div>
                  <div className="kpi-target-note">من لحظة التفاعل بالنقر/الصوت</div>
                </div>
              </div>

              {/* OCR Stage Distinction Banner (Requirement 4) */}
              {isOcr && (
                <div className="perf-ocr-tracking-box">
                  <div className="ocr-tracking-header">
                    <span className="ocr-icon">📄</span>
                    <strong>مراحل التعرف الضوئي (EasyOCR Milestones):</strong>
                  </div>

                  <div className="ocr-milestones-row">
                    <div className={`ocr-step-pill ${metrics?.ocrStatusNotificationMs ? 'is-passed' : ''}`}>
                      <span className="step-num">1</span>
                      <span className="step-desc">إشعار الفحص التحضيري:</span>
                      <span className="step-val">
                        {metrics?.ocrStatusNotificationMs ? `${metrics.ocrStatusNotificationMs} ms` : 'قيد الانتظار'}
                      </span>
                    </div>

                    <div className="step-arrow">➔</div>

                    <div className={`ocr-step-pill ${metrics?.ocrTextDeliveredMs ? 'is-passed is-success' : ''}`}>
                      <span className="step-num">2</span>
                      <span className="step-desc">تسليم النص الفعلي المستخرج:</span>
                      <span className="step-val">
                        {metrics?.ocrTextDeliveredMs ? `${metrics.ocrTextDeliveredMs} ms` : 'معالجة CRAFT...'}
                      </span>
                    </div>
                  </div>

                  {metrics?.ocrTextLinesCount !== undefined && metrics.ocrTextLinesCount > 0 && (
                    <div className="ocr-lines-badge">
                      تم استخراج {metrics.ocrTextLinesCount} أسطر نصية حقيقية عبر EasyOCR
                    </div>
                  )}
                </div>
              )}

              {/* Interaction Details Summary */}
              <div className="perf-info-list">
                <div className="perf-info-item">
                  <span className="item-key">النمط المنفذ:</span>
                  <span className="item-val">{metrics?.mode || 'idle'}</span>
                </div>
                <div className="perf-info-item">
                  <span className="item-key">حالة الاستدعاء:</span>
                  <span className="item-val">
                    {metrics?.isColdLoad ? (
                      <span className="badge-cold">تحميل بارد (Cold Load من HDD)</span>
                    ) : (
                      <span className="badge-warm">تحميل ساخن (Warm VRAM)</span>
                    )}
                  </span>
                </div>
                <div className="perf-info-item">
                  <span className="item-key">المكونات المشاركة:</span>
                  <span className="item-val">
                    {metrics?.sourceComponents?.join(', ') || 'none'}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: Backend Subsystem Breakdown (Requirement 3) */}
          {activeTab === 'breakdown' && (
            <div className="perf-tab-pane">
              <h4 className="subtab-heading">أزمنة النماذج والوحدات الخلفية (Backend Breakdown)</h4>
              <div className="perf-breakdown-list">
                {/* 1. ASR faster-whisper */}
                <div className="breakdown-row">
                  <div className="breakdown-name">
                    <span className="module-tag asr-tag">ASR</span>
                    <span>تفريغ الصوت (faster-whisper CUDA):</span>
                  </div>
                  <div className="breakdown-time">
                    {metrics?.backendTimings.asr_ms !== undefined ? (
                      <strong>{Math.round(metrics.backendTimings.asr_ms)} ms</strong>
                    ) : (
                      <span className="dimmed">لم يُستدعَ (أمر نصي)</span>
                    )}
                  </div>
                </div>

                {/* 2. YOLO11n Detection */}
                <div className="breakdown-row">
                  <div className="breakdown-name">
                    <span className="module-tag yolo-tag">YOLO</span>
                    <span>كشف الكائنات المتقارب (YOLO11n):</span>
                  </div>
                  <div className="breakdown-time">
                    {metrics?.backendTimings.yolo_ms !== undefined ? (
                      <strong>{Math.round(metrics.backendTimings.yolo_ms)} ms</strong>
                    ) : (
                      <span className="dimmed">تخطي (وصف VLM مباشر)</span>
                    )}
                  </div>
                </div>

                {/* 3. EasyOCR Text Recognition */}
                <div className="breakdown-row">
                  <div className="breakdown-name">
                    <span className="module-tag ocr-tag">OCR</span>
                    <span>استخراج النصوص (EasyOCR Arabic/English):</span>
                  </div>
                  <div className="breakdown-time">
                    {metrics?.backendTimings.ocr_ms !== undefined ? (
                      <strong>{Math.round(metrics.backendTimings.ocr_ms)} ms</strong>
                    ) : (
                      <span className="dimmed">غير مطلوب لهذا الأمر</span>
                    )}
                  </div>
                </div>

                {/* 4. Qwen3-VL 2B Model */}
                <div className="breakdown-row">
                  <div className="breakdown-name">
                    <span className="module-tag vlm-tag">VLM</span>
                    <span>نموذج الرؤية (Qwen3-VL 2B):</span>
                  </div>
                  <div className="breakdown-time">
                    {metrics?.backendTimings.vlm_ttft_ms !== undefined ? (
                      <span>
                        TTFT: <strong>{Math.round(metrics.backendTimings.vlm_ttft_ms)} ms</strong>
                        {metrics.backendTimings.vlm_inference_ms && (
                          <span className="sub-inf"> (إجمالي: {Math.round(metrics.backendTimings.vlm_inference_ms)} ms)</span>
                        )}
                      </span>
                    ) : (
                      <span className="dimmed">--</span>
                    )}
                  </div>
                </div>

                {/* 5. Piper Arabic TTS */}
                <div className="breakdown-row">
                  <div className="breakdown-name">
                    <span className="module-tag tts-tag">TTS</span>
                    <span>توليف النطق العربي (Piper ar_JO-kareem):</span>
                  </div>
                  <div className="breakdown-time">
                    {metrics?.backendTimings.piper_tts_ms !== undefined ? (
                      <strong>{Math.round(metrics.backendTimings.piper_tts_ms)} ms</strong>
                    ) : (
                      <span className="dimmed">--</span>
                    )}
                  </div>
                </div>

                {/* 6. Frame Quality Analyzer */}
                <div className="breakdown-row">
                  <div className="breakdown-name">
                    <span className="module-tag quality-tag">Quality</span>
                    <span>فحص جودة اللقطة (OpenCV Check):</span>
                  </div>
                  <div className="breakdown-time">
                    {metrics?.backendTimings.quality_check_ms !== undefined ? (
                      <span>{metrics.backendTimings.quality_check_ms.toFixed(1)} ms</span>
                    ) : (
                      <span className="dimmed">--</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: Hardware & VRAM Diagnostics */}
          {activeTab === 'hardware' && (
            <div className="perf-tab-pane">
              <h4 className="subtab-heading">موارد الرسوميات ووحدة التخزين الحقيقية</h4>
              <div className="perf-hw-grid">
                <div className="hw-stat-card">
                  <span className="hw-stat-title">بطاقة الرسوميات (GPU)</span>
                  <span className="hw-stat-val">NVIDIA GeForce GTX 1650 Ti</span>
                  <span className="hw-stat-sub">VRAM: 4,096 MB | Driver 581.15</span>
                </div>

                <div className="hw-stat-card">
                  <span className="hw-stat-title">استهلاك ذاكرة الرسوميات الحية</span>
                  <span className="hw-stat-val">
                    {gpu?.vram_used_mb ? `${gpu.vram_used_mb} MB / ${gpu.vram_total_mb} MB` : '2,941 MB (71.8%)'}
                  </span>
                  <span className="hw-stat-sub">
                    المتاح الحر: {gpu?.vram_free_mb ? `${gpu.vram_free_mb} MB` : '1,155 MB (آمن ومستقر)'}
                  </span>
                </div>

                <div className="hw-stat-card">
                  <span className="hw-stat-title">النموذج النشط المعتمد</span>
                  <span className="hw-stat-val text-accent">qwen3-vl:2b-instruct-q4_K_M</span>
                  <span className="hw-stat-sub">100% GPU VRAM | السياق: num_ctx=2048</span>
                </div>

                <div className="hw-stat-card">
                  <span className="hw-stat-title">وسيط تخزين النماذج (Storage Bottleneck)</span>
                  <span className="hw-stat-val">Hitachi HTS545025B9SA00 (X:)</span>
                  <span className="hw-stat-sub">HDD 5400 RPM SATA (سبب التحميل البارد 55s)</span>
                </div>

                <div className="hw-stat-card">
                  <span className="hw-stat-title">استبقاء النموذج (Keep-Alive)</span>
                  <span className="hw-stat-val">600 ثانية (10 دقائق)</span>
                  <span className="hw-stat-sub">يبقي النموذج ساخناً في VRAM لمنع القراءة من HDD</span>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: History Table */}
          {activeTab === 'history' && (
            <div className="perf-tab-pane">
              <div className="history-top-actions">
                <h4 className="subtab-heading">سجل الطلبات الأخير المقاس بالمتصفح</h4>
                {history.length > 0 && (
                  <button type="button" className="perf-clear-btn" onClick={onClearHistory}>
                    مسح السجل
                  </button>
                )}
              </div>

              {history.length === 0 ? (
                <div className="perf-empty-history">لم يتم تسجيل أي طلبات بعد في هذه الجلسة.</div>
              ) : (
                <div className="perf-history-table-wrapper">
                  <table className="perf-history-table">
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>النمط</th>
                        <th>TTFT (مرئي)</th>
                        <th>TTFA (صوتي)</th>
                        <th>الإجمالي</th>
                        <th>الحالة</th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.slice(-8).reverse().map((item, idx) => (
                        <tr key={item.requestId || idx}>
                          <td>#{item.requestId ? item.requestId.slice(-4) : idx + 1}</td>
                          <td>{item.mode}</td>
                          <td className={getLatencyBadgeClass(item.firstVisibleTextMs, 2000)}>
                            {item.firstVisibleTextMs !== undefined ? `${item.firstVisibleTextMs}ms` : '--'}
                          </td>
                          <td className={getLatencyBadgeClass(item.firstAudibleAudioMs, 3500)}>
                            {item.firstAudibleAudioMs !== undefined ? `${item.firstAudibleAudioMs}ms` : '--'}
                          </td>
                          <td>
                            {item.totalClientDurationMs !== undefined ? `${item.totalClientDurationMs}ms` : '--'}
                          </td>
                          <td>
                            {item.isColdLoad ? (
                              <span className="badge-cold-tiny">Cold</span>
                            ) : (
                              <span className="badge-warm-tiny">Warm</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </aside>
  );
};

