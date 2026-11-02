"""Frame quality assessment and retake guidance heuristics.
Analyzes brightness (underexposure/overexposure), blur (Laplacian variance),
empty/solid frames, frame freshness, and OCR document positioning.
"""
from __future__ import annotations

import base64
import io
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import cv2
import numpy as np
from PIL import Image

class FrameQualityReport:
    def __init__(
        self,
        is_usable: bool,
        issue: Optional[str] = None,
        advice_ar: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        should_speak: bool = True,
        duration_ms: float = 0.0,
    ):
        self.is_usable = is_usable
        self.issue = issue
        self.advice_ar = advice_ar
        self.metrics = metrics or {}
        self.should_speak = should_speak
        self.duration_ms = duration_ms

    def to_dict(self) -> dict:
        return {
            "is_usable": self.is_usable,
            "issue": self.issue,
            "advice_ar": self.advice_ar,
            "metrics": self.metrics,
            "should_speak": self.should_speak,
            "duration_ms": self.duration_ms,
        }

class FrameQualityAnalyzer:
    def __init__(
        self,
        min_brightness: float = 30.0,
        max_brightness: float = 248.0,
        min_blur_var: float = 35.0,
        min_std_dev: float = 3.0,
        min_dim: int = 64,
        cooldown_seconds: float = 8.0,
        max_frame_age_s: float = 5.0,
    ):
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.min_blur_var = min_blur_var
        self.min_std_dev = min_std_dev
        self.min_dim = min_dim
        self.cooldown_seconds = cooldown_seconds
        self.max_frame_age_s = max_frame_age_s

        # Cooldown state: maps issue_type -> last_spoken_time
        self._last_spoken_times: Dict[str, float] = {}

    def _should_speak_warning(self, issue: str) -> bool:
        now = time.time()
        last = self._last_spoken_times.get(issue, 0.0)
        if (now - last) >= self.cooldown_seconds:
            self._last_spoken_times[issue] = now
            return True
        return False

    def reset_cooldowns(self):
        self._last_spoken_times.clear()

    def analyze(
        self,
        image_input: Image.Image | str | np.ndarray,
        frame_timestamp: Optional[float] = None,
        force_override: bool = False,
    ) -> FrameQualityReport:
        t0 = time.perf_counter()

        # Check frame freshness if timestamp provided
        if frame_timestamp is not None:
            now_ts = time.time()
            age_s = now_ts - frame_timestamp
            if age_s > self.max_frame_age_s and not force_override:
                duration_ms = round((time.perf_counter() - t0) * 1000, 2)
                return FrameQualityReport(
                    is_usable=False,
                    issue="stale_frame",
                    advice_ar="لم يتم استلام إطار جديد من الكاميرا.",
                    metrics={"frame_age_s": round(age_s, 2)},
                    should_speak=self._should_speak_warning("stale_frame"),
                    duration_ms=duration_ms,
                )

        # Convert to numpy RGB
        try:
            if isinstance(image_input, str):
                cleaned_str = image_input.strip()
                if not cleaned_str:
                    duration_ms = round((time.perf_counter() - t0) * 1000, 2)
                    return FrameQualityReport(
                        is_usable=False,
                        issue="empty_frame",
                        advice_ar="الكاميرا غير متصلة أو الإطار فارغ.",
                        metrics={"error": "empty_string"},
                        should_speak=self._should_speak_warning("empty_frame"),
                        duration_ms=duration_ms,
                    )
                # Check if it's a file path
                if (cleaned_str.endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp")) or "/" in cleaned_str or "\\" in cleaned_str) and Path(cleaned_str).exists():
                    pil_img = Image.open(cleaned_str).convert("RGB")
                    np_img = np.array(pil_img)
                else:
                    if "," in cleaned_str:
                        cleaned_str = cleaned_str.split(",", 1)[1]
                    raw = base64.b64decode(cleaned_str)
                    pil_img = Image.open(io.BytesIO(raw)).convert("RGB")
                    np_img = np.array(pil_img)
            elif isinstance(image_input, Image.Image):
                np_img = np.array(image_input.convert("RGB"))
            elif isinstance(image_input, np.ndarray):
                np_img = image_input
            else:
                duration_ms = round((time.perf_counter() - t0) * 1000, 2)
                return FrameQualityReport(
                    is_usable=False,
                    issue="invalid_input",
                    advice_ar="الكاميرا غير متصلة أو الإطار فارغ.",
                    metrics={},
                    should_speak=self._should_speak_warning("invalid_input"),
                    duration_ms=duration_ms,
                )
        except Exception as e:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            return FrameQualityReport(
                is_usable=False,
                issue="decode_error",
                advice_ar="الكاميرا غير متصلة أو الإطار فارغ.",
                metrics={"error": str(e)},
                should_speak=self._should_speak_warning("decode_error"),
                duration_ms=duration_ms,
            )

        if np_img is None or np_img.size == 0:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            return FrameQualityReport(
                is_usable=False,
                issue="empty_frame",
                advice_ar="الكاميرا غير متصلة أو الإطار فارغ.",
                metrics={},
                should_speak=self._should_speak_warning("empty_frame"),
                duration_ms=duration_ms,
            )

        h, w = np_img.shape[:2]
        if w < self.min_dim or h < self.min_dim:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            return FrameQualityReport(
                is_usable=False,
                issue="too_small",
                advice_ar="أبعاد الإطار صغيرة جداً للتحليل.",
                metrics={"width": w, "height": h},
                should_speak=self._should_speak_warning("too_small"),
                duration_ms=duration_ms,
            )

        # Grayscale conversion for luminance, blur, and variance analysis
        gray = cv2.cvtColor(np_img, cv2.COLOR_RGB2GRAY)
        mean_brightness = float(np.mean(gray))
        pixel_std = float(np.std(gray))

        # Variance of Laplacian for blur detection
        lap = cv2.Laplacian(gray, cv2.CV_64F)
        blur_variance = float(lap.var())

        metrics = {
            "brightness": round(mean_brightness, 1),
            "blur_variance": round(blur_variance, 1),
            "std_dev": round(pixel_std, 2),
            "width": w,
            "height": h,
            "forced_override": force_override,
        }

        # 1. Darkness / Underexposure check
        # Note: Do not assume camera is physically covered, use wording supported by observation
        if mean_brightness < self.min_brightness and not force_override:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            return FrameQualityReport(
                is_usable=False,
                issue="underexposed",
                advice_ar="الإضاءة قليلة، جرّب مكان أضوى.",
                metrics=metrics,
                should_speak=self._should_speak_warning("underexposed"),
                duration_ms=duration_ms,
            )

        # 2. Check for solid blank image (all white, all grey, or uniform solid color)
        if pixel_std < self.min_std_dev and not force_override:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            return FrameQualityReport(
                is_usable=False,
                issue="solid_or_empty",
                advice_ar="الكاميرا غير متصلة أو الإطار فارغ.",
                metrics=metrics,
                should_speak=self._should_speak_warning("solid_or_empty"),
                duration_ms=duration_ms,
            )

        # 3. Excessive glare / Overexposure check
        # Avoid false rejection on printed white documents: high mean brightness with good text contrast (std_dev >= 20) is usable!
        is_glare = (mean_brightness > self.max_brightness and pixel_std < 20.0) or (mean_brightness > 252.0 and pixel_std < 10.0)
        if is_glare and not force_override:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            return FrameQualityReport(
                is_usable=False,
                issue="overexposed",
                advice_ar="الإضاءة ساطعة جداً، عدّل زاوية الكاميرا.",
                metrics=metrics,
                should_speak=self._should_speak_warning("overexposed"),
                duration_ms=duration_ms,
            )

        # 4. Severe blur check (motion blur)
        if blur_variance < self.min_blur_var and not force_override:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            return FrameQualityReport(
                is_usable=False,
                issue="blurry",
                advice_ar="ثبّت الكاميرا لحظة.",
                metrics=metrics,
                should_speak=self._should_speak_warning("blurry"),
                duration_ms=duration_ms,
            )

        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        return FrameQualityReport(
            is_usable=True,
            issue=None,
            advice_ar=None,
            metrics=metrics,
            should_speak=False,
            duration_ms=duration_ms,
        )

    def analyze_ocr_guidance(
        self,
        image_shape: tuple[int, int],
        ocr_items: List[Any],
    ) -> Optional[Dict[str, Any]]:
        """Provides document positioning and text size guidance for OCR."""
        if not ocr_items:
            return None

        h, w = image_shape[:2]
        heights = []
        is_clipped = False

        margin_x = w * 0.03
        margin_y = h * 0.03

        for item in ocr_items:
            bbox = getattr(item, "bbox", None) or (item.get("bbox") if isinstance(item, dict) else None)
            if not bbox or len(bbox) < 4:
                continue

            xs = [pt[0] for pt in bbox]
            ys = [pt[1] for pt in bbox]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)

            box_h = max_y - min_y
            if box_h > 0:
                heights.append(box_h)

            # Check if text is clipped near outer image boundary
            if min_x < margin_x or max_x > (w - margin_x) or min_y < margin_y or max_y > (h - margin_y):
                is_clipped = True

        if not heights:
            return None

        median_height = float(np.median(heights))
        # Text is too small/far away (less than 18px or less than 2.5% of frame height)
        if median_height < max(18.0, h * 0.025):
            return {
                "issue": "text_too_small",
                "advice_ar": "قرّب الورقة شوي.",
                "median_height": round(median_height, 1),
            }

        if is_clipped:
            return {
                "issue": "document_clipped",
                "advice_ar": "عدّل زاوية الورقة لتظهر بالكامل.",
                "median_height": round(median_height, 1),
            }

        return None
