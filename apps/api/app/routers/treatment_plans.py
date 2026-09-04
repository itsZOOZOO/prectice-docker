"""Treatment plan API routes (desk MVP)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import OkResponse
from app import treatment_plans as tp

router = APIRouter(tags=["treatment-plans"])


@router.get("/treatments/catalog", response_model=OkResponse)
def treatments_catalog(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    return OkResponse(data=tp.list_catalog(db, user.clinic_id))


@router.get("/treatments/{treatment_id}/price-options", response_model=OkResponse)
def treatment_price_options(
    treatment_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    return OkResponse(data=tp.list_price_options(db, user.clinic_id, treatment_id))


@router.get("/clients/{client_id}/treatment-plans", response_model=OkResponse)
def list_client_treatment_plans(
    client_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    return OkResponse(data=tp.list_client_plans(db, user.clinic_id, client_id))


async def _parse_photos_by_row(
    file_rows: list[int] | int | None,
    files: list[UploadFile] | UploadFile | None,
) -> dict[int, list[str]]:
    row_list = file_rows if isinstance(file_rows, list) else ([file_rows] if file_rows is not None else [])
    file_list = files if isinstance(files, list) else ([files] if files is not None else [])
    # Drop empty uploads
    file_list = [f for f in file_list if f is not None and getattr(f, "filename", None)]
    if not file_list and not row_list:
        return {}
    if len(row_list) != len(file_list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="file_rows length must match files",
        )
    grouped: dict[int, list[UploadFile]] = {}
    for row_idx, upload in zip(row_list, file_list, strict=True):
        grouped.setdefault(int(row_idx), []).append(upload)
    out: dict[int, list[str]] = {}
    cursor = 0
    for row_idx, uploads in grouped.items():
        keys = await tp._upload_row_photos(uploads, start_index=cursor)
        cursor += len(keys)
        out[row_idx] = keys
    return out


@router.post(
    "/clients/{client_id}/treatment-plans",
    response_model=OkResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_treatment_plan(
    client_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    plan: str = Form(...),
    files: Annotated[list[UploadFile] | None, File()] = None,
    file_rows: Annotated[list[int] | None, Form()] = None,
) -> OkResponse:
    body = tp._parse_plan_body(plan)
    photos = await _parse_photos_by_row(file_rows, files)
    created = tp.create_plan(
        db,
        clinic_id=user.clinic_id,
        client_id=client_id,
        user=user,
        body=body,
        photos_by_row=photos,
    )
    return OkResponse(data=tp.serialize_plan(created))


@router.get("/treatment-plans/{plan_id}", response_model=OkResponse)
def get_treatment_plan(
    plan_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    plan = tp.get_plan_or_404(db, user.clinic_id, plan_id)
    return OkResponse(data=tp.serialize_plan(plan))


@router.put("/treatment-plans/{plan_id}", response_model=OkResponse)
async def update_treatment_plan(
    plan_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    plan: str = Form(...),
    files: Annotated[list[UploadFile] | None, File()] = None,
    file_rows: Annotated[list[int] | None, Form()] = None,
) -> OkResponse:
    body = tp._parse_plan_body(plan)
    photos = await _parse_photos_by_row(file_rows, files)
    updated = tp.update_plan(
        db,
        clinic_id=user.clinic_id,
        plan_id=plan_id,
        user=user,
        body=body,
        photos_by_row=photos,
    )
    return OkResponse(data=tp.serialize_plan(updated))


@router.delete("/treatment-plans/{plan_id}", response_model=OkResponse)
def delete_treatment_plan(
    plan_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    tp.soft_delete_plan(db, user.clinic_id, plan_id)
    return OkResponse(data={"plan_id": plan_id, "visible": False})


@router.put("/treatment-plans/{plan_id}/pricing", response_model=OkResponse)
def update_treatment_plan_pricing(
    plan_id: int,
    body: dict[str, Any],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    updated = tp.update_pricing(db, user.clinic_id, plan_id, body)
    return OkResponse(data=tp.serialize_plan(updated))
