"""Upload letterhead backgrounds from apps/api/assets to S3.

  python scripts/sync_prescription_backgrounds_to_s3.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

from app import media as media_svc

ASSETS = ROOT / "assets"


def main() -> None:
    files = [
        ASSETS / "prescription_background.jpg",
        ASSETS / "prescription_backgrounds" / "clinic_1_bg.jpg",
    ]
    missing = [str(p) for p in files if not p.is_file()]
    if missing:
        raise SystemExit(f"Missing local assets:\n  " + "\n  ".join(missing))

    client, settings = media_svc.require_s3()
    for path in files:
        key = str(path.relative_to(ASSETS)).replace("\\", "/")
        body = path.read_bytes()
        client.put_object(
            Bucket=settings.s3_bucket,
            Key=key,
            Body=body,
            ContentType="image/jpeg",
        )
        print(f"uploaded s3://{settings.s3_bucket}/{key} ({len(body)} bytes)")


if __name__ == "__main__":
    main()
