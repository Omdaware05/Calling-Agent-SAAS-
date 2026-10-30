import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
import httpx

from app.schemas.voice import VoiceListResponse, VoiceProvider
from app.services.voice_service import voice_service
from app.config import settings
from app.dependencies import verify_app_client

logger = logging.getLogger(__name__)

# Voice settings endpoints read/write provider API keys — they previously
# had NO auth and returned FULL keys. Now behind the app key like the rest.
router = APIRouter(prefix="/voice", tags=["Voice Settings"], dependencies=[Depends(verify_app_client)])

LOCAL_AI_URL = "http://127.0.0.1:8002"


@router.get("/providers", response_model=List[VoiceProvider])
async def get_voice_providers():
    """List supported AI TTS voice providers."""
    return voice_service.list_providers()


@router.get("/providers/{provider}/voices", response_model=VoiceListResponse)
async def get_provider_voices(
    provider: str,
    gender: Optional[str] = Query(None, description="female, male, or all"),
    language: Optional[str] = Query(None, description="hi, en, etc."),
    search: Optional[str] = Query(None, description="Search voice name or description"),
):
    """
    Fetch voices from Dograh's verified voice catalog for the given provider.
    """
    return await voice_service.get_voices(
        provider=provider,
        gender=gender,
        language=language,
        search=search,
    )


@router.get("/preview")
async def preview_voice(
    preview_url: str = Query(..., description="Target voice preview audio URL from voice catalog"),
):
    """
    Safely stream voice sample audio from Dograh's audio repository to the web client.
    """
    if not voice_service.validate_preview_url(preview_url):
        raise HTTPException(status_code=400, detail="Invalid or untrusted voice preview URL.")

    async def audio_stream():
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                async with client.stream("GET", preview_url) as resp:
                    if resp.status_code != 200:
                        yield b""
                        return
                    async for chunk in resp.aiter_bytes(chunk_size=4096):
                        yield chunk
        except Exception as e:
            logger.warning(f"Error streaming preview audio: {e}")
            yield b""

    # Determine audio format
    content_type = "audio/mpeg" if preview_url.endswith(".mp3") else "audio/wav"

    return StreamingResponse(
        audio_stream(),
        media_type=content_type,
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=86400",
        },
    )


@router.get("/preview-local/{voice_id}")
async def preview_local_voice(voice_id: str):
    """
    Synthesize and stream a real-time crystal-clear preview audio sample for local Kokoro voices.
    """
    target_voice = "hm_omega" if "omega" in voice_id.lower() or "male" in voice_id.lower() else voice_id
    sample_text = "नमस्ते! मैं आपकी क्या सहायता कर सकता हूँ? आज का मौसम बहुत अच्छा है।"
    tts_payload = {
        "model": "kokoro",
        "input": sample_text,
        "voice": target_voice,
        "speed": 1.05,
        "response_format": "wav"
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{LOCAL_AI_URL}/v1/audio/speech", json=tts_payload)
            if resp.status_code == 200:
                from fastapi import Response
                return Response(
                    content=resp.content,
                    media_type="audio/wav",
                    headers={"Cache-Control": "public, max-age=86400"}
                )
    except Exception as e:
        logger.warning(f"Error generating local preview: {e}")
    raise HTTPException(status_code=502, detail="Local TTS preview engine unavailable")


@router.get("/preview-sarvam/{voice_id}")
async def preview_sarvam_voice(voice_id: str):
    """
    Synthesize and stream a real-time crystal-clear preview audio sample using Sarvam AI TTS (bulbul:v3).
    """
    valid_sarvam_voices = {
        "shubh", "ritu", "aditya", "priya", "rahul", "pooja", "rohan",
        "simran", "kavya", "amit", "dev", "ishita", "ashutosh", "neha"
    }
    speaker = voice_id.lower() if voice_id.lower() in valid_sarvam_voices else getattr(settings, "SARVAM_DEFAULT_VOICE", "shubh")
    sample_text = "नमस्ते! मैं वोक्सोरा एआई कॉलिंग असिस्टेंट हूँ। मैं आज आपकी क्या सहायता कर सकता हूँ?"
    sarvam_key = getattr(settings, "SARVAM_API_KEY", "")

    tts_payload = {
        "inputs": [sample_text],
        "target_language_code": "hi-IN",
        "speaker": speaker,
        "model": "bulbul:v3",
    }
    headers = {
        "api-subscription-key": sarvam_key,
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post("https://api.sarvam.ai/text-to-speech", json=tts_payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                audios = data.get("audios") or []
                if audios:
                    import base64
                    audio_bytes = base64.b64decode(audios[0])
                    from fastapi import Response
                    return Response(
                        content=audio_bytes,
                        media_type="audio/wav",
                        headers={"Cache-Control": "public, max-age=86400"}
                    )
            logger.warning(f"Sarvam preview generation returned {resp.status_code}: {resp.text}")
    except Exception as e:
        logger.warning(f"Error generating Sarvam preview: {e}")

    # Fallback to local audio preview if Sarvam API fails
    return await preview_local_voice("hm_omega")


@router.get("/sarvam/config")
async def get_sarvam_config():
    """
    Returns the current Sarvam AI configuration status.
    """
    key = getattr(settings, "SARVAM_API_KEY", "") or ""
    masked = f"{key[:7]}...{key[-4:]}" if len(key) > 12 else ("Configured" if key else "")
    return {
        "success": True,
        # Never return the raw key — clients use masked_api_key +
        # is_configured for status and POST a new key only to replace it.
        "api_key": "",
        "masked_api_key": masked,
        "default_voice": getattr(settings, "SARVAM_DEFAULT_VOICE", "shubh"),
        "tts_model": getattr(settings, "SARVAM_TTS_MODEL", "bulbul:v3"),
        "stt_model": getattr(settings, "SARVAM_STT_MODEL", "saaras:v3"),
        "llm_model": getattr(settings, "SARVAM_LLM_MODEL", "sarvam-105b"),
        "is_configured": bool(key and key.startswith("sk_")),
        "active": getattr(settings, "ACTIVE_MODEL_MODE", "sarvam") == "sarvam",
    }


@router.post("/sarvam/config")
async def update_sarvam_config(req: dict):
    """
    Updates and persists Sarvam AI credentials and voice settings.
    """
    from app.config import save_sarvam_credentials, save_model_mode

    api_key = (req.get("api_key") or "").strip()
    if not api_key:
        # Empty key = "keep the existing one" (GET no longer returns the
        # raw key, so settings pages save other fields with a blank key).
        api_key = getattr(settings, "SARVAM_API_KEY", "") or ""
    if not api_key:
        raise HTTPException(status_code=400, detail="Sarvam API key cannot be empty")

    default_voice = req.get("default_voice", "shubh")
    save_sarvam_credentials(api_key=api_key, default_voice=default_voice)

    if req.get("set_active"):
        save_model_mode("sarvam")

    return {
        "success": True,
        "message": "Sarvam AI configuration saved and persisted successfully.",
        "default_voice": default_voice,
    }


@router.post("/sarvam/test")
async def test_sarvam_connection(req: Optional[dict] = None):
    """
    Tests live connection to Sarvam AI using the configured or provided API key.
    """
    api_key = (req or {}).get("api_key") or getattr(settings, "SARVAM_API_KEY", "") or ""
    if not api_key:
        raise HTTPException(status_code=400, detail="No Sarvam API key provided to test.")

    test_payload = {
        "inputs": ["नमस्ते, यह वोक्सोरा एआई कॉलिंग एजेंट का कनेक्टिविटी परीक्षण है।"],
        "target_language_code": "hi-IN",
        "speaker": (req or {}).get("default_voice") or getattr(settings, "SARVAM_DEFAULT_VOICE", "shubh"),
        "model": "bulbul:v3",
    }
    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post("https://api.sarvam.ai/text-to-speech", json=test_payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                audios = data.get("audios") or []
                return {
                    "success": True,
                    "connected": True,
                    "status": "CONNECTED",
                    "message": "Sarvam AI API verified! Neural speech synthesis and STT ready for outbound calls.",
                    "model": "bulbul:v3",
                    "speaker": test_payload["speaker"],
                    "request_id": data.get("request_id"),
                    "has_audio": bool(audios),
                }
            error_data = {}
            try:
                error_data = resp.json()
            except Exception:
                pass
            msg = error_data.get("error", {}).get("message") if isinstance(error_data, dict) else resp.text
            return {
                "success": False,
                "connected": False,
                "status": f"HTTP {resp.status_code}",
                "message": f"Sarvam AI returned error: {msg}",
            }
    except Exception as e:
        return {
            "success": False,
            "connected": False,
            "status": "NETWORK_ERROR",
            "message": f"Could not connect to Sarvam AI API: {str(e)}",
        }


# -------------------------------------------------------------
# Transcript API & Google Gemini Configuration Endpoints
# -------------------------------------------------------------
@router.get("/transcript-api/config")
async def get_transcript_api_config():
    """
    Returns current Transcript API and Google Gemini model configuration status.
    """
    import os
    key = getattr(settings, "GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "") or ""
    masked = f"{key[:6]}...{key[-4:]}" if len(key) > 10 else ("Configured" if key else "Not configured")
    model = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
    return {
        "success": True,
        "provider": "google_gemini",
        "provider_name": "Google Gemini AI",
        # Never return the raw key (see /sarvam/config note).
        "api_key": "",
        "masked_api_key": masked,
        "model": model,
        "is_configured": bool(key and len(key) > 8),
        "available_models": [
            {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash (Fast & Recommended)", "latency": "Ultra-Low"},
            {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash (Standard Fast)", "latency": "Low"},
            {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash (Ultra-Fast)", "latency": "Ultra-Low"},
            {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro (High Accuracy)", "latency": "Medium"},
            {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro (Deep Reasoning & Complex Nuances)", "latency": "Low-Medium"},
            {"id": "gemini-2.0-flash-lite", "name": "Gemini 2.0 Flash Lite", "latency": "Ultra-Low"},
        ],
        "stt_engine": getattr(settings, "SARVAM_STT_MODEL", "saaras:v3"),
    }


@router.post("/transcript-api/config")
async def update_transcript_api_config(req: dict):
    """
    Updates and persists Google Gemini / Transcript API credentials in real-time.
    """
    from app.config import save_transcript_api_credentials

    api_key = (req.get("api_key") or "").strip()
    if not api_key:
        # Empty key = keep the existing one (see /sarvam/config).
        import os as _os
        api_key = getattr(settings, "GEMINI_API_KEY", "") or _os.environ.get("GEMINI_API_KEY", "") or ""
    if not api_key:
        raise HTTPException(status_code=400, detail="Gemini / Transcript API key cannot be empty")

    model = (req.get("model") or "gemini-2.5-flash").strip()
    save_transcript_api_credentials(gemini_api_key=api_key, gemini_model=model)

    return {
        "success": True,
        "message": "Transcript API credentials updated and persisted successfully. Active in real-time without restart.",
        "model": model,
    }


@router.post("/transcript-api/test")
async def test_transcript_api_connection(req: Optional[dict] = None):
    """
    Tests live connection to Google Gemini API using configured or provided API key.
    """
    import os
    api_key = (req or {}).get("api_key") or getattr(settings, "GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "") or ""
    if not api_key:
        raise HTTPException(status_code=400, detail="No Gemini API key provided to test.")

    model = (req or {}).get("model") or getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
    m_clean = model if not model.startswith("models/") else model.split("/")[-1]

    t0 = time.time()
    try:
        # First verify models list with the key
        models_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        async with httpx.AsyncClient(timeout=12.0) as client:
            list_resp = await client.get(models_url)
            latency_ms = round((time.time() - t0) * 1000)
            if list_resp.status_code == 200:
                models_data = list_resp.json()
                models_list = [m.get("name", "").replace("models/", "") for m in models_data.get("models", [])]
                return {
                    "success": True,
                    "connected": True,
                    "status": "CONNECTED",
                    "latency_ms": latency_ms,
                    "model": m_clean,
                    "available_models_count": len(models_list),
                    "message": f"Google Gemini API verified successfully! ({latency_ms}ms response time). Live transcript intelligence ready.",
                }
            error_data = {}
            try:
                error_data = list_resp.json()
            except Exception:
                pass
            msg = error_data.get("error", {}).get("message") if isinstance(error_data, dict) else list_resp.text
            return {
                "success": False,
                "connected": False,
                "status": f"HTTP {list_resp.status_code}",
                "message": f"Google API error: {msg}",
            }
    except Exception as e:
        return {
            "success": False,
            "connected": False,
            "status": "NETWORK_ERROR",
            "message": f"Could not connect to Google Gemini API: {str(e)}",
        }



# -------------------------------------------------------------
# Local Voice Testing (Zero Internet / Laptop Offline Mode)
# -------------------------------------------------------------
from fastapi import File, Form, UploadFile, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import base64
import json
import time
from app.database import get_db
from app.models.agent import Agent


@router.get("/test-status")
async def get_local_test_status():
    """Checks whether the AI Voice engine (Sarvam AI or Local) is ready for direct testing."""
    # First check if local engine is running
    try:
        async with httpx.AsyncClient(timeout=0.6) as client:
            resp = await client.get(f"{LOCAL_AI_URL}/health")
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "ready": True,
                    "engine": "local",
                    "stt": data.get("stt", "whisper"),
                    "tts": data.get("tts", "kokoro"),
                    "llm_provider": data.get("llm_provider", "local"),
                    "llm_backend": data.get("llm_backend", "gemma-4"),
                }
    except Exception:
        pass

    # If Sarvam AI is configured (default active engine)
    sarvam_key = getattr(settings, "SARVAM_API_KEY", "") or ""
    if sarvam_key:
        return {
            "ready": True,
            "engine": "sarvam",
            "stt": getattr(settings, "SARVAM_STT_MODEL", "saaras:v3"),
            "tts": getattr(settings, "SARVAM_TTS_MODEL", "bulbul:v3"),
            "llm_provider": "sarvam",
            "llm_backend": getattr(settings, "SARVAM_LLM_MODEL", "sarvam-105b-conversations"),
        }

    return {
        "ready": False,
        "stt": "offline",
        "tts": "offline",
        "llm_provider": "unknown",
        "error": "No voice engine ready. Configure SARVAM_API_KEY in backend/.env",
    }


_shared_client: Optional[httpx.AsyncClient] = None
_tts_cache: dict[str, str] = {}


def _get_shared_client() -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        limits = httpx.Limits(max_keepalive_connections=40, max_connections=60, keepalive_expiry=180.0)
        _shared_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=2.5), limits=limits)
    return _shared_client


async def _synthesize_voice_audio(text: str, agent: Agent) -> tuple[str, float]:
    """Synthesizes voice audio (WAV) and returns (base64_wav, latency_ms)."""
    t0 = time.time()
    clean_text = text.strip()
    if not clean_text:
        return "", 0.0

    # 1. Try local Kokoro TTS if local engine is explicitly enabled
    if getattr(settings, "VOICE_ENGINE", "sarvam") == "local":
        try:
            voice = agent.voice_id or "hm_omega"
            if voice == "hm_omega" or (agent.voice_gender or "").lower() == "male" or "omega" in (agent.voice_name or "").lower():
                voice = "hm_omega"
            elif not voice.startswith(("hm_", "hf_", "am_", "af_")):
                voice = "hf_alpha" if "female" in (agent.voice_gender or "").lower() else "hm_omega"

            tts_payload = {
                "model": "kokoro",
                "input": clean_text,
                "voice": voice,
                "speed": float(agent.speaking_speed or 1.05),
                "response_format": "wav",
            }
            client = _get_shared_client()
            resp = await client.post(f"{LOCAL_AI_URL}/v1/audio/speech", json=tts_payload)
            if resp.status_code == 200:
                tts_ms = (time.time() - t0) * 1000
                return base64.b64encode(resp.content).decode("utf-8"), tts_ms
        except Exception:
            pass

    # 2. Use Sarvam AI Bulbul TTS (Native Low-Latency with warm connection and caching)
    sarvam_key = getattr(settings, "SARVAM_API_KEY", "") or ""
    if sarvam_key:
        valid_sarvam_voices = {
            "shubh", "ritu", "aditya", "priya", "rahul", "pooja", "rohan",
            "simran", "kavya", "amit", "dev", "ishita", "ashutosh", "neha"
        }
        v_name = (agent.voice_id or agent.voice_name or "").lower()
        if v_name in valid_sarvam_voices:
            speaker = v_name
        elif "female" in (agent.voice_gender or "").lower():
            speaker = "ritu"
        elif "male" in (agent.voice_gender or "").lower():
            speaker = "shubh"
        else:
            speaker = getattr(settings, "SARVAM_DEFAULT_VOICE", "shubh")

        cache_key = f"{speaker}:{clean_text}"
        if cache_key in _tts_cache:
            return _tts_cache[cache_key], round((time.time() - t0) * 1000, 1)

        payload = {
            "inputs": [clean_text],
            "target_language_code": "hi-IN",
            "speaker": speaker,
            "model": getattr(settings, "SARVAM_TTS_MODEL", "bulbul:v3"),
            "speech_sample_rate": 8000,
            "enable_preprocessing": False,
        }
        headers = {
            "api-subscription-key": sarvam_key,
            "Content-Type": "application/json",
        }
        try:
            client = _get_shared_client()
            resp = await client.post("https://api.sarvam.ai/text-to-speech", json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                audios = data.get("audios") or []
                if audios:
                    tts_ms = (time.time() - t0) * 1000
                    if len(_tts_cache) < 300:
                        _tts_cache[cache_key] = audios[0]
                    return audios[0], tts_ms
        except Exception as e:
            logger.warning(f"Sarvam test turn TTS synthesis error: {e}")

    return "", (time.time() - t0) * 1000


@router.post("/test-greeting")
async def get_test_greeting(
    request: dict,
    db: AsyncSession = Depends(get_db),
):
    """Generates initial greeting audio for the selected agent with real-time TTS."""
    agent_id = request.get("agent_id")
    if not agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required")

    stmt = select(Agent).where(Agent.id == agent_id)
    res = await db.execute(stmt)
    agent = res.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    greeting_text = (
        agent.greeting_message
        or f"नमस्ते! मैं {agent.company_name or 'कस्टमर सपोर्ट'} से {agent.name} बोल रहा हूँ। बताइए, आपकी क्या सहायता कर सकता हूँ?"
    )

    t0 = time.time()
    audio_base64, tts_ms = await _synthesize_voice_audio(greeting_text, agent)
    total_ms = (time.time() - t0) * 1000

    return {
        "agent_name": agent.name,
        "greeting_text": greeting_text,
        "audio_base64": audio_base64,
        "metrics": {
            "tts_ms": round(tts_ms, 1),
            "total_ms": round(total_ms, 1),
        },
    }


@router.post("/test-turn")
async def process_test_turn(
    agent_id: str = Form(...),
    text: Optional[str] = Form(None),
    audio: Optional[UploadFile] = File(None),
    history: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Executes a complete full cycle (STT -> LLM -> TTS) with minimal latency.
    Supports native Sarvam AI engine with local fallback.
    Returns transcription, assistant reply, audio bytes (base64), and exact latency metrics.
    """
    stmt = select(Agent).where(Agent.id == agent_id)
    res = await db.execute(stmt)
    agent = res.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    start_total = time.time()
    user_text = ""
    stt_ms = 0.0

    # 1. STT (if audio file provided from browser mic)
    if audio:
        t_stt = time.time()
        audio_bytes = await audio.read()

        # If local engine enabled, try local whisper first
        if getattr(settings, "VOICE_ENGINE", "sarvam") == "local":
            try:
                files = {"file": ("mic.wav", audio_bytes, "audio/wav")}
                data = {"model": "whisper-large-v3-turbo", "language": "hi"}
                async with httpx.AsyncClient(timeout=1.0) as client:
                    stt_resp = await client.post(f"{LOCAL_AI_URL}/v1/audio/transcriptions", files=files, data=data)
                    if stt_resp.status_code == 200:
                        stt_json = stt_resp.json()
                        user_text = stt_json.get("text", "").strip()
            except Exception:
                pass

        # Otherwise use Sarvam Saaras STT
        if not user_text and getattr(settings, "SARVAM_API_KEY", ""):
            try:
                files = {"file": (audio.filename or "mic.wav", audio_bytes, audio.content_type or "audio/wav")}
                data = {
                    "model": getattr(settings, "SARVAM_STT_MODEL", "saaras:v3"),
                    "language_code": "hi-IN",
                }
                headers = {"api-subscription-key": settings.SARVAM_API_KEY}
                client = _get_shared_client()
                resp = await client.post("https://api.sarvam.ai/speech-to-text", headers=headers, files=files, data=data)
                if resp.status_code == 200:
                    user_text = resp.json().get("transcript", "").strip()
            except Exception as e:
                logger.error(f"Sarvam STT test turn error: {e}")

        stt_ms = (time.time() - t_stt) * 1000
    elif text:
        user_text = text.strip()

    if not user_text:
        return {
            "user_text": "",
            "agent_reply": "माफ़ कीजिए, कोई आवाज़ सुनाई नहीं दी। कृपया दोबारा बोलें।",
            "audio_base64": "",
            "metrics": {"stt_ms": round(stt_ms, 1), "total_ms": round((time.time() - start_total) * 1000, 1)},
        }

    # 2. Build LLM Conversation Prompt
    messages = []
    system_prompt = (
        agent.system_prompt
        or f"आप '{agent.company_name or 'फास्टनेट ब्रॉडबैंड'}' के कस्टमर सपोर्ट एग्जीक्यूटिव '{agent.name}' हैं।\n"
           f"{agent.instructions or ''}\n"
           f"नियम:\n"
           f"1. सीधे 1-2 बहुत छोटे वाक्यों (12-18 शब्द) में स्वाभाविक बोलचाल की हिंदी में उत्तर दें।\n"
           f"2. सामान्य तकनीकी शब्द (इंटरनेट, कनेक्शन, स्लो, डिवाइस, चेक, नंबर, एरिया, नेटवर्क, हॉटस्पॉट) देवनागरी में लिखें।\n"
           f"3. कोई किताबी शुद्ध हिंदी न बोलें और कोई ब्रैकेट जैसे (मुस्कुराते हुए) न लिखें।\n"
           f"4. उत्तर के अंत में कॉलर से केवल 1 सरल प्रश्न पूछें।"
    )

    # Add past turns
    if history:
        try:
            past_turns = json.loads(history)
            if isinstance(past_turns, list):
                messages.extend(past_turns)
        except Exception:
            pass

    messages.append({"role": "user", "content": user_text})

    # 3. LLM Generation
    t_llm = time.time()
    llm_ttfb_ms = None
    agent_reply = ""

    # Try local LLM if configured
    if getattr(settings, "VOICE_ENGINE", "sarvam") == "local":
        try:
            llm_payload = {
                "model": "google/gemma-4-e4b",
                "messages": [{"role": "system", "content": system_prompt}] + messages,
                "stream": True,
                "max_tokens": 80,
                "temperature": 0.3,
            }
            client = _get_shared_client()
            async with client.stream("POST", f"{LOCAL_AI_URL}/v1/chat/completions", json=llm_payload) as resp:
                if resp.status_code == 200:
                    async for line in resp.aiter_lines():
                        line_str = line.strip()
                        if line_str.startswith("data: ") and line_str != "data: [DONE]":
                            try:
                                chunk = json.loads(line_str[6:])
                                delta = chunk["choices"][0].get("delta", {}).get("content", "")
                                if delta:
                                    if llm_ttfb_ms is None:
                                        llm_ttfb_ms = (time.time() - t_llm) * 1000
                                    agent_reply += delta
                            except Exception:
                                pass
        except Exception:
            pass

    # If local not used or empty, use Sarvam LLM
    if not agent_reply and getattr(settings, "SARVAM_API_KEY", ""):
        try:
            sarvam_llm_payload = {
                "model": getattr(settings, "SARVAM_LLM_MODEL", "sarvam-105b-conversations"),
                "messages": [{"role": "system", "content": system_prompt}] + messages,
                "temperature": 0.2,
                "max_tokens": 45,
                "stream": True,
            }
            sarvam_headers = {
                "api-subscription-key": settings.SARVAM_API_KEY,
                "Content-Type": "application/json",
            }
            client = _get_shared_client()
            async with client.stream("POST", "https://api.sarvam.ai/v1/chat/completions", json=sarvam_llm_payload, headers=sarvam_headers) as resp:
                async with client.stream("POST", "https://api.sarvam.ai/v1/chat/completions", json=sarvam_llm_payload, headers=sarvam_headers) as resp:
                    if resp.status_code == 200:
                        async for line in resp.aiter_lines():
                            line_str = line.strip()
                            if line_str.startswith("data: ") and line_str != "data: [DONE]":
                                try:
                                    delta_json = json.loads(line_str[6:])
                                    delta_text = delta_json["choices"][0].get("delta", {}).get("content", "")
                                    if delta_text:
                                        if llm_ttfb_ms is None:
                                            llm_ttfb_ms = (time.time() - t_llm) * 1000
                                        agent_reply += delta_text
                                except Exception:
                                    pass
        except Exception as e:
            logger.error(f"Sarvam LLM test turn error: {e}")

    llm_total_ms = (time.time() - t_llm) * 1000
    if llm_ttfb_ms is None:
        llm_ttfb_ms = llm_total_ms

    agent_reply = agent_reply.strip()
    if not agent_reply:
        agent_reply = "जी, समझ गया। क्या आप इसके बारे में और कुछ जानना चाहते हैं?"

    # 4. TTS Synthesis
    audio_base64, tts_ms = await _synthesize_voice_audio(agent_reply, agent)
    total_ms = (time.time() - start_total) * 1000

    return {
        "user_text": user_text,
        "agent_reply": agent_reply,
        "audio_base64": audio_base64,
        "metrics": {
            "stt_ms": round(stt_ms, 1),
            "llm_ttfb_ms": round(llm_ttfb_ms, 1),
            "llm_total_ms": round(llm_total_ms, 1),
            "tts_ms": round(tts_ms, 1),
            "total_ms": round(total_ms, 1),
        },
    }

