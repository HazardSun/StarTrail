"""观星指数仪表盘 — 圆形环形进度条 + 中心大数字 + 颜色分级。

参考天文通的核心视觉元素：一眼判断今夜是否适合观星。
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QRadialGradient

from app.theme import Theme


class StargazingIndexGauge(QFrame):
    """圆形观星指数仪表盘。

    参数:
        value: 0-100 整数，观星指数分数
        size: 直径像素（默认 120）
        stroke_width: 环形粗细（默认 10）
    """

    def __init__(self, value: int = 0, size: int = 120, stroke_width: int = 10, parent=None):
        super().__init__(parent)
        self._value = max(0, min(100, int(value)))
        self._size = size
        self._stroke = stroke_width
        self.setFixedSize(size, size)

    def setValue(self, v: int):
        self._value = max(0, min(100, int(v)))
        self.update()

    def _level_color(self):
        """根据分数返回颜色。"""
        if self._value >= 75:
            return QColor(Theme.SG_EXCELLENT)   # 绿 — 优秀
        elif self._value >= 50:
            return QColor(Theme.SG_GOOD)         # 黄绿 — 良好
        elif self._value >= 25:
            return QColor(Theme.SG_FAIR)          # 橙 — 一般
        else:
            return QColor(Theme.SG_POOR)          # 红 — 差

    def _level_label(self):
        if self._value >= 75:
            return "优秀"
        elif self._value >= 50:
            return "良好"
        elif self._value >= 25:
            return "一般"
        else:
            return "较差"

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        radius = (min(w, h) - self._stroke * 2 - 4) // 2
        rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)

        # ── Background ring (暗底环) ──
        bg_pen = QPen(QColor(255, 255, 255, 8), self._stroke)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(rect, 90 * 16, 360 * 16)  # 从顶部开始顺时针

        # ── Value ring (彩色进度弧) ──
        span_angle = int(-self._value / 100.0 * 360 * 16)
        fg_color = self._level_color()
        fg_pen = QPen(fg_color, self._stroke)
        fg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(fg_pen)
        painter.drawArc(rect, 90 * 16, span_angle)

        # ── Center glow dot at the arc end ──
        if self._value > 0:
            import math
            angle_rad = math.radians(90 - self._value / 100.0 * 360)
            dot_x = cx + radius * math.cos(angle_rad)
            dot_y = cy - radius * math.sin(angle_rad)
            glow = QRadialGradient(dot_x, dot_y, self._stroke * 1.5)
            glow.setColorAt(0, QColor(fg_color.red(), fg_color.green(), fg_color.blue(), 180))
            glow.setColorAt(1, QColor(fg_color.red(), fg_color.green(), fg_color.blue(), 0))
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(dot_x - self._stroke, dot_y - self._stroke,
                                       self._stroke * 2, self._stroke * 2))

        # ── Center text: big number ──
        font_big = QFont(Theme.FONT_FAMILY, 28, QFont.Weight.Bold)
        painter.setFont(font_big)
        painter.setPen(QColor(Theme.TEXT_PRIMARY))
        text = str(self._value)
        r_text = painter.fontMetrics().horizontalAdvance(text)
        painter.drawText(cx - r_text // 2, cy + 10, text)

        # ── Sub label: level name ──
        font_small = QFont(Theme.FONT_FAMILY, 9)
        painter.setFont(font_small)
        level = self._level_label()
        painter.setPen(fg_color)
        r_sub = painter.fontMetrics().horizontalAdvance(level)
        painter.drawText(cx - r_sub // 2, cy + 26, level)

        painter.end()


class MetricMiniCard(QFrame):
    """紧凑型气象指标小卡（用于观星指南面板内嵌）。"""

    def __init__(self, icon: str, label: str, value: str, detail: str = "",
                 color: str = None, parent=None):
        super().__init__(parent)
        color = color or Theme.ACCENT
        self.setObjectName("metricMini")
        self.setStyleSheet(f"""
            QFrame#metricMini {{
                background: {Theme.BG_ELEVATED};
                border: 1px solid {Theme.DIVIDER};
                border-radius: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        top = QHBoxLayout()
        top.setSpacing(6)
        ic = QLabel(icon)
        ic.setStyleSheet(f"color: {color}; background: transparent; font-size: 14px;")
        top.addWidget(ic)
        lb = QLabel(label)
        lb.setFont(Theme.caption())
        lb.setStyleSheet(f"color: {Theme.TEXT_MUTED}; background: transparent;")
        top.addWidget(lb)
        top.addStretch()
        layout.addLayout(top)

        val = QLabel(value)
        val.setFont(Theme.metric())
        val.setStyleSheet(f"color: {Theme.TEXT_HEADING}; background: transparent;")
        layout.addWidget(val)

        if detail:
            dt = QLabel(detail)
            dt.setFont(Theme.tiny())
            dt.setStyleSheet(f"color: {Theme.TEXT_MUTED}; background: transparent;")
            layout.addWidget(dt)
