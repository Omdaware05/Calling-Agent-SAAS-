"""
Local AI Voice Server (OpenAI-compatible Speaches & Chat API) for Laptop
Serves:
1. POST /v1/audio/transcriptions -> Local Whisper Large-v3-Turbo on CUDA
2. POST /v1/audio/speech -> Local Kokoro 82M ONNX TTS
3. POST /v1/chat/completions -> Local LM Studio Gemma 4 E4B (proxy)
4. GET /health -> Service health check
Runs on port 8002.
"""

import io
import os
import sys
import json
import time
import re
import logging
from pathlib import Path
from typing import Optional, List

import numpy as np
import soundfile as sf
import torch
import httpx
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("local_ai_server")

app = FastAPI(title="Local AI Voice Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# 1. Models Initialization
# -------------------------------------------------------------
DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"
logger.info(f"Target compute device: {DEVICE}")

# Kokoro TTS
KOKORO_MODEL_PATH = Path(r"D:\Model\TTS\Kokoro\models\model.onnx")
KOKORO_VOICES_PATH = Path(r"D:\Model\TTS\Kokoro\voices-v1.0.bin")

kokoro_engine = None
try:
    from kokoro_onnx import Kokoro
    if KOKORO_MODEL_PATH.exists() and KOKORO_VOICES_PATH.exists():
        kokoro_engine = Kokoro(
            model_path=str(KOKORO_MODEL_PATH),
            voices_path=str(KOKORO_VOICES_PATH),
        )
        logger.info("Kokoro ONNX TTS initialized successfully.")
    else:
        logger.warning(f"Kokoro model files missing at {KOKORO_MODEL_PATH}")
except Exception as e:
    logger.error(f"Failed to load Kokoro TTS: {e}")

# Whisper STT
whisper_pipeline = None
hindi_prompt_ids = None
try:
    import torchaudio
    from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
    snapshot_dir = Path.home() / ".cache" / "huggingface" / "hub" / "models--openai--whisper-large-v3-turbo" / "snapshots" / "41f01f3fe87f28c78e2fbf8b568835947dd65ed9"
    if snapshot_dir.exists():
        processor = AutoProcessor.from_pretrained(str(snapshot_dir))
        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            str(snapshot_dir),
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            low_cpu_mem_usage=True,
        ).to(DEVICE)
        whisper_pipeline = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device=0 if torch.cuda.is_available() else -1,
        )
        try:
            hindi_prompt_ids = torch.tensor(
                processor.get_prompt_ids("यह एक भारतीय किसान और कृषि सलाहकार के बीच फोन पर बातचीत है। खेती, गेहूं, सोयाबीन, चना, कपास, खाद, बीज, एकड़, जमीन, जानकारी, नमस्ते, हाँ, नहीं, नहीं जानना, नहीं चाहिए, ना, नाही, बस, रहने दो, धन्यवाद।")
            ).to(DEVICE)
            logger.info("Hindi context prompt IDs precomputed for high-accuracy telephony STT.")
        except Exception as pe:
            logger.warning(f"Could not precompute prompt IDs: {pe}")
        logger.info("Whisper Large-v3-Turbo initialized successfully on CUDA.")
        try:
            logger.info("Pre-warming Whisper CUDA engine...")
            dummy_pcm = np.zeros(16000, dtype=np.float32)
            whisper_pipeline({"raw": dummy_pcm, "sampling_rate": 16000}, generate_kwargs={"language": "hi", "task": "transcribe"})
            logger.info("Whisper CUDA pre-warm complete.")
        except Exception as we:
            logger.warning(f"Whisper pre-warm note: {we}")
    else:
        logger.warning(f"Whisper snapshot missing at {snapshot_dir}")
except Exception as e:
    logger.error(f"Failed to load Whisper STT: {e}")

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

# LLM Providers Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
GEMINI_API_URL = os.getenv("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://127.0.0.1:1234/v1")
logger.info(f"Active LLM Provider: {LLM_PROVIDER.upper()} (Gemini Model: {GEMINI_MODEL}, LM Studio: {LM_STUDIO_URL})")


# -------------------------------------------------------------
# 2. Endpoints
# -------------------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "healthy",
        "stt": "ready" if whisper_pipeline else "offline",
        "tts": "ready" if kokoro_engine else "offline",
        "llm_provider": LLM_PROVIDER,
        "llm_backend": GEMINI_API_URL if LLM_PROVIDER == "gemini" else LM_STUDIO_URL,
    }


@app.get("/v1/models")
def list_models():
    active_model = GEMINI_MODEL if LLM_PROVIDER == "gemini" else "google/gemma-4-e4b"
    return {
        "object": "list",
        "data": [
            {"id": "whisper-large-v3-turbo", "object": "model", "owned_by": "local-stt"},
            {"id": "kokoro", "object": "model", "owned_by": "local-tts"},
            {"id": active_model, "object": "model", "owned_by": LLM_PROVIDER},
            {"id": "google/gemma-4-e4b", "object": "model", "owned_by": "local-lmstudio"},
        ]
    }


# Speech to Text (Speaches / OpenAI compatible)
@app.post("/v1/audio/transcriptions")
async def transcribe_audio(
    file: UploadFile = File(...),
    model: Optional[str] = Form("whisper-large-v3-turbo"),
    language: Optional[str] = Form(None),
    response_format: Optional[str] = Form("json"),
):
    if not whisper_pipeline:
        raise HTTPException(status_code=503, detail="Local Whisper STT model not loaded")

    try:
        content = await file.read()
        audio_io = io.BytesIO(content)
        data, sample_rate = sf.read(audio_io)

        # Convert to mono if stereo
        if len(data.shape) > 1:
            data = data.mean(axis=1)

        # 1. Telephony Resampling (8kHz -> 16kHz)
        if sample_rate != 16000:
            tensor_data = torch.from_numpy(data).float()
            resampled_tensor = torchaudio.functional.resample(tensor_data, sample_rate, 16000)
            data = resampled_tensor.numpy()
            sample_rate = 16000

        # 2. Volume Normalization (boost weak telephone microphones)
        max_val = np.max(np.abs(data))
        if max_val > 0.005:
            data = (data / max_val) * 0.95

        data = data.astype(np.float32)

        t_start = time.time()
        # 3. High-Accuracy Hindi Decoding parameters
        generate_kwargs = {
            "language": "hi",
            "task": "transcribe",
            "temperature": 0.0,
        }
        if hindi_prompt_ids is not None:
            generate_kwargs["prompt_ids"] = hindi_prompt_ids

        result = whisper_pipeline({"raw": data, "sampling_rate": 16000}, generate_kwargs=generate_kwargs)
        text = result.get("text", "").strip()
        stt_dur = round((time.time() - t_start) * 1000)
        logger.info(f"Local Whisper transcription in {stt_dur}ms: '{text}'")

        if response_format == "text":
            return Response(content=text, media_type="text/plain")
        return {"text": text}

    except Exception as e:
        logger.error(f"Error in transcription: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Text to Speech (Speaches / OpenAI compatible)
class TTSRequest(BaseModel):
    model: str = "kokoro"
    input: str
    voice: Optional[str] = "hm_omega"
    speed: Optional[float] = 1.18
    response_format: Optional[str] = "wav"


@app.post("/v1/audio/speech")
async def generate_speech(req: TTSRequest):
    text = req.input.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Input text cannot be empty")

    voice = req.voice or "hm_omega"
    if any(f in voice.lower() for f in ["aarti", "shreya", "female", "hf_"]):
        voice = "hf_alpha"
    elif "omega" in voice.lower() or "psi" in voice.lower():
        voice = "hm_omega"

    speed = float(req.speed if req.speed is not None else 1.05)
    speed = max(0.6, min(speed, 2.0))

    if voice.startswith("h") or any(0x0900 <= ord(c) <= 0x097F for c in text[:50]):
        lang = "hi"
    else:
        lang = "en-us"

    # 1. Primary High-Speed Accelerated Docker Kokoro CUDA (350ms vs 5000ms CPU)
    docker_url = os.getenv("KOKORO_DOCKER_URL", "http://localhost:8880")
    docker_key = os.getenv("KOKORO_DOCKER_KEY", "kokoro-87c72016c99d8bdcb42345e147e24d656f3e3436057cd963")
    try:
        t0 = time.time()
        headers = {
            "Authorization": f"Bearer {docker_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "tts-1",
            "input": text,
            "voice": voice,
            "speed": speed,
            "response_format": "wav",
        }
        r = await http_client.post(f"{docker_url}/v1/audio/speech", headers=headers, json=payload, timeout=4.0)
        if r.status_code == 200:
            audio_bytes = r.content
            dur = round((time.time() - t0) * 1000)
            if req.response_format == "pcm":
                data, sr = sf.read(io.BytesIO(audio_bytes))
                pcm_data = (np.clip(data, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes()
                logger.info(f"Kokoro Docker CUDA synthesized {len(pcm_data)} PCM bytes in {dur}ms (voice={voice}, speed={speed}) for: '{text[:35]}...'")
                return Response(content=pcm_data, media_type="audio/pcm")
            logger.info(f"Kokoro Docker CUDA synthesized {len(audio_bytes)} WAV bytes in {dur}ms (voice={voice}, speed={speed}) for: '{text[:35]}...'")
            return Response(content=audio_bytes, media_type="audio/wav")
    except Exception as docker_err:
        logger.warning(f"Kokoro Docker unavailable ({docker_err}), falling back to local ONNX engine...")

    # 2. Fallback to Local Kokoro ONNX
    if not kokoro_engine:
        raise HTTPException(status_code=503, detail="Local Kokoro TTS engine not loaded")

    try:
        t0 = time.time()
        samples, sample_rate = kokoro_engine.create(
            text=text,
            voice=voice,
            speed=speed,
            lang=lang,
        )
        dur = round((time.time() - t0) * 1000)

        if req.response_format == "pcm":
            pcm_data = (np.clip(samples, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes()
            logger.info(f"Local Kokoro synthesized {len(pcm_data)} raw PCM bytes in {dur}ms (voice={voice}) for: '{text[:35]}...'")
            return Response(content=pcm_data, media_type="audio/pcm")

        out_io = io.BytesIO()
        sf.write(out_io, samples, sample_rate, format="WAV")
        wav_bytes = out_io.getvalue()
        logger.info(f"Local Kokoro synthesized {len(wav_bytes)} WAV bytes in {dur}ms (voice={voice}) for: '{text[:35]}...'")

        return Response(content=wav_bytes, media_type="audio/wav")

    except Exception as e:
        logger.error(f"Error in speech synthesis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


try:
    from app.services.questionnaire_runtime_service import FastQuestionnaireOrchestrator
except ImportError:
    try:
        from questionnaire_runtime_service import FastQuestionnaireOrchestrator
    except ImportError:
        FastQuestionnaireOrchestrator = None

http_client = httpx.AsyncClient(timeout=httpx.Timeout(6.0, connect=3.0))

def clean_speech_text(text: str, is_subsequent: bool = False, is_final: bool = True) -> str:
    """Cleans LLM response text for speech synthesis: strips brackets, leading repeated greetings, formatting, and incomplete trailing sentences."""
    if not text:
        return text
    # 1. Remove brackets / parenthetical text e.g. (मुस्कुराते हुए) or [विनम्रता से]
    text = re.sub(r'\(.*?\)|\[.*?\]', '', text)
    # 2. Clean markdown formatting and normalize spaces first so regexes match clean text
    text = re.sub(r'[*_#`]', '', text).strip()
    text = re.sub(r'[ \t]+', ' ', text).strip()
    # 3. Strip leading greeting if subsequent turn (supports both male and female agents)
    if is_subsequent:
        text = re.sub(r'^(नमस्कार|नमस्ते|प्रणाम|हेलो|हैलो|हाय|सुप्रभात)[\s,।,! जी-]*(जी)?[\s,।,!-]*', '', text).strip()
        text = re.sub(r'^(?:मैं\s+)?[^\s]+\s+बोल\s+(?:रहा|रही)\s+हूँ[\s,।,!-]*', '', text).strip()
        text = re.sub(r'^(?:मैं\s+)?[^\s]+\s+हूँ[\s,।,!-]*', '', text).strip()
    # 4. If cut off mid-sentence on final text, trim back to last complete sentence
    if is_final:
        m = list(re.finditer(r'[।?!.]', text))
        if m:
            last_idx = m[-1].end()
            trailing = text[last_idx:].strip()
            if trailing and len(trailing) < 15:
                text = text[:last_idx].strip()
    return text


# LLM Proxy (Gemini or LM Studio) with Turn-Aware Telephony Optimization
@app.post("/v1/chat/completions")
async def chat_completions_proxy(request: Request):
    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)

    stream = False
    is_subsequent = False
    target_url = f"{LM_STUDIO_URL}/chat/completions"

    try:
        body_json = json.loads(body)
        messages = body_json.get("messages", [])
        stream = body_json.get("stream", False)

        # Count caller turns
        user_msgs = [m for m in messages if m.get("role") == "user"]
        is_subsequent = len(user_msgs) > 1

        # FAST DIRECT QUESTIONNAIRE RESOLUTION (< 2ms, bypass slow LLM)
        if FastQuestionnaireOrchestrator:
            direct_reply = FastQuestionnaireOrchestrator.resolve_next_turn(messages)
            if direct_reply:
                direct_reply = clean_speech_text(direct_reply, is_subsequent=is_subsequent, is_final=True)
                created_ts = int(time.time())
                chat_id = f"chatcmpl-fast-q-{int(time.time()*1000)}"
                logger.info(f"Fast Questionnaire Direct Response (LLM Bypassed in <2ms): '{direct_reply}'")

                active_model = GEMINI_MODEL if LLM_PROVIDER == "gemini" else "google/gemma-4-e4b"
                if stream:
                    async def fast_sse_stream():
                        chunk = {
                            "id": chat_id,
                            "object": "chat.completion.chunk",
                            "created": created_ts,
                            "model": active_model,
                            "choices": [{
                                "index": 0,
                                "delta": {"role": "assistant", "content": direct_reply},
                                "finish_reason": "stop"
                            }]
                        }
                        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                        yield "data: [DONE]\n\n"

                    return StreamingResponse(fast_sse_stream(), media_type="text/event-stream")

                return JSONResponse(content={
                    "id": chat_id,
                    "object": "chat.completion",
                    "created": created_ts,
                    "model": active_model,
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": direct_reply
                        },
                        "finish_reason": "stop"
                    }],
                    "usage": {
                        "prompt_tokens": len(str(messages)) // 4,
                        "completion_tokens": len(direct_reply) // 4,
                        "total_tokens": (len(str(messages)) + len(direct_reply)) // 4
                    }
                })

        # Inject turn guidance to strictly enforce natural, ultra-concise conversational telephony Hindi
        telephony_guidance = (
            "यह एक लाइव फोन कॉल है। कॉलर प्रतीक्षा कर रहा है। अत्यंत अनिवार्य नियम:\n"
            "1. आपका उत्तर बहुत संक्षिप्त होना चाहिए: केवल 1 या 2 छोटे वाक्यों (अधिकतम 15-20 शब्द) में उत्तर दें। कभी भी लंबा पैराग्राफ न बोलें।\n"
            "2. प्राकृतिक, सहज और आम बोलचाल की भाषा बोलें। सामान्य शब्द जैसे 'इंटरनेट', 'चेक', 'स्लो', 'कनेक्शन', 'एरिया' आदि को देवनागरी में प्रयोग करें।\n"
            "3. कोई कोष्ठक या ब्रैकेट जैसे (मुस्कुराते हुए) न लिखें।"
        )
        if is_subsequent:
            telephony_guidance += "\n4. बातचीत के बीच में 'नमस्ते', 'नमस्कार', 'हेलो' या अपना नाम दोहराना सख्त मना है।"
        messages.append({"role": "system", "content": telephony_guidance})

        # Ensure Gemini receives at least one user turn (Gemini OpenAI endpoint rejects requests with only system messages)
        if LLM_PROVIDER == "gemini":
            non_system = [m for m in messages if m.get("role") in ("user", "assistant")]
            if not non_system:
                messages.append({"role": "user", "content": "नमस्ते, कॉल कनेक्ट हो गया है। कृपया अपना संक्षिप्त अभिवादन और परिचय दीजिए।"})

        # Clean any messages with null or empty content
        for m in messages:
            if not m.get("content"):
                m["content"] = " "

        body_json["messages"] = messages

        # Route to Gemini or LM Studio
        if LLM_PROVIDER == "gemini":
            target_url = f"{GEMINI_API_URL}/chat/completions"
            body_json["model"] = GEMINI_MODEL
            body_json["max_tokens"] = 65
            body_json["temperature"] = 0.3
            body_json.pop("reasoning_effort", None)
            body_json.pop("thinking", None)
            body_json.pop("reasoning", None)
            headers["authorization"] = f"Bearer {GEMINI_API_KEY}"
            headers["Authorization"] = f"Bearer {GEMINI_API_KEY}"
            headers["content-type"] = "application/json"
        else:
            target_url = f"{LM_STUDIO_URL}/chat/completions"
            body_json["model"] = "google/gemma-4-e4b"
            body_json["reasoning_effort"] = "none"
            body_json["thinking"] = False
            body_json["reasoning"] = False
            body_json["enable_thinking"] = False
            body_json["max_tokens"] = 90
            body_json["temperature"] = 0.3


    except Exception as parse_err:
        logger.warning(f"Error processing completions request: {parse_err}")

    async def attempt_call(url: str, body_payload: dict, req_headers: dict):
        clean_hdrs = {k: v for k, v in req_headers.items() if k.lower() not in ("content-length", "host")}
        clean_hdrs["content-type"] = "application/json"
        raw_bytes = json.dumps(body_payload, ensure_ascii=False).encode("utf-8")
        if stream:
            req = http_client.build_request("POST", url, content=raw_bytes, headers=clean_hdrs)
            return await http_client.send(req, stream=True)
        return await http_client.post(url, content=raw_bytes, headers=clean_hdrs)

    resp = None
    try:
        resp = await attempt_call(target_url, body_json, headers)
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}")
    except Exception as primary_err:
        logger.warning(f"Primary LLM ({target_url}) error/timeout ({primary_err}). Failing over to backup provider...")
        # Determine fallback provider
        if target_url.startswith(GEMINI_API_URL):
            backup_url = f"{LM_STUDIO_URL}/chat/completions"
            backup_body = dict(body_json)
            backup_body["model"] = "google/gemma-4-e4b"
            backup_body["max_tokens"] = 90
            backup_body["temperature"] = 0.3
            backup_headers = {"content-type": "application/json"}
        else:
            backup_url = f"{GEMINI_API_URL}/chat/completions"
            backup_body = dict(body_json)
            backup_body["model"] = GEMINI_MODEL
            backup_body["max_tokens"] = 180
            backup_body["temperature"] = 0.3
            backup_headers = {
                "authorization": f"Bearer {GEMINI_API_KEY}",
                "Authorization": f"Bearer {GEMINI_API_KEY}",
                "content-type": "application/json",
            }
        try:
            resp = await attempt_call(backup_url, backup_body, backup_headers)
            target_url = backup_url
        except Exception as backup_err:
            logger.error(f"Both primary and backup LLM backends failed: {backup_err}")
            raise HTTPException(status_code=502, detail=f"LLM proxy error: {primary_err} -> {backup_err}")

    try:
        if stream:
            if resp.status_code != 200:
                err_content = await resp.aread()
                return Response(content=err_content, status_code=resp.status_code, media_type="application/json")

            async def filtered_sse_generator():
                initial_buffer = ""
                flushed_initial = False
                first_chunk_dict = None

                try:
                    async for chunk_bytes in resp.aiter_lines():
                        line = chunk_bytes.strip()
                        if not line:
                            continue
                        if line.startswith("data: "):
                            raw = line[6:]
                            if raw == "[DONE]":
                                if not flushed_initial and initial_buffer:
                                    cleaned = clean_speech_text(initial_buffer, is_subsequent=is_subsequent, is_final=False)
                                    if cleaned and first_chunk_dict:
                                        first_chunk_dict["choices"][0]["delta"]["content"] = cleaned
                                        yield f"data: {json.dumps(first_chunk_dict, ensure_ascii=False)}\n\n".encode("utf-8")
                                yield b"data: [DONE]\n\n"
                                break
                            try:
                                chunk_json = json.loads(raw)
                                choices = chunk_json.get("choices", [])
                                if not choices:
                                    yield f"{line}\n\n".encode("utf-8")
                                    continue
                                delta_text = choices[0].get("delta", {}).get("content", "")
                                if not delta_text:
                                    yield f"{line}\n\n".encode("utf-8")
                                    continue
                                if not flushed_initial:
                                    if first_chunk_dict is None:
                                        first_chunk_dict = chunk_json
                                    initial_buffer += delta_text
                                    if len(initial_buffer) >= 15 or any(p in initial_buffer for p in ("\n", "।", "?", "!", ",")):
                                        cleaned = clean_speech_text(initial_buffer, is_subsequent=is_subsequent, is_final=False)
                                        flushed_initial = True
                                        if cleaned:
                                            chunk_json["choices"][0]["delta"]["content"] = cleaned
                                            yield f"data: {json.dumps(chunk_json, ensure_ascii=False)}\n\n".encode("utf-8")
                                    continue
                                else:
                                    yield f"{line}\n\n".encode("utf-8")
                            except Exception:
                                yield f"{line}\n\n".encode("utf-8")
                finally:
                    await resp.aclose()

            return StreamingResponse(
                filtered_sse_generator(),
                status_code=resp.status_code,
                headers={"content-type": "text/event-stream"},
                media_type="text/event-stream",
            )

        try:
            resp_data = resp.json()
            if "choices" in resp_data and len(resp_data["choices"]) > 0:
                msg = resp_data["choices"][0].get("message", {})
                content = msg.get("content", "")
                if content:
                    msg["content"] = clean_speech_text(content, is_subsequent=is_subsequent)
                    resp_data["choices"][0]["message"] = msg
                    return JSONResponse(content=resp_data, status_code=resp.status_code)
        except Exception:
            pass

        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=dict(resp.headers),
            media_type=resp.headers.get("content-type"),
        )
    except Exception as e:
        logger.error(f"Error handling LLM response ({target_url}): {e}")
        raise HTTPException(status_code=502, detail=f"LLM proxy error: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
