"""YOLO11 object detection adapter with Arabic localization and COCO mapping."""
from __future__ import annotations

import base64
import io
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image

from app.config import DetectionConfig
from app.schemas import BoundingBox, DetectionItem, DetectResponse

# 80 COCO classes mapped to precise Arabic names
COCO_ARABIC_NAMES: Dict[str, str] = {
    "person": "شخص",
    "bicycle": "دراجة هوائية",
    "car": "سيارة",
    "motorcycle": "دراجة نارية",
    "airplane": "طائرة",
    "bus": "حافلة",
    "train": "قطار",
    "truck": "شاحنة",
    "boat": "قارب",
    "traffic light": "إشارة مرور",
    "fire hydrant": "صنبور إطفاء",
    "stop sign": "علامة توقف",
    "parking meter": "عداد مواقف",
    "bench": "مقعد",
    "bird": "طائر",
    "cat": "قطة",
    "dog": "كلب",
    "horse": "حصان",
    "sheep": "خروف",
    "cow": "بقرة",
    "elephant": "فيل",
    "bear": "دب",
    "zebra": "حمار وحشي",
    "giraffe": "زرافة",
    "backpack": "حقيبة ظهر",
    "umbrella": "مظلة",
    "handbag": "حقيبة يد",
    "tie": "ربطة عنق",
    "suitcase": "حقيبة سفر",
    "frisbee": "قرص طائر",
    "skis": "زلاجات",
    "snowboard": "لوح تزلج",
    "sports ball": "كرة",
    "kite": "طائرة ورقية",
    "baseball bat": "مضرب بيسبول",
    "baseball glove": "قفاز بيسبول",
    "skateboard": "لوح تزلج",
    "surfboard": "لوح ركوب الأمواج",
    "tennis racket": "مضرب تنس",
    "bottle": "قنينة",
    "wine glass": "كأس",
    "cup": "كوب",
    "fork": "شوكة",
    "knife": "سكين",
    "spoon": "ملعقة",
    "bowl": "وعاء",
    "banana": "موزة",
    "apple": "تفاحة",
    "sandwich": "شطيرة",
    "orange": "برتقالة",
    "broccoli": "بروكلي",
    "carrot": "جزرة",
    "hot dog": "شطيرة سجق",
    "pizza": "بيتزا",
    "donut": "دونات",
    "cake": "كعكة",
    "chair": "كرسي",
    "couch": "أريكة",
    "potted plant": "نبتة منزلية",
    "bed": "سرير",
    "dining table": "طاولة طعام",
    "toilet": "مرحاض",
    "tv": "تلفزيون",
    "laptop": "حاسوب محمول",
    "mouse": "فأرة حاسوب",
    "remote": "جهاز تحكم",
    "keyboard": "لوحة مفاتيح",
    "cell phone": "هاتف خلوي",
    "microwave": "مايكروويف",
    "oven": "فرن",
    "toaster": "محمصة خبز",
    "sink": "مغسلة",
    "refrigerator": "ثلاجة",
    "book": "كتاب",
    "clock": "ساعة",
    "vase": "مزهرية",
    "scissors": "مقص",
    "teddy bear": "دبدوب",
    "hair drier": "مجفف شعر",
    "toothbrush": "فرشاة أسنان",
}

# Arabic alias lookup mapping common queries and dialect words to COCO english classes
ARABIC_ALIASES_TO_COCO: Dict[str, str] = {
    # Bottle
    "قنينة": "bottle",
    "قارورة": "bottle",
    "زجاجة": "bottle",
    "بطل": "bottle",
    "ماء": "bottle",
    "ماي": "bottle",
    # Person
    "شخص": "person",
    "انسان": "person",
    "إنسان": "person",
    "رجال": "person",
    "رجل": "person",
    "مرة": "person",
    "امراة": "person",
    "امرأة": "person",
    "بنت": "person",
    "ولد": "person",
    "احد": "person",
    "أحد": "person",
    # Chair
    "كرسي": "chair",
    "كراسي": "chair",
    "مقعد": "chair",
    # Cup
    "كوب": "cup",
    "فنجان": "cup",
    "قلاص": "cup",
    "كاسة": "cup",
    "قدح": "cup",
    # Phone
    "هاتف": "cell phone",
    "تلفون": "cell phone",
    "موبايل": "cell phone",
    "جوال": "cell phone",
    "خلوي": "cell phone",
    # Laptop
    "لابتوب": "laptop",
    "حاسوب": "laptop",
    "كمبيوتر": "laptop",
    # Bag
    "حقيبة": "backpack",
    "شنطة": "backpack",
    "جنطة": "backpack",
    "حقيبة ظهر": "backpack",
    "حقيبة يد": "handbag",
    # Glasses / Remote / Mouse / Keys
    "ريموت": "remote",
    "تحكم": "remote",
    "ماوس": "mouse",
    "فارة": "mouse",
    "فأرة": "mouse",
    "كيبورد": "keyboard",
    "لوحة مفاتيح": "keyboard",
    "شاشة": "tv",
    "تلفزيون": "tv",
    "تلفاز": "tv",
    "طاولة": "dining table",
    "ميز": "dining table",
    "مكتب": "dining table",
    "قنفة": "couch",
    "اريكة": "couch",
    "أريكة": "couch",
    "سرير": "bed",
    "جرباية": "bed",
    "كتاب": "book",
    "كتب": "book",
    "ساعة": "clock",
    "مقص": "scissors",
    "فرشاة": "toothbrush",
}

# Unsupported targets that blind users commonly ask for but COCO lacks
EXPLICITLY_UNSUPPORTED_TARGETS = {
    "باب": "الأبواب ليست ضمن فئات كشف الكائنات المدعومة حالياً (COCO80)، وتتطلب نموذجاً مخصصاً.",
    "ابواب": "الأبواب ليست ضمن فئات كشف الكائنات المدعومة حالياً (COCO80)، وتتطلب نموذجاً مخصصاً.",
    "درج": "الدرج والسلالم ليست ضمن فئات كشف الكائنات المدعومة حالياً (COCO80).",
    "سلم": "السلالم ليست ضمن فئات كشف الكائنات المدعومة حالياً (COCO80).",
    "حفرة": "الحفر والعوائق الأرضية ليست ضمن فئات كشف الكائنات وتتطلب مستشعرات عمق.",
}

class DetectionAdapter:
    def __init__(self, config: Optional[DetectionConfig] = None):
        self.config = config or DetectionConfig()
        self.model = None
        self._loaded = False
        self._load_error: Optional[str] = None
        # Bounded temporal smoothing state for target tracking
        # Maps target_class -> {"timestamp": float, "position": str, "hits": int}
        self._target_history: Dict[str, dict] = {}
        self.history_ttl_seconds: float = 2.0

    def load_model(self) -> bool:
        if self._loaded and self.model is not None:
            return True
        try:
            from ultralytics import YOLO
            model_path = Path(self.config.model_path)
            if not model_path.exists():
                self._load_error = f"Model file not found: {model_path}"
                return False
            self.model = YOLO(str(model_path))
            self._loaded = True
            self._load_error = None
            return True
        except Exception as e:
            self._load_error = str(e)
            self._loaded = False
            return False

    def is_ready(self) -> bool:
        return self._loaded and self.model is not None

    def normalize_target_query(self, query: str) -> Tuple[Optional[str], Optional[str]]:
        """Normalize Arabic query to COCO class name if supported."""
        cleaned = query.strip().lower()
        # Check explicit unsupported
        for unsupp, reason in EXPLICITLY_UNSUPPORTED_TARGETS.items():
            if unsupp in cleaned:
                return None, reason

        # Check aliases
        for alias, coco_class in ARABIC_ALIASES_TO_COCO.items():
            if alias in cleaned:
                return coco_class, None

        # Check direct english
        for cls_name in COCO_ARABIC_NAMES.keys():
            if cls_name in cleaned:
                return cls_name, None

        return None, None

    def detect(
        self,
        image_input: Image.Image | str,
        target_object_ar: Optional[str] = None,
        frame_id: Optional[str] = None,
        confidence_threshold: Optional[float] = None,
        mirrored: bool = False,
    ) -> DetectResponse:
        t0 = time.perf_counter()
        now = time.time()
        conf_thresh = confidence_threshold if confidence_threshold is not None else self.config.confidence_threshold

        # Parse image
        if isinstance(image_input, str):
            if (image_input.endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp")) or "/" in image_input or "\\" in image_input) and Path(image_input).exists():
                img = Image.open(image_input).convert("RGB")
            else:
                if "," in image_input:
                    image_input = image_input.split(",", 1)[1]
                raw_bytes = base64.b64decode(image_input)
                img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        else:
            img = image_input.convert("RGB")

        w, h = img.size

        if not self.is_ready():
            ok = self.load_model()
            if not ok:
                return DetectResponse(
                    frame_id=frame_id,
                    image_width=w,
                    image_height=h,
                    status="model_not_ready",
                    error=self._load_error or "Detection model not loaded",
                    latency_ms=round((time.perf_counter() - t0) * 1000, 2),
                )

        target_en = None
        unsupported_reason = None
        if target_object_ar:
            target_en, unsupported_reason = self.normalize_target_query(target_object_ar)
            if unsupported_reason:
                return DetectResponse(
                    frame_id=frame_id,
                    image_width=w,
                    image_height=h,
                    target_object_ar=target_object_ar,
                    target_found=False,
                    summary_ar=unsupported_reason,
                    status="unsupported_target",
                    latency_ms=round((time.perf_counter() - t0) * 1000, 2),
                )

        # Run inference on CPU/specified device
        results = self.model.predict(
            source=img,
            conf=conf_thresh,
            device=self.config.device,
            imgsz=self.config.input_size,
            verbose=False,
        )

        detections: List[DetectionItem] = []
        target_matches: List[DetectionItem] = []

        if results and len(results) > 0:
            boxes = results[0].boxes
            for b in boxes:
                cls_id = int(b.cls[0].item())
                cls_en = self.model.names.get(cls_id, f"class_{cls_id}")
                cls_ar = COCO_ARABIC_NAMES.get(cls_en, cls_en)
                conf = float(b.conf[0].item())
                xyxy = b.xyxy[0].tolist()

                cx = (xyxy[0] + xyxy[2]) / 2.0
                cy = (xyxy[1] + xyxy[3]) / 2.0
                norm_cx = cx / max(w, 1)

                # Adjust for camera preview mirroring convention if requested
                if mirrored:
                    norm_cx = 1.0 - norm_cx

                # Determine relative horizontal position from user's camera viewpoint
                if norm_cx < 0.38:
                    pos = "left"
                elif norm_cx > 0.62:
                    pos = "right"
                else:
                    pos = "center"

                item = DetectionItem(
                    class_id=cls_id,
                    class_name_en=cls_en,
                    class_name_ar=cls_ar,
                    confidence=round(conf, 3),
                    bbox=BoundingBox(
                        x1=round(xyxy[0], 1),
                        y1=round(xyxy[1], 1),
                        x2=round(xyxy[2], 1),
                        y2=round(xyxy[3], 1),
                    ),
                    center_x=round(norm_cx, 3),
                    center_y=round(cy / max(h, 1), 3),
                    position=pos,
                )
                detections.append(item)

                if target_en and cls_en == target_en:
                    target_matches.append(item)

        latency = round((time.perf_counter() - t0) * 1000, 2)

        # Build Arabic summary with temporal smoothing for target searches
        if target_object_ar:
            pos_ar_map = {"left": "على اليسار", "center": "في المنتصف مباشرة", "right": "على اليمين"}
            target_ar_name = COCO_ARABIC_NAMES.get(target_en, target_object_ar)

            if target_matches:
                # Update temporal history
                prev = self._target_history.get(target_en)
                hits = (prev["hits"] + 1) if (prev and (now - prev["timestamp"]) < self.history_ttl_seconds) else 1
                self._target_history[target_en] = {
                    "timestamp": now,
                    "position": target_matches[0].position,
                    "hits": hits,
                }

                if len(target_matches) == 1:
                    m = target_matches[0]
                    summary = f"تم رصد {target_ar_name} {pos_ar_map[m.position]} أمام الكاميرا."
                else:
                    positions = [pos_ar_map[m.position] for m in target_matches]
                    summary = f"تم رصد {len(target_matches)} من {target_ar_name}: {', '.join(positions)}."
                return DetectResponse(
                    frame_id=frame_id,
                    detections=detections,
                    image_width=w,
                    image_height=h,
                    target_object_ar=target_object_ar,
                    target_found=True,
                    target_position=target_matches[0].position,
                    summary_ar=summary,
                    latency_ms=latency,
                    status="ok",
                )
            else:
                # Check if recently tracked to smooth temporal single-frame dropouts
                prev = self._target_history.get(target_en)
                if prev and (now - prev["timestamp"]) < 1.2 and prev.get("hits", 0) >= 2:
                    pos = prev["position"]
                    summary = f"تم رصد {target_ar_name} قبل لحظات {pos_ar_map[pos]}، يرجى تثبيت الكاميرا."
                    return DetectResponse(
                        frame_id=frame_id,
                        detections=detections,
                        image_width=w,
                        image_height=h,
                        target_object_ar=target_object_ar,
                        target_found=True,
                        target_position=pos,
                        summary_ar=summary,
                        latency_ms=latency,
                        status="ok",
                    )
                else:
                    # Expire stale target tracking
                    if prev and (now - prev["timestamp"]) >= self.history_ttl_seconds:
                        self._target_history.pop(target_en, None)

                    summary = f"لم يتم رصد {target_object_ar} في هذا الإطار الحالي."
                    return DetectResponse(
                        frame_id=frame_id,
                        detections=detections,
                        image_width=w,
                        image_height=h,
                        target_object_ar=target_object_ar,
                        target_found=False,
                        summary_ar=summary,
                        latency_ms=latency,
                        status="ok",
                    )

        # General scene detections summary
        if not detections:
            summary = "لم يتم رصد أي كائنات واضحة في الإطار."
        else:
            # Count detected classes
            counts: Dict[str, int] = {}
            for d in detections:
                counts[d.class_name_ar] = counts.get(d.class_name_ar, 0) + 1
            parts = [f"{cls} ({cnt})" if cnt > 1 else cls for cls, cnt in counts.items()]
            summary = f"الكائنات المرصودة: {', '.join(parts)}."

        return DetectResponse(
            frame_id=frame_id,
            detections=detections,
            image_width=w,
            image_height=h,
            summary_ar=summary,
            latency_ms=latency,
            status="ok",
        )
