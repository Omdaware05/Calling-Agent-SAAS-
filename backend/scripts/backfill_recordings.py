import asyncio
import os
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.call import Call, Recording
from app.services.call_service import persist_post_call_artifacts
from app.services.storage.s3 import storage_service

async def main():
    async with AsyncSessionLocal() as session:
        stmt = select(Call).where(Call.status == "completed")
        res = await session.execute(stmt)
        calls = res.scalars().all()
        print(f"Found {len(calls)} completed calls.")

        for call in calls:
            await persist_post_call_artifacts(session, call)
            storage_key = f"calls/{call.id}/recording.wav"
            exists = await storage_service.exists(storage_key)
            print(f"Call {call.id}: recording_url={call.recording_url}, exists_in_storage={exists}")
        await session.commit()
    print("Backfill complete.")

if __name__ == "__main__":
    asyncio.run(main())
