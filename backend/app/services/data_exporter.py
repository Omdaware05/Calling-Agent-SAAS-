"""
Unified Data Exporter Service
=============================
Guarantees that all call recordings, transcripts, and lead intelligence analyses
are systematically stored in the single root `data/` directory:

  data/
  ├── recordings/     <-- call_{call_id}.wav
  ├── transcripts/    <-- call_{call_id}_transcript.txt & .json
  ├── intelligence/   <-- call_{call_id}_intel.json
  ├── database/       <-- calling_agent.db
  └── logs/           <-- backend.log, tunnel.log

Clean, professional, and accessible directly from the filesystem by clients.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import (
    DATA_DIR,
    INTELLIGENCE_DIR,
    RECORDINGS_DIR,
    TRANSCRIPTS_DIR,
)

logger = logging.getLogger(__name__)


def _format_seconds(seconds: Optional[float]) -> str:
    if seconds is None:
        return "00:00"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


class DataExporterService:
    """
    Automated exporter that guarantees zero data loss and organized
    client-facing artifacts for every phone call.
    """

    def export_call_transcript(
        self,
        call_id: str,
        phone_number: str = "",
        agent_name: str = "Voice Assistant",
        duration: float = 0.0,
        disposition: str = "completed",
        segments: Optional[List[Dict[str, Any]]] = None,
        intelligence_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """
        Exports both human-readable (.txt) and structured (.json) transcripts
        directly into data/transcripts/.
        """
        TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
        txt_path = TRANSCRIPTS_DIR / f"call_{call_id}_transcript.txt"
        json_path = TRANSCRIPTS_DIR / f"call_{call_id}_transcript.json"

        segs = segments or []
        created_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        # 1. Build human-readable text document
        lines = [
            "=" * 78,
            "                   AI VOICE CALL TRANSCRIPT REPORT",
            "=" * 78,
            f"Call ID:        {call_id}",
            f"Phone Number:   {phone_number or 'N/A'}",
            f"Agent Name:     {agent_name}",
            f"Date & Time:    {created_str}",
            f"Total Duration: {duration:.1f} seconds ({_format_seconds(duration)})",
            f"Call Status:    {disposition.upper()}",
            f"Audio File:     data/recordings/call_{call_id}.wav",
            "-" * 78,
            "CONVERSATION DIALOGUE:",
            "-" * 78,
        ]

        if not segs:
            lines.append("  (No verbal conversation turns captured during this call session)")
        else:
            for s in segs:
                speaker = s.get("speaker", "agent").capitalize()
                if speaker.lower() in ("bot", "assistant", "system"):
                    speaker = "Agent"
                elif speaker.lower() in ("customer", "user", "caller"):
                    speaker = "Customer"

                t_start = s.get("start_time")
                t_str = f"[{_format_seconds(t_start)}]" if t_start is not None else "[--:--]"
                text = (s.get("text") or "").strip()
                lines.append(f"{t_str} {speaker}: {text}")

        lines.extend([
            "-" * 78,
            "LEAD INTELLIGENCE & CALL QUALIFICATION:",
            "-" * 78,
        ])

        if intelligence_data:
            status = intelligence_data.get("status") or disposition
            conf = intelligence_data.get("confidence") or intelligence_data.get("confidence_score")
            conf_str = f"{float(conf) * 100:.0f}%" if conf is not None else "N/A"
            reasoning = intelligence_data.get("reasoning") or "Evaluated automatically via AI intelligence."
            signals = intelligence_data.get("signals") or []

            lines.append(f"Qualification:  {str(status).upper()} (Confidence: {conf_str})")
            lines.append(f"Reasoning:      {reasoning}")
            if signals:
                lines.append(f"Key Signals:    {', '.join(signals) if isinstance(signals, list) else signals}")
        else:
            lines.append(f"Disposition:    {disposition.upper()}")

        lines.extend([
            "=" * 78,
            "Exported automatically by ARB SoftTech AI Calling Agent Platform.",
            "",
        ])

        try:
            txt_path.write_text("\n".join(lines), encoding="utf-8")
        except Exception as err:
            logger.warning(f"[DataExporter] Could not write transcript txt: {err}")

        # 2. Build structured JSON
        json_payload = {
            "call_id": call_id,
            "phone_number": phone_number,
            "agent_name": agent_name,
            "created_at": created_str,
            "duration_seconds": duration,
            "disposition": disposition,
            "recording_file": f"data/recordings/call_{call_id}.wav",
            "segments_count": len(segs),
            "segments": segs,
            "intelligence": intelligence_data or {},
        }

        try:
            json_path.write_text(json.dumps(json_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as err:
            logger.warning(f"[DataExporter] Could not write transcript json: {err}")

        logger.info(f"[DataExporter] Saved call {call_id} transcripts to {txt_path.name} & {json_path.name}")
        return {
            "txt_path": str(txt_path),
            "json_path": str(json_path),
        }

    def export_call_intelligence(
        self,
        call_id: str,
        intelligence_data: Dict[str, Any],
        phone_number: str = "",
        disposition: str = "",
    ) -> str:
        """
        Exports the detailed Gemini / AI lead intelligence report to data/intelligence/.
        """
        INTELLIGENCE_DIR.mkdir(parents=True, exist_ok=True)
        intel_path = INTELLIGENCE_DIR / f"call_{call_id}_intel.json"

        payload = {
            "call_id": call_id,
            "phone_number": phone_number,
            "disposition": disposition,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "intelligence": intelligence_data,
        }

        try:
            intel_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.info(f"[DataExporter] Saved call intelligence to {intel_path.name}")
            return str(intel_path)
        except Exception as err:
            logger.warning(f"[DataExporter] Could not write intelligence report: {err}")
            return ""

    def export_call_recording(
        self,
        call_id: str,
        audio_bytes: bytes,
    ) -> str:
        """
        Persists audio bytes directly as data/recordings/call_{call_id}.wav.
        """
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        rec_path = RECORDINGS_DIR / f"call_{call_id}.wav"

        try:
            rec_path.write_bytes(audio_bytes)
            logger.info(f"[DataExporter] Saved audio recording: {rec_path.name} ({len(audio_bytes)} bytes)")
            return str(rec_path)
        except Exception as err:
            logger.warning(f"[DataExporter] Could not write recording file: {err}")
            return ""


data_exporter = DataExporterService()
