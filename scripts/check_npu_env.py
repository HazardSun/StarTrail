#!/usr/bin/env python3
"""NPU 环境检测脚本 - 检测 DirectML / NPU 可用性及推理性能。"""
import sys
import time
import platform


def print_header(text):
    print(f"\n{'='*50}")
    print(f"  {text}")
    print(f"{'='*50}")


def check_python():
    print_header("Python 环境")
    print(f"  版本:      {sys.version}")
    print(f"  平台:      {platform.platform()}")
    print(f"  处理器:    {platform.processor()}")
    print(f"  架构:      {platform.machine()}")


def check_numpy():
    print_header("NumPy")
    try:
        import numpy as np
        print(f"  版本:      {np.__version__}")
    except ImportError:
        print("  ❌ 未安装 → pip install numpy")
        return False
    return True


def check_onnxruntime():
    print_header("ONNX Runtime")
    try:
        import onnxruntime as ort
        print(f"  版本:      {ort.__version__}")
        providers = ort.get_available_providers()
        print(f"  可用 Provider:")
        for p in providers:
            marker = "✅" if p != "CPUExecutionProvider" else "  "
            print(f"    {marker} {p}")
        return True
    except ImportError:
        print("  ❌ 未安装 onnxruntime")
        print("  → pip install onnxruntime-directml")
        return False


def check_directml():
    print_header("DirectML / NPU 检测")
    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()
        has_dml = "DmlExecutionProvider" in providers
        if has_dml:
            print("  ✅ DirectML 可用 → NPU/GPU 推理已就绪")
        else:
            print("  ⚠️  DirectML 不可用 → 仅 CPU 推理")
            print("  → 安装: pip install onnxruntime-directml")
            print("  → 要求: Windows 10 1903+, DirectX 12 GPU")
        return has_dml
    except Exception as e:
        print(f"  ❌ 检测失败: {e}")
        return False


def check_npu_device():
    print_header("GPU 设备信息 (Windows)")
    try:
        import subprocess
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-WmiObject Win32_VideoController | "
             "Select-Object Name, DriverVersion, AdapterRAM | "
             "Format-List"],
            capture_output=True, text=True, timeout=10
        )
        if result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    print(f"  {line.strip()}")
        else:
            print("  (无法获取 GPU 信息)")
    except Exception as e:
        print(f"  ⚠️  查询失败: {e}")


def benchmark_inference():
    print_header("推理性能基准测试")
    try:
        import numpy as np
        import onnxruntime as ort

        providers = ort.get_available_providers()
        if "DmlExecutionProvider" in providers:
            provider = [("DmlExecutionProvider", {"device_id": 0}),
                        "CPUExecutionProvider"]
            device_name = "NPU/DirectML"
        else:
            provider = ["CPUExecutionProvider"]
            device_name = "CPU"

        print(f"  Provider:  {device_name}")

        from onnx import helper, TensorProto
        X = helper.make_tensor_value_info("input", TensorProto.FLOAT,
                                          [1, 3, 64, 64])
        Y = helper.make_tensor_value_info("output", TensorProto.FLOAT,
                                          [1, 3, 64, 64])
        node = helper.make_node("Relu", ["input"], ["output"])
        graph = helper.make_graph([node], "test", [X], [Y])
        model = helper.make_model(graph,
                                  opset_imports=[helper.make_opsetid("", 13)])

        import tempfile
        import os
        tmp = tempfile.NamedTemporaryFile(suffix=".onnx", delete=False)
        tmp.write(model.SerializeToString())
        tmp.close()

        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        session = ort.InferenceSession(tmp.name, opts, providers=provider)
        os.unlink(tmp.name)

        dummy = np.random.randn(1, 3, 64, 64).astype(np.float32)

        # 预热
        for _ in range(5):
            session.run(None, {"input": dummy})

        # 基准测试
        times = []
        for _ in range(50):
            t0 = time.perf_counter()
            session.run(None, {"input": dummy})
            times.append((time.perf_counter() - t0) * 1000)

        avg_ms = sum(times) / len(times)
        min_ms = min(times)
        max_ms = max(times)
        fps = 1000.0 / avg_ms

        print(f"  输入尺寸:  1×3×64×64 (float32)")
        print(f"  运行次数:  50")
        print(f"  平均延迟:  {avg_ms:.2f} ms")
        print(f"  最小延迟:  {min_ms:.2f} ms")
        print(f"  最大延迟:  {max_ms:.2f} ms")
        print(f"  理论 FPS:  {fps:.1f}")

        if avg_ms < 5:
            print("  ✅ 性能优秀")
        elif avg_ms < 20:
            print("  ✅ 性能良好")
        else:
            print("  ⚠️  性能一般，受 CPU 限制")

    except Exception as e:
        print(f"  ❌ 基准测试失败: {type(e).__name__}: {e}")


def check_opengl():
    print_header("OpenGL 渲染")
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtOpenGLWidgets import QOpenGLWidget
        print("  ✅ PySide6 QOpenGLWidget 可用")
    except ImportError:
        print("  ❌ QOpenGLWidget 不可用")
        return False
    try:
        from OpenGL import GL
        ver = GL.glGetString(GL.GL_VERSION)
        renderer = GL.glGetString(GL.GL_RENDERER)
        print(f"  ✅ PyOpenGL: GL {ver}")
        print(f"  → Renderer: {renderer}")
        return True
    except Exception as e:
        print(f"  ❌ PyOpenGL 异常: {e}")
        return False


def check_skyfield():
    print_header("Skyfield 天文计算")
    try:
        from skyfield.api import load
        ts = load.timescale()
        t = ts.now()
        print(f"  ✅ Skyfield 可用, JD: {t.tt:.4f}")
        return True
    except ImportError:
        print("  ❌ Skyfield 未安装 → pip install skyfield")
        return False


def check_pyside6():
    print_header("PySide6 GUI 框架")
    try:
        import PySide6
        from PySide6.QtCore import QT_VERSION_STR
        print(f"  ✅ PySide6 {PySide6.__version__} / Qt {QT_VERSION_STR}")
        return True
    except ImportError:
        print("  ❌ PySide6 未安装 → pip install PySide6")
        return False


def main():
    print("\n" + "=" * 50)
    print("  StarTrail NPU 环境检测")
    print("=" * 50)

    check_python()
    check_pyside6()
    ok_numpy = check_numpy()
    ok_onnx = check_onnxruntime()
    has_dml = check_directml() if ok_onnx else False
    check_npu_device()
    if ok_onnx:
        benchmark_inference()
    check_opengl()
    check_skyfield()

    print_header("总结")
    parts = []
    if has_dml:
        parts.append("NPU ✅")
    elif ok_onnx:
        parts.append("NPU ⚠️ CPU")
    else:
        parts.append("NPU ❌")
    parts.append(f"Python {sys.version_info.major}.{sys.version_info.minor}")
    print(f"  {' | '.join(parts)}\n")


if __name__ == "__main__":
    main()
