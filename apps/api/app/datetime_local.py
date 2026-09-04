"""Parse datetime-local strings as clinic wall time (Asia/Kolkata)."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

CLINIC_TZ = ZoneInfo("Asia/Kolkata")


def parse_clinic_local_datetime(value: str | None) -> datetime | None:
    """Interpret YYYY-MM-DDTHH:mm (or with seconds) as Asia/Kolkata wall time.

    Raises ValueError if the string is non-empty but not a valid datetime.
    """
    if value is None:
        return None
    raw = str(value).strip().replace(" ", "T")
    if not raw:
        return None
    if raw.endswith("Z"):
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    # Offset after the date (e.g. ...+05:30 or ...-05:00)
    if len(raw) > 19 and ("+" in raw[19:] or raw[19:].startswith("-")):
        return datetime.fromisoformat(raw)
    if len(raw) == 16:
        naive = datetime.strptime(raw, "%Y-%m-%dT%H:%M")
    elif len(raw) >= 19:
        naive = datetime.strptime(raw[:19], "%Y-%m-%dT%H:%M:%S")
    else:
        naive = datetime.fromisoformat(raw)
        if naive.tzinfo is not None:
            return naive
    return naive.replace(tzinfo=CLINIC_TZ)
