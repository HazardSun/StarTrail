import math

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QFrame, QSizePolicy
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont

from app.theme import Theme


class LoadingOverlay(QWidget):
    def __init__(self, parent=None, text="加载中..."):
        super().__init__(parent)
        self._text = text
        self._angle = 0
        self.setVisible(False)

        if parent:
            self.setGeometry(parent.rect())

        self._timer = QTimer()
        self._timer.timeout.connect(self._rotate)
        self._timer.setSingleShot(False)

    def _rotate(self):
        self._angle = (self._angle + 6) % 360
        if self.isVisible():
            self.update()

    def show(self, text=None):
        if text:
            self._text = text
        if self.parent():
            self.setGeometry(self.parent().rect())
        super().show()
        self.raise_()
        self._timer.start()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QColor(11, 14, 26, 200))

        cx, cy = self.width() / 2, self.height() / 2 - 30
        r = 20

        painter.setPen(Qt.PenStyle.NoPen)
        for i in range(12):
            a = self._angle + i * 30
            alpha = 40 + (i * 18) % 180
            painter.setBrush(QBrush(QColor(Theme.ACCENT, alpha)))
            painter.drawEllipse(QRectF(
                cx + r * 0.8 * math.cos(math.radians(a)) - 3,
                cy + r * 0.8 * math.sin(math.radians(a)) - 3,
                6, 6
            ))

        painter.setFont(Theme.font(14, bold=True))
        painter.setPen(QPen(QColor(Theme.TEXT_PRIMARY, 200)))
        painter.drawText(QRectF(0, cy + 40, self.width(), 30),
                         Qt.AlignmentFlag.AlignCenter, self._text)

        painter.end()

    def hide(self):
        self._timer.stop()
        super().hide()
