# 📋 ARB SoftTech AI Calling Agent - Client Handover Document

**Project:** Autonomous AI Enterprise Voice Calling Agent Platform  
**Client Version:** 2.0.0 Production  
**Handover Date:** October 2026  
**Telephony Engine:** Native Sarvam AI Telephony (PSTN Full Duplex 8kHz) + Google Gemini AI  

---

## 🎯 Project Overview & Deliverables

This repository contains the complete, autonomous **AI Voice Calling Agent Platform** configured for real-time outbound PSTN calls to mobile and landline phones across India and international regions.

### Key Capabilities Delivered
1. **Human-like Conversational AI:** Native multi-turn dialogue in polite spoken Hindi (Devanagari script) and conversational English.
2. **Sub-400ms Barge-In Interruption:** Millisecond voice activity detection (VAD). When the customer interrupts, the agent halts speaking immediately and listens attentively.
3. **PSTN Carrier Integration:** Integrated directly with VoBiz and Twilio cellular trunks for crisp, jitter-free phone connections.
4. **Automated Sales & Lead Qualification:** Analyzes call transcripts using Google Gemini to classify customer intent (Interested, Callback Requested, Not Interested, Line Busy).
5. **Unified Data Storage:** Every single recording, transcript, analysis, and database record is saved neatly in a dedicated `data/` directory.

---

## 🚀 1-Click Setup on Any Computer

When sharing this project with your client or team members, they **do not** need to install tools manually:

### Option 1: 1-Click Setup File (Double-Click)
```cmd
setup_and_run.bat
```
- Checks for Python, Node.js, Ngrok, and Docker.
- Automatically downloads missing tools (including official `ngrok.exe` into `bin/`).
- Initializes environments, database, and seeds default voice agents.
- Starts the system and opens the web dashboard at `http://localhost:5173`.

### Option 2: Daily Launch File
```cmd
start_all.bat
```
Launches the Ngrok public tunnel, FastAPI backend, and React dashboard concurrently.

---

## 📁 Centralized Data Storage Structure (`data/`)

All call artifacts are organized neatly in the root `data/` folder:

| Folder | What is Stored | File Format |
| :--- | :--- | :--- |
| **`data/recordings/`** | Authentic 2-way call audio recordings | `call_<call_id>.wav` (8kHz 16-bit PCM WAV) |
| **`data/transcripts/`** | Human-readable & structured conversation dialogue | `call_<call_id>_transcript.txt` and `.json` |
| **`data/intelligence/`** | Google Gemini lead interest analysis & score | `call_<call_id>_intel.json` |
| **`data/database/`** | Persistent SQLite database | `data/database/calling_agent.db` |
| **`data/logs/`** | Backend server & tunnel logs | `backend.log`, `tunnel.log`, `tunnel_url.txt` |

---

## 🔑 System Endpoints & Default Credentials

### Web Interfaces & APIs
| Service | URL | Description |
| :--- | :--- | :--- |
| **Web Dashboard** | `http://localhost:5173` | CRM, AI Agents, Live Calls, Lead Intelligence, Settings |
| **Backend API Docs** | `http://localhost:8001/docs` | Interactive Swagger OpenAPI documentation |
| **Telephony Status** | `http://localhost:8001/api/v1/telephony/vobiz/status` | Real-time diagnostic health check |

### Pre-Configured Voice Agents Seeded
1. **Admission & Career Counselor (ID: `agent-admission-advisor`)**:
   - Voice: `shubh` (Conversational Hindi Male)
   - Purpose: Academic course guidance and admission qualification.
2. **Priya - Real Estate Advisor (ID: `agent-real-estate`)**:
   - Voice: `ritu` (Expressive Hindi Female)
   - Purpose: Property buyer inquiry and site visit scheduling.
3. **Raj - Technical & Broadband Support (ID: `agent-technical-support`)**:
   - Voice: `aditya` (Friendly Hindi Male)
   - Purpose: Internet connection troubleshooting and engineer dispatch.

---

## 📞 How Live Phone Calls Work

1. In the Dashboard (`http://localhost:5173`), click **"AI Agents"** and choose an agent.
2. Click **"Quick Call"**, enter your telephone number with country code (e.g. `+919876543210`), and click **"Call Now"**.
3. **Your mobile phone will ring within 2 to 5 seconds!**
4. Answer the call and converse in Hindi or English.
5. Once hung up, immediately check:
   - **`data/recordings/`**: Play the authentic recording.
   - **`data/transcripts/`**: Read the complete timestamped transcript.
   - **`data/intelligence/`**: Check the buyer interest score.

---

## 🩺 Diagnostic Tools Included

Run these anytime from the terminal to test your system:
- **System Doctor:** `python scripts/doctor.py`
- **Telephony & Carrier Test:** `python scripts/verify_calling.py`

---

## 🔒 Security & Git Notice
The `.gitignore` has been pre-configured so that client call recordings, transcripts, databases, and `.env` credentials are **never pushed to public Git repositories**. Only code, schemas, and configurations are tracked.
