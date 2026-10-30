import asyncio
import os
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.call import Call, Recording
from app.services.call_service import persist_post_call_artifacts
from app.services.storage.s3 import storage_service

async def main(dry_run: bool = False, limit: int = 0):
    async with AsyncSessionLocal() as session:
        stmt = select(Call).where(Call.status == "completed")
        res = await session.execute(stmt)
        calls = res.scalars().all()
        if limit:
            calls = calls[:limit]
        print(f"Found {len(calls)} completed calls.{' (DRY RUN: read-only)' if dry_run else ''}")

        for call in calls:
            if dry_run:
                storage_key = f"calls/{call.id}/recording.wav"
                exists = await storage_service.exists(storage_key)
                print(f"Call {call.id}: recording_url={call.recording_url}, exists_in_storage={exists}")
                continue
            await persist_post_call_artifacts(session, call)
            storage_key = f"calls/{call.id}/recording.wav"
            exists = await storage_service.exists(storage_key)
            print(f"Call {call.id}: recording_url={call.recording_url}, exists_in_storage={exists}")
        await session.commit()
    print("Backfill complete.")

if __name__ == "__main__":
    import sys as _sys
    _limit = 0
    if "--limit" in _sys.argv:
        _limit = int(_sys.argv[_sys.argv.index("--limit") + 1])
    asyncio.run(main(dry_run="--dry-run" in _sys.argv, limit=_limit))
