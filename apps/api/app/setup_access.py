"""Desk setup PIN unlock (HMAC token + ClinicSetting storage)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time
from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user, hash_password, verify_password
from app.clinic_settings_svc import get_setting, set_setting
from app.config import get_settings
from app.db import get_db
from app.models import User

PIN_HASH_KEY = "desk_setup_pin_hash"
UNLOCK_TTL_KEY = "desk_setup_unlock_ttl_minutes"
DEFAULT_UNLOCK_TTL_MINUTES = 45
MIN_PIN_LENGTH = 4
MAX_PIN_LENGTH = 6
MAX_PIN_ATTEMPTS = 5
PIN_LOCK_SECONDS = 300

_PIN_RE = re.compile(r"^\d+$")

# In-memory failed PIN attempts: key -> {count, window_start, locked_until}
_pin_failures: dict[str, dict[str, int]] = {}


def _failure_key(clinic_id: int, user_id: int) -> str:
    return hashlib.sha256(f"setup_pin:{clinic_id}:{user_id}".encode()).hexdigest()


def get_pin_hash(db: Session, clinic_id: int) -> str | None:
    value = get_setting(db, clinic_id, PIN_HASH_KEY, "")
    return value if value else None


def is_pin_configured(db: Session, clinic_id: int) -> bool:
    return get_pin_hash(db, clinic_id) is not None


def get_unlock_ttl_minutes(db: Session, clinic_id: int) -> int:
    raw = int(get_setting(db, clinic_id, UNLOCK_TTL_KEY, str(DEFAULT_UNLOCK_TTL_MINUTES)) or DEFAULT_UNLOCK_TTL_MINUTES)
    if raw < 15:
        return DEFAULT_UNLOCK_TTL_MINUTES
    if raw > 240:
        return 240
    return raw


def get_status(db: Session, clinic_id: int) -> dict[str, Any]:
    return {
        "pin_configured": is_pin_configured(db, clinic_id),
        "unlock_ttl_minutes": get_unlock_ttl_minutes(db, clinic_id),
    }


def _validate_pin_pair(pin: str, confirm_pin: str) -> str:
    pin = (pin or "").strip()
    confirm_pin = (confirm_pin or "").strip()
    if not _PIN_RE.match(pin):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Setup PIN must contain digits only.",
        )
    length = len(pin)
    if length < MIN_PIN_LENGTH or length > MAX_PIN_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Setup PIN must be {MIN_PIN_LENGTH}–{MAX_PIN_LENGTH} digits.",
        )
    if pin != confirm_pin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PIN confirmation does not match.",
        )
    return pin


def create_pin(db: Session, clinic_id: int, pin: str, confirm_pin: str) -> None:
    if get_pin_hash(db, clinic_id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Setup PIN is already configured for this clinic.",
        )
    pin = _validate_pin_pair(pin, confirm_pin)
    set_setting(db, clinic_id, PIN_HASH_KEY, hash_password(pin))


def _assert_not_pin_locked(clinic_id: int, user_id: int) -> None:
    state = _pin_failures.get(_failure_key(clinic_id, user_id))
    if not state:
        return
    locked_until = int(state.get("locked_until") or 0)
    now = int(time.time())
    if locked_until > now:
        wait = max(1, locked_until - now)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many incorrect PIN attempts. Try again in {wait} seconds.",
        )


def _record_pin_failure(clinic_id: int, user_id: int) -> None:
    key = _failure_key(clinic_id, user_id)
    now = int(time.time())
    state = _pin_failures.get(key) or {"count": 0, "window_start": now, "locked_until": 0}
    window_start = int(state.get("window_start") or now)
    count = int(state.get("count") or 0)
    if now - window_start >= PIN_LOCK_SECONDS:
        window_start = now
        count = 0
    count += 1
    locked_until = 0
    if count >= MAX_PIN_ATTEMPTS:
        locked_until = now + PIN_LOCK_SECONDS
        count = 0
        window_start = now
    _pin_failures[key] = {
        "count": count,
        "window_start": window_start,
        "locked_until": locked_until,
    }


def _clear_pin_failures(clinic_id: int, user_id: int) -> None:
    _pin_failures.pop(_failure_key(clinic_id, user_id), None)


def _signing_secret() -> str:
    return get_settings().jwt_secret


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes | None:
    try:
        pad = "=" * ((4 - len(data) % 4) % 4)
        return base64.urlsafe_b64decode(data + pad)
    except (ValueError, TypeError):
        return None


def issue_unlock_token(clinic_id: int, user_id: int, expires_at: int) -> dict[str, Any]:
    payload = json.dumps({"c": clinic_id, "u": user_id, "e": expires_at}, separators=(",", ":"))
    payload_b64 = _b64url_encode(payload.encode("utf-8"))
    sig = hmac.new(
        _signing_secret().encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return {"expires_at": expires_at, "token": f"{payload_b64}.{sig}"}


def verify_unlock_token(clinic_id: int, user_id: int, token: str) -> bool:
    parts = (token or "").split(".", 1)
    if len(parts) != 2:
        return False
    payload_b64, sig = parts
    expected = hmac.new(
        _signing_secret().encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return False
    raw = _b64url_decode(payload_b64)
    if raw is None:
        return False
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False
    if not isinstance(payload, dict):
        return False
    return (
        int(payload.get("c") or 0) == clinic_id
        and int(payload.get("u") or 0) == user_id
        and int(payload.get("e") or 0) >= int(time.time())
    )


def unlock(db: Session, clinic_id: int, user_id: int, pin: str) -> dict[str, Any]:
    _assert_not_pin_locked(clinic_id, user_id)
    pin_hash = get_pin_hash(db, clinic_id)
    if pin_hash is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setup PIN is not configured yet.",
        )
    pin = (pin or "").strip()
    if not verify_password(pin, pin_hash):
        _record_pin_failure(clinic_id, user_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Incorrect setup PIN.",
        )
    _clear_pin_failures(clinic_id, user_id)
    expires_at = int(time.time()) + get_unlock_ttl_minutes(db, clinic_id) * 60
    return issue_unlock_token(clinic_id, user_id, expires_at)


def require_unlocked(
    db: Session,
    clinic_id: int,
    user_id: int,
    token: str | None,
    *,
    require_pin_configured: bool = True,
) -> None:
    if not is_pin_configured(db, clinic_id):
        if require_pin_configured:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Clinic setup PIN is not configured.",
            )
        return
    if not token or not verify_unlock_token(clinic_id, user_id, token.strip()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Setup PIN required. Unlock clinic setup to continue.",
        )


def change_pin(
    db: Session,
    clinic_id: int,
    user_id: int,
    token: str | None,
    current_pin: str,
    new_pin: str,
    confirm_pin: str,
) -> None:
    require_unlocked(db, clinic_id, user_id, token, require_pin_configured=True)
    pin_hash = get_pin_hash(db, clinic_id)
    if pin_hash is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setup PIN is not configured yet.",
        )
    current_pin = (current_pin or "").strip()
    if not verify_password(current_pin, pin_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Current setup PIN is incorrect.",
        )
    new_pin = _validate_pin_pair(new_pin, confirm_pin)
    if current_pin == new_pin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New PIN must be different from the current PIN.",
        )
    set_setting(db, clinic_id, PIN_HASH_KEY, hash_password(new_pin))


def set_unlock_ttl_minutes(
    db: Session,
    clinic_id: int,
    user_id: int,
    token: str | None,
    minutes: int,
) -> int:
    require_unlocked(db, clinic_id, user_id, token, require_pin_configured=True)
    if minutes < 15 or minutes > 240:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Auto-lock duration must be between 15 and 240 minutes.",
        )
    set_setting(db, clinic_id, UNLOCK_TTL_KEY, str(int(minutes)))
    return int(minutes)


def require_setup_unlock(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_setup_unlock: Annotated[str | None, Header(alias="X-Setup-Unlock")] = None,
) -> None:
    """
    FastAPI dependency for locked settings mutations.

    If no PIN is configured yet, mutations are allowed (clinic can still be set up).
    Once a PIN exists, a valid X-Setup-Unlock token is required.
    """
    require_unlocked(
        db,
        user.clinic_id,
        user.user_id,
        x_setup_unlock,
        require_pin_configured=False,
    )
