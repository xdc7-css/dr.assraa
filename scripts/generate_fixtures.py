"""Fixture generator for offline and repeatable model testing with accurate Arabic text shaping.
Generates 10 diverse test fixtures for comprehensive 2B vs 4B VLM benchmark, OCR,
object detection, and quality analyzer evaluation.
"""
from __future__ import annotations

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = PROJECT_ROOT / "data" / "fixtures"

def render_arabic_text(draw: ImageDraw.ImageDraw, pos: tuple[int, int], text: str, font: ImageFont.FreeTypeFont, fill: tuple[int, int, int]):
    """Renders Arabic and mixed script text with natural character shaping and BiDi layout."""
    reshaped = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped)
    draw.text(pos, bidi_text, font=font, fill=fill)

def get_font(size: int):
    font_path = "C:/Windows/Fonts/tahoma.ttf"
    try:
        return ImageFont.truetype(font_path, size)
    except Exception:
        return ImageFont.load_default()

def generate_all_fixtures():
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {}

    # 1. Academic Lab Printed Notice
    f1 = FIXTURES_DIR / "arabic_printed_notice.jpg"
    im1 = Image.new("RGB", (700, 360), color=(255, 255, 255))
    d1 = ImageDraw.Draw(im1)
    d1.rectangle([10, 10, 690, 350], outline=(30, 41, 59), width=3)
    d1.rectangle([15, 15, 685, 345], outline=(148, 163, 184), width=1)
    t_lg, t_md, t_sm = get_font(28), get_font(22), get_font(18)
    lines1 = [
        ((80, 40), "جمهورية العراق - وزارة التعليم العالي", t_lg, (15, 23, 42)),
        ((120, 105), "قسم هندسة الحاسوب والذكاء الاصطناعي", t_lg, (29, 78, 216)),
        ((160, 175), "مختبر الرؤية الحاسوبية - ROOM 204", t_md, (15, 23, 42)),
        ((200, 240), "يرجى الهدوء - Quiet Please", t_md, (185, 28, 28)),
        ((230, 300), "تاريخ الإعلان: 2026", t_sm, (71, 85, 105)),
    ]
    for pos, text, font, fill in lines1:
        render_arabic_text(d1, pos, text, font, fill)
    im1.save(f1, quality=98)
    manifest["arabic_printed_notice"] = {
        "fixture": "data/fixtures/arabic_printed_notice.jpg",
        "category": "ocr_printed",
        "reference_text": "جمهورية العراق - وزارة التعليم العالي\nقسم هندسة الحاسوب والذكاء الاصطناعي\nمختبر الرؤية الحاسوبية - ROOM 204\nيرجى الهدوء - Quiet Please\nتاريخ الإعلان: 2026",
    }

    # 2. Pharmacy Notice (Held-out Numbers and Medication Instructions)
    f2 = FIXTURES_DIR / "arabic_heldout_notice.jpg"
    im2 = Image.new("RGB", (650, 320), color=(250, 250, 250))
    d2 = ImageDraw.Draw(im2)
    d2.rectangle([10, 10, 640, 310], outline=(51, 65, 85), width=2)
    lines2 = [
        ((100, 35), "صيدلية بغداد المركزية", get_font(26), (2, 132, 199)),
        ((90, 100), "طريقة الاستخدام: قرص واحد بعد الطعام", get_font(20), (15, 23, 42)),
        ((140, 160), "سعر الدواء: 5000 دينار عراقي", get_font(20), (15, 23, 42)),
        ((160, 220), "رقم الهاتف: 07701234567", get_font(20), (30, 41, 59)),
        ((180, 270), "Baghdad Pharmacy - 2026", get_font(20), (71, 85, 105)),
    ]
    for pos, text, font, fill in lines2:
        render_arabic_text(d2, pos, text, font, fill)
    im2.save(f2, quality=98)
    manifest["arabic_heldout_notice"] = {
        "fixture": "data/fixtures/arabic_heldout_notice.jpg",
        "category": "ocr_heldout_numbers",
        "reference_text": "صيدلية بغداد المركزية\nطريقة الاستخدام: قرص واحد بعد الطعام\nسعر الدواء: 5000 دينار عراقي\nرقم الهاتف: 07701234567\nBaghdad Pharmacy - 2026",
    }

    # 3. Office Desk Scene Objects (Bottle, Laptop, Cup)
    f3 = FIXTURES_DIR / "scene_objects.jpg"
    im3 = Image.new("RGB", (640, 480), color=(220, 225, 230))
    d3 = ImageDraw.Draw(im3)
    d3.rectangle([0, 280, 640, 480], fill=(160, 130, 95))
    # Bottle left
    d3.rectangle([110, 200, 150, 340], fill=(50, 120, 200), outline=(20, 40, 80), width=2)
    d3.rectangle([122, 170, 138, 200], fill=(220, 230, 240), outline=(20, 40, 80), width=2)
    # Laptop center
    d3.rectangle([240, 220, 420, 320], fill=(40, 45, 50), outline=(10, 10, 10), width=2)
    d3.rectangle([250, 230, 410, 310], fill=(100, 180, 255))
    d3.polygon([(220, 350), (440, 350), (420, 320), (240, 320)], fill=(70, 75, 80))
    # Cup right
    d3.rectangle([480, 270, 540, 340], fill=(230, 230, 235), outline=(50, 50, 50), width=2)
    d3.arc([530, 280, 560, 330], 270, 90, fill=(50, 50, 50), width=3)
    im3.save(f3, quality=95)
    manifest["scene_objects"] = {
        "fixture": "data/fixtures/scene_objects.jpg",
        "category": "detection_desk",
        "objects": ["bottle", "laptop", "cup", "dining table"],
    }

    # 4. Low Lighting / Dim Scene
    f4 = FIXTURES_DIR / "dark_unclear.jpg"
    im4 = Image.new("RGB", (640, 480), color=(18, 18, 22))
    d4 = ImageDraw.Draw(im4)
    d4.rectangle([200, 200, 400, 350], fill=(28, 28, 35))
    im4.save(f4, quality=90)
    manifest["dark_unclear"] = {
        "fixture": "data/fixtures/dark_unclear.jpg",
        "category": "quality_underexposed",
        "expected_issue": "underexposed",
    }

    # 5. Living Room Scene (Couch, Coffee table, TV on wall)
    f5 = FIXTURES_DIR / "living_room.jpg"
    im5 = Image.new("RGB", (640, 480), color=(235, 230, 220))
    d5 = ImageDraw.Draw(im5)
    d5.rectangle([0, 320, 640, 480], fill=(180, 150, 120))  # Wooden Floor
    # Couch on left/center
    d5.rectangle([80, 240, 340, 360], fill=(60, 80, 120), outline=(30, 40, 60), width=3)
    d5.rectangle([60, 200, 360, 260], fill=(70, 95, 140), outline=(30, 40, 60), width=2)
    # TV on wall
    d5.rectangle([420, 80, 580, 200], fill=(20, 20, 20), outline=(100, 100, 100), width=3)
    d5.rectangle([430, 90, 570, 190], fill=(40, 60, 90))
    # Chair
    d5.rectangle([460, 260, 560, 360], fill=(140, 70, 60), outline=(80, 30, 30), width=2)
    im5.save(f5, quality=95)
    manifest["living_room"] = {
        "fixture": "data/fixtures/living_room.jpg",
        "category": "detection_indoor",
        "objects": ["couch", "chair", "tv"],
    }

    # 6. Kitchen Table Scene (Bottles, Cups, Bowls)
    f6 = FIXTURES_DIR / "kitchen_scene.jpg"
    im6 = Image.new("RGB", (640, 480), color=(240, 240, 245))
    d6 = ImageDraw.Draw(im6)
    d6.rectangle([0, 250, 640, 480], fill=(210, 190, 170))  # Table
    # Two bottles
    d6.rectangle([100, 160, 140, 320], fill=(30, 140, 70), outline=(10, 50, 20), width=2)
    d6.rectangle([180, 170, 220, 320], fill=(200, 60, 40), outline=(80, 20, 10), width=2)
    # Bowl center
    d6.ellipse([300, 260, 420, 340], fill=(240, 230, 210), outline=(100, 80, 60), width=2)
    # Cup right
    d6.rectangle([480, 220, 540, 310], fill=(240, 240, 250), outline=(60, 60, 70), width=2)
    im6.save(f6, quality=95)
    manifest["kitchen_scene"] = {
        "fixture": "data/fixtures/kitchen_scene.jpg",
        "category": "multi_instance_bottle",
        "objects": ["bottle", "bowl", "cup", "dining table"],
    }

    # 7. Street Crossing / Sidewalk Scene (Pedestrian, Vehicle, Crosswalk)
    f7 = FIXTURES_DIR / "street_crossing.jpg"
    im7 = Image.new("RGB", (640, 480), color=(180, 210, 240))  # Sky
    d7 = ImageDraw.Draw(im7)
    d7.rectangle([0, 200, 640, 480], fill=(70, 75, 80))  # Asphalt Road
    # Sidewalk curb
    d7.rectangle([0, 170, 640, 210], fill=(160, 165, 170), outline=(110, 115, 120), width=2)
    # Crosswalk zebra stripes
    for x in range(80, 560, 60):
        d7.rectangle([x, 260, x + 35, 420], fill=(245, 245, 245))
    # Car on right
    d7.rectangle([420, 180, 580, 260], fill=(190, 40, 30), outline=(80, 10, 10), width=2)
    # Person on left sidewalk
    d7.ellipse([140, 110, 165, 140], fill=(230, 190, 160))
    d7.rectangle([135, 140, 170, 200], fill=(40, 60, 120))
    im7.save(f7, quality=95)
    manifest["street_crossing"] = {
        "fixture": "data/fixtures/street_crossing.jpg",
        "category": "mobility_outdoor",
        "objects": ["person", "car", "crosswalk", "curb"],
    }

    # 8. Indoor Doorway & Stairs Representation (Candidate Classes)
    f8 = FIXTURES_DIR / "indoor_doorway.jpg"
    im8 = Image.new("RGB", (640, 480), color=(230, 225, 220))
    d8 = ImageDraw.Draw(im8)
    # Floor
    d8.rectangle([0, 350, 640, 480], fill=(190, 175, 160))
    # Door on left
    d8.rectangle([80, 100, 220, 380], fill=(120, 80, 50), outline=(50, 30, 15), width=4)
    d8.ellipse([195, 240, 210, 255], fill=(210, 180, 60))  # Doorknob
    # Stairs on right
    for i in range(5):
        y_step = 230 + i * 30
        x_start = 380 + i * 30
        d8.rectangle([x_start, y_step, 620, y_step + 30], fill=(160 - i * 15, 160 - i * 15, 160 - i * 15), outline=(60, 60, 60), width=2)
    im8.save(f8, quality=95)
    manifest["indoor_doorway"] = {
        "fixture": "data/fixtures/indoor_doorway.jpg",
        "category": "candidate_assistive_classes",
        "objects": ["door", "stairs"],
    }

    # 9. Book Page Reading (Multi-line paragraph text)
    f9 = FIXTURES_DIR / "book_reading.jpg"
    im9 = Image.new("RGB", (640, 480), color=(252, 250, 242))
    d9 = ImageDraw.Draw(im9)
    d9.rectangle([20, 20, 620, 460], outline=(200, 195, 185), width=2)
    book_lines = [
        ((80, 50), "الفصل الأول: مدخل إلى الذكاء الاصطناعي", get_font(24), (20, 30, 50)),
        ((60, 110), "تعتبر أنظمة المساعدات البصرية الحديثة خطوة رائدة", get_font(18), (40, 45, 55)),
        ((60, 150), "في تمكين المكفوفين من إدراك بيئتهم المحيطة بدقة.", get_font(18), (40, 45, 55)),
        ((60, 190), "تعتمد التقنية على التعرف اللحظي على الكائنات وقراءة النصوص.", get_font(18), (40, 45, 55)),
        ((60, 230), "المعالجة المحلية الكاملة تضمن أعلى درجات الخصوصية.", get_font(18), (40, 45, 55)),
        ((280, 410), "الصفحة 42", get_font(16), (100, 105, 115)),
    ]
    for pos, text, font, fill in book_lines:
        render_arabic_text(d9, pos, text, font, fill)
    im9.save(f9, quality=98)
    manifest["book_reading"] = {
        "fixture": "data/fixtures/book_reading.jpg",
        "category": "ocr_book_paragraphs",
        "reference_text": "الفصل الأول: مدخل إلى الذكاء الاصطناعي\nتعتبر أنظمة المساعدات البصرية الحديثة خطوة رائدة\nفي تمكين المكفوفين من إدراك بيئتهم المحيطة بدقة.\nتعتمد التقنية على التعرف اللحظي على الكائنات وقراءة النصوص.\nالمعالجة المحلية الكاملة تضمن أعلى درجات الخصوصية.\nالصفحة 42",
    }

    # 10. Glare / Bright Exposure Scene
    f10 = FIXTURES_DIR / "bright_glare.jpg"
    im10 = Image.new("RGB", (640, 480), color=(252, 252, 252))
    d10 = ImageDraw.Draw(im10)
    # Bright sunlight spot washing out details
    d10.ellipse([150, 80, 490, 420], fill=(255, 255, 255))
    im10.save(f10, quality=90)
    manifest["bright_glare"] = {
        "fixture": "data/fixtures/bright_glare.jpg",
        "category": "quality_overexposed",
        "expected_issue": "overexposed",
    }

    gt_file = FIXTURES_DIR / "fixtures_ground_truth.json"
    gt_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Generated all 10 diverse fixtures and updated: {gt_file}")

if __name__ == "__main__":
    generate_all_fixtures()
