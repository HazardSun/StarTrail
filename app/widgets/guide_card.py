from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QFrame, QPushButton, QScrollArea, QSizePolicy)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont

from app.theme import Theme


class GuideCard(QFrame):
    goto_signal = Signal(dict)

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self._data = data
        self.setObjectName("card")
        self.setStyleSheet(Theme.card_style())
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(110)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        name_label = QLabel(data.get("name", ""))
        name_label.setFont(Theme.font(14, bold=True))
        name_label.setStyleSheet(f"color: {Theme.TEXT_PRIMARY};")
        layout.addWidget(name_label)

        desc_label = QLabel(data.get("description", ""))
        desc_label.setFont(Theme.body())
        desc_label.setStyleSheet(f"color: {Theme.TEXT_SECONDARY};")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        detail_label = QLabel(data.get("detail", ""))
        detail_label.setFont(Theme.caption())
        detail_label.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        layout.addWidget(detail_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        goto_btn = QPushButton("🔭 定位到星图")
        goto_btn.setFixedHeight(26)
        goto_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Theme.ACCENT}; color: white; border: none;
                border-radius: 6px; padding: 4px 14px; font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {Theme.ACCENT_DEEP}; }}
        """)
        goto_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        goto_btn.clicked.connect(self._goto)
        btn_row.addWidget(goto_btn)

        layout.addLayout(btn_row)

    def _goto(self):
        self.goto_signal.emit(self._data)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        accent_color = {
            "moon": Theme.STAR_GOLD,
            "planet": Theme.ACCENT,
            "star": Theme.STAR_WARM,
        }.get(self._data.get("type", ""), Theme.ACCENT)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(accent_color)))
        painter.drawRoundedRect(0, 0, 5, rect.height(), 3, 3)
        painter.end()


class GuidePanel(QFrame):
    goto_signal = Signal(dict)

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(Theme.card_style())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        title_row = QHBoxLayout()
        title = QLabel("🌟 今晚观星指南")
        title.setFont(Theme.h2())
        title.setStyleSheet(f"color: {Theme.STAR_GOLD};")
        title_row.addWidget(title)
        title_row.addStretch()

        rating = data.get("rating", 3)
        rt = QLabel(f"{'★' * rating}{'☆' * (5 - rating)}  {data.get('rating_text', '')}")
        rt.setFont(Theme.font(12, bold=True))
        rt.setStyleSheet(f"color: {Theme.STAR_GOLD if rating >= 4 else Theme.WARNING if rating >= 3 else Theme.TEXT_MUTED};")
        title_row.addWidget(rt)
        layout.addLayout(title_row)

        advice = QLabel(data.get("advice", ""))
        advice.setFont(Theme.caption())
        advice.setStyleSheet(f"color: {Theme.TEXT_SECONDARY};")
        layout.addWidget(advice)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        cards_widget = QWidget()
        cards_widget.setStyleSheet("background: transparent;")
        cards_layout = QHBoxLayout(cards_widget)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(10)

        for t in data.get("targets", []):
            card = GuideCard(t)
            card.goto_signal.connect(lambda d: self.goto_signal.emit(d))
            cards_layout.addWidget(card)

        scroll.setWidget(cards_widget)
        layout.addWidget(scroll)
