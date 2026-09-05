"""Clinic client tag catalog (settings CRUD)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app import client_filters as cf
from app.db import get_db
from app.models import ClientTag, ClientTagDefinition, User
from app.schemas import OkResponse
from app.setup_access import require_setup_unlock

router = APIRouter(prefix="/settings/client-tags", tags=["settings-client-tags"])

UnlockDep = Annotated[None, Depends(require_setup_unlock)]


class TagCreate(BaseModel):
    tag_name: str = Field(min_length=1, max_length=120)


class TagUpdate(BaseModel):
    tag_name: str = Field(min_length=1, max_length=120)


@router.get("", response_model=OkResponse)
def list_tags(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    return OkResponse(data={"tags": cf.list_client_tags(db, user.clinic_id)})


@router.post("", response_model=OkResponse, status_code=status.HTTP_201_CREATED)
def create_tag(
    body: TagCreate,
    _unlock: UnlockDep,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    name = body.tag_name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tag name is required.")
    exists = (
        db.query(ClientTagDefinition)
        .filter(
            ClientTagDefinition.clinic_id == user.clinic_id,
            ClientTagDefinition.tag_name == name,
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tag already exists.")
    row = ClientTagDefinition(
        clinic_id=user.clinic_id,
        tag_name=name,
        short_code=None,
        sync_priority=0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return OkResponse(
        data={
            "tag": {
                "client_tag_id": row.client_tag_id,
                "tag_name": row.tag_name,
            }
        }
    )


@router.patch("/{tag_id}", response_model=OkResponse)
def update_tag(
    tag_id: int,
    body: TagUpdate,
    _unlock: UnlockDep,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    row = (
        db.query(ClientTagDefinition)
        .filter(
            ClientTagDefinition.client_tag_id == tag_id,
            ClientTagDefinition.clinic_id == user.clinic_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found.")
    name = body.tag_name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tag name is required.")
    clash = (
        db.query(ClientTagDefinition)
        .filter(
            ClientTagDefinition.clinic_id == user.clinic_id,
            ClientTagDefinition.tag_name == name,
            ClientTagDefinition.client_tag_id != tag_id,
        )
        .first()
    )
    if clash:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tag already exists.")
    row.tag_name = name
    db.commit()
    db.refresh(row)
    return OkResponse(
        data={
            "tag": {
                "client_tag_id": row.client_tag_id,
                "tag_name": row.tag_name,
            }
        }
    )


@router.delete("/{tag_id}", response_model=OkResponse)
def delete_tag(
    tag_id: int,
    _unlock: UnlockDep,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    row = (
        db.query(ClientTagDefinition)
        .filter(
            ClientTagDefinition.client_tag_id == tag_id,
            ClientTagDefinition.clinic_id == user.clinic_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found.")
    (
        db.query(ClientTag)
        .filter(ClientTag.client_tag_id == tag_id)
        .delete(synchronize_session=False)
    )
    db.delete(row)
    db.commit()
    return OkResponse(data={"deleted": True})
