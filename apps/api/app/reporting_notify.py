"""Staff app notifications via reporting.pratikp.com (not WhatsApp).

Fire-and-forget: short timeout, failures logged only — never raise to callers.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from datetime import date, time

from app.config import get_settings

logger = logging.getLogger(__name__)

REPORTING_SOURCE = "Appointments"
ACTIONABLE_STATUSES = frozenset({"Confirmed", "Completed", "Cancelled", "No Show"})


def _format_when(appt_date: date, appt_time: time) -> str:
    # Match PHP: j M + g:i A  e.g. "5 Sep 2:30 PM"
    day = appt_date.day
    mon = appt_date.strftime("%b")
    hour = appt_time.hour % 12 or 12
    minute = appt_time.minute
    ampm = "AM" if appt_time.hour < 12 else "PM"
    return f"{day} {mon} {hour}:{minute:02d} {ampm}"


def format_booked(
    name: str,
    doctor_name: str | None,
    appt_date: date,
    appt_time: time,
    service_name: str | None,
) -> str:
    doctor = (doctor_name or "").strip() or "Doctor"
    service = (service_name or "").strip() or "Appointment"
    return (
        f"Appointment Booked: {name} — {doctor} — "
        f"{_format_when(appt_date, appt_time)} ({service})"
    )


def format_changed(
    name: str,
    doctor_name: str | None,
    appt_date: date,
    appt_time: time,
    service_name: str | None,
) -> str:
    doctor = (doctor_name or "").strip() or "Doctor"
    service = (service_name or "").strip() or "Appointment"
    return (
        f"Appointment Changed: {name} — {doctor} — "
        f"{_format_when(appt_date, appt_time)} ({service})"
    )


def format_status(
    new_status: str,
    name: str,
    doctor_name: str | None,
    appt_date: date,
    appt_time: time,
    service_name: str | None,
) -> str:
    doctor = (doctor_name or "").strip() or "Doctor"
    service = (service_name or "").strip() or "Appointment"
    return (
        f"Status → {new_status}: {name} — {doctor} — "
        f"{_format_when(appt_date, appt_time)} ({service})"
    )


def format_cancelled(
    name: str,
    doctor_name: str | None,
    appt_date: date,
    appt_time: time,
    service_name: str | None,
) -> str:
    doctor = (doctor_name or "").strip() or "Doctor"
    service = (service_name or "").strip() or "Appointment"
    return (
        f"Appointment cancelled: {name} — {doctor} — "
        f"{_format_when(appt_date, appt_time)} ({service})"
    )


def send_app_notification(message: str) -> None:
    """POST to reporting portal. No-op if API key unset. Never raises."""
    settings = get_settings()
    api_key = (settings.reporting_api_key or "").strip()
    if not api_key:
        return

    url = (settings.reporting_api_url or "").strip()
    if not url:
        return

    payload = json.dumps(
        {
            "source": REPORTING_SOURCE,
            "message": message,
            "group_id": int(settings.reporting_group_id),
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            code = getattr(resp, "status", None) or resp.getcode()
            body = resp.read().decode("utf-8", errors="replace")
            if code != 200:
                logger.warning(
                    "reporting notify failed HTTP %s msg=%r body=%r",
                    code,
                    message,
                    body[:500],
                )
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        logger.warning(
            "reporting notify failed HTTP %s msg=%r body=%r",
            e.code,
            message,
            body[:500],
        )
    except Exception as e:
        logger.warning("reporting notify failed msg=%r err=%s", message, e)
