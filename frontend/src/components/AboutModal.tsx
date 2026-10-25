import React, { useEffect } from 'react';
import { AMAV_IDENTITY } from '../config/identity';

interface AboutModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AboutModal: React.FC<AboutModalProps> = ({ isOpen, onClose }) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        className="academic-modal-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="about-modal-heading"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-top-bar">
          <h2 id="about-modal-heading" className="modal-heading-text">
            بيانات المشروع الأكاديمية والتوثيق
          </h2>
          <button
            type="button"
            className="modal-close-icon-btn"
            onClick={onClose}
            aria-label="إغلاق نافذة معلومات المشروع"
          >
            <svg className="app-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <div className="modal-scroll-body">
          <section className="modal-info-block">
            <h3 className="block-title">العنوان الأكاديمي المعتمد (English Project Title)</h3>
            <p className="english-title-box" dir="ltr" lang="en">
              {AMAV_IDENTITY.englishTitle}
            </p>
          </section>

          <section className="modal-info-block">
            <h3 className="block-title">المؤسسة الأكاديمية</h3>
            <p className="affiliation-text">
              {AMAV_IDENTITY.university} — {AMAV_IDENTITY.college} — {AMAV_IDENTITY.department}
            </p>
            <p className="academic-year-text">العام الدراسي: {AMAV_IDENTITY.academicYear}</p>
          </section>

          <section className="modal-info-block">
            <h3 className="block-title">فريق العمل (إعداد الطالبات والتسلسلات الرسمية)</h3>
            <ul className="students-roster-list">
              {AMAV_IDENTITY.students.map((student) => (
                <li key={student.sequence} className="student-roster-item">
                  <span className="student-roster-name">{student.name}</span>
                  <span className="student-roster-seq">التسلسل: {student.sequence}</span>
                </li>
              ))}
            </ul>
          </section>

          <section className="modal-info-block">
            <h3 className="block-title">الإشراف الأكاديمي</h3>
            <p className="supervisor-text">
              <strong>{AMAV_IDENTITY.supervisor}</strong>
            </p>
          </section>

          <section className="modal-info-block">
            <h3 className="block-title">بنية المعالجة وحماية الخصوصية</h3>
            <p className="privacy-body-text">
              يعتمد النظام بالكامل على تقنية الحوسبة الطرفية المحلية (Offline Edge Processing).
              تتم معالجة كافة تدفقات الكاميرا والتسجيلات الصوتية محلياً على جهاز الحاسوب دون الحاجة إلى أي اتصال بالإنترنت أو خدمات سحابية مدفوعة، مما يضمن أقصى معايير الخصوصية والأمان للمستخدم.
            </p>
          </section>
        </div>

        <div className="modal-bottom-actions">
          <button type="button" className="modal-primary-btn" onClick={onClose}>
            إغلاق
          </button>
        </div>
      </div>
    </div>
  );
};
