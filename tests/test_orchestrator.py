"""Unit and integration tests for AMAV Orchestrator and Arabic Intent Routing."""
import pytest
from app.orchestrator import Orchestrator
from app.schemas import AssistRequest, BoundingBox, DetectionItem, DetectResponse

@pytest.fixture
def orchestrator():
    return Orchestrator()

def test_intent_routing_describe(orchestrator):
    assert orchestrator.route_intent("شنو قدامي؟")[0] == "describe"
    assert orchestrator.route_intent("صف المشهد")[0] == "describe"
    assert orchestrator.route_intent("صف ما ترى في هذه الصورة")[0] == "describe"
    assert orchestrator.route_intent("ماذا يوجد أمامي؟")[0] == "describe"

def test_intent_routing_read(orchestrator):
    assert orchestrator.route_intent("اقرأ المكتوب")[0] == "read"
    assert orchestrator.route_intent("اقرأ النص")[0] == "read"
    assert orchestrator.route_intent("شنو مكتوب على الورقة؟")[0] == "read"
    assert orchestrator.route_intent("قراءة النص")[0] == "read"

def test_intent_routing_find_aliases(orchestrator):
    mode, target = orchestrator.route_intent("وين القنينة؟")
    assert mode == "find"
    assert "قنين" in target

    mode, target = orchestrator.route_intent("وين الكرسي؟")
    assert mode == "find"
    assert "كرسي" in target

    mode, target = orchestrator.route_intent("ابحث عن اللابتوب")
    assert mode == "find"
    assert "لابتوب" in target

    mode, target = orchestrator.route_intent("وين الشخص؟")
    assert mode == "find"
    assert "شخص" in target

def test_intent_routing_repeat(orchestrator):
    assert orchestrator.route_intent("كرر")[0] == "repeat"
    assert orchestrator.route_intent("عيد الجواب")[0] == "repeat"
    assert orchestrator.route_intent("أعد")[0] == "repeat"

def test_intent_routing_general_ask(orchestrator):
    assert orchestrator.route_intent("ما هو لون هذه الحقيبة؟")[0] == "ask"
    assert orchestrator.route_intent("كم عدد الأشخاص الواقفين؟")[0] == "ask"

def test_unsupported_targets_detection(orchestrator):
    # COCO does not have doors or stairs; adapter should explicitly report unsupported
    target_en, reason = orchestrator.detection.normalize_target_query("باب")
    assert target_en is None
    assert reason is not None
    assert "الأبواب" in reason

    target_en, reason = orchestrator.detection.normalize_target_query("درج")
    assert target_en is None
    assert reason is not None
    assert "الدرج" in reason

def test_repeat_functionality(orchestrator):
    # Initial state
    res_repeat = orchestrator.execute_assist(AssistRequest(query_text="كرر", mode="repeat"))
    assert "لا توجد إجابة سابقة" in res_repeat.answer_ar

    # Simulate an answer stored
    orchestrator.last_valid_answer_ar = "أمامك طاولة عليها حاسوب محمول وقنينة ماء."
    res_repeat2 = orchestrator.execute_assist(AssistRequest(query_text="كرر", mode="repeat"))
    assert res_repeat2.answer_ar == "أمامك طاولة عليها حاسوب محمول وقنينة ماء."
    assert "memory_cache" in res_repeat2.source_components

def test_cancellation(orchestrator):
    req_id = "test-cancel-123"
    orchestrator.cancel_request(req_id)
    assert orchestrator.is_cancelled(req_id) is True

def test_end_to_end_find_assist(orchestrator):
    import base64
    from pathlib import Path
    fixture = Path("data/fixtures/scene_objects.jpg")
    if fixture.exists():
        with open(fixture, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        req = AssistRequest(mode="find", target_object_ar="قنينة", image_base64=b64)
        res = orchestrator.execute_assist(req)
        assert res.status == "ok"
        assert "قنينة" in res.answer_ar
def test_end_to_end_read_assist(orchestrator):
    import base64
    from pathlib import Path
    fixture = Path("data/fixtures/arabic_printed_notice.jpg")
    if fixture.exists():
        with open(fixture, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        req = AssistRequest(mode="read", image_base64=b64)
        res = orchestrator.execute_assist(req)
        assert res.status == "ok"
        assert "easyocr" in res.source_components
        assert len(res.answer_ar) > 5
        assert res.audio_base64 is not None

def test_intent_routing_greeting_and_empty(orchestrator):
    assert orchestrator.route_intent("مرحبا كيف تساعدني؟")[0] == "greeting"
    assert orchestrator.route_intent("السلام عليكم")[0] == "greeting"
    assert orchestrator.route_intent("عاشت ايدك")[0] == "greeting"
    assert orchestrator.route_intent("")[0] == "unknown"
    assert orchestrator.route_intent("   ")[0] == "unknown"

def test_frame_quality_analyzer_dark_frame(orchestrator):
    import numpy as np
    import cv2
    import base64
    # Pitch black frame
    dark_img = np.zeros((480, 640, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", dark_img)
    b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
    report = orchestrator.quality_analyzer.analyze(b64)
    assert report.is_usable is False
    assert report.issue == "underexposed"
    assert len(report.advice_ar) > 10
    assert report.metrics["brightness"] < 35.0

def test_detection_temporal_smoothing(orchestrator):
    import time
    # Populate temporal tracking history
    orchestrator.detection._target_history["bottle"] = {
        "timestamp": time.time(),
        "position": "center",
        "hits": 3,
    }
    assert "bottle" in orchestrator.detection._target_history
    assert orchestrator.detection._target_history["bottle"]["position"] == "center"
    assert orchestrator.detection._target_history["bottle"]["hits"] == 3

def test_real_qwen_vlm_inference(orchestrator):
    import base64
    from pathlib import Path
    fixture = Path("data/fixtures/scene_objects.jpg")
    if fixture.exists():
        with open(fixture, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        res = orchestrator.vlm.ask(
            question="صف ما تراه في الصورة باختصار",
            image_input=b64,
            frame_id="test_vlm_unit"
        )
        assert res.status == "ok"
        assert len(res.answer_ar) > 5
        assert "qwen3-vl:2b" in res.model

def test_vlm_thinking_suppression(orchestrator):
    # Ensure sanitize_answer correctly strips <think> blocks and analytical narration
    raw_with_think = "<think>\nThe user is asking about the image.\nLooking at the objects...\n</think>\nأمامك طاولة عليها حاسوب محمول."
    cleaned = orchestrator.vlm.sanitize_answer(raw_with_think)
    assert cleaned == "أمامك طاولة عليها حاسوب محمول."
    assert "The user is asking" not in cleaned

    # Ensure leaked English analytical monologue is rejected
    leaked_monologue = "Wait, the user provided a description of the image. Looking at the icons, maybe this is..."
    rejected = orchestrator.vlm.sanitize_answer(leaked_monologue)
    assert rejected == ""

