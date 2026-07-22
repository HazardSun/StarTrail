from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QFrame, QScrollArea, QPushButton, QComboBox,
                               QLineEdit, QCheckBox)
from PySide6.QtCore import Qt, QTimer, Signal

from app.theme import Theme
from app.config import config
from app.api.location_api import (get_city_names, get_coords, auto_detect_location,
                                   get_location_warning)
from app.widgets.ui_kit import SegmentedControl
from app.api.weather_api import test_key as test_weather_key
from app.api.nasa_api import test_key as test_nasa_key


class SettingsView(QWidget):
    mode_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("view")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(Theme.scroll_style())
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setStyleSheet(f"background: {Theme.BG_PRIMARY};")
        self.main_layout = QVBoxLayout(content)
        self.main_layout.setContentsMargins(28, 24, 28, 24)
        self.main_layout.setSpacing(20)

        scroll.setWidget(content)

        view_layout = QVBoxLayout(self)
        view_layout.setContentsMargins(0, 0, 0, 0)
        view_layout.addWidget(scroll)

        self._build_header()
        self._build_mode_card()
        self._build_location_card()
        self._build_api_card()
        self._build_pro_card()
        self._build_about_card()

        self.main_layout.addStretch()

    def _build_header(self):
        header = QFrame()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        title = QLabel("⚙️ 设置")
        title.setFont(Theme.h1())
        title.setStyleSheet(f"color: {Theme.TEXT_PRIMARY};")

        subtitle = QLabel("自定义观星体验 · 所有设置自动保存")
        subtitle.setFont(Theme.body())
        subtitle.setStyleSheet(f"color: {Theme.TEXT_SECONDARY};")

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        self.main_layout.addWidget(header)

    def _build_mode_card(self):
        card = self._make_card("🧑‍🚀 使用模式")

        modes = [
            ("beginner", "🌟 新手模式", "简洁界面 · 一键观星\n自动获取今日最佳观星时间"),
            ("professional", "🔭 专业模式", "RA/Dec 网格 · DSO 列表\nISS 追踪 · 原始数据展示"),
        ]
        self._mode_seg = SegmentedControl(modes)
        self._mode_seg.set_current(config.mode)
        self._mode_seg.currentChanged.connect(self._on_mode_selected)
        card.content_layout().addWidget(self._mode_seg)

        self.mode_hint = QLabel()
        self.mode_hint.setFont(Theme.caption())
        self.mode_hint.setStyleSheet(f"color: {Theme.ACCENT};")
        card.content_layout().addWidget(self.mode_hint)
        self._update_mode_hint(config.mode)

        self.main_layout.addWidget(card)

    def _build_location_card(self):
        card = self._make_card("📍 观测地点")

        row = QHBoxLayout()
        row.setSpacing(8)

        self.city_combo = QComboBox()
        self.city_combo.setStyleSheet(Theme.combo_style())
        cities = get_city_names()
        self.city_combo.addItems(cities)
        if config.city_name in cities:
            self.city_combo.setCurrentText(config.city_name)
        self.city_combo.currentTextChanged.connect(self._on_city_changed)
        row.addWidget(self.city_combo, 1)

        locate_btn = QPushButton("🌐 自动定位")
        locate_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Theme.ACCENT}; color: white; border: none;
                border-radius: 6px; padding: 8px 16px; font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {Theme.ACCENT_DEEP}; }}
            QPushButton:disabled {{ background: {Theme.BG_CARD}; color: {Theme.TEXT_MUTED}; }}
        """)
        locate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        locate_btn.clicked.connect(lambda: self._auto_locate(locate_btn))
        row.addWidget(locate_btn)

        lbl = QLabel("城市")
        lbl.setFont(Theme.caption())
        lbl.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        lbl.setFixedWidth(60)
        row.insertWidget(0, lbl)

        card.content_layout().addLayout(row)

        self.coord_label = QLabel(f"纬度: {config.latitude}°N  |  经度: {config.longitude}°E")
        self.coord_label.setFont(Theme.caption())
        self.coord_label.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        card.content_layout().addWidget(self.coord_label)

        self.locate_status = QLabel("")
        self.locate_status.setFont(Theme.caption())
        self.locate_status.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        card.content_layout().addWidget(self.locate_status)

        card.content_layout().addSpacing(8)

        light_row = QHBoxLayout()
        light_row.setSpacing(8)

        light_lbl = QLabel("光污染")
        light_lbl.setFont(Theme.caption())
        light_lbl.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        light_lbl.setFixedWidth(60)
        light_row.addWidget(light_lbl)

        self.light_combo = QComboBox()
        self.light_combo.setStyleSheet(Theme.combo_style())
        light_levels = ["暗空区", "乡村", "郊区", "城市"]
        self.light_combo.addItems(light_levels)
        if config.light_pollution in light_levels:
            self.light_combo.setCurrentText(config.light_pollution)
        self.light_combo.currentTextChanged.connect(self._on_light_changed)
        light_row.addWidget(self.light_combo, 1)

        light_desc = QLabel("Bortle 1-2  ·  无光污染")
        light_desc.setFont(Theme.caption())
        light_desc.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        light_row.addWidget(light_desc)
        self._light_desc = light_desc

        card.content_layout().addLayout(light_row)

        self.main_layout.addWidget(card)

    def _auto_locate(self, btn):
        btn.setEnabled(False)
        btn.setText("定位中...")
        self.locate_status.setText("正在通过 IP 获取位置（VPN 下可能不准确）...")
        self.locate_status.setStyleSheet(f"color: {Theme.TEXT_MUTED};")

        QTimer.singleShot(50, lambda: self._do_auto_locate(btn))

    def _do_auto_locate(self, btn):
        from app.core.background_worker import run_in_background

        def _fetch():
            return auto_detect_location()

        def _on_done(result):
            try:
                city, lat, lon = result
                warning = get_location_warning()
                if city:
                    idx = self.city_combo.findText(city)
                    if idx >= 0:
                        self.city_combo.setCurrentIndex(idx)
                    else:
                        # 城市不在内置列表中：以文本回显，避免静默丢弃定位结果
                        self.city_combo.setCurrentText(city)
                    config.city_name = city
                    config.latitude = lat
                    config.longitude = lon
                    config.save()
                    self.city_combo.setCurrentText(config.city_name)
                    self.coord_label.setText(f"纬度: {lat}°N  |  经度: {lon}°E")
                    if warning:
                        self.locate_status.setText(warning)
                        self.locate_status.setStyleSheet(f"color: {Theme.WARNING};")
                    else:
                        self.locate_status.setText(f"已定位到: {config.city_name}")
                        self.locate_status.setStyleSheet(f"color: {Theme.SUCCESS};")
                else:
                    # city 为 None：检测到 VPN/代理，已保留手动位置，仅提示
                    self.locate_status.setText(warning or "已保留手动设置的位置")
                    self.locate_status.setStyleSheet(f"color: {Theme.WARNING};")
                btn.setEnabled(True)
                btn.setText("🌐 自动定位")
            except Exception as ex:
                self.locate_status.setText(f"定位失败: {ex}")
                self.locate_status.setStyleSheet(f"color: {Theme.DANGER};")
                btn.setEnabled(True)
                btn.setText("🌐 自动定位")

        run_in_background(_fetch, on_finished=_on_done, on_error=lambda e: (
            self.locate_status.setText(f"定位失败: {e}"),
            self.locate_status.setStyleSheet(f"color: {Theme.DANGER};"),
            btn.setEnabled(True),
            btn.setText("🌐 自动定位")
        ))

    def _build_api_card(self):
        card = self._make_card("🔑 API 密钥")

        self.nasa_input = QLineEdit()
        self.nasa_input.setStyleSheet(Theme.line_edit_style())
        self.nasa_input.setPlaceholderText("NASA API 密钥（可选，留空使用 DEMO_KEY）")
        self.nasa_input.setText(config.api_keys.get("nasa", ""))
        self.nasa_input.textChanged.connect(lambda v: self._on_key_changed("nasa", v))
        self._add_api_row(card, "NASA", self.nasa_input, self._test_nasa, "nasa_status")

        nasa_hint = QLabel("💡 https://api.nasa.gov 免费注册 · DEMO_KEY 每日限额 30 次")
        nasa_hint.setFont(Theme.caption())
        nasa_hint.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        nasa_hint.setWordWrap(True)
        card.content_layout().addWidget(nasa_hint)

        card.content_layout().addSpacing(8)

        self.weather_input = QLineEdit()
        self.weather_input.setStyleSheet(Theme.line_edit_style())
        self.weather_input.setPlaceholderText("OpenWeatherMap API 密钥（必填才能获取天气）")
        self.weather_input.setText(config.api_keys.get("openweather", ""))
        self.weather_input.textChanged.connect(lambda v: self._on_key_changed("openweather", v))
        self._add_api_row(card, "天气", self.weather_input, self._test_weather, "weather_status")

        weather_hint = QLabel("💡 https://openweathermap.org/api 免费注册 · 观星预报依赖此接口")
        weather_hint.setFont(Theme.caption())
        weather_hint.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        weather_hint.setWordWrap(True)
        card.content_layout().addWidget(weather_hint)

        self.main_layout.addWidget(card)

    def _add_api_row(self, card, label, input_widget, test_fn, status_attr):
        row = QHBoxLayout()
        row.setSpacing(8)

        lbl = QLabel(label)
        lbl.setFont(Theme.caption())
        lbl.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        lbl.setFixedWidth(60)
        row.addWidget(lbl)

        row.addWidget(input_widget, 1)

        test_btn = QPushButton("测试")
        test_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Theme.BG_CARD};
                color: {Theme.TEXT_SECONDARY};
                border: 1px solid {Theme.DIVIDER};
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                border: 1px solid {Theme.ACCENT};
                color: {Theme.ACCENT};
            }}
        """)
        test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        test_btn.clicked.connect(lambda: test_fn(test_btn))
        row.addWidget(test_btn)

        status_label = QLabel("")
        status_label.setFont(Theme.caption())
        status_label.setFixedWidth(120)
        row.addWidget(status_label)
        setattr(self, status_attr, status_label)

        card.content_layout().addLayout(row)

    def _test_nasa(self, btn):
        key = self.nasa_input.text().strip()
        btn.setEnabled(False)
        btn.setText("测试中...")
        self.nasa_status.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        self.nasa_status.setText("")

        QTimer.singleShot(50, lambda: self._do_test_nasa(btn))

    def _do_test_nasa(self, btn):
        from app.core.background_worker import run_in_background
        key = self.nasa_input.text().strip()

        def _compute():
            return test_nasa_key(key)

        def _on_done(res):
            ok, msg = res
            if ok:
                self.nasa_status.setText("✓ 连接成功")
                self.nasa_status.setStyleSheet(f"color: {Theme.SUCCESS};")
            else:
                self.nasa_status.setText(f"✗ {msg[:14]}")
                self.nasa_status.setStyleSheet(f"color: {Theme.DANGER};")
            btn.setEnabled(True)
            btn.setText("测试")

        run_in_background(_compute, on_finished=_on_done, on_error=lambda e: (
            self.nasa_status.setText("✗ 测试失败"),
            self.nasa_status.setStyleSheet(f"color: {Theme.DANGER};"),
            btn.setEnabled(True), btn.setText("测试")
        ))

    def _test_weather(self, btn):
        key = self.weather_input.text().strip()
        if not key:
            self.weather_status.setText("请先输入密钥")
            self.weather_status.setStyleSheet(f"color: {Theme.WARNING};")
            return
        btn.setEnabled(False)
        btn.setText("测试中...")
        self.weather_status.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        self.weather_status.setText("")

        QTimer.singleShot(50, lambda: self._do_test_weather(btn))

    def _do_test_weather(self, btn):
        from app.core.background_worker import run_in_background
        key = self.weather_input.text().strip()

        def _compute():
            return test_weather_key(key)

        def _on_done(res):
            ok, msg = res
            if ok:
                self.weather_status.setText("✓ 连接成功")
                self.weather_status.setStyleSheet(f"color: {Theme.SUCCESS};")
            else:
                self.weather_status.setText(f"✗ {msg[:12]}")
                self.weather_status.setStyleSheet(f"color: {Theme.DANGER};")
            btn.setEnabled(True)
            btn.setText("测试")

        run_in_background(_compute, on_finished=_on_done, on_error=lambda e: (
            self.weather_status.setText("✗ 测试失败"),
            self.weather_status.setStyleSheet(f"color: {Theme.DANGER};"),
            btn.setEnabled(True), btn.setText("测试")
        ))

    def _build_pro_card(self):
        self.pro_card = self._make_card("🔬 专业模式设置")

        self.show_grid = QCheckBox("显示 RA/Dec 坐标网格")
        self.show_grid.setFont(Theme.body())
        self.show_grid.setStyleSheet(f"color: {Theme.TEXT_PRIMARY};")
        self.show_grid.setChecked(config.pro_settings.get("show_ra_dec_grid", True))
        self.show_grid.toggled.connect(lambda v: self._on_pro_setting("show_ra_dec_grid", v))
        self.pro_card.content_layout().addWidget(self.show_grid)

        self.show_dso = QCheckBox("显示深空天体 (DSO) 标记")
        self.show_dso.setFont(Theme.body())
        self.show_dso.setStyleSheet(f"color: {Theme.TEXT_PRIMARY};")
        self.show_dso.setChecked(config.pro_settings.get("show_dso", True))
        self.show_dso.toggled.connect(lambda v: self._on_pro_setting("show_dso", v))
        self.pro_card.content_layout().addWidget(self.show_dso)

        self.auto_refresh = QCheckBox("自动刷新数据")
        self.auto_refresh.setFont(Theme.body())
        self.auto_refresh.setStyleSheet(f"color: {Theme.TEXT_PRIMARY};")
        self.auto_refresh.setChecked(config.pro_settings.get("auto_refresh", False))
        self.auto_refresh.toggled.connect(lambda v: self._on_pro_setting("auto_refresh", v))
        self.pro_card.content_layout().addWidget(self.auto_refresh)

        self.main_layout.addWidget(self.pro_card)
        self.pro_card.setVisible(config.is_pro)

    def _build_about_card(self):
        card = self._make_card("ℹ️ 关于星迹")

        about = (
            "星迹 StarTrail v1.0.2\n\n"
            "基于 Skyfield 天文计算引擎的桌面观星工具\n"
            "调用开放 API 获取实时天文与天气数据\n\n"
            "核心技术:\n"
            "  • Skyfield — 精准天文计算\n"
            "  • NASA Open APIs — 天文图库\n"
            "  • OpenWeatherMap — 气象数据\n"
            "  • ip-api.com — 自动定位\n\n"
            "数据来源:\n"
            "  • Hipparcos 星表 (亮星数据)\n"
            "  • JPL DE421 行星历表\n"
            "  • 内置深空天体目录\n\n"
            "操作提示:\n"
            "  • 新手模式: 简化界面，一键观星\n"
            "  • 专业模式: 完整天文参数与自定义\n"
            "  • 双击星空图刷新\n"
            "  • 配置 API 密钥解锁全部功能"
        )
        about_label = QLabel(about)
        about_label.setFont(Theme.body())
        about_label.setStyleSheet(f"color: {Theme.TEXT_MUTED}; line-height: 1.6;")
        about_label.setWordWrap(True)
        card.content_layout().addWidget(about_label)

        self.main_layout.addWidget(card)

    def _make_card(self, title):
        from app.widgets.glass_card import GlassCard
        card = GlassCard()
        card.set_title(title)
        return card

    def _on_city_changed(self, city):
        lat, lon = get_coords(city)
        config.city_name = city
        config.latitude = lat
        config.longitude = lon
        config.save()
        self.coord_label.setText(f"纬度: {lat}°N  |  经度: {lon}°E")

    def _on_light_changed(self, level):
        config.light_pollution = level
        config.save()
        descs = {
            "暗空区": "Bortle 1-2  ·  无光污染",
            "乡村": "Bortle 3-4  ·  轻微光污染",
            "郊区": "Bortle 5-6  ·  中等光污染",
            "城市": "Bortle 7-9  ·  严重光污染",
        }
        self._light_desc.setText(descs.get(level, ""))

    def _on_key_changed(self, key, value):
        config.api_keys[key] = value.strip()
        config.save()

    def _on_pro_setting(self, key, value):
        config.pro_settings[key] = value
        config.save()

    def on_show(self):
        self.pro_card.setVisible(config.is_pro)

    def on_mode_changed(self, mode):
        self.pro_card.setVisible(mode == "professional")
        self._update_mode_display(mode)

    def _on_mode_selected(self, mode):
        if mode == config.mode:
            return
        config.mode = mode
        config.save()
        self._update_mode_hint(mode)
        self.mode_changed.emit(mode)

    def _update_mode_display(self, mode):
        self._mode_seg.set_current(mode)
        self._update_mode_hint(mode)

    def _update_mode_hint(self, mode):
        self.mode_hint.setText(
            f"当前: {'🔭 专业模式' if mode == 'professional' else '🌟 新手模式'}"
        )
