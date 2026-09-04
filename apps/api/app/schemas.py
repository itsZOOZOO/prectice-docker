from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field


class OkResponse(BaseModel):
    ok: bool = True
    data: dict | list | None = None
    error: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    clinic_id: int
    username: str
    full_name: str
    role: str
    email: str | None = None


class LoginData(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: TokenUser
    clinic_name: str


class ClinicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    clinic_id: int
    clinic_name: str
    clinic_phone: str | None = None
    clinic_email: str | None = None


class ClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    number: str | None = None
    country_code: int | None = 91
    place: str | None = None
    age: int | None = None
    gender: str | None = None
    date_of_birth: date | None = None
    status: str = "Inquiry"
    lead_source: str | None = None
    reference: str | None = None
    client_personal_note: str | None = None
    calling_name: str | None = None


class ClientUpdate(BaseModel):
    name: str | None = None
    number: str | None = None
    country_code: int | None = None
    place: str | None = None
    age: int | None = None
    gender: str | None = None
    date_of_birth: date | None = None
    status: str | None = None
    lead_source: str | None = None
    reference: str | None = None
    client_personal_note: str | None = None
    calling_name: str | None = None


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    client_id: int
    clinic_id: int
    name: str
    calling_name: str | None = None
    number: str | None = None
    country_code: int | None = None
    place: str | None = None
    age: int | None = None
    gender: str | None = None
    date_of_birth: date | None = None
    status: str
    lead_source: str | None = None
    reference: str | None = None
    client_personal_note: str | None = None
    check_in_status: bool
    checked_in_at: datetime | None = None
    created_at: datetime


class NoteCreate(BaseModel):
    body: str = Field(min_length=1)


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    note_id: int
    clinic_id: int
    client_id: int
    user_id: int | None
    body: str
    created_at: datetime
    author_name: str | None = None


class CheckinOut(BaseModel):
    client_id: int
    check_in_status: bool
    checked_in_at: datetime | None = None


class DoctorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    doctor_id: int
    doctor_name: str
    specialization: str | None = None
    color_code: str | None = None
    is_active: bool


class ServiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    service_id: int
    service_name: str
    duration_minutes: int
    description: str | None = None
    is_active: bool


class StatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status_id: int
    status_name: str
    color: str
    is_active: bool


class AppointmentCreate(BaseModel):
    client_id: int | None = None
    doctor_id: int
    service_id: int | None = None
    name: str = Field(min_length=1, max_length=255)
    phone: str | None = None
    appointment_date: date
    appointment_time: time
    status: str = "Confirmed"
    notes: str | None = None
    send_whatsapp: bool = False


class AppointmentStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=50)


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    appointment_id: int
    clinic_id: int
    client_id: int | None
    doctor_id: int
    service_id: int | None
    name: str
    phone: str | None
    appointment_date: date
    appointment_time: time
    end_time: time | None
    status: str
    notes: str | None
    doctor_name: str | None = None
    service_name: str | None = None
    created_at: datetime


class BillCreate(BaseModel):
    amount_due: float = Field(gt=0)
    description: str | None = None


class BillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bill_id: int
    clinic_id: int
    client_id: int
    amount_due: float
    status: str
    description: str | None
    issued_at: datetime


class ReceiptCreate(BaseModel):
    amount: float = Field(gt=0)
    payment_mode: str = "Cash"
    description: str | None = None
    bill_id: int | None = None


class ReceiptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    receipt_id: int
    clinic_id: int
    client_id: int
    bill_id: int | None
    amount: float
    payment_mode: str
    description: str | None
    received_at: datetime


class MedicineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    medicine_id: int
    medicine_name: str
    strength: str | None = None
    default_quantity: int | None = None
    default_dosage: str | None = None
    default_days: int | None = None
    default_instructions: str | None = None


class PrescriptionItemIn(BaseModel):
    medicine_id: int | None = None
    medicine_name: str = ""
    quantity: int | None = None
    dosage: str | None = None
    days: int | None = None
    instructions: str | None = None


class PrescriptionItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id: int
    medicine_id: int | None
    medicine_name: str
    quantity: int | None
    dosage: str | None
    days: int | None
    instructions: str | None


class PrescriptionCreate(BaseModel):
    prescription_date: date | None = None
    notes: str | None = None
    items: list[PrescriptionItemIn]


class PrescriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    prescription_id: int
    clinic_id: int
    client_id: int
    prescription_date: date
    notes: str | None
    created_at: datetime
    items: list[PrescriptionItemOut] = []


class TaskCreate(BaseModel):
    task_description: str = Field(min_length=1)
    client_id: int | None = None
    assignee_id: int | None = None
    due_date: date | None = None


class TaskUpdate(BaseModel):
    task_description: str | None = None
    client_id: int | None = None
    assignee_id: int | None = None
    due_date: date | None = None
    status: str | None = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: int
    clinic_id: int
    client_id: int | None
    task_description: str
    due_date: date | None
    status: str
    assignee_id: int | None
    created_by: int | None
    completed_at: datetime | None
    created_at: datetime
    client_name: str | None = None
    assignee_name: str | None = None
