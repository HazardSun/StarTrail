import os
import subprocess
import time
from datetime import datetime

import psutil

_GPU_QUERY_TIME = 0
_GPU_INFO = None
_STAR_CHART_REF = None
_NET_LATENCIES = []


def set_star_chart_ref(chart):
    global _STAR_CHART_REF
    _STAR_CHART_REF = chart


def get_cpu_percent():
    """Return overall CPU usage percentage."""
    try:
        return round(psutil.cpu_percent(interval=0), 1)
    except Exception:
        return 0.0


def get_memory_info():
    """Return (used_gb, total_gb, percent)."""
    try:
        mem = psutil.virtual_memory()
        used = mem.used / (1024 ** 3)
        total = mem.total / (1024 ** 3)
        return round(used, 1), round(total, 1), mem.percent
    except Exception:
        return 0.0, 0.0, 0


def get_gpu_info():
    """Return GPU name and usage, or None."""
    global _GPU_QUERY_TIME, _GPU_INFO
    now = time.time()
    if _GPU_INFO and (now - _GPU_QUERY_TIME) < 10:
        return _GPU_INFO
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            timeout=3, stderr=subprocess.DEVNULL, encoding="utf-8"
        ).strip()
        if out:
            parts = out.split(",")
            if len(parts) >= 4:
                name = parts[0].strip()
                util = int(parts[1].strip())
                mem_used = int(parts[2].strip())
                mem_total = int(parts[3].strip())
                _GPU_INFO = {"name": name, "util": util, "mem_used": mem_used, "mem_total": mem_total}
                _GPU_QUERY_TIME = now
                return _GPU_INFO
    except Exception:
        pass
    # Fallback: try AMD via dxdiag or just return None
    _GPU_INFO = None
    _GPU_QUERY_TIME = now
    return None


def get_fps():
    """Return current FPS from StarChart, or 0."""
    global _STAR_CHART_REF
    if _STAR_CHART_REF is None:
        return 0
    try:
        elapsed = _STAR_CHART_REF._last_paint_ms
        if elapsed > 0:
            return round(1000.0 / elapsed, 1)
        return 0
    except Exception:
        return 0


def get_object_counts():
    """Return dict of celestial object counts from StarChart."""
    global _STAR_CHART_REF
    if _STAR_CHART_REF is None:
        return {}
    try:
        sc = _STAR_CHART_REF
        return {
            "stars": len(sc._stars),
            "planets": len(sc._planets),
            "satellites": len(sc._satellites),
            "aircraft": len(sc._aircraft),
            "dsos": len(sc._dsos),
        }
    except Exception:
        return {}


def record_api_latency(latency_ms):
    """Record a single API call latency (ms)."""
    global _NET_LATENCIES
    _NET_LATENCIES.append(latency_ms)
    if len(_NET_LATENCIES) > 20:
        _NET_LATENCIES.pop(0)


def get_network_stats():
    """Return (avg_latency_ms, last_latency_ms, success) or None."""
    global _NET_LATENCIES
    if not _NET_LATENCIES:
        return None
    try:
        avg = round(sum(_NET_LATENCIES) / len(_NET_LATENCIES), 0)
        last = round(_NET_LATENCIES[-1], 0)
        failed = sum(1 for l in _NET_LATENCIES if l < 0)
        return {
            "avg_latency": avg,
            "last_latency": last,
            "total_calls": len(_NET_LATENCIES),
            "failed": failed,
        }
    except Exception:
        return None
