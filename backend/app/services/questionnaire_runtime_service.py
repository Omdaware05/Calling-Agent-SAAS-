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

    # Words that carry no question identity (honorifics, fillers, auxiliaries).
    # Dropped before token-overlap matching so paraphrases still match.
    _MATCH_STOPWORDS = {
        "साहेब", "जी", "sir", "madam", "the", "a", "an", "का", "की", "के",
        "आहे", "आहेत", "है", "हैं", "हो", "का?", "तुम्ही", "आपण", "आप",
    }

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
        """True if this scripted question was already spoken in `msg_norm`.

        Two complementary checks (the old code only did a raw 35-char prefix
        substring, so ANY LLM paraphrase of a question became invisible and
        the question was re-asked — the 'repeated questions' complaint):
        1. normalized full-text / leading-core substring;
        2. token overlap: >= 60% of the question's content tokens appear in
           the message (paraphrase-tolerant, still question-specific).
        """
        q_norm = cls._normalize_for_match(q_text)
        if not q_norm:
            return False
        if q_norm in msg_norm:
            return True
        core = q_norm[:40]
        if len(core) >= 12 and core in msg_norm:
            return True
        q_tokens = {t for t in q_norm.split() if len(t) >= 2 and t not in cls._MATCH_STOPWORDS}
        if len(q_tokens) >= 3:
            overlap = len(q_tokens & msg_tokens) / len(q_tokens)
            if overlap >= 0.6:
                return True
        return False

    # Markers that make a caller utterance a QUESTION rather than an answer
    # to the current script question. Deliberately conservative: a false
    # positive costs one fallback line + the pending question repeated; a
    # false negative lets the LLM improvise an answer, which must not happen.
    _QUESTION_WORDS = {
        "kya", "क्या", "kitna", "kitne", "kitni", "किती", "kab", "कब", "kahan",
        "kaha", "kaise", "कैसे", "kaisa", "kese", "kyu", "kyon", "क्यों",
        "konsa", "konsi", "konta", "konti", "kadhi", "कधी", "kase", "काय",
        "kuthe", "kashala", "what", "which", "how", "when", "where", "why",
        "does",
    }
    _QUESTION_PHRASES = (
        "is there", "do you", "can i", "can we", "hai kya", "है क्या",
        "ahe ka", "ahet ka", "आहे का", "milega kya", "hoga kya",
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
            if q["index"] not in asked and (q.get("type") or "").lower() != "reference":
                return q
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

        script_lang = cls.detect_script_language(system_prompt + " " + questions[0]["text"])
        last_user_lower = last_user_msg.lower()

        # 4. Check for Caller Refusal / Opt-out
        if cls.is_refusal(last_user_msg):
            logger.info("FastQuestionnaireEngine: Caller refusal detected -> instant polite goodbye")
            if script_lang == "mr":
                return "जी काही हरकत नाही साहेब, आपला खूप खूप धन्यवाद!"
            elif script_lang == "hi":
                return "जी कोई बात नहीं, आपका बहुत-बहुत धन्यवाद।"
            return "No problem at all, thank you very much for your time. Have a wonderful day!"

        # Determine which questions were already asked (paraphrase-tolerant).
        asked_indices = cls.asked_question_indices(questions, assistant_msgs)
        last_q_idx = max(asked_indices) if asked_indices else None

        # NOTE: there is deliberately no "Turn 0 -> LLM" bail any more. The
        # static greeting is spoken by the start node; the caller's first
        # reply used to fall through to the slow LLM, which paraphrased Q1 —
        # and because the paraphrase could not be recognised later, Q1 was
        # then re-asked verbatim (the 'welcome is slow' + 'repeated
        # questions' complaints). Now the flow below deterministically
        # serves the first unasked question (Q1) on that turn too.

        # 5. Check for Reschedule / Busy Right Now
        if any(kw in last_user_lower for kw in ["busy hu", "busy ahe", "call later", "call back", "nantar kara", "nantar phone", "bad me phone", "meeting me hu"]):
            logger.info("FastQuestionnaireEngine: Caller busy -> instant polite reschedule acknowledgement")
            if script_lang == "mr":
                return "काही हरकत नाही साहेब, आम्ही आपल्याला नंतर कॉल करू. खूप खूप धन्यवाद!"
            elif script_lang == "hi":
                return "जी कोई बात नहीं, हम आपको बाद में कॉल करेंगे। आपका बहुत-बहुत धन्यवाद और दिन शुभ हो!"
            return "No problem at all, we will call you back later. Thank you very much and have a great day!"

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
        caller_is_question = cls._looks_like_question(last_user_msg)
        caller_tokens = cls._qa_tokens(last_user_msg)
        caller_price_intent = bool(caller_tokens & _PRICE_MARKERS) or \
            any(kw in last_user_lower for kw in ["किंमत", "दर", "खर्च"])
        best_q, best_key = None, None
        for q in questions:
            q_text_lower = q["text"].lower()
            exp_ans = q.get("expected_answer", "")
            if not exp_ans or exp_ans.lower() in ("any answer", ""):
                continue
            legacy_match = any(kw in last_user_lower for kw in _QA_KEYWORDS) and \
                any(kw in q_text_lower for kw in _QA_KEYWORDS)
            overlap_match = caller_is_question and cls._qa_overlap_match(last_user_msg, q["text"])
            if not (legacy_match or overlap_match):
                continue
            q_tokens = cls._qa_tokens(q["text"])
            shared = sum(1 for tok in caller_tokens
                         if any(cls._token_match(tok, qt) for qt in q_tokens))
            q_price = 1 if (caller_price_intent and q_tokens & _PRICE_MARKERS) else 0
            key = (q_price, shared, -q["index"])
            if best_key is None or key > best_key:
                best_q, best_key = q, key
        if best_q is not None:
            exp_ans = best_q["expected_answer"]
            logger.info(f"FastQuestionnaireEngine: Direct Q&A match for '{best_q['text']}' -> returning expected answer directly")
            if script_lang == "mr":
                return f"साहेब, {exp_ans}. पुढचा प्रश्न..."
            elif script_lang == "hi":
                return f"जी, {exp_ans}।"
            return f"Regarding that, {exp_ans}."

        # 11. Unknown-question guard: the caller asked something that has NO
        # scripted answer. Never let the LLM invent one — speak the fixed
        # fallback line and carry on with the pending script question.
        if cls._looks_like_question(last_user_msg):
            next_q = cls.next_unasked_question(questions, asked_indices)
            q_suffix = f" {next_q['text']}" if next_q else ""
            logger.info("FastQuestionnaireEngine: Unknown caller question -> fixed no-information fallback (LLM invention blocked)")
            if script_lang == "mr":
                return f"माझ्याकडे याची माहिती सध्या नाही. आमची टीम आपल्याला कॉल करून माहिती देईल.{q_suffix}"
            elif script_lang == "hi":
                return f"मेरे पास इसकी जानकारी अभी नहीं है। हमारी टीम आपको कॉल करके जानकारी देगी।{q_suffix}"
            return f"I don't have that information currently. Our team will call you back with the details.{q_suffix}"

        # 12. Advance to the FIRST question that has not been asked yet.
        # (When nothing was asked yet — e.g. the caller just replied to the
        # opening greeting — this serves Q1 instantly and deterministically
        # instead of paying a slow LLM round-trip.)
        next_question_obj = cls.next_unasked_question(questions, asked_indices)

        if next_question_obj:
            next_q_text = next_question_obj["text"]
            logger.info(f"FastQuestionnaireEngine: Asked so far={sorted(asked_indices)} -> Serving Q{next_question_obj['index']}: '{next_q_text}'")

            if script_lang == "mr":
                ack_prefix = "समजले साहेब. "
            elif script_lang == "hi":
                ack_prefix = "जी ठीक है। "
            else:
                ack_prefix = "Understood. "

            return f"{ack_prefix}{next_q_text}"

        # 13. All questions completed -> deliver warm pre-defined closing
        logger.info(f"FastQuestionnaireEngine: All {len(questions)} questions completed -> delivering closing")
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
        if last_user_msg and cls.is_refusal(last_user_msg):
            return reply, True
        questions = cls.parse_questionnaire_from_prompt(system_prompt)
        if questions:
            asked = cls.asked_question_indices(questions, assistant_msgs)
            if cls.next_unasked_question(questions, asked) is None:
                return reply, True
        return reply, False


fast_questionnaire_orchestrator = FastQuestionnaireOrchestrator()
