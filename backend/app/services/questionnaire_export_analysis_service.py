"""Persisted Gemini extraction for questionnaire-based lead exports."""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.agent import Agent
from app.models.call import Call, Transcript, TranscriptSegment
from app.models.questionnaire import Questionnaire

logger = logging.getLogger(__name__)


def lead_questions(questionnaire: Questionnaire) -> List[Dict[str, str]]:
    questions: List[Dict[str, str]] = []
    for index, item in enumerate(questionnaire.questions or []):
        if str(item.get("type") or "text").lower() in {"reference", "follow_up", "closing"}:
            continue
        text = str(item.get("text") or "").strip()
        if text:
            questions.append({"id": str(item.get("question_id") or f"question_{index + 1}"), "question": text})
    return questions


async def analyze_transcript(transcript_text: str, questions: List[Dict[str, str]]) -> Dict[str, Any]:
    """Return only customer-stated answers and a factual one-paragraph remark."""
    api_key = getattr(settings, "GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
    if not transcript_text:
        return {"answers": {}, "remarks": "No transcript available for analysis.", "status": "no_transcript"}
    if not api_key:
        return {"answers": {}, "remarks": "Gemini API key is not configured.", "status": "not_configured"}

    prompt = f"""Extract lead information from this voice-call transcript.
Use only facts spoken by the CUSTOMER. Do not infer or invent. A missing field must be an empty string.
Lead fields: {json.dumps(questions, ensure_ascii=False)}
Return ONLY valid JSON:
{{"answers": {{"field_id": "customer answer"}}, "remarks": "Brief factual summary of need, questions, objections/callback request, and next action."}}
Transcript:\n{transcript_text[:18000]}"""
    configured = (getattr(settings, "GEMINI_MODEL", "gemini-flash-lite-latest") or "gemini-flash-lite-latest").replace("models/", "")
    # Keep current model aliases first. Retired 1.5/2.x names return HTTP 404
    # for newer Gemini API accounts and must not be used as the only fallback.
    candidates = list(dict.fromkeys([
        configured,
        "gemini-flash-lite-latest",
        "gemini-flash-latest",
        "gemini-3.8-flash",
    ]))
    last_error = ""
    async with httpx.AsyncClient(timeout=30.0) as client:
        for model in candidates:
            try:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.0},
                    },
                )
                if response.status_code != 200:
                    last_error = f"HTTP {response.status_code}"
                    logger.warning("Questionnaire export Gemini model %s failed: %s", model, last_error)
                    continue
                content = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                if content.startswith("```"):
                    content = content.strip("`").removeprefix("json").strip()
                parsed = json.loads(content)
                answers = parsed.get("answers") if isinstance(parsed.get("answers"), dict) else {}
                return {
                    "answers": {str(key): str(value or "") for key, value in answers.items()},
                    "remarks": str(parsed.get("remarks") or ""),
                    "status": "completed",
                    "model": model,
                }
            except Exception as exc:
                last_error = type(exc).__name__
                logger.warning("Questionnaire export Gemini model %s error: %s", model, str(exc)[:180])
    return {"answers": {}, "remarks": "Gemini analysis pending; please export again after checking Gemini configuration.", "status": "failed", "error": last_error}


async def analyze_and_store_call(session: AsyncSession, call: Call, segments: Optional[List[Any]] = None) -> Optional[Dict[str, Any]]:
    """Run after a call ends and cache extraction in Call.context_data."""
    agent = await session.get(Agent, call.agent_id)
    if not agent or not agent.questionnaire_id:
        return None
    questionnaire = await session.get(Questionnaire, agent.questionnaire_id)
    if not questionnaire:
        return None
    existing = (call.context_data or {}).get("questionnaire_export_analysis")
    if (
        isinstance(existing, dict)
        and (call.context_data or {}).get("questionnaire_export_questionnaire_id") == questionnaire.id
        and existing.get("status") == "completed"
    ):
        return existing
    questions = lead_questions(questionnaire)
    if not questions:
        return None
    if segments is None:
        from sqlalchemy import select
        result = await session.execute(
            select(TranscriptSegment).join(Transcript).where(Transcript.call_id == call.id).order_by(TranscriptSegment.sequence.asc())
        )
        segments = result.scalars().all()
    lines = []
    for segment in segments or []:
        speaker = segment.get("speaker", "") if isinstance(segment, dict) else getattr(segment, "speaker", "")
        text = segment.get("text", "") if isinstance(segment, dict) else getattr(segment, "text", "")
        label = "Agent" if str(speaker).lower() in {"agent", "assistant", "bot"} else "Customer"
        lines.append(f"{label}: {text}")
    analysis = await analyze_transcript("\n".join(lines), questions)
    context = dict(call.context_data or {})
    context["questionnaire_export_analysis"] = analysis
    context["questionnaire_export_questionnaire_id"] = questionnaire.id
    call.context_data = context
    return analysis
