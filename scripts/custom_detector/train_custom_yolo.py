"""Training pipeline to fine-tune YOLO11n on custom assistive classes
while preventing catastrophic forgetting of base COCO representations.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

def train_custom_model(
    data_yaml: str,
    base_model: str = "models/yolo11n.pt",
    epochs: int = 50,
    batch_size: int = 16,
    imgsz: int = 640,
    device: str = "0",
    freeze_backbone: bool = True,
    output_dir: str = "models/custom_detector_runs",
):
    try:
        from ultralytics import YOLO
    except ImportError:
        print("Ultralytics package is required for YOLO training.")
        sys.exit(1)

    data_path = Path(data_yaml).resolve()
    if not data_path.exists():
        print(f"Data configuration YAML not found at: {data_path}")
        print("Please prepare the dataset and data.yaml first using the protocol in README.md.")
        return False

    base_weights = Path(base_model).resolve()
    if not base_weights.exists():
        print(f"Base YOLO weights not found at: {base_weights}")
        return False

    print("==================================================")
    print(" AMAV Custom YOLO11n Fine-Tuning Pipeline")
    print(f" Base Weights: {base_weights}")
    print(f" Dataset YAML: {data_path}")
    print(f" Epochs: {epochs} | Batch: {batch_size} | Image Size: {imgsz}")
    print(f" Device: {device} | Freeze Backbone: {freeze_backbone}")
    print("==================================================")

    model = YOLO(str(base_weights))

    # Fine-tuning parameters
    # Freeze the first 10 layers (backbone features) to retain base object detection competence
    freeze_layers = 10 if freeze_backbone else None

    results = model.train(
        data=str(data_path),
        epochs=epochs,
        batch=batch_size,
        imgsz=imgsz,
        device=device,
        project=output_dir,
        name="amav_custom_mobility",
        freeze=freeze_layers,
        save=True,
        plots=True,
        verbose=True,
    )

    print("\nTraining completed successfully!")
    print(f"Best checkpoint saved to: {output_dir}/amav_custom_mobility/weights/best.pt")
    return True

def main():
    parser = argparse.ArgumentParser(description="Fine-tune YOLO11n on custom assistive mobility classes")
    parser.add_argument("--data", type=str, default="data/custom_dataset/data.yaml", help="Path to data.yaml")
    parser.add_argument("--base", type=str, default="models/yolo11n.pt", help="Path to pretrained base weights")
    parser.add_argument("--epochs", type=int, default=30, help="Number of training epochs")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument("--imgsz", type=int, default=640, help="Input image dimension")
    parser.add_argument("--device", type=str, default="0", help="CUDA device ID (0) or 'cpu'")
    parser.add_argument("--no-freeze", action="store_true", help="Do not freeze backbone layers")
    args = parser.parse_args()

    train_custom_model(
        data_yaml=args.data,
        base_model=args.base,
        epochs=args.epochs,
        batch_size=args.batch,
        imgsz=args.imgsz,
        device=args.device,
        freeze_backbone=not args.no_freeze,
    )

if __name__ == "__main__":
    main()
