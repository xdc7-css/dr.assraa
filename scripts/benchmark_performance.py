"""AMAV Empirical Performance Benchmark & Resource Profiler.
Measures latency, CPU%, GPU%, VRAM, and RAM across isolated tasks.
Outputs structured JSON and formatted markdown tables.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import platform
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import psutil

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# NVML initialization
HAS_NVML = False
try:
    import pynvml
    pynvml.nvmlInit()
    nvml_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
    HAS_NVML = True
except Exception:
    HAS_NVML = False
    nvml_handle = None

class ResourceSampler:
    """High-frequency background sampler for process and system resource utilization."""
    def __init__(self, interval_s: float = 0.05):
        self.interval_s = interval_s
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.proc = psutil.Process()
        self.num_cpus = psutil.cpu_count(logical=True) or 1

        self.proc_cpu_samples: List[float] = []
        self.sys_cpu_samples: List[float] = []
        self.gpu_util_samples: List[float] = []
        self.vram_used_samples: List[float] = []
        self.proc_ram_samples: List[float] = []
        self.sys_ram_samples: List[float] = []
        self.baseline_vram_mb: float = 0.0

    def _sample_loop(self):
        # Prime process cpu_percent
        try:
            self.proc.cpu_percent()
        except Exception:
            pass

        while not self.stop_event.is_set():
            try:
                # Process CPU normalized to 100% of machine capacity
                p_cpu = self.proc.cpu_percent() / self.num_cpus
                s_cpu = psutil.cpu_percent()
                p_mem = self.proc.memory_info().rss / (1024 * 1024)
                s_mem = psutil.virtual_memory().used / (1024 * 1024)

                g_util = 0.0
                v_used = 0.0
                if HAS_NVML and nvml_handle:
                    try:
                        g_rates = pynvml.nvmlDeviceGetUtilizationRates(nvml_handle)
                        g_util = float(g_rates.gpu)
                        m_info = pynvml.nvmlDeviceGetMemoryInfo(nvml_handle)
                        v_used = float(m_info.used) / (1024 * 1024)
                    except Exception:
                        pass

                self.proc_cpu_samples.append(p_cpu)
                self.sys_cpu_samples.append(s_cpu)
                self.proc_ram_samples.append(p_mem)
                self.sys_ram_samples.append(s_mem)
                self.gpu_util_samples.append(g_util)
                self.vram_used_samples.append(v_used)
            except Exception:
                pass

            time.sleep(self.interval_s)

    def start(self):
        self.proc_cpu_samples.clear()
        self.sys_cpu_samples.clear()
        self.gpu_util_samples.clear()
        self.vram_used_samples.clear()
        self.proc_ram_samples.clear()
        self.sys_ram_samples.clear()

        # Capture baseline VRAM
        if HAS_NVML and nvml_handle:
            try:
                m_info = pynvml.nvmlDeviceGetMemoryInfo(nvml_handle)
                self.baseline_vram_mb = float(m_info.used) / (1024 * 1024)
            except Exception:
                self.baseline_vram_mb = 0.0

        self.stop_event.clear()
        self.thread = threading.Thread(target=self._sample_loop, daemon=True)
        self.thread.start()

    def stop(self) -> Dict[str, Any]:
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=1.0)

        # Aggregate statistics
        def safe_mean(lst): return round(float(np.mean(lst)), 2) if lst else 0.0
        def safe_max(lst): return round(float(np.max(lst)), 2) if lst else 0.0

        peak_vram = safe_max(self.vram_used_samples)
        delta_vram = round(max(0.0, peak_vram - self.baseline_vram_mb), 2)

        return {
            "samples_count": len(self.proc_cpu_samples),
            "proc_cpu_avg_pct": safe_mean(self.proc_cpu_samples),
            "proc_cpu_peak_pct": safe_max(self.proc_cpu_samples),
            "sys_cpu_avg_pct": safe_mean(self.sys_cpu_samples),
            "sys_cpu_peak_pct": safe_max(self.sys_cpu_samples),
            "gpu_util_avg_pct": safe_mean(self.gpu_util_samples),
            "gpu_util_peak_pct": safe_max(self.gpu_util_samples),
            "vram_peak_mb": peak_vram,
            "vram_delta_mb": delta_vram,
            "proc_ram_peak_mb": safe_max(self.proc_ram_samples),
            "sys_ram_peak_mb": safe_max(self.sys_ram_samples),
        }

def get_system_environment() -> Dict[str, Any]:
    """Capture detailed hardware, OS, and framework versions."""
    mem = psutil.virtual_memory()
    disk_x = psutil.disk_usage("X:\\") if os.path.exists("X:\\") else None
    disk_c = psutil.disk_usage("C:\\") if os.path.exists("C:\\") else None

    # GPU info
    gpu_info = {"available": False}
    if HAS_NVML and nvml_handle:
        try:
            name = pynvml.nvmlDeviceGetName(nvml_handle)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(nvml_handle)
            driver = pynvml.nvmlSystemGetDriverVersion()
            cuda_v = pynvml.nvmlSystemGetCudaDriverVersion()
            gpu_info = {
                "available": True,
                "name": name,
                "driver_version": driver,
                "cuda_driver_version": f"{cuda_v // 1000}.{(cuda_v % 1000) // 10}",
                "vram_total_mb": round(mem_info.total / (1024 * 1024), 2),
                "vram_free_mb": round(mem_info.free / (1024 * 1024), 2),
            }
        except Exception as e:
            gpu_info["error"] = str(e)

    # Package versions
    packages = {}
    for pkg in ["torch", "torchvision", "ctranslate2", "onnxruntime", "easyocr", "ultralytics", "faster_whisper"]:
        try:
            mod = __import__(pkg)
            packages[pkg] = getattr(mod, "__version__", "installed")
        except Exception as e:
            packages[pkg] = f"not available ({e})"

    # Torch CUDA details
    torch_cuda = {"available": False}
    try:
        import torch
        torch_cuda["available"] = torch.cuda.is_available()
        torch_cuda["version"] = torch.__version__
        torch_cuda["cuda_build"] = torch.version.cuda
        if torch.cuda.is_available():
            torch_cuda["device_name"] = torch.cuda.get_device_name(0)
    except Exception as e:
        torch_cuda["error"] = str(e)

    # Ollama status
    ollama_stat = {}
    local_ollama = PROJECT_ROOT / "tools" / "Ollama" / "ollama.exe"
    ollama_bin = str(local_ollama) if local_ollama.exists() else "ollama"
    try:
        res = subprocess.run([ollama_bin, "--version"], capture_output=True, text=True, timeout=5)
        ollama_stat["version"] = res.stdout.strip() or res.stderr.strip()
    except Exception as e:
        ollama_stat["error"] = str(e)

    return {
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "cpu": {
            "processor": platform.processor(),
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_threads": psutil.cpu_count(logical=True),
        },
        "system_ram": {
            "total_mb": round(mem.total / (1024 * 1024), 2),
            "available_mb": round(mem.available / (1024 * 1024), 2),
            "used_mb": round(mem.used / (1024 * 1024), 2),
        },
        "gpu": gpu_info,
        "torch_cuda": torch_cuda,
        "packages": packages,
        "ollama": ollama_stat,
        "disk": {
            "x_free_gb": round(disk_x.free / (1024**3), 2) if disk_x else 0,
            "c_free_gb": round(disk_c.free / (1024**3), 2) if disk_c else 0,
        },
        "python": {
            "executable": sys.executable,
            "version": sys.version,
        }
    }

def run_isolated_task(
    task_name: str,
    func,
    args: tuple,
    kwargs: dict,
    warm_iterations: int = 3,
    sampler: Optional[ResourceSampler] = None,
) -> Dict[str, Any]:
    """Executes 1 cold run followed by warm_iterations, recording profiling metrics."""
    print(f"\n[{task_name}] Running Cold Run (first load)...")
    sampler.start()
    t0 = time.perf_counter()
    cold_result = func(*args, **kwargs)
    cold_latency_s = time.perf_counter() - t0
    cold_metrics = sampler.stop()

    warm_latencies = []
    warm_metrics_list = []

    print(f"[{task_name}] Running {warm_iterations} Warm Iterations...")
    for i in range(warm_iterations):
        time.sleep(0.3)
        sampler.start()
        t0 = time.perf_counter()
        warm_result = func(*args, **kwargs)
        dur_s = time.perf_counter() - t0
        m = sampler.stop()
        warm_latencies.append(dur_s)
        warm_metrics_list.append(m)

    # Compute warm aggregates
    avg_warm_lat = round(float(np.mean(warm_latencies)), 4) if warm_latencies else 0.0
    p95_warm_lat = round(float(np.percentile(warm_latencies, 95)), 4) if warm_latencies else 0.0
    min_warm_lat = round(float(np.min(warm_latencies)), 4) if warm_latencies else 0.0
    max_warm_lat = round(float(np.max(warm_latencies)), 4) if warm_latencies else 0.0

    avg_proc_cpu = round(float(np.mean([m["proc_cpu_avg_pct"] for m in warm_metrics_list])), 2) if warm_metrics_list else 0.0
    peak_proc_cpu = round(float(np.max([m["proc_cpu_peak_pct"] for m in warm_metrics_list])), 2) if warm_metrics_list else 0.0
    peak_sys_cpu = round(float(np.max([m["sys_cpu_peak_pct"] for m in warm_metrics_list])), 2) if warm_metrics_list else 0.0
    peak_gpu_util = round(float(np.max([m["gpu_util_peak_pct"] for m in warm_metrics_list])), 2) if warm_metrics_list else 0.0
    peak_vram = round(float(np.max([m["vram_peak_mb"] for m in warm_metrics_list])), 2) if warm_metrics_list else 0.0

    return {
        "task_name": task_name,
        "cold_latency_s": round(cold_latency_s, 4),
        "cold_metrics": cold_metrics,
        "warm_iterations": warm_iterations,
        "warm_latencies_s": [round(x, 4) for x in warm_latencies],
        "warm_avg_latency_s": avg_warm_lat,
        "warm_p95_latency_s": p95_warm_lat,
        "warm_min_latency_s": min_warm_lat,
        "warm_max_latency_s": max_warm_lat,
        "warm_proc_cpu_avg_pct": avg_proc_cpu,
        "warm_proc_cpu_peak_pct": peak_proc_cpu,
        "warm_sys_cpu_peak_pct": peak_sys_cpu,
        "warm_gpu_util_peak_pct": peak_gpu_util,
        "warm_vram_peak_mb": peak_vram,
        "cold_result_preview": str(cold_result)[:200],
    }

def main():
    parser = argparse.ArgumentParser(description="AMAV Performance Benchmark")
    parser.add_argument("--output", type=str, default="data/baseline_performance.json", help="Path to output JSON")
    parser.add_argument("--skip-4b", action="store_true", help="Skip VLM 4B benchmark")
    args = parser.parse_args()

    print("=" * 70)
    print("AMAV MULTIMODAL PERFORMANCE BENCHMARK & SYSTEM PROFILER")
    print("=" * 70)

    env = get_system_environment()
    print(f"OS: {env['os']}")
    print(f"CPU: {env['cpu']['processor']} ({env['cpu']['physical_cores']}C / {env['cpu']['logical_threads']}T)")
    print(f"RAM: {env['system_ram']['used_mb']} MB / {env['system_ram']['total_mb']} MB (Avail: {env['system_ram']['available_mb']} MB)")
    if env['gpu']['available']:
        print(f"GPU: {env['gpu']['name']} | VRAM: {env['gpu']['vram_free_mb']} / {env['gpu']['vram_total_mb']} MB | Driver: {env['gpu']['driver_version']}")
    else:
        print("GPU: None detected via NVML")
    print(f"Torch CUDA Available: {env['torch_cuda']['available']} (PyTorch: {env['torch_cuda'].get('version')})")
    print("=" * 70)

    sampler = ResourceSampler(interval_s=0.04)

    # 1. OCR Benchmark
    from app.config import get_config
    cfg = get_config()
    from app.adapters.ocr_adapter import OCRAdapter
    ocr_adapter = OCRAdapter(cfg.ocr)
    ocr_fixture = PROJECT_ROOT / "data" / "fixtures" / "arabic_printed_notice.jpg"
    
    ocr_bench = run_isolated_task(
        task_name="EasyOCR Arabic Printed Notice",
        func=ocr_adapter.recognize,
        args=(str(ocr_fixture),),
        kwargs={"apply_preprocessing": True},
        warm_iterations=3,
        sampler=sampler,
    )

    # 2. VLM 2B Benchmark
    from app.adapters.vlm_adapter import VLMAdapter
    vlm_adapter = VLMAdapter(cfg.vlm)
    scene_fixture = PROJECT_ROOT / "data" / "fixtures" / "scene_objects.jpg"

    vlm_2b_bench = run_isolated_task(
        task_name="VLM 2B (Qwen3-VL-2B Instruct)",
        func=vlm_adapter.ask,
        args=("صف المشهد باختصار للمستخدم الكفيف", str(scene_fixture)),
        kwargs={"model_mode": "fast"},
        warm_iterations=3,
        sampler=sampler,
    )

    # 3. VLM 4B Benchmark
    vlm_4b_bench = None
    if not args.skip_4b:
        vlm_4b_bench = run_isolated_task(
            task_name="VLM 4B (Qwen3-VL-4B Instruct)",
            func=vlm_adapter.ask,
            args=("صف المشهد باختصار للمستخدم الكفيف", str(scene_fixture)),
            kwargs={"model_mode": "detailed"},
            warm_iterations=1,
            sampler=sampler,
        )

    # 4. Object Detection / YOLO11n Benchmark
    from app.adapters.detection_adapter import DetectionAdapter
    det_adapter = DetectionAdapter(cfg.detection)
    living_fixture = PROJECT_ROOT / "data" / "fixtures" / "living_room.jpg"

    det_bench = run_isolated_task(
        task_name="YOLO11n Object Search (Living Room - Chair)",
        func=det_adapter.detect,
        args=(str(living_fixture),),
        kwargs={"target_object_ar": "كرسي"},
        warm_iterations=5,
        sampler=sampler,
    )

    # 5. ASR / faster-whisper Benchmark
    from app.adapters.asr_adapter import ASRAdapter
    asr_adapter = ASRAdapter(cfg.asr)
    audio_sample_path = PROJECT_ROOT / "data" / "audio_samples" / "objects_normal_pace_1.00.wav"
    with open(audio_sample_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode("utf-8")

    asr_bench = run_isolated_task(
        task_name="faster-whisper Arabic Speech Recognition",
        func=asr_adapter.transcribe,
        args=(audio_b64,),
        kwargs={"audio_format": "wav", "language": "ar"},
        warm_iterations=3,
        sampler=sampler,
    )

    # 6. TTS / Piper Benchmark
    from app.adapters.tts_adapter import TTSAdapter
    tts_adapter = TTSAdapter(cfg.tts)
    sample_text = "يوجد كرسي أمامك مباشرة على مسافة مترين تقريباً."

    tts_bench = run_isolated_task(
        task_name="Piper TTS Arabic Synthesis",
        func=tts_adapter.speak,
        args=(sample_text,),
        kwargs={},
        warm_iterations=3,
        sampler=sampler,
    )

    # Compile Benchmark Results
    all_tasks = [ocr_bench, vlm_2b_bench, det_bench, asr_bench, tts_bench]
    if vlm_4b_bench:
        all_tasks.append(vlm_4b_bench)

    final_report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "environment": env,
        "tasks": all_tasks,
    }

    out_path = PROJECT_ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print("BENCHMARK EXECUTION SUMMARY")
    print("=" * 80)
    print(f"{'Task':<35} | {'Cold (s)':<9} | {'Warm Avg (s)':<12} | {'Sys CPU%':<9} | {'Proc CPU%':<10} | {'GPU%':<6} | {'VRAM (MB)':<10}")
    print("-" * 100)
    for t in all_tasks:
        print(f"{t['task_name'][:35]:<35} | {t['cold_latency_s']:<9.2f} | {t['warm_avg_latency_s']:<12.3f} | {t['warm_sys_cpu_peak_pct']:<9.1f} | {t['warm_proc_cpu_peak_pct']:<10.1f} | {t['warm_gpu_util_peak_pct']:<6.1f} | {t['warm_vram_peak_mb']:<10.1f}")
    print("=" * 100)
    print(f"Results successfully saved to: {out_path}")

if __name__ == "__main__":
    main()
