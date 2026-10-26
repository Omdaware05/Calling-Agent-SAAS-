import asyncio
import os
import sys

# Ensure backend root is on sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import AsyncSessionLocal
from app.models.call import Call, Transcript
from app.models.lead import Lead
from app.services.lead_intelligence_service import lead_intelligence_service

async def reclassify_all_calls():
    print("--- Starting Lead Intelligence Re-classification via Gemini ---")
    async with AsyncSessionLocal() as session:
        # Load all calls with their transcripts and segments
        stmt = select(Call).options(
            selectinload(Call.transcript).selectinload(Transcript.segments)
        ).order_by(Call.created_at.desc())
        
        res = await session.execute(stmt)
        calls = res.scalars().all()
        print(f"Total calls found in database: {len(calls)}")
        
        reclassified_count = 0
        interested_count = 0
        not_interested_count = 0
        uncertain_count = 0
        
        for call in calls:
            transcript_text = lead_intelligence_service.build_transcript_text(call)
            if not transcript_text:
                continue
            
            reclassified_count += 1
            print(f"\nEvaluating Call ID: {call.id} | Phone: {call.phone_number or call.caller_number}")
            print(f"Transcript lines: {len(transcript_text.splitlines())}")
            
            try:
                result = await lead_intelligence_service.analyze_call(session, call)
                status = result.get("status")
                conf = result.get("confidence", 0.0)
                reason = result.get("reasoning", "")
                
                print(f"-> Status: {status} | Confidence: {conf * 100:.1f}%")
                # print reasoning safely
                safe_reason = reason.encode("ascii", "replace").decode("ascii")
                print(f"-> Reasoning: {safe_reason}")
                
                if status == "interested":
                    interested_count += 1
                elif status == "not_interested":
                    not_interested_count += 1
                else:
                    uncertain_count += 1
            except Exception as e:
                print(f"Error evaluating call {call.id}: {e}")
            await asyncio.sleep(0.3)
        
        await session.commit()
        
        # Verify and clean any stale/orphan leads whose call is not interested
        leads_res = await session.execute(select(Lead))
        all_leads = leads_res.scalars().all()
        for lead in all_leads:
            if lead.call_id:
                call_stmt = select(Call).where(Call.id == lead.call_id)
                c_res = await session.execute(call_stmt)
                c = c_res.scalar_one_or_none()
                if c and (c.disposition or "").lower() != "interested":
                    print(f"Removing false lead for non-interested call {lead.call_id}")
                    await session.delete(lead)
        await session.commit()

        # Check current leads table after cleanup
        leads_res = await session.execute(select(Lead))
        all_leads = leads_res.scalars().all()
        print(f"\n==========================================")
        print(f"Re-classification Summary:")
        print(f"Calls re-analyzed: {reclassified_count}")
        print(f"Interested: {interested_count}")
        print(f"Not Interested: {not_interested_count}")
        print(f"Uncertain: {uncertain_count}")
        print(f"Final Qualified Leads in Pipeline: {len(all_leads)}")
        for lead in all_leads:
            safe_r = (lead.reason or "").encode("ascii", "replace").decode("ascii")
            print(f"  * Lead [{lead.phone_number}] Score: {((lead.score or 0) * 100):.1f}% | Reason: {safe_r}")
        print(f"==========================================")

if __name__ == "__main__":
    asyncio.run(reclassify_all_calls())
