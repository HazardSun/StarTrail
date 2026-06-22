import math
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from app.config import config

BRIGHT_STARS = [
    ("天狼星", 101.287, -16.716, -1.46, "#A8C8FF"),
    ("老人星", 95.988, -52.696, -0.72, "#FFD700"),
    ("大角星", 213.915, 19.182, -0.05, "#FFB347"),
    ("织女星", 279.235, 38.784, 0.03, "#A8C8FF"),
    ("五车二", 73.952, 45.998, 0.08, "#FFD700"),
    ("参宿七", 78.634, -8.202, 0.13, "#A8C8FF"),
    ("南河三", 114.825, 5.225, 0.34, "#FFD700"),
    ("参宿四", 88.793, 7.407, 0.45, "#FF6B6B"),
    ("水委一", 24.428, -57.237, 0.46, "#A8C8FF"),
    ("牛郎星", 297.696, 8.868, 0.76, "#FFD700"),
    ("毕宿五", 68.980, 16.509, 0.87, "#FF6B6B"),
    ("角宿一", 201.298, -11.161, 0.98, "#A8C8FF"),
    ("心宿二", 247.352, -26.432, 1.06, "#FF6B6B"),
    ("北河三", 116.329, 28.026, 1.16, "#FFB347"),
    ("北落师门", 344.412, -29.622, 1.17, "#FFD700"),
    ("天津四", 310.358, 45.290, 1.25, "#A8C8FF"),
    ("轩辕十四", 152.093, 11.967, 1.36, "#A8C8FF"),
    ("土司空", 9.888, -17.987, 1.36, "#FFD700"),
    ("马腹一", 210.956, -60.373, 1.33, "#A8C8FF"),
    ("十字架二", 187.791, -63.099, 1.25, "#FFD700"),
    ("尾宿八", 264.330, -42.998, 1.50, "#FF6B6B"),
    ("候", 319.645, 62.585, 2.05, "#FFB347"),
    ("北斗一", 165.932, 61.751, 1.76, "#FFD700"),
    ("北斗二", 153.685, 49.314, 2.37, "#FFD700"),
    ("北斗三", 148.888, 69.065, 2.45, "#FFD700"),
    ("北斗四", 172.914, 74.656, 3.32, "#FFD700"),
    ("北斗五", 200.981, 54.925, 1.79, "#FFB347"),
    ("北斗六", 178.458, 53.694, 2.27, "#FFB347"),
    ("北斗七", 165.932, 61.751, 1.76, "#FFB347"),
    ("辇道增七", 304.268, 27.957, 3.05, "#FFD700"),
    ("渐台二", 283.816, 36.804, 3.52, "#A8C8FF"),
    ("天大将军", 46.535, 29.341, 4.20, "#FFD700"),
    ("阁道三", 347.987, 59.011, 2.95, "#A8C8FF"),
    ("天枢增", 180.0, 60.0, 6.20, "#A8C8FF"),
    ("玉衡次", 195.0, 55.0, 6.50, "#FFB347"),
    ("开阳伴", 200.0, 58.0, 6.80, "#FFD700"),
    ("北极增一", 30.0, 88.0, 7.10, "#A8C8FF"),
    ("织女伴", 282.0, 39.0, 7.50, "#A8C8FF"),
    ("天琴增一", 285.0, 37.0, 8.00, "#A8C8FF"),
    ("天鹅增一", 312.0, 42.0, 8.20, "#FFB347"),
    ("天鹅增二", 308.0, 44.0, 8.80, "#FFD700"),
    ("天鹰增一", 299.0, 6.0, 9.00, "#FFD700"),
    ("天鹰增二", 295.0, 10.0, 9.50, "#A8C8FF"),
    ("宝瓶增一", 330.0, -10.0, 10.00, "#A8C8FF"),
    ("宝瓶增二", 335.0, -8.0, 10.50, "#FFB347"),
    ("双鱼增一", 350.0, 5.0, 11.00, "#A8C8FF"),
    ("双鱼增二", 355.0, 8.0, 11.50, "#FFD700"),
    ("仙女增一", 15.0, 35.0, 12.00, "#A8C8FF"),
]

DEVICE_CONFIGS = [
    {"name": "肉眼", "icon": "👁", "mag_limit": 5.5, "desc": "裸眼观测"},
    {"name": "双筒望远镜", "icon": "🔭", "mag_limit": 9.0, "desc": "7×50 标准双筒"},
    {"name": "小型望远镜", "icon": "🔬", "mag_limit": 12.0, "desc": "口径 80mm 折射"},
    {"name": "大型望远镜", "icon": "🛸", "mag_limit": 99.0, "desc": "口径 200mm 以上"},
    {"name": "相机", "icon": "📷", "mag_limit": 99.0, "desc": "摄影器材模拟", "is_camera": True},
]

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DSO_CATALOG = []

def _load_dso():
    global DSO_CATALOG
    if DSO_CATALOG:
        return
    path = DATA_DIR / "dso_catalog.json"
    if path.exists():
        try:
            DSO_CATALOG = json.loads(path.read_text(encoding="utf-8"))
            return
        except Exception:
            pass

def dso_magnitude(obj):
    return obj.get("mag", 99)

def dso_bortle_visible(obj, user_bortle):
    req = obj.get("bortle", 9)
    if user_bortle <= req:
        return "✅ 可见", Theme.SUCCESS
    elif user_bortle <= req + 2:
        return "⚠️ 勉强", Theme.WARNING
    else:
        return "❌ 不可见", Theme.DANGER

def dso_aladin_url(obj_id):
    return f"https://aladin.cds.unistra.fr/AladinLite/?target={obj_id}&fov=0.5& Survey=CDS%2FP%2FDSS2%2Fcolor"

def get_dso_detail(obj):
    return {
        "id": obj.get("id", ""),
        "name": obj.get("name", ""),
        "type": obj.get("type", ""),
        "constellation": obj.get("const", ""),
        "magnitude": obj.get("mag", 99),
        "size_arcmin": obj.get("size", 0),
        "distance_ly": obj.get("dist_ly", 0),
        "bortle": obj.get("bortle", 9),
        "description": obj.get("desc", ""),
        "aladin_url": dso_aladin_url(obj.get("id", "")),
    }

def filter_dso_for_night(dt=None, mag_limit=12.0, min_alt=30, user_bortle=8):
    _load_dso()
    if dt is None:
        dt = datetime.now()
    results = []
    for obj in DSO_CATALOG:
        mag = obj.get("mag", 99)
        if mag > mag_limit:
            continue
        ra = obj.get("ra", 0)
        dec = obj.get("dec", 0)
        lst = sky._approx_lst(dt)
        ha = lst - ra / 15.0
        ha = ha % 24
        if ha > 12: ha -= 24
        ha_deg = ha * 15
        lat_r = math.radians(config.latitude)
        dec_r = math.radians(dec)
        ha_r = math.radians(ha_deg)
        alt = math.asin(math.sin(lat_r) * math.sin(dec_r) + math.cos(lat_r) * math.cos(dec_r) * math.cos(ha_r))
        alt_deg = math.degrees(alt)
        if alt_deg < min_alt:
            continue
        bortle_req = obj.get("bortle", 9)
        visible = user_bortle <= bortle_req
        results.append({
            "id": obj["id"],
            "name": obj["name"],
            "type": obj["type"],
            "mag": mag,
            "altitude": round(alt_deg, 1),
            "visible": visible,
            "size": obj.get("size", 0),
            "dist_ly": obj.get("dist_ly", 0),
        })
    return sorted(results, key=lambda x: (-x["visible"], x["mag"]))

PLANET_DATA = [
    ("水星", "#B5B5B5"), ("金星", "#FFD700"), ("火星", "#FF6B6B"),
    ("木星", "#D4A574"), ("土星", "#E8D5A3"), ("天王星", "#7EC8E3"),
    ("海王星", "#4A90D9"),
]

MOON_PHASES = [
    (0.00, "🌑", "新月"), (0.125, "🌒", "蛾眉月"), (0.25, "🌓", "上弦月"),
    (0.375, "🌔", "盈凸月"), (0.50, "🌕", "满月"), (0.625, "🌖", "亏凸月"),
    (0.75, "🌗", "下弦月"), (0.875, "🌘", "残月"), (1.0, "🌑", "新月"),
]

EVENTS_2026 = [
    ("2026-01-03", "象限仪座流星雨极大", "流星雨"),
    ("2026-03-20", "春分", "节气"),
    ("2026-04-22", "天琴座流星雨极大", "流星雨"),
    ("2026-05-06", "宝瓶座η流星雨极大", "流星雨"),
    ("2026-06-21", "夏至", "节气"),
    ("2026-07-28", "宝瓶座δ流星雨极大", "流星雨"),
    ("2026-08-12", "英仙座流星雨极大", "流星雨"),
    ("2026-09-07", "土星冲日", "行星动态"),
    ("2026-09-23", "秋分", "节气"),
    ("2026-10-08", "天龙座流星雨极大", "流星雨"),
    ("2026-10-21", "猎户座流星雨极大", "流星雨"),
    ("2026-11-17", "狮子座流星雨极大", "流星雨"),
    ("2026-12-14", "双子座流星雨极大", "流星雨"),
    ("2026-12-22", "冬至", "节气"),
]

CONSTELLATION_LINES = {
    "猎户座": [
        (88.793, 7.407, 78.634, -8.202),
        (88.793, 7.407, 83.822, -5.391),
        (78.634, -8.202, 83.822, -5.391),
        (83.822, -5.391, 86.939, -9.670),
        (83.822, -5.391, 85.190, -1.943),
    ],
    "大熊座": [
        (165.932, 61.751, 153.685, 49.314),
        (153.685, 49.314, 148.888, 69.065),
        (148.888, 69.065, 172.914, 74.656),
        (172.914, 74.656, 200.981, 54.925),
        (200.981, 54.925, 178.458, 53.694),
        (178.458, 53.694, 165.932, 61.751),
    ],
    "天鹅座": [
        (310.358, 45.290, 313.192, 40.934),
        (313.192, 40.934, 305.557, 40.257),
        (305.557, 40.257, 295.302, 45.592),
        (295.302, 45.592, 310.358, 45.290),
    ],
    "天琴座": [
        (279.235, 38.784, 281.414, 39.642),
        (281.414, 39.642, 283.816, 36.804),
        (283.816, 36.804, 277.848, 36.014),
        (277.848, 36.014, 279.235, 38.784),
    ],
    "天蝎座": [
        (247.352, -26.432, 244.979, -26.468),
        (244.979, -26.468, 240.357, -22.622),
        (240.357, -22.622, 238.786, -26.621),
        (238.786, -26.621, 242.005, -23.281),
    ],
    "狮子座": [
        (152.093, 11.967, 153.670, 11.454),
        (153.670, 11.454, 154.993, 15.427),
        (154.993, 15.427, 151.375, 15.590),
        (151.375, 15.590, 152.093, 11.967),
    ],
}

EVENT_TYPE_COLORS = {
    "流星雨": "#E8915D",
    "节气": "#5B9F8F",
    "行星动态": "#8B7EC8",
    "天文现象": "#D4868F",
}

HEMISPHERE_EVENTS = {
    "象限仪座流星雨": "北半球",
    "英仙座流星雨": "北半球",
    "天龙座流星雨": "北半球",
    "狮子座流星雨": "北半球",
    "双子座流星雨": "北半球",
    "宝瓶座η流星雨": "南半球",
    "宝瓶座δ流星雨": "南半球",
    "天琴座流星雨": "南北皆可",
    "猎户座流星雨": "南北皆可",
}


def get_hemisphere_label(event_title):
    for keyword, hemi in HEMISPHERE_EVENTS.items():
        if keyword in event_title:
            return hemi
    return "全球"


def get_visible_hemisphere(latitude):
    return "南半球" if latitude < 0 else "北半球"

class SkyCalculator:
    def __init__(self):
        self._ts = None
        self._eph = None
        self._planets = {}
        self._earth = None
        self._observer = None
        self._loaded = False
        self._tried_load = False

    def _ensure_loaded(self):
        if self._loaded:
            return True
        if self._tried_load:
            return False
        self._tried_load = True
        try:
            from skyfield.api import load, wgs84, Star, Distance
        except ImportError:
            return False
        try:
            self._ts = load.timescale()
            skyfield_dir = Path.home() / ".startrail" / "skyfield"
            skyfield_dir.mkdir(parents=True, exist_ok=True)
            bsp_path = skyfield_dir / "de421.bsp"
            try:
                self._eph = load(str(bsp_path))
            except Exception:
                return False
            self._earth = self._eph["earth"]
            self._planets = {
                "mercury": self._eph["mercury"],
                "venus": self._eph["venus"],
                "mars": self._eph["mars"],
                "jupiter": self._eph["jupiter barycenter"],
                "saturn": self._eph["saturn barycenter"],
                "uranus": self._eph["uranus barycenter"],
                "neptune": self._eph["neptune barycenter"],
                "moon": self._eph["moon"],
                "sun": self._eph["sun"],
            }
            self._loaded = True
            return True
        except Exception:
            return False

    def _utc_tuple(self, dt):
        """Convert naive local datetime to UTC (y,m,d,h,m,s) tuple."""
        if dt.tzinfo is not None:
            utc = dt.astimezone(timezone.utc)
        else:
            off = -time.timezone
            utc = datetime.fromtimestamp(dt.timestamp() + off, tz=timezone.utc)
        return utc.year, utc.month, utc.day, utc.hour, utc.minute, utc.second + utc.microsecond / 1e6

    def get_planet_positions(self, dt: Optional[datetime] = None):
        if dt is None:
            dt = datetime.now()
        results = []
        if self._ensure_loaded():
            utc_args = self._utc_tuple(dt)
            t = self._ts.utc(*utc_args)
            obs = self._earth + wgs84.latlon(config.latitude, config.longitude)
            for idx, (name, color) in enumerate(PLANET_DATA):
                key = list(self._planets.keys())[idx]
                try:
                    astro = obs.at(t).observe(self._planets[key])
                    app = astro.apparent()
                    alt, az, _ = app.altaz()
                    ra, dec, _ = app.radec()
                    dist = app.distance().au
                    if alt.degrees > -5:
                        results.append({
                            "name": name, "color": color, "altitude": alt.degrees,
                            "azimuth": az.degrees, "ra": ra.hours, "dec": dec.degrees,
                            "distance_au": dist, "magnitude": self._calc_mag(name)
                        })
                except Exception:
                    continue
        else:
            for name, color in PLANET_DATA:
                h = hash((name, dt.year, dt.month, dt.day))
                alt = (h % 60) + 10 if h % 3 != 0 else -10
                if alt > -5:
                    results.append({
                        "name": name, "color": color, "altitude": alt,
                        "azimuth": (h % 360), "ra": (h % 24),
                        "dec": (h % 90) - 45, "distance_au": 1.0,
                        "magnitude": self._calc_mag(name)
                    })
        results.sort(key=lambda x: x.get("magnitude", 99))
        return results

    def _calc_mag(self, name):
        mags = {"水星": 0.5, "金星": -4.5, "火星": -1.5, "木星": -2.5,
                "土星": 0.5, "天王星": 5.5, "海王星": 8.0}
        return mags.get(name, 5.0)

    def get_moon_phase(self, dt: Optional[datetime] = None):
        if dt is None:
            dt = datetime.now()
        known_new = datetime(2000, 1, 6)
        diff = (dt - known_new).days + (dt.hour / 24)
        lunation = diff / 29.53058867
        phase = lunation % 1.0
        for p, icon, name in MOON_PHASES:
            if phase <= p:
                illumination = (1 - math.cos(2 * math.pi * phase)) / 2
                return {"phase": phase, "name": name, "icon": icon, "illumination": f"{illumination:.0%}"}
        return {"phase": 0, "name": "新月", "icon": "🌑", "illumination": "0%"}

    def _altaz_for(self, body_key, dt):
        if self._ensure_loaded() and body_key in self._planets:
            try:
                t = self._ts.utc(*self._utc_tuple(dt))
                obs = self._earth + wgs84.latlon(config.latitude, config.longitude)
                astro = obs.at(t).observe(self._planets[body_key])
                app = astro.apparent()
                alt, az, _ = app.altaz()
                ra, dec, _ = app.radec()
                return {"altitude": alt.degrees, "azimuth": az.degrees, "ra": ra.hours, "dec": dec.degrees}
            except Exception:
                pass
        return None

    def get_sun_position(self, dt: Optional[datetime] = None):
        if dt is None:
            dt = datetime.now()
        pos = self._altaz_for("sun", dt)
        if pos:
            return pos
        lst = self._approx_lst(dt)
        days_since_equinox = dt.timetuple().tm_yday - 81
        sun_lon = days_since_equinox * 0.9856
        eps_r = math.radians(23.44)
        ra_sun = math.degrees(math.atan2(math.sin(math.radians(sun_lon)) * math.cos(eps_r), math.cos(math.radians(sun_lon)))) + 180
        ha = lst - ra_sun / 15.0
        ha = ha % 24
        if ha > 12:
            ha -= 24
        ha_deg = ha * 15
        dec_sun = 23.44 * math.sin(math.radians(360 / 365 * (dt.timetuple().tm_yday - 81)))
        lat_r = math.radians(config.latitude)
        dec_r = math.radians(dec_sun)
        ha_r = math.radians(ha_deg)
        alt = math.asin(math.sin(lat_r) * math.sin(dec_r) + math.cos(lat_r) * math.cos(dec_r) * math.cos(ha_r))
        az = math.atan2(-math.sin(ha_r), math.tan(dec_r) * math.cos(lat_r) - math.sin(lat_r) * math.cos(ha_r))
        return {"altitude": math.degrees(alt), "azimuth": math.degrees(az), "ra": ra_sun / 15, "dec": dec_sun}

    def get_moon_position(self, dt: Optional[datetime] = None):
        if dt is None:
            dt = datetime.now()
        pos = self._altaz_for("moon", dt)
        if pos:
            pos["phase"] = self.get_moon_phase(dt)
            return pos
        phase_data = self.get_moon_phase(dt)
        p = phase_data["phase"]
        ra = p * 24 + 6
        lst = self._approx_lst(dt)
        ha = lst - ra
        ha = ha % 24
        if ha > 12:
            ha -= 24
        ha_deg = ha * 15
        dec_moon = p * 50 - 25
        lat_r = math.radians(config.latitude)
        dec_r = math.radians(dec_moon)
        ha_r = math.radians(ha_deg)
        alt = math.asin(math.sin(lat_r) * math.sin(dec_r) + math.cos(lat_r) * math.cos(dec_r) * math.cos(ha_r))
        az = math.atan2(-math.sin(ha_r), math.tan(dec_r) * math.cos(lat_r) - math.sin(lat_r) * math.cos(ha_r))
        return {"altitude": math.degrees(alt), "azimuth": math.degrees(az), "ra": ra, "dec": dec_moon, "phase": phase_data}

    def get_upcoming_events(self, days=30):
        today = datetime.now()
        end = today + timedelta(days=days)
        events = []
        for date_str, title, etype in EVENTS_2026:
            d = datetime.strptime(date_str, "%Y-%m-%d")
            if today <= d <= end:
                events.append({"date": date_str, "title": title, "type": etype})
        return sorted(events, key=lambda x: x["date"])

    def get_all_events(self):
        return [{"date": d, "title": t, "type": e} for d, t, e in EVENTS_2026]

    def get_bright_stars_altaz(self, dt: Optional[datetime] = None, mag_limit: float = 99.0):
        if dt is None:
            dt = datetime.now()
        results = []
        stars_to_show = [s for s in BRIGHT_STARS if s[3] <= mag_limit]
        if self._ensure_loaded():
            t = self._ts.utc(*self._utc_tuple(dt))
            obs = self._earth + wgs84.latlon(config.latitude, config.longitude)
            for name, ra, dec, mag, color in stars_to_show:
                try:
                    star = Star(ra_hours=ra / 15.0, dec_degrees=dec)
                    astro = obs.at(t).observe(star)
                    app = astro.apparent()
                    alt, az, _ = app.altaz()
                    if alt.degrees > 0:
                        results.append({
                            "name": name, "ra": ra, "dec": dec, "mag": mag,
                            "color": color, "altitude": alt.degrees, "azimuth": az.degrees
                        })
                except Exception:
                    continue
        else:
            for name, ra_deg, dec, mag, color in stars_to_show:
                lst_hours = self._approx_lst(dt)
                ra_hours = ra_deg / 15.0
                ha = lst_hours - ra_hours
                ha = ha % 24
                if ha > 12:
                    ha -= 24
                ha_deg = ha * 15
                dec_rad = math.radians(dec)
                lat_rad = math.radians(config.latitude)
                ha_rad = math.radians(ha_deg)
                alt = math.asin(
                    math.sin(lat_rad) * math.sin(dec_rad) +
                    math.cos(lat_rad) * math.cos(dec_rad) * math.cos(ha_rad)
                )
                alt_deg = math.degrees(alt)
                if alt_deg > 0:
                    az = math.atan2(
                        -math.sin(ha_rad),
                        math.tan(dec_rad) * math.cos(lat_rad) - math.sin(lat_rad) * math.cos(ha_rad)
                    )
                    results.append({
                        "name": name, "ra": ra_deg, "dec": dec, "mag": mag,
                        "color": color, "altitude": alt_deg, "azimuth": math.degrees(az)
                    })
        return sorted(results, key=lambda x: x.get("mag", 99))[:60]

    def _approx_lst(self, dt):
        from app.config import config
        jd = self._julian_day(dt)
        gst = 280.46061837 + 360.98564736629 * (jd - 2451545.0)
        gst = gst % 360
        lst = gst + config.longitude
        return (lst / 15) % 24

    @staticmethod
    def _julian_day(dt):
        if dt.tzinfo is not None:
            utc = dt.astimezone(timezone.utc)
        else:
            utc = datetime.fromtimestamp(dt.timestamp(), tz=timezone.utc)
        y, m, d = utc.year, utc.month, utc.day
        if m <= 2:
            y -= 1; m += 12
        a = y // 100
        b = 2 - a + a // 4
        jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5
        h = utc.hour + utc.minute / 60 + utc.second / 3600 + utc.microsecond / 3600000000
        return jd + (h - 12) / 24

    def get_sun_times(self, dt: Optional[datetime] = None):
        if dt is None:
            dt = datetime.now()
        lat, lon = config.latitude, config.longitude

        if self._ensure_loaded():
            try:
                from skyfield import almanac
                location = wgs84.latlon(lat, lon)
                u = self._utc_tuple(dt)
                t0 = self._ts.utc(u[0], u[1], u[2])
                t1 = self._ts.utc(u[0], u[1], u[2] + 1)
                f = almanac.sunrise_sunset(self._eph, location)
                times, events = almanac.find_discrete(t0, t1, f)
                sunrise = sunset = None
                for t, e in zip(times, events):
                    h = t.utc_datetime().hour + t.utc_datetime().minute / 60
                    if e == 1:
                        sunrise = h
                    else:
                        sunset = h
                if sunrise is not None and sunset is not None:
                    sr_h, sr_m = int(sunrise), int((sunrise % 1) * 60)
                    ss_h, ss_m = int(sunset), int((sunset % 1) * 60)
                    return {
                        "sunrise": f"{sr_h:02d}:{sr_m:02d}",
                        "sunset": f"{ss_h:02d}:{ss_m:02d}",
                    }
            except Exception:
                pass

        approx_day = 12.0
        lat_rad = math.radians(lat)
        decl = 23.44 * math.cos(math.radians(360 / 365 * (dt.timetuple().tm_yday - 81)))
        decl_rad = math.radians(decl)
        cos_ha = -math.tan(lat_rad) * math.tan(decl_rad)
        if -1 <= cos_ha <= 1:
            ha = math.degrees(math.acos(cos_ha))
            day_len = ha / 15 * 2
            noon = 12.0
            sunrise_h = noon - day_len / 2
            sunset_h = noon + day_len / 2
        else:
            sunrise_h, sunset_h = 6.0, 18.0

        sr_h, sr_m = int(sunrise_h), int((sunrise_h % 1) * 60)
        ss_h, ss_m = int(sunset_h), int((sunset_h % 1) * 60)
        return {"sunrise": f"{sr_h:02d}:{sr_m:02d}", "sunset": f"{ss_h:02d}:{ss_m:02d}"}

    def get_moon_times(self, dt: Optional[datetime] = None):
        if dt is None:
            dt = datetime.now()
        lat, lon = config.latitude, config.longitude
        moon = self.get_moon_phase(dt)

        if self._ensure_loaded():
            try:
                from skyfield import almanac
                location = wgs84.latlon(lat, lon)
                u = self._utc_tuple(dt)
                t0 = self._ts.utc(u[0], u[1], u[2])
                t1 = self._ts.utc(u[0], u[1], u[2] + 1)
                f = almanac.risings_and_settings(self._eph, self._planets["moon"], location)
                times, events = almanac.find_discrete(t0, t1, f)
                moonrise = moonset = None
                for t, e in zip(times, events):
                    h = t.utc_datetime().hour + t.utc_datetime().minute / 60
                    if e == 1:
                        moonrise = h
                    else:
                        moonset = h
                if moonrise is not None and moonset is not None:
                    mr_h, mr_m = int(moonrise), int((moonrise % 1) * 60)
                    ms_h, ms_m = int(moonset), int((moonset % 1) * 60)
                    return {
                        "moonrise": f"{mr_h:02d}:{mr_m:02d}",
                        "moonset": f"{ms_h:02d}:{ms_m:02d}",
                        "moon_phase": moon,
                    }
            except Exception:
                pass

        phase = moon["phase"]
        mr_h = 6 + phase * 12
        ms_h = (mr_h + 12) % 24
        mr_hh, mr_mm = int(mr_h), int((mr_h % 1) * 60)
        ms_hh, ms_mm = int(ms_h), int((ms_h % 1) * 60)
        return {
            "moonrise": f"{mr_hh:02d}:{mr_mm:02d}",
            "moonset": f"{ms_hh:02d}:{ms_mm:02d}",
            "moon_phase": moon,
        }

    @staticmethod
    def get_jd(dt: Optional[datetime] = None):
        if dt is None:
            dt = datetime.now()
        return round(SkyCalculator._julian_day(dt), 5)

    @staticmethod
    def get_mjd(dt: Optional[datetime] = None):
        return round(SkyCalculator.get_jd(dt) - 2400000.5, 5)

    @staticmethod
    def airmass(altitude_deg):
        if altitude_deg <= 0:
            return None
        alt_rad = math.radians(altitude_deg)
        return round(1.0 / math.sin(alt_rad), 2)

    def get_best_window(self, dt: Optional[datetime] = None):
        if dt is None:
            dt = datetime.now()
        sun = self.get_sun_times(dt)
        moon = self.get_moon_times(dt)
        moon_phase = self.get_moon_phase(dt)

        sunset_str = sun.get("sunset", "18:00")
        sr_h, sr_m = map(int, sunset_str.split(":"))

        astro_dark_h = sr_h + 1.5
        astro_dark = max(sr_h + 1, int(astro_dark_h))

        moonrise_str = moon.get("moonrise", "06:00")
        mr_h, _ = map(int, moonrise_str.split(":"))

        moonset_str = moon.get("moonset", "18:00")
        ms_h, _ = map(int, moonset_str.split(":"))

        mp = moon_phase.get("phase", 0)
        moon_bright = abs(mp - 0.5) * 2

        window_start = astro_dark
        window_end = 24

        if moon_bright > 0.3:
            if ms_h > sr_h and ms_h < 24:
                window_end = ms_h
            elif mr_h < sr_h:
                window_end = 24
            else:
                window_end = max(sr_h + 1, mr_h - 1)
        else:
            window_end = 24

        sunrise_next = sr_h if sr_h > 0 else 6
        if window_start >= sunrise_next:
            window_start = max(window_start, sr_h + 1)

        if window_end > 24:
            window_end = 24
        if window_start < 0:
            window_start = 0

        start_str = f"{int(window_start):02d}:{int((window_start % 1) * 60):02d}"
        end_str = f"{int(window_end):02d}:{int((window_end % 1) * 60):02d}"
        duration = window_end - window_start

        quality = "优" if duration > 5 else "良" if duration > 2 else "差"
        return {
            "start": start_str,
            "end": end_str,
            "duration_hours": round(duration, 1),
            "quality": quality,
            "moon_factor": round(moon_bright, 2),
        }

    def get_dso_visibility(self, dt: Optional[datetime] = None):
        if dt is None:
            dt = datetime.now()
        results = []
        _load_dso()
        for obj in DSO_CATALOG:
            ra = obj.get("ra", 0)
            dec = obj.get("dec", 0)
            lst = self._approx_lst(dt)
            ha = lst - ra / 15.0
            ha = ha % 24
            if ha > 12: ha -= 24
            ha_deg = ha * 15
            lat_r = math.radians(config.latitude)
            dec_r = math.radians(dec)
            ha_r = math.radians(ha_deg)
            alt = math.asin(math.sin(lat_r) * math.sin(dec_r) + math.cos(lat_r) * math.cos(dec_r) * math.cos(ha_r))
            alt_deg = math.degrees(alt)
            transit_h = (ra / 15.0 - config.longitude / 15 + 24) % 24
            results.append({
                "id": obj.get("id", ""),
                "name": obj.get("name", ""),
                "type": obj.get("type", ""),
                "mag": obj.get("mag", 99),
                "size": obj.get("size", 0),
                "dist_ly": obj.get("dist_ly", 0),
                "bortle": obj.get("bortle", 9),
                "visible": alt_deg > 0,
                "altitude": round(alt_deg, 1),
                "transit_hour": round(transit_h, 1),
            })
        return sorted(results, key=lambda x: -x["altitude"])

    SATELLITE_CATALOG = [
        (25544, "ISS (国际空间站)", "#FFFFFF", True),
        (48274, "天宫空间站", "#FFD700", True),
        (20580, "哈勃望远镜", "#6C8CFF", True),
        (50463, "韦伯望远镜", "#B8860B", True),
        (44713, "哨兵6号", "#4CAF50", False),
        (54222, "星链-1000", "#A8C8FF", False),
        (54223, "星链-1001", "#A8C8FF", False),
    ]

    _tle_cache = None
    _tle_cache_time = 0
    _tle_file = Path.home() / ".startrail" / "tle_cache.json"

    def _save_tle_local(self, data):
        try:
            self._tle_file.parent.mkdir(parents=True, exist_ok=True)
            self._tle_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _load_tle_local(self):
        try:
            if self._tle_file.exists():
                data = json.loads(self._tle_file.read_text(encoding="utf-8"))
                return {int(k): tuple(v) if isinstance(v, list) else v for k, v in data.items()}
        except Exception:
            pass
        return {}

    def _fetch_tle(self):
        now = datetime.now().timestamp()
        if self._tle_cache and (now - self._tle_cache_time) < 3600:
            return self._tle_cache

        local = self._load_tle_local()
        if local and not self._tle_cache:
            self._tle_cache = local
            self._tle_cache_time = now

        ids = ",".join(str(s[0]) for s in self.SATELLITE_CATALOG)
        url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={ids}&FORMAT=TLE"
        try:
            import requests
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                lines = resp.text.strip().splitlines()
                tle_dict = {}
                i = 0
                while i + 2 < len(lines):
                    name = lines[i].strip()
                    line1 = lines[i + 1].strip()
                    line2 = lines[i + 2].strip()
                    if line1.startswith("1 ") and line2.startswith("2 "):
                        norad = int(line1[2:7])
                        tle_dict[norad] = (name, line1, line2)
                    i += 3
                self._tle_cache = tle_dict
                self._tle_cache_time = now
                self._save_tle_local(tle_dict)
                return tle_dict
        except Exception:
            pass
        return self._tle_cache or {}

    def get_satellite_positions(self, dt: Optional[datetime] = None):
        if dt is None:
            dt = datetime.now()
        tle_dict = self._fetch_tle()
        results = []

        lat_r = math.radians(config.latitude)
        lon_r = math.radians(config.longitude)

        for norad_id, sname, color, is_primary in self.SATELLITE_CATALOG:
            tle = tle_dict.get(norad_id)
            if tle:
                try:
                    from skyfield.api import EarthSatellite
                    name, line1, line2 = tle
                    sat = EarthSatellite(line1, line2, name)
                    t = self._ts.utc(*self._utc_tuple(dt))
                    obs = self._earth + wgs84.latlon(config.latitude, config.longitude)
                    diff = sat - obs
                    topo = diff.at(t)
                    alt, az, dist = topo.altaz()
                    ra, dec, _ = topo.radec()

                    traj = []
                    u = self._utc_tuple(dt)
                    dt_utc = datetime(u[0], u[1], u[2], u[3], u[4], int(u[5]), tzinfo=timezone.utc)
                    for minute in range(0, 31, 2):
                        ft = dt_utc + timedelta(minutes=minute)
                        t_future = self._ts.utc(ft.year, ft.month, ft.day, ft.hour, ft.minute, ft.second)
                        f_diff = sat - obs
                        f_topo = f_diff.at(t_future)
                        f_alt, f_az, _ = f_topo.altaz()
                        traj.append({"alt": f_alt.degrees, "az": f_az.degrees})

                    results.append({
                        "norad": norad_id,
                        "name": sname,
                        "color": color,
                        "is_primary": is_primary,
                        "altitude": alt.degrees,
                        "azimuth": az.degrees,
                        "ra": ra.hours,
                        "dec": dec.degrees,
                        "distance_km": round(dist.km, 0),
                        "trajectory": traj,
                    })
                    continue
                except Exception:
                    pass

            h = hash((norad_id, dt.minute // 5))
            alt = (h % 60) - 15
            results.append({
                "norad": norad_id,
                "name": sname,
                "color": color,
                "is_primary": is_primary,
                "altitude": alt,
                "azimuth": h % 360,
                "ra": 0, "dec": 0,
                "distance_km": 500,
                "trajectory": [{"alt": alt + i * 0.5, "az": (h + i * 3) % 360} for i in range(31)],
            })

        return results

    def predict_satellite_passes(self, norad_id, dt: Optional[datetime] = None, duration_hours=24):
        if dt is None:
            dt = datetime.now()
        tle_dict = self._fetch_tle()
        tle = tle_dict.get(norad_id)
        if not tle:
            return []

        try:
            from skyfield.api import EarthSatellite
            name, line1, line2 = tle
            sat = EarthSatellite(line1, line2, name)
            obs = self._earth + wgs84.latlon(config.latitude, config.longitude)
            passes = []
            u = self._utc_tuple(dt)
            dt_utc = datetime(u[0], u[1], u[2], u[3], u[4], int(u[5]), tzinfo=timezone.utc)
            step = 2
            for minute_offset in range(0, duration_hours * 60, step):
                ft = dt_utc + timedelta(minutes=minute_offset)
                t_check = self._ts.utc(ft.year, ft.month, ft.day, ft.hour, ft.minute, ft.second)
                diff = sat - obs
                topo = diff.at(t_check)
                alt, _, _ = topo.altaz()
                passes.append((minute_offset, alt.degrees))

            events = []
            i = 1
            while i < len(passes) - 1:
                if passes[i - 1][1] < 10 and passes[i][1] >= 10:
                    start_min = passes[i][0]
                    peak_alt = -90
                    peak_min = start_min
                    for j in range(i, len(passes)):
                        if passes[j][1] > peak_alt:
                            peak_alt = passes[j][1]
                            peak_min = passes[j][0]
                        if passes[j][1] < 10 and j > i + 2:
                            end_min = passes[j][0]
                            dt_start = dt + timedelta(minutes=start_min)
                            dt_peak = dt + timedelta(minutes=peak_min)
                            dt_end = dt + timedelta(minutes=end_min)
                            events.append({
                                "start": dt_start.strftime("%H:%M"),
                                "peak": dt_peak.strftime("%H:%M"),
                                "end": dt_end.strftime("%H:%M"),
                                "max_alt": round(peak_alt, 1),
                                "duration_min": end_min - start_min,
                            })
                            i = j
                            break
                i += 1
            return sorted(events, key=lambda x: -x["max_alt"])[:5]
        except Exception:
            return []

    def get_constellation_lines(self):
        return CONSTELLATION_LINES

    def get_dso_list(self):
        _load_dso()
        return DSO_CATALOG

    def get_current_constellations(self):
        month = datetime.now().month
        if 1 <= month <= 3:
            return ["猎户座", "金牛座", "双子座", "大熊座"]
        elif 4 <= month <= 6:
            return ["狮子座", "室女座", "大熊座", "小熊座"]
        elif 7 <= month <= 9:
            return ["天鹅座", "天琴座", "天蝎座", "人马座"]
        else:
            return ["仙后座", "宝瓶座", "双鱼座", "白羊座"]

    def get_satellite_positions_bg(self, dt=None):
        """Return (tle_dict, lat, lon, dt_tuple) for background computation."""
        if dt is None:
            dt = datetime.now()
        return (self._fetch_tle(), config.latitude, config.longitude,
                (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second))


_SATELLITE_CATALOG = [
    (25544, "ISS (国际空间站)", "#FFFFFF", True),
    (48274, "天宫空间站", "#FFD700", True),
    (20580, "哈勃望远镜", "#6C8CFF", True),
    (50463, "韦伯望远镜", "#B8860B", True),
    (44713, "哨兵6号", "#4CAF50", False),
    (54222, "星链-1000", "#A8C8FF", False),
    (54223, "星链-1001", "#A8C8FF", False),
]


def compute_satellites_bg(data):
    """Run in background thread: compute satellite positions from TLE.

    `data` is (tle_dict, lat, lon, dt_tuple) as returned by get_satellite_positions_bg.
    Returns list of satellite dicts.
    """
    tle_dict, lat, lon, dt_tuple = data
    results = []
    try:
        from skyfield.api import load, wgs84, EarthSatellite
        from skyfield.timelib import Timescale
        ts = load.timescale()
        bsp = str(Path.home() / ".startrail" / "skyfield" / "de421.bsp")
        eph = load(bsp)
        earth = eph["earth"]
        y, mo, d, h, mi, s = dt_tuple
        t = ts.utc(y, mo, d, h, mi, s)
        obs = earth + wgs84.latlon(lat, lon)
        dt_utc = datetime(y, mo, d, h, mi, int(s), tzinfo=timezone.utc)

        for norad_id, sname, color, is_primary in _SATELLITE_CATALOG:
            tle = tle_dict.get(norad_id)
            if tle:
                try:
                    name, line1, line2 = tle
                    sat = EarthSatellite(line1, line2, name)
                    diff = sat - obs
                    topo = diff.at(t)
                    alt, az, dist = topo.altaz()
                    ra, dec, _ = topo.radec()
                    traj = []
                    for minute in range(0, 31, 2):
                        ft = dt_utc + timedelta(minutes=minute)
                        tf = ts.utc(ft.year, ft.month, ft.day, ft.hour, ft.minute, ft.second)
                        fd = sat - obs
                        ftopo = fd.at(tf)
                        fa, faz, _ = ftopo.altaz()
                        traj.append({"alt": fa.degrees, "az": faz.degrees})
                    results.append({
                        "norad": norad_id, "name": sname, "color": color,
                        "is_primary": is_primary, "altitude": alt.degrees,
                        "azimuth": az.degrees, "ra": ra.hours, "dec": dec.degrees,
                        "distance_km": round(dist.km, 0), "trajectory": traj,
                    })
                    continue
                except Exception:
                    pass
            h = hash((norad_id, dt_tuple[4] // 5))
            alt = (h % 60) - 15
            results.append({
                "norad": norad_id, "name": sname, "color": color,
                "is_primary": is_primary, "altitude": alt,
                "azimuth": h % 360, "ra": 0, "dec": 0,
                "distance_km": 500,
                "trajectory": [{"alt": alt + i * 0.5, "az": (h + i * 3) % 360} for i in range(31)],
            })
    except Exception:
        pass
    return results

def get_tonight_guide(dt=None):
    if dt is None:
        dt = datetime.now()
    lat, lon = config.latitude, config.longitude

    candidates = []

    moon = sky.get_moon_phase(dt)
    moon_pos = sky.get_moon_position(dt)
    if moon_pos and moon_pos["altitude"] > 0:
        moon_phase_names = {"新月": "一弯新月如钩", "蛾眉月": "蛾眉月挂天边",
                           "上弦月": "上弦月明如镜", "盈凸月": "月渐圆满",
                           "满月": "明月当空照", "亏凸月": "月华渐褪",
                           "下弦月": "下弦月静悬", "残月": "残月如弓"}
        mpn = moon.get("name", "月亮")
        desc = moon_phase_names.get(mpn, f"今晚是{mpn}")
        candidates.append({
            "name": f"🌙 月亮 ({mpn})", "type": "moon", "priority": 0,
            "altitude": moon_pos["altitude"], "azimuth": moon_pos["azimuth"],
            "brightness": -12.7, "description": desc,
            "detail": f"照明度 {moon['illumination']}，{mpn}是夜空中最明亮的天体。"
        })

    planets = sky.get_planet_positions(dt)
    planet_myths = {"金星":"维纳斯的化身","火星":"战神的象征","木星":"众神之王",
                    "土星":"时光之神","水星":"信使之神","天王星":"天空之神","海王星":"海洋之神"}
    planet_colors = {"金星":"洁白耀眼","火星":"微微发红","木星":"温暖金黄",
                     "土星":"淡黄柔和","水星":"银灰闪烁","天王星":"青绿幽光","海王星":"深蓝神秘"}
    for p in planets:
        if p["altitude"] > 10:
            name = p["name"]
            myth = planet_myths.get(name, "神秘天体")
            col = planet_colors.get(name, "闪烁")
            candidates.append({
                "name": f"🪐 {name}", "type": "planet", "priority": 1,
                "altitude": p["altitude"], "azimuth": p["azimuth"],
                "brightness": -p.get("magnitude", 5),
                "description": f"今晚{name}在{'东南西北'[int(p['azimuth']/90)%4]}方天空{col}，它是{myth}。",
                "detail": f"星等 {p.get('magnitude', 0):.1f}，适合小型望远镜观测。"
            })

    stars_visible = sky.get_bright_stars_altaz(dt, mag_limit=2.0)
    star_poems = {
        "天狼星":"大犬座的主星，冬季最亮的恒星",
        "织女星":"织女与牛郎隔河相望",
        "牛郎星":"牵牛星与织女星遥遥相对",
        "大角星":"牧夫座的璀璨明珠",
        "五车二":"御夫座中最明亮的恒星",
        "参宿四":"猎户座的红超巨星",
        "参宿七":"猎户座的蓝白巨星",
        "天津四":"天鹅座的尾部明星",
        "北河三":"双子座中较亮的一颗",
    }
    for s in stars_visible[:6]:
        name = s["name"]
        poem = star_poems.get(name, f"夜空中的璀璨之星")
        candidates.append({
            "name": f"⭐ {name}", "type": "star", "priority": 2,
            "altitude": s["altitude"], "azimuth": s["azimuth"],
            "brightness": -s.get("mag", 5),
            "description": f"今晚{name}在{'东南西北'[int(s['azimuth']/90)%4]}方高空闪耀，{poem}。",
            "detail": f"星等 {s.get('mag', 0):.1f}，{'即使在城市中也能看到' if s.get('mag',0) < 2 else '需要到暗空下观测'}。"
        })

    candidates.sort(key=lambda x: (-x["brightness"], x["priority"]))
    top3 = candidates[:3]

    score = 50
    try:
        from app.api.weather_api import get_weather, calc_stargazing_index
        weather = get_weather(timeout=5)
        if isinstance(weather, dict) and "error" not in weather:
            score, _, _, _ = calc_stargazing_index(weather, moon)
    except Exception:
        pass

    if score >= 80:
        stars_rating = 5
        score_text = "✨✨✨✨✨ 绝佳观测夜！"
        score_advice = "带上你的望远镜，今晚星空璀璨。"
    elif score >= 60:
        stars_rating = 4
        score_text = "✨✨✨✨ 适宜观测"
        score_advice = "条件不错，出门看看星星吧。"
    elif score >= 40:
        stars_rating = 3
        score_text = "✨✨✨ 可以一试"
        score_advice = "云量较多，但亮星仍可见。"
    elif score >= 20:
        stars_rating = 2
        score_text = "✨✨ 条件一般"
        score_advice = "月光较强或云层较厚，建议关注亮星。"
    else:
        stars_rating = 1
        score_text = "✨ 不太理想"
        score_advice = "天气不佳，建议改日再观测。"

    return {
        "targets": top3,
        "rating": stars_rating,
        "rating_text": score_text,
        "advice": score_advice,
    }

sky = SkyCalculator()
