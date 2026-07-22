import math

from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath

from app.theme import Theme

COLOR_MAP = {
    "success": "#4CAF50",
    "warning": "#FFA726",
    "danger": "#EF5350",
}


class SeeingChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []
        self.setMinimumHeight(80)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    def set_data(self, hourly_data):
        self._data = hourly_data if hourly_data else []
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        if w < 20 or h < 20 or not self._data:
            painter.end()
            return

        margin_l, margin_r, margin_t, margin_b = 20, 8, 12, 18
        chart_w = w - margin_l - margin_r
        chart_h = h - margin_t - margin_b
        n = len(self._data)

        seeing_vals = [d["seeing"] for d in self._data]
        y_min = max(0, min(seeing_vals) - 0.3)
        y_max = max(seeing_vals) + 0.3
        y_range = max(y_max - y_min, 0.5)

        def to_screen(idx, val):
            x = margin_l + chart_w * idx / (n - 1) if n > 1 else margin_l + chart_w / 2
            y = margin_t + chart_h * (1 - (val - y_min) / y_range)
            return QPointF(x, y)

        points = [to_screen(i, v) for i, v in enumerate(seeing_vals)]

        chart_rect = QRectF(margin_l, margin_t, chart_w, chart_h)

        # fill background
        painter.fillRect(chart_rect, Theme.qcolor(Theme.BG_CARD))

        # draw horizontal reference lines
        for val in [1.0, 2.0, 3.0]:
            py = margin_t + chart_h * (1 - (val - y_min) / y_range)
            painter.setPen(QPen(Theme.qcolor(Theme.DIVIDER), 0.5, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(margin_l, py), QPointF(w - margin_r, py))

        # fill gradient under curve
        if len(points) > 1:
            path = QPainterPath()
            path.moveTo(points[0].x(), margin_t + chart_h)
            for p in points:
                path.lineTo(p)
            path.lineTo(points[-1].x(), margin_t + chart_h)
            path.closeSubpath()
            grad = painter.pen().color()  # placeholder
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(Theme.qcolor(Theme.ACCENT_DIM)))
            painter.drawPath(path)

        # draw line
        painter.setPen(QPen(QColor(Theme.ACCENT), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(1, len(points)):
            painter.drawLine(points[i - 1], points[i])

        # draw dots
        for i, p in enumerate(points):
            color = COLOR_MAP.get(self._data[i].get("color", ""), Theme.ACCENT)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(color)))
            painter.drawEllipse(p, 3, 3)

        # x-axis labels
        painter.setFont(Theme.font(8))
        for i, d in enumerate(self._data):
            x = margin_l + chart_w * i / (n - 1) if n > 1 else margin_l + chart_w / 2
            painter.setPen(QPen(QColor(Theme.TEXT_MUTED)))
            fm = painter.fontMetrics()
            label = d["hour"]
            tw = fm.horizontalAdvance(label)
            painter.drawText(int(x - tw / 2), int(h - 4), label)

        # y-axis label
        painter.setPen(QPen(QColor(Theme.TEXT_MUTED)))
        painter.setFont(Theme.font(7))
        painter.drawText(QRectF(0, margin_t, margin_l - 2, chart_h),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                         "mag")

        # "better" / "worse" indicators
        painter.setPen(QPen(QColor(Theme.TEXT_MUTED)))
        painter.setFont(Theme.font(7))
        painter.drawText(QRectF(0, margin_t - 2, margin_l - 2, 10),
                         Qt.AlignmentFlag.AlignRight, "优")
        painter.drawText(QRectF(0, margin_t + chart_h - 10, margin_l - 2, 10),
                         Qt.AlignmentFlag.AlignRight, "差")

        # threshold zones (colored bands)
        for val_low, val_high, color_key in [(0, 1.2, "success"), (1.2, 2.0, "warning"), (2.0, 5.0, "danger")]:
            y_low = margin_t + chart_h * (1 - (val_low - y_min) / y_range)
            y_high = margin_t + chart_h * (1 - (val_high - y_min) / y_range)
            if y_low < margin_t: y_low = margin_t
            if y_high > margin_t + chart_h: y_high = margin_t + chart_h
            if y_low >= y_high:
                continue
            rect = QRectF(margin_l, y_low, chart_w, y_high - y_low)
            c = QColor(COLOR_MAP.get(color_key, Theme.ACCENT))
            c.setAlpha(12)
            painter.fillRect(rect, c)

        painter.end()
