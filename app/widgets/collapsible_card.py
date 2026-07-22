"""可折叠卡片组件 — 深空紫蓝玻璃态风格。

圆角 14px、半透明底色 + 微妙发光边框、hover 微光反馈。
箭头在右侧，展开 ▾ / 折叠 ▶（折叠时箭头变强调色）。
内容区为普通 QWidget（无内层 QScrollArea），避免与外层侧栏滚动区嵌套截断。
"""

from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                               QSizePolicy)
from PySide6.QtCore import Qt, Signal

from app.theme import Theme


class _ClickableFrame(QFrame):
    """A QFrame that emits clicked on left mouse press."""
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class CollapsibleCard(QFrame):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        r = Theme.CORNER_RADIUS_MD
        # ── Card body: glass background with subtle glow border ──
        self.setStyleSheet(f"""
            QFrame#card {{
                background: {Theme.BG_CARD};
                border: 1px solid {Theme.CARD_BORDER};
                border-radius: {r}px;
            }}
            QFrame#card:hover {{
                border: 1px solid {Theme.CARD_BORDER_HOVER};
            }}
        """)

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        # ── Header: [title ... spacer ... chevron] ──
        self._header = _ClickableFrame()
        self._header.setFixedHeight(40)          # header 高度
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header.setObjectName("cardHeader")
        self._apply_header_style(expanded=True)
        self._header.clicked.connect(self._toggle)

        hdr_lyt = QHBoxLayout(self._header)
        hdr_lyt.setContentsMargins(12, 0, 8, 0)   # 缩小左右边距适配窄栏
        hdr_lyt.setSpacing(4)

        self._title_label = QLabel(title)
        self._title_label.setFont(Theme.font(12, bold=True))   # 字号缩小
        self._title_label.setStyleSheet(f"color: {Theme.TEXT_PRIMARY}; background: transparent;")
        self._title_label.setWordWrap(True)                     # 允许标题换行防溢出
        hdr_lyt.addWidget(self._title_label)

        hdr_lyt.addStretch()

        self._arrow_label = QLabel("\u25BE")      # ▾
        self._arrow_label.setFont(Theme.font(10))
        self._arrow_label.setStyleSheet(f"color: {Theme.TEXT_MUTED}; background: transparent;")
        self._arrow_label.setFixedWidth(16)
        self._arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hdr_lyt.addWidget(self._arrow_label)

        self._main_layout.addWidget(self._header)

        # ── Content container (plain QWidget — no nested scroll area!) ──
        self._content_widget = QFrame()
        self._content_widget.setStyleSheet("background: transparent; border: none;")
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(12, 8, 12, 10)   # 缩小内边距
        self._content_layout.setSpacing(5)
        self._main_layout.addWidget(self._content_widget, 1)     # stretch=1 让内容撑满

        self._collapsed = False
        self._title = title

    # ── Header style helpers ──

    def _apply_header_style(self, expanded=True):
        r = Theme.CORNER_RADIUS_MD
        if expanded:
            self._header.setStyleSheet(f"""
                QFrame#cardHeader {{
                    background: transparent;
                    border-bottom: 1px solid {Theme.DIVIDER};
                    border-top-left-radius: {r}px;
                    border-top-right-radius: {r}px;
                }}
                QFrame#cardHeader:hover {{
                    background: {Theme.BG_ELEVATED};
                }}
            """)
        else:
            self._header.setStyleSheet(f"""
                QFrame#cardHeader {{
                    background: transparent;
                    border-bottom: none;
                    border-radius: {r}px;
                }}
                QFrame#cardHeader:hover {{
                    background: {Theme.BG_ELEVATED};
                }}
            """)

    # ── Toggle logic ──

    def _toggle(self):
        self._collapsed = not self._collapsed
        if self._collapsed:
            self._arrow_label.setText("\u25B6")   # ▶
            self._arrow_label.setStyleSheet(f"color: {Theme.ACCENT}; background: transparent;")
            self._content_widget.setVisible(False)
            self._apply_header_style(expanded=False)
            self.setFixedHeight(40)               # match header height
        else:
            self._arrow_label.setText("\u25BE")   # ▾
            self._arrow_label.setStyleSheet(f"color: {Theme.TEXT_MUTED}; background: transparent;")
            self._content_widget.setVisible(True)
            self._apply_header_style(expanded=True)
            self.setMinimumHeight(0)
            self.setMaximumHeight(16777215)
            self.setSizePolicy(
                QSizePolicy.Policy.Preferred,
                QSizePolicy.Policy.Preferred,
            )

    # ── Public API (unchanged signature) ──

    def content_layout(self):
        return self._content_layout

    def set_title(self, title):
        self._title = title
        self._title_label.setText(title)

    def collapse(self):
        if not self._collapsed:
            self._toggle()

    def expand(self):
        if self._collapsed:
            self._toggle()
