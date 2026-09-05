"""Warranty card PDF — ports patient.quantumdental/generate_pdf_direct.php layout."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fpdf import FPDF
from sqlalchemy.orm import Session

from app.models import (
    Benefit,
    CardIssued,
    CardType,
    Client,
    ProductMembershipType,
    TermsCondition,
)

ASSETS = Path(__file__).resolve().parents[1] / "assets"
BG_PATH = ASSETS / "warranty_card_pdf.png"
IST = ZoneInfo("Asia/Kolkata")


def _pdf_bytes(pdf: FPDF) -> bytes:
    out = pdf.output()
    if isinstance(out, (bytes, bytearray)):
        return bytes(out)
    return str(out).encode("latin-1")


def generate_warranty_card_pdf(db: Session, clinic_id: int, card_id: int) -> bytes:
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
        raise ValueError("Warranty card not found")

    client = db.get(Client, card.client_id)
    card_type = db.get(CardType, card.card_type_id)
    product = db.get(ProductMembershipType, card.product_id)
    benefit = db.get(Benefit, card.benefit_id)
    terms = db.get(TermsCondition, card.terms_conditions_id)

    name = (client.name if client else "") or "Patient"
    product_label = f"{(product.name if product else 'Product')} ({card.number_of_units} Units)"
    period = (
        f"{card.benefit_start_date.strftime('%d-%m-%Y')} to "
        f"{card.benefit_end_date.strftime('%d-%m-%Y')}"
    )
    benefits_text = (benefit.detailed_benefit if benefit else "") or ""
    terms_text = (terms.detailed_condition if terms else "") or ""
    code = card.unique_code or ""
    # type_name unused on PDF body (legacy writes product_name); keep for parity if needed
    _ = card_type.type_name if card_type else None

    pdf = FPDF(unit="mm", format="A4")
    pdf.set_auto_page_break(False)
    pdf.add_page()

    if BG_PATH.is_file():
        pdf.image(str(BG_PATH), x=0, y=0, w=210, h=297)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_xy(92, 10)
    pdf.cell(0, 10, "Warranty Card")

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_xy(50, 37)
    pdf.cell(0, 10, name)
    pdf.set_xy(50, 48)
    pdf.cell(0, 10, product_label)
    pdf.set_xy(50, 58)
    pdf.cell(0, 10, period)
    pdf.set_xy(50, 67)
    pdf.cell(0, 10, str(card.warranty_period))

    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(125, 128, 140)
    pdf.set_xy(144, 24)
    pdf.cell(0, 10, code)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_xy(92, 103)
    pdf.cell(0, 10, "Backside")

    pdf.set_font("Courier", "", 8)
    pdf.set_xy(49, 124)
    pdf.cell(0, 10, benefits_text[:120])
    pdf.set_xy(49, 137)
    pdf.multi_cell(110, 3, terms_text)

    pdf.set_text_color(125, 128, 140)
    pdf.set_font("Courier", "B", 8)
    pdf.set_xy(49, 200)
    pdf.multi_cell(
        110,
        7,
        "Note: This is a computer-generated card and does not require a signature.",
    )
    today = datetime.now(IST).strftime("%d-%m-%Y %H:%M %p")
    pdf.set_x(49)
    pdf.cell(0, 10, f"Downloaded On: {today}", align="L")

    return _pdf_bytes(pdf)
