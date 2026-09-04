from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text

from app.config import get_settings
from app.db import Base, engine
from app.routers import appointments, auth, billing, clients, desk, labs, media, prescriptions, settings, tasks

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
app.include_router(clients.router, prefix="/api")
app.include_router(appointments.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(prescriptions.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(desk.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(labs.router, prefix="/api")
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


@app.on_event("startup")
def on_startup() -> None:
    _ensure_media_schema()


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "service": settings_cfg.app_name, "go": "4.5"}
