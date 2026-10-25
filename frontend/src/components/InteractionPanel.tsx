import React, { useState } from 'react';
import type { AppLifecycleState } from '../types';

interface InteractionPanelProps {
  lifecycleState: AppLifecycleState;
  isRecording: boolean;
  isPlayingAudio: boolean;
  recognizedQuery: string | null;
  onStartVoice: () => void;
  onStopVoice: () => void;
  onQuickAction: (mode: 'describe' | 'read' | 'find' | 'repeat', param?: string) => void;
  onSendTextQuery: (text: string) => void;
  onStopAll: () => void;
  onFileUpload: (file: File) => void;
}

export const InteractionPanel: React.FC<InteractionPanelProps> = ({
  lifecycleState,
  isRecording,
  isPlayingAudio,
  recognizedQuery,
  onStartVoice,
  onStopVoice,
  onQuickAction,
  onSendTextQuery,
  onStopAll,
  onFileUpload,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [textQuery, setTextQuery] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);

  const isBusy =
    lifecycleState === 'listening' ||
    lifecycleState === 'transcribing' ||
    lifecycleState === 'analyzing' ||
    lifecycleState === 'speaking' ||
    isRecording ||
    isPlayingAudio;

  const handleVoiceToggle = () => {
    if (isRecording) {
      onStopVoice();
    } else {
      onStartVoice();
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const term = searchTerm.trim() || 'قنينة';
    onQuickAction('find', term);
  };

  const handleTextSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (textQuery.trim()) {
      onSendTextQuery(textQuery.trim());
      setTextQuery('');
    }
  };

  const getVoiceHint = () => {
    if (isRecording || lifecycleState === 'listening') {
      return 'أستمع إليك الآن... تحدث بوضوح ثم اضغط للإنهاء';
    }
    if (lifecycleState === 'transcribing') {
      return 'جاري تحويل الصوت إلى نص...';
    }
    if (lifecycleState === 'analyzing') {
      return 'جاري تحليل الصورة والمشهد بالنماذج المحلية...';
    }
    if (isPlayingAudio || lifecycleState === 'speaking') {
      return 'المساعد يتحدث الآن...';
    }
    return 'اضغط للبدء، واضغط ثانية للإنهاء (أو استمر بالضغط على المسافة)';
  };

  return (
    <section className="interaction-workspace-card" aria-label="منطقة التفاعل الصوتي والأوامر">
      <div className="card-top-bar">
        <div className="card-heading-group">
          <svg className="app-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
            <line x1="12" y1="19" x2="12" y2="23"></line>
            <line x1="8" y1="23" x2="16" y2="23"></line>
          </svg>
          <h2 className="card-heading">أوامر المساعد والتفاعل</h2>
        </div>

        {/* Persistent, Single Coherent Stop Action */}
        <button
          type="button"
          className={`persistent-stop-btn ${isBusy ? 'is-busy-active' : ''}`}
          onClick={onStopAll}
          aria-label="إيقاف فوري للصوت والعمليات وإلغاء الطلب (مفتاح الإيقاف Esc)"
        >
          <svg className="app-svg" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <rect x="5" y="5" width="14" height="14" rx="2"></rect>
          </svg>
          <span>إيقاف (Esc)</span>
        </button>
      </div>

      {/* Prominent Scale Microphone Button */}
      <div className="voice-mic-container">
        <button
          type="button"
          className={`primary-voice-control ${isRecording ? 'recording-active' : ''}`}
          onClick={handleVoiceToggle}
          aria-pressed={isRecording}
          aria-label="تحدث مع المساعد البصري"
        >
          <div className="mic-icon-wrapper">
            <svg className="app-svg-lg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
              <line x1="12" y1="19" x2="12" y2="23"></line>
              <line x1="8" y1="23" x2="16" y2="23"></line>
            </svg>
          </div>

          <div className="mic-text-content">
            <span className="mic-title">تحدث مع المساعد</span>
            <span className="mic-example-hint">جرّب: شنو قدامي؟ أو اقرأ المكتوب</span>
            <span className="mic-state-status">{getVoiceHint()}</span>
          </div>
        </button>
      </div>

      {/* Recognized Command Banner */}
      {recognizedQuery && (
        <div className="recognized-query-banner" role="status">
          <span className="query-label">الطلب المنطوق:</span>
          <span className="query-content">«{recognizedQuery}»</span>
        </div>
      )}

      {/* Secondary Actions Grid */}
      <div className="secondary-commands-row" role="group" aria-label="أوامر التحليل السريعة">
        <button
          type="button"
          className="action-pill-btn"
          onClick={() => onQuickAction('describe')}
          aria-label="صف المشهد البصري الحالي"
        >
          <svg className="app-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
            <circle cx="12" cy="12" r="3"></circle>
          </svg>
          <div className="btn-label-pair">
            <span className="btn-main-txt">صف المشهد</span>
            <span className="btn-shortcut-hint">(D)</span>
          </div>
        </button>

        <button
          type="button"
          className="action-pill-btn"
          onClick={() => onQuickAction('read')}
          aria-label="اقرأ النصوص والمطبوعات"
        >
          <svg className="app-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
          </svg>
          <div className="btn-label-pair">
            <span className="btn-main-txt">اقرأ النص</span>
            <span className="btn-shortcut-hint">(R)</span>
          </div>
        </button>

        <button
          type="button"
          className="action-pill-btn"
          onClick={() => {
            const input = document.getElementById('search-object-field');
            if (input) input.focus();
          }}
          aria-label="ابحث عن كائن محدد في المشهد"
        >
          <svg className="app-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <div className="btn-label-pair">
            <span className="btn-main-txt">ابحث عن غرض</span>
            <span className="btn-shortcut-hint">(F)</span>
          </div>
        </button>
      </div>

      {/* Properly Labelled Object Search Field */}
      <form onSubmit={handleSearchSubmit} className="search-object-container">
        <label htmlFor="search-object-field" className="form-sub-label">
          البحث عن غرض محدد في المشهد:
        </label>
        <div className="search-field-row">
          <input
            type="text"
            id="search-object-field"
            className="clean-text-input"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="اكتب اسم الغرض (مثال: قنينة، كوب، لابتوب)..."
            aria-label="اسم الغرض المراد البحث عنه"
          />
          <button type="submit" className="search-action-btn">
            ابحث (F)
          </button>
        </div>
      </form>

      {/* Compact Expandable Secondary Input: Text Query & File Upload */}
      <div className="advanced-input-disclosure">
        <button
          type="button"
          className="disclosure-toggle-btn"
          onClick={() => setShowAdvanced(!showAdvanced)}
          aria-expanded={showAdvanced}
        >
          <span>{showAdvanced ? '− خيارات الإدخال البديلة' : '+ كتابة سؤال بديل أو رفع صورة من ملف'}</span>
        </button>

        {showAdvanced && (
          <div className="disclosure-content-box">
            <form onSubmit={handleTextSubmit} className="text-query-form">
              <label htmlFor="manual-query-field" className="form-sub-label">
                كتابة سؤال يدوي بدلاً من الصوت:
              </label>
              <div className="search-field-row">
                <input
                  type="text"
                  id="manual-query-field"
                  className="clean-text-input"
                  value={textQuery}
                  onChange={(e) => setTextQuery(e.target.value)}
                  placeholder="اكتب سؤالك هنا (مثال: شنو على الميز؟ أو اقرأ هذه الورقة)..."
                  aria-label="سؤال كتابي للمساعد"
                />
                <button type="submit" className="search-action-btn">
                  إرسال
                </button>
              </div>
            </form>

            <div className="file-upload-block">
              <label htmlFor="file-image-picker" className="form-sub-label">
                تحليل صورة من ملف محلي:
              </label>
              <input
                type="file"
                id="file-image-picker"
                accept="image/*"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    onFileUpload(e.target.files[0]);
                  }
                }}
                className="clean-file-input"
                aria-label="اختيار صورة من الجهاز"
              />
            </div>
          </div>
        )}
      </div>
    </section>
  );
};
