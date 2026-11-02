"""YOLO11 object detection adapter with Arabic localization, Iraqi dialect synonyms,
multi-instance tracking continuity, and continuous search session state machine.
"""
from __future__ import annotations

import base64
import io
import math
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image

from app.config import DetectionConfig
from app.schemas import BoundingBox, DetectionItem, DetectResponse, SearchSessionState

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

# Arabic and Iraqi dialect synonyms mapped to COCO classes
ARABIC_ALIASES_TO_COCO: Dict[str, str] = {
    # Bottle & liquid containers (Iraqi: بطل، دولكة، ماي، مي)
    "قنينة": "bottle",
    "قارورة": "bottle",
    "زجاجة": "bottle",
    "بطل": "bottle",
    "دولكة": "bottle",
    "ماء": "bottle",
    "ماي": "bottle",
    "مي": "bottle",
    # Cups & mugs (Iraqi: قلاص، كاسة، فنجان، استكان)
    "كوب": "cup",
    "فنجان": "cup",
    "قلاص": "cup",
    "كاسة": "cup",
    "استكان": "cup",
    "قدح": "cup",
    # Person (Iraqi: رجال، مرة، ولد، بنية، احد)
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
    "طفل": "person",
    "احد": "person",
    "أحد": "person",
    # Chair
    "كرسي": "chair",
    "كراسي": "chair",
    "مقعد": "chair",
    # Couch / Sofa (Iraqi: قنفة، تخم)
    "قنفة": "couch",
    "تخم": "couch",
    "اريكة": "couch",
    "أريكة": "couch",
    "صوفة": "couch",
    # Table (Iraqi: ميز، منضدة)
    "طاولة": "dining table",
    "ميز": "dining table",
    "مكتب": "dining table",
    "منضدة": "dining table",
    # Bed (Iraqi: جرباية)
    "سرير": "bed",
    "جرباية": "bed",
    "منامة": "bed",
    # Bags (Iraqi: جنطة، شنطة)
    "حقيبة": "backpack",
    "شنطة": "backpack",
    "جنطة": "backpack",
    "حقيبة ظهر": "backpack",
    "جنطة ظهر": "backpack",
    "حقيبة يد": "handbag",
    "جنطة يد": "handbag",
    # Mobile phone
    "هاتف": "cell phone",
    "تلفون": "cell phone",
    "موبايل": "cell phone",
    "جوال": "cell phone",
    "خلوي": "cell phone",
    # Laptop & Computer (Iraqi: حاسبة، كمبيوتر)
    "لابتوب": "laptop",
    "حاسوب": "laptop",
    "كمبيوتر": "laptop",
    "حاسبة": "laptop",
    # Animals (Iraqi: بزونة، جلب)
    "قطة": "cat",
    "بزونة": "cat",
    "بس": "cat",
    "هر": "cat",
    "كلب": "dog",
    "جلب": "dog",
    "طير": "bird",
    "طائر": "bird",
    # Electronics / accessories
    "ريموت": "remote",
    "تحكم": "remote",
    "جهاز تحكم": "remote",
    "رموت": "remote",
    "ماوس": "mouse",
    "فارة": "mouse",
    "فأرة": "mouse",
    "كيبورد": "keyboard",
    "لوحة مفاتيح": "keyboard",
    "شاشة": "tv",
    "تلفزيون": "tv",
    "تلفاز": "tv",
    # Household
    "كتاب": "book",
    "كتب": "book",
    "دفتر": "book",
    "ملزمة": "book",
    "ساعة": "clock",
    "ساعة حائط": "clock",
    "ساعة يد": "clock",
    "مقص": "scissors",
    "فرشاة": "toothbrush",
    "فرشاة أسنان": "toothbrush",
    "ثلاجة": "refrigerator",
    "مايكروويف": "microwave",
    "مغسلة": "sink",
    "سيارة": "car",
    "سيارات": "car",
    "دراجة": "bicycle",
    "بايسكل": "bicycle",
    "ماتور": "motorcycle",
}

# Explicitly unsupported targets with educational guidance for blind users
EXPLICITLY_UNSUPPORTED_TARGETS = {
    "باب": "الأبواب ليست ضمن فئات كشف الكائنات المدعومة حالياً (COCO80)، وتتطلب نموذجاً مخصصاً.",
    "ابواب": "الأبواب ليست ضمن فئات كشف الكائنات المدعومة حالياً (COCO80)، وتتطلب نموذجاً مخصصاً.",
    "شباك": "النوافذ والشبابيك ليست ضمن فئات كشف الكائنات المدعومة حالياً.",
    "نافذة": "النوافذ والشبابيك ليست ضمن فئات كشف الكائنات المدعومة حالياً.",
    "درج": "الدرج والسلالم ليست ضمن فئات كشف الكائنات المدعومة حالياً (COCO80).",
    "سلم": "السلالم ليست ضمن فئات كشف الكائنات المدعومة حالياً (COCO80).",
    "سلالم": "الدرج والسلالم ليست ضمن فئات كشف الكائنات المدعومة حالياً (COCO80).",
    "حفرة": "الحفر والعوائق الأرضية ليست ضمن فئات كشف الكائنات وتتطلب مستشعرات عمق للأمان.",
    "رصيف": "حواف الأرصفة تتطلب مستشعرات عمق مخصصة ولا يمكن الاعتماد على كاميرا الألوان وحدها.",
    "صيدلية": "اللافتات والمحلات تتطلب قراءة نصوص أو نظام ملاحة خارجي.",
}

# Horizontal relative position labels (Image-relative convention)
POSITION_AR_MAP = {
    "left": "يسار الصورة",
    "center": "وسط الصورة",
    "right": "يمين الصورة",
}

class DetectionAdapter:
    def __init__(self, config: Optional[DetectionConfig] = None):
        self.config = config or DetectionConfig()
        self.model = None
        self._loaded = False
        self._load_error: Optional[str] = None

        # Temporal smoothing state for single queries
        self._target_history: Dict[str, dict] = {}
        self.history_ttl_seconds: float = 2.0

        # Continuous Search Sessions store
        # session_id -> state dict
        self._search_sessions: Dict[str, dict] = {}
        self.max_session_duration_s: float = 45.0
        self.speech_cooldown_s: float = 3.5
        import threading
        self._search_lock = threading.Lock()

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

    @staticmethod
    def _clean_ar(text: str) -> str:
        import re
        t = text.strip().lower()
        t = re.sub(r"[إأآا]", "ا", t)
        t = re.sub(r"ة", "ه", t)
        t = re.sub(r"[\u064B-\u065F]", "", t)
        t = re.sub(r"[!؟?.,،]", "", t)
        t = re.sub(r"^(ال|ا)", "", t).strip()
        return t

    def normalize_target_query(self, query: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """Normalize Arabic query to COCO class name if supported.
        Returns (coco_class_en, unsupported_reason_ar).
        """
        if not query:
            return None, None
        raw_cleaned = query.strip().lower()
        norm_q = self._clean_ar(raw_cleaned)

        # Check explicit unsupported targets
        for unsupp, reason in EXPLICITLY_UNSUPPORTED_TARGETS.items():
            if self._clean_ar(unsupp) in norm_q or unsupp in raw_cleaned:
                return None, reason

        # Check aliases
        for alias, coco_class in ARABIC_ALIASES_TO_COCO.items():
            clean_alias = self._clean_ar(alias)
            if clean_alias == norm_q or clean_alias in norm_q or alias in raw_cleaned:
                return coco_class, None

        # Check direct english
        for cls_name in COCO_ARABIC_NAMES.keys():
            if cls_name in raw_cleaned:
                return cls_name, None

        return None, None

    def _parse_image(self, image_input: Image.Image | str | np.ndarray) -> Image.Image:
        import numpy as np
        import cv2
        if isinstance(image_input, np.ndarray):
            if len(image_input.shape) == 3 and image_input.shape[2] == 3:
                return Image.fromarray(cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB))
            elif len(image_input.shape) == 2:
                return Image.fromarray(image_input).convert("RGB")
            return Image.fromarray(image_input)
        if isinstance(image_input, str):
            if (image_input.endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp")) or "/" in image_input or "\\" in image_input) and Path(image_input).exists():
                return Image.open(image_input).convert("RGB")
            else:
                if "," in image_input:
                    image_input = image_input.split(",", 1)[1]
                raw_bytes = base64.b64decode(image_input)
                return Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        if isinstance(image_input, Image.Image):
            return image_input.convert("RGB")
        return Image.fromarray(np.array(image_input)).convert("RGB")

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

        try:
            img = self._parse_image(image_input)
        except Exception as e:
            return DetectResponse(
                frame_id=frame_id,
                status="image_decode_error",
                error=f"Failed to decode image: {str(e)}",
                latency_ms=round((time.perf_counter() - t0) * 1000, 2),
            )

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

        # Run YOLO inference
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

                # Correct for mirrored camera preview
                if mirrored:
                    norm_cx = 1.0 - norm_cx

                # Horizontal position determination
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

        # Single-query target search summary
        if target_object_ar:
            target_ar_name = COCO_ARABIC_NAMES.get(target_en, target_object_ar)

            if target_matches:
                # Multi-instance sorting: sort by distance to image center (0.5)
                target_matches.sort(key=lambda it: abs(it.center_x - 0.5))
                primary = target_matches[0]
                direction_ar = POSITION_AR_MAP[primary.position]

                # Update temporal history
                prev = self._target_history.get(target_en)
                hits = (prev["hits"] + 1) if (prev and (now - prev["timestamp"]) < self.history_ttl_seconds) else 1
                self._target_history[target_en] = {
                    "timestamp": now,
                    "position": primary.position,
                    "hits": hits,
                }

                if len(target_matches) == 1:
                    summary = f"{target_ar_name} {direction_ar}."
                else:
                    pos_list = [POSITION_AR_MAP[m.position] for m in target_matches]
                    summary = f"أشوف {len(target_matches)} من {target_ar_name}: الأولى {pos_list[0]} والثانية {pos_list[1]}."

                return DetectResponse(
                    frame_id=frame_id,
                    detections=detections,
                    image_width=w,
                    image_height=h,
                    target_object_ar=target_object_ar,
                    target_found=True,
                    target_position=primary.position,
                    target_direction_ar=direction_ar,
                    instance_count=len(target_matches),
                    summary_ar=summary,
                    latency_ms=latency,
                    status="ok",
                )
            else:
                # Check recent history for temporal smoothing of momentary dropouts
                prev = self._target_history.get(target_en)
                if prev and (now - prev["timestamp"]) < 1.2 and prev.get("hits", 0) >= 2:
                    pos = prev["position"]
                    direction_ar = POSITION_AR_MAP[pos]
                    summary = f"{target_ar_name} كانت {direction_ar}، ثبّت الكاميرا."
                    return DetectResponse(
                        frame_id=frame_id,
                        detections=detections,
                        image_width=w,
                        image_height=h,
                        target_object_ar=target_object_ar,
                        target_found=True,
                        target_position=pos,
                        target_direction_ar=direction_ar,
                        instance_count=1,
                        summary_ar=summary,
                        latency_ms=latency,
                        status="ok",
                    )
                else:
                    if prev and (now - prev["timestamp"]) >= self.history_ttl_seconds:
                        self._target_history.pop(target_en, None)

                    summary = f"لم يتم رصد {target_object_ar} في الإطار الحالي."
                    return DetectResponse(
                        frame_id=frame_id,
                        detections=detections,
                        image_width=w,
                        image_height=h,
                        target_object_ar=target_object_ar,
                        target_found=False,
                        instance_count=0,
                        summary_ar=summary,
                        latency_ms=latency,
                        status="ok",
                    )

        # General scene detections summary
        if not detections:
            summary = "لم يتم رصد أي كائنات واضحة في الإطار."
        else:
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

    # -------------------------------------------------------------
    # Continuous Object Search Session State Machine
    # -------------------------------------------------------------
    def start_search_session(self, target_object_ar: str) -> SearchSessionState:
        session_id = f"search_{uuid.uuid4().hex[:8]}"
        target_en, unsupported_reason = self.normalize_target_query(target_object_ar)

        target_ar_name = COCO_ARABIC_NAMES.get(target_en, target_object_ar) if target_en else target_object_ar

        if unsupported_reason:
            state = SearchSessionState(
                session_id=session_id,
                target_query_ar=target_object_ar,
                status="stopped",
                direction_text_ar=unsupported_reason,
                should_announce=True,
                announcement_text_ar=unsupported_reason,
            )
            return state

        now = time.time()
        self._search_sessions[session_id] = {
            "session_id": session_id,
            "target_query_ar": target_object_ar,
            "target_class_en": target_en,
            "target_ar_name": target_ar_name,
            "start_time": now,
            "last_step_time": now,
            "last_announced_direction": None,
            "last_announced_time": 0.0,
            "consecutive_lost_frames": 0,
            "lost_announced": False,
            "last_primary_coords": None,
            "status": "active",
        }

        # Initial prompt announcement
        initial_msg = f"بدأت البحث عن {target_ar_name}. حرّك الكاميرا بهدوء."
        return SearchSessionState(
            session_id=session_id,
            target_query_ar=target_object_ar,
            target_class_en=target_en,
            status="active",
            direction_text_ar=initial_msg,
            should_announce=True,
            announcement_text_ar=initial_msg,
            elapsed_seconds=0.0,
        )

    def step_search_session(
        self,
        session_id: str | SearchSessionState,
        image_input: Image.Image | str,
        mirrored: bool = False,
    ) -> SearchSessionState:
        if isinstance(session_id, SearchSessionState):
            sid = session_id.session_id
        else:
            sid = str(session_id)
        session = self._search_sessions.get(sid)
        now = time.time()

        if not session or session.get("status") == "stopped":
            return SearchSessionState(
                session_id=session_id,
                target_query_ar="",
                status="stopped",
                direction_text_ar="جلسة البحث متوقفة.",
                should_announce=False,
            )

        elapsed = now - session["start_time"]
        if elapsed > self.max_session_duration_s:
            session["status"] = "timeout"
            timeout_msg = "انتهت جلسة البحث."
            return SearchSessionState(
                session_id=session_id,
                target_query_ar=session["target_query_ar"],
                target_class_en=session["target_class_en"],
                status="timeout",
                direction_text_ar=timeout_msg,
                should_announce=True,
                announcement_text_ar=timeout_msg,
                elapsed_seconds=round(elapsed, 1),
            )

        # Guard: Non-blocking acquisition drops stale frames when inference is busy
        if not self._search_lock.acquire(blocking=False):
            return SearchSessionState(
                session_id=session_id,
                target_query_ar=session.get("target_query_ar", ""),
                target_class_en=session.get("target_class_en"),
                status=session.get("status", "tracking"),
                direction_text_ar=session.get("last_direction_display", "جاري المتابعة..."),
                should_announce=False,
                elapsed_seconds=round(elapsed, 1),
            )

        try:
            target_en = session["target_class_en"]
            target_ar_name = session["target_ar_name"]

            # Run object detection
            det_res = self.detect(
                image_input=image_input,
                target_object_ar=session["target_query_ar"],
                mirrored=mirrored,
            )

            matches = [d for d in det_res.detections if d.class_name_en == target_en]

            should_announce = False
            announcement_text = None
            direction_rel = None
            direction_text = ""

            if matches:
                session["consecutive_lost_frames"] = 0
                session["lost_announced"] = False
                session["status"] = "tracking"

                # Multi-instance continuity: select the instance closest to previous coordinates
                last_coords = session.get("last_primary_coords")
                if last_coords and len(matches) > 1:
                    matches.sort(key=lambda it: math.hypot(it.center_x - last_coords[0], it.center_y - last_coords[1]))
                else:
                    matches.sort(key=lambda it: abs(it.center_x - 0.5))

                primary = matches[0]
                session["last_primary_coords"] = (primary.center_x, primary.center_y)
                direction_rel = primary.position
                direction_text = POSITION_AR_MAP[direction_rel]

                if len(matches) == 1:
                    direction_display = f"{target_ar_name} {direction_text}."
                else:
                    pos2 = POSITION_AR_MAP[matches[1].position]
                    direction_display = f"أشوف {len(matches)} من {target_ar_name}: الأولى {direction_text} والثانية {pos2}."

                session["last_direction_display"] = direction_display

                # Direction change or cooldown speech check
                last_dir = session.get("last_announced_direction")
                time_since_speech = now - session.get("last_announced_time", 0.0)

                if last_dir != direction_rel or time_since_speech >= self.speech_cooldown_s:
                    should_announce = True
                    announcement_text = f"{target_ar_name} {direction_text}."
                    session["last_announced_direction"] = direction_rel
                    session["last_announced_time"] = now

                res_state = SearchSessionState(
                    session_id=session_id,
                    target_query_ar=session["target_query_ar"],
                    target_class_en=target_en,
                    status="tracking",
                    direction_relative=direction_rel,
                    direction_text_ar=direction_display,
                    instance_count=len(matches),
                    stable_lost_count=0,
                    should_announce=should_announce,
                    announcement_text_ar=announcement_text,
                    elapsed_seconds=round(elapsed, 1),
                )
            else:
                # Target lost in this frame
                session["consecutive_lost_frames"] += 1
                lost_count = session["consecutive_lost_frames"]
                session["status"] = "lost"

                # Announce disappearance once target has been missing for a stable interval (2 consecutive frames)
                if lost_count >= 2 and not session.get("lost_announced", False):
                    should_announce = True
                    announcement_text = "هسه ما أشوفها."
                    session["lost_announced"] = True
                    session["last_announced_direction"] = None
                    session["last_announced_time"] = now

                lost_display = "هسه ما أشوفها." if lost_count >= 2 else "جاري البحث..."
                session["last_direction_display"] = lost_display

                res_state = SearchSessionState(
                    session_id=session_id,
                    target_query_ar=session["target_query_ar"],
                    target_class_en=target_en,
                    status="lost",
                    direction_relative=None,
                    direction_text_ar=lost_display,
                    instance_count=0,
                    stable_lost_count=lost_count,
                    should_announce=should_announce,
                    announcement_text_ar=announcement_text,
                    elapsed_seconds=round(elapsed, 1),
                )
            return res_state
        finally:
            self._search_lock.release()

    def stop_search_session(self, session_id: str) -> SearchSessionState:
        session = self._search_sessions.pop(session_id, None)
        target = session.get("target_query_ar", "") if session else ""
        return SearchSessionState(
            session_id=session_id,
            target_query_ar=target,
            status="stopped",
            direction_text_ar="تم إيقاف جلسة البحث.",
            should_announce=True,
            announcement_text_ar="تم إيقاف البحث.",
        )
