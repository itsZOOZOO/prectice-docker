"""Import pdf_templates from MySQL (print layouts per clinic).

  python scripts/import_pdf_templates.py --clinic-id 1 --type all
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # Support PHP-style defines pasted into .env
        m = re.match(
            r"define\(\s*'([A-Z0-9_]+)'\s*,\s*'((?:\\'|[^'])*)'\s*\)\s*;?\s*$",
            line,
        )
        if m:
            key, val = m.group(1), m.group(2).replace("\\'", "'")
            mapping = {
                "DB_HOST": "MYSQL_HOST",
                "DB_NAME": "MYSQL_DATABASE",
                "DB_USER": "MYSQL_USER",
                "DB_PASS": "MYSQL_PASSWORD",
            }
            os.environ.setdefault(mapping.get(key, key), val)
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

import json

import pymysql

from app.db import Base, SessionLocal, engine
from app.models import PdfTemplate


def _header_ok(raw: str | None) -> bool:
    """Reject MySQL VARCHAR(255)-truncated JSON so we don't overwrite good Postgres rows."""
    text = (raw or "").strip()
    if not text:
        return True
    try:
        parsed = json.loads(text)
        return isinstance(parsed, dict)
    except json.JSONDecodeError:
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clinic-id", type=int, default=1)
    parser.add_argument("--type", choices=("print", "whatsapp", "all"), default="print")
    args = parser.parse_args()

    missing = [k for k in ("MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE") if not os.getenv(k)]
    if missing:
        raise SystemExit(f"Missing env: {', '.join(missing)}")

    types = ["print", "whatsapp"] if args.type == "all" else [args.type]

    ssl_mode = os.getenv("MYSQL_SSL", "1")
    connect_kwargs: dict = dict(
        host=os.environ["MYSQL_HOST"],
        user=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        database=os.environ["MYSQL_DATABASE"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=30,
    )
    if ssl_mode not in {"0", "false", "False"}:
        connect_kwargs["ssl"] = {"ssl": True}

    Base.metadata.create_all(bind=engine)
    src = pymysql.connect(**connect_kwargs)
    db = SessionLocal()
    try:
        with src.cursor() as cur:
            cur.execute(
                "SELECT id, clinic_id, template_type, logo_path, header_content, "
                "footer_content, IFNULL(is_default, 0) AS is_default, template_name "
                "FROM pdf_templates "
                "WHERE template_type IN %s AND (clinic_id = %s OR is_default = 1 OR clinic_id IS NULL)",
                (tuple(types), args.clinic_id),
            )
            rows = cur.fetchall()

        if not rows:
            raise SystemExit(f"No pdf_templates found for clinic_id={args.clinic_id} types={types}")

        upserted = 0
        skipped = 0
        for r in rows:
            clinic_id = r.get("clinic_id")
            tmpl_type = r["template_type"]
            header_content = r.get("header_content")
            if not _header_ok(header_content):
                skipped += 1
                print(
                    f"  SKIP truncated/invalid header JSON "
                    f"id={r.get('id')} clinic={clinic_id} type={tmpl_type} "
                    f"len={len(header_content or '')} — run repair_pdf_templates.py "
                    f"or widen MySQL then re-save in template manager"
                )
                continue

            existing = (
                db.query(PdfTemplate)
                .filter(
                    PdfTemplate.clinic_id == clinic_id,
                    PdfTemplate.template_type == tmpl_type,
                )
                .first()
            )
            if existing is None and clinic_id is None:
                existing = (
                    db.query(PdfTemplate)
                    .filter(
                        PdfTemplate.clinic_id.is_(None),
                        PdfTemplate.template_type == tmpl_type,
                        PdfTemplate.is_default.is_(True),
                    )
                    .first()
                )

            if existing:
                existing.logo_path = r.get("logo_path")
                existing.header_content = header_content
                existing.footer_content = r.get("footer_content")
                existing.is_default = bool(r.get("is_default"))
            else:
                db.add(
                    PdfTemplate(
                        clinic_id=clinic_id,
                        template_type=tmpl_type,
                        logo_path=r.get("logo_path"),
                        header_content=header_content,
                        footer_content=r.get("footer_content"),
                        is_default=bool(r.get("is_default")),
                    )
                )
            upserted += 1
            preview = (header_content or "")[:80].replace("\n", " ")
            print(
                f"  id={r.get('id')} name={r.get('template_name')!r} clinic={clinic_id} "
                f"type={tmpl_type} default={bool(r.get('is_default'))} "
                f"logo={r.get('logo_path')!r} header≈{preview!r}"
            )

        db.commit()
        print(
            f"Upserted {upserted} pdf_templates for clinic_id={args.clinic_id}"
            + (f" (skipped {skipped} truncated)" if skipped else "")
        )
    finally:
        db.close()
        src.close()


if __name__ == "__main__":
    main()
