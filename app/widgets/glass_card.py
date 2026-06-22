from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient

from app.theme import Theme


class GlassCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._hovered = False
        self.setObjectName("glass")
        self.setStyleSheet(f"""
            QFrame#glass {{
                background: rgba(21, 27, 53, 0.75);
                border: 1px solid rgba(108, 140, 255, 0.12);
                border-radius: {Theme.CORNER_RADIUS_MD}px;
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

        bg_color = QColor(21, 27, 53, 180)
        if self._hovered:
            bg_color = QColor(26, 33, 64, 200)

        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, radius, radius)

        border_color = QColor(108, 140, 255, 30)
        border_pen = QPen(border_color, 1)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), radius, radius)

        if self._hovered:
            highlight = QLinearGradient(0, 0, rect.width(), 0)
            highlight.setColorAt(0, QColor(108, 140, 255, 0))
            highlight.setColorAt(0.5, QColor(108, 140, 255, 20))
            highlight.setColorAt(1, QColor(108, 140, 255, 0))
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
        self._title_label.setStyleSheet(f"color: {Theme.TEXT_PRIMARY};")
        self._content_layout.insertWidget(0, self._title_label)
        return self._title_label

    def add_row(self, label_text, value_widget):
        row = QHBoxLayout()
        row.setSpacing(12)
        label = QLabel(label_text)
        label.setFont(Theme.caption())
        label.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        label.setFixedWidth(80)
        row.addWidget(label)
        if isinstance(value_widget, QLabel):
            value_widget.setStyleSheet(f"color: {Theme.TEXT_SECONDARY}; font-size: 12px;")
        row.addWidget(value_widget, 1)
        self._content_layout.addLayout(row)
        return row
