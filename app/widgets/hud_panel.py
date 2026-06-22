from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from app.theme import Theme
from app.api.system_monitor import (
    get_cpu_percent, get_memory_info, get_gpu_info,
    get_fps, get_object_counts, get_network_stats,
)
from app.api.npu_enhancer import get_stats as get_npu_stats

_HUD_CSS = """
    QLabel {{
        background: transparent;
        color: {color};
        font-family: "Consolas", "Courier New", monospace;
        font-size: {size}px;
        padding: 0;
        margin: 0;
    }}
"""


class HudPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(1)

        self._lines = []
        for _ in range(9):
            lbl = QLabel("--")
            lbl.setFont(self._make_font(9))
            lbl.setStyleSheet(_HUD_CSS.format(color=Theme.SUCCESS, size=9))
            layout.addWidget(lbl)
            self._lines.append(lbl)

        layout.addStretch()

        self._timer = QTimer()
        self._timer.timeout.connect(self._refresh)
        self._timer.start(1000)

    def _make_font(self, size):
        f = QFont("Consolas", size)
        f.setStyleHint(QFont.StyleHint.Monospace)
        return f

    def _refresh(self):
        cpu = get_cpu_percent()
        mem_used, mem_total, mem_pct = get_memory_info()
        gpu = get_gpu_info()
        fps = get_fps()
        objs = get_object_counts()
        net = get_network_stats()

        lines = []

        cpu_color = Theme.SUCCESS if cpu < 50 else (Theme.WARNING if cpu < 80 else Theme.DANGER)
        lines.append(("CPU".ljust(10) + f"{cpu:5.1f}%", cpu_color))

        mem_color = Theme.SUCCESS if mem_pct < 60 else (Theme.WARNING if mem_pct < 85 else Theme.DANGER)
        lines.append(("MEM".ljust(10) + f"{mem_used:.1f}/{mem_total:.0f}GB", mem_color))

        if gpu:
            gpu_color = Theme.SUCCESS if gpu["util"] < 50 else (Theme.WARNING if gpu["util"] < 80 else Theme.DANGER)
            gpu_name = gpu["name"].split()[:1]
            gpu_label = "GPU"  # shorten
            lines.append((f"GPU".ljust(10) + f"{gpu['util']:5d}%", gpu_color))
        else:
            lines.append(("GPU".ljust(10) + "N/A", Theme.TEXT_MUTED))

        fps_color = Theme.SUCCESS if fps >= 30 else (Theme.WARNING if fps >= 15 else Theme.DANGER)
        lines.append(("FPS".ljust(10) + f"{fps:5.1f}", fps_color))

        obj_str = f"{objs.get('stars',0)}S {objs.get('planets',0)}P {objs.get('satellites',0)}Sat {objs.get('dsos',0)}D"
        lines.append(("OBJECTS".ljust(10) + obj_str, Theme.TEXT_SECONDARY))

        if net:
            lat = net["avg_latency"]
            lat_color = Theme.SUCCESS if lat < 200 else (Theme.WARNING if lat < 500 else Theme.DANGER)
            lines.append((f"LATENCY".ljust(10) + f"{lat:5.0f}ms", lat_color))
        else:
            lines.append(("LATENCY".ljust(10) + "---", Theme.TEXT_MUTED))

        net_status = "OK" if (net and net["failed"] == 0) else ("FAIL" if net and net["failed"] > 0 else "---")
        net_color = Theme.SUCCESS if net_status == "OK" else (Theme.DANGER if net_status == "FAIL" else Theme.TEXT_MUTED)
        lines.append((f"NET".ljust(10) + f"{net_status:>5}", net_color))

        npu_stats = get_npu_stats()
        npu_str = f"{npu_stats.device.value}" if npu_stats.device.value != "N/A" else "N/A"
        npu_lat = f"{npu_stats.latency_ms:.0f}ms" if npu_stats.frames_processed > 0 else "--"
        npu_color = Theme.SUCCESS if npu_stats.running and npu_stats.latency_ms < 50 else Theme.TEXT_SECONDARY
        lines.append((f"NPU".ljust(10) + f"{npu_str:>5} {npu_lat}", npu_color))

        # Last line — timestamp
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        lines.append(("TIME".ljust(10) + ts, Theme.TEXT_MUTED))

        for i, (text, color) in enumerate(lines):
            if i < len(self._lines):
                hex_color = color if isinstance(color, str) else "#E8EAF0"
                self._lines[i].setText(f"$ {text}")
                self._lines[i].setStyleSheet(_HUD_CSS.format(color=hex_color, size=9))

    def showEvent(self, event):
        super().showEvent(event)
        self._timer.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._timer.stop()
