"""Fixture generator for offline and repeatable model testing with accurate Arabic text shaping."""
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

def generate_arabic_text_fixture() -> Path:
    """Creates a high-contrast notice with Arabic and English printed text."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = FIXTURES_DIR / "arabic_printed_notice.jpg"

    img = Image.new("RGB", (700, 360), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Clean double border
    draw.rectangle([10, 10, 690, 350], outline=(30, 41, 59), width=3)
    draw.rectangle([15, 15, 685, 345], outline=(148, 163, 184), width=1)

    font_path = "C:/Windows/Fonts/tahoma.ttf"
    try:
        font_lg = ImageFont.truetype(font_path, 28)
        font_md = ImageFont.truetype(font_path, 22)
        font_sm = ImageFont.truetype(font_path, 18)
    except Exception:
        font_lg = font_md = font_sm = ImageFont.load_default()

    # Lines to render
    lines = [
        ((80, 40), "جمهورية العراق - وزارة التعليم العالي", font_lg, (15, 23, 42)),
        ((120, 105), "قسم هندسة الحاسوب والذكاء الاصطناعي", font_lg, (29, 78, 216)),
        ((160, 175), "مختبر الرؤية الحاسوبية - ROOM 204", font_md, (15, 23, 42)),
        ((200, 240), "يرجى الهدوء - Quiet Please", font_md, (185, 28, 28)),
        ((230, 300), "تاريخ الإعلان: 2026", font_sm, (71, 85, 105)),
    ]

    for pos, text, font, fill in lines:
        render_arabic_text(draw, pos, text, font, fill)

    img.save(out_path, quality=98)
    print(f"Generated text fixture: {out_path}")
    return out_path

def generate_heldout_fixture() -> Path:
    """Creates a second held-out fixture with numbers, mixed script, and instructions."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = FIXTURES_DIR / "arabic_heldout_notice.jpg"

    img = Image.new("RGB", (650, 320), color=(250, 250, 250))
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 640, 310], outline=(51, 65, 85), width=2)

    font_path = "C:/Windows/Fonts/tahoma.ttf"
    try:
        font_lg = ImageFont.truetype(font_path, 26)
        font_md = ImageFont.truetype(font_path, 20)
    except Exception:
        font_lg = font_md = ImageFont.load_default()

    lines = [
        ((100, 35), "صيدلية بغداد المركزية", font_lg, (2, 132, 199)),
        ((90, 100), "طريقة الاستخدام: قرص واحد بعد الطعام", font_md, (15, 23, 42)),
        ((140, 160), "سعر الدواء: 5000 دينار عراقي", font_md, (15, 23, 42)),
        ((160, 220), "رقم الهاتف: 07701234567", font_md, (30, 41, 59)),
        ((180, 270), "Baghdad Pharmacy - 2026", font_md, (71, 85, 105)),
    ]

    for pos, text, font, fill in lines:
        render_arabic_text(draw, pos, text, font, fill)

    img.save(out_path, quality=98)
    print(f"Generated held-out text fixture: {out_path}")
    return out_path

def generate_objects_fixture() -> Path:
    """Creates a fixture image with distinct everyday objects (bottle, cup, laptop representation)."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = FIXTURES_DIR / "scene_objects.jpg"

    img = Image.new("RGB", (640, 480), color=(220, 225, 230))
    draw = ImageDraw.Draw(img)

    # Desk surface
    draw.rectangle([0, 280, 640, 480], fill=(160, 130, 95))

    # Bottle representation on left (x: 100-160, y: 160-340)
    draw.rectangle([110, 200, 150, 340], fill=(50, 120, 200), outline=(20, 40, 80), width=2)
    draw.rectangle([122, 170, 138, 200], fill=(220, 230, 240), outline=(20, 40, 80), width=2)

    # Laptop representation in center (x: 240-420, y: 220-350)
    draw.rectangle([240, 220, 420, 320], fill=(40, 45, 50), outline=(10, 10, 10), width=2)
    draw.rectangle([250, 230, 410, 310], fill=(100, 180, 255))
    draw.polygon([(220, 350), (440, 350), (420, 320), (240, 320)], fill=(70, 75, 80))

    # Cup representation on right (x: 480-550, y: 260-340)
    draw.rectangle([480, 270, 540, 340], fill=(230, 230, 235), outline=(50, 50, 50), width=2)
    draw.arc([530, 280, 560, 330], 270, 90, fill=(50, 50, 50), width=3)

    img.save(out_path, quality=95)
    print(f"Generated objects fixture: {out_path}")
    return out_path

def save_ground_truth_manifest():
    """Saves ground truth texts to JSON manifest for transparent verification."""
    gt = {
        "arabic_printed_notice": {
            "fixture": "data/fixtures/arabic_printed_notice.jpg",
            "reference_text": (
                "جمهورية العراق - وزارة التعليم العالي\n"
                "قسم هندسة الحاسوب والذكاء الاصطناعي\n"
                "مختبر الرؤية الحاسوبية - ROOM 204\n"
                "يرجى الهدوء - Quiet Please\n"
                "تاريخ الإعلان: 2026"
            ),
            "lines": [
                "جمهورية العراق - وزارة التعليم العالي",
                "قسم هندسة الحاسوب والذكاء الاصطناعي",
                "مختبر الرؤية الحاسوبية - ROOM 204",
                "يرجى الهدوء - Quiet Please",
                "تاريخ الإعلان: 2026"
            ]
        },
        "arabic_heldout_notice": {
            "fixture": "data/fixtures/arabic_heldout_notice.jpg",
            "reference_text": (
                "صيدلية بغداد المركزية\n"
                "طريقة الاستخدام: قرص واحد بعد الطعام\n"
                "سعر الدواء: 5000 دينار عراقي\n"
                "رقم الهاتف: 07701234567\n"
                "Baghdad Pharmacy - 2026"
            ),
            "lines": [
                "صيدلية بغداد المركزية",
                "طريقة الاستخدام: قرص واحد بعد الطعام",
                "سعر الدواء: 5000 دينار عراقي",
                "رقم الهاتف: 07701234567",
                "Baghdad Pharmacy - 2026"
            ]
        }
    }
    gt_file = FIXTURES_DIR / "fixtures_ground_truth.json"
    with open(gt_file, "w", encoding="utf-8") as f:
        json.dump(gt, f, indent=2, ensure_ascii=False)
    print(f"Saved ground truth manifest: {gt_file}")

if __name__ == "__main__":
    generate_arabic_text_fixture()
    generate_heldout_fixture()
    generate_objects_fixture()
    save_ground_truth_manifest()
