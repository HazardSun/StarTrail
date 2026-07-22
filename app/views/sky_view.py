from datetime import datetime

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QFrame, QPushButton, QButtonGroup, QSizePolicy,
                               QCheckBox, QSpinBox)
from PySide6.QtCore import Qt, QTimer, QPointF

from app.theme import Theme
from app.config import config
from app.widgets.star_chart import StarChart
from app.widgets.glass_card import GlassCard
from app.widgets.camera_sim import CameraPanel
from app.api.adsb_api import fetch_aircraft
from app.widgets.collapsible_card import CollapsibleCard
from app.widgets.guide_card import GuidePanel
from app.api.astronomy_api import sky, DEVICE_CONFIGS, get_tonight_guide
from app.widgets.seeing_chart import SeeingChart
from app.widgets.ui_kit import StatusPill


class DeviceButton(QPushButton):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._dev_config = config
        self.setCheckable(True)
        self.setText(f"{config['icon']}  {config['name']}")
        self.setToolTip(f"星等上限: {config['mag_limit']} · {config['desc']}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(32)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.setSizePolicy(sizePolicy)


class SkyView(QWidget):
    def __init__(self, sidebar_panel=None):
        super().__init__()
        self.setObjectName("view")
        self._sidebar_panel = sidebar_panel

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._build_guide_panel(layout)
        self._build_header(layout)
        self._build_camera_panel(layout)
        self._build_chart(layout)
        self._build_info_bar(layout)

        self._update_timer = self._start_timer()

    def _build_guide_panel(self, parent):
        self._guide_panel = None
        self._guide_parent = parent
        from app.core.background_worker import run_in_background
        run_in_background(get_tonight_guide, on_finished=self._on_guide_loaded,
                          on_error=lambda e: None)

    def _on_guide_loaded(self, guide_data):
        try:
            if guide_data and guide_data.get("targets"):
                self._guide_card = CollapsibleCard("🌟 今晚观星指南")
                self._guide_panel = GuidePanel(guide_data)
                self._guide_panel.goto_signal.connect(self._on_guide_goto)
                self._guide_card.content_layout().addWidget(self._guide_panel)
                self._guide_card.setVisible(not config.is_pro)
                self._guide_parent.layout().insertWidget(0, self._guide_card)
        except Exception:
            pass

    def _on_guide_goto(self, target):
        alt = target.get("altitude", 45)
        az = target.get("azimuth", 0)
        self.star_chart.guide_goto(alt, az)

    def _build_header(self, parent):
        header = QFrame()
        header.setStyleSheet(f"background: {Theme.BG_SECONDARY}; border-bottom: 1px solid {Theme.DIVIDER};")
        self._header_frame = header

        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(28, 8, 28, 8)
        header_layout.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        title = QLabel("🌌 实时星空")
        title.setFont(Theme.h1())
        title.setStyleSheet(f"color: {Theme.TEXT_PRIMARY};")
        top_row.addWidget(title)

        self.subtitle = QLabel()
        self.subtitle.setFont(Theme.body())
        self.subtitle.setStyleSheet(f"color: {Theme.TEXT_SECONDARY};")
        top_row.addWidget(self.subtitle)
        top_row.addStretch()

        self.pro_badge = StatusPill(
            "🔬 专业模式 · 双击刷新 · RA/Dec 网格 · DSO", Theme.ACCENT
        )
        self.pro_badge.setVisible(config.is_pro)
        top_row.addWidget(self.pro_badge)

        self.export_btn = QPushButton("📋 导出日志")
        self.export_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Theme.BG_CARD}; color: {Theme.TEXT_SECONDARY};
                border: 1px solid {Theme.DIVIDER}; border-radius: 6px;
                padding: 4px 12px; font-size: 11px;
            }}
            QPushButton:hover {{ border: 1px solid {Theme.STAR_GOLD}; color: {Theme.STAR_GOLD}; }}
        """)
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.clicked.connect(self._export_log)
        self.export_btn.setVisible(config.is_pro)
        top_row.addWidget(self.export_btn)

        header_layout.addLayout(top_row)

        device_row = QHBoxLayout()
        device_row.setSpacing(6)

        device_label = QLabel("观星设备:")
        device_label.setFont(Theme.caption())
        device_label.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        device_row.addWidget(device_label)

        self.device_group = QButtonGroup()
        self.device_group.setExclusive(True)
        for i, dc in enumerate(DEVICE_CONFIGS):
            btn = DeviceButton(dc)
            btn.setStyleSheet(self._device_btn_style(False))
            if i == 0:
                btn.setChecked(True)
                btn.setStyleSheet(self._device_btn_style(True))
            btn.clicked.connect(lambda checked, idx=i, b=btn: self._on_device_changed(idx, b))
            self.device_group.addButton(btn, i)
            device_row.addWidget(btn)

        device_row.addStretch()
        header_layout.addLayout(device_row)

        self._camera_settings_row = QFrame()
        self._camera_settings_row.setVisible(False)
        cam_layout = QVBoxLayout(self._camera_settings_row)
        cam_layout.setContentsMargins(0, 4, 0, 0)
        cam_layout.setSpacing(0)
        self.camera_panel = CameraPanel()
        self.camera_panel.params_changed.connect(self._on_camera_changed)
        cam_layout.addWidget(self.camera_panel)
        header_layout.addWidget(self._camera_settings_row)

        parent.addWidget(header)

    def _device_btn_style(self, active):
        if active:
            return f"""
                QPushButton {{
                    background: {Theme.ACCENT}; color: white; border: none;
                    border-radius: 6px; padding: 4px 12px; font-size: 11px;
                    font-weight: bold;
                }}
            """
        return f"""
            QPushButton {{
                background: {Theme.BG_CARD}; color: {Theme.TEXT_SECONDARY};
                border: 1px solid {Theme.DIVIDER}; border-radius: 6px;
                padding: 4px 12px; font-size: 11px;
            }}
            QPushButton:hover {{
                border: 1px solid {Theme.ACCENT}; color: {Theme.ACCENT};
            }}
        """

    def _on_device_changed(self, idx, btn):
        for b in self.device_group.buttons():
            b.setStyleSheet(self._device_btn_style(b is btn))
        is_camera = idx >= len(DEVICE_CONFIGS) - 1 and DEVICE_CONFIGS[idx].get("is_camera")
        self.star_chart.set_device(idx)
        self._camera_settings_row.setVisible(is_camera)
        if is_camera:
            self.star_chart.set_camera_fov({"fov_h_deg": 2.86, "fov_v_deg": 1.91, "rotation": 0, "show": True})
        else:
            self.star_chart.set_camera_fov(None)
        self._refresh_info()

    def _build_camera_panel(self, parent):
        sp = self._sidebar_panel
        if sp is None:
            return

        self.sat_card = CollapsibleCard("🛰 卫星实时追踪")
        self.sat_info = QLabel("正在获取TLE数据...")
        self.sat_info.setFont(Theme.caption())
        self.sat_info.setStyleSheet(f"color: {Theme.TEXT_SECONDARY};")
        self.sat_info.setWordWrap(True)
        self.sat_card.content_layout().addWidget(self.sat_info)
        self.sat_pass_info = QLabel("")
        self.sat_pass_info.setFont(Theme.caption())
        self.sat_pass_info.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        self.sat_pass_info.setWordWrap(True)
        self.sat_card.content_layout().addWidget(self.sat_pass_info)
        sp.addWidget(self.sat_card)
        sp.addSpacing(4)

        self.dso_card = CollapsibleCard("🌀 DSO 筛选 · 今晚最佳")
        fr = QHBoxLayout()
        fr.setSpacing(3)
        fl1 = QLabel("亮≤"); fl1.setFont(Theme.tiny()); fl1.setStyleSheet(f"color:{Theme.TEXT_MUTED};")
        fr.addWidget(fl1)
        self.dso_mag_spin = QSpinBox()
        self.dso_mag_spin.setRange(1, 20); self.dso_mag_spin.setValue(10); self.dso_mag_spin.setFixedWidth(38)
        self.dso_mag_spin.setStyleSheet(f"QSpinBox{{background:{Theme.BG_CARD};color:{Theme.TEXT_PRIMARY};border:1px solid {Theme.DIVIDER};border-radius:4px;padding:0px 2px;font-size:8px;}}")
        fr.addWidget(self.dso_mag_spin)
        fl2 = QLabel("高≥"); fl2.setFont(Theme.tiny()); fl2.setStyleSheet(f"color:{Theme.TEXT_MUTED};")
        fr.addWidget(fl2)
        self.dso_alt_spin = QSpinBox()
        self.dso_alt_spin.setRange(0, 90); self.dso_alt_spin.setValue(30); self.dso_alt_spin.setSuffix("°")
        self.dso_alt_spin.setFixedWidth(40)
        self.dso_alt_spin.setStyleSheet(f"QSpinBox{{background:{Theme.BG_CARD};color:{Theme.TEXT_PRIMARY};border:1px solid {Theme.DIVIDER};border-radius:4px;padding:0px 2px;font-size:8px;}}")
        fr.addWidget(self.dso_alt_spin)
        filter_btn = QPushButton("刷新")
        filter_btn.setFixedHeight(18)
        filter_btn.setStyleSheet(f"QPushButton{{background:{Theme.ACCENT};color:white;border:none;border-radius:3px;padding:0px 5px;font-size:8px;font-weight:bold;}}QPushButton:hover{{background:{Theme.ACCENT_DEEP};}}")
        filter_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        filter_btn.clicked.connect(self._refresh_dso_list)
        fr.addWidget(filter_btn)
        fr.addStretch()
        self.dso_card.content_layout().addLayout(fr)
        self.dso_list_label = QLabel("点击「刷新」获取目标")
        self.dso_list_label.setFont(Theme.caption())
        self.dso_list_label.setStyleSheet(f"color:{Theme.TEXT_MUTED};")
        self.dso_list_label.setWordWrap(True)
        self.dso_card.content_layout().addWidget(self.dso_list_label)
        sp.addWidget(self.dso_card)
        sp.addSpacing(4)

        self.ac_card = CollapsibleCard("✈ ADS-B 航空器追踪")
        ac_layout = QVBoxLayout()
        ac_layout.setSpacing(4)
        ac_top = QHBoxLayout()
        ac_top.setSpacing(4)
        self.ac_label = QLabel("正在获取航班数据...")
        self.ac_label.setFont(Theme.tiny())
        self.ac_label.setStyleSheet(f"color:{Theme.TEXT_SECONDARY};")
        self.ac_label.setWordWrap(True)
        ac_top.addWidget(self.ac_label, 1)
        self.ac_refresh_btn = QPushButton("↻")
        self.ac_refresh_btn.setFixedSize(22, 22)
        self.ac_refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ac_refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Theme.BG_CARD}; color: {Theme.TEXT_SECONDARY};
                border: 1px solid {Theme.DIVIDER}; border-radius: 4px;
                font-size: 12px; font-weight: bold;
            }}
            QPushButton:hover {{ background: {Theme.ACCENT_DIM}; color: {Theme.TEXT_PRIMARY}; }}
        """)
        self.ac_refresh_btn.clicked.connect(self._force_refresh_aircraft)
        ac_top.addWidget(self.ac_refresh_btn)
        self.ac_card.content_layout().addLayout(ac_top)
        sp.addWidget(self.ac_card)
        sp.addSpacing(4)

        # ── 大气质量卡片 ──
        self.atmos_card = CollapsibleCard("🌬️ 大气宁静度 · 专业模式")
        self.atmos_card.setVisible(False)
        atmos_layout = QVBoxLayout()
        atmos_layout.setSpacing(4)
        atmos_top = QHBoxLayout()
        self.atmos_seeing_label = QLabel("--")
        self.atmos_seeing_label.setFont(Theme.font(11, bold=True))
        self.atmos_seeing_label.setStyleSheet(f"color: {Theme.ACCENT};")
        atmos_top.addWidget(self.atmos_seeing_label)
        self.atmos_rating_label = QLabel("")
        self.atmos_rating_label.setFont(Theme.font(9))
        atmos_top.addWidget(self.atmos_rating_label)
        atmos_top.addStretch()
        self.atmos_refresh_btn = QPushButton("↻")
        self.atmos_refresh_btn.setFixedSize(24, 24)
        self.atmos_refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.atmos_refresh_btn.setStyleSheet(f"""
            QPushButton {{ background: {Theme.BG_CARD}; color: {Theme.TEXT_SECONDARY};
                border: 1px solid {Theme.DIVIDER}; border-radius: 4px; font-size: 13px; font-weight: bold; }}
            QPushButton:hover {{ background: {Theme.ACCENT_DIM}; color: {Theme.TEXT_PRIMARY}; }}
        """)
        self.atmos_refresh_btn.clicked.connect(self._refresh_atmosphere)
        atmos_top.addWidget(self.atmos_refresh_btn)
        atmos_layout.addLayout(atmos_top)

        self.atmos_detail = QLabel("")
        self.atmos_detail.setFont(Theme.font(9))
        self.atmos_detail.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        self.atmos_detail.setWordWrap(True)
        atmos_layout.addWidget(self.atmos_detail)

        self.atmos_chart = SeeingChart()
        atmos_layout.addWidget(self.atmos_chart)

        self.atmos_advice = QLabel("")
        self.atmos_advice.setFont(Theme.font(10, bold=True))
        self.atmos_advice.setWordWrap(True)
        atmos_layout.addWidget(self.atmos_advice)

        self.atmos_card.content_layout().addLayout(atmos_layout)
        sp.addWidget(self.atmos_card)

        self._atmos_timer = QTimer()
        self._atmos_timer.timeout.connect(self._refresh_atmosphere)
        self._atmos_timer.start(300000)
        QTimer.singleShot(2000, self._refresh_atmosphere)

    def _refresh_atmosphere(self):
        from app.core.background_worker import run_in_background
        def _fetch():
            from app.api.atmosphere_api import get_atmosphere_forecast
            return get_atmosphere_forecast()
        run_in_background(
            target=_fetch,
            on_finished=self._on_atmos_done,
        )

    def _on_atmos_done(self, data):
        try:
            if not data or "error" in data:
                self.atmos_seeing_label.setText("获取失败")
                return
            cur = data.get("current")
            if not cur:
                return
            self.atmos_seeing_label.setText(f'{cur["seeing"]}"')
            color = cur.get("rating_color", "warning")
            color_map = {"success": Theme.SUCCESS, "warning": Theme.WARNING, "danger": Theme.DANGER}
            c = color_map.get(color, Theme.WARNING)
            self.atmos_rating_label.setStyleSheet(f"color: {c}; font-weight: bold; font-size: 11px;")
            self.atmos_rating_label.setText(f'{cur["rating_icon"]} {cur["rating_label"]}')
            self.atmos_detail.setText(
                f'🌡️ {cur["temp"]}°C  💧 {cur["humidity"]}%  💨 {cur["wind_speed"]}m/s  ☁️ {cur["cloud_pct"]}%'
            )
            hourly = data.get("hourly", [])
            self.atmos_chart.set_data(hourly)
            advice_lines = cur.get("advice", [])
            self.atmos_advice.setText("\n".join(advice_lines) if advice_lines else "")
        except Exception:
            self.atmos_seeing_label.setText("--")

    def _force_refresh_aircraft(self):
        self.ac_label.setText("正在刷新航班数据...")
        from app.api.adsb_api import fetch_aircraft, add_aircraft_trajectories, fetch_aircraft_registrations
        from app.core.background_worker import run_in_background

        def _do_fetch():
            dt = datetime.now()
            ac = fetch_aircraft(dt)
            if ac:
                add_aircraft_trajectories(ac)
                fetch_aircraft_registrations(ac)
            return ac

        def _on_done(ac):
            try:
                if ac:
                    visible = [a for a in ac if a.get("altitude", -90) > 0]
                    lines = [f"✈ 追踪 {len(ac)} 架  |  可见 {len(visible)} 架"]
                    for a in sorted(visible, key=lambda x: -x["altitude"])[:5]:
                        lines.append(f"  {a['callsign']:>6s}  {a.get('altitude_ft',0):.0f}ft"
                                     f"  A{a['altitude']:.0f}°  {a.get('distance_km',0):.0f}km")
                    if len(visible) > 5:
                        lines.append(f"  ...及 {len(visible)-5} 架更多")
                    self._cached_ac = "\n".join(lines)
                    self.star_chart._aircraft = ac
                    self.star_chart.update()
                else:
                    self._cached_ac = "✈ 当前区域无航班数据"
                self._last_ac_update = datetime.now().timestamp()
            except Exception:
                self._cached_ac = "✈ 获取失败（请尝试启用网络）"
            self.ac_label.setText(self._cached_ac)

        run_in_background(_do_fetch, on_finished=_on_done, on_error=lambda e: self.ac_label.setText("✈ 获取失败"))

    def _on_camera_changed(self, params):
        if hasattr(self.star_chart, 'set_camera_fov'):
            self.star_chart.set_camera_fov(params)

    def _build_chart(self, parent):
        use_gl = config.pro_settings.get("gl_renderer", False)
        if use_gl:
            try:
                from app.widgets.gl_hybrid_chart import GLHybridChart
                self.star_chart = GLHybridChart()
            except Exception:
                from app.widgets.star_chart import StarChart
                self.star_chart = StarChart()
        else:
            from app.widgets.star_chart import StarChart
            self.star_chart = StarChart()
        parent.addWidget(self.star_chart, 1)

    def _build_info_bar(self, parent):
        bar = QFrame()
        bar.setFixedHeight(48)
        bar.setStyleSheet(f"background: {Theme.BG_SECONDARY}; border-top: 1px solid {Theme.DIVIDER};")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(28, 0, 28, 0)

        toggles = [
            ("stars", "⭐恒星"), ("planets", "🪐行星"), ("sun_moon", "☀️日月"),
            ("satellites", "🛰卫星"), ("aircraft", "✈航空器"), ("constellations", "📐星座线"),
        ]
        dso_toggles = [
            ("dso_nebula", "🌀星云"), ("dso_cluster", "⭐星团"), ("dso_galaxy", "🌌星系"),
        ]

        self._toggle_cbs = {}
        for key, label in toggles + dso_toggles:
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.setFont(Theme.caption())
            cb.setStyleSheet(f"""
                QCheckBox {{
                    color: {Theme.TEXT_SECONDARY}; spacing: 3px; font-size: 10px;
                }}
                QCheckBox::indicator {{
                    width: 12px; height: 12px; border-radius: 3px;
                    border: 1px solid {Theme.ACCENT}66;
                    background: {Theme.BG_CARD};
                }}
                QCheckBox::indicator:checked {{
                    background: {Theme.ACCENT}; border: 1px solid {Theme.ACCENT};
                }}
                QCheckBox:hover {{ color: {Theme.TEXT_PRIMARY}; }}
            """)
            cb.toggled.connect(lambda checked, k=key: self.star_chart.set_show(k, checked))
            bar_layout.addWidget(cb)
            bar_layout.addSpacing(8)
            self._toggle_cbs[key] = cb

        bar_layout.addStretch()

        self.star_count = QLabel()
        self.star_count.setFont(Theme.caption())
        self.star_count.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        bar_layout.addWidget(self.star_count)

        parent.addWidget(bar)

    def _start_timer(self):
        timer = QTimer()
        timer.timeout.connect(self._refresh_info)
        timer.start(3000)
        return timer

    def _refresh_info(self):
        now = datetime.now()
        self.subtitle.setText(f"{config.city_name}  ·  {now.strftime('%Y/%m/%d %H:%M:%S')}")
        dc = DEVICE_CONFIGS[self.star_chart._device_index]
        if dc.get("is_camera"):
            fov = self.star_chart._camera_fov
            if fov:
                self.star_count.setText(f"📷 相机  |  FOV {fov['fov_h_deg']:.2f}°×{fov['fov_v_deg']:.2f}°")
            else:
                self.star_count.setText(f"📷 相机  |  设置参数以显示取景框")
        else:
            self.star_count.setText(f"设备: {dc['name']}  |  恒星: {len(self.star_chart._stars)} 颗")
        if config.is_pro and hasattr(self, 'star_chart'):
            self._update_satellite_info()
            self._update_aircraft_info()

    def _update_satellite_info(self):
        if not hasattr(self, 'sat_info'):
            return
        now = datetime.now()
        if not hasattr(self, '_last_sat_update'):
            self._last_sat_update = 0
            self._cached_sat_visible = 0
            self._cached_sat_lines = "🛰 加载中..."
            self._cached_iss_pass = ""

        if (now.timestamp() - self._last_sat_update) > 60:
            self._last_sat_update = now.timestamp()
            sats = self.star_chart._satellites
            if sats:
                visible = [s for s in sats if s.get("altitude", -90) > 0]
                lines = [f"🛰 追踪 {len(sats)} 颗  |  地平线上 {len(visible)} 颗"]
                for s in sats[:3]:
                    alt = s.get("altitude", 0)
                    icon = "↑" if alt > 0 else "↓"
                    lines.append(f"  {s['name']} {icon} A{alt:.0f}° Az{s['azimuth']:.0f}°")
                self._cached_sat_lines = "\n".join(lines)
                self._cached_sat_visible = len(visible)

                try:
                    sats = self.star_chart._satellites
                    iss_current = None
                    for s in sats:
                        if s.get("norad") == 25544:
                            iss_current = s
                            break
                    if iss_current and iss_current.get("altitude", -90) > 0:
                        alt_now = iss_current["altitude"]
                        az_now = iss_current["azimuth"]
                        self._cached_iss_pass = (
                            f"🛸 ISS 正在过境  Alt {alt_now:.0f}°  Az {az_now:.0f}°"
                        )
                    else:
                        self._fetch_iss_pass()
                except Exception:
                    pass

    def _fetch_iss_pass(self):
        from app.core.background_worker import run_in_background

        def _compute():
            return sky.predict_satellite_passes(25544)

        def _on_done(passes):
            try:
                if passes:
                    p = passes[0]
                    self._cached_iss_pass = (
                        f"🛸 ISS下次过境: {p['start']} 升起 → {p['peak']} 最高 {p['max_alt']}° → {p['end']} 落下"
                    )
                else:
                    self._cached_iss_pass = "ISS 24h内无可见过境"
                if hasattr(self, "sat_pass_info"):
                    self.sat_pass_info.setText(self._cached_iss_pass)
            except Exception:
                pass

        run_in_background(_compute, on_finished=_on_done, on_error=lambda e: None)

        if hasattr(self, "sat_info"):
            self.sat_info.setText(self._cached_sat_lines)
        if hasattr(self, "sat_pass_info"):
            self.sat_pass_info.setText(self._cached_iss_pass)

    def on_show(self):
        self.star_chart.refresh()
        self._refresh_info()

    def on_mode_changed(self, mode):
        is_pro = mode == "professional"
        self.pro_badge.setVisible(is_pro)
        self.export_btn.setVisible(is_pro)
        is_camera = DEVICE_CONFIGS[self.star_chart._device_index].get("is_camera", False)
        self._camera_settings_row.setVisible(is_pro and is_camera)
        for cb in self._toggle_cbs.values():
            cb.setVisible(is_pro)
        if hasattr(self, '_guide_card') and self._guide_card:
            self._guide_card.setVisible(not is_pro)
        if hasattr(self, '_atmos_card'):
            self._atmos_card.setVisible(is_pro)
        if not is_pro:
            self.star_chart.set_camera_fov(None)
        self.star_chart.update()

    def _refresh_dso_list(self):
        from app.core.background_worker import run_in_background
        from app.api.astronomy_api import filter_dso_for_night
        mag_lim = self.dso_mag_spin.value()
        alt_min = self.dso_alt_spin.value()
        user_bortle = {"暗空区": 2, "乡村": 4, "郊区": 6, "城市": 8}.get(config.light_pollution, 8)

        def _compute():
            return filter_dso_for_night(mag_limit=mag_lim, min_alt=alt_min, user_bortle=user_bortle)

        def _on_done(targets):
            try:
                if not targets:
                    self.dso_list_label.setText(f"未找到满足条件的目标 (亮度≤{mag_lim}, 高度≥{alt_min}°)")
                    return
                lines = [f"🎯 找到 {len(targets)} 个最佳目标 (亮度≤{mag_lim}, 高度≥{alt_min}°):"]
                for t in targets[:20]:
                    vis_icon = "✅" if t["visible"] else "⚠️"
                    d = f"{t['dist_ly']/1000:.0f}k" if t["dist_ly"] > 10000 else f"{t['dist_ly']:.0f}"
                    lines.append(f"  {vis_icon} {t['id']:6s} {t['name']:8s} Mag{t['mag']:.1f} Alt{t['altitude']:.0f}° {d}ly {t['type']}")
                if len(targets) > 20:
                    lines.append(f"  ...及 {len(targets)-20} 个更多目标")
                self.dso_list_label.setText("\n".join(lines))
            except Exception as e:
                self.dso_list_label.setText(f"获取失败: {e}")

        run_in_background(_compute, on_finished=_on_done, on_error=lambda e: None)

    def _update_aircraft_info(self):
        if not hasattr(self, 'ac_label'):
            return
        now = datetime.now()
        if not hasattr(self, '_last_ac_update'):
            self._last_ac_update = 0
            self._cached_ac = "✈ 加载中..."
        if (now.timestamp() - self._last_ac_update) > 120:
            self._last_ac_update = now.timestamp()
            from app.core.background_worker import run_in_background

            def _fetch():
                return fetch_aircraft()

            def _on_done(ac):
                try:
                    if ac:
                        visible = [a for a in ac if a.get("altitude", -90) > 0]
                        lines = [f"✈ 追踪 {len(ac)} 架  |  可见 {len(visible)} 架"]
                        for a in sorted(visible, key=lambda x: -x["altitude"])[:5]:
                            lines.append(f"  {a['callsign']:>6s}  {a.get('altitude_ft',0):.0f}ft"
                                         f"  A{a['altitude']:.0f}°  {a.get('distance_km',0):.0f}km")
                        if len(visible) > 5:
                            lines.append(f"  ...及 {len(visible)-5} 架更多")
                        self._cached_ac = "\n".join(lines)
                    else:
                        self._cached_ac = "✈ 当前区域无航班数据"
                except Exception:
                    self._cached_ac = "✈ 获取失败（请尝试启用网络）"
                self.ac_label.setText(self._cached_ac)

            run_in_background(_fetch, on_finished=_on_done, on_error=lambda e: self.ac_label.setText(self._cached_ac))
        self.ac_label.setText(self._cached_ac)

    def _export_log(self):
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        path, _ = QFileDialog.getSaveFileName(self, "导出观测日志", "观测日志.txt", "文本文件 (*.txt)")
        if not path:
            return
        try:
            now = datetime.now()
            lines = [f"星迹 StarTrail - 观测日志", f"时间: {now.strftime('%Y-%m-%d %H:%M:%S')}",
                     f"地点: {config.city_name} ({config.latitude}°N, {config.longitude}°E)",
                     f"设备: {DEVICE_CONFIGS[self.star_chart._device_index]['name']}", "=" * 40, ""]
            lines.append(f"可见恒星: {len(self.star_chart._stars)} 颗")
            for s in self.star_chart._stars[:20]:
                lines.append(f"  {s['name']}  Mag:{s.get('mag',0):.1f}  Alt:{s['altitude']:.0f}°  Az:{s['azimuth']:.0f}°")
            lines.append("")
            lines.append(f"行星: {len(self.star_chart._planets)} 颗")
            for p in self.star_chart._planets:
                lines.append(f"  {p['name']}  Alt:{p['altitude']:.0f}°  Az:{p['azimuth']:.0f}°")
            lines.append("")
            lines.append(f"太阳: Alt {self.star_chart._sun.get('altitude',0):.0f}°" if self.star_chart._sun else "太阳: 不可见")
            lines.append(f"月亮: Alt {self.star_chart._moon.get('altitude',0):.0f}°" if self.star_chart._moon else "月亮: 不可见")
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            QMessageBox.information(self, "导出成功", f"日志已保存至:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", str(e))
