"""Upsert note_attachments (+ legacy notes.attachment_url) keys from MySQL.

Does not copy S3 files — keys only. Requires MYSQL_* and DATABASE_URL.

  python scripts/import_note_attachments.py --clinic-id 1
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pymysql

from app.db import Base, SessionLocal, engine
from app.models import Note, NoteAttachment


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
                "SELECT n.note_id, n.client_id, n.user_id, n.note_text, n.attachment_url, n.created_at "
                "FROM notes n "
                "JOIN clients c ON c.client_id = n.client_id "
                "WHERE c.clinic_id = %s AND IFNULL(n.visible, 1) = 1",
                (args.clinic_id,),
            )
            notes = cur.fetchall()

        note_ids: list[int] = []
        updated_notes = 0
        for n in notes:
            body = (n.get("note_text") or "").strip()
            legacy = (n.get("attachment_url") or "").strip() or None
            if not body and not legacy:
                continue
            note_ids.append(n["note_id"])
            existing = db.get(Note, n["note_id"])
            if existing:
                existing.attachment_url = legacy
                if not (existing.body or "").strip() and body:
                    existing.body = body
                updated_notes += 1
            else:
                db.add(
                    Note(
                        note_id=n["note_id"],
                        clinic_id=args.clinic_id,
                        client_id=n["client_id"],
                        user_id=n.get("user_id"),
                        body=body or "",
                        attachment_url=legacy,
                        visible=True,
                        created_at=n.get("created_at") or datetime.now(timezone.utc),
                        updated_at=n.get("created_at") or datetime.now(timezone.utc),
                    )
                )
                updated_notes += 1
        db.flush()

        attach_count = 0
        if note_ids:
            with src.cursor() as cur:
                # chunk IN lists
                chunk = 500
                rows = []
                for i in range(0, len(note_ids), chunk):
                    part = note_ids[i : i + chunk]
                    ph = ",".join(["%s"] * len(part))
                    cur.execute(
                        f"SELECT id, note_id, attachment_url FROM note_attachments WHERE note_id IN ({ph})",
                        part,
                    )
                    rows.extend(cur.fetchall())
            for a in rows:
                url = (a.get("attachment_url") or "").strip()
                if not url:
                    continue
                db.merge(
                    NoteAttachment(
                        id=a["id"],
                        note_id=a["note_id"],
                        clinic_id=args.clinic_id,
                        attachment_url=url,
                    )
                )
                attach_count += 1

        db.commit()
        print(f"Notes touched: {updated_notes}")
        print(f"note_attachments upserted: {attach_count}")
    finally:
        db.close()
        src.close()


if __name__ == "__main__":
    main()
