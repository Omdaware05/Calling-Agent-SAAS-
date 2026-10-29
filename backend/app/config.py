from pathlib import Path
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_backend_env = Path(__file__).resolve().parent.parent / ".env"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RECORDINGS_DIR = DATA_DIR / "recordings"
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"
INTELLIGENCE_DIR = DATA_DIR / "intelligence"
DATABASE_DIR = DATA_DIR / "database"
LOGS_DIR = DATA_DIR / "logs"

# Ensure all central data directories exist
for _d in [DATA_DIR, RECORDINGS_DIR, TRANSCRIPTS_DIR, INTELLIGENCE_DIR, DATABASE_DIR, LOGS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    # Central Data Directory Paths
    PROJECT_ROOT_PATH: str = str(PROJECT_ROOT)
    DATA_DIR_PATH: str = str(DATA_DIR)
    RECORDINGS_DIR_PATH: str = str(RECORDINGS_DIR)
    TRANSCRIPTS_DIR_PATH: str = str(TRANSCRIPTS_DIR)
    INTELLIGENCE_DIR_PATH: str = str(INTELLIGENCE_DIR)
    DATABASE_DIR_PATH: str = str(DATABASE_DIR)
    LOGS_DIR_PATH: str = str(LOGS_DIR)

    # Dograh API Settings
    DOGRAH_BASE_URL: str = "http://localhost:8000"
    DOGRAH_API_KEY: str = "sk-placeholder-key-for-local-dev"
    DOGRAH_MPS_KEY: str = "oss_sk_yV7obDwIeYaTeOrcllPfnJAplrcduHwe"

    # Custom Backend Server Settings
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8001
    ENVIRONMENT: str = "development"

    # Database Settings
    # SQLite (default for local dev, no setup needed):
    #   DATABASE_URL=sqlite+aiosqlite:///./calling_agent.db
    # PostgreSQL (production):
    #   DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/voxora
    DATABASE_URL: str = "sqlite+aiosqlite:///./calling_agent.db"

    # Redis Settings (optional — used for async job queuing)
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: str = ""

    # MinIO / S3 Storage Settings (optional — used for call recordings)
    S3_ENDPOINT_URL: str = ""          # e.g. http://localhost:9000 for MinIO
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = "voxora-recordings"
    S3_REGION: str = "us-east-1"
    S3_USE_SSL: bool = False

    # Security & Optional Webhook Secret
    APP_API_KEY: str = ""
    DOGRAH_WEBHOOK_SECRET: str = ""
    CORS_ORIGINS: Union[List[str], str] = ["*"]

    # Public callback URL for Dograh post-call webhooks if configured
    BACKEND_PUBLIC_URL: str = "http://localhost:8001"

    # Optional Vobiz Telephony Credentials from Environment
    VOBIZ_AUTH_ID: str = ""
    VOBIZ_AUTH_TOKEN: str = ""
    VOBIZ_FROM_NUMBER: str = ""
    VOBIZ_APPLICATION_ID: str = ""

    # Optional Twilio Telephony Credentials from Environment
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # BYOK (Bring Your Own Key / Local Model) Paths Configuration
    BYOK_MODELS_DIR: str = "D:\\Model"
    BYOK_LLM_MODEL_PATH: str = "D:\\Model\\LLM\\Google\\lmstudio-community\\gemma-4-E4B-it-GGUF\\gemma-4-E4B-it-Q4_K_M.gguf"
    BYOK_STT_MODEL_PATH: str = "D:\\Model\\STT\\STT"
    BYOK_TTS_MODEL_PATH: str = "D:\\Model\\TTS\\Kokoro"

    # Active AI Model Mode: "local" (100% Local GPU), "sarvam" (Sarvam AI), or "api" (Dograh Cloud API)
    ACTIVE_MODEL_MODE: str = "sarvam"
    LOCAL_AI_BASE_URL: str = "http://host.docker.internal:8002/v1"

    # Sarvam AI Voice & Model Settings
    VOICE_ENGINE: str = "sarvam"  # "sarvam" (native direct VoBiz engine) or "dograh"
    SARVAM_API_KEY: str = ""
    SARVAM_DEFAULT_VOICE: str = "shubh"
    SARVAM_TTS_MODEL: str = "bulbul:v3"
    SARVAM_STT_MODEL: str = "saaras:v3"
    SARVAM_LLM_MODEL: str = "sarvam-105b-conversations"

    # Gemini API Settings for Lead Interest Intelligence
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"


    @field_validator("DOGRAH_BASE_URL", mode="before")
    @classmethod
    def resolve_docker_dograh_url(cls, v):
        import os
        if (os.environ.get("IN_DOCKER") == "true" or os.path.exists("/.dockerenv")) and isinstance(v, str):
            if "localhost:8000" in v or "127.0.0.1:8000" in v:
                return v.replace("localhost:8000", "api:8000").replace("127.0.0.1:8000", "api:8000")
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=(_backend_env, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


def save_model_mode(mode: str) -> None:
    """
    Updates runtime settings and writes ACTIVE_MODEL_MODE to .env file for persistence.
    Supports "local", "sarvam", and "api".
    """
    import logging
    from pathlib import Path

    raw = (mode or "").lower()
    if raw in ("sarvam", "sarvamai", "indic"):
        normalized_mode = "sarvam"
    elif raw in ("api", "cloud"):
        normalized_mode = "api"
    else:
        normalized_mode = "local"
    settings.ACTIVE_MODEL_MODE = normalized_mode

    # Find the backend .env file
    possible_paths = [
        Path(".env"),
        Path(__file__).resolve().parent.parent / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
    ]
    env_file = None
    for p in possible_paths:
        if p.exists() and p.is_file():
            env_file = p
            break
    if not env_file:
        env_file = Path(__file__).resolve().parent.parent / ".env"

    lines = []
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            lines = []

    new_lines = []
    found = False
    for line in lines:
        if line.strip().startswith("ACTIVE_MODEL_MODE="):
            new_lines.append(f"ACTIVE_MODEL_MODE={normalized_mode}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines.append("\n")
        new_lines.append(f"ACTIVE_MODEL_MODE={normalized_mode}\n")

    try:
        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception as e:
        logging.getLogger(__name__).warning(f"Could not persist ACTIVE_MODEL_MODE to {env_file}: {e}")


def save_vobiz_credentials(auth_id: str, auth_token: str, from_number: str) -> None:
    """
    Updates runtime settings and writes VOBIZ credentials to .env file for persistence.
    """
    import logging
    from pathlib import Path

    settings.VOBIZ_AUTH_ID = auth_id
    settings.VOBIZ_AUTH_TOKEN = auth_token
    settings.VOBIZ_FROM_NUMBER = from_number

    # Find the backend .env file
    possible_paths = [
        Path(".env"),
        Path(__file__).resolve().parent.parent / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
    ]
    env_file = None
    for p in possible_paths:
        if p.exists() and p.is_file():
            env_file = p
            break
    if not env_file:
        env_file = Path(__file__).resolve().parent.parent / ".env"

    updates = {
        "VOBIZ_AUTH_ID": auth_id,
        "VOBIZ_AUTH_TOKEN": auth_token,
        "VOBIZ_FROM_NUMBER": from_number,
    }

    lines = []
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            lines = []

    new_lines = []
    seen_keys = set()
    for line in lines:
        matched_key = None
        for k in updates:
            if line.strip().startswith(f"{k}="):
                matched_key = k
                break
        if matched_key:
            new_lines.append(f"{matched_key}={updates[matched_key]}\n")
            seen_keys.add(matched_key)
        else:
            new_lines.append(line)

    unseen = [k for k in updates if k not in seen_keys]
    if unseen:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines.append("\n")
        new_lines.append("\n# VoBiz Telephony Credentials\n")
        for k in unseen:
            new_lines.append(f"{k}={updates[k]}\n")

    try:
        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception as e:
        logging.getLogger(__name__).warning(f"Could not persist VoBiz credentials to {env_file}: {e}")


def save_twilio_credentials(account_sid: str, auth_token: str, phone_number: str) -> None:
    """
    Updates runtime settings and writes TWILIO credentials to .env file for persistence.
    """
    import logging
    from pathlib import Path

    settings.TWILIO_ACCOUNT_SID = account_sid
    settings.TWILIO_AUTH_TOKEN = auth_token
    settings.TWILIO_PHONE_NUMBER = phone_number

    # Find the backend .env file
    possible_paths = [
        Path(".env"),
        Path(__file__).resolve().parent.parent / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
    ]
    env_file = None
    for p in possible_paths:
        if p.exists() and p.is_file():
            env_file = p
            break
    if not env_file:
        env_file = Path(__file__).resolve().parent.parent / ".env"

    updates = {
        "TWILIO_ACCOUNT_SID": account_sid,
        "TWILIO_AUTH_TOKEN": auth_token,
        "TWILIO_PHONE_NUMBER": phone_number,
    }

    lines = []
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            lines = []

    new_lines = []
    seen_keys = set()
    for line in lines:
        matched_key = None
        for k in updates:
            if line.strip().startswith(f"{k}="):
                matched_key = k
                break
        if matched_key:
            new_lines.append(f"{matched_key}={updates[matched_key]}\n")
            seen_keys.add(matched_key)
        else:
            new_lines.append(line)

    unseen = [k for k in updates if k not in seen_keys]
    if unseen:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines.append("\n")
        new_lines.append("\n# Twilio Telephony Credentials\n")
        for k in unseen:
            new_lines.append(f"{k}={updates[k]}\n")

    try:
        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception as e:
        logging.getLogger(__name__).warning(f"Could not persist Twilio credentials to {env_file}: {e}")


def save_sarvam_credentials(api_key: str, default_voice: Optional[str] = None) -> None:
    """
    Updates runtime settings and writes SARVAM AI credentials to .env file for persistence.
    """
    import logging
    from pathlib import Path

    settings.SARVAM_API_KEY = api_key
    if default_voice:
        settings.SARVAM_DEFAULT_VOICE = default_voice

    possible_paths = [
        Path(".env"),
        Path(__file__).resolve().parent.parent / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
    ]
    env_file = None
    for p in possible_paths:
        if p.exists() and p.is_file():
            env_file = p
            break
    if not env_file:
        env_file = Path(__file__).resolve().parent.parent / ".env"

    updates = {
        "SARVAM_API_KEY": api_key,
    }
    if default_voice:
        updates["SARVAM_DEFAULT_VOICE"] = default_voice

    lines = []
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            lines = []

    new_lines = []
    seen_keys = set()
    for line in lines:
        matched_key = None
        for k in updates:
            if line.strip().startswith(f"{k}="):
                matched_key = k
                break
        if matched_key:
            new_lines.append(f"{matched_key}={updates[matched_key]}\n")
            seen_keys.add(matched_key)
        else:
            new_lines.append(line)

    unseen = [k for k in updates if k not in seen_keys]
    if unseen:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines.append("\n")
        new_lines.append("\n# Sarvam AI Credentials\n")
        for k in unseen:
            new_lines.append(f"{k}={updates[k]}\n")

    try:
        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception as e:
        logging.getLogger(__name__).warning(f"Could not persist Sarvam credentials to {env_file}: {e}")


def save_transcript_api_credentials(gemini_api_key: str, gemini_model: Optional[str] = None) -> None:
    """
    Updates runtime settings and writes Google Gemini / Transcript AI credentials to .env file for persistence.
    Updates in real-time without requiring backend restart.
    """
    import os
    import logging
    from pathlib import Path

    clean_key = (gemini_api_key or "").strip()
    settings.GEMINI_API_KEY = clean_key
    os.environ["GEMINI_API_KEY"] = clean_key
    os.environ["GOOGLE_API_KEY"] = clean_key

    if gemini_model:
        clean_model = gemini_model.strip()
        settings.GEMINI_MODEL = clean_model
        os.environ["GEMINI_MODEL"] = clean_model

    possible_paths = [
        Path(".env"),
        Path(__file__).resolve().parent.parent / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
    ]
    env_file = None
    for p in possible_paths:
        if p.exists() and p.is_file():
            env_file = p
            break
    if not env_file:
        env_file = Path(__file__).resolve().parent.parent / ".env"

    updates = {
        "GEMINI_API_KEY": clean_key,
    }
    if gemini_model:
        updates["GEMINI_MODEL"] = gemini_model.strip()

    lines = []
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            lines = []

    new_lines = []
    seen_keys = set()
    for line in lines:
        matched_key = None
        for k in updates:
            if line.strip().startswith(f"{k}="):
                matched_key = k
                break
        if matched_key:
            new_lines.append(f"{matched_key}={updates[matched_key]}\n")
            seen_keys.add(matched_key)
        else:
            new_lines.append(line)

    unseen = [k for k in updates if k not in seen_keys]
    if unseen:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines.append("\n")
        new_lines.append("\n# Google Gemini / Transcript Intelligence Credentials\n")
        for k in unseen:
            new_lines.append(f"{k}={updates[k]}\n")

    try:
        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception as e:
        logging.getLogger(__name__).warning(f"Could not persist Transcript API credentials to {env_file}: {e}")

