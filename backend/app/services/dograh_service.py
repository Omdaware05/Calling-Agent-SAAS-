import logging
import uuid
from typing import Any, Dict, Optional, Tuple
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class DograhServiceException(Exception):
    def __init__(self, message: str, status_code: int = 500, error_code: str = "DOGRAH_ERROR"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code


class DograhService:
    def __init__(self):
        self.base_url = settings.DOGRAH_BASE_URL.rstrip("/")
        self.api_key = settings.DOGRAH_API_KEY

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    async def check_health(self) -> Dict[str, Any]:
        """Check if Dograh API is reachable and healthy."""
        url = f"{self.base_url}/api/v1/health"
        try:
            fast_timeout = httpx.Timeout(1.5, connect=0.5)
            async with httpx.AsyncClient(timeout=fast_timeout) as client:
                resp = await client.get(url, headers=self._get_headers())
                if resp.status_code == 200:
                    return {"reachable": True, "status": "ok", "detail": resp.json()}
                return {"reachable": True, "status": "degraded", "code": resp.status_code}
        except Exception as e:
            logger.warning(f"Dograh health check failed: {e}")
            return {"reachable": False, "status": "unavailable", "error": str(e)}

    async def initiate_call(
        self,
        phone_number: str,
        trigger_path: Optional[str] = None,
        workflow_id: Optional[int] = None,
        initial_context: Optional[Dict[str, Any]] = None,
        telephony_configuration_id: Optional[int] = None,
        from_phone_number_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Initiate an outbound call via Dograh using the verified endpoints:
        Primary: POST /api/v1/public/agent/{trigger_path}
        Fallback: POST /api/v1/telephony/initiate-call (if workflow_id provided without trigger_path)
        """
        context = initial_context or {}

        if trigger_path:
            url = f"{self.base_url}/api/v1/public/agent/{trigger_path}"
            payload: Dict[str, Any] = {
                "phone_number": phone_number,
                "initial_context": context,
            }
            if telephony_configuration_id is not None:
                payload["telephony_configuration_id"] = telephony_configuration_id
            if from_phone_number_id is not None:
                payload["from_phone_number_id"] = from_phone_number_id
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:

                    resp = await client.post(url, json=payload, headers=self._get_headers())
                    if resp.status_code in (200, 201):
                        return resp.json()
                    error_msg = resp.text
                    try:
                        err_json = resp.json()
                        if isinstance(err_json, dict) and "detail" in err_json:
                            error_msg = str(err_json["detail"])
                    except Exception:
                        pass
                    logger.error(f"Dograh public agent call failed: {resp.status_code} {error_msg}")
                    raise DograhServiceException(
                        message=error_msg,
                        status_code=resp.status_code,
                        error_code="DOGRAH_CALL_INITIATION_FAILED",
                    )
            except httpx.RequestError as e:
                logger.error(f"Dograh network error during call initiation: {e}")
                raise DograhServiceException(
                    message="Dograh server is currently unreachable",
                    status_code=503,
                    error_code="DOGRAH_UNAVAILABLE",
                )

        elif workflow_id:
            url = f"{self.base_url}/api/v1/telephony/initiate-call"
            payload = {
                "workflow_id": workflow_id,
                "phone_number": phone_number,
            }
            if telephony_configuration_id is not None:
                payload["telephony_configuration_id"] = telephony_configuration_id
            if from_phone_number_id is not None:
                payload["from_phone_number_id"] = from_phone_number_id
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:

                    resp = await client.post(url, json=payload, headers=self._get_headers())
                    if resp.status_code in (200, 201):
                        data = resp.json()
                        # Extract run name from message e.g. "Call initiated successfully with run name WR-TEL-OUT-..."
                        return {
                            "status": "success",
                            "workflow_run_name": data.get("message", "").split("run name ")[-1] if "run name " in data.get("message", "") else "WR-TEL-OUT",
                            "raw": data,
                        }
                    error_msg = resp.text
                    try:
                        err_json = resp.json()
                        if isinstance(err_json, dict) and "detail" in err_json:
                            error_msg = str(err_json["detail"])
                    except Exception:
                        pass
                    logger.error(f"Dograh telephony call failed: {resp.status_code} {error_msg}")
                    raise DograhServiceException(
                        message=error_msg,
                        status_code=resp.status_code,
                        error_code="DOGRAH_CALL_INITIATION_FAILED",
                    )
            except httpx.RequestError as e:
                logger.error(f"Dograh network error: {e}")
                raise DograhServiceException(
                    message="Dograh server is currently unreachable",
                    status_code=503,
                    error_code="DOGRAH_UNAVAILABLE",
                )

        raise DograhServiceException(
            message="Cannot initiate call: neither trigger_path nor workflow_id is configured for agent",
            status_code=400,
            error_code="AGENT_CONFIGURATION_INCOMPLETE",
        )

    async def get_run_details(self, workflow_id: int, run_id: int) -> Dict[str, Any]:
        """
        Fetch details of a workflow run:
        GET /api/v1/workflow/{workflow_id}/runs/{run_id}
        """
        url = f"{self.base_url}/api/v1/workflow/{workflow_id}/runs/{run_id}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self._get_headers())
                if resp.status_code == 200:
                    return resp.json()
                logger.warning(f"Failed to fetch run details for run {run_id}: {resp.status_code}")
                return {}
        except Exception as e:
            logger.warning(f"Error fetching run details from Dograh: {e}")
            return {}

    async def terminate_call(self, run_id: int, workflow_id: Optional[int] = None) -> bool:
        """
        Terminate / stop a live workflow run in Dograh.
        Tries two known Dograh endpoints:
          1. POST /api/v1/run/{run_id}/stop
          2. POST /api/v1/workflow/{workflow_id}/runs/{run_id}/stop  (if workflow_id provided)
        Returns True if the call was successfully terminated.
        """
        candidates: list[str] = [
            f"{self.base_url}/api/v1/run/{run_id}/stop",
        ]
        if workflow_id:
            candidates.append(f"{self.base_url}/api/v1/workflow/{workflow_id}/runs/{run_id}/stop")

        async with httpx.AsyncClient(timeout=8.0) as client:
            for url in candidates:
                try:
                    resp = await client.post(url, headers=self._get_headers())
                    if resp.status_code in (200, 201, 204):
                        logger.info(f"Dograh run {run_id} terminated via {url}")
                        return True
                    logger.warning(f"Dograh terminate attempt {url} returned {resp.status_code}: {resp.text[:200]}")
                except Exception as e:
                    logger.warning(f"Dograh terminate attempt {url} failed: {e}")

        logger.warning(f"Could not terminate Dograh run {run_id} — marking as completed in DB only.")
        return False

    def build_workflow_definition(
        self,
        name: str,
        purpose: str,
        instructions: str,
        allowed_topics: list[str],
        restricted_topics: list[str],
        behavior_rules: list[str],
        trigger_path: str,
        voice_style: str = "Friendly + Professional + Conversational",
        language_mode: str = "auto_match",
        company_name: Optional[str] = None,
        company_description: Optional[str] = None,
        greeting_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Builds a full, valid Dograh ReactFlowDTO graph implementing the complete natural
        conversational flow for calling agent with pre-defined company identity and greeting.
        """
        comp_name = company_name or "ARB SoftTech"
        comp_desc = company_description or purpose or "providing professional consultation and assistance"

        # Dynamic LLM Persona & Rules based on Role and System Instructions
        topics_str = ", ".join(allowed_topics) if allowed_topics else f"Inquiries and topics related to {comp_name} and {comp_desc}"
        restricted_str = ", ".join(restricted_topics) if restricted_topics else "Illegal activities, abuse, and unsupported claims"
        rules_list = "\n".join(f"- {r}" for r in behavior_rules) if behavior_rules else "- Speak naturally, warmly, and politely.\n- Answer every question immediately in 1-2 concise sentences."

        custom_instructions = instructions.strip() if instructions else f"Assist the caller effectively regarding {comp_name} and {comp_desc}."

        global_prompt = (
            f"AGENT IDENTITY & ROLE:\n"
            f"- Agent Name: '{name}', AI Voice Assistant\n"
            f"- Company / Organization: '{comp_name}'\n"
            f"- Purpose: {comp_desc}\n"
            f"- Tone: {voice_style}\n\n"
            f"SYSTEM INSTRUCTIONS & KNOWLEDGE:\n"
            f"{custom_instructions}\n\n"
            f"CONVERSATIONAL CALLING RULES:\n"
            f"1. ONE-TIME GREETING: Speak 'नमस्कार जी...' ONLY ON TURN 1 when call connects. NEVER repeat greeting or your name in any subsequent turn.\n"
            f"2. PURE SPOKEN HINDI (DEVANAGARI): Speak in natural conversational Hindi. Never use English script (Roman letters) or difficult bookish words.\n"
            f"3. ULTRA-SHORT REPLIES: Keep every response strictly to 1 or 2 short sentences (12-20 words max). Never monologue.\n"
            f"4. ONE QUESTION AT A TIME: Ask exactly ONE clear question at the end to keep the phone conversation flowing.\n"
            f"5. NO STAGE DIRECTIONS: Never write asterisks, markdown, or bracketed text like (मुस्कुराते हुए).\n"
            f"6. REFUSAL / DECLINE: If caller says 'नहीं', 'ना', 'नहीं चाहिए', 'रहने दो', immediately say 'जी ठीक है, आपका बहुत धन्यवाद!' and conclude.\n\n"
            f"ALLOWED TOPICS:\n{topics_str}\n\n"
            f"RESTRICTED TOPICS:\n{restricted_str}\n\n"
            f"BEHAVIOR RULES:\n{rules_list}"
        )

        # Ensure an instant opening greeting so the bot speaks immediately on call answer (0s LLM delay)
        effective_greeting = (greeting_message or "").strip()
        if not effective_greeting:
            desc_lower = (comp_desc or "").lower()
            if any(k in desc_lower for k in ["admission", "student", "course", "college", "school", "education"]):
                effective_greeting = f"नमस्कार जी, मैं {comp_name} से {name} बात कर रहा हूँ। क्या आप एडमिशन और कोर्स की जानकारी चाहते हैं?"
            elif any(k in desc_lower for k in ["broadband", "internet", "wifi", "network"]):
                effective_greeting = f"नमस्ते! मैं {comp_name} से {name} बोल रहा हूँ। बताइए, क्या आपके इंटरनेट कनेक्शन में कोई समस्या आ रही है?"
            elif any(k in desc_lower for k in ["agri", "kisan", "crop", "farming"]):
                effective_greeting = f"नमस्कार किसान भाई, मैं {comp_name} से {name} बात कर रहा हूँ। क्या मैं आपकी फसलों के बारे में जानकारी ले सकता हूँ?"
            else:
                effective_greeting = f"नमस्कार जी, मैं {comp_name} से {name} बात कर रहा हूँ। क्या मैं आपसे दो मिनट बात कर सकता हूँ?"

        opening_turn_instruction = (
            f"- TURN 1: The opening greeting has already been delivered to the caller: '{effective_greeting}'\n"
            f"- WHEN CALLER SPEAKS: If caller says 'Hello', 'हेलो', 'हॅलो', 'हाँ', 'जी', 'yes', or asks 'कौन?', acknowledge warmly in ONE short sentence (e.g. 'जी, मैं {comp_name} से {name} बात कर रहा हूँ') and ask your first relevant question.\n"
            f"- ULTRA-FAST SPOKEN HINDI: Keep every response strictly under 15-20 words in natural conversational Hindi. Never monologue."
        )

        start_prompt = (
            f"You are '{name}' on a live phone call representing '{comp_name}'.\n"
            f"Purpose: {comp_desc}\n\n"
            f"SYSTEM INSTRUCTIONS & KNOWLEDGE:\n{custom_instructions}\n\n"
            f"CALL OPENING GUIDELINES:\n"
            f"{opening_turn_instruction}\n"
            f"- TURN > 1: DO NOT repeat greeting. Answer caller directly in 1-2 short sentences (15-20 words max), and ask the next relevant question from your instructions or questionnaire.\n"
            f"- If caller declines or is not interested, say: 'जी ठीक है, आपका बहुत धन्यवाद!' and close."
        )

        agent_prompt = (
            f"You are '{name}' from '{comp_name}'.\n"
            f"Purpose: {comp_desc}\n\n"
            f"SYSTEM INSTRUCTIONS & KNOWLEDGE:\n{custom_instructions}\n\n"
            f"RULES:\n"
            f"- If caller says 'Hello', 'हेलो' or asks 'कौन बोल रहे हैं?', immediately confirm: 'जी, मैं {comp_name} से {name} बोल रहा हूँ।' and ask your next question.\n"
            f"- NEVER repeat the full opening greeting again.\n"
            f"- Exactly 1-2 short spoken Hindi sentences (under 20 words).\n"
            f"- Follow your instructions/questionnaire step by step and ask only 1 simple question at a time.\n"
            f"- If caller says no or is not interested, thank them politely and end."
        )

        # Unique node IDs
        global_node_id = f"node_global_{uuid.uuid4().hex[:6]}"
        start_node_id = f"node_start_{uuid.uuid4().hex[:6]}"
        agent_node_id = f"node_agent_{uuid.uuid4().hex[:6]}"
        end_interested_id = f"node_end_interested_{uuid.uuid4().hex[:6]}"
        end_not_interested_id = f"node_end_not_interested_{uuid.uuid4().hex[:6]}"
        trigger_node_id = f"node_trigger_{uuid.uuid4().hex[:6]}"
        webhook_node_id = f"node_webhook_{uuid.uuid4().hex[:6]}"

        backend_url = getattr(settings, "BACKEND_PUBLIC_URL", "http://localhost:8001")
        if "localhost:8001" in backend_url or "127.0.0.1:8001" in backend_url:
            backend_url = backend_url.replace("localhost:8001", "host.docker.internal:8001").replace("127.0.0.1:8001", "host.docker.internal:8001")
        callback_url = f"{backend_url}/api/webhooks/dograh"

        nodes = [
            # 1. Global Persona Node
            {
                "id": global_node_id,
                "type": "globalNode",
                "position": {"x": 250, "y": 0},
                "data": {
                    "name": "Global Rules & Persona",
                    "prompt": global_prompt,
                },
            },
            # 2. Trigger Node
            {
                "id": trigger_node_id,
                "type": "trigger",
                "position": {"x": 0, "y": 100},
                "data": {
                    "name": "API Trigger",
                    "enabled": True,
                    "trigger_path": trigger_path,
                },
            },
            # 3. Start Call Node (Instant on-connect greeting via TTS speak frame)
            {
                "id": start_node_id,
                "type": "startCall",
                "position": {"x": 250, "y": 150},
                "data": {
                    "name": "Call Opening & Consultation",
                    "greeting_type": "text",
                    "greeting": effective_greeting,
                    "prompt": start_prompt,
                    "allow_interrupt": True,
                    "add_global_prompt": True,
                },
            },
            # 4. Agent Node (Advanced Counseling)
            {
                "id": agent_node_id,
                "type": "agentNode",
                "position": {"x": 250, "y": 320},
                "data": {
                    "name": "Advanced Counseling",
                    "prompt": agent_prompt,
                    "allow_interrupt": True,
                    "add_global_prompt": True,
                },
            },
            # 5. End Call Node - Interested
            {
                "id": end_interested_id,
                "type": "endCall",
                "position": {"x": 100, "y": 500},
                "data": {
                    "name": "Completed / Interested",
                    "prompt": "Call completed successfully. The caller interest was recorded and natural closing delivered.",
                    "add_global_prompt": False,
                },
            },
            # 6. End Call Node - Not Interested
            {
                "id": end_not_interested_id,
                "type": "endCall",
                "position": {"x": 400, "y": 500},
                "data": {
                    "name": "Not Interested / Polite Close",
                    "prompt": "Call completed politely. The caller was not interested or busy.",
                    "add_global_prompt": False,
                },
            },
            # 7. Webhook Node
            {
                "id": webhook_node_id,
                "type": "webhook",
                "position": {"x": 250, "y": 640},
                "data": {
                    "name": "Report to Backend",
                    "enabled": True,
                    "http_method": "POST",
                    "endpoint_url": callback_url,
                    "payload_template": {
                        "call_id": "{{initial_context.app_call_id}}",
                        "workflow_run_id": "{{workflow_run_id}}",
                        "status": "{{gathered_context.call_status}}",
                        "disposition": "{{gathered_context.call_disposition}}",
                        "duration": "{{cost_info.call_duration_seconds}}",
                        "transcript_url": "{{transcript_url}}",
                        "recording_url": "{{recording_url}}",
                        "user_recording_url": "{{user_recording_url}}",
                        "bot_recording_url": "{{bot_recording_url}}",
                    },
                },
            },
        ]

        edges = [
            # StartCall -> Continue Conversation to AgentNode on any response, greeting, or question
            {
                "id": f"edge_{start_node_id}_{agent_node_id}",
                "source": start_node_id,
                "target": agent_node_id,
                "data": {
                    "label": "continue_conversation",
                    "condition": "Caller responds, says hello, 'हेलो', 'हॅलो', 'हाँ', 'जी', 'yes', asks a question, or continues the conversation.",
                },
            },
            # StartCall -> End Not Interested (When caller declined or is busy)
            {
                "id": f"edge_{start_node_id}_{end_not_interested_id}",
                "source": start_node_id,
                "target": end_not_interested_id,
                "data": {
                    "label": "end_call_declined",
                    "condition": "Caller declines, says no, 'नहीं', 'ना', 'नाही', 'नहीं जानना', 'नहीं चाहिए', 'बस', 'रहने दो', is not interested, or polite rejection close spoken.",
                },
            },
            # StartCall -> End Interested (When caller interest is understood and closing delivered)
            {
                "id": f"edge_{start_node_id}_{end_interested_id}",
                "source": start_node_id,
                "target": end_interested_id,
                "data": {
                    "label": "end_call_interested",
                    "condition": f"Caller objective regarding {name} is satisfied, interest is noted, or polite closing delivered.",
                },
            },
            # AgentNode -> End Interested
            {
                "id": f"edge_{agent_node_id}_{end_interested_id}",
                "source": agent_node_id,
                "target": end_interested_id,
                "data": {
                    "label": "agent_end_interested",
                    "condition": f"Consultation regarding {name} is complete and caller interest recorded.",
                },
            },
            # AgentNode -> End Not Interested
            {
                "id": f"edge_{agent_node_id}_{end_not_interested_id}",
                "source": agent_node_id,
                "target": end_not_interested_id,
                "data": {
                    "label": "agent_end_declined",
                    "condition": "Caller declines, says no, 'नहीं', 'ना', 'नहीं जानना', 'नहीं चाहिए', 'रहने दो', 'नाही', or is not interested.",
                },
            },
        ]

        return {
            "name": name,
            "workflow_definition": {
                "nodes": nodes,
                "edges": edges,
            },
        }

    async def sync_workflow_to_dograh(
        self,
        name: str,
        purpose: str,
        instructions: str,
        allowed_topics: list[str],
        restricted_topics: list[str],
        behavior_rules: list[str],
        existing_workflow_id: Optional[int] = None,
        existing_trigger_path: Optional[str] = None,
        voice_id: str = "hm_omega",
        speaking_speed: float = 1.05,
        language_mode: str = "auto_match",
        primary_language: str = "multi",
        voice_style: str = "Friendly + Professional + Conversational",
        tts_provider: str = "dograh",
        company_name: Optional[str] = None,
        company_description: Optional[str] = None,
        greeting_message: Optional[str] = None,
    ) -> Tuple[Optional[int], Optional[str]]:
        """
        Creates or updates the workflow in Dograh with voice configuration override.
        Returns (dograh_workflow_id, dograh_trigger_path).
        """
        trigger_path = existing_trigger_path or f"agent-{uuid.uuid4().hex[:12]}"
        workflow_payload = self.build_workflow_definition(
            name=name,
            purpose=purpose,
            instructions=instructions,
            allowed_topics=allowed_topics,
            restricted_topics=restricted_topics,
            behavior_rules=behavior_rules,
            trigger_path=trigger_path,
            voice_style=voice_style,
            language_mode=language_mode,
            company_name=company_name,
            company_description=company_description,
            greeting_message=greeting_message,
        )

        # Attach voice/model configuration override based on ACTIVE_MODEL_MODE or agent voice provider
        active_mode = getattr(settings, "ACTIVE_MODEL_MODE", "sarvam") or "sarvam"
        is_sarvam = active_mode == "sarvam" or (tts_provider or "").lower() == "sarvam"

        if is_sarvam:
            sarvam_key = getattr(settings, "SARVAM_API_KEY", "") or "sk_nipv0trp_igNxLgrUcrqEGnKbEk1pSViR"
            valid_sarvam_voices = {
                "shubh", "ritu", "aditya", "priya", "rahul", "pooja", "rohan",
                "simran", "kavya", "amit", "dev", "ishita", "ashutosh", "neha"
            }
            target_voice = voice_id.lower() if voice_id and voice_id.lower() in valid_sarvam_voices else getattr(settings, "SARVAM_DEFAULT_VOICE", "shubh")
            stt_lang = "hi-IN" if primary_language in ("hi", "Hindi", "hi-IN") else "unknown"

            model_override = {
                "version": 2,
                "mode": "byok",
                "byok": {
                    "mode": "pipeline",
                    "pipeline": {
                        "llm": {
                            "provider": "sarvam",
                            "model": getattr(settings, "SARVAM_LLM_MODEL", "sarvam-105b"),
                            "api_key": sarvam_key,
                            "temperature": 0.5,
                        },
                        "stt": {
                            "provider": "sarvam",
                            "model": getattr(settings, "SARVAM_STT_MODEL", "saaras:v3"),
                            "language": stt_lang,
                            "api_key": sarvam_key,
                        },
                        "tts": {
                            "provider": "sarvam",
                            "model": getattr(settings, "SARVAM_TTS_MODEL", "bulbul:v3"),
                            "voice": target_voice,
                            "language": "hi-IN",
                            "speed": float(speaking_speed or 1.0),
                            "api_key": sarvam_key,
                        },
                    },
                },
            }
        elif active_mode == "local":
            ai_base_url = getattr(settings, "LOCAL_AI_BASE_URL", "http://host.docker.internal:8002/v1")
            model_override = {
                "version": 2,
                "mode": "byok",
                "byok": {
                    "mode": "pipeline",
                    "pipeline": {
                        "llm": {
                            "provider": "openai",
                            "model": "google/gemma-4-e4b",
                            "base_url": ai_base_url,
                            "api_key": "not-needed",
                        },
                        "stt": {
                            "provider": "speaches",
                            "model": "whisper-large-v3-turbo",
                            "base_url": ai_base_url,
                            "language": "hi",
                            "api_key": "none",
                        },
                        "tts": {
                            "provider": "speaches",
                            "model": "kokoro",
                            "base_url": ai_base_url,
                            "voice": voice_id or "hm_omega",
                            "speed": float(speaking_speed or 1.05),
                            "api_key": "none",
                        },
                    },
                },
            }
        else:
            stt_lang = "multi" if language_mode in ("auto_match", "hinglish") else primary_language
            model_override = {
                "version": 2,
                "mode": "dograh",
                "dograh": {
                    "api_key": settings.DOGRAH_MPS_KEY,
                    "voice": voice_id,
                    "speed": float(speaking_speed),
                    "language": stt_lang,
                },
            }
        workflow_payload["workflow_configurations"] = {
            "model_configuration_v2_override": model_override,
            "turn_start_strategy": "default",
            "turn_start_min_words": 1,
            "turn_stop_strategy": "transcription",
            "smart_turn_stop_secs": 0.8,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                if existing_workflow_id:
                    # Update workflow definition
                    update_url = f"{self.base_url}/api/v1/workflow/{existing_workflow_id}"
                    resp = await client.put(update_url, json=workflow_payload, headers=self._get_headers())
                    if resp.status_code in (200, 204):
                        # Publish draft
                        await client.post(f"{self.base_url}/api/v1/workflow/{existing_workflow_id}/publish", headers=self._get_headers())
                        return existing_workflow_id, trigger_path
                    logger.warning(f"Workflow update failed ({resp.status_code}), will attempt create: {resp.text}")

                # Create workflow from definition
                create_url = f"{self.base_url}/api/v1/workflow/create/definition"
                resp = await client.post(create_url, json=workflow_payload, headers=self._get_headers())
                if resp.status_code in (200, 201):
                    created_data = resp.json()
                    new_workflow_id = created_data.get("id")
                    if new_workflow_id:
                        # Apply workflow configurations (BYOK / local models override)
                        try:
                            await client.put(f"{self.base_url}/api/v1/workflow/{new_workflow_id}", json=workflow_payload, headers=self._get_headers())
                        except Exception as put_err:
                            logger.warning(f"Workflow configuration update warning: {put_err}")
                    return new_workflow_id, trigger_path

                logger.warning(f"Could not sync workflow to Dograh: {resp.status_code} {resp.text}")
                return None, trigger_path

        except Exception as e:
            logger.warning(f"Could not connect to Dograh to sync workflow: {e}")
            return None, trigger_path


dograh_service = DograhService()
