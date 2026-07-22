"""可复用的轻量 UI 组件（深空紫蓝玻璃态风格）。

提供统一的评分条、状态胶囊、分段控件等，保证全局视觉一致、
层级清晰，并自带正确的自适应宽度。
"""

from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                               QFrame, QPushButton, QButtonGroup)
from PySide6.QtCore import Qt, Signal

from app.theme import Theme


class MetricBar(QWidget):
    """0-100 的横向评分条，圆角胶囊形，自动随父容器宽度缩放。"""

    def __init__(self, value: int = 0, color: str = None, height: int = 6, parent=None):
        super().__init__(parent)
        self._value = max(0, min(100, int(value)))
        self._color = color or Theme.ACCENT
        self._height = max(4, height)
        self._build()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.bg = QFrame()
        self.bg.setFixedHeight(self._height)
        r = self._height // 2
        self.bg.setStyleSheet(
            f"background: rgba(255,255,255,0.06); border-radius: {r}px;"
        )
        self.fill = QFrame(self.bg)
        self.fill.setFixedHeight(self._height)
        self.fill.setFixedWidth(0)
        self._paint_fill()
        layout.addWidget(self.bg, 1)

    def _paint_fill(self):
        r = self._height // 2
        self.fill.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {self._color}, stop:1 {Theme._lighten(self._color, 20)});"
            f"border-radius: {r}px;"
        )

    def setValue(self, value: int):
        self._value = max(0, min(100, int(value)))
        self._apply_width()

    def setColor(self, color: str):
        self._color = color
        self._paint_fill()

    def _apply_width(self):
        w = self.bg.width()
        if w > 0:
            self.fill.setFixedWidth(int(w * self._value / 100.0))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_width()


class StatusPill(QFrame):
    """圆角状态药丸标签（半透明底 + 彩色边框 + 彩色字）。"""

    def __init__(self, text: str = "", color: str = None, parent=None):
        super().__init__(parent)
        self.setObjectName("pill")
        self._color = color or Theme.ACCENT
        self._label = QLabel(text)
        self._label.setFont(Theme.caption())
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(4)
        layout.addStretch()
        layout.addWidget(self._label)
        layout.addStretch()
        self._apply()

    def _apply(self):
        c = self._color
        self.setStyleSheet(
            f"QFrame#pill {{"
            f"  background: rgba(255,255,255,0.03);"
            f"  border: 1px solid {c}33;"          # 20% opacity border
            f"  border-radius: 12px;"
            f"}}"
        )
        self._label.setStyleSheet(f"color: {c}; background: transparent;")

    def setText(self, text: str):
        self._label.setText(text)

    def setColor(self, color: str):
        self._color = color
        self._apply()


class SegmentedControl(QFrame):
    """分段选择器（如 新手/专业 切换），玻璃态卡片风格。"""

    currentChanged = Signal(str)

    def __init__(self, options, parent=None):
        super().__init__(parent)
        self.setObjectName("segmented")
        self._options = options  # list of (key, title, desc)
        self._buttons = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._group.idClicked.connect(self._on_click)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)
        for idx, (key, title, desc) in enumerate(options):
            btn = self._make_button(key, title, desc)
            self._group.addButton(btn, idx)
            layout.addWidget(btn, 1)
            self._buttons[key] = btn

    def _make_button(self, key, title, desc):
        btn = QPushButton()
        btn.setObjectName("segBtn")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setText("")
        btn.setMinimumHeight(64)
        fl = QVBoxLayout(btn)
        fl.setContentsMargins(16, 12, 16, 12)
        fl.setSpacing(4)
        tl = QLabel(title)
        tl.setFont(Theme.h3())
        tl.setStyleSheet(f"color: {Theme.TEXT_PRIMARY}; background: transparent;")
        dl = QLabel(desc)
        dl.setFont(Theme.caption())
        dl.setWordWrap(True)
        dl.setStyleSheet(f"color: {Theme.TEXT_MUTED}; background: transparent;")
        fl.addWidget(tl)
        fl.addWidget(dl)
        btn._key = key
        return btn

    def _on_click(self, idx):
        key = self._options[idx][0]
        self.set_current(key)
        self.currentChanged.emit(key)

    def set_current(self, key):
        for k, btn in self._buttons.items():
            active = (k == key)
            if active:
                btn.setStyleSheet(
                    f"QPushButton#segBtn {{"
                    f"  background: {Theme.BG_ELEVATED};"
                    f"  border: 1.5px solid {Theme.ACCENT};"
                    f"  border-radius: 12px;"
                    f"}}"
                )
            else:
                btn.setStyleSheet(
                    f"QPushButton#segBtn {{"
                    f"  background: transparent;"
                    f"  border: 1px solid {Theme.DIVIDER};"
                    f"  border-radius: 12px;"
                    f"}}"
                )
            tl = btn.layout().itemAt(0).widget()
            dl = btn.layout().itemAt(1).widget()
            tl.setStyleSheet(
                f"color: {Theme.TEXT_HEADING if active else Theme.TEXT_SECONDARY}; "
                f"background: transparent;"
            )
            dl.setStyleSheet(
                f"color: {Theme.TEXT_SECONDARY if active else Theme.TEXT_MUTED}; "
                f"background: transparent;"
            )
        for k, btn in self._buttons.items():
            btn.setChecked(k == key)

    _color = Theme.ACCENT


# ── 工具函数 ───────────────────────────────

def _lighten(hex_color: str, amount: int = 20) -> str:
    """将 hex 颜色提亮 amount (0-255)。"""
    from PySide6.QtGui import QColor
    c = QColor(hex_color)
    r = min(255, c.red() + amount)
    g = min(255, c.green() + amount)
    b = min(255, c.blue() + amount)
    return f"rgb({r},{g},{b})"


# 挂到 Theme 上方便全局使用
Theme._lighten = staticmethod(_lighten)
