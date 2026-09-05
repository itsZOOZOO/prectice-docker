"""Widen live MySQL pdf_templates text columns (fixes truncated WhatsApp slots).

  python scripts/widen_mysql_pdf_templates.py

Requires MYSQL_* in apps/api/.env
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

import pymysql


def main() -> None:
    missing = [k for k in ("MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE") if not os.getenv(k)]
    if missing:
        raise SystemExit(f"Missing env: {', '.join(missing)}")

    ssl_mode = os.getenv("MYSQL_SSL", "1")
    kwargs: dict = dict(
        host=os.environ["MYSQL_HOST"],
        user=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        database=os.environ["MYSQL_DATABASE"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=30,
    )
    if ssl_mode not in {"0", "false", "False"}:
        kwargs["ssl"] = {"ssl": True}

    conn = pymysql.connect(**kwargs)
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW COLUMNS FROM pdf_templates LIKE 'header_content'")
            before_h = cur.fetchone()
            cur.execute("SHOW COLUMNS FROM pdf_templates LIKE 'footer_content'")
            before_f = cur.fetchone()
            print("before header_content:", before_h)
            print("before footer_content:", before_f)

            cur.execute("ALTER TABLE pdf_templates MODIFY header_content TEXT NULL")
            cur.execute("ALTER TABLE pdf_templates MODIFY footer_content TEXT NULL")
            # logo_path can be long relative paths
            cur.execute("ALTER TABLE pdf_templates MODIFY logo_path VARCHAR(512) NULL")
            conn.commit()

            cur.execute("SHOW COLUMNS FROM pdf_templates LIKE 'header_content'")
            print("after header_content:", cur.fetchone())
            cur.execute("SHOW COLUMNS FROM pdf_templates LIKE 'footer_content'")
            print("after footer_content:", cur.fetchone())
            cur.execute("SHOW COLUMNS FROM pdf_templates LIKE 'logo_path'")
            print("after logo_path:", cur.fetchone())
        print("MySQL pdf_templates columns widened. Re-save clinic WhatsApp templates in the PHP template manager so full slot JSON is stored.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
