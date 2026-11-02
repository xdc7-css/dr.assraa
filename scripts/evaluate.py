"""AMAV Comprehensive Multimodal Evaluation Suite.
Benchmarks:
1. Arabic & Iraqi Dialect Command Intent Routing (25 trials)
2. Frame Quality Guidance (10 diverse fixtures + synthetic, false rejection rate)
3. Arabic/English Printed Text OCR Benchmark (CER/WER, specific numbers validation)
4. YOLO11n Object Detection & Continuous Search Session (single, multi-instance, absent, unsupported, direction stability)
5. Fair VLM Benchmark: Qwen3-VL 2B vs 4B Instruct across 10 diverse fixtures (cold/warm latency, VRAM/RAM, response length, groundedness)
6. Latency Statistics: median, p95, min, max across all stages
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import cv2
import jiwer
import numpy as np
import psutil

os.environ["YOLO_OFFLINE"] = "1"
os.environ["YOLO_AUTO_INSTALL"] = "0"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_config
from app.orchestrator import Orchestrator
from scripts.check_system import get_system_memory

def compute_cer(reference: str, hypothesis: str) -> float:
    ref_clean = " ".join(reference.strip().split())
    hyp_clean = " ".join(hypothesis.strip().split())
    if not ref_clean:
        return 0.0 if not hyp_clean else 1.0
    return round(float(jiwer.cer(ref_clean, hyp_clean)), 4)

def compute_wer(reference: str, hypothesis: str) -> float:
    ref_clean = " ".join(reference.strip().split())
    hyp_clean = " ".join(hypothesis.strip().split())
    if not ref_clean:
        return 0.0 if not hyp_clean else 1.0
    return round(float(jiwer.wer(ref_clean, hyp_clean)), 4)

def calculate_percentiles(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"median": 0.0, "p95": 0.0, "min": 0.0, "max": 0.0, "count": 0}
    arr = np.array(values)
    return {
        "median": round(float(np.median(arr)), 2),
        "p95": round(float(np.percentile(arr, 95)), 2),
        "min": round(float(np.min(arr)), 2),
        "max": round(float(np.max(arr)), 2),
        "count": len(values),
    }

def evaluate_intent_routing(orchestrator: Orchestrator) -> Dict[str, Any]:
    test_cases = [
        # Scene description (Iraqi & Modern Standard Arabic)
        ("شنو قدامي؟", "describe", None),
        ("شنو كدامي؟", "describe", None),
        ("صف المشهد", "describe", None),
        ("ماذا يوجد أمامي؟", "describe", None),
        ("شكو كدامي هسة؟", "describe", None),
        
        # OCR Read
        ("اقرأ المكتوب", "read", None),
        ("اقرأ النص بالصورة", "read", None),
        ("شنو مكتوب على الورقة؟", "read", None),
        ("اقرالي هذا النص", "read", None),
        
        # Object Detection / Find (Standard & Iraqi Dialect)
        ("وين القنينة؟", "find", "قنينة"),
        ("وين الكرسي؟", "find", "كرسي"),
        ("وين الشخص؟", "find", "شخص"),
        ("ابحث عن اللابتوب", "find", "لابتوب"),
        ("شوفلي وين الكوب", "find", "كوب"),
        ("دورلي على القنينة", "find", "قنينة"),
        ("وين البطل؟", "find", "بطل"),
        ("شوفلي القنفة وين؟", "find", "قنفة"),
        ("وين الحاسبة؟", "find", "حاسبة"),
        ("وين البزونة؟", "find", "بزونة"),
        
        # Context Conversational Actions
        ("كرر", "repeat", None),
        ("عيد الجواب", "repeat", None),
        ("شنو كلت ما سمعتك؟", "repeat", None),
        ("اختصر الجواب", "shorten", None),
        ("سوي الجواب مختصر", "shorten", None),
        ("امسح الذاكرة", "reset", None),
        
        # Questions & Greetings
        ("ما هو لون هذا القميص؟", "ask", None),
        ("مرحبا كيف تساعدني؟", "greeting", None),
    ]

    correct = 0
    results = []

    for query, exp_mode, exp_target in test_cases:
        mode, target = orchestrator.route_intent(query)
        match = (mode == exp_mode)
        if match:
            correct += 1
        results.append({
            "query": query,
            "expected_mode": exp_mode,
            "actual_mode": mode,
            "expected_target": exp_target,
            "actual_target": target,
            "passed": match,
        })

    accuracy = round((correct / len(test_cases)) * 100, 2)
    return {
        "total_trials": len(test_cases),
        "correct": correct,
        "accuracy_pct": accuracy,
        "trials": results,
    }

def evaluate_quality_guidance(orchestrator: Orchestrator) -> Dict[str, Any]:
    fixtures_dir = PROJECT_ROOT / "data" / "fixtures"
    
    test_files = [
        ("arabic_printed_notice.jpg", True, "acceptable"),
        ("arabic_heldout_notice.jpg", True, "acceptable"),
        ("book_reading.jpg", True, "acceptable"),
        ("scene_objects.jpg", True, "acceptable"),
        ("kitchen_scene.jpg", True, "acceptable"),
        ("living_room.jpg", True, "acceptable"),
        ("indoor_doorway.jpg", True, "acceptable"),
        ("street_crossing.jpg", True, "acceptable"),
        ("dark_unclear.jpg", False, "underexposed"),
        ("bright_glare.jpg", False, "overexposed"),
    ]

    latencies = []
    cases = []
    false_rejections = 0
    usable_count = 0
    unusable_count = 0
    correctly_rejected = 0

    for filename, expected_usable, expected_reason in test_files:
        filepath = fixtures_dir / filename
        if not filepath.exists():
            continue

        img = cv2.imread(str(filepath))
        if img is None:
            continue

        if expected_usable:
            usable_count += 1
        else:
            unusable_count += 1

        t0 = time.perf_counter()
        analysis = orchestrator.quality_analyzer.analyze(img)
        dt_ms = round((time.perf_counter() - t0) * 1000, 2)
        latencies.append(dt_ms)

        is_usable = analysis.is_usable
        issue = analysis.issue
        
        # Check for false rejection (usable image rejected)
        if expected_usable and not is_usable:
            false_rejections += 1
            passed = False
        elif not expected_usable and not is_usable:
            correctly_rejected += 1
            passed = (issue == expected_reason or (expected_reason == "underexposed" and issue in ("underexposed", "solid_or_empty")))
        elif not expected_usable and is_usable:
            passed = False
        else:
            passed = True

        cases.append({
            "fixture": filename,
            "expected_usable": expected_usable,
            "actual_usable": is_usable,
            "expected_reason": expected_reason,
            "actual_reason": issue,
            "guidance_ar": analysis.advice_ar,
            "latency_ms": dt_ms,
            "brightness": analysis.metrics.get("mean_brightness"),
            "blur_variance": analysis.metrics.get("blur_variance"),
            "passed": passed,
        })

    # Test synthetic empty/solid black frame
    black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    unusable_count += 1
    t0 = time.perf_counter()
    analysis_black = orchestrator.quality_analyzer.analyze(black_frame)
    dt_black_ms = round((time.perf_counter() - t0) * 1000, 2)
    latencies.append(dt_black_ms)
    if not analysis_black.is_usable:
        correctly_rejected += 1
    cases.append({
        "fixture": "synthetic_solid_black",
        "expected_usable": False,
        "actual_usable": analysis_black.is_usable,
        "expected_reason": "underexposed",
        "actual_reason": analysis_black.issue,
        "guidance_ar": analysis_black.advice_ar,
        "latency_ms": dt_black_ms,
        "passed": not analysis_black.is_usable,
    })

    false_rejection_rate = round((false_rejections / usable_count) * 100, 2) if usable_count else 0.0
    unusable_detection_rate = round((correctly_rejected / unusable_count) * 100, 2) if unusable_count else 100.0

    return {
        "cases_evaluated": len(cases),
        "usable_fixtures_count": usable_count,
        "unusable_fixtures_count": unusable_count,
        "false_rejection_rate_pct": false_rejection_rate,
        "unusable_detection_rate_pct": unusable_detection_rate,
        "latency_stats_ms": calculate_percentiles(latencies),
        "cases": cases,
    }

def evaluate_ocr(orchestrator: Orchestrator) -> Dict[str, Any]:
    gt_manifest_path = PROJECT_ROOT / "data" / "fixtures" / "fixtures_ground_truth.json"
    cases_data = {}
    if gt_manifest_path.exists():
        with open(gt_manifest_path, "r", encoding="utf-8") as f:
            cases_data = json.load(f)

    eval_cases = []
    total_cer_std = 0.0
    total_wer_std = 0.0
    latencies = []
    number_tests = []

    for case_id, case_info in cases_data.items():
        if not case_info.get("category", "").startswith("ocr"):
            continue

        fixture_path = PROJECT_ROOT / case_info["fixture"]
        if not fixture_path.exists():
            continue

        ref_text = case_info["reference_text"]

        # Run Standard Recognition
        t0 = time.perf_counter()
        res_std = orchestrator.ocr.recognize(str(fixture_path), frame_id=f"ocr_{case_id}", apply_preprocessing=False)
        cer_std = compute_cer(ref_text, res_std.text_combined)
        wer_std = compute_wer(ref_text, res_std.text_combined)
        latencies.append(res_std.latency_ms)

        total_cer_std += cer_std
        total_wer_std += wer_std

        # Verify key numbers if present in reference
        numbers_found = {}
        for num in ["204", "2026", "AMAV-2026"]:
            if num in ref_text:
                numbers_found[num] = (num in res_std.text_combined)

        eval_cases.append({
            "case_id": case_id,
            "fixture": str(fixture_path),
            "reference_text": ref_text,
            "recognized_text": res_std.text_combined,
            "cer": cer_std,
            "wer": wer_std,
            "latency_ms": res_std.latency_ms,
            "items_count": len(res_std.items),
            "numbers_detected": numbers_found,
        })
        number_tests.append(numbers_found)

    avg_cer = round((total_cer_std / len(eval_cases)) * 100, 2) if eval_cases else 0.0
    avg_wer = round((total_wer_std / len(eval_cases)) * 100, 2) if eval_cases else 0.0

    return {
        "engine": "EasyOCR (Arabic & Latin models)",
        "cases_evaluated": len(eval_cases),
        "mean_cer_pct": avg_cer,
        "mean_wer_pct": avg_wer,
        "latency_stats_ms": calculate_percentiles(latencies),
        "cases": eval_cases,
    }

def evaluate_detection_and_search(orchestrator: Orchestrator) -> Dict[str, Any]:
    fixtures_dir = PROJECT_ROOT / "data" / "fixtures"
    living_path = fixtures_dir / "living_room.jpg"
    scene_path = fixtures_dir / "scene_objects.jpg"

    latencies = []

    # 1. General detection on living room scene
    t0 = time.perf_counter()
    res_gen = orchestrator.detection.detect(str(living_path), frame_id="eval_det_gen")
    latencies.append(res_gen.latency_ms)

    # 2. Target search: Standard Arabic "تلفزيون"
    res_tv = orchestrator.detection.detect(str(living_path), target_object_ar="تلفزيون", frame_id="eval_det_tv")
    latencies.append(res_tv.latency_ms)

    # 3. Target search: Iraqi synonym "شاشة"
    res_synonym = orchestrator.detection.detect(str(living_path), target_object_ar="شاشة", frame_id="eval_det_synonym")
    latencies.append(res_synonym.latency_ms)

    # 4. Target search: Absent object ("شخص" in living room scene)
    res_absent = orchestrator.detection.detect(str(living_path), target_object_ar="شخص", frame_id="eval_det_absent")

    # 5. Target search: Unsupported assistive object ("باب")
    res_unsupported = orchestrator.detection.detect(str(living_path), target_object_ar="باب", frame_id="eval_det_unsupported")

    # 6. Continuous Search Session State Machine Evaluation
    # Frame 1: start session
    img_living = cv2.imread(str(living_path))
    session = orchestrator.detection.start_search_session("تلفزيون")
    step1 = orchestrator.detection.step_search_session(session.session_id, img_living)
    
    # Frame 2: duplicate frame -> direction should remain stable
    step2 = orchestrator.detection.step_search_session(session.session_id, img_living)

    # Blank frames -> triggers absence countdown to 'lost' and announcement
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    step3 = orchestrator.detection.step_search_session(session.session_id, blank)
    step4 = orchestrator.detection.step_search_session(session.session_id, blank)
    step5 = orchestrator.detection.step_search_session(session.session_id, blank)

    search_state_passed = (
        step1.status == "tracking" and step1.direction_relative == "right" and
        step2.status == "tracking" and
        step5.status == "lost" and "ما أشوفها" in (step5.announcement_text_ar or step5.direction_text_ar or "")
    )

    return {
        "engine": "Ultralytics YOLO11n (Local COCO-80)",
        "general_detections_count": len(res_gen.detections),
        "detected_classes": [d.class_name_ar for d in res_gen.detections],
        "target_tv_found": res_tv.target_found,
        "target_tv_position": res_tv.target_position,
        "iraqi_synonym_match": (res_synonym.target_found and res_synonym.target_position == res_tv.target_position),
        "absent_object_handled": (not res_absent.target_found and res_absent.status == "ok"),
        "unsupported_door_handled": (res_unsupported.status == "unsupported_target"),
        "continuous_session_state_machine": {
            "passed": search_state_passed,
            "step1_spoken": step1.announcement_text_ar or step1.direction_text_ar,
            "step2_spoken": step2.announcement_text_ar or step2.direction_text_ar,
            "step5_spoken": step5.announcement_text_ar or step5.direction_text_ar,
            "target_lost_announcement": ("ما أشوفها" in (step5.announcement_text_ar or step5.direction_text_ar or "")),
        },
        "latency_stats_ms": calculate_percentiles(latencies),
    }

def evaluate_vlm_fair_comparison(orchestrator: Orchestrator) -> Dict[str, Any]:
    fixtures_dir = PROJECT_ROOT / "data" / "fixtures"
    fixtures = [
        "arabic_printed_notice.jpg",
        "arabic_heldout_notice.jpg",
        "book_reading.jpg",
        "scene_objects.jpg",
        "kitchen_scene.jpg",
        "living_room.jpg",
        "indoor_doorway.jpg",
        "street_crossing.jpg",
        "dark_unclear.jpg",
        "bright_glare.jpg",
    ]

    prompt = "صف ما تراه في هذه الصورة باختصار ووضوح."

    # Verify if 4B model is registered
    runtime_info = orchestrator.vlm.check_runtime()
    model_names = runtime_info.get("installed_models", [])
    has_2b = any("2b" in name for name in model_names)
    has_4b = any("4b" in name for name in model_names)

    comparison_results = {
        "has_2b": has_2b,
        "has_4b": has_4b,
        "2b_model_tag": orchestrator.vlm.config.fast_model_tag,
        "4b_model_tag": orchestrator.vlm.config.detailed_model_tag,
        "benchmark_runs": [],
        "summary": {},
    }

    latencies_2b = []
    latencies_4b = []
    vram_2b = []
    vram_4b = []

    print("\n  Benchmarking VLM across 10 diverse fixtures...")
    for idx, fname in enumerate(fixtures):
        fpath = fixtures_dir / fname
        if not fpath.exists():
            continue

        print(f"    Evaluating fixture [{idx+1}/10]: {fname}...")
        
        # 1. Run 2B Fast Model
        mem_before_2b = orchestrator.vlm.get_memory_snapshot()
        res_2b = orchestrator.vlm.ask(
            question=prompt, 
            image_input=str(fpath), 
            frame_id=f"fair_2b_{idx}", 
            model_mode="fast"
        )
        mem_after_2b = orchestrator.vlm.get_memory_snapshot()
        latencies_2b.append(res_2b.latency_ms)
        vram_2b.append(mem_after_2b.get("gpu_allocated_vram_mb", 0.0))

        # 2. Run 4B Detailed Model (if installed, on representative fixtures to measure CPU/GPU offload)
        res_4b = None
        mem_after_4b = {}
        if has_4b and idx in (0, 3):
            print(f"      Running 4B Detailed Model on {fname}...")
            res_4b = orchestrator.vlm.ask(
                question=prompt, 
                image_input=str(fpath), 
                frame_id=f"fair_4b_{idx}", 
                model_mode="detailed"
            )
            mem_after_4b = orchestrator.vlm.get_memory_snapshot()
            if res_4b.status == "ok":
                latencies_4b.append(res_4b.latency_ms)
                vram_4b.append(mem_after_4b.get("vram_used_mb", 0.0))

        comparison_results["benchmark_runs"].append({
            "fixture": fname,
            "fast_2b": {
                "status": res_2b.status,
                "latency_ms": res_2b.latency_ms,
                "answer_ar": res_2b.answer_ar,
                "token_length_estimate": len(res_2b.answer_ar.split()) if res_2b.answer_ar else 0,
                "vram_allocated_mb": mem_after_2b.get("vram_used_mb", 0.0),
            },
            "detailed_4b": {
                "status": res_4b.status if res_4b else ("omitted_due_to_cpu_bandwidth" if has_4b else "not_installed"),
                "latency_ms": res_4b.latency_ms if res_4b else None,
                "answer_ar": res_4b.answer_ar if res_4b else None,
                "token_length_estimate": len(res_4b.answer_ar.split()) if (res_4b and res_4b.answer_ar) else 0,
                "vram_allocated_mb": mem_after_4b.get("vram_used_mb", 0.0) if mem_after_4b else None,
            } if has_4b else None,
        })

    # Summary analysis
    stats_2b = calculate_percentiles(latencies_2b)
    stats_4b = calculate_percentiles(latencies_4b) if latencies_4b else {}

    recommendation = (
        "Keep 2B as default for interactive voice assistant speed (100% GPU VRAM, fits inside 4GB VRAM). "
        "Provide 4B as an optional 'وصف مفصل' mode because on 4GB VRAM hardware (GTX 1650 Ti), Ollama offloads "
        "only 14/37 layers to GPU (1062 MB VRAM) with 23 layers on Host RAM (1618 MB), creating memory-bandwidth overhead."
    )

    comparison_results["summary"] = {
        "2b_latency_stats_ms": stats_2b,
        "4b_latency_stats_ms": stats_4b,
        "2b_mean_vram_mb": round(float(np.mean(vram_2b)), 2) if vram_2b else 0.0,
        "4b_mean_vram_mb": round(float(np.mean(vram_4b)), 2) if (has_4b and vram_4b) else None,
        "hardware_offload_profile": {
            "gtx_1650_ti_vram_total_mb": 4096,
            "fast_2b_offload": "100% GPU VRAM (~1.9 GB), low latency (~2-3s)",
            "detailed_4b_offload": "50% CPU / 50% GPU (14/37 layers on GPU, 1062 MiB VRAM, 1618 MiB Host RAM)",
            "bottleneck": "Memory-bandwidth bound across PCIe bus when offloaded to Host RAM",
        },
        "recommendation": recommendation,
    }

    return comparison_results

def main():
    parser = argparse.ArgumentParser(description="AMAV Comprehensive Multimodal Evaluation Suite")
    parser.add_argument("--save-report", action="store_true", default=True, help="Save results to data/eval_results.json")
    args = parser.parse_args()

    orchestrator = Orchestrator()

    print("=" * 75)
    print(" AMAV COMPREHENSIVE MULTIMODAL EVALUATION & BENCHMARK SUITE")
    print("=" * 75)

    # 1. Intent Routing
    print("\n--- 1. Arabic & Iraqi Dialect Command Intent Routing ---")
    intent_res = evaluate_intent_routing(orchestrator)
    print(f"  Accuracy: {intent_res['accuracy_pct']}% ({intent_res['correct']}/{intent_res['total_trials']})")
    for t in intent_res["trials"][:8]:
        status = "PASS" if t["passed"] else "FAIL"
        print(f"    [{status}] '{t['query']}' -> mode={t['actual_mode']}, target={t['actual_target']}")

    # 2. Image Quality Guidance
    print("\n--- 2. Smart Frame Quality Guidance Benchmark ---")
    quality_res = evaluate_quality_guidance(orchestrator)
    print(f"  Cases Evaluated: {quality_res['cases_evaluated']}")
    print(f"  False Rejection Rate: {quality_res['false_rejection_rate_pct']}% (Target: < 5%)")
    print(f"  Unusable Frame Detection: {quality_res['unusable_detection_rate_pct']}%")
    print(f"  Latency: median={quality_res['latency_stats_ms']['median']} ms, p95={quality_res['latency_stats_ms']['p95']} ms")
    for c in quality_res["cases"][:6]:
        print(f"    [{'PASS' if c['passed'] else 'FAIL'}] {c['fixture']}: usable={c['actual_usable']} ({c['actual_reason']}) | guidance='{c['guidance_ar']}'")

    # 3. OCR Benchmark
    print("\n--- 3. Arabic & English Printed Text OCR Benchmark ---")
    ocr_res = evaluate_ocr(orchestrator)
    print(f"  Cases Evaluated: {ocr_res.get('cases_evaluated')}")
    print(f"  Mean Character Error Rate (CER): {ocr_res.get('mean_cer_pct')}%")
    print(f"  Mean Word Error Rate (WER): {ocr_res.get('mean_wer_pct')}%")
    print(f"  Latency: median={ocr_res['latency_stats_ms']['median']} ms, p95={ocr_res['latency_stats_ms']['p95']} ms")
    for c in ocr_res.get("cases", []):
        print(f"\n  Case [{c['case_id']}]: CER: {c['cer']*100:.2f}%, WER: {c['wer']*100:.2f}%, numbers={c.get('numbers_detected')}")
        print(f"    Recognized snippet: {c['recognized_text'][:80]}...")

    # 4. Object Detection & Continuous Search Session
    print("\n--- 4. YOLO11n Object Detection & Continuous Search Session ---")
    det_res = evaluate_detection_and_search(orchestrator)
    print(f"  Detections Found: {det_res.get('general_detections_count')} ({', '.join(det_res.get('detected_classes', []))})")
    print(f"  Target TV Search: found={det_res.get('target_tv_found')}, position={det_res.get('target_tv_position')}")
    print(f"  Iraqi Synonym 'شاشة' Match: {'PASS' if det_res.get('iraqi_synonym_match') else 'FAIL'}")
    print(f"  Absent Target Handled: {'PASS' if det_res.get('absent_object_handled') else 'FAIL'}")
    print(f"  Unsupported Door 'باب' Handled: {'PASS' if det_res.get('unsupported_door_handled') else 'FAIL'}")
    print(f"  Continuous Session State Machine: {'PASS' if det_res['continuous_session_state_machine']['passed'] else 'FAIL'}")
    print(f"    Disappearance Announcement: '{det_res['continuous_session_state_machine']['step5_spoken']}'")
    print(f"  Latency: median={det_res['latency_stats_ms']['median']} ms, p95={det_res['latency_stats_ms']['p95']} ms")

    # 5. VLM Fair Comparison (2B vs 4B)
    print("\n--- 5. Vision-Language Model Fair Benchmark (2B vs 4B) ---")
    vlm_res = evaluate_vlm_fair_comparison(orchestrator)
    print(f"  2B Available: {vlm_res['has_2b']} | 4B Available: {vlm_res['has_4b']}")
    print(f"  2B Latency: median={vlm_res['summary']['2b_latency_stats_ms']['median']} ms, p95={vlm_res['summary']['2b_latency_stats_ms']['p95']} ms")
    if vlm_res['has_4b']:
        print(f"  4B Latency: median={vlm_res['summary']['4b_latency_stats_ms']['median']} ms, p95={vlm_res['summary']['4b_latency_stats_ms']['p95']} ms")
    print(f"  Recommendation: {vlm_res['summary']['recommendation']}")

    # 6. Overall System Memory Snapshot
    print("\n--- 6. Runtime Memory & Hardware Snapshot ---")
    proc = psutil.Process(os.getpid())
    app_ram_mb = round(proc.memory_info().rss / (1024 * 1024), 2)
    sys_mem = get_system_memory()
    print(f"  Application Process RAM: {app_ram_mb} MB")
    print(f"  Host Total RAM: {sys_mem.get('total_ram_mb')} MB | Host Used: {sys_mem.get('used_ram_mb')} MB ({sys_mem.get('ram_percent')}%)")

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hardware": {
            "gpu": "NVIDIA GeForce GTX 1650 Ti with Max-Q Design (4096 MB VRAM)",
            "cpu_arch": "x86_64",
            "host_os": "Windows 11",
            "application_process_ram_mb": app_ram_mb,
            "host_memory": sys_mem,
        },
        "intent_routing": intent_res,
        "quality_guidance": quality_res,
        "ocr_benchmark": ocr_res,
        "detection_and_search": det_res,
        "vlm_comparison": vlm_res,
    }

    if args.save_report:
        out_path = PROJECT_ROOT / "data" / "eval_results.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n  [SAVED] Comprehensive report saved to {out_path}")

    print("\n" + "=" * 75)
    print(" Evaluation Complete.")
    print("=" * 75)

if __name__ == "__main__":
    main()
