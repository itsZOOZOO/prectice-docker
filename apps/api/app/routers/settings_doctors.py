"""Doctors, schedules, breaks, time-off, and service assignments."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo

from app.auth import get_current_user
from app import clinic_settings_svc as css
from app.db import get_db
from app.models import (
    AppointmentDoctor,
    AppointmentService,
    DoctorBreak,
    DoctorServiceLink,
    DoctorTimeOff,
    User,
)
from app.schemas import OkResponse
from app.setup_access import require_setup_unlock

router = APIRouter(prefix="/settings/doctors", tags=["settings-doctors"])

UnlockDep = Annotated[None, Depends(require_setup_unlock)]

IST = ZoneInfo("Asia/Kolkata")
ELIGIBLE_ROLES = {"admin", "doctor", "staff", "receptionist"}
LUNCH_START = time(13, 0)
LUNCH_END = time(14, 0)


class ClinicDayHoursIn(BaseModel):
    day_name: str
    is_working: bool = False
    start_time: str = "10:00"
    end_time: str = "19:00"


class DoctorCreate(BaseModel):
    user_id: int | None = None
    doctor_name: str | None = Field(default=None, max_length=255)
    specialization: str | None = Field(default=None, max_length=255)
    color_code: str | None = Field(default=None, max_length=7)


class DoctorActiveUpdate(BaseModel):
    is_active: bool


class DoctorScheduleUpdate(BaseModel):
    days: list[ClinicDayHoursIn]


class DoctorBreakIn(BaseModel):
    day_name: str
    start_time: str
    end_time: str
    break_name: str | None = Field(default=None, max_length=100)
    allow_booking: bool = False


class DoctorTimeOffIn(BaseModel):
    start_date: date
    end_date: date
    start_time: str | None = None
    end_time: str | None = None
    reason: str | None = Field(default=None, max_length=255)


class DoctorServicesUpdate(BaseModel):
    service_ids: list[int]


def _today_ist() -> date:
    return datetime.now(IST).date()


def _get_doctor(db: Session, clinic_id: int, doctor_id: int) -> AppointmentDoctor:
    row = (
        db.query(AppointmentDoctor)
        .filter(
            AppointmentDoctor.doctor_id == doctor_id,
            AppointmentDoctor.clinic_id == clinic_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    return row


def _linked_user(db: Session, doctor: AppointmentDoctor) -> User | None:
    if not doctor.user_id:
        return None
    return db.query(User).filter(User.user_id == doctor.user_id).first()


def _doctor_list_item(db: Session, doctor: AppointmentDoctor) -> dict[str, Any]:
    user = _linked_user(db, doctor)
    full_name = (user.full_name if user else None) or doctor.doctor_name
    return {
        "doctor_id": doctor.doctor_id,
        "user_id": doctor.user_id,
        "full_name": full_name,
        "doctor_name": doctor.doctor_name,
        "specialization": doctor.specialization or "",
        "color_code": doctor.color_code or "#0f766e",
        "is_active": bool(doctor.is_active),
        "username": user.username if user else "",
        "role": user.role if user else "",
        "user_active": bool(user.active) if user else False,
    }


def _break_out(row: DoctorBreak) -> dict[str, Any]:
    return {
        "break_id": row.break_id,
        "day_name": css.weekday_to_day_name(row.weekday),
        "break_name": row.break_name or "",
        "start_time": css.format_time_hm(row.start_time),
        "end_time": css.format_time_hm(row.end_time),
        "allow_booking": bool(row.allow_booking),
    }


def _time_off_out(row: DoctorTimeOff, *, today: date | None = None) -> dict[str, Any]:
    today = today or _today_ist()
    return {
        "time_off_id": row.time_off_id,
        "start_date": row.start_date.isoformat(),
        "end_date": row.end_date.isoformat(),
        "start_time": css.format_time_hm(row.start_time) if row.start_time else None,
        "end_time": css.format_time_hm(row.end_time) if row.end_time else None,
        "reason": row.reason or "",
        "google_sourced": bool(row.google_sourced),
        "is_approved": bool(row.is_approved),
        "is_past": row.end_date < today,
    }


def _doctor_detail(db: Session, doctor: AppointmentDoctor) -> dict[str, Any]:
    today = _today_ist()
    user = _linked_user(db, doctor)
    full_name = (user.full_name if user else None) or doctor.doctor_name

    breaks = (
        db.query(DoctorBreak)
        .filter(
            DoctorBreak.clinic_id == doctor.clinic_id,
            DoctorBreak.doctor_id == doctor.doctor_id,
        )
        .order_by(DoctorBreak.weekday, DoctorBreak.start_time)
        .all()
    )
    time_offs = (
        db.query(DoctorTimeOff)
        .filter(
            DoctorTimeOff.clinic_id == doctor.clinic_id,
            DoctorTimeOff.doctor_id == doctor.doctor_id,
        )
        .order_by(DoctorTimeOff.start_date.desc(), DoctorTimeOff.time_off_id.desc())
        .all()
    )
    services = (
        db.query(AppointmentService)
        .filter(AppointmentService.clinic_id == doctor.clinic_id)
        .order_by(AppointmentService.service_name)
        .all()
    )
    assigned_ids = {
        link.service_id
        for link in db.query(DoctorServiceLink)
        .filter(
            DoctorServiceLink.clinic_id == doctor.clinic_id,
            DoctorServiceLink.doctor_id == doctor.doctor_id,
            DoctorServiceLink.is_active.is_(True),
        )
        .all()
    }

    return {
        "doctor_id": doctor.doctor_id,
        "user_id": doctor.user_id,
        "full_name": full_name,
        "doctor_name": doctor.doctor_name,
        "username": user.username if user else "",
        "role": user.role if user else "",
        "specialization": doctor.specialization or "",
        "color_code": doctor.color_code or "#0f766e",
        "is_active": bool(doctor.is_active),
        "schedule": css.schedule_days_for_doctor(db, doctor.clinic_id, doctor.doctor_id),
        "breaks": [_break_out(b) for b in breaks],
        "time_off": [_time_off_out(t, today=today) for t in time_offs],
        "services": [
            {
                "service_id": s.service_id,
                "service_name": s.service_name,
                "duration_minutes": s.duration_minutes,
                "assigned": s.service_id in assigned_ids,
            }
            for s in services
        ],
    }


def _seed_lunch_breaks(db: Session, clinic_id: int, doctor_id: int, days: list[dict[str, Any]]) -> None:
    for day in days:
        if not day.get("is_working"):
            continue
        weekday = css.day_name_to_weekday(day["day_name"])
        db.add(
            DoctorBreak(
                clinic_id=clinic_id,
                doctor_id=doctor_id,
                weekday=weekday,
                start_time=LUNCH_START,
                end_time=LUNCH_END,
                break_name="Lunch",
                allow_booking=False,
            )
        )


def _assign_all_active_services(db: Session, clinic_id: int, doctor_id: int) -> None:
    services = (
        db.query(AppointmentService)
        .filter(
            AppointmentService.clinic_id == clinic_id,
            AppointmentService.is_active.is_(True),
        )
        .all()
    )
    for svc in services:
        db.add(
            DoctorServiceLink(
                clinic_id=clinic_id,
                doctor_id=doctor_id,
                service_id=svc.service_id,
                is_active=True,
            )
        )


def _parse_optional_time(value: str | None, *, field: str) -> time | None:
    if value is None or str(value).strip() == "":
        return None
    return css.parse_time_hm(value, field=field)


def _validate_time_off(body: DoctorTimeOffIn) -> tuple[time | None, time | None]:
    if body.end_date < body.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be on or after start_date",
        )
    start_t = _parse_optional_time(body.start_time, field="start_time")
    end_t = _parse_optional_time(body.end_time, field="end_time")
    if (start_t is None) != (end_t is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide both start_time and end_time, or neither for full-day leave",
        )
    if start_t is not None and end_t is not None and start_t >= end_t and body.start_date == body.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_time must be before end_time",
        )
    return start_t, end_t


@router.get("", response_model=OkResponse)
def list_doctors(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    doctors = (
        db.query(AppointmentDoctor)
        .filter(AppointmentDoctor.clinic_id == user.clinic_id)
        .order_by(AppointmentDoctor.is_active.desc(), AppointmentDoctor.doctor_name)
        .all()
    )
    linked_user_ids = {d.user_id for d in doctors if d.user_id}

    eligible = (
        db.query(User)
        .filter(
            User.clinic_id == user.clinic_id,
            User.active.is_(True),
        )
        .order_by(User.full_name)
        .all()
    )
    eligible_users = [
        {
            "user_id": u.user_id,
            "full_name": u.full_name,
            "username": u.username,
            "role": u.role,
        }
        for u in eligible
        if (u.role or "").lower() in ELIGIBLE_ROLES and u.user_id not in linked_user_ids
    ]

    today = _today_ist()
    upcoming_rows = (
        db.query(DoctorTimeOff, AppointmentDoctor)
        .join(AppointmentDoctor, AppointmentDoctor.doctor_id == DoctorTimeOff.doctor_id)
        .filter(
            DoctorTimeOff.clinic_id == user.clinic_id,
            DoctorTimeOff.end_date >= today,
        )
        .order_by(DoctorTimeOff.start_date, DoctorTimeOff.time_off_id)
        .all()
    )
    upcoming_time_off = []
    for row, doctor in upcoming_rows:
        item = _time_off_out(row, today=today)
        item.update(
            {
                "doctor_id": doctor.doctor_id,
                "doctor_name": doctor.doctor_name,
                "color_code": doctor.color_code or "#0f766e",
            }
        )
        upcoming_time_off.append(item)

    return OkResponse(
        data={
            "doctors": [_doctor_list_item(db, d) for d in doctors],
            "eligible_users": eligible_users,
            "upcoming_time_off": upcoming_time_off,
        }
    )


@router.post("", response_model=OkResponse, status_code=status.HTTP_201_CREATED)
def create_doctor(
    body: DoctorCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    _: UnlockDep,
) -> OkResponse:
    if body.user_id is None and not (body.doctor_name or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide user_id or doctor_name",
        )

    linked: User | None = None
    doctor_name = (body.doctor_name or "").strip()
    if body.user_id is not None:
        linked = (
            db.query(User)
            .filter(User.user_id == body.user_id, User.clinic_id == user.clinic_id)
            .first()
        )
        if not linked:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if (linked.role or "").lower() not in ELIGIBLE_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User role is not eligible to be a doctor",
            )
        existing = (
            db.query(AppointmentDoctor)
            .filter(
                AppointmentDoctor.clinic_id == user.clinic_id,
                AppointmentDoctor.user_id == body.user_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already linked as a doctor",
            )
        doctor_name = linked.full_name.strip()

    doctor = AppointmentDoctor(
        clinic_id=user.clinic_id,
        user_id=body.user_id,
        doctor_name=doctor_name,
        specialization=(body.specialization or "").strip() or None,
        color_code=(body.color_code or "").strip() or "#0f766e",
        is_active=True,
    )
    db.add(doctor)
    db.flush()

    hours = css.get_clinic_weekly_hours(db, user.clinic_id)
    css.apply_schedule_to_doctor(db, user.clinic_id, doctor.doctor_id, hours)
    _seed_lunch_breaks(db, user.clinic_id, doctor.doctor_id, hours)
    _assign_all_active_services(db, user.clinic_id, doctor.doctor_id)
    db.commit()
    db.refresh(doctor)
    return OkResponse(data={"doctor": _doctor_detail(db, doctor)})


@router.get("/{doctor_id}", response_model=OkResponse)
def get_doctor(
    doctor_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    doctor = _get_doctor(db, user.clinic_id, doctor_id)
    return OkResponse(data={"doctor": _doctor_detail(db, doctor)})


@router.patch("/{doctor_id}/active", response_model=OkResponse)
def set_doctor_active(
    doctor_id: int,
    body: DoctorActiveUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    _: UnlockDep,
) -> OkResponse:
    doctor = _get_doctor(db, user.clinic_id, doctor_id)
    doctor.is_active = body.is_active
    db.commit()
    db.refresh(doctor)
    return OkResponse(data={"doctor": _doctor_detail(db, doctor)})


@router.put("/{doctor_id}/schedule", response_model=OkResponse)
def put_doctor_schedule(
    doctor_id: int,
    body: DoctorScheduleUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    _: UnlockDep,
) -> OkResponse:
    doctor = _get_doctor(db, user.clinic_id, doctor_id)
    css.apply_schedule_to_doctor(
        db,
        user.clinic_id,
        doctor.doctor_id,
        [d.model_dump() for d in body.days],
    )
    db.commit()
    db.refresh(doctor)
    return OkResponse(data={"doctor": _doctor_detail(db, doctor)})


@router.post("/{doctor_id}/schedule/reset-from-clinic", response_model=OkResponse)
def reset_doctor_schedule(
    doctor_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    _: UnlockDep,
) -> OkResponse:
    doctor = _get_doctor(db, user.clinic_id, doctor_id)
    hours = css.get_clinic_weekly_hours(db, user.clinic_id)
    css.apply_schedule_to_doctor(db, user.clinic_id, doctor.doctor_id, hours)
    db.commit()
    db.refresh(doctor)
    return OkResponse(data={"doctor": _doctor_detail(db, doctor)})


@router.get("/{doctor_id}/breaks", response_model=OkResponse)
def list_breaks(
    doctor_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    doctor = _get_doctor(db, user.clinic_id, doctor_id)
    rows = (
        db.query(DoctorBreak)
        .filter(
            DoctorBreak.clinic_id == user.clinic_id,
            DoctorBreak.doctor_id == doctor.doctor_id,
        )
        .order_by(DoctorBreak.weekday, DoctorBreak.start_time)
        .all()
    )
    return OkResponse(data={"breaks": [_break_out(r) for r in rows]})


@router.post("/{doctor_id}/breaks", response_model=OkResponse, status_code=status.HTTP_201_CREATED)
def create_break(
    doctor_id: int,
    body: DoctorBreakIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    _: UnlockDep,
) -> OkResponse:
    doctor = _get_doctor(db, user.clinic_id, doctor_id)
    weekday = css.day_name_to_weekday(body.day_name)
    start = css.parse_time_hm(body.start_time, field="start_time")
    end = css.parse_time_hm(body.end_time, field="end_time")
    if start >= end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_time must be before end_time",
        )
    row = DoctorBreak(
        clinic_id=user.clinic_id,
        doctor_id=doctor.doctor_id,
        weekday=weekday,
        start_time=start,
        end_time=end,
        break_name=(body.break_name or "").strip() or None,
        allow_booking=body.allow_booking,
    )
    db.add(row)
    db.commit()
    db.refresh(doctor)
    return OkResponse(data={"doctor": _doctor_detail(db, doctor)})


@router.patch("/{doctor_id}/breaks/{break_id}", response_model=OkResponse)
def update_break(
    doctor_id: int,
    break_id: int,
    body: DoctorBreakIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    _: UnlockDep,
) -> OkResponse:
    doctor = _get_doctor(db, user.clinic_id, doctor_id)
    row = (
        db.query(DoctorBreak)
        .filter(
            DoctorBreak.break_id == break_id,
            DoctorBreak.doctor_id == doctor.doctor_id,
            DoctorBreak.clinic_id == user.clinic_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Break not found")
    weekday = css.day_name_to_weekday(body.day_name)
    start = css.parse_time_hm(body.start_time, field="start_time")
    end = css.parse_time_hm(body.end_time, field="end_time")
    if start >= end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_time must be before end_time",
        )
    row.weekday = weekday
    row.start_time = start
    row.end_time = end
    row.break_name = (body.break_name or "").strip() or None
    row.allow_booking = body.allow_booking
    db.commit()
    db.refresh(doctor)
    return OkResponse(data={"doctor": _doctor_detail(db, doctor)})


@router.delete("/{doctor_id}/breaks/{break_id}", response_model=OkResponse)
def delete_break(
    doctor_id: int,
    break_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    _: UnlockDep,
) -> OkResponse:
    doctor = _get_doctor(db, user.clinic_id, doctor_id)
    row = (
        db.query(DoctorBreak)
        .filter(
            DoctorBreak.break_id == break_id,
            DoctorBreak.doctor_id == doctor.doctor_id,
            DoctorBreak.clinic_id == user.clinic_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Break not found")
    db.delete(row)
    db.commit()
    db.refresh(doctor)
    return OkResponse(data={"doctor": _doctor_detail(db, doctor)})


@router.get("/{doctor_id}/time-off", response_model=OkResponse)
def list_time_off(
    doctor_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    doctor = _get_doctor(db, user.clinic_id, doctor_id)
    today = _today_ist()
    rows = (
        db.query(DoctorTimeOff)
        .filter(
            DoctorTimeOff.clinic_id == user.clinic_id,
            DoctorTimeOff.doctor_id == doctor.doctor_id,
        )
        .order_by(DoctorTimeOff.start_date.desc())
        .all()
    )
    return OkResponse(data={"time_off": [_time_off_out(r, today=today) for r in rows]})


@router.post("/{doctor_id}/time-off", response_model=OkResponse, status_code=status.HTTP_201_CREATED)
def create_time_off(
    doctor_id: int,
    body: DoctorTimeOffIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    _: UnlockDep,
) -> OkResponse:
    doctor = _get_doctor(db, user.clinic_id, doctor_id)
    start_t, end_t = _validate_time_off(body)
    row = DoctorTimeOff(
        clinic_id=user.clinic_id,
        doctor_id=doctor.doctor_id,
        start_date=body.start_date,
        end_date=body.end_date,
        start_time=start_t,
        end_time=end_t,
        reason=(body.reason or "").strip() or None,
        is_approved=True,
        google_sourced=False,
    )
    db.add(row)
    db.commit()
    db.refresh(doctor)
    return OkResponse(data={"doctor": _doctor_detail(db, doctor)})


@router.patch("/{doctor_id}/time-off/{time_off_id}", response_model=OkResponse)
def update_time_off(
    doctor_id: int,
    time_off_id: int,
    body: DoctorTimeOffIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    _: UnlockDep,
) -> OkResponse:
    doctor = _get_doctor(db, user.clinic_id, doctor_id)
    row = (
        db.query(DoctorTimeOff)
        .filter(
            DoctorTimeOff.time_off_id == time_off_id,
            DoctorTimeOff.doctor_id == doctor.doctor_id,
            DoctorTimeOff.clinic_id == user.clinic_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Time off not found")
    start_t, end_t = _validate_time_off(body)
    row.start_date = body.start_date
    row.end_date = body.end_date
    row.start_time = start_t
    row.end_time = end_t
    row.reason = (body.reason or "").strip() or None
    db.commit()
    db.refresh(doctor)
    return OkResponse(data={"doctor": _doctor_detail(db, doctor)})


@router.delete("/{doctor_id}/time-off/{time_off_id}", response_model=OkResponse)
def delete_time_off(
    doctor_id: int,
    time_off_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    _: UnlockDep,
) -> OkResponse:
    doctor = _get_doctor(db, user.clinic_id, doctor_id)
    row = (
        db.query(DoctorTimeOff)
        .filter(
            DoctorTimeOff.time_off_id == time_off_id,
            DoctorTimeOff.doctor_id == doctor.doctor_id,
            DoctorTimeOff.clinic_id == user.clinic_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Time off not found")
    db.delete(row)
    db.commit()
    db.refresh(doctor)
    return OkResponse(data={"doctor": _doctor_detail(db, doctor)})


@router.put("/{doctor_id}/services", response_model=OkResponse)
def put_doctor_services(
    doctor_id: int,
    body: DoctorServicesUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    _: UnlockDep,
) -> OkResponse:
    doctor = _get_doctor(db, user.clinic_id, doctor_id)
    service_ids = list(dict.fromkeys(body.service_ids))
    if service_ids:
        found = {
            s.service_id
            for s in db.query(AppointmentService)
            .filter(
                AppointmentService.clinic_id == user.clinic_id,
                AppointmentService.service_id.in_(service_ids),
            )
            .all()
        }
        missing = [sid for sid in service_ids if sid not in found]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown service_ids: {missing}",
            )

    existing = (
        db.query(DoctorServiceLink)
        .filter(
            DoctorServiceLink.clinic_id == user.clinic_id,
            DoctorServiceLink.doctor_id == doctor.doctor_id,
        )
        .all()
    )
    by_service = {link.service_id: link for link in existing}
    wanted = set(service_ids)

    for sid, link in by_service.items():
        link.is_active = sid in wanted

    for sid in wanted:
        if sid not in by_service:
            db.add(
                DoctorServiceLink(
                    clinic_id=user.clinic_id,
                    doctor_id=doctor.doctor_id,
                    service_id=sid,
                    is_active=True,
                )
            )

    db.commit()
    db.refresh(doctor)
    return OkResponse(data={"doctor": _doctor_detail(db, doctor)})
