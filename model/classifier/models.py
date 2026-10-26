from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class IntentClassification(str, Enum):
    INTERESTED = "INTERESTED"
    NOT_INTERESTED = "NOT_INTERESTED"
    CALLBACK_REQUESTED = "CALLBACK_REQUESTED"
    NEEDS_INFORMATION = "NEEDS_INFORMATION"
    UNCERTAIN = "UNCERTAIN"


class InterestStrength(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class StrictClassificationResponse(BaseModel):
    """
    Strict response format required by Section 20 of specification:
    {
      "classification": "INTERESTED"
    }
    """
    classification: IntentClassification = Field(
        ...,
        description="Core intent classification label."
    )


class SpeakerRole(str, Enum):
    AGENT = "agent"
    CUSTOMER = "customer"
    UNKNOWN = "unknown"


class Turn(BaseModel):
    role: SpeakerRole
    text: str
    turn_index: int
    signals: List[str] = Field(default_factory=list)


class DetailedClassificationResponse(BaseModel):
    classification: IntentClassification
    confidence: float
    reason: str
    priority_level: int
    rule_applied: str
    languages_detected: List[str] = Field(default_factory=list)
    customer_turns_count: int
    total_turns_count: int
    signals_detected: List[str] = Field(default_factory=list)
    is_ambiguous_rescued: bool = False
    interest_strength: InterestStrength = Field(
        default=InterestStrength.UNKNOWN,
        description="Strength of customer buying interest: HIGH, MEDIUM, LOW, or UNKNOWN."
    )
    opt_out_detected: bool = Field(
        default=False,
        description="True if customer explicitly demanded no-further-contact / DNC / number deletion."
    )
    callback_requested: bool = Field(
        default=False,
        description="True if customer requested a callback / postpone without rejection."
    )
    objection_detected: Optional[str] = Field(
        default=None,
        description="Type of objection raised, e.g. 'price' or 'trust', if customer remained engaged."
    )
    binary_classification: Optional[str] = Field(
        default=None,
        description="Strict two-class projection ('INTERESTED' or 'NOT_INTERESTED') for backward compatibility."
    )
    turns: Optional[List[Turn]] = None


class ClassifyRequest(BaseModel):
    transcript: str = Field(
        ...,
        description="The call transcript containing Agent and Customer utterances."
    )
    explain: bool = Field(
        default=False,
        description="If true, returns detailed explanation, signals, and turns. If false, returns strict format."
    )
    binary: bool = Field(
        default=True,
        description="If true in strict mode, projects classification to binary INTERESTED/NOT_INTERESTED."
    )
    industry_context: Optional[str] = Field(
        default=None,
        description="Optional industry metadata (e.g. SaaS, Insurance, Finance). Model remains industry-agnostic."
    )


class BatchClassifyRequest(BaseModel):
    transcripts: List[str] = Field(
        ...,
        description="List of transcript strings to classify."
    )
    explain: bool = Field(
        default=False,
        description="Whether to include detailed explanations."
    )
    binary: bool = Field(
        default=True,
        description="Whether to project results to binary classes."
    )


class BatchClassifyResponse(BaseModel):
    results: List[Any]
    total: int
    interested_count: int
    not_interested_count: int
