"""Append-only clinic activity events (staff actors only)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models import ActivityEvent

logger = logging.getLogger(__name__)

CLIENT_CREATED = "client.created"
APPOINTMENT_BOOKED = "appointment.booked"
APPOINTMENT_STATUS_CHANGED = "appointment.status_changed"

KNOWN_TYPES = {
    CLIENT_CREATED,
    APPOINTMENT_BOOKED,
    APPOINTMENT_STATUS_CHANGED,
}


def record(
    db: Session,
    *,
    clinic_id: int,
    actor_user_id: int | None,
    event_type: str,
    entity_type: str,
    entity_id: int,
    client_id: int | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    if clinic_id <= 0 or entity_id <= 0 or not event_type or not entity_type:
        return
    if actor_user_id is None or actor_user_id <= 0:
        return
    try:
        db.add(
            ActivityEvent(
                clinic_id=clinic_id,
                actor_user_id=actor_user_id,
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                client_id=client_id,
                payload=payload or None,
            )
        )
        db.commit()
    except Exception:
        logger.exception("ActivityLog.record failed")
        db.rollback()


def client_created(
    db: Session,
    *,
    clinic_id: int,
    actor_user_id: int,
    client_id: int,
    payload: dict[str, Any] | None = None,
) -> None:
    record(
        db,
        clinic_id=clinic_id,
        actor_user_id=actor_user_id,
        event_type=CLIENT_CREATED,
        entity_type="client",
        entity_id=client_id,
        client_id=client_id,
        payload=payload,
    )


def appointment_booked(
    db: Session,
    *,
    clinic_id: int,
    actor_user_id: int,
    appointment_id: int,
    client_id: int | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    record(
        db,
        clinic_id=clinic_id,
        actor_user_id=actor_user_id,
        event_type=APPOINTMENT_BOOKED,
        entity_type="appointment",
        entity_id=appointment_id,
        client_id=client_id,
        payload=payload,
    )


def appointment_status_changed(
    db: Session,
    *,
    clinic_id: int,
    actor_user_id: int,
    appointment_id: int,
    client_id: int | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    record(
        db,
        clinic_id=clinic_id,
        actor_user_id=actor_user_id,
        event_type=APPOINTMENT_STATUS_CHANGED,
        entity_type="appointment",
        entity_id=appointment_id,
        client_id=client_id,
        payload=payload,
    )
