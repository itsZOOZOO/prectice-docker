"""Dental lab case domain helpers (parity with legacy DentalLabQueries/Actions)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import Date, Time, and_, cast, exists, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app import media as media_svc
from app.models import Appointment, Client, DentalLab, LabCase, LabCaseCycle, User

IST = ZoneInfo("Asia/Kolkata")

VALID_FILTERS = {
    "action_needed",
    "blocked_on_clinic",
    "at_lab",
    "at_lab_overdue",
    "received_no_future_appointment",
    "open",
    "closed",
    "cancelled",
}

CASE_TYPE_CHIPS = ("Crown & Bridge", "Denture", "Implant prosthesis")


def today_ist() -> date:
    return datetime.now(IST).date()


def now_ist() -> datetime:
    return datetime.now(IST)


def _nullable_trim(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def derive_stage(cycle: LabCaseCycle | None) -> str:
    if cycle is None:
        return "send_pending"
    if cycle.received_at:
        return "received"
    if cycle.sent_at:
        return "at_lab"
    return "send_pending"


def days_overdue(expected: date | None, cycle: LabCaseCycle | None, today: date) -> int | None:
    if not cycle or not cycle.sent_at or cycle.received_at or not expected:
        return None
    if expected >= today:
        return None
    return (today - expected).days


def derive_action_category(
    case_status: str,
    cycle: LabCaseCycle | None,
    has_future_appt: bool,
    today: date,
) -> str | None:
    if case_status != "open" or cycle is None:
        return None
    expected = cycle.expected_return_date
    sent = bool(cycle.sent_at)
    received = bool(cycle.received_at)
    send_pending = bool(cycle.send_pending_at)

    if sent and not received and expected is None:
        return "at_lab_missing_due"
    if sent and not received and expected is not None and expected < today:
        return "at_lab_overdue"
    if send_pending and not sent:
        return "blocked_on_clinic"
    if received and not has_future_appt:
        return "received_no_future_appointment"
    if sent and not received:
        return "at_lab"
    return None


def add_clinic_working_days(start: date, working_days: int) -> date:
    """Mon–Sat open, Sunday closed (default until clinic hours exist)."""
    if working_days <= 0:
        return start
    cursor = start
    counted = 0
    while counted < working_days:
        cursor = cursor + timedelta(days=1)
        if cursor.weekday() != 6:  # Sunday
            counted += 1
    return cursor


def expected_return_from_offset(offset_days: int, from_date: date | None = None) -> date:
    start = from_date or today_ist()
    return add_clinic_working_days(start, offset_days)


def _as_ist(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=IST)
    return dt.astimezone(IST)


def _appointment_after_received_clause(received_at_col):
    """Appointments strictly after lab receive time (IST date/time)."""
    recv_local = func.timezone("Asia/Kolkata", received_at_col)
    recv_date = cast(recv_local, Date)
    recv_time = cast(recv_local, Time)
    return or_(
        Appointment.appointment_date > recv_date,
        and_(
            Appointment.appointment_date == recv_date,
            Appointment.appointment_time > recv_time,
        ),
    )


def _future_appt_exists(
    db: Session,
    clinic_id: int,
    client_id: int,
    today: date,
    *,
    after: datetime | None = None,
) -> bool:
    """True if client has a non-cancelled appointment still upcoming and after receive time."""
    q = db.query(Appointment.appointment_id).filter(
        Appointment.clinic_id == clinic_id,
        Appointment.client_id == client_id,
        Appointment.appointment_date >= today,
        Appointment.status.notin_(["Cancelled"]),
    )
    if after is not None:
        after_ist = _as_ist(after)
        after_d = after_ist.date()
        after_t = after_ist.time().replace(microsecond=0)
        q = q.filter(
            or_(
                Appointment.appointment_date > after_d,
                and_(
                    Appointment.appointment_date == after_d,
                    Appointment.appointment_time > after_t,
                ),
            )
        )
    return q.first() is not None


def _received_needs_appointment_exists(clinic_id: int, today: date):
    """EXISTS: appointment on/after today AND after this cycle's received_at."""
    return exists(
        select(Appointment.appointment_id).where(
            Appointment.client_id == LabCase.client_id,
            Appointment.clinic_id == clinic_id,
            Appointment.appointment_date >= today,
            Appointment.status.notin_(["Cancelled"]),
            _appointment_after_received_clause(LabCaseCycle.received_at),
        )
    )


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return dt.isoformat()


def _active_cycle(case: LabCase) -> LabCaseCycle | None:
    for c in case.cycles or []:
        if c.cycle_number == case.current_cycle_number:
            return c
    return None


def serialize_lab(lab: DentalLab) -> dict:
    return {
        "lab_id": lab.lab_id,
        "name": lab.name,
        "contact_person": lab.contact_person,
        "phone": lab.phone,
        "notes": lab.notes,
        "created_at": _iso(lab.created_at) or "",
        "updated_at": _iso(lab.updated_at),
    }


def serialize_case(
    db: Session,
    case: LabCase,
    *,
    client_name: str,
    lab_name: str,
    profile_key: str | None,
    cycle: LabCaseCycle | None,
    has_future_appt: bool,
    today: date,
    include_cycles: bool = False,
) -> dict:
    stage = derive_stage(cycle)
    expected = cycle.expected_return_date if cycle else None
    photo = media_svc.resolve_media_key(profile_key) if profile_key else None
    data = {
        "case_id": case.case_id,
        "case_ref": case.case_ref,
        "client_id": case.client_id,
        "client_name": client_name,
        "profile_photo_url": photo,
        "lab_id": case.lab_id,
        "lab_name": lab_name,
        "case_type": case.case_type,
        "tooth_numbers": case.tooth_numbers,
        "description": case.description,
        "status": case.status,
        "current_cycle_number": case.current_cycle_number,
        "stage": stage,
        "action_category": derive_action_category(case.status, cycle, has_future_appt, today),
        "expected_return_date": expected.isoformat() if expected else None,
        "days_overdue": days_overdue(expected, cycle, today),
        "send_pending_at": _iso(cycle.send_pending_at) if cycle else None,
        "sent_at": _iso(cycle.sent_at) if cycle else None,
        "received_at": _iso(cycle.received_at) if cycle else None,
        "has_future_appointment": has_future_appt,
        "created_at": _iso(case.created_at) or "",
    }
    if include_cycles:
        data["cycles"] = [
            {
                "cycle_id": c.cycle_id,
                "cycle_number": c.cycle_number,
                "stage": derive_stage(c),
                "send_pending_at": _iso(c.send_pending_at),
                "sent_at": _iso(c.sent_at),
                "received_at": _iso(c.received_at),
                "expected_return_date": c.expected_return_date.isoformat() if c.expected_return_date else None,
                "notes": c.notes,
                "created_at": _iso(c.created_at) or "",
            }
            for c in sorted(case.cycles or [], key=lambda x: x.cycle_number)
        ]
    return data


def get_lab_or_404(db: Session, lab_id: int, clinic_id: int) -> DentalLab:
    lab = (
        db.query(DentalLab)
        .filter(DentalLab.lab_id == lab_id, DentalLab.clinic_id == clinic_id, DentalLab.visible.is_(True))
        .first()
    )
    if not lab:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab not found")
    return lab


def get_client_or_404(db: Session, client_id: int, clinic_id: int) -> Client:
    client = (
        db.query(Client)
        .filter(Client.client_id == client_id, Client.clinic_id == clinic_id, Client.visible.is_(True))
        .first()
    )
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


def get_case_or_404(db: Session, case_id: int, clinic_id: int) -> LabCase:
    case = (
        db.query(LabCase)
        .options(joinedload(LabCase.cycles), joinedload(LabCase.lab))
        .filter(LabCase.case_id == case_id, LabCase.clinic_id == clinic_id, LabCase.visible.is_(True))
        .first()
    )
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return case


def _case_query(db: Session, clinic_id: int):
    return (
        db.query(LabCase, Client, DentalLab, LabCaseCycle)
        .join(Client, and_(Client.client_id == LabCase.client_id, Client.visible.is_(True)))
        .join(DentalLab, and_(DentalLab.lab_id == LabCase.lab_id, DentalLab.visible.is_(True)))
        .join(
            LabCaseCycle,
            and_(
                LabCaseCycle.case_id == LabCase.case_id,
                LabCaseCycle.cycle_number == LabCase.current_cycle_number,
            ),
        )
        .filter(LabCase.clinic_id == clinic_id, LabCase.visible.is_(True))
    )


def _apply_filter(query, filter_name: str, clinic_id: int, today: date):
    future_appt = _received_needs_appointment_exists(clinic_id, today)
    if filter_name == "blocked_on_clinic":
        return query.filter(
            LabCase.status == "open",
            LabCaseCycle.send_pending_at.isnot(None),
            LabCaseCycle.sent_at.is_(None),
        )
    if filter_name == "at_lab":
        return query.filter(
            LabCase.status == "open",
            LabCaseCycle.sent_at.isnot(None),
            LabCaseCycle.received_at.is_(None),
        )
    if filter_name == "at_lab_overdue":
        # Past due OR missing expected return (both need clinic attention).
        return query.filter(
            LabCase.status == "open",
            LabCaseCycle.sent_at.isnot(None),
            LabCaseCycle.received_at.is_(None),
            or_(
                LabCaseCycle.expected_return_date.is_(None),
                LabCaseCycle.expected_return_date < today,
            ),
        )
    if filter_name == "received_no_future_appointment":
        return query.filter(
            LabCase.status == "open",
            LabCaseCycle.received_at.isnot(None),
            ~future_appt,
        )
    if filter_name == "open":
        return query.filter(LabCase.status == "open")
    if filter_name == "closed":
        return query.filter(LabCase.status == "closed")
    if filter_name == "cancelled":
        return query.filter(LabCase.status == "cancelled")
    # action_needed
    return query.filter(
        or_(
            and_(
                LabCase.status == "open",
                LabCaseCycle.send_pending_at.isnot(None),
                LabCaseCycle.sent_at.is_(None),
            ),
            and_(
                LabCase.status == "open",
                LabCaseCycle.sent_at.isnot(None),
                LabCaseCycle.received_at.is_(None),
                or_(
                    LabCaseCycle.expected_return_date.is_(None),
                    LabCaseCycle.expected_return_date < today,
                ),
            ),
            and_(
                LabCase.status == "open",
                LabCaseCycle.received_at.isnot(None),
                ~future_appt,
            ),
        )
    )


def list_cases(db: Session, clinic_id: int, filter_name: str = "action_needed") -> list[dict]:
    filt = filter_name if filter_name in VALID_FILTERS else "action_needed"
    today = today_ist()
    q = _apply_filter(_case_query(db, clinic_id), filt, clinic_id, today)
    rows = q.order_by(LabCase.case_id.desc()).limit(500).all()
    items: list[dict] = []
    for case, client, lab, cycle in rows:
        has_future = _future_appt_exists(
            db,
            clinic_id,
            case.client_id,
            today,
            after=cycle.received_at if cycle else None,
        )
        items.append(
            serialize_case(
                db,
                case,
                client_name=client.name,
                lab_name=lab.name,
                profile_key=(client.profile_photo_url or "").strip() or None,
                cycle=cycle,
                has_future_appt=has_future,
                today=today,
            )
        )
    return items


def list_cases_for_client(db: Session, clinic_id: int, client_id: int) -> list[dict]:
    get_client_or_404(db, client_id, clinic_id)
    today = today_ist()
    rows = (
        _case_query(db, clinic_id)
        .filter(LabCase.client_id == client_id)
        .order_by(LabCase.case_id.desc())
        .all()
    )
    items: list[dict] = []
    for case, client, lab, cycle in rows:
        has_future = _future_appt_exists(
            db,
            clinic_id,
            case.client_id,
            today,
            after=cycle.received_at if cycle else None,
        )
        items.append(
            serialize_case(
                db,
                case,
                client_name=client.name,
                lab_name=lab.name,
                profile_key=(client.profile_photo_url or "").strip() or None,
                cycle=cycle,
                has_future_appt=has_future,
                today=today,
            )
        )
    return items


def get_case_detail(db: Session, case_id: int, clinic_id: int) -> dict:
    case = get_case_or_404(db, case_id, clinic_id)
    client = get_client_or_404(db, case.client_id, clinic_id)
    lab = get_lab_or_404(db, case.lab_id, clinic_id)
    today = today_ist()
    cycle = _active_cycle(case)
    has_future = _future_appt_exists(
        db,
        clinic_id,
        case.client_id,
        today,
        after=cycle.received_at if cycle else None,
    )
    return serialize_case(
        db,
        case,
        client_name=client.name,
        lab_name=lab.name,
        profile_key=(client.profile_photo_url or "").strip() or None,
        cycle=cycle,
        has_future_appt=has_future,
        today=today,
        include_cycles=True,
    )


def summary_counts(db: Session, clinic_id: int) -> dict:
    today = today_ist()
    future_appt = _received_needs_appointment_exists(clinic_id, today)
    base = (
        db.query(LabCase, LabCaseCycle)
        .join(
            LabCaseCycle,
            and_(
                LabCaseCycle.case_id == LabCase.case_id,
                LabCaseCycle.cycle_number == LabCase.current_cycle_number,
            ),
        )
        .filter(LabCase.clinic_id == clinic_id, LabCase.visible.is_(True))
    )
    blocked = (
        base.filter(
            LabCase.status == "open",
            LabCaseCycle.send_pending_at.isnot(None),
            LabCaseCycle.sent_at.is_(None),
        ).count()
    )
    at_lab = (
        base.filter(
            LabCase.status == "open",
            LabCaseCycle.sent_at.isnot(None),
            LabCaseCycle.received_at.is_(None),
        ).count()
    )
    overdue = (
        base.filter(
            LabCase.status == "open",
            LabCaseCycle.sent_at.isnot(None),
            LabCaseCycle.received_at.is_(None),
            or_(
                LabCaseCycle.expected_return_date.is_(None),
                LabCaseCycle.expected_return_date < today,
            ),
        ).count()
    )
    needs_appt = (
        base.filter(
            LabCase.status == "open",
            LabCaseCycle.received_at.isnot(None),
            ~future_appt,
        ).count()
    )
    open_count = base.filter(LabCase.status == "open").count()
    return {
        "action_needed": blocked + overdue + needs_appt,
        "blocked_on_clinic": blocked,
        "at_lab": at_lab,
        "at_lab_overdue": overdue,
        "received_no_future_appointment": needs_appt,
        "open": open_count,
    }


def next_case_ref(db: Session, clinic_id: int, year: str) -> str:
    prefix = f"LAB-{year}-"
    like = f"{prefix}%"
    rows = (
        db.query(LabCase.case_ref)
        .filter(LabCase.clinic_id == clinic_id, LabCase.case_ref.like(like))
        .with_for_update()
        .all()
    )
    max_seq = 0
    for (ref,) in rows:
        try:
            max_seq = max(max_seq, int(str(ref).rsplit("-", 1)[-1]))
        except ValueError:
            continue
    return f"{prefix}{max_seq + 1:04d}"


def create_lab(
    db: Session,
    user: User,
    *,
    name: str,
    contact_person: str | None,
    phone: str | None,
    notes: str | None,
) -> DentalLab:
    name = name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lab name is required")
    lab = DentalLab(
        clinic_id=user.clinic_id,
        name=name,
        contact_person=_nullable_trim(contact_person),
        phone=_nullable_trim(phone),
        notes=_nullable_trim(notes),
        visible=True,
        created_by=user.user_id,
        created_at=now_ist(),
    )
    db.add(lab)
    db.commit()
    db.refresh(lab)
    return lab


def update_lab(
    db: Session,
    user: User,
    lab_id: int,
    *,
    name: str,
    contact_person: str | None,
    phone: str | None,
    notes: str | None,
) -> DentalLab:
    lab = get_lab_or_404(db, lab_id, user.clinic_id)
    name = name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lab name is required")
    lab.name = name
    lab.contact_person = _nullable_trim(contact_person)
    lab.phone = _nullable_trim(phone)
    lab.notes = _nullable_trim(notes)
    lab.updated_at = now_ist()
    db.commit()
    db.refresh(lab)
    return lab


def archive_lab(db: Session, user: User, lab_id: int) -> dict:
    lab = get_lab_or_404(db, lab_id, user.clinic_id)
    open_count = (
        db.query(LabCase)
        .filter(
            LabCase.lab_id == lab_id,
            LabCase.clinic_id == user.clinic_id,
            LabCase.status == "open",
            LabCase.visible.is_(True),
        )
        .count()
    )
    if open_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot archive a lab with open cases",
        )
    lab.visible = False
    lab.updated_at = now_ist()
    db.commit()
    return {"lab_id": lab_id, "archived": True}


def create_case(
    db: Session,
    user: User,
    *,
    client_id: int,
    lab_id: int,
    case_type: str,
    tooth_numbers: str | None,
    description: str | None,
) -> dict:
    get_client_or_404(db, client_id, user.clinic_id)
    get_lab_or_404(db, lab_id, user.clinic_id)
    case_type = case_type.strip()
    if not case_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Case type is required")

    year = now_ist().strftime("%Y")
    case_ref = next_case_ref(db, user.clinic_id, year)
    now = now_ist()
    case = LabCase(
        clinic_id=user.clinic_id,
        client_id=client_id,
        lab_id=lab_id,
        case_ref=case_ref,
        case_type=case_type,
        tooth_numbers=_nullable_trim(tooth_numbers),
        description=_nullable_trim(description),
        current_cycle_number=1,
        status="open",
        created_by=user.user_id,
        visible=True,
        created_at=now,
    )
    db.add(case)
    db.flush()
    db.add(
        LabCaseCycle(
            case_id=case.case_id,
            cycle_number=1,
            send_pending_at=now,
            send_pending_by=user.user_id,
            created_at=now,
        )
    )
    db.commit()
    return {"case_id": case.case_id, "case_ref": case_ref}


def update_case(
    db: Session,
    user: User,
    case_id: int,
    *,
    case_type: str | None,
    tooth_numbers: str | None,
    description: str | None,
    expected_return_date: str | None,
) -> dict:
    case = get_case_or_404(db, case_id, user.clinic_id)
    if case.status != "open":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only open cases can be edited")
    now = now_ist()
    if case_type is not None:
        ct = case_type.strip()
        if not ct:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Case type cannot be empty")
        case.case_type = ct
    if tooth_numbers is not None:
        case.tooth_numbers = _nullable_trim(tooth_numbers)
    if description is not None:
        case.description = _nullable_trim(description)
    case.updated_at = now

    if expected_return_date is not None:
        cycle = _active_cycle(case)
        if cycle:
            raw = expected_return_date.strip()
            if raw == "":
                cycle.expected_return_date = None
            else:
                try:
                    cycle.expected_return_date = date.fromisoformat(raw)
                except ValueError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid expected return date",
                    ) from exc
            cycle.updated_at = now

    db.commit()
    return get_case_detail(db, case_id, user.clinic_id)


def set_stage(
    db: Session,
    user: User,
    case_id: int,
    cycle_number: int,
    *,
    stage: str,
    action: str,
    expected_return_date: str | None,
) -> dict:
    case = get_case_or_404(db, case_id, user.clinic_id)
    if case.status != "open":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Case is not open")
    if cycle_number != case.current_cycle_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stage changes are only allowed on the active cycle",
        )
    stage = stage.strip().lower()
    action = action.strip().lower()
    if stage not in {"send_pending", "sent", "received"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid stage")
    if action not in {"set", "clear"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action")

    cycle = _active_cycle(case)
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found")
    now = now_ist()

    if action == "set":
        if stage == "sent":
            if not cycle.send_pending_at or cycle.sent_at:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Case cannot be marked sent")
            if not expected_return_date or not expected_return_date.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Expected return date is required when marking sent",
                )
            try:
                return_date = date.fromisoformat(expected_return_date.strip())
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid expected return date",
                ) from exc
            cycle.sent_at = now
            cycle.sent_by = user.user_id
            cycle.receive_pending_at = now
            cycle.receive_pending_by = user.user_id
            cycle.expected_return_date = return_date
            cycle.updated_at = now
        elif stage == "received":
            if not cycle.sent_at or cycle.received_at:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Case cannot be marked received",
                )
            cycle.received_at = now
            cycle.received_by = user.user_id
            cycle.updated_at = now
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot set send_pending directly",
            )
    else:
        if stage == "received":
            if not cycle.received_at:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nothing to undo")
            cycle.received_at = None
            cycle.received_by = None
            cycle.updated_at = now
        elif stage == "sent":
            if not cycle.sent_at:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nothing to undo")
            cycle.sent_at = None
            cycle.sent_by = None
            cycle.receive_pending_at = None
            cycle.receive_pending_by = None
            cycle.updated_at = now
        else:
            if not cycle.send_pending_at or cycle.sent_at:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nothing to undo")
            cycle.send_pending_at = None
            cycle.send_pending_by = None
            cycle.updated_at = now

    case.updated_at = now
    db.commit()
    return get_case_detail(db, case_id, user.clinic_id)


def close_case(db: Session, user: User, case_id: int) -> dict:
    case = get_case_or_404(db, case_id, user.clinic_id)
    if case.status != "open":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Case is not open")
    now = now_ist()
    case.status = "closed"
    case.closed_at = now
    case.closed_by = user.user_id
    case.updated_at = now
    db.commit()
    return get_case_detail(db, case_id, user.clinic_id)


def cancel_case(db: Session, user: User, case_id: int) -> dict:
    case = get_case_or_404(db, case_id, user.clinic_id)
    if case.status != "open":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Case is not open")
    case.status = "cancelled"
    case.updated_at = now_ist()
    db.commit()
    return get_case_detail(db, case_id, user.clinic_id)


def add_cycle(db: Session, user: User, case_id: int) -> dict:
    case = get_case_or_404(db, case_id, user.clinic_id)
    if case.status != "open":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Case is not open")
    active = _active_cycle(case)
    if not active or not active.received_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rework requires the current cycle to be received first",
        )
    now = now_ist()
    next_n = case.current_cycle_number + 1
    case.current_cycle_number = next_n
    case.updated_at = now
    db.add(
        LabCaseCycle(
            case_id=case.case_id,
            cycle_number=next_n,
            send_pending_at=now,
            send_pending_by=user.user_id,
            created_at=now,
        )
    )
    db.commit()
    return get_case_detail(db, case_id, user.clinic_id)
