import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEMO_KEY = "DEMO_KEY"


def _session():
    s = requests.Session()
    retries = Retry(total=2, backoff_factor=1, status_forcelist=[500, 502, 503])
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://", HTTPAdapter(max_retries=retries))
    return s


def _fetch(url, params, timeout=20):
    """HTTPS-only fetch. No HTTP fallback to protect API key."""
    session = _session()
    try:
        resp = session.get(url, params=params, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        return {"error": "http_error", "code": resp.status_code}
    except requests.exceptions.SSLError:
        return {"error": "ssl_error"}
    except requests.exceptions.Timeout:
        return {"error": "timeout"}
    except requests.exceptions.ConnectionError:
        return {"error": "connection_error"}
    except Exception:
        return {"error": "unknown"}


def test_key(api_key):
    key = api_key or DEMO_KEY
    result = _fetch(
        "https://api.nasa.gov/planetary/apod",
        {"api_key": key, "count": 1}
    )
    if isinstance(result, dict):
        err = result.get("error")
        if err == "http_error":
            return False, f"服务返回错误 ({result.get('code', '?')})"
        if err == "timeout":
            return False, "连接超时，请检查网络"
    return True, None


def get_apod(api_key=None, date=None):
    key = api_key or DEMO_KEY
    params = {"api_key": key}
    if date:
        params["date"] = date
    return _fetch("https://api.nasa.gov/planetary/apod", params)
