"""Treatment plan domain helpers (desk MVP parity with legacy TreatmentPlanActions)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from app import media as media_svc
from app.models import (
    Client,
    PriceOption,
    Treatment,
    TreatmentPlan,
    TreatmentSubPlan,
    TreatmentSubPlanPhoto,
    User,
)

IST = ZoneInfo("Asia/Kolkata")
SUB_PLAN_TYPES = {"Definitive", "Tentative"}
MAX_PHOTOS_PER_SUB_PLAN = 10


def now_ist() -> datetime:
    return datetime.now(IST)


def _trim(value: str | None) -> str | None:
    if value is None:
        return None
    t = str(value).strip()
    return t or None


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return dt.isoformat()


def _client(db: Session, clinic_id: int, client_id: int) -> Client:
    row = (
        db.query(Client)
        .filter(Client.client_id == client_id, Client.clinic_id == clinic_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return row


def _plan_query(db: Session, clinic_id: int, plan_id: int) -> TreatmentPlan | None:
    return (
        db.query(TreatmentPlan)
        .options(
            joinedload(TreatmentPlan.sub_plans)
            .joinedload(TreatmentSubPlan.treatment),
            joinedload(TreatmentPlan.sub_plans)
            .joinedload(TreatmentSubPlan.chosen_price_option),
            joinedload(TreatmentPlan.sub_plans)
            .joinedload(TreatmentSubPlan.photos),
        )
        .filter(
            TreatmentPlan.plan_id == plan_id,
            TreatmentPlan.clinic_id == clinic_id,
            TreatmentPlan.visible.is_(True),
        )
        .first()
    )


def get_plan_or_404(db: Session, clinic_id: int, plan_id: int) -> TreatmentPlan:
    plan = _plan_query(db, clinic_id, plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Treatment plan not found")
    return plan


def assert_unlocked(plan: TreatmentPlan) -> None:
    if plan.locked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plan is locked and cannot be edited",
        )


def list_catalog(db: Session, clinic_id: int) -> list[dict[str, Any]]:
    rows = (
        db.query(Treatment)
        .filter(Treatment.clinic_id == clinic_id, Treatment.active.is_(True))
        .order_by(Treatment.sort_order.asc(), Treatment.name.asc())
        .all()
    )
    return [{"treatment_id": t.treatment_id, "name": t.name} for t in rows]


def list_catalog_browse(db: Session, clinic_id: int) -> list[dict[str, Any]]:
    """Rich catalog for mobile Treats tab (parity with PHP listCatalogBrowse)."""
    treatments = (
        db.query(Treatment)
        .options(
            joinedload(Treatment.photos),
            joinedload(Treatment.price_options).joinedload(PriceOption.photos),
        )
        .filter(Treatment.clinic_id == clinic_id, Treatment.active.is_(True))
        .order_by(Treatment.sort_order.asc(), Treatment.name.asc())
        .all()
    )
    out: list[dict[str, Any]] = []
    for t in treatments:
        treatment_photos = [
            url
            for ph in sorted(t.photos, key=lambda p: (p.sort_order, p.photo_id))
            if (url := media_svc.resolve_media_key(ph.photo_url))
        ]
        price_options_raw = sorted(
            t.price_options,
            key=lambda p: (float(p.price or 0), p.price_option_id),
        )
        price_options: list[dict[str, Any]] = []
        all_photos = list(treatment_photos)
        prices: list[float] = []
        for po in price_options_raw:
            option_photos = [
                url
                for ph in sorted(po.photos, key=lambda p: p.photo_id)
                if (url := media_svc.resolve_media_key(ph.photo_url))
            ]
            all_photos.extend(option_photos)
            prices.append(float(po.price or 0))
            price_options.append(
                {
                    "id": po.price_option_id,
                    "label": po.label,
                    "price": float(po.price or 0),
                    "explainer": po.explainer,
                    "is_foc": bool(po.is_foc),
                    "photos": option_photos,
                }
            )
        price_count = len(price_options)
        out.append(
            {
                "id": t.treatment_id,
                "name": t.name,
                "short_explainer": t.short_explainer,
                "default_appts": int(t.default_appts or 0),
                "photos": treatment_photos,
                "all_photos": all_photos,
                "photo_count": len(all_photos),
                "price_options": price_options,
                "price_count": price_count,
                "min_price": min(prices) if price_count else None,
                "max_price": max(prices) if price_count else None,
            }
        )
    return out


def list_price_options(db: Session, clinic_id: int, treatment_id: int) -> list[dict[str, Any]]:
    t = (
        db.query(Treatment)
        .filter(Treatment.treatment_id == treatment_id, Treatment.clinic_id == clinic_id)
        .first()
    )
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Treatment not found")
    rows = (
        db.query(PriceOption)
        .filter(PriceOption.treatment_id == treatment_id)
        .order_by(PriceOption.price.asc(), PriceOption.price_option_id.asc())
        .all()
    )
    return [
        {
            "price_option_id": p.price_option_id,
            "treatment_id": p.treatment_id,
            "label": p.label,
            "price": float(p.price),
            "explainer": p.explainer,
            "is_foc": p.is_foc,
        }
        for p in rows
    ]


def _photo_out(photo: TreatmentSubPlanPhoto) -> dict[str, Any]:
    return {
        "photo_id": photo.photo_id,
        "key": photo.photo_url,
        "url": media_svc.resolve_media_key(photo.photo_url),
    }


def _sub_plan_price(sp: TreatmentSubPlan) -> float | None:
    if sp.is_foc:
        return 0.0
    if sp.chosen_price_option is None:
        return None
    return float(sp.chosen_price_option.price) * max(int(sp.qty or 1), 1)


def serialize_plan(plan: TreatmentPlan) -> dict[str, Any]:
    total_cost = 0.0
    total_foc = 0
    unpriced = 0
    all_photos: list[dict[str, Any]] = []
    sub_out: list[dict[str, Any]] = []

    for sp in plan.sub_plans:
        price = _sub_plan_price(sp)
        if sp.is_foc:
            total_foc += 1
        elif price is None:
            unpriced += 1
        else:
            total_cost += price

        photos = [_photo_out(p) for p in sp.photos]
        all_photos.extend(photos)
        sub_out.append(
            {
                "sub_plan_id": sp.sub_plan_id,
                "treatment_id": sp.treatment_id,
                "treatment_name": sp.treatment.name if sp.treatment else None,
                "type": sp.type,
                "complaint_text": sp.complaint_text,
                "location_text": sp.location_text,
                "tooth_fdi": sp.tooth_fdi,
                "qty": sp.qty,
                "notes": sp.notes,
                "chosen_price_option_id": sp.chosen_price_option_id,
                "price_amount": price,
                "price_label": sp.chosen_price_option.label if sp.chosen_price_option else None,
                "is_foc": sp.is_foc,
                "photos": photos,
            }
        )

    return {
        "plan_id": plan.plan_id,
        "clinic_id": plan.clinic_id,
        "client_id": plan.client_id,
        "title": plan.title,
        "notes": plan.notes,
        "locked_at": _iso(plan.locked_at),
        "created_at": _iso(plan.created_at),
        "total_cost": None if unpriced else total_cost,
        "unpriced_count": unpriced,
        "total_foc": total_foc,
        "photos": all_photos,
        "sub_plans": sub_out,
    }


def serialize_timeline_item(plan: TreatmentPlan) -> dict[str, Any]:
    data = serialize_plan(plan)
    summary = []
    for sp in data["sub_plans"][:2]:
        name = sp["treatment_name"] or "Treatment"
        qty = sp["qty"] or 1
        summary.append(f"{name} ×{qty}" if qty and qty != 1 else name)
    extra = len(data["sub_plans"]) - 2
    if extra > 0:
        summary.append(f"+{extra}")
    return {
        "plan_id": data["plan_id"],
        "title": data["title"] or "Treatment plan",
        "notes": data["notes"],
        "created_at": data["created_at"],
        "locked_at": data["locked_at"],
        "total_cost": data["total_cost"],
        "sub_plans": [
            {
                "sub_plan_id": sp["sub_plan_id"],
                "treatment_name": sp["treatment_name"],
                "qty": sp["qty"],
                "price_amount": sp["price_amount"],
            }
            for sp in data["sub_plans"]
        ],
        "photos": data["photos"],
        "summary": " · ".join(summary) if summary else None,
    }


def list_client_plans(db: Session, clinic_id: int, client_id: int) -> list[dict[str, Any]]:
    _client(db, clinic_id, client_id)
    rows = (
        db.query(TreatmentPlan)
        .options(
            joinedload(TreatmentPlan.sub_plans).joinedload(TreatmentSubPlan.treatment),
            joinedload(TreatmentPlan.sub_plans).joinedload(TreatmentSubPlan.chosen_price_option),
            joinedload(TreatmentPlan.sub_plans).joinedload(TreatmentSubPlan.photos),
        )
        .filter(
            TreatmentPlan.clinic_id == clinic_id,
            TreatmentPlan.client_id == client_id,
            TreatmentPlan.visible.is_(True),
        )
        .order_by(TreatmentPlan.created_at.asc())
        .all()
    )
    return [serialize_timeline_item(p) for p in rows]


def _parse_plan_body(raw: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid plan JSON") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Invalid plan JSON")
    return data


def _validate_sub_plan_dicts(db: Session, clinic_id: int, subs: list[Any]) -> list[dict[str, Any]]:
    if not isinstance(subs, list) or not subs:
        raise HTTPException(status_code=400, detail="Add at least one treatment")
    out: list[dict[str, Any]] = []
    for i, raw in enumerate(subs):
        if not isinstance(raw, dict):
            raise HTTPException(status_code=400, detail=f"Invalid treatment row {i + 1}")
        tid = int(raw.get("treatment_id") or 0)
        if tid <= 0:
            raise HTTPException(status_code=400, detail=f"Select a treatment for row {i + 1}")
        t = (
            db.query(Treatment)
            .filter(
                Treatment.treatment_id == tid,
                Treatment.clinic_id == clinic_id,
                Treatment.active.is_(True),
            )
            .first()
        )
        if not t:
            raise HTTPException(status_code=400, detail=f"Unknown treatment on row {i + 1}")
        sp_type = str(raw.get("type") or "Definitive")
        if sp_type not in SUB_PLAN_TYPES:
            sp_type = "Definitive"
        qty = int(raw.get("qty") or 1)
        if qty < 1:
            qty = 1
        out.append(
            {
                "sub_plan_id": int(raw["id"]) if raw.get("id") else None,
                "treatment_id": tid,
                "type": sp_type,
                "complaint_text": _trim(raw.get("complaint_text")),
                "location_text": _trim(raw.get("location_text")),
                "tooth_fdi": _trim(raw.get("tooth_fdi")),
                "qty": qty,
                "notes": _trim(raw.get("notes")),
                "keep_photo_keys": [
                    str(k).strip()
                    for k in (raw.get("keep_photo_keys") or raw.get("keep_photo_urls") or [])
                    if str(k).strip()
                ],
            }
        )
    return out


async def _upload_row_photos(files: list[UploadFile], start_index: int = 0) -> list[str]:
    if len(files) > MAX_PHOTOS_PER_SUB_PLAN:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_PHOTOS_PER_SUB_PLAN} photos per treatment",
        )
    keys: list[str] = []
    for i, upload in enumerate(files):
        if not upload.filename:
            continue
        raw = await upload.read()
        mime = media_svc.validate_photo_file(upload.content_type, len(raw), upload.filename)
        key = media_svc.upload_bytes(
            raw,
            filename=upload.filename,
            content_type=mime,
            index=start_index + i,
        )
        # Prefer tplan prefix for clarity
        if not key.startswith("upload/tplan/"):
            # rewrite by re-uploading path is wasteful; keep default upload/ key (compatible)
            pass
        keys.append(key)
    return keys


def create_plan(
    db: Session,
    *,
    clinic_id: int,
    client_id: int,
    user: User,
    body: dict[str, Any],
    photos_by_row: dict[int, list[str]],
) -> TreatmentPlan:
    _client(db, clinic_id, client_id)
    subs = _validate_sub_plan_dicts(db, clinic_id, body.get("sub_plans") or [])
    plan = TreatmentPlan(
        clinic_id=clinic_id,
        client_id=client_id,
        user_id=user.user_id,
        title=_trim(body.get("title")),
        notes=_trim(body.get("notes")),
        visible=True,
    )
    db.add(plan)
    db.flush()

    for idx, sp in enumerate(subs):
        row = TreatmentSubPlan(
            plan_id=plan.plan_id,
            treatment_id=sp["treatment_id"],
            type=sp["type"],
            complaint_text=sp["complaint_text"],
            location_text=sp["location_text"],
            tooth_fdi=sp["tooth_fdi"],
            qty=sp["qty"],
            notes=sp["notes"],
            user_id=user.user_id,
        )
        db.add(row)
        db.flush()
        for order, key in enumerate(photos_by_row.get(idx, [])):
            db.add(
                TreatmentSubPlanPhoto(sub_plan_id=row.sub_plan_id, photo_url=key, sort_order=order)
            )

    db.commit()
    return get_plan_or_404(db, clinic_id, plan.plan_id)


def update_plan(
    db: Session,
    *,
    clinic_id: int,
    plan_id: int,
    user: User,
    body: dict[str, Any],
    photos_by_row: dict[int, list[str]],
) -> TreatmentPlan:
    plan = get_plan_or_404(db, clinic_id, plan_id)
    assert_unlocked(plan)
    subs = _validate_sub_plan_dicts(db, clinic_id, body.get("sub_plans") or [])

    # Preserve pricing when sub_plan id resent
    old_pricing: dict[int, tuple[int | None, bool]] = {
        sp.sub_plan_id: (sp.chosen_price_option_id, sp.is_foc) for sp in plan.sub_plans
    }

    plan.title = _trim(body.get("title"))
    if "notes" in body:
        plan.notes = _trim(body.get("notes"))

    for sp in list(plan.sub_plans):
        for photo in list(sp.photos):
            db.delete(photo)
        db.delete(sp)
    db.flush()

    for idx, sp in enumerate(subs):
        prev_id = sp["sub_plan_id"]
        price_opt_id, is_foc = old_pricing.get(prev_id, (None, False)) if prev_id else (None, False)
        row = TreatmentSubPlan(
            plan_id=plan.plan_id,
            treatment_id=sp["treatment_id"],
            type=sp["type"],
            complaint_text=sp["complaint_text"],
            location_text=sp["location_text"],
            tooth_fdi=sp["tooth_fdi"],
            qty=sp["qty"],
            notes=sp["notes"],
            user_id=user.user_id,
            chosen_price_option_id=price_opt_id,
            is_foc=is_foc,
        )
        db.add(row)
        db.flush()
        keys = list(sp["keep_photo_keys"])
        keys.extend(photos_by_row.get(idx, []))
        keys = keys[:MAX_PHOTOS_PER_SUB_PLAN]
        for order, key in enumerate(keys):
            db.add(
                TreatmentSubPlanPhoto(sub_plan_id=row.sub_plan_id, photo_url=key, sort_order=order)
            )

    db.commit()
    return get_plan_or_404(db, clinic_id, plan.plan_id)


def soft_delete_plan(db: Session, clinic_id: int, plan_id: int) -> None:
    plan = get_plan_or_404(db, clinic_id, plan_id)
    plan.visible = False
    plan.deleted_at = now_ist()
    db.commit()


def update_pricing(db: Session, clinic_id: int, plan_id: int, body: dict[str, Any]) -> TreatmentPlan:
    plan = get_plan_or_404(db, clinic_id, plan_id)
    assert_unlocked(plan)

    if "title" in body:
        plan.title = _trim(body.get("title"))
    if "notes" in body:
        plan.notes = _trim(body.get("notes"))

    rows = body.get("sub_plans") or []
    if not isinstance(rows, list):
        raise HTTPException(status_code=400, detail="Invalid pricing payload")

    by_id = {sp.sub_plan_id: sp for sp in plan.sub_plans}
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        sid = int(raw.get("id") or raw.get("sub_plan_id") or 0)
        sp = by_id.get(sid)
        if not sp:
            continue
        is_foc = bool(raw.get("is_foc"))
        opt_id = raw.get("price_option_id")
        if is_foc:
            sp.is_foc = True
            sp.chosen_price_option_id = None
            continue
        sp.is_foc = False
        if opt_id is None or opt_id == "" or int(opt_id) <= 0:
            sp.chosen_price_option_id = None
            continue
        opt_id = int(opt_id)
        opt = (
            db.query(PriceOption)
            .filter(
                PriceOption.price_option_id == opt_id,
                PriceOption.treatment_id == sp.treatment_id,
            )
            .first()
        )
        if not opt:
            raise HTTPException(status_code=400, detail=f"Invalid price option for sub-plan {sid}")
        sp.chosen_price_option_id = opt_id

    db.flush()

    lock_plan = bool(body.get("lock_plan"))
    unpriced = sum(
        1 for sp in plan.sub_plans if not sp.is_foc and sp.chosen_price_option_id is None
    )
    if lock_plan:
        if unpriced:
            raise HTTPException(
                status_code=400,
                detail="Price every treatment (or mark FOC) before locking",
            )
        if not plan.sub_plans:
            raise HTTPException(status_code=400, detail="Cannot lock an empty plan")
        plan.locked_at = now_ist()

    db.commit()
    return get_plan_or_404(db, clinic_id, plan.plan_id)
