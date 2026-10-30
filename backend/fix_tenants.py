"""One-off repair: assign a tenant to agents/calls whose tenant_id IS NULL.

Safeguarded version. The original hard-coded one tenant UUID and a
relative DB path and committed immediately — run from the wrong
directory or against the wrong database it permanently mis-assigned
every orphaned row to a single client (cross-tenant corruption).

Usage:
    python fix_tenants.py --db path/to.db --tenant <tenant-uuid>          # dry run (default)
    python fix_tenants.py --db path/to.db --tenant <tenant-uuid> --apply  # actually write
The tenant id / DB path can also come from FIX_TENANTS_TENANT_ID /
FIX_TENANTS_DB env vars.
"""
import argparse
import os
import sqlite3
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.environ.get("FIX_TENANTS_DB", "calling_agent.db"))
    ap.add_argument("--tenant", default=os.environ.get("FIX_TENANTS_TENANT_ID", ""))
    ap.add_argument("--apply", action="store_true", help="actually write (default is a dry run)")
    args = ap.parse_args()

    if not args.tenant:
        print("ERROR: --tenant <tenant-uuid> is required (no hard-coded default anymore).")
        return 2
    if not os.path.exists(args.db):
        print(f"ERROR: database not found at {args.db!r} — pass --db explicitly.")
        return 2

    conn = sqlite3.connect(args.db)
    c = conn.cursor()
    n_agents = c.execute("SELECT COUNT(*) FROM agents WHERE tenant_id IS NULL").fetchone()[0]
    n_calls = c.execute("SELECT COUNT(*) FROM calls WHERE tenant_id IS NULL").fetchone()[0]
    print(f"DB: {args.db}")
    print(f"Rows with tenant_id IS NULL: agents={n_agents}, calls={n_calls}")
    print(f"Target tenant: {args.tenant}")

    if not args.apply:
        print("DRY RUN — nothing written. Re-run with --apply to commit.")
        conn.close()
        return 0

    c.execute("UPDATE agents SET tenant_id = ? WHERE tenant_id IS NULL", (args.tenant,))
    c.execute("UPDATE calls SET tenant_id = ? WHERE tenant_id IS NULL", (args.tenant,))
    conn.commit()
    print(f"Applied to agents={n_agents}, calls={n_calls}.")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
