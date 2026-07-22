import math

from app.config import config
from app.api.client import cached_get

CITIES = [
    ("北京", 39.9042, 116.4074), ("上海", 31.2304, 121.4737),
    ("广州", 23.1291, 113.2644), ("深圳", 22.5431, 114.0579),
    ("杭州", 30.2741, 120.1551), ("成都", 30.5728, 104.0668),
    ("武汉", 30.5928, 114.3055), ("南京", 32.0603, 118.7969),
    ("重庆", 29.4316, 106.9123), ("西安", 34.3416, 108.9398),
    ("天津", 39.1252, 117.1908), ("苏州", 31.2990, 120.5853),
    ("长沙", 28.2282, 112.9388), ("郑州", 34.7466, 113.6253),
    ("东莞", 23.0208, 113.7518), ("青岛", 36.0671, 120.3826),
    ("沈阳", 41.8057, 123.4315), ("昆明", 25.0389, 102.7183),
    ("大连", 38.9140, 121.6147), ("厦门", 24.4798, 118.0894),
    ("哈尔滨", 45.8038, 126.5350), ("济南", 36.6512, 116.9972),
    ("福州", 26.0745, 119.2965), ("合肥", 31.8206, 117.2272),
    ("长春", 43.8171, 125.3235), ("贵阳", 26.4670, 106.6300),
    ("南宁", 22.8170, 108.3665), ("太原", 37.8706, 112.5509),
    ("南昌", 28.6829, 115.8580), ("石家庄", 38.0428, 114.5149),
    ("呼和浩特", 40.8422, 111.7498), ("乌鲁木齐", 43.8256, 87.6168),
    ("拉萨", 29.6500, 91.1000), ("兰州", 36.0611, 103.8343),
    ("西宁", 36.6232, 101.7801), ("银川", 38.4872, 106.2309),
    ("海口", 20.0440, 110.3493), ("台北", 25.0330, 121.5654),
    ("香港", 22.3193, 114.1694), ("澳门", 22.1987, 113.5439),
]

_address_cache = None
last_location_warning = ""


# 内置城市列表全部为国内城市（含港澳台），用于判断“出口 IP 在境外”是否可疑
_CN_CITIES = {c[0] for c in CITIES}


def _is_domestic(cc: str) -> bool:
    """CN/HK/MO/TW 均视为境内，避免把港澳台用户误判为 VPN。"""
    return cc in ("CN", "HK", "MO", "TW")


def _suspect_vpn(cc: str) -> bool:
    """用户当前设置在国内城市，但网络出口 IP 在境外 → 极可能是 VPN/代理。

    此时 IP 定位结果（境外节点）与用户真实位置不符，不应覆盖手动位置。
    """
    if _is_domestic(cc):
        return False
    return config.city_name in _CN_CITIES


def get_location_warning() -> str:
    """返回最近一次自动定位时的提示（如 VPN 告警），无则空字符串。"""
    return last_location_warning


def auto_detect_location(vpn_safe: bool = True):
    """通过 ip-api 获取当前位置。

    返回 ``(city, lat, lon)``。当检测到 VPN/代理导致出口 IP 在境外时，
    为不破坏用户真实（手动设置的）位置，返回 ``(None, 当前lat, 当前lon)``
    并在 :data:`last_location_warning` 中写入告警文案，由调用方决定是否更新。

    全程使用 HTTPS，密钥无关，失败时优雅回退到已保存的配置。
    """
    global _address_cache, last_location_warning
    last_location_warning = ""
    try:
        data = cached_get(
            "https://ip-api.com/json/",
            params={
                "lang": "zh-CN",
                "fields": "status,message,country,countryCode,regionName,city,district,zip,isp,lat,lon",
            },
            timeout=5, ttl=0,
        )
        if isinstance(data, dict) and data.get("status") == "success":
            lat = data.get("lat", config.latitude)
            lon = data.get("lon", config.longitude)
            city = data.get("city", config.city_name)
            country = data.get("country", "")
            cc = data.get("countryCode", "")

            _address_cache = {
                "city": city,
                "region": data.get("regionName", ""),
                "district": data.get("district", ""),
                "zip": data.get("zip", ""),
                "isp": data.get("isp", ""),
                "lat": lat,
                "lon": lon,
                "country": country,
                "countryCode": cc,
            }

            if vpn_safe and _suspect_vpn(cc):
                # 出口 IP 在境外，IP 定位不可信 —— 保留用户手动设置的真实位置
                last_location_warning = (
                    f"检测到网络出口位于境外（{country or cc}），"
                    f"可能是 VPN/代理，IP 定位不可信。已保留你手动设置的「{config.city_name}」"
                )
                return None, config.latitude, config.longitude

            matched_city = _find_nearest_city(lat, lon)
            return matched_city or city, lat, lon
    except Exception:
        pass
    return config.city_name, config.latitude, config.longitude


def get_full_address():
    if _address_cache:
        # VPN 场景下缓存的是境外地址，不应展示为“当前位置”
        if last_location_warning and not _is_domestic(_address_cache.get("countryCode", "")):
            return config.city_name
        parts = [p for p in [
            _address_cache.get("region"),
            _address_cache.get("city"),
            _address_cache.get("district"),
        ] if p]
        return " · ".join(parts) if parts else None

    try:
        data = cached_get(
            "https://ip-api.com/json/",
            params={"lang": "zh-CN", "fields": "status,countryCode,regionName,city,district"},
            timeout=5, ttl=0,
        )
        if isinstance(data, dict) and data.get("status") == "success":
            cc = data.get("countryCode", "")
            if last_location_warning and not _is_domestic(cc):
                return config.city_name
            parts = [p for p in [
                data.get("regionName", ""),
                data.get("city", ""),
                data.get("district", ""),
            ] if p]
            if parts:
                return " · ".join(parts)
    except Exception:
        pass
    return None


def _find_nearest_city(lat, lon):
    best = None
    best_dist_km = 500.0
    for name, clat, clon in CITIES:
        lat1, lon1 = math.radians(lat), math.radians(lon)
        lat2, lon2 = math.radians(clat), math.radians(clon)
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        dist_km = 6371 * c
        if dist_km < best_dist_km:
            best = name
            best_dist_km = dist_km
    return best if best_dist_km < 50.0 else None


def get_city_names():
    return [c[0] for c in CITIES]


def get_coords(city_name):
    for name, lat, lon in CITIES:
        if name == city_name:
            return lat, lon
    return config.latitude, config.longitude


OBSERVATION_SITES = {
    "北京": [("雾灵山天文台", 120, "暗空区", "🐉"), ("延庆华海天文农庄", 90, "乡村", "🌾"), ("国家天文台兴隆站", 150, "暗空区", "🔭")],
    "上海": [("崇明东滩", 60, "乡村", "🌿"), ("南汇嘴", 70, "郊区", "🌊"), ("天荒坪", 230, "暗空区", "⛰️")],
    "广州": [("从化阿婆六", 100, "乡村", "🌄"), ("佛山高明茶山", 80, "乡村", "🍵"), ("肇庆鼎湖山", 110, "乡村", "🌲")],
    "深圳": [("大鹏半岛", 60, "乡村", "🏝️"), ("西涌天文台", 65, "乡村", "🔭"), ("南澳", 55, "郊区", "🌅")],
    "杭州": [("天荒坪", 80, "暗空区", "⛰️"), ("大明山", 100, "乡村", "🌄"), ("莫干山", 90, "乡村", "🏔️")],
    "成都": [("龙泉山", 40, "郊区", "🌄"), ("四姑娘山", 200, "暗空区", "🏔️"), ("峨眉山", 150, "乡村", "⛰️")],
    "武汉": [("木兰山", 60, "乡村", "🌲"), ("九宫山", 200, "暗空区", "⛰️"), ("大别山", 180, "乡村", "🏔️")],
    "南京": [("紫金山天文台", 15, "郊区", "🔭"), ("盱眙天文台", 120, "乡村", "🌾"), ("老山", 30, "郊区", "🌲")],
    "重庆": [("南山", 15, "郊区", "🌄"), ("仙女山", 200, "乡村", "🏔️"), ("金佛山", 180, "暗空区", "⛰️")],
    "西安": [("翠华山", 40, "乡村", "🌲"), ("太白山", 120, "暗空区", "🏔️"), ("骊山", 30, "郊区", "🌅")],
    "天津": [("盘山", 110, "乡村", "⛰️"), ("蓟州九山顶", 130, "乡村", "🌲"), ("北大港湿地", 60, "乡村", "🌾")],
    "苏州": [("西山", 40, "郊区", "🏝️"), ("东山", 45, "郊区", "🌾"), ("太湖", 35, "郊区", "🌊")],
    "长沙": [("岳麓山", 10, "郊区", "🍁"), ("大围山", 150, "暗空区", "⛰️"), ("黑麋峰", 35, "郊区", "🌄")],
    "郑州": [("嵩山", 70, "乡村", "⛰️"), ("云台山", 90, "乡村", "🏔️"), ("黄河湿地", 40, "郊区", "🌾")],
    "东莞": [("银瓶山", 50, "乡村", "🌲"), ("大岭山", 30, "郊区", "🌳"), ("松山湖", 25, "郊区", "🌊")],
    "青岛": [("崂山", 30, "乡村", "⛰️"), ("即墨田横岛", 80, "乡村", "🏝️"), ("灵山岛", 60, "暗空区", "🏝️")],
    "沈阳": [("棋盘山", 30, "郊区", "♟️"), ("本溪大石湖", 120, "乡村", "🌲"), ("鞍山千山", 90, "乡村", "⛰️")],
    "昆明": [("云南天文台", 12, "郊区", "🔭"), ("抚仙湖", 80, "暗空区", "🌊"), ("丽江高美古", 500, "暗空区", "🔭")],
    "大连": [("大黑山", 35, "乡村", "⛰️"), ("旅顺老铁山", 50, "乡村", "🌅"), ("金石滩", 55, "郊区", "🏝️")],
    "厦门": [("鼓浪屿", 5, "郊区", "🏝️"), ("漳州镇海角", 80, "乡村", "🌊"), ("武夷山", 350, "暗空区", "⛰️")],
    "哈尔滨": [("太阳岛", 15, "郊区", "☀️"), ("帽儿山", 90, "乡村", "⛰️"), ("五大连池", 350, "暗空区", "🌋")],
    "济南": [("千佛山", 8, "郊区", "⛰️"), ("泰山", 70, "乡村", "🏔️"), ("红叶谷", 40, "郊区", "🍁")],
    "福州": [("鼓岭", 20, "郊区", "🌲"), ("平潭岛", 120, "乡村", "🏝️"), ("武夷山", 280, "暗空区", "⛰️")],
    "合肥": [("紫蓬山", 25, "郊区", "🌲"), ("巢湖姥山", 50, "乡村", "🌊"), ("黄山", 280, "暗空区", "🏔️")],
    "长春": [("净月潭", 20, "郊区", "🌲"), ("长白山", 380, "暗空区", "🏔️"), ("莲花山", 35, "郊区", "🌄")],
    "贵阳": [("黔灵山", 10, "郊区", "🌲"), ("花溪", 20, "郊区", "🌊"), ("荔波茂兰", 280, "暗空区", "🌳")],
    "南宁": [("青秀山", 10, "郊区", "🌴"), ("大明山", 100, "暗空区", "⛰️"), ("德天瀑布", 200, "乡村", "🌊")],
    "太原": [("天龙山", 30, "乡村", "🐉"), ("晋祠", 25, "郊区", "🏛️"), ("五台山", 200, "暗空区", "⛰️")],
    "南昌": [("梅岭", 15, "郊区", "🌲"), ("庐山", 120, "暗空区", "⛰️"), ("三清山", 280, "暗空区", "🏔️")],
    "石家庄": [("苍岩山", 60, "乡村", "⛰️"), ("嶂石岩", 90, "乡村", "🗻"), ("西柏坡", 70, "乡村", "🌄")],
    "呼和浩特": [("大青山", 25, "乡村", "⛰️"), ("希拉穆仁草原", 120, "暗空区", "🌾"), ("响沙湾", 200, "暗空区", "🏜️")],
    "乌鲁木齐": [("南山牧场", 60, "暗空区", "🐑"), ("天山天池", 110, "暗空区", "🏔️"), ("达坂城", 90, "暗空区", "🌄")],
    "拉萨": [("色拉寺后山", 8, "暗空区", "🏔️"), ("纳木错", 200, "暗空区", "🌊"), ("羊八井", 90, "暗空区", "♨️")],
    "兰州": [("白塔山", 5, "郊区", "🏯"), ("兴隆山", 45, "乡村", "⛰️"), ("刘家峡", 80, "乡村", "🌊")],
    "西宁": [("湟中塔尔寺", 25, "乡村", "🏛️"), ("青海湖", 150, "暗空区", "🌊"), ("祁连山", 280, "暗空区", "🏔️")],
    "银川": [("贺兰山", 40, "暗空区", "⛰️"), ("沙湖", 50, "乡村", "🌊"), ("西夏王陵", 30, "乡村", "🏛️")],
    "海口": [("火山口公园", 15, "郊区", "🌋"), ("文昌航天城", 70, "乡村", "🚀"), ("五指山", 220, "暗空区", "⛰️")],
    "台北": [("阳明山", 15, "郊区", "🌋"), ("合欢山", 300, "暗空区", "🏔️"), ("玉山", 350, "暗空区", "⛰️")],
    "香港": [("麦理浩径", 30, "乡村", "🥾"), ("大屿山", 30, "乡村", "🏝️"), ("西贡", 25, "郊区", "🌊")],
    "澳门": [("路环", 10, "郊区", "🏝️"), ("氹仔", 8, "郊区", "🎰"), ("黑沙海滩", 12, "郊区", "🏖️")],
}


def get_nearby_sites(city_name=None):
    """Return nearby observation sites for a city, or all if city not found."""
    if city_name is None:
        city_name = config.city_name
    return OBSERVATION_SITES.get(city_name, [])[:4]
