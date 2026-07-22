"""玻璃态卡片 — 深空紫蓝风格。

半透明底色 + 微妙发光边框 + hover 高亮。
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient

from app.theme import Theme


class GlassCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._hovered = False
        self.setObjectName("glass")
        r = Theme.CORNER_RADIUS_MD
        self.setStyleSheet(f"""
            QFrame#glass {{
                background: {Theme.BG_CARD_GLASS};
                border: 1px solid {Theme.GLASS_BORDER};
                border-radius: {r}px;
            }}
        """)

        self._content_layout = QVBoxLayout(self)
        self._content_layout.setContentsMargins(20, 16, 20, 16)
        self._content_layout.setSpacing(8)

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        radius = Theme.CORNER_RADIUS_MD

        # Background
        bg_color = QColor(19, 27, 56, 170)
        if self._hovered:
            bg_color = QColor(24, 33, 68, 195)

        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, radius, radius)

        # Border glow
        border_alpha = 35 if self._hovered else 20
        border_color = QColor(107, 142, 255, border_alpha)
        border_pen = QPen(border_color, 1)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), radius, radius)

        # Hover top highlight
        if self._hovered:
            highlight = QLinearGradient(0, 0, rect.width(), 0)
            highlight.setColorAt(0, QColor(107, 142, 255, 0))
            highlight.setColorAt(0.5, QColor(107, 142, 255, 18))
            highlight.setColorAt(1, QColor(107, 142, 255, 0))
            painter.setBrush(QBrush(highlight))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, radius, radius)

        painter.end()

    def content_layout(self):
        return self._content_layout

    def set_title(self, title):
        if hasattr(self, '_title_label') and self._title_label:
            self._content_layout.removeWidget(self._title_label)
            self._title_label.deleteLater()
        self._title_label = QLabel(title)
        self._title_label.setFont(Theme.h3())
        self._title_label.setStyleSheet(f"color: {Theme.TEXT_PRIMARY}; background: transparent;")
        self._content_layout.insertWidget(0, self._title_label)
        return self._title_label

    def add_row(self, label_text, value_widget):
        row = QHBoxLayout()
        row.setSpacing(12)
        label = QLabel(label_text)
        label.setFont(Theme.caption())
        label.setStyleSheet(f"color: {Theme.TEXT_MUTED}; background: transparent;")
        label.setFixedWidth(80)
        row.addWidget(label)
        if isinstance(value_widget, QLabel):
            value_widget.setStyleSheet(f"color: {Theme.TEXT_SECONDARY}; font-size: 12px; background: transparent;")
        row.addWidget(value_widget, 1)
        self._content_layout.addLayout(row)
        return row
