"""天体信息链接生成。

双击星图中的天体时打开的资料页。所有链接指向稳定、公开、可访问的权威来源：

- 恒星 / 行星 / 太阳 / 月亮：中文维基百科（按中文名直达词条）
- 深空天体 (DSO)：Aladin Lite 实景星图（按 M / NGC 编号定位）
- 人造卫星：N2YO（按 NORAD 编号）
- 航空器：Flightradar24（按 ICAO24）/ JetPhotos（按注册号）

对无法精确匹配的天体，统一回退到维基百科搜索页（始终可打开），
避免指向已失效的站点（如旧的 starfyi.com）导致「链接打不开」。
"""
from urllib.parse import quote

WIKI_ZH = "https://zh.wikipedia.org/wiki/"
WIKI_SEARCH = "https://www.wikipedia.org/w/index.php?search={q}&title=Special:Search"
ALADIN = "https://aladin.cds.unistra.fr/AladinLite/?target={t}&fov=0.5&survey=CDS%2FP%2FDSS2%2Fcolor"


def _has_cjk(s: str) -> bool:
    return any('\u4e00' <= c <= '\u9fff' for c in s)


def _wiki_search(query: str) -> str:
    return WIKI_SEARCH.format(q=quote(query))


def get_info_url(obj) -> "str | None":
    """根据天体对象返回其资料页 URL；无合适链接时返回 None。"""
    if not isinstance(obj, dict):
        return None
    obj_type = obj.get("type", "")
    name = (obj.get("name") or "").strip()

    if obj_type == "star":
        if name:
            # 中文专名直达中文维基；其余（星表编号等）回退维基搜索
            if _has_cjk(name):
                return WIKI_ZH + quote(name)
            return _wiki_search(name + " star")
        return None

    if obj_type == "planet":
        return WIKI_ZH + quote(name) if name else None

    if obj_type == "sun":
        return WIKI_ZH + "太阳"

    if obj_type == "moon":
        return WIKI_ZH + "月球"

    if obj_type == "dso":
        obj_id = (obj.get("id") or "").strip()
        if obj_id:
            return ALADIN.format(t=quote(obj_id))
        if name:
            return _wiki_search(name)
        return None

    if obj_type == "satellite":
        norad = obj.get("norad") or obj.get("norad_id")
        if norad:
            return f"https://www.n2yo.com/satellite/?s={norad}"
        return None

    if obj_type == "aircraft":
        icao = (obj.get("icao") or "").strip()
        if icao:
            return "https://www.flightradar24.com/" + quote(icao.lower())
        reg = (obj.get("registration") or "").strip()
        if reg:
            return "https://www.jetphotos.com/registration/" + quote(reg)
        if name:
            return _wiki_search(name + " aircraft")
        return None

    return None


def dso_aladin_url(obj_id) -> str:
    """返回 DSO 的 Aladin Lite 实景星图链接（供详情面板复用）。"""
    obj_id = (obj_id or "").strip()
    if not obj_id:
        return ""
    return ALADIN.format(t=quote(obj_id))
