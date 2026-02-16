import os
import urllib.request


_AUTO_TRUST_ENV_DECISION: bool | None = None


def env_truthy(name: str) -> bool:
    v = (os.getenv(name) or "").strip().lower()
    return v in {"1", "true", "yes", "y", "on"}


def windows_system_proxy_url() -> str | None:
    if os.name != "nt":
        return None
    try:
        proxies = urllib.request.getproxies() or {}
        proxy = proxies.get("https") or proxies.get("http")
        proxy = (str(proxy).strip() if proxy else "")
        if not proxy:
            return None
        if "://" not in proxy:
            proxy = "http://" + proxy
        return proxy
    except Exception:
        return None


def auto_decide_trust_env_for_telegram() -> bool:
    global _AUTO_TRUST_ENV_DECISION
    if _AUTO_TRUST_ENV_DECISION is not None:
        return _AUTO_TRUST_ENV_DECISION

    try:
        import httpx

        with httpx.Client(trust_env=False, timeout=5.0, follow_redirects=True) as client:
            client.get("https://api.telegram.org")

        _AUTO_TRUST_ENV_DECISION = False
    except Exception:
        _AUTO_TRUST_ENV_DECISION = True

    return _AUTO_TRUST_ENV_DECISION
