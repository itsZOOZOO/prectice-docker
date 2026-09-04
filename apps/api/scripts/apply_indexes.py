"""Apply Go 4 Postgres indexes."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from app.db import engine


def main() -> None:
    sql_path = Path(__file__).with_name("apply_indexes.sql")
    sql = sql_path.read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.execute(text(sql))
    print(f"Applied indexes from {sql_path.name}")


if __name__ == "__main__":
    main()
