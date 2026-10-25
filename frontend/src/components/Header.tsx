import React from 'react';
import { AMAV_IDENTITY } from '../config/identity';

interface HeaderProps {
  highContrast: boolean;
  onToggleTheme: () => void;
  onOpenAbout: () => void;
  onOpenDiagnostics: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  highContrast,
  onToggleTheme,
  onOpenAbout,
  onOpenDiagnostics,
}) => {
  return (
    <header className="academic-header" role="banner">
      <div className="app-container">
        <div className="header-top-row">
          <div className="header-brand-block">
            <div className="affiliation-line">
              <span className="uni-title">{AMAV_IDENTITY.university}</span>
              <span className="dot-sep" aria-hidden="true">·</span>
              <span className="dept-title">{AMAV_IDENTITY.college} · {AMAV_IDENTITY.department}</span>
              <span className="short-badge" aria-label="رمز المشروع">{AMAV_IDENTITY.shortName}</span>
            </div>

            <h1 className="main-project-title">{AMAV_IDENTITY.title}</h1>
            <p className="main-project-subtitle">{AMAV_IDENTITY.subtitle}</p>
          </div>

          <div className="header-action-tools">
            <button
              type="button"
              className="tool-btn"
              onClick={onToggleTheme}
              aria-label={highContrast ? "التبديل إلى الوضع الطبيعي" : "التبديل إلى وضع التباين الفائق"}
            >
              <svg className="app-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <circle cx="12" cy="12" r="10"></circle>
                <path d="M12 2a10 10 0 0 1 10 10 10 10 0 0 1-10 10V2z" fill="currentColor"></path>
              </svg>
              <span>{highContrast ? "وضع طبيعي" : "تباين فائق"}</span>
            </button>

            <button
              type="button"
              className="tool-btn"
              onClick={onOpenAbout}
              aria-haspopup="dialog"
              aria-label="عرض تفاصيل ومعلومات المشروع الأكاديمية"
            >
              <svg className="app-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
              </svg>
              <span>حول المشروع</span>
            </button>

            <a
              href="/static/audio_comparison.html"
              target="_blank"
              rel="noreferrer"
              className="tool-btn link-tool-btn"
              title="مقارنة جودة النطق والسرعات في نافذة جديدة"
            >
              <svg className="app-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
                <path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path>
              </svg>
              <span>مقارنة النطق</span>
            </a>

            <button
              type="button"
              className="tool-btn"
              onClick={onOpenDiagnostics}
              aria-label="فتح لوحة التشخيص الهندسي وحالة النماذج"
            >
              <svg className="app-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <circle cx="12" cy="12" r="3"></circle>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
              </svg>
              <span>التشخيص</span>
            </button>
          </div>
        </div>

        {/* Dedicated, Clearly Readable Academic Credits Row */}
        <div className="academic-credits-container" aria-label="فريق العمل والإشراف الأكاديمي">
          <div className="credits-students-col">
            <span className="credits-title">إعداد الطالبات:</span>
            <div className="credits-names-list">
              {AMAV_IDENTITY.students.map((student, idx) => (
                <span key={student.sequence} className="student-name-item">
                  {student.name}
                  {idx < AMAV_IDENTITY.students.length - 1 && <span className="name-sep" aria-hidden="true">•</span>}
                </span>
              ))}
            </div>
          </div>

          <div className="credits-supervisor-col">
            <span className="credits-title">بإشراف:</span>
            <span className="supervisor-name-item">{AMAV_IDENTITY.supervisor}</span>
          </div>
        </div>
      </div>
    </header>
  );
};
