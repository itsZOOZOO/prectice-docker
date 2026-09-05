"""Setup PIN create / unlock / change / TTL for desk settings."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import OkResponse
from app import setup_access as sa

router = APIRouter(prefix="/settings/setup-access", tags=["settings-setup-access"])


class CreatePinIn(BaseModel):
    pin: str = Field(min_length=4, max_length=6)
    confirm_pin: str = Field(min_length=4, max_length=6)


class ChangePinIn(BaseModel):
    current_pin: str = Field(min_length=4, max_length=6)
    new_pin: str = Field(min_length=4, max_length=6)
    confirm_pin: str = Field(min_length=4, max_length=6)


class UnlockIn(BaseModel):
    pin: str = Field(min_length=4, max_length=6)


class TtlUpdate(BaseModel):
    unlock_ttl_minutes: int = Field(ge=15, le=240)


@router.get("", response_model=OkResponse)
def get_status(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    return OkResponse(data=sa.get_status(db, user.clinic_id))


@router.post("/pin", response_model=OkResponse)
def create_pin(
    body: CreatePinIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    sa.create_pin(db, user.clinic_id, body.pin, body.confirm_pin)
    db.commit()
    return OkResponse(data=sa.get_status(db, user.clinic_id))


@router.patch("/pin", response_model=OkResponse)
def change_pin(
    body: ChangePinIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_setup_unlock: Annotated[str | None, Header(alias="X-Setup-Unlock")] = None,
) -> OkResponse:
    sa.change_pin(
        db,
        user.clinic_id,
        user.user_id,
        x_setup_unlock,
        body.current_pin,
        body.new_pin,
        body.confirm_pin,
    )
    db.commit()
    return OkResponse(data={"changed": True})


@router.post("/unlock", response_model=OkResponse)
def unlock(
    body: UnlockIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    result = sa.unlock(db, user.clinic_id, user.user_id, body.pin)
    return OkResponse(data=result)


@router.patch("", response_model=OkResponse)
def patch_ttl(
    body: TtlUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    x_setup_unlock: Annotated[str | None, Header(alias="X-Setup-Unlock")] = None,
) -> OkResponse:
    minutes = sa.set_unlock_ttl_minutes(
        db,
        user.clinic_id,
        user.user_id,
        x_setup_unlock,
        body.unlock_ttl_minutes,
    )
    db.commit()
    return OkResponse(data={"unlock_ttl_minutes": minutes})


@router.post("/lock", response_model=OkResponse)
def lock(
    user: Annotated[User, Depends(get_current_user)],
) -> OkResponse:
    # Client discards the unlock token; nothing to invalidate server-side (HMAC expiry).
    _ = user
    return OkResponse(data={"locked": True})
