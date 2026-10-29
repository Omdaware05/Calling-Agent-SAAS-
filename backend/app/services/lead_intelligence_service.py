import os
import sys
import logging
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# Ensure the model package is importable
MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "model"))
if MODEL_DIR not in sys.path and os.path.exists(MODEL_DIR):
    sys.path.insert(0, MODEL_DIR)

try:
    from classifier.engine import IntentClassifier
    from classifier.models import IntentClassification, DetailedClassificationResponse
    from classifier.followup_detector import followup_detector, FollowupDetectionResult, FOLLOWUP_CATEGORIES
    _classifier_available = True
except Exception as e:
    logging.getLogger(__name__).warning(f"Could not import IntentClassifier or FollowupDetector from model dir: {e}")
    _classifier_available = False
    followup_detector = None
    FOLLOWUP_CATEGORIES = {}

try:
    # One-file offline analyzer (stdlib only): customer-info extraction,
    # why-interested / why-not reasons with evidence, lead score, Excel export.
    from transcript_analyzer import analyze_transcript as _analyze_transcript_offline
    _analyzer_available = True
except Exception as e:
    logging.getLogger(__name__).warning(f"Could not import transcript_analyzer: {e}")
    _analyzer_available = False
    _analyze_transcript_offline = None

from app.models.call import Call, Transcript, TranscriptSegment
from app.models.lead import Lead, Followup
from app.models.contact import Contact
from app.config import settings

logger = logging.getLogger(__name__)


class LeadIntelligenceService:
    """
    Lead Interest Intelligence Service powered by Google Gemini LLM
    with secondary fallback to the Multilingual AI Intent Classifier.
    Evaluates real customer conversation transcripts across English, Hindi (Devanagari & Hinglish),
    Marathi, and Indic code-mixed speech.
    Accurately scores confidence, explains reasoning, detects opt-outs, and manages the
    Interested Leads Pipeline.
    """

    def __init__(self):
        if _classifier_available:
            self.classifier = IntentClassifier()
        else:
            self.classifier = None

    def build_transcript_text(self, call: Call) -> str:
        """
        Extracts formatted multi-turn conversation text from call transcript segments.
        """
        if not call.transcript or not call.transcript.segments:
            return ""

        lines = []
        for seg in sorted(call.transcript.segments, key=lambda s: s.sequence if s.sequence is not None else 0):
            role_prefix = "Agent" if seg.speaker in ("agent", "bot", "assistant") else "Customer"
            lines.append(f"{role_prefix}: {seg.text}")

        return "\n".join(lines).strip()

    async def analyze_with_gemini(self, transcript_text: str) -> Optional[Dict[str, Any]]:
        """
        Uses Gemini LLM to accurately determine customer intent and interest from multi-turn transcript.
        Specifically handles Indic dialects, Hindi transliterations ('नॉट इंटरेस्टेड', 'नहीं चाहिए'),
        and nuanced sales conversation signals.
        """
        gemini_key = getattr(settings, "GEMINI_API_KEY", None) or os.environ.get("GEMINI_API_KEY", "")
        if not gemini_key:
            return None

        # Fast, low-latency, resilient model hierarchy
        configured_model = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
        candidate_models = list(dict.fromkeys([
            configured_model,
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-1.5-flash",
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash-lite",
            "gemini-flash-lite-latest",
        ]))

        prompt = f"""You are a specialized Lead Interest Intelligence analyzer for enterprise sales and support telephony calls.
Your objective: accurately classify customer intent from the conversation transcript.

Transcript to analyze:
\"\"\"
{transcript_text}
\"\"\"

Crucial Classification Rules:
1. Indic & Hindi Nuances:
   - Phrases like "नॉट इंटरेस्टेड", "not interested", "नहीं बोलना", "नहीं चाहिए", "phone mat karo", "fursat nahi hai", "cut the call", "wrong number", or hanging up with clear negative sentiment MUST BE CLASSIFIED AS:
     status: "not_interested", is_interested: false, classification: "NOT_INTERESTED", interest_strength: "NONE", confidence: 0.90 to 0.99.
   - Under NO circumstance should a customer rejection or refusal be classified as interested!
2. Genuine Interest:
   - Customer inquires about pricing, offers, products, or service assistance (e.g. "kya plan hai", "bataiye", "price kitna hai", agrees to next step/demo):
     status: "interested", is_interested: true, classification: "INTERESTED", interest_strength: "HIGH" or "MEDIUM", confidence: 0.70 to 0.99.
3. Callback Request:
   - Customer asks to be called back later ("baad mein call karo", "call tomorrow"):
     status: "callback_requested", is_interested: true, classification: "CALLBACK_REQUESTED", interest_strength: "MEDIUM", confidence: 0.80 to 0.95.
4. Ambiguous / Disconnected:
   - Customer only uttered greeting ("hello") or silence with no real engagement:
     status: "uncertain", is_interested: false, classification: "UNCERTAIN", interest_strength: "LOW", confidence: 0.30 to 0.50.

Return ONLY a valid JSON object with these exact keys:
{{
  "status": "interested" | "not_interested" | "callback_requested" | "uncertain",
  "is_interested": boolean,
  "classification": "INTERESTED" | "NOT_INTERESTED" | "CALLBACK_REQUESTED" | "UNCERTAIN",
  "interest_strength": "HIGH" | "MEDIUM" | "LOW" | "NONE",
  "confidence": float,
  "reasoning": string,
  "rule_applied": string,
  "signals": list of strings,
  "languages": list of strings,
  "opt_out_detected": boolean,
  "callback_requested": boolean
}}"""

        import httpx

        for model_name in candidate_models:
            m_clean = model_name if not model_name.startswith("models/") else model_name.split("/")[-1]
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_clean}:generateContent?key={gemini_key}"
            try:
                gen_config = {
                    "responseMimeType": "application/json",
                    "temperature": 0.1,
                }
                async with httpx.AsyncClient(timeout=25.0) as client:
                    resp = await client.post(
                        url,
                        json={
                            "contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": gen_config,
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        text_payload = data["candidates"][0]["content"]["parts"][0]["text"]
                        import json
                        parsed = json.loads(text_payload)
                        logger.info(f"Lead intelligence successfully evaluated via Gemini ({m_clean}): status={parsed.get('status')}, confidence={parsed.get('confidence')}")
                        return parsed
            except Exception as ex:
                logger.warning(f"Error querying Gemini model {m_clean} for lead intelligence: {type(ex).__name__} - {str(ex)[:100]}")

        return None

    async def analyze_call(self, session: AsyncSession, call: Call) -> Dict[str, Any]:
        """
        Analyzes a call's full transcript using Gemini LLM (with fallback to local engine)
        and updates the call disposition, contact suppression, and Interested Leads Pipeline.
        """
        transcript_text = self.build_transcript_text(call)

        # Handle empty/unrecorded calls
        if not transcript_text:
            return {
                "analysis_id": f"intel_{call.id}",
                "call_id": call.id,
                "agent_id": call.agent_id,
                "contact_id": call.contact_id,
                "status": "uncertain",
                "confidence_score": 0.0,
                "confidence": 0.0,
                "classification": "UNCERTAIN",
                "interest_strength": "UNKNOWN",
                "opt_out_detected": False,
                "callback_requested": False,
                "objection_detected": None,
                "reasoning": "No transcript turns available to evaluate customer intent.",
                "rule_applied": "No conversational data",
                "signals": [],
                "languages": [],
                "keywords": [],
                "created_at": datetime.now(UTC).isoformat(),
            }

        # 0. Offline analyzer (always available, stdlib only): extracts the
        # customer's stated details and WHY-reasons with evidence quotes.
        # This runs fully offline on any machine; Gemini/local classification
        # below stays the classifier of record.
        offline: Dict[str, Any] = {}
        customer_info: Dict[str, Any] = {}
        why_interested: List[Dict[str, str]] = []
        why_not_interested: List[Dict[str, str]] = []
        if _analyzer_available and _analyze_transcript_offline is not None:
            try:
                offline = _analyze_transcript_offline(transcript_text)
                customer_info = offline.get("customer_info") or {}
                why_interested = offline.get("why_interested") or []
                why_not_interested = offline.get("why_not_interested") or []
            except Exception as ae:
                logger.warning(f"Offline transcript analyzer failed: {ae}")

        # 1. Primary: Evaluate using Gemini LLM
        gemini_result = None
        try:
            gemini_result = await self.analyze_with_gemini(transcript_text)
        except Exception as ge:
            logger.warning(f"Gemini lead analysis failed, falling back to rule engine: {ge}")

        if gemini_result and isinstance(gemini_result, dict):
            status = gemini_result.get("status", "uncertain")
            is_interested = bool(gemini_result.get("is_interested", False))
            confidence = float(gemini_result.get("confidence", 0.85))
            classification_str = gemini_result.get("classification", "UNCERTAIN")
            interest_strength_str = gemini_result.get("interest_strength", "NONE" if not is_interested else "HIGH")
            opt_out = bool(gemini_result.get("opt_out_detected", False))
            callback_req = bool(gemini_result.get("callback_requested", False))
            reasoning = gemini_result.get("reasoning", "")
            rule_applied = gemini_result.get("rule_applied", "Gemini AI Lead Interest Intelligence")
            signals = gemini_result.get("signals", [])
            languages = gemini_result.get("languages", ["Hindi"])

            # Sync Call disposition
            if opt_out:
                status = "not_interested"
                call.disposition = "not_interested"
                if call.contact_id:
                    try:
                        c_stmt = select(Contact).where(Contact.id == call.contact_id)
                        c_res = await session.execute(c_stmt)
                        contact = c_res.scalar_one_or_none()
                        if contact:
                            contact.status = "do_not_call"
                            session.add(contact)
                    except Exception as ce:
                        logger.warning(f"Could not update contact DNC: {ce}")
            elif callback_req:
                status = "callback_requested"
                call.disposition = "callback_requested"
            elif is_interested:
                status = "interested"
                call.disposition = "interested"
            else:
                status = "not_interested"
                call.disposition = "not_interested"

            session.add(call)

            # Manage Lead in Database
            lead_stmt = select(Lead).where(Lead.call_id == call.id)
            lead_res = await session.execute(lead_stmt)
            existing_lead = lead_res.scalar_one_or_none()

            if is_interested and not opt_out:
                lead_metadata = {
                    "classification": classification_str,
                    "interest_strength": interest_strength_str,
                    "signals": signals,
                    "rule_applied": rule_applied,
                    "analyzer": "gemini",
                    "customer_info": customer_info,
                    "why_interested": why_interested,
                    "why_not_interested": why_not_interested,
                }
                phone = customer_info.get("phone") or call.phone_number or call.caller_number
                if not existing_lead:
                    existing_lead = Lead(
                        tenant_id=call.tenant_id,
                        agent_id=call.agent_id,
                        contact_id=call.contact_id,
                        call_id=call.id,
                        name=customer_info.get("name"),
                        email=customer_info.get("email"),
                        phone_number=phone,
                        score=confidence,
                        reason=reasoning,
                        status="interested",
                        metadata_json=lead_metadata,
                    )
                    session.add(existing_lead)
                else:
                    existing_lead.score = confidence
                    existing_lead.reason = reasoning
                    existing_lead.status = "interested"
                    existing_lead.metadata_json = lead_metadata
                    if customer_info.get("name"):
                        existing_lead.name = customer_info["name"]
                    if customer_info.get("email"):
                        existing_lead.email = customer_info["email"]
                    session.add(existing_lead)
            else:
                # If not genuinely interested, ensure FALSE leads are removed from pipeline
                if existing_lead:
                    await session.delete(existing_lead)

            # Check follow-up detector
            followup_info = None
            if followup_detector:
                try:
                    f_res = followup_detector.detect_followup_detailed(transcript_text)
                    if f_res.category_id is not None:
                        followup_info = {
                            "category_id": f_res.category_id,
                            "name": f_res.name,
                            "description": f_res.description,
                            "requires_followup": f_res.requires_followup,
                            "action": f_res.action,
                            "suggested_scheduled_at": f_res.suggested_scheduled_at,
                            "matched_utterance": f_res.matched_utterance,
                        }
                except Exception as fe:
                    logger.debug(f"Followup check exception: {fe}")

            return {
                "analysis_id": f"intel_{call.id}",
                "call_id": call.id,
                "agent_id": call.agent_id,
                "contact_id": call.contact_id,
                "status": status,
                "confidence_score": confidence,
                "confidence": confidence,
                "classification": classification_str,
                "binary_classification": "interested" if is_interested else "not_interested",
                "interest_strength": interest_strength_str,
                "opt_out_detected": opt_out,
                "callback_requested": callback_req,
                "objection_detected": None,
                "reasoning": reasoning,
                "rule_applied": rule_applied,
                "signals": signals,
                "languages": languages,
                "keywords": [f"Lang: {l}" for l in languages] + signals,
                "customer_info": customer_info,
                "why_interested": why_interested,
                "why_not_interested": why_not_interested,
                "offline_lead_score": offline.get("lead_score"),
                "followup": followup_info,
                "raw_model_output": gemini_result,
                "created_at": datetime.now(UTC).isoformat(),
            }

        # 2. Secondary Fallback: Use local rule classifier if Gemini was unavailable
        if self.classifier:
            try:
                diag: DetailedClassificationResponse = self.classifier.classify_detailed(transcript_text)
                is_interested = (
                    diag.classification in (IntentClassification.INTERESTED, IntentClassification.NEEDS_INFORMATION)
                    or diag.binary_classification == "INTERESTED"
                )
                confidence = float(diag.confidence)

                # Determine disposition and handle opt-out suppression
                if diag.opt_out_detected:
                    status = "not_interested"
                    call.disposition = "not_interested"
                    if call.contact_id:
                        try:
                            contact_stmt = select(Contact).where(Contact.id == call.contact_id)
                            c_res = await session.execute(contact_stmt)
                            contact = c_res.scalar_one_or_none()
                            if contact:
                                contact.status = "do_not_call"
                                session.add(contact)
                        except Exception as ce:
                            logger.warning(f"Could not update contact DNC status: {ce}")
                elif diag.callback_requested:
                    status = "callback_requested"
                    call.disposition = "callback_requested"
                elif is_interested:
                    status = "interested"
                    call.disposition = "interested"
                else:
                    status = "not_interested"
                    call.disposition = "not_interested"

                session.add(call)

                # Auto-create or update Lead record if interested and NOT opted-out
                lead_stmt = select(Lead).where(Lead.call_id == call.id)
                lead_res = await session.execute(lead_stmt)
                lead = lead_res.scalar_one_or_none()

                if is_interested and not diag.opt_out_detected:
                    lead_metadata = {
                        "classification": diag.classification.value,
                        "interest_strength": diag.interest_strength.value,
                        "objection_detected": diag.objection_detected,
                        "signals": diag.signals_detected,
                        "rule_applied": diag.rule_applied,
                        "analyzer": "rule_engine",
                        "customer_info": customer_info,
                        "why_interested": why_interested,
                        "why_not_interested": why_not_interested,
                    }
                    if not lead:
                        lead = Lead(
                            tenant_id=call.tenant_id,
                            agent_id=call.agent_id,
                            contact_id=call.contact_id,
                            call_id=call.id,
                            name=customer_info.get("name"),
                            email=customer_info.get("email"),
                            phone_number=customer_info.get("phone") or call.phone_number or call.caller_number,
                            score=confidence,
                            reason=diag.reason,
                            status="interested",
                            metadata_json=lead_metadata,
                        )
                        session.add(lead)
                    else:
                        lead.score = confidence
                        lead.reason = diag.reason
                        lead.status = "interested"
                        lead.metadata_json = lead_metadata
                        if customer_info.get("name"):
                            lead.name = customer_info["name"]
                        if customer_info.get("email"):
                            lead.email = customer_info["email"]
                        session.add(lead)
                else:
                    if lead:
                        await session.delete(lead)

                keywords = list(diag.signals_detected) if diag.signals_detected else []
                if diag.languages_detected:
                    keywords.extend([f"Lang: {l}" for l in diag.languages_detected if l not in keywords])

                followup_info = None
                if followup_detector:
                    f_res = followup_detector.detect_followup_detailed(transcript_text)
                    if f_res.category_id is not None:
                        followup_info = {
                            "category_id": f_res.category_id,
                            "name": f_res.name,
                            "description": f_res.description,
                            "requires_followup": f_res.requires_followup,
                            "action": f_res.action,
                            "suggested_scheduled_at": f_res.suggested_scheduled_at,
                            "matched_utterance": f_res.matched_utterance,
                        }

                return {
                    "analysis_id": f"intel_{call.id}",
                    "call_id": call.id,
                    "agent_id": call.agent_id,
                    "contact_id": call.contact_id,
                    "status": status,
                    "confidence_score": confidence,
                    "confidence": confidence,
                    "classification": diag.classification.value,
                    "binary_classification": diag.binary_classification or ("interested" if is_interested else "not_interested"),
                    "interest_strength": diag.interest_strength.value,
                    "opt_out_detected": diag.opt_out_detected,
                    "callback_requested": diag.callback_requested,
                    "objection_detected": diag.objection_detected,
                    "reasoning": diag.reason,
                    "rule_applied": diag.rule_applied,
                    "signals": diag.signals_detected,
                    "languages": diag.languages_detected,
                    "keywords": keywords,
                    "customer_info": customer_info,
                    "why_interested": why_interested,
                    "why_not_interested": why_not_interested,
                    "offline_lead_score": offline.get("lead_score"),
                    "followup": followup_info,
                    "raw_model_output": diag.model_dump(),
                    "created_at": datetime.now(UTC).isoformat(),
                }
            except Exception as e:
                logger.error(f"IntentClassifier fallback failed on call {call.id}: {e}", exc_info=True)


        # Fallback if engine unavailable
        return {
            "analysis_id": f"intel_{call.id}",
            "call_id": call.id,
            "agent_id": call.agent_id,
            "contact_id": call.contact_id,
            "status": "uncertain",
            "confidence_score": 0.5,
            "confidence": 0.5,
            "classification": "UNCERTAIN",
            "reasoning": "Model classifier engine could not be executed.",
            "rule_applied": "Fallback",
            "signals": [],
            "languages": [],
            "keywords": [],
            "followup": None,
            "created_at": datetime.now(UTC).isoformat(),
        }

    async def analyze_followup(self, session: AsyncSession, call: Call) -> Dict[str, Any]:
        """
        Evaluates the transcript using the 25-category Follow-Up Detection Engine.
        If a follow-up condition is detected, optionally records or updates the Followup table.
        """
        transcript_text = self.build_transcript_text(call)
        if not followup_detector:
            return {
                "call_id": call.id,
                "category_id": None,
                "name": None,
                "requires_followup": False,
                "message": "Followup detector engine unavailable"
            }

        res: FollowupDetectionResult = followup_detector.detect_followup_detailed(transcript_text)
        scheduled_dt = None
        if res.suggested_scheduled_at:
            try:
                scheduled_dt = datetime.fromisoformat(res.suggested_scheduled_at.replace("Z", "+00:00"))
            except Exception:
                pass

        followup_record_id = None
        # Auto-create or update Followup record if category requires follow-up
        call_phone = call.phone_number or call.caller_number
        if res.requires_followup and call_phone:
            stmt = select(Followup).where(Followup.call_id == call.id)
            db_res = await session.execute(stmt)
            followup = db_res.scalar_one_or_none()
            notes_str = f"Category {res.category_id}: {res.name}. Action: {res.action}. (Matched: '{res.matched_utterance or 'N/A'}')"

            if not followup:
                followup = Followup(
                    tenant_id=call.tenant_id,
                    contact_id=call.contact_id,
                    agent_id=call.agent_id,
                    call_id=call.id,
                    phone_number=call_phone,
                    scheduled_at=scheduled_dt,
                    status="pending",
                    notes=notes_str,
                )
                session.add(followup)
            else:
                followup.scheduled_at = scheduled_dt or followup.scheduled_at
                followup.notes = notes_str
                followup.status = "pending"

            await session.flush()
            followup_record_id = followup.id

        return {
            "call_id": call.id,
            "agent_id": call.agent_id,
            "category_id": res.category_id,
            "name": res.name,
            "description": res.description,
            "requires_followup": res.requires_followup,
            "action": res.action,
            "suggested_scheduled_at": res.suggested_scheduled_at,
            "matched_utterance": res.matched_utterance,
            "priority_level": res.priority_level,
            "followup_id": followup_record_id,
        }


lead_intelligence_service = LeadIntelligenceService()

