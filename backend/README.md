# Calling Agent — Custom Backend

Production-ready, lightweight FastAPI backend that bridges our **Web UI/UX Frontend** with the **Dograh Voice AI Orchestration Engine**.

---

## Architectural Role

```
Web UI / UX Frontend (React + Vite)
          ↓ (HTTPS / REST + WS)
Custom Backend (FastAPI, Port 8001)
   • Holds Dograh API Key & Telephony Secrets
   • Validates Phone Numbers & Authenticates Clients
   • Normalizes Status & Dispatches Dograh Workflows
   • Ingests Post-Call Webhooks (Transcripts, Audio, Outcomes)
          ↓ (REST: X-API-Key: sk-...)
Dograh Voice Engine (FastAPI, Port 8000)
          ↓ (Telephony Provider Webhooks / Media WSS)
Telephony Provider (Twilio / Plivo / Telnyx / etc.)
          ↓ (PSTN Call)
Customer Phone
```

---

## Key Features

1. **Security Isolation**: Administrative Dograh API keys, database credentials, and carrier secrets remain strictly server-side.
2. **Simplified Agent Model**: High-level Course Sales Agent definitions automatically translate into Dograh `ReactFlowDTO` workflow node graphs (`globalNode`, `startCall`, `agentNode`, `endCall`, `trigger`, `webhook`).
3. **Outbound Call Dispatch**: Initiates outbound calls via verified Dograh triggers (`POST /api/v1/public/agent/{trigger_path}`) or telephony endpoints.
4. **Live Call Status Tracking**: Normalizes provider and Dograh callbacks into canonical states (`initiating`, `ringing`, `in_progress`, `completed`, `busy`, `no_answer`, `failed`).
5. **Webhook Ingestion**: Post-call webhook receiver updates call duration, transcript URLs, audio recording URLs, and final dispositions.
6. **Local SQLite / PostgreSQL Ready**: Runs locally with zero database setup via SQLite (`aiosqlite`), with full support for PostgreSQL.

---

## Requirements

- Python 3.10+ (Tested on Python 3.12)
- Running or configured Dograh server (default `http://localhost:8000`)

---

## Getting Started

### 1. Create and Activate Virtual Environment

```bash
# Windows PowerShell
cd "Calling Agent/backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux / macOS
cd "Calling Agent/backend"
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment (`.env`)

Copy the template file:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# Dograh API Settings
DOGRAH_BASE_URL=http://localhost:8000
DOGRAH_API_KEY=sk-your-dograh-api-key

# Backend Server
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8001
ENVIRONMENT=development

# Database (SQLite by default)
DATABASE_URL=sqlite+aiosqlite:///./calling_agent.db

# Security & Webhook (Optional token for mobile client & webhook verification)
APP_API_KEY=
DOGRAH_WEBHOOK_SECRET=
CORS_ORIGINS=["*"]
```

### 4. Start the Backend Server

```bash
# Windows / PowerShell
.\.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Linux / macOS
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

Interactive OpenAPI documentation is available at:
- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`

---

## API Endpoints Reference

### System

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Service health status & Dograh connectivity check |

### Agents (`/api/agents`)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/agents` | List all configured voice agents |
| `POST` | `/api/agents` | Create agent & synchronize workflow to Dograh |
| `GET` | `/api/agents/{agent_id}` | Retrieve agent by ID |
| `PUT` | `/api/agents/{agent_id}` | Update agent configuration & re-sync |
| `DELETE` | `/api/agents/{agent_id}` | Delete agent |

### Calls (`/api/calls`)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/calls/initiate` | Trigger an outbound phone call |
| `GET` | `/api/calls/{call_id}/status` | Get live normalized status of a call |
| `GET` | `/api/calls/history` | Retrieve call history with duration and audio links |

### Webhooks (`/api/webhooks`)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/webhooks/dograh` | Ingest post-call metrics and recordings from Dograh |

---

## Example Requests & Responses

### 1. Create a Voice Agent

**Request:**
```http
POST /api/agents HTTP/1.1
Host: localhost:8001
Content-Type: application/json

{
  "name": "Course Sales Agent",
  "purpose": "Sell our company's AI and Software Engineering courses",
  "instructions": "Explain course curriculum, pricing, benefits, and eligibility. Answer queries clearly and concisely.",
  "allowed_topics": [
    "Course curriculum",
    "Pricing and discounts",
    "Eligibility criteria",
    "Duration and batch timings"
  ],
  "restricted_topics": [
    "Politics",
    "Religion",
    "Personal financial advice",
    "Unrelated topics"
  ],
  "behavior_rules": [
    "If customer is interested -> continue sales conversation and capture contact preference.",
    "If customer is not interested -> politely thank them and close the call.",
    "If customer asks off-topic questions -> courteously bring conversation back to the course."
  ],
  "enabled": true
}
```

**Response (`201 Created`):**
```json
{
  "id": "e98e4ba4-9a84-4861-a476-80ceae28cbf4",
  "name": "Course Sales Agent",
  "purpose": "Sell our company's AI and Software Engineering courses",
  "instructions": "Explain course curriculum, pricing, benefits, and eligibility. Answer queries clearly and concisely.",
  "allowed_topics": [
    "Course curriculum",
    "Pricing and discounts",
    "Eligibility criteria",
    "Duration and batch timings"
  ],
  "restricted_topics": [
    "Politics",
    "Religion",
    "Personal financial advice",
    "Unrelated topics"
  ],
  "behavior_rules": [
    "If customer is interested -> continue sales conversation and capture contact preference.",
    "If customer is not interested -> politely thank them and close the call.",
    "If customer asks off-topic questions -> courteously bring conversation back to the course."
  ],
  "enabled": true,
  "dograh_workflow_id": 14,
  "dograh_trigger_path": "agent-7f12a8b9c0d1",
  "created_at": "2026-09-04T15:00:00Z",
  "updated_at": "2026-09-04T15:00:00Z"
}
```

---

### 2. Initiate Outbound Call

**Request:**
```http
POST /api/calls/initiate HTTP/1.1
Host: localhost:8001
Content-Type: application/json

{
  "phone_number": "+919876543210",
  "agent_id": "e98e4ba4-9a84-4861-a476-80ceae28cbf4"
}
```

**Response (`200 OK`):**
```json
{
  "success": true,
  "call_id": "c17983ea-6eb1-46bb-b3b3-85f26938942b",
  "status": "initiating",
  "message": "Call successfully initiated"
}
```

---

### 3. Poll Call Status

**Request:**
```http
GET /api/calls/c17983ea-6eb1-46bb-b3b3-85f26938942b/status HTTP/1.1
Host: localhost:8001
```

**Response (`200 OK`):**
```json
{
  "call_id": "c17983ea-6eb1-46bb-b3b3-85f26938942b",
  "status": "completed",
  "phone_number": "+919876543210",
  "agent_id": "e98e4ba4-9a84-4861-a476-80ceae28cbf4",
  "agent_name": "Course Sales Agent",
  "started_at": "2026-09-04T15:05:00Z",
  "ended_at": "2026-09-04T15:06:15Z",
  "duration": 75.0,
  "disposition": "interested",
  "transcript_url": "http://localhost:9000/voice-audio/transcripts/run-142.json",
  "recording_url": "http://localhost:9000/voice-audio/recordings/run-142.wav"
}
```

---

## Running Automated Tests

Run the test suite via pytest:

```bash
cd "Calling Agent/backend"
.\.venv\Scripts\pytest -v
```

Test coverage includes:
- E.164 phone number validation and normalization.
- Canonical call state mapping.
- Agent creation, updating, listing, and deletion.
- Call initiation, status polling, and error handling.
- Mocked Dograh API responses and webhook processing.
- Health check endpoints.

---

## Security Guidelines

1. **Keep Secrets Server-Side**: The Dograh API key (`DOGRAH_API_KEY`) and telephony credentials must never be shared with mobile clients.
2. **Never Commit `.env`**: Always use `.env.example` as a template and keep secret keys in environment variables.
3. **CORS Restrictions**: In production deployments, configure `CORS_ORIGINS` to only permit authorized client domains.
