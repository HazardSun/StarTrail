# StarTrail 开发环境配置指南

> Agent 3（全栈性能工程师）输出 · 基于 Agent 1/2 分析结果

---

## 1. Python 依赖版本清单

### 1.1 当前 requirements.txt（原始）

```
PySide6>=6.6.0
requests>=2.31.0
skyfield>=1.45
```

**问题**: 缺少 numpy、PyOpenGL、onnxruntime 等运行时依赖，实际 `import` 会报错。

### 1.2 增强版 requirements.txt

```txt
# ═══════════════════════════════════════════════════
# StarTrail 开发环境依赖（Python 3.11 / 3.12）
# ═══════════════════════════════════════════════════

# ── GUI 框架 ──
PySide6==6.6.3.4              # Qt 6.6 LTS，稳定版，含 QOpenGLWidgets

# ── 天文计算 ──
skyfield==1.46                 # DE421/DE440 ephemeris，J2000.0 历元

# ── OpenGL 渲染 ──
PyOpenGL==3.1.7               # GL/GLU/GLUT 绑定（gl_hybrid_chart.py 依赖）
numpy==1.26.4                  # 数组运算、GL 顶点缓冲

# ── NPU/AI 加速 ──
onnxruntime-directml==1.19.0  # DirectML provider（NPU/GPU 推理）
                               # 替代: onnxruntime-gpu==1.19.0 (CUDA)
                               # 或:   onnxruntime==1.19.0 (CPU fallback)

# ── 网络与数据 ──
requests==2.32.3               # HTTP（CelesTrak/ADSB API）

# ── 打包 ──
pyinstaller==6.10.0            # Windows 打包

# ── 开发工具（可选）──
ruff==0.7.0                    # Linter
mypy==1.13.0                   # Type checker
pytest==8.3.4                  # 测试
pytest-qt==4.4.0               # Qt widget 测试
```

### 1.3 版本选择依据

| 组件 | 选择版本 | 理由 |
|------|---------|------|
| PySide6 | 6.6.3.4 | Qt 6.6 LTS，与 build.py 的 EXCLUDE 列表兼容 |
| Skyfield | 1.46 | DE421 仍默认加载（300MB），DE440 可选 |
| numpy | 1.26.4 | 与 PySide6/PyOpenGL 兼容，float32 GL 缓冲 |
| PyOpenGL | 3.1.7 | 稳定版，支持 GL 3.3 Core Profile |
| onnxruntime-directml | 1.19.0 | Windows 10+ DirectML NPU 支持 |
| Python | 3.11.x | 性能最优，PySide6/ONNX 兼容性最佳 |

---

## 2. NPU 环境检测脚本

保存为 `scripts/check_npu_env.py`，可直接运行：

```python
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
        print(f"  BLAS:      {np.show_config() or '见上方输出'}")
    except ImportError:
        print("  ❌ 未安装")
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
            print("  ✅ DirectML 可用")
            print("  → NPU/GPU 推理已就绪")
        else:
            print("  ⚠️  DirectML 不可用")
            print("  → 仅 CPU 推理")
            print("  → 安装: pip install onnxruntime-directml")
            print("  → 要求: Windows 10 1903+, 支持 DirectX 12 的 GPU")
        return has_dml
    except Exception as e:
        print(f"  ❌ 检测失败: {e}")
        return False


def check_npu_device():
    print_header("NPU 设备信息（Windows）")
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

        # 创建一个简单的 ONNX 模型用于测试
        from onnxruntime.capi.onnxruntime_pybind11_state import InferenceSession
        import onnx
        from onnx import helper, TensorProto

        X = helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, 3, 64, 64])
        Y = helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 3, 64, 64])
        node = helper.make_node("Relu", ["input"], ["output"])
        graph = helper.make_graph([node], "test", [X], [Y])
        model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])

        import tempfile
        import os
        tmp = tempfile.NamedTemporaryFile(suffix=".onnx", delete=False)
        tmp.write(model.SerializeToString())
        tmp.close()

        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        session = ort.InferenceSession(tmp.name, opts, providers=provider)
        os.unlink(tmp.name)

        # 预热
        dummy = np.random.randn(1, 3, 64, 64).astype(np.float32)
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
            print("  ⚠️  性能一般，可能受 CPU 限制")

    except Exception as e:
        print(f"  ❌ 基准测试失败: {e}")
        print(f"  → {type(e).__name__}: {e}")


def check_opengl():
    print_header("OpenGL 渲染")
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtOpenGLWidgets import QOpenGLWidget
        from PySide6.QtGui import QSurfaceFormat
        print("  ✅ PySide6 QOpenGLWidget 可用")
    except ImportError:
        print("  ❌ QOpenGLWidget 不可用")
        return False

    try:
        from OpenGL import GL
        print(f"  ✅ PyOpenGL 可用: {GL.glGetString(GL.GL_VERSION)}")
        print(f"  → GL Renderer: {GL.glGetString(GL.GL_RENDERER)}")
        return True
    except Exception as e:
        print(f"  ❌ PyOpenGL 异常: {e}")
        return False


def check_skyfield():
    print_header("Skyfield 天文计算")
    try:
        from skyfield.api import load
        print(f"  ✅ Skyfield 可用")
        ts = load.timescale()
        print(f"  ✅ 时间尺度加载成功")
    except ImportError:
        print("  ❌ Skyfield 未安装")
        return False
    return True


def check_pyside6():
    print_header("PySide6 GUI 框架")
    try:
        import PySide6
        print(f"  ✅ PySide6 版本: {PySide6.__version__}")
        from PySide6.QtCore import QT_VERSION_STR
        print(f"  → Qt 版本: {QT_VERSION_STR}")
        return True
    except ImportError:
        print("  ❌ PySide6 未安装")
        return False


def main():
    print("\n" + "=" * 50)
    print("  StarTrail NPU 环境检测")
    print("=" * 50)

    check_python()
    check_pyside6()
    check_numpy()
    has_onnx = check_onnxruntime()
    has_dml = check_directml() if has_onnx else False
    check_npu_device()
    if has_onnx:
        benchmark_inference()
    check_opengl()
    check_skyfield()

    print_header("总结")
    status = []
    if has_dml:
        status.append("NPU/DirectML ✅")
    elif has_onnx:
        status.append("NPU/DirectML ⚠️ (CPU fallback)")
    else:
        status.append("NPU/DirectML ❌")
    print(f"  {' | '.join(status)}")
    print(f"  Python {sys.version_info.major}.{sys.version_info.minor}")
    print()


if __name__ == "__main__":
    main()
```

---

## 3. ASCOM 兼容性检查

### 3.1 适用性评估

| 功能 | 当前状态 | ASCOM 需求 | 优先级 |
|------|---------|-----------|--------|
| 赤道仪控制 | 未实现 | ASCOM Telescope V2 | P2 |
| 相机控制 | 未实现 | ASCOM Camera V3 | P2 |
| 星图导星 | StarChart 有 guide_goto() | 需要 ASCOM 桥接 | P3 |
| FOV 叠加 | set_camera_fov 已有接口 | 可直接对接 | P2 |

### 3.2 ASCOM 检查脚本

保存为 `scripts/check_ascom.py`：

```python
#!/usr/bin/env python3
"""ASCOM 兼容性检查 - 检测 Windows 平台 ASCOM 驱动可用性。"""
import sys
import os
import winreg
from pathlib import Path


def check_ascom_platform():
    """检查 ASCOM Platform 是否安装。"""
    print("=" * 50)
    print("  ASCOM 兼容性检查")
    print("=" * 50)

    ascom_paths = [
        Path(os.environ.get("ProgramFiles", "")) / "ASCOM",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "ASCOM",
        Path(os.environ.get("LOCALAPPDATA", "")) / "ASCOM",
    ]

    found = False
    for p in ascom_paths:
        if p.exists():
            print(f"  ✅ ASCOM 目录: {p}")
            found = True
            break

    if not found:
        print("  ❌ 未检测到 ASCOM Platform")
        print("  → 下载: https://ascom-standards.org/")
        print("  → 安装 ASCOM Platform 6.6+")

    return found


def check_ascom_registry():
    """检查 Windows 注册表中的 ASCOM 驱动。"""
    print("\n已注册的 ASCOM 驱动:")

    drivers = {
        "Telescope": r"SOFTWARE\ASCOM\Telescope Drivers",
        "Camera": r"SOFTWARE\ASCOM\Camera Drivers",
        "Focuser": r"SOFTWARE\ASCOM\Focuser Drivers",
        "FilterWheel": r"SOFTWARE\ASCOM\FilterWheel Drivers",
    }

    for dev_type, reg_path in drivers.items():
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path)
            count = 0
            i = 0
            while True:
                try:
                    name, _, _ = winreg.EnumValue(key, i)
                    if count == 0:
                        print(f"\n  {dev_type}:")
                    print(f"    - {name}")
                    count += 1
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
            if count == 0:
                print(f"  {dev_type}: (无)")
        except FileNotFoundError:
            print(f"  {dev_type}: (未注册)")


def check_python_ascom():
    """检查 Python ASCOM 绑定。"""
    print("\nPython ASCOM 绑定:")
    try:
        import win32com.client
        print("  ✅ pywin32 可用 (COM 自动化)")
    except ImportError:
        print("  ❌ pywin32 未安装 → pip install pywin32")

    try:
        import clr
        print("  ✅ pythonnet 可用 (.NET 互操作)")
    except ImportError:
        print("  ⚠️  pythonnet 未安装 (可选) → pip install pythonnet")


def recommend_interface():
    print("\n" + "=" * 50)
    print("  StarTrail ASCOM 集成建议")
    print("=" * 50)
    print("""
  推荐方案：ASCOM Alpaca（跨平台 REST API）

  1. 赤道仪控制接口:
     - ASCOM Telescope.V2 → CoordsSlewToAltAz()
     - 对接 StarChart.guide_goto(alt, az)
     - 支持: 公制/英制坐标切换

  2. 相机控制接口:
     - ASCOM Camera.V3 → StartExposure() / ImageArray
     - 对接 NPU 增强 pipeline
     - 支持: FITS/JPEG 格式

  3. FOV 计算:
     - 从 ASCOM Camera 获取 PixelSize / FocalLength
     - 自动计算 fov_h_deg / fov_v_deg
     - 对接 StarChart.set_camera_fov()

  注意: 当前版本可跳过 ASCOM，使用内置天文数据库即可。
  ASCOM 集成建议在 v2.0 阶段实现。
""")


if __name__ == "__main__":
    if sys.platform == "win32":
        check_ascom_platform()
        check_ascom_registry()
        check_python_ascom()
        recommend_interface()
    else:
        print("ASCOM 仅支持 Windows 平台")
```

---

## 4. 开发环境配置建议

### 4.1 Python 版本

```
推荐: Python 3.11.x (3.11.9 最新)
次选: Python 3.12.x
禁用: Python 3.13+ (PySide6 兼容性风险)
```

### 4.2 虚拟环境设置

```bash
# 创建虚拟环境
python -m venv .venv

# 激活（Windows PowerShell）
.venv\Scripts\Activate.ps1

# 或激活（CMD）
.venv\Scripts\activate.bat

# 安装依赖
pip install -r requirements.txt

# 验证安装
python scripts/check_npu_env.py
```

### 4.3 IDE 配置

**VS Code `.vscode/settings.json`:**
```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe",
    "python.terminal.activateEnvironment": true,
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.fixAll.ruff": "explicit",
            "source.organizeImports.ruff": "explicit"
        }
    },
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        "**/build": true,
        "**/dist": true,
        "**/*.spec": true
    },
    "search.exclude": {
        "**/data": true,
        "**/.venv": true
    }
}
```

**推荐 VS Code 扩展:**
- `ms-python.python` - Python 支持
- `charliermarsh.ruff` - Linter + Formatter
- `ms-python.mypy-type-checker` - 类型检查
- `ms-python.debugpy` - 调试器

### 4.4 调试技巧

```bash
# 性能分析（cProfile）
python -m cProfile -o profile.prof main.py
snakeviz profile.prof  # 可视化

# 内存分析
pip install memory_profiler
python -m memory_profiler main.py

# OpenGL 调试（设置环境变量）
set QT_LOGGING_RULES="qt.opengl*=true"
python main.py

# Skyfield 性能测试
python -c "
from skyfield.api import load
ts = load.timescale()
t = ts.now()
print(f'JD: {t.tt}')
print('Skyfield 加载完成')
"

# NPU 推理日志
set ONNX_LOG_LEVEL=0
python main.py
```

---

## 5. 性能优化建议

### 5.1 星表数据索引策略

**当前问题**: `astronomy_api.py` 中 `BRIGHT_STARS` 是 59 颗硬编码恒星，DSO 目录从 JSON 全量加载后无索引。

**优化方案:**

```python
# app/api/star_index.py（新建文件）
"""星表空间索引 - 基于 RA/Dec 的 KD-Tree 加速查询。"""
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class StarRecord:
    name: str
    ra_deg: float   # 赤经 (度)
    dec_deg: float  # 赤纬 (度)
    mag: float
    color: str


class StarIndex:
    """基于 RA/Dec 的简单网格索引，替代全量遍历。"""

    def __init__(self, cell_size_deg: float = 10.0):
        self._cell_size = cell_size_deg
        self._grid: Dict[Tuple[int, int], List[StarRecord]] = {}
        self._all_stars: List[StarRecord] = []

    def build(self, stars: List[Dict]):
        """从原始星表数据构建索引。"""
        self._grid.clear()
        self._all_stars.clear()
        for s in stars:
            rec = StarRecord(
                name=s.get("name", ""),
                ra_deg=s.get("ra", 0),
                dec_deg=s.get("dec", 0),
                mag=s.get("mag", 99),
                color=s.get("color", "#FFFFFF"),
            )
            self._all_stars.append(rec)
            cell = self._cell_key(rec.ra_deg, rec.dec_deg)
            if cell not in self._grid:
                self._grid[cell] = []
            self._grid[cell].append(rec)

    def _cell_key(self, ra: float, dec: float) -> Tuple[int, int]:
        return (int(ra // self._cell_size), int(dec // self._cell_size))

    def query_radius(self, ra_deg: float, dec_deg: float,
                     radius_deg: float) -> List[StarRecord]:
        """查询 RA/Dec 周围 radius_deg 范围内的恒星。"""
        results = []
        min_ra = ra_deg - radius_deg
        max_ra = ra_deg + radius_deg
        min_dec = dec_deg - radius_deg
        max_dec = dec_deg + radius_deg

        ra_cells = range(int(min_ra // self._cell_size),
                         int(max_ra // self._cell_size) + 1)
        dec_cells = range(int(min_dec // self._cell_size),
                          int(max_dec // self._cell_size) + 1)

        for rc in ra_cells:
            for dc in dec_cells:
                for star in self._grid.get((rc, dc), []):
                    # 简化：用 RA/Dec 坐标距离近似
                    dra = star.ra_deg - ra_deg
                    ddec = star.dec_deg - dec_deg
                    dist = (dra ** 2 + ddec ** 2) ** 0.5
                    if dist <= radius_deg:
                        results.append(star)
        return sorted(results, key=lambda s: s.mag)

    def query_visible(self, altitude_min: float = 10.0,
                      latitude: float = 39.9) -> List[StarRecord]:
        """查询当前可见的恒星（简化：仅按星等过滤）。"""
        return [s for s in self._all_stars if s.mag < 6.0]

    @property
    def count(self) -> int:
        return len(self._all_stars)
```

**集成方式**: 在 `astronomy_api.py` 的 `SkyCalculator` 中初始化索引，替代全量遍历：

```python
# astronomy_api.py 修改建议
class SkyCalculator:
    _star_index = None

    @classmethod
    def _ensure_index(cls):
        if cls._star_index is None:
            from app.api.star_index import StarIndex
            cls._star_index = StarIndex(cell_size_deg=15.0)
            cls._star_index.build(BRIGHT_STARS)
```

### 5.2 GL 渲染优化

**当前问题**: `gl_hybrid_chart.py` 每帧都重新上传顶点数据，QPainter overlay 与 GL 混合效率低。

**优化方案:**

```python
# 优化点 1: VBO 缓存 - 仅在数据变化时重新上传
def _upload_stars(self):
    """仅在星表数据变化时上传 VBO。"""
    if not self._gl_ok:
        return
    # 计算数据哈希，避免重复上传
    data_hash = hash(tuple(
        (s["altitude"], s["azimuth"], s.get("mag", 5))
        for s in self._stars[:100]  # 采样前100颗星
    ))
    if hasattr(self, '_last_data_hash') and self._last_data_hash == data_hash:
        return
    self._last_data_hash = data_hash
    # ... 原有上传逻辑 ...


# 优化点 2: 批量 QPainter 调用 - 减少状态切换
def _draw_overlay_batched(self):
    """将 QPainter 绘制分批执行，减少 pen/brush 切换。"""
    p = QPainter(self)
    p.setRenderHint(QPainter.Antialiasing)

    # 批次 1: 所有行星（同一种 pen/brush）
    self._draw_planets_batch(p)

    # 批次 2: 所有卫星
    self._draw_satellites_batch(p)

    p.end()


# 优化点 3: 降低 QPainter overlay 频率
# 在 paintGL() 中，GL 层始终绘制，overlay 每3帧更新一次
def paintGL(self):
    self._draw_skybox()
    self._draw_stars_gl()
    self._frame_counter = getattr(self, '_frame_counter', 0) + 1
    if self._frame_counter % 3 == 0 or self._needs_overlay_update:
        self._draw_overlay()
        self._needs_overlay_update = False
```

### 5.3 多线程调度优化

**当前问题**: `background_worker.py` 限制 2 个线程，但 NPU 推理、卫星计算、网络请求串行执行。

**优化方案:**

```python
# 修改 background_worker.py
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool, QTimer

class TaskPriority:
    """任务优先级。"""
    LOW = 0       # 网络请求、飞机数据
    NORMAL = 1    # 卫星计算
    HIGH = 2      # NPU 推理、UI 响应
    CRITICAL = 3  # 用户交互


class _PrioritizedTask(QRunnable):
    def __init__(self, target, args, kwargs, signals, priority):
        super().__init__()
        self._target = target
        self._args = args
        self._kwargs = kwargs
        self._signals = signals
        self._priority = priority
        self.setAutoDelete(True)

    def run(self):
        try:
            result = self._target(*self._args, **self._kwargs)
            self._signals.finished.emit(result)
        except Exception as e:
            self._signals.error.emit(str(e))


# 线程池配置：NPU 专用线程 + IO 线程 + 计算线程
NPU_POOL = QThreadPool()
NPU_POOL.setMaxThreadCount(1)  # NPU 串行执行

IO_POOL = QThreadPool()
IO_POOL.setMaxThreadCount(3)  # 网络 I/O 并行

COMPUTE_POOL = QThreadPool()
COMPUTE_POOL.setMaxThreadCount(2)  # CPU 计算


def run_in_background(target, on_finished=None, on_error=None,
                      args=None, kwargs=None, priority=TaskPriority.NORMAL,
                      pool=None):
    """改进版后台任务调度。"""
    signals = _TaskSignals()
    _SIGNAL_REFS.append(signals)

    task = _PrioritizedTask(target, args or (), kwargs or {},
                            signals, priority)

    if on_finished:
        signals.finished.connect(on_finished)
    if on_error:
        signals.error.connect(on_error)
    signals.finished.connect(lambda: _SIGNAL_REFS.remove(signals)
                             if signals in _SIGNAL_REFS else None)

    if pool is None:
        pool = QThreadPool.globalInstance()
    pool.start(task)
```

### 5.4 Skyfield 计算缓存

```python
# astronomy_api.py 中添加计算缓存
from functools import lru_cache
from datetime import datetime, timedelta

class SkyCalculator:
    _position_cache = {}
    _cache_ttl = timedelta(minutes=5)

    @classmethod
    def get_bright_stars_altaz(cls, dt: datetime, mag_limit: float):
        """带缓存的位置计算。"""
        cache_key = (dt.strftime("%Y%m%d%H"), mag_limit)
        now = datetime.now()

        if cache_key in cls._position_cache:
            cached_time, cached_data = cls._position_cache[cache_key]
            if now - cached_time < cls._cache_ttl:
                return cached_data

        # 计算新数据
        result = cls._compute_stars(dt, mag_limit)
        cls._position_cache[cache_key] = (now, result)

        # 清理过期缓存
        expired = [k for k, (t, _) in cls._position_cache.items()
                   if now - t > cls._cache_ttl * 2]
        for k in expired:
            del cls._position_cache[k]

        return result
```

---

## 6. 快速启动清单

```bash
# 1. 克隆仓库
git clone <repo-url> startrail
cd startrail

# 2. 创建虚拟环境
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. 安装依赖
pip install -r requirements.txt

# 4. 验证环境
python scripts/check_npu_env.py

# 5. 运行应用
python main.py

# 6. 运行测试
pytest tests/ -v

# 7. 代码检查
ruff check app/ --fix
mypy app/ --ignore-missing-imports
```

---

*文档生成时间: 2026-07-08 | Agent 3 - 全栈性能工程师*
