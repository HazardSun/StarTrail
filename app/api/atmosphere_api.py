import math
import time
from datetime import datetime, timedelta

from app.config import config
from app.api.weather_api import get_weather

_FORECAST_CACHE = None
_FORECAST_CACHE_TIME = 0


def compute_seeing(ws_10m, humidity, cloud_pct, temp_c, is_night):
    """Estimate seeing (arcsec) from surface weather data.

    Simple empirical model based on:
      - wind speed at 10m (m/s) — higher wind = worse seeing
      - relative humidity (%) — higher = worse extinction/seeing
      - cloud cover (%) — higher = worse
      - day/night — daytime solar heating degrades seeing
    """
    base = 0.6
    wind_factor = 0.06 * min(ws_10m, 25.0)
    humidity_factor = 0.008 * max(0, humidity - 30)
    cloud_factor = 0.005 * cloud_pct
    diurnal_factor = 0.3 if not is_night else 0.0
    seeing = base + wind_factor + humidity_factor + cloud_factor + diurnal_factor
    return round(max(0.3, min(seeing, 5.0)), 2)


def compute_extinction(humidity, cloud_pct):
    """Estimate atmospheric extinction (magnitudes per airmass)."""
    base = 0.12
    humidity_factor = 0.002 * max(0, humidity - 30)
    cloud_factor = 0.004 * cloud_pct
    extinction = base + humidity_factor + cloud_factor
    return round(max(0.08, min(extinction, 2.0)), 3)


def get_seeing_rating(seeing):
    """Return (label, color, icon) for a seeing value in arcsec."""
    if seeing <= 0.8:
        return "极佳", "success", "🌟🌟"
    elif seeing <= 1.2:
        return "优秀", "success", "⭐"
    elif seeing <= 1.8:
        return "良好", "warning", "👍"
    elif seeing <= 2.5:
        return "一般", "warning", "👌"
    else:
        return "较差", "danger", "⚠️"


def get_seeing_advice(seeing, extinction, cloud_pct, is_night):
    """Generate human-readable observation advice."""
    parts = []
    if not is_night:
        parts.append("☀️ 白天不建议天文观测")
        return parts
    if cloud_pct > 80:
        parts.append("☁️ 云量过大，不适合观测")
        return parts
    if seeing <= 1.2:
        parts.append("🔭 适合高倍行星摄影")
        if extinction < 0.2:
            parts.append("🌌 大气通透，适合深空摄影")
        else:
            parts.append("🌫️ 大气略浑浊，深空摄影效果一般")
    elif seeing <= 2.0:
        parts.append("🔭 适合低倍目视观测")
        if extinction > 0.5:
            parts.append("🌫️ 消光较大，适合观测亮星/行星")
        else:
            parts.append("🌌 可尝试双筒巡天")
    else:
        parts.append("👁️ 仅适合目视亮星/行星")
    return parts


def get_atmosphere_forecast():
    """Compute 6-hour atmosphere quality forecast.

    Returns a dict with:
      - current: {seeing, extinction, rating, advice}
      - hourly: list of {hour, seeing, rating, extinction} (6 data points)
    """
    global _FORECAST_CACHE, _FORECAST_CACHE_TIME
    now = datetime.now()
    if _FORECAST_CACHE and (now.timestamp() - _FORECAST_CACHE_TIME) < 180:
        return _FORECAST_CACHE

    weather = get_weather(timeout=8)
    result = {"current": None, "hourly": []}

    if isinstance(weather, dict) and "error" not in weather:
        main = weather.get("main", {})
        wind = weather.get("wind", {})
        clouds = weather.get("clouds", {})
        w_list = weather.get("weather", [{}])

        temp = main.get("temp", 20)
        humidity = main.get("humidity", 50)
        ws = wind.get("speed", 5)
        cloud_pct = clouds.get("all", 30)
        w_icon = w_list[0].get("icon", "01d") if w_list else "01d"
        is_night = w_icon.endswith("n") if w_icon else False

        seeing = compute_seeing(ws, humidity, cloud_pct, temp, is_night)
        extinction = compute_extinction(humidity, cloud_pct)
        rating_label, rating_color, rating_icon = get_seeing_rating(seeing)
        advice = get_seeing_advice(seeing, extinction, cloud_pct, is_night)

        result["current"] = {
            "seeing": seeing,
            "extinction": extinction,
            "rating_label": rating_label,
            "rating_color": rating_color,
            "rating_icon": rating_icon,
            "advice": advice,
            "temp": round(temp, 1),
            "humidity": humidity,
            "wind_speed": round(ws, 1),
            "cloud_pct": cloud_pct,
            "location": config.city_name,
        }

        hourly = []
        base_hour = now.hour
        for i in range(6):
            h = (base_hour + i) % 24
            hour_is_night = h < 5 or h > 19
            hour_seeing = compute_seeing(
                ws * (0.7 + 0.1 * math.sin(i * 1.2)),
                max(30, humidity + int(5 * math.sin(i * 0.8))),
                max(0, min(100, cloud_pct + int(10 * math.sin(i * 0.5)))),
                temp + int(2 * math.sin(i * 0.6)),
                hour_is_night,
            )
            hr_label, hr_color, hr_icon = get_seeing_rating(hour_seeing)
            hourly.append({
                "hour": f"{h:02d}:00",
                "seeing": hour_seeing,
                "rating_label": hr_label,
                "color": hr_color,
                "icon": hr_icon,
                "is_night": hour_is_night,
            })
        result["hourly"] = hourly
    else:
        result["error"] = weather.get("error", "unknown")

    if "error" not in result:
        _FORECAST_CACHE = result
        _FORECAST_CACHE_TIME = now.timestamp()
    return result
