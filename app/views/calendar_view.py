import math
from datetime import datetime, date, timedelta

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QFrame, QPushButton, QGridLayout, QScrollArea,
                               QSizePolicy)
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QFontMetrics

from app.theme import Theme
from app.config import config
from app.api.astronomy_api import (sky, EVENT_TYPE_COLORS,
                                      get_hemisphere_label, get_visible_hemisphere)
from app.api.location_api import get_nearby_sites

CELL_SIZE = 72
HEADER_HEIGHT = 36


def _c(hex_color, alpha=255):
    c = QColor(hex_color)
    if alpha < 255:
        c.setAlpha(alpha)
    return c


class CalendarCell(QWidget):
    clicked = Signal(int)

    def __init__(self, day, is_today, is_current_month, parent=None):
        super().__init__(parent)
        self.day = day
        self.is_today = is_today
        self.is_current_month = is_current_month
        self.is_selected = False
        self.events = []
        self.setFixedSize(CELL_SIZE, CELL_SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        bg = Theme.BG_PRIMARY if self.is_current_month else Theme.BG_SECONDARY
        painter.fillRect(rect, QColor(bg))

        has_events = bool(self.events)
        primary_color = None
        extra_colors = []
        if has_events:
            seen = []
            for e in self.events:
                ct = e["type"]
                if ct not in seen and len(seen) < 3:
                    seen.append(ct)
                    extra_colors.append(EVENT_TYPE_COLORS.get(ct, Theme.ACCENT))
            primary_color = extra_colors[0]

        cx = rect.center().x()
        cy = rect.center().y() - 6
        circle_r = min(rect.width(), rect.height()) * 0.32

        if self.is_selected:
            sel = QColor(Theme.ACCENT)
            sel.setAlpha(22)
            painter.fillRect(rect, sel)
            pen = QPen(_c(Theme.ACCENT, 60), 1)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 4, 4)

        if self.is_today and not has_events:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(Theme.ACCENT)))
            painter.drawEllipse(QRectF(cx - circle_r, cy - circle_r, circle_r * 2, circle_r * 2))
            painter.setPen(QPen(Qt.GlobalColor.white))

        elif has_events:
            c = QColor(primary_color)
            painter.setPen(Qt.PenStyle.NoPen)
            glow = QColor(c)
            glow.setAlpha(20)
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(QRectF(cx - circle_r - 3, cy - circle_r - 3,
                                       circle_r * 2 + 6, circle_r * 2 + 6))
            painter.setBrush(QBrush(c))
            painter.drawEllipse(QRectF(cx - circle_r, cy - circle_r, circle_r * 2, circle_r * 2))

            if self.is_today:
                ring = QPen(QColor(Theme.ACCENT), 2)
                painter.setPen(ring)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(QRectF(cx - circle_r - 1, cy - circle_r - 1,
                                           circle_r * 2 + 2, circle_r * 2 + 2))

            if len(extra_colors) > 1:
                for i, ec in enumerate(extra_colors[1:], 1):
                    angle = 90 + i * 60
                    rad = math.radians(angle)
                    dx = cx + (circle_r + 2) * math.cos(rad)
                    dy = cy + (circle_r + 2) * math.sin(rad)
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QBrush(QColor(ec)))
                    painter.drawEllipse(QRectF(dx - 3, dy - 3, 6, 6))

            painter.setPen(QPen(Qt.GlobalColor.white))

        else:
            painter.setPen(QPen(
                _c(Theme.TEXT_PRIMARY, 180 if self.is_current_month else 80)
            ))

        painter.setFont(Theme.font(10, bold=(self.is_today or has_events)))
        tw = QFontMetrics(painter.font()).horizontalAdvance(str(self.day))
        painter.drawText(int(cx - tw / 2), int(cy + 5), str(self.day))

        painter.end()

    def mousePressEvent(self, event):
        self.clicked.emit(self.day)

    def enterEvent(self, event):
        self.update()

    def leaveEvent(self, event):
        self.update()


class MonthHeader(QWidget):
    prev_clicked = Signal()
    next_clicked = Signal()
    today_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(64)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        painter.fillRect(rect, QColor(Theme.BG_SECONDARY))

        painter.setPen(QPen(_c(Theme.DIVIDER, 80), 1))
        painter.drawLine(0, rect.height() - 1, rect.width(), rect.height() - 1)

        painter.end()

    def mousePressEvent(self, event):
        x = event.position().x()
        w = self.width()
        if x < 50:
            self.prev_clicked.emit()
        elif x > w - 50:
            self.next_clicked.emit()
        elif w / 2 - 60 < x < w / 2 + 60:
            self.today_clicked.emit()


class DayHeader(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(HEADER_HEIGHT)
        self.days = ["日", "一", "二", "三", "四", "五", "六"]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        painter.fillRect(rect, QColor(Theme.BG_SECONDARY))

        painter.setFont(Theme.caption())
        cell_w = rect.width() / 7
        for i, d in enumerate(self.days):
            x = int(i * cell_w + cell_w / 2)
            c = Theme.DANGER if i in (0, 6) else Theme.TEXT_MUTED
            painter.setPen(QPen(QColor(c), 1))
            painter.drawText(QRectF(i * cell_w, 0, cell_w, rect.height()),
                             Qt.AlignmentFlag.AlignCenter, d)

        painter.setPen(QPen(_c(Theme.DIVIDER, 60), 1))
        painter.drawLine(0, rect.height() - 1, rect.width(), rect.height() - 1)
        painter.end()


class CalendarView(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("view")

        self._current_date = date.today()
        self._display_year = self._current_date.year
        self._display_month = self._current_date.month
        self._selected_day = date.today().day
        self._all_events = sky.get_all_events()
        self._moon = sky.get_moon_phase()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._build_nav_bar(layout)
        self._build_calendar_layout(layout)
        self._build_event_panel(layout)
        self._build_pro_section(layout)

    # ── 导航栏 ──
    def _build_nav_bar(self, parent):
        nav = QFrame()
        nav.setFixedHeight(56)
        nav.setStyleSheet(f"background: {Theme.BG_SECONDARY}; border-bottom: 1px solid {Theme.DIVIDER};")

        nav_layout = QHBoxLayout(nav)
        nav_layout.setContentsMargins(28, 0, 28, 0)
        nav_layout.setSpacing(12)

        self.prev_btn = QPushButton("◀")
        self.prev_btn.setFixedSize(36, 32)
        self.prev_btn.setStyleSheet(self._nav_btn_style())
        self.prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_btn.clicked.connect(self._prev_month)
        nav_layout.addWidget(self.prev_btn)

        self.month_label = QLabel()
        self.month_label.setFont(Theme.h1())
        self.month_label.setStyleSheet(f"color: {Theme.TEXT_PRIMARY};")
        nav_layout.addWidget(self.month_label)

        self.next_btn = QPushButton("▶")
        self.next_btn.setFixedSize(36, 32)
        self.next_btn.setStyleSheet(self._nav_btn_style())
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.clicked.connect(self._next_month)
        nav_layout.addWidget(self.next_btn)

        nav_layout.addStretch()

        self.today_btn = QPushButton("今日")
        self.today_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Theme.ACCENT}; color: white; border: none;
                border-radius: 14px; padding: 6px 18px; font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {Theme.ACCENT_DEEP}; }}
        """)
        self.today_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.today_btn.clicked.connect(self._go_today)
        nav_layout.addWidget(self.today_btn)

        self.moon_indicator = QLabel()
        self.moon_indicator.setFont(Theme.body())
        self.moon_indicator.setStyleSheet(f"color: {Theme.STAR_GOLD};")
        nav_layout.addWidget(self.moon_indicator)

        parent.addWidget(nav)

    def _nav_btn_style(self):
        return f"""
            QPushButton {{
                background: {Theme.BG_CARD}; color: {Theme.TEXT_SECONDARY};
                border: 1px solid {Theme.DIVIDER}; border-radius: 6px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: {Theme.ACCENT_DIM}; color: {Theme.ACCENT};
            }}
        """

    # ── 日历网格 ──
    def _build_calendar_layout(self, parent):
        container = QWidget()
        container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        container.setStyleSheet(f"background: {Theme.BG_PRIMARY};")

        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(28, 0, 28, 0)
        vbox.setSpacing(0)

        dh = DayHeader()
        vbox.addWidget(dh)

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(1)
        vbox.addWidget(self.grid_widget)

        parent.addWidget(container)
        self._render_month()

    def _render_month(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        y, m = self._current_date.year, self._current_date.month
        first_day = date(y, m, 1)
        if m == 12:
            last_day = date(y + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(y, m + 1, 1) - timedelta(days=1)

        start_weekday = first_day.weekday()
        start_col = (start_weekday + 1) % 7

        today = date.today()
        events_by_day = self._group_events_by_day(y, m)

        day = 1
        for row in range(6):
            has_cells = False
            for col in range(7):
                if (row == 0 and col < start_col) or day > last_day.day:
                    placeholder = QWidget()
                    placeholder.setFixedSize(CELL_SIZE, CELL_SIZE)
                    self.grid_layout.addWidget(placeholder, row, col)
                    continue

                has_cells = True
                d = date(y, m, day)
                is_today = d == today
                cell = CalendarCell(day, is_today, True)
                cell.events = events_by_day.get(day, [])
                cell.is_selected = (day == self._selected_day and
                                    y == self._display_year and m == self._display_month)
                cell.clicked.connect(self._on_day_clicked)
                self.grid_layout.addWidget(cell, row, col)
                day += 1

            if not has_cells:
                break

        self._update_header()

    def _group_events_by_day(self, year, month):
        grouped = {}
        for e in self._all_events:
            try:
                d = datetime.strptime(e["date"], "%Y-%m-%d")
                if d.year == year and d.month == month:
                    day = d.day
                    grouped.setdefault(day, []).append(e)
            except ValueError:
                continue
        return grouped

    # ── 事件列表面板 ──
    def _build_event_panel(self, parent):
        self.event_panel = QFrame()
        self.event_panel.setStyleSheet(f"background: {Theme.BG_SECONDARY};")
        self.event_panel.setSizePolicy(QSizePolicy.Policy.Expanding,
                                       QSizePolicy.Policy.Expanding)

        panel_layout = QVBoxLayout(self.event_panel)
        panel_layout.setContentsMargins(28, 4, 28, 12)
        panel_layout.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(Theme.scroll_style())
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.event_list = QWidget()
        self.event_list_layout = QVBoxLayout(self.event_list)
        self.event_list_layout.setContentsMargins(0, 0, 0, 0)
        self.event_list_layout.setSpacing(6)
        self.event_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.event_list)

        panel_layout.addWidget(scroll)
        parent.addWidget(self.event_panel, 1)

    def _update_event_list(self):
        while self.event_list_layout.count():
            item = self.event_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        y, m = self._current_date.year, self._current_date.month
        try:
            sel_date = date(y, m, self._selected_day)
        except ValueError:
            sel_date = date.today()

        sel_title = QLabel(f"📅 {sel_date.strftime('%m月%d日  %A')}")
        sel_title.setFont(Theme.h3())
        sel_title.setStyleSheet(f"color: {Theme.TEXT_PRIMARY}; padding: 4px 0;")
        self.event_list_layout.addWidget(sel_title)

        events = self._group_events_by_day(y, m).get(self._selected_day, [])
        if events:
            for e in events:
                self.event_list_layout.addWidget(self._make_event_card(e, show_hemi=True))
        else:
            empty = QFrame()
            empty.setObjectName("card")
            empty.setStyleSheet(Theme.card_style())
            empty.setFixedHeight(60)
            el = QHBoxLayout(empty)
            lbl = QLabel("🌠 当天没有天文事件")
            lbl.setFont(Theme.body())
            lbl.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            el.addWidget(lbl)
            self.event_list_layout.addWidget(empty)

        self.event_list_layout.addSpacing(16)

        self.event_list_layout.addWidget(self._make_today_section())

        upcoming = sky.get_upcoming_events(30)
        if upcoming:
            upcoming_title = QLabel("📆 未来一个月内可观测事件")
            upcoming_title.setFont(Theme.h3())
            upcoming_title.setStyleSheet(
                f"color: {Theme.TEXT_PRIMARY}; padding: 8px 0 4px;"
            )
            self.event_list_layout.addWidget(upcoming_title)

            user_hemi = get_visible_hemisphere(config.latitude)
            for e in upcoming:
                card = self._make_event_card(e, show_hemi=True)
                self.event_list_layout.addWidget(card)

        self.event_list_layout.addStretch()

    def _make_event_card(self, event, show_hemi=False):
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(Theme.card_style())
        card.setFixedHeight(60)

        color = EVENT_TYPE_COLORS.get(event["type"], Theme.ACCENT)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        accent = QFrame()
        accent.setFixedWidth(4)
        accent.setStyleSheet(f"background: {color}; border-radius: 2px;")
        layout.addWidget(accent)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)

        title = QLabel(event["title"])
        title.setFont(Theme.font(13, bold=True))
        title.setStyleSheet(f"color: {Theme.TEXT_PRIMARY};")
        text_layout.addWidget(title)

        meta_parts = [f"{event['date']}  ·  {event['type']}"]
        if show_hemi:
            hemi = get_hemisphere_label(event["title"])
            hemi_symbol = "🌏" if hemi == "全球" else ("⬆️" if hemi == "北半球" else "⬇️")
            meta_parts.append(f"{hemi_symbol} {hemi}")
        meta = QLabel("  ·  ".join(meta_parts))
        meta.setFont(Theme.caption())
        meta.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        text_layout.addWidget(meta)

        layout.addLayout(text_layout, 1)

        badge = QLabel(event["type"])
        badge.setFont(Theme.caption())
        badge.setStyleSheet(f"""
            background: {color}22; color: {color};
            border: 1px solid {color}44; border-radius: 4px;
            padding: 2px 8px;
        """)
        layout.addWidget(badge)

        if show_hemi:
            hemi_color = Theme.SUCCESS if hemi == get_visible_hemisphere(config.latitude) else Theme.WARNING
            hemi_label = QLabel(hemi)
            hemi_label.setFont(Theme.caption())
            hemi_label.setStyleSheet(f"""
                background: {hemi_color}18; color: {hemi_color};
                border: 1px solid {hemi_color}30; border-radius: 4px;
                padding: 2px 6px; font-size: 10px;
            """)
            layout.addWidget(hemi_label)

        return card

    def _make_today_section(self):
        section = QFrame()
        section.setObjectName("card")
        section.setStyleSheet(Theme.card_style())
        layout = QVBoxLayout(section)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        today = date.today()
        title = QLabel(f"🔭 今日观测 · {config.city_name}")
        title.setFont(Theme.font(13, bold=True))
        title.setStyleSheet(f"color: {Theme.ACCENT};")
        layout.addWidget(title)

        lines = []

        # ── 可见行星（望远镜推荐） ──
        try:
            planets = sky.get_planet_positions()
            visible = [p for p in planets if p.get("altitude", 0) > 15]
            if visible:
                names = "、".join(p["name"] for p in visible[:3])
                lines.append(f"🔭 望远镜目标: {names}")
        except Exception:
            pass

        # ── 今日天象 ──
        try:
            today_events = [e for e in self._all_events if e["date"] == today.strftime("%Y-%m-%d")]
            for e in today_events:
                lines.append(f"🌠 {e['title']} ({e['type']})")
        except Exception:
            pass

        # ── 月相提示 ──
        try:
            moon = getattr(self, '_moon', {}) or sky.get_moon_phase()
            mp = moon.get("phase", 0)
            icon = moon.get("icon", "🌙")
            name = moon.get("name", "")
            if abs(mp - 0.5) > 0.3:
                lines.append(f"{icon} {name} · 月光偏亮，不适合深空观测")
            else:
                lines.append(f"{icon} {name} · 月光干扰小，适合深空观测")
        except Exception:
            pass

        for line in lines:
            lbl = QLabel(line)
            lbl.setFont(Theme.font(11))
            lbl.setStyleSheet(f"color: {Theme.TEXT_SECONDARY};")
            lbl.setWordWrap(True)
            layout.addWidget(lbl)

        # ── 卫星当前位置 / 推荐观星地（联网 + 重计算，后台加载） ──
        sat_lbl = QLabel("🛸 正在获取卫星与观星地信息...")
        sat_lbl.setFont(Theme.font(11))
        sat_lbl.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        sat_lbl.setWordWrap(True)
        layout.addWidget(sat_lbl)

        def _fetch():
            sat_lines = []
            try:
                sats = sky.get_satellite_positions()
                for sat_id, sat_name in [(25544, "ISS"), (48274, "天宫")]:
                    for s in sats:
                        if s.get("norad") == sat_id:
                            alt = s.get("altitude", -90)
                            icon = "🛸" if sat_id == 25544 else "🇨🇳"
                            if alt > 0:
                                az = s.get("azimuth", 0)
                                dirs = ["北", "东北", "东", "东南", "南", "西南", "西", "西北"]
                                d = dirs[int((az + 22.5) / 45) % 8]
                                sat_lines.append(f"{icon} {sat_name} 可见  Alt {alt:.0f}°  {d}方")
                            else:
                                sat_lines.append(f"{icon} {sat_name} 地平线下")
                            break
            except Exception:
                pass
            site_lines = []
            try:
                sites = get_nearby_sites()
                if sites:
                    site_lines.append("📍 推荐观星地点:")
                    for sname, dist, lp, sicon in sites:
                        site_lines.append(f"  {sicon} {sname}  {dist}km  {lp}")
            except Exception:
                pass
            return sat_lines, site_lines

        def _on_done(res):
            try:
                sat_lines, site_lines = res
                if sat_lines or site_lines:
                    sat_lbl.setText("\n".join(sat_lines + site_lines))
                    sat_lbl.setStyleSheet(f"color: {Theme.TEXT_SECONDARY};")
                else:
                    sat_lbl.setText("今日无特别天象 / 卫星数据不可用")
                    sat_lbl.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
            except Exception:
                pass

        from app.core.background_worker import run_in_background
        run_in_background(_fetch, on_finished=_on_done, on_error=lambda e: None)

        return section

    # ── 专业模式 ──
    def _build_pro_section(self, parent):
        self.pro_section = QFrame()
        pro_layout = QVBoxLayout(self.pro_section)
        pro_layout.setContentsMargins(28, 8, 28, 8)

        pro_header = QLabel("🔬 专业模式 · 事件统计数据")
        pro_header.setFont(Theme.h3())
        pro_header.setStyleSheet(f"color: {Theme.STAR_GOLD};")
        pro_layout.addWidget(pro_header)

        type_counts = {}
        for e in self._all_events:
            t = e["type"]
            type_counts[t] = type_counts.get(t, 0) + 1
        stats = "  ".join(f"{t}: {c}" for t, c in type_counts.items())
        stats += f"  |  总计: {len(self._all_events)} 个"
        self.pro_info = QLabel(stats)
        self.pro_info.setFont(Theme.body())
        self.pro_info.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        self.pro_info.setWordWrap(True)
        pro_layout.addWidget(self.pro_info)

        parent.addWidget(self.pro_section)
        self.pro_section.setVisible(config.is_pro)

    # ── 交互 ──
    def _on_day_clicked(self, day):
        self._selected_day = day
        self._render_month()
        self._update_event_list()

    def _prev_month(self):
        y, m = self._current_date.year, self._current_date.month
        if m == 1:
            self._current_date = date(y - 1, 12, 1)
        else:
            self._current_date = date(y, m - 1, 1)
        self._selected_day = 1
        self._render_month()
        self._update_event_list()

    def _next_month(self):
        y, m = self._current_date.year, self._current_date.month
        if m == 12:
            self._current_date = date(y + 1, 1, 1)
        else:
            self._current_date = date(y, m + 1, 1)
        self._selected_day = 1
        self._render_month()
        self._update_event_list()

    def _go_today(self):
        self._current_date = date.today()
        self._selected_day = date.today().day
        self._render_month()
        self._update_event_list()

    def _update_header(self):
        self.month_label.setText(
            f"{self._current_date.year}年 {self._current_date.month}月"
        )
        self.moon_indicator.setText(
            f"{self._moon['icon']} {self._moon['name']}  "
            f"照明 {self._moon['illumination']}"
        )

    # ── 生命周期 ──
    def on_show(self):
        self._moon = sky.get_moon_phase()
        self._update_header()
        self._update_event_list()

    def on_mode_changed(self, mode):
        self.pro_section.setVisible(mode == "professional")
