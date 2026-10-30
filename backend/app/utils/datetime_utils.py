from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def to_iso_utc(dt: Optional[datetime | str]) -> Optional[str]:
    """
    Standardize any datetime or ISO string to an explicit UTC ISO-8601 string
    ending with 'Z' (e.g. '2026-10-30T11:04:00.410692Z').
    """
    if dt is None:
        return None
    if isinstance(dt, str):
        s = dt.strip()
        if not s:
            return None
        # Replace space with T for ISO format
        if " " in s and "T" not in s:
            s = s.replace(" ", "T")
        if s.endswith("+00:00"):
            return s[:-6] + "Z"
        if s.endswith("Z") or ("+" in s[10:]) or ("-" in s[10:]):
            return s
        return s + "Z"

    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    s = dt.isoformat()
    if s.endswith("+00:00"):
        s = s[:-6] + "Z"
    elif not s.endswith("Z") and not ("+" in s[10:] or "-" in s[10:]):
        s += "Z"
    return s


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Ensure a datetime is converted to UTC and stripped of tzinfo for safe SQLite storage.
    If dt has tzinfo (e.g. Asia/Kolkata), convert to UTC then strip tzinfo.
    If dt is naive, assume it is already UTC.
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt
