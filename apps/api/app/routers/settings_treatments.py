"""Treatment catalog settings (pin fields, price options, photos)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.db import get_db
from app import media as media_svc
from app.models import (
    PriceOption,
    PriceOptionPhoto,
    Treatment,
    TreatmentPhoto,
    TreatmentSubPlan,
    User,
)
from app.schemas import OkResponse
from app.setup_access import require_setup_unlock

router = APIRouter(prefix="/settings/treatments", tags=["settings-treatments"])

UnlockDep = Annotated[None, Depends(require_setup_unlock)]


class PriceOptionIn(BaseModel):
    id: int | None = None
    price_option_id: int | None = None
    label: str = Field(min_length=1, max_length=255)
    price: float = 0
    explainer: str | None = None
    is_foc: bool = False


class TreatmentUpsert(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    short_explainer: str | None = None
    default_appts: int | None = None
    active: bool | None = None
    sort_order: int | None = None
    price_options: list[PriceOptionIn] = Field(default_factory=list)


class TreatmentActiveUpdate(BaseModel):
    active: bool


def _photo_out(photo_id: int, key: str, sort_order: int | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "photo_id": photo_id,
        "photo_url": media_svc.resolve_media_key(key),
        "key": key,
    }
    if sort_order is not None:
        out["sort_order"] = sort_order
    return out


def _price_option_out(po: PriceOption) -> dict[str, Any]:
    photos = sorted(po.photos, key=lambda p: p.photo_id)
    return {
        "id": po.price_option_id,
        "price_option_id": po.price_option_id,
        "label": po.label,
        "price": float(po.price or 0),
        "explainer": po.explainer,
        "is_foc": bool(po.is_foc),
        "photos": [_photo_out(ph.photo_id, ph.photo_url) for ph in photos],
    }


def _treatment_detail(t: Treatment) -> dict[str, Any]:
    photos = sorted(t.photos, key=lambda p: (p.sort_order, p.photo_id))
    options = sorted(t.price_options, key=lambda p: (float(p.price or 0), p.price_option_id))
    return {
        "id": t.treatment_id,
        "treatment_id": t.treatment_id,
        "name": t.name,
        "short_explainer": t.short_explainer,
        "default_appts": int(t.default_appts or 0),
        "active": bool(t.active),
        "sort_order": int(t.sort_order or 0),
        "price_options": [_price_option_out(po) for po in options],
        "photos": [_photo_out(ph.photo_id, ph.photo_url, ph.sort_order) for ph in photos],
        "price_option_count": len(options),
        "photo_count": len(photos),
    }


def _treatment_list_item(t: Treatment) -> dict[str, Any]:
    return {
        "id": t.treatment_id,
        "name": t.name,
        "short_explainer": t.short_explainer,
        "default_appts": int(t.default_appts or 0),
        "active": bool(t.active),
        "sort_order": int(t.sort_order or 0),
        "price_option_count": len(t.price_options or []),
        "photo_count": len(t.photos or []),
    }


def _get_treatment(db: Session, clinic_id: int, treatment_id: int, *, load_all: bool = False) -> Treatment:
    q = db.query(Treatment).filter(
        Treatment.treatment_id == treatment_id,
        Treatment.clinic_id == clinic_id,
    )
    if load_all:
        q = q.options(
            joinedload(Treatment.photos),
            joinedload(Treatment.price_options).joinedload(PriceOption.photos),
        )
    row = q.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Treatment not found")
    return row


def _option_id(body: PriceOptionIn) -> int | None:
    return body.id if body.id is not None else body.price_option_id


def _apply_price_options(db: Session, treatment: Treatment, options: list[PriceOptionIn]) -> None:
    existing = {po.price_option_id: po for po in treatment.price_options}
    keep_ids: set[int] = set()

    for item in options:
        oid = _option_id(item)
        label = item.label.strip()
        if not label:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Price option label required")
        if oid is not None and oid in existing:
            po = existing[oid]
            po.label = label
            po.price = item.price
            po.explainer = (item.explainer or "").strip() or None
            po.is_foc = bool(item.is_foc)
            keep_ids.add(oid)
        else:
            po = PriceOption(
                treatment_id=treatment.treatment_id,
                label=label,
                price=item.price,
                explainer=(item.explainer or "").strip() or None,
                is_foc=bool(item.is_foc),
            )
            db.add(po)
            treatment.price_options.append(po)

    to_delete = [po for pid, po in existing.items() if pid not in keep_ids]
    if to_delete:
        delete_ids = [po.price_option_id for po in to_delete]
        (
            db.query(TreatmentSubPlan)
            .filter(TreatmentSubPlan.chosen_price_option_id.in_(delete_ids))
            .update({TreatmentSubPlan.chosen_price_option_id: None}, synchronize_session=False)
        )
        for po in to_delete:
            db.delete(po)


async def _read_photo(upload: UploadFile) -> tuple[bytes, str]:
    if not upload.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename required")
    raw = await upload.read()
    mime = media_svc.validate_photo_file(upload.content_type, len(raw), upload.filename)
    return raw, mime


@router.get("", response_model=OkResponse)
def list_treatments(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    rows = (
        db.query(Treatment)
        .options(joinedload(Treatment.photos), joinedload(Treatment.price_options))
        .filter(Treatment.clinic_id == user.clinic_id)
        .order_by(Treatment.sort_order.asc(), Treatment.name.asc())
        .all()
    )
    return OkResponse(data={"treatments": [_treatment_list_item(t) for t in rows]})


@router.get("/{treatment_id}", response_model=OkResponse)
def get_treatment(
    treatment_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    t = _get_treatment(db, user.clinic_id, treatment_id, load_all=True)
    return OkResponse(data=_treatment_detail(t))


@router.post("", response_model=OkResponse, status_code=201)
def create_treatment(
    body: TreatmentUpsert,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],

    _: UnlockDep,
) -> OkResponse:
    t = Treatment(
        clinic_id=user.clinic_id,
        name=body.name.strip(),
        short_explainer=(body.short_explainer or "").strip() or None,
        default_appts=body.default_appts if body.default_appts is not None else 0,
        active=True if body.active is None else bool(body.active),
        sort_order=body.sort_order if body.sort_order is not None else 0,
    )
    db.add(t)
    db.flush()
    _apply_price_options(db, t, body.price_options)
    db.commit()
    t = _get_treatment(db, user.clinic_id, t.treatment_id, load_all=True)
    return OkResponse(data=_treatment_detail(t))


@router.put("/{treatment_id}", response_model=OkResponse)
def update_treatment(
    treatment_id: int,
    body: TreatmentUpsert,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],

    _: UnlockDep,
) -> OkResponse:
    t = _get_treatment(db, user.clinic_id, treatment_id, load_all=True)
    t.name = body.name.strip()
    if body.short_explainer is not None:
        t.short_explainer = body.short_explainer.strip() or None
    if body.default_appts is not None:
        t.default_appts = body.default_appts
    if body.active is not None:
        t.active = bool(body.active)
    if body.sort_order is not None:
        t.sort_order = body.sort_order
    _apply_price_options(db, t, body.price_options)
    db.commit()
    t = _get_treatment(db, user.clinic_id, treatment_id, load_all=True)
    return OkResponse(data=_treatment_detail(t))


@router.patch("/{treatment_id}/active", response_model=OkResponse)
def patch_treatment_active(
    treatment_id: int,
    body: TreatmentActiveUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],

    _: UnlockDep,
) -> OkResponse:
    t = _get_treatment(db, user.clinic_id, treatment_id)
    t.active = bool(body.active)
    db.commit()
    return OkResponse(data={"id": t.treatment_id, "active": bool(t.active)})


@router.delete("/{treatment_id}", response_model=OkResponse)
def delete_treatment(
    treatment_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],

    _: UnlockDep,
) -> OkResponse:
    t = _get_treatment(db, user.clinic_id, treatment_id, load_all=True)
    in_use = (
        db.query(TreatmentSubPlan.sub_plan_id)
        .filter(TreatmentSubPlan.treatment_id == treatment_id)
        .first()
    )
    if in_use:
        t.active = False
        db.commit()
        return OkResponse(data={"id": treatment_id, "deleted": False, "active": False})

    option_ids = [po.price_option_id for po in t.price_options]
    if option_ids:
        (
            db.query(TreatmentSubPlan)
            .filter(TreatmentSubPlan.chosen_price_option_id.in_(option_ids))
            .update({TreatmentSubPlan.chosen_price_option_id: None}, synchronize_session=False)
        )
    db.delete(t)
    db.commit()
    return OkResponse(data={"id": treatment_id, "deleted": True})


@router.post("/{treatment_id}/photos", response_model=OkResponse, status_code=201)
async def add_treatment_photo(
    treatment_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    _: UnlockDep,
    file: UploadFile = File(...),
) -> OkResponse:
    t = _get_treatment(db, user.clinic_id, treatment_id, load_all=True)
    raw, mime = await _read_photo(file)
    key = media_svc.upload_bytes(raw, filename=file.filename or "photo.jpg", content_type=mime, index=0)
    max_order = max((ph.sort_order for ph in t.photos), default=-1)
    photo = TreatmentPhoto(treatment_id=t.treatment_id, photo_url=key, sort_order=max_order + 1)
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return OkResponse(data=_photo_out(photo.photo_id, photo.photo_url, photo.sort_order))


@router.delete("/{treatment_id}/photos/{photo_id}", response_model=OkResponse)
def delete_treatment_photo(
    treatment_id: int,
    photo_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],

    _: UnlockDep,
) -> OkResponse:
    t = _get_treatment(db, user.clinic_id, treatment_id)
    photo = (
        db.query(TreatmentPhoto)
        .filter(TreatmentPhoto.photo_id == photo_id, TreatmentPhoto.treatment_id == t.treatment_id)
        .first()
    )
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")
    key = photo.photo_url
    db.delete(photo)
    db.commit()
    media_svc.delete_object(key)
    return OkResponse(data={"photo_id": photo_id, "deleted": True})


@router.post("/{treatment_id}/price-options/{option_id}/photos", response_model=OkResponse, status_code=201)
async def add_price_option_photo(
    treatment_id: int,
    option_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    _: UnlockDep,
    file: UploadFile = File(...),
) -> OkResponse:
    t = _get_treatment(db, user.clinic_id, treatment_id)
    po = (
        db.query(PriceOption)
        .filter(PriceOption.price_option_id == option_id, PriceOption.treatment_id == t.treatment_id)
        .first()
    )
    if not po:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Price option not found")
    raw, mime = await _read_photo(file)
    key = media_svc.upload_bytes(raw, filename=file.filename or "photo.jpg", content_type=mime, index=0)
    photo = PriceOptionPhoto(price_option_id=po.price_option_id, photo_url=key)
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return OkResponse(data=_photo_out(photo.photo_id, photo.photo_url))


@router.delete(
    "/{treatment_id}/price-options/{option_id}/photos/{photo_id}",
    response_model=OkResponse,
)
def delete_price_option_photo(
    treatment_id: int,
    option_id: int,
    photo_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    _: UnlockDep,
) -> OkResponse:
    t = _get_treatment(db, user.clinic_id, treatment_id)
    po = (
        db.query(PriceOption)
        .filter(PriceOption.price_option_id == option_id, PriceOption.treatment_id == t.treatment_id)
        .first()
    )
    if not po:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Price option not found")
    photo = (
        db.query(PriceOptionPhoto)
        .filter(
            PriceOptionPhoto.photo_id == photo_id,
            PriceOptionPhoto.price_option_id == po.price_option_id,
        )
        .first()
    )
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")
    key = photo.photo_url
    db.delete(photo)
    db.commit()
    media_svc.delete_object(key)
    return OkResponse(data={"photo_id": photo_id, "deleted": True})
