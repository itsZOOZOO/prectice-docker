from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app import client_filters as client_filters_svc
from app.datetime_local import parse_clinic_local_datetime
from app.db import get_db
from app import media as media_svc
from app.models import Bill, Client, ClientCheckinLog, MoneyReceipt, Note, NoteAttachment, User
from app.schemas import (
    CheckinOut,
    ClientCreate,
    ClientOut,
    ClientUpdate,
    NoteAttachmentOut,
    NoteCreate,
    NoteOut,
    OkResponse,
)


def _optional_clinic_datetime(value: str | None):
    try:
        return parse_clinic_local_datetime(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid datetime: {value}",
        ) from exc

router = APIRouter(prefix="/clients", tags=["clients"])


def _author_name(user: User | None) -> str | None:
    if not user:
        return None
    name = (user.full_name or "").strip()
    return name or user.username


def _pending_bills_by_client(db: Session, clinic_id: int, client_ids: list[int]) -> dict[int, dict]:
    """Latest collectable bill per client with remaining balance (desk checked-in Collect)."""
    if not client_ids:
        return {}
    bills = (
        db.query(Bill)
        .filter(
            Bill.clinic_id == clinic_id,
            Bill.client_id.in_(client_ids),
            Bill.visible.is_(True),
            func.lower(Bill.status).in_(("pending", "partial", "open")),
        )
        .order_by(Bill.issued_at.desc(), Bill.bill_id.desc())
        .all()
    )
    latest: dict[int, Bill] = {}
    for bill in bills:
        if bill.client_id not in latest:
            latest[bill.client_id] = bill
    if not latest:
        return {}

    bill_ids = [b.bill_id for b in latest.values()]
    paid_rows = (
        db.query(MoneyReceipt.bill_id, func.coalesce(func.sum(MoneyReceipt.amount), 0))
        .filter(MoneyReceipt.bill_id.in_(bill_ids), MoneyReceipt.visible.is_(True))
        .group_by(MoneyReceipt.bill_id)
        .all()
    )
    paid_map = {int(bill_id): float(paid or 0) for bill_id, paid in paid_rows}

    out: dict[int, dict] = {}
    for client_id, bill in latest.items():
        total = float(bill.amount_due or 0)
        paid = paid_map.get(bill.bill_id, 0.0)
        balance = max(0.0, total - paid)
        out[client_id] = {
            "pending_bill_id": bill.bill_id,
            "pending_amount": balance,
            "pending_bill_total": total,
            "pending_total_paid": paid,
        }
    return out


def _last_payments_by_client(db: Session, clinic_id: int, client_ids: list[int]) -> dict[int, dict]:
    """Most recent visible receipt per client (for checked-in last-payment strip)."""
    if not client_ids:
        return {}
    receipts = (
        db.query(MoneyReceipt)
        .filter(
            MoneyReceipt.clinic_id == clinic_id,
            MoneyReceipt.client_id.in_(client_ids),
            MoneyReceipt.visible.is_(True),
        )
        .order_by(MoneyReceipt.received_at.desc(), MoneyReceipt.receipt_id.desc())
        .all()
    )
    latest: dict[int, MoneyReceipt] = {}
    for r in receipts:
        if r.client_id not in latest:
            latest[r.client_id] = r
    if not latest:
        return {}

    bill_ids = [r.bill_id for r in latest.values() if r.bill_id]
    bill_totals: dict[int, float] = {}
    if bill_ids:
        for bill in db.query(Bill).filter(Bill.bill_id.in_(bill_ids)).all():
            bill_totals[bill.bill_id] = float(bill.amount_due or 0)

    out: dict[int, dict] = {}
    for client_id, r in latest.items():
        out[client_id] = {
            "last_payment_amount": float(r.amount or 0),
            "last_payment_mode": r.payment_mode,
            "last_payment_at": r.received_at.isoformat() if r.received_at else None,
            "last_payment_bill_total": bill_totals.get(r.bill_id) if r.bill_id else None,
        }
    return out


def _serialize_client(
    client: Client,
    pending: dict | None = None,
    last_payment: dict | None = None,
) -> dict:
    data = ClientOut.model_validate(client).model_dump()
    key = (client.profile_photo_url or "").strip() or None
    data["profile_photo_key"] = key
    data["profile_photo_url"] = media_svc.resolve_media_key(key) if key else None
    if pending:
        data["pending_bill_id"] = int(pending.get("pending_bill_id") or 0)
        data["pending_amount"] = float(pending.get("pending_amount") or 0)
        data["pending_bill_total"] = pending.get("pending_bill_total")
        data["pending_total_paid"] = float(pending.get("pending_total_paid") or 0)
    else:
        data["pending_bill_id"] = 0
        data["pending_amount"] = 0.0
        data["pending_bill_total"] = None
        data["pending_total_paid"] = 0.0
    if last_payment and last_payment.get("last_payment_amount"):
        data["last_payment_amount"] = float(last_payment["last_payment_amount"])
        data["last_payment_mode"] = last_payment.get("last_payment_mode")
        data["last_payment_at"] = last_payment.get("last_payment_at")
        data["last_payment_bill_total"] = last_payment.get("last_payment_bill_total")
    else:
        data["last_payment_amount"] = None
        data["last_payment_mode"] = None
        data["last_payment_at"] = None
        data["last_payment_bill_total"] = None
    return data


def _note_attachment_keys(db: Session, note: Note) -> list[tuple[int | None, str]]:
    rows = (
        db.query(NoteAttachment)
        .filter(NoteAttachment.note_id == note.note_id)
        .order_by(NoteAttachment.id.asc())
        .all()
    )
    items: list[tuple[int | None, str]] = [(r.id, r.attachment_url) for r in rows if r.attachment_url]
    if not items and note.attachment_url:
        items.append((None, note.attachment_url))
    return items


def _serialize_note(db: Session, note: Note) -> dict:
    author = db.get(User, note.user_id) if note.user_id else None
    attachments: list[dict] = []
    for attach_id, key in _note_attachment_keys(db, note):
        attachments.append(
            NoteAttachmentOut(
                id=attach_id,
                key=key,
                url=media_svc.resolve_media_key(key),
            ).model_dump()
        )
    return NoteOut(
        note_id=note.note_id,
        clinic_id=note.clinic_id,
        client_id=note.client_id,
        user_id=note.user_id,
        body=note.body or "",
        created_at=note.created_at,
        author_name=_author_name(author),
        attachments=attachments,
    ).model_dump()


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
    filter_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> OkResponse:
    query = db.query(Client).filter(Client.clinic_id == user.clinic_id, Client.visible.is_(True))

    if filter_id is not None:
        ids = client_filters_svc.client_ids_for_filter(db, user.clinic_id, filter_id)
        if not ids:
            return OkResponse(data={"total": 0, "items": []})
        query = query.filter(Client.client_id.in_(ids))

    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(Client.name.ilike(like), Client.number.ilike(like), Client.calling_name.ilike(like))
        )

    if checked_in is not None:
        query = query.filter(Client.check_in_status.is_(checked_in))

    total = query.count()
    rows = query.order_by(Client.updated_at.desc()).offset(offset).limit(limit).all()
    client_ids = [r.client_id for r in rows]
    pending_map = _pending_bills_by_client(db, user.clinic_id, client_ids)
    last_pay_map = _last_payments_by_client(db, user.clinic_id, client_ids)
    return OkResponse(
        data={
            "total": total,
            "items": [
                _serialize_client(
                    r,
                    pending_map.get(r.client_id),
                    last_pay_map.get(r.client_id),
                )
                for r in rows
            ],
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
    data = _serialize_client(client)

    from app import activity_log

    activity_log.client_created(
        db,
        clinic_id=user.clinic_id,
        actor_user_id=user.user_id,
        client_id=client.client_id,
        payload={"name": client.name},
    )

    return OkResponse(data=data)


@router.get("/{client_id}", response_model=OkResponse)
def get_client(
    client_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    client = _get_clinic_client(db, user.clinic_id, client_id)
    return OkResponse(data=_serialize_client(client))


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
    return OkResponse(data=_serialize_client(client))


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
async def create_note(
    client_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    body: str = Form(default=""),
    note_datetime: str | None = Form(default=None),
    files: Annotated[list[UploadFile] | None, File()] = None,
) -> OkResponse:
    _get_clinic_client(db, user.clinic_id, client_id)
    text = (body or "").strip()
    uploads = [f for f in (files or []) if f is not None and f.filename]
    if not text and not uploads:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Note text or attachment is required")
    if len(uploads) > media_svc.MAX_NOTE_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {media_svc.MAX_NOTE_FILES} files allowed per note",
        )

    created_at = _optional_clinic_datetime(note_datetime)
    note = Note(
        clinic_id=user.clinic_id,
        client_id=client_id,
        user_id=user.user_id,
        body=text,
        **({"created_at": created_at} if created_at else {}),
    )
    db.add(note)
    db.flush()

    for i, upload in enumerate(uploads):
        raw = await upload.read()
        mime = media_svc.validate_note_file(upload.content_type, len(raw), upload.filename or "file")
        key = media_svc.upload_bytes(raw, filename=upload.filename or "file", content_type=mime, index=i)
        db.add(
            NoteAttachment(
                note_id=note.note_id,
                clinic_id=user.clinic_id,
                attachment_url=key,
            )
        )

    db.commit()
    db.refresh(note)
    return OkResponse(data=_serialize_note(db, note))


@router.post("/{client_id}/notes/json", response_model=OkResponse, status_code=status.HTTP_201_CREATED)
def create_note_json(
    client_id: int,
    body: NoteCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    """Text-only note (JSON) — kept for scripts/tools."""
    _get_clinic_client(db, user.clinic_id, client_id)
    created_at = _optional_clinic_datetime(body.note_datetime)
    note = Note(
        clinic_id=user.clinic_id,
        client_id=client_id,
        user_id=user.user_id,
        body=body.body.strip(),
        **({"created_at": created_at} if created_at else {}),
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return OkResponse(data=_serialize_note(db, note))


def _get_visible_note(db: Session, clinic_id: int, client_id: int, note_id: int) -> Note:
    note = (
        db.query(Note)
        .filter(
            Note.note_id == note_id,
            Note.client_id == client_id,
            Note.clinic_id == clinic_id,
            Note.visible.is_(True),
        )
        .first()
    )
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note


@router.patch("/{client_id}/notes/{note_id}", response_model=OkResponse)
async def update_note(
    client_id: int,
    note_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    body: str = Form(default=""),
    note_datetime: str | None = Form(default=None),
    remove_attachment_ids: str | None = Form(default=None),
    files: Annotated[list[UploadFile] | None, File()] = None,
) -> OkResponse:
    """Update note text/datetime; optionally remove attachments and add new files."""
    _get_clinic_client(db, user.clinic_id, client_id)
    note = _get_visible_note(db, user.clinic_id, client_id, note_id)

    text = (body or "").strip()
    uploads = [f for f in (files or []) if f is not None and f.filename]

    remove_ids: list[int] = []
    if remove_attachment_ids:
        for part in remove_attachment_ids.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                remove_ids.append(int(part))
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid remove_attachment_ids: {part}",
                ) from exc

    existing = (
        db.query(NoteAttachment)
        .filter(NoteAttachment.note_id == note_id, NoteAttachment.clinic_id == user.clinic_id)
        .all()
    )
    by_id = {r.id: r for r in existing}
    for rid in remove_ids:
        if rid not in by_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Attachment not found: {rid}",
            )

    kept_count = len(existing) - len(remove_ids)
    if kept_count + len(uploads) > media_svc.MAX_NOTE_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {media_svc.MAX_NOTE_FILES} files allowed per note",
        )

    remaining_after = kept_count + len(uploads)
    # Legacy single attachment_url counts if no attachment rows
    if remaining_after == 0 and note.attachment_url and not existing:
        remaining_after = 1
    if not text and remaining_after == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Note text or attachment is required",
        )

    keys_to_delete: list[str] = []
    for rid in remove_ids:
        row = by_id[rid]
        if row.attachment_url:
            keys_to_delete.append(row.attachment_url)
        db.delete(row)

    note.body = text
    if note_datetime is not None and note_datetime.strip():
        parsed = _optional_clinic_datetime(note_datetime)
        if parsed is not None:
            note.created_at = parsed

    db.flush()

    start_index = kept_count
    for i, upload in enumerate(uploads):
        raw = await upload.read()
        mime = media_svc.validate_note_file(upload.content_type, len(raw), upload.filename or "file")
        key = media_svc.upload_bytes(
            raw, filename=upload.filename or "file", content_type=mime, index=start_index + i
        )
        db.add(
            NoteAttachment(
                note_id=note.note_id,
                clinic_id=user.clinic_id,
                attachment_url=key,
            )
        )

    db.commit()
    db.refresh(note)
    for key in keys_to_delete:
        media_svc.delete_object(key)
    return OkResponse(data=_serialize_note(db, note))


@router.delete("/{client_id}/notes/{note_id}", response_model=OkResponse)
def delete_note(
    client_id: int,
    note_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    """Soft-delete a note (visible=false). Attachments left in storage."""
    _get_clinic_client(db, user.clinic_id, client_id)
    note = _get_visible_note(db, user.clinic_id, client_id, note_id)
    note.visible = False
    db.commit()
    return OkResponse(data={"note_id": note_id, "deleted": True})


@router.delete("/{client_id}/notes/{note_id}/attachments/{attachment_id}", response_model=OkResponse)
def delete_note_attachment(
    client_id: int,
    note_id: int,
    attachment_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    _get_clinic_client(db, user.clinic_id, client_id)
    note = (
        db.query(Note)
        .filter(
            Note.note_id == note_id,
            Note.client_id == client_id,
            Note.clinic_id == user.clinic_id,
            Note.visible.is_(True),
        )
        .first()
    )
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    row = (
        db.query(NoteAttachment)
        .filter(
            NoteAttachment.id == attachment_id,
            NoteAttachment.note_id == note_id,
            NoteAttachment.clinic_id == user.clinic_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    key = row.attachment_url
    db.delete(row)
    db.commit()
    media_svc.delete_object(key)
    return OkResponse(data=_serialize_note(db, note))


@router.post("/{client_id}/photo", response_model=OkResponse)
async def upload_profile_photo(
    client_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
) -> OkResponse:
    client = _get_clinic_client(db, user.clinic_id, client_id)
    raw = await file.read()
    mime = media_svc.validate_photo_file(file.content_type, len(raw), file.filename or "photo.jpg")
    new_key = media_svc.upload_bytes(raw, filename=file.filename or "photo.jpg", content_type=mime, index=0)
    old_key = (client.profile_photo_url or "").strip() or None
    client.profile_photo_url = new_key
    db.commit()
    db.refresh(client)
    if old_key and old_key != new_key:
        media_svc.delete_object(old_key)
    return OkResponse(data=_serialize_client(client))
