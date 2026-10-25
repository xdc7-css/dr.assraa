import React, { useState } from 'react';
import type { AssistResponse, AppLifecycleState } from '../types';

interface ResponseCardProps {
  lifecycleState: AppLifecycleState;
  response: AssistResponse | null;
  hasAudio: boolean;
  isPlayingAudio: boolean;
  onReplayAudio: () => void;
  onRepeatAnswer: () => void;
}

export const ResponseCard: React.FC<ResponseCardProps> = ({
  lifecycleState,
  response,
  hasAudio,
  isPlayingAudio,
  onReplayAudio,
  onRepeatAnswer,
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

    if (lifecycleState === 'analyzing') {
      return (
        <div className="response-state-msg is-processing">
          <span className="dot-pulse" aria-hidden="true" />
          <span>جاري تحليل المشهد البصري بواسطة النماذج المحلية...</span>
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

    if (response?.answer_ar) {
      return (
        <div className="response-answer-text" tabIndex={0} role="region" aria-label="نص إجابة المساعد">
          {response.answer_ar}
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
          </div>
        )}
      </div>

      <div className="response-surface-viewport">
        {renderContent()}
      </div>
    </section>
  );
};
