"""One-off: normalize agent voice_ids to the Sarvam voice set.

Safeguarded version. The original hard-coded a personal Windows path
(d:\\Final Project\\...) and committed a catch-all UPDATE immediately.
Now: the DB path comes from --db / CALLING_AGENT_DB, matching row
counts are printed first, and nothing is written without --apply.
"""
import argparse
import os
import sqlite3
import sys

UPDATES = [
    ("shreya (by name)", "voice_id = 'shreya'", "lower(name) LIKE '%shreya%'"),
    ("shubh (by name)", "voice_id = 'shubh'", "lower(name) LIKE '%yash%' OR lower(name) LIKE '%ai calling%'"),
    ("aditya (by name)", "voice_id = 'aditya'", "lower(name) LIKE '%aman%'"),
    ("shubh (legacy dg voices / NULL)", "voice_id = 'shubh'", "voice_id LIKE 'dg_voice_%' OR voice_id IS NULL"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.environ.get("CALLING_AGENT_DB", "calling_agent.db"))
    ap.add_argument("--apply", action="store_true", help="actually write (default is a dry run)")
    args = ap.parse_args()

    if not os.path.exists(args.db):
        print(f"ERROR: database not found at {args.db!r} — pass --db explicitly.")
        return 2

    con = sqlite3.connect(args.db)
    cur = con.cursor()
    print(f"DB: {args.db}")
    for label, _set_clause, where in UPDATES:
        n = cur.execute(f"SELECT COUNT(*) FROM agents WHERE {where}").fetchone()[0]
        print(f"  {label}: {n} row(s) would change")

    if not args.apply:
        print("DRY RUN — nothing written. Re-run with --apply to commit.")
        con.close()
        return 0

    for _label, set_clause, where in UPDATES:
        cur.execute(f"UPDATE agents SET {set_clause} WHERE {where}")
    con.commit()
    print("Updated agents:")
    for row in cur.execute("SELECT id, name, voice_id FROM agents").fetchall():
        print(row)
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
