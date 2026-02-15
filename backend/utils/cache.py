from __future__ import annotations

import json
import os
import threading
import time
from typing import Any


class _MemoryCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: dict[str, tuple[float, str]] = {}

    def get(self, key: str) -> str | None:
        now = time.time()
        with self._lock:
            item = self._items.get(key)
            if not item:
                return None
            expires_at, value = item
            if expires_at <= now:
                self._items.pop(key, None)
                return None
            return value

    def set(self, key: str, value: str, ttl_s: int) -> None:
        ttl_s = max(0, int(ttl_s))
        if ttl_s <= 0:
            return
        expires_at = time.time() + ttl_s
        with self._lock:
            self._items[key] = (expires_at, value)


_mem_cache = _MemoryCache()


def _get_redis_client():
    url = (os.getenv("REDIS_URL") or "").strip()
    if not url:
        return None
    try:
        import redis  # type: ignore

        return redis.Redis.from_url(url, decode_responses=True)
    except Exception:
        return None


def cache_get_json(key: str) -> Any | None:
    key = str(key)
    r = _get_redis_client()
    if r is not None:
        try:
            raw = r.get(key)
            if not raw:
                return None
            return json.loads(raw)
        except Exception:
            return None

    raw = _mem_cache.get(key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def cache_set_json(key: str, value: Any, ttl_s: int) -> None:
    key = str(key)
    ttl_s = max(0, int(ttl_s))
    if ttl_s <= 0:
        return

    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    r = _get_redis_client()
    if r is not None:
        try:
            r.setex(key, ttl_s, raw)
            return
        except Exception:
            pass

    _mem_cache.set(key, raw, ttl_s)
