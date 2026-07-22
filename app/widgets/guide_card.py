"""今晚观星指南面板 — 天文通风格重设计。

布局：
  ┌─ 标题行（标题 + 星级评分 + 建议）
  ├─ 观星指数仪表盘(圆) | 云量小卡 | 视宁度小卡 | 透明度小卡
  └─ 目标卡片横向滚动
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QFrame, QPushButton, QScrollArea, QSizePolicy)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont

from app.theme import Theme
from app.widgets.gauge import StargazingIndexGauge, MetricMiniCard


class GuideCard(QFrame):
    """单个推荐目标卡片 — 玻璃态升级。"""
    goto_signal = Signal(dict)

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self._data = data
        self.setObjectName("guideCard")
        r = Theme.CORNER_RADIUS_MD
        self.setStyleSheet(f"""
            QFrame#guideCard {{
                background: {Theme.BG_CARD};
                border: 1px solid {Theme.CARD_BORDER};
                border-radius: {r}px;
            }}
            QFrame#guideCard:hover {{
                border: 1px solid {Theme.CARD_BORDER_HOVER};
                background: {Theme.BG_ELEVATED};
            }}
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(100)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        name_label = QLabel(data.get("name", ""))
        name_label.setFont(Theme.h3())
        name_label.setStyleSheet(f"color: {Theme.TEXT_PRIMARY}; background: transparent;")
        layout.addWidget(name_label)

        desc_label = QLabel(data.get("description", ""))
        desc_label.setFont(Theme.body())
        desc_label.setStyleSheet(f"color: {Theme.TEXT_SECONDARY}; background: transparent;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        detail_label = QLabel(data.get("detail", ""))
        detail_label.setFont(Theme.caption())
        detail_label.setStyleSheet(f"color: {Theme.TEXT_MUTED}; background: transparent;")
        layout.addWidget(detail_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        goto_btn = QPushButton("🔭 定位到星图")
        goto_btn.setFixedHeight(26)
        goto_btn.setProperty("ghost", True)
        goto_btn.setStyleSheet(Theme.button_ghost_style())
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
        painter.drawRoundedRect(0, 0, 4, rect.height(), 2, 2)
        painter.end()


class GuidePanel(QFrame):
    """今晚观星指南主面板 — 含观星指数仪表盘。"""
    goto_signal = Signal(dict)

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        r = Theme.CORNER_RADIUS_LG
        self.setStyleSheet(f"""
            QFrame#card {{
                background: {Theme.BG_CARD};
                border: 1px solid {Theme.CARD_BORDER};
                border-radius: {r}px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # ═══ 标题行 ═══
        title_row = QHBoxLayout()
        title_row.setSpacing(12)

        title = QLabel("🌟 今晚观星指南")
        title.setFont(Theme.h2())
        title.setStyleSheet(f"color: {Theme.STAR_GOLD}; background: transparent;")
        title_row.addWidget(title)

        rating = data.get("rating", 3)
        rt = QLabel(f"{'★' * rating}{'☆' * (5 - rating)}  {data.get('rating_text', '')}")
        rt.setFont(Theme.font(12, bold=True))
        rt_color = Theme.STAR_GOLD if rating >= 4 else (Theme.WARNING if rating >= 3 else Theme.TEXT_MUTED)
        rt.setStyleSheet(f"color: {rt_color}; background: transparent;")
        title_row.addWidget(rt)

        title_row.addStretch()

        advice = QLabel(data.get("advice", ""))
        advice.setFont(Theme.body())
        advice.setStyleSheet(f"color: {Theme.TEXT_SECONDARY}; background: transparent;")
        advice.setWordWrap(True)
        layout.addWidget(advice)

        # ═══ 观星指数仪表盘 + 气象指标行 ═══
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(12)

        # 左侧：圆形仪表盘
        gauge_value = data.get("stargazing_index", data.get("rating", 3) * 20)
        self.gauge = StargazingIndexGauge(value=gauge_value, size=110, stroke_width=9)
        metrics_row.addWidget(self.gauge)

        # 右侧：气象指标小卡
        conditions = data.get("conditions", {})
        cloud = conditions.get("cloud", {"value": "--", "detail": ""})
        seeing = conditions.get("seeing", {"value": "--", "detail": ""})
        transparency = conditions.get("transparency", {"value": "--", "detail": ""})

        metrics_row.addWidget(MetricMiniCard(
            "☁️", "云量", cloud.get("value", "--"),
            cloud.get("detail", ""), Theme.INFO
        ))
        metrics_row.addWidget(MetricMiniCard(
            "👁️", "视宁度", seeing.get("value", "--"),
            seeing.get("detail", ""), Theme.SUCCESS
        ))
        metrics_row.addWidget(MetricMiniCard(
            "🔭", "透明度", transparency.get("value", "--"),
            transparency.get("detail", ""), Theme.ACCENT_PURPLE
        ))

        metrics_row.addStretch()
        layout.addLayout(metrics_row)

        # ═══ 分割线 ═══
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: {Theme.DIVIDER};")
        layout.addWidget(divider)

        # ═══ 目标卡片横向滚动 ═══
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:horizontal {
                background: transparent; height: 5px;
            }
            QScrollBar::handle:horizontal {
                background: rgba(107,142,255,0.18); border-radius: 2px; min-width: 30px;
            }
            QScrollBar::handle:horizontal:hover {
                background: rgba(107,142,255,0.35);
            }
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal { width: 0; }
        """)

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
        layout.addWidget(scroll, 1)  # stretch to fill remaining space
