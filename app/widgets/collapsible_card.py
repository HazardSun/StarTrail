from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QScrollArea
from PySide6.QtCore import Qt

from app.theme import Theme


class CollapsibleCard(QFrame):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(Theme.card_style())

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        self._header = QPushButton()
        self._header.setFixedHeight(36)
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {Theme.TEXT_PRIMARY};
                border: none; border-bottom: 1px solid {Theme.DIVIDER};
                text-align: left; padding: 0 12px; font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: {Theme.ACCENT};
            }}
        """)
        self._header.clicked.connect(self._toggle)
        self._main_layout.addWidget(self._header)

        self._content = QScrollArea()
        self._content.setWidgetResizable(True)
        self._content.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._content.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._content.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: transparent; width: 4px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {Theme.TEXT_MUTED}; border-radius: 2px; min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        self._content_widget = QFrame()
        self._content_widget.setStyleSheet("background: transparent; border: none;")
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(12, 8, 12, 8)
        self._content_layout.setSpacing(6)
        self._content.setWidget(self._content_widget)
        self._main_layout.addWidget(self._content, 1)

        self._collapsed = False
        self._arrow = "▼"
        self._title = title
        self._update_header()

    def _update_header(self):
        self._header.setText(f"{self._arrow}  {self._title}")

    def _toggle(self):
        self._collapsed = not self._collapsed
        self._arrow = "▶" if self._collapsed else "▼"
        self._update_header()
        self._content.setVisible(not self._collapsed)
        if self._collapsed:
            self.setFixedHeight(36)
        else:
            self.setMinimumHeight(0)
            self.setMaximumHeight(16777215)
            self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

    def content_layout(self):
        return self._content_layout

    def set_title(self, title):
        self._title = title
        self._update_header()

    def collapse(self):
        self._collapsed = True
        self._arrow = "▶"
        self._update_header()
        self._content.setVisible(False)

    def expand(self):
        self._collapsed = False
        self._arrow = "▼"
        self._update_header()
        self._content.setVisible(True)
