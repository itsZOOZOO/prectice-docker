from datetime import date
from decimal import Decimal
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app import labs as lab_svc
from app.models import Appointment, Clinic, Client, MoneyReceipt, Task, User
from app.routers.appointments import _enrich_many
from app.schemas import ClinicOut, OkResponse

router = APIRouter(prefix="/desk", tags=["desk"])

IST = ZoneInfo("Asia/Kolkata")


@router.get("/summary", response_model=OkResponse)
def desk_summary(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    from datetime import datetime

    clinic = db.get(Clinic, user.clinic_id)
    today = datetime.now(IST).date()
    start = datetime.combine(today, datetime.min.time(), tzinfo=IST)
    end = datetime.combine(today, datetime.max.time(), tzinfo=IST)

    checked_in = (
        db.query(Client)
        .filter(
            Client.clinic_id == user.clinic_id,
            Client.visible.is_(True),
            Client.check_in_status.is_(True),
        )
        .count()
    )
    clients_total = (
        db.query(Client)
        .filter(Client.clinic_id == user.clinic_id, Client.visible.is_(True))
        .count()
    )
    appts_today = (
        db.query(Appointment)
        .filter(
            Appointment.clinic_id == user.clinic_id,
            Appointment.appointment_date == today,
            Appointment.status.notin_(["Cancelled"]),
        )
        .count()
    )
    receipts = (
        db.query(MoneyReceipt)
        .filter(
            MoneyReceipt.clinic_id == user.clinic_id,
            MoneyReceipt.visible.is_(True),
            MoneyReceipt.received_at >= start,
            MoneyReceipt.received_at <= end,
        )
        .all()
    )
    receipts_total = float(sum((r.amount for r in receipts), Decimal("0")))
    open_tasks = (
        db.query(Task)
        .filter(
            Task.clinic_id == user.clinic_id,
            Task.visible.is_(True),
            Task.status.in_(["Open", "Pending"]),
            Task.due_date == today,
        )
        .count()
    )
    lab_counts = lab_svc.summary_counts(db, user.clinic_id)
    return OkResponse(
        data={
            "clinic": ClinicOut.model_validate(clinic).model_dump() if clinic else None,
            "checked_in": checked_in,
            "clients_total": clients_total,
            "appointments_today": appts_today,
            "receipts_today_total": receipts_total,
            "receipts_today_count": len(receipts),
            "open_tasks": open_tasks,
            "lab_action_needed": lab_counts["action_needed"],
            "today": today.isoformat(),
        }
    )


@router.get("/today", response_model=OkResponse)
def desk_today(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    on: date | None = Query(default=None),
) -> OkResponse:
    from datetime import datetime

    day = on or datetime.now(IST).date()
    rows = (
        db.query(Appointment)
        .filter(
            Appointment.clinic_id == user.clinic_id,
            Appointment.appointment_date == day,
        )
        .order_by(Appointment.appointment_time.asc())
        .all()
    )
    return OkResponse(data={"date": day.isoformat(), "items": _enrich_many(db, rows)})
