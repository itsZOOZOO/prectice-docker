from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import Base, engine
from app.routers import appointments, auth, billing, clients, desk, prescriptions, settings, tasks

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


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "service": settings_cfg.app_name, "go": "4.5"}
