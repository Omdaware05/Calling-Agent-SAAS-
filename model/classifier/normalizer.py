import re
import unicodedata
from typing import Optional


class TextNormalizer:
    """
    Robust multilingual text normalizer for Indian English, Hindi, Marathi,
    Hinglish, and Marathish conversational call transcripts.
    
    Principles:
    1. NEVER remove or distort negation tokens ('no', 'not', 'don\'t', 'nahi', 'nahin', 'mat', 'nako', 'नाही', 'नको').
    2. Normalize common ASR misspellings, colloquial Romanized variations, and punctuation.
    3. Retain Devanagari scripts and handle Unicode NFC normalization.
    4. Collapse excessive whitespace, repeated characters, and filler disfluencies.
    """

    # Transliteration & spelling normalization mapping for Romanized Hindi / Hinglish
    HINGLISH_SPELLING_MAP = {
        r"\b(?:watsp|watsap|wapp|whatsap)\b": "whatsapp",
        r"\b(?:detils|deatils|detail|detais)\b": "details",
        r"\b(?:snd|sndt)\b": "send",
        r"\b(?:prce|prise|priz)\b": "price",
        r"\b(?:chaahiye|chahye|chahie)\b": "chahiye",
        r"\b(?:jaroorat|jarurat|zaroorat|jaroorat)\b": "zarurat",
        r"\b(?:btao|btaiye|bataye|batao na)\b": "bataiye",
        r"\b(?:mehanga|mahanga|mehenga)\b": "mehnga",
        r"\b(?:sikhna|sikhne|seekhe)\b": "seekhna",
        r"\b(?:jaankari|jankari|jankaari)\b": "jankari",
        r"\b(?:kharcha|kharche)\b": "kharch",
        r"\b(?:discount|discnt)\b": "discount",
    }

    # Transliteration & spelling normalization mapping for Romanized Marathi / Marathish
    MARATHISH_SPELLING_MAP = {
        r"\b(?:udhya|udyaach|udyach)\b": "udya",
        r"\b(?:maahiti|maheti|mahetee)\b": "mahiti",
        r"\b(?:aahe|ahe|ahet|ahet ka)\b": "aahe",
        r"\b(?:pahije|pahidje|pahijea|pahijel)\b": "pahije",
        r"\b(?:nakoy|nakos|nako re)\b": "nako",
        r"\b(?:vichaar|vchar)\b": "vichar",
        r"\b(?:saanga|saang)\b": "sanga",
        r"\b(?:majha|maza|maazi)\b": "majha",
        r"\b(?:nantar|nantrr)\b": "nantar",
        r"\b(?:pathva|paathva|send kara)\b": "pathva",
        r"\b(?:kasa|kasaa)\b": "kasa",
        r"\b(?:kiti|kitti)\b": "kiti",
    }

    # Filler words and disfluencies that can be safely cleaned from turn boundaries
    FILLER_PATTERN = re.compile(
        r"^(?:\s*(?:um+|uh+|er+|ah+|arre|bhai|yaar|hmm+|haanji|toh)\s*[,:\-]?\s*)+",
        re.IGNORECASE
    )

    # Repeated punctuation pattern
    REPEATED_PUNCT_PATTERN = re.compile(r"([!?,.:;])\1+")

    # Repeated space pattern
    REPEATED_SPACE_PATTERN = re.compile(r"\s+")

    @classmethod
    def normalize(cls, text: str) -> str:
        """
        Normalizes a conversational utterance while preserving negation and intent semantics.
        """
        if not text:
            return ""

        # 1. Unicode NFC normalization
        normalized = unicodedata.normalize("NFC", text.strip())

        # 2. Collapse repeated punctuation (e.g. '???' -> '?', '!!!' -> '!')
        normalized = cls.REPEATED_PUNCT_PATTERN.sub(r"\1", normalized)

        # 3. Collapse multiple whitespaces
        normalized = cls.REPEATED_SPACE_PATTERN.sub(" ", normalized)

        # 4. Remove leading conversational disfluencies (e.g. 'Uh, um, I want to know')
        normalized = cls.FILLER_PATTERN.sub("", normalized)

        # 5. Apply phonetic & spelling maps on Romanized words (case-insensitive substitution preserving casing)
        lower_check = normalized.lower()

        for pattern, replacement in cls.HINGLISH_SPELLING_MAP.items():
            if re.search(pattern, lower_check):
                normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

        for pattern, replacement in cls.MARATHISH_SPELLING_MAP.items():
            if re.search(pattern, lower_check):
                normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

        return normalized.strip()

    @classmethod
    def clean_turn_text(cls, text: str) -> str:
        """
        Lightweight cleaner for turns, keeping punctuation minimal but intact.
        """
        return cls.normalize(text)
