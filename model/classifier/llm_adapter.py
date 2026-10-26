import os
import json
from typing import Optional, Dict, Any
from .models import IntentClassification, InterestStrength

SYSTEM_PROMPT = """You are a Multilingual AI Call Transcript Customer Intent Classifier.
You analyze customer utterances across English, Hindi, Marathi, Hinglish, and Marathish to classify customer intent into:
- INTERESTED: Explicit buying intent, placing orders, requesting discounts/payment links, or affirmative product interest.
- NOT_INTERESTED: Explicit rejection, indirect refusal ("rehne dijiye", "rahu dya", "no thanks"), wrong number, or opt-out/DNC.
- CALLBACK_REQUESTED: Asking to call tomorrow, later, in the evening, busy now, driving, or in a meeting without rejection.
- NEEDS_INFORMATION: Asking exploratory questions about price, mechanism, features, package options, or cheaper alternatives.
- UNCERTAIN: Hesitation, deliberation ("maybe", "let me think", "sochkar bataunga", "vichar karun sangto", "not sure if interested").

Critical Principles:
1. CLASSIFY INTENT, NOT SENTIMENT: An angry customer saying "faltu baat band karo pehle price batao" has positive inquiry intent (NEEDS_INFORMATION).
2. CONTEXTUAL ACKNOWLEDGEMENT: A customer saying "Yes" / "Haan" / "Ho" to an identity verification question ("Am I speaking with Mr. Patil?") is NEUTRAL (UNCERTAIN), NOT product interest. A customer saying "Yes" to "Would you like to know more about this product?" is INTERESTED.
3. NEGATION & SKEPTICISM:
   - "I'm interested" -> INTERESTED
   - "I'm not interested" -> NOT_INTERESTED
   - "I'm not sure if I'm interested" -> UNCERTAIN
   - "It's expensive, but I'm interested" -> INTERESTED with price objection
   - "It's expensive, I don't want it" -> NOT_INTERESTED
4. PRIORITY 1 OPT-OUT: Explicit do-not-contact / DNC ("Don't call again", "Remove my number", "Punha call karu naka") overrides everything -> NOT_INTERESTED, opt_out_detected: true.
5. INTEREST STRENGTH:
   - HIGH: Explicit purchase, order, buy, proceed, discount request, payment link.
   - MEDIUM: Genuine product interest, questions about price, mechanism, features, requesting WhatsApp details.
   - LOW: Weak positive signals or callback requests without established product commitment.
   - UNKNOWN: Rejection, opt-out, bare identity confirmation, or unclassifiable disfluencies.

STRICT OUTPUT FORMAT:
Return strictly a valid JSON object:
{
  "classification": "INTERESTED",
  "interest_strength": "HIGH",
  "opt_out_detected": false,
  "callback_requested": false,
  "binary_classification": "INTERESTED"
}
"""

class LLMClassifierAdapter:
    """
    Optional LLM adapter supporting OpenAI or Gemini APIs when API keys are configured.
    Falls back safely if no API key is set or on network failure.
    """

    def __init__(self):
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        self.gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    def is_available(self) -> bool:
        return bool(self.openai_key or self.gemini_key)

    def classify(self, transcript: str, binary: bool = True) -> Optional[Dict[str, Any]]:
        """Invokes LLM if configured, returns parsed dict or None."""
        if self.openai_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.openai_key)
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": transcript}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0
                )
                raw_json = response.choices[0].message.content
                data = json.loads(raw_json)
                if binary:
                    binary_label = data.get("binary_classification") or (
                        "INTERESTED" if data.get("classification") in ["INTERESTED", "NEEDS_INFORMATION", "CALLBACK_REQUESTED"] else "NOT_INTERESTED"
                    )
                    return {"classification": binary_label}
                return data
            except Exception:
                return None
        return None
