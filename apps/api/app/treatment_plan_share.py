"""Treatment plan public share links + access analytics."""

from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app import media as media_svc
from app import treatment_plans as tp
from app.config import get_settings
from app.models import (
    Client,
    Clinic,
    PriceOptionPhoto,
    TreatmentPhoto,
    TreatmentPlan,
    TreatmentPlanLinkAccessLog,
    TreatmentPlanSharedLink,
    TreatmentSubPlan,
)

IST = ZoneInfo("Asia/Kolkata")
CODE_RE = re.compile(r"^[A-Za-z0-9]{7}$")
SLUG_RE = re.compile(r"^[a-z0-9-]+$")


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return dt.isoformat()


def plan_public_base_url() -> str:
    return get_settings().plan_public_base_url.rstrip("/")


def public_path(short_code: str, plan_slug: str) -> str:
    return f"{short_code}/{plan_slug}"


def share_url(short_code: str, plan_slug: str) -> str:
    return f"{plan_public_base_url()}/{public_path(short_code, plan_slug)}"


def create_url_slug(title: str | None) -> str:
    raw = (title or "treatment-plan").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return (slug[:80] or "treatment-plan")


def generate_short_code(db: Session) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    for _ in range(40):
        code = "".join(secrets.choice(alphabet) for _ in range(7))
        exists = (
            db.query(TreatmentPlanSharedLink.id)
            .filter(TreatmentPlanSharedLink.short_code == code)
            .first()
        )
        if not exists:
            return code
    raise HTTPException(status_code=500, detail="Could not allocate share code")


def _link_status(row: TreatmentPlanSharedLink, now: datetime | None = None) -> str:
    if not row.is_active:
        return "inactive"
    now = now or datetime.now(IST)
    exp = row.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=IST)
    if now > exp:
        return "expired"
    return "active"


def format_link(row: TreatmentPlanSharedLink) -> dict[str, Any]:
    path = public_path(row.short_code, row.plan_slug)
    return {
        "id": row.id,
        "plan_id": row.plan_id,
        "short_code": row.short_code,
        "plan_slug": row.plan_slug,
        "public_path": path,
        "share_url": share_url(row.short_code, row.plan_slug),
        "expires_at": _iso(row.expires_at),
        "validity_days": row.validity_days,
        "notes": row.notes,
        "is_active": row.is_active,
        "status": _link_status(row),
        "view_count": row.view_count,
        "last_accessed": _iso(row.last_accessed),
        "created_at": _iso(row.created_at),
    }


def generate_link(
    db: Session,
    *,
    clinic_id: int,
    user_id: int,
    plan_id: int,
    validity_days: int = 7,
    notes: str = "",
) -> dict[str, Any]:
    plan = tp.get_plan_or_404(db, clinic_id, plan_id)
    days = max(1, min(int(validity_days or 7), 365))
    code = generate_short_code(db)
    slug = create_url_slug(plan.title)
    expires = datetime.now(IST) + timedelta(days=days)
    row = TreatmentPlanSharedLink(
        plan_id=plan.plan_id,
        clinic_id=clinic_id,
        user_id=user_id,
        token=secrets.token_hex(20),
        short_code=code,
        plan_slug=slug,
        expires_at=expires,
        validity_days=days,
        notes=(notes or "").strip() or None,
        is_active=True,
        view_count=0,
    )
    db.add(row)
    db.flush()
    data = format_link(row)
    return {"link": data, "share_url": data["share_url"], "public_path": data["public_path"]}


def list_links(db: Session, clinic_id: int, plan_id: int) -> list[dict[str, Any]]:
    tp.get_plan_or_404(db, clinic_id, plan_id)
    rows = (
        db.query(TreatmentPlanSharedLink)
        .filter(
            TreatmentPlanSharedLink.plan_id == plan_id,
            TreatmentPlanSharedLink.clinic_id == clinic_id,
        )
        .order_by(TreatmentPlanSharedLink.created_at.desc())
        .all()
    )
    return [format_link(r) for r in rows]


def deactivate_link(db: Session, clinic_id: int, plan_id: int, link_id: int) -> None:
    tp.get_plan_or_404(db, clinic_id, plan_id)
    row = (
        db.query(TreatmentPlanSharedLink)
        .filter(
            TreatmentPlanSharedLink.id == link_id,
            TreatmentPlanSharedLink.plan_id == plan_id,
            TreatmentPlanSharedLink.clinic_id == clinic_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Share link not found")
    row.is_active = False
    db.flush()


def _compute_stats(db: Session, link_id: int) -> dict[str, Any]:
    total = (
        db.query(func.count(TreatmentPlanLinkAccessLog.id))
        .filter(TreatmentPlanLinkAccessLog.shared_link_id == link_id)
        .scalar()
        or 0
    )
    unique = (
        db.query(func.count(func.distinct(TreatmentPlanLinkAccessLog.ip_address)))
        .filter(TreatmentPlanLinkAccessLog.shared_link_id == link_id)
        .scalar()
        or 0
    )
    avg_s = (
        db.query(func.avg(TreatmentPlanLinkAccessLog.session_duration))
        .filter(
            TreatmentPlanLinkAccessLog.shared_link_id == link_id,
            TreatmentPlanLinkAccessLog.session_duration > 0,
        )
        .scalar()
    )
    max_s = (
        db.query(func.max(TreatmentPlanLinkAccessLog.session_duration))
        .filter(TreatmentPlanLinkAccessLog.shared_link_id == link_id)
        .scalar()
        or 0
    )
    return {
        "total_views": int(total),
        "unique_views": int(unique),
        "avg_session_seconds": round(float(avg_s or 0), 1),
        "max_session_seconds": int(max_s or 0),
    }


def analytics_for_link(db: Session, clinic_id: int, plan_id: int, link_id: int) -> dict[str, Any]:
    tp.get_plan_or_404(db, clinic_id, plan_id)
    row = (
        db.query(TreatmentPlanSharedLink)
        .filter(
            TreatmentPlanSharedLink.id == link_id,
            TreatmentPlanSharedLink.plan_id == plan_id,
            TreatmentPlanSharedLink.clinic_id == clinic_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Share link not found")
    logs = (
        db.query(TreatmentPlanLinkAccessLog)
        .filter(TreatmentPlanLinkAccessLog.shared_link_id == link_id)
        .order_by(
            TreatmentPlanLinkAccessLog.accessed_at.desc(),
            TreatmentPlanLinkAccessLog.id.desc(),
        )
        .limit(200)
        .all()
    )
    stats = _compute_stats(db, link_id)
    return {
        "link": format_link(row),
        **stats,
        "access_logs": [
            {
                "id": log.id,
                "ip_address": log.ip_address or "",
                "user_agent": log.user_agent or "",
                "session_duration": log.session_duration,
                "accessed_at": _iso(log.accessed_at),
                "page_views": log.page_views,
            }
            for log in logs
        ],
    }


def _media_urls(keys: list[str]) -> list[str]:
    out: list[str] = []
    for key in keys:
        url = media_svc.resolve_media_key(key)
        if url:
            out.append(url)
    return out


def serialize_public_plan(db: Session, plan: TreatmentPlan) -> dict[str, Any]:
    """Staff-free plan payload for patient page."""
    sub_out: list[dict[str, Any]] = []
    for sp in plan.sub_plans:
        t = sp.treatment
        price = None
        if sp.chosen_price_option and not sp.is_foc:
            price = float(sp.chosen_price_option.price or 0) * max(1, sp.qty or 1)

        sp_photos = _media_urls([p.photo_url for p in (sp.photos or [])])
        t_photos: list[str] = []
        po_photos: list[str] = []
        if t:
            t_photos = _media_urls(
                [
                    p.photo_url
                    for p in db.query(TreatmentPhoto)
                    .filter(TreatmentPhoto.treatment_id == t.treatment_id)
                    .order_by(TreatmentPhoto.sort_order.asc())
                    .all()
                ]
            )
        if sp.chosen_price_option_id:
            po_photos = _media_urls(
                [
                    p.photo_url
                    for p in db.query(PriceOptionPhoto)
                    .filter(PriceOptionPhoto.price_option_id == sp.chosen_price_option_id)
                    .all()
                ]
            )

        sub_out.append(
            {
                "sub_plan_id": sp.sub_plan_id,
                "type": sp.type,
                "treatment_name": t.name if t else "Treatment",
                "treatment_name_gu": (t.name_gu if t else None) or None,
                "short_explainer": t.short_explainer if t else None,
                "short_explainer_gu": t.short_explainer_gu if t else None,
                "badge_en": t.badge_en if t else None,
                "badge_gu": t.badge_gu if t else None,
                "recovery_days": t.recovery_days if t else None,
                "default_appts": int(t.default_appts or 0) if t else 0,
                "achievement_value": t.achievement_value if t else None,
                "achievement_label": t.achievement_label if t else None,
                "achievement_label_gu": t.achievement_label_gu if t else None,
                "complaint_text": sp.complaint_text,
                "location_text": sp.location_text,
                "tooth_fdi": sp.tooth_fdi or "",
                "qty": sp.qty,
                "notes": sp.notes,
                "is_foc": sp.is_foc,
                "price": price,
                "photos": sp_photos,
                "treatment_photos": t_photos,
                "price_option_photos": po_photos,
                "testimonials": [],
            }
        )

    clinic = db.query(Clinic).filter(Clinic.clinic_id == plan.clinic_id).first()
    client = (
        db.query(Client)
        .filter(Client.client_id == plan.client_id, Client.clinic_id == plan.clinic_id)
        .first()
    )
    return {
        "plan_id": plan.plan_id,
        "title": plan.title or "Treatment plan",
        "notes": plan.notes,
        "created_at": _iso(plan.created_at),
        "sub_plans": sub_out,
        "patient_name": client.name if client else "",
        "clinic_name": clinic.clinic_name if clinic else "",
        "clinic_phone": clinic.clinic_phone if clinic else "",
        "clinic_address": clinic.clinic_address if clinic else "",
    }


def resolve_public(
    db: Session,
    short_code: str,
    plan_slug: str,
    *,
    ip: str | None,
    user_agent: str | None,
) -> dict[str, Any]:
    if not CODE_RE.match(short_code) or not SLUG_RE.match(plan_slug):
        raise HTTPException(status_code=404, detail="This link is not available.")

    row = (
        db.query(TreatmentPlanSharedLink)
        .filter(
            TreatmentPlanSharedLink.short_code == short_code,
            TreatmentPlanSharedLink.plan_slug == plan_slug,
            TreatmentPlanSharedLink.is_active.is_(True),
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="This link is not available.")

    exp = row.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=IST)
    if datetime.now(IST) > exp:
        raise HTTPException(status_code=410, detail="This link has expired.")

    plan = (
        db.query(TreatmentPlan)
        .options(
            joinedload(TreatmentPlan.sub_plans).joinedload(TreatmentSubPlan.treatment),
            joinedload(TreatmentPlan.sub_plans).joinedload(TreatmentSubPlan.chosen_price_option),
            joinedload(TreatmentPlan.sub_plans).joinedload(TreatmentSubPlan.photos),
        )
        .filter(
            TreatmentPlan.plan_id == row.plan_id,
            TreatmentPlan.visible.is_(True),
        )
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="This link is not available.")

    log = TreatmentPlanLinkAccessLog(
        shared_link_id=row.id,
        ip_address=(ip or "")[:64] or None,
        user_agent=(user_agent or "unknown")[:500],
        session_duration=0,
        page_views=1,
    )
    db.add(log)
    row.view_count = int(row.view_count or 0) + 1
    row.last_accessed = datetime.now(IST)
    db.flush()

    plan_data = serialize_public_plan(db, plan)
    first = (plan_data.get("patient_name") or "").split(" ")[0]
    return {
        "plan": plan_data,
        "link": {
            "expires_at": _iso(row.expires_at),
            "validity_days": row.validity_days,
            "access_log_id": log.id,
            "short_code": row.short_code,
            "plan_slug": row.plan_slug,
        },
        "context": {
            "patient_name": first,
            "clinic_name": plan_data.get("clinic_name") or "",
            "clinic_phone": plan_data.get("clinic_phone") or "",
            "clinic_address": plan_data.get("clinic_address") or "",
        },
    }


def update_session(
    db: Session,
    short_code: str,
    plan_slug: str,
    access_log_id: int,
    duration_seconds: int,
) -> None:
    if access_log_id <= 0 or duration_seconds < 0:
        raise HTTPException(status_code=400, detail="Invalid session payload.")
    duration_seconds = min(int(duration_seconds), 86400)
    if not CODE_RE.match(short_code) or not SLUG_RE.match(plan_slug):
        raise HTTPException(status_code=404, detail="This link is not available.")

    log = (
        db.query(TreatmentPlanLinkAccessLog)
        .join(
            TreatmentPlanSharedLink,
            TreatmentPlanLinkAccessLog.shared_link_id == TreatmentPlanSharedLink.id,
        )
        .filter(
            TreatmentPlanLinkAccessLog.id == access_log_id,
            TreatmentPlanSharedLink.short_code == short_code,
            TreatmentPlanSharedLink.plan_slug == plan_slug,
            TreatmentPlanSharedLink.is_active.is_(True),
        )
        .first()
    )
    if not log:
        raise HTTPException(status_code=404, detail="Access log not found.")
    log.session_duration = duration_seconds
    db.flush()
