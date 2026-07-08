#!/usr/bin/env python3
import shutil, subprocess, sys, os
from pathlib import Path

BASE = Path(__file__).parent
DIST = BASE / "dist"
PYTHON = sys.executable

os.chdir(BASE)

EXCLUDE = [
    "PySide6.Qt3DAnimation", "PySide6.Qt3DCore", "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput", "PySide6.Qt3DLogic", "PySide6.Qt3DRender",
    "PySide6.QtAxContainer", "PySide6.QtBluetooth", "PySide6.QtCharts",
    "PySide6.QtConcurrent", "PySide6.QtDataVisualization", "PySide6.QtDBus",
    "PySide6.QtDesigner", "PySide6.QtGraphs", "PySide6.QtGraphsWidgets",
    "PySide6.QtHelp", "PySide6.QtHttpServer", "PySide6.QtLocation",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
    "PySide6.QtNetworkAuth", "PySide6.QtNfc", "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets", "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "PySide6.QtPositioning", "PySide6.QtPrintSupport", "PySide6.QtQuick",
    "PySide6.QtQuick3D", "PySide6.QtQuickControls2", "PySide6.QtQuickTest",
    "PySide6.QtQuickWidgets", "PySide6.QtRemoteObjects", "PySide6.QtScxml",
    "PySide6.QtSensors", "PySide6.QtSerialBus", "PySide6.QtSerialPort",
    "PySide6.QtSpatialAudio", "PySide6.QtSql", "PySide6.QtStateMachine",
    "PySide6.QtSvg", "PySide6.QtSvgWidgets", "PySide6.QtTest",
    "PySide6.QtTextToSpeech", "PySide6.QtUiTools", "PySide6.QtWebChannel",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineQuick",
    "PySide6.QtWebEngineWidgets", "PySide6.QtWebSockets", "PySide6.QtWebView",
    "PySide6.QtXml", "PySide6.QtCanvasPainter",
    "skyfield.tests", "skyfield.data.hipparcos",
    # Large ML packages not used at runtime
    "torch", "torchvision", "tensorflow", "transformers",
    "scipy", "scipy.special", "scipy.spatial", "scipy.stats", "scipy.linalg",
    "scipy.io", "scipy.sparse", "scipy.optimize", "scipy.fft", "scipy.signal",
    "sklearn", "pandas", "matplotlib", "PIL", "PIL.ImageFilter",
    "openpyxl", "cffi", "pycparser", "lxml", "fsspec", "pydantic",
    "rich", "pygments", "jinja2", "regex",
    "win32com", "charset_normalizer",
]

cmd = [str(PYTHON), "-m", "PyInstaller",
       "--windowed", "--onedir", "--noconfirm", "--clean",
       "--name", "StarTrail",
       "--add-data", f"data{os.pathsep}data",
       "--collect-all", "PySide6",
       "--collect-all", "skyfield"]

for m in EXCLUDE:
    cmd.extend(["--exclude-module", m])

cmd.append(str(BASE / "main.py"))

print("Building StarTrail...")
print(f"Excluded {len(EXCLUDE)} Python modules")
print()

proc = subprocess.run(cmd, capture_output=False)

exe_dir = DIST / "StarTrail"
exe_path = exe_dir / "StarTrail.exe"

if proc.returncode == 0 and exe_path.exists():
    internal = exe_dir / "_internal"
    pyside = internal / "PySide6"
    plugins = internal / "PySide6" / "plugins"

    killed_size = 0

    dll_kill = [
        "Qt6WebEngineCore.dll", "Qt6Quick.dll", "Qt6Quick3D*.dll",
        "Qt6QuickControls2*.dll", "Qt6QuickDialogs2*.dll",
        "Qt6QuickTemplates2*.dll", "Qt6QuickTest.dll", "Qt6QuickWidgets.dll",
        "Qt6Qml.dll", "Qt6Qml*.dll", "Qt6Designer.dll",
        "Qt6Pdf.dll", "Qt6PdfWidgets.dll",
        "Qt6WebChannel.dll", "Qt6WebSockets.dll",
        "Qt6Positioning.dll", "Qt6Location.dll",
        "Qt6Multimedia*.dll", "Qt6Serial*.dll",
        "Qt6Bluetooth.dll", "Qt6Nfc.dll",
        "Qt6Sensors.dll", "Qt6SerialBus.dll",
        "Qt6SpatialAudio.dll", "Qt6TextToSpeech.dll",
        "Qt6VirtualKeyboard.dll",
        "opengl32sw.dll", "d3dcompiler_*.dll",
        "avcodec-*.dll", "avformat-*.dll", "avutil-*.dll",
        "swresample-*.dll", "swscale-*.dll",
    ]
    if pyside and pyside.exists():
        for pat in dll_kill:
            for f in pyside.glob(pat):
                killed_size += f.stat().st_size
                f.unlink()

        for dirname in ["qml", "QtQuick", "QtQuick3D", "QtQml"]:
            d = pyside / dirname
            if d.exists():
                killed_size += sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
                shutil.rmtree(d, ignore_errors=True)

    if plugins and plugins.exists():
        for sub_dir in ["multimedia", "playlistformats", "position", "sensorgestures",
                        "sqldrivers", "webview"]:
            d = plugins / sub_dir
            if d.exists():
                killed_size += sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
                shutil.rmtree(d, ignore_errors=True)
        for f in plugins.glob("*.webp"):
            killed_size += f.stat().st_size
            f.unlink()

    total_mb = sum(f.stat().st_size for f in exe_dir.rglob("*") if f.is_file()) / 1048576
    killed_mb = killed_size / 1048576
    print()
    print("=" * 50)
    print(f"  Build OK!  EXE: {exe_path}")
    print(f"  Removed: {killed_mb:.0f} MB of unused Qt assets")
    print(f"  Final size: {total_mb:.0f} MB")
    print("=" * 50)

    zip_name = "StarTrail_v1.0.1.zip"
    zip_path = BASE / zip_name
    if zip_path.exists():
        zip_path.unlink()
    shutil.make_archive(str(zip_path.with_suffix("")), "zip", exe_dir)
    zip_mb = zip_path.stat().st_size / 1048576
    print(f"  ZIP: {zip_name} ({zip_mb:.0f} MB)")
else:
    print()
    print(f"  Build FAILED (code: {proc.returncode})")

for p in [BASE / "build", BASE / "__pycache__"]:
    shutil.rmtree(p, ignore_errors=True)
for p in BASE.rglob("__pycache__"):
    shutil.rmtree(p, ignore_errors=True)
spec = BASE / "StarTrail.spec"
if spec.exists():
    spec.unlink()
