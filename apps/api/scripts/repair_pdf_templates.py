"""Repair clinic WhatsApp/print pdf_templates after truncated MySQL import.

MySQL historically stored header_content as VARCHAR(255), which truncates
slot JSON. This writes a known-good Aarogyam (clinic 1) WhatsApp + print
layout into Postgres (TEXT columns).

  python scripts/repair_pdf_templates.py --clinic-id 1
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db import Base, SessionLocal, engine
from app.models import PdfTemplate

# Verbatim from patient.quantumdental migrate-add-pdf-templates-clinic.php
AAROGYAM_WA_HEADER = {
    "logo": {"full_page": True},
    "clinic_name": "AAAROGYAM DENTAL",
    "doctor_name": "Dr. Sneha Pipalia",
    "tagline": "IMPLANTS - ALIGNERS - BRACES",
    "qualification": "(BDS, C. Ortho)",
}

AAROGYAM_WA_FOOTER = {
    "timing": "9:30 AM to 1:30 PM, 4:30 PM to 8:30 PM",
    "website": "www.aarogyams.com",
    "email": "aarogyam52@gmail.com",
    "phone": "7 99 99 99 527",
    "address": "#212, Nilkanth Plaza, Bapasitaram Chowk, Mavdi Main Road, Rajkot - 04",
}

AAROGYAM_PRINT_HEADER = {
    "date_x": 175,
    "date_y": 38,
    "content_x": 30,
    "tagline": "Your Smile Matters :)",
}

# Prefer clinic-specific background; falls back in prescription_pdf resolver
AAROGYAM_WA_LOGO = "prescription_backgrounds/clinic_1_bg.jpg"


def _upsert(
    db,
    *,
    clinic_id: int | None,
    template_type: str,
    header: dict,
    footer: dict | str,
    logo_path: str,
    is_default: bool = False,
) -> None:
    existing = (
        db.query(PdfTemplate)
        .filter(PdfTemplate.clinic_id == clinic_id, PdfTemplate.template_type == template_type)
        .first()
    )
    footer_s = footer if isinstance(footer, str) else json.dumps(footer, ensure_ascii=False)
    header_s = json.dumps(header, ensure_ascii=False)
    if existing:
        existing.header_content = header_s
        existing.footer_content = footer_s
        existing.logo_path = logo_path
        existing.is_default = is_default
        action = "updated"
    else:
        db.add(
            PdfTemplate(
                clinic_id=clinic_id,
                template_type=template_type,
                header_content=header_s,
                footer_content=footer_s,
                logo_path=logo_path,
                is_default=is_default,
            )
        )
        action = "inserted"
    print(f"  {action} clinic={clinic_id} type={template_type} header_len={len(header_s)} logo={logo_path!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clinic-id", type=int, default=1)
    args = parser.parse_args()

    if args.clinic_id != 1:
        raise SystemExit("Only clinic_id=1 (Aarogyam seed) is supported by this repair script for now.")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _upsert(
            db,
            clinic_id=1,
            template_type="whatsapp",
            header=AAROGYAM_WA_HEADER,
            footer=AAROGYAM_WA_FOOTER,
            logo_path=AAROGYAM_WA_LOGO,
        )
        _upsert(
            db,
            clinic_id=1,
            template_type="print",
            header=AAROGYAM_PRINT_HEADER,
            footer="",
            logo_path="",
        )
        db.commit()
        print("Repair complete.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
