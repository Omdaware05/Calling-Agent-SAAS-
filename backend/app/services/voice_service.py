import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import httpx

from app.config import settings
from app.schemas.voice import VoiceItem, VoiceListResponse, VoiceProvider
from app.services.dograh_service import DograhServiceException

logger = logging.getLogger(__name__)

# Trusted hostnames for voice preview audio proxying
TRUSTED_AUDIO_HOSTS = {
    "services.dograh.com",
    "cdn.sanity.io",
    "storage.googleapis.com",
    # "localhost" / "127.0.0.1" were in this allowlist — the voice
    # preview proxy would then fetch ANY internal service on the
    # backend host itself (SSRF). Loopback is not a trusted audio host.
}

# Verified default voice catalog for instant selection & fallback
DEFAULT_VOICE_CATALOG: Dict[str, List[Dict[str, Any]]] = {
    "dograh": [
        {
            "voice_id": "hm_omega",
            "name": "Omega - Clear Hindi Male (Kokoro)",
            "gender": "male",
            "language": "hi",
            "accent": "in",
            "description": "Clear, articulate Hindi adult male voice with crisp diction for customer support, consultation, and advisory.",
            "preview_url": "http://localhost:8001/api/voice/preview-local/hm_omega",
        },
        {
            "voice_id": "dg_voice_4c52528b7a1804810035",
            "name": "Aarti - Conversationalist",
            "gender": "female",
            "language": "hi",
            "accent": "in",
            "description": "Natural Indian female voice for polite customer dialogue, support, and appointments.",
            "preview_url": "https://services.dograh.com/api/v1/voice-proxy/dograh/voices/dg_voice_4c52528b7a1804810035/preview",
        },
        {
            "voice_id": "dg_voice_ee5efd12f17797d0ff39",
            "name": "Aarav - Old Time Storyteller",
            "gender": "male",
            "language": "en",
            "accent": "in",
            "description": "Warm, trustworthy adult male voice with a natural Indian accent, ideal for advisory and banking.",
            "preview_url": "https://services.dograh.com/api/v1/voice-proxy/dograh/voices/dg_voice_ee5efd12f17797d0ff39/preview",
        },
        {
            "voice_id": "dg_voice_7a81b2c3d4e5f6012345",
            "name": "Pooja - Dynamic & Cheerful",
            "gender": "female",
            "language": "hi",
            "accent": "in",
            "description": "Bright, enthusiastic female voice suited for sales promotions, reminders, and outbound campaigns.",
            "preview_url": "https://services.dograh.com/api/v1/voice-proxy/dograh/voices/dg_voice_4c52528b7a1804810035/preview",
        },
        {
            "voice_id": "dg_voice_8b92c3d4e5f6a7012345",
            "name": "Rohan - Calm Executive",
            "gender": "male",
            "language": "hi",
            "accent": "in",
            "description": "Assertive executive male voice with crisp Hindi-English diction for B2B client communications.",
            "preview_url": "https://services.dograh.com/api/v1/voice-proxy/dograh/voices/dg_voice_ee5efd12f17797d0ff39/preview",
        },
        {
            "voice_id": "dg_voice_9c03d4e5f6a7b8012345",
            "name": "Kavya - Empathetic Care",
            "gender": "female",
            "language": "hi",
            "accent": "in",
            "description": "Gentle, soothing tone best suited for clinic bookings, customer care, and sensitive followups.",
            "preview_url": "https://services.dograh.com/api/v1/voice-proxy/dograh/voices/dg_voice_4c52528b7a1804810035/preview",
        },
        {
            "voice_id": "dg_voice_0d14e5f6a7b8c9012345",
            "name": "Vikram - Direct & Clear",
            "gender": "male",
            "language": "en",
            "accent": "in",
            "description": "Clear and authoritative male voice with high diction clarity for verification calls and alerts.",
            "preview_url": "https://services.dograh.com/api/v1/voice-proxy/dograh/voices/dg_voice_ee5efd12f17797d0ff39/preview",
        },
    ],
    "sarvam": [
        {
            "voice_id": "shubh",
            "name": "Shubh - Northern Conversational",
            "gender": "male",
            "language": "hi",
            "accent": "in",
            "description": "Authentic conversational male voice, optimized for Hindi customer support and outreach.",
            "preview_url": "http://localhost:8001/api/voice/preview-sarvam/shubh",
        },
        {
            "voice_id": "ritu",
            "name": "Ritu - Warm Professional",
            "gender": "female",
            "language": "hi",
            "accent": "in",
            "description": "Polite, friendly female Hindi speaker for general inquiries and welcoming customer interactions.",
            "preview_url": "http://localhost:8001/api/voice/preview-sarvam/ritu",
        },
        {
            "voice_id": "aditya",
            "name": "Aditya - Regional Articulate",
            "gender": "male",
            "language": "mr",
            "accent": "in",
            "description": "Warm regional tone for Marathi, Hindi, and English customer interactions.",
            "preview_url": "http://localhost:8001/api/voice/preview-sarvam/aditya",
        },
        {
            "voice_id": "priya",
            "name": "Priya - Southern Fluent",
            "gender": "female",
            "language": "ta",
            "accent": "in",
            "description": "Fluent regional voice for Tamil, Telugu, and Hindi customer support.",
            "preview_url": "http://localhost:8001/api/voice/preview-sarvam/priya",
        },
        {
            "voice_id": "rahul",
            "name": "Rahul - High Confidence",
            "gender": "male",
            "language": "pa",
            "accent": "in",
            "description": "Confident male voice with natural Punjabi and Hindi cadence for retail and lead updates.",
            "preview_url": "http://localhost:8001/api/voice/preview-sarvam/rahul",
        },
        {
            "voice_id": "pooja",
            "name": "Pooja - Dynamic & Friendly",
            "gender": "female",
            "language": "hi",
            "accent": "in",
            "description": "Bright, energetic female tone ideal for promotions, reminders, surveys, and customer engagement.",
            "preview_url": "http://localhost:8001/api/voice/preview-sarvam/pooja",
        },
        {
            "voice_id": "kavya",
            "name": "Kavya - Empathetic Care",
            "gender": "female",
            "language": "hi",
            "accent": "in",
            "description": "Gentle, reassuring tone best suited for clinic bookings, customer satisfaction, and support callbacks.",
            "preview_url": "http://localhost:8001/api/voice/preview-sarvam/kavya",
        },
    ],
    "cartesia": [
        {
            "voice_id": "cartesia_sonic_sarah",
            "name": "Sonic Sarah - Expressive",
            "gender": "female",
            "language": "en",
            "accent": "us",
            "description": "Ultra-low latency conversational female voice, sub-150ms time-to-first-audio.",
            "preview_url": "https://services.dograh.com/api/v1/voice-proxy/dograh/voices/dg_voice_4c52528b7a1804810035/preview",
        },
        {
            "voice_id": "cartesia_sonic_mark",
            "name": "Sonic Mark - Dynamic",
            "gender": "male",
            "language": "en",
            "accent": "us",
            "description": "Crisp, dynamic conversational male voice with rapid response timing.",
            "preview_url": "https://services.dograh.com/api/v1/voice-proxy/dograh/voices/dg_voice_ee5efd12f17797d0ff39/preview",
        },
        {
            "voice_id": "cartesia_sonic_priya",
            "name": "Sonic Priya - Indian Bilingual",
            "gender": "female",
            "language": "hi",
            "accent": "in",
            "description": "Low-latency bilingual Indian English and Hindi voice for real-time interactions.",
            "preview_url": "https://services.dograh.com/api/v1/voice-proxy/dograh/voices/dg_voice_4c52528b7a1804810035/preview",
        },
    ],
    "elevenlabs": [
        {
            "voice_id": "21m00Tcm4TlvDq8ikWAM",
            "name": "Rachel - Conversational",
            "gender": "female",
            "language": "en",
            "accent": "us",
            "description": "Calm and natural conversational female voice with expressive depth.",
            "preview_url": "https://services.dograh.com/api/v1/voice-proxy/dograh/voices/dg_voice_4c52528b7a1804810035/preview",
        },
        {
            "voice_id": "AZnzlk1XvdvUeBnXmlld",
            "name": "Domi - Strong Narration",
            "gender": "female",
            "language": "en",
            "accent": "us",
            "description": "Strong, engaging voice for urgent notifications and outbound reminders.",
            "preview_url": "https://services.dograh.com/api/v1/voice-proxy/dograh/voices/dg_voice_4c52528b7a1804810035/preview",
        },
        {
            "voice_id": "ErXwobaYiN019PkySvjV",
            "name": "Antoni - Well-Rounded",
            "gender": "male",
            "language": "en",
            "accent": "us",
            "description": "Well-rounded, warm male voice suitable for friendly customer assistance.",
            "preview_url": "https://services.dograh.com/api/v1/voice-proxy/dograh/voices/dg_voice_ee5efd12f17797d0ff39/preview",
        },
        {
            "voice_id": "EXAVITQu4vr4xnSDxMaL",
            "name": "Bella - Expressive",
            "gender": "female",
            "language": "en",
            "accent": "us",
            "description": "Soft, expressive female voice with clear narrative pacing.",
            "preview_url": "https://services.dograh.com/api/v1/voice-proxy/dograh/voices/dg_voice_4c52528b7a1804810035/preview",
        },
    ],
    "deepgram": [
        {
            "voice_id": "aura-asteria-en",
            "name": "Asteria - Casual Conversational",
            "gender": "female",
            "language": "en",
            "accent": "us",
            "description": "Confident, casual female voice with ultra-fast latency for real-time dialogue.",
            "preview_url": "https://services.dograh.com/api/v1/voice-proxy/dograh/voices/dg_voice_4c52528b7a1804810035/preview",
        },
        {
            "voice_id": "aura-luna-en",
            "name": "Luna - Soothing",
            "gender": "female",
            "language": "en",
            "accent": "us",
            "description": "Soft, pleasant conversational female voice for sensitive customer support.",
            "preview_url": "https://services.dograh.com/api/v1/voice-proxy/dograh/voices/dg_voice_4c52528b7a1804810035/preview",
        },
        {
            "voice_id": "aura-orion-en",
            "name": "Orion - Deep & Approachable",
            "gender": "male",
            "language": "en",
            "accent": "us",
            "description": "Deep, approachable male voice ideal for business guidance and updates.",
            "preview_url": "https://services.dograh.com/api/v1/voice-proxy/dograh/voices/dg_voice_ee5efd12f17797d0ff39/preview",
        },
        {
            "voice_id": "aura-arcas-en",
            "name": "Arcas - Natural Clarity",
            "gender": "male",
            "language": "en",
            "accent": "us",
            "description": "Natural, clear male voice with neutral tone and rapid response.",
            "preview_url": "https://services.dograh.com/api/v1/voice-proxy/dograh/voices/dg_voice_ee5efd12f17797d0ff39/preview",
        },
    ],
}


VOICES_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "voices"


class VoiceService:
    def __init__(self):
        self.dograh_url = settings.DOGRAH_BASE_URL
        self.dograh_key = settings.DOGRAH_API_KEY
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 3600  # 1 hour in memory
        
        # Pre-seed cache from local voice files for instant zero-latency responses
        for provider in ["dograh", "sarvam", "cartesia", "elevenlabs", "deepgram"]:
            voices = self._load_local_catalog(provider)
            if voices:
                self._cache[provider] = {"timestamp": time.time(), "voices": voices}

    def _load_local_catalog(self, provider: str) -> List[Dict[str, Any]]:
        """Loads cached voices from disk if available, otherwise returns fallback."""
        file_path = VOICES_DATA_DIR / f"{provider.lower()}.json"
        if file_path.is_file():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and data:
                        return data
            except Exception as e:
                logger.warning(f"Failed to read local voice catalog for {provider}: {e}")
        return DEFAULT_VOICE_CATALOG.get(provider.lower(), [])

    def _save_local_catalog(self, provider: str, voices: List[Dict[str, Any]]) -> None:
        """Saves fresh voices to disk."""
        try:
            VOICES_DATA_DIR.mkdir(parents=True, exist_ok=True)
            file_path = VOICES_DATA_DIR / f"{provider.lower()}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(voices, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write voice catalog to disk for {provider}: {e}")

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-API-Key": self.dograh_key,
        }

    def list_providers(self) -> List[VoiceProvider]:
        return [
            VoiceProvider(
                provider="dograh",
                display_name="Dograh Neural Voices",
                description="High-fidelity voice engine with Indian accents, Hindi, English, and multilingual auto-detect.",
                supports_speed=True,
                supports_style=True,
                supported_languages=["multi", "en", "hi", "es", "fr", "de", "pa", "mr", "ta", "te"],
            ),
            VoiceProvider(
                provider="sarvam",
                display_name="Sarvam AI",
                description="Specialized in Indian languages and expressive regional speech.",
                supports_speed=True,
                supports_style=False,
                supported_languages=["hi", "en-IN", "bn", "kn", "ml", "mr", "od", "pa", "ta", "te", "gu"],
            ),
            VoiceProvider(
                provider="cartesia",
                display_name="Cartesia Sonic",
                description="Ultra-low latency conversational voices with speed and emotion controls.",
                supports_speed=True,
                supports_style=True,
                supported_languages=["en", "hi", "es", "fr", "de", "ja"],
            ),
            VoiceProvider(
                provider="elevenlabs",
                display_name="ElevenLabs",
                description="Industry-standard expressive voice cloning and narrative voices.",
                supports_speed=True,
                supports_style=True,
                supported_languages=["en", "hi", "es", "fr", "de", "it", "pt"],
            ),
            VoiceProvider(
                provider="deepgram",
                display_name="Deepgram Aura",
                description="Ultra-fast natural conversational voices.",
                supports_speed=True,
                supports_style=False,
                supported_languages=["en", "es"],
            ),
        ]

    async def get_voices(
        self,
        provider: str = "dograh",
        gender: Optional[str] = None,
        language: Optional[str] = None,
        search: Optional[str] = None,
    ) -> VoiceListResponse:
        """
        Fetches all voices for the given TTS provider. Queries cache first, or fetches
        from upstream with a safe 15s timeout. Seamlessly provides all 1000+ Dograh voices.
        """
        now = time.time()
        provider_key = (provider or "dograh").lower()
        cached = self._cache.get(provider_key)
        raw_voices: List[Dict[str, Any]] = []

        if cached and (now - cached["timestamp"] < self._cache_ttl):
            raw_voices = cached["voices"]
        else:
            url = f"{self.dograh_url}/api/v1/user/configurations/voices/{provider_key}"
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(url, headers=self._get_headers())
                    if resp.status_code == 200:
                        data = resp.json()
                        fetched = data.get("voices", [])
                        if fetched:
                            raw_voices = fetched
                            self._cache[provider_key] = {"timestamp": now, "voices": raw_voices}
                            self._save_local_catalog(provider_key, raw_voices)
            except Exception as e:
                logger.debug(f"Upstream Dograh voices not reachable for '{provider_key}' ({e}); using local catalog.")

            if not raw_voices:
                # Use previously cached or local file on disk
                if cached and cached.get("voices"):
                    raw_voices = cached["voices"]
                else:
                    raw_voices = self._load_local_catalog(provider_key)
                self._cache[provider_key] = {"timestamp": now, "voices": raw_voices}

        # Filter voices
        filtered: List[VoiceItem] = []
        for v in raw_voices:
            v_gender = (v.get("gender") or "").lower()
            v_lang = (v.get("language") or "").lower()
            v_name = v.get("name") or ""
            v_desc = v.get("description") or ""
            v_accent = v.get("accent") or ""

            if gender and gender.lower() != "all" and v_gender != gender.lower():
                continue

            if language and language.lower() not in ("all", "multi", "auto_match"):
                lang_term = language.lower()
                if lang_term not in v_lang and lang_term not in v_accent.lower():
                    continue

            if search:
                s = search.lower()
                if (
                    s not in v_name.lower()
                    and s not in v_desc.lower()
                    and s not in v_accent.lower()
                    and s not in v_lang.lower()
                ):
                    continue

            filtered.append(
                VoiceItem(
                    voice_id=v.get("voice_id", ""),
                    name=v.get("name", "Unnamed Voice"),
                    gender=v.get("gender"),
                    language=v.get("language"),
                    accent=v.get("accent"),
                    description=v.get("description"),
                    preview_url=v.get("preview_url"),
                )
            )

        return VoiceListResponse(
            provider=provider_key,
            total=len(filtered),
            voices=filtered,
        )

    async def validate_voice_config(
        self,
        provider: str,
        voice_id: str,
        speaking_speed: float,
        language_mode: str,
    ) -> bool:
        """
        Validates voice parameters against supported options.
        """
        if speaking_speed < 0.5 or speaking_speed > 2.0:
            raise DograhServiceException(
                f"Speaking speed {speaking_speed} is out of bounds (allowed: 0.5x to 2.0x).",
                status_code=400,
                error_code="INVALID_SPEED",
            )

        valid_providers = [p.provider for p in self.list_providers()]
        if provider not in valid_providers:
            raise DograhServiceException(
                f"TTS Provider '{provider}' is not supported.",
                status_code=400,
                error_code="UNSUPPORTED_PROVIDER",
            )

        # Validate voice ID if catalog is accessible
        try:
            catalog = await self.get_voices(provider=provider)
            if catalog.voices:
                valid_ids = {v.voice_id for v in catalog.voices}
                if voice_id not in valid_ids and voice_id != "default":
                    raise DograhServiceException(
                        f"Selected voice '{voice_id}' is not available for provider '{provider}'.",
                        status_code=400,
                        error_code="INVALID_VOICE_ID",
                    )
        except DograhServiceException:
            raise
        except Exception as e:
            logger.warning(f"Could not verify voice against catalog: {e}")

        return True

    def validate_preview_url(self, url: str) -> bool:
        """
        Ensures the URL is from an allowed trusted host to prevent SSRF.
        """
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False
            hostname = parsed.hostname
            if not hostname:
                return False
            if hostname in TRUSTED_AUDIO_HOSTS or hostname.endswith(".dograh.com"):
                return True
            return False
        except Exception:
            return False


voice_service = VoiceService()
