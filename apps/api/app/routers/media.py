from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth import get_current_user
from app.media import resolve_many
from app.models import User
from app.schemas import OkResponse

router = APIRouter(prefix="/media", tags=["media"])


class MediaResolveRequest(BaseModel):
    keys: list[str] = Field(default_factory=list, max_length=200)


@router.post("/resolve", response_model=OkResponse)
def resolve_media(
    body: MediaResolveRequest,
    _user: Annotated[User, Depends(get_current_user)],
) -> OkResponse:
    # Deduplicate while preserving order
    seen: set[str] = set()
    keys: list[str] = []
    for k in body.keys:
        k = (k or "").strip()
        if not k or k in seen:
            continue
        seen.add(k)
        keys.append(k)
        if len(keys) >= 200:
            break
    return OkResponse(data={"urls": resolve_many(keys)})
