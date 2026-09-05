"""SSO helpers for auth.pratikp.com (Google sign-in)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from app.config import get_settings


def sso_configured() -> bool:
    settings = get_settings()
    return bool(settings.sso_app_secret.strip() and settings.sso_app_slug.strip())


def exchange_sso_code(code: str) -> dict[str, Any]:
    """POST code to auth portal; returns provider payload on success.

    Expected success shape includes email and optional session_token / final_redirect.
    """
    settings = get_settings()
    if not sso_configured():
        raise RuntimeError("SSO is not configured")

    url = f"{settings.sso_auth_base_url.rstrip('/')}/exchange-code.php"
    body = json.dumps(
        {
            "code": code.strip(),
            "app": settings.sso_app_slug,
            "app_secret": settings.sso_app_secret,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read().decode("utf-8")
        except Exception:
            raise RuntimeError("SSO exchange failed") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("SSO provider unreachable") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("SSO exchange returned invalid JSON") from exc

    if not isinstance(data, dict) or not data.get("success"):
        raise RuntimeError("SSO exchange failed")
    return data
