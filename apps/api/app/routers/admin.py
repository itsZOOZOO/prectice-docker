"""Platform admin API — superadmin only (all clinics + users)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import hash_password, require_superadmin
from app.db import get_db
from app.models import Clinic, PdfTemplate, User
from app.schemas import OkResponse

router = APIRouter(prefix="/admin", tags=["admin"])

ASSIGNABLE_ROLES = frozenset({"admin", "doctor", "staff"})
MAX_BG_BYTES = 5 * 1024 * 1024
ALLOWED_BG_MIME = frozenset({"image/jpeg", "image/jpg", "image/png", "image/webp"})


class AdminClinicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    clinic_id: int
    clinic_name: str
    clinic_address: str | None = None
    clinic_phone: str | None = None
    clinic_email: str | None = None
    is_active: bool
    user_count: int = 0


class ClinicCreateBody(BaseModel):
    clinic_name: str = Field(min_length=1, max_length=255)
    clinic_address: str | None = None
    clinic_phone: str | None = None
    clinic_email: str | None = None
    is_active: bool = True


class ClinicUpdateBody(BaseModel):
    clinic_name: str | None = Field(default=None, min_length=1, max_length=255)
    clinic_address: str | None = None
    clinic_phone: str | None = None
    clinic_email: str | None = None
    is_active: bool | None = None


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    clinic_id: int
    username: str
    full_name: str
    role: str
    email: str | None = None
    active: bool


class UserCreateBody(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=6, max_length=128)
    email: str | None = None
    role: str = "staff"


class UserUpdateBody(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: str | None = None
    role: str | None = None
    active: bool | None = None


class PasswordResetBody(BaseModel):
    password: str = Field(min_length=6, max_length=128)


class WhatsappLetterheadForm(BaseModel):
    clinic_name: str = ""
    doctor_name: str = ""
    tagline: str = ""
    qualification: str = ""
    timing: str = ""
    website: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""


class PrintLetterheadForm(BaseModel):
    date_x: float = 175
    date_y: float = 38
    content_x: float = 30
    tagline: str = "Your Smile Matters :)"


class LetterheadSaveBody(BaseModel):
    whatsapp: WhatsappLetterheadForm
    print: PrintLetterheadForm
    remove_background: bool = False


def _clinic_out(db: Session, clinic: Clinic) -> dict:
    count = (
        db.query(func.count(User.user_id))
        .filter(User.clinic_id == clinic.clinic_id)
        .scalar()
        or 0
    )
    return AdminClinicOut(
        clinic_id=clinic.clinic_id,
        clinic_name=clinic.clinic_name,
        clinic_address=clinic.clinic_address,
        clinic_phone=clinic.clinic_phone,
        clinic_email=clinic.clinic_email,
        is_active=clinic.is_active,
        user_count=int(count),
    ).model_dump()


def _validate_assignable_role(role: str) -> str:
    r = (role or "").strip().lower()
    if r not in ASSIGNABLE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role must be one of: {', '.join(sorted(ASSIGNABLE_ROLES))}",
        )
    return r


def _require_clinic(db: Session, clinic_id: int) -> Clinic:
    clinic = db.get(Clinic, clinic_id)
    if not clinic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    return clinic


def _get_template(db: Session, clinic_id: int, template_type: str) -> PdfTemplate | None:
    return (
        db.query(PdfTemplate)
        .filter(PdfTemplate.clinic_id == clinic_id, PdfTemplate.template_type == template_type)
        .first()
    )


def _upsert_template(
    db: Session,
    *,
    clinic_id: int,
    template_type: str,
    header_content: str,
    footer_content: str,
    logo_path: str,
) -> PdfTemplate:
    row = _get_template(db, clinic_id, template_type)
    if row:
        row.header_content = header_content
        row.footer_content = footer_content
        row.logo_path = logo_path
        row.is_default = False
    else:
        row = PdfTemplate(
            clinic_id=clinic_id,
            template_type=template_type,
            header_content=header_content,
            footer_content=footer_content,
            logo_path=logo_path,
            is_default=False,
        )
        db.add(row)
    return row


def _bg_rel_key(clinic_id: int, ext: str = "jpg") -> str:
    safe = ext.lower().lstrip(".")
    if safe not in {"jpg", "jpeg", "png", "webp"}:
        safe = "jpg"
    if safe == "jpeg":
        safe = "jpg"
    return f"prescription_backgrounds/clinic_{clinic_id}_bg.{safe}"


def _cache_bg_locally(clinic_id: int, data: bytes, ext: str) -> Path:
    from app.prescription_pdf import ASSETS_DIR

    rel = _bg_rel_key(clinic_id, ext)
    dest = ASSETS_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return dest


@router.get("/clinics", response_model=OkResponse)
def list_clinics(
    _: Annotated[User, Depends(require_superadmin)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    rows = db.query(Clinic).order_by(Clinic.clinic_id.asc()).all()
    return OkResponse(data=[_clinic_out(db, c) for c in rows])


@router.post("/clinics", response_model=OkResponse, status_code=status.HTTP_201_CREATED)
def create_clinic(
    body: ClinicCreateBody,
    _: Annotated[User, Depends(require_superadmin)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    clinic = Clinic(
        clinic_name=body.clinic_name.strip(),
        clinic_address=body.clinic_address,
        clinic_phone=body.clinic_phone,
        clinic_email=body.clinic_email,
        is_active=body.is_active,
    )
    db.add(clinic)
    db.commit()
    db.refresh(clinic)
    return OkResponse(data=_clinic_out(db, clinic))


@router.get("/clinics/{clinic_id}", response_model=OkResponse)
def get_clinic(
    clinic_id: int,
    _: Annotated[User, Depends(require_superadmin)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    return OkResponse(data=_clinic_out(db, _require_clinic(db, clinic_id)))


@router.patch("/clinics/{clinic_id}", response_model=OkResponse)
def update_clinic(
    clinic_id: int,
    body: ClinicUpdateBody,
    _: Annotated[User, Depends(require_superadmin)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    clinic = _require_clinic(db, clinic_id)
    if body.clinic_name is not None:
        clinic.clinic_name = body.clinic_name.strip()
    if body.clinic_address is not None:
        clinic.clinic_address = body.clinic_address
    if body.clinic_phone is not None:
        clinic.clinic_phone = body.clinic_phone
    if body.clinic_email is not None:
        clinic.clinic_email = body.clinic_email
    if body.is_active is not None:
        clinic.is_active = body.is_active
    db.commit()
    db.refresh(clinic)
    return OkResponse(data=_clinic_out(db, clinic))


@router.get("/clinics/{clinic_id}/users", response_model=OkResponse)
def list_clinic_users(
    clinic_id: int,
    _: Annotated[User, Depends(require_superadmin)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    _require_clinic(db, clinic_id)
    rows = (
        db.query(User)
        .filter(User.clinic_id == clinic_id)
        .order_by(User.user_id.asc())
        .all()
    )
    return OkResponse(data=[AdminUserOut.model_validate(u).model_dump() for u in rows])


@router.post("/clinics/{clinic_id}/users", response_model=OkResponse, status_code=status.HTTP_201_CREATED)
def create_clinic_user(
    clinic_id: int,
    body: UserCreateBody,
    _: Annotated[User, Depends(require_superadmin)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    _require_clinic(db, clinic_id)
    username = body.username.strip().lower()
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")
    user = User(
        clinic_id=clinic_id,
        username=username,
        full_name=body.full_name.strip(),
        email=body.email,
        role=_validate_assignable_role(body.role),
        password_hash=hash_password(body.password),
        active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return OkResponse(data=AdminUserOut.model_validate(user).model_dump())


@router.patch("/clinics/{clinic_id}/users/{user_id}", response_model=OkResponse)
def update_clinic_user(
    clinic_id: int,
    user_id: int,
    body: UserUpdateBody,
    actor: Annotated[User, Depends(require_superadmin)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    user = (
        db.query(User)
        .filter(User.user_id == user_id, User.clinic_id == clinic_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if body.full_name is not None:
        user.full_name = body.full_name.strip()
    if body.email is not None:
        user.email = body.email
    if body.role is not None:
        if user.role == "superadmin" and user.user_id != actor.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change another superadmin's role here",
            )
        if user.role != "superadmin":
            user.role = _validate_assignable_role(body.role)
    if body.active is not None:
        if user.user_id == actor.user_id and not body.active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate yourself")
        user.active = body.active
    db.commit()
    db.refresh(user)
    return OkResponse(data=AdminUserOut.model_validate(user).model_dump())


@router.post("/clinics/{clinic_id}/users/{user_id}/reset-password", response_model=OkResponse)
def reset_user_password(
    clinic_id: int,
    user_id: int,
    body: PasswordResetBody,
    _: Annotated[User, Depends(require_superadmin)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    user = (
        db.query(User)
        .filter(User.user_id == user_id, User.clinic_id == clinic_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.password_hash = hash_password(body.password)
    db.commit()
    return OkResponse(data={"user_id": user_id, "password_reset": True})


@router.get("/clinics/{clinic_id}/letterhead", response_model=OkResponse)
def get_letterhead(
    clinic_id: int,
    _: Annotated[User, Depends(require_superadmin)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    from app import media as media_svc
    from app.prescription_pdf import (
        fetch_template,
        print_form_from_raw,
        whatsapp_form_from_raw,
    )

    _require_clinic(db, clinic_id)
    wa_raw = fetch_template(db, clinic_id, "whatsapp")
    print_raw = fetch_template(db, clinic_id, "print")
    wa = whatsapp_form_from_raw(wa_raw)
    pr = print_form_from_raw(print_raw)
    logo_path = wa.get("logo_path") or ""
    logo_url = media_svc.resolve_media_key(logo_path) if logo_path else None
    return OkResponse(
        data={
            "clinic_id": clinic_id,
            "whatsapp": {k: v for k, v in wa.items() if k != "logo_path"},
            "print": pr,
            "logo_path": logo_path or None,
            "logo_url": logo_url,
        }
    )


@router.put("/clinics/{clinic_id}/letterhead", response_model=OkResponse)
def save_letterhead(
    clinic_id: int,
    body: LetterheadSaveBody,
    _: Annotated[User, Depends(require_superadmin)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    from app.prescription_pdf import encode_print_template, encode_whatsapp_template

    _require_clinic(db, clinic_id)
    existing = _get_template(db, clinic_id, "whatsapp")
    logo_path = (existing.logo_path if existing else "") or ""
    if body.remove_background:
        logo_path = ""

    wa_enc = encode_whatsapp_template(body.whatsapp.model_dump(), logo_path=logo_path)
    pr_enc = encode_print_template(body.print.model_dump())
    _upsert_template(
        db,
        clinic_id=clinic_id,
        template_type="whatsapp",
        header_content=wa_enc["header_content"],
        footer_content=wa_enc["footer_content"],
        logo_path=wa_enc["logo_path"],
    )
    _upsert_template(
        db,
        clinic_id=clinic_id,
        template_type="print",
        header_content=pr_enc["header_content"],
        footer_content=pr_enc["footer_content"],
        logo_path=pr_enc["logo_path"],
    )
    db.commit()
    return OkResponse(
        data={
            "clinic_id": clinic_id,
            "logo_path": logo_path or None,
            "saved": True,
        }
    )


@router.post("/clinics/{clinic_id}/letterhead/background", response_model=OkResponse)
async def upload_letterhead_background(
    clinic_id: int,
    _: Annotated[User, Depends(require_superadmin)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
) -> OkResponse:
    from app import media as media_svc
    from app.prescription_pdf import encode_whatsapp_template, fetch_template, whatsapp_form_from_raw

    _require_clinic(db, clinic_id)
    mime = (file.content_type or "").split(";")[0].strip().lower()
    name = file.filename or "background.jpg"
    lower = name.lower()
    if mime not in ALLOWED_BG_MIME and not lower.endswith((".jpg", ".jpeg", ".png", ".webp")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Background must be JPG, PNG, or WebP")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if len(data) > MAX_BG_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Background must be under 5MB")

    ext = (
        "png"
        if lower.endswith(".png") or mime == "image/png"
        else "webp"
        if lower.endswith(".webp") or mime == "image/webp"
        else "jpg"
    )
    key = _bg_rel_key(clinic_id, ext)
    _cache_bg_locally(clinic_id, data, ext)
    media_svc.upload_bytes_key(data, key=key, content_type=mime or f"image/{ext}")

    wa_form = whatsapp_form_from_raw(fetch_template(db, clinic_id, "whatsapp"))
    enc = encode_whatsapp_template(wa_form, logo_path=key)
    _upsert_template(
        db,
        clinic_id=clinic_id,
        template_type="whatsapp",
        header_content=enc["header_content"],
        footer_content=enc["footer_content"],
        logo_path=key,
    )
    db.commit()
    return OkResponse(
        data={
            "logo_path": key,
            "logo_url": media_svc.presign_get(key, expires_in=3600),
        }
    )


@router.delete("/clinics/{clinic_id}/letterhead/background", response_model=OkResponse)
def remove_letterhead_background(
    clinic_id: int,
    _: Annotated[User, Depends(require_superadmin)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    from app.prescription_pdf import encode_whatsapp_template, fetch_template, whatsapp_form_from_raw

    _require_clinic(db, clinic_id)
    wa_form = whatsapp_form_from_raw(fetch_template(db, clinic_id, "whatsapp"))
    enc = encode_whatsapp_template(wa_form, logo_path="")
    _upsert_template(
        db,
        clinic_id=clinic_id,
        template_type="whatsapp",
        header_content=enc["header_content"],
        footer_content=enc["footer_content"],
        logo_path="",
    )
    db.commit()
    return OkResponse(data={"logo_path": None, "removed": True})


@router.post("/clinics/{clinic_id}/letterhead/preview")
async def preview_letterhead(
    clinic_id: int,
    _: Annotated[User, Depends(require_superadmin)],
    db: Annotated[Session, Depends(get_db)],
    template_type: Annotated[Literal["whatsapp", "print"], Form()] = "whatsapp",
    payload: Annotated[str, Form()] = "{}",
    background: UploadFile | None = File(None),
) -> Response:
    """Preview PDF from unsaved form. Optional background file for WhatsApp."""
    from app.prescription_pdf import preview_from_forms

    _require_clinic(db, clinic_id)
    try:
        data: dict[str, Any] = json.loads(payload or "{}")
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payload JSON: {e}",
        ) from e

    logo_file: str | None = None
    tmp_path: Path | None = None
    try:
        if background is not None and background.filename:
            raw = await background.read()
            if raw:
                if len(raw) > MAX_BG_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Background must be under 5MB",
                    )
                suffix = Path(background.filename).suffix or ".jpg"
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                tmp.write(raw)
                tmp.close()
                tmp_path = Path(tmp.name)
                logo_file = str(tmp_path)

        existing = _get_template(db, clinic_id, "whatsapp")
        logo_path = (existing.logo_path if existing else "") or ""
        if data.get("remove_background"):
            logo_path = ""

        pdf_bytes = preview_from_forms(
            template_type=template_type,
            whatsapp=data.get("whatsapp") if isinstance(data.get("whatsapp"), dict) else {},
            print_form=data.get("print") if isinstance(data.get("print"), dict) else {},
            logo_path=logo_path,
            logo_file=logo_file,
        )
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="letterhead-preview-{template_type}.pdf"',
            "Cache-Control": "private, no-store",
        },
    )


# --- Integrations (Call Intelligence) ---------------------------------------


class CallIntelligenceUpdateBody(BaseModel):
    enabled: bool | None = None
    api_token: str | None = None
    clear_token: bool = False
    api_base_url: str | None = None
    run_smoke_test: bool = True


@router.get("/clinics/{clinic_id}/integrations/call-intelligence", response_model=OkResponse)
def get_call_intelligence(
    clinic_id: int,
    _: Annotated[User, Depends(require_superadmin)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    from app import call_intelligence_svc as ci

    _require_clinic(db, clinic_id)
    return OkResponse(data=ci.admin_status(db, clinic_id))


@router.patch("/clinics/{clinic_id}/integrations/call-intelligence", response_model=OkResponse)
def update_call_intelligence(
    clinic_id: int,
    body: CallIntelligenceUpdateBody,
    _: Annotated[User, Depends(require_superadmin)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    from app import call_intelligence_svc as ci

    _require_clinic(db, clinic_id)
    data = ci.save_admin_config(
        db,
        clinic_id,
        enabled=body.enabled,
        api_token=body.api_token,
        clear_token=body.clear_token,
        api_base_url=body.api_base_url,
        run_smoke_test=body.run_smoke_test,
    )
    return OkResponse(data=data)


@router.post("/clinics/{clinic_id}/integrations/call-intelligence/smoke-test", response_model=OkResponse)
def smoke_test_call_intelligence(
    clinic_id: int,
    _: Annotated[User, Depends(require_superadmin)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    from app import call_intelligence_svc as ci

    _require_clinic(db, clinic_id)
    return OkResponse(data=ci.smoke_test(db, clinic_id))


# --- Integrations (Lead Intelligence) ---------------------------------------


class LeadIntelligenceUpdateBody(BaseModel):
    enabled: bool | None = None
    api_token: str | None = None
    clear_token: bool = False
    api_base_url: str | None = None
    run_smoke_test: bool = True


@router.get("/clinics/{clinic_id}/integrations/lead-intelligence", response_model=OkResponse)
def get_lead_intelligence(
    clinic_id: int,
    _: Annotated[User, Depends(require_superadmin)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    from app import lead_intelligence_svc as li

    _require_clinic(db, clinic_id)
    return OkResponse(data=li.admin_status(db, clinic_id))


@router.patch("/clinics/{clinic_id}/integrations/lead-intelligence", response_model=OkResponse)
def update_lead_intelligence(
    clinic_id: int,
    body: LeadIntelligenceUpdateBody,
    _: Annotated[User, Depends(require_superadmin)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    from app import lead_intelligence_svc as li

    _require_clinic(db, clinic_id)
    data = li.save_admin_config(
        db,
        clinic_id,
        enabled=body.enabled,
        api_token=body.api_token,
        clear_token=body.clear_token,
        api_base_url=body.api_base_url,
        run_smoke_test=body.run_smoke_test,
    )
    return OkResponse(data=data)


@router.post("/clinics/{clinic_id}/integrations/lead-intelligence/smoke-test", response_model=OkResponse)
def smoke_test_lead_intelligence(
    clinic_id: int,
    _: Annotated[User, Depends(require_superadmin)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    from app import lead_intelligence_svc as li

    _require_clinic(db, clinic_id)
    return OkResponse(data=li.smoke_test(db, clinic_id))


# --- Integrations (WhatsApp) ------------------------------------------------


class WhatsAppIntegrationUpdateBody(BaseModel):
    wa_enabled: bool | None = None
    inbox_enabled: bool | None = None
    api_token: str | None = None
    clear_token: bool = False
    wa_api_url: str | None = None
    wa_inbox_api_url: str | None = None
    run_smoke_test: bool = True


@router.get("/clinics/{clinic_id}/integrations/whatsapp", response_model=OkResponse)
def get_whatsapp_integration(
    clinic_id: int,
    _: Annotated[User, Depends(require_superadmin)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    from app import whatsapp as wa

    _require_clinic(db, clinic_id)
    return OkResponse(data=wa.admin_status(db, clinic_id))


@router.patch("/clinics/{clinic_id}/integrations/whatsapp", response_model=OkResponse)
def update_whatsapp_integration(
    clinic_id: int,
    body: WhatsAppIntegrationUpdateBody,
    _: Annotated[User, Depends(require_superadmin)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    from app import whatsapp as wa

    _require_clinic(db, clinic_id)
    data = wa.save_admin_config(
        db,
        clinic_id,
        wa_enabled=body.wa_enabled,
        inbox_enabled=body.inbox_enabled,
        api_token=body.api_token,
        clear_token=body.clear_token,
        wa_api_url=body.wa_api_url,
        wa_inbox_api_url=body.wa_inbox_api_url,
        run_smoke_test=body.run_smoke_test,
    )
    return OkResponse(data=data)


@router.post("/clinics/{clinic_id}/integrations/whatsapp/smoke-test", response_model=OkResponse)
def smoke_test_whatsapp_integration(
    clinic_id: int,
    _: Annotated[User, Depends(require_superadmin)],
    db: Annotated[Session, Depends(get_db)],
) -> OkResponse:
    from app import whatsapp as wa

    _require_clinic(db, clinic_id)
    return OkResponse(data=wa.smoke_test(db, clinic_id))
