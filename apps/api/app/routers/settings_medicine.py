"""Clinic medicine template settings (CRUD for prescribing catalog)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import MedicineTemplate, User
from app.schemas import MedicineOut, OkResponse

router = APIRouter(prefix="/settings/medicine-templates", tags=["settings-medicine"])


class MedicineCreate(BaseModel):
    medicine_name: str = Field(min_length=1, max_length=255)
    strength: str | None = Field(default=None, max_length=50)
    default_quantity: int | None = None
    default_dosage: str | None = Field(default=None, max_length=50)
    default_days: int | None = None
    default_instructions: str | None = Field(default=None, max_length=255)


class MedicineUpdate(BaseModel):
    medicine_name: str | None = Field(default=None, min_length=1, max_length=255)
    strength: str | None = Field(default=None, max_length=50)
    default_quantity: int | None = None
    default_dosage: str | None = Field(default=None, max_length=50)
    default_days: int | None = None
    default_instructions: str | None = Field(default=None, max_length=255)


def _get_medicine(db: Session, clinic_id: int, medicine_id: int) -> MedicineTemplate:
    row = (
        db.query(MedicineTemplate)
        .filter(
            MedicineTemplate.medicine_id == medicine_id,
            MedicineTemplate.clinic_id == clinic_id,
            MedicineTemplate.visible.is_(True),
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medicine template not found")
    return row


def _out(row: MedicineTemplate) -> dict:
    return MedicineOut.model_validate(row).model_dump()


@router.get("", response_model=OkResponse)
def list_medicine_templates(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    rows = (
        db.query(MedicineTemplate)
        .filter(MedicineTemplate.clinic_id == user.clinic_id, MedicineTemplate.visible.is_(True))
        .order_by(MedicineTemplate.medicine_name.asc())
        .all()
    )
    return OkResponse(data={"templates": [_out(r) for r in rows]})


@router.post("", response_model=OkResponse, status_code=201)
def create_medicine_template(
    body: MedicineCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    row = MedicineTemplate(
        clinic_id=user.clinic_id,
        medicine_name=body.medicine_name.strip(),
        strength=(body.strength or "").strip() or None,
        default_quantity=body.default_quantity if body.default_quantity is not None else 10,
        default_dosage=(body.default_dosage or "").strip() or None,
        default_days=body.default_days if body.default_days is not None else 5,
        default_instructions=(body.default_instructions or "").strip() or None,
        visible=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return OkResponse(data=_out(row))


@router.patch("/{medicine_id}", response_model=OkResponse)
def update_medicine_template(
    medicine_id: int,
    body: MedicineUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    row = _get_medicine(db, user.clinic_id, medicine_id)
    data = body.model_dump(exclude_unset=True)
    if "medicine_name" in data and data["medicine_name"] is not None:
        row.medicine_name = data["medicine_name"].strip()
    if "strength" in data:
        row.strength = (data["strength"] or "").strip() or None
    if "default_quantity" in data:
        row.default_quantity = data["default_quantity"]
    if "default_dosage" in data:
        row.default_dosage = (data["default_dosage"] or "").strip() or None
    if "default_days" in data:
        row.default_days = data["default_days"]
    if "default_instructions" in data:
        row.default_instructions = (data["default_instructions"] or "").strip() or None
    db.commit()
    db.refresh(row)
    return OkResponse(data=_out(row))


@router.delete("/{medicine_id}", response_model=OkResponse)
def delete_medicine_template(
    medicine_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    row = _get_medicine(db, user.clinic_id, medicine_id)
    row.visible = False
    db.commit()
    return OkResponse(data={"medicine_id": medicine_id, "visible": False})
