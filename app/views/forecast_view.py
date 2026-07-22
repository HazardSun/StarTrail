from datetime import datetime

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QFrame, QScrollArea, QSizePolicy)
from PySide6.QtCore import Qt, QTimer

from app.theme import Theme
from app.config import config
from app.widgets.glass_card import GlassCard
from app.widgets.ui_kit import MetricBar
from app.widgets.gauge import StargazingIndexGauge
from app.api.weather_api import (get_weather, get_forecast, calc_stargazing_index,
                                 check_precipitation, wind_direction)
from app.api.astronomy_api import sky
from app.api.location_api import get_full_address

SCORE_RULES = [
    ("云量", "≤30% 不扣 → 30-50% 扣≤10 → 50-75% 扣≤30 → >75% 扣≤40", "非线性扣分，云量影响逐步加重"),
    ("能见度", "≥10km 不扣 → 5-10km 扣 5 → 1-5km 扣 15 → <1km 扣 30", "大气通透度直接影响"),
    ("湿度", "≤80% 不扣 → >80% 扣 10", "湿度过高镜片易起雾"),
    ("月相", "新月 不扣 → 满月 扣 15", "月光越亮暗星越难见"),
    ("风速", "≤10m/s 不扣 → 10-15m/s 扣 5 → >15m/s 扣 15", "大风影响稳定性和舒适度"),
    ("光污染", "暗空区 不扣 → 乡村 扣 5 → 郊区 扣 15 → 城市 扣 25", "可在设置中修改观测环境"),
]


class ForecastView(QWidget):
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
        self._build_score_card()
        self._build_score_rules()
        self._build_score_breakdown()
        self._build_conditions()
        self._build_precip_card()
        self._build_sun_moon_card()
        self._build_moon_planet()
        self._build_pro_forecast()

        self._weather_cache = None
        self._weather_cache_time = 0

        self.main_layout.addStretch()

    def _build_header(self):
        header = QFrame()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        title = QLabel("🔭 观星预报")
        title.setFont(Theme.h1())
        title.setStyleSheet(f"color: {Theme.TEXT_PRIMARY};")

        subtitle = QLabel("结合天气、月相、光污染，智能评估今晚观星条件")
        subtitle.setFont(Theme.body())
        subtitle.setStyleSheet(f"color: {Theme.TEXT_SECONDARY};")

        self.location_detail = QLabel("")
        self.location_detail.setFont(Theme.caption())
        self.location_detail.setStyleSheet(f"color: {Theme.ACCENT};")

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        header_layout.addWidget(self.location_detail)
        self.main_layout.addWidget(header)

    def _build_score_card(self):
        card = GlassCard()
        card.set_title("🌟 观星适宜度")

        # ── 圆形仪表盘居中（已包含分数 + 等级文字）──
        gauge_row = QHBoxLayout()
        gauge_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gauge = StargazingIndexGauge(value=0, size=140, stroke_width=12)
        gauge_row.addWidget(self.gauge)

        card.content_layout().addLayout(gauge_row)

        # 底部进度条参考
        self.score_bar = MetricBar(0, Theme.TEXT_MUTED, height=6)
        self.score_bar.setFixedHeight(6)
        card.content_layout().addWidget(self.score_bar)
        self.main_layout.addWidget(card)

    def _build_score_rules(self):
        card = GlassCard()
        card.set_title("📊 评分规则")
        html = "<div style='line-height:1.6'>"
        for factor, rule, note in SCORE_RULES:
            html += f"<b style='color:{Theme.TEXT_PRIMARY}'>{factor}</b><br>"
            html += f"<span style='color:{Theme.TEXT_SECONDARY};font-size:11px'>{rule}</span><br>"
            html += f"<span style='color:{Theme.TEXT_MUTED};font-size:10px'>{note}</span><br><br>"
        html += "</div>"
        label = QLabel(html)
        label.setWordWrap(True)
        label.setOpenExternalLinks(False)
        label.setStyleSheet("background:transparent;")
        card.content_layout().addWidget(label)
        self.main_layout.addWidget(card)

    def _build_precip_card(self):
        card = GlassCard()
        card.set_title("🌧 未来降水预报")

        row = QHBoxLayout()
        row.setSpacing(8)

        self._precip_labels = {}
        for label, hours, icon in [("2小时", 2, "⏳"), ("8小时", 8, "🌤"), ("12小时", 12, "☁️"), ("24小时", 24, "🌦")]:
            frame = QFrame()
            frame.setObjectName("card")
            frame.setStyleSheet(Theme.card_style())
            fl = QVBoxLayout(frame)
            fl.setContentsMargins(8, 8, 8, 8)
            fl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            title = QLabel(f"{icon} {label}")
            title.setFont(Theme.caption())
            title.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fl.addWidget(title)

            val = QLabel("--")
            val.setFont(Theme.font(12, bold=True))
            val.setStyleSheet(f"color: {Theme.TEXT_SECONDARY};")
            val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fl.addWidget(val)

            row.addWidget(frame)
            self._precip_labels[label] = val

        card.content_layout().addLayout(row)
        self.main_layout.addWidget(card)

    def _build_sun_moon_card(self):
        card = GlassCard()
        card.set_title("☀️🌙 日月升落")

        row = QHBoxLayout()
        row.setSpacing(16)

        sun_frame = QFrame()
        sun_frame.setObjectName("card")
        sun_frame.setStyleSheet(Theme.card_style())
        sun_layout = QVBoxLayout(sun_frame)
        sun_layout.setContentsMargins(16, 12, 16, 12)
        sun_layout.setSpacing(4)
        sun_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sun_icon = QLabel("☀️")
        sun_icon.setFont(Theme.font(24))
        sun_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sun_layout.addWidget(sun_icon)

        sun_title = QLabel("太阳")
        sun_title.setFont(Theme.font(12, bold=True))
        sun_title.setStyleSheet(f"color: {Theme.TEXT_PRIMARY};")
        sun_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sun_layout.addWidget(sun_title)

        self.sunrise_label = QLabel("--:--")
        self.sunrise_label.setFont(Theme.body())
        self.sunrise_label.setStyleSheet(f"color: {Theme.STAR_GOLD};")
        self.sunrise_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sun_layout.addWidget(self.sunrise_label)

        self.sunrise_title = QLabel("日出")
        self.sunrise_title.setFont(Theme.caption())
        self.sunrise_title.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        self.sunrise_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sun_layout.addWidget(self.sunrise_title)

        self.sunset_label = QLabel("--:--")
        self.sunset_label.setFont(Theme.body())
        self.sunset_label.setStyleSheet(f"color: {Theme.ACCENT};")
        self.sunset_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sun_layout.addWidget(self.sunset_label)

        self.sunset_title = QLabel("日落")
        self.sunset_title.setFont(Theme.caption())
        self.sunset_title.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        self.sunset_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sun_layout.addWidget(self.sunset_title)

        row.addWidget(sun_frame)

        moon_frame = QFrame()
        moon_frame.setObjectName("card")
        moon_frame.setStyleSheet(Theme.card_style())
        moon_layout = QVBoxLayout(moon_frame)
        moon_layout.setContentsMargins(16, 12, 16, 12)
        moon_layout.setSpacing(4)
        moon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        moon_icon = QLabel("🌙")
        moon_icon.setFont(Theme.font(24))
        moon_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        moon_layout.addWidget(moon_icon)

        moon_title = QLabel("月亮")
        moon_title.setFont(Theme.font(12, bold=True))
        moon_title.setStyleSheet(f"color: {Theme.TEXT_PRIMARY};")
        moon_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        moon_layout.addWidget(moon_title)

        self.moonrise_label = QLabel("--:--")
        self.moonrise_label.setFont(Theme.body())
        self.moonrise_label.setStyleSheet(f"color: {Theme.STAR_GOLD};")
        self.moonrise_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        moon_layout.addWidget(self.moonrise_label)

        self.moonrise_title = QLabel("月出")
        self.moonrise_title.setFont(Theme.caption())
        self.moonrise_title.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        self.moonrise_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        moon_layout.addWidget(self.moonrise_title)

        self.moonset_label = QLabel("--:--")
        self.moonset_label.setFont(Theme.body())
        self.moonset_label.setStyleSheet(f"color: {Theme.ACCENT};")
        self.moonset_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        moon_layout.addWidget(self.moonset_label)

        self.moonset_title = QLabel("月落")
        self.moonset_title.setFont(Theme.caption())
        self.moonset_title.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        self.moonset_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        moon_layout.addWidget(self.moonset_title)

        row.addWidget(moon_frame)
        card.content_layout().addLayout(row)

        self.main_layout.addWidget(card)

    def _build_score_breakdown(self):
        card = GlassCard()
        card.set_title("📉 今日扣分明细")

        self._breakdown_widgets = {}
        for factor in ["云量", "能见度", "湿度", "月相", "风速", "光污染"]:
            row = QHBoxLayout()
            row.setSpacing(8)

            name = QLabel(factor)
            name.setFont(Theme.font(12, bold=True))
            name.setStyleSheet(f"color: {Theme.TEXT_SECONDARY};")
            name.setFixedWidth(56)
            row.addWidget(name)

            val = QLabel("--")
            val.setFont(Theme.body())
            val.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
            val.setFixedWidth(90)
            row.addWidget(val)

            bar = MetricBar(0, Theme.ACCENT, height=8)
            row.addWidget(bar, 1)

            deduct = QLabel("-0")
            deduct.setFont(Theme.font(12, bold=True))
            deduct.setStyleSheet(f"color: {Theme.SUCCESS};")
            deduct.setFixedWidth(40)
            deduct.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(deduct)

            self._breakdown_widgets[factor] = {
                "val": val, "bar": bar, "deduct": deduct
            }

            card.content_layout().addLayout(row)

        self.main_layout.addWidget(card)

    def _update_breakdown(self, breakpoints):
        for factor in ["云量", "能见度", "湿度", "月相", "风速", "光污染"]:
            w = self._breakdown_widgets.get(factor)
            if not w:
                continue

            found = [b for b in breakpoints if b[0] == factor]
            if found:
                _, raw, pts_str = found[0]
                pts = int(pts_str)
                w["val"].setText(str(raw))
                w["deduct"].setText(f"-{pts}")
                if pts == 0:
                    w["deduct"].setStyleSheet(f"color: {Theme.SUCCESS}; font-size: 12px; font-weight: bold;")
                    w["bar"].setValue(0)
                    w["bar"].setColor(Theme.SUCCESS)
                elif pts <= 10:
                    w["deduct"].setStyleSheet(f"color: {Theme.WARNING}; font-size: 12px; font-weight: bold;")
                    w["bar"].setValue(int(pts / 40.0 * 100))
                    w["bar"].setColor(Theme.WARNING)
                else:
                    w["deduct"].setStyleSheet(f"color: {Theme.DANGER}; font-size: 12px; font-weight: bold;")
                    w["bar"].setValue(int(pts / 40.0 * 100))
                    w["bar"].setColor(Theme.DANGER)
            else:
                w["val"].setText("--")
                w["deduct"].setText("-0")
                w["deduct"].setStyleSheet(f"color: {Theme.SUCCESS}; font-size: 12px; font-weight: bold;")
                w["bar"].setValue(0)
                w["bar"].setColor(Theme.SUCCESS)

    def _build_conditions(self):
        card = GlassCard()
        card.set_title("🌤 当前天气详情")

        self._weather_icon = QLabel()
        self._weather_icon.setFont(Theme.font(32))
        self._weather_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.content_layout().addWidget(self._weather_icon)

        self.condition_labels = {}
        for label in ["天气状况", "温度", "体感温度", "气压", "湿度", "云量", "能见度", "风向", "风速"]:
            val_label = QLabel("--")
            val_label.setFont(Theme.body())
            val_label.setStyleSheet(f"color: {Theme.TEXT_SECONDARY};")
            card.add_row(label, val_label)
            self.condition_labels[label] = val_label

        self.main_layout.addWidget(card)

    def _build_moon_planet(self):
        row = QHBoxLayout()
        row.setSpacing(16)

        moon_card = GlassCard()
        moon_card.set_title("🌙 月相")
        self.moon_icon = QLabel("--")
        self.moon_icon.setFont(Theme.font(36))
        self.moon_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        moon_card.content_layout().addWidget(self.moon_icon)
        self.moon_name = QLabel("--")
        self.moon_name.setFont(Theme.h2())
        self.moon_name.setStyleSheet(f"color: {Theme.TEXT_PRIMARY};")
        self.moon_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        moon_card.content_layout().addWidget(self.moon_name)
        self.moon_illum = QLabel("--")
        self.moon_illum.setFont(Theme.body())
        self.moon_illum.setStyleSheet(f"color: {Theme.TEXT_SECONDARY};")
        self.moon_illum.setAlignment(Qt.AlignmentFlag.AlignCenter)
        moon_card.content_layout().addWidget(self.moon_illum)
        row.addWidget(moon_card)

        planet_card = GlassCard()
        planet_card.set_title("🪐 今晚行星")
        self.planet_list = QWidget()
        self.planet_list_layout = QVBoxLayout(self.planet_list)
        self.planet_list_layout.setContentsMargins(0, 0, 0, 0)
        self.planet_list_layout.setSpacing(4)
        self.planet_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        planet_card.content_layout().addWidget(self.planet_list, 1)
        row.addWidget(planet_card)

        self.main_layout.addLayout(row)

    def _build_pro_forecast(self):
        self.pro_section = QFrame()
        pro_layout = QVBoxLayout(self.pro_section)
        pro_layout.setContentsMargins(0, 0, 0, 0)
        pro_layout.setSpacing(12)

        pro_header = QLabel("🔬 专业预报参数")
        pro_header.setFont(Theme.h3())
        pro_header.setStyleSheet(f"color: {Theme.STAR_GOLD};")
        pro_layout.addWidget(pro_header)

        self.pro_info = QLabel("切换至专业模式查看详细技术参数")
        self.pro_info.setFont(Theme.body())
        self.pro_info.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        self.pro_info.setWordWrap(True)
        pro_layout.addWidget(self.pro_info)

        self.main_layout.addWidget(self.pro_section)
        self.pro_section.setVisible(config.is_pro)

    def on_show(self):
        self.location_detail.setText(f"📍 {config.city_name}")
        QTimer.singleShot(0, self._refresh_data)
        if not hasattr(self, '_address_done'):
            self._address_done = True
            QTimer.singleShot(200, self._try_address)

    def _try_address(self):
        from app.core.background_worker import run_in_background

        def _fetch():
            return get_full_address()

        def _on_done(addr):
            if addr:
                self.location_detail.setText(f"📍 {addr}")

        run_in_background(_fetch, on_finished=_on_done, on_error=lambda e: None)

    def on_mode_changed(self, mode):
        self.pro_section.setVisible(mode == "professional")
        if mode == "professional":
            self._update_pro_data()

    def _refresh_data(self):
        self._cached_moon_phase = sky.get_moon_phase()
        self._update_astronomy()
        QTimer.singleShot(0, self._update_weather)
        if config.is_pro:
            QTimer.singleShot(100, self._update_pro_data)

    def _update_weather(self):
        now = datetime.now().timestamp()
        if self._weather_cache and (now - self._weather_cache_time) < 120:
            weather = self._weather_cache
            self._apply_weather(weather)
            self._apply_forecast(getattr(self, "_forecast_cache", None))
            return

        from app.core.background_worker import run_in_background

        def _fetch():
            return get_weather(), get_forecast()

        def _on_done(result):
            try:
                weather, forecast = result
                if isinstance(weather, dict) and "error" not in weather:
                    self._weather_cache = weather
                    self._weather_cache_time = datetime.now().timestamp()
                if isinstance(forecast, dict) and "error" not in forecast:
                    self._forecast_cache = forecast
                self._apply_weather(weather)
                self._apply_forecast(forecast)
            except Exception:
                pass

        run_in_background(_fetch, on_finished=_on_done, on_error=lambda e: None)

    def _apply_weather(self, weather):

        moon_phase = getattr(self, '_cached_moon_phase', {}) or sky.get_moon_phase()

        if isinstance(weather, dict) and "error" not in weather:
            main = weather.get("main", {})
            clouds = weather.get("clouds", {}).get("all", "--")
            vis = weather.get("visibility", 0)
            wind = weather.get("wind", {})

            w_list = weather.get("weather", [{}])
            w_desc = w_list[0].get("description", "--") if w_list else "--"
            w_icon_code = w_list[0].get("icon", "01d") if w_list else "01d"
            w_main = w_list[0].get("main", "") if w_list else ""

            icon_map = {
                "Thunderstorm": "⛈", "Drizzle": "🌦", "Rain": "🌧",
                "Snow": "🌨", "Mist": "🌫", "Smoke": "🌫",
                "Haze": "🌫", "Dust": "🌫", "Fog": "🌫",
                "Clear": "☀️" if "d" in w_icon_code else "🌙",
                "Clouds": "⛅" if "d" in w_icon_code else "☁️",
            }
            if "Clouds" in w_main and clouds and clouds > 80:
                w_emoji = "☁️"
            else:
                w_emoji = icon_map.get(w_main, "🌤")

            self._weather_icon.setText(f"{w_emoji}  {w_desc}")
            self.condition_labels["天气状况"].setText(w_desc)

            temp = main.get("temp", "--")
            feels_like = main.get("feels_like", "--")
            temp_min = main.get("temp_min", "")
            temp_max = main.get("temp_max", "")

            if temp_min and temp_max:
                temp_str = f"{temp}°C  (↓{temp_min} ↑{temp_max})"
            else:
                temp_str = f"{temp}°C"
            self.condition_labels["温度"].setText(temp_str)
            self.condition_labels["体感温度"].setText(f"{feels_like}°C")
            self.condition_labels["气压"].setText(f'{main.get("pressure", "--")} hPa')
            self.condition_labels["湿度"].setText(f'{main.get("humidity", "--")}%')
            self.condition_labels["云量"].setText(f"{clouds}%")
            self.condition_labels["能见度"].setText(f"{vis / 1000:.1f} km" if vis else "-- km")

            wind_speed = wind.get("speed", "--")
            wind_deg = wind.get("deg", 0)
            wind_gust = wind.get("gust", 0)
            self.condition_labels["风向"].setText(wind_direction(wind_deg) if isinstance(wind_deg, (int, float)) else "--")
            gust_str = f"  (阵风 {wind_gust} m/s)" if wind_gust else ""
            self.condition_labels["风速"].setText(f"{wind_speed} m/s{gust_str}")

            score, desc, color, bp = calc_stargazing_index(weather, moon_phase)
            self.gauge.setValue(score)
            self.score_bar.setValue(score)
            self.score_bar.setColor(color)
            self._update_breakdown(bp)
        else:
            if weather is None:
                err = "network"
            elif isinstance(weather, dict):
                err = weather.get("error", "")
            else:
                err = "no_key"
            code = weather.get("code", "?") if isinstance(weather, dict) else "?"
            msgs = {
                "no_key": "🔑 请在设置中填写 OpenWeather API 密钥",
                "invalid_key": "❌ API 密钥无效，请在设置中检查并重新填写",
                "timeout": "⏱ 连接超时\nOpenWeatherMap 在中国大陆可能需要科学上网",
                "http_error": f"⚠️ 服务返回错误 (HTTP {code})",
                "network": "🌐 网络连接失败，请检查网络设置",
            }
            msg = msgs.get(err, "🌐 网络连接失败，请检查网络设置")
            self.gauge.setValue(0)
            self.score_bar.setValue(0)
            self.score_bar.setColor(Theme.TEXT_MUTED)
            self._update_breakdown([])

    def _apply_forecast(self, forecast):
        if isinstance(forecast, dict) and "error" not in forecast:
            self._update_precip(forecast)
        else:
            for lbl in ["2小时", "8小时", "12小时", "24小时"]:
                self._precip_labels[lbl].setText("--")

    def _update_precip(self, forecast):
        periods = [("2小时", 2), ("8小时", 8), ("12小时", 12), ("24小时", 24)]
        for label, hours in periods:
            result = check_precipitation(forecast, hours)
            if result["has_precip"]:
                text = result["desc"]
                color = Theme.WARNING if result["prob"] < 50 else Theme.DANGER
            else:
                text = "☀️ 无降水"
                color = Theme.SUCCESS
            self._precip_labels[label].setText(text)
            self._precip_labels[label].setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")

    def _update_astronomy(self):
        moon = getattr(self, '_cached_moon_phase', {}) or sky.get_moon_phase()
        self.moon_icon.setText(moon["icon"])
        self.moon_name.setText(moon["name"])
        self.moon_illum.setText(f"照明度: {moon['illumination']}")

        from app.core.background_worker import run_in_background

        def _compute():
            return sky.get_sun_times(), sky.get_moon_times(), sky.get_planet_positions()

        def _on_done(result):
            try:
                sun_times, moon_times, planets = result
                if sun_times:
                    self.sunrise_label.setText(sun_times.get("sunrise", "--:--"))
                    self.sunset_label.setText(sun_times.get("sunset", "--:--"))
                if moon_times:
                    self.moonrise_label.setText(moon_times.get("moonrise", "--:--"))
                    self.moonset_label.setText(moon_times.get("moonset", "--:--"))
                for i in reversed(range(self.planet_list_layout.count())):
                    w = self.planet_list_layout.itemAt(i).widget()
                    if w:
                        w.deleteLater()
                if planets:
                    for p in planets:
                        p_label = QLabel(
                            f"● {p['name']}  "
                            f"高度: {p['altitude']:.0f}°  "
                            f"星等: {p.get('magnitude', 0):.1f}"
                        )
                        p_label.setFont(Theme.body())
                        p_label.setStyleSheet(f"color: {p.get('color', Theme.TEXT_SECONDARY)};")
                        self.planet_list_layout.addWidget(p_label)
                else:
                    no_p = QLabel("今晚没有可见行星")
                    no_p.setFont(Theme.body())
                    no_p.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
                    self.planet_list_layout.addWidget(no_p)
            except Exception:
                pass

        run_in_background(_compute, on_finished=_on_done, on_error=lambda e: None)

    def _update_pro_data(self):
        data = [f"观测坐标: {config.latitude}°N, {config.longitude}°E"]
        data.append(f"城市: {config.city_name}")
        data.append(f"单位制: {'公制' if config.pro_settings.get('units') == 'metric' else '英制'}")
        data.append(f"自动刷新: {'开' if config.pro_settings.get('auto_refresh') else '关'}")

        moon = getattr(self, '_cached_moon_phase', {}) or sky.get_moon_phase()
        data.append(f"月相参数: {moon['phase']:.3f} (0=新月, 0.5=满月)")

        jd = sky.get_jd()
        mjd = sky.get_mjd()
        data.append(f"JD: {jd}  |  MJD: {mjd}")

        from app.core.background_worker import run_in_background

        def _compute():
            return sky.get_best_window()

        def _on_done(window):
            try:
                wdata = list(data)
                if window:
                    wdata.append(f"最佳观测: {window['start']} - {window['end']}")
                    wdata.append(f"窗口时长: {window['duration_hours']}h  质量: {window['quality']}")
                if self._weather_cache and isinstance(self._weather_cache, dict):
                    wdata.append(f"气压: {self._weather_cache.get('main', {}).get('pressure', '--')} hPa")
                else:
                    wdata.append("天气数据: 不可用")
                if hasattr(self, "pro_info"):
                    self.pro_info.setText("\n".join(wdata))
            except Exception:
                pass

        run_in_background(_compute, on_finished=_on_done, on_error=lambda e: None)
