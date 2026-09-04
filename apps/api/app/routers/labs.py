from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import labs as lab_svc
from app.auth import get_current_user
from app.db import get_db
from app.models import DentalLab, User
from app.schemas import OkResponse

router = APIRouter(tags=["labs"])


class DentalLabCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    contact_person: str | None = None
    phone: str | None = None
    notes: str | None = None


class DentalLabUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    contact_person: str | None = None
    phone: str | None = None
    notes: str | None = None


class LabCaseCreate(BaseModel):
    client_id: int
    lab_id: int
    case_type: str = Field(min_length=1, max_length=128)
    tooth_numbers: str | None = None
    description: str | None = None


class LabCaseUpdate(BaseModel):
    case_type: str | None = None
    tooth_numbers: str | None = None
    description: str | None = None
    expected_return_date: str | None = None


class LabStageBody(BaseModel):
    stage: str
    action: str = "set"
    expected_return_date: str | None = None


# ── Vendors ──────────────────────────────────────────────────────────

@router.get("/labs", response_model=OkResponse)
def list_labs(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    rows = (
        db.query(DentalLab)
        .filter(DentalLab.clinic_id == user.clinic_id, DentalLab.visible.is_(True))
        .order_by(DentalLab.name.asc())
        .all()
    )
    return OkResponse(data={"items": [lab_svc.serialize_lab(r) for r in rows]})


@router.post("/labs", response_model=OkResponse, status_code=status.HTTP_201_CREATED)
def create_lab(
    body: DentalLabCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    lab = lab_svc.create_lab(
        db,
        user,
        name=body.name,
        contact_person=body.contact_person,
        phone=body.phone,
        notes=body.notes,
    )
    return OkResponse(data=lab_svc.serialize_lab(lab))


@router.patch("/labs/{lab_id}", response_model=OkResponse)
def update_lab(
    lab_id: int,
    body: DentalLabUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    lab = lab_svc.update_lab(
        db,
        user,
        lab_id,
        name=body.name,
        contact_person=body.contact_person,
        phone=body.phone,
        notes=body.notes,
    )
    return OkResponse(data=lab_svc.serialize_lab(lab))


@router.delete("/labs/{lab_id}", response_model=OkResponse)
def archive_lab(
    lab_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    return OkResponse(data=lab_svc.archive_lab(db, user, lab_id))


# ── Cases ─────────────────────────────────────────────────────────────

@router.get("/lab-cases/summary", response_model=OkResponse)
def lab_cases_summary(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    return OkResponse(data={"counts": lab_svc.summary_counts(db, user.clinic_id)})


@router.get("/lab-cases", response_model=OkResponse)
def list_lab_cases(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    filter: str = Query(default="action_needed"),
) -> OkResponse:
    cases = lab_svc.list_cases(db, user.clinic_id, filter)
    return OkResponse(data={"cases": cases, "filter": filter, "count": len(cases)})


@router.post("/lab-cases", response_model=OkResponse, status_code=status.HTTP_201_CREATED)
def create_lab_case(
    body: LabCaseCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    return OkResponse(
        data=lab_svc.create_case(
            db,
            user,
            client_id=body.client_id,
            lab_id=body.lab_id,
            case_type=body.case_type,
            tooth_numbers=body.tooth_numbers,
            description=body.description,
        )
    )


@router.get("/lab-cases/{case_id}", response_model=OkResponse)
def get_lab_case(
    case_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    return OkResponse(data=lab_svc.get_case_detail(db, case_id, user.clinic_id))


@router.patch("/lab-cases/{case_id}", response_model=OkResponse)
def patch_lab_case(
    case_id: int,
    body: LabCaseUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    return OkResponse(
        data=lab_svc.update_case(
            db,
            user,
            case_id,
            case_type=body.case_type,
            tooth_numbers=body.tooth_numbers,
            description=body.description,
            expected_return_date=body.expected_return_date,
        )
    )


@router.post("/lab-cases/{case_id}/close", response_model=OkResponse)
def close_lab_case(
    case_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    return OkResponse(data={"case": lab_svc.close_case(db, user, case_id)})


@router.post("/lab-cases/{case_id}/cancel", response_model=OkResponse)
def cancel_lab_case(
    case_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    return OkResponse(data={"case": lab_svc.cancel_case(db, user, case_id)})


@router.post("/lab-cases/{case_id}/cycles", response_model=OkResponse)
def add_lab_cycle(
    case_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    return OkResponse(data={"case": lab_svc.add_cycle(db, user, case_id)})


@router.post("/lab-cases/{case_id}/cycles/{cycle_number}/stages", response_model=OkResponse)
def set_lab_stage(
    case_id: int,
    cycle_number: int,
    body: LabStageBody,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    return OkResponse(
        data={
            "case": lab_svc.set_stage(
                db,
                user,
                case_id,
                cycle_number,
                stage=body.stage,
                action=body.action,
                expected_return_date=body.expected_return_date,
            )
        }
    )


@router.get("/clients/{client_id}/lab-cases", response_model=OkResponse)
def client_lab_cases(
    client_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    cases = lab_svc.list_cases_for_client(db, user.clinic_id, client_id)
    return OkResponse(data={"cases": cases, "count": len(cases)})
