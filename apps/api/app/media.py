"""S3 resolve + upload/delete for legacy Quantum Dental bucket."""

from __future__ import annotations

import re
import time
from functools import lru_cache

import boto3
from botocore.client import Config
from fastapi import HTTPException, status

from app.config import get_settings

MAX_NOTE_FILES = 10
MAX_FILE_BYTES = 10 * 1024 * 1024
ALLOWED_NOTE_MIME = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/heic",
    "image/heif",
    "application/pdf",
}
ALLOWED_PHOTO_MIME = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/heic",
    "image/heif",
}


@lru_cache
def _s3_client():
    settings = get_settings()
    if not settings.s3_configured:
        return None
    return boto3.client(
        "s3",
        region_name=settings.s3_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        config=Config(signature_version="s3v4"),
    )


def require_s3():
    client = _s3_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="S3 is not configured (set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY)",
        )
    return client, get_settings()


def resolve_media_key(raw: str | None) -> str | None:
    if not raw:
        return None
    key = raw.strip()
    if not key:
        return None
    if key.startswith("http://") or key.startswith("https://"):
        return key

    settings = get_settings()
    client = _s3_client()
    if client is None:
        return None
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket, "Key": key},
            ExpiresIn=settings.s3_url_ttl,
        )
    except Exception:  # noqa: BLE001
        return None


def resolve_many(keys: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in keys:
        url = resolve_media_key(key)
        if url:
            out[key] = url
    return out


def _sanitize_filename(name: str) -> str:
    base = name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    cleaned = re.sub(r"[^a-zA-Z0-9.\-_]", "", base) or "file"
    return cleaned[:120]


def make_upload_key(filename: str, index: int = 0) -> str:
    return f"upload/{int(time.time())}_{index}_{_sanitize_filename(filename)}"


def upload_bytes(data: bytes, *, filename: str, content_type: str, index: int = 0) -> str:
    client, settings = require_s3()
    key = make_upload_key(filename, index)
    client.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=data,
        ContentType=content_type or "application/octet-stream",
    )
    return key


def upload_bytes_key(data: bytes, *, key: str, content_type: str) -> str:
    """Upload to an explicit S3 key (e.g. prescription PDFs for WhatsApp)."""
    client, settings = require_s3()
    cleaned = key.strip().lstrip("/")
    if not cleaned:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid S3 key")
    client.put_object(
        Bucket=settings.s3_bucket,
        Key=cleaned,
        Body=data,
        ContentType=content_type or "application/octet-stream",
    )
    return cleaned


def presign_get(key: str, *, expires_in: int | None = None) -> str:
    client, settings = require_s3()
    cleaned = key.strip()
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        return cleaned
    ttl = expires_in if expires_in is not None else settings.s3_url_ttl
    # S3 max presign is 7 days for IAM user credentials
    ttl = max(60, min(int(ttl), 604800))
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": cleaned},
        ExpiresIn=ttl,
    )


def delete_object(key: str | None) -> None:
    if not key or key.startswith("http://") or key.startswith("https://"):
        return
    client, settings = require_s3()
    try:
        client.delete_object(Bucket=settings.s3_bucket, Key=key.strip())
    except Exception:  # noqa: BLE001 — best-effort delete
        pass


def validate_note_file(content_type: str | None, size: int, filename: str) -> str:
    mime = (content_type or "").split(";")[0].strip().lower() or "application/octet-stream"
    if mime not in ALLOWED_NOTE_MIME:
        # Fallback by extension
        lower = filename.lower()
        if lower.endswith((".jpg", ".jpeg")):
            mime = "image/jpeg"
        elif lower.endswith(".png"):
            mime = "image/png"
        elif lower.endswith(".webp"):
            mime = "image/webp"
        elif lower.endswith(".gif"):
            mime = "image/gif"
        elif lower.endswith((".heic", ".heif")):
            mime = "image/heic"
        elif lower.endswith(".pdf"):
            mime = "application/pdf"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type for {filename} (images or PDF only)",
            )
    if size > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'File "{filename}" exceeds the 10 MB limit',
        )
    if size <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'Empty file "{filename}"')
    return mime


def validate_photo_file(content_type: str | None, size: int, filename: str) -> str:
    mime = validate_note_file(content_type, size, filename)
    if mime == "application/pdf":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profile photo must be an image")
    if mime not in ALLOWED_PHOTO_MIME and not mime.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profile photo must be an image")
    return mime
