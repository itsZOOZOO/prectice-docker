from __future__ import annotations

from datetime import date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.db import get_db
from app.models import Client, MedicineTemplate, Prescription, PrescriptionItem, User
from app.schemas import (
    MedicineOut,
    OkResponse,
    PrescriptionCreate,
    PrescriptionItemOut,
    PrescriptionOut,
)

router = APIRouter(tags=["prescriptions"])
IST = ZoneInfo("Asia/Kolkata")


def _client(db: Session, clinic_id: int, client_id: int) -> Client:
    row = (
        db.query(Client)
        .filter(Client.client_id == client_id, Client.clinic_id == clinic_id, Client.visible.is_(True))
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return row


def _rx_out(rx: Prescription) -> dict:
    data = PrescriptionOut.model_validate(rx).model_dump()
    data["prescription_date"] = rx.prescription_date.isoformat()
    data["items"] = [PrescriptionItemOut.model_validate(i).model_dump() for i in rx.items]
    return data


@router.get("/medicine-templates", response_model=OkResponse)
def list_medicines(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    rows = (
        db.query(MedicineTemplate)
        .filter(MedicineTemplate.clinic_id == user.clinic_id, MedicineTemplate.visible.is_(True))
        .order_by(MedicineTemplate.medicine_name)
        .all()
    )
    return OkResponse(data=[MedicineOut.model_validate(r).model_dump() for r in rows])


@router.get("/clients/{client_id}/prescriptions", response_model=OkResponse)
def list_prescriptions(
    client_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    _client(db, user.clinic_id, client_id)
    rows = (
        db.query(Prescription)
        .options(joinedload(Prescription.items))
        .filter(
            Prescription.clinic_id == user.clinic_id,
            Prescription.client_id == client_id,
            Prescription.visible.is_(True),
        )
        .order_by(Prescription.prescription_date.desc(), Prescription.prescription_id.desc())
        .all()
    )
    return OkResponse(data=[_rx_out(r) for r in rows])


@router.post(
    "/clients/{client_id}/prescriptions",
    response_model=OkResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_prescription(
    client_id: int,
    body: PrescriptionCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    _client(db, user.clinic_id, client_id)
    if not body.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Add at least one medicine")

    rx = Prescription(
        clinic_id=user.clinic_id,
        client_id=client_id,
        prescription_date=body.prescription_date or datetime.now(IST).date(),
        notes=body.notes,
        user_id=user.user_id,
    )
    db.add(rx)
    db.flush()

    for item in body.items:
        medicine_name = item.medicine_name.strip()
        medicine_id = item.medicine_id
        if medicine_id and not medicine_name:
            tmpl = (
                db.query(MedicineTemplate)
                .filter(
                    MedicineTemplate.medicine_id == medicine_id,
                    MedicineTemplate.clinic_id == user.clinic_id,
                    MedicineTemplate.visible.is_(True),
                )
                .first()
            )
            if tmpl:
                medicine_name = tmpl.medicine_name
        if not medicine_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Medicine name required")
        db.add(
            PrescriptionItem(
                clinic_id=user.clinic_id,
                prescription_id=rx.prescription_id,
                medicine_id=medicine_id,
                medicine_name=medicine_name,
                quantity=item.quantity,
                dosage=item.dosage,
                days=item.days,
                instructions=item.instructions,
            )
        )

    db.commit()
    rx = (
        db.query(Prescription)
        .options(joinedload(Prescription.items))
        .filter(Prescription.prescription_id == rx.prescription_id)
        .one()
    )
    return OkResponse(data=_rx_out(rx))


@router.delete("/clients/{client_id}/prescriptions/{prescription_id}", response_model=OkResponse)
def delete_prescription(
    client_id: int,
    prescription_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    _client(db, user.clinic_id, client_id)
    rx = (
        db.query(Prescription)
        .filter(
            Prescription.prescription_id == prescription_id,
            Prescription.client_id == client_id,
            Prescription.clinic_id == user.clinic_id,
            Prescription.visible.is_(True),
        )
        .first()
    )
    if not rx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")
    rx.visible = False
    db.commit()
    return OkResponse(data={"prescription_id": prescription_id, "visible": False})
