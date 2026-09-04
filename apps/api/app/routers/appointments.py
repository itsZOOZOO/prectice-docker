from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import (
    Appointment,
    AppointmentDoctor,
    AppointmentService,
    AppointmentStatus,
    Client,
    DoctorSchedule,
    User,
)
from app.schemas import (
    AppointmentCreate,
    AppointmentOut,
    AppointmentStatusUpdate,
    DoctorOut,
    OkResponse,
    ServiceOut,
    StatusOut,
)

router = APIRouter(prefix="/appointments", tags=["appointments"])

IST = ZoneInfo("Asia/Kolkata")
CANCELLED_STATUSES = {"Cancelled", "No Show"}


def _add_minutes(t: time, minutes: int) -> time:
    base = datetime.combine(date.today(), t) + timedelta(minutes=minutes)
    return base.time()


def _overlaps(a_start: time, a_end: time, b_start: time, b_end: time) -> bool:
    return a_start < b_end and b_start < a_end


def _serialize(appt: Appointment, doctor_name: str | None = None, service_name: str | None = None) -> dict:
    data = AppointmentOut.model_validate(appt).model_dump()
    data["doctor_name"] = doctor_name
    data["service_name"] = service_name
    data["appointment_time"] = appt.appointment_time.strftime("%H:%M")
    data["end_time"] = appt.end_time.strftime("%H:%M") if appt.end_time else None
    data["appointment_date"] = appt.appointment_date.isoformat()
    return data


def _enrich_many(db: Session, rows: list[Appointment]) -> list[dict]:
    doctor_ids = {r.doctor_id for r in rows}
    service_ids = {r.service_id for r in rows if r.service_id}
    doctors = {
        d.doctor_id: d.doctor_name
        for d in db.query(AppointmentDoctor).filter(AppointmentDoctor.doctor_id.in_(doctor_ids)).all()
    } if doctor_ids else {}
    services = {
        s.service_id: s.service_name
        for s in db.query(AppointmentService).filter(AppointmentService.service_id.in_(service_ids)).all()
    } if service_ids else {}
    return [_serialize(r, doctors.get(r.doctor_id), services.get(r.service_id) if r.service_id else None) for r in rows]


@router.get("/meta", response_model=OkResponse)
def appointment_meta(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    doctors = (
        db.query(AppointmentDoctor)
        .filter(AppointmentDoctor.clinic_id == user.clinic_id, AppointmentDoctor.is_active.is_(True))
        .order_by(AppointmentDoctor.doctor_name)
        .all()
    )
    services = (
        db.query(AppointmentService)
        .filter(AppointmentService.clinic_id == user.clinic_id, AppointmentService.is_active.is_(True))
        .order_by(AppointmentService.service_name)
        .all()
    )
    statuses = (
        db.query(AppointmentStatus)
        .filter(AppointmentStatus.clinic_id == user.clinic_id, AppointmentStatus.is_active.is_(True))
        .order_by(AppointmentStatus.status_id)
        .all()
    )
    return OkResponse(
        data={
            "doctors": [DoctorOut.model_validate(d).model_dump() for d in doctors],
            "services": [ServiceOut.model_validate(s).model_dump() for s in services],
            "statuses": [StatusOut.model_validate(s).model_dump() for s in statuses],
        }
    )


@router.get("", response_model=OkResponse)
def list_appointments(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    on: date | None = Query(default=None, description="Day to load (YYYY-MM-DD)"),
    doctor_id: int | None = None,
    client_id: int | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> OkResponse:
    query = db.query(Appointment).filter(Appointment.clinic_id == user.clinic_id)
    if doctor_id:
        query = query.filter(Appointment.doctor_id == doctor_id)

    if client_id is not None:
        rows = (
            query.filter(Appointment.client_id == client_id)
            .order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc())
            .limit(limit)
            .all()
        )
        return OkResponse(data={"date": None, "items": _enrich_many(db, rows)})

    day = on or datetime.now(IST).date()
    rows = (
        query.filter(Appointment.appointment_date == day)
        .order_by(Appointment.appointment_time.asc())
        .all()
    )
    return OkResponse(data={"date": day.isoformat(), "items": _enrich_many(db, rows)})


@router.get("/slots", response_model=OkResponse)
def list_slots(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    on: date = Query(...),
    doctor_id: int = Query(...),
    service_id: int | None = None,
) -> OkResponse:
    doctor = (
        db.query(AppointmentDoctor)
        .filter(
            AppointmentDoctor.doctor_id == doctor_id,
            AppointmentDoctor.clinic_id == user.clinic_id,
            AppointmentDoctor.is_active.is_(True),
        )
        .first()
    )
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    duration = 30
    if service_id:
        service = (
            db.query(AppointmentService)
            .filter(
                AppointmentService.service_id == service_id,
                AppointmentService.clinic_id == user.clinic_id,
                AppointmentService.is_active.is_(True),
            )
            .first()
        )
        if not service:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
        duration = service.duration_minutes

    weekday = on.weekday()  # Mon=0
    schedule = (
        db.query(DoctorSchedule)
        .filter(
            DoctorSchedule.doctor_id == doctor_id,
            DoctorSchedule.clinic_id == user.clinic_id,
            DoctorSchedule.weekday == weekday,
            DoctorSchedule.is_working.is_(True),
        )
        .first()
    )
    if not schedule:
        return OkResponse(data={"date": on.isoformat(), "duration_minutes": duration, "slots": []})

    existing = (
        db.query(Appointment)
        .filter(
            Appointment.clinic_id == user.clinic_id,
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == on,
            Appointment.status.notin_(list(CANCELLED_STATUSES)),
        )
        .all()
    )

    slots: list[str] = []
    cursor = datetime.combine(on, schedule.start_time)
    end_bound = datetime.combine(on, schedule.end_time)
    step = timedelta(minutes=duration)

    while cursor + step <= end_bound:
        start_t = cursor.time()
        end_t = (cursor + step).time()
        conflict = False
        for appt in existing:
            appt_end = appt.end_time or _add_minutes(appt.appointment_time, duration)
            if _overlaps(start_t, end_t, appt.appointment_time, appt_end):
                conflict = True
                break
        if not conflict:
            slots.append(start_t.strftime("%H:%M"))
        cursor += step

    return OkResponse(data={"date": on.isoformat(), "duration_minutes": duration, "slots": slots})


@router.post("", response_model=OkResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    body: AppointmentCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    doctor = (
        db.query(AppointmentDoctor)
        .filter(
            AppointmentDoctor.doctor_id == body.doctor_id,
            AppointmentDoctor.clinic_id == user.clinic_id,
            AppointmentDoctor.is_active.is_(True),
        )
        .first()
    )
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    duration = 30
    service_name = None
    if body.service_id:
        service = (
            db.query(AppointmentService)
            .filter(
                AppointmentService.service_id == body.service_id,
                AppointmentService.clinic_id == user.clinic_id,
                AppointmentService.is_active.is_(True),
            )
            .first()
        )
        if not service:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
        duration = service.duration_minutes
        service_name = service.service_name

    client = None
    if body.client_id:
        client = (
            db.query(Client)
            .filter(
                Client.client_id == body.client_id,
                Client.clinic_id == user.clinic_id,
                Client.visible.is_(True),
            )
            .first()
        )
        if not client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    end_t = _add_minutes(body.appointment_time, duration)
    existing = (
        db.query(Appointment)
        .filter(
            Appointment.clinic_id == user.clinic_id,
            Appointment.doctor_id == body.doctor_id,
            Appointment.appointment_date == body.appointment_date,
            Appointment.status.notin_(list(CANCELLED_STATUSES)),
        )
        .all()
    )
    for appt in existing:
        appt_end = appt.end_time or _add_minutes(appt.appointment_time, duration)
        if _overlaps(body.appointment_time, end_t, appt.appointment_time, appt_end):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slot already booked")

    appt = Appointment(
        clinic_id=user.clinic_id,
        client_id=body.client_id,
        doctor_id=body.doctor_id,
        service_id=body.service_id,
        name=body.name.strip() if not client else client.name,
        phone=body.phone if not client else (body.phone or client.number),
        appointment_date=body.appointment_date,
        appointment_time=body.appointment_time,
        end_time=end_t,
        status=body.status or "Confirmed",
        notes=body.notes,
        created_by=user.user_id,
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return OkResponse(data=_serialize(appt, doctor.doctor_name, service_name))


@router.patch("/{appointment_id}/status", response_model=OkResponse)
def update_status(
    appointment_id: int,
    body: AppointmentStatusUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    appt = (
        db.query(Appointment)
        .filter(Appointment.appointment_id == appointment_id, Appointment.clinic_id == user.clinic_id)
        .first()
    )
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    allowed = {
        s.status_name
        for s in db.query(AppointmentStatus)
        .filter(AppointmentStatus.clinic_id == user.clinic_id, AppointmentStatus.is_active.is_(True))
        .all()
    }
    if body.status not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")

    appt.status = body.status
    db.commit()
    db.refresh(appt)
    return OkResponse(data=_enrich_many(db, [appt])[0])
