"""AMAV Custom Dataset Validator for YOLO Object Detection.
Validates annotation formatting, normalized coordinates, missing files, empty annotations,
and train/validation leakages.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from PIL import Image

def validate_dataset(dataset_dir: Path) -> Dict[str, any]:
    report = {
        "dataset_path": str(dataset_dir),
        "valid": True,
        "splits": {},
        "errors": [],
        "warnings": [],
        "class_counts": {},
    }

    if not dataset_dir.exists():
        report["valid"] = False
        report["errors"].append(f"Dataset root does not exist: {dataset_dir}")
        return report

    for split in ["train", "val", "test"]:
        img_dir = dataset_dir / "images" / split
        lbl_dir = dataset_dir / "labels" / split

        if not img_dir.exists():
            if split != "test":
                report["warnings"].append(f"Split images directory missing: {img_dir}")
            continue

        images = list(img_dir.glob("*.[jJ][pP][gG]")) + list(img_dir.glob("*.[pP][nN][gG]")) + list(img_dir.glob("*.[wW][eE][bB][pP]"))
        labels = list(lbl_dir.glob("*.txt")) if lbl_dir.exists() else []

        split_info = {
            "image_count": len(images),
            "label_count": len(labels),
            "unmatched_images": 0,
            "corrupt_images": 0,
            "invalid_labels": 0,
            "box_count": 0,
        }

        # Check image files and matching labels
        for img_path in images:
            # Check image integrity
            try:
                with Image.open(img_path) as im:
                    w, h = im.size
                    if w < 32 or h < 32:
                        report["warnings"].append(f"Image too small ({w}x{h}): {img_path.name}")
            except Exception as e:
                split_info["corrupt_images"] += 1
                report["errors"].append(f"Corrupt image {img_path.name}: {str(e)}")
                report["valid"] = False

            # Check matching label
            lbl_path = lbl_dir / f"{img_path.stem}.txt"
            if not lbl_path.exists():
                split_info["unmatched_images"] += 1
                report["warnings"].append(f"Missing label file for image: {img_path.name}")
                continue

            # Validate YOLO format: <class> <x_center> <y_center> <width> <height>
            try:
                content = lbl_path.read_text(encoding="utf-8").strip()
                if not content:
                    continue  # background image, allowed in YOLO

                for line in content.splitlines():
                    parts = line.strip().split()
                    if len(parts) != 5:
                        split_info["invalid_labels"] += 1
                        report["errors"].append(f"Invalid YOLO label format (expected 5 tokens, got {len(parts)}): {lbl_path.name}")
                        report["valid"] = False
                        continue

                    cls_id = int(parts[0])
                    coords = [float(p) for p in parts[1:]]

                    # Verify coordinates are strictly normalized in [0.0, 1.0]
                    if any(c < 0.0 or c > 1.0 for c in coords):
                        split_info["invalid_labels"] += 1
                        report["errors"].append(f"Bounding box coordinate out of normalized bounds [0, 1]: {lbl_path.name} -> {coords}")
                        report["valid"] = False

                    split_info["box_count"] += 1
                    report["class_counts"][cls_id] = report["class_counts"].get(cls_id, 0) + 1
            except Exception as e:
                split_info["invalid_labels"] += 1
                report["errors"].append(f"Error reading label {lbl_path.name}: {str(e)}")
                report["valid"] = False

        report["splits"][split] = split_info

    # Leakage check: ensure no identical image stems in train and val
    train_imgs = {p.stem for p in (dataset_dir / "images" / "train").glob("*.*")} if (dataset_dir / "images" / "train").exists() else set()
    val_imgs = {p.stem for p in (dataset_dir / "images" / "val").glob("*.*")} if (dataset_dir / "images" / "val").exists() else set()
    overlap = train_imgs.intersection(val_imgs)
    if overlap:
        report["valid"] = False
        report["errors"].append(f"Data leakage detected! {len(overlap)} images found in both train and val splits: {list(overlap)[:5]}")

    return report

def main():
    parser = argparse.ArgumentParser(description="Validate YOLO format assistive dataset")
    parser.add_argument("--data-dir", type=str, default="data/custom_dataset", help="Path to dataset root directory")
    args = parser.parse_args()

    target_dir = Path(args.data_dir).resolve()
    print(f"Validating dataset at: {target_dir}")
    rep = validate_dataset(target_dir)

    print(f"\n--- Validation Report ---")
    print(f"Status: {'PASSED' if rep['valid'] else 'FAILED'}")
    print(f"Splits summary: {rep['splits']}")
    print(f"Class bounding box counts: {rep['class_counts']}")
    if rep["errors"]:
        print(f"\nErrors ({len(rep['errors'])}):")
        for err in rep["errors"][:10]:
            print(f"  ❌ {err}")
    if rep["warnings"]:
        print(f"\nWarnings ({len(rep['warnings'])}):")
        for w in rep["warnings"][:10]:
            print(f"  ⚠️ {w}")

    sys.exit(0 if rep["valid"] else 1)

if __name__ == "__main__":
    main()
