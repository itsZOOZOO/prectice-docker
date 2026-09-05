"""Import warranty lookups + issued cards from MySQL into Postgres.

  cd apps/api && set -a && source .env && set +a
  python scripts/import_warranty_cards.py --clinic-id 1
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
from app.models import (
    Benefit,
    CardIssued,
    CardType,
    Client,
    ProductMembershipType,
    TermsCondition,
)


def _load_dotenv() -> None:
    """Load apps/api/.env with override (passwords may contain ';' which breaks `source`)."""
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ[key] = val


def _mysql():
    _load_dotenv()
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
    if v is None:
        return True
    return bool(int(v))


def _reset_sequences(db) -> None:
    # After bulk insert with explicit PKs, advance sequences or new rows collide.
    for table, col in (
        ("card_types", "id"),
        ("product_membership_types", "id"),
        ("terms_conditions", "id"),
        ("benefits", "id"),
        ("card_issued", "id"),
    ):
        db.execute(
            text(
                f"SELECT setval("
                f"pg_get_serial_sequence('{table}', '{col}'), "
                f"GREATEST(COALESCE((SELECT MAX({col}) FROM {table}), 1), 1), "
                f"true)"
            )
        )


def import_warranty(*, clinic_id: int) -> None:
    Base.metadata.create_all(bind=engine)
    src = _mysql()
    db = SessionLocal()
    stats: dict[str, int] = {
        "card_types": 0,
        "products": 0,
        "terms": 0,
        "benefits": 0,
        "cards_upserted": 0,
        "cards_skipped_no_client": 0,
    }
    try:
        with src.cursor() as cur:
            cur.execute(
                "SELECT * FROM card_types WHERE clinic_id=%s ORDER BY id",
                (clinic_id,),
            )
            for row in cur.fetchall():
                stats["card_types"] += 1
                rid = int(row["id"])
                existing = db.get(CardType, rid)
                if existing:
                    existing.clinic_id = clinic_id
                    existing.type_name = row.get("type_name") or existing.type_name
                    existing.note = row.get("note")
                    existing.user_id = int(row["user_id"]) if row.get("user_id") else None
                else:
                    db.add(
                        CardType(
                            id=rid,
                            clinic_id=clinic_id,
                            type_name=row.get("type_name") or "Card",
                            note=row.get("note"),
                            user_id=int(row["user_id"]) if row.get("user_id") else None,
                        )
                    )

            cur.execute(
                "SELECT * FROM product_membership_types WHERE clinic_id=%s ORDER BY id",
                (clinic_id,),
            )
            for row in cur.fetchall():
                stats["products"] += 1
                rid = int(row["id"])
                existing = db.get(ProductMembershipType, rid)
                if existing:
                    existing.clinic_id = clinic_id
                    existing.name = row.get("name") or existing.name
                    existing.note = row.get("note")
                    existing.user_id = int(row["user_id"]) if row.get("user_id") else None
                else:
                    db.add(
                        ProductMembershipType(
                            id=rid,
                            clinic_id=clinic_id,
                            name=row.get("name") or "Product",
                            note=row.get("note"),
                            user_id=int(row["user_id"]) if row.get("user_id") else None,
                        )
                    )

            cur.execute(
                "SELECT * FROM terms_conditions WHERE clinic_id=%s ORDER BY id",
                (clinic_id,),
            )
            for row in cur.fetchall():
                stats["terms"] += 1
                rid = int(row["id"])
                existing = db.get(TermsCondition, rid)
                if existing:
                    existing.clinic_id = clinic_id
                    existing.name = row.get("name") or existing.name
                    existing.detailed_condition = row.get("detailed_condition")
                    existing.note = row.get("note")
                    existing.user_id = int(row["user_id"]) if row.get("user_id") else None
                else:
                    db.add(
                        TermsCondition(
                            id=rid,
                            clinic_id=clinic_id,
                            name=row.get("name") or "Terms",
                            detailed_condition=row.get("detailed_condition"),
                            note=row.get("note"),
                            user_id=int(row["user_id"]) if row.get("user_id") else None,
                        )
                    )

            cur.execute(
                "SELECT * FROM benefits WHERE clinic_id=%s ORDER BY id",
                (clinic_id,),
            )
            for row in cur.fetchall():
                stats["benefits"] += 1
                rid = int(row["id"])
                existing = db.get(Benefit, rid)
                if existing:
                    existing.clinic_id = clinic_id
                    existing.name = row.get("name") or existing.name
                    existing.detailed_benefit = row.get("detailed_benefit")
                    existing.note = row.get("note")
                    existing.user_id = int(row["user_id"]) if row.get("user_id") else None
                else:
                    db.add(
                        Benefit(
                            id=rid,
                            clinic_id=clinic_id,
                            name=row.get("name") or "Benefit",
                            detailed_benefit=row.get("detailed_benefit"),
                            note=row.get("note"),
                            user_id=int(row["user_id"]) if row.get("user_id") else None,
                        )
                    )

            db.flush()

            cur.execute(
                """
                SELECT * FROM card_issued
                WHERE clinic_id=%s AND IFNULL(visible, 1)=1
                ORDER BY id
                """,
                (clinic_id,),
            )
            for row in cur.fetchall():
                client_id = int(row["client_id"])
                client = db.get(Client, client_id)
                if not client or client.clinic_id != clinic_id:
                    stats["cards_skipped_no_client"] += 1
                    continue
                rid = int(row["id"])
                existing = db.get(CardIssued, rid)
                payload = dict(
                    clinic_id=clinic_id,
                    client_id=client_id,
                    card_type_id=int(row["card_type_id"]),
                    product_id=int(row["product_id"]),
                    date_of_purchase=row["date_of_purchase"],
                    benefit_start_date=row["benefit_start_date"],
                    benefit_end_date=row["benefit_end_date"],
                    terms_conditions_id=int(row["terms_conditions_id"]),
                    benefit_id=int(row["benefit_id"]),
                    number_of_units=int(row.get("number_of_units") or 1),
                    note=row.get("note"),
                    unique_code=str(row.get("unique_code") or f"XX-IMP-{rid}"),
                    warranty_period=int(row.get("warranty_period") or 0),
                    visible=_as_bool(row.get("visible", 1)),
                    user_id=int(row["user_id"]) if row.get("user_id") else None,
                )
                if existing:
                    for k, v in payload.items():
                        setattr(existing, k, v)
                else:
                    db.add(CardIssued(id=rid, **payload))
                stats["cards_upserted"] += 1

        _reset_sequences(db)
        db.commit()
        print("Import complete:", stats)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        src.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clinic-id", type=int, default=1)
    args = parser.parse_args()
    import_warranty(clinic_id=args.clinic_id)


if __name__ == "__main__":
    main()
