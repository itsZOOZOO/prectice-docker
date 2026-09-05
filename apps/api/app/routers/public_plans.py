"""Unauthenticated public treatment plan pages (myplan.in)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import treatment_plan_share as share
from app.db import get_db
from app.schemas import OkResponse

router = APIRouter(prefix="/public/treatment-plans", tags=["public-treatment-plans"])


class SessionIn(BaseModel):
    access_log_id: int = Field(gt=0)
    duration_seconds: int = Field(ge=0)


def _client_ip(request: Request, x_forwarded_for: str | None, x_real_ip: str | None) -> str:
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    if x_real_ip:
        return x_real_ip.strip()
    return request.client.host if request.client else ""


@router.get("/{code}/{slug}", response_model=OkResponse)
def get_public_plan(
    code: str,
    slug: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    x_forwarded_for: Annotated[str | None, Header()] = None,
    x_real_ip: Annotated[str | None, Header()] = None,
    x_client_user_agent: Annotated[str | None, Header()] = None,
    user_agent: Annotated[str | None, Header()] = None,
) -> OkResponse:
    ip = _client_ip(request, x_forwarded_for, x_real_ip)
    ua = (x_client_user_agent or user_agent or "")[:500]
    data = share.resolve_public(db, code, slug, ip=ip, user_agent=ua)
    db.commit()
    return OkResponse(data=data)


@router.post("/{code}/{slug}/session", response_model=OkResponse)
def post_public_session(
    code: str,
    slug: str,
    body: SessionIn,
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    share.update_session(db, code, slug, body.access_log_id, body.duration_seconds)
    db.commit()
    return OkResponse(data={"ok": True})
