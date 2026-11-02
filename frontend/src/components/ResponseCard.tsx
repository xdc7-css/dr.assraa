import React, { useState } from 'react';
import type { AssistResponse, AppLifecycleState } from '../types';

interface ResponseCardProps {
  lifecycleState: AppLifecycleState;
  response: AssistResponse | null;
  hasAudio: boolean;
  isPlayingAudio: boolean;
  ocrState?: 'none' | 'processing_notice' | 'text_delivered';
  onReplayAudio: () => void;
  onRepeatAnswer: () => void;
  onShortenAnswer: () => void;
  onOverrideQuality?: () => void;
}

export const ResponseCard: React.FC<ResponseCardProps> = ({
  lifecycleState,
  response,
  hasAudio,
  isPlayingAudio,
  ocrState = 'none',
  onReplayAudio,
  onRepeatAnswer,
  onShortenAnswer,
  onOverrideQuality,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!response?.answer_ar) return;
    try {
      await navigator.clipboard.writeText(response.answer_ar);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.warn('Clipboard write failed:', err);
    }
  };

  const isQualityIssue = Boolean(response?.frame_quality && !response.frame_quality.is_usable);

  const renderContent = () => {
    if (lifecycleState === 'listening') {
      return (
        <div className="response-state-msg is-listening">
          <span className="dot-pulse" aria-hidden="true" />
          <span>جاري الاستماع إلى صوتك الآن... تحدث بوضوح.</span>
        </div>
      );
    }

    if (lifecycleState === 'transcribing') {
      return (
        <div className="response-state-msg is-processing">
          <span className="dot-pulse" aria-hidden="true" />
          <span>جاري تحويل التسجيل الصوتي إلى نص محلياً...</span>
        </div>
      );
    }

    if (lifecycleState === 'cancelled') {
      return (
        <div className="response-state-msg is-cancelled">
          <span>تم إيقاف الصوت وإلغاء الطلب بنجاح.</span>
        </div>
      );
    }

    if (lifecycleState === 'error') {
      return (
        <div className="response-state-msg is-error">
          <span>تعذر إكمال المعالجة. يرجى التأكد من تشغيل النماذج وإعادة المحاولة.</span>
        </div>
      );
    }

    // Quality guidance warning box
    if (isQualityIssue && response?.frame_quality) {
      return (
        <div className="quality-guidance-card" role="alert" aria-live="assertive">
          <div className="quality-warning-header">
            <span className="warning-icon" aria-hidden="true">⚠️</span>
            <span className="warning-title">إرشاد جودة الصورة واللقطة</span>
          </div>
          <p className="quality-advice-text">
            {response.frame_quality.advice_ar || response.answer_ar}
          </p>
          {onOverrideQuality && (
            <button
              type="button"
              className="quality-override-btn"
              onClick={onOverrideQuality}
              aria-label="تجاهل تنبيه الجودة وتحليل الصورة الحالية على أي حال"
            >
              تجاهل التحذير والمتابعة بالتحليل ⚡
            </button>
          )}
        </div>
      );
    }

    // Immediate Streaming Arabic Answer Display
    if (response?.answer_ar) {
      return (
        <div className="response-content-wrapper">
          <div className="response-meta-badge-row">
            {response.model_mode && (
              <span className={`model-mode-badge mode-${response.model_mode}`}>
                {response.model_mode === 'detailed' ? '🔍 وصف مفصّل (2B-Detailed)' : '⚡ سريع (2B)'}
              </span>
            )}
            {/* Distinct OCR Milestones Indicator */}
            {response.mode === 'read' && (
              ocrState === 'text_delivered' || response.answer_ar.includes('النص المكتوب هو') ? (
                <span className="ocr-milestone-badge ocr-delivered-badge" title="تم تسليم نصوص المستند الفعلية بنجاح">
                  📄 تم استخراج النصوص الفعلية
                </span>
              ) : (
                <span className="ocr-milestone-badge ocr-notice-badge" title="إشعار بدء فحص EasyOCR">
                  ⏳ جاري استخراج النصوص...
                </span>
              )
            )}
            {lifecycleState === 'analyzing' && (
              <span className="streaming-live-pill" aria-live="polite">
                <span className="dot-pulse" aria-hidden="true" />
                <span>جاري التدفق اللحظي...</span>
              </span>
            )}
            {response.total_latency_ms > 0 && lifecycleState !== 'analyzing' && (
              <span className="latency-badge">{Math.round(response.total_latency_ms)} ms</span>
            )}
          </div>

          <div className="response-answer-text" tabIndex={0} role="region" aria-label="نص إجابة المساعد">
            {response.answer_ar}
            {lifecycleState === 'analyzing' && <span className="typing-cursor" aria-hidden="true">▌</span>}
          </div>
        </div>
      );
    }

    if (lifecycleState === 'analyzing') {
      return (
        <div className="response-state-msg is-processing">
          <span className="dot-pulse" aria-hidden="true" />
          <span>جاري تحليل المشهد البصري بواسطة النماذج المحلية...</span>
        </div>
      );
    }

    // Default honest empty state
    return (
      <div className="response-empty-state">
        <p className="empty-prompt">
          المساعد بانتظار طلبك. اضغط زر «تحدث مع المساعد» أو اختر أحد الأوامر لبدء المعاينة والتحليل.
        </p>
      </div>
    );
  };

  return (
    <section className="assistant-response-card" aria-label="منطقة إجابة المساعد">
      <div className="card-top-bar">
        <div className="card-heading-group">
          <svg className="app-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
          <h2 className="card-heading">إجابة المساعد</h2>
        </div>

        {response?.answer_ar && (
          <div className="response-action-buttons">
            {hasAudio && (
              <button
                type="button"
                className={`secondary-tool-btn ${isPlayingAudio ? 'is-playing' : ''}`}
                onClick={onReplayAudio}
                aria-label="إعادة الاستماع للإجابة الصوتية"
              >
                <svg className="app-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                  <path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path>
                  <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
                </svg>
                <span>{isPlayingAudio ? 'أتحدث...' : 'استمع للإجابة'}</span>
              </button>
            )}

            <button
              type="button"
              className="secondary-tool-btn"
              onClick={handleCopy}
              aria-label="نسخ نص الإجابة إلى الحافظة"
            >
              <svg className="app-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
              <span>{copied ? 'تم النسخ ✓' : 'نسخ النص'}</span>
            </button>

            <button
              type="button"
              className="secondary-tool-btn"
              onClick={onRepeatAnswer}
              aria-label="إعادة نطق الإجابة الأخيرة (مفتاح A)"
            >
              <svg className="app-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <polyline points="1 4 1 10 7 10"></polyline>
                <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path>
              </svg>
              <span>كرر (A)</span>
            </button>

            <button
              type="button"
              className="secondary-tool-btn"
              onClick={onShortenAnswer}
              aria-label="اختصر الجواب السابق"
            >
              <span>اختصر</span>
            </button>
          </div>
        )}
      </div>

      <div className="response-surface-viewport">
        {renderContent()}
      </div>
    </section>
  );
};
