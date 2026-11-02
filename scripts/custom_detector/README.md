# خط أنابيب تدريب وتقييم كاشف الكائنات المخصص (AMAV Custom Object Detector)

---

## 📌 الهدف والمبررات
يوفر هذا الدليل البنية البرمجية المتكاملة لتدريب وتقييم كاشف كائنات خفيف ومخصص (`YOLO11n`) على الفئات الأكثر إلحاحاً للمكفوفين وضعاف البصر والتي تفتقر إليها مجموعة بيانات COCO القياسية:
1. **الأبواب (`door` - باب):** الملاحة الداخلية والتنقل بين الغرف.
2. **الدرج والسلالم (`stairs` - درج):** تجنب السقوط وتحديد بداية ونهاية الدرجات.
3. **حواف الأرصفة (`curb` - حافة رصيف):** تفادي التعثر عند النزول إلى الشارع.
4. **ممرات المشاة (`crosswalk` - ممر مشاة):** عبور الشارع بأمان.

---

## 📂 بنية مجلد البيانات المطلوب (YOLO Directory Format)
```text
data/custom_dataset/
├── data.yaml
├── images/
│   ├── train/    (صور التدريب)
│   ├── val/      (صور التحقق والتقييم)
│   └── test/     (صور الاختبار المستقل)
└── labels/
    ├── train/    (ملفات التسميات TXT المطابقة)
    └── val/
```

### صيغة `data.yaml`:
```yaml
path: data/custom_dataset
train: images/train
val: images/val

nc: 4
names: ['door', 'stairs', 'curb', 'crosswalk']
```

---

## 🚀 خطوات التشغيل والتحقق

### 1. التحقق من سلامة البيانات وخلوها من التسريب:
```powershell
.\.venv\Scripts\python.exe scripts/custom_detector/dataset_validator.py --data-dir data/custom_dataset
```

### 2. بدء تدريب النموذج مع تجميد العمود الفقري (Backbone Freezing) للحفاظ على كشف كائنات COCO:
```powershell
.\.venv\Scripts\python.exe scripts/custom_detector/train_custom_yolo.py --data data/custom_dataset/data.yaml --epochs 50 --batch 16 --device 0
```

### 3. التقييم المستقل وحساب الدقة (mAP50, mAP50-95):
```powershell
.\.venv\Scripts\python.exe scripts/custom_detector/evaluate_custom_yolo.py --model models/custom_detector_runs/amav_custom_mobility/weights/best.pt --data data/custom_dataset/data.yaml
```

---
> **ملاحظة أكاديمية:** البنية البرمجية مكتملة وجاهزة 100%. عند توفر الصور المصنفة محلياً، يمكن تدريب النموذج مباشرة دون الحاجة لأي تعديلات برمجية إضافية.
