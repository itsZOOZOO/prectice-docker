"""Per-clinic WhatsApp send via wa.aarogyams.com (appointment_confirm)."""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from datetime import date, time as time_of_day
from typing import Any

from sqlalchemy.orm import Session

from app.models import Client, ClientPhone, ClinicSetting

DEFAULT_WA_API_URL = "https://wa.aarogyams.com/api.php"
DISABLED_MESSAGE = "WhatsApp messaging is not enabled for this clinic."
PRESCRIPTION_WA_TTL = 7 * 24 * 3600  # 7 days


def get_setting(db: Session, clinic_id: int, key: str, default: str = "") -> str:
    row = (
        db.query(ClinicSetting)
        .filter(ClinicSetting.clinic_id == clinic_id, ClinicSetting.setting_key == key)
        .first()
    )
    if row and row.setting_value is not None and str(row.setting_value).strip() != "":
        return str(row.setting_value).strip()
    return default


def whatsapp_status(db: Session, clinic_id: int) -> dict[str, bool | str | None]:
    wa_enabled = get_setting(db, clinic_id, "wa_enabled", "0") == "1"
    key = get_setting(db, clinic_id, "wa_api_key", "")
    url = get_setting(db, clinic_id, "wa_api_url", "") or DEFAULT_WA_API_URL
    has_key = bool(key)
    preview = None
    if has_key:
        preview = ("…" + key[-4:]) if len(key) > 4 else "••••"
    return {
        "enabled": wa_enabled and has_key,
        "wa_enabled": wa_enabled,
        "has_api_key": has_key,
        "api_key_preview": preview,
        "wa_api_url": url,
    }


def upsert_setting(db: Session, clinic_id: int, key: str, value: str | None) -> None:
    row = (
        db.query(ClinicSetting)
        .filter(ClinicSetting.clinic_id == clinic_id, ClinicSetting.setting_key == key)
        .first()
    )
    if row:
        row.setting_value = value
    else:
        db.add(ClinicSetting(clinic_id=clinic_id, setting_key=key, setting_value=value))


def update_whatsapp_settings(
    db: Session,
    clinic_id: int,
    *,
    wa_enabled: bool | None = None,
    wa_api_key: str | None = None,
    wa_api_url: str | None = None,
    clear_api_key: bool = False,
) -> dict[str, bool | str | None]:
    if wa_enabled is not None:
        upsert_setting(db, clinic_id, "wa_enabled", "1" if wa_enabled else "0")
    if clear_api_key:
        upsert_setting(db, clinic_id, "wa_api_key", "")
    elif wa_api_key is not None:
        trimmed = wa_api_key.strip()
        if trimmed:
            upsert_setting(db, clinic_id, "wa_api_key", trimmed)
    if wa_api_url is not None:
        trimmed_url = wa_api_url.strip()
        upsert_setting(db, clinic_id, "wa_api_url", trimmed_url or DEFAULT_WA_API_URL)
    db.commit()
    return whatsapp_status(db, clinic_id)


def is_enabled(db: Session, clinic_id: int) -> bool:
    return bool(whatsapp_status(db, clinic_id)["enabled"])


def api_url(db: Session, clinic_id: int) -> str:
    url = get_setting(db, clinic_id, "wa_api_url", "")
    return url or DEFAULT_WA_API_URL


def api_key(db: Session, clinic_id: int) -> str:
    return get_setting(db, clinic_id, "wa_api_key", "")


def resolve_phone(
    *,
    form_phone: str | None,
    client: Client | None,
    db: Session,
) -> str:
    if form_phone and form_phone.strip():
        return form_phone.strip()
    if client and client.number and client.number.strip():
        return client.number.strip()
    if client:
        primary = (
            db.query(ClientPhone)
            .filter(ClientPhone.client_id == client.client_id, ClientPhone.is_primary.is_(True))
            .first()
        )
        if primary and primary.phone:
            return primary.phone.strip()
        any_phone = (
            db.query(ClientPhone)
            .filter(ClientPhone.client_id == client.client_id)
            .order_by(ClientPhone.id.asc())
            .first()
        )
        if any_phone and any_phone.phone:
            return any_phone.phone.strip()
    return ""


def normalize_recipient(phone: str) -> str | None:
    digits = re.sub(r"[^0-9]", "", phone)
    n = len(digits)
    if n == 10:
        return "91" + digits
    if n == 11 and digits[0] == "0":
        return "44" + digits[1:]
    if 11 <= n <= 15:
        return digits
    return None


def format_appointment_datetime(appt_date: date, appt_time: time_of_day) -> str:
    # Match legacy: "Feb 9 Monday at 10:30 AM"
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    hour = appt_time.hour % 12 or 12
    ampm = "AM" if appt_time.hour < 12 else "PM"
    return (
        f"{months[appt_date.month - 1]} {appt_date.day} {weekdays[appt_date.weekday()]} "
        f"at {hour}:{appt_time.minute:02d} {ampm}"
    )


def send_appointment_confirm(
    db: Session,
    *,
    clinic_id: int,
    phone: str,
    patient_name: str,
    appt_date: date,
    appt_time: time_of_day,
) -> dict[str, Any]:
    if not is_enabled(db, clinic_id):
        return {"success": False, "message": DISABLED_MESSAGE, "response": None}

    recipient = normalize_recipient(phone)
    if not recipient:
        return {
            "success": False,
            "message": "Invalid phone number format (must be 10-15 digits)",
            "response": None,
        }

    when = format_appointment_datetime(appt_date, appt_time)
    payload = {
        "to": recipient,
        "type": "template",
        "template_name": "appointment_confirm",
        "language": "en",
        "header_params": [when],
        "template_params": [when, patient_name],
        "contact_name": patient_name,
    }
    return _post_template(db, clinic_id, payload)


def format_missed_datetime(appt_date: date, appt_time: time_of_day) -> str:
    # Match PHP: "Mon, 05 Sep 2026 at 10:30 AM"
    weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    hour = appt_time.hour % 12 or 12
    ampm = "AM" if appt_time.hour < 12 else "PM"
    return (
        f"{weekdays[appt_date.weekday()]}, {appt_date.day:02d} {months[appt_date.month - 1]} "
        f"{appt_date.year} at {hour}:{appt_time.minute:02d} {ampm}"
    )


def send_missed_appointment_reminder(
    db: Session,
    *,
    clinic_id: int,
    phone: str,
    patient_name: str,
    appt_date: date,
    appt_time: time_of_day,
    clinic_contact: str,
) -> dict[str, Any]:
    if not is_enabled(db, clinic_id):
        return {"success": False, "message": DISABLED_MESSAGE, "response": None}

    recipient = normalize_recipient(phone)
    if not recipient:
        return {
            "success": False,
            "message": "Invalid phone number format (must be 10-15 digits)",
            "response": None,
        }

    when = format_missed_datetime(appt_date, appt_time)
    payload = {
        "to": recipient,
        "type": "template",
        "template_name": "missed_appointment_english",
        "language": "en_US",
        "template_params": [patient_name, when, clinic_contact],
        "contact_name": patient_name,
    }
    return _post_template(db, clinic_id, payload)


def send_prescription(
    db: Session,
    *,
    clinic_id: int,
    user_id: int,
    prescription_id: int,
) -> dict[str, Any]:
    """Generate letterhead PDF, upload to S3, send WA template with file_url."""
    if not is_enabled(db, clinic_id):
        return {"success": False, "message": DISABLED_MESSAGE, "response": None, "note_id": None}

    from app import media as media_svc
    from app.models import Note, Prescription
    from app.prescription_pdf import generate_letterhead_pdf

    rx = (
        db.query(Prescription)
        .filter(
            Prescription.prescription_id == prescription_id,
            Prescription.clinic_id == clinic_id,
            Prescription.visible.is_(True),
        )
        .first()
    )
    if not rx:
        return {"success": False, "message": "Prescription not found", "response": None, "note_id": None}

    client = db.get(Client, rx.client_id)
    if not client or client.clinic_id != clinic_id:
        return {"success": False, "message": "Prescription not found", "response": None, "note_id": None}

    phone = resolve_phone(form_phone=None, client=client, db=db)
    recipient = normalize_recipient(phone) if phone else None
    if not recipient:
        return {
            "success": False,
            "message": "No WhatsApp-enabled phone number for this patient",
            "response": None,
            "note_id": None,
        }

    client_name = (client.name or "").strip() or "Patient"
    safe_name = re.sub(r'[/\\:*?"<>|]+', "", client_name).strip() or "Patient"
    pdf_name = f"{safe_name} - Prescription.pdf"

    try:
        pdf_bytes = generate_letterhead_pdf(db, clinic_id, prescription_id)
    except Exception as e:  # noqa: BLE001
        return {"success": False, "message": f"PDF failed: {e}", "response": None, "note_id": None}

    try:
        key = media_svc.upload_bytes_key(
            pdf_bytes,
            key=f"prescriptions/wa/{clinic_id}/{prescription_id}_{int(time.time())}.pdf",
            content_type="application/pdf",
        )
        file_url = media_svc.presign_get(key, expires_in=PRESCRIPTION_WA_TTL)
    except Exception as e:  # noqa: BLE001
        return {"success": False, "message": f"Upload failed: {e}", "response": None, "note_id": None}

    payload = {
        "to": recipient,
        "type": "template",
        "template_name": "prescription_message",
        "language": "en",
        "file_url": file_url,
        "name": pdf_name,
        "template_params": [client_name],
        "contact_name": client_name,
    }
    result = _post_template(db, clinic_id, payload)
    note_id = None
    if result.get("success"):
        note = Note(
            clinic_id=clinic_id,
            client_id=client.client_id,
            user_id=user_id,
            body="Prescription message sent successfully.",
        )
        db.add(note)
        db.commit()
        db.refresh(note)
        note_id = note.note_id
    result["note_id"] = note_id
    result["file_url"] = file_url
    return result


def send_warranty_card(
    db: Session,
    *,
    clinic_id: int,
    user_id: int,
    card_id: int,
) -> dict[str, Any]:
    """Generate warranty PDF, upload to S3, send WA template wrnty_membrshp_plan_card."""
    if not is_enabled(db, clinic_id):
        return {"success": False, "message": DISABLED_MESSAGE, "response": None, "note_id": None}

    from app import media as media_svc
    from app.models import CardIssued, CardType, Note, ProductMembershipType
    from app.warranty_pdf import generate_warranty_card_pdf

    card = (
        db.query(CardIssued)
        .filter(
            CardIssued.id == card_id,
            CardIssued.clinic_id == clinic_id,
            CardIssued.visible.is_(True),
        )
        .first()
    )
    if not card:
        return {"success": False, "message": "Warranty card not found", "response": None, "note_id": None}

    client = db.get(Client, card.client_id)
    if not client or client.clinic_id != clinic_id:
        return {"success": False, "message": "Warranty card not found", "response": None, "note_id": None}

    phone = resolve_phone(form_phone=None, client=client, db=db)
    recipient = normalize_recipient(phone) if phone else None
    if not recipient:
        return {
            "success": False,
            "message": "No WhatsApp-enabled phone number for this patient",
            "response": None,
            "note_id": None,
        }

    client_name = (client.name or "").strip() or "Patient"
    card_type = db.get(CardType, card.card_type_id)
    product = db.get(ProductMembershipType, card.product_id)
    card_type_name = (card_type.type_name if card_type else "") or "Warranty card"
    product_name = (product.name if product else "") or ""
    units = max(1, int(card.number_of_units or 1))
    product_membership = (
        f"{product_name} ({units} units)" if product_name else f"{units} units"
    )
    period = f"{int(card.warranty_period or 0)} days"
    pdf_name = f"Warranty Card - {re.sub(r'[/\\\\:*?\"<>|]+', '', client_name).strip() or 'Patient'}.pdf"

    try:
        pdf_bytes = generate_warranty_card_pdf(db, clinic_id, card_id)
    except Exception as e:  # noqa: BLE001
        return {"success": False, "message": f"PDF failed: {e}", "response": None, "note_id": None}

    try:
        key = media_svc.upload_bytes_key(
            pdf_bytes,
            key=f"warranty-cards/wa/{clinic_id}/{card_id}_{int(time.time())}.pdf",
            content_type="application/pdf",
        )
        file_url = media_svc.presign_get(key, expires_in=PRESCRIPTION_WA_TTL)
    except Exception as e:  # noqa: BLE001
        return {"success": False, "message": f"Upload failed: {e}", "response": None, "note_id": None}

    payload = {
        "to": recipient,
        "type": "template",
        "template_name": "wrnty_membrshp_plan_card",
        "language": "en",
        "file_url": file_url,
        "name": pdf_name,
        "template_params": {
            "client_print_name": client_name,
            "card_type_name": card_type_name,
            "product_membrshp_typ": product_membership,
            "period": period,
        },
        "contact_name": client_name,
    }
    result = _post_template(db, clinic_id, payload)
    note_id = None
    if result.get("success"):
        note = Note(
            clinic_id=clinic_id,
            client_id=client.client_id,
            user_id=user_id,
            body=f"Warranty card message sent successfully to {client_name}.",
        )
        db.add(note)
        db.commit()
        db.refresh(note)
        note_id = note.note_id
    result["note_id"] = note_id
    result["file_url"] = file_url
    return result


def _post_template(db: Session, clinic_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    key = api_key(db, clinic_id)
    url = api_url(db, clinic_id)
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Api-Key": key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            http_code = resp.getcode()
            try:
                parsed = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                parsed = {"raw": raw}
            ok = 200 <= http_code < 300 and bool(parsed.get("success", True) if isinstance(parsed, dict) else True)
            # Intermediate API may return success in body
            if isinstance(parsed, dict) and "success" in parsed:
                ok = bool(parsed.get("success"))
            if isinstance(parsed, dict) and parsed.get("wa_message_id"):
                ok = True
            message = ""
            if isinstance(parsed, dict):
                message = str(parsed.get("message") or parsed.get("error") or "")
            if not message:
                message = "WhatsApp sent" if ok else f"WhatsApp API HTTP {http_code}"
            return {"success": ok, "message": message, "response": parsed}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return {"success": False, "message": f"WhatsApp HTTP {e.code}: {raw[:200]}", "response": None}
    except Exception as e:  # noqa: BLE001 — surface to desk toast
        return {"success": False, "message": f"WhatsApp error: {e}", "response": None}
