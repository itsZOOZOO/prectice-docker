from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import func, text

from app.config import get_settings
from app.db import Base, engine
from app import models as _models  # noqa: F401 — register metadata
from app.routers import (
    activity,
    admin,
    appointments,
    auth,
    billing,
    call_intelligence,
    clients,
    desk,
    labs,
    lead_intelligence,
    media,
    prescriptions,
    settings,
    settings_clinic,
    settings_client_filters,
    settings_doctors,
    settings_medicine,
    settings_setup,
    settings_treatments,
    settings_warranty,
    statistics,
    tasks,
    treatment_plans,
    warranty_cards,
)

settings_cfg = get_settings()

app = FastAPI(title=settings_cfg.app_name, version="0.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings_cfg.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(activity.router, prefix="/api")
app.include_router(clients.router, prefix="/api")
app.include_router(appointments.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(prescriptions.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(desk.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(settings_clinic.router, prefix="/api")
app.include_router(settings_doctors.router, prefix="/api")
app.include_router(settings_medicine.router, prefix="/api")
app.include_router(settings_treatments.router, prefix="/api")
app.include_router(settings_warranty.router, prefix="/api")
app.include_router(settings_client_filters.router, prefix="/api")
app.include_router(settings_client_filters.dashboard_router, prefix="/api")
app.include_router(settings_setup.router, prefix="/api")
app.include_router(statistics.router, prefix="/api")
app.include_router(call_intelligence.router, prefix="/api")
app.include_router(call_intelligence.status_router, prefix="/api")
app.include_router(lead_intelligence.router, prefix="/api")
app.include_router(lead_intelligence.status_router, prefix="/api")
app.include_router(labs.router, prefix="/api")
app.include_router(treatment_plans.router, prefix="/api")
app.include_router(warranty_cards.router, prefix="/api")
app.include_router(media.router, prefix="/api")


def _ensure_media_schema() -> None:
    """Additive columns/tables for media without Alembic (pilot)."""
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE notes ADD COLUMN IF NOT EXISTS attachment_url VARCHAR(512)"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS attachment_url VARCHAR(512)"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE task_notes ADD COLUMN IF NOT EXISTS attachment_url VARCHAR(512)"
            )
        )
        # Nullable first (no DEFAULT on ADD — that would backfill all legacy rows).
        conn.execute(
            text(
                "ALTER TABLE card_issued ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE card_issued ALTER COLUMN created_at SET DEFAULT now()"
            )
        )
        # Desk settings Wave 1 — additive column (create_all won't alter existing tables).
        conn.execute(
            text(
                """
                DO $$
                BEGIN
                  IF to_regclass('appointments_services') IS NOT NULL THEN
                    ALTER TABLE appointments_services
                      ADD COLUMN IF NOT EXISTS allow_public_booking BOOLEAN NOT NULL DEFAULT false;
                  END IF;
                END $$;
                """
            )
        )
    Base.metadata.create_all(bind=engine)
    # Keep serials ahead of imported explicit PKs (warranty cards, etc.)
    with engine.begin() as conn:
        for table, col in (
            ("card_issued", "id"),
            ("card_types", "id"),
            ("product_membership_types", "id"),
            ("terms_conditions", "id"),
            ("benefits", "id"),
            ("task_notes", "note_id"),
            ("treatment_photos", "photo_id"),
            ("price_option_photos", "photo_id"),
            ("appointments_doctor_breaks", "break_id"),
            ("appointments_doctor_time_off", "time_off_id"),
            ("appointments_doctor_services", "id"),
            ("clinic_client_filters", "filter_id"),
            ("clinic_client_filter_members", "id"),
        ):
            conn.execute(
                text(
                    f"""
                    DO $$
                    BEGIN
                      IF to_regclass('{table}') IS NOT NULL
                         AND pg_get_serial_sequence('{table}', '{col}') IS NOT NULL THEN
                        PERFORM setval(
                          pg_get_serial_sequence('{table}', '{col}'),
                          GREATEST(COALESCE((SELECT MAX({col}) FROM {table}), 1), 1),
                          true
                        );
                      END IF;
                    END $$;
                    """
                )
            )


def _promote_aarogyam_superadmin() -> None:
    """One-shot: clinic 1 username admin → superadmin (platform ops)."""
    from app.db import SessionLocal
    from app.models import User

    db = SessionLocal()
    try:
        row = (
            db.query(User)
            .filter(User.clinic_id == 1, func.lower(User.username) == "admin")
            .first()
        )
        if row and (row.role or "").lower() != "superadmin":
            row.role = "superadmin"
            db.commit()
    finally:
        db.close()


@app.on_event("startup")
def on_startup() -> None:
    _ensure_media_schema()
    try:
        _promote_aarogyam_superadmin()
    except Exception:  # noqa: BLE001 — don't block boot
        pass


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "service": settings_cfg.app_name, "go": "4.5"}
