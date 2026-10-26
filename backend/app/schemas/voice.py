from typing import List, Optional
from pydantic import BaseModel, Field


class VoiceProvider(BaseModel):
    provider: str
    display_name: str
    description: str
    supports_speed: bool = True
    supports_style: bool = False
    supported_languages: List[str] = Field(default_factory=list)


class VoiceItem(BaseModel):
    voice_id: str
    name: str
    gender: Optional[str] = None
    language: Optional[str] = None
    accent: Optional[str] = None
    description: Optional[str] = None
    preview_url: Optional[str] = None


class VoiceListResponse(BaseModel):
    provider: str
    total: int
    voices: List[VoiceItem]


class AgentVoiceConfig(BaseModel):
    voice_gender: str = Field(default="male", description="Gender of the voice: female, male, neutral")
    voice_id: str = Field(default="hm_omega", description="Dograh/TTS Voice ID")
    voice_name: str = Field(default="Omega - Clear Hindi Male", description="Human-friendly voice name")
    tts_provider: str = Field(default="speaches", description="TTS Provider key: dograh, speaches, sarvam, cartesia, elevenlabs, deepgram")
    language_mode: str = Field(default="auto_match", description="auto_match, hindi, english, hinglish, fixed")
    primary_language: str = Field(default="multi", description="multi (Auto Detect), hi, en, etc.")
    voice_style: str = Field(default="Friendly + Professional + Conversational", description="Style personality of the agent")
    speaking_speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speaking speed: 0.8x - 1.2x recommended")
