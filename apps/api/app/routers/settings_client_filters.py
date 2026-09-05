"""Saved client filter / patient list settings."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app import client_filters as cf
from app.db import get_db
from app.models import User
from app.schemas import OkResponse

router = APIRouter(prefix="/settings/client-filters", tags=["settings-client-filters"])
dashboard_router = APIRouter(prefix="/client-filters", tags=["client-filters"])


class FilterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    criteria: dict[str, Any] = Field(default_factory=dict)
    show_on_dashboard: bool = False
    sort_order: int = 0


class FilterUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    criteria: dict[str, Any] | None = None
    show_on_dashboard: bool | None = None
    sort_order: int | None = None


class PreviewIn(BaseModel):
    criteria: dict[str, Any] = Field(default_factory=dict)
    filter_id: int | None = None


class MemberIn(BaseModel):
    client_id: int


@router.get("", response_model=OkResponse)
def list_filters(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    dashboard_only: bool = Query(default=False),
) -> OkResponse:
    items = cf.list_filters(db, user.clinic_id, dashboard_only=dashboard_only)
    return OkResponse(data={"filters": items, "tags": cf.list_client_tags(user.clinic_id)})


@router.post("", response_model=OkResponse, status_code=status.HTTP_201_CREATED)
def create_filter(
    body: FilterCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    row = cf.create_filter(
        db,
        user.clinic_id,
        user.user_id,
        name=body.name,
        criteria=body.criteria,
        show_on_dashboard=body.show_on_dashboard,
        sort_order=body.sort_order,
    )
    db.commit()
    return OkResponse(data={"filter": row})


@router.post("/preview", response_model=OkResponse)
def preview_filter(
    body: PreviewIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    count = cf.preview_count(
        db,
        user.clinic_id,
        body.criteria,
        filter_id=body.filter_id,
    )
    return OkResponse(data={"count": count})


@router.patch("/{filter_id}", response_model=OkResponse)
def update_filter(
    filter_id: int,
    body: FilterUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    data = body.model_dump(exclude_unset=True)
    row = cf.update_filter(db, filter_id, user.clinic_id, data)
    db.commit()
    return OkResponse(data={"filter": row})


@router.delete("/{filter_id}", response_model=OkResponse)
def delete_filter(
    filter_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    cf.delete_filter(db, filter_id, user.clinic_id)
    db.commit()
    return OkResponse(data={"deleted": True})


@router.get("/{filter_id}/members", response_model=OkResponse)
def get_members(
    filter_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    members = cf.list_members(db, filter_id, user.clinic_id)
    return OkResponse(data={"members": members})


@router.post("/{filter_id}/members", response_model=OkResponse, status_code=status.HTTP_201_CREATED)
def post_member(
    filter_id: int,
    body: MemberIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    cf.add_member(db, filter_id, user.clinic_id, user.user_id, body.client_id)
    db.commit()
    return OkResponse(data={"added": True})


@router.delete("/{filter_id}/members/{client_id}", response_model=OkResponse)
def delete_member(
    filter_id: int,
    client_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    cf.remove_member(db, filter_id, user.clinic_id, client_id)
    db.commit()
    return OkResponse(data={"removed": True})


@dashboard_router.get("/dashboard", response_model=OkResponse)
def dashboard_filters(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    items = cf.list_filters(db, user.clinic_id, dashboard_only=True)
    return OkResponse(data={"filters": items})
