"""EasyOCR Adapter for Arabic and English printed text recognition."""
from __future__ import annotations

import base64
import io
import time
from pathlib import Path
from typing import List, Optional
import numpy as np
from PIL import Image

from app.config import OCRConfig
from app.schemas import OCRItem, OCRResponse

class OCRAdapter:
    def __init__(self, config: Optional[OCRConfig] = None):
        self.config = config or OCRConfig()
        self.reader = None
        self._loaded = False
        self._load_error: Optional[str] = None

    def load_model(self) -> bool:
        if self._loaded and self.reader is not None:
            return True
        try:
            import easyocr
            model_dir = Path(self.config.model_dir)
            model_dir.mkdir(parents=True, exist_ok=True)
            self.reader = easyocr.Reader(
                lang_list=self.config.languages,
                gpu=self.config.gpu,
                model_storage_directory=str(model_dir),
                download_enabled=False,
                verbose=False,
            )
            self._loaded = True
            self._load_error = None
            return True
        except Exception as e:
            # Fallback with download enabled if missing files
            try:
                import easyocr
                model_dir = Path(self.config.model_dir)
                self.reader = easyocr.Reader(
                    lang_list=self.config.languages,
                    gpu=self.config.gpu,
                    model_storage_directory=str(model_dir),
                    download_enabled=True,
                    verbose=False,
                )
                self._loaded = True
                self._load_error = None
                return True
            except Exception as e2:
                self._load_error = str(e2)
                self._loaded = False
                return False

    def is_ready(self) -> bool:
        return self._loaded and self.reader is not None

    @staticmethod
    def preprocess_image(img_rgb: np.ndarray) -> np.ndarray:
        """Apply CLAHE contrast enhancement on luminance channel for low-contrast images."""
        import cv2
        lab = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        enhanced_lab = cv2.merge((cl, a, b))
        return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2RGB)

    @staticmethod
    def sort_reading_order(items: List[OCRItem]) -> List[OCRItem]:
        """Sort detected OCR items top-to-bottom by line, and right-to-left for Arabic text."""
        if not items:
            return []

        # Calculate line height approximation
        heights = []
        for it in items:
            ys = [pt[1] for pt in it.bbox]
            heights.append(max(ys) - min(ys))
        median_h = float(np.median(heights)) if heights else 20.0
        line_thresh = max(14.0, median_h * 0.65)

        # Sort items primarily by top y
        sorted_by_y = sorted(items, key=lambda it: min(pt[1] for pt in it.bbox))

        # Group into lines
        lines: List[List[OCRItem]] = []
        current_line: List[OCRItem] = []
        current_line_y = None

        for it in sorted_by_y:
            item_y = min(pt[1] for pt in it.bbox)
            if current_line_y is None or abs(item_y - current_line_y) < line_thresh:
                current_line.append(it)
                current_line_y = item_y if current_line_y is None else (current_line_y + item_y) / 2.0
            else:
                lines.append(current_line)
                current_line = [it]
                current_line_y = item_y
        if current_line:
            lines.append(current_line)

        # Sort within each line: Arabic text right-to-left (descending min x), English left-to-right (ascending min x)
        sorted_items: List[OCRItem] = []
        for line in lines:
            combined_line_text = " ".join(it.text for it in line)
            is_arabic = any("\u0600" <= ch <= "\u06FF" for ch in combined_line_text)
            if is_arabic:
                line_sorted = sorted(line, key=lambda it: min(pt[0] for pt in it.bbox), reverse=True)
            else:
                line_sorted = sorted(line, key=lambda it: min(pt[0] for pt in it.bbox))
            sorted_items.extend(line_sorted)

        return sorted_items

    def recognize(
        self,
        image_input: Image.Image | str | np.ndarray,
        frame_id: Optional[str] = None,
        apply_preprocessing: bool = False,
    ) -> OCRResponse:
        t0 = time.perf_counter()

        # Parse image input
        if isinstance(image_input, str):
            if (image_input.endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp")) or "/" in image_input or "\\" in image_input) and Path(image_input).exists():
                pil_img = Image.open(image_input).convert("RGB")
                np_img = np.array(pil_img)
            else:
                if "," in image_input:
                    image_input = image_input.split(",", 1)[1]
                raw_bytes = base64.b64decode(image_input)
                pil_img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
                np_img = np.array(pil_img)
        elif isinstance(image_input, Image.Image):
            pil_img = image_input.convert("RGB")
            np_img = np.array(pil_img)
        elif isinstance(image_input, np.ndarray):
            np_img = image_input
        else:
            return OCRResponse(
                frame_id=frame_id,
                status="invalid_input",
                error="نوع الصورة غير مدعوم للتعرف الضوئي",
                latency_ms=round((time.perf_counter() - t0) * 1000, 2),
            )

        if not self.is_ready():
            ok = self.load_model()
            if not ok:
                return OCRResponse(
                    frame_id=frame_id,
                    status="model_not_ready",
                    error=self._load_error or "نموذج التعرف الضوئي EasyOCR غير محمل",
                    latency_ms=round((time.perf_counter() - t0) * 1000, 2),
                )

        target_img = self.preprocess_image(np_img) if apply_preprocessing else np_img

        try:
            results = self.reader.readtext(target_img, detail=self.config.detail)
        except Exception as e:
            return OCRResponse(
                frame_id=frame_id,
                status="ocr_execution_error",
                error=f"خطأ أثناء تشغيل EasyOCR: {str(e)}",
                latency_ms=round((time.perf_counter() - t0) * 1000, 2),
            )

        raw_items: List[OCRItem] = []
        raw_lines: List[str] = []

        for res in results:
            bbox, text, conf = res
            clean_text = str(text).strip()
            if clean_text and float(conf) >= self.config.min_confidence:
                norm_bbox = [[float(pt[0]), float(pt[1])] for pt in bbox]
                raw_items.append(
                    OCRItem(
                        text=clean_text,
                        confidence=round(float(conf), 3),
                        bbox=norm_bbox,
                    )
                )
                raw_lines.append(clean_text)

        # Apply reading order sorting
        ordered_items = self.sort_reading_order(raw_items)
        ordered_lines = [it.text for it in ordered_items]

        raw_combined = "\n".join(raw_lines)
        combined = "\n".join(ordered_lines)
        latency = round((time.perf_counter() - t0) * 1000, 2)

        return OCRResponse(
            frame_id=frame_id,
            text_combined=combined,
            raw_text=raw_combined,
            preprocessing_applied=apply_preprocessing,
            items=ordered_items,
            status="ok",
            latency_ms=latency,
        )
