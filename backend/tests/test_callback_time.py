"""Offline tests for the callback-time parser + working-hours rules.

Run with pytest, or directly:  python tests/test_callback_time.py
All cases use a fixed 'now': Wednesday 2026-10-29 14:00 IST.
"""
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.callback_time import (  # noqa: E402
    next_working_slot,
    parse_callback_time,
    schedule_from_transcript,
)

IST = ZoneInfo("Asia/Kolkata")
NOW = datetime(2026, 10, 29, 14, 0, tzinfo=IST)  # a Wednesday afternoon


def at(day_offset, hour, minute=0):
    base = NOW + __import__("datetime").timedelta(days=day_offset)
    return base.replace(hour=hour, minute=minute, second=0, microsecond=0)


def test_tomorrow_at_5pm_stays():
    got = schedule_from_transcript("Customer: Please call me tomorrow at 5 pm", now=NOW)
    assert got == at(1, 17), got


def test_tomorrow_at_8pm_moves_to_next_day_9am():
    # 20:00 is outside working hours -> 09:00 the following day
    got = schedule_from_transcript("Customer: call me tomorrow at 8 pm", now=NOW)
    assert got == at(2, 9), got


def test_hindi_kal_shaam_6_baje():
    got = schedule_from_transcript("Customer: kal shaam ko 6 baje call karna", now=NOW)
    assert got == at(1, 18), got


def test_marathi_udya_sakali():
    got = schedule_from_transcript("Customer: udya sakali phone kara", now=NOW)
    assert got == at(1, 10), got


def test_two_ghante_baad():
    got = schedule_from_transcript("Customer: main abhi busy hoon, 2 ghante baad call karo", now=NOW)
    assert got == at(0, 16), got


def test_evening_request_at_night_rolls_to_next_morning():
    got = schedule_from_transcript("Customer: shaam ko call karna", now=NOW)
    # today 17:30 is in hours and ahead -> stays today
    assert got == at(0, 17, 30), got


def test_bare_time_in_past_goes_tomorrow():
    got = schedule_from_transcript("Customer: call at 11 am", now=NOW)
    assert got == at(1, 11), got


def test_early_morning_becomes_9am_same_day():
    desired = parse_callback_time("Customer: tomorrow 7 am call karna", now=NOW)
    got = next_working_slot(desired, now=NOW)
    assert got == at(1, 9), got


def test_no_time_mentioned_returns_none():
    assert parse_callback_time("Customer: yes I am interested, send details", now=NOW) is None
    assert schedule_from_transcript("Customer: theek hai", now=NOW) is None


def test_weekday_next_monday():
    got = schedule_from_transcript("Customer: call me on monday at 12 pm", now=NOW)
    # 2026-10-29 is Thursday; next Monday is +4 days
    assert got == at(4, 12), got


def test_agent_words_are_ignored():
    t = "Agent: I will call you tomorrow at 5 pm\nCustomer: no, not interested"
    assert parse_callback_time(t, now=NOW) is None


def test_in_30_minutes_evening_overflow():
    late = datetime(2026, 10, 29, 18, 50, tzinfo=IST)
    got = schedule_from_transcript("Customer: call me in 30 minutes", now=late)
    # 19:20 is outside hours -> next day 09:00
    assert got == datetime(2026, 10, 30, 9, 0, tzinfo=IST), got


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("PASS", fn.__name__)
    print(f"{len(fns)}/{len(fns)} callback-time tests passed")


def test_named_weekday_already_past_means_next_week():
    # Friday 2026-10-30 18:00 IST: "call me Friday at 5 pm" must mean NEXT
    # Friday (2026-11-06 17:00), not today 17:00 clamped to ~now.
    fri_evening = datetime(2026, 10, 30, 18, 0, tzinfo=IST)
    got = schedule_from_transcript("Customer: call me Friday at 5 pm", now=fri_evening)
    assert got == datetime(2026, 11, 6, 17, 0, tzinfo=IST), got


def test_named_weekday_still_ahead_stays_this_week():
    # NOW is Thursday 2026-10-29 14:00 -> "Friday at 5 pm" is tomorrow,
    # Friday 2026-10-30 17:00.
    got = schedule_from_transcript("Customer: call me Friday at 5 pm", now=NOW)
    assert got == datetime(2026, 10, 30, 17, 0, tzinfo=IST), got
