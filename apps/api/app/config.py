from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Prectice"
    database_url: str = "postgresql+psycopg://prectice:prectice@127.0.0.1:5432/prectice"
    jwt_secret: str = "change-me"
    jwt_expire_hours: int = 72
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Legacy Quantum Dental S3 — set via apps/api/.env (never commit keys)
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    s3_bucket: str = "quantum-dental-patients-files"
    s3_region: str = "ap-south-1"
    s3_url_ttl: int = 3600

    # Staff app notifications (reporting.pratikp.com) — empty key = disabled
    reporting_api_url: str = "https://reporting.pratikp.com/api.php"
    reporting_api_key: str = ""
    reporting_group_id: int = 1

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def s3_configured(self) -> bool:
        return bool(self.aws_access_key_id and self.aws_secret_access_key and self.s3_bucket)


@lru_cache
def get_settings() -> Settings:
    return Settings()
