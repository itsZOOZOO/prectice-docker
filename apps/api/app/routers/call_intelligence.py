"""Call Intelligence statistics proxy + clinic status (setup-PIN gated for mutations/reads)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app import call_intelligence_svc as ci
from app.db import get_db
from app.models import User
from app.schemas import OkResponse
from app.setup_access import require_setup_unlock

router = APIRouter(prefix="/statistics/call-intelligence", tags=["call-intelligence"])
status_router = APIRouter(prefix="/settings", tags=["call-intelligence"])


class CreateTagBody(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    color: str = Field(default="#0d6efd", max_length=20)


class AddCallTagBody(BaseModel):
    tag_id: int


class SaveNoteBody(BaseModel):
    note: str = ""


@status_router.get("/call-intelligence", response_model=OkResponse)
def call_intelligence_status(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    return OkResponse(data=ci.clinic_status(db, user.clinic_id))


@router.get("/priority-devices", response_model=OkResponse, dependencies=[Depends(require_setup_unlock)])
def priority_devices(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    return OkResponse(data=ci.proxy(db, user.clinic_id, "GET", "/priority-devices"))


@router.get("/priority-report", response_model=OkResponse, dependencies=[Depends(require_setup_unlock)])
def priority_report(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    device: str = Query(...),
    date_from: str = Query(...),
    date_to: str = Query(...),
    view: str = Query("all_first"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
) -> OkResponse:
    data = ci.proxy(
        db,
        user.clinic_id,
        "GET",
        "/priority-report",
        query={
            "device": device,
            "date_from": date_from,
            "date_to": date_to,
            "view": view,
            "page": page,
            "per_page": per_page,
        },
    )
    return OkResponse(data=data)


@router.get("/recording-presign", response_model=OkResponse, dependencies=[Depends(require_setup_unlock)])
def recording_presign(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    s3_key: str = Query(...),
) -> OkResponse:
    return OkResponse(
        data=ci.proxy(
            db,
            user.clinic_id,
            "GET",
            "/recording-presign",
            query={"s3_key": s3_key},
        )
    )


@router.get("/tags", response_model=OkResponse, dependencies=[Depends(require_setup_unlock)])
def list_tags(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    return OkResponse(data=ci.proxy(db, user.clinic_id, "GET", "/tags"))


@router.post("/tags", response_model=OkResponse, dependencies=[Depends(require_setup_unlock)])
def create_tag(
    body: CreateTagBody,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    return OkResponse(
        data=ci.proxy(
            db,
            user.clinic_id,
            "POST",
            "/tags",
            body={"name": body.name.strip(), "color": body.color.strip() or "#0d6efd"},
        )
    )


@router.post("/calls/{call_id}/tags", response_model=OkResponse, dependencies=[Depends(require_setup_unlock)])
def add_call_tag(
    call_id: int,
    body: AddCallTagBody,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    return OkResponse(
        data=ci.proxy(
            db,
            user.clinic_id,
            "POST",
            f"/calls/{call_id}/tags",
            body={"tag_id": body.tag_id},
        )
    )


@router.delete(
    "/calls/{call_id}/tags/{tag_id}",
    response_model=OkResponse,
    dependencies=[Depends(require_setup_unlock)],
)
def remove_call_tag(
    call_id: int,
    tag_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    return OkResponse(
        data=ci.proxy(db, user.clinic_id, "DELETE", f"/calls/{call_id}/tags/{tag_id}")
    )


@router.put("/calls/{call_id}/note", response_model=OkResponse, dependencies=[Depends(require_setup_unlock)])
def save_call_note(
    call_id: int,
    body: SaveNoteBody,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    return OkResponse(
        data=ci.proxy(
            db,
            user.clinic_id,
            "PUT",
            f"/calls/{call_id}/note",
            body={"note": body.note},
        )
    )
