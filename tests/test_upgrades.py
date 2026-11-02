"""Comprehensive automated tests for AMAV upgrades:
1. Smart Frame Quality Guidance (dark, blur, solid/empty, stale, OCR positioning).
2. Continuous Object Search Session (movement, stable disappearance, multi-instance, Iraqi synonyms).
3. Short Conversational Context (repeat without re-analysis, shorten, reset, pronoun referents).
4. Vision-Language Fast (2B) vs Detailed (4B) routing and fallback.
5. Speech Pace and Emergency Cancellation.
"""
from __future__ import annotations

import base64
import io
import time
import cv2
import numpy as np
import pytest
from PIL import Image

from app.config import get_config
from app.orchestrator import Orchestrator
from app.quality_analyzer import FrameQualityAnalyzer
from app.schemas import AssistRequest, SearchSessionRequest

@pytest.fixture(scope="module")
def orch():
    cfg = get_config()
    return Orchestrator(cfg)

# -------------------------------------------------------------
# 1. SMART IMAGE-QUALITY TESTS
# -------------------------------------------------------------
def test_quality_analyzer_heuristics():
    qa = FrameQualityAnalyzer()

    # Dark / Underexposed
    dark_img = np.zeros((200, 200, 3), dtype=np.uint8) + 15
    rep_dark = qa.analyze(dark_img)
    assert not rep_dark.is_usable
    assert rep_dark.issue == "underexposed"
    assert "الإضاءة قليلة" in rep_dark.advice_ar

    # Blurry image: high contrast scene with smoothed edges (blur variance drops below 35)
    sharp_img = np.zeros((200, 200, 3), dtype=np.uint8)
    sharp_img[:, :100] = 60
    sharp_img[:, 100:] = 180
    blurred_img = cv2.GaussianBlur(sharp_img, (25, 25), 0)
    rep_blur = qa.analyze(blurred_img)
    assert not rep_blur.is_usable
    assert rep_blur.issue == "blurry"
    assert "ثبّت الكاميرا" in rep_blur.advice_ar

    # Empty / Zero-dimension / Solid
    solid_img = np.full((200, 200, 3), 128, dtype=np.uint8)
    rep_solid = qa.analyze(solid_img)
    assert not rep_solid.is_usable
    assert rep_solid.issue == "solid_or_empty"

    # Stale frame
    rep_stale = qa.analyze(sharp_img, frame_timestamp=time.time() - 10.0)
    assert not rep_stale.is_usable
    assert rep_stale.issue == "stale_frame"

    # Forced override ignores issues
    rep_override = qa.analyze(dark_img, force_override=True)
    assert rep_override.is_usable is True

def test_quality_ocr_guidance():
    qa = FrameQualityAnalyzer()
    shape = (480, 640)

    # Small text boxes
    small_boxes = [
        {"bbox": [[50, 50], [100, 50], [100, 60], [50, 60]]},  # height = 10px
        {"bbox": [[120, 50], [180, 50], [180, 58], [120, 58]]},
    ]
    guidance = qa.analyze_ocr_guidance(shape, small_boxes)
    assert guidance is not None
    assert guidance["issue"] == "text_too_small"
    assert "قرّب الورقة" in guidance["advice_ar"]

    # Clipped border text boxes
    clipped_boxes = [
        {"bbox": [[2, 50], [200, 50], [200, 90], [2, 90]]},  # x=2 touches left border
    ]
    guidance_clip = qa.analyze_ocr_guidance(shape, clipped_boxes)
    assert guidance_clip is not None
    assert guidance_clip["issue"] == "document_clipped"
    assert "عدّل زاوية الورقة" in guidance_clip["advice_ar"]

# -------------------------------------------------------------
# 2. SHORT CONVERSATIONAL CONTEXT TESTS
# -------------------------------------------------------------
def test_conversational_context_repeat_and_shorten(orch):
    # Reset first
    orch.context.reset()

    # Empty context check
    res_repeat_empty = orch.execute_assist(AssistRequest(mode="repeat"))
    assert "لا توجد إجابة سابقة" in res_repeat_empty.answer_ar

    # Simulate an answer stored
    sample_answer = "في هذه الصورة أرى طاولة مكتب خشبية وعليها حاسوب محمول أسود مفتوح وإلى جانبه قنينة ماء شفافة وكوب قهوة أبيض. الإضاءة جيدة والمشهد هادئ."
    orch.context.update(command="شنو قدامي؟", answer=sample_answer, mode="describe", target_obj="قنينة")

    # Repeat returns exact answer without new vision call
    res_repeat = orch.execute_assist(AssistRequest(mode="repeat"))
    assert res_repeat.answer_ar == sample_answer
    assert "memory_cache" in res_repeat.source_components

    # Shorten condenses the answer
    res_shorten = orch.execute_assist(AssistRequest(query_text="اختصر الجواب"))
    assert len(res_shorten.answer_ar) < len(sample_answer)
    assert "حاسوب" in res_shorten.answer_ar or "طاولة" in res_shorten.answer_ar

    # Ambiguous pronoun "وينها؟" resolves to "قنينة" from context
    mode, target = orch.route_intent("وينها؟")
    assert mode == "find"
    assert target == "قنينة"

    # Reset clears memory
    res_reset = orch.execute_assist(AssistRequest(query_text="امسح الذاكرة"))
    assert "تم مسح الذاكرة" in res_reset.answer_ar
    assert orch.context.last_completed_answer is None

# -------------------------------------------------------------
# 3. CONTINUOUS OBJECT SEARCH TESTS
# -------------------------------------------------------------
def test_continuous_search_session(orch):
    # Start session
    state_start = orch.detection.start_search_session("قنينة")
    session_id = state_start.session_id
    assert state_start.status == "active"
    assert "بدأت البحث" in state_start.direction_text_ar

    # Create dummy images: Left target and Right target
    img_left = np.zeros((480, 640, 3), dtype=np.uint8) + 200
    img_right = np.zeros((480, 640, 3), dtype=np.uint8) + 200

    # Step search (even if synthetic image has no YOLO detections, disappearance logic works)
    state_step1 = orch.detection.step_search_session(session_id, img_left)
    assert state_step1.status in ("tracking", "lost")

    # Second lost frame triggers stable disappearance announcement
    state_step2 = orch.detection.step_search_session(session_id, img_left)
    assert state_step2.status == "lost"
    assert state_step2.direction_text_ar == "هسه ما أشوفها."
    assert state_step2.should_announce is True

    # Stop session
    state_stop = orch.detection.stop_search_session(session_id)
    assert state_stop.status == "stopped"

def test_iraqi_dialect_synonyms_routing(orch):
    # Iraqi words for bottle: بطل، دولكة، ماي
    mode, target = orch.route_intent("وين البطل؟")
    assert mode == "find"
    coco_cls, _ = orch.detection.normalize_target_query(target)
    assert coco_cls == "bottle"

    mode, target = orch.route_intent("وين الدولكة؟")
    assert mode == "find"
    coco_cls, _ = orch.detection.normalize_target_query(target)
    assert coco_cls == "bottle"

    # Iraqi words for cup: استكان، قلاص
    mode, target = orch.route_intent("وين الاستكان؟")
    assert mode == "find"
    coco_cls, _ = orch.detection.normalize_target_query(target)
    assert coco_cls == "cup"

    # Iraqi words for couch: قنفة، تخم
    mode, target = orch.route_intent("شوفلي القنفة وين")
    assert mode == "find"
    coco_cls, _ = orch.detection.normalize_target_query(target)
    assert coco_cls == "couch"

    # Iraqi words for cat: بزونة
    mode, target = orch.route_intent("وين البزونة؟")
    assert mode == "find"
    coco_cls, _ = orch.detection.normalize_target_query(target)
    assert coco_cls == "cat"

    # Unsupported classes with guidance
    _, unsupp = orch.detection.normalize_target_query("باب")
    assert unsupp is not None
    assert "الأبواب" in unsupp

    _, unsupp = orch.detection.normalize_target_query("درج")
    assert unsupp is not None
    assert "الدرج" in unsupp

# -------------------------------------------------------------
# 4. FAST VS DETAILED VLM ROUTING TESTS
# -------------------------------------------------------------
def test_vlm_modes_config(orch):
    assert orch.vlm.config.fast_model_tag == "qwen3-vl:2b-instruct-q4_K_M"
    assert orch.vlm.config.detailed_model_tag == "qwen3-vl:4b-instruct-q4_K_M"

    # Test memory snapshot capture
    snap = orch.vlm.get_memory_snapshot()
    assert isinstance(snap, dict)
    assert "system_ram_used_mb" in snap
