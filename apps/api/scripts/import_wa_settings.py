"""Upsert WhatsApp clinic_settings from MySQL without wiping clinic data.

Requires same MYSQL_* and DATABASE_URL env as import_mysql.py.

  python scripts/import_wa_settings.py --clinic-id 1
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pymysql

from app.db import Base, SessionLocal, engine
from app.models import ClinicSetting

WA_KEYS = (
    "wa_enabled",
    "wa_api_key",
    "wa_api_url",
    "wa_inbox_enabled",
    "wa_inbox_api_url",
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clinic-id", type=int, default=1)
    args = parser.parse_args()

    missing = [k for k in ("MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE") if not os.getenv(k)]
    if missing:
        raise SystemExit(f"Missing env: {', '.join(missing)}")

    ssl_mode = os.getenv("MYSQL_SSL", "1")
    connect_kwargs = dict(
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
                f"SELECT setting_key, setting_value FROM clinic_settings "
                f"WHERE clinic_id=%s AND setting_key IN ({','.join(['%s'] * len(WA_KEYS))})",
                (args.clinic_id, *WA_KEYS),
            )
            rows = cur.fetchall()
        if not rows:
            raise SystemExit(f"No WA settings found in MySQL for clinic_id={args.clinic_id}")

        for s in rows:
            existing = (
                db.query(ClinicSetting)
                .filter(
                    ClinicSetting.clinic_id == args.clinic_id,
                    ClinicSetting.setting_key == s["setting_key"],
                )
                .first()
            )
            if existing:
                existing.setting_value = s.get("setting_value")
            else:
                db.add(
                    ClinicSetting(
                        clinic_id=args.clinic_id,
                        setting_key=s["setting_key"],
                        setting_value=s.get("setting_value"),
                    )
                )
            print(f"  {s['setting_key']}: {'(set)' if s.get('setting_value') else '(empty)'}")
        db.commit()
        print(f"Upserted {len(rows)} clinic_settings for clinic_id={args.clinic_id}")
    finally:
        db.close()
        src.close()


if __name__ == "__main__":
    main()
