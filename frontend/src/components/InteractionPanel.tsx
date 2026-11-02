import React, { useState } from 'react';
import type { AppLifecycleState, SearchSessionState, VLMMode } from '../types';

interface InteractionPanelProps {
  lifecycleState: AppLifecycleState;
  isRecording: boolean;
  isPlayingAudio: boolean;
  recognizedQuery: string | null;
  modelMode: VLMMode;
  speechSpeed: number;
  activeSearchSession: SearchSessionState | null;
  onStartVoice: () => void;
  onStopVoice: () => void;
  onQuickAction: (mode: 'describe' | 'read' | 'find' | 'repeat' | 'shorten' | 'reset', param?: string) => void;
  onSendTextQuery: (text: string) => void;
  onStartContinuousSearch: (target: string) => void;
  onStopContinuousSearch: () => void;
  onToggleModelMode: (mode: VLMMode) => void;
  onChangeSpeechSpeed: (speed: number) => void;
  onStopAll: () => void;
  onFileUpload: (file: File) => void;
}

export const InteractionPanel: React.FC<InteractionPanelProps> = ({
  lifecycleState,
  isRecording,
  isPlayingAudio,
  recognizedQuery,
  modelMode,
  speechSpeed,
  activeSearchSession,
  onStartVoice,
  onStopVoice,
  onQuickAction,
  onSendTextQuery,
  onStartContinuousSearch,
  onStopContinuousSearch,
  onToggleModelMode,
  onChangeSpeechSpeed,
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

  const isSearching = Boolean(activeSearchSession && activeSearchSession.status !== 'stopped' && activeSearchSession.status !== 'timeout');

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
    onStartContinuousSearch(term);
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
      return 'جاري تحويل الصوت إلى نص محلياً...';
    }
    if (lifecycleState === 'analyzing') {
      return 'جاري تحليل المشهد بالنماذج المحلية...';
    }
    if (isPlayingAudio || lifecycleState === 'speaking') {
      return 'المساعد يتحدث الآن... (اضغط Esc للإيقاف)';
    }
    if (isSearching) {
      return `جلسة بحث مستمرة عن «${activeSearchSession?.target_query_ar}»...`;
    }
    return 'اضغط للبدء واضغط ثانية للإنهاء (أو استمر بالضغط على زر المسافة)';
  };

  return (
    <section className="interaction-workspace-card" aria-label="منطقة التفاعل الصوتي والأوامر">
      {/* Top bar with Stop Button & Model Mode Selector */}
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

        {/* Persistent Emergency Stop Action */}
        <button
          type="button"
          className={`persistent-stop-btn ${isBusy || isSearching ? 'is-busy-active' : ''}`}
          onClick={onStopAll}
          aria-label="إيقاف فوري للصوت والعمليات وإلغاء الطلب أو البحث (مفتاح Esc)"
        >
          <svg className="app-svg" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <rect x="5" y="5" width="14" height="14" rx="2"></rect>
          </svg>
          <span>إيقاف (Esc)</span>
        </button>
      </div>

      {/* Model Mode Toggle: Fast (2B) vs Detailed (4B) */}
      <div className="model-mode-selector-bar" role="group" aria-label="وضع نموذج الرؤية واللغة">
        <span className="mode-selector-label">نموذج الرؤية:</span>
        <div className="mode-toggle-group">
          <button
            type="button"
            className={`mode-toggle-btn ${modelMode === 'fast' ? 'is-active' : ''}`}
            onClick={() => onToggleModelMode('fast')}
            aria-pressed={modelMode === 'fast'}
            title="النموذج السريع الافتراضي (2B) - منخفض الذاكرة وسريع الاستجابة"
          >
            ⚡ سريع (2B)
          </button>
          <button
            type="button"
            className={`mode-toggle-btn ${modelMode === 'detailed' ? 'is-active' : ''}`}
            onClick={() => onToggleModelMode('detailed')}
            aria-pressed={modelMode === 'detailed'}
            title="النموذج المفصل الاختياري (4B) - وصف أعمق وتفاصيل بصرية أوسع"
          >
            🔍 وصف مفصّل (4B)
          </button>
        </div>

        {/* Speech Speed Controls */}
        <div className="speed-selector-group" role="group" aria-label="سرعة النطق الصوتي">
          <span className="speed-label">السرعة:</span>
          {[0.75, 1.0, 1.25, 1.5].map((spd) => (
            <button
              key={spd}
              type="button"
              className={`speed-pill-btn ${speechSpeed === spd ? 'speed-active' : ''}`}
              onClick={() => onChangeSpeechSpeed(spd)}
              aria-pressed={speechSpeed === spd}
              aria-label={`سرعة النطق ${spd} ضعف`}
            >
              {spd}x
            </button>
          ))}
        </div>
      </div>

      {/* Active Continuous Search Session Banner */}
      {isSearching && activeSearchSession && (
        <div className="search-session-active-card" role="status" aria-live="polite">
          <div className="session-card-header">
            <span className="session-pulse-indicator" aria-hidden="true" />
            <span className="session-target-title">
              جلسة بحث مستمرة عن: <strong>{activeSearchSession.target_query_ar}</strong>
            </span>
            <span className="session-timer-badge">{Math.round(activeSearchSession.elapsed_seconds)} ثانية</span>
          </div>
          <div className="session-direction-box">
            <span className="direction-icon">🎯</span>
            <span className="direction-live-text">{activeSearchSession.direction_text_ar || 'جاري البحث في الإطار...'}</span>
          </div>
          <button
            type="button"
            className="session-stop-btn"
            onClick={onStopContinuousSearch}
            aria-label="إيقاف جلسة البحث المستمرة"
          >
            إنهاء جلسة البحث
          </button>
        </div>
      )}

      {/* Primary Push-to-Talk Microphone Button */}
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
            <span className="mic-example-hint">جرّب: شنو قدامي؟ | وين القنينة؟ | اقرأ المكتوب | كرر | اختصر</span>
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
          aria-label="صف المشهد البصري الحالي (مفتاح D)"
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
          aria-label="اقرأ النصوص والمطبوعات (مفتاح R)"
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
          aria-label="ابحث عن كائن محدد في المشهد (مفتاح F)"
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

        <button
          type="button"
          className="action-pill-btn"
          onClick={() => onQuickAction('shorten')}
          aria-label="اختصر الجواب السابق دون تحليل جديد"
        >
          <svg className="app-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <line x1="4" y1="6" x2="20" y2="6"></line>
            <line x1="4" y1="12" x2="14" y2="12"></line>
            <line x1="4" y1="18" x2="10" y2="18"></line>
          </svg>
          <div className="btn-label-pair">
            <span className="btn-main-txt">اختصر الجواب</span>
          </div>
        </button>
      </div>

      {/* Continuous Object Search Form */}
      <form onSubmit={handleSearchSubmit} className="search-object-container">
        <label htmlFor="search-object-field" className="form-sub-label">
          البحث المستمر عن غرض في المشهد (مع التوجيه اللحظي يمين/وسط/يسار):
        </label>
        <div className="search-field-row">
          <input
            type="text"
            id="search-object-field"
            className="clean-text-input"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="اكتب الغرض (مثال: قنينة، بطل، كوب، لابتوب، جنطة)..."
            aria-label="اسم الغرض للبحث المستمر"
          />
          <button type="submit" className="search-action-btn">
            بدء البحث المستمر 🎯
          </button>
        </div>
      </form>

      {/* Expandable Alternative Input: Text Query & File Upload */}
      <div className="advanced-input-disclosure">
        <button
          type="button"
          className="disclosure-toggle-btn"
          onClick={() => setShowAdvanced(!showAdvanced)}
          aria-expanded={showAdvanced}
        >
          <span>{showAdvanced ? '− خيارات الإدخال والذاكرة البديلة' : '+ كتابة سؤال بديل، إعادة ضبط الذاكرة، أو رفع صورة'}</span>
        </button>

        {showAdvanced && (
          <div className="disclosure-content-box">
            <div className="memory-reset-row">
              <button
                type="button"
                className="secondary-tool-btn reset-memory-btn"
                onClick={() => onQuickAction('reset')}
                aria-label="مسح ذاكرة السياق الصوتي والبدء من جديد"
              >
                🔄 إعادة ضبط الذاكرة والسياق
              </button>
            </div>

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
                  placeholder="اكتب سؤالك هنا (مثال: شنو على الميز؟ أو وين الكوب؟)..."
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
