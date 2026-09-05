"""Desk Reports / statistics endpoints (setup-PIN gated)."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import OkResponse
from app.setup_access import require_setup_unlock
from app import statistics_svc as stats

router = APIRouter(
    prefix="/statistics",
    tags=["statistics"],
    dependencies=[Depends(require_setup_unlock)],
)


def _valid_year(year: int) -> int:
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid year")
    return year


def _valid_month(month: int) -> int:
    if month < 1 or month > 12:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid month")
    return month


@router.get("/income-yearly", response_model=OkResponse)
def income_yearly(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    year: int = Query(...),
    mode: Literal["calendar", "financial"] = Query("calendar"),
) -> OkResponse:
    year = _valid_year(year)
    data = stats.yearly_income(db, user.clinic_id, year, mode)
    return OkResponse(data=data)


@router.get("/income-monthly", response_model=OkResponse)
def income_monthly(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    year: int = Query(...),
    month: int = Query(...),
) -> OkResponse:
    year = _valid_year(year)
    month = _valid_month(month)
    data = stats.monthly_income(db, user.clinic_id, year, month)
    return OkResponse(data=data)


@router.get("/clients-yearly", response_model=OkResponse)
def clients_yearly(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    year: int = Query(...),
    start_month: int = Query(1),
    end_month: int = Query(12),
) -> OkResponse:
    year = _valid_year(year)
    start_month = _valid_month(start_month)
    end_month = _valid_month(end_month)
    data = stats.yearly_clients(db, user.clinic_id, year, start_month, end_month)
    return OkResponse(data=data)


@router.get("/clients-monthly", response_model=OkResponse)
def clients_monthly(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    year: int = Query(...),
    month: int = Query(...),
) -> OkResponse:
    year = _valid_year(year)
    month = _valid_month(month)
    data = stats.monthly_clients(db, user.clinic_id, year, month)
    return OkResponse(data=data)


@router.get("/appointments-yearly", response_model=OkResponse)
def appointments_yearly(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    year: int = Query(...),
    start_month: int = Query(1),
    end_month: int = Query(12),
) -> OkResponse:
    year = _valid_year(year)
    start_month = _valid_month(start_month)
    end_month = _valid_month(end_month)
    data = stats.yearly_appointments(db, user.clinic_id, year, start_month, end_month)
    return OkResponse(data=data)


@router.get("/appointments-monthly", response_model=OkResponse)
def appointments_monthly(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    year: int = Query(...),
    month: int = Query(...),
) -> OkResponse:
    year = _valid_year(year)
    month = _valid_month(month)
    data = stats.monthly_appointments(db, user.clinic_id, year, month)
    return OkResponse(data=data)


@router.get("/checkins-yearly", response_model=OkResponse)
def checkins_yearly(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    year: int = Query(...),
    start_month: int = Query(1),
    end_month: int = Query(12),
) -> OkResponse:
    year = _valid_year(year)
    start_month = _valid_month(start_month)
    end_month = _valid_month(end_month)
    data = stats.yearly_checkins(db, user.clinic_id, year, start_month, end_month)
    return OkResponse(data=data)


@router.get("/checkins-monthly", response_model=OkResponse)
def checkins_monthly(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    year: int = Query(...),
    month: int = Query(...),
) -> OkResponse:
    year = _valid_year(year)
    month = _valid_month(month)
    data = stats.monthly_checkins(db, user.clinic_id, year, month)
    return OkResponse(data=data)


@router.get("/inquiry-conversion-yearly", response_model=OkResponse)
def inquiry_conversion_yearly(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    year: int = Query(...),
) -> OkResponse:
    year = _valid_year(year)
    data = stats.yearly_inquiry_conversion(db, user.clinic_id, year)
    return OkResponse(data=data)


@router.get("/inquiry-conversion-monthly", response_model=OkResponse)
def inquiry_conversion_monthly(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    year: int = Query(...),
    month: int = Query(...),
) -> OkResponse:
    year = _valid_year(year)
    month = _valid_month(month)
    data = stats.monthly_inquiry_conversion(db, user.clinic_id, year, month)
    return OkResponse(data=data)
