"""Frame quality assessment and retake guidance heuristics.
Analyzes brightness (underexposure/overexposure), blur (Laplacian variance),
and dimensions to provide real-time user feedback.
"""
from __future__ import annotations

import base64
import io
from typing import Dict, Optional
import cv2
import numpy as np
from PIL import Image

class FrameQualityReport:
    def __init__(
        self,
        is_usable: bool,
        issue: Optional[str] = None,
        advice_ar: Optional[str] = None,
        metrics: Optional[Dict[str, float]] = None,
    ):
        self.is_usable = is_usable
        self.issue = issue
        self.advice_ar = advice_ar
        self.metrics = metrics or {}

    def to_dict(self) -> dict:
        return {
            "is_usable": self.is_usable,
            "issue": self.issue,
            "advice_ar": self.advice_ar,
            "metrics": self.metrics,
        }

class FrameQualityAnalyzer:
    def __init__(
        self,
        min_brightness: float = 35.0,
        max_brightness: float = 230.0,
        min_blur_var: float = 40.0,
    ):
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.min_blur_var = min_blur_var

    def analyze(self, image_input: Image.Image | str | np.ndarray) -> FrameQualityReport:
        # Convert to numpy RGB
        if isinstance(image_input, str):
            if "," in image_input:
                image_input = image_input.split(",", 1)[1]
            raw = base64.b64decode(image_input)
            pil_img = Image.open(io.BytesIO(raw)).convert("RGB")
            np_img = np.array(pil_img)
        elif isinstance(image_input, Image.Image):
            np_img = np.array(image_input.convert("RGB"))
        elif isinstance(image_input, np.ndarray):
            np_img = image_input
        else:
            return FrameQualityReport(
                is_usable=False,
                issue="invalid_input",
                advice_ar="صيغة الصورة غير مدعومة.",
            )

        h, w = np_img.shape[:2]
        if w < 64 or h < 64:
            return FrameQualityReport(
                is_usable=False,
                issue="too_small",
                advice_ar="أبعاد الإطار صغيرة جداً للتحليل.",
                metrics={"width": w, "height": h},
            )

        # Grayscale conversion for luminance and blur analysis
        gray = cv2.cvtColor(np_img, cv2.COLOR_RGB2GRAY)

        # 1. Luminance / Brightness metric
        mean_brightness = float(np.mean(gray))

        # 2. Blur metric (Variance of Laplacian)
        lap = cv2.Laplacian(gray, cv2.CV_64F)
        blur_variance = float(lap.var())

        metrics = {
            "brightness": round(mean_brightness, 1),
            "blur_variance": round(blur_variance, 1),
            "width": w,
            "height": h,
        }

        # Darkness check
        if mean_brightness < self.min_brightness:
            return FrameQualityReport(
                is_usable=False,
                issue="underexposed",
                advice_ar="الإضاءة منخفضة جداً والمعتمة، يرجى التوجه نحو مصدر ضوء أو تشغيل إضاءة الغرفة.",
                metrics=metrics,
            )

        # Glare / Overexposure check
        if mean_brightness > self.max_brightness:
            return FrameQualityReport(
                is_usable=False,
                issue="overexposed",
                advice_ar="الإضاءة ساطعة جداً وهناك سطوع مباشر في الكاميرا، يرجى تعديل زاوية الرؤية.",
                metrics=metrics,
            )

        # Severe blur check
        if blur_variance < self.min_blur_var:
            return FrameQualityReport(
                is_usable=False,
                issue="blurry",
                advice_ar="الصورة غير واضحة أو مهتزة، يرجى تثبيت يدك والكاميرا لحظة التقاط المشهد.",
                metrics=metrics,
            )

        return FrameQualityReport(
            is_usable=True,
            issue=None,
            advice_ar=None,
            metrics=metrics,
        )
