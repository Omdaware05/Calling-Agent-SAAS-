import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.call import Call, Recording, Transcript, TranscriptSegment
from app.services.call_service import persist_post_call_artifacts
from app.services.redis_service import redis_service
from app.services.storage.s3 import storage_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def backfill_and_verify():
    print("=" * 60)
    print("STARTING CALL DATA-STORAGE ARCHITECTURE VERIFICATION & BACKFILL")
    print("=" * 60)

    # 1. Test Redis
    print("\n--- 1. Testing Redis Temporary State Cache ---")
    client = await redis_service.get_client()
    if client:
        await redis_service.record_call_event_metric("system.verify")
        print("  Redis connection: OK")
    else:
        print("  Redis connection: FAILED")

    # 2. Test MinIO
    print("\n--- 2. Testing MinIO Call Recordings Storage ---")
    minio_client = storage_service._client
    if minio_client:
        print(f"  MinIO connected: Endpoint={storage_service.endpoint_url}, Bucket={storage_service.bucket}")
    else:
        print("  MinIO connection: FAILED")

    # 3. Backfill Existing Calls in PostgreSQL
    print("\n--- 3. Backfilling Existing Calls in PostgreSQL ---")
    async with AsyncSessionLocal() as session:
        stmt = (
            select(Call)
            .options(
                selectinload(Call.agent),
                selectinload(Call.transcript).selectinload(Transcript.segments),
                selectinload(Call.recording),
            )
        )
        res = await session.execute(stmt)
        calls = list(res.scalars().all())
        print(f"  Found {len(calls)} calls in PostgreSQL")

        for c in calls:
            print(f"  Processing call {c.id} (Status: {c.status}, Phone: {c.phone_number})...")
            await persist_post_call_artifacts(session, c)
            await session.commit()
            await session.refresh(c, ["recording", "transcript"])
            print(f"    - Recording in DB: {c.recording.storage_key if c.recording else 'None'}")
            print(f"    - Transcript in DB: {c.transcript.id if c.transcript else 'None'}")

        # Verification Query
        print("\n--- 4. Verification Check Across MinIO, Postgres & Redis ---")
        stmt_verify = (
            select(Call)
            .options(
                selectinload(Call.agent),
                selectinload(Call.transcript).selectinload(Transcript.segments),
                selectinload(Call.recording),
            )
        )
        res_verify = await session.execute(stmt_verify)
        verified_calls = list(res_verify.scalars().all())

        for c in verified_calls:
            # Check MinIO
            has_audio = False
            audio_size = 0
            if c.recording and c.recording.storage_key:
                has_audio = await storage_service.exists(c.recording.storage_key)
                if has_audio:
                    audio_bytes = await storage_service.download(c.recording.storage_key)
                    audio_size = len(audio_bytes) if audio_bytes else 0

            # Check Transcript segments
            num_segments = len(c.transcript.segments) if (c.transcript and c.transcript.segments) else 0

            print(f"\nCall ID: {c.id}")
            print(f"  Caller Phone: {c.phone_number}")
            print(f"  Status: {c.status}")
            print(f"  PostgreSQL Call -> MinIO Recording link: {c.recording.storage_key if c.recording else 'Missing'}")
            print(f"  MinIO File Exists: {has_audio} ({audio_size} bytes)")
            print(f"  PostgreSQL Transcript Segments count: {num_segments}")
            if num_segments > 0:
                print(f"  Sample Turn: [{c.transcript.segments[0].speaker.upper()}]: {c.transcript.segments[0].text[:60]}...")

    print("\n" + "=" * 60)
    print("DATA-STORAGE ARCHITECTURE VERIFICATION COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(backfill_and_verify())
