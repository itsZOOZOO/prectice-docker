from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Client, ClientCheckinLog, Note, User
from app.schemas import (
    CheckinOut,
    ClientCreate,
    ClientOut,
    ClientUpdate,
    NoteCreate,
    NoteOut,
    OkResponse,
)

router = APIRouter(prefix="/clients", tags=["clients"])


def _author_name(user: User | None) -> str | None:
    if not user:
        return None
    name = (user.full_name or "").strip()
    return name or user.username


def _serialize_note(db: Session, note: Note) -> dict:
    data = NoteOut.model_validate(note).model_dump()
    author = db.get(User, note.user_id) if note.user_id else None
    data["author_name"] = _author_name(author)
    return data


def _get_clinic_client(db: Session, clinic_id: int, client_id: int) -> Client:
    client = (
        db.query(Client)
        .filter(
            Client.client_id == client_id,
            Client.clinic_id == clinic_id,
            Client.visible.is_(True),
        )
        .first()
    )
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


@router.get("", response_model=OkResponse)
def list_clients(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    q: str | None = Query(default=None),
    checked_in: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> OkResponse:
    query = db.query(Client).filter(Client.clinic_id == user.clinic_id, Client.visible.is_(True))

    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(Client.name.ilike(like), Client.number.ilike(like), Client.calling_name.ilike(like)))

    if checked_in is not None:
        query = query.filter(Client.check_in_status.is_(checked_in))

    total = query.count()
    rows = query.order_by(Client.updated_at.desc()).offset(offset).limit(limit).all()
    return OkResponse(
        data={
            "total": total,
            "items": [ClientOut.model_validate(r).model_dump() for r in rows],
        }
    )


@router.post("", response_model=OkResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    body: ClientCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    client = Client(
        clinic_id=user.clinic_id,
        name=body.name.strip(),
        calling_name=body.calling_name,
        number=body.number,
        country_code=body.country_code,
        place=body.place,
        age=body.age,
        gender=body.gender,
        date_of_birth=body.date_of_birth,
        status=body.status,
        lead_source=body.lead_source,
        reference=body.reference,
        client_personal_note=body.client_personal_note,
        created_by=user.user_id,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return OkResponse(data=ClientOut.model_validate(client).model_dump())


@router.get("/{client_id}", response_model=OkResponse)
def get_client(
    client_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    client = _get_clinic_client(db, user.clinic_id, client_id)
    return OkResponse(data=ClientOut.model_validate(client).model_dump())


@router.patch("/{client_id}", response_model=OkResponse)
def update_client(
    client_id: int,
    body: ClientUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    client = _get_clinic_client(db, user.clinic_id, client_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        if key == "name" and isinstance(value, str):
            value = value.strip()
        setattr(client, key, value)
    db.commit()
    db.refresh(client)
    return OkResponse(data=ClientOut.model_validate(client).model_dump())


@router.post("/{client_id}/check-in", response_model=OkResponse)
def check_in(
    client_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    client = _get_clinic_client(db, user.clinic_id, client_id)
    now = datetime.now(timezone.utc)
    client.check_in_status = True
    client.checked_in_at = now
    db.add(
        ClientCheckinLog(
            clinic_id=user.clinic_id,
            client_id=client.client_id,
            user_id=user.user_id,
            action="check_in",
        )
    )
    db.commit()
    db.refresh(client)
    return OkResponse(
        data=CheckinOut(
            client_id=client.client_id,
            check_in_status=client.check_in_status,
            checked_in_at=client.checked_in_at,
        ).model_dump()
    )


@router.post("/{client_id}/check-out", response_model=OkResponse)
def check_out(
    client_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    client = _get_clinic_client(db, user.clinic_id, client_id)
    client.check_in_status = False
    client.checked_in_at = None
    db.add(
        ClientCheckinLog(
            clinic_id=user.clinic_id,
            client_id=client.client_id,
            user_id=user.user_id,
            action="check_out",
        )
    )
    db.commit()
    db.refresh(client)
    return OkResponse(
        data=CheckinOut(
            client_id=client.client_id,
            check_in_status=client.check_in_status,
            checked_in_at=client.checked_in_at,
        ).model_dump()
    )


@router.get("/{client_id}/notes", response_model=OkResponse)
def list_notes(
    client_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    _get_clinic_client(db, user.clinic_id, client_id)
    rows = (
        db.query(Note)
        .filter(
            Note.clinic_id == user.clinic_id,
            Note.client_id == client_id,
            Note.visible.is_(True),
        )
        .order_by(Note.created_at.desc())
        .all()
    )
    return OkResponse(data=[_serialize_note(db, r) for r in rows])


@router.post("/{client_id}/notes", response_model=OkResponse, status_code=status.HTTP_201_CREATED)
def create_note(
    client_id: int,
    body: NoteCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    _get_clinic_client(db, user.clinic_id, client_id)
    note = Note(
        clinic_id=user.clinic_id,
        client_id=client_id,
        user_id=user.user_id,
        body=body.body.strip(),
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return OkResponse(data=_serialize_note(db, note))
