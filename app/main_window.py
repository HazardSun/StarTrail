import traceback

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QStackedWidget, QLabel, QFrame, QSizePolicy,
                               QButtonGroup)
from PySide6.QtCore import Qt, Signal, QTimer

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

        self._create_sidebar()
        layout.addWidget(self.sidebar)

        divider = QFrame()
        divider.setFixedWidth(1)
        divider.setStyleSheet(f"background: {Theme.DIVIDER};")
        layout.addWidget(divider)

        self._create_content()
        layout.addWidget(self.content, 1)

    def _create_sidebar(self):
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(200)
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

        self.sidebar_panel = QWidget()
        self.sidebar_panel.setObjectName("sidebarPanel")
        self.sidebar_panel.setVisible(False)
        self.sidebar_panel_layout = QVBoxLayout(self.sidebar_panel)
        self.sidebar_panel_layout.setContentsMargins(0, 4, 0, 0)
        self.sidebar_panel_layout.setSpacing(4)
        sidebar_layout.addWidget(self.sidebar_panel, 1)

        version = QLabel("v1.0.1")
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
        self.sidebar_panel.setVisible(is_pro)
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
