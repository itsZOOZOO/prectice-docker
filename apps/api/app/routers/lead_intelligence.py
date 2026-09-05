"""Lead Intelligence status + response-log proxy (setup-PIN gated)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app import lead_intelligence_svc as li
from app.db import get_db
from app.models import User
from app.schemas import OkResponse
from app.setup_access import require_setup_unlock

router = APIRouter(prefix="/statistics/lead-intelligence", tags=["lead-intelligence"])
status_router = APIRouter(prefix="/settings", tags=["lead-intelligence"])


@status_router.get("/lead-intelligence", response_model=OkResponse)
def lead_intelligence_status(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    return OkResponse(data=li.clinic_status(db, user.clinic_id))


@router.get("/response-log", response_model=OkResponse, dependencies=[Depends(require_setup_unlock)])
def response_log(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    period: str | None = Query(None),
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    ym: str | None = Query(None),
    limit: int | None = Query(None),
    duty: str | None = Query(None),
    all_groups: str | None = Query(None),
    group_or: list[int] = Query(default=[]),
    group_and: list[int] = Query(default=[]),
) -> OkResponse:
    data = li.response_log(
        db,
        user.clinic_id,
        {
            "period": period,
            "from": date_from,
            "to": date_to,
            "ym": ym,
            "limit": limit,
            "duty": duty,
            "all_groups": all_groups,
            "group_or": group_or,
            "group_and": group_and,
        },
    )
    return OkResponse(data=data)
