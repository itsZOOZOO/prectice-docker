"""Saved client / patient list filters (Desk Wave 3)."""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, exists, func, not_, or_, select
from sqlalchemy.orm import Session

from app.models import (
    Appointment,
    Bill,
    Client,
    ClientTag,
    ClientTagDefinition,
    ClinicClientFilter,
    ClinicClientFilterMember,
    MoneyReceipt,
    Task,
)

VALID_STATUSES = (
    "None",
    "Inquiry",
    "Under Rx",
    "Ortho",
    "Completed",
    "6m followup",
    "Yearly followup",
    "DND",
)

RELATIVE_DAYS = (7, 15, 30, 60, 90)
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def list_client_tags(db: Session, clinic_id: int) -> list[dict[str, Any]]:
    rows = (
        db.query(ClientTagDefinition)
        .filter(ClientTagDefinition.clinic_id == clinic_id)
        .order_by(ClientTagDefinition.tag_name.asc())
        .all()
    )
    return [
        {"client_tag_id": int(r.client_tag_id), "tag_name": r.tag_name}
        for r in rows
    ]


def assigned_tags_for_client(db: Session, clinic_id: int, client_id: int) -> list[dict[str, Any]]:
    rows = (
        db.query(ClientTagDefinition)
        .join(ClientTag, ClientTag.client_tag_id == ClientTagDefinition.client_tag_id)
        .filter(
            ClientTag.client_id == client_id,
            ClientTagDefinition.clinic_id == clinic_id,
        )
        .order_by(ClientTagDefinition.tag_name.asc())
        .all()
    )
    return [
        {"client_tag_id": int(r.client_tag_id), "tag_name": r.tag_name}
        for r in rows
    ]


def set_client_tags(
    db: Session,
    clinic_id: int,
    client_id: int,
    tag_ids: list[int],
) -> list[dict[str, Any]]:
    normalized: list[int] = []
    seen: set[int] = set()
    for raw in tag_ids:
        tid = int(raw)
        if tid > 0 and tid not in seen:
            seen.add(tid)
            normalized.append(tid)

    if normalized:
        valid = {
            int(r.client_tag_id)
            for r in db.query(ClientTagDefinition.client_tag_id)
            .filter(
                ClientTagDefinition.clinic_id == clinic_id,
                ClientTagDefinition.client_tag_id.in_(normalized),
            )
            .all()
        }
        if sorted(valid) != sorted(normalized):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more tags are invalid for this clinic.",
            )

    db.query(ClientTag).filter(ClientTag.client_id == client_id).delete(synchronize_session=False)
    for tid in normalized:
        db.add(ClientTag(client_id=client_id, client_tag_id=tid))
    db.flush()
    return assigned_tags_for_client(db, clinic_id, client_id)


def normalize_money_threshold(raw: Any) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        value = round(float(raw), 2)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Billing thresholds must be numeric.",
        ) from exc
    if value <= 0:
        return None
    return value


def _normalize_status_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for status_val in raw:
        s = str(status_val)
        if s in VALID_STATUSES and s not in out:
            out.append(s)
    return out


def _normalize_tag_list(raw: Any, available_tags: list[str]) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for tag in raw:
        t = str(tag).strip()
        if t and t in available_tags and t not in out:
            out.append(t)
    return out


def normalize_criteria(db: Session, clinic_id: int, raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="criteria object is required.",
        )

    available_tags = [t["tag_name"] for t in list_client_tags(db, clinic_id)]
    status_include = _normalize_status_list(raw.get("status_include"))
    status_exclude = _normalize_status_list(raw.get("status_exclude"))
    tag_include = _normalize_tag_list(raw.get("tag_include"), available_tags)
    tag_exclude = _normalize_tag_list(raw.get("tag_exclude"), available_tags)

    date_raw = raw.get("date") if isinstance(raw.get("date"), dict) else {}
    date_mode = str(date_raw.get("mode") or "any")
    if date_mode not in ("any", "relative", "absolute"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date mode.")

    date_crit: dict[str, Any] = {"mode": date_mode}
    if date_mode == "relative":
        days = int(date_raw.get("relative_days") or 0)
        if days not in RELATIVE_DAYS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="relative_days must be one of 7, 15, 30, 60, 90.",
            )
        date_crit["relative_days"] = days
    elif date_mode == "absolute":
        date_crit["from"] = str(date_raw.get("from") or "").strip()
        date_crit["to"] = str(date_raw.get("to") or "").strip()

    future_appointment = str(raw.get("future_appointment") or "any")
    future_task = str(raw.get("future_task") or "any")
    if future_appointment not in ("any", "has", "none"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid future_appointment value.",
        )
    if future_task not in ("any", "has", "none"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid future_task value.",
        )

    return {
        "status_include": status_include,
        "status_exclude": status_exclude,
        "tag_include": tag_include,
        "tag_exclude": tag_exclude,
        "date": date_crit,
        "future_appointment": future_appointment,
        "future_task": future_task,
        "total_billed_min": normalize_money_threshold(raw.get("total_billed_min")),
        "pending_payment_min": normalize_money_threshold(raw.get("pending_payment_min")),
    }


def _count_members(db: Session, filter_id: int) -> int:
    return (
        db.query(func.count(ClinicClientFilterMember.id))
        .filter(ClinicClientFilterMember.filter_id == filter_id)
        .scalar()
        or 0
    )


def _filter_has_members(db: Session, filter_id: int) -> bool:
    return (
        db.query(ClinicClientFilterMember.id)
        .filter(ClinicClientFilterMember.filter_id == filter_id)
        .limit(1)
        .first()
        is not None
    )


def map_filter_row(db: Session, row: ClinicClientFilter) -> dict[str, Any]:
    criteria = row.criteria_json if isinstance(row.criteria_json, dict) else {}
    return {
        "filter_id": row.filter_id,
        "clinic_id": row.clinic_id,
        "name": row.name,
        "sort_order": int(row.sort_order or 0),
        "show_on_dashboard": bool(row.show_on_dashboard),
        "criteria": criteria,
        "manual_member_count": _count_members(db, row.filter_id),
        "created_at": row.created_at.isoformat() if row.created_at else "",
        "updated_at": row.updated_at.isoformat() if row.updated_at else "",
    }


def list_filters(db: Session, clinic_id: int, *, dashboard_only: bool = False) -> list[dict[str, Any]]:
    q = db.query(ClinicClientFilter).filter(
        ClinicClientFilter.clinic_id == clinic_id,
        ClinicClientFilter.visible.is_(True),
    )
    if dashboard_only:
        q = q.filter(ClinicClientFilter.show_on_dashboard.is_(True))
    rows = q.order_by(ClinicClientFilter.sort_order.asc(), ClinicClientFilter.name.asc()).all()
    return [map_filter_row(db, r) for r in rows]


def get_filter(db: Session, filter_id: int, clinic_id: int) -> ClinicClientFilter | None:
    return (
        db.query(ClinicClientFilter)
        .filter(
            ClinicClientFilter.filter_id == filter_id,
            ClinicClientFilter.clinic_id == clinic_id,
            ClinicClientFilter.visible.is_(True),
        )
        .first()
    )


def assert_filter(db: Session, filter_id: int, clinic_id: int) -> ClinicClientFilter:
    if filter_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filter id.")
    row = get_filter(db, filter_id, clinic_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filter not found.")
    return row


def create_filter(
    db: Session,
    clinic_id: int,
    user_id: int,
    *,
    name: str,
    criteria: Any,
    show_on_dashboard: bool = False,
    sort_order: int = 0,
) -> dict[str, Any]:
    name = (name or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filter name is required.")
    normalized = normalize_criteria(db, clinic_id, criteria if criteria is not None else {})
    row = ClinicClientFilter(
        clinic_id=clinic_id,
        name=name,
        sort_order=int(sort_order or 0),
        show_on_dashboard=bool(show_on_dashboard),
        criteria_json=normalized,
        created_by_user_id=user_id,
        visible=True,
    )
    db.add(row)
    db.flush()
    return map_filter_row(db, row)


def update_filter(db: Session, filter_id: int, clinic_id: int, body: dict[str, Any]) -> dict[str, Any]:
    row = assert_filter(db, filter_id, clinic_id)
    changed = False

    if "name" in body:
        name = str(body.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filter name is required.")
        row.name = name
        changed = True
    if "sort_order" in body:
        row.sort_order = int(body.get("sort_order") or 0)
        changed = True
    if "show_on_dashboard" in body:
        row.show_on_dashboard = bool(body.get("show_on_dashboard"))
        changed = True
    if "criteria" in body:
        row.criteria_json = normalize_criteria(db, clinic_id, body.get("criteria"))
        changed = True

    if not changed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update.")

    db.flush()
    return map_filter_row(db, row)


def delete_filter(db: Session, filter_id: int, clinic_id: int) -> None:
    row = (
        db.query(ClinicClientFilter)
        .filter(
            ClinicClientFilter.filter_id == filter_id,
            ClinicClientFilter.clinic_id == clinic_id,
            ClinicClientFilter.visible.is_(True),
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filter not found.")
    row.visible = False
    db.flush()


def list_members(db: Session, filter_id: int, clinic_id: int) -> list[dict[str, Any]]:
    assert_filter(db, filter_id, clinic_id)
    rows = (
        db.query(Client)
        .join(
            ClinicClientFilterMember,
            ClinicClientFilterMember.client_id == Client.client_id,
        )
        .filter(
            ClinicClientFilterMember.filter_id == filter_id,
            ClinicClientFilterMember.clinic_id == clinic_id,
            Client.visible.is_(True),
        )
        .order_by(Client.name.asc())
        .all()
    )
    return [
        {
            "client_id": c.client_id,
            "name": c.name,
            "number": c.number,
            "place": c.place,
        }
        for c in rows
    ]


def add_member(db: Session, filter_id: int, clinic_id: int, user_id: int, client_id: int) -> None:
    assert_filter(db, filter_id, clinic_id)
    if client_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client id.")
    client = (
        db.query(Client)
        .filter(
            Client.client_id == client_id,
            Client.clinic_id == clinic_id,
            Client.visible.is_(True),
        )
        .first()
    )
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found.")

    existing = (
        db.query(ClinicClientFilterMember)
        .filter(
            ClinicClientFilterMember.filter_id == filter_id,
            ClinicClientFilterMember.client_id == client_id,
        )
        .first()
    )
    if existing:
        return

    db.add(
        ClinicClientFilterMember(
            filter_id=filter_id,
            clinic_id=clinic_id,
            client_id=client_id,
            added_by_user_id=user_id,
        )
    )
    db.flush()


def remove_member(db: Session, filter_id: int, clinic_id: int, client_id: int) -> None:
    assert_filter(db, filter_id, clinic_id)
    if client_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client id.")
    (
        db.query(ClinicClientFilterMember)
        .filter(
            ClinicClientFilterMember.filter_id == filter_id,
            ClinicClientFilterMember.clinic_id == clinic_id,
            ClinicClientFilterMember.client_id == client_id,
        )
        .delete(synchronize_session=False)
    )
    db.flush()


def _pending_bill_statuses() -> tuple:
    return ("pending", "partial", "open")


def _build_criteria_clause(clinic_id: int, criteria: dict[str, Any]) -> Any | None:
    """Return SQLAlchemy boolean clause for criteria, or None if empty."""
    parts: list[Any] = []

    status_include = criteria.get("status_include") or []
    if status_include:
        parts.append(Client.status.in_(list(status_include)))

    status_exclude = criteria.get("status_exclude") or []
    if status_exclude:
        parts.append(Client.status.notin_(list(status_exclude)))

    tag_include = criteria.get("tag_include") or []
    if tag_include:
        parts.append(
            exists(
                select(1)
                .select_from(ClientTag)
                .join(
                    ClientTagDefinition,
                    ClientTag.client_tag_id == ClientTagDefinition.client_tag_id,
                )
                .where(
                    ClientTag.client_id == Client.client_id,
                    ClientTagDefinition.clinic_id == clinic_id,
                    ClientTagDefinition.tag_name.in_(list(tag_include)),
                )
            )
        )

    tag_exclude = criteria.get("tag_exclude") or []
    if tag_exclude:
        parts.append(
            ~exists(
                select(1)
                .select_from(ClientTag)
                .join(
                    ClientTagDefinition,
                    ClientTag.client_tag_id == ClientTagDefinition.client_tag_id,
                )
                .where(
                    ClientTag.client_id == Client.client_id,
                    ClientTagDefinition.clinic_id == clinic_id,
                    ClientTagDefinition.tag_name.in_(list(tag_exclude)),
                )
            )
        )

    date_crit = criteria.get("date") if isinstance(criteria.get("date"), dict) else {}
    date_mode = str(date_crit.get("mode") or "any")
    today = date.today()

    if date_mode == "relative":
        days = int(date_crit.get("relative_days") or 0)
        if days not in RELATIVE_DAYS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid relative_days for date filter.",
            )
        cutoff = today - timedelta(days=days)
        parts.append(func.date(Client.created_at) >= cutoff)
    elif date_mode == "absolute":
        from_s = str(date_crit.get("from") or "").strip()
        to_s = str(date_crit.get("to") or "").strip()
        if not from_s or not to_s:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both from and to dates are required for absolute date filter.",
            )
        if not _DATE_RE.match(from_s) or not _DATE_RE.match(to_s):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD.",
            )
        parts.append(
            and_(
                func.date(Client.created_at) >= date.fromisoformat(from_s),
                func.date(Client.created_at) <= date.fromisoformat(to_s),
            )
        )

    appt_filter = str(criteria.get("future_appointment") or "any")
    if appt_filter in ("has", "none"):
        appt_exists = exists(
            select(Appointment.appointment_id).where(
                Appointment.client_id == Client.client_id,
                Appointment.clinic_id == clinic_id,
                Appointment.appointment_date >= today,
            )
        )
        parts.append(not_(appt_exists) if appt_filter == "none" else appt_exists)

    task_filter = str(criteria.get("future_task") or "any")
    if task_filter in ("has", "none"):
        task_exists = exists(
            select(Task.task_id).where(
                Task.client_id == Client.client_id,
                Task.clinic_id == clinic_id,
                Task.due_date >= today,
                Task.visible.is_(True),
                Task.completed_at.is_(None),
            )
        )
        parts.append(not_(task_exists) if task_filter == "none" else task_exists)

    total_billed_min = normalize_money_threshold(criteria.get("total_billed_min"))
    if total_billed_min is not None:
        billed_subq = (
            select(func.coalesce(func.sum(Bill.amount_due), 0))
            .where(
                Bill.client_id == Client.client_id,
                Bill.clinic_id == clinic_id,
                Bill.visible.is_(True),
                func.lower(Bill.status).in_(_pending_bill_statuses()),
            )
            .correlate(Client)
            .scalar_subquery()
        )
        parts.append(billed_subq >= total_billed_min)

    pending_payment_min = normalize_money_threshold(criteria.get("pending_payment_min"))
    if pending_payment_min is not None:
        paid_subq = (
            select(
                MoneyReceipt.bill_id.label("bill_id"),
                func.coalesce(func.sum(MoneyReceipt.amount), 0).label("paid"),
            )
            .where(MoneyReceipt.visible.is_(True))
            .group_by(MoneyReceipt.bill_id)
            .subquery()
        )
        pending_subq = (
            select(
                func.coalesce(
                    func.sum(
                        func.greatest(
                            Bill.amount_due - func.coalesce(paid_subq.c.paid, 0),
                            0,
                        )
                    ),
                    0,
                )
            )
            .select_from(Bill)
            .outerjoin(paid_subq, paid_subq.c.bill_id == Bill.bill_id)
            .where(
                Bill.client_id == Client.client_id,
                Bill.clinic_id == clinic_id,
                Bill.visible.is_(True),
                func.lower(Bill.status).in_(_pending_bill_statuses()),
            )
            .correlate(Client)
            .scalar_subquery()
        )
        parts.append(pending_subq >= pending_payment_min)

    if not parts:
        return None
    return and_(*parts)


def _matching_client_id_query(
    db: Session,
    clinic_id: int,
    criteria: dict[str, Any],
    *,
    filter_id: int | None = None,
):
    criteria_clause = _build_criteria_clause(clinic_id, criteria)
    member_clause = None
    if filter_id is not None and _filter_has_members(db, filter_id):
        member_clause = exists(
            select(ClinicClientFilterMember.id).where(
                ClinicClientFilterMember.filter_id == filter_id,
                ClinicClientFilterMember.client_id == Client.client_id,
            )
        )

    base = and_(Client.visible.is_(True), Client.clinic_id == clinic_id)

    if criteria_clause is not None and member_clause is not None:
        where = and_(base, or_(criteria_clause, member_clause))
    elif member_clause is not None:
        where = and_(base, member_clause)
    elif criteria_clause is not None:
        where = and_(base, criteria_clause)
    else:
        where = and_(base, False)

    return db.query(Client.client_id).filter(where)


def preview_count(
    db: Session,
    clinic_id: int,
    criteria: Any,
    *,
    filter_id: int | None = None,
) -> int:
    normalized = normalize_criteria(db, clinic_id, criteria if criteria is not None else {})
    q = _matching_client_id_query(db, clinic_id, normalized, filter_id=filter_id)
    return q.distinct().count()


def client_ids_for_filter(db: Session, clinic_id: int, filter_id: int) -> list[int]:
    row = assert_filter(db, filter_id, clinic_id)
    criteria = row.criteria_json if isinstance(row.criteria_json, dict) else {}
    normalized = normalize_criteria(db, clinic_id, criteria)
    rows = _matching_client_id_query(db, clinic_id, normalized, filter_id=filter_id).distinct().all()
    return [int(r[0]) for r in rows]


def list_clients_for_filter(
    db: Session,
    clinic_id: int,
    filter_id: int,
    *,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[int, list[Client]]:
    row = assert_filter(db, filter_id, clinic_id)
    criteria = row.criteria_json if isinstance(row.criteria_json, dict) else {}
    normalized = normalize_criteria(db, clinic_id, criteria)

    id_subq = (
        _matching_client_id_query(db, clinic_id, normalized, filter_id=filter_id)
        .distinct()
        .subquery()
    )
    query = db.query(Client).filter(Client.client_id.in_(select(id_subq.c.client_id)))

    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Client.name.ilike(like),
                Client.number.ilike(like),
                Client.place.ilike(like),
                Client.calling_name.ilike(like),
            )
        )

    total = query.count()
    rows = query.order_by(Client.created_at.desc()).offset(offset).limit(limit).all()
    return total, rows
