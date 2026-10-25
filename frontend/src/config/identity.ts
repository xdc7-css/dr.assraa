/**
 * AMAV — Arabic Multimodal Assistive Vision
 * Centralized Academic Identity Configuration
 *
 * يحتوي هذا الملف على كافة نصوص وبيانات المشروع الأكاديمية لسهولة التعديل المركزي.
 */

export interface Student {
  name: string;
  sequence: string;
}

export interface AcademicIdentity {
  university: string;
  college: string;
  department: string;
  title: string;
  subtitle: string;
  shortName: string;
  englishTitle: string;
  students: Student[];
  supervisor: string;
  academicYear: string;
  processingType: string;
  privacyGuarantee: string;
}

export const AMAV_IDENTITY: AcademicIdentity = {
  university: "جامعة البصرة",
  college: "كلية الهندسة",
  department: "قسم هندسة الحاسوب",
  title: "مساعد بصري ذكي",
  subtitle: "للتعرف على البيئة وقراءة النصوص والتفاعل الصوتي",
  shortName: "AMAV",
  englishTitle:
    "Design and Development of an AI-Based Multimodal Intelligent Assistant for Assisting Blind and Visually Impaired Individuals in Real-Time Environment Recognition and Voice Interaction",
  students: [
    { name: "بشاير احسان احمد محمد", sequence: "35" },
    { name: "الاء محمد عبدالواحد مطلب", sequence: "55" },
    { name: "غدير علاء كامل حسين", sequence: "109" },
  ],
  supervisor: "م.د. اسراء حبيب",
  academicYear: "2025 - 2026",
  processingType: "معالجة طرفية محلية كاملة (Edge Offline Architecture)",
  privacyGuarantee:
    "حماية الخصوصية مضمونة 100% — لا يتم إرسال أي إطار من الكاميرا أو تسجيل صوتي إلى أي خادم خارجي أو سحابي.",
};
