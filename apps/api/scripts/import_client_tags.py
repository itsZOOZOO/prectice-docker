"""Upsert client tag definitions + assignments from MySQL.

Requires same MYSQL_* and DATABASE_URL env as import_mysql.py.

  python scripts/import_client_tags.py --clinic-id 1
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pymysql
from sqlalchemy import text

from app.db import Base, SessionLocal, engine
from app.models import Client, ClientTag, ClientTagDefinition


def _mysql():
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
        read_timeout=600,
        write_timeout=600,
    )
    if ssl_mode not in {"0", "false", "False"}:
        connect_kwargs["ssl"] = {"check_hostname": False}
    return pymysql.connect(**connect_kwargs)


def import_client_tags(*, clinic_id: int) -> None:
    Base.metadata.create_all(bind=engine)
    src = _mysql()
    db = SessionLocal()
    try:
        with src.cursor() as cur:
            cur.execute(
                "SELECT client_tag_id, tag_name, clinic_id, short_code, sync_priority "
                "FROM client_tag_definitions WHERE clinic_id=%s",
                (clinic_id,),
            )
            defs = cur.fetchall()
            print(f"definitions={len(defs)}")

            for row in defs:
                tid = int(row["client_tag_id"])
                existing = db.get(ClientTagDefinition, tid)
                name = (row.get("tag_name") or "").strip()
                if not name:
                    continue
                short = (row.get("short_code") or "").strip().upper() or None
                prio = int(row.get("sync_priority") or 0)
                if existing:
                    existing.clinic_id = clinic_id
                    existing.tag_name = name
                    existing.short_code = short
                    existing.sync_priority = prio
                else:
                    db.add(
                        ClientTagDefinition(
                            client_tag_id=tid,
                            clinic_id=clinic_id,
                            tag_name=name,
                            short_code=short,
                            sync_priority=prio,
                        )
                    )
            db.flush()

            # Reset sequence so new desk-created tags don't collide
            db.execute(
                text(
                    "SELECT setval(pg_get_serial_sequence('client_tag_definitions','client_tag_id'), "
                    "COALESCE((SELECT MAX(client_tag_id) FROM client_tag_definitions), 1))"
                )
            )

            cur.execute(
                """
                SELECT ct.client_id, ct.client_tag_id
                FROM client_tags ct
                JOIN client_tag_definitions ctd ON ct.client_tag_id = ctd.client_tag_id
                WHERE ctd.clinic_id = %s
                """,
                (clinic_id,),
            )
            assigns = cur.fetchall()
            print(f"assignments={len(assigns)}")

            client_ids = {
                int(r[0])
                for r in db.query(Client.client_id).filter(Client.clinic_id == clinic_id).all()
            }
            def_ids = {
                int(r[0])
                for r in db.query(ClientTagDefinition.client_tag_id)
                .filter(ClientTagDefinition.clinic_id == clinic_id)
                .all()
            }

            # Replace assignments for this clinic's clients
            if client_ids:
                db.query(ClientTag).filter(ClientTag.client_id.in_(client_ids)).delete(
                    synchronize_session=False
                )
                db.flush()

            added = 0
            for row in assigns:
                cid = int(row["client_id"])
                tid = int(row["client_tag_id"])
                if cid not in client_ids or tid not in def_ids:
                    continue
                db.add(ClientTag(client_id=cid, client_tag_id=tid))
                added += 1
            db.commit()
            print(f"assignments_imported={added}")
            print("Client tags import complete")
    finally:
        db.close()
        src.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clinic-id", type=int, required=True)
    args = parser.parse_args()
    import_client_tags(clinic_id=args.clinic_id)


if __name__ == "__main__":
    main()
