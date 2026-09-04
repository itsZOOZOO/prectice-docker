from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import OkResponse
from app import whatsapp as wa

router = APIRouter(prefix="/settings", tags=["settings"])


class WhatsAppSettingsUpdate(BaseModel):
    wa_enabled: bool | None = None
    wa_api_key: str | None = Field(default=None, max_length=255)
    wa_api_url: str | None = Field(default=None, max_length=500)
    clear_api_key: bool = False


@router.get("/whatsapp", response_model=OkResponse)
def whatsapp_status(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    return OkResponse(data=wa.whatsapp_status(db, user.clinic_id))


@router.patch("/whatsapp", response_model=OkResponse)
def update_whatsapp(
    body: WhatsAppSettingsUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    data = wa.update_whatsapp_settings(
        db,
        user.clinic_id,
        wa_enabled=body.wa_enabled,
        wa_api_key=body.wa_api_key,
        wa_api_url=body.wa_api_url,
        clear_api_key=body.clear_api_key,
    )
    return OkResponse(data=data)
