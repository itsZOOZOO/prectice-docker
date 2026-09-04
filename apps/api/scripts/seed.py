"""Seed Go 1–2 demo clinic, patients, doctors, services, appointments."""

from __future__ import annotations

import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.auth import hash_password
from app.db import Base, SessionLocal, engine
from app.models import (
    Appointment,
    AppointmentDoctor,
    AppointmentService,
    AppointmentStatus,
    Bill,
    Client,
    Clinic,
    DoctorSchedule,
    MedicineTemplate,
    MoneyReceipt,
    Note,
    Prescription,
    PrescriptionItem,
    Task,
    User,
)

IST = ZoneInfo("Asia/Kolkata")
DEFAULT_STATUSES = [
    ("Confirmed", "success"),
    ("Pending", "warning"),
    ("Completed", "neutral"),
    ("Cancelled", "error"),
    ("No Show", "warning"),
]


def _ensure_statuses(db, clinic_id: int) -> None:
    existing = {
        s.status_name
        for s in db.query(AppointmentStatus).filter(AppointmentStatus.clinic_id == clinic_id).all()
    }
    for name, color in DEFAULT_STATUSES:
        if name not in existing:
            db.add(
                AppointmentStatus(
                    clinic_id=clinic_id,
                    status_name=name,
                    color=color,
                    is_system=True,
                    is_active=True,
                )
            )


def _ensure_schedule(db, clinic_id: int, doctor_id: int) -> None:
    for weekday in range(0, 6):  # Mon–Sat
        exists = (
            db.query(DoctorSchedule)
            .filter(DoctorSchedule.doctor_id == doctor_id, DoctorSchedule.weekday == weekday)
            .first()
        )
        if not exists:
            db.add(
                DoctorSchedule(
                    clinic_id=clinic_id,
                    doctor_id=doctor_id,
                    weekday=weekday,
                    is_working=True,
                    start_time=time(10, 0),
                    end_time=time(19, 0),
                )
            )


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        clinic = db.query(Clinic).filter(Clinic.clinic_id == 1).first()
        if not clinic:
            clinic = Clinic(
                clinic_id=1,
                clinic_name="Aarogyam Dental",
                clinic_phone="+91 00000 00000",
                clinic_email="desk@example.com",
                is_active=True,
            )
            db.add(clinic)
            db.flush()

        admin = (
            db.query(User)
            .filter(User.clinic_id == clinic.clinic_id, User.username == "admin")
            .first()
        )
        if not admin:
            admin = User(
                clinic_id=clinic.clinic_id,
                username="admin",
                email="admin@example.com",
                password_hash=hash_password("admin123"),
                full_name="Desk Admin",
                role="admin",
                active=True,
            )
            db.add(admin)
            db.flush()

        doctor_user = (
            db.query(User)
            .filter(User.clinic_id == clinic.clinic_id, User.username == "doctor")
            .first()
        )
        if not doctor_user:
            doctor_user = User(
                clinic_id=clinic.clinic_id,
                username="doctor",
                email="doctor@example.com",
                password_hash=hash_password("doctor123"),
                full_name="Dr Pratik",
                role="doctor",
                active=True,
            )
            db.add(doctor_user)
            db.flush()

        if db.query(Client).filter(Client.clinic_id == clinic.clinic_id).count() == 0:
            samples = [
                Client(
                    clinic_id=clinic.clinic_id,
                    name="Riya Shah",
                    calling_name="Riya",
                    number="9876543210",
                    status="Under Rx",
                    place="Rajkot",
                    gender="Female",
                    age=28,
                    created_by=admin.user_id,
                    check_in_status=True,
                ),
                Client(
                    clinic_id=clinic.clinic_id,
                    name="Amit Patel",
                    calling_name="Amit",
                    number="9123456780",
                    status="Inquiry",
                    place="Rajkot",
                    gender="Male",
                    age=34,
                    created_by=admin.user_id,
                ),
                Client(
                    clinic_id=clinic.clinic_id,
                    name="Neha Joshi",
                    number="9988776655",
                    status="Completed",
                    place="Jamnagar",
                    gender="Female",
                    age=41,
                    created_by=admin.user_id,
                ),
            ]
            db.add_all(samples)
            db.flush()
            db.add(
                Note(
                    clinic_id=clinic.clinic_id,
                    client_id=samples[0].client_id,
                    user_id=admin.user_id,
                    body="First visit — sensitivity on upper left. Advised scaling.",
                )
            )

        _ensure_statuses(db, clinic.clinic_id)

        if db.query(AppointmentDoctor).filter(AppointmentDoctor.clinic_id == clinic.clinic_id).count() == 0:
            docs = [
                AppointmentDoctor(
                    clinic_id=clinic.clinic_id,
                    user_id=doctor_user.user_id,
                    doctor_name="Dr Pratik",
                    specialization="Endodontics",
                    color_code="#0f766e",
                    is_active=True,
                ),
                AppointmentDoctor(
                    clinic_id=clinic.clinic_id,
                    user_id=admin.user_id,
                    doctor_name="Dr Associate",
                    specialization="General",
                    color_code="#b45309",
                    is_active=True,
                ),
            ]
            db.add_all(docs)
            db.flush()
            for d in docs:
                _ensure_schedule(db, clinic.clinic_id, d.doctor_id)

        if db.query(AppointmentService).filter(AppointmentService.clinic_id == clinic.clinic_id).count() == 0:
            db.add_all(
                [
                    AppointmentService(
                        clinic_id=clinic.clinic_id,
                        service_name="Consultation",
                        duration_minutes=30,
                        description="General checkup",
                        is_active=True,
                    ),
                    AppointmentService(
                        clinic_id=clinic.clinic_id,
                        service_name="Dental Cleaning",
                        duration_minutes=45,
                        description="Scaling & polishing",
                        is_active=True,
                    ),
                    AppointmentService(
                        clinic_id=clinic.clinic_id,
                        service_name="Filling",
                        duration_minutes=30,
                        is_active=True,
                    ),
                    AppointmentService(
                        clinic_id=clinic.clinic_id,
                        service_name="Extraction",
                        duration_minutes=30,
                        is_active=True,
                    ),
                ]
            )
            db.flush()

        today = datetime.now(IST).date()
        if (
            db.query(Appointment)
            .filter(Appointment.clinic_id == clinic.clinic_id, Appointment.appointment_date == today)
            .count()
            == 0
        ):
            clients = (
                db.query(Client)
                .filter(Client.clinic_id == clinic.clinic_id)
                .order_by(Client.client_id)
                .all()
            )
            doctor = (
                db.query(AppointmentDoctor)
                .filter(AppointmentDoctor.clinic_id == clinic.clinic_id)
                .order_by(AppointmentDoctor.doctor_id)
                .first()
            )
            consult = (
                db.query(AppointmentService)
                .filter(
                    AppointmentService.clinic_id == clinic.clinic_id,
                    AppointmentService.service_name == "Consultation",
                )
                .first()
            )
            cleaning = (
                db.query(AppointmentService)
                .filter(
                    AppointmentService.clinic_id == clinic.clinic_id,
                    AppointmentService.service_name == "Dental Cleaning",
                )
                .first()
            )
            if clients and doctor and consult and cleaning:
                db.add_all(
                    [
                        Appointment(
                            clinic_id=clinic.clinic_id,
                            client_id=clients[0].client_id,
                            doctor_id=doctor.doctor_id,
                            service_id=consult.service_id,
                            name=clients[0].name,
                            phone=clients[0].number,
                            appointment_date=today,
                            appointment_time=time(11, 0),
                            end_time=time(11, 30),
                            status="Confirmed",
                            created_by=admin.user_id,
                        ),
                        Appointment(
                            clinic_id=clinic.clinic_id,
                            client_id=clients[1].client_id,
                            doctor_id=doctor.doctor_id,
                            service_id=cleaning.service_id,
                            name=clients[1].name,
                            phone=clients[1].number,
                            appointment_date=today,
                            appointment_time=time(12, 0),
                            end_time=time(12, 45),
                            status="Pending",
                            created_by=admin.user_id,
                        ),
                        Appointment(
                            clinic_id=clinic.clinic_id,
                            client_id=clients[2].client_id,
                            doctor_id=doctor.doctor_id,
                            service_id=consult.service_id,
                            name=clients[2].name,
                            phone=clients[2].number,
                            appointment_date=today + timedelta(days=1),
                            appointment_time=time(16, 0),
                            end_time=time(16, 30),
                            status="Confirmed",
                            created_by=admin.user_id,
                        ),
                    ]
                )

        # --- Go 3: medicines, billing, Rx, tasks ---
        if db.query(MedicineTemplate).filter(MedicineTemplate.clinic_id == clinic.clinic_id).count() == 0:
            db.add_all(
                [
                    MedicineTemplate(
                        clinic_id=clinic.clinic_id,
                        medicine_name="AmoxyClav 625",
                        strength="625mg",
                        default_quantity=10,
                        default_dosage="1-0-1",
                        default_days=5,
                        default_instructions="After meal",
                    ),
                    MedicineTemplate(
                        clinic_id=clinic.clinic_id,
                        medicine_name="Diclo-P",
                        strength="",
                        default_quantity=10,
                        default_dosage="1-1-1",
                        default_days=3,
                        default_instructions="After meal",
                    ),
                    MedicineTemplate(
                        clinic_id=clinic.clinic_id,
                        medicine_name="Pantop 40",
                        strength="40mg",
                        default_quantity=10,
                        default_dosage="1-0-0",
                        default_days=5,
                        default_instructions="Before meal",
                    ),
                ]
            )
            db.flush()

        clients = (
            db.query(Client)
            .filter(Client.clinic_id == clinic.clinic_id)
            .order_by(Client.client_id)
            .all()
        )
        if clients and db.query(Bill).filter(Bill.clinic_id == clinic.clinic_id).count() == 0:
            bill = Bill(
                clinic_id=clinic.clinic_id,
                client_id=clients[0].client_id,
                amount_due=1500,
                status="open",
                description="Consultation + scaling",
                user_id=admin.user_id,
            )
            db.add(bill)
            db.flush()
            db.add(
                MoneyReceipt(
                    clinic_id=clinic.clinic_id,
                    client_id=clients[0].client_id,
                    bill_id=None,
                    amount=500,
                    payment_mode="Cash",
                    description="Advance",
                    user_id=admin.user_id,
                )
            )

        if clients and db.query(Prescription).filter(Prescription.clinic_id == clinic.clinic_id).count() == 0:
            meds = (
                db.query(MedicineTemplate)
                .filter(MedicineTemplate.clinic_id == clinic.clinic_id)
                .order_by(MedicineTemplate.medicine_id)
                .all()
            )
            if meds:
                rx = Prescription(
                    clinic_id=clinic.clinic_id,
                    client_id=clients[0].client_id,
                    prescription_date=today,
                    notes="Post scaling",
                    user_id=admin.user_id,
                )
                db.add(rx)
                db.flush()
                db.add_all(
                    [
                        PrescriptionItem(
                            clinic_id=clinic.clinic_id,
                            prescription_id=rx.prescription_id,
                            medicine_id=meds[0].medicine_id,
                            medicine_name=meds[0].medicine_name,
                            quantity=meds[0].default_quantity,
                            dosage=meds[0].default_dosage,
                            days=meds[0].default_days,
                            instructions=meds[0].default_instructions,
                        ),
                        PrescriptionItem(
                            clinic_id=clinic.clinic_id,
                            prescription_id=rx.prescription_id,
                            medicine_id=meds[1].medicine_id,
                            medicine_name=meds[1].medicine_name,
                            quantity=meds[1].default_quantity,
                            dosage=meds[1].default_dosage,
                            days=meds[1].default_days,
                            instructions=meds[1].default_instructions,
                        ),
                    ]
                )

        if db.query(Task).filter(Task.clinic_id == clinic.clinic_id).count() == 0 and clients:
            db.add_all(
                [
                    Task(
                        clinic_id=clinic.clinic_id,
                        client_id=clients[0].client_id,
                        task_description="Call patient for review after scaling",
                        due_date=today + timedelta(days=2),
                        status="Open",
                        created_by=admin.user_id,
                        assignee_id=doctor_user.user_id,
                    ),
                    Task(
                        clinic_id=clinic.clinic_id,
                        client_id=None,
                        task_description="Order composite capsules",
                        due_date=today,
                        status="Open",
                        created_by=admin.user_id,
                        assignee_id=admin.user_id,
                    ),
                ]
            )

        other = db.query(Clinic).filter(Clinic.clinic_id == 2).first()
        if not other:
            other = Clinic(clinic_id=2, clinic_name="Smile Makers", is_active=True)
            db.add(other)
            db.flush()
            db.add(
                User(
                    clinic_id=other.clinic_id,
                    username="smile",
                    email="smile@example.com",
                    password_hash=hash_password("smile123"),
                    full_name="Smile Staff",
                    role="staff",
                    active=True,
                )
            )
            _ensure_statuses(db, other.clinic_id)

        db.commit()
        print("Seed OK (Go 1–3)")
        print("  Login: admin / admin123  (Aarogyam Dental)")
        print("  Login: doctor / doctor123")
        print("  Login: smile / smile123  (Smile Makers)")
        print(f"  Today seed appointments: {today.isoformat()}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
