"""Clinic activity feed — recent staff actions."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.activity_log import KNOWN_TYPES
from app.auth import get_current_user
from app.db import get_db
from app.models import ActivityEvent, Client, User
from app.schemas import OkResponse

router = APIRouter(prefix="/activity", tags=["activity"])

PAGE_DEFAULT = 30
PAGE_MAX = 100


def _serialize(row: ActivityEvent, actor_name: str | None, client_name: str | None) -> dict[str, Any]:
    return {
        "id": row.id,
        "event_type": row.event_type,
        "entity_type": row.entity_type,
        "entity_id": row.entity_id,
        "client_id": row.client_id,
        "payload": row.payload,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "actor_name": actor_name,
        "client_name": client_name,
    }


@router.get("", response_model=OkResponse)
def list_activity(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=PAGE_DEFAULT, ge=1, le=PAGE_MAX),
    before_id: int | None = Query(default=None, ge=1),
    type: str = Query(default=""),
) -> OkResponse:
    event_type = type.strip() if type.strip() in KNOWN_TYPES else ""

    q = db.query(ActivityEvent).filter(ActivityEvent.clinic_id == user.clinic_id)
    if before_id:
        q = q.filter(ActivityEvent.id < before_id)
    if event_type:
        q = q.filter(ActivityEvent.event_type == event_type)

    rows = q.order_by(ActivityEvent.id.desc()).limit(limit).all()

    actor_ids = {r.actor_user_id for r in rows}
    client_ids = {r.client_id for r in rows if r.client_id}

    actors: dict[int, str] = {}
    if actor_ids:
        for u in db.query(User.user_id, User.full_name).filter(User.user_id.in_(actor_ids)).all():
            actors[u.user_id] = (u.full_name or "").strip() or "Staff"

    clients: dict[int, str] = {}
    if client_ids:
        for c in (
            db.query(Client.client_id, Client.name)
            .filter(Client.clinic_id == user.clinic_id, Client.client_id.in_(client_ids))
            .all()
        ):
            clients[c.client_id] = c.name

    events = [
        _serialize(
            r,
            actors.get(r.actor_user_id),
            clients.get(r.client_id) if r.client_id else None,
        )
        for r in rows
    ]
    next_before = events[-1]["id"] if events else None

    return OkResponse(
        data={
            "events": events,
            "has_more": len(events) == limit,
            "next_before_id": next_before,
        }
    )
