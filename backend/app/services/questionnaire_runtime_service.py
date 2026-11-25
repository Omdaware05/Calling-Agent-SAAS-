import re
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class FastQuestionnaireOrchestrator:
    """
    Real-time deterministic dialogue orchestrator for questionnaire-driven calls.
    Directly resolves question sequencing, customer acknowledgements, direct Q&A answers,
    and polite refusals in < 2ms, completely bypassing slow LLM generation.
    """

    # Refusal and negative intent regex patterns across Marathi, Hindi, English.
    # The telephony verbs (disconnect / kat do / band karo) now require a
    # call/phone subject or a standalone utterance: bare matches ended
    # calls on ordinary support sentences like "Internet disconnect ho
    # raha hai" or "mera net band ho gaya" — a complaint, not a refusal.
    REFUSAL_PATTERN = re.compile(
        r"\b(?:nahi\s+chahiye|chahiye\s+nahi|rehne\s+do|rehne\s+dijiye|rahude|"
        r"rahu\s+dya|garaj\s+nahi|interest\s+nahi|mat\s+karo|not\s+interested|"
        r"don'?t\s+need|don'?t\s+want|stop\s+calling|dnc|remove\s+my\s+number|"
        r"wrong\s+number|cut\s+the\s+call|"
        r"(?:call|phone|फोन|कॉल)\s+(?:disconnect|kat\s+do|kaat\s+do|band\s+karo)|"
        r"disconnect\s+kar\s+do|"
        r"no\s+thanks|no\s+thank\s+you|nahi\s+bhai|nako\s+re|nako\s+baba|nakoy)\b|"
        r"^(?:no|nope|nahi|nahin|nako|नको|नाही|नहीं|kat\s+do|kaat\s+do|band\s+karo)[.!?, ]*$|"
        r"नको\s+आहे|गरज\s+नाही|रस\s+नाही|नाही\s+पाहिजे|नकोय|फोन\s+करू\s+नका|"
        r"नहीं\s+चाहिए|रहने\s+दो|रहने\s+दीजिए|राहू\s+द्या|कॉल\s+काटो|फोन\s+मत\s+करो|"
        # Mixed-script refusal ("interest नाही"): lives in this final group
        # because the first group's trailing \b never matches after a
        # Devanagari vowel sign at end-of-string.
        r"interest\s+नाही",
        re.IGNORECASE
    )

    # NOTE: the Marathi question particle "का" must be a standalone word
    # (\s का \b) — as a bare substring it also matches inside common Hindi
    # words like "जानकारी" and "सलाहकार", which misclassified pure-Hindi
    # scripts as Marathi and made every scripted reply come out in Marathi.
    MARATHI_INDICATORS = re.compile(r"[\u0900-\u097F]*(?:आहे|\sका\b|साहेब|करा|नाही|नको|द्या|सांगा|किती|घ्या|पाहिजे|व्हरायटी|नियोजन|एकरा|दिवसांत)")
    HINDI_INDICATORS = re.compile(r"[\u0900-\u097F]*(?:है|क्या|जी|नमस्ते|बताइए|चाहिए|कीजिए|खरीदना|देंगे|लेना|धन्यवाद)")

    @classmethod
    def parse_questionnaire_from_prompt(cls, prompt_text: str) -> List[Dict[str, Any]]:
        """
        Parses structured questionnaire questions and expected reference answers
        from the prompt script block.
        """
        if not prompt_text:
            return []

        # Find the questionnaire script section
        match = re.search(
            r"### MANDATORY QUESTIONNAIRE SCRIPT(?:\s*\([^)]*\))?:(.*?)(?=\n\n[A-Z#]|\Z)",
            prompt_text,
            re.DOTALL | re.IGNORECASE
        )
        if not match:
            return []

        block = match.group(1).strip()
        questions = []

        # Pattern for:
        # 1. Question: "..."
        #    - Expected Answer / Reference: "..."
        # or:
        # 1. Question: "..." (Type: text)
        q_regex = re.compile(
            r'(\d+)\.\s*Question:\s*"([^"]+)"(?:\s*\(([^)]*)\))?'
            r'(?:\s*\n\s*-\s*Expected Answer\s*(?:/\s*Reference)?:\s*"([^"]*)")?',
            re.IGNORECASE
        )

        for m in q_regex.finditer(block):
            num = int(m.group(1))
            q_text = m.group(2).strip()
            paren = m.group(3) or ""
            exp_ans = m.group(4).strip() if m.group(4) else ""
            type_match = re.search(r'Type:\s*([\w-]+)', paren, re.IGNORECASE)
            questions.append({
                "index": num,
                "text": q_text,
                "expected_answer": exp_ans,
                "type": type_match.group(1).lower() if type_match else "",
            })

        return questions

    @classmethod
    def detect_script_language(cls, text: str) -> str:
        """Determines if the text is primarily Marathi, Hindi, or English."""
        if cls.MARATHI_INDICATORS.search(text):
            return "mr"
        if cls.HINDI_INDICATORS.search(text):
            return "hi"
        return "en"

    @classmethod
    def is_refusal(cls, text: str) -> bool:
        """Checks if the caller expressed clear refusal or desire to end the call."""
        if not text:
            return False
        return bool(cls.REFUSAL_PATTERN.search(text.strip()))

    # Words that carry no question identity (honorifics, fillers, auxiliaries, grammatical frame tokens).
    # Dropped before token-overlap matching so paraphrases still match without false positives.
    _MATCH_STOPWORDS = {
        # Honorifics & Salutations
        "साहेब", "जी", "sir", "madam", "mr", "mrs", "shree", "shri", "namaste", "namaskar",
        "the", "a", "an", "is", "are", "was", "were", "to", "for", "in", "on", "at", "by",
        "and", "or", "of", "with", "this", "that", "these", "those",
        # Hindi / Hinglish pronouns & grammatical particles
        "का", "की", "के", "को", "से", "में", "पे", "पर", "ने", "तक",
        "ka", "ki", "ke", "ko", "se", "me", "mein", "pe", "par", "ne", "tak",
        "आप", "आपका", "आपकी", "आपके", "हम", "हमारा", "हमारी", "हमारे", "मैं", "मेरा", "मेरी", "मेरे",
        "aap", "aapka", "aapki", "aapke", "hum", "humara", "humari", "humare", "main", "mera", "meri", "mere",
        "यह", "ये", "वह", "वो", "इस", "इन", "उस", "उन",
        "yeh", "ye", "woh", "wo", "is", "in", "us", "un", "iss", "iski", "iske", "isko",
        # Hindi verbs & auxiliaries
        "है", "हैं", "हो", "हूँ", "था", "थी", "थे", "होगा", "होगी", "होंगे",
        "hai", "hain", "ho", "hoon", "hun", "tha", "thi", "the", "hoga", "hogi", "honge",
        "कर", "करना", "करने", "करते", "करती", "करेंगे", "करेंगी", "करो", "करें", "कीजिए",
        "kar", "karna", "karne", "karte", "karti", "karenge", "karein", "kijiye", "kare",
        "रहा", "रहे", "रही", "बना", "बनाने", "बताइए", "बताएं", "दीजिए", "दें", "सकते", "सकती",
        "raha", "rahe", "rahi", "bana", "banane", "bataiye", "batao", "dijiye", "den", "sakte", "sakti",
        "या", "और", "भी", "तो", "ही", "किस", "कौन", "कौनसा", "कौनसी", "क्या",
        "ya", "aur", "bhi", "to", "hi", "kis", "kaun", "konsa", "konsi", "kya",
        # Domain generic frame tokens
        "योजना", "प्लानिंग", "प्लान", "फसल", "पिक", "पिकाचे", "नियोजन",
        "yojna", "yojana", "planning", "plan", "crop", "fasal",
        # Marathi pronouns & particles
        "आहे", "आहेत", "होय", "नाही", "नका", "तुम्ही", "तुम्हाला", "तुमचे", "तुमचा", "तुमची",
        "आपण", "आपल्या", "आपला", "आपली", "या", "यापैकी", "त्या", "त्यासाठी",
        "करा", "कराल", "करणार", "करू", "सांगा", "सांगाल", "द्या",
    }

    _DISTINCTIVE_KEYWORDS = {
        "एकड़", "एकर", "acre", "acres", "जमीन",
        "दिन", "दिवस", "days", "din", "divas",
        "नाम", "नाव", "name", "गाँव", "गाव", "village", "तहसील", "तालुका", "taluka", "जिला", "जिल्हा", "district",
        "किस्म", "किस्में", "वाण", "variety", "varieties",
        "खरीदने", "खरीदी", "खरेदी", "purchase", "buy",
        "क्विंटल", "किलो", "kg", "quintal", "दर", "भाव", "rate", "price", "fee", "fees"
    }

    CONFUSION_INTERRUPTION_PATTERN = re.compile(
        r"\b(?:"
        r"galat|galti|gadbad|wrong|mistake|error|fault|"
        r"गलत|गलती|गड़बड़|चूक|"
        r"ruko|ruk|rukiye|hold\s+on|wait|ek\s+min|ek\s+minute|ek\s+second|"
        r"रुको|रुकिए|रुक|रोको|एक\s+मिनट|एक\s+सेकंड|एक\s+क्षण|"
        r"suno|suniye|listen|meri\s+baat|hear\s+me|ऐका|ऐका\s+ना|माझं\s+ऐका|"
        r"aao\s+na\s+yaar|kya\s+bol\s+rahe|kya\s+kar\s+rahe|ye\s+kya\s+hai|"
        r"ये\s+क्या|क्या\s+बोल\s+रहे|काय\s+चाललंय|हे\s+काय|समजत\s+नाही|समझ\s+नहीं|"
        r"not\s+listening|you\s+are\s+not\s+listening|bot\s+hai|machine\s+hai|ai\s+hai"
        r")\b",
        re.IGNORECASE
    )

    FILLER_PATTERN = re.compile(
        r"^(?:theek\s+hai|theek|thik\s+hai|thik|ok|okay|accha|achha|achha\s+ji|"
        r"haan|han|haanji|hanji|ji|ji\s+haan|yes|yep|yeah|ha|"
        r"hello|hi|namaste|namaskar|boliye|bataiye|kahiye|batao|suno|"
        r"ठीक\s+है|ठीक|अच्छा|अच्छा\s+जी|हाँ|हां|हाँजी|हांजी|जी|जी\s+हाँ|हा|"
        r"हेलो|हॅलो|नमस्ते|नमस्कार|बोलिए|बताइए|सांगा|बोला|हो|होय)$",
        re.IGNORECASE
    )

    RESCHEDULE_BUSY_PATTERNS = [
        r"(?:थोड़ी\s+देर\s+बाद|देर\s+बाद|बाद\s+में|नंतर|थोड्या\s+वेळाने|थोडे\s+वेळाने|फिर|कल|उद्या)\s*(?:कॉल|फोन|call|phone|बात|बोला|करा|करो|करना)",
        r"(?:कॉल|फोन|call|phone|बात|बोला)\s*(?:बाद\s+में|नंतर|कल|उद्या|फिर|थोड़ी\s+देर\s+बाद|थोड्या\s+वेळाने|थोडे\s+वेळाने)",
        r"(?:बाद\s+में|नंतर|थोड्या\s+वेळाने|थोडे\s+वेळाने|थोड़ी\s+देर\s+बाद)\s*(?:करना|करा|करिए|करिये|कर\s+सकते|करो)",
        r"(?:baad\s+me|bad\s+me|nantar|thodi\s+der\s+baad|der\s+baad|kal|udya)\s*(?:call|phone|baat|bola|kara|karo|karna)",
        r"(?:call|phone|baat|bola)\s*(?:baad\s+me|bad\s+me|nantar|kal|udya|thodi\s+der\s+baad|der\s+baad)",
        r"(?:baad\s+me|bad\s+me|nantar|thodi\s+der\s+baad)\s*(?:karna|kara|kariye|kar\s+sakte|karo)",
        r"\b(?:call\s+(?:me\s+)?later|call\s+back|call\s+me\s+back|call\s+tomorrow|call\s+again|call\s+later\s+please)\b",
        r"\b(?:busy\s+(?:right\s+)?now|busy\s+now|in\s+a\s+meeting|cant\s+talk|can't\s+talk|busy\s+hu|busy\s+ahe|meeting\s+me\s+hu)\b",
        r"(?:अभी|सध्या|आता)\s*(?:बिजी|व्यस्त|कामात|वेळ\s+नाही|टाइम\s+नहीं|टाइम\s+नाही)",
        r"(?:वेळ\s+नाही|टाइम\s+नाही|टाइम\s+नही|समय\s+नहीं)",
    ]
    _COMPILED_RESCHEDULE = [re.compile(p, re.IGNORECASE) for p in RESCHEDULE_BUSY_PATTERNS]

    FAREWELL_SIGNATURES = [
        "समय देने के लिए", "समय देने के लिए आपका बहुत धन्यवाद", "समय देने के लिए धन्यवाद",
        "वेळ दिल्याबद्दल", "वेळ दिल्याबद्दल खूप धन्यवाद", "वेळ दिल्याबद्दल धन्यवाद",
        "thank you for your time", "thanks for your time",
        "दिन शुभ हो", "दिवस शुभ जावो", "have a great day", "अलविदा", "goodbye", "take care",
        "संपर्क करने के लिए बहुत धन्यवाद", "संपर्क केल्याबद्दल खूप धन्यवाद",
        "बाद में सुविधानुसार कॉल करेंगे", "नंतर सोयीच्या वेळी पुन्हा कॉल करू",
        "बाद में कॉल करेंगे", "नंतर कॉल करू", "पुन्हा कॉल करू", "बाद में फोन करेंगे"
    ]

    @classmethod
    def is_reschedule_or_busy(cls, text: str) -> bool:
        """True if caller asks to be called back later, expresses busy/meeting status, or reschedules."""
        if not text:
            return False
        t = text.lower().strip()
        hard_negatives = (
            "not interested", "don't call", "do not call", "stop calling",
            "नहीं चाहिए", "नही चाहिए", "wrong number", "गलत नंबर",
        )
        if any(h in t for h in hard_negatives):
            return False
        direct_phrases = (
            "call later", "call me later", "call back", "callback",
            "बाद में बात", "बाद में करो", "बाद में कॉल", "बाद में call",
            "फिर कॉल", "फिर call", "अभी बिजी", "बिजी हूँ", "बिजी हूं",
            "व्यस्त हूँ", "व्यस्त हूं", "busy right now", "busy now",
            "अभी बात नहीं", "बाद में बात करेंगे", "बाद में फोन", "नंतर फोन",
            "नंतर कॉल", "नंतर बोला", "नंतर सांगा", "नंतर करा", "कल कॉल", "उद्या फोन",
            "उद्या करा", "नंतर सांगतो", "बाद में बताऊंगा", "थोड़ी देर बाद", "देर बाद",
            "थोडी देर बाद", "थोड़ी देर बाद", "थोड्या वेळाने", "थोडे वेळाने", "busy hu", "busy ahe",
            "nantar kara", "nantar phone", "bad me phone", "meeting me hu"
        )
        if any(p in t for p in direct_phrases):
            return True
        return any(p.search(t) for p in cls._COMPILED_RESCHEDULE)

    @classmethod
    def is_farewell_text(cls, text: str) -> bool:
        """True if text is an assistant farewell / closing statement and does not ask questions."""
        if not text:
            return False
        t = text.lower().strip()
        question_markers = ["?", "？", "बताइए", "बताएं", "सांगा", "का?", "कितने", "किती", "कोणती", "क्या आप", "तुम्ही"]
        if any(q in t for q in question_markers) or t.endswith("?"):
            return False
        return any(sig in t for sig in cls.FAREWELL_SIGNATURES)

    @classmethod
    def is_confusion_or_interruption(cls, text: str) -> bool:
        """True if caller expresses confusion, interruption, frustration, or objection."""
        if not text:
            return False
        return bool(cls.CONFUSION_INTERRUPTION_PATTERN.search(text.strip()))

    @classmethod
    def is_conversational_filler(cls, text: str) -> bool:
        """True if text is purely an acknowledgment or conversational filler without an answer."""
        if not text:
            return False
        clean = re.sub(r"[।.!?,;:\"'()\[\]{}<>*`_#\-–—/\\]+", " ", text).strip()
        clean = re.sub(r"\s+", " ", clean)
        return bool(cls.FILLER_PATTERN.match(clean))

    @classmethod
    def _normalize_for_match(cls, text: str) -> str:
        """Lowercase, strip punctuation and collapse whitespace so the text
        the caller actually HEARD (TTS-cleaned, ack-prefixed, honorifics
        added/removed) can be matched against the scripted question text."""
        t = (text or "").lower()
        t = re.sub(r"[।.!?,;:\"'()\[\]{}<>*`_#\-–—/\\]+", " ", t)
        return re.sub(r"\s+", " ", t).strip()

    @classmethod
    def _question_was_asked(cls, q_text: str, msg_norm: str, msg_tokens: set) -> bool:
        """True if this scripted question was already spoken in `msg_norm`."""
        q_norm = cls._normalize_for_match(q_text)
        if not q_norm:
            return False
        if q_norm in msg_norm:
            return True
        core = q_norm[:45]
        if len(core) >= 20 and core in msg_norm:
            return True
        q_tokens = {t for t in q_norm.split() if len(t) >= 2 and t not in cls._MATCH_STOPWORDS}
        if len(q_tokens) >= 2:
            distinctive_in_q = q_tokens & cls._DISTINCTIVE_KEYWORDS
            if distinctive_in_q and not (distinctive_in_q & msg_tokens):
                return False
            overlap = len(q_tokens & msg_tokens) / len(q_tokens)
            if overlap >= 0.75:
                return True
        return False

    # Markers that make a caller utterance a QUESTION rather than an answer
    # to the current script question. Deliberately conservative: a false
    # positive costs one fallback line + the pending question repeated; a
    # false negative lets the LLM improvise an answer, which must not happen.
    _QUESTION_WORDS = {
        "kya", "क्या", "kitna", "kitne", "kitni", "कितना", "कितने", "कितनी", "किती",
        "kab", "कब", "kahan", "kaha", "कहाँ", "कहा", "किधर", "kaise", "कैसे", "kaisa", "kese",
        "kyu", "kyon", "क्यों", "konsa", "konsi", "konta", "konti", "kadhi", "कधी",
        "kase", "काय", "kuthe", "kashala", "कोण", "कोणाचा", "कोणाची", "कोणाचे", "कोणाला",
        "किसका", "किसकी", "किसके", "किस", "what", "which", "how", "when", "where", "why",
        "does",
    }
    _QUESTION_PHRASES = (
        "is there", "do you", "can i", "can we", "hai kya", "है क्या",
        "ahe ka", "ahet ka", "आहे का", "milega kya", "hoga kya",
        "जानना है", "जानना चाहता", "जानना चाहती", "जानकारी चाहिए", "बताइए", "बताओ", "बताएं",
        "सांगा", "माहिती हवी", "माहिती पाहिजे", "माहिती सांगा", "विचारत होतो", "विचारू का",
        "want to know", "tell me", "need to know",
    )
    _QA_FILLER_TOKENS = {
        "hai", "hain", "kya", "ahe", "ahet", "the", "is", "are", "was", "me",
        "mein", "ka", "ki", "ke", "ko", "se", "ne", "aur", "bhi", "to", "hi",
        "aap", "aapka", "mera", "mere", "mujhe", "hum", "yeh", "ye", "wo",
        "woh", "ek", "kar", "karke", "raha", "rahe", "rahi", "gaya", "wali",
        "wala", "wale", "batao", "please", "for", "and", "with", "your",
        "yours", "have", "has", "had", "will", "would", "can", "could",
        "should", "there", "their", "them", "they", "this", "that", "these",
        "those", "what", "which", "when", "where", "about",
        # The subject of nearly every Q&A in a script — carries no
        # discriminating power for matching a caller's question to one item.
        "college", "institute", "company", "school", "technology",
    }
    _QA_SHORT_SIGNIFICANT = {"fee", "fees", "jee", "cet", "lpa"}

    # High-confidence intent words for Hindi, Hinglish, and English FAQ
    # questions. Generic overlap (such as "college") must not send a
    # placement query to the campus-visit answer.
    _FAQ_INTENTS = {
        "eligibility": ("eligibility", "criteria", "eligible", "admission criteria", "पात्रता"),
        "placement": ("placement", "package", "lpa", "recruiter", "प्लेसमेंट", "पैकेज"),
        "hostel": ("hostel", "accommodation", "हॉस्टल"),
        "scholarship": ("scholarship", "scholar", "स्कॉलरशिप", "छात्रवृत्ति"),
        "fees": ("fee", "fees", "tuition", "cost", "price", "फीस", "फीज़"),
        "visit": ("visit", "campus visit", "tour", "दौरा"),
        "courses": ("course", "courses", "branch", "branches", "कोर्स"),
    }

    @classmethod
    def _faq_intent(cls, text: str) -> Optional[str]:
        intents = cls._faq_intents(text)
        return intents[0] if intents else None

    @classmethod
    def _faq_intents(cls, text: str) -> List[str]:
        normalized = (text or "").lower()
        return [
            intent for intent, aliases in cls._FAQ_INTENTS.items()
            if any(alias in normalized for alias in aliases)
        ]

    @classmethod
    def _looks_like_question(cls, text: str) -> bool:
        """True when the caller's utterance is phrased as a question."""
        if not text:
            return False
        if "?" in text:
            return True
        norm = cls._normalize_for_match(text)
        if any(phrase in norm for phrase in cls._QUESTION_PHRASES):
            return True
        return any(tok in cls._QUESTION_WORDS for tok in norm.split())

    @classmethod
    def _qa_tokens(cls, text: str) -> set:
        """Significant content tokens of a text for Q&A matching."""
        norm = cls._normalize_for_match(text)
        return {
            t for t in norm.split()
            if (len(t) >= 4 or t in cls._QA_SHORT_SIGNIFICANT)
            and t not in cls._QA_FILLER_TOKENS
        }

    @classmethod
    def _token_match(cls, a: str, b: str) -> bool:
        if a == b:
            return True
        short, long_ = (a, b) if len(a) <= len(b) else (b, a)
        return len(short) >= 3 and long_.startswith(short) and len(long_) - len(short) <= 2

    @classmethod
    def _qa_overlap_match(cls, caller_text: str, q_text: str) -> bool:
        """True when the caller's utterance shares significant content tokens
        with a scripted Q&A question (so 'hostel hai kya?' or 'fees kitni
        hai?' land on their scripted answer, not on the free-form LLM)."""
        caller_tokens = cls._qa_tokens(caller_text)
        q_tokens = cls._qa_tokens(q_text)
        if not caller_tokens or not q_tokens:
            return False
        shared = {
            ct for ct in caller_tokens
            if any(cls._token_match(ct, qt) for qt in q_tokens)
        }
        if len(shared) >= 2:
            return True
        if len(shared) == 1:
            only = next(iter(shared))
            matched_q = next(qt for qt in q_tokens if cls._token_match(only, qt))
            distinctive = len(only) >= 5 or only in cls._QA_SHORT_SIGNIFICANT \
                or matched_q in cls._QA_SHORT_SIGNIFICANT
            return distinctive and cls._looks_like_question(caller_text)
        return False

    @classmethod
    def asked_question_indices(
        cls, questions: List[Dict[str, Any]], assistant_messages: List[str]
    ) -> set:
        """Set of question indices already spoken in ANY assistant message."""
        asked = set()
        for msg in assistant_messages:
            msg_norm = cls._normalize_for_match(msg)
            if not msg_norm:
                continue
            msg_tokens = set(msg_norm.split())
            for q in questions:
                if q["index"] not in asked and cls._question_was_asked(q["text"], msg_norm, msg_tokens):
                    asked.add(q["index"])
        return asked

    @classmethod
    def find_last_question_asked(
        cls, questions: List[Dict[str, Any]], assistant_messages: List[str]
    ) -> Optional[int]:
        """Highest question index the assistant has already asked (or None)."""
        asked = cls.asked_question_indices(questions, assistant_messages)
        return max(asked) if asked else None

    @classmethod
    def next_unasked_question(
        cls, questions: List[Dict[str, Any]], asked: set
    ) -> Optional[Dict[str, Any]]:
        """First question (in script order) that has NOT been asked yet.
        Advancing to the first unasked question — instead of last+1 — means a
        question can never be repeated and never silently skipped.
        Items typed "reference" are knowledge Q&A for answering the caller —
        they are NEVER served as questions to ask."""
        for q in sorted(questions, key=lambda x: x["index"]):
            if q["index"] not in asked and (q.get("type") or "").lower() not in {"reference", "faq", "closing"}:
                return q
        return None

    @classmethod
    def closing_text(cls, questions: List[Dict[str, Any]]) -> Optional[str]:
        """Return an explicitly supplied closing line, if the questionnaire has one."""
        for q in questions:
            if (q.get("type") or "").lower() == "closing" and q.get("text"):
                return q["text"]
        return None

    @classmethod
    def resolve_next_turn(cls, messages: List[Dict[str, Any]]) -> Optional[str]:
        """
        Evaluates the current dialogue state against the assigned questionnaire.
        Returns:
        - Instant spoken response (str) if deterministically resolved in < 2ms.
        - None if turn requires fallback to dynamic LLM generation.
        """
        if not messages or not isinstance(messages, list):
            return None

        # 1. Extract system prompt and conversation turns
        system_prompt = ""
        assistant_msgs: List[str] = []
        last_user_msg = ""

        for m in messages:
            role = m.get("role", "")
            content = m.get("content", "") or ""
            if role == "system" and not system_prompt:
                system_prompt = content
            elif role == "assistant":
                assistant_msgs.append(content)
            elif role == "user":
                last_user_msg = content.strip()

        if not system_prompt or not last_user_msg:
            return None

        # 2. Extract identity and company metadata from system prompt
        m_agent = re.search(r"Agent Name:\s*'([^']+)'|You are '([^']+)'", system_prompt, re.I)
        agent_name = (m_agent.group(1) or m_agent.group(2)) if m_agent else "Aarti"

        m_comp = re.search(r"Company(?:\s*/\s*Organization)?:\s*'([^']+)'", system_prompt, re.I)
        company_name = m_comp.group(1) if m_comp else "ARB SoftTech"

        m_desc = re.search(r"Company Specialty(?:\s*&\s*Purpose)?:\s*([^\n]+)", system_prompt, re.I)
        company_desc = m_desc.group(1).strip() if m_desc else "हम बेहतरीन सेवाएँ और समाधान उपलब्ध कराते हैं।"


        # 3. Parse questionnaire
        questions = cls.parse_questionnaire_from_prompt(system_prompt)
        if not questions:
            return None

        script_lang = cls.detect_script_language(" ".join(q["text"] for q in questions[:3]))
        last_user_lower = last_user_msg.lower()

        # Determine which questions were already asked (paraphrase-tolerant).
        asked_indices = cls.asked_question_indices(questions, assistant_msgs)
        last_q_idx = max(asked_indices) if asked_indices else None
        last_q = next((q for q in questions if q["index"] == last_q_idx), None) if last_q_idx else None
        follow_up_question = next(
            (q for q in questions if (q.get("type") or "").lower() == "follow_up"),
            None,
        )
        in_follow_up_phase = bool(follow_up_question and follow_up_question["index"] in asked_indices)
        follow_up_suffix = " Aapka koi aur question hai?" if in_follow_up_phase else ""

        # 3b. Check if assistant has ALREADY delivered a farewell earlier in the call
        if any(cls.is_farewell_text(m) for m in assistant_msgs):
            logger.info("FastQuestionnaireEngine: Farewell was already delivered earlier in the call -> concluding call")
            if script_lang == "mr":
                return "नमस्कार साहेब!"
            elif script_lang == "hi":
                return "जी नमस्कार!"
            return "Thank you, goodbye!"

        # 4. Check for Caller Refusal / Opt-out
        is_yes_no_q = bool(last_q and (last_q.get("type") or "").lower() == "yes_no")
        is_bare_negative = last_user_msg.strip().lower() in ["no", "nope", "nahi", "nahin", "nako", "नको", "नाही", "नहीं"]
        if cls.is_refusal(last_user_msg) and not (is_yes_no_q and is_bare_negative):
            logger.info("FastQuestionnaireEngine: Caller refusal detected -> instant polite goodbye")
            if script_lang == "mr":
                return "काही हरकत नाही साहेब, आपला वेळ दिल्याबद्दल खूप धन्यवाद!"
            elif script_lang == "hi":
                return "जी कोई बात नहीं, अपना समय देने के लिए आपका बहुत धन्यवाद!"
            return "Theek hai, thank you for your time. Have a wonderful day!"

        # 4a. Check for Reschedule / Busy / Callback Request (Evaluated before generic filler handling)
        if cls.is_reschedule_or_busy(last_user_msg):
            logger.info(f"FastQuestionnaireEngine: Caller busy/callback requested ('{last_user_msg}') -> instant polite reschedule acknowledgement")
            if script_lang == "mr":
                return "काही हरकत नाही साहेब, आम्ही आपल्याला नंतर कॉल करू. खूप खूप धन्यवाद!"
            elif script_lang == "hi":
                return "जी कोई बात नहीं, हम आपको बाद में कॉल करेंगे। आपका बहुत-बहुत धन्यवाद और दिन शुभ हो!"
            return "No problem at all, we will call you back later. Thank you very much and have a great day!"

        # 4b. Caller Confusion / Objection / Interruption / Frustration Check:
        # If caller expresses difficulty, confusion or asks to hold ("रुको", "गलती हो रही है", "मेरी बात सुनो"),
        # do NOT blurt out the next script question. Fall back to LLM to recover conversation empathetically.
        if cls.is_confusion_or_interruption(last_user_msg):
            logger.info(f"FastQuestionnaireEngine: Caller confusion/interruption detected in '{last_user_msg}' -> falling back to dynamic LLM")
            return None

        # 4c. Non-Answer / Conversational Filler Evaluation:
        # If caller gives generic filler ("ठीक है", "हाँ", "hello", "जी") without answering
        # the pending question, do NOT advance blindly! Re-prompt the unanswered question politely.
        # But if the assistant has ALREADY delivered a farewell/closing, do NOT re-prompt!
        if last_q and not is_yes_no_q and cls.is_conversational_filler(last_user_msg):
            if any(cls.is_farewell_text(m) for m in assistant_msgs):
                logger.info(f"FastQuestionnaireEngine: Conversational filler '{last_user_msg}' after farewell already delivered -> not re-prompting")
                return None
            logger.info(f"FastQuestionnaireEngine: Conversational filler '{last_user_msg}' without answering Q{last_q['index']} -> re-prompting Q{last_q['index']}")
            if script_lang == "mr":
                return f"होय साहेब, {last_q['text']}"
            elif script_lang == "hi":
                return f"जी ठीक है, {last_q['text']}"
            return f"Understood. {last_q['text']}"

        # NOTE: there is deliberately no "Turn 0 -> LLM" bail any more. The
        # static greeting is spoken by the start node; the caller's first
        # reply used to fall through to the slow LLM, which paraphrased Q1 —
        # and because the paraphrase could not be recognised later, Q1 was
        # then re-asked verbatim (the 'welcome is slow' + 'repeated
        # questions' complaints). Now the flow below deterministically
        # serves the first unasked question (Q1) on that turn too.

        # 6. Check for WhatsApp / Brochure Requests
        if any(kw in last_user_lower for kw in ["whatsapp", "whats app", "details bhejo", "msg karo", "message karo", "brochure", "mahiti pathva"]):
            logger.info("FastQuestionnaireEngine: WhatsApp request -> instant confirmation")
            if script_lang == "mr":
                return "नक्कीच साहेब, कॉल संपल्यानंतर आपल्या याच नंबरवर संपूर्ण माहिती WhatsApp केली जाईल. पुढचा प्रश्न विचारू का?"
            elif script_lang == "hi":
                return "जी बिल्कुल, कॉल समाप्त होते ही आपके इस नंबर पर संपूर्ण जानकारी WhatsApp कर दी जाएगी। क्या हम आगे बात कर सकते हैं?"
            return "Certainly! We will share complete details on your WhatsApp right after this call. May we proceed?"

        next_q_obj = cls.next_unasked_question(questions, asked_indices)
        active_q_text = next_q_obj["text"] if next_q_obj else None

        # 7. Check for Agent Identity Inquiries ("Who are you? / Aap kaun?")
        if any(kw in last_user_lower for kw in ["kaun bol raha", "kon boltoy", "who is this", "who are you", "aapka naam", "aap kaun", "koni call kela", "kiska call", "apka nam"]):
            logger.info(f"FastQuestionnaireEngine: Identity inquiry -> returning agent {agent_name} from {company_name}")
            q_suffix = f" {active_q_text}" if active_q_text else ""
            if script_lang == "mr":
                return f"हो साहेब, मी {company_name} कडून {agent_name} बोलत आहे.{q_suffix}"
            elif script_lang == "hi":
                return f"जी, मैं {company_name} से {agent_name} बात कर रहा हूँ।{q_suffix}"
            return f"This is {agent_name} calling from {company_name}.{q_suffix}"

        # 8. Check for Company Identity Inquiries ("Which company? / Konsi company?")
        if any(kw in last_user_lower for kw in ["konsi company", "which company", "company ka naam", "konati company", "kaha se bol rahe", "where are you calling from"]):
            logger.info(f"FastQuestionnaireEngine: Company inquiry -> returning {company_name} and {company_desc}")
            q_suffix = f" {active_q_text}" if active_q_text else ""
            if script_lang == "mr":
                return f"हो साहेब, ही {company_name} आहे. {company_desc}.{q_suffix}"
            elif script_lang == "hi":
                return f"जी, यह {company_name} है। {company_desc}।{q_suffix}"
            return f"This is {company_name}. {company_desc}.{q_suffix}"

        # 9. Check for Call Reason Inquiries ("Why are you calling? / Kyu phone kiya?")
        if any(kw in last_user_lower for kw in ["kyu phone kiya", "kyu call kiya", "why are you calling", "ka phone kela", "call kis liye", "reason for call", "kashasathi"]):
            logger.info(f"FastQuestionnaireEngine: Reason inquiry -> returning purpose for {company_name}")
            q_suffix = f" {active_q_text}" if active_q_text else ""
            if script_lang == "mr":
                return f"साहेब, {company_desc} या संदर्भात माहिती देण्यासाठी कॉल केला आहे.{q_suffix}"
            elif script_lang == "hi":
                return f"जी, {company_desc} के सिलसिले में आपको जानकारी देने के लिए कॉल किया है।{q_suffix}"
            return f"I am reaching out regarding {company_desc}.{q_suffix}"

        # 10. Check if caller asked a direct question matching a scripted Q&A
        # item. Legacy price/info keyword match, widened with significant-
        # token overlap so questions like "hostel hai kya?" or "fees kitni
        # hai?" also land on their scripted answer instead of the LLM. The
        # overlap path only fires for question-phrased utterances — a plain
        # answer that merely shares words with a Q&A item must advance the
        # script, not trigger an answer. When several items match, the one
        # sharing the most content tokens wins (price intent breaks ties).
        _QA_KEYWORDS = ["किंमत", "price", "rate", "दर", "खर्च", "व्हरायटी", "माहिती", "फायदे"]
        _PRICE_MARKERS = {"fee", "fees", "price", "rate", "cost", "tuition",
                          "charge", "charges", "kitna", "kitne", "kitni"}
        caller_intents = cls._faq_intents(last_user_msg)
        # FAQ requests are often natural statements ("mujhe fees aur
        # scholarship ki information chahiye"), not grammatical questions.
        caller_is_question = cls._looks_like_question(last_user_msg) or bool(caller_intents)
        caller_tokens = cls._qa_tokens(last_user_msg)
        caller_intent = caller_intents[0] if caller_intents else None
        caller_price_intent = bool(caller_tokens & _PRICE_MARKERS) or \
            any(kw in last_user_lower for kw in ["किंमत", "दर", "खर्च"])
        best_q, best_key = None, None
        matched_intent_refs: Dict[str, Dict[str, Any]] = {}
        for q in questions:
            # Only explicitly marked reference/FAQ rows are facts the agent
            # may say aloud. Regular questionnaire answer cells are customer
            # data-collection guidance, not a source of information.
            if (q.get("type") or "").lower() not in {"reference", "faq"}:
                continue
            q_text_lower = q["text"].lower()
            exp_ans = q.get("expected_answer", "")
            if not exp_ans or exp_ans.lower() in ("any answer", ""):
                continue
            reference_intent = cls._faq_intent(q["text"])
            if caller_intents and reference_intent not in caller_intents:
                continue
            if caller_intents and reference_intent:
                matched_intent_refs.setdefault(reference_intent, q)
                continue
            legacy_match = any(kw in last_user_lower for kw in _QA_KEYWORDS) and \
                any(kw in q_text_lower for kw in _QA_KEYWORDS)
            overlap_match = caller_is_question and cls._qa_overlap_match(last_user_msg, q["text"])
            intent_match = bool(caller_intent and caller_intent == reference_intent)
            if not (legacy_match or overlap_match or intent_match):
                continue
            q_tokens = cls._qa_tokens(q["text"])
            shared = sum(1 for tok in caller_tokens
                         if any(cls._token_match(tok, qt) for qt in q_tokens))
            q_price = 1 if (caller_price_intent and q_tokens & _PRICE_MARKERS) else 0
            key = (q_price, shared, -q["index"])
            if best_key is None or key > best_key:
                best_q, best_key = q, key
        if matched_intent_refs:
            answers = [matched_intent_refs[intent]["expected_answer"]
                       for intent in caller_intents if intent in matched_intent_refs]
            return f"Okay, {' '.join(answers)}{follow_up_suffix}"

        if best_q is not None:
            exp_ans = best_q["expected_answer"]
            logger.info(f"FastQuestionnaireEngine: Direct Q&A match for '{best_q['text']}' -> returning expected answer directly")
            # A follow-up item keeps the conversation open for repeated,
            # approved FAQs instead of ending after the first answer.
            if in_follow_up_phase:
                return f"Okay, {exp_ans}{follow_up_suffix}"
            if script_lang == "mr":
                return f"साहेब, {exp_ans}. पुढचा प्रश्न..."
            elif script_lang == "hi":
                return f"जी, {exp_ans}।"
            return f"Regarding that, {exp_ans}."

        # 10b. If caller was answering a Yes/No question (e.g. "Do you want variety info?"):
        if is_yes_no_q and last_q:
            is_affirmative = any(w in last_user_lower for w in ["हाँ", "हां", "हाँजी", "बताइए", "ज़रूर", "जानकारी", "yes", "yeah", "sure", "सांगा", "होय", "हो"])
            if is_affirmative:
                ref_variety = next((q for q in questions if (q.get("type") or "").lower() == "reference" and any(k in q.get("text", "").lower() for k in ["variety", "varieties", "वाण", "किस्म"])), None)
                if ref_variety and ref_variety.get("expected_answer"):
                    logger.info(f"FastQuestionnaireEngine: Yes/No answered YES -> providing reference '{ref_variety['text']}'")
                    return f"{ref_variety['expected_answer']}{follow_up_suffix}"
                return None

        # 11. Unknown-question guard: the caller asked something that has NO
        # scripted answer. Never let the LLM invent one — speak the fixed
        # fallback line and carry on with the pending script question.
        if cls._looks_like_question(last_user_msg):
            next_q = cls.next_unasked_question(questions, asked_indices)
            q_suffix = f" {next_q['text']}" if next_q else follow_up_suffix
            logger.info("FastQuestionnaireEngine: Unknown caller question -> fixed no-information fallback (LLM invention blocked)")
            # A prompt can explicitly opt into Sarvam answering from the
            # business facts it contains. The LLM receives the full system
            # prompt and is instructed to use only those facts or the same
            # fallback below; this keeps custom, approved prompt knowledge
            # usable without turning regular questionnaire notes into facts.
            if "ALLOW_SYSTEM_PROMPT_FACTS" in system_prompt:
                return None
            if script_lang == "mr":
                return f"माझ्याकडे याची माहिती सध्या नाही. आमची टीम आपल्याला कॉल करून माहिती देईल.{q_suffix}"
            elif script_lang == "hi":
                return f"मेरे पास इसकी जानकारी अभी नहीं है। हमारी टीम आपको कॉल करके जानकारी देगी।{q_suffix}"
            return f"Sorry, mere paas abhi iski information nahi hai.{q_suffix}"

        # 12. Advance to the FIRST question that has not been asked yet.
        # (When nothing was asked yet — e.g. the caller just replied to the
        # opening greeting — this serves Q1 instantly and deterministically
        # instead of paying a slow LLM round-trip.)
        next_question_obj = cls.next_unasked_question(questions, asked_indices)

        if next_question_obj:
            next_q_text = next_question_obj["text"]
            logger.info(f"FastQuestionnaireEngine: Asked so far={sorted(asked_indices)} -> Serving Q{next_question_obj['index']}: '{next_q_text}'")

            ack_prefix = ""
            if not any(next_q_text.lower().startswith(w) for w in ["नमस्ते", "नमस्कार", "hello", "hi", "धन्यवाद", "thanks"]):
                if last_q and (last_q.get("type") or "").lower() == "single_choice":
                    ack_prefix = "बहुत बढ़िया! " if script_lang == "hi" else ("खूप छान! " if script_lang == "mr" else "Great! ")
                elif last_q and (last_q.get("type") or "").lower() == "text":
                    ack_prefix = "धन्यवाद। " if script_lang == "hi" else ("धन्यवाद साहेब. " if script_lang == "mr" else "Thank you. ")
                elif last_q and (last_q.get("type") or "").lower() == "number":
                    ack_prefix = "जी बिल्कुल! " if script_lang == "hi" else ("नक्कीच! " if script_lang == "mr" else "Understood. ")
                elif last_q:
                    ack_prefix = "जी ठीक है। " if script_lang == "hi" else ("समजले साहेब. " if script_lang == "mr" else "Okay. ")

            return f"{ack_prefix}{next_q_text}"

        # 13. All questions completed -> use the supplied closing when one
        # exists; otherwise preserve the generic closing for older scripts.
        # Guard: In follow-up phase ("Aapka koi aur question hai?"), do NOT close
        # if caller is asking a question, inquiring, or confirming continuation!
        if in_follow_up_phase:
            user_has_no_more = bool(re.search(
                r"\b(?:nahi|nahin|no|nope|nothing|बस|काही\s+नाही|नाही|नको|कुछ\s+नहीं|नहीं|झाले|हो\s+गया)\b|"
                r"^(?:nahi|nahin|no|nope|na|ना|नहीं|नाही|नको|बस|धन्यवाद|thanks|thank\s+you)[.!, ]*$",
                last_user_msg.strip(),
                re.IGNORECASE
            ))
            if not user_has_no_more:
                if "ALLOW_SYSTEM_PROMPT_FACTS" in system_prompt:
                    logger.info("FastQuestionnaireEngine: Follow-up phase active question/statement -> delegating to LLM")
                    return None
                if cls.is_conversational_filler(last_user_msg) or any(w in last_user_lower for w in ["हाँ", "हां", "yes", "sure", "सांगा", "होय", "हो"]):
                    if script_lang == "mr":
                        return "होय साहेब, सांगा काय माहिती हवी आहे?"
                    elif script_lang == "hi":
                        return "जी, बताइए आपका क्या प्रश्न है?"
                    return "Yes, please let me know what you would like to ask."

        logger.info(f"FastQuestionnaireEngine: All {len(questions)} questions completed -> delivering closing")
        scripted_closing = cls.closing_text(questions)
        if scripted_closing:
            return scripted_closing
        if script_lang == "mr":
            return "धन्यवाद साहेब, आपली माहिती नोंदवली गेली आहे. आमची टीम लवकरच आपल्याशी संपर्क करेल. आपला दिवस चांगला जावो!"
        elif script_lang == "hi":
            return "धन्यवाद जी, आपकी सभी जानकारी दर्ज कर ली गई है। हमारा प्रतिनिधि जल्द ही आपसे संपर्क करेगा। आपका दिन शुभ हो!"
        return "Thank you so much, all your details have been noted. Our team will contact you shortly. Have a great day!"


    @classmethod
    def resolve_next_turn_detailed(cls, messages: List[Dict[str, Any]]) -> Tuple[Optional[str], bool]:
        """resolve_next_turn + a terminal flag: True when the returned reply
        ends the call (caller-refusal goodbye, or the script-completed
        closing). Telephony engines use it to hang up cleanly after speaking
        the reply instead of waiting for another caller turn. The plain
        resolve_next_turn contract is unchanged for existing callers."""
        reply = cls.resolve_next_turn(messages)
        if reply is None:
            return None, False
        system_prompt = ""
        assistant_msgs: List[str] = []
        last_user_msg = ""
        for m in messages:
            role = m.get("role", "")
            content = m.get("content", "") or ""
            if role == "system" and not system_prompt:
                system_prompt = content
            elif role == "assistant":
                assistant_msgs.append(content)
            elif role == "user":
                last_user_msg = content.strip()
        questions = cls.parse_questionnaire_from_prompt(system_prompt)
        asked = cls.asked_question_indices(questions, assistant_msgs) if questions else set()
        last_q_idx = max(asked) if asked else None
        last_q = next((q for q in questions if q["index"] == last_q_idx), None) if last_q_idx else None
        is_yes_no_q = bool(last_q and (last_q.get("type") or "").lower() == "yes_no")
        is_bare_neg = last_user_msg.strip().lower() in ["no", "nope", "nahi", "nahin", "nako", "नको", "नाही", "नहीं"]
        # Terminal check: Caller refusal or callback/reschedule request ends call cleanly
        if last_user_msg and (cls.is_refusal(last_user_msg) or cls.is_reschedule_or_busy(last_user_msg)) and not (is_yes_no_q and is_bare_neg):
            return reply, True
        # If assistant has already delivered a farewell earlier in the call, this turn is terminal
        if any(cls.is_farewell_text(m) for m in assistant_msgs):
            return reply, True
        if questions:
            asked = cls.asked_question_indices(questions, assistant_msgs)
            # Once the scripted closing has actually been spoken, finish the
            # carrier call. This prevents a later "okay" from falling into
            # the general LLM and changing language after the goodbye.
            if reply == cls.closing_text(questions):
                return reply, True
            # A follow-up item intentionally keeps the call open for repeated
            # approved FAQ answers until the caller says they have no more.
            if any((q.get("type") or "").lower() == "follow_up" for q in questions):
                return reply, False
            if cls.next_unasked_question(questions, asked) is None:
                return reply, True
        return reply, False


fast_questionnaire_orchestrator = FastQuestionnaireOrchestrator()
