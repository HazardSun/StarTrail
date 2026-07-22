import traceback

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QStackedWidget, QLabel, QFrame, QSizePolicy,
                               QButtonGroup, QScrollArea)
from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import QCursor, QPainter, QColor, QPen

from app.theme import Theme
from app.config import config
from app.widgets.loading_overlay import LoadingOverlay
from app.widgets.hud_panel import HudPanel
from app.api.system_monitor import set_star_chart_ref
from app.views.sky_view import SkyView
from app.views.forecast_view import ForecastView
from app.views.calendar_view import CalendarView
from app.views.settings_view import SettingsView


NAV_ITEMS = [
    ("sky", "🌌", "实时星空"),
    ("forecast", "🔭", "观星预报"),
    ("calendar", "📅", "天文日历"),
    ("settings", "⚙️", "设置"),
]

VIEW_CLASSES = {
    "sky": SkyView,
    "forecast": ForecastView,
    "calendar": CalendarView,
    "settings": SettingsView,
}


class NavButton(QPushButton):
    def __init__(self, icon, text, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setText(f"{icon}  {text}")
        self.setObjectName("navBtn")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(44)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


class ModeToggle(QFrame):
    mode_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self.setStyleSheet(f"""
            ModeToggle {{
                background: {Theme.BG_CARD};
                border: 1px solid {Theme.DIVIDER};
                border-radius: 8px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        self._beginner_btn = QPushButton("🌙  新手")
        self._beginner_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._beginner_btn.setFixedHeight(32)

        self._pro_btn = QPushButton("☀️  专业")
        self._pro_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pro_btn.setFixedHeight(32)

        self._group = QButtonGroup()
        self._group.addButton(self._beginner_btn, 0)
        self._group.addButton(self._pro_btn, 1)
        self._group.setExclusive(True)
        self._group.idClicked.connect(self._on_clicked)

        layout.addWidget(self._beginner_btn, 1)
        layout.addWidget(self._pro_btn, 1)

        self._update_display()

    def _on_clicked(self, btn_id):
        new = "professional" if btn_id == 1 else "beginner"
        if new == config.mode:
            return
        config.mode = new
        config.save()
        self._update_display()
        self.mode_changed.emit(new)

    def _update_display(self):
        is_pro = config.mode == "professional"
        self._beginner_btn.setChecked(not is_pro)
        self._pro_btn.setChecked(is_pro)
        self._beginner_btn.setStyleSheet(self._btn_style(not is_pro))
        self._pro_btn.setStyleSheet(self._btn_style(is_pro))

    def _btn_style(self, active):
        if active:
            return f"""
                QPushButton {{
                    background: {Theme.ACCENT};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: {Theme.ACCENT_DEEP};
                }}
            """
        return f"""
            QPushButton {{
                background: transparent;
                color: {Theme.TEXT_MUTED};
                border: none;
                border-radius: 6px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {Theme.ACCENT_DIM};
                color: {Theme.TEXT_SECONDARY};
            }}
        """


class SidebarResizer(QFrame):
    """可拖拽的侧边栏宽度调节手柄。鼠标按下后左右拖动改变侧边栏宽度。"""
    width_changed = Signal(int)        # 自拖拽起点的累计水平位移（像素）
    drag_started = Signal()            # 拖拽开始
    drag_finished = Signal()           # 拖拽结束（松手）

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(5)
        self.setCursor(Qt.CursorShape.SplitHCursor)
        self._dragging = False
        self._start_x = 0
        self.setStyleSheet(f"background: transparent;")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor(Theme.ACCENT)
        c.setAlpha(60 if not self._dragging else 200)
        pen = QPen(c, 2)
        p.setPen(pen)
        cx = self.width() // 2
        p.drawLine(cx, 4, cx, self.height() - 4)

        # 拖动时画手柄圆点
        if self._dragging:
            c.setAlpha(180)
            p.setBrush(c)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(cx - 3, self.height() // 2 - 6, 6, 12)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._start_x = event.globalPosition().x()
            self.update()
            self.drag_started.emit()

    def mouseMoveEvent(self, event):
        if self._dragging:
            dx = int(event.globalPosition().x() - self._start_x)
            self.width_changed.emit(dx)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            self.update()
            self.drag_finished.emit()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("星迹 StarTrail")
        self.setMinimumSize(1100, 720)
        self.resize(1280, 800)
        self.setStyleSheet(f"background: {Theme.BG_PRIMARY};")

        self._views = {}
        self._current_key = "sky"

        self._setup_ui()
        self.loading = LoadingOverlay(self.content, "星迹加载中...")
        QTimer.singleShot(50, self._lazy_init)

    def _lazy_init(self):
        self._on_mode_changed(config.mode)
        sky = self._views.get("sky")
        if sky and hasattr(sky, "on_show"):
            sky.on_show()
        QTimer.singleShot(600, self.loading.hide)

    def _get_or_create_view(self, key):
        if key in self._views:
            return self._views[key]
        cls = VIEW_CLASSES.get(key)
        if not cls:
            return None
        view = cls()
        view.setStyleSheet(f"QWidget#view {{ background: {Theme.BG_PRIMARY}; }}")
        self._views[key] = view
        self.stacked.addWidget(view)
        if key == "settings" and hasattr(view, "mode_changed"):
            view.mode_changed.connect(self._on_mode_changed)
        if hasattr(view, "on_mode_changed"):
            try:
                view.on_mode_changed(config.mode)
            except Exception:
                pass
        return view

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._sidebar_width = config.pro_settings.get("sidebar_width", 240)
        self._min_sidebar = 180
        self._max_sidebar = 450
        self._resize_anchor = self._sidebar_width

        self._create_sidebar()
        layout.addWidget(self.sidebar)

        # ── 可拖拽宽度调节手柄（替代静态 divider）──
        self._resizer = SidebarResizer()
        self._resizer.drag_started.connect(self._on_resize_start)
        self._resizer.width_changed.connect(self._on_resize_drag)
        self._resizer.drag_finished.connect(self._on_resize_release)
        layout.addWidget(self._resizer)

        self._create_content()
        layout.addWidget(self.content, 1)

    def _create_sidebar(self):
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setMinimumWidth(self._min_sidebar)
        self.sidebar.setMaximumWidth(self._max_sidebar)
        self.sidebar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.sidebar.setFixedWidth(self._sidebar_width)
        self.sidebar.setStyleSheet(f"""
            QWidget#sidebar {{
                background: {Theme.BG_SIDEBAR};
                border-right: 1px solid {Theme.DIVIDER};
            }}
        """)

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 24, 12, 20)
        sidebar_layout.setSpacing(2)

        logo = QLabel("✨ 星迹")
        logo.setFont(Theme.font(18, bold=True))
        logo.setStyleSheet(f"color: {Theme.TEXT_PRIMARY}; padding: 0 10px 16px;")
        sidebar_layout.addWidget(logo)

        self.mode_toggle = ModeToggle()
        self.mode_toggle.mode_changed.connect(self._on_mode_changed)
        sidebar_layout.addWidget(self.mode_toggle)

        sidebar_layout.addSpacing(8)

        self.nav_buttons = {}
        for key, icon, text in NAV_ITEMS:
            btn = NavButton(icon, text)
            btn.clicked.connect(lambda checked, k=key: self._switch_view(k))
            self.nav_buttons[key] = btn
            sidebar_layout.addWidget(btn)

        # ── Section divider: nav vs tracking panels ──
        section_div = QFrame()
        section_div.setFixedHeight(1)
        section_div.setStyleSheet(f"background: {Theme.DIVIDER}; margin: 8px 8px 0;")
        sidebar_layout.addWidget(section_div)

        # ── Scrollable tracking panel (single scroll for all cards) ──
        self._sidebar_scroll = QScrollArea()
        self._sidebar_scroll.setWidgetResizable(True)
        self._sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._sidebar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._sidebar_scroll.setStyleSheet(Theme.scroll_style())
        self._sidebar_scroll.setVisible(False)

        self.sidebar_panel = QWidget()
        self.sidebar_panel.setObjectName("sidebarPanel")
        self.sidebar_panel_layout = QVBoxLayout(self.sidebar_panel)
        self.sidebar_panel_layout.setContentsMargins(4, 6, 4, 4)
        self.sidebar_panel_layout.setSpacing(6)
        self._sidebar_scroll.setWidget(self.sidebar_panel)

        sidebar_layout.addWidget(self._sidebar_scroll, 1)

        version = QLabel("v1.0.2")
        version.setFont(Theme.caption())
        version.setStyleSheet(f"color: {Theme.TEXT_MUTED}; padding: 8px;")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(version)

        self.nav_buttons["sky"].setChecked(True)

    def _create_content(self):
        self.content = QWidget()
        self.content.setStyleSheet(f"background: {Theme.BG_PRIMARY};")
        self.content.resizeEvent = lambda e: self._on_content_resize(e.size().width(), e.size().height())

        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.stacked = QStackedWidget()

        sky = SkyView(sidebar_panel=self.sidebar_panel_layout)
        sky.setStyleSheet(f"QWidget#view {{ background: {Theme.BG_PRIMARY}; }}")
        self._views["sky"] = sky
        self.stacked.addWidget(sky)

        content_layout.addWidget(self.stacked)

        self._hud = HudPanel(self.content)
        self._hud.setVisible(False)
        from app.api.system_monitor import set_star_chart_ref
        set_star_chart_ref(sky.star_chart)

    def _on_content_resize(self, w, h):
        if hasattr(self, '_hud'):
            self._hud.setFixedSize(min(280, w - 20), self._hud.sizeHint().height())
            self._hud.move(w - self._hud.width() - 6, h - self._hud.height() - 6)

    def _on_resize_start(self):
        # 记录拖拽起点时的侧边栏宽度作为锚点，后续按「锚点 + 累计位移」计算，避免重复累加
        self._resize_anchor = self._sidebar_width

    def _on_resize_drag(self, dx):
        new_w = max(self._min_sidebar, min(self._max_sidebar, self._resize_anchor + dx))
        if new_w != self._sidebar_width:
            self._sidebar_width = new_w
            self.sidebar.setFixedWidth(new_w)
            config.pro_settings["sidebar_width"] = new_w

    def _on_resize_release(self):
        # 松手后持久化宽度，重启后保持
        try:
            config.save()
        except Exception:
            pass

    def _switch_view(self, key):
        if key == self._current_key:
            return
        self._current_key = key

        for k, btn in self.nav_buttons.items():
            btn.setChecked(k == key)

        view = self._get_or_create_view(key)
        if view is None:
            return

        is_cached = key in self._views
        self.stacked.setCurrentWidget(view)
        if is_cached:
            try:
                if hasattr(view, "on_show"):
                    view.on_show()
            except Exception:
                pass
        else:
            self.loading.show("加载中...")
            QTimer.singleShot(0, lambda v=view: self._finish_switch(v))

    def _finish_switch(self, view):
        try:
            if hasattr(view, "on_show"):
                view.on_show()
        except Exception:
            traceback.print_exc()
        self.loading.hide()

    def _on_mode_changed(self, mode):
        is_pro = mode == "professional"
        self._sidebar_scroll.setVisible(is_pro)
        if hasattr(self, 'mode_toggle'):
            self.mode_toggle._update_display()
        if hasattr(self, '_hud'):
            self._hud.setVisible(is_pro)
            if is_pro:
                self._on_content_resize(self.content.width(), self.content.height())
                self._hud.raise_()
        for view in self._views.values():
            if hasattr(view, "on_mode_changed"):
                try:
                    view.on_mode_changed(mode)
                except Exception:
                    traceback.print_exc()
