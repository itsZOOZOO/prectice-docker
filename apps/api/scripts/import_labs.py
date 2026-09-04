"""Upsert dental labs / cases / cycles from MySQL without wiping clinic data.

Requires same MYSQL_* and DATABASE_URL env as import_mysql.py.

  python scripts/import_labs.py --clinic-id 1
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
from sqlalchemy import text

from app.db import Base, SessionLocal, engine
from app.models import DentalLab, LabCase, LabCaseCycle


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


def _as_bool(v) -> bool:
    return bool(int(v)) if v is not None else True


def _reset_lab_sequences(db) -> None:
    for table, col in (
        ("dental_labs", "lab_id"),
        ("lab_cases", "case_id"),
        ("lab_case_cycles", "cycle_id"),
    ):
        db.execute(
            text(
                f"SELECT setval(pg_get_serial_sequence('{table}', '{col}'), "
                f"COALESCE((SELECT MAX({col}) FROM {table}), 1))"
            )
        )


def import_labs(*, clinic_id: int) -> None:
    Base.metadata.create_all(bind=engine)
    src = _mysql()
    db = SessionLocal()
    try:
        with src.cursor() as cur:
            cur.execute(
                "SELECT * FROM dental_labs WHERE clinic_id=%s ORDER BY lab_id",
                (clinic_id,),
            )
            labs = cur.fetchall()
            for lab in labs:
                existing = db.get(DentalLab, lab["lab_id"])
                if existing:
                    existing.name = lab["name"]
                    existing.contact_person = lab.get("contact_person")
                    existing.phone = lab.get("phone")
                    existing.notes = lab.get("notes")
                    existing.visible = _as_bool(lab.get("visible", 1))
                    existing.updated_at = lab.get("updated_at")
                else:
                    db.add(
                        DentalLab(
                            lab_id=lab["lab_id"],
                            clinic_id=clinic_id,
                            name=lab["name"],
                            contact_person=lab.get("contact_person"),
                            phone=lab.get("phone"),
                            notes=lab.get("notes"),
                            visible=_as_bool(lab.get("visible", 1)),
                            created_by=lab.get("created_by"),
                            created_at=lab.get("created_at") or datetime.now(timezone.utc),
                            updated_at=lab.get("updated_at"),
                        )
                    )
            db.flush()

            cur.execute(
                "SELECT * FROM lab_cases WHERE clinic_id=%s ORDER BY case_id",
                (clinic_id,),
            )
            cases = cur.fetchall()
            for lc in cases:
                existing = db.get(LabCase, lc["case_id"])
                if existing:
                    existing.client_id = lc["client_id"]
                    existing.lab_id = lc["lab_id"]
                    existing.case_ref = lc["case_ref"]
                    existing.case_type = lc.get("case_type")
                    existing.tooth_numbers = lc.get("tooth_numbers")
                    existing.description = lc.get("description")
                    existing.current_cycle_number = int(lc.get("current_cycle_number") or 1)
                    existing.status = lc.get("status") or "open"
                    existing.closed_at = lc.get("closed_at")
                    existing.closed_by = lc.get("closed_by")
                    existing.visible = _as_bool(lc.get("visible", 1))
                    existing.updated_at = lc.get("updated_at")
                else:
                    db.add(
                        LabCase(
                            case_id=lc["case_id"],
                            clinic_id=clinic_id,
                            client_id=lc["client_id"],
                            lab_id=lc["lab_id"],
                            case_ref=lc["case_ref"],
                            case_type=lc.get("case_type"),
                            tooth_numbers=lc.get("tooth_numbers"),
                            description=lc.get("description"),
                            current_cycle_number=int(lc.get("current_cycle_number") or 1),
                            status=lc.get("status") or "open",
                            created_by=lc.get("created_by"),
                            closed_at=lc.get("closed_at"),
                            closed_by=lc.get("closed_by"),
                            visible=_as_bool(lc.get("visible", 1)),
                            created_at=lc.get("created_at") or datetime.now(timezone.utc),
                            updated_at=lc.get("updated_at"),
                        )
                    )
            db.flush()

            if cases:
                case_ids = [c["case_id"] for c in cases]
                fmt = ",".join(["%s"] * len(case_ids))
                cur.execute(
                    f"SELECT * FROM lab_case_cycles WHERE case_id IN ({fmt}) ORDER BY cycle_id",
                    case_ids,
                )
                cycles = cur.fetchall()
            else:
                cycles = []

            for cy in cycles:
                existing = db.get(LabCaseCycle, cy["cycle_id"])
                if existing:
                    existing.cycle_number = int(cy["cycle_number"])
                    existing.send_pending_at = cy.get("send_pending_at")
                    existing.send_pending_by = cy.get("send_pending_by")
                    existing.sent_at = cy.get("sent_at")
                    existing.sent_by = cy.get("sent_by")
                    existing.receive_pending_at = cy.get("receive_pending_at")
                    existing.receive_pending_by = cy.get("receive_pending_by")
                    existing.received_at = cy.get("received_at")
                    existing.received_by = cy.get("received_by")
                    existing.expected_return_date = cy.get("expected_return_date")
                    existing.notes = cy.get("notes")
                    existing.updated_at = cy.get("updated_at")
                else:
                    db.add(
                        LabCaseCycle(
                            cycle_id=cy["cycle_id"],
                            case_id=cy["case_id"],
                            cycle_number=int(cy["cycle_number"]),
                            send_pending_at=cy.get("send_pending_at"),
                            send_pending_by=cy.get("send_pending_by"),
                            sent_at=cy.get("sent_at"),
                            sent_by=cy.get("sent_by"),
                            receive_pending_at=cy.get("receive_pending_at"),
                            receive_pending_by=cy.get("receive_pending_by"),
                            received_at=cy.get("received_at"),
                            received_by=cy.get("received_by"),
                            expected_return_date=cy.get("expected_return_date"),
                            notes=cy.get("notes"),
                            created_at=cy.get("created_at") or datetime.now(timezone.utc),
                            updated_at=cy.get("updated_at"),
                        )
                    )

            db.commit()
            _reset_lab_sequences(db)
            db.commit()
            print(
                f"Upserted dental_labs={len(labs)} lab_cases={len(cases)} "
                f"lab_case_cycles={len(cycles)} for clinic_id={clinic_id}"
            )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        src.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import dental labs from MySQL → Postgres")
    parser.add_argument("--clinic-id", type=int, default=1)
    args = parser.parse_args()
    import_labs(clinic_id=args.clinic_id)


if __name__ == "__main__":
    main()
