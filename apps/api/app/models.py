from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Clinic(Base):
    __tablename__ = "clinics"

    clinic_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_name: Mapped[str] = mapped_column(String(255), nullable=False)
    clinic_address: Mapped[str | None] = mapped_column(String(255))
    clinic_phone: Mapped[str | None] = mapped_column(String(20))
    clinic_email: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list[User]] = relationship(back_populates="clinic")
    clients: Mapped[list[Client]] = relationship(back_populates="clinic")
    settings: Mapped[list[ClinicSetting]] = relationship(back_populates="clinic", cascade="all, delete-orphan")


class ClinicSetting(Base):
    __tablename__ = "clinic_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.clinic_id"), nullable=False, index=True)
    setting_key: Mapped[str] = mapped_column(String(100), nullable=False)
    setting_value: Mapped[str | None] = mapped_column(Text)

    clinic: Mapped[Clinic] = relationship(back_populates="settings")

    __table_args__ = (UniqueConstraint("clinic_id", "setting_key", name="uq_clinic_settings_key"),)


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.clinic_id"), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="staff", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    profile_photo_url: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    clinic: Mapped[Clinic] = relationship(back_populates="users")

    __table_args__ = (UniqueConstraint("clinic_id", "username", name="uq_users_clinic_username"),)


class Client(Base):
    __tablename__ = "clients"

    client_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.clinic_id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    calling_name: Mapped[str | None] = mapped_column(String(255))
    number: Mapped[str | None] = mapped_column(String(30), index=True)
    country_code: Mapped[int | None] = mapped_column(Integer, default=91)
    place: Mapped[str | None] = mapped_column(String(255))
    age: Mapped[int | None] = mapped_column(Integer)
    gender: Mapped[str | None] = mapped_column(String(50))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(50), default="Inquiry", nullable=False)
    lead_source: Mapped[str | None] = mapped_column(String(50))
    reference: Mapped[str | None] = mapped_column(String(255))
    client_personal_note: Mapped[str | None] = mapped_column(String(255))
    check_in_status: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    profile_photo_url: Mapped[str | None] = mapped_column(String(255))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    clinic: Mapped[Clinic] = relationship(back_populates="clients")
    notes: Mapped[list[Note]] = relationship(back_populates="client", cascade="all, delete-orphan")
    phone_numbers: Mapped[list[ClientPhone]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )


class ClientPhone(Base):
    __tablename__ = "client_phone_numbers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.clinic_id"), nullable=False, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.client_id"), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    label: Mapped[str | None] = mapped_column(String(50))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    client: Mapped[Client] = relationship(back_populates="phone_numbers")


class Note(Base):
    __tablename__ = "notes"

    note_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.clinic_id"), nullable=False, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.client_id"), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_url: Mapped[str | None] = mapped_column(String(512))
    visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    client: Mapped[Client] = relationship(back_populates="notes")
    attachments: Mapped[list[NoteAttachment]] = relationship(
        back_populates="note", cascade="all, delete-orphan"
    )


class NoteAttachment(Base):
    __tablename__ = "note_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    note_id: Mapped[int] = mapped_column(ForeignKey("notes.note_id"), nullable=False, index=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.clinic_id"), nullable=False, index=True)
    attachment_url: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    note: Mapped[Note] = relationship(back_populates="attachments")


class ClientCheckinLog(Base):
    __tablename__ = "client_checkin_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.clinic_id"), nullable=False, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.client_id"), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # check_in | check_out
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AppointmentDoctor(Base):
    __tablename__ = "appointments_doctors"

    doctor_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.clinic_id"), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    doctor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    specialization: Mapped[str | None] = mapped_column(String(255))
    color_code: Mapped[str | None] = mapped_column(String(7), default="#0f766e")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    schedules: Mapped[list[DoctorSchedule]] = relationship(back_populates="doctor", cascade="all, delete-orphan")


class AppointmentService(Base):
    __tablename__ = "appointments_services"

    service_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.clinic_id"), nullable=False, index=True)
    service_name: Mapped[str] = mapped_column(String(255), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AppointmentStatus(Base):
    __tablename__ = "appointments_statuses"

    status_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.clinic_id"), nullable=False, index=True)
    status_name: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="neutral", nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("clinic_id", "status_name", name="uq_appt_status_clinic_name"),
    )


class DoctorSchedule(Base):
    __tablename__ = "appointments_doctor_schedules"

    schedule_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.clinic_id"), nullable=False, index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("appointments_doctors.doctor_id"), nullable=False, index=True)
    # 0=Mon .. 6=Sun
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    is_working: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    doctor: Mapped[AppointmentDoctor] = relationship(back_populates="schedules")

    __table_args__ = (
        UniqueConstraint("doctor_id", "weekday", name="uq_doctor_weekday"),
    )


class Appointment(Base):
    __tablename__ = "appointments"

    appointment_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.clinic_id"), nullable=False, index=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.client_id"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("appointments_doctors.doctor_id"), nullable=False, index=True)
    service_id: Mapped[int | None] = mapped_column(ForeignKey("appointments_services.service_id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    appointment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    appointment_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time | None] = mapped_column(Time)
    status: Mapped[str] = mapped_column(String(50), default="Confirmed", nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(String(255))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Bill(Base):
    __tablename__ = "bills"

    bill_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.clinic_id"), nullable=False, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.client_id"), nullable=False, index=True)
    amount_due: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False)  # open | paid
    description: Mapped[str | None] = mapped_column(String(255))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class MoneyReceipt(Base):
    __tablename__ = "money_receipts"

    receipt_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.clinic_id"), nullable=False, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.client_id"), nullable=False, index=True)
    bill_id: Mapped[int | None] = mapped_column(ForeignKey("bills.bill_id"), index=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    payment_mode: Mapped[str] = mapped_column(String(50), default="Cash", nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class MedicineTemplate(Base):
    __tablename__ = "medicine_templates"

    medicine_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.clinic_id"), nullable=False, index=True)
    medicine_name: Mapped[str] = mapped_column(String(255), nullable=False)
    strength: Mapped[str | None] = mapped_column(String(50))
    default_quantity: Mapped[int | None] = mapped_column(Integer, default=10)
    default_dosage: Mapped[str | None] = mapped_column(String(50))
    default_days: Mapped[int | None] = mapped_column(Integer, default=5)
    default_instructions: Mapped[str | None] = mapped_column(String(255))
    visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Prescription(Base):
    __tablename__ = "prescriptions"

    prescription_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.clinic_id"), nullable=False, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.client_id"), nullable=False, index=True)
    prescription_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(255))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list[PrescriptionItem]] = relationship(
        back_populates="prescription", cascade="all, delete-orphan"
    )


class PrescriptionItem(Base):
    __tablename__ = "prescription_items"

    item_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.clinic_id"), nullable=False, index=True)
    prescription_id: Mapped[int] = mapped_column(
        ForeignKey("prescriptions.prescription_id"), nullable=False, index=True
    )
    medicine_id: Mapped[int | None] = mapped_column(ForeignKey("medicine_templates.medicine_id"))
    medicine_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int | None] = mapped_column(Integer)
    dosage: Mapped[str | None] = mapped_column(String(50))
    days: Mapped[int | None] = mapped_column(Integer)
    instructions: Mapped[str | None] = mapped_column(String(255))

    prescription: Mapped[Prescription] = relationship(back_populates="items")


class Task(Base):
    __tablename__ = "tasks"

    task_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.clinic_id"), nullable=False, index=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.client_id"), index=True)
    task_description: Mapped[str] = mapped_column(Text, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="Open", nullable=False, index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
