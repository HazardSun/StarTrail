"""OpenWeatherMap 天气数据访问层。

所有网络请求统一走 :mod:`app.api.client`，复用连接池、带缓存与超时控制，
显著提升响应速度并避免 UI 卡顿。天气数据按 5 分钟 TTL 缓存。
"""

from datetime import datetime
from app.config import config
from app.api.client import cached_get

WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
WEATHER_TTL = 300  # 5 分钟


def get_weather(timeout: int = 20):
    """获取当前天气。无密钥或网络失败均返回错误字典。"""
    key = config.api_keys.get("openweather")
    if not key:
        return {"error": "no_key"}
    params = {
        "lat": config.latitude, "lon": config.longitude,
        "appid": key, "units": "metric", "lang": "zh_cn",
    }
    return cached_get(WEATHER_URL, params, timeout=timeout, ttl=WEATHER_TTL)


def get_forecast(timeout: int = 20):
    """获取 5 天 / 3 小时间隔预报。"""
    key = config.api_keys.get("openweather")
    if not key:
        return {"error": "no_key"}
    params = {
        "lat": config.latitude, "lon": config.longitude,
        "appid": key, "units": "metric", "lang": "zh_cn", "cnt": 16,
    }
    return cached_get(FORECAST_URL, params, timeout=timeout, ttl=WEATHER_TTL)


def test_key(api_key: str):
    """验证 OpenWeatherMap 密钥是否可用。"""
    result = cached_get(
        WEATHER_URL,
        {"lat": 39.9, "lon": 116.4, "appid": api_key, "units": "metric"},
        timeout=15, ttl=0,
    )
    if isinstance(result, dict):
        err = result.get("error")
        if err == "invalid_key":
            return False, "API 密钥无效 (401)"
        if err == "http_error":
            return False, f"服务返回错误 ({result.get('code', '?')})"
        if err == "timeout":
            return False, "连接超时（OpenWeatherMap 在中国大陆可能需要 VPN 访问）"
        if err == "ssl_error":
            return False, "SSL 连接失败（请检查网络/VPN）"
        if err == "no_key":
            return False, "请填写密钥"
    return True, None


def check_precipitation(forecast_data, hours=24):
    if not forecast_data or not isinstance(forecast_data, dict):
        return {"has_precip": False, "prob": 0, "desc": "数据不足"}

    if "error" in forecast_data:
        return {"has_precip": False, "prob": 0, "desc": "数据不可用"}

    now = datetime.now().timestamp()
    end = now + hours * 3600
    entries = forecast_data.get("list", [])

    max_pop = 0
    has_rain = False
    has_snow = False
    precip_desc = ""
    total_volume = 0

    for entry in entries:
        if entry.get("dt", 0) > end:
            break

        pop = entry.get("pop") or 0
        max_pop = max(max_pop, pop)

        rain = entry.get("rain", {})
        snow = entry.get("snow", {})
        vol = rain.get("3h", 0) + snow.get("3h", 0)
        total_volume += vol

        weather_list = entry.get("weather", [])
        for w in weather_list:
            main = w.get("main", "")
            if main == "Rain":
                has_rain = True
            elif main == "Snow":
                has_snow = True
                if not precip_desc:
                    precip_desc = w.get("description", "")
            if not precip_desc:
                precip_desc = w.get("description", "")

    has_precip = has_rain or has_snow or max_pop > 0.3

    if has_precip:
        if has_rain and has_snow:
            desc = "雨雪混合"
        elif has_rain:
            desc = "有降雨"
        elif has_snow:
            desc = "有降雪"
        else:
            desc = "可能有降水"
        prob = int(max_pop * 100)
        vol_str = f"{total_volume:.1f}mm" if total_volume > 0 else ""
        parts = [f"{desc} ({prob}%)"]
        if vol_str:
            parts.append(vol_str)
        return {"has_precip": True, "prob": prob, "desc": " ".join(parts)}
    else:
        return {"has_precip": False, "prob": 0, "desc": "无降水"}


WIND_DIRECTIONS = [
    ("北风", 0), ("东北风", 45), ("东风", 90), ("东南风", 135),
    ("南风", 180), ("西南风", 225), ("西风", 270), ("西北风", 315),
]


def wind_direction(deg):
    best = "北风"
    best_diff = 360
    for name, d in WIND_DIRECTIONS:
        diff = abs(deg - d)
        if diff > 180:
            diff = 360 - diff
        if diff < best_diff:
            best = name
            best_diff = diff
    return best


LIGHT_POLUTION_PENALTIES = {
    "暗空区": 0,
    "乡村": 5,
    "郊区": 15,
    "城市": 25,
}


def calc_stargazing_index(weather_data, moon_phase=None):
    if not weather_data:
        return 50, "数据不足", "#555A78", []
    if isinstance(weather_data, dict) and "error" in weather_data:
        return 0, "天气数据不可用", "#EF5350", []

    clouds = weather_data.get("clouds", {}).get("all", 50)
    visibility = weather_data.get("visibility", 10000)
    humidity = weather_data.get("main", {}).get("humidity", 50)
    wind_speed = weather_data.get("wind", {}).get("speed", 0)

    breakpoints = []
    score = 100

    # 1. 云量 → 非线性扣分
    if clouds <= 30:
        cloud_deduct = 0
    elif clouds <= 50:
        factor = (clouds - 30) / 20
        cloud_deduct = factor * 10
    elif clouds <= 75:
        factor = (clouds - 50) / 25
        cloud_deduct = 10 + factor * 20
    else:
        factor = min(1.0, (clouds - 75) / 25)
        cloud_deduct = 30 + factor * 10
    cloud_deduct = round(cloud_deduct)
    score -= cloud_deduct
    breakpoints.append(("云量", f"{clouds}%", f"{cloud_deduct:.0f}"))

    # 2. 能见度
    if visibility < 1000:
        vis_deduct = 30
        vis_label = "< 1km"
    elif visibility < 5000:
        vis_deduct = 15
        vis_label = "1-5km"
    elif visibility < 10000:
        vis_deduct = 5
        vis_label = "5-10km"
    else:
        vis_deduct = 0
        vis_label = "> 10km"
    score -= vis_deduct
    breakpoints.append(("能见度", vis_label, str(vis_deduct)))

    # 3. 湿度
    if humidity > 80:
        humid_deduct = 10
        score -= humid_deduct
        breakpoints.append(("湿度", f"{humidity}%", str(humid_deduct)))
    else:
        breakpoints.append(("湿度", f"{humidity}%", "0"))

    # 4. 月相
    if moon_phase is not None:
        mp = moon_phase.get("phase", 0)
        moon_factor = abs(mp - 0.5) * 2
        moon_penalty = int((1 - moon_factor) * 15)
        score -= moon_penalty
        breakpoints.append(("月相", moon_phase.get("name", "?"), str(moon_penalty)))

    # 5. 风速
    if wind_speed > 15:
        wind_deduct = 15
        wind_label = "> 15m/s"
    elif wind_speed > 10:
        wind_deduct = 5
        wind_label = "10-15m/s"
    else:
        wind_deduct = 0
        wind_label = f"{wind_speed} m/s"
    score -= wind_deduct
    breakpoints.append(("风速", wind_label, str(wind_deduct)))

    # 6. 光污染
    from app.config import config
    light_level = config.light_pollution
    light_deduct = LIGHT_POLUTION_PENALTIES.get(light_level, 15)
    score -= light_deduct
    breakpoints.append(("光污染", light_level, str(light_deduct)))

    score = max(0, min(100, int(score)))

    if score >= 80:
        return score, "🌟 绝佳！今晚超适合观星", "#FFD700", breakpoints
    elif score >= 60:
        return score, "👍 适宜观星", "#4CAF50", breakpoints
    elif score >= 40:
        return score, "🌤 一般，可以试试", "#FFA726", breakpoints
    elif score >= 20:
        return score, "☁️ 云量较多，不太推荐", "#EF5350", breakpoints
    else:
        return score, "🌧 天气不佳，不建议观星", "#EF5350", breakpoints
