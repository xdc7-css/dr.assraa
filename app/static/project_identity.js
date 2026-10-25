/**
 * AMAV — Arabic Multimodal Assistive Vision
 * Project Identity and Academic Metadata Configuration
 * 
 * جميع بيانات المشروع الأكاديمية والأسماء موجودة هنا لسهولة التعديل.
 * All academic credits, titles, student names, and supervisor info are centralized here.
 */

const AMAV_IDENTITY = {
  // الجامعة والقسم الأكاديمي
  university: "جامعة البصرة",
  college: "كلية الهندسة",
  department: "قسم هندسة الحاسوب",

  // العناوين الرسمية
  projectTitleAr: "مساعد بصري ذكي متعدد الوسائط",
  projectSubtitleAr: "لمساعدة المكفوفين وضعاف البصر في التعرف على البيئة والتفاعل الصوتي",
  projectTitleEn: "Design and Development of an AI-Based Multimodal Intelligent Assistant for Assisting Blind and Visually Impaired Individuals in Real-Time Environment Recognition and Voice Interaction",

  // بيانات إعداد الطالبات (الأسماء والتسلسلات الرسمية)
  students: [
    { name: "بشاير احسان احمد محمد", sequence: "35" },
    { name: "الاء محمد عبدالواحد مطلب", sequence: "55" },
    { name: "غدير علاء كامل حسين", sequence: "109" }
  ],

  // المشرفة الأكاديمية (بدون تعديل أو إضافة)
  supervisor: "م.د. اسراء حبيب",

  // تفاصيل التخرج والمعالجة
  academicYear: "2025 - 2026",
  projectType: "مشروع تخرج لنيل شهادة البكالوريوس في هندسة الحاسوب",
  processingType: "معالجة طرفية محلية كاملة (Edge Offline Architecture)",
  privacyGuarantee: "الخصوصية مضمونة 100% — لا يتم إرسال أي إطار كاميرا أو تسجيل صوتي إلى أي خادم خارجي أو سحابي."
};

// جعل الكائن متاحاً للنافذة العامة
if (typeof window !== 'undefined') {
  window.AMAV_IDENTITY = AMAV_IDENTITY;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = AMAV_IDENTITY;
}
