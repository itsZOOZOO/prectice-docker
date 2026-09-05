"""Per-clinic Lead Intelligence linking + proxy to leads.quantumdental.in/practice-api."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.clinic_settings_svc import get_setting, set_setting

ENABLED_KEY = "lead_intelligence_enabled"
TOKEN_KEY = "lead_intelligence_api_token"
BASE_URL_KEY = "lead_intelligence_api_base"
USER_ID_KEY = "lead_intelligence_user_id"
USER_NAME_KEY = "lead_intelligence_user_name"
USER_EMAIL_KEY = "lead_intelligence_user_email"

DEFAULT_BASE_URL = "https://leads.quantumdental.in/practice-api"


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


def linked_user(db: Session, clinic_id: int) -> dict[str, Any] | None:
    if not has_token(db, clinic_id):
        return None
    uid = int(get_setting(db, clinic_id, USER_ID_KEY, "0") or 0)
    name = get_setting(db, clinic_id, USER_NAME_KEY, "").strip()
    email = get_setting(db, clinic_id, USER_EMAIL_KEY, "").strip()
    if uid <= 0 and not name and not email:
        return None
    return {
        "id": uid,
        "name": name or None,
        "email": email or None,
    }


def clinic_status(db: Session, clinic_id: int) -> dict[str, Any]:
    enabled = is_enabled(db, clinic_id)
    token_set = has_token(db, clinic_id)
    return {
        "enabled": enabled,
        "has_api_key": token_set,
        "can_use": enabled and token_set,
        "can_manage_link": False,  # superadmin-only via /admin
        "linked_user": linked_user(db, clinic_id),
    }


def admin_status(db: Session, clinic_id: int) -> dict[str, Any]:
    token = get_token(db, clinic_id)
    return {
        "enabled": is_enabled(db, clinic_id),
        "has_api_key": bool(token),
        "token_hint": f"…{token[-4:]}" if len(token) >= 4 else (token if token else None),
        "api_base_url": get_base_url(db, clinic_id),
        "default_api_base_url": DEFAULT_BASE_URL,
        "can_use": can_use(db, clinic_id),
        "linked_user": linked_user(db, clinic_id),
    }


def assert_can_use(db: Session, clinic_id: int) -> None:
    if not is_enabled(db, clinic_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Lead Intelligence is not enabled for this clinic.",
        )
    if not has_token(db, clinic_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Leads account is not linked for this clinic.",
        )


def _http_get(url: str, token: str) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        method="GET",
    )
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
            if http_code in (401, 403):
                message = "Leads API authentication failed."
            else:
                message = f"Leads Practice API error ({http_code})"
        raise HTTPException(
            status_code=http_code if 400 <= http_code < 600 else status.HTTP_502_BAD_GATEWAY,
            detail=message,
        ) from e
    except urllib.error.URLError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Leads Practice API unreachable: {e.reason}",
        ) from e

    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid response from Leads Practice API.",
        ) from e

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid response from Leads Practice API.",
        )

    if http_code >= 400:
        message = payload.get("error")
        if not isinstance(message, str) or not message:
            message = "Leads Practice API error."
        raise HTTPException(
            status_code=http_code if 400 <= http_code < 600 else status.HTTP_502_BAD_GATEWAY,
            detail=message,
        )

    return payload


def validate_token(token: str, base_url: str | None = None) -> dict[str, Any]:
    token = (token or "").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="API token is required.")
    base = (base_url or DEFAULT_BASE_URL).strip().rstrip("/") or DEFAULT_BASE_URL
    payload = _http_get(f"{base}/me", token)
    if not payload.get("success"):
        err = payload.get("error")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=err if isinstance(err, str) and err else "Invalid leads API token.",
        )
    user = payload.get("user") if isinstance(payload.get("user"), dict) else {}
    uid = int(user.get("id") or 0)
    if uid <= 0:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Leads API did not return a user.",
        )
    name = user.get("name")
    email = user.get("email")
    return {
        "id": uid,
        "name": str(name) if name else None,
        "email": str(email) if email else None,
    }


def smoke_test(
    db: Session,
    clinic_id: int,
    *,
    token: str | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    use_token = (token if token is not None else get_token(db, clinic_id)).strip()
    use_base = (base_url if base_url is not None else get_base_url(db, clinic_id)).rstrip("/")
    user = validate_token(use_token, use_base)
    return {"ok": True, "linked_user": user}


def _store_linked_user(db: Session, clinic_id: int, user: dict[str, Any] | None) -> None:
    if not user:
        set_setting(db, clinic_id, USER_ID_KEY, None)
        set_setting(db, clinic_id, USER_NAME_KEY, None)
        set_setting(db, clinic_id, USER_EMAIL_KEY, None)
        return
    set_setting(db, clinic_id, USER_ID_KEY, str(int(user.get("id") or 0)))
    set_setting(db, clinic_id, USER_NAME_KEY, (user.get("name") or "") or None)
    set_setting(db, clinic_id, USER_EMAIL_KEY, (user.get("email") or "") or None)


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
    linked: dict[str, Any] | None = None
    if run_smoke_test and next_enabled and next_token:
        smoke = smoke_test(db, clinic_id, token=next_token, base_url=next_base)
        linked = smoke.get("linked_user") if isinstance(smoke, dict) else None

    if enabled is not None:
        set_setting(db, clinic_id, ENABLED_KEY, "1" if enabled else "0")

    if clear_token:
        set_setting(db, clinic_id, TOKEN_KEY, None)
        _store_linked_user(db, clinic_id, None)
    elif api_token is not None:
        token = api_token.strip()
        if token:
            set_setting(db, clinic_id, TOKEN_KEY, token)
            if linked:
                _store_linked_user(db, clinic_id, linked)
    elif linked and next_token and not clear_token:
        # Enabling with existing token — refresh linked user from smoke
        _store_linked_user(db, clinic_id, linked)

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


def response_log(db: Session, clinic_id: int, query: dict[str, Any]) -> dict[str, Any]:
    assert_can_use(db, clinic_id)
    token = get_token(db, clinic_id)
    base = get_base_url(db, clinic_id)

    forward: dict[str, Any] = {}
    for key in ("period", "from", "to", "ym", "limit", "duty", "all_groups"):
        val = query.get(key)
        if val is not None and val != "":
            forward[key] = val
    for key in ("group_or", "group_and"):
        val = query.get(key)
        if isinstance(val, list) and val:
            forward[key] = [int(x) for x in val if str(x).strip() != ""]
        elif isinstance(val, str) and val.strip():
            forward[key] = val

    url = f"{base}/response-log"
    if forward:
        # Match PHP http_build_query array style: group_or[0]=…
        url = f"{url}?{urllib.parse.urlencode(forward, doseq=True)}"

    payload = _http_get(url, token)
    if not payload.get("success"):
        err = payload.get("error")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=err if isinstance(err, str) and err else "Failed to load lead response log.",
        )
    payload = dict(payload)
    payload.pop("success", None)
    return payload
