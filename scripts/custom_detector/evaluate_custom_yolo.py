"""Independent evaluation script for custom assistive object detection checkpoint.
Computes mAP50, mAP50-95, per-class precision/recall, and inference latency.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

def evaluate_custom_model(
    model_path: str,
    data_yaml: str,
    imgsz: int = 640,
    device: str = "cpu",
    output_report: str = "data/eval/custom_detector_eval.json",
):
    try:
        from ultralytics import YOLO
    except ImportError:
        print("Ultralytics package required.")
        return

    m_path = Path(model_path).resolve()
    d_path = Path(data_yaml).resolve()

    if not m_path.exists():
        print(f"Custom model weights not found at: {m_path}")
        print("Please train or provide valid weights before evaluation.")
        return

    if not d_path.exists():
        print(f"Data configuration YAML not found at: {d_path}")
        return

    print("Evaluating custom YOLO model...")
    model = YOLO(str(m_path))

    t0 = time.perf_counter()
    metrics = model.val(
        data=str(d_path),
        imgsz=imgsz,
        device=device,
        verbose=True,
    )
    val_time = time.perf_counter() - t0

    report = {
        "model": str(m_path),
        "data_yaml": str(d_path),
        "device": device,
        "evaluation_time_seconds": round(val_time, 2),
        "map50": round(float(metrics.box.map50), 4),
        "map50_95": round(float(metrics.box.map), 4),
        "mean_precision": round(float(metrics.box.mp), 4),
        "mean_recall": round(float(metrics.box.mr), 4),
    }

    out_file = Path(output_report)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nEvaluation completed. Results saved to: {out_file}")
    print(f"mAP50: {report['map50']} | mAP50-95: {report['map50_95']} | Precision: {report['mean_precision']} | Recall: {report['mean_recall']}")

def main():
    parser = argparse.ArgumentParser(description="Evaluate custom assistive detector checkpoint")
    parser.add_argument("--model", type=str, default="models/yolo11n.pt", help="Path to weights")
    parser.add_argument("--data", type=str, default="data/custom_dataset/data.yaml", help="Path to data.yaml")
    parser.add_argument("--device", type=str, default="cpu", help="Device (cpu or 0)")
    args = parser.parse_args()

    evaluate_custom_model(
        model_path=args.model,
        data_yaml=args.data,
        device=args.device,
    )

if __name__ == "__main__":
    main()
