"""
Offline callback-time understanding for automatic rescheduling.

Stdlib only — no API keys, no network, runs on any low-end machine.

Two jobs:
1. ``parse_callback_time`` — turn what the customer said on the call
   ("call me tomorrow at 5 pm", "kal shaam ko 6 baje", "2 ghante baad",
   "udya sakali phone kara") into a concrete local datetime.
2. ``next_working_slot`` — move that moment inside working hours
   (09:00–19:00, Asia/Kolkata): requests before 09:00 are called at
   09:00 the same day; requests at/after 19:00 are called at 09:00 the
   NEXT day, so an out-of-hours promise never fires at night.

The detector (model/classifier/followup_detector.py) decides WHETHER a
follow-up is needed; this module decides WHEN, from the customer's own
words, instead of a fixed per-category delay.
"""

from __future__ import annotations

import re
from datetime import datetime, time as dtime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Asia/Kolkata")
WORK_START = dtime(9, 0)
WORK_END = dtime(19, 0)
# Never schedule in the immediate next minutes — the customer just hung up.
MIN_LEAD = timedelta(minutes=10)

_WEEKDAYS = {
    "monday": 0, "somvaar": 0, "somvar": 0,
    "tuesday": 1, "mangalvaar": 1, "mangalvar": 1,
    "wednesday": 2, "budhvaar": 2, "budhvar": 2,
    "thursday": 3, "guruvaar": 3, "guruvar": 3,
    "friday": 4, "shukravaar": 4, "shukravar": 4,
    "saturday": 5, "shanivaar": 5, "shanivar": 5,
    "sunday": 6, "ravivaar": 6, "ravivar": 6,
}

_DAYPARTS = [
    (re.compile(r"\b(subah|sakali|sakal|morning)\b"), dtime(10, 0)),
    (re.compile(r"\b(dopahar|dupari|afternoon|lunch)\b"), dtime(13, 30)),
    (re.compile(r"\b(shaam|sandhya|sandhyakal|evening)\b"), dtime(17, 30)),
    (re.compile(r"\b(raat|ratri|night)\b"), dtime(20, 30)),
]


def _customer_text(transcript: str) -> str:
    """Use only customer lines when role prefixes exist (like the detector)."""
    lines = []
    has_roles = False
    for line in transcript.split("\n"):
        s = line.strip()
        low = s.lower()
        if any(low.startswith(p) for p in ("customer:", "user:", "client:", "caller:")):
            has_roles = True
            lines.append(s.split(":", 1)[1].strip())
        elif any(low.startswith(p) for p in ("agent:", "assistant:", "bot:")):
            has_roles = True
    if has_roles and lines:
        return " ".join(lines)
    return transcript


def _parse_clock(text: str) -> Optional[dtime]:
    """Extract a time-of-day from '5 pm', '17:30', '6 baje', daypart words."""
    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", text)
    if m:
        hour = int(m.group(1)) % 12
        if m.group(3) == "pm":
            hour += 12
        return dtime(hour, int(m.group(2) or 0))

    m = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", text)
    if m:
        return dtime(int(m.group(1)), int(m.group(2)))

    m = re.search(r"\b(\d{1,2})\s*(baje|vajta|waje)\b", text)
    if m:
        hour = int(m.group(1))
        if re.search(r"\b(subah|sakali|morning)\b", text):
            return dtime(hour % 12, 0)
        if re.search(r"\b(shaam|sandhya|evening|raat|night)\b", text):
            return dtime(hour % 12 + 12 if hour != 12 else 12, 0)
        # Bare "5 baje" in Indian usage almost always means the evening;
        # 7–11 stays morning, 12 is noon.
        if 1 <= hour <= 6:
            return dtime(hour + 12, 0)
        return dtime(hour, 0)

    for pattern, t in _DAYPARTS:
        if pattern.search(text):
            return t
    return None


def parse_callback_time(transcript: str, now: Optional[datetime] = None) -> Optional[datetime]:
    """
    Parse the customer's requested callback moment from a transcript.
    Returns a timezone-aware datetime in Asia/Kolkata (NOT yet adjusted
    to working hours), or None when no time was mentioned.
    """
    if not transcript or not transcript.strip():
        return None
    now = now or datetime.now(LOCAL_TZ)
    if now.tzinfo is None:
        now = now.replace(tzinfo=LOCAL_TZ)
    text = _customer_text(transcript).lower()

    # 1) Relative offsets: "in 2 hours", "30 minutes later", "2 ghante baad"
    m = re.search(r"\bin\s+(\d+)\s*(minutes?|mins?|hours?|hrs?|days?)\b", text)
    if not m:
        m = re.search(r"\b(\d+)\s*(ghante|ghanta|hours?|hrs?|minutes?|mins?)\s*(baad|later|after)\b", text)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        if unit.startswith(("hour", "hr", "ghant")):
            return now + timedelta(hours=n)
        if unit.startswith("day"):
            return now + timedelta(days=n)
        return now + timedelta(minutes=n)
    if re.search(r"\b(aadha|half)\s*(ghanta|hour)\b", text):
        return now + timedelta(minutes=30)

    # 2) Day selection
    day_offset: Optional[int] = None
    if re.search(r"\b(day after tomorrow|parso|parwa)\b", text):
        day_offset = 2
    elif re.search(r"\b(tomorrow|kal|udya|udiya)\b", text):
        day_offset = 1
    elif re.search(r"\b(today|aaj|aata)\b", text):
        day_offset = 0
    elif re.search(r"\bnext week\b", text):
        day_offset = 7
    else:
        for name, weekday in _WEEKDAYS.items():
            if re.search(rf"\b{name}\b", text):
                day_offset = (weekday - now.weekday()) % 7
                break

    clock = _parse_clock(text)

    if day_offset is None and clock is None:
        return None

    base_date = now.date() + timedelta(days=day_offset or 0)
    if clock is None:
        # A day with no time: late morning is the safest default.
        clock = dtime(11, 0)
    result = datetime.combine(base_date, clock, tzinfo=LOCAL_TZ)

    # A bare clock time ("call at 5 pm") with no day means today when it
    # is still ahead, otherwise tomorrow.
    if day_offset is None and result <= now:
        result += timedelta(days=1)
    return result


def next_working_slot(desired: datetime, now: Optional[datetime] = None) -> datetime:
    """
    Move a desired callback moment into working hours (09:00–19:00 IST):
    before 09:00 → 09:00 the same day; at/after 19:00 → 09:00 the next
    day. Moments already past roll forward to the next valid slot.
    """
    now = now or datetime.now(LOCAL_TZ)
    if now.tzinfo is None:
        now = now.replace(tzinfo=LOCAL_TZ)
    candidate = desired
    if candidate.tzinfo is None:
        candidate = candidate.replace(tzinfo=LOCAL_TZ)
    candidate = candidate.astimezone(LOCAL_TZ)

    earliest = now + MIN_LEAD
    if candidate < earliest:
        candidate = earliest

    for _ in range(4):
        t = candidate.time()
        if t < WORK_START:
            candidate = candidate.replace(hour=WORK_START.hour, minute=0, second=0, microsecond=0)
        elif t >= WORK_END:
            candidate = (candidate + timedelta(days=1)).replace(hour=WORK_START.hour, minute=0, second=0, microsecond=0)
        else:
            break
        if candidate < earliest:
            candidate = (candidate + timedelta(days=1)).replace(hour=WORK_START.hour, minute=0, second=0, microsecond=0)
    return candidate


def schedule_from_transcript(transcript: str, now: Optional[datetime] = None) -> Optional[datetime]:
    """Parse + working-hours in one call; None when no time was stated."""
    desired = parse_callback_time(transcript, now=now)
    if desired is None:
        return None
    return next_working_slot(desired, now=now)
