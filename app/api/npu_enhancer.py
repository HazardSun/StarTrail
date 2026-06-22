"""NPU-accelerated AI image enhancement module.

Hardware priority: DML (DirectML/NPU) → CPU fallback.
Uses data/models/denoiser.onnx for real NPU inference.
"""
import time
import threading
import os
from pathlib import Path
import numpy as np
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable

_HAS_ONNX = False
_DML_SESSION = None
_MODEL_PATH = Path(__file__).parent.parent.parent / "data" / "models" / "denoiser.onnx"
try:
    import onnxruntime
    _HAS_ONNX = True
except ImportError:
    pass


class DeviceType(Enum):
    NPU = "NPU (DirectML)"
    CPU = "CPU"
    NONE = "N/A"


@dataclass
class EnhancementStats:
    device: DeviceType = DeviceType.NONE
    latency_ms: float = 0.0
    running: bool = False
    frames_processed: int = 0


_stats = EnhancementStats()
_lock = threading.Lock()


def detect_device() -> DeviceType:
    if not _HAS_ONNX:
        return DeviceType.NONE
    try:
        providers = onnxruntime.get_available_providers()
        if "DmlExecutionProvider" in providers:
            return DeviceType.NPU
        return DeviceType.CPU
    except Exception:
        return DeviceType.NONE


def _load_model():
    """Load the ONNX denoiser model into the DML session."""
    global _DML_SESSION
    if not _HAS_ONNX or not _MODEL_PATH.exists():
        print(f"[NPU] Model not found at {_MODEL_PATH}, using CPU fallback")
        return False
    try:
        device = detect_device()
        opts = onnxruntime.SessionOptions()
        opts.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_ENABLE_ALL
        opts.enable_cpu_mem_arena = True
        if device == DeviceType.NPU:
            providers = [("DmlExecutionProvider", {"device_id": 0}), "CPUExecutionProvider"]
        else:
            providers = ["CPUExecutionProvider"]
        _DML_SESSION = onnxruntime.InferenceSession(str(_MODEL_PATH), opts, providers=providers)
        print(f"[NPU] Model loaded on {device.value}")
        return True
    except Exception as e:
        print(f"[NPU] Model load failed: {e}")
        return False


def _bilateral_filter_np(img: np.ndarray, d: int = 3, sigma_color: float = 30.0) -> np.ndarray:
    """CPU bilateral filter fallback."""
    h, w, c = img.shape
    out = img.copy().astype(np.float32)
    half = d // 2
    space_kernel = np.zeros((d, d), dtype=np.float32)
    for i in range(d):
        for j in range(d):
            space_kernel[i, j] = np.exp(-((i - half) ** 2 + (j - half) ** 2) / 2.0)
    for y in range(half, h - half):
        for x in range(half, w - half):
            patch = img[y - half:y + half + 1, x - half:x + half + 1].astype(np.float32)
            center = img[y, x].astype(np.float32)
            cd = np.sum((patch - center) ** 2, axis=2)
            ck = np.exp(-cd / (2 * sigma_color ** 2))
            k = space_kernel * ck
            k /= k.sum()
            for ch in range(c):
                out[y, x, ch] = np.sum(patch[:, :, ch] * k)
    return np.clip(out, 0, 255).astype(np.uint8)


def _sharpen_np(img: np.ndarray, strength: float = 0.3) -> np.ndarray:
    """CPU box-blur unsharp mask fallback."""
    from numpy.lib.stride_tricks import sliding_window_view
    k = 3
    pad = k // 2
    padded = np.pad(img.astype(np.float32), ((pad, pad), (pad, pad), (0, 0)), mode='edge')
    h, w = img.shape[:2]
    blurred = np.zeros_like(img, dtype=np.float32)
    for i in range(k):
        for j in range(k):
            blurred += padded[i:i+h, j:j+w]
    blurred /= (k * k)
    sharpened = img.astype(np.float32) + strength * (img.astype(np.float32) - blurred)
    return np.clip(sharpened, 0, 255).astype(np.uint8)


def _run_onnx_inference(rgb: np.ndarray) -> np.ndarray:
    """Run the ONNX model on an RGB frame using DML/NPU.

    rgb: (H, W, 3) uint8 numpy array.
    Returns enhanced (H, W, 3) uint8 numpy array.
    """
    global _DML_SESSION
    if _DML_SESSION is None:
        return rgb

    try:
        h, w = rgb.shape[:2]
        # ONNX model expects (1, 3, H, W) float32
        inp = rgb.astype(np.float32).transpose(2, 0, 1)[np.newaxis, ...]
        inp /= 255.0

        io = onnxruntime.IOBinding(_DML_SESSION)
        io.bind_cpu_input("input", inp)
        out_tensor = onnxruntime.OrtValue.ortvalue_from_shape_and_type(
            [1, 3, h, w], np.float32, "dml"
        )
        io.bind_output("output", out_tensor)
        _DML_SESSION.run_with_iobinding(io)
        result = out_tensor.numpy()

        result = np.clip(result[0].transpose(1, 2, 0) * 255.0, 0, 255).astype(np.uint8)
        return result
    except Exception:
        return rgb


def enhance_frame(frame: np.ndarray, scale: float = 1.0) -> np.ndarray:
    """Enhance a single frame using NPU or CPU fallback."""
    global _stats
    t0 = time.perf_counter()

    if frame is None or frame.size == 0:
        return frame

    if frame.shape[2] == 4:
        rgb = frame[:, :, :3].copy()
        alpha = frame[:, :, 3:4].copy()
    else:
        rgb = frame.copy()
        alpha = None

    # NPU/ONNX inference path
    if _DML_SESSION is not None:
        rgb = _run_onnx_inference(rgb)
    else:
        # CPU fallback
        rgb = _bilateral_filter_np(rgb, d=3, sigma_color=25.0)
        rgb = _sharpen_np(rgb, strength=0.25)

    # Upscale
    if scale > 1.0:
        try:
            h, w = rgb.shape[:2]
            nh, nw = int(h * scale), int(w * scale)
            y = np.linspace(0, h - 1, nh)
            x = np.linspace(0, w - 1, nw)
            y0 = y.astype(np.int32)
            x0 = x.astype(np.int32)
            y1 = np.minimum(y0 + 1, h - 1)
            x1 = np.minimum(x0 + 1, w - 1)
            ya = y - y0
            xa = x - x0
            rgb = (
                rgb[y0][:, x0] * (1 - ya)[:, None] * (1 - xa) +
                rgb[y0][:, x1] * (1 - ya)[:, None] * xa +
                rgb[y1][:, x0] * ya[:, None] * (1 - xa) +
                rgb[y1][:, x1] * ya[:, None] * xa
            ).astype(np.uint8)
        except Exception:
            pass

    if alpha is not None:
        if scale > 1.0:
            ah, aw = alpha.shape[:2]
            alpha = alpha.repeat(scale, axis=0).repeat(scale, axis=1)[:int(ah*scale), :int(aw*scale)]
        result = np.concatenate([rgb, alpha], axis=2)
    else:
        result = rgb

    elapsed = (time.perf_counter() - t0) * 1000
    with _lock:
        _stats.latency_ms = round(elapsed, 1)
        _stats.frames_processed += 1
        _stats.running = True
        _stats.device = detect_device()

    return result


class AsyncEnhancer:
    """Runs enhancement in a background thread, calls callback on completion."""

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._callback: Optional[Callable] = None
        self._pending = False

    def submit(self, frame: np.ndarray, scale: float, callback: Callable):
        if self._pending:
            return
        self._pending = True
        self._callback = callback
        self._thread = threading.Thread(
            target=self._run,
            args=(frame.copy() if frame is not None else None, scale),
            daemon=True,
        )
        self._thread.start()

    def _run(self, frame, scale):
        if frame is None:
            self._pending = False
            return
        result = enhance_frame(frame, scale)
        self._pending = False
        if self._callback:
            self._callback(result)


def get_stats() -> EnhancementStats:
    with _lock:
        return EnhancementStats(
            device=_stats.device,
            latency_ms=_stats.latency_ms,
            running=_stats.running,
            frames_processed=_stats.frames_processed,
        )


def reset_stats():
    with _lock:
        _stats.latency_ms = 0.0
        _stats.frames_processed = 0


# Auto-init
_DEVICE = detect_device()
if _DEVICE != DeviceType.NONE:
    _load_model()
    with _lock:
        _stats.device = _DEVICE
