"""Upsert treatments / price options / treatment plans from MySQL.

Requires same MYSQL_* and DATABASE_URL env as import_mysql.py.

  python scripts/import_treatment_plans.py --clinic-id 1
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
from app.models import (
    PriceOption,
    Treatment,
    TreatmentPlan,
    TreatmentSubPlan,
    TreatmentSubPlanPhoto,
)


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
    return bool(int(v)) if v is not None else False


def _reset_sequences(db) -> None:
    for table, col in (
        ("treatments", "treatment_id"),
        ("price_options", "price_option_id"),
        ("treatment_plans", "plan_id"),
        ("treatment_sub_plans", "sub_plan_id"),
        ("treatment_sub_plan_photos", "photo_id"),
    ):
        db.execute(
            text(
                f"SELECT setval(pg_get_serial_sequence('{table}', '{col}'), "
                f"COALESCE((SELECT MAX({col}) FROM {table}), 1))"
            )
        )


def import_treatment_plans(*, clinic_id: int) -> None:
    Base.metadata.create_all(bind=engine)
    src = _mysql()
    db = SessionLocal()
    stats: dict[str, int] = {}
    try:
        with src.cursor() as cur:
            cur.execute(
                "SELECT * FROM treatments WHERE clinic_id=%s ORDER BY id",
                (clinic_id,),
            )
            treatments = cur.fetchall()
            stats["treatments"] = len(treatments)
            treatment_ids: list[int] = []
            for t in treatments:
                tid = int(t["id"])
                treatment_ids.append(tid)
                existing = db.get(Treatment, tid)
                if existing:
                    existing.clinic_id = clinic_id
                    existing.name = t.get("name") or existing.name
                    existing.short_explainer = t.get("short_explainer")
                    existing.default_appts = int(t.get("default_appts") or 0)
                    existing.active = _as_bool(t.get("active", 1)) if t.get("active") is not None else True
                    existing.sort_order = int(t.get("sort_order") or 0)
                else:
                    db.add(
                        Treatment(
                            treatment_id=tid,
                            clinic_id=clinic_id,
                            name=t.get("name") or f"Treatment {tid}",
                            short_explainer=t.get("short_explainer"),
                            default_appts=int(t.get("default_appts") or 0),
                            active=_as_bool(t.get("active", 1)) if t.get("active") is not None else True,
                            sort_order=int(t.get("sort_order") or 0),
                        )
                    )
            db.flush()

            price_options = []
            if treatment_ids:
                fmt = ",".join(["%s"] * len(treatment_ids))
                cur.execute(
                    f"SELECT * FROM price_options WHERE treatment_id IN ({fmt}) ORDER BY id",
                    treatment_ids,
                )
                price_options = cur.fetchall()
            stats["price_options"] = len(price_options)
            for po in price_options:
                pid = int(po["id"])
                existing = db.get(PriceOption, pid)
                if existing:
                    existing.treatment_id = int(po["treatment_id"])
                    existing.label = po.get("label") or existing.label
                    existing.price = po.get("price") or 0
                    existing.explainer = po.get("explainer")
                    existing.is_foc = _as_bool(po.get("is_foc"))
                else:
                    db.add(
                        PriceOption(
                            price_option_id=pid,
                            treatment_id=int(po["treatment_id"]),
                            label=po.get("label") or "Option",
                            price=po.get("price") or 0,
                            explainer=po.get("explainer"),
                            is_foc=_as_bool(po.get("is_foc")),
                        )
                    )
            db.flush()

            # Plans authored by clinic users
            cur.execute(
                """
                SELECT tp.*
                FROM treatment_plans tp
                JOIN users u ON u.user_id = tp.user_id
                WHERE u.clinic_id = %s
                ORDER BY tp.id
                """,
                (clinic_id,),
            )
            plans = cur.fetchall()
            stats["treatment_plans"] = 0
            plan_ids: list[int] = []
            for p in plans:
                if p.get("client_id") is None:
                    continue
                plan_id = int(p["id"])
                plan_ids.append(plan_id)
                stats["treatment_plans"] += 1
                visible = _as_bool(p.get("visible", 1)) if p.get("visible") is not None else True
                if p.get("deleted_at"):
                    visible = False
                existing = db.get(TreatmentPlan, plan_id)
                if existing:
                    existing.clinic_id = clinic_id
                    existing.client_id = int(p["client_id"])
                    existing.user_id = p.get("user_id")
                    existing.title = p.get("title")
                    existing.notes = p.get("notes")
                    existing.visible = visible
                    existing.locked_at = p.get("locked_at")
                    existing.deleted_at = p.get("deleted_at")
                    existing.created_at = p.get("created_at") or existing.created_at
                else:
                    db.add(
                        TreatmentPlan(
                            plan_id=plan_id,
                            clinic_id=clinic_id,
                            client_id=int(p["client_id"]),
                            user_id=p.get("user_id"),
                            title=p.get("title"),
                            notes=p.get("notes"),
                            visible=visible,
                            locked_at=p.get("locked_at"),
                            deleted_at=p.get("deleted_at"),
                            created_at=p.get("created_at") or datetime.now(timezone.utc),
                        )
                    )
            db.flush()

            sub_plans = []
            if plan_ids:
                fmt = ",".join(["%s"] * len(plan_ids))
                cur.execute(
                    f"SELECT * FROM treatment_sub_plans WHERE plan_id IN ({fmt}) ORDER BY id",
                    plan_ids,
                )
                sub_plans = cur.fetchall()
            stats["treatment_sub_plans"] = len(sub_plans)
            sub_ids: list[int] = []
            for sp in sub_plans:
                sid = int(sp["id"])
                sub_ids.append(sid)
                existing = db.get(TreatmentSubPlan, sid)
                payload = dict(
                    plan_id=int(sp["plan_id"]),
                    treatment_id=int(sp["treatment_id"]),
                    type=sp.get("type") or "Definitive",
                    complaint_text=sp.get("complaint_text"),
                    location_text=sp.get("location_text"),
                    tooth_fdi=sp.get("tooth_fdi"),
                    qty=int(sp.get("qty") or 1),
                    notes=sp.get("notes"),
                    user_id=sp.get("user_id"),
                    chosen_price_option_id=sp.get("chosen_price_option_id"),
                    is_foc=_as_bool(sp.get("is_foc")),
                )
                if existing:
                    for k, v in payload.items():
                        setattr(existing, k, v)
                else:
                    db.add(TreatmentSubPlan(sub_plan_id=sid, **payload))
            db.flush()

            photos = []
            if sub_ids:
                fmt = ",".join(["%s"] * len(sub_ids))
                cur.execute(
                    f"SELECT * FROM treatment_sub_plan_photos WHERE sub_plan_id IN ({fmt}) ORDER BY id",
                    sub_ids,
                )
                photos = cur.fetchall()
            stats["treatment_sub_plan_photos"] = len(photos)
            for ph in photos:
                pid = int(ph["id"])
                key = (ph.get("url") or "").strip()
                if not key:
                    continue
                existing = db.get(TreatmentSubPlanPhoto, pid)
                if existing:
                    existing.sub_plan_id = int(ph["sub_plan_id"])
                    existing.photo_url = key
                    existing.sort_order = int(ph.get("sort_order") or 0)
                else:
                    db.add(
                        TreatmentSubPlanPhoto(
                            photo_id=pid,
                            sub_plan_id=int(ph["sub_plan_id"]),
                            photo_url=key,
                            sort_order=int(ph.get("sort_order") or 0),
                        )
                    )

            db.commit()
            _reset_sequences(db)
            db.commit()

        print("Treatment plan import complete")
        for k, v in stats.items():
            print(f"  {k}: {v}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        src.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import MySQL treatment plans → Postgres")
    parser.add_argument("--clinic-id", type=int, default=1)
    args = parser.parse_args()
    import_treatment_plans(clinic_id=args.clinic_id)


if __name__ == "__main__":
    main()
