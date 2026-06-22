import math
import random
import traceback
from urllib.parse import quote
from datetime import datetime

STAR_DATA = {
    "天狼星": ("A1V", 8.6, "蓝白", "sirius"), "老人星": ("F0II", 310, "黄白", "canopus"),
    "大角星": ("K0III", 37, "橙黄", "arcturus"), "织女星": ("A0V", 25, "蓝白", "vega"),
    "五车二": ("G3III", 43, "黄白", "capella"), "参宿七": ("B8Ia", 860, "蓝白", "rigel"),
    "南河三": ("F5IV-V", 11, "黄白", "procyon"), "参宿四": ("M2Iab", 640, "红", "betelgeuse"),
    "水委一": ("B6V", 144, "蓝白", "achernar"), "牛郎星": ("A7V", 17, "黄白", "altair"),
    "毕宿五": ("K5III", 65, "橙红", "aldebaran"), "角宿一": ("B1V", 250, "蓝白", "spica"),
    "心宿二": ("M1.5Iab", 550, "红", "antares"), "北河三": ("K0III", 34, "橙黄", "pollux"),
    "北落师门": ("A3V", 25, "黄白", "fomalhaut"), "天津四": ("A2Ia", 2600, "蓝白", "deneb"),
    "轩辕十四": ("B7V", 79, "蓝白", "regulus"), "土司空": ("K0III", 39, "橙黄", "diphda"),
    "马腹一": ("B1III", 490, "蓝白", "hadar"), "十字架二": ("B0.5IV", 320, "蓝白", "acrux"),
    "尾宿八": ("B2IV", 470, "蓝白", "shaula"),
    "北斗一": ("A1V", 83, "蓝白", "dubhe"), "北斗二": ("A0V", 80, "蓝白", "merak"),
    "北斗三": ("A1V", 89, "蓝白", "phecda"), "北斗四": ("A0V", 130, "蓝白", "megrez"),
    "北斗五": ("F0V", 90, "黄白", "alioth"), "北斗六": ("F8V", 44, "黄白", "mizar"),
    "北斗七": ("A1V", 83, "蓝白", "alkaid"),
    "辇道增七": ("K0III", 380, "橙黄", "albireo"), "渐台二": ("M3II", 1200, "红", "sheliak"),
    "天大将军": ("K2III", 220, "橙", "almach"),
}

PLANET_DATA_INFO = {
    "水星": ("类地行星", 4879, "最小行星"), "金星": ("类地行星", 12104, "最热行星"),
    "火星": ("类地行星", 6792, "红色星球"), "木星": ("气态巨行星", 142984, "最大行星"),
    "土星": ("气态巨行星", 120536, "有光环"), "天王星": ("冰巨行星", 51118, "侧躺自转"),
    "海王星": ("冰巨行星", 49528, "最远行星"),
}


from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, QRect, Signal, QElapsedTimer
from PySide6.QtGui import (QPainter, QColor, QPen, QBrush, QLinearGradient,
                           QRadialGradient, QFont, QPainterPath, QFontMetrics,
                           QMouseEvent, QWheelEvent)

from app.theme import Theme
from app.config import config
from app.api.astronomy_api import sky, DEVICE_CONFIGS, compute_satellites_bg


def _c(hex_color, alpha=255):
    c = QColor(hex_color)
    if alpha < 255:
        c.setAlpha(alpha)
    return c


_GRADIENT_CACHE_LIMIT = 256

def _get_gradient(cache, key, factory):
    if key not in cache:
        if len(cache) >= _GRADIENT_CACHE_LIMIT:
            cache.pop(next(iter(cache)))
        cache[key] = factory()
    return cache[key]


def _make_glow(color, radius, alpha=40):
    g = QRadialGradient(QPointF(0, 0), radius)
    c = QColor(color)
    g.setColorAt(0, QColor(c.red(), c.green(), c.blue(), alpha))
    g.setColorAt(1, QColor(c.red(), c.green(), c.blue(), 0))
    g.setCoordinateMode(QRadialGradient.CoordinateMode.ObjectBoundingMode)
    return g


HOVER_RADIUS = 12


class StarChart(QWidget):
    mode_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(500, 400)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._stars = []
        self._planets = []
        self._sun = None
        self._moon = None
        self._satellites = []
        self._aircraft = []
        self._aircraft_warnings = []
        self._dsos = []
        self._const_lines = {}
        self._time_offset = 0

        self._view_scale = 1.0
        self._view_offset = QPointF(0, 0)
        self._min_scale = 0.3
        self._max_scale = 8.0
        self._is_panning = False
        self._pan_start = QPointF(0, 0)
        self._pan_offset_start = QPointF(0, 0)

        self._hit_stars = []
        self._hit_planets = []
        self._hit_suns = []
        self._hit_moons = []
        self._hit_satellites_list = []
        self._hit_aircraft = []
        self._hit_dsos = []
        self._hovered_obj = None
        self._selected_obj = None
        self._mouse_pos = None

        self._device_index = 0
        self._device_config = DEVICE_CONFIGS[0]

        self._camera_fov = None
        self._fov_center = QPointF(0, 0)
        self._fov_dragging = False
        self._fov_drag_start = QPointF(0, 0)
        self._fov_center_start = QPointF(0, 0)

        self._show_stars = True
        self._show_planets = True
        self._show_sun_moon = True
        self._show_satellites = True
        self._show_aircraft = True
        self._show_dso = True
        self._show_dso_nebula = True
        self._show_dso_cluster = True
        self._show_dso_galaxy = True
        self._show_constellations = True
        self._show_fov = True

        self._gradient_cache = {}
        self._last_paint_ms = 0
        self._frame_skip_counter = 0

        self._anim_timer = QTimer()
        self._anim_timer.timeout.connect(self._tick)
        self._anim_timer.start(1000)

        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self.refresh)

        self._zoom_label_timer = QTimer()
        self._zoom_label_timer.setSingleShot(True)
        self._zoom_label_timer.timeout.connect(lambda: setattr(self, '_show_zoom_label', False) or self.update())
        self._show_zoom_label = False

        self._info_panel_rect = QRectF()
        self._drag_threshold = 5
        self._press_pos = None

        self._elapsed = QElapsedTimer()

        QTimer.singleShot(0, self._deferred_init)

    def set_camera_fov(self, params):
        self._camera_fov = params
        self.update()

    def set_show(self, key, value):
        setattr(self, f"_show_{key}", value)
        self.update()

    def _deferred_init(self):
        self.refresh()
        self._refresh_timer.start(600000)
        self._network_timer = QTimer()
        self._network_timer.timeout.connect(self._refresh_network)
        self._network_timer.start(600000)
        QTimer.singleShot(3000, self._refresh_network)

    def set_device(self, index):
        self._device_index = index
        self._device_config = DEVICE_CONFIGS[index]
        self.refresh()

    def refresh(self):
        dt = datetime.now()
        self._stars = sky.get_bright_stars_altaz(dt, self._device_config["mag_limit"])
        self._planets = sky.get_planet_positions(dt)
        self._sun = sky.get_sun_position(dt)
        self._moon = sky.get_moon_position(dt)
        self._satellites = sky.get_satellite_positions(dt) if config.is_pro else []
        self._const_lines = sky.get_constellation_lines()
        self._dsos = sky.get_dso_list()
        self._dso_visibility = sky.get_dso_visibility(dt) if config.is_pro else []
        self.update()

    def _refresh_network(self):
        """Refresh satellite + aircraft data in background threads."""
        if not config.is_pro:
            return
        from app.core.background_worker import run_in_background
        dt = datetime.now()

        # ── Satellite positions (heavy TLE computation) ──
        bg_data = sky.get_satellite_positions_bg(dt)
        run_in_background(
            target=compute_satellites_bg,
            args=(bg_data,),
            on_finished=lambda res: self._on_satellites_done(res) if res else None,
        )

        # ── Aircraft data (network I/O) ──
        self._aircraft = []
        self._aircraft_warnings = []
        if config.pro_settings.get("show_iss_track", True):
            run_in_background(
                target=self._fetch_aircraft_bg,
                args=(dt,),
                on_finished=lambda res: self._on_aircraft_done(res) if res else None,
            )

    def _on_satellites_done(self, results):
        self._satellites = results
        self.update()

    def _fetch_aircraft_bg(self, dt):
        from app.api.adsb_api import fetch_aircraft, add_aircraft_trajectories, fetch_aircraft_registrations
        try:
            ac = fetch_aircraft(dt)
            if ac:
                add_aircraft_trajectories(ac)
                fetch_aircraft_registrations(ac)
            return ac
        except Exception:
            return None

    def _on_aircraft_done(self, results):
        if results is not None:
            self._aircraft = results
            self._aircraft_warnings = []
            self.update()

    def _tick(self):
        self._time_offset += 0.25
        if self._last_paint_ms > 40:
            self._frame_skip_counter = (self._frame_skip_counter + 1) % 3
            if self._frame_skip_counter != 0:
                return
        self.update()

    # =========================================================================
    # 坐标转换
    # =========================================================================
    def _sky_to_screen(self, alt_deg, az_deg, cx, cy, radius):
        alt_norm = max(0.01, alt_deg / 90.0)
        r = radius * math.sqrt(alt_norm)
        rx = r * math.sin(math.radians(az_deg))
        ry = -r * math.cos(math.radians(az_deg))
        return QPointF(cx + rx, cy + ry)

    def _apply_view(self, cx, cy, radius):
        ecx = cx + self._view_offset.x()
        ecy = cy + self._view_offset.y()
        erad = radius * self._view_scale
        return ecx, ecy, erad

    def _screen_to_sky(self, sx, sy, cx, cy, radius):
        ecx, ecy, erad = self._apply_view(cx, cy, radius)
        dx = sx - ecx
        dy = sy - ecy
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > erad or dist < 1:
            return None
        alt_deg = 90.0 * (dist / erad) ** 2
        az_deg = math.degrees(math.atan2(dx, -dy)) % 360
        return {"altitude": alt_deg, "azimuth": az_deg}

    # =========================================================================
    # 事件处理
    # =========================================================================
    def wheelEvent(self, event: QWheelEvent):
        old_scale = self._view_scale
        factor = 1.1 if event.angleDelta().y() > 0 else 1 / 1.1
        new_scale = max(self._min_scale, min(self._max_scale, old_scale * factor))
        self._view_scale = new_scale
        self._show_zoom_label = True
        self._zoom_label_timer.start(1500)
        self.update()

    def _get_fov_rect(self):
        if not self._camera_fov or not self._camera_fov.get("show"):
            return None
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        radius = min(w, h) * 0.42
        ecx, ecy, erad = self._apply_view(cx, cy, radius)
        fx = ecx + self._fov_center.x()
        fy = ecy + self._fov_center.y()
        fov_h = self._camera_fov.get("fov_h_deg", 1)
        fov_v = self._camera_fov.get("fov_v_deg", 1)
        half_w = erad * (fov_h / 90.0) * 1.5
        half_h = erad * (fov_v / 90.0) * 1.5
        return QRectF(fx - half_w, fy - half_h, half_w * 2, half_h * 2)

    def mousePressEvent(self, event: QMouseEvent):
        self._press_pos = event.position()
        if event.button() == Qt.MouseButton.LeftButton:
            fr = self._get_fov_rect()
            if fr and fr.contains(event.position()):
                self._fov_dragging = True
                self._fov_drag_start = event.position()
                self._fov_center_start = QPointF(self._fov_center)
                return
            self._pan_start = event.position()
            self._pan_offset_start = QPointF(self._view_offset)
            self._is_panning = False

    def mouseMoveEvent(self, event: QMouseEvent):
        self._mouse_pos = event.position()
        pos = event.position()

        if self._fov_dragging:
            delta = pos - self._fov_drag_start
            self._fov_center = QPointF(
                self._fov_center_start.x() + delta.x(),
                self._fov_center_start.y() + delta.y()
            )
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.update()
            return

        if self._press_pos and (pos - self._press_pos).manhattanLength() > self._drag_threshold:
            self._is_panning = True

        if self._is_panning:
            delta = pos - self._pan_start
            self._view_offset = QPointF(
                self._pan_offset_start.x() + delta.x(),
                self._pan_offset_start.y() + delta.y()
            )
            self.update()
        else:
            fr = self._get_fov_rect()
            if fr and fr.contains(pos):
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            hit = self._hit_test(pos)
            if hit != self._hovered_obj:
                self._hovered_obj = hit
                self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._fov_dragging:
            self._fov_dragging = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return
        if event.button() == Qt.MouseButton.LeftButton:
            if not self._is_panning and self._press_pos:
                pos = event.position()
                hit = self._hit_test(pos)
                if hit:
                    self._selected_obj = hit if hit != self._selected_obj else None
                else:
                    self._selected_obj = None
                self.update()
            self._is_panning = False
            self._press_pos = None

    def _get_image_url(self, obj):
        obj_type = obj.get("type", "")
        if obj_type == "dso":
            dso_id = obj.get("id", "")
            if dso_id:
                return f"https://aladin.cds.unistra.fr/AladinLite/?target={dso_id}&fov=0.5&survey=CDS%2FP%2FDSS2%2Fcolor"
        elif obj_type == "star":
            name = obj.get("name", "")
            sd = STAR_DATA.get(name)
            if sd and sd[3]:
                return f"https://starfyi.com/zh-hans/star/{sd[3]}/"
            if name:
                return f"https://baike.baidu.com/item/{quote(name)}"
        elif obj_type == "planet":
            name = obj.get("name", "")
            if name:
                return f"https://baike.baidu.com/item/{quote(name)}"
        elif obj_type == "sun":
            return "https://soho.nascom.nasa.gov/data/realtime/hmi_igr/1024/latest.jpg"
        elif obj_type == "moon":
            return "https://lroc.sese.asu.edu/images/latest/thumbnail.jpg"
        elif obj_type == "satellite":
            norad = obj.get("norad", 0)
            if norad:
                return f"https://www.n2yo.com/satellite/?s={norad}"
        elif obj_type == "aircraft":
            reg = obj.get("registration", "")
            if reg:
                return f"https://www.jetphotos.com/registration/{reg}"
            icao = obj.get("icao", "")
            if icao:
                return f"https://www.jetphotos.com/photo/keyword={icao}"
        return None

    def guide_goto(self, alt, az):
        """Rotate view to center on given altitude/azimuth."""
        self._view_scale = 2.0
        self._view_offset = QPointF(0, 0)
        self._fov_center = QPointF(0, 0)
        w, h = self.width(), self.height()
        if w > 10 and h > 10:
            cx, cy = w / 2, h / 2
            radius = min(w, h) * 0.42
            ecx, ecy, erad = self._apply_view(cx, cy, radius)
            p = self._sky_to_screen(alt, az, ecx, ecy, erad)
            dx = p.x() - cx
            dy = p.y() - cy
            self._view_offset = QPointF(-dx, -dy)
        self.update()

    def mouseDoubleClickEvent(self, event):
        pos = event.position()
        hit = self._hit_test(pos)
        if hit:
            url = self._get_image_url(hit)
            if url:
                import webbrowser
                webbrowser.open(url)
                return
        self._view_scale = 1.0
        self._view_offset = QPointF(0, 0)
        self.refresh()
        self._show_zoom_label = True
        self._zoom_label_timer.start(1500)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_R:
            self._view_scale = 1.0
            self._view_offset = QPointF(0, 0)
            self.refresh()
            self._show_zoom_label = True
            self._zoom_label_timer.start(1500)
            self.update()

    # =========================================================================
    # 碰撞检测
    # =========================================================================
    def _hit_test(self, pos):
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        radius = min(w, h) * 0.42

        best = None
        best_dist = HOVER_RADIUS * 2

        for item in self._hit_suns + self._hit_moons + self._hit_satellites_list + self._hit_aircraft + self._hit_planets + self._hit_stars + self._hit_dsos:
            d = (QPointF(item["sx"], item["sy"]) - pos).manhattanLength()
            if d < best_dist:
                best_dist = d
                best = item

        return best

    def _make_tooltip(self, obj):
        lines = [f"<b>{obj.get('name', '?')}</b>"]
        obj_type = obj.get("type", "")
        if obj_type == "sun":
            lines.append("☀️ 太阳")
        elif obj_type == "moon":
            ph = obj.get("phase", {})
            if ph:
                lines.append(f"{ph.get('icon', '🌙')} {ph.get('name', '')}")
        if "mag" in obj:
            lines.append(f"星等: {obj['mag']}")
        if "magnitude" in obj:
            lines.append(f"星等: {obj['magnitude']}")
        lines.append(f"高度: {obj['altitude']:.1f}°")
        lines.append(f"方位: {obj['azimuth']:.1f}°")
        if obj_type == "satellite" and obj.get("distance_km"):
            lines.append(f"距离: {obj['distance_km']:.0f} km")
        if obj_type == "aircraft":
            if obj.get("airline"):
                lines.append(f"航司: {obj['airline']}")
            lines.append(f"高度: {obj.get('altitude_ft', 0):.0f} ft")
            lines.append(f"速度: {obj.get('velocity_kmh', 0):.0f} km/h")
            lines.append(f"距离: {obj.get('distance_km', 0):.1f} km")
            lines.append(f"航向: {obj.get('heading', 0):.0f}°")
            if obj.get("country"):
                lines.append(f"注册地: {obj['country']}")
        if "ra" in obj and config.is_pro:
            lines.append(f"RA: {obj['ra']:.2f}h  Dec: {obj['dec']:.1f}°")
        return "<br>".join(lines)

    # =========================================================================
    # 绘制
    # =========================================================================
    def paintEvent(self, event):
        self._elapsed.start()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        radius = min(w, h) * 0.42

        if h > 0:
            gradient = QLinearGradient(0, 0, 0, h)
            gradient.setColorAt(0.0, QColor("#050812"))
            gradient.setColorAt(0.3, QColor("#0A1025"))
            gradient.setColorAt(0.7, QColor("#0D1530"))
            gradient.setColorAt(1.0, QColor("#080C1A"))
            painter.fillRect(self.rect(), gradient)

        self._hit_stars.clear()
        self._hit_planets.clear()
        self._hit_suns.clear()
        self._hit_moons.clear()
        self._hit_satellites_list.clear()
        self._hit_aircraft.clear()
        self._hit_dsos.clear()

        try:
            self._draw_zenith_marker(painter, cx, cy, radius)
            self._draw_grid(painter, cx, cy, radius)
            if self._show_constellations:
                self._draw_constellation_lines(painter, cx, cy, radius)
            self._draw_background_stars(painter, cx, cy, radius)
            if self._show_stars:
                self._draw_stars(painter, cx, cy, radius)
            if self._show_sun_moon:
                self._draw_sun(painter, cx, cy, radius)
                self._draw_moon(painter, cx, cy, radius)
            if self._show_satellites:
                self._draw_satellites(painter, cx, cy, radius)
            self._draw_aircraft(painter, cx, cy, radius)
            self._draw_aircraft_warnings(painter)
            if self._show_planets:
                self._draw_planets(painter, cx, cy, radius)
            if self._show_dso:
                self._draw_dso(painter, cx, cy, radius)
            self._draw_camera_fov(painter, cx, cy, radius)
            self._draw_hover_highlight(painter)
        except Exception:
            traceback.print_exc()

        dc = self._device_config
        stars_info = f"{len(self._stars)} 颗恒星 (星等 ≤ {dc['mag_limit']})" if dc["mag_limit"] < 99 else "全部恒星"
        jd = sky.get_jd()
        mjd = sky.get_mjd()
        now = datetime.now()
        txt = (
            f"{dc['icon']} {dc['name']}  |  {stars_info}  |  "
            f"{config.city_name} {now.strftime('%H:%M:%S')}  |  "
            f"{self._view_scale:.1f}x"
        )
        painter.setPen(QPen(_c(Theme.TEXT_MUTED, 60), 1))
        painter.setFont(Theme.caption())
        painter.drawText(16, self.height() - 12, txt)

        if config.is_pro:
            painter.setPen(_c(Theme.TEXT_MUTED, 50))
            pro_info = f"JD {jd}  |  MJD {mjd}  |  Alt/Az 十字线"
            painter.drawText(16, self.height() - 2, pro_info)

        if self._mouse_pos and config.is_pro:
            self._draw_cursor_cross(painter, cx, cy, radius)

        if self._show_zoom_label:
            self._draw_zoom_indicator(painter, cx)

        try:
            if self._selected_obj:
                self._draw_info_panel(painter, cx, cy, radius)
            elif self._hovered_obj and not self._is_panning:
                self._draw_hover_info(painter)
        except Exception:
            traceback.print_exc()

        self._last_paint_ms = self._elapsed.elapsed()
        painter.end()

    # =========================================================================
    # 子绘制方法
    # =========================================================================
    def _draw_zenith_marker(self, painter, cx, cy, radius):
        ecx, ecy, erad = self._apply_view(cx, cy, radius)
        zoom = self._view_scale
        lw = max(1, int(1.5 / zoom))

        horizon_pen = QPen(_c(Theme.TEXT_PRIMARY, int(50 / zoom)), lw + 1)
        painter.setPen(horizon_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(ecx, ecy), erad, erad)

        grad = QRadialGradient(QPointF(ecx, ecy), erad)
        grad.setColorAt(0.92, _c(Theme.TEXT_PRIMARY, 0))
        grad.setColorAt(0.98, _c(Theme.TEXT_PRIMARY, 12))
        grad.setColorAt(1.0, _c(Theme.TEXT_PRIMARY, 0))
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(ecx, ecy), erad, erad)

        dash_pen = QPen(_c(Theme.TEXT_MUTED, int(35 / zoom)), lw, Qt.PenStyle.DashLine)
        painter.setPen(dash_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(ecx, ecy), erad * 0.7, erad * 0.7)
        painter.drawEllipse(QPointF(ecx, ecy), erad * 0.4, erad * 0.4)

        dir_size = max(4, int(8 / zoom))
        label_dist = erad + max(20, int(24 / zoom))
        tri_dist = erad - 2

        for angle_deg, label, color in [
            (0, "北", Theme.ACCENT),
            (90, "东", Theme.STAR_GOLD),
            (180, "南", Theme.WARNING),
            (270, "西", Theme.ACCENT),
        ]:
            rad = math.radians(angle_deg - 90)

            tx = ecx + tri_dist * math.cos(rad)
            ty = ecy + tri_dist * math.sin(rad)

            tri_color = _c(color, int(120 / zoom))
            painter.setBrush(QBrush(tri_color))
            painter.setPen(Qt.PenStyle.NoPen)

            if angle_deg == 0:
                pts = [QPointF(tx, ty - dir_size), QPointF(tx - dir_size * 0.6, ty + dir_size),
                       QPointF(tx + dir_size * 0.6, ty + dir_size)]
            elif angle_deg == 180:
                pts = [QPointF(tx, ty + dir_size), QPointF(tx - dir_size * 0.6, ty - dir_size),
                       QPointF(tx + dir_size * 0.6, ty - dir_size)]
            elif angle_deg == 90:
                pts = [QPointF(tx + dir_size, ty), QPointF(tx - dir_size, ty - dir_size * 0.6),
                       QPointF(tx - dir_size, ty + dir_size * 0.6)]
            else:
                pts = [QPointF(tx - dir_size, ty), QPointF(tx + dir_size, ty - dir_size * 0.6),
                       QPointF(tx + dir_size, ty + dir_size * 0.6)]
            painter.drawPolygon(pts)

            lx = ecx + label_dist * math.cos(rad)
            ly = ecy + label_dist * math.sin(rad)
            painter.setFont(Theme.font(max(10, int(12 / zoom)), bold=True))
            painter.setPen(QPen(_c(color, int(160 / zoom))))
            fm = QFontMetrics(painter.font())
            tw = fm.horizontalAdvance(label)
            painter.drawText(int(lx - tw / 2), int(ly + 5), label)

    def _draw_grid(self, painter, cx, cy, radius):
        if not config.is_pro:
            return
        ecx, ecy, erad = self._apply_view(cx, cy, radius)
        zoom = self._view_scale

        grid_pen = QPen(_c(Theme.RA_DEC_LINE, int(60 / zoom)), max(0.5, 0.5 / zoom), Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)

        for i in range(6):
            angle = i * 30
            rad = math.radians(angle - 90)
            x = ecx + erad * 0.85 * math.cos(rad)
            y = ecy + erad * 0.85 * math.sin(rad)
            painter.drawLine(QPointF(ecx, ecy), QPointF(x, y))

            lx = ecx + erad * 0.92 * math.cos(rad)
            ly = ecy + erad * 0.92 * math.sin(rad)
            painter.setPen(QPen(_c(Theme.RA_DEC_LINE, 80), 1))
            painter.drawText(int(lx - 10), int(ly + 4), f"{i * 2}h")

        for i in range(1, 4):
            r = erad * (i / 4.0)
            painter.setPen(grid_pen)
            painter.drawEllipse(QPointF(ecx, ecy), r, r)

    def _draw_constellation_lines(self, painter, cx, cy, radius):
        if self._view_scale > 3.0:
            return
        ecx, ecy, erad = self._apply_view(cx, cy, radius)
        pen = QPen(_c(Theme.ACCENT_DIM), max(0.8, 1.2 / self._view_scale), Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        star_pos = {}
        for s in self._stars:
            p = self._sky_to_screen(s["altitude"], s["azimuth"], ecx, ecy, erad)
            star_pos[s["name"]] = p

        for const_name, lines in self._const_lines.items():
            for ra1, dec1, ra2, dec2 in lines:
                s1 = s2 = None
                for s in self._stars:
                    if abs(s.get("ra", 0) - ra1) < 2 and abs(s.get("dec", 0) - dec1) < 5:
                        s1 = s["name"]
                    if abs(s.get("ra", 0) - ra2) < 2 and abs(s.get("dec", 0) - dec2) < 5:
                        s2 = s["name"]
                if s1 and s2 and s1 in star_pos and s2 in star_pos:
                    painter.drawLine(star_pos[s1], star_pos[s2])

    def _draw_background_stars(self, painter, cx, cy, radius):
        ecx, ecy, erad = self._apply_view(cx, cy, radius)

        if not hasattr(self, '_bg_stars'):
            bg = []
            random.seed(42)
            for _ in range(150):
                bg.append((
                    random.uniform(0.05, 1.0),
                    random.uniform(0, 360),
                    random.uniform(0.5, 1.8),
                    random.uniform(0.2, 0.6),
                ))
            self._bg_stars = bg

        background_stars = []
        for alt_r, az_r, size_r, bright_r in self._bg_stars:
            p = self._sky_to_screen(alt_r * 90, az_r, ecx, ecy, erad)
            if 0 < p.x() < self.width() and 0 < p.y() < self.height():
                background_stars.append((p.x(), p.y(), size_r, bright_r))

        twinkle = math.sin(self._time_offset) * 0.15 + 0.85
        for sx, sy, size, bright in background_stars:
            alpha = int(bright * twinkle * 180)
            color = QColor(200, 210, 230, alpha)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(sx, sy), size, size)

    def _draw_stars(self, painter, cx, cy, radius):
        ecx, ecy, erad = self._apply_view(cx, cy, radius)
        twinkle = math.sin(self._time_offset) * 0.15 + 0.85
        zoom = self._view_scale

        for star in self._stars:
            alt = star["altitude"]
            az = star["azimuth"]
            mag = star.get("mag", 0)
            name = star.get("name", "")
            color_str = star.get("color", "#FFFFFF")

            p = self._sky_to_screen(alt, az, ecx, ecy, erad)

            if not (0 < p.x() < self.width() and 0 < p.y() < self.height()):
                continue

            self._hit_stars.append({**star, "sx": p.x(), "sy": p.y(), "type": "star"})

            base_size = max(2.0, 5.0 - mag * 0.8) * min(1.0, zoom)
            base_size = min(base_size, 12.0)
            alpha = int(min(255, (1.0 + mag * 0.1) * twinkle * 240))

            base_color = QColor(color_str)
            glow_r = base_size * 3
            gkey = (color_str, int(glow_r))
            def _make():
                g = QRadialGradient(QPointF(0, 0), glow_r)
                g.setCoordinateMode(QRadialGradient.CoordinateMode.ObjectBoundingMode)
                g.setColorAt(0, QColor(base_color.red(), base_color.green(), base_color.blue(), 40))
                g.setColorAt(1, QColor(base_color.red(), base_color.green(), base_color.blue(), 0))
                return g
            glow = _get_gradient(self._gradient_cache, gkey, _make)
            glow = self._gradient_cache[gkey]
            painter.save()
            painter.translate(p)
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(0, 0), glow_r, glow_r)
            painter.restore()

            star_color = QColor(base_color.red(), base_color.green(), base_color.blue(), alpha)
            painter.setBrush(QBrush(star_color))
            painter.drawEllipse(p, base_size, base_size)

            inner = QRadialGradient(QPointF(p.x() - base_size * 0.3, p.y() - base_size * 0.3), base_size)
            inner.setColorAt(0, QColor(255, 255, 255, 200))
            inner.setColorAt(1, QColor(255, 255, 255, 0))
            painter.setBrush(QBrush(inner))
            painter.drawEllipse(p, base_size * 0.6, base_size * 0.6)

            if name and config.is_pro and zoom >= 1.5:
                painter.setPen(QPen(_c(Theme.TEXT_SECONDARY, 180)))
                painter.setFont(Theme.caption())
                fm = QFontMetrics(painter.font())
                tw = fm.horizontalAdvance(name)
                painter.drawText(int(p.x() - tw / 2), int(p.y() + base_size + 14), name)

            if config.is_pro and zoom >= 2.0:
                painter.setPen(QPen(_c(Theme.TEXT_MUTED, 80)))
                painter.setFont(Theme.caption())
                info = f"{star.get('ra', 0):.1f}h {star.get('dec', 0):.0f}°"
                fm = QFontMetrics(painter.font())
                iw = fm.horizontalAdvance(info)
                painter.drawText(int(p.x() - iw / 2), int(p.y() + base_size + 28), info)

    def _draw_sun(self, painter, cx, cy, radius):
        sun = self._sun
        if not sun:
            return
        ecx, ecy, erad = self._apply_view(cx, cy, radius)
        alt = sun["altitude"]
        p = self._sky_to_screen(max(0, alt), sun["azimuth"], ecx, ecy, erad)

        if not (0 < p.x() < self.width() and 0 < p.y() < self.height()) or alt < -5:
            return

        self._hit_suns.append({
            "name": "太阳", "type": "sun", "altitude": alt, "azimuth": sun["azimuth"],
            "sx": p.x(), "sy": p.y(), "ra": sun.get("ra", 0), "dec": sun.get("dec", 0),
        })

        above = alt > 5
        alpha_scale = 1.0 if above else max(0.2, (alt + 5) / 10)

        corona_sizes = [80, 50, 30, 15]
        for i, cs in enumerate(corona_sizes):
            a = max(3, int(30 * alpha_scale)) - i * 6
            if a <= 0:
                break
            glow = QRadialGradient(p, cs)
            glow.setColorAt(0, QColor(255, 200, 50, a))
            glow.setColorAt(0.5, QColor(255, 180, 80, a // 2))
            glow.setColorAt(1, QColor(255, 200, 50, 0))
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(p, cs, cs)

        r = 8
        sun_bright = int(200 * alpha_scale)
        sun_alpha = int(200 * alpha_scale)
        glow = QRadialGradient(p, r * 2 * alpha_scale)
        glow.setColorAt(0, QColor(255, 255, 220, sun_alpha))
        glow.setColorAt(0.5, QColor(255, 220, 100, int(150 * alpha_scale)))
        glow.setColorAt(1, QColor(255, 200, 50, 0))
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(p, r * 2 * alpha_scale, r * 2 * alpha_scale)

        painter.setBrush(QBrush(QColor(255, 220, 50, sun_bright)))
        painter.drawEllipse(p, r, r)

        painter.setBrush(QBrush(QColor(255, 255, 240, int(180 * alpha_scale))))
        painter.drawEllipse(p, r * 0.6, r * 0.6)

        if config.is_pro:
            painter.setPen(_c(Theme.TEXT_MUTED, 100))
            painter.setFont(Theme.caption())
            info = f"Alt: {alt:.1f}°  Az: {sun['azimuth']:.1f}°"
            painter.drawText(int(p.x() - 50), int(p.y() + r + 20), info)

    def _draw_moon(self, painter, cx, cy, radius):
        moon = self._moon
        if not moon:
            return
        ecx, ecy, erad = self._apply_view(cx, cy, radius)
        alt = moon["altitude"]
        p = self._sky_to_screen(max(0, alt), moon["azimuth"], ecx, ecy, erad)

        if not (0 < p.x() < self.width() and 0 < p.y() < self.height()):
            return

        phase_data = moon.get("phase", {"phase": 0, "name": "新月", "icon": "🌑"})
        mp = phase_data.get("phase", 0)

        self._hit_moons.append({
            "name": f"月亮 ({phase_data.get('name', '')})", "type": "moon",
            "altitude": alt, "azimuth": moon["azimuth"],
            "sx": p.x(), "sy": p.y(), "ra": moon.get("ra", 0), "dec": moon.get("dec", 0),
            "phase": phase_data,
        })

        if alt < -5:
            return

        above = alt > 5
        alpha_s = 1.0 if above else max(0.25, (alt + 5) / 10)

        r = 10
        glow_a = int(40 * alpha_s)
        glow = QRadialGradient(p, r * 3)
        glow.setColorAt(0, QColor(200, 220, 255, glow_a))
        glow.setColorAt(1, QColor(200, 220, 255, 0))
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(p, r * 3, r * 3)

        painter.setBrush(QBrush(QColor(40, 45, 65)))
        painter.drawEllipse(p, r, r)

        illumination = abs(mp - 0.5) * 2
        if illumination > 0.01:
            painter.save()
            clip = QPainterPath()
            clip.addEllipse(p, r, r)
            painter.setClipPath(clip)

            moon_color = QColor(230, 235, 245, max(80, int(180 * illumination)))
            dark_side = QColor(40, 45, 65)

            if mp < 0.25:
                painter.setBrush(QBrush(moon_color))
                painter.drawEllipse(QPointF(p.x() - r * (1 - mp * 4), p.y()), r, r)
            elif mp < 0.5:
                painter.setBrush(QBrush(moon_color))
                pw = r * (mp - 0.25) * 4
                painter.drawEllipse(QPointF(p.x() + r - pw * 2, p.y()), r, r)
            elif mp < 0.75:
                painter.setBrush(QBrush(moon_color))
                painter.drawEllipse(p, r, r)
                painter.setBrush(QBrush(dark_side))
                pw = r * (0.75 - mp) * 4
                painter.drawEllipse(QPointF(p.x() - r + pw * 2, p.y()), r, r)
                painter.setBrush(Qt.BrushStyle.NoBrush)
            else:
                painter.setBrush(QBrush(moon_color))
                painter.drawEllipse(p, r, r)
                painter.setBrush(QBrush(dark_side))
                pw = r * (mp - 0.75) * 4
                painter.drawEllipse(QPointF(p.x() + r - pw * 2, p.y()), r, r)

            painter.setClipping(False)
            painter.restore()

        painter.setPen(QPen(QColor(180, 190, 210, int(100 * alpha_s)), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(p, r, r)

        if config.is_pro:
            painter.setPen(_c(Theme.TEXT_MUTED, 100))
            painter.setFont(Theme.caption())
            info = f"Alt: {alt:.1f}°  Az: {moon['azimuth']:.1f}°"
            info += f"  {phase_data.get('illumination', '?')}"
            painter.drawText(int(p.x() - 60), int(p.y() + r + 20), info)

    def _draw_camera_fov(self, painter, cx, cy, radius):
        fov = self._camera_fov
        if not fov or not fov.get("show") or not self._show_fov:
            return
        ecx, ecy, erad = self._apply_view(cx, cy, radius)
        zoom = self._view_scale

        fx = ecx + self._fov_center.x()
        fy = ecy + self._fov_center.y()

        fov_h = fov["fov_h_deg"]
        fov_v = fov["fov_v_deg"]
        rot = fov.get("rotation", 0)

        half_h_px = erad * (fov_h / 90.0)
        half_v_px = erad * (fov_v / 90.0)
        if half_h_px < 2 or half_v_px < 2:
            return

        rot_rad = math.radians(rot)
        cos_r, sin_r = math.cos(rot_rad), math.sin(rot_rad)

        corners = []
        for dx, dy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
            rx = dx * half_h_px
            ry = dy * half_v_px
            px = fx + rx * cos_r - ry * sin_r
            py = fy + rx * sin_r + ry * cos_r
            corners.append(QPointF(px, py))

        painter.setPen(QPen(QColor(Theme.DANGER), max(1, int(1.5 / zoom)), Qt.PenStyle.SolidLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(4):
            painter.drawLine(corners[i], corners[(i + 1) % 4])

        painter.setPen(QPen(_c(Theme.DANGER, 60), max(0.5, 0.5 / zoom), Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(fx, fy), corners[0])
        painter.drawLine(QPointF(fx, fy), corners[2])

        painter.setPen(QPen(QColor(Theme.DANGER), max(0.5, 0.5 / zoom)))
        painter.drawLine(QPointF(fx - 4, fy), QPointF(fx + 4, fy))
        painter.drawLine(QPointF(fx, fy - 4), QPointF(fx, fy + 4))

        painter.setPen(_c(Theme.DANGER, 180))
        painter.setFont(Theme.caption())
        label = f"📷 {fov_h:.2f}°×{fov_v:.2f}°"
        fm = QFontMetrics(painter.font())
        tw = fm.horizontalAdvance(label)
        painter.drawText(int(fx - tw / 2), int(fy - max(half_h_px, half_v_px) - 10), label)

        painter.setPen(_c(Theme.TEXT_MUTED, 100))
        label2 = f"旋转 {rot}°  |  拖拽移动取景框"
        painter.drawText(int(fx - 80), int(fy + max(half_h_px, half_v_px) + 16), label2)

    def _draw_satellites(self, painter, cx, cy, radius):
        if not config.is_pro or not self._satellites:
            return
        ecx, ecy, erad = self._apply_view(cx, cy, radius)
        zoom = self._view_scale

        for sat in self._satellites:
            traj = sat.get("trajectory", [])
            name = sat.get("name", "")
            color_str = sat.get("color", "#FFFFFF")
            alt_now = sat.get("altitude", -90)

            if traj and zoom > 1.5:
                pts = []
                for tp in traj:
                    p = self._sky_to_screen(max(-5, tp["alt"]), tp["az"], ecx, ecy, erad)
                    pts.append(p)
                traj_len = len(pts)
                for i in range(1, traj_len):
                    alpha = max(20, int(180 * (1 - i / traj_len)))
                    painter.setPen(QPen(_c(color_str, alpha), max(0.5, 1 / zoom), Qt.PenStyle.DashLine))
                    painter.drawLine(pts[i - 1], pts[i])

            if alt_now < -5:
                continue

            p = self._sky_to_screen(max(0, alt_now), sat["azimuth"], ecx, ecy, erad)
            if not (0 < p.x() < self.width() and 0 < p.y() < self.height()):
                continue

            base_color = QColor(color_str)
            r = 3 * min(1.5, zoom)
            gkey = (color_str, int(r * 3), 80)
            def _make():
                g = QRadialGradient(QPointF(0, 0), r * 3)
                g.setCoordinateMode(QRadialGradient.CoordinateMode.ObjectBoundingMode)
                g.setColorAt(0, QColor(base_color.red(), base_color.green(), base_color.blue(), 80))
                g.setColorAt(1, QColor(base_color.red(), base_color.green(), base_color.blue(), 0))
                return g
            glow = _get_gradient(self._gradient_cache, gkey, _make)
            painter.save()
            painter.translate(p)
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(0, 0), r * 3, r * 3)
            painter.restore()

            self._hit_satellites_list.append({
                "name": name, "type": "satellite", "norad": sat.get("norad", 0),
                "altitude": alt_now, "azimuth": sat["azimuth"],
                "sx": p.x(), "sy": p.y(), "ra": sat.get("ra", 0), "dec": sat.get("dec", 0),
                "distance_km": sat.get("distance_km", 0), "color": color_str,
            })

            painter.setBrush(QBrush(base_color))
            painter.drawEllipse(p, r, r)

            is_primary = sat.get("is_primary", False)
            if is_primary or zoom > 1.5:
                painter.setPen(_c(color_str, 200))
                painter.setFont(Theme.caption())
                tw = QFontMetrics(painter.font()).horizontalAdvance(name)
                painter.drawText(int(p.x() - tw / 2), int(p.y() - r - 4), name)

                painter.setPen(_c(Theme.TEXT_MUTED, 80))
                info = f"Alt {alt_now:.0f}°  Az {sat['azimuth']:.0f}°"
                painter.drawText(int(p.x() - 40), int(p.y() + r + 12), info)

    def _draw_aircraft(self, painter, cx, cy, radius):
        if not config.is_pro or not self._aircraft or not self._show_aircraft:
            return
        ecx, ecy, erad = self._apply_view(cx, cy, radius)
        zoom = self._view_scale

        for ac in self._aircraft:
            try:
                alt = ac["altitude"]
                p = self._sky_to_screen(max(0, alt), ac["azimuth"], ecx, ecy, erad)
                if not (0 < p.x() < self.width() and 0 < p.y() < self.height()):
                    continue

                if alt < 0:
                    continue

                traj = ac.get("trajectory", [])
                if traj and zoom > 1.0:
                    pts = [p]
                    for tp in traj:
                        pp = self._sky_to_screen(max(-5, tp["alt"]), tp["az"], ecx, ecy, erad)
                        pts.append(pp)
                    traj_len = len(pts)
                    for i in range(1, traj_len):
                        alpha = max(30, int(200 * (1 - i / traj_len)))
                        painter.setPen(QPen(_c("#FF6633", alpha), max(0.5, 1 / zoom), Qt.PenStyle.DashLine))
                        painter.drawLine(pts[i - 1], pts[i])
            except Exception:
                continue

            self._hit_aircraft.append({
                **ac, "sx": p.x(), "sy": p.y(), "type": "aircraft", "name": ac["callsign"],
            })

            r = 3 * min(1.5, zoom)
            gkey = ("#FF6633", int(r * 3))
            def _make():
                g = QRadialGradient(QPointF(0, 0), r * 3)
                g.setCoordinateMode(QRadialGradient.CoordinateMode.ObjectBoundingMode)
                g.setColorAt(0, QColor(255, 100, 50, 80))
                g.setColorAt(1, QColor(255, 100, 50, 0))
                return g
            glow = _get_gradient(self._gradient_cache, gkey, _make)
            painter.save()
            painter.translate(p)
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(0, 0), r * 3, r * 3)
            painter.restore()

            painter.setBrush(QBrush(QColor(255, 120, 50)))
            painter.drawEllipse(p, r, r)

            painter.setPen(_c(Theme.WARNING, 200))
            painter.setFont(Theme.caption())
            label = f"✈ {ac['callsign']}"
            tw = QFontMetrics(painter.font()).horizontalAdvance(label)
            painter.drawText(int(p.x() - tw / 2), int(p.y() - r - 4), label)
            painter.setPen(_c(Theme.TEXT_MUTED, 100))
            painter.drawText(int(p.x() - 25), int(p.y() + r + 12),
                             f"{ac['altitude_ft']:.0f}ft  {ac['velocity_kmh']:.0f}km/h")

    def _draw_aircraft_warnings(self, painter):
        if not config.is_pro or not self._selected_obj or not self._aircraft:
            return
        target_alt = self._selected_obj.get("altitude", 0)
        target_az = self._selected_obj.get("azimuth", 0)
        from app.api.adsb_api import check_aircraft_proximity
        warnings = check_aircraft_proximity(self._aircraft, target_alt, target_az)
        self._aircraft_warnings = warnings
        if not warnings:
            return
        y = 20
        painter.setFont(Theme.font(11, bold=True))
        for w in warnings[:3]:
            fm = QFontMetrics(painter.font())
            text = f"⚠️ {w['callsign']} 距目标 {w['separation']:.0f}°"
            tw = fm.horizontalAdvance(text) + 20
            painter.setBrush(QBrush(QColor(Theme.DANGER, 200)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(self.width() - tw - 16, y, tw, 24, 6, 6)
            painter.setPen(QPen(Qt.GlobalColor.white))
            painter.drawText(int(self.width() - tw - 8), int(y + 16), text)
            y += 30

    def _draw_planets(self, painter, cx, cy, radius):
        ecx, ecy, erad = self._apply_view(cx, cy, radius)
        zoom = self._view_scale

        for planet in self._planets:
            alt = planet["altitude"]
            az = planet["azimuth"]
            name = planet.get("name", "")
            color_str = planet.get("color", "#6C8CFF")
            mag = planet.get("magnitude", 0)

            p = self._sky_to_screen(alt, az, ecx, ecy, erad)

            if not (0 < p.x() < self.width() and 0 < p.y() < self.height()):
                continue

            self._hit_planets.append({**planet, "sx": p.x(), "sy": p.y(), "type": "planet"})

            size = min(8.0, max(4.0, 5.0 * zoom)) if mag < 0 else min(6.0, max(3.0, 4.0 * zoom))
            base_color = QColor(color_str)

            glow_r = size * 4
            pkey = (color_str, int(glow_r), 60)
            def _make():
                pg = QRadialGradient(QPointF(0, 0), glow_r)
                pg.setCoordinateMode(QRadialGradient.CoordinateMode.ObjectBoundingMode)
                pg.setColorAt(0, QColor(base_color.red(), base_color.green(), base_color.blue(), 60))
                pg.setColorAt(1, QColor(base_color.red(), base_color.green(), base_color.blue(), 0))
                return pg
            glow = _get_gradient(self._gradient_cache, pkey, _make)
            painter.save()
            painter.translate(p)
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(0, 0), glow_r, glow_r)
            painter.restore()

            painter.setBrush(QBrush(base_color))
            painter.drawEllipse(p, size, size)

            cs = size + 3
            painter.setPen(QPen(base_color, max(1, int(1.5 / zoom))))
            painter.drawLine(QPointF(p.x() - cs, p.y()), QPointF(p.x() + cs, p.y()))
            painter.drawLine(QPointF(p.x(), p.y() - cs), QPointF(p.x(), p.y() + cs))

            painter.setPen(QPen(base_color))
            painter.setFont(Theme.font(10, bold=True))
            fm = QFontMetrics(painter.font())
            tw = fm.horizontalAdvance(name)
            painter.drawText(int(p.x() - tw / 2), int(p.y() - size - 6), name)

            if config.is_pro:
                painter.setPen(QPen(_c(Theme.TEXT_MUTED, 100)))
                painter.setFont(Theme.caption())
                info = f"RA: {planet.get('ra', 0):.2f}h  Dec: {planet.get('dec', 0):.1f}°"
                fm = QFontMetrics(painter.font())
                iw = fm.horizontalAdvance(info)
                painter.drawText(int(p.x() - iw / 2), int(p.y() + size + 16), info)

    def _draw_dso(self, painter, cx, cy, radius):
        if not config.is_pro or not config.pro_settings.get("show_dso", True):
            return
        ecx, ecy, erad = self._apply_view(cx, cy, radius)

        visible_map = {}
        if hasattr(self, '_dso_visibility'):
            for v in self._dso_visibility:
                visible_map[v.get("id", "")] = v

        def _dso_cat(t):
            for kw in ["发射","反射","行星状","暗星云","超新星"]:
                if kw in t: return "nebula"
            for kw in ["疏散星团","球状星团"]:
                if kw in t: return "cluster"
            for kw in ["旋涡","椭圆","棒旋","透镜","星暴","塞弗特"]:
                if kw in t: return "galaxy"
            return "other"

        for obj in self._dsos:
            if isinstance(obj, (list, tuple)):
                continue
            obj_id = obj.get("id", "")
            name = obj.get("name", "")
            obj_type = obj.get("type", "")
            ra = obj.get("ra", 0)
            dec = obj.get("dec", 0)
            mag = obj.get("mag", 99)

            dcat = _dso_cat(obj_type)
            show_key = f"_show_dso_{dcat}"
            if not getattr(self, show_key, True):
                continue

            vis = visible_map.get(obj_id, {})
            alt_dso = vis.get("altitude", 50) if vis else 50 + (hash(obj_id) % 30)

            if vis and alt_dso <= 0:
                continue

            if vis and "transit_hour" in vis:
                lst = sky.get_jd() % 1 * 24
                az_sim = (lst - ra / 15) * 15 % 360
            else:
                az_sim = hash(obj_id) % 360

            p = self._sky_to_screen(max(1, alt_dso), az_sim, ecx, ecy, erad)
            if not (0 < p.x() < self.width() and 0 < p.y() < self.height()):
                continue

            alt_str = vis.get("altitude", "?") if vis else "?"
            self._hit_dsos.append({
                "name": f"{obj_id} ({name})",
                "type": "dso",
                "obj_type": obj_type,
                "altitude": alt_dso,
                "azimuth": az_sim,
                "sx": p.x(), "sy": p.y(),
                "desc": obj.get("desc", ""),
                "altitude_str": alt_str,
                "mag": mag,
                "id": obj_id,
                "size": obj.get("size", 0),
                "dist_ly": obj.get("dist_ly", 0),
                "bortle": obj.get("bortle", 9),
            })

            painter.setPen(QPen(_c(Theme.DANGER, 180), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(p, 6, 6)

            painter.setPen(_c(Theme.DANGER, 100))
            painter.setFont(Theme.caption())
            label = f"{obj_id} ({name})"
            painter.drawText(int(p.x() + 8), int(p.y() + 4), label)
            if isinstance(alt_str, (int, float)):
                painter.drawText(int(p.x() + 8), int(p.y() + 16), f"Mag {mag}  Alt {alt_str:.1f}°")
            else:
                painter.drawText(int(p.x() + 8), int(p.y() + 16), f"Mag {mag}")

    # =========================================================================
    # 交互反馈
    # =========================================================================
    def _draw_hover_highlight(self, painter):
        obj = self._hovered_obj
        if not obj or self._is_panning:
            return
        px, py = obj.get("sx", 0), obj.get("sy", 0)
        painter.setPen(QPen(_c(Theme.ACCENT, 120), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(px, py), HOVER_RADIUS, HOVER_RADIUS)

    def _draw_hover_info(self, painter):
        obj = self._hovered_obj
        if not obj or self._is_panning:
            return
        px, py = obj.get("sx", 0), obj.get("sy", 0)
        lines = [f"{obj.get('name', '?')}"]
        obj_type = obj.get("type", "")
        if obj_type == "aircraft":
            if obj.get("airline"):
                lines.append(f"航司: {obj['airline']}")
            if obj.get("model"):
                lines.append(f"机型: {obj['model']}")
            lines.append(f"高度: {obj.get('altitude_ft', 0):.0f}ft  {obj.get('velocity_kmh', 0):.0f}km/h")
        mag = obj.get("mag") or obj.get("magnitude", "")
        if mag:
            lines.append(f"星等: {mag}")
        lines.append(f"高度: {obj['altitude']:.1f}°  方位: {obj['azimuth']:.1f}°")

        painter.setFont(Theme.caption())
        fm = QFontMetrics(painter.font())
        line_h = fm.height() + 2
        box_w = max(fm.horizontalAdvance(l) for l in lines) + 20
        box_h = len(lines) * line_h + 12

        bx = min(px + 20, self.width() - box_w - 10)
        by = min(py - 10, self.height() - box_h - 10)

        painter.setBrush(QBrush(QColor(11, 14, 26, 220)))
        painter.setPen(QPen(_c(Theme.DIVIDER, 100), 1))
        painter.drawRoundedRect(QRectF(bx, by, box_w, box_h), 6, 6)

        painter.setPen(_c(Theme.TEXT_PRIMARY, 200))
        for i, line in enumerate(lines):
            painter.drawText(int(bx + 10), int(by + 12 + i * line_h), line)

    def _draw_info_panel(self, painter, cx, cy, radius):
        obj = self._selected_obj
        if not obj:
            return

        obj_type = obj.get("type", "")
        is_dso = obj_type == "dso"
        is_sun = obj_type == "sun"
        is_moon = obj_type == "moon"
        is_sat = obj_type == "satellite"
        is_ac = obj_type == "aircraft"

        lines = [f"✦ {obj.get('name', '?')}"]
        lines.append("─" * 20)

        if is_sun:
            lines.append("类型: 太阳 (G2V)")
            lines.append("直径: 1,392,700 km")
            lines.append("表面温度: 5,778 K")
        elif is_moon:
            ph = obj.get("phase", {})
            if ph:
                lines.append(f"月相: {ph.get('icon', '')} {ph.get('name', '')}")
                lines.append(f"照明度: {ph.get('illumination', '')}")
        elif is_sat:
            lines.append("类型: 人造卫星")
            dist = obj.get("distance_km", 0)
            if dist:
                lines.append(f"距离: {dist:.0f} km")
                lines.append(f"轨道: 近地轨道 (LEO)")
        elif is_ac:
            lines.append(f"类型: 航空器 ✈")
            lines.append(f"识别码: {obj.get('callsign', '----')}")
            if obj.get("registration"):
                lines.append(f"注册号: {obj['registration']}")
            if obj.get("airline"):
                lines.append(f"航司: {obj['airline']}")
            if obj.get("aircraft_type") or obj.get("aircraft_model"):
                type_str = obj.get("aircraft_type", "")
                model_str = obj.get("aircraft_model", "")
                if model_str and type_str:
                    lines.append(f"具体型号: {model_str} ({type_str})")
                elif model_str:
                    lines.append(f"具体型号: {model_str}")
            elif obj.get("model"):
                lines.append(f"具体型号: {obj['model']}")
            if obj.get("year"):
                lines.append(f"出厂年份: {obj['year']}")
            if obj.get("serial"):
                lines.append(f"序列号: {obj['serial']}")
            lines.append(f"高度: {obj.get('altitude_ft', 0):.0f} ft")
            lines.append(f"速度: {obj.get('velocity_kmh', 0):.0f} km/h")
            lines.append(f"距离: {obj.get('distance_km', 0):.1f} km")
            lines.append(f"航向: {obj.get('heading', 0):.0f}°")
            if obj.get("country"):
                lines.append(f"注册地: {obj['country']}")

        mag = obj.get("mag") or obj.get("magnitude", "")
        if mag:
            lines.append(f"星等:  {mag}")

        if is_dso:
            ot = obj.get("obj_type", "")
            if ot:
                lines.append(f"类型:  {ot}")
            sz = obj.get("size", 0)
            if sz:
                lines.append(f"角直径: {sz}′")
            dist = obj.get("dist_ly", 0)
            if dist:
                d_str = f"{dist/1000:.1f} kly" if dist > 10000 else f"{dist:.0f} ly"
                lines.append(f"距离:  {d_str}")
            bortle = obj.get("bortle", 9)
            from app.config import config
            user_b = {"暗空区": 2, "乡村": 4, "郊区": 6, "城市": 8}.get(config.light_pollution, 8)
            if user_b <= bortle:
                bv = "✅ 可见"
            elif user_b <= bortle + 2:
                bv = "⚠️ 勉强"
            else:
                bv = "❌ 不可见"
            lines.append(f"可见性: {bv} (Bortle≤{bortle})")
        elif obj_type == "star":
            name = obj.get("name", "")
            sd = STAR_DATA.get(name)
            if sd:
                spec, dist_ly, color_desc, _ = sd
                lines.append(f"光谱:  {spec} ({color_desc})")
                d_str = f"{dist_ly:.1f} ly" if dist_ly < 1000 else f"{dist_ly/1000:.1f} kly"
                lines.append(f"距离:  {d_str}")
            lines.append(f"类型:  恒星 (主序星)")
        elif obj_type == "planet":
            name = obj.get("name", "")
            pd = PLANET_DATA_INFO.get(name)
            if pd:
                ptype, diameter, note = pd
                lines.append(f"类型:  {ptype}")
                lines.append(f"直径:  {diameter:,} km")
                lines.append(f"特点:  {note}")
            dist_au = obj.get("distance_au")
            if dist_au:
                lines.append(f"距地:  {dist_au:.2f} AU ({dist_au*1.496e8:.0f} km)")

        lines.append(f"高度 (Alt):   {obj['altitude']:.1f}°")
        lines.append(f"方位 (Az):    {obj['azimuth']:.1f}°")
        if obj.get("ra") is not None:
            lines.append(f"赤经 (RA):   {obj['ra']:.2f}h")
        if obj.get("dec") is not None:
            lines.append(f"赤纬 (Dec):  {obj['dec']:.1f}°")
        if obj.get("distance_au"):
            lines.append(f"距离:        {obj['distance_au']:.2f} AU")
        if obj.get("desc"):
            lines.append(f"描述: {obj['desc']}")
        if is_dso:
            dso_id = obj.get("id", "")
            if dso_id:
                lines.append(f"🛸 科学图像: 双击以在浏览器打开")
        elif is_sat:
            lines.append(f"🛰 卫星追踪: 双击在 N2YO.com 打开")
        elif is_ac and obj.get("registration"):
            lines.append(f"📷 JetPhotos: 双击查看注册号图片")
        elif obj_type in ("star", "planet", "sun", "moon"):
            lines.append(f"📖 详细知识: 双击了解详情")
        lines.append("")
        lines.append("[点击空白处关闭]")

        painter.setFont(Theme.body())
        fm = QFontMetrics(painter.font())
        line_h = fm.height() + 4
        box_w = max(fm.horizontalAdvance(l) for l in lines) + 28
        if box_w > 280:
            box_w = 280
        box_h = len(lines) * line_h + 20

        bx, by = 20, 20
        self._info_panel_rect = QRectF(bx, by, box_w, box_h)

        painter.setBrush(QBrush(QColor(11, 14, 26, 230)))
        painter.setPen(QPen(_c(Theme.ACCENT, 60), 1))
        painter.drawRoundedRect(self._info_panel_rect, 10, 10)

        accent_line = QRectF(bx, by, box_w, 3)
        painter.setBrush(QBrush(_c(Theme.ACCENT, 120)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(accent_line, 2, 2)

        painter.setPen(_c(Theme.TEXT_PRIMARY, 220))
        for i, line in enumerate(lines):
            is_title = i == 0
            painter.setFont(Theme.font(12, bold=is_title))
            painter.drawText(int(bx + 14), int(by + 18 + i * line_h), line)

        close_btn = QRectF(bx + box_w - 28, by + 4, 24, 24)
        painter.setPen(_c(Theme.TEXT_MUTED, 100))
        painter.setFont(Theme.caption())
        painter.drawText(close_btn, Qt.AlignmentFlag.AlignCenter, "✕")

    def _draw_zoom_indicator(self, painter, cx):
        text = f"{self._view_scale:.1f}x"
        painter.setFont(Theme.font(14, bold=True))
        fm = QFontMetrics(painter.font())
        tw = fm.horizontalAdvance(text)
        x, y = int(cx - tw / 2), 60

        painter.setBrush(QBrush(QColor(11, 14, 26, 200)))
        painter.setPen(QPen(_c(Theme.ACCENT, 60), 1))
        painter.drawRoundedRect(QRectF(x - 12, y - 22, tw + 24, 34), 8, 8)

        painter.setPen(_c(Theme.ACCENT, 220))
        painter.drawText(int(cx - tw / 2), y + 4, text)

    def _draw_cursor_cross(self, painter, cx, cy, radius):
        if not self._mouse_pos:
            return
        mx, my = self._mouse_pos.x(), self._mouse_pos.y()
        ecx, ecy, erad = self._apply_view(cx, cy, radius)
        dx, dy = mx - ecx, my - ecy
        dist = math.sqrt(dx*dx + dy*dy)

        painter.setPen(QPen(_c(Theme.ACCENT, 80), 1, Qt.PenStyle.DashLine))
        painter.drawLine(int(mx), 0, int(mx), self.height())
        painter.drawLine(0, int(my), self.width(), int(my))

        if dist <= erad:
            alt_deg = 90.0 * (dist / erad) ** 2
            az_deg = math.degrees(math.atan2(dx, -dy)) % 360
            lst = sky.get_jd() % 1 * 24
            ra = lst - az_deg / 15
            if ra < 0: ra += 24
            dec = 90 - alt_deg
            am = sky.airmass(alt_deg) if alt_deg > 0 else None
            info = f"Alt {alt_deg:.0f}°  Az {az_deg:.0f}°  RA {ra:.2f}h  Dec {dec:.0f}°"
            if am:
                info += f"  Airmass {am}"

            painter.setPen(_c(Theme.ACCENT, 180))
            painter.setFont(Theme.font(10, bold=True))
            painter.drawText(int(mx - 80), int(my - 16), info)
