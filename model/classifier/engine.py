import re
from typing import List, Optional, Tuple, Dict, Any
from .models import (
    IntentClassification,
    InterestStrength,
    StrictClassificationResponse,
    DetailedClassificationResponse,
    Turn,
    SpeakerRole,
)
from .parser import TranscriptParser
from .lexicon import IntentLexicon
from .normalizer import TextNormalizer
from .context_analyzer import ContextAnalyzer


class IntentClassifier:
    """
    Multilingual Intent Classifier for AI-powered sales & support calls.
    Accurately classifies customer responses into 5 core categories:
    1. INTERESTED
    2. NOT_INTERESTED
    3. CALLBACK_REQUESTED
    4. NEEDS_INFORMATION
    5. UNCERTAIN
    
    Also provides granular `interest_strength` scoring (HIGH, MEDIUM, LOW, UNKNOWN),
    opt-out detection, objection diagnosis, and preceding-turn context analysis.
    
    Supports:
    - English
    - Hindi (Devanagari & Romanized/Hinglish)
    - Marathi (Devanagari & Romanized/Marathish)
    - Code-mixed utterances
    """

    def __init__(self):
        self.parser = TranscriptParser
        self.lexicon = IntentLexicon
        self.normalizer = TextNormalizer
        self.context_analyzer = ContextAnalyzer

    def classify_strict(self, transcript: str, binary: bool = True) -> Dict[str, str]:
        """
        Returns strict JSON format.
        If binary=True (default for backward compatibility), returns:
        {"classification": "INTERESTED"} or {"classification": "NOT_INTERESTED"}.
        If binary=False, returns exact class:
        {"classification": "INTERESTED"|"NOT_INTERESTED"|"CALLBACK_REQUESTED"|"NEEDS_INFORMATION"|"UNCERTAIN"}
        """
        detailed = self.classify_detailed(transcript)
        if binary and detailed.binary_classification:
            return {"classification": detailed.binary_classification}
        return {"classification": detailed.classification.value}

    def classify(self, transcript: str, explain: bool = False, binary: bool = True) -> Dict[str, Any]:
        """Classifies transcript, returning strict JSON or detailed schema based on `explain`."""
        if not explain:
            return self.classify_strict(transcript, binary=binary)
        return self.classify_detailed(transcript).model_dump()

    def classify_detailed(self, transcript: str) -> DetailedClassificationResponse:
        """
        Evaluates the transcript through the context-aware multilingual decision algorithm
        and returns a complete diagnostic response.
        """
        raw_text = transcript.strip() if transcript else ""
        if not raw_text:
            return DetailedClassificationResponse(
                classification=IntentClassification.NOT_INTERESTED,
                binary_classification="NOT_INTERESTED",
                interest_strength=InterestStrength.UNKNOWN,
                confidence=1.0,
                reason="Empty transcript: No evidence of customer intent.",
                priority_level=2,
                rule_applied="Empty transcript fallback",
                languages_detected=[],
                customer_turns_count=0,
                total_turns_count=0,
                signals_detected=[],
                is_ambiguous_rescued=False,
                opt_out_detected=False,
                callback_requested=False,
                objection_detected=None,
                turns=[]
            )

        turns = self.parser.parse(raw_text)
        languages = self.lexicon.detect_languages(raw_text)

        customer_turns: List[Turn] = []
        customer_turn_preceding_agents: List[Optional[str]] = []
        all_detected_signals = set()

        last_agent_text: Optional[str] = None
        for turn in turns:
            normalized_turn_text = self.normalizer.normalize(turn.text)
            signals = self.lexicon.extract_signals_from_text(normalized_turn_text)
            turn.signals = signals

            if turn.role == SpeakerRole.AGENT:
                last_agent_text = turn.text
            elif turn.role == SpeakerRole.CUSTOMER:
                customer_turns.append(turn)
                customer_turn_preceding_agents.append(last_agent_text)
                all_detected_signals.update(signals)

        # Fallback if no explicit Customer turns were identified
        if not customer_turns:
            for turn in turns:
                if turn.role != SpeakerRole.AGENT:
                    customer_turns.append(turn)
                    customer_turn_preceding_agents.append(None)
                    all_detected_signals.update(turn.signals)

        # -------------------------------------------------------------
        # STEP 0: Context-Aware Bare Acknowledgements
        # If customer provided ONLY bare affirmative acknowledgements ('Yes', 'Haan', 'Ho')
        # in response to a preceding agent question, resolve contextual intent first.
        # -------------------------------------------------------------
        is_only_bare_acknowledgements = bool(customer_turns) and all(
            self.context_analyzer.is_bare_acknowledgement(ct.text)
            for ct in customer_turns
        )

        if is_only_bare_acknowledgements and customer_turn_preceding_agents and customer_turn_preceding_agents[-1]:
            last_cust_turn = customer_turns[-1]
            last_agent_question = customer_turn_preceding_agents[-1]

            eval_result = self.context_analyzer.evaluate_acknowledgement(last_agent_question, last_cust_turn.text)

            if eval_result == "NEUTRAL_IDENTITY":
                return DetailedClassificationResponse(
                    classification=IntentClassification.UNCERTAIN,
                    binary_classification="NOT_INTERESTED",
                    interest_strength=InterestStrength.UNKNOWN,
                    confidence=0.88,
                    reason=f"Customer merely acknowledged identity or audio verification ('{last_cust_turn.text}'); no product interest inferred.",
                    priority_level=5,
                    rule_applied="Context-Aware Acknowledgement: Identity check agreement is neutral -> UNCERTAIN",
                    languages_detected=languages,
                    customer_turns_count=len(customer_turns),
                    total_turns_count=len(turns),
                    signals_detected=list(all_detected_signals),
                    is_ambiguous_rescued=False,
                    opt_out_detected=False,
                    callback_requested=False,
                    objection_detected=None,
                    turns=turns
                )
            elif eval_result == "PITCH_AGREEMENT":
                return DetailedClassificationResponse(
                    classification=IntentClassification.INTERESTED,
                    binary_classification="INTERESTED",
                    interest_strength=InterestStrength.MEDIUM,
                    confidence=0.90,
                    reason="Customer agreed to receive product explanation in response to agent inquiry.",
                    priority_level=3,
                    rule_applied="Context-Aware Acknowledgement: Agreed to product pitch -> INTERESTED",
                    languages_detected=languages,
                    customer_turns_count=len(customer_turns),
                    total_turns_count=len(turns),
                    signals_detected=list(all_detected_signals),
                    is_ambiguous_rescued=False,
                    opt_out_detected=False,
                    callback_requested=False,
                    objection_detected=None,
                    turns=turns
                )

        # -------------------------------------------------------------
        # STEP 1: Empty or Non-Conversational Disconnects
        # -------------------------------------------------------------
        is_empty_or_greeting_only = True
        for ct in customer_turns:
            cleaned_simple = re.sub(r"[^\w\s]", "", ct.text.strip().lower()).strip()
            if (not self.lexicon.match_any(ct.text, self.lexicon.EMPTY_OR_GREETING_PATTERNS)
                    and cleaned_simple not in ["hello", "hi", "hey", "haan", "ha", "boliye", "bolo", "kaun", "ji"]):
                is_empty_or_greeting_only = False
                break

        positive_signal_types = {
            "HIGH_INTENT", "GENERAL_INTEREST", "NEEDS_INFORMATION", 
            "CALLBACK_REQUESTED", "OBJECTION_BUT_INTERESTED", "SKEPTICISM"
        }

        if is_empty_or_greeting_only and not any(s in all_detected_signals for s in positive_signal_types):
            return DetailedClassificationResponse(
                classification=IntentClassification.NOT_INTERESTED,
                binary_classification="NOT_INTERESTED",
                interest_strength=InterestStrength.UNKNOWN,
                confidence=0.95,
                reason="Call disconnected or contained only greetings without product discussion or intent signal.",
                priority_level=2,
                rule_applied="Non-conversational disconnect",
                languages_detected=languages,
                customer_turns_count=len(customer_turns),
                total_turns_count=len(turns),
                signals_detected=list(all_detected_signals),
                is_ambiguous_rescued=False,
                opt_out_detected=False,
                callback_requested=False,
                objection_detected=None,
                turns=turns
            )

        # -------------------------------------------------------------
        # STEP 2: Hard Opt-Out / Do-Not-Contact (Priority 1)
        # Explicit opt-out / DNC MUST result in NOT_INTERESTED and flag opt_out_detected
        # -------------------------------------------------------------
        for ct in customer_turns:
            if "OPT_OUT" in ct.signals:
                return DetailedClassificationResponse(
                    classification=IntentClassification.NOT_INTERESTED,
                    binary_classification="NOT_INTERESTED",
                    interest_strength=InterestStrength.UNKNOWN,
                    confidence=0.99,
                    reason=f"Customer explicitly requested do-not-contact: '{ct.text}'",
                    priority_level=1,
                    rule_applied="Priority 1: Customer opt-out / DNC overrides all positive signals",
                    languages_detected=languages,
                    customer_turns_count=len(customer_turns),
                    total_turns_count=len(turns),
                    signals_detected=list(all_detected_signals),
                    is_ambiguous_rescued=False,
                    opt_out_detected=True,
                    callback_requested=False,
                    objection_detected=None,
                    turns=turns
                )

        # -------------------------------------------------------------
        # STEP 3: Wrong Person / Irrelevant Customer (Priority 1.5)
        # -------------------------------------------------------------
        for ct in customer_turns:
            if "WRONG_PERSON" in ct.signals:
                return DetailedClassificationResponse(
                    classification=IntentClassification.NOT_INTERESTED,
                    binary_classification="NOT_INTERESTED",
                    interest_strength=InterestStrength.UNKNOWN,
                    confidence=0.95,
                    reason=f"Customer indicated wrong person or irrelevant requirement: '{ct.text}'",
                    priority_level=1,
                    rule_applied="Wrong Person / Irrelevant Customer",
                    languages_detected=languages,
                    customer_turns_count=len(customer_turns),
                    total_turns_count=len(turns),
                    signals_detected=list(all_detected_signals),
                    is_ambiguous_rescued=False,
                    opt_out_detected=False,
                    callback_requested=False,
                    objection_detected=None,
                    turns=turns
                )

        # -------------------------------------------------------------
        # STEP 4: Uncertain Negation Nuance ("Not sure if I'm interested")
        # Example: "I'm not sure if I'm interested" / "मला रस आहे की नाही ते माहीत नाही"
        # -------------------------------------------------------------
        for ct in customer_turns:
            if "UNCERTAIN_NEGATION" in ct.signals:
                return DetailedClassificationResponse(
                    classification=IntentClassification.UNCERTAIN,
                    binary_classification="INTERESTED",  # Rescued for lead follow-up
                    interest_strength=InterestStrength.UNKNOWN,
                    confidence=0.90,
                    reason=f"Customer expressed uncertainty regarding interest: '{ct.text}'",
                    priority_level=5,
                    rule_applied="Negation Nuance: Customer uncertain if interested -> UNCERTAIN",
                    languages_detected=languages,
                    customer_turns_count=len(customer_turns),
                    total_turns_count=len(turns),
                    signals_detected=list(all_detected_signals),
                    is_ambiguous_rescued=True,
                    opt_out_detected=False,
                    callback_requested=False,
                    objection_detected=None,
                    turns=turns
                )

        # -------------------------------------------------------------
        # STEP 5: Mixed Sentiment Resolution
        # Case A: "Expensive, but I'm interested" / "Thoda expensive hai, but what are specs?" -> INTERESTED (Objection: price)
        # Case B: "Expensive, I don't want it" -> NOT_INTERESTED (Objection: price)
        # -------------------------------------------------------------
        has_objection_with_inquiry = (
            "OBJECTION_BUT_INTERESTED" in all_detected_signals or
            ("SKEPTICISM" in all_detected_signals and any(sig in {"NEEDS_INFORMATION", "GENERAL_INTEREST", "HIGH_INTENT"} for sig in all_detected_signals))
        )

        if has_objection_with_inquiry:
            return DetailedClassificationResponse(
                classification=IntentClassification.INTERESTED,
                binary_classification="INTERESTED",
                interest_strength=InterestStrength.MEDIUM,
                confidence=0.91,
                reason="Customer raised a price/product objection alongside an inquiry or affirmation.",
                priority_level=3,
                rule_applied="Mixed Sentiment: Positive intent overrides price objection -> INTERESTED",
                languages_detected=languages,
                customer_turns_count=len(customer_turns),
                total_turns_count=len(turns),
                signals_detected=list(all_detected_signals),
                is_ambiguous_rescued=False,
                opt_out_detected=False,
                callback_requested=False,
                objection_detected="price",
                turns=turns
            )

        if "OBJECTION_AND_REJECTED" in all_detected_signals and not any(s in all_detected_signals for s in ["HIGH_INTENT", "GENERAL_INTEREST"]):
            return DetailedClassificationResponse(
                classification=IntentClassification.NOT_INTERESTED,
                binary_classification="NOT_INTERESTED",
                interest_strength=InterestStrength.UNKNOWN,
                confidence=0.95,
                reason="Customer rejected offer citing cost/objection.",
                priority_level=2,
                rule_applied="Mixed Sentiment: Objection followed by rejection -> NOT_INTERESTED",
                languages_detected=languages,
                customer_turns_count=len(customer_turns),
                total_turns_count=len(turns),
                signals_detected=list(all_detected_signals),
                is_ambiguous_rescued=False,
                opt_out_detected=False,
                callback_requested=False,
                objection_detected="price",
                turns=turns
            )

        # -------------------------------------------------------------
        # STEP 6: Context-Aware Bare Acknowledgements
        # If customer only provided a bare acknowledgement ('Yes', 'Haan', 'Ho')
        # Check preceding agent turn!
        # -------------------------------------------------------------
        is_only_bare_acknowledgements = all(
            self.context_analyzer.is_bare_acknowledgement(ct.text)
            for ct in customer_turns
        )

        if is_only_bare_acknowledgements:
            last_cust_turn = customer_turns[-1]
            last_agent_question = customer_turn_preceding_agents[-1]

            eval_result = self.context_analyzer.evaluate_acknowledgement(last_agent_question, last_cust_turn.text)

            if eval_result == "NEUTRAL_IDENTITY":
                return DetailedClassificationResponse(
                    classification=IntentClassification.UNCERTAIN,
                    binary_classification="NOT_INTERESTED",
                    interest_strength=InterestStrength.UNKNOWN,
                    confidence=0.88,
                    reason="Customer merely acknowledged identity or audio verification ('" + last_cust_turn.text + "'); no product interest inferred.",
                    priority_level=5,
                    rule_applied="Context-Aware Acknowledgement: Identity check agreement is neutral -> UNCERTAIN",
                    languages_detected=languages,
                    customer_turns_count=len(customer_turns),
                    total_turns_count=len(turns),
                    signals_detected=list(all_detected_signals),
                    is_ambiguous_rescued=False,
                    opt_out_detected=False,
                    callback_requested=False,
                    objection_detected=None,
                    turns=turns
                )
            elif eval_result == "PITCH_AGREEMENT":
                return DetailedClassificationResponse(
                    classification=IntentClassification.INTERESTED,
                    binary_classification="INTERESTED",
                    interest_strength=InterestStrength.MEDIUM,
                    confidence=0.90,
                    reason="Customer agreed to receive product explanation in response to agent inquiry.",
                    priority_level=3,
                    rule_applied="Context-Aware Acknowledgement: Agreed to product pitch -> INTERESTED",
                    languages_detected=languages,
                    customer_turns_count=len(customer_turns),
                    total_turns_count=len(turns),
                    signals_detected=list(all_detected_signals),
                    is_ambiguous_rescued=False,
                    opt_out_detected=False,
                    callback_requested=False,
                    objection_detected=None,
                    turns=turns
                )

        # -------------------------------------------------------------
        # STEP 7: Temporal Analysis (Rejections vs Later Positive Signals)
        # -------------------------------------------------------------
        latest_rejection_idx = -1
        latest_positive_idx = -1

        rejection_signal_types = {"REJECTION", "INDIRECT_REJECTION"}

        for idx, ct in enumerate(customer_turns):
            if any(sig in rejection_signal_types for sig in ct.signals):
                latest_rejection_idx = idx
            if any(sig in positive_signal_types for sig in ct.signals):
                latest_positive_idx = idx

        # Late positive signal overrides earlier hesitation/rejection
        if latest_positive_idx > latest_rejection_idx and latest_positive_idx != -1:
            matching_turn = customer_turns[latest_positive_idx]
            
            if "HIGH_INTENT" in matching_turn.signals:
                c_label = IntentClassification.INTERESTED
                s_level = InterestStrength.HIGH
            elif "NEEDS_INFORMATION" in matching_turn.signals:
                c_label = IntentClassification.NEEDS_INFORMATION
                s_level = InterestStrength.MEDIUM
            elif "CALLBACK_REQUESTED" in matching_turn.signals:
                c_label = IntentClassification.CALLBACK_REQUESTED
                s_level = InterestStrength.LOW
            else:
                c_label = IntentClassification.INTERESTED
                s_level = InterestStrength.MEDIUM

            return DetailedClassificationResponse(
                classification=c_label,
                binary_classification="INTERESTED",
                interest_strength=s_level,
                confidence=0.92,
                reason=f"Customer showed positive signal ('{matching_turn.text}') which overrides earlier hesitation.",
                priority_level=3,
                rule_applied="Temporal Override: Positive signal overrides earlier hesitation",
                languages_detected=languages,
                customer_turns_count=len(customer_turns),
                total_turns_count=len(turns),
                signals_detected=list(all_detected_signals),
                is_ambiguous_rescued=False,
                opt_out_detected=False,
                callback_requested=(c_label == IntentClassification.CALLBACK_REQUESTED),
                objection_detected=None,
                turns=turns
            )

        # Rejection at the end
        if latest_rejection_idx != -1 and latest_rejection_idx >= latest_positive_idx:
            rejection_turn = customer_turns[latest_rejection_idx]

            # If the rejection turn contains an active inquiry ("pehle price batao phir bolunga")
            if any(sig in positive_signal_types for sig in rejection_turn.signals):
                return DetailedClassificationResponse(
                    classification=IntentClassification.INTERESTED,
                    binary_classification="INTERESTED",
                    interest_strength=InterestStrength.MEDIUM,
                    confidence=0.88,
                    reason=f"Customer expressed frustration alongside an active inquiry ('{rejection_turn.text}'). Intent overrides sentiment.",
                    priority_level=4,
                    rule_applied="Active inquiry overrides impatient sentiment",
                    languages_detected=languages,
                    customer_turns_count=len(customer_turns),
                    total_turns_count=len(turns),
                    signals_detected=list(all_detected_signals),
                    is_ambiguous_rescued=False,
                    opt_out_detected=False,
                    callback_requested=False,
                    objection_detected=None,
                    turns=turns
                )

            # Check if it was merely a polite sign-off (e.g. 'bye', 'thank you') after genuine inquiry
            polite_signoff_pattern = re.compile(
                r"^\s*(?:(?:ok|theek\s+hai|chalo|accha)\s*,?\s*)?(?:bye|bye\s+bye|alvida|tata|टाटा|बाय|thank\s+you|dhanyawad|shukriya)[\s\.,!]*$",
                re.IGNORECASE
            )
            is_pure_signoff = bool(polite_signoff_pattern.match(rejection_turn.text.strip()))

            if latest_positive_idx != -1 and is_pure_signoff:
                matching_turn = customer_turns[latest_positive_idx]
                return DetailedClassificationResponse(
                    classification=IntentClassification.INTERESTED,
                    binary_classification="INTERESTED",
                    interest_strength=InterestStrength.MEDIUM,
                    confidence=0.90,
                    reason=f"Customer engaged in positive discovery ('{matching_turn.text}') before polite call closing.",
                    priority_level=3,
                    rule_applied="Inquiry Preservation: Polite sign-off does not negate prior positive inquiry",
                    languages_detected=languages,
                    customer_turns_count=len(customer_turns),
                    total_turns_count=len(turns),
                    signals_detected=list(all_detected_signals),
                    is_ambiguous_rescued=False,
                    opt_out_detected=False,
                    callback_requested=False,
                    objection_detected=None,
                    turns=turns
                )

            return DetailedClassificationResponse(
                classification=IntentClassification.NOT_INTERESTED,
                binary_classification="NOT_INTERESTED",
                interest_strength=InterestStrength.UNKNOWN,
                confidence=0.95,
                reason=f"Customer made clear final rejection: '{rejection_turn.text}'",
                priority_level=2,
                rule_applied="Explicit final rejection -> NOT_INTERESTED",
                languages_detected=languages,
                customer_turns_count=len(customer_turns),
                total_turns_count=len(turns),
                signals_detected=list(all_detected_signals),
                is_ambiguous_rescued=False,
                opt_out_detected=False,
                callback_requested=False,
                objection_detected=None,
                turns=turns
            )

        # -------------------------------------------------------------
        # STEP 8: Specific Intent Categories (when no rejection)
        # -------------------------------------------------------------
        
        # 8A. Strong Buying Intent (HIGH Strength)
        if "HIGH_INTENT" in all_detected_signals:
            return DetailedClassificationResponse(
                classification=IntentClassification.INTERESTED,
                binary_classification="INTERESTED",
                interest_strength=InterestStrength.HIGH,
                confidence=0.96,
                reason="Customer showed explicit purchase, order, or immediate proceeding intent.",
                priority_level=3,
                rule_applied="Strong buying intent -> INTERESTED (HIGH)",
                languages_detected=languages,
                customer_turns_count=len(customer_turns),
                total_turns_count=len(turns),
                signals_detected=list(all_detected_signals),
                is_ambiguous_rescued=False,
                opt_out_detected=False,
                callback_requested=False,
                objection_detected=None,
                turns=turns
            )

        # 8B. General Positive Interest (MEDIUM Strength)
        if "GENERAL_INTEREST" in all_detected_signals:
            return DetailedClassificationResponse(
                classification=IntentClassification.INTERESTED,
                binary_classification="INTERESTED",
                interest_strength=InterestStrength.MEDIUM,
                confidence=0.93,
                reason="Customer showed positive interest, requested details on WhatsApp, or asked for a demo.",
                priority_level=3,
                rule_applied="Positive interest & engagement -> INTERESTED (MEDIUM)",
                languages_detected=languages,
                customer_turns_count=len(customer_turns),
                total_turns_count=len(turns),
                signals_detected=list(all_detected_signals),
                is_ambiguous_rescued=False,
                opt_out_detected=False,
                callback_requested=False,
                objection_detected=None,
                turns=turns
            )

        # 8C. Needs Information / Exploratory Inquiry (MEDIUM Strength)
        if "NEEDS_INFORMATION" in all_detected_signals:
            return DetailedClassificationResponse(
                classification=IntentClassification.NEEDS_INFORMATION,
                binary_classification="INTERESTED",
                interest_strength=InterestStrength.MEDIUM,
                confidence=0.90,
                reason="Customer asked exploratory questions regarding pricing, mechanism, benefits, or options.",
                priority_level=4,
                rule_applied="Customer inquiries and exploration -> NEEDS_INFORMATION (MEDIUM)",
                languages_detected=languages,
                customer_turns_count=len(customer_turns),
                total_turns_count=len(turns),
                signals_detected=list(all_detected_signals),
                is_ambiguous_rescued=False,
                opt_out_detected=False,
                callback_requested=False,
                objection_detected=None,
                turns=turns
            )

        # 8D. Skepticism with Continued Engagement
        if "SKEPTICISM" in all_detected_signals:
            return DetailedClassificationResponse(
                classification=IntentClassification.INTERESTED,
                binary_classification="INTERESTED",
                interest_strength=InterestStrength.MEDIUM,
                confidence=0.86,
                reason="Customer expressed skepticism or cost concerns while remaining engaged in the dialogue.",
                priority_level=6,
                rule_applied="Skepticism with continued engagement -> INTERESTED (MEDIUM)",
                languages_detected=languages,
                customer_turns_count=len(customer_turns),
                total_turns_count=len(turns),
                signals_detected=list(all_detected_signals),
                is_ambiguous_rescued=False,
                opt_out_detected=False,
                callback_requested=False,
                objection_detected="price",
                turns=turns
            )

        # 8E. Callback Requested (LOW Strength)
        if "CALLBACK_REQUESTED" in all_detected_signals:
            return DetailedClassificationResponse(
                classification=IntentClassification.CALLBACK_REQUESTED,
                binary_classification="INTERESTED",
                interest_strength=InterestStrength.LOW,
                confidence=0.92,
                reason="Customer requested a callback at a later time or date without rejecting.",
                priority_level=5,
                rule_applied="Customer requested callback -> CALLBACK_REQUESTED (LOW)",
                languages_detected=languages,
                customer_turns_count=len(customer_turns),
                total_turns_count=len(turns),
                signals_detected=list(all_detected_signals),
                is_ambiguous_rescued=False,
                opt_out_detected=False,
                callback_requested=True,
                objection_detected=None,
                turns=turns
            )

        # 8F. Uncertain / Indecision
        if "UNCERTAIN" in all_detected_signals:
            return DetailedClassificationResponse(
                classification=IntentClassification.UNCERTAIN,
                binary_classification="INTERESTED",  # Preserved for nurture
                interest_strength=InterestStrength.UNKNOWN,
                confidence=0.88,
                reason="Customer expressed hesitation, indecision, or requested deliberation time.",
                priority_level=5,
                rule_applied="Customer indecision -> UNCERTAIN",
                languages_detected=languages,
                customer_turns_count=len(customer_turns),
                total_turns_count=len(turns),
                signals_detected=list(all_detected_signals),
                is_ambiguous_rescued=True,
                opt_out_detected=False,
                callback_requested=False,
                objection_detected=None,
                turns=turns
            )

        # -------------------------------------------------------------
        # STEP 9: Negative Sentiment & Disinterest Check Before Multi-Turn Fallback
        # -------------------------------------------------------------
        customer_full_text = " ".join(ct.text for ct in customer_turns).strip()
        has_negative_signals = any(
            sig in {"REJECTION", "INDIRECT_REJECTION", "OPT_OUT", "WRONG_PERSON"}
            for sig in all_detected_signals
        )

        negative_markers_found = []
        for pat in self.lexicon.EXPLICIT_REJECTION_PATTERNS + self.lexicon.INDIRECT_REJECTION_PATTERNS:
            m = pat.search(customer_full_text)
            if m:
                negative_markers_found.append(m.group(0))

        if has_negative_signals or negative_markers_found:
            return DetailedClassificationResponse(
                classification=IntentClassification.NOT_INTERESTED,
                binary_classification="NOT_INTERESTED",
                interest_strength=InterestStrength.UNKNOWN,
                confidence=0.88,
                reason="Customer indicated lack of interest or refusal with no positive inquiry.",
                priority_level=2,
                rule_applied="Customer disinterest / refusal -> NOT_INTERESTED",
                languages_detected=languages,
                customer_turns_count=len(customer_turns),
                total_turns_count=len(turns),
                signals_detected=list(all_detected_signals) or ["REJECTION"],
                is_ambiguous_rescued=False,
                opt_out_detected=False,
                callback_requested=False,
                objection_detected=None,
                turns=turns
            )

        # -------------------------------------------------------------
        # STEP 10: Multi-Turn Engagement Rescue vs Unsupported Uncertainty
        # -------------------------------------------------------------
        if (len(customer_turns) >= 2 or len(turns) >= 4) and not has_negative_signals:
            return DetailedClassificationResponse(
                classification=IntentClassification.INTERESTED,
                binary_classification="INTERESTED",
                interest_strength=InterestStrength.LOW,
                confidence=0.75,
                reason="Multi-turn conversation without rejection preserved as lead.",
                priority_level=7,
                rule_applied="Unclear multi-turn dialogue without rejection rescued as lead",
                languages_detected=languages,
                customer_turns_count=len(customer_turns),
                total_turns_count=len(turns),
                signals_detected=list(all_detected_signals),
                is_ambiguous_rescued=True,
                opt_out_detected=False,
                callback_requested=False,
                objection_detected=None,
                turns=turns
            )

        # If transcript is very short or unclear, prefer UNCERTAIN rather than guessing
        return DetailedClassificationResponse(
            classification=IntentClassification.UNCERTAIN,
            binary_classification="NOT_INTERESTED",
            interest_strength=InterestStrength.UNKNOWN,
            confidence=0.65,
            reason="Customer intent cannot be reliably established from short or inconclusive utterance.",
            priority_level=5,
            rule_applied="Inconclusive conversational data -> UNCERTAIN",
            languages_detected=languages,
            customer_turns_count=len(customer_turns),
            total_turns_count=len(turns),
            signals_detected=list(all_detected_signals),
            is_ambiguous_rescued=False,
            opt_out_detected=False,
            callback_requested=False,
            objection_detected=None,
            turns=turns
        )
