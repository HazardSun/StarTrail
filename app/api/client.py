"""统一的 HTTP 客户端层。

星迹所有对外 API 调用都经过这里，集中解决三类问题：

1. **性能**：全局复用一个 ``requests.Session``（带连接池与重试），避免每次
   请求都重建 TCP/TLS 握手；对可缓存的响应按 TTL 做内存缓存，显著降低重复
   查询的延迟。
2. **健壮性**：统一的超时、指数退避重试、规范化的错误结构
   (``{"error": "timeout" | "connection_error" | ...}``)，以及网络延迟上报，
   任何单点故障都不会让 UI 卡死。
3. **VPN / 本地运行安全**：默认全程 HTTPS；仅对**不含密钥**的公开端点
   （ip-api、Celestrak、OpenSky、airplanes.live）在 SSL 失败时回退到 HTTP，
   而携带密钥的端点（OpenWeatherMap、NASA）绝不降级为明文，避免密钥泄露。

设计原则：本模块不依赖任何 GUI/业务配置，可独立 import；延迟上报通过
惰性导入 ``system_monitor`` 实现，即使 psutil 缺失也不会影响网络调用。
"""

from __future__ import annotations

import time
import threading
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# --------------------------------------------------------------------------- #
# 共享 Session（连接池 + 重试）
# --------------------------------------------------------------------------- #

_SESSION: Optional[requests.Session] = None
_SESSION_LOCK = threading.Lock()

_USER_AGENT = "StarTrail/1.1 (+https://github.com/HazardSun/StarTrail)"


def get_session() -> requests.Session:
    """返回进程内复用的 Session；线程安全且仅创建一次。"""
    global _SESSION
    if _SESSION is None:
        with _SESSION_LOCK:
            if _SESSION is None:
                s = requests.Session()
                retry = Retry(
                    total=2,
                    backoff_factor=0.5,
                    status_forcelist=[500, 502, 503, 504],
                    allowed_methods=["GET"],
                    raise_on_status=False,
                )
                adapter = HTTPAdapter(
                    max_retries=retry,
                    pool_connections=4,
                    pool_maxsize=10,
                )
                s.mount("https://", adapter)
                s.mount("http://", adapter)
                s.headers.update({"User-Agent": _USER_AGENT, "Accept": "application/json"})
                _SESSION = s
    return _SESSION


# --------------------------------------------------------------------------- #
# 响应缓存（按 URL+params 的 TTL 内存缓存）
# --------------------------------------------------------------------------- #

_CACHE: Dict[str, tuple] = {}
_CACHE_LOCK = threading.Lock()


def _cache_key(url: str, params: Optional[Dict[str, Any]]) -> str:
    if not params:
        return url
    # 排序保证参数顺序不影响缓存命中
    qs = "&".join(f"{k}={v}" for k, v in sorted(params.items(), key=lambda kv: str(kv[0])))
    return f"{url}?{qs}"


def clear_cache() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()


# --------------------------------------------------------------------------- #
# 延迟上报（惰性导入，避免强依赖 psutil）
# --------------------------------------------------------------------------- #

def _report_latency(ms: float) -> None:
    try:
        from app.api.system_monitor import record_api_latency
        record_api_latency(ms)
    except Exception:
        pass


def _is_secret_endpoint(url: str) -> bool:
    """携带密钥的端点不应回退到明文 HTTP。"""
    return ("openweathermap" in url) or ("api.nasa.gov" in url)


# --------------------------------------------------------------------------- #
# 核心 GET
# --------------------------------------------------------------------------- #

def cached_get(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = 15,
    ttl: int = 300,
    headers: Optional[Dict[str, str]] = None,
    use_cache: bool = True,
) -> Any:
    """发起 GET 请求，返回解析后的 JSON，或在失败时返回错误字典。

    成功结构示例::

        {"coord": ..., "weather": [...]}

    错误结构示例::

        {"error": "timeout"} / {"error": "http_error", "code": 503}
        {"error": "connection_error"} / {"error": "ssl_error"} / {"error": "unknown"}

    ``ttl`` 为缓存有效期（秒）；``use_cache=False`` 强制实时请求。
    """
    key = _cache_key(url, params)
    now = time.time()

    if use_cache and ttl > 0:
        with _CACHE_LOCK:
            hit = _CACHE.get(key)
            if hit is not None and (now - hit[1]) < ttl:
                return hit[0]

    t0 = time.perf_counter()
    try:
        resp = get_session().get(url, params=params, timeout=timeout, headers=headers)
        elapsed = (time.perf_counter() - t0) * 1000.0
        _report_latency(elapsed)

        if resp.status_code == 200:
            try:
                data = resp.json()
            except ValueError:
                return {"error": "invalid_json"}
            if use_cache and ttl > 0:
                with _CACHE_LOCK:
                    _CACHE[key] = (data, now)
            return data
        if resp.status_code == 401:
            return {"error": "invalid_key", "code": 401}
        return {"error": "http_error", "code": resp.status_code}

    except requests.exceptions.SSLError:
        # 仅对不含密钥的公开端点尝试 HTTP 回退
        if _is_secret_endpoint(url):
            _report_latency(-1)
            return {"error": "ssl_error"}
        try:
            http_url = url.replace("https://", "http://")
            resp = get_session().get(http_url, params=params, timeout=timeout, headers=headers)
            elapsed = (time.perf_counter() - t0) * 1000.0
            _report_latency(elapsed)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                except ValueError:
                    return {"error": "invalid_json"}
                if use_cache and ttl > 0:
                    with _CACHE_LOCK:
                        _CACHE[key] = (data, now)
                return data
            return {"error": "http_error", "code": resp.status_code}
        except Exception:
            _report_latency(-1)
            return {"error": "ssl_error"}

    except requests.exceptions.Timeout:
        _report_latency(-1)
        return {"error": "timeout"}
    except requests.exceptions.ConnectionError:
        _report_latency(-1)
        return {"error": "connection_error"}
    except Exception:
        _report_latency(-1)
        return {"error": "unknown"}


def post_json(
    url: str,
    json_body: Optional[Dict[str, Any]] = None,
    timeout: int = 15,
    headers: Optional[Dict[str, str]] = None,
) -> Any:
    """发起 JSON POST（少数 API 需要），同样返回 JSON 或错误字典。"""
    t0 = time.perf_counter()
    try:
        resp = get_session().post(url, json=json_body, timeout=timeout, headers=headers)
        elapsed = (time.perf_counter() - t0) * 1000.0
        _report_latency(elapsed)
        if resp.status_code == 200:
            try:
                return resp.json()
            except ValueError:
                return {"error": "invalid_json"}
        if resp.status_code == 401:
            return {"error": "invalid_key", "code": 401}
        return {"error": "http_error", "code": resp.status_code}
    except requests.exceptions.Timeout:
        _report_latency(-1)
        return {"error": "timeout"}
    except requests.exceptions.ConnectionError:
        _report_latency(-1)
        return {"error": "connection_error"}
    except Exception:
        _report_latency(-1)
        return {"error": "unknown"}
