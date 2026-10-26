import re
from typing import Optional


class ContextAnalyzer:
    """
    Analyzes conversational context across turns, specifically examining
    preceding agent questions to evaluate customer responses accurately.
    """

    # Questions asking for customer identity, greeting verification, or audio check
    IDENTITY_OR_GREETING_PATTERNS = [
        re.compile(p, re.IGNORECASE) for p in [
            r"\bam\s+i\s+(?:speaking|talking)\s+(?:to|with)\b",
            r"\bis\s+this\s+[a-z\s\.\']+\??$",
            r"\bis\s+that\s+[a-z\s\.\']+\??$",
            r"\bcan\s+you\s+hear\s+me\b",
            r"\bam\s+i\s+audible\b",
            r"\bhello\s*,?\s*(?:can\s+you\s+hear|are\s+you\s+there)\b",
            # Hindi / Hinglish
            r"\b(?:kya\s+)?(?:main\s+)?[a-z\s\.\']+\s+se\s+baat\s+kar\s+raha\s+hoon\b",
            r"\b(?:kya\s+)?aap\s+[a-z\s\.\']+\s+bol\s+rahe\s+hain\b",
            r"\b(?:kya\s+)?aap\s+[a-z\s\.\']+\s+hain\s*\??$",
            r"\baawaz\s+aa\s+rahi\s+hai\b",
            r"\bmeri\s+aawaz\s+mil\s+rahi\s+hai\b",
            # Marathi
            r"\bmee\s+[a-z\s\.\']+\s+shi\s+boltoy\s+ka\b",
            r"\btumhi\s+[a-z\s\.\']+\s+aahat\s+ka\b",
            r"\bmajha\s+aawaz\s+yetoy\s+ka\b",
            r"\baawaz\s+aika\s+yetoy\s+ka\b",
            # Devanagari
            r"काय\s+मी\s+.*शी\s+बोलत\s+आहे\s+का",
            r"माझा\s+आवाज\s+येतोय\s+का",
            r"क्या\s+मेरी\s+आवाज़\s+आ\s+रही\s+है",
            r"क्या\s+मैं\s+.*से\s+बात\s+कर\s+रहा\s+हूँ",
            r"(?:क्या\s+)?आप\s+.*बोल\s+रहे\s+हैं",
        ]
    ]

    # Questions offering product information, pitch permission, or subscription interest
    PRODUCT_PITCH_PATTERNS = [
        re.compile(p, re.IGNORECASE) for p in [
            r"\bwould\s+you\s+like\s+to\s+(?:know|hear|learn)\s+more\b",
            r"\bcan\s+i\s+(?:explain|tell\s+you\s+about|share)\s+(?:our|the|this)?\b",
            r"\bcan\s+i\s+tell\s+you\s+about\s+our\s+service\b",
            r"\bare\s+you\s+interested\s+in\b",
            r"\bshall\s+i\s+(?:explain|proceed|share)\b",
            r"\bdo\s+you\s+want\s+to\s+(?:know|check|see)\b",
            r"\bdo\s+you\s+need\s+(?:any\s+)?(?:loan|insurance|software|service|help)\b",
            # Hindi / Hinglish
            r"\bkya\s+(?:main\s+)?(?:iske|service\s+ke|product\s+ke)\s+baare\s+mein\s+bata\s+sakta\s+hoon\b",
            r"\bkya\s+aap\s+janana\s+chahte\s+hain\b",
            r"\bkya\s+main\s+explain\s+karun\b",
            r"\bkya\s+main\s+details\s+bataun\b",
            r"\bkya\s+aapko\s+.*chahiye\b",
            # Marathi
            r"\baamhi\s+ya\s+badal\s+mahiti\s+deu\s+ka\b",
            r"\btumhala\s+ya\s+badal\s+janun\s+ghyayche\s+aahe\s+ka\b",
            r"\bme\s+explain\s+karu\s+ka\b",
            r"\bdetails\s+sangu\s+ka\b",
            # Devanagari
            r"क्या\s+आप\s+(?:जानना|सुनना)\s+चाहते\s+हैं",
            r"क्या\s+मैं\s+.*बता\s+सकता\s+हूँ",
            r"आम्ही\s+याबद्दल\s+माहिती\s+देऊ\s+का",
            r"तुम्हाला\s+याबद्दल\s+जाणून\s+घ्यायचे\s+का",
        ]
    ]

    # Bare positive affirmative words without further semantic continuation
    BARE_ACKNOWLEDGEMENT_PATTERN = re.compile(
        r"^\s*(?:yes|yeah|yep|yup|sure|okay|ok|haan|ha|haa|ji|haji|ho|ho\s+sir|yes\s+sir|hmm|theek\s+hai|barobar)[\s\.,!]*$",
        re.IGNORECASE
    )

    @classmethod
    def is_identity_question(cls, text: str) -> bool:
        if not text:
            return False
        return any(pat.search(text) for pat in cls.IDENTITY_OR_GREETING_PATTERNS)

    @classmethod
    def is_product_pitch_question(cls, text: str) -> bool:
        if not text:
            return False
        return any(pat.search(text) for pat in cls.PRODUCT_PITCH_PATTERNS)

    @classmethod
    def is_bare_acknowledgement(cls, text: str) -> bool:
        if not text:
            return False
        return bool(cls.BARE_ACKNOWLEDGEMENT_PATTERN.match(text.strip()))

    @classmethod
    def evaluate_acknowledgement(cls, preceding_agent_text: Optional[str], customer_text: str) -> str:
        """
        Determines the intent of a bare affirmative response ('yes', 'haan', 'ho')
        based on the preceding agent turn.
        
        Returns:
        - 'NEUTRAL_IDENTITY': Confirmed identity or line audio, NO product interest inferred.
        - 'PITCH_AGREEMENT': Agreed to hear about the product or service.
        - 'GENERIC_AGREEMENT': Uncontextualized agreement.
        """
        if not cls.is_bare_acknowledgement(customer_text):
            return "NON_BARE"

        if not preceding_agent_text:
            return "GENERIC_AGREEMENT"

        if cls.is_identity_question(preceding_agent_text):
            return "NEUTRAL_IDENTITY"

        if cls.is_product_pitch_question(preceding_agent_text):
            return "PITCH_AGREEMENT"

        return "GENERIC_AGREEMENT"
