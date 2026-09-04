"""
Import one clinic from legacy MySQL into Postgres (Go 4 pilot).

Requires env (never commit secrets):
  MYSQL_HOST MYSQL_USER MYSQL_PASSWORD MYSQL_DATABASE
  DATABASE_URL  (Postgres)

Example:
  export MYSQL_HOST=db.pratikp.com
  export MYSQL_USER=...
  export MYSQL_PASSWORD=...
  export MYSQL_DATABASE=prctc_mngmt_pt
  python scripts/import_mysql.py --clinic-id 1 --replace
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pymysql
from sqlalchemy import text

from app.auth import hash_password
from app.db import Base, SessionLocal, engine
from app.models import (
    Appointment,
    AppointmentDoctor,
    AppointmentService,
    AppointmentStatus,
    Bill,
    Client,
    ClientCheckinLog,
    Clinic,
    ClinicSetting,
    DentalLab,
    DoctorSchedule,
    LabCase,
    LabCaseCycle,
    MedicineTemplate,
    MoneyReceipt,
    Note,
    NoteAttachment,
    Prescription,
    PrescriptionItem,
    Task,
    User,
)

DAY_MAP = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def _mysql():
    missing = [k for k in ("MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE") if not os.getenv(k)]
    if missing:
        raise SystemExit(f"Missing env: {', '.join(missing)}")
    # Hostinger / managed MySQL often requires TLS
    ssl_mode = os.getenv("MYSQL_SSL", "1")
    connect_kwargs = dict(
        host=os.environ["MYSQL_HOST"],
        user=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        database=os.environ["MYSQL_DATABASE"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=30,
        read_timeout=600,
        write_timeout=600,
    )
    if ssl_mode not in {"0", "false", "False"}:
        connect_kwargs["ssl"] = {"check_hostname": False}
    return pymysql.connect(**connect_kwargs)


def _norm_hash(h: str | None) -> str:
    if not h:
        return hash_password("ChangeMe123!")
    if h.startswith("$2y$"):
        return "$2b$" + h[4:]
    return h


def _as_bool(v) -> bool:
    return bool(int(v)) if v is not None else True


def _as_time(v) -> time | None:
    if v is None:
        return None
    if isinstance(v, timedelta):
        total = int(v.total_seconds())
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        return time(h % 24, m, s)
    if isinstance(v, time):
        return v
    if isinstance(v, datetime):
        return v.time()
    if isinstance(v, str) and v:
        parts = v.split(":")
        return time(int(parts[0]), int(parts[1]), int(float(parts[2])) if len(parts) > 2 else 0)
    return None


def _reset_sequences(db) -> None:
    tables = [
        ("clinics", "clinic_id"),
        ("users", "user_id"),
        ("clients", "client_id"),
        ("notes", "note_id"),
        ("note_attachments", "id"),
        ("client_checkin_logs", "id"),
        ("clinic_settings", "id"),
        ("appointments_doctors", "doctor_id"),
        ("appointments_services", "service_id"),
        ("appointments_statuses", "status_id"),
        ("appointments_doctor_schedules", "schedule_id"),
        ("appointments", "appointment_id"),
        ("bills", "bill_id"),
        ("money_receipts", "receipt_id"),
        ("medicine_templates", "medicine_id"),
        ("prescriptions", "prescription_id"),
        ("prescription_items", "item_id"),
        ("tasks", "task_id"),
        ("dental_labs", "lab_id"),
        ("lab_cases", "case_id"),
        ("lab_case_cycles", "cycle_id"),
    ]
    for table, col in tables:
        db.execute(
            text(
                f"SELECT setval(pg_get_serial_sequence('{table}', '{col}'), "
                f"COALESCE((SELECT MAX({col}) FROM {table}), 1))"
            )
        )


def _wipe_clinic(db, clinic_id: int) -> None:
    # FK-safe order
    case_ids = [
        r[0]
        for r in db.query(LabCase.case_id).filter(LabCase.clinic_id == clinic_id).all()
    ]
    if case_ids:
        db.query(LabCaseCycle).filter(LabCaseCycle.case_id.in_(case_ids)).delete(synchronize_session=False)
    tables = [
        LabCase,
        DentalLab,
        PrescriptionItem,
        Prescription,
        MoneyReceipt,
        Bill,
        NoteAttachment,
        Note,
        ClientCheckinLog,
        Appointment,
        DoctorSchedule,
        AppointmentDoctor,
        AppointmentService,
        AppointmentStatus,
        MedicineTemplate,
        Task,
        ClinicSetting,
        Client,
        User,
        Clinic,
    ]
    for model in tables:
        if model is Clinic:
            db.query(model).filter(model.clinic_id == clinic_id).delete(synchronize_session=False)
        elif hasattr(model, "clinic_id"):
            db.query(model).filter(model.clinic_id == clinic_id).delete(synchronize_session=False)
    db.flush()


def import_clinic(*, clinic_id: int, replace: bool, dry_run: bool, keep_admin: bool) -> None:
    Base.metadata.create_all(bind=engine)
    src = _mysql()
    db = SessionLocal()
    stats: dict[str, int] = {}

    try:
        with src.cursor() as cur:
            cur.execute("SELECT * FROM clinics WHERE clinic_id=%s", (clinic_id,))
            clinic_row = cur.fetchone()
            if not clinic_row:
                raise SystemExit(f"Clinic {clinic_id} not found in MySQL")

            if dry_run:
                print(f"[dry-run] Would import clinic {clinic_id}: {clinic_row['clinic_name']}")
            else:
                if replace:
                    print(f"Wiping Postgres clinic_id={clinic_id} …")
                    _wipe_clinic(db, clinic_id)
                    db.commit()
                    db.expire_all()
                db.add(
                    Clinic(
                        clinic_id=clinic_row["clinic_id"],
                        clinic_name=clinic_row["clinic_name"],
                        clinic_address=clinic_row.get("clinic_address"),
                        clinic_phone=clinic_row.get("clinic_phone"),
                        clinic_email=clinic_row.get("clinic_email"),
                        is_active=_as_bool(clinic_row.get("is_active", 1)),
                        created_at=clinic_row.get("created_at") or datetime.now(timezone.utc),
                    )
                )
                db.flush()
                stats["clinics"] = 1

            # Per-clinic WhatsApp / feature flags (wa_enabled, wa_api_key, …)
            wa_keys = (
                "wa_enabled",
                "wa_api_key",
                "wa_api_url",
                "wa_inbox_enabled",
                "wa_inbox_api_url",
            )
            cur.execute(
                f"SELECT setting_key, setting_value FROM clinic_settings "
                f"WHERE clinic_id=%s AND setting_key IN ({','.join(['%s'] * len(wa_keys))})",
                (clinic_id, *wa_keys),
            )
            setting_rows = cur.fetchall()
            stats["clinic_settings"] = len(setting_rows)
            if not dry_run:
                for s in setting_rows:
                    existing = (
                        db.query(ClinicSetting)
                        .filter(
                            ClinicSetting.clinic_id == clinic_id,
                            ClinicSetting.setting_key == s["setting_key"],
                        )
                        .first()
                    )
                    if existing:
                        existing.setting_value = s.get("setting_value")
                    else:
                        db.add(
                            ClinicSetting(
                                clinic_id=clinic_id,
                                setting_key=s["setting_key"],
                                setting_value=s.get("setting_value"),
                            )
                        )
                db.flush()

            cur.execute("SELECT * FROM users WHERE clinic_id=%s", (clinic_id,))
            users = cur.fetchall()
            stats["users"] = len(users)
            if not dry_run:
                for u in users:
                    db.merge(
                        User(
                            user_id=u["user_id"],
                            clinic_id=clinic_id,
                            username=(u.get("username") or f"user{u['user_id']}").strip(),
                            email=u.get("email"),
                            password_hash=_norm_hash(u.get("password_hash")),
                            full_name=(u.get("full_name") or u.get("username") or f"User {u['user_id']}").strip(),
                            role=(u.get("role") or "staff").strip().lower(),
                            active=_as_bool(u.get("active", 1)),
                            profile_photo_url=u.get("profile_photo_url"),
                            created_at=u.get("created_at") or datetime.now(timezone.utc),
                            last_login=u.get("last_login"),
                        )
                    )
                db.flush()

            cur.execute("SELECT * FROM appointments_statuses WHERE clinic_id=%s", (clinic_id,))
            statuses = cur.fetchall()
            stats["statuses"] = len(statuses)
            if not dry_run:
                for s in statuses:
                    db.merge(
                        AppointmentStatus(
                            status_id=s["status_id"],
                            clinic_id=clinic_id,
                            status_name=s["status_name"],
                            color=s.get("color") or "neutral",
                            is_system=_as_bool(s.get("is_system", 1)),
                            is_active=_as_bool(s.get("is_active", 1)),
                        )
                    )

            cur.execute(
                """
                SELECT d.*, u.full_name AS user_full_name
                FROM appointments_doctors d
                LEFT JOIN users u ON u.user_id = d.user_id
                WHERE d.clinic_id=%s
                """,
                (clinic_id,),
            )
            doctors = cur.fetchall()
            stats["doctors"] = len(doctors)
            doctor_ids = [d["doctor_id"] for d in doctors]
            if not dry_run:
                for d in doctors:
                    db.merge(
                        AppointmentDoctor(
                            doctor_id=d["doctor_id"],
                            clinic_id=clinic_id,
                            user_id=d.get("user_id"),
                            doctor_name=(d.get("user_full_name") or f"Doctor {d['doctor_id']}").strip(),
                            specialization=d.get("specialization"),
                            color_code=d.get("color_code") or "#0f766e",
                            is_active=_as_bool(d.get("is_active", 1)),
                        )
                    )

            cur.execute("SELECT * FROM appointments_services WHERE clinic_id=%s", (clinic_id,))
            services = cur.fetchall()
            stats["services"] = len(services)
            if not dry_run:
                for s in services:
                    db.merge(
                        AppointmentService(
                            service_id=s["service_id"],
                            clinic_id=clinic_id,
                            service_name=s["service_name"],
                            duration_minutes=int(s.get("duration_minutes") or 30),
                            description=s.get("description"),
                            is_active=_as_bool(s.get("is_active", 1)),
                        )
                    )
                db.flush()

                format_ids = ",".join(["%s"] * len(doctor_ids))
                cur.execute(
                    f"SELECT * FROM appointments_doctor_schedules WHERE doctor_id IN ({format_ids})",
                    doctor_ids,
                )
                schedules = cur.fetchall()
            else:
                schedules = []
            stats["schedules"] = len(schedules)
            if not dry_run:
                for s in schedules:
                    weekday = DAY_MAP.get(str(s.get("day_name") or "").lower())
                    if weekday is None:
                        continue
                    start_t = _as_time(s.get("start_time")) or time(10, 0)
                    end_t = _as_time(s.get("end_time")) or time(19, 0)
                    db.merge(
                        DoctorSchedule(
                            schedule_id=s["schedule_id"],
                            clinic_id=clinic_id,
                            doctor_id=s["doctor_id"],
                            weekday=weekday,
                            is_working=_as_bool(s.get("is_working", 1)),
                            start_time=start_t,
                            end_time=end_t,
                        )
                    )

            cur.execute("SELECT * FROM medicine_templates WHERE clinic_id=%s", (clinic_id,))
            meds = cur.fetchall()
            stats["medicines"] = len(meds)
            medicine_ids: set[int] = set()
            if not dry_run:
                for m in meds:
                    medicine_ids.add(m["medicine_id"])
                    db.merge(
                        MedicineTemplate(
                            medicine_id=m["medicine_id"],
                            clinic_id=clinic_id,
                            medicine_name=m["medicine_name"],
                            strength=m.get("strength"),
                            default_quantity=m.get("default_quantity"),
                            default_dosage=m.get("default_dosage"),
                            default_days=m.get("default_days"),
                            default_instructions=m.get("default_instructions"),
                            visible=_as_bool(m.get("visible", 1)),
                        )
                    )
                db.flush()

            cur.execute("SELECT * FROM clients WHERE clinic_id=%s", (clinic_id,))
            clients = cur.fetchall()
            stats["clients"] = len(clients)
            client_ids = [c["client_id"] for c in clients]
            if not dry_run:
                for c in clients:
                    db.merge(
                        Client(
                            client_id=c["client_id"],
                            clinic_id=clinic_id,
                            name=(c.get("name") or "Unknown").strip(),
                            calling_name=c.get("calling_name"),
                            number=c.get("number"),
                            country_code=c.get("country_code") or 91,
                            place=c.get("place"),
                            age=c.get("age"),
                            gender=c.get("gender"),
                            date_of_birth=c.get("date_of_birth"),
                            status=c.get("status") or "Inquiry",
                            lead_source=c.get("lead_source"),
                            reference=c.get("reference"),
                            client_personal_note=c.get("client_personal_note"),
                            check_in_status=_as_bool(c.get("check_in_status", 0)),
                            checked_in_at=c.get("checked_in_at"),
                            visible=_as_bool(c.get("visible", 1)),
                            profile_photo_url=c.get("profile_photo_url"),
                            created_by=c.get("user_id"),
                            created_at=c.get("created_at") or datetime.now(timezone.utc),
                            updated_at=c.get("updated_at") or c.get("created_at") or datetime.now(timezone.utc),
                        )
                    )
                db.flush()

            if client_ids:
                # chunk notes/bills/etc by client list size — MySQL IN can be large; 2197 is fine
                format_ids = ",".join(["%s"] * len(client_ids))

                cur.execute(
                    f"SELECT * FROM notes WHERE client_id IN ({format_ids}) AND IFNULL(visible,1)=1",
                    client_ids,
                )
                notes = cur.fetchall()
                stats["notes"] = len(notes)
                imported_note_ids: list[int] = []
                for n in notes:
                    body = (n.get("note_text") or "").strip()
                    legacy_attach = (n.get("attachment_url") or "").strip() or None
                    if not body and not legacy_attach:
                        continue
                    imported_note_ids.append(n["note_id"])
                    if not dry_run:
                        db.merge(
                            Note(
                                note_id=n["note_id"],
                                clinic_id=clinic_id,
                                client_id=n["client_id"],
                                user_id=n.get("user_id"),
                                body=body or "",
                                attachment_url=legacy_attach,
                                visible=True,
                                created_at=n.get("created_at") or datetime.now(timezone.utc),
                                updated_at=n.get("created_at") or datetime.now(timezone.utc),
                            )
                        )
                if not dry_run:
                    db.flush()

                # note_attachments keys only (files stay in S3)
                if imported_note_ids:
                    note_ph = ",".join(["%s"] * len(imported_note_ids))
                    cur.execute(
                        f"SELECT id, note_id, attachment_url FROM note_attachments "
                        f"WHERE note_id IN ({note_ph})",
                        imported_note_ids,
                    )
                    attach_rows = cur.fetchall()
                else:
                    attach_rows = []
                stats["note_attachments"] = len(attach_rows)
                if not dry_run:
                    for a in attach_rows:
                        url = (a.get("attachment_url") or "").strip()
                        if not url:
                            continue
                        db.merge(
                            NoteAttachment(
                                id=a["id"],
                                note_id=a["note_id"],
                                clinic_id=clinic_id,
                                attachment_url=url,
                            )
                        )

                cur.execute(
                    f"SELECT * FROM bills WHERE client_id IN ({format_ids})",
                    client_ids,
                )
                bills = cur.fetchall()
                stats["bills"] = len(bills)
                bill_ids: set[int] = set()
                if not dry_run:
                    for b in bills:
                        st = str(b.get("status") or "open").lower()
                        status = "paid" if st == "paid" else "open"
                        bill_ids.add(b["bill_id"])
                        db.merge(
                            Bill(
                                bill_id=b["bill_id"],
                                clinic_id=clinic_id,
                                client_id=b["client_id"],
                                amount_due=Decimal(str(b.get("amount_due") or 0)),
                                status=status,
                                description=None,
                                user_id=b.get("user_id"),
                                issued_at=b.get("issued_at") or datetime.now(timezone.utc),
                                visible=True,
                            )
                        )
                    db.flush()

                cur.execute(
                    f"SELECT * FROM money_receipts WHERE client_id IN ({format_ids}) AND IFNULL(visible,1)=1",
                    client_ids,
                )
                receipts = cur.fetchall()
                stats["receipts"] = len(receipts)
                if not dry_run:
                    for r in receipts:
                        received = r.get("received_date") or r.get("receipt_date") or datetime.now(timezone.utc)
                        raw_bill = r.get("bill_id")
                        bill_id = int(raw_bill) if raw_bill not in (None, 0, "0") else None
                        if bill_id is not None and bill_id not in bill_ids:
                            bill_id = None
                        db.merge(
                            MoneyReceipt(
                                receipt_id=r["receipt_id"],
                                clinic_id=clinic_id,
                                client_id=r["client_id"],
                                bill_id=bill_id,
                                amount=Decimal(str(r.get("amount") or 0)),
                                payment_mode=r.get("payment_mode") or "Cash",
                                description=r.get("description"),
                                user_id=r.get("user_id"),
                                received_at=received,
                                visible=True,
                            )
                        )
                    db.flush()

                cur.execute(
                    f"SELECT * FROM prescriptions WHERE client_id IN ({format_ids}) AND IFNULL(visible,1)=1",
                    client_ids,
                )
                rxs = cur.fetchall()
                stats["prescriptions"] = len(rxs)
                rx_ids = [p["prescription_id"] for p in rxs]
                if not dry_run:
                    for p in rxs:
                        db.merge(
                            Prescription(
                                prescription_id=p["prescription_id"],
                                clinic_id=clinic_id,
                                client_id=p["client_id"],
                                prescription_date=p.get("prescription_date") or date.today(),
                                notes=p.get("notes"),
                                user_id=p.get("user_id"),
                                visible=True,
                                created_at=p.get("created_at") or datetime.now(timezone.utc),
                                updated_at=p.get("updated_at") or datetime.now(timezone.utc),
                            )
                        )

                if rx_ids:
                    fmt = ",".join(["%s"] * len(rx_ids))
                    cur.execute(f"SELECT * FROM prescription_items WHERE prescription_id IN ({fmt})", rx_ids)
                    items = cur.fetchall()
                else:
                    items = []
                stats["prescription_items"] = len(items)
                if not dry_run:
                    for i in items:
                        name = (i.get("medicine_name") or "").strip() or "Medicine"
                        mid = i.get("medicine_id")
                        if mid not in medicine_ids:
                            mid = None
                        db.merge(
                            PrescriptionItem(
                                item_id=i["item_id"],
                                clinic_id=clinic_id,
                                prescription_id=i["prescription_id"],
                                medicine_id=mid,
                                medicine_name=name,
                                quantity=i.get("quantity"),
                                dosage=i.get("dosage"),
                                days=i.get("days"),
                                instructions=i.get("instructions"),
                            )
                        )
                    db.flush()

            cur.execute("SELECT * FROM appointments WHERE clinic_id=%s", (clinic_id,))
            appts = cur.fetchall()
            stats["appointments"] = len(appts)
            if not dry_run:
                for a in appts:
                    start_t = _as_time(a.get("appointment_time")) or time(10, 0)
                    end_t = _as_time(a.get("end_time"))
                    db.merge(
                        Appointment(
                            appointment_id=a["appointment_id"],
                            clinic_id=clinic_id,
                            client_id=a.get("client_id"),
                            doctor_id=a["doctor_id"],
                            service_id=a.get("service_id"),
                            name=(a.get("name") or "Patient").strip(),
                            phone=a.get("phone"),
                            appointment_date=a["appointment_date"],
                            appointment_time=start_t,
                            end_time=end_t,
                            status=a.get("status") or "Confirmed",
                            notes=a.get("notes"),
                            created_by=a.get("created_by"),
                            created_at=a.get("created_at") or datetime.now(timezone.utc),
                            updated_at=a.get("updated_at") or datetime.now(timezone.utc),
                        )
                    )

            cur.execute(
                "SELECT * FROM tasks WHERE clinic_id=%s AND IFNULL(visible,1)=1",
                (clinic_id,),
            )
            tasks = cur.fetchall()
            stats["tasks"] = len(tasks)
            if not dry_run:
                for t in tasks:
                    st = t.get("status") or "Open"
                    if st not in {"Open", "Completed", "Cancelled"}:
                        st = "Completed" if str(st).lower() == "completed" else "Open"
                    db.merge(
                        Task(
                            task_id=t["task_id"],
                            clinic_id=clinic_id,
                            client_id=t.get("client_id"),
                            task_description=(t.get("task_description") or "Task").strip(),
                            due_date=t.get("due_date"),
                            status=st,
                            created_by=t.get("created_by"),
                            assignee_id=None,
                            completed_at=t.get("completed_at"),
                            visible=True,
                            created_at=t.get("created_at") or datetime.now(timezone.utc),
                        )
                    )

                # task assignments → first assignee
                if tasks:
                    task_ids = [t["task_id"] for t in tasks]
                    fmt = ",".join(["%s"] * len(task_ids))
                    cur.execute(
                        f"SELECT task_id, user_id FROM task_assignments WHERE task_id IN ({fmt}) ORDER BY assigned_at",
                        task_ids,
                    )
                    for row in cur.fetchall():
                        task = db.get(Task, row["task_id"])
                        if task and task.assignee_id is None:
                            task.assignee_id = row["user_id"]

            # Dental labs + cases + cycles
            try:
                cur.execute(
                    "SELECT * FROM dental_labs WHERE clinic_id=%s ORDER BY lab_id",
                    (clinic_id,),
                )
                labs = cur.fetchall()
            except Exception:
                labs = []
            stats["dental_labs"] = len(labs)
            if not dry_run:
                for lab in labs:
                    db.add(
                        DentalLab(
                            lab_id=lab["lab_id"],
                            clinic_id=clinic_id,
                            name=lab["name"],
                            contact_person=lab.get("contact_person"),
                            phone=lab.get("phone"),
                            notes=lab.get("notes"),
                            visible=_as_bool(lab.get("visible", 1)),
                            created_by=lab.get("created_by"),
                            created_at=lab.get("created_at") or datetime.now(timezone.utc),
                            updated_at=lab.get("updated_at"),
                        )
                    )
                db.flush()

            try:
                cur.execute(
                    "SELECT * FROM lab_cases WHERE clinic_id=%s ORDER BY case_id",
                    (clinic_id,),
                )
                cases = cur.fetchall()
            except Exception:
                cases = []
            stats["lab_cases"] = len(cases)
            if not dry_run:
                for lc in cases:
                    db.add(
                        LabCase(
                            case_id=lc["case_id"],
                            clinic_id=clinic_id,
                            client_id=lc["client_id"],
                            lab_id=lc["lab_id"],
                            case_ref=lc["case_ref"],
                            case_type=lc.get("case_type"),
                            tooth_numbers=lc.get("tooth_numbers"),
                            description=lc.get("description"),
                            current_cycle_number=int(lc.get("current_cycle_number") or 1),
                            status=lc.get("status") or "open",
                            created_by=lc.get("created_by"),
                            closed_at=lc.get("closed_at"),
                            closed_by=lc.get("closed_by"),
                            visible=_as_bool(lc.get("visible", 1)),
                            created_at=lc.get("created_at") or datetime.now(timezone.utc),
                            updated_at=lc.get("updated_at"),
                        )
                    )
                db.flush()

            try:
                if cases:
                    case_ids = [c["case_id"] for c in cases]
                    fmt = ",".join(["%s"] * len(case_ids))
                    cur.execute(
                        f"SELECT * FROM lab_case_cycles WHERE case_id IN ({fmt}) ORDER BY cycle_id",
                        case_ids,
                    )
                    cycles = cur.fetchall()
                else:
                    cycles = []
            except Exception:
                cycles = []
            stats["lab_case_cycles"] = len(cycles)
            if not dry_run:
                for cy in cycles:
                    db.add(
                        LabCaseCycle(
                            cycle_id=cy["cycle_id"],
                            case_id=cy["case_id"],
                            cycle_number=int(cy["cycle_number"]),
                            send_pending_at=cy.get("send_pending_at"),
                            send_pending_by=cy.get("send_pending_by"),
                            sent_at=cy.get("sent_at"),
                            sent_by=cy.get("sent_by"),
                            receive_pending_at=cy.get("receive_pending_at"),
                            receive_pending_by=cy.get("receive_pending_by"),
                            received_at=cy.get("received_at"),
                            received_by=cy.get("received_by"),
                            expected_return_date=cy.get("expected_return_date"),
                            notes=cy.get("notes"),
                            created_at=cy.get("created_at") or datetime.now(timezone.utc),
                            updated_at=cy.get("updated_at"),
                        )
                    )

            # check-in logs (optional / lighter mapping)
            cur.execute(
                "SELECT * FROM client_checkin_logs WHERE clinic_id=%s ORDER BY log_id",
                (clinic_id,),
            )
            logs = cur.fetchall()
            stats["checkin_logs"] = len(logs)
            if not dry_run:
                for log in logs:
                    if log.get("checked_in_at"):
                        db.add(
                            ClientCheckinLog(
                                clinic_id=clinic_id,
                                client_id=log["client_id"],
                                user_id=log.get("user_id"),
                                action="check_in",
                                created_at=log.get("checked_in_at") or log.get("created_at") or datetime.now(timezone.utc),
                            )
                        )
                    if log.get("checked_out_at"):
                        db.add(
                            ClientCheckinLog(
                                clinic_id=clinic_id,
                                client_id=log["client_id"],
                                user_id=log.get("user_id"),
                                action="check_out",
                                created_at=log.get("checked_out_at") or log.get("created_at") or datetime.now(timezone.utc),
                            )
                        )

            if not dry_run and keep_admin:
                existing = (
                    db.query(User)
                    .filter(User.clinic_id == clinic_id, User.username == "admin")
                    .first()
                )
                if not existing:
                    # allocate high id to avoid collisions
                    max_id = db.execute(text("SELECT COALESCE(MAX(user_id), 0) FROM users")).scalar() or 0
                    db.add(
                        User(
                            user_id=int(max_id) + 1,
                            clinic_id=clinic_id,
                            username="admin",
                            email="admin@local",
                            password_hash=hash_password("admin123"),
                            full_name="Break-glass Admin",
                            role="admin",
                            active=True,
                        )
                    )
                    stats["breakglass_admin"] = 1

            if not dry_run:
                db.commit()
                _reset_sequences(db)
                db.commit()
                # indexes
                sql = Path(__file__).with_name("apply_indexes.sql").read_text(encoding="utf-8")
                db.execute(text(sql))
                db.commit()

        print("Import complete" if not dry_run else "Dry-run counts")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        if not dry_run and keep_admin:
            print("  Break-glass login: admin / admin123")
        print("  Staff logins: use existing MySQL usernames + passwords")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        src.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import MySQL clinic → Postgres")
    parser.add_argument("--clinic-id", type=int, default=1)
    parser.add_argument("--replace", action="store_true", help="Wipe target clinic_id in Postgres first")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--keep-admin", action="store_true", default=True, help="Ensure local admin/admin123 exists")
    parser.add_argument("--no-keep-admin", action="store_false", dest="keep_admin")
    args = parser.parse_args()
    import_clinic(
        clinic_id=args.clinic_id,
        replace=args.replace,
        dry_run=args.dry_run,
        keep_admin=args.keep_admin,
    )


if __name__ == "__main__":
    main()
