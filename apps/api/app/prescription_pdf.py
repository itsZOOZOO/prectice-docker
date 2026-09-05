"""Prescription PDFs: print (letterhead paper) + WhatsApp digital letterhead.

Port of patient.quantumdental PrescriptionPdf + PdfTemplateLayout.
"""

from __future__ import annotations

import json
import tempfile
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fpdf import FPDF
from sqlalchemy.orm import Session, joinedload

from app.models import Client, Clinic, PdfTemplate, Prescription

ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"


def default_print_layout() -> dict[str, Any]:
    return {
        "logo": {},
        "slots": [],
        "logo_path": "",
        "anchors": {
            "date": {"x": 175, "y": 38, "prefix": "", "font": "Arial", "style": "B", "font_size": 12},
            "title": {"text": "Prescription", "align": "C", "font": "Arial", "style": "BU", "font_size": 14},
            "patient_block": {"x": 30},
            "medicine_table": {"x": 30},
            "disclaimer": {"x": 30, "font_size": 9},
            "closing_tagline": {
                "text": "Your Smile Matters :)",
                "align": "C",
                "font": "Courier",
                "style": "",
                "font_size": 17,
            },
            "signature": {"x": 150, "text": "For,", "font": "Arial", "style": "", "font_size": 10},
        },
    }


def default_whatsapp_layout() -> dict[str, Any]:
    return {
        "logo": {"full_page": True},
        "logo_path": "",
        "slots": [
            {
                "text": "AAAROGYAM DENTAL",
                "x": 20,
                "y": 8,
                "font": "Helvetica",
                "style": "B",
                "font_size": 20,
                "align": "L",
                "width": 110,
                "area": "header",
            },
            {
                "text": "Dr. Sneha Pipalia",
                "x": 130,
                "y": 10,
                "font": "Helvetica",
                "style": "B",
                "font_size": 13,
                "align": "R",
                "width": 60,
                "area": "header",
            },
            {
                "text": "IMPLANTS - ALIGNERS - BRACES",
                "x": 20,
                "y": 27,
                "font": "Arial",
                "style": "I",
                "font_size": 13,
                "align": "L",
                "width": 110,
                "area": "header",
            },
            {
                "text": "(BDS, C. Ortho)",
                "x": 140,
                "y": 25,
                "font": "Arial",
                "style": "I",
                "font_size": 12,
                "align": "R",
                "width": 50,
                "area": "header",
            },
            {
                "text": "Timing : 9:30 AM to 1:30 PM, 4:30 PM to 8:30 PM",
                "x": 10,
                "y": 267,
                "font": "Arial",
                "style": "",
                "font_size": 12,
                "align": "C",
                "width": 190,
                "area": "footer",
            },
            {
                "text": "www.aarogyams.com   |   aarogyam52@gmail.com  |  Ph. No: 7 99 99 99 527",
                "x": 10,
                "y": 275,
                "font": "Arial",
                "style": "",
                "font_size": 12,
                "align": "C",
                "width": 190,
                "area": "footer",
            },
            {
                "text": "#212, Nilkanth Plaza, Bapasitaram Chowk, Mavdi Main Road, Rajkot - 04",
                "x": 10,
                "y": 282,
                "font": "Arial",
                "style": "",
                "font_size": 12,
                "align": "C",
                "width": 190,
                "area": "footer",
            },
        ],
        "anchors": {
            "date": {
                "x": 160,
                "y": 39,
                "prefix": "Date: ",
                "font": "Arial",
                "style": "B",
                "font_size": 12,
            },
            "title": {
                "text": "Digital Prescription",
                "align": "C",
                "font": "Arial",
                "style": "BU",
                "font_size": 14,
            },
            "patient_block": {"x": 30},
            "medicine_table": {"x": 30},
            "disclaimer": {"x": 30, "font_size": 9},
            "closing_tagline": {
                "text": " Your Smile Matters :) ",
                "align": "C",
                "font": "Courier",
                "style": "",
                "font_size": 17,
            },
            "signature": {"x": 150, "text": "For,", "font": "Arial", "style": "", "font_size": 10},
        },
    }


def _merge_anchors(base: dict[str, Any], override: dict[str, Any] | None) -> dict[str, Any]:
    out = deepcopy(base)
    if not isinstance(override, dict):
        return out
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = {**out[key], **val}
        else:
            out[key] = val
    return out


def _sanitize_slots(slots: list[Any] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not slots:
        return out
    for slot in slots:
        if not isinstance(slot, dict):
            continue
        text = str(slot.get("text") or "").strip()
        if not text:
            continue
        out.append(
            {
                "text": text,
                "x": float(slot.get("x") or 10),
                "y": float(slot.get("y") or 10),
                "font": str(slot.get("font") or "Arial"),
                "style": str(slot.get("style") or ""),
                "font_size": float(slot.get("font_size") or 12),
                "align": str(slot.get("align") or "L"),
                "width": float(slot.get("width") or 190),
                "area": "footer" if slot.get("area") == "footer" else "header",
            }
        )
    return out


def _legacy_to_slots(header: dict[str, Any], footer: dict[str, Any]) -> list[dict[str, Any]]:
    clinic_name = str(header.get("clinic_name") or "").strip()
    doctor_name = str(header.get("doctor_name") or "").strip()
    tagline = str(header.get("tagline") or "").strip()
    qualification = str(header.get("qualification") or "").strip()
    timing = str(footer.get("timing") or "").strip()
    website = str(footer.get("website") or "").strip()
    email = str(footer.get("email") or "").strip()
    phone = str(footer.get("phone") or "").strip()
    address = str(footer.get("address") or "").strip()

    slots: list[dict[str, Any]] = []
    if clinic_name:
        slots.append(
            {
                "text": clinic_name,
                "x": 20,
                "y": 8,
                "font": "Helvetica",
                "style": "B",
                "font_size": 20,
                "align": "L",
                "width": 110,
                "area": "header",
            }
        )
    if doctor_name:
        slots.append(
            {
                "text": doctor_name,
                "x": 130,
                "y": 10,
                "font": "Helvetica",
                "style": "B",
                "font_size": 13,
                "align": "R",
                "width": 60,
                "area": "header",
            }
        )
    if tagline:
        slots.append(
            {
                "text": tagline,
                "x": 20,
                "y": 27,
                "font": "Arial",
                "style": "I",
                "font_size": 13,
                "align": "L",
                "width": 110,
                "area": "header",
            }
        )
    if qualification:
        slots.append(
            {
                "text": qualification,
                "x": 140,
                "y": 25,
                "font": "Arial",
                "style": "I",
                "font_size": 12,
                "align": "R",
                "width": 50,
                "area": "header",
            }
        )
    if timing:
        slots.append(
            {
                "text": f"Timing : {timing}",
                "x": 10,
                "y": 267,
                "font": "Arial",
                "style": "",
                "font_size": 12,
                "align": "C",
                "width": 190,
                "area": "footer",
            }
        )
    contact = "   |   ".join(
        p
        for p in [
            website,
            email,
            f"Ph. No: {phone}" if phone else "",
        ]
        if p
    )
    if contact:
        slots.append(
            {
                "text": contact,
                "x": 10,
                "y": 275,
                "font": "Arial",
                "style": "",
                "font_size": 12,
                "align": "C",
                "width": 190,
                "area": "footer",
            }
        )
    if address:
        slots.append(
            {
                "text": address,
                "x": 10,
                "y": 282,
                "font": "Arial",
                "style": "",
                "font_size": 12,
                "align": "C",
                "width": 190,
                "area": "footer",
            }
        )
    return _sanitize_slots(slots)


def normalize_print_layout(raw: dict[str, Any] | None) -> dict[str, Any]:
    defaults = default_print_layout()
    if not raw:
        return defaults

    try:
        header = json.loads(raw.get("header_content") or "{}")
    except json.JSONDecodeError:
        return defaults
    if not isinstance(header, dict):
        return defaults

    if "slots" in header or "anchors" in header:
        return {
            "logo": header.get("logo") if isinstance(header.get("logo"), dict) else {},
            "slots": _sanitize_slots(header.get("slots") if isinstance(header.get("slots"), list) else []),
            "anchors": _merge_anchors(defaults["anchors"], header.get("anchors")),
            "logo_path": str(raw.get("logo_path") or ""),
        }

    anchors = deepcopy(defaults["anchors"])
    if "date_x" in header:
        anchors["date"]["x"] = float(header["date_x"])
    if "date_y" in header:
        anchors["date"]["y"] = float(header["date_y"])
    if "content_x" in header:
        x = float(header["content_x"])
        anchors["patient_block"]["x"] = x
        anchors["medicine_table"]["x"] = x
        anchors["disclaimer"]["x"] = x
    if "tagline" in header:
        anchors["closing_tagline"]["text"] = str(header.get("tagline") or "")

    return {"logo": {}, "slots": [], "anchors": anchors, "logo_path": str(raw.get("logo_path") or "")}


def normalize_whatsapp_layout(
    raw: dict[str, Any] | None,
    *,
    clinic: Clinic | None = None,
) -> dict[str, Any]:
    defaults = default_whatsapp_layout()
    if not raw:
        return defaults

    try:
        header = json.loads(raw.get("header_content") or "{}")
    except json.JSONDecodeError:
        header = {}
    try:
        footer = json.loads(raw.get("footer_content") or "{}")
    except json.JSONDecodeError:
        footer = {}
    if not isinstance(header, dict):
        header = {}
    if not isinstance(footer, dict):
        footer = {}

    # Fill empty clinic_name from clinics table (legacy behaviour)
    if clinic and not str(header.get("clinic_name") or "").strip() and clinic.clinic_name:
        header = {**header, "clinic_name": clinic.clinic_name}
        if not str(footer.get("phone") or "").strip() and clinic.clinic_phone:
            footer = {**footer, "phone": clinic.clinic_phone}
        if not str(footer.get("email") or "").strip() and clinic.clinic_email:
            footer = {**footer, "email": clinic.clinic_email}
        if not str(footer.get("address") or "").strip() and clinic.clinic_address:
            footer = {**footer, "address": clinic.clinic_address}

    if "slots" in header and isinstance(header.get("slots"), list):
        slots = _sanitize_slots(header["slots"])
        anchors = _merge_anchors(defaults["anchors"], header.get("anchors"))
        logo_cfg = header.get("logo") if isinstance(header.get("logo"), dict) else deepcopy(defaults["logo"])
    else:
        slots = _legacy_to_slots(header, footer)
        if not slots:
            slots = deepcopy(defaults["slots"])
        anchors = _merge_anchors(defaults["anchors"], header.get("anchors") if isinstance(header.get("anchors"), dict) else None)
        logo_cfg = deepcopy(defaults["logo"])

    return {
        "logo": logo_cfg or {},
        "slots": slots,
        "anchors": anchors,
        "logo_path": str(raw.get("logo_path") or ""),
    }


def fetch_template(db: Session, clinic_id: int, template_type: str) -> dict[str, Any]:
    row = (
        db.query(PdfTemplate)
        .filter(PdfTemplate.template_type == template_type, PdfTemplate.clinic_id == clinic_id)
        .first()
    )
    if not row:
        row = (
            db.query(PdfTemplate)
            .filter(PdfTemplate.template_type == template_type, PdfTemplate.is_default.is_(True))
            .first()
        )
    if not row:
        return {}
    return {
        "logo_path": row.logo_path,
        "header_content": row.header_content,
        "footer_content": row.footer_content,
    }


def _resolve_logo_file(logo_path: str) -> str | None:
    """Return a local filesystem path if the logo can be opened; else None.

    Resolution order:
    1. Absolute / existing path
    2. ``apps/api/assets/<logo_path>`` (and basename)
    3. Download from S3 using ``logo_path`` as the object key
    4. S3 ``prescription_background.jpg`` as last resort when a path was requested
    """
    raw = (logo_path or "").strip()
    if not raw:
        return None

    candidates: list[Path] = []
    p = Path(raw)
    if p.is_file():
        return str(p)
    if not raw.startswith(("/", "http://", "https://")):
        candidates.append(ASSETS_DIR / raw)
        candidates.append(ASSETS_DIR / Path(raw).name)

    for c in candidates:
        if c.is_file():
            return str(c)

    # Try S3 download into a temp file (same relative key as PHP / DB logo_path)
    if not raw.startswith(("http://", "https://", "/")):
        try:
            from app import media as media_svc

            client, settings = media_svc.require_s3()
            suffix = Path(raw).suffix or ".jpg"
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.close()
            client.download_file(settings.s3_bucket, raw, tmp.name)
            return tmp.name
        except Exception:  # noqa: BLE001 — logo optional; fall through
            pass
        # Last resort: shared default background key (older PHP root file)
        try:
            from app import media as media_svc

            client, settings = media_svc.require_s3()
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            tmp.close()
            try:
                client.download_file(settings.s3_bucket, "prescription_background.jpg", tmp.name)
                return tmp.name
            except Exception:  # noqa: BLE001
                Path(tmp.name).unlink(missing_ok=True)
        except Exception:  # noqa: BLE001 — logo optional
            return None
    return None


def _set_font(pdf: FPDF, font: str, style: str, size: float) -> None:
    family = font if font in {"Arial", "Helvetica", "Courier", "Times"} else "Helvetica"
    st = style.replace("U", "") if "U" in style and "B" in style else style
    try:
        pdf.set_font(family, st, size)
    except Exception:
        pdf.set_font("Helvetica", "", size)


def _draw_slots(pdf: FPDF, slots: list[dict[str, Any]], area: str) -> None:
    for slot in slots:
        if slot.get("area") != area:
            continue
        _set_font(pdf, slot["font"], slot["style"], slot["font_size"])
        pdf.set_xy(slot["x"], slot["y"])
        h = slot["font_size"] * 0.45 + 2
        pdf.cell(slot["width"], h, slot["text"], align=slot["align"])


def _draw_logo(pdf: FPDF, logo_path: str, logo_cfg: dict[str, Any]) -> None:
    path = _resolve_logo_file(logo_path)
    if not path:
        return
    try:
        if logo_cfg.get("full_page"):
            pdf.image(path, x=0, y=0, w=210, h=297)
            return
        x = float(logo_cfg.get("x") or 0)
        y = float(logo_cfg.get("y") or 0)
        w = float(logo_cfg.get("w") or 0)
        h = float(logo_cfg.get("h") or 0)
        if w > 0 and h > 0:
            pdf.image(path, x=x, y=y, w=w, h=h)
        elif w > 0:
            pdf.image(path, x=x, y=y, w=w)
        else:
            pdf.image(path, x=x, y=y)
    except Exception:  # noqa: BLE001 — skip broken images
        return


class _LayoutPdf(FPDF):
    def __init__(self, layout: dict[str, Any]) -> None:
        super().__init__()
        self._layout = layout

    def header(self) -> None:  # noqa: N802
        _draw_logo(self, str(self._layout.get("logo_path") or ""), self._layout.get("logo") or {})
        _draw_slots(self, self._layout.get("slots") or [], "header")

    def footer(self) -> None:  # noqa: N802
        _draw_slots(self, self._layout.get("slots") or [], "footer")


def _fmt_date(value: date | datetime | str) -> str:
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.strftime("%d-%m-%Y")
    try:
        return datetime.fromisoformat(str(value)[:10]).strftime("%d-%m-%Y")
    except ValueError:
        return str(value)


def _load_rx(db: Session, clinic_id: int, prescription_id: int) -> tuple[Prescription, Client]:
    rx = (
        db.query(Prescription)
        .options(joinedload(Prescription.items))
        .filter(
            Prescription.prescription_id == prescription_id,
            Prescription.clinic_id == clinic_id,
            Prescription.visible.is_(True),
        )
        .first()
    )
    if not rx:
        raise LookupError("Prescription not found")
    client = (
        db.query(Client)
        .filter(Client.client_id == rx.client_id, Client.clinic_id == clinic_id)
        .first()
    )
    if not client:
        raise LookupError("Prescription not found")
    return rx, client


def _render_body(
    pdf: FPDF,
    *,
    rx: Prescription,
    client: Client,
    anchors: dict[str, Any],
    whatsapp_mode: bool,
) -> None:
    date_cfg = anchors.get("date") or {}
    title_cfg = anchors.get("title") or {}
    patient_x = float((anchors.get("patient_block") or {}).get("x") or 30)
    table_x = float((anchors.get("medicine_table") or {}).get("x") or patient_x)
    disc_cfg = anchors.get("disclaimer") or {}
    tag_cfg = anchors.get("closing_tagline") or {}
    sig_cfg = anchors.get("signature") or {}

    date_text = f"{date_cfg.get('prefix') or ''}{_fmt_date(rx.prescription_date)}"
    _set_font(
        pdf,
        str(date_cfg.get("font") or "Arial"),
        str(date_cfg.get("style") or "B"),
        float(date_cfg.get("font_size") or 12),
    )
    pdf.set_xy(float(date_cfg.get("x") or (160 if whatsapp_mode else 175)), float(date_cfg.get("y") or 38))
    pdf.cell(0, 10, date_text)

    default_title = "Digital Prescription" if whatsapp_mode else "Prescription"
    title = str(title_cfg.get("text") or default_title).strip()
    if title:
        _set_font(
            pdf,
            str(title_cfg.get("font") or "Arial"),
            str(title_cfg.get("style") or "BU"),
            float(title_cfg.get("font_size") or 14),
        )
        pdf.cell(0, 10, title, align=str(title_cfg.get("align") or "C"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

    pdf.set_font("Helvetica", "", 12)
    age = client.age
    age_display: Any = age if age is not None else ""
    if not whatsapp_mode and isinstance(age, int) and age < 4:
        age_display = " - "

    pdf.set_x(patient_x)
    pdf.cell(0, 10, f"Patient Name: {client.name}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(patient_x)
    pdf.cell(0, 10, f"Age/Gender: {age_display}/{client.gender or ''}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(patient_x)
    pdf.cell(0, 10, f"Address: {client.place or ''}", new_x="LMARGIN", new_y="NEXT")

    if rx.notes:
        pdf.set_x(patient_x)
        pdf.multi_cell(0, 10, f"Notes: {rx.notes}")

    pdf.ln(5)
    pdf.set_x(table_x)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(10, 10, "Sr", border=1, align="C")
    pdf.cell(55, 10, "Medicine", border=1, align="C")
    pdf.cell(15, 10, "Qty", border=1, align="C")
    pdf.cell(25, 10, "Dosage", border=1, align="C")
    pdf.cell(20, 10, "Days", border=1, align="C")
    pdf.cell(35, 10, "Instructions", border=1, align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 12)
    for i, item in enumerate(rx.items, start=1):
        pdf.set_x(table_x)
        pdf.cell(10, 10, str(i), border=1, align="C")
        pdf.cell(55, 10, (item.medicine_name or "")[:40], border=1)
        pdf.cell(15, 10, "" if item.quantity is None else str(item.quantity), border=1, align="C")
        pdf.cell(25, 10, (item.dosage or "")[:16], border=1, align="C")
        pdf.cell(20, 10, "" if item.days is None else str(item.days), border=1, align="C")
        pdf.cell(35, 10, (item.instructions or "")[:22], border=1, new_x="LMARGIN", new_y="NEXT")

    disc_x = float(disc_cfg.get("x") or table_x)
    pdf.set_x(disc_x)
    pdf.set_font("Helvetica", "", float(disc_cfg.get("font_size") or 9))
    pdf.cell(
        0,
        10,
        "Note: Please consult the doctor and confirm the medicines before taking them.",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    tagline = str(tag_cfg.get("text") or "").strip()
    if tagline:
        inner = tagline.strip(' "')
        display = f'" {inner} " ' if whatsapp_mode else f'"{inner}"'
        _set_font(
            pdf,
            str(tag_cfg.get("font") or "Courier"),
            str(tag_cfg.get("style") or ""),
            float(tag_cfg.get("font_size") or 17),
        )
        pdf.cell(0, 20, display, align=str(tag_cfg.get("align") or "C"), new_x="LMARGIN", new_y="NEXT")

    sig_text = str(sig_cfg.get("text") or "For,")
    if sig_text:
        _set_font(
            pdf,
            str(sig_cfg.get("font") or "Arial"),
            str(sig_cfg.get("style") or ""),
            float(sig_cfg.get("font_size") or 10),
        )
        pdf.set_x(float(sig_cfg.get("x") or 150))
        pdf.cell(0, 20, sig_text)


def _pdf_bytes(pdf: FPDF) -> bytes:
    out = pdf.output()
    return bytes(out) if isinstance(out, (bytes, bytearray)) else out.encode("latin-1")


def generate_print_pdf(db: Session, clinic_id: int, prescription_id: int) -> bytes:
    rx, client = _load_rx(db, clinic_id, prescription_id)
    layout = normalize_print_layout(fetch_template(db, clinic_id, "print"))
    pdf = _LayoutPdf(layout)
    pdf.add_page()
    _render_body(pdf, rx=rx, client=client, anchors=layout["anchors"], whatsapp_mode=False)
    return _pdf_bytes(pdf)


def generate_letterhead_pdf(db: Session, clinic_id: int, prescription_id: int) -> bytes:
    """Digital letterhead PDF for WhatsApp (template_type=whatsapp)."""
    rx, client = _load_rx(db, clinic_id, prescription_id)
    clinic = db.get(Clinic, clinic_id)
    layout = normalize_whatsapp_layout(fetch_template(db, clinic_id, "whatsapp"), clinic=clinic)
    pdf = _LayoutPdf(layout)
    pdf.add_page()
    _render_body(pdf, rx=rx, client=client, anchors=layout["anchors"], whatsapp_mode=True)
    return _pdf_bytes(pdf)


def whatsapp_form_from_raw(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Flatten a stored whatsapp template into the simple admin form fields."""
    empty = {
        "clinic_name": "",
        "doctor_name": "",
        "tagline": "",
        "qualification": "",
        "timing": "",
        "website": "",
        "email": "",
        "phone": "",
        "address": "",
        "logo_path": "",
    }
    if not raw:
        return empty
    try:
        header = json.loads(raw.get("header_content") or "{}")
    except json.JSONDecodeError:
        header = {}
    try:
        footer = json.loads(raw.get("footer_content") or "{}")
    except json.JSONDecodeError:
        footer = {}
    if not isinstance(header, dict):
        header = {}
    if not isinstance(footer, dict):
        footer = {}

    out = {
        **empty,
        "logo_path": str(raw.get("logo_path") or ""),
        "clinic_name": str(header.get("clinic_name") or ""),
        "doctor_name": str(header.get("doctor_name") or ""),
        "tagline": str(header.get("tagline") or ""),
        "qualification": str(header.get("qualification") or ""),
        "timing": str(footer.get("timing") or ""),
        "website": str(footer.get("website") or ""),
        "email": str(footer.get("email") or ""),
        "phone": str(footer.get("phone") or ""),
        "address": str(footer.get("address") or ""),
    }

    # Best-effort reverse of free slots → form fields (order matches _legacy_to_slots)
    if not out["clinic_name"] and isinstance(header.get("slots"), list):
        header_slots = [s for s in header["slots"] if isinstance(s, dict) and s.get("area") != "footer"]
        footer_slots = [s for s in header["slots"] if isinstance(s, dict) and s.get("area") == "footer"]
        texts_h = [str(s.get("text") or "").strip() for s in header_slots]
        texts_f = [str(s.get("text") or "").strip() for s in footer_slots]
        if len(texts_h) > 0:
            out["clinic_name"] = texts_h[0]
        if len(texts_h) > 1:
            out["doctor_name"] = texts_h[1]
        if len(texts_h) > 2:
            out["tagline"] = texts_h[2]
        if len(texts_h) > 3:
            out["qualification"] = texts_h[3]
        if len(texts_f) > 0 and texts_f[0].lower().startswith("timing"):
            out["timing"] = texts_f[0].split(":", 1)[-1].strip() if ":" in texts_f[0] else texts_f[0]
        if len(texts_f) > 1:
            parts = [p.strip() for p in texts_f[1].split("|")]
            if parts:
                out["website"] = parts[0]
            if len(parts) > 1:
                out["email"] = parts[1]
            if len(parts) > 2:
                phone = parts[2]
                out["phone"] = phone.replace("Ph. No:", "").replace("Ph. No", "").strip(" :")
        if len(texts_f) > 2:
            out["address"] = texts_f[2]
    return out


def print_form_from_raw(raw: dict[str, Any] | None) -> dict[str, Any]:
    defaults = {"date_x": 175.0, "date_y": 38.0, "content_x": 30.0, "tagline": "Your Smile Matters :)"}
    if not raw:
        return defaults
    try:
        header = json.loads(raw.get("header_content") or "{}")
    except json.JSONDecodeError:
        return defaults
    if not isinstance(header, dict):
        return defaults
    if "date_x" in header or "content_x" in header or "tagline" in header:
        return {
            "date_x": float(header.get("date_x") if header.get("date_x") is not None else defaults["date_x"]),
            "date_y": float(header.get("date_y") if header.get("date_y") is not None else defaults["date_y"]),
            "content_x": float(header.get("content_x") if header.get("content_x") is not None else defaults["content_x"]),
            "tagline": str(header.get("tagline") if header.get("tagline") is not None else defaults["tagline"]),
        }
    layout = normalize_print_layout(raw)
    anchors = layout.get("anchors") or {}
    return {
        "date_x": float((anchors.get("date") or {}).get("x") or defaults["date_x"]),
        "date_y": float((anchors.get("date") or {}).get("y") or defaults["date_y"]),
        "content_x": float((anchors.get("patient_block") or {}).get("x") or defaults["content_x"]),
        "tagline": str((anchors.get("closing_tagline") or {}).get("text") or defaults["tagline"]),
    }


def encode_whatsapp_template(form: dict[str, Any], *, logo_path: str) -> dict[str, str]:
    header = {
        "logo": {"full_page": True},
        "clinic_name": str(form.get("clinic_name") or "").strip(),
        "doctor_name": str(form.get("doctor_name") or "").strip(),
        "tagline": str(form.get("tagline") or "").strip(),
        "qualification": str(form.get("qualification") or "").strip(),
    }
    footer = {
        "timing": str(form.get("timing") or "").strip(),
        "website": str(form.get("website") or "").strip(),
        "email": str(form.get("email") or "").strip(),
        "phone": str(form.get("phone") or "").strip(),
        "address": str(form.get("address") or "").strip(),
    }
    return {
        "header_content": json.dumps(header, ensure_ascii=False),
        "footer_content": json.dumps(footer, ensure_ascii=False),
        "logo_path": logo_path,
    }


def encode_print_template(form: dict[str, Any]) -> dict[str, str]:
    header = {
        "date_x": float(form.get("date_x") if form.get("date_x") is not None else 175),
        "date_y": float(form.get("date_y") if form.get("date_y") is not None else 38),
        "content_x": float(form.get("content_x") if form.get("content_x") is not None else 30),
        "tagline": str(form.get("tagline") or "").strip(),
    }
    return {
        "header_content": json.dumps(header, ensure_ascii=False),
        "footer_content": "",
        "logo_path": "",
    }


def preview_from_forms(
    *,
    template_type: str,
    whatsapp: dict[str, Any] | None = None,
    print_form: dict[str, Any] | None = None,
    logo_path: str = "",
    logo_file: str | None = None,
) -> bytes:
    """Build a sample-patient PDF from unsaved admin form state."""
    sample_client = type(
        "SampleClient",
        (),
        {
            "name": "Sample Patient",
            "age": 32,
            "gender": "male",
            "place": "Sample Address, Rajkot",
        },
    )()
    sample_item = type(
        "SampleItem",
        (),
        {
            "medicine_name": "Amoxicillin",
            "quantity": 10,
            "dosage": "1-0-1",
            "days": 5,
            "instructions": "After food",
        },
    )()
    sample_item2 = type(
        "SampleItem",
        (),
        {
            "medicine_name": "Ibuprofen",
            "quantity": 6,
            "dosage": "1-0-1",
            "days": 3,
            "instructions": "SOS",
        },
    )()
    sample_rx = type(
        "SampleRx",
        (),
        {
            "prescription_date": date.today(),
            "notes": "",
            "items": [sample_item, sample_item2],
        },
    )()

    if template_type == "print":
        raw = encode_print_template(print_form or {})
        layout = normalize_print_layout(raw)
        pdf = _LayoutPdf(layout)
        pdf.add_page()
        _render_body(pdf, rx=sample_rx, client=sample_client, anchors=layout["anchors"], whatsapp_mode=False)
        return _pdf_bytes(pdf)

    path = logo_file or logo_path
    raw = encode_whatsapp_template(whatsapp or {}, logo_path=path)
    layout = normalize_whatsapp_layout(raw, clinic=None)
    if logo_file:
        layout["logo_path"] = logo_file
    pdf = _LayoutPdf(layout)
    pdf.add_page()
    _render_body(pdf, rx=sample_rx, client=sample_client, anchors=layout["anchors"], whatsapp_mode=True)
    return _pdf_bytes(pdf)
