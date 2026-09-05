"""Clinic statistics aggregations (income + patients) for desk Reports."""

from __future__ import annotations

import calendar
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Literal
from zoneinfo import ZoneInfo

from sqlalchemy import and_, case, extract, func
from sqlalchemy.orm import Session

from app.models import (
    Appointment,
    AppointmentDoctor,
    AppointmentService,
    Client,
    ClientCheckinLog,
    MoneyReceipt,
)

IST = ZoneInfo("Asia/Kolkata")
SIGNIFICANT_THRESHOLD = 10000.0

MONTH_LABELS = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}

CONVERTED_STATUSES = frozenset(
    {
        "Under Rx",
        "Completed",
        "6m followup",
        "Yearly followup",
        "Ortho",
    }
)

IncomeYearMode = Literal["calendar", "financial"]


def _ist_day_bounds(d: date) -> tuple[datetime, datetime]:
    start = datetime.combine(d, time.min, tzinfo=IST)
    end = datetime.combine(d, time.max, tzinfo=IST)
    return start, end


def _month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    last = calendar.monthrange(year, month)[1]
    return _ist_day_bounds(date(year, month, 1))[0], _ist_day_bounds(date(year, month, last))[1]


def _income_range(year: int, mode: IncomeYearMode) -> tuple[datetime, datetime, str, str, str]:
    if mode == "financial":
        start_d = date(year, 4, 1)
        end_d = date(year + 1, 3, 31)
        label = f"April {year} – March {year + 1}"
    else:
        start_d = date(year, 1, 1)
        end_d = date(year, 12, 31)
        label = f"January – December {year}"
    start, _ = _ist_day_bounds(start_d)
    _, end = _ist_day_bounds(end_d)
    return start, end, start_d.isoformat(), end_d.isoformat(), label


def _money(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(round(value, 2))
    return float(round(float(value), 2))


def _month_status(income: float) -> str:
    if income > SIGNIFICANT_THRESHOLD:
        return "significant"
    if income > 0:
        return "low"
    return "none"


def _payment_modes(db: Session, clinic_id: int, start: datetime, end: datetime) -> list[dict[str, Any]]:
    mode_expr = func.coalesce(
        func.nullif(func.trim(MoneyReceipt.payment_mode), ""),
        "Other",
    )
    rows = (
        db.query(
            mode_expr.label("payment_mode"),
            func.sum(MoneyReceipt.amount).label("total"),
            func.count(MoneyReceipt.receipt_id).label("cnt"),
        )
        .join(Client, Client.client_id == MoneyReceipt.client_id)
        .filter(
            MoneyReceipt.clinic_id == clinic_id,
            MoneyReceipt.visible.is_(True),
            Client.clinic_id == clinic_id,
            MoneyReceipt.received_at >= start,
            MoneyReceipt.received_at <= end,
        )
        .group_by(mode_expr)
        .order_by(func.sum(MoneyReceipt.amount).desc())
        .all()
    )
    return [
        {
            "payment_mode": str(r.payment_mode or "Other"),
            "total": _money(r.total),
            "count": int(r.cnt or 0),
        }
        for r in rows
    ]


def yearly_income(db: Session, clinic_id: int, year: int, mode: IncomeYearMode = "calendar") -> dict[str, Any]:
    mode = "financial" if mode == "financial" else "calendar"
    start, end, start_date, end_date, date_range_label = _income_range(year, mode)

    month_key = func.to_char(
        func.timezone("Asia/Kolkata", MoneyReceipt.received_at),
        "YYYY-MM",
    )
    raw_rows = (
        db.query(
            month_key.label("month_key"),
            func.sum(MoneyReceipt.amount).label("month_total"),
        )
        .join(Client, Client.client_id == MoneyReceipt.client_id)
        .filter(
            MoneyReceipt.clinic_id == clinic_id,
            MoneyReceipt.visible.is_(True),
            Client.clinic_id == clinic_id,
            MoneyReceipt.received_at >= start,
            MoneyReceipt.received_at <= end,
        )
        .group_by(month_key)
        .all()
    )
    raw = {str(r.month_key): _money(r.month_total) for r in raw_rows}

    all_months: list[dict[str, Any]] = []
    cursor = date(start.year, start.month, 1)
    end_month = date(end.year, end.month, 1)
    while cursor <= end_month:
        key = f"{cursor.year:04d}-{cursor.month:02d}"
        amount = float(raw.get(key, 0.0))
        label = (
            f"{MONTH_LABELS[cursor.month]} {cursor.year}"
            if mode == "financial"
            else MONTH_LABELS[cursor.month]
        )
        all_months.append(
            {
                "month_key": key,
                "month": cursor.month,
                "year": cursor.year,
                "label": label,
                "income": amount,
                "status": _month_status(amount),
            }
        )
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)

    total_income = 0.0
    months_with_income = 0
    significant_months = 0
    significant_income_total = 0.0
    for row in all_months:
        amount = float(row["income"])
        total_income += amount
        if amount > 0:
            months_with_income += 1
        if amount > SIGNIFICANT_THRESHOLD:
            significant_months += 1
            significant_income_total += amount

    average_monthly = (
        round(significant_income_total / significant_months, 2) if significant_months > 0 else 0.0
    )

    return {
        "year": year,
        "mode": mode,
        "start_date": start_date,
        "end_date": end_date,
        "date_range_label": date_range_label,
        "total_income": round(total_income, 2),
        "average_monthly_income": average_monthly,
        "significant_month_threshold": SIGNIFICANT_THRESHOLD,
        "significant_months": significant_months,
        "months_in_range": len(all_months),
        "months_with_income": months_with_income,
        "monthly_flow": all_months,
        "payment_modes": _payment_modes(db, clinic_id, start, end),
    }


def monthly_income(db: Session, clinic_id: int, year: int, month: int) -> dict[str, Any]:
    month = max(1, min(12, month))
    start, end = _month_bounds(year, month)
    days_in_month = calendar.monthrange(year, month)[1]
    month_key = f"{year:04d}-{month:02d}"

    rows = (
        db.query(MoneyReceipt, Client)
        .join(Client, Client.client_id == MoneyReceipt.client_id)
        .filter(
            MoneyReceipt.clinic_id == clinic_id,
            MoneyReceipt.visible.is_(True),
            Client.clinic_id == clinic_id,
            MoneyReceipt.received_at >= start,
            MoneyReceipt.received_at <= end,
        )
        .order_by(MoneyReceipt.received_at.desc())
        .all()
    )

    transactions: list[dict[str, Any]] = []
    total_income = 0.0
    daily_raw: dict[int, dict[str, float | int]] = {}

    for receipt, client in rows:
        amount = _money(receipt.amount)
        total_income += amount
        received = receipt.received_at
        if received is not None:
            if received.tzinfo is None:
                received = received.replace(tzinfo=IST)
            local = received.astimezone(IST)
            day = local.day
            bucket = daily_raw.setdefault(day, {"income": 0.0, "count": 0})
            bucket["income"] = float(bucket["income"]) + amount
            bucket["count"] = int(bucket["count"]) + 1
            receipt_date = local.isoformat()
        else:
            receipt_date = ""

        transactions.append(
            {
                "receipt_id": receipt.receipt_id,
                "client_id": client.client_id,
                "client_name": client.name or "",
                "client_visible": bool(client.visible),
                "amount": amount,
                "payment_mode": (receipt.payment_mode or "").strip() or None,
                "description": (receipt.description or "").strip() or None,
                "receipt_date": receipt_date,
            }
        )

    daily_flow = []
    for d in range(1, days_in_month + 1):
        bucket = daily_raw.get(d) or {"income": 0.0, "count": 0}
        daily_flow.append(
            {
                "day": d,
                "label": str(d),
                "income": round(float(bucket["income"]), 2),
                "count": int(bucket["count"]),
            }
        )

    return {
        "year": year,
        "month": month,
        "month_label": MONTH_LABELS[month],
        "month_key": month_key,
        "days_in_month": days_in_month,
        "total_income": round(total_income, 2),
        "transaction_count": len(transactions),
        "average_per_day": round(total_income / days_in_month, 2) if days_in_month else 0.0,
        "payment_modes": _payment_modes(db, clinic_id, start, end),
        "daily_flow": daily_flow,
        "transactions": transactions,
    }


def _client_base_filter(clinic_id: int, start: datetime, end: datetime):
    return and_(
        Client.clinic_id == clinic_id,
        Client.visible.is_(True),
        Client.created_at >= start,
        Client.created_at <= end,
    )


def _build_clients_overview(db: Session, clinic_id: int, start: datetime, end: datetime) -> dict[str, Any]:
    clients = (
        db.query(Client)
        .filter(_client_base_filter(clinic_id, start, end))
        .order_by(Client.created_at.desc())
        .all()
    )
    total_clients = len(clients)

    status_rows = (
        db.query(Client.status, func.count(Client.client_id))
        .filter(_client_base_filter(clinic_id, start, end))
        .group_by(Client.status)
        .order_by(func.count(Client.client_id).desc())
        .all()
    )
    status_counts = [{"status": str(s or ""), "count": int(c)} for s, c in status_rows]

    converted = 0
    not_converted = 0
    for c in clients:
        if (c.status or "") in CONVERTED_STATUSES:
            converted += 1
        else:
            not_converted += 1
    overall_pct = int(round(converted / total_clients * 100)) if total_clients else 0

    source_expr = func.coalesce(func.nullif(Client.lead_source, ""), "Unknown")
    lead_converted = case(
        (
            and_(
                Client.status.isnot(None),
                Client.status.notin_(["None", "Inquiry", "DND", ""]),
            ),
            1,
        ),
        else_=0,
    )
    lead_rows = (
        db.query(
            source_expr.label("source"),
            func.count(Client.client_id).label("total"),
            func.sum(lead_converted).label("converted"),
        )
        .filter(_client_base_filter(clinic_id, start, end))
        .group_by(source_expr)
        .order_by(func.count(Client.client_id).desc())
        .all()
    )
    lead_sources = []
    for r in lead_rows:
        total = int(r.total or 0)
        conv = int(r.converted or 0)
        lead_sources.append(
            {
                "source": str(r.source or "Unknown"),
                "total": total,
                "converted": conv,
                "conversion_pct": int(round(conv / total * 100)) if total else 0,
            }
        )

    client_rows = []
    for c in clients:
        created = c.created_at
        if created is not None and created.tzinfo is None:
            created = created.replace(tzinfo=IST)
        client_rows.append(
            {
                "client_id": c.client_id,
                "name": c.name or "",
                "number": c.number or "",
                "place": c.place or "",
                "age": c.age,
                "gender": c.gender or "",
                "status": c.status or "",
                "created_at": created.isoformat() if created else None,
            }
        )

    return {
        "total_clients": total_clients,
        "status_counts": status_counts,
        "conversion": {
            "overall_pct": overall_pct,
            "converted": converted,
            "not_converted": not_converted,
            "total": total_clients,
        },
        "lead_sources": lead_sources,
        "clients": client_rows,
    }


def yearly_clients(
    db: Session,
    clinic_id: int,
    year: int,
    start_month: int = 1,
    end_month: int = 12,
) -> dict[str, Any]:
    start_month = max(1, min(12, start_month))
    end_month = max(1, min(12, end_month))
    if start_month > end_month:
        start_month, end_month = end_month, start_month

    start, _ = _month_bounds(year, start_month)
    _, end = _month_bounds(year, end_month)
    overview = _build_clients_overview(db, clinic_id, start, end)

    local_created = func.timezone("Asia/Kolkata", Client.created_at)
    month_expr = extract("month", local_created)
    raw_rows = (
        db.query(month_expr.label("month_num"), func.count(Client.client_id))
        .filter(_client_base_filter(clinic_id, start, end))
        .group_by(month_expr)
        .all()
    )
    monthly_raw = {int(m): int(c) for m, c in raw_rows}

    monthly_flow = [
        {"month": m, "label": MONTH_LABELS[m], "count": monthly_raw.get(m, 0)}
        for m in range(start_month, end_month + 1)
    ]
    number_of_months = end_month - start_month + 1
    average_per_month = (
        round(overview["total_clients"] / number_of_months, 1) if number_of_months else 0.0
    )

    return {
        **overview,
        "year": year,
        "start_month": start_month,
        "end_month": end_month,
        "average_per_month": average_per_month,
        "monthly_flow": monthly_flow,
    }


def monthly_clients(db: Session, clinic_id: int, year: int, month: int) -> dict[str, Any]:
    month = max(1, min(12, month))
    start, end = _month_bounds(year, month)
    days_in_month = calendar.monthrange(year, month)[1]
    overview = _build_clients_overview(db, clinic_id, start, end)

    local_created = func.timezone("Asia/Kolkata", Client.created_at)
    day_expr = extract("day", local_created)
    raw_rows = (
        db.query(day_expr.label("day_num"), func.count(Client.client_id))
        .filter(_client_base_filter(clinic_id, start, end))
        .group_by(day_expr)
        .all()
    )
    daily_raw = {int(d): int(c) for d, c in raw_rows}
    daily_flow = [
        {"day": d, "label": str(d), "count": daily_raw.get(d, 0)}
        for d in range(1, days_in_month + 1)
    ]
    average_per_day = round(overview["total_clients"] / days_in_month, 1) if days_in_month else 0.0

    return {
        **overview,
        "year": year,
        "month": month,
        "month_label": date(year, month, 1).strftime("%B"),
        "days_in_month": days_in_month,
        "average_per_day": average_per_day,
        "daily_flow": daily_flow,
    }


# --- Wave 2: appointments / check-ins / inquiry conversion -----------------

WEEKDAY_LABELS = {
    0: "Mon",
    1: "Tue",
    2: "Wed",
    3: "Thu",
    4: "Fri",
    5: "Sat",
    6: "Sun",
}

CONVERTED_STATUS_LIST = [
    "Under Rx",
    "Completed",
    "6m followup",
    "Yearly followup",
    "Ortho",
]


def _clamp_month_range(start_month: int, end_month: int) -> tuple[int, int]:
    start_month = max(1, min(12, start_month))
    end_month = max(1, min(12, end_month))
    if start_month > end_month:
        start_month, end_month = end_month, start_month
    return start_month, end_month


def _date_range_days(year: int, start_month: int, end_month: int) -> tuple[date, date]:
    start_month, end_month = _clamp_month_range(start_month, end_month)
    first = date(year, start_month, 1)
    last = date(year, end_month, calendar.monthrange(year, end_month)[1])
    return first, last


def _attendance_rate(completed: int, cancelled: int, no_show: int) -> tuple[int, int]:
    shown = completed + cancelled + no_show
    rate = int(round(completed / shown * 100)) if shown > 0 else 0
    return rate, shown


def _appt_status_counts(db: Session, clinic_id: int, first: date, last: date) -> dict[str, int]:
    row = (
        db.query(
            func.count(Appointment.appointment_id).label("total"),
            func.sum(case((Appointment.status == "Completed", 1), else_=0)).label("completed"),
            func.sum(case((Appointment.status == "Confirmed", 1), else_=0)).label("confirmed"),
            func.sum(case((Appointment.status == "Cancelled", 1), else_=0)).label("cancelled"),
            func.sum(case((Appointment.status == "No Show", 1), else_=0)).label("no_show"),
            func.sum(case((Appointment.status == "Pending", 1), else_=0)).label("pending"),
        )
        .filter(
            Appointment.clinic_id == clinic_id,
            Appointment.appointment_date >= first,
            Appointment.appointment_date <= last,
        )
        .one()
    )
    return {
        "total": int(row.total or 0),
        "completed": int(row.completed or 0),
        "confirmed": int(row.confirmed or 0),
        "cancelled": int(row.cancelled or 0),
        "no_show": int(row.no_show or 0),
        "pending": int(row.pending or 0),
    }


def _appt_doctor_breakdown(db: Session, clinic_id: int, first: date, last: date) -> list[dict[str, Any]]:
    rows = (
        db.query(
            Appointment.doctor_id,
            func.coalesce(AppointmentDoctor.doctor_name, "Unknown").label("doctor_name"),
            func.count(Appointment.appointment_id).label("total"),
            func.sum(case((Appointment.status == "Completed", 1), else_=0)).label("completed"),
            func.sum(case((Appointment.status == "Confirmed", 1), else_=0)).label("confirmed"),
            func.sum(case((Appointment.status == "Cancelled", 1), else_=0)).label("cancelled"),
            func.sum(case((Appointment.status == "No Show", 1), else_=0)).label("no_show"),
            func.sum(case((Appointment.status == "Pending", 1), else_=0)).label("pending"),
        )
        .outerjoin(AppointmentDoctor, AppointmentDoctor.doctor_id == Appointment.doctor_id)
        .filter(
            Appointment.clinic_id == clinic_id,
            Appointment.appointment_date >= first,
            Appointment.appointment_date <= last,
        )
        .group_by(Appointment.doctor_id, AppointmentDoctor.doctor_name)
        .order_by(func.count(Appointment.appointment_id).desc())
        .all()
    )
    out = []
    for r in rows:
        completed = int(r.completed or 0)
        cancelled = int(r.cancelled or 0)
        no_show = int(r.no_show or 0)
        rate, _ = _attendance_rate(completed, cancelled, no_show)
        out.append(
            {
                "doctor_id": int(r.doctor_id) if r.doctor_id is not None else None,
                "doctor_name": str(r.doctor_name or "Unknown"),
                "total": int(r.total or 0),
                "completed": completed,
                "confirmed": int(r.confirmed or 0),
                "cancelled": cancelled,
                "no_show": no_show,
                "pending": int(r.pending or 0),
                "attendance_rate": rate,
            }
        )
    return out


def _appt_no_shows(db: Session, clinic_id: int, first: date, last: date) -> list[dict[str, Any]]:
    rows = (
        db.query(Appointment, AppointmentDoctor, AppointmentService)
        .outerjoin(AppointmentDoctor, AppointmentDoctor.doctor_id == Appointment.doctor_id)
        .outerjoin(AppointmentService, AppointmentService.service_id == Appointment.service_id)
        .filter(
            Appointment.clinic_id == clinic_id,
            Appointment.status == "No Show",
            Appointment.appointment_date >= first,
            Appointment.appointment_date <= last,
        )
        .order_by(Appointment.appointment_date.asc(), Appointment.appointment_time.asc())
        .all()
    )
    out: list[dict[str, Any]] = []
    for appt, doctor, service in rows:
        re_booked = False
        later = db.query(Appointment.appointment_id).filter(
            Appointment.clinic_id == clinic_id,
            Appointment.appointment_date > appt.appointment_date,
            Appointment.status.notin_(["Cancelled", "No Show"]),
        )
        if appt.client_id:
            later = later.filter(Appointment.client_id == appt.client_id)
        elif appt.phone:
            later = later.filter(Appointment.phone == appt.phone)
        else:
            later = None
        if later is not None:
            re_booked = later.first() is not None

        t = appt.appointment_time
        time_str = t.strftime("%H:%M:%S") if t else ""
        out.append(
            {
                "appointment_id": appt.appointment_id,
                "name": appt.name or "",
                "phone": appt.phone or "",
                "client_id": appt.client_id,
                "appointment_date": appt.appointment_date.isoformat(),
                "appointment_time": time_str,
                "doctor_name": (doctor.doctor_name if doctor else "") or "",
                "service_name": (service.service_name if service else "") or "",
                "re_booked": re_booked,
            }
        )
    return out


def monthly_appointments(db: Session, clinic_id: int, year: int, month: int) -> dict[str, Any]:
    month = max(1, min(12, month))
    first = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])
    days_in_month = last.day
    counts = _appt_status_counts(db, clinic_id, first, last)
    attend_rate, shown = _attendance_rate(counts["completed"], counts["cancelled"], counts["no_show"])

    day_rows = (
        db.query(
            extract("day", Appointment.appointment_date).label("day_num"),
            func.count(Appointment.appointment_id),
        )
        .filter(
            Appointment.clinic_id == clinic_id,
            Appointment.appointment_date >= first,
            Appointment.appointment_date <= last,
        )
        .group_by(extract("day", Appointment.appointment_date))
        .all()
    )
    daily_raw = {int(d): int(c) for d, c in day_rows}
    daily_flow = [
        {"day": d, "label": str(d), "count": daily_raw.get(d, 0)}
        for d in range(1, days_in_month + 1)
    ]
    total_flow = sum(p["count"] for p in daily_flow)
    average_per_day = round(total_flow / days_in_month, 1) if days_in_month else 0.0

    no_shows = _appt_no_shows(db, clinic_id, first, last)
    rebooked_count = sum(1 for r in no_shows if r["re_booked"])

    return {
        "year": year,
        "month": month,
        "month_label": MONTH_LABELS[month],
        "days_in_month": days_in_month,
        **counts,
        "attendance_rate": attend_rate,
        "shown_count": shown,
        "average_per_day": average_per_day,
        "daily_flow": daily_flow,
        "doctors": _appt_doctor_breakdown(db, clinic_id, first, last),
        "no_shows": no_shows,
        "rebooked_count": rebooked_count,
        "rebook_rate": int(round(rebooked_count / counts["no_show"] * 100)) if counts["no_show"] else 0,
    }


def yearly_appointments(
    db: Session,
    clinic_id: int,
    year: int,
    start_month: int = 1,
    end_month: int = 12,
) -> dict[str, Any]:
    start_month, end_month = _clamp_month_range(start_month, end_month)
    first, last = _date_range_days(year, start_month, end_month)
    counts = _appt_status_counts(db, clinic_id, first, last)
    attend_rate, shown = _attendance_rate(counts["completed"], counts["cancelled"], counts["no_show"])

    month_rows = (
        db.query(
            extract("month", Appointment.appointment_date).label("month_num"),
            func.count(Appointment.appointment_id),
        )
        .filter(
            Appointment.clinic_id == clinic_id,
            Appointment.appointment_date >= first,
            Appointment.appointment_date <= last,
        )
        .group_by(extract("month", Appointment.appointment_date))
        .all()
    )
    monthly_raw = {int(m): int(c) for m, c in month_rows}
    monthly_flow = [
        {"month": m, "label": MONTH_LABELS[m], "count": monthly_raw.get(m, 0)}
        for m in range(start_month, end_month + 1)
    ]
    number_of_months = end_month - start_month + 1
    average_per_month = round(counts["total"] / number_of_months, 1) if number_of_months else 0.0

    no_shows = _appt_no_shows(db, clinic_id, first, last)
    rebooked_count = sum(1 for r in no_shows if r["re_booked"])

    return {
        "year": year,
        "start_month": start_month,
        "end_month": end_month,
        **counts,
        "attendance_rate": attend_rate,
        "shown_count": shown,
        "average_per_month": average_per_month,
        "monthly_flow": monthly_flow,
        "doctors": _appt_doctor_breakdown(db, clinic_id, first, last),
        "no_shows": no_shows,
        "rebooked_count": rebooked_count,
        "rebook_rate": int(round(rebooked_count / counts["no_show"] * 100)) if counts["no_show"] else 0,
    }


def _hour_label(hour: int) -> str:
    if hour == 0:
        return "12a"
    if hour < 12:
        return f"{hour}a"
    if hour == 12:
        return "12p"
    return f"{hour - 12}p"


def _checkin_base(clinic_id: int, start: datetime, end: datetime):
    return and_(
        ClientCheckinLog.clinic_id == clinic_id,
        ClientCheckinLog.action == "check_in",
        ClientCheckinLog.created_at >= start,
        ClientCheckinLog.created_at <= end,
    )


def _checkin_count(db: Session, clinic_id: int, start: datetime, end: datetime) -> int:
    return (
        db.query(func.count(ClientCheckinLog.id))
        .filter(_checkin_base(clinic_id, start, end))
        .scalar()
        or 0
    )


def _checkin_weekday_hour_flows(
    db: Session, clinic_id: int, start: datetime, end: datetime
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    local_ts = func.timezone("Asia/Kolkata", ClientCheckinLog.created_at)
    # MySQL WEEKDAY: Mon=0..Sun=6 → Postgres isodow Mon=1..Sun=7
    wd_expr = extract("isodow", local_ts) - 1
    hr_expr = extract("hour", local_ts)

    wd_rows = (
        db.query(wd_expr.label("wd"), func.count(ClientCheckinLog.id))
        .filter(_checkin_base(clinic_id, start, end))
        .group_by(wd_expr)
        .all()
    )
    wd_raw = {int(w): int(c) for w, c in wd_rows}
    weekday_flow = [
        {"weekday": wd, "label": WEEKDAY_LABELS[wd], "count": wd_raw.get(wd, 0)}
        for wd in range(0, 7)
    ]

    hr_rows = (
        db.query(hr_expr.label("hr"), func.count(ClientCheckinLog.id))
        .filter(_checkin_base(clinic_id, start, end))
        .group_by(hr_expr)
        .all()
    )
    hr_raw = {int(h): int(c) for h, c in hr_rows}
    hour_flow = [
        {"hour": h, "label": _hour_label(h), "count": hr_raw.get(h, 0)}
        for h in range(0, 24)
    ]

    busiest_weekday = None
    max_wd = 0
    for row in weekday_flow:
        if row["count"] > max_wd:
            max_wd = row["count"]
            busiest_weekday = row["label"]
    if max_wd == 0:
        busiest_weekday = None

    busiest_hour = None
    busiest_hour_label = None
    max_hr = 0
    for row in hour_flow:
        if row["count"] > max_hr:
            max_hr = row["count"]
            busiest_hour = row["hour"]
            busiest_hour_label = row["label"]
    if max_hr == 0:
        busiest_hour = None
        busiest_hour_label = None

    return weekday_flow, hour_flow, {
        "busiest_weekday": busiest_weekday,
        "busiest_hour": busiest_hour,
        "busiest_hour_label": busiest_hour_label,
    }


def monthly_checkins(db: Session, clinic_id: int, year: int, month: int) -> dict[str, Any]:
    month = max(1, min(12, month))
    start, end = _month_bounds(year, month)
    days_in_month = calendar.monthrange(year, month)[1]
    year_start, _ = _ist_day_bounds(date(year, 1, 1))
    _, year_end = _ist_day_bounds(date(year, 12, 31))
    days_in_year = 366 if calendar.isleap(year) else 365

    month_total = int(_checkin_count(db, clinic_id, start, end))
    year_total = int(_checkin_count(db, clinic_id, year_start, year_end))

    local_ts = func.timezone("Asia/Kolkata", ClientCheckinLog.created_at)
    day_expr = extract("day", local_ts)
    day_rows = (
        db.query(day_expr.label("day_num"), func.count(ClientCheckinLog.id))
        .filter(_checkin_base(clinic_id, start, end))
        .group_by(day_expr)
        .all()
    )
    daily_raw = {int(d): int(c) for d, c in day_rows}
    daily_flow = [
        {"day": d, "label": str(d), "count": daily_raw.get(d, 0)}
        for d in range(1, days_in_month + 1)
    ]
    weekday_flow, hour_flow, busiest = _checkin_weekday_hour_flows(db, clinic_id, start, end)

    return {
        "year": year,
        "month": month,
        "month_label": MONTH_LABELS[month],
        "days_in_month": days_in_month,
        "month_total": month_total,
        "average_per_day": round(month_total / days_in_month, 1) if days_in_month else 0.0,
        "year_total": year_total,
        "year_average_per_day": round(year_total / days_in_year, 1) if days_in_year else 0.0,
        "days_in_year": days_in_year,
        "daily_flow": daily_flow,
        "weekday_flow": weekday_flow,
        "hour_flow": hour_flow,
        **busiest,
    }


def yearly_checkins(
    db: Session,
    clinic_id: int,
    year: int,
    start_month: int = 1,
    end_month: int = 12,
) -> dict[str, Any]:
    start_month, end_month = _clamp_month_range(start_month, end_month)
    first, last = _date_range_days(year, start_month, end_month)
    start, _ = _ist_day_bounds(first)
    _, end = _ist_day_bounds(last)
    days_in_range = (last - first).days + 1

    total = int(_checkin_count(db, clinic_id, start, end))
    local_ts = func.timezone("Asia/Kolkata", ClientCheckinLog.created_at)
    month_expr = extract("month", local_ts)
    month_rows = (
        db.query(month_expr.label("month_num"), func.count(ClientCheckinLog.id))
        .filter(_checkin_base(clinic_id, start, end))
        .group_by(month_expr)
        .all()
    )
    monthly_raw = {int(m): int(c) for m, c in month_rows}
    monthly_flow = [
        {"month": m, "label": MONTH_LABELS[m], "count": monthly_raw.get(m, 0)}
        for m in range(start_month, end_month + 1)
    ]
    months_in_range = end_month - start_month + 1
    weekday_flow, hour_flow, busiest = _checkin_weekday_hour_flows(db, clinic_id, start, end)

    return {
        "year": year,
        "start_month": start_month,
        "end_month": end_month,
        "total": total,
        "average_per_month": round(total / months_in_range, 1) if months_in_range else 0.0,
        "average_per_day": round(total / days_in_range, 1) if days_in_range else 0.0,
        "days_in_range": days_in_range,
        "monthly_flow": monthly_flow,
        "weekday_flow": weekday_flow,
        "hour_flow": hour_flow,
        **busiest,
    }


def _inquiry_range_overview(
    db: Session,
    clinic_id: int,
    from_date: date,
    to_date: date,
    extra: dict[str, Any],
) -> dict[str, Any]:
    start, _ = _ist_day_bounds(from_date)
    _, end = _ist_day_bounds(to_date)
    local_created = func.timezone("Asia/Kolkata", Client.created_at)
    month_key = func.to_char(local_created, "YYYY-MM")

    inquiry_case = case((Client.status == "Inquiry", 1), else_=0)
    conversion_case = case((Client.status.in_(CONVERTED_STATUS_LIST), 1), else_=0)

    rows = (
        db.query(
            month_key.label("month_key"),
            extract("year", local_created).label("year_val"),
            extract("month", local_created).label("month_val"),
            func.sum(inquiry_case).label("inquiry_count"),
            func.sum(conversion_case).label("conversion_count"),
        )
        .filter(
            Client.clinic_id == clinic_id,
            Client.visible.is_(True),
            Client.status != "DND",
            Client.created_at >= start,
            Client.created_at <= end,
        )
        .group_by(month_key, extract("year", local_created), extract("month", local_created))
        .order_by(extract("year", local_created), extract("month", local_created))
        .all()
    )
    raw_by_key = {
        str(r.month_key): {
            "inquiry_count": int(r.inquiry_count or 0),
            "conversion_count": int(r.conversion_count or 0),
        }
        for r in rows
    }

    monthly_flow: list[dict[str, Any]] = []
    cursor = date(from_date.year, from_date.month, 1)
    end_month = date(to_date.year, to_date.month, 1)
    while cursor <= end_month:
        key = f"{cursor.year:04d}-{cursor.month:02d}"
        inquiry = int(raw_by_key.get(key, {}).get("inquiry_count", 0))
        conversion = int(raw_by_key.get(key, {}).get("conversion_count", 0))
        total = inquiry + conversion
        pct = round(conversion / total * 100, 2) if total else 0.0
        monthly_flow.append(
            {
                "month_key": key,
                "year": cursor.year,
                "month": cursor.month,
                "label": f"{MONTH_LABELS[cursor.month]} {cursor.year}",
                "inquiry_count": inquiry,
                "conversion_count": conversion,
                "total_clients": total,
                "conversion_pct": pct,
            }
        )
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)

    total_inquiry = sum(r["inquiry_count"] for r in monthly_flow)
    total_conversion = sum(r["conversion_count"] for r in monthly_flow)
    total_clients = total_inquiry + total_conversion
    avg_pct = round(total_conversion / total_clients * 100, 2) if total_clients else 0.0

    return {
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "date_range_label": (
            f"{from_date.strftime('%b')} {from_date.day}, {from_date.year}"
            f" – {to_date.strftime('%b')} {to_date.day}, {to_date.year}"
        ),
        "total_clients": total_clients,
        "total_inquiry": total_inquiry,
        "total_conversion": total_conversion,
        "avg_conversion_pct": avg_pct,
        "monthly_flow": monthly_flow,
        "conversion_statuses": list(CONVERTED_STATUS_LIST),
        **extra,
    }


def yearly_inquiry_conversion(db: Session, clinic_id: int, year: int) -> dict[str, Any]:
    return _inquiry_range_overview(
        db,
        clinic_id,
        date(year, 1, 1),
        date(year, 12, 31),
        {"year": year, "mode": "yearly"},
    )


def monthly_inquiry_conversion(db: Session, clinic_id: int, year: int, month: int) -> dict[str, Any]:
    month = max(1, min(12, month))
    first = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])
    return _inquiry_range_overview(
        db,
        clinic_id,
        first,
        last,
        {
            "year": year,
            "month": month,
            "month_label": MONTH_LABELS[month],
            "mode": "monthly",
        },
    )
