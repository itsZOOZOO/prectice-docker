"""Clinic weekly hours + appointment booking rules (Desk settings Wave 1)."""

from __future__ import annotations

import json
import re
from datetime import time
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import AppointmentDoctor, ClinicSetting, DoctorSchedule

WEEK_DAYS = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)

_DAY_NAME_TO_WEEKDAY = {name.lower(): i for i, name in enumerate(WEEK_DAYS)}

APPOINTMENT_SETTING_DEFAULTS: dict[str, Any] = {
    "slot_interval": 15,
    "allow_overlapping_appointments": False,
    "booking_lead_time_hours": 0,
    "max_advance_booking_days": 90,
    "public_booking_min_days_ahead": 0,
    "public_booking_max_days_ahead": 30,
}

CLINIC_WEEKLY_HOURS_KEY = "clinic_weekly_hours"

_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})(?::\d{2})?$")


def day_name_to_weekday(day_name: str) -> int:
    key = (day_name or "").strip().lower()
    if key not in _DAY_NAME_TO_WEEKDAY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid day_name: {day_name!r}",
        )
    return _DAY_NAME_TO_WEEKDAY[key]


def weekday_to_day_name(weekday: int) -> str:
    if weekday < 0 or weekday > 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid weekday: {weekday}",
        )
    return WEEK_DAYS[weekday]


def format_time_hm(value: time | str | None, *, default: str = "10:00") -> str:
    if value is None:
        return default
    if isinstance(value, time):
        return f"{value.hour:02d}:{value.minute:02d}"
    raw = str(value).strip()
    m = _TIME_RE.match(raw)
    if not m:
        return default
    return f"{int(m.group(1)):02d}:{int(m.group(2)):02d}"


def parse_time_hm(value: str | time | None, *, field: str = "time") -> time:
    if isinstance(value, time):
        return time(value.hour, value.minute)
    raw = str(value or "").strip()
    m = _TIME_RE.match(raw)
    if not m:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field}: expected HH:MM",
        )
    hour, minute = int(m.group(1)), int(m.group(2))
    if hour > 23 or minute > 59:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field}: expected HH:MM",
        )
    return time(hour, minute)


def get_setting(db: Session, clinic_id: int, key: str, default: str = "") -> str:
    row = (
        db.query(ClinicSetting)
        .filter(ClinicSetting.clinic_id == clinic_id, ClinicSetting.setting_key == key)
        .first()
    )
    if row and row.setting_value is not None and str(row.setting_value).strip() != "":
        return str(row.setting_value)
    return default


def set_setting(db: Session, clinic_id: int, key: str, value: str | None) -> None:
    row = (
        db.query(ClinicSetting)
        .filter(ClinicSetting.clinic_id == clinic_id, ClinicSetting.setting_key == key)
        .first()
    )
    if row:
        row.setting_value = value
    else:
        db.add(ClinicSetting(clinic_id=clinic_id, setting_key=key, setting_value=value))


def default_weekly_hours() -> list[dict[str, Any]]:
    days: list[dict[str, Any]] = []
    for i, name in enumerate(WEEK_DAYS):
        is_working = i < 6  # Mon–Sat
        days.append(
            {
                "day_name": name,
                "is_working": is_working,
                "start_time": "10:00",
                "end_time": "19:00",
            }
        )
    return days


def _normalize_day_hours(day: dict[str, Any] | Any) -> dict[str, Any]:
    if hasattr(day, "model_dump"):
        raw = day.model_dump()
    elif isinstance(day, dict):
        raw = day
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid day hours entry",
        )
    day_name = str(raw.get("day_name") or "").strip()
    weekday = day_name_to_weekday(day_name)
    is_working = bool(raw.get("is_working", False))
    start = parse_time_hm(raw.get("start_time") or "10:00", field="start_time")
    end = parse_time_hm(raw.get("end_time") or "19:00", field="end_time")
    if is_working and start >= end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"start_time must be before end_time for {WEEK_DAYS[weekday]}",
        )
    return {
        "day_name": WEEK_DAYS[weekday],
        "weekday": weekday,
        "is_working": is_working,
        "start_time": format_time_hm(start),
        "end_time": format_time_hm(end),
        "start_time_obj": start,
        "end_time_obj": end,
    }


def normalize_weekly_hours(days: list[Any]) -> list[dict[str, Any]]:
    if not isinstance(days, list) or len(days) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="days must be a non-empty list",
        )
    by_weekday: dict[int, dict[str, Any]] = {}
    for entry in days:
        normalized = _normalize_day_hours(entry)
        by_weekday[normalized["weekday"]] = normalized
    # Fill missing weekdays from defaults
    defaults = {i: d for i, d in enumerate(default_weekly_hours())}
    result: list[dict[str, Any]] = []
    for i in range(7):
        if i in by_weekday:
            d = by_weekday[i]
            result.append(
                {
                    "day_name": d["day_name"],
                    "is_working": d["is_working"],
                    "start_time": d["start_time"],
                    "end_time": d["end_time"],
                }
            )
        else:
            result.append(defaults[i])
    return result


def _hours_from_doctor_schedules(db: Session, clinic_id: int) -> list[dict[str, Any]] | None:
    doctor = (
        db.query(AppointmentDoctor)
        .filter(
            AppointmentDoctor.clinic_id == clinic_id,
            AppointmentDoctor.is_active.is_(True),
        )
        .order_by(AppointmentDoctor.doctor_id)
        .first()
    )
    if not doctor:
        return None
    rows = (
        db.query(DoctorSchedule)
        .filter(
            DoctorSchedule.clinic_id == clinic_id,
            DoctorSchedule.doctor_id == doctor.doctor_id,
        )
        .all()
    )
    if not rows:
        return None
    by_weekday = {r.weekday: r for r in rows}
    defaults = default_weekly_hours()
    out: list[dict[str, Any]] = []
    for i, default in enumerate(defaults):
        row = by_weekday.get(i)
        if row:
            out.append(
                {
                    "day_name": WEEK_DAYS[i],
                    "is_working": bool(row.is_working),
                    "start_time": format_time_hm(row.start_time),
                    "end_time": format_time_hm(row.end_time),
                }
            )
        else:
            out.append(default)
    return out


def get_clinic_weekly_hours(db: Session, clinic_id: int) -> list[dict[str, Any]]:
    raw = get_setting(db, clinic_id, CLINIC_WEEKLY_HOURS_KEY, "")
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list) and parsed:
                return normalize_weekly_hours(parsed)
        except (json.JSONDecodeError, HTTPException, TypeError, ValueError):
            pass
    from_doctor = _hours_from_doctor_schedules(db, clinic_id)
    if from_doctor:
        return from_doctor
    return default_weekly_hours()


def apply_schedule_to_doctor(
    db: Session,
    clinic_id: int,
    doctor_id: int,
    days: list[dict[str, Any]],
) -> None:
    normalized = normalize_weekly_hours(days)
    existing = {
        r.weekday: r
        for r in db.query(DoctorSchedule)
        .filter(
            DoctorSchedule.clinic_id == clinic_id,
            DoctorSchedule.doctor_id == doctor_id,
        )
        .all()
    }
    for day in normalized:
        weekday = day_name_to_weekday(day["day_name"])
        start = parse_time_hm(day["start_time"], field="start_time")
        end = parse_time_hm(day["end_time"], field="end_time")
        row = existing.get(weekday)
        if row:
            row.is_working = bool(day["is_working"])
            row.start_time = start
            row.end_time = end
        else:
            db.add(
                DoctorSchedule(
                    clinic_id=clinic_id,
                    doctor_id=doctor_id,
                    weekday=weekday,
                    is_working=bool(day["is_working"]),
                    start_time=start,
                    end_time=end,
                )
            )


def update_clinic_weekly_hours(
    db: Session,
    clinic_id: int,
    days: list[Any],
) -> list[dict[str, Any]]:
    normalized = normalize_weekly_hours(days)
    set_setting(db, clinic_id, CLINIC_WEEKLY_HOURS_KEY, json.dumps(normalized))
    doctors = (
        db.query(AppointmentDoctor)
        .filter(
            AppointmentDoctor.clinic_id == clinic_id,
            AppointmentDoctor.is_active.is_(True),
        )
        .all()
    )
    for doctor in doctors:
        apply_schedule_to_doctor(db, clinic_id, doctor.doctor_id, normalized)
    db.flush()
    return normalized


def get_appointment_settings(db: Session, clinic_id: int) -> dict[str, Any]:
    settings = dict(APPOINTMENT_SETTING_DEFAULTS)
    for key, default in APPOINTMENT_SETTING_DEFAULTS.items():
        raw = get_setting(db, clinic_id, key, "")
        if raw == "":
            continue
        if isinstance(default, bool):
            settings[key] = raw.strip().lower() in ("1", "true", "yes", "on")
        else:
            try:
                settings[key] = int(str(raw).strip())
            except ValueError:
                settings[key] = default
    return settings


def _clamp_int(value: Any, *, lo: int, hi: int, field: str) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field} must be an integer",
        ) from None
    if n < lo or n > hi:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field} must be between {lo} and {hi}",
        )
    return n


def update_appointment_settings(
    db: Session,
    clinic_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    current = get_appointment_settings(db, clinic_id)
    if "slot_interval" in payload and payload["slot_interval"] is not None:
        current["slot_interval"] = _clamp_int(
            payload["slot_interval"], lo=5, hi=60, field="slot_interval"
        )
    if "allow_overlapping_appointments" in payload and payload["allow_overlapping_appointments"] is not None:
        current["allow_overlapping_appointments"] = bool(payload["allow_overlapping_appointments"])
    if "booking_lead_time_hours" in payload and payload["booking_lead_time_hours"] is not None:
        current["booking_lead_time_hours"] = _clamp_int(
            payload["booking_lead_time_hours"],
            lo=0,
            hi=48,
            field="booking_lead_time_hours",
        )
    if "max_advance_booking_days" in payload and payload["max_advance_booking_days"] is not None:
        current["max_advance_booking_days"] = _clamp_int(
            payload["max_advance_booking_days"],
            lo=1,
            hi=365,
            field="max_advance_booking_days",
        )
    if "public_booking_min_days_ahead" in payload and payload["public_booking_min_days_ahead"] is not None:
        current["public_booking_min_days_ahead"] = _clamp_int(
            payload["public_booking_min_days_ahead"],
            lo=0,
            hi=30,
            field="public_booking_min_days_ahead",
        )
    if "public_booking_max_days_ahead" in payload and payload["public_booking_max_days_ahead"] is not None:
        current["public_booking_max_days_ahead"] = _clamp_int(
            payload["public_booking_max_days_ahead"],
            lo=1,
            hi=90,
            field="public_booking_max_days_ahead",
        )
    if current["public_booking_min_days_ahead"] > current["public_booking_max_days_ahead"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="public_booking_min_days_ahead cannot exceed public_booking_max_days_ahead",
        )

    set_setting(db, clinic_id, "slot_interval", str(current["slot_interval"]))
    set_setting(
        db,
        clinic_id,
        "allow_overlapping_appointments",
        "1" if current["allow_overlapping_appointments"] else "0",
    )
    set_setting(db, clinic_id, "booking_lead_time_hours", str(current["booking_lead_time_hours"]))
    set_setting(db, clinic_id, "max_advance_booking_days", str(current["max_advance_booking_days"]))
    set_setting(
        db,
        clinic_id,
        "public_booking_min_days_ahead",
        str(current["public_booking_min_days_ahead"]),
    )
    set_setting(
        db,
        clinic_id,
        "public_booking_max_days_ahead",
        str(current["public_booking_max_days_ahead"]),
    )
    db.flush()
    return current


def schedule_days_for_doctor(db: Session, clinic_id: int, doctor_id: int) -> list[dict[str, Any]]:
    rows = (
        db.query(DoctorSchedule)
        .filter(
            DoctorSchedule.clinic_id == clinic_id,
            DoctorSchedule.doctor_id == doctor_id,
        )
        .all()
    )
    by_weekday = {r.weekday: r for r in rows}
    clinic_hours = get_clinic_weekly_hours(db, clinic_id)
    out: list[dict[str, Any]] = []
    for i, clinic_day in enumerate(clinic_hours):
        row = by_weekday.get(i)
        if row:
            out.append(
                {
                    "day_name": WEEK_DAYS[i],
                    "is_working": bool(row.is_working),
                    "start_time": format_time_hm(row.start_time),
                    "end_time": format_time_hm(row.end_time),
                }
            )
        else:
            out.append(dict(clinic_day))
    return out
