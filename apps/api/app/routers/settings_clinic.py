"""Clinic hours, booking rules, and appointment services settings."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app import clinic_settings_svc as css
from app.db import get_db
from app.models import AppointmentService, User
from app.schemas import OkResponse
from app.setup_access import require_setup_unlock

router = APIRouter(prefix="/settings/clinic", tags=["settings-clinic"])

UnlockDep = Annotated[None, Depends(require_setup_unlock)]


class ClinicDayHoursIn(BaseModel):
    day_name: str
    is_working: bool = False
    start_time: str = "10:00"
    end_time: str = "19:00"


class ClinicHoursUpdate(BaseModel):
    days: list[ClinicDayHoursIn]


class AppointmentSettingsUpdate(BaseModel):
    slot_interval: int | None = None
    allow_overlapping_appointments: bool | None = None
    booking_lead_time_hours: int | None = None
    max_advance_booking_days: int | None = None
    public_booking_min_days_ahead: int | None = None
    public_booking_max_days_ahead: int | None = None


class ServiceCreate(BaseModel):
    service_name: str = Field(min_length=1, max_length=255)
    duration_minutes: int = Field(default=30, ge=5, le=480)
    description: str | None = Field(default=None, max_length=255)


class ServiceUpdate(BaseModel):
    service_name: str | None = Field(default=None, min_length=1, max_length=255)
    duration_minutes: int | None = Field(default=None, ge=5, le=480)
    description: str | None = Field(default=None, max_length=255)


class ServiceActiveUpdate(BaseModel):
    is_active: bool


class ServicePublicBookingUpdate(BaseModel):
    allow_public_booking: bool


def _service_out(row: AppointmentService) -> dict[str, Any]:
    return {
        "service_id": row.service_id,
        "service_name": row.service_name,
        "duration_minutes": row.duration_minutes,
        "description": row.description or "",
        "is_active": bool(row.is_active),
        "allow_public_booking": bool(getattr(row, "allow_public_booking", False)),
    }


def _get_service(db: Session, clinic_id: int, service_id: int) -> AppointmentService:
    row = (
        db.query(AppointmentService)
        .filter(
            AppointmentService.service_id == service_id,
            AppointmentService.clinic_id == clinic_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return row


@router.get("/hours", response_model=OkResponse)
def get_clinic_hours(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    days = css.get_clinic_weekly_hours(db, user.clinic_id)
    return OkResponse(data={"days": days})


@router.patch("/hours", response_model=OkResponse)
def patch_clinic_hours(
    body: ClinicHoursUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    _: UnlockDep,
) -> OkResponse:
    days = css.update_clinic_weekly_hours(db, user.clinic_id, [d.model_dump() for d in body.days])
    db.commit()
    return OkResponse(data={"days": days})


@router.get("/appointment-settings", response_model=OkResponse)
def get_appointment_settings(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    settings = css.get_appointment_settings(db, user.clinic_id)
    return OkResponse(data={"settings": settings})


@router.patch("/appointment-settings", response_model=OkResponse)
def patch_appointment_settings(
    body: AppointmentSettingsUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    _: UnlockDep,
) -> OkResponse:
    settings = css.update_appointment_settings(
        db,
        user.clinic_id,
        body.model_dump(exclude_unset=True),
    )
    db.commit()
    return OkResponse(data={"settings": settings})


@router.get("/services", response_model=OkResponse)
def list_services(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    rows = (
        db.query(AppointmentService)
        .filter(AppointmentService.clinic_id == user.clinic_id)
        .order_by(AppointmentService.service_name)
        .all()
    )
    return OkResponse(data={"services": [_service_out(r) for r in rows]})


@router.post("/services", response_model=OkResponse, status_code=status.HTTP_201_CREATED)
def create_service(
    body: ServiceCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    _: UnlockDep,
) -> OkResponse:
    row = AppointmentService(
        clinic_id=user.clinic_id,
        service_name=body.service_name.strip(),
        duration_minutes=body.duration_minutes,
        description=(body.description or "").strip() or None,
        is_active=True,
        allow_public_booking=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return OkResponse(data={"service": _service_out(row)})


@router.patch("/services/{service_id}", response_model=OkResponse)
def update_service(
    service_id: int,
    body: ServiceUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    _: UnlockDep,
) -> OkResponse:
    row = _get_service(db, user.clinic_id, service_id)
    data = body.model_dump(exclude_unset=True)
    if "service_name" in data and data["service_name"] is not None:
        row.service_name = data["service_name"].strip()
    if "duration_minutes" in data and data["duration_minutes"] is not None:
        row.duration_minutes = data["duration_minutes"]
    if "description" in data:
        desc = data["description"]
        row.description = (desc or "").strip() or None
    db.commit()
    db.refresh(row)
    return OkResponse(data={"service": _service_out(row)})


@router.patch("/services/{service_id}/active", response_model=OkResponse)
def set_service_active(
    service_id: int,
    body: ServiceActiveUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    _: UnlockDep,
) -> OkResponse:
    row = _get_service(db, user.clinic_id, service_id)
    row.is_active = body.is_active
    db.commit()
    db.refresh(row)
    return OkResponse(data={"service": _service_out(row)})


@router.patch("/services/{service_id}/public-booking", response_model=OkResponse)
def set_service_public_booking(
    service_id: int,
    body: ServicePublicBookingUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    _: UnlockDep,
) -> OkResponse:
    row = _get_service(db, user.clinic_id, service_id)
    row.allow_public_booking = body.allow_public_booking
    db.commit()
    db.refresh(row)
    return OkResponse(data={"service": _service_out(row)})
