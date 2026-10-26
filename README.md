# 🎙️ ARB SoftTech AI Enterprise Voice Calling Agent Platform

<div align="center">

![Platform Banner](https://img.shields.io/badge/ARB_SoftTech-Voice_AI_Platform-00d2ff?style=for-the-badge&logo=probot)
![Python](https://img.shields.io/badge/Python-3.11_|_3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React_18-Vite_UI-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![License](https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge)

**Autonomous Conversational Telephony Agent for Real-Time PSTN Phone Calls**  
*Fluent Hindi (Devanagari), English & Indic Dialects • Sub-400ms Barge-In Interruption • Lead Intelligence Qualification*

[⚡ 1-Click Quickstart](#-1-click-universal-quickstart) • [📁 Data Storage Guide](#-clean-data-storage-architecture) • [📞 Telephony Setup](#-telephony-carrier-setup-vobiz--twilio) • [🩺 System Doctor](#-preflight-system-doctor) • [🛠️ Troubleshooting](#%EF%B8%8F-troubleshooting)

</div>

---

## 🌟 Executive Summary

The **ARB SoftTech AI Calling Agent** is a full-stack, enterprise-grade outbound and inbound telephony platform. It dials regular mobile and landline telephone numbers over PSTN networks, conducts human-like conversations in natural spoken Hindi and English with millisecond-latency voice activity detection (VAD), records authentic 2-way audio, and extracts sales intelligence (Interested, Callback, Rejection) using Google Gemini AI.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 TELEPHONY ARCHITECTURE                                 │
│                                                                                        │
│   📱 Customer Phone <───(PSTN Cellular)───> 📞 VoBiz / Twilio <───(WebSockets)───┐     │
│                                                                                  │     │
│                                                                                  ▼     │
│   💻 Client Browser <───(REST / WS)───> ⚡ FastAPI Engine (Port 8001) <───> 🌐 Ngrok   │
│       (Port 5173)                                │                                     │
│                                                  ▼                                     │
│                        ┌─────────────────────────────────────────────────┐             │
│                        │       📁 Central Client Data Folder (data/)     │             │
│                        │  ├── recordings/   (Authentic 2-way .wav)       │             │
│                        │  ├── transcripts/  (Turn-by-turn .txt & .json)   │             │
│                        │  ├── intelligence/ (Gemini Lead Intent Scoring) │             │
│                        │  └── database/     (calling_agent.db)           │             │
│                        └─────────────────────────────────────────────────┘             │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ 1-Click Universal Quickstart

The repository is built for **zero-friction client deployment**. You do **not** need to manually download Docker, Ngrok, or Python packages. A single command handles inspection, automatic installation, environment initialization, and service startup.

### 🪟 Windows (Recommended)
Simply double-click the master installer file in File Explorer:
```cmd
setup_and_run.bat
```
*What this automated script does:*
1. **Checks Ngrok**: If missing, automatically downloads the official 64-bit `ngrok.exe` directly into `bin\ngrok.exe` (no admin rights needed).
2. **Checks Python**: Verifies Python 3.10+; if missing, auto-installs Python 3.12 with PATH configured.
3. **Checks Node.js**: Verifies Node.js & npm; if missing, auto-installs Node.js LTS via winget.
4. **Checks Docker**: Detects Docker Desktop and launches the daemon if present. *(Note: High-performance Native Sarvam AI mode runs 100% without Docker!)*
5. **Initializes `data/`**: Sets up `data/recordings`, `data/transcripts`, `data/intelligence`, and `data/database`.
6. **Creates Virtualenv**: Creates `backend\.venv` and installs all dependencies automatically.
7. **Seeds Default Voice Agents**: Automatically seeds pre-configured Admission Counselor, Real Estate Advisor, and Tech Support agents.
8. **Starts Tunnel & Servers**: Automatically launches Ngrok on port 8001, hooks into the FastAPI Backend, launches the React Dashboard, and opens `http://localhost:5173` in your browser.

---

### 🐧 Linux / macOS
Open your terminal inside the repository and run:
```bash
chmod +x setup_and_run.sh
./setup_and_run.sh
```

---

## 📁 Clean Data Storage Architecture

All persistent call artifacts are organized neatly into a single root-level `data/` folder:

```
calling-agent-platform/
├── data/
│   ├── recordings/       <-- Authentic 2-way WAV audio recordings (call_<id>.wav)
│   ├── transcripts/      <-- Human-readable (.txt) & structured (.json) dialogue logs
│   ├── intelligence/     <-- Google Gemini lead qualification & interest scoring
│   ├── database/         <-- SQLite database (calling_agent.db)
│   └── logs/             <-- Backend server and Ngrok tunnel runtime logs
```

### 1. Audio Recordings (`data/recordings/`)
Every completed call automatically saves its master 2-way mixed audio file:
- File naming: `call_{call_id}.wav`
- Format: 8,000Hz 16-bit PCM WAV (lossless telephony standard).
- Directly playable in Windows Media Player, VLC, or any audio player.

### 2. Transcripts (`data/transcripts/`)
Every call exports two complementary transcript formats:
- **`call_{call_id}_transcript.txt`**: Clean, formatted for human reading:
  ```text
  ==============================================================================
                     AI VOICE CALL TRANSCRIPT REPORT
  ==============================================================================
  Call ID:        63b90a42-d04b-4822-b5e8-0b5c92ba1851
  Phone Number:   +919405311676
  Agent Name:     Admission & Career Counselor
  Date & Time:    2026-10-26 19:45:00 UTC
  Total Duration: 42.5 seconds (00:42)
  Call Status:    INTERESTED
  Audio File:     data/recordings/call_63b90a42.wav
  ------------------------------------------------------------------------------
  CONVERSATION DIALOGUE:
  ------------------------------------------------------------------------------
  [00:01] Agent: नमस्कार जी! मैं ARB SoftTech से बात कर रहा हूँ।
  [00:04] Customer: हाँ बोलिए, मुझे एडमिशन के बारे में जानना है।
  [00:09] Agent: जी ज़रूर! आप किस कोर्स में एडमिशन लेना चाहते हैं?
  [00:14] Customer: बी.टेक कंप्यूटर साइंस के लिए।
  ------------------------------------------------------------------------------
  LEAD INTELLIGENCE & CALL QUALIFICATION:
  ------------------------------------------------------------------------------
  Qualification:  INTERESTED (Confidence: 95%)
  Reasoning:      Customer actively inquired about B.Tech Computer Science admissions.
  Key Signals:    b.tech, admission, computer science
  ==============================================================================
  ```
- **`call_{call_id}_transcript.json`**: Structured JSON format with segment start/end timestamps, speaker roles, confidence scores, and raw metadata.

### 3. Lead Intelligence (`data/intelligence/`)
Automated intent evaluation generated by Google Gemini:
- Classification: `INTERESTED`, `NOT_INTERESTED`, `CALLBACK_REQUESTED`, `LINE_BUSY`.
- Confidence score (0.00 to 1.00).
- Actionable follow-up recommendation and reason.

---

## 📞 Telephony Carrier Setup (VoBiz & Twilio)

### Setting Credentials in `backend/.env`
Open `backend/.env` in Notepad or your text editor:

```ini
# ============================================================
# 1. Telephony Webhook Public Tunnel
# ============================================================
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8001
# (Leave blank or set to your custom domain; setup_and_run.bat auto-detects Ngrok)
BACKEND_PUBLIC_URL=

# ============================================================
# 2. Sarvam AI Voice Engine Credentials
# ============================================================
SARVAM_API_KEY=sk_your_sarvam_api_key_here
SARVAM_DEFAULT_VOICE=shubh
SARVAM_TTS_MODEL=bulbul:v3
SARVAM_STT_MODEL=saaras:v3
SARVAM_LLM_MODEL=sarvam-105b-conversations

# ============================================================
# 3. VoBiz Carrier Telephony Credentials
# ============================================================
VOBIZ_AUTH_ID=MA_VLR9RPFZ
VOBIZ_AUTH_TOKEN=your_vobiz_auth_token_here
VOBIZ_FROM_NUMBER=+918065354620

# ============================================================
# 4. Google Gemini API Key (Transcript Intelligence)
# ============================================================
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

---

## 🩺 Preflight System Doctor

To verify that your computer, API credentials, and network tunnels are 100% operational before dialing:

```cmd
python scripts/doctor.py
```

To test live Sarvam AI speech synthesis and VoBiz carrier authentication:
```cmd
python scripts/verify_calling.py
```

---

## 🚀 How to Launch on Subsequent Days

After running `setup_and_run.bat` for the initial installation, simply run:
```cmd
start_all.bat
```
This starts all three services in parallel:
- 🌐 **Ngrok Public Tunnel**: Captures public audio stream webhook
- ⚡ **FastAPI Backend**: `http://localhost:8001`
- 🖥️ **React Dashboard**: `http://localhost:5173`

---

## 📱 Placing Your First Live Call

1. Open **`http://localhost:5173`** in your browser.
2. Navigate to **"AI Agents"** on the left menu.
3. Select any seeded agent (e.g., *Admission Counselor* or *Real Estate Advisor*).
4. Click **"Quick Call"** (or open the Dial modal).
5. Enter your phone number with country code (e.g. `+919876543210`) and click **"Call Now"**.
6. **Your phone will ring!** Answer and speak in natural Hindi or English.
7. When the call ends, inspect:
   - Dashboard: **Calls History** with live audio waveform and transcript.
   - Filesystem: **`data/recordings/`** and **`data/transcripts/`**.

---

## 🛠️ Troubleshooting

| Issue | Root Cause | Solution |
| :--- | :--- | :--- |
| **Ngrok tunnel inactive** | First time running without Ngrok authtoken | Run `ngrok config add-authtoken <YOUR_TOKEN>` from [dashboard.ngrok.com](https://dashboard.ngrok.com/get-started/your-authtoken) |
| **Call rings but drops on answer** | Webhook URL was unreachable by carrier | Ensure `start_all.bat` is running; verify tunnel in `python scripts/verify_calling.py` |
| **Python command not found** | Python was installed without checking PATH | Run `setup_and_run.bat` which auto-configures PATH, or restart terminal |
| **Port 8001 in use** | A previous instance is lingering | Run `taskkill /F /IM uvicorn.exe` or `netstat -ano \| findstr :8001` |

---

## 📄 License & Proprietary Rights
**ARB SoftTech Enterprise Platform** • All rights reserved. Configured for turn-key client deployment.
