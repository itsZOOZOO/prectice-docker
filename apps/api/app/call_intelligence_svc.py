"""Per-clinic Call Intelligence linking + HTTP proxy to calls.aarogyams.com."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.clinic_settings_svc import get_setting, set_setting

ENABLED_KEY = "call_intelligence_enabled"
TOKEN_KEY = "call_intelligence_api_token"
BASE_URL_KEY = "call_intelligence_api_base"

DEFAULT_BASE_URL = "https://calls.aarogyams.com/api"


def _truthy(value: str) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def get_base_url(db: Session, clinic_id: int) -> str:
    raw = get_setting(db, clinic_id, BASE_URL_KEY, "").strip()
    return (raw or DEFAULT_BASE_URL).rstrip("/")


def get_token(db: Session, clinic_id: int) -> str:
    return get_setting(db, clinic_id, TOKEN_KEY, "").strip()


def is_enabled(db: Session, clinic_id: int) -> bool:
    return _truthy(get_setting(db, clinic_id, ENABLED_KEY, "0"))


def has_token(db: Session, clinic_id: int) -> bool:
    return bool(get_token(db, clinic_id))


def can_use(db: Session, clinic_id: int) -> bool:
    return is_enabled(db, clinic_id) and has_token(db, clinic_id)


def clinic_status(db: Session, clinic_id: int) -> dict[str, Any]:
    enabled = is_enabled(db, clinic_id)
    token_set = has_token(db, clinic_id)
    return {
        "enabled": enabled,
        "has_token": token_set,
        "can_use": enabled and token_set,
    }


def admin_status(db: Session, clinic_id: int) -> dict[str, Any]:
    token = get_token(db, clinic_id)
    return {
        "enabled": is_enabled(db, clinic_id),
        "has_token": bool(token),
        "token_hint": f"…{token[-4:]}" if len(token) >= 4 else (token if token else None),
        "api_base_url": get_base_url(db, clinic_id),
        "default_api_base_url": DEFAULT_BASE_URL,
        "can_use": can_use(db, clinic_id),
    }


def assert_can_use(db: Session, clinic_id: int) -> None:
    if not is_enabled(db, clinic_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Call Intelligence is not enabled for this clinic.",
        )
    if not has_token(db, clinic_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Call Intelligence API token is not configured for this clinic.",
        )


def smoke_test(db: Session, clinic_id: int, *, token: str | None = None, base_url: str | None = None) -> dict[str, Any]:
    """Hit /priority-devices with the given or stored credentials."""
    use_token = (token if token is not None else get_token(db, clinic_id)).strip()
    use_base = (base_url if base_url is not None else get_base_url(db, clinic_id)).rstrip("/")
    if not use_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API token is required for smoke test.",
        )
    data = _request_raw("GET", f"{use_base}/priority-devices", use_token)
    devices = data.get("devices") if isinstance(data, dict) else None
    count = len(devices) if isinstance(devices, list) else 0
    return {"ok": True, "devices_count": count}


def save_admin_config(
    db: Session,
    clinic_id: int,
    *,
    enabled: bool | None = None,
    api_token: str | None = None,
    clear_token: bool = False,
    api_base_url: str | None = None,
    run_smoke_test: bool = True,
) -> dict[str, Any]:
    next_enabled = is_enabled(db, clinic_id) if enabled is None else bool(enabled)
    next_token = get_token(db, clinic_id)
    if clear_token:
        next_token = ""
    elif api_token is not None and api_token.strip():
        next_token = api_token.strip()

    next_base = get_base_url(db, clinic_id)
    if api_base_url is not None:
        base = api_base_url.strip().rstrip("/")
        next_base = base or DEFAULT_BASE_URL

    smoke: dict[str, Any] | None = None
    if run_smoke_test and next_enabled and next_token:
        smoke = smoke_test(db, clinic_id, token=next_token, base_url=next_base)

    if enabled is not None:
        set_setting(db, clinic_id, ENABLED_KEY, "1" if enabled else "0")

    if clear_token:
        set_setting(db, clinic_id, TOKEN_KEY, None)
    elif api_token is not None:
        token = api_token.strip()
        if token:
            set_setting(db, clinic_id, TOKEN_KEY, token)

    if api_base_url is not None:
        base = api_base_url.strip().rstrip("/")
        if not base or base == DEFAULT_BASE_URL:
            set_setting(db, clinic_id, BASE_URL_KEY, None)
        else:
            set_setting(db, clinic_id, BASE_URL_KEY, base)

    db.commit()

    out = admin_status(db, clinic_id)
    if smoke is not None:
        out["smoke_test"] = smoke
    return out


def _request_raw(
    method: str,
    url: str,
    token: str,
    *,
    query: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if query:
        filtered = {k: v for k, v in query.items() if v is not None and v != ""}
        if filtered:
            url = f"{url}?{urllib.parse.urlencode(filtered)}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    data_bytes: bytes | None = None
    if body is not None and method in {"POST", "PUT", "PATCH"}:
        data_bytes = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read().decode("utf-8")
            http_code = getattr(resp, "status", 200) or 200
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        http_code = e.code
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {}
        message = payload.get("error") if isinstance(payload, dict) else None
        if not isinstance(message, str) or not message:
            message = f"Call Intelligence API error ({http_code})"
        raise HTTPException(
            status_code=http_code if 400 <= http_code < 600 else status.HTTP_502_BAD_GATEWAY,
            detail=message,
        ) from e
    except urllib.error.URLError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Call Intelligence API unreachable: {e.reason}",
        ) from e

    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid response from Call Intelligence API.",
        ) from e

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid response from Call Intelligence API.",
        )

    if http_code >= 400 or not payload.get("ok"):
        message = payload.get("error")
        if not isinstance(message, str) or not message:
            message = "Call Intelligence API error"
        raise HTTPException(
            status_code=http_code if 400 <= http_code < 600 else status.HTTP_502_BAD_GATEWAY,
            detail=message,
        )

    data = payload.get("data")
    return data if isinstance(data, dict) else {}


def proxy(
    db: Session,
    clinic_id: int,
    method: str,
    path: str,
    *,
    query: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    assert_can_use(db, clinic_id)
    base = get_base_url(db, clinic_id)
    token = get_token(db, clinic_id)
    if not path.startswith("/"):
        path = "/" + path
    return _request_raw(method, f"{base}{path}", token, query=query, body=body)
