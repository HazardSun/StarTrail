"""NASA APOD（每日一天文图）访问层，统一走 :mod:`app.api.client`。"""

from app.api.client import cached_get

DEMO_KEY = "DEMO_KEY"
APOD_URL = "https://api.nasa.gov/planetary/apod"
APOD_TTL = 3600  # 一天文图每小时最多刷新一次


def test_key(api_key: str):
    key = api_key or DEMO_KEY
    result = cached_get(
        APOD_URL,
        {"api_key": key, "count": 1},
        timeout=15, ttl=0,
    )
    if isinstance(result, dict):
        err = result.get("error")
        if err == "http_error":
            return False, f"服务返回错误 ({result.get('code', '?')})"
        if err == "timeout":
            return False, "连接超时，请检查网络"
        if err == "ssl_error":
            return False, "SSL 连接失败（请检查网络/VPN）"
        if err == "invalid_key":
            return False, "API 密钥无效 (401)，请在设置中检查并重新填写"
    return True, None


def get_apod(api_key=None, date=None):
    key = api_key or DEMO_KEY
    params = {"api_key": key}
    if date:
        params["date"] = date
    return cached_get(APOD_URL, params, timeout=15, ttl=APOD_TTL)
