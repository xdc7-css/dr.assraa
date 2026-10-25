"""System inspection and hardware diagnostic tool for Arabic Multimodal Assistive Vision.
Checks RAM, VRAM, GPUs, drivers, Python version, disk space, and Ollama availability.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

def get_disk_info(paths: list[str]) -> dict:
    disks = {}
    for p in paths:
        try:
            target = Path(p).resolve()
            drive = target.anchor or p
            if drive not in disks:
                usage = shutil.disk_usage(drive)
                disks[drive] = {
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                }
        except Exception as e:
            disks[p] = {"error": str(e)}
    return disks

def get_system_memory() -> dict:
    mem = {}
    try:
        import psutil
        v = psutil.virtual_memory()
        mem["total_ram_mb"] = round(v.total / (1024 * 1024), 1)
        mem["available_ram_mb"] = round(v.available / (1024 * 1024), 1)
        mem["used_ram_mb"] = round(v.used / (1024 * 1024), 1)
        mem["ram_percent"] = v.percent
    except ImportError:
        # Fallback using Windows systeminfo / wmic or ctypes
        try:
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            mem["total_ram_mb"] = round(stat.ullTotalPhys / (1024 * 1024), 1)
            mem["available_ram_mb"] = round(stat.ullAvailPhys / (1024 * 1024), 1)
            mem["used_ram_mb"] = round((stat.ullTotalPhys - stat.ullAvailPhys) / (1024 * 1024), 1)
            mem["ram_percent"] = stat.dwMemoryLoad
        except Exception as e:
            mem["error"] = str(e)
    return mem

def get_gpu_info() -> list[dict]:
    gpus = []
    # Check via nvidia-smi
    smi = shutil.which("nvidia-smi")
    if smi:
        try:
            cmd = [
                smi,
                "--query-gpu=name,driver_version,memory.total,memory.free,memory.used",
                "--format=csv,noheader,nounits"
            ]
            out = subprocess.check_output(cmd, encoding="utf-8", errors="ignore").strip()
            for line in out.splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 5:
                    gpus.append({
                        "name": parts[0],
                        "driver_version": parts[1],
                        "vram_total_mb": float(parts[2]),
                        "vram_free_mb": float(parts[3]),
                        "vram_used_mb": float(parts[4]),
                    })
        except Exception as e:
            gpus.append({"nvidia_smi_error": str(e)})
    return gpus

def check_ollama() -> dict:
    info = {"installed": False, "running": False, "version": None, "endpoint": "http://127.0.0.1:11434"}
    ollama_path = shutil.which("ollama")
    if ollama_path:
        info["installed"] = True
        info["path"] = ollama_path
        try:
            ver = subprocess.check_output([ollama_path, "--version"], encoding="utf-8", errors="ignore").strip()
            info["version"] = ver
        except Exception:
            pass
    else:
        # Check standard user local directory
        user_local = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
        if user_local.exists():
            info["installed"] = True
            info["path"] = str(user_local)
            try:
                ver = subprocess.check_output([str(user_local), "--version"], encoding="utf-8", errors="ignore").strip()
                info["version"] = ver
            except Exception:
                pass

    # Check if REST API is responsive
    try:
        import urllib.request
        req = urllib.request.Request(f"{info['endpoint']}/api/version")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            info["running"] = True
            info["api_version"] = data.get("version")
    except Exception:
        info["running"] = False

    return info

def check_profile(ram_mb: float, vram_mb: float) -> str:
    # Recommended profile selection
    if ram_mb < 12000 or vram_mb < 6000:
        return "low_memory"
    return "balanced"

def run_diagnostics() -> dict:
    mem = get_system_memory()
    gpus = get_gpu_info()
    cwd = Path.cwd()
    disks = get_disk_info([str(cwd), "C:\\", "X:\\"])
    ollama = check_ollama()

    total_ram = mem.get("total_ram_mb", 0)
    total_vram = gpus[0].get("vram_total_mb", 0) if gpus and "vram_total_mb" in gpus[0] else 0
    recommended_profile = check_profile(total_ram, total_vram)

    report = {
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "python": sys.version,
        "python_executable": sys.executable,
        "workspace": str(cwd.resolve()),
        "memory": mem,
        "gpu": gpus,
        "disks": disks,
        "ollama": ollama,
        "recommended_profile": recommended_profile,
    }
    return report

if __name__ == "__main__":
    report = run_diagnostics()
    print("=" * 60)
    print(" SYSTEM DIAGNOSTICS & HARDWARE REPORT")
    print("=" * 60)
    print(f"OS: {report['os']}")
    print(f"Python: {report['python']}")
    print(f"RAM: Total {report['memory'].get('total_ram_mb', 'N/A')} MB | Available {report['memory'].get('available_ram_mb', 'N/A')} MB")
    if report["gpu"]:
        for g in report["gpu"]:
            print(f"GPU: {g.get('name', 'Unknown')} | VRAM Total {g.get('vram_total_mb', 'N/A')} MB | Free {g.get('vram_free_mb', 'N/A')} MB")
    else:
        print("GPU: None detected or nvidia-smi unavailable")
    print("Disk free space:")
    for d, info in report["disks"].items():
        if "free_gb" in info:
            print(f"  {d} -> {info['free_gb']} GB free of {info['total_gb']} GB")
    print(f"Ollama status: Installed: {report['ollama']['installed']}, Running: {report['ollama']['running']}")
    print(f"Recommended Profile: {report['recommended_profile'].upper()}")
    print("=" * 60)
