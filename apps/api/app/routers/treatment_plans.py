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


@router.get("/treatments/catalog/browse", response_model=OkResponse)
def treatments_catalog_browse(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    return OkResponse(data=tp.list_catalog_browse(db, user.clinic_id))


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


@router.get("/treatment-plans/{plan_id}/share-links", response_model=OkResponse)
def list_share_links(
    plan_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    from app import treatment_plan_share as share

    return OkResponse(data={"items": share.list_links(db, user.clinic_id, plan_id)})


@router.post("/treatment-plans/{plan_id}/share-links", response_model=OkResponse, status_code=status.HTTP_201_CREATED)
def create_share_link(
    plan_id: int,
    body: dict[str, Any],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    from app import treatment_plan_share as share

    result = share.generate_link(
        db,
        clinic_id=user.clinic_id,
        user_id=user.user_id,
        plan_id=plan_id,
        validity_days=int(body.get("validity_days") or 7),
        notes=str(body.get("notes") or ""),
    )
    db.commit()
    return OkResponse(data=result)


@router.delete("/treatment-plans/{plan_id}/share-links/{link_id}", response_model=OkResponse)
def delete_share_link(
    plan_id: int,
    link_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    from app import treatment_plan_share as share

    share.deactivate_link(db, user.clinic_id, plan_id, link_id)
    db.commit()
    return OkResponse(data={"deleted": True})


@router.get("/treatment-plans/{plan_id}/share-links/{link_id}/analytics", response_model=OkResponse)
def share_link_analytics(
    plan_id: int,
    link_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    from app import treatment_plan_share as share

    return OkResponse(data=share.analytics_for_link(db, user.clinic_id, plan_id, link_id))


@router.post("/treatment-plans/{plan_id}/send-whatsapp", response_model=OkResponse)
def send_plan_whatsapp(
    plan_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    from app import treatment_plan_share as share
    from app import whatsapp as wa
    from app.models import Client, Note

    plan = tp.get_plan_or_404(db, user.clinic_id, plan_id)
    client = (
        db.query(Client)
        .filter(Client.client_id == plan.client_id, Client.clinic_id == user.clinic_id)
        .first()
    )
    if not client:
        raise HTTPException(status_code=422, detail="This plan is not linked to a client.")

    phone = wa.resolve_phone(form_phone=None, client=client, db=db)
    if not phone:
        raise HTTPException(status_code=422, detail="No valid WhatsApp phone number found for this client.")

    link = share.generate_link(
        db,
        clinic_id=user.clinic_id,
        user_id=user.user_id,
        plan_id=plan_id,
        validity_days=7,
        notes="Sent via WhatsApp",
    )
    result = wa.send_plan_share(
        db,
        clinic_id=user.clinic_id,
        phone=phone,
        patient_name=client.name,
        public_path=link["public_path"],
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=502,
            detail=result.get("message") or "WhatsApp send failed.",
        )

    note = Note(
        clinic_id=user.clinic_id,
        client_id=client.client_id,
        user_id=user.user_id,
        body=f"Treatment plan has been sent successfully via WhatsApp to {client.name}.",
        visible=True,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return OkResponse(
        data={
            "wa_message_id": (result.get("response") or {}).get("wa_message_id"),
            "share_url": link["share_url"],
            "public_path": link["public_path"],
            "note_id": note.note_id,
        }
    )
