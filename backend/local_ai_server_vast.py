"""
Local AI Voice Server (OpenAI-compatible Speaches & Chat API) for Vast.ai GPU
Serves:
1. POST /v1/audio/transcriptions -> Local Whisper Large-v3-Turbo on CUDA
2. POST /v1/audio/speech -> Local Kokoro 82M ONNX TTS
3. POST /v1/chat/completions -> Local Ollama Qwen2.5:7b (proxy)
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
KOKORO_MODEL_PATH = Path("/workspace/models/Kokoro/model.onnx")
KOKORO_VOICES_PATH = Path("/workspace/models/Kokoro/voices-v1.0.bin")

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
    model_id = "openai/whisper-large-v3-turbo"
    processor = AutoProcessor.from_pretrained(model_id)
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_id,
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
except Exception as e:
    logger.error(f"Failed to load Whisper STT: {e}")

# Ollama LLM Configuration
LLM_BACKEND_URL = "http://127.0.0.1:11434/v1"


# -------------------------------------------------------------
# 2. Endpoints
# -------------------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "healthy",
        "stt": "ready" if whisper_pipeline else "offline",
        "tts": "ready" if kokoro_engine else "offline",
        "llm_backend": LLM_BACKEND_URL,
    }


@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "whisper-large-v3-turbo", "object": "model", "owned_by": "local-stt"},
            {"id": "kokoro", "object": "model", "owned_by": "local-tts"},
            {"id": "qwen2.5:7b", "object": "model", "owned_by": "local-llm"},
            {"id": "google/gemma-4-e4b", "object": "model", "owned_by": "local-llm"},
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

        # 3. High-Accuracy Hindi Decoding parameters
        generate_kwargs = {
            "language": "hi",
            "task": "transcribe",
            "temperature": 0.0,
            "no_repeat_ngram_size": 3,
        }
        if hindi_prompt_ids is not None:
            generate_kwargs["prompt_ids"] = hindi_prompt_ids

        result = whisper_pipeline({"raw": data, "sampling_rate": 16000}, generate_kwargs=generate_kwargs)
        text = result.get("text", "").strip()
        logger.info(f"Local Whisper transcription: '{text}'")

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
    if not kokoro_engine:
        raise HTTPException(status_code=503, detail="Local Kokoro TTS engine not loaded")

    try:
        text = req.input.strip()
        if not text:
            raise HTTPException(status_code=400, detail="Input text cannot be empty")

        voice = req.voice or "hm_omega"
        if voice in ("af_heart", "default", "none", ""):
            voice = "hm_omega"
        speed = float(req.speed or 1.18)
        if speed < 1.15:
            speed = 1.18  # ensure snappy, conversational delivery

        # Kokoro language selection
        # hm_omega, hm_psi, hf_alpha, hf_beta are Hindi voices
        if voice.startswith("h") or any(0x0900 <= ord(c) <= 0x097F for c in text[:50]):
            lang = "hi"
        else:
            lang = "en-us"

        # Kokoro synthesis
        samples, sample_rate = kokoro_engine.create(
            text=text,
            voice=voice,
            speed=speed,
            lang=lang,
        )

        if req.response_format == "pcm":
            pcm_data = (np.clip(samples, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes()
            logger.info(f"Local Kokoro synthesized {len(pcm_data)} raw PCM bytes (voice={voice}, speed={speed}, lang={lang}) for: '{text[:40]}...'")
            return Response(content=pcm_data, media_type="audio/pcm")

        out_io = io.BytesIO()
        sf.write(out_io, samples, sample_rate, format="WAV")
        wav_bytes = out_io.getvalue()
        logger.info(f"Local Kokoro synthesized {len(wav_bytes)} WAV bytes (voice={voice}, speed={speed}, lang={lang}) for: '{text[:40]}...'")

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

http_client = httpx.AsyncClient(timeout=60.0)

def clean_speech_text(text: str, is_subsequent: bool = False) -> str:
    """Cleans LLM response text for speech synthesis: strips brackets, leading repeated greetings, formatting, and incomplete trailing sentences."""
    if not text:
        return text
    # 1. Remove brackets / parenthetical text e.g. (मुस्कुराते हुए) or [विनम्रता से]
    text = re.sub(r'\(.*?\)|\[.*?\]', '', text)
    # 2. Strip leading greeting if subsequent turn
    if is_subsequent:
        text = re.sub(r'^(नमस्कार|नमस्ते|प्रणाम|हेलो|हैलो|हाय|सुप्रभात)[\s,।,! जी-]*(जी)?[\s,।,!-]*', '', text).strip()
        text = re.sub(r'^(मैं [^\s]+ बोल रही हूँ[\s,।,!]*|मैं [^\s]+ हूँ[\s,।,!]*)', '', text).strip()
    # 3. Clean markdown formatting
    text = re.sub(r'[*_#`]', '', text).strip()
    # 4. If cut off mid-sentence (no terminal punctuation), trim back to last complete sentence
    m = list(re.finditer(r'[।?!]', text))
    if m:
        last_idx = m[-1].end()
        if len(text) - last_idx > 0:
            text = text[:last_idx].strip()
    return text


# LLM Proxy to Ollama with Turn-Aware Telephony Optimization
@app.post("/v1/chat/completions")
async def chat_completions_proxy(request: Request):
    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)

    stream = False
    is_subsequent = False
    try:
        body_json = json.loads(body)
        messages = body_json.get("messages", [])
        stream = body_json.get("stream", False)

        # Route model to qwen2.5:7b
        body_json["model"] = "qwen2.5:7b"

        # Count caller turns
        user_msgs = [m for m in messages if m.get("role") == "user"]
        is_subsequent = len(user_msgs) > 1

        # FAST DIRECT QUESTIONNAIRE RESOLUTION (< 2ms, bypass slow LLM)
        if FastQuestionnaireOrchestrator:
            direct_reply = FastQuestionnaireOrchestrator.resolve_next_turn(messages)
            if direct_reply:
                direct_reply = clean_speech_text(direct_reply, is_subsequent=is_subsequent)
                created_ts = int(time.time())
                chat_id = f"chatcmpl-fast-q-{int(time.time()*1000)}"
                logger.info(f"Fast Questionnaire Direct Response (LLM Bypassed in <2ms): '{direct_reply}'")

                if stream:
                    async def fast_sse_stream():
                        chunk = {
                            "id": chat_id,
                            "object": "chat.completion.chunk",
                            "created": created_ts,
                            "model": "qwen2.5:7b",
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
                    "model": "qwen2.5:7b",
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

        # Inject turn guidance to strictly forbid repeated greetings on subsequent turns
        if is_subsequent:
            turn_guidance = (
                "यह बातचीत का अगला चरण है। महत्वपूर्ण नियम:\n"
                "1. 'नमस्कार', 'नमस्ते', 'प्रणाम', 'हेलो' या अपना नाम बिल्कुल न बोलें।\n"
                "2. सीधे कॉलर के सवाल का उत्तर केवल 1 या 2 छोटे वाक्यों (15-20 शब्द) में दें।\n"
                "3. केवल शुद्ध देवनागरी हिंदी में बोलें। कोई अंग्रेजी/हिंग्लिश अक्षर न लिखें।\n"
                "4. कोई ब्रैकेट या कोष्ठक जैसे (मुस्कुराते हुए) न लिखें।\n"
                "5. उत्तर के अंत में कॉलर से केवल 1 सरल प्रश्न पूछें।"
            )
            messages.append({"role": "system", "content": turn_guidance})

        # Set tight telephony token limit and temperature for fast (<0.8s), crisp generation
        body_json["max_tokens"] = 95
        body_json["temperature"] = 0.35
        body_json["options"] = {
            "num_predict": 95,
            "temperature": 0.35,
            "top_p": 0.9,
        }

        body_json["messages"] = messages
        body = json.dumps(body_json, ensure_ascii=False).encode("utf-8")
        headers["content-length"] = str(len(body))
    except Exception as parse_err:
        logger.warning(f"Error processing completions request: {parse_err}")

    try:
        if stream:
            req = http_client.build_request(
                "POST",
                f"{LLM_BACKEND_URL}/chat/completions",
                content=body,
                headers=headers,
            )
            resp = await http_client.send(req, stream=True)

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
                                    cleaned = clean_speech_text(initial_buffer, is_subsequent=is_subsequent)
                                    if cleaned and first_chunk_dict:
                                        first_chunk_dict["choices"][0]["delta"]["content"] = cleaned
                                        yield f"data: {json.dumps(first_chunk_dict, ensure_ascii=False)}\n\n".encode("utf-8")
                                yield b"data: [DONE]\n\n"
                                break
                            try:
                                chunk_json = json.loads(raw)
                                delta_text = chunk_json.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if not flushed_initial:
                                    if first_chunk_dict is None:
                                        first_chunk_dict = chunk_json
                                    initial_buffer += delta_text
                                    # Buffer until we have ~18 characters or sentence punctuation
                                    if len(initial_buffer) >= 18 or any(p in initial_buffer for p in ("\n", "।", "?", "!", ",")):
                                        cleaned = clean_speech_text(initial_buffer, is_subsequent=is_subsequent)
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

        resp = await http_client.post(
            f"{LLM_BACKEND_URL}/chat/completions",
            content=body,
            headers=headers,
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
        logger.error(f"Error proxying to LLM backend: {e}")
        raise HTTPException(status_code=502, detail=f"LLM backend proxy error: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10200)
