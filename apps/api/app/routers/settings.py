from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import OkResponse
from app import whatsapp as wa

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/whatsapp", response_model=OkResponse)
def whatsapp_status(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    return OkResponse(data=wa.whatsapp_status(db, user.clinic_id))


@router.patch("/whatsapp", response_model=OkResponse)
def update_whatsapp_forbidden(
    _: Annotated[User, Depends(get_current_user)],
) -> OkResponse:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="WhatsApp settings are managed by a superadmin.",
    )
