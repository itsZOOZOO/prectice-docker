from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import func, text

from app.config import get_settings
from app.db import Base, engine
from app import models as _models  # noqa: F401 — register metadata
from app.routers import (
    admin,
    appointments,
    auth,
    billing,
    clients,
    desk,
    labs,
    media,
    prescriptions,
    settings,
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
app.include_router(clients.router, prefix="/api")
app.include_router(appointments.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(prescriptions.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(desk.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
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
    Base.metadata.create_all(bind=engine)
    # Keep serials ahead of imported explicit PKs (warranty cards, etc.)
    with engine.begin() as conn:
        for table, col in (
            ("card_issued", "id"),
            ("card_types", "id"),
            ("product_membership_types", "id"),
            ("terms_conditions", "id"),
            ("benefits", "id"),
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
