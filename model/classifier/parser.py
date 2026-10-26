import re
from typing import List, Tuple
from .models import Turn, SpeakerRole


class TranscriptParser:
    """
    Parses conversational call transcripts into structured turns,
    distinguishing Agent vs Customer utterances across diverse formats.
    """

    AGENT_PATTERNS = [
        re.compile(r"^(?:agent|assistant|samruddhi|representative|sales|rep|bot|ai|executive|telecaller|एजेंट|प्रतिनिधी)\s*[:\-\]]", re.IGNORECASE),
        re.compile(r"^\[?(?:agent|assistant|samruddhi|bot|sales|rep)\]?\s*:", re.IGNORECASE),
        re.compile(r"^a\s*:", re.IGNORECASE),
        re.compile(r"^speaker\s*1\s*:", re.IGNORECASE),
    ]

    CUSTOMER_PATTERNS = [
        re.compile(r"^(?:customer|caller|client|user|prospect|lead|farmer|receiver|person|consumer|कस्टमर|ग्राहक)\s*[:\-\]]", re.IGNORECASE),
        re.compile(r"^\[?(?:customer|caller|client|user|farmer)\]?\s*:", re.IGNORECASE),
        re.compile(r"^c\s*:", re.IGNORECASE),
        re.compile(r"^speaker\s*2\s*:", re.IGNORECASE),
    ]

    TIMESTAMP_PATTERN = re.compile(r"^\[?\d{1,2}:\d{2}(?::\d{2})?\]?\s*")
    HANGUP_PATTERNS = [
        re.compile(r"\[.*?(?:hangs?|disconnect|drops?|end of call).*?\]", re.IGNORECASE),
        re.compile(r"\(.*?(?:hangs?|disconnect|drops?|end of call).*?\)", re.IGNORECASE),
    ]

    INLINE_SPEAKER_SPLIT = re.compile(
        r"(?:^|\s+)(?=(?:agent|representative|sales|rep|bot|ai|executive|caller|telecaller|एजेंट|प्रतिनिधी|customer|client|user|prospect|lead|farmer|receiver|person|consumer|कस्टमर|ग्राहक|speaker\s*\d+|a|c)\s*[:\-\]])",
        re.IGNORECASE
    )

    @classmethod
    def clean_line(cls, line: str) -> str:
        """Strips timestamps and normalizes spacing."""
        cleaned = line.strip()
        cleaned = cls.TIMESTAMP_PATTERN.sub("", cleaned)
        return cleaned.strip()

    @classmethod
    def identify_speaker(cls, line: str) -> Tuple[SpeakerRole, str]:
        """
        Determines if a line starts with an agent, customer, or unknown speaker.
        Returns (role, text_without_speaker_prefix).
        """
        cleaned = cls.clean_line(line)
        
        for pat in cls.AGENT_PATTERNS:
            match = pat.match(cleaned)
            if match:
                return SpeakerRole.AGENT, cleaned[match.end():].strip()

        for pat in cls.CUSTOMER_PATTERNS:
            match = pat.match(cleaned)
            if match:
                return SpeakerRole.CUSTOMER, cleaned[match.end():].strip()

        return SpeakerRole.UNKNOWN, cleaned

    @classmethod
    def parse(cls, transcript: str) -> List[Turn]:
        """
        Parses a full transcript text into an ordered list of Turns.
        Properly handles multi-line statements and non-standard layouts,
        as well as inline speaker markers on the same line.
        """
        if not transcript or not transcript.strip():
            return []

        # First normalize or split lines that contain inline speaker tags
        raw_lines = transcript.strip().splitlines()
        normalized_lines = []
        for raw_l in raw_lines:
            subparts = [p.strip() for p in cls.INLINE_SPEAKER_SPLIT.split(raw_l) if p.strip()]
            if subparts:
                normalized_lines.extend(subparts)
            else:
                normalized_lines.append(raw_l)

        turns: List[Turn] = []
        current_role: SpeakerRole = SpeakerRole.UNKNOWN
        current_text_parts: List[str] = []

        def flush_turn():
            nonlocal current_role, current_text_parts
            if current_text_parts:
                full_text = " ".join(part for part in current_text_parts if part).strip()
                if full_text:
                    turns.append(Turn(
                        role=current_role,
                        text=full_text,
                        turn_index=len(turns)
                    ))
            current_text_parts = []

        for line in normalized_lines:
            line = line.strip()
            if not line:
                continue

            # Check if this line is purely a system/hangup notice
            is_hangup = any(pat.search(line) for pat in cls.HANGUP_PATTERNS)
            if is_hangup and not (":" in line and ("agent" in line.lower() or "customer" in line.lower())):
                flush_turn()
                turns.append(Turn(
                    role=SpeakerRole.UNKNOWN,
                    text=line,
                    turn_index=len(turns)
                ))
                current_role = SpeakerRole.UNKNOWN
                continue

            role, content = cls.identify_speaker(line)

            if role != SpeakerRole.UNKNOWN:
                flush_turn()
                current_role = role
                if content:
                    current_text_parts.append(content)
            else:
                if current_role == SpeakerRole.UNKNOWN:
                    flush_turn()
                    current_role = SpeakerRole.UNKNOWN
                    current_text_parts.append(line)
                else:
                    current_text_parts.append(line)

        flush_turn()

        # If all turns ended up as UNKNOWN (e.g. no Agent: or Customer: tags),
        # heuristic fallback: if there are alternating lines, assume Turn 0 is Agent and Turn 1 is Customer, etc.
        # But if explicit speaker tags were present, respect them.
        has_known_speakers = any(t.role in (SpeakerRole.AGENT, SpeakerRole.CUSTOMER) for t in turns)
        if not has_known_speakers and len(turns) >= 2:
            # Alternating fallback
            for i, t in enumerate(turns):
                t.role = SpeakerRole.AGENT if i % 2 == 0 else SpeakerRole.CUSTOMER

        return turns
