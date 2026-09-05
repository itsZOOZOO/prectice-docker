"""WhatsApp Inbox proxy — clinic staff when can_use_inbox (no Setup PIN)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import OkResponse
from app import whatsapp as wa

router = APIRouter(tags=["wa-inbox"])


def _created_by(user: User) -> str:
    name = (getattr(user, "full_name", None) or "").strip()
    if name:
        return name
    return (getattr(user, "username", None) or "receptionist").strip() or "receptionist"


@router.get("/wa-inbox", response_model=OkResponse)
def wa_inbox_get(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    action: str = Query(...),
) -> OkResponse:
    # Forward remaining query params (status, list_id, tag_id, q, id, …)
    query: dict[str, str] = {}
    for key, value in request.query_params.multi_items():
        if key == "action":
            continue
        query[key] = value
    data = wa.proxy_inbox(
        db,
        user.clinic_id,
        method="GET",
        action=action,
        query=query,
    )
    return OkResponse(data=data)


@router.post("/wa-inbox", response_model=OkResponse)
async def wa_inbox_post(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    action: str | None = Query(None),
) -> OkResponse:
    body: dict[str, Any] = {}
    try:
        raw = await request.json()
        if isinstance(raw, dict):
            body = raw
    except Exception:  # noqa: BLE001
        body = {}

    act = (action or body.get("action") or "").strip()
    if "action" in body:
        body = {k: v for k, v in body.items() if k != "action"}

    data = wa.proxy_inbox(
        db,
        user.clinic_id,
        method="POST",
        action=act,
        body=body,
        created_by=_created_by(user),
    )
    return OkResponse(data=data)
