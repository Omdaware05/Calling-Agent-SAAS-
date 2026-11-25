# ARB SoftTech AI Voice Calling Agent SaaS Platform
## Comprehensive Viva, Oral Defense & Architecture Master Guide

> [!IMPORTANT]
> This master document is your complete preparation guide for your project viva and examination. It covers the **system architecture, end-to-end call pipeline, every backend and frontend file, all algorithms used, tunable parameters ("which value change does what"), and expected examiner questions with winning answers**.

---

## 1. Project High-Level Overview

### 1.1 What is this Project?
**ARB SoftTech AI Voice Calling Agent SaaS** is an enterprise-grade, multi-tenant AI Voice Telephony Platform designed specifically for Indian enterprise workflows (such as Agritech lead generation, college admissions, customer feedback, and sales qualification) supporting **Hindi, Marathi, Hinglish, Gujarati, and Indian English**.

The platform connects directly to the **Public Switched Telephone Network (PSTN)** via telecom carriers (VoBiz, Plivo, Twilio) and conducts natural, real-time, two-way conversational phone calls with human customers using artificial intelligence.

### 1.2 Core Problem Solved & Differentiators
1. **Ultra-Low Latency (<200ms TTFB)**: Traditional voice bots take 2 to 4 seconds to reply because they send every audio turn to an LLM. Our system uses a **Hybrid Orchestration Engine**: deterministic scripted questions and FAQ matches are answered in **<2ms**, completely bypassing the LLM.
2. **Zero Hallucination Guarantee**: In sectors like Agriculture or College Admissions, an LLM might invent seed prices, yield figures, or fee structures. Our platform uses an approved **Deterministic Questionnaire Engine** that strictly sticks to approved facts.
3. **Indic Language Precision**: Built on **Sarvam AI (Saaras STT & Bulbul TTS)** for authentic Indian accents and Devanagari script processing, avoiding awkward Western-accented synthesizers.
4. **Adaptive Conversational Pacing**: Custom adaptive Voice Activity Detection (VAD) that prevents the AI from interrupting slow-speaking rural callers.

---

## 2. End-to-End Call Pipeline Architecture

The diagram below illustrates what happens from the millisecond a call is dialed until post-call intelligence is stored.

```mermaid
sequenceDiagram
    autonumber
    actor Customer as Human Customer (PSTN Mobile)
    participant Carrier as Telecom Carrier (VoBiz / Plivo)
    participant Telephony as sarvam_telephony_service.py (FastAPI WebSocket)
    participant FSM as FastQuestionnaireOrchestrator (<2ms FSM)
    participant LLM as Google Gemini (Fallback)
    participant Sarvam as Sarvam AI (STT & TTS API)
    participant DB as SQLite / PostgreSQL

    Note over Customer,Carrier: 1. Outbound / Inbound Call Triggered
    Carrier->>Customer: Rings phone & connects call
    Carrier->>Telephony: WebSocket Connect (`/api/telephony/sarvam/stream/{call_id}`)
    Carrier->>Telephony: Send `{"event": "start"}`
    Telephony->>Sarvam: Synthesize opening greeting (Bulbul TTS 8kHz)
    Sarvam-->>Telephony: Return Linear PCM16
    Telephony->>Telephony: Compand PCM16 to G.711 mu-law (8kHz)
    Telephony->>Carrier: Stream mu-law audio packets (Base64)
    Carrier->>Customer: Customer hears: "नमस्ते, मैं Samruddhi Agritech से..."

    Note over Customer,Telephony: 2. Customer Speaks
    Customer->>Carrier: Customer speaks: "मैं मक्का की योजना बना रहा हूँ"
    Carrier->>Telephony: Send Base64 mu-law chunks over WebSocket
    Telephony->>Telephony: Adaptive VAD & Silence Threshold Detection (1.1s - 1.35s)
    Telephony->>Sarvam: Send accumulated PCM WAV to Sarvam Saaras STT
    Sarvam-->>Telephony: Text: "मैं मक्का की योजना बना रहा हूँ"

    Note over Telephony,LLM: 3. Dialogue Orchestration Decision
    Telephony->>Telephony: Check 1: Is caller busy / requesting callback?
    Telephony->>Telephony: Check 2: Is caller refusing / declining?
    Telephony->>FSM: Check 3: FastQuestionnaireOrchestrator.resolve_next_turn()
    alt Scripted Question or FAQ Match (<2ms)
        FSM-->>Telephony: Return exact scripted turn + terminal flag
    else Unscripted Inquiry / Complex Repair
        Telephony->>LLM: Fallback to Gemini 1.5 Flash (<15 words, strict rules)
        LLM-->>Telephony: Return LLM response
    end

    Note over Telephony,Customer: 4. Audio Playback & Progression
    Telephony->>Sarvam: Synthesize response via Bulbul TTS
    Sarvam-->>Telephony: PCM Audio
    Telephony->>Carrier: Stream G.711 mu-law audio packets
    Carrier->>Customer: Customer hears agent response

    Note over Telephony,DB: 5. Call Conclusion & Post-Call Analytics
    alt Call Terminated (Script completed / Farewell spoken / Disconnected)
        Telephony->>Carrier: Telecom Hangup Command
        Telephony->>DB: Save Transcripts, Call Duration, Dispositions
        Telephony->>DB: Lead Intelligence Analysis (Classification, Crop, Acreage)
    end
```

---

## 3. Comprehensive File-by-File Guide

### 3.1 Backend Root (`backend/app/`)

| File Path | Core Role & Responsibility | Key Classes / Functions |
| :--- | :--- | :--- |
| `main.py` | **Application Entry Point**. Initializes FastAPI app, CORS middleware, API route routers, lifespan startup/shutdown events, static directory mounts, and database table creation. | `create_app()`, `lifespan()`, `app` |
| `config.py` | **Central Configuration & Environment Variables**. Uses Pydantic `BaseSettings` to load API keys (`SARVAM_API_KEY`, `GEMINI_API_KEY`, `VOBIZ_AUTH_ID`, `TWILIO_ACCOUNT_SID`), database URLs, and Redis config. | `Settings`, `get_settings()` |
| `database.py` | **Database Engine & Session Management**. Configures SQLAlchemy asynchronous engine (`create_async_engine`), `AsyncSessionLocal`, and base declarative model class. | `engine`, `AsyncSessionLocal`, `Base`, `get_db()` |
| `database_migrations.py`| **Lightweight Schema Auto-Migration**. Adds missing database columns dynamically on application boot without needing external Alembic CLI runs. | `run_migrations()` |
| `dependencies.py` | **FastAPI Request Dependencies**. Provides tenant extraction, authentication verification, and DB session injection for route endpoints. | `get_current_tenant()`, `get_db_session()` |

---

### 3.2 Backend Telephony & Dialogue Services (`backend/app/services/`)

This is the **heart** of the entire application:

#### 1. `sarvam_telephony_service.py` *(Most Important File!)*
* **Role**: Manages the live **WebSocket full-duplex audio stream** between the telecom carrier and the AI bot.
* **Key Components**:
  - `handle_sarvam_telephony_stream(websocket, call_id)`: Async loop that receives binary/base64 audio packets, detects silence, calls STT, orchestrates response, calls TTS, and streams audio back.
  - `is_callback_request(text)`: Regex and phrase detector for rescheduling requests (*"क्या आप मुझे थोड़ी देर बाद कॉल कर सकते हैं?"*, *"उद्या फोन करा"*).
  - `is_refusal_or_call_termination(text)`: Detects negative intent (*"नहीं चाहिए"*, *"phone kato"*).
  - `is_farewell_reply(text)`: Detects when the AI delivers a closing statement (*"समय देने के लिए धन्यवाद"*, *"शुभ हो"*) and automatically cuts the carrier call.
  - `synthesize_speech(text, voice, language_code)`: Calls Sarvam Bulbul API and extracts 8kHz 16-bit PCM.
  - `transcribe_audio_sarvam(audio_bytes, language_code)`: Sends user audio buffer to Sarvam Saaras STT API.
  - **Companding**: Uses `audioop.lin2ulaw` and `audioop.ulaw2lin` to convert between 16-bit linear PCM and 8-bit G.711 mu-law telephony audio.

#### 2. `questionnaire_runtime_service.py` *(Second Most Important File!)*
* **Role**: The **Deterministic Finite State Machine (FSM)** engine. Executes dynamic questionnaires in <2ms without needing an LLM.
* **Key Components**:
  - `FastQuestionnaireOrchestrator`: Orchestrator class.
  - `parse_questionnaire_from_prompt(system_prompt)`: Parses questions, types (single_choice, text, number, yes_no, reference, closing), and expected answers.
  - `resolve_next_turn(messages)`: Evaluates current dialogue state, checks which questions were asked, and returns the next question or approved FAQ answer.
  - `resolve_next_turn_detailed(messages)`: Returns `(reply_text, is_terminal)`. When `is_terminal=True`, tells telephony to hang up the call cleanly.
  - `_qa_overlap_match(user_text, question_text)`: Jaccard/token overlap algorithm with stopword removal to match caller questions against scripted FAQ entries.
  - `is_conversational_filler(text)`: Recognizes non-answers like *"ठीक है"*, *"हाँ"*, *"अच्छा"* and re-prompts the unanswered question.

#### 3. `telephony_service.py`
* **Role**: Abstract carrier gateway. Handles dialing outbound phone calls and triggering carrier-side PSTN hangups via REST APIs for VoBiz, Plivo, and Twilio.
* **Key Methods**: `initiate_outbound_call()`, `hangup_live_telephony_call()`.

#### 4. `lead_intelligence_service.py`
* **Role**: Post-call classification engine. Runs right after a call ends.
* **Key Functions**:
  - Analyzes full transcript to assign a **Qualification Status**: `INTERESTED`, `NOT_INTERESTED`, `CALLBACK_REQUESTED`, or `UNCERTAIN`.
  - Calculates confidence score (0.0 to 1.0).
  - Extracts customer signals, crop type, acreage, buying timeline, and saves to database.

#### 5. `questionnaire_export_analysis_service.py`
* **Role**: Analysis extraction and caching for exports.
* **Key Functions**: Maps spoken answers directly to questionnaire question columns so Excel reports have clean, structured columns instead of raw paragraphs.

#### 6. `call_service.py` & `agent_service.py`
* **Role**: Business logic for CRUD operations on calls, transcripts, agent definitions, assigned voices, greetings, and system prompts.

#### 7. `batch_dialer_service.py` & `campaign_service.py`
* **Role**: Outbound campaign dialer. Iterates through contact lists, respects rate limits (e.g. 8 concurrent lines), and schedules automated calls.

#### 8. `storage/audio_generator.py` & `storage/s3.py`
* **Role**: Reconstructs recorded audio from streamed segments or downloads call recordings from telecom carrier storage and persists them locally (`data/recordings/`) or to AWS S3.

---

### 3.3 Backend API Routes (`backend/app/api/routes/`)

- `calls.py`: Endpoints to list calls, view call detail, retrieve transcripts, download audio recordings, and export Excel reports (`/api/calls/export.xlsx`).
- `agents.py`: Endpoints to create, update, delete, and configure AI Voice Agents (voice ID, speed, prompt, questionnaire linkage).
- `questionnaires.py`: Endpoints to manage structured dynamic questionnaire templates.
- `telephony.py`: Inbound webhooks and outbound stream bridge endpoints for VoBiz / Plivo / Twilio.
- `leads.py`: Lead management, qualification stats, and CRM synchronization.
- `campaigns.py`: Campaign creation, contact uploading, and batch dialer execution.
- `stats.py`: Dashboard KPIs (total calls, minutes spoken, interested lead conversion rate, active concurrency).

---

### 3.4 Backend Data Models (`backend/app/models/`)

- `call.py`: Defines tables `calls`, `transcripts`, `transcript_segments`, and `recordings`.
- `agent.py`: Defines table `agents` (stores `name`, `system_prompt`, `voice_id`, `language`, `questionnaire_id`, `greeting_message`).
- `questionnaire.py`: Defines table `questionnaires` (stores JSON array of questions, validation rules, translations).
- `lead.py`: Defines table `leads` (qualified buyer information, qualification confidence, extracted fields).
- `campaign.py` & `contact.py`: Defines marketing contact lists and campaign scheduling.

---

### 3.5 Frontend Architecture (`frontend_1/src/`)

Built with **React 18 + TypeScript + Vite + TailwindCSS**:
- `features/modern/ModernDashboard.tsx`: Executive dashboard displaying active calls, telemetry stats, network health, live line status, and recent call activity.
- `features/calls/CallsPage.tsx`: Interactive CDR (Call Detail Record) explorer with audio player, waveform scrubber, and synchronized transcript reader.
- `features/agents/AgentFormDrawer.tsx`: Agent builder interface where users can select voice (`shubh`, `amartya`), language, test TTS preview, and attach questionnaires.
- `features/questionnaires/QuestionnairesPage.tsx`: Dynamic questionnaire builder with drag-and-drop question ordering and translation support.
- `components/layout/QuickDialModal.tsx`: Softphone dialpad to trigger live test calls directly to any real phone number.
- `services/api/client.ts`: Axios client configured with JWT auth headers, base URL, and response interceptors.

---

## 4. Key Values, Knobs & Parameters ("Which Change Does What?")

Examiners love asking: *"If I change this parameter from X to Y, what happens to the system?"* Here is your cheat sheet:

| Parameter & Location | Default Value | What Happens if Increased? | What Happens if Decreased? | Why This Specific Value was Chosen |
| :--- | :--- | :--- | :--- | :--- |
| **`silence_threshold`**<br>`sarvam_telephony_service.py` | Adaptive:<br>`1.10s` (short)<br>`1.35s` (medium)<br>`1.25s` (long) | **Higher (e.g. 2.5s)**: The bot waits too long before answering. Caller feels awkward dead air or thinks the call got disconnected. | **Lower (e.g. 0.6s)**: The bot interrupts the caller while they are pausing to think (e.g. while saying *"मेरा नाम ओम है... [pause]... अमरावती से"*). | Different utterances need different patience windows. Multi-part answers require `1.35s` to prevent premature interruption. |
| **`audio_buffer` limits**<br>`sarvam_telephony_service.py` | `12000` samples (~1.5s)<br>`32000` samples (~4.0s) | **Higher**: Accumulates more audio before categorizing utterance length. May delay classification. | **Lower**: Treats medium utterances as short, triggering quicker silence timeout and cutting off callers. | Matches human conversational cadence in 8000Hz 8-bit audio representation. |
| **`sample_rate`**<br>Audio Pipeline | `8000 Hz` (8 kHz) | **Higher (e.g. 16000 Hz)**: Telecom carrier audio stream crashes with garbled Donald-Duck noise because standard telephony PSTN channels only support G.711 8kHz. | **Lower (e.g. 4000 Hz)**: Speech becomes unintelligible and muddy. | `8000 Hz` is the worldwide standard for PSTN telephone systems (ITU-T G.711). |
| **`temperature`**<br>Gemini LLM Call | `0.1` | **Higher (e.g. 0.8)**: LLM becomes creative and hallucinates (invents fake seed prices, discounts, or dates). | **Lower (0.0)**: Completely rigid, can get stuck in deterministic loops. | `0.1` keeps responses strictly anchored to business facts with minimal variance. |
| **`hangup_delay`**<br>`sarvam_telephony_service.py` | `1.2 seconds`<br>(`asyncio.sleep(1.2)`) | **Higher (e.g. 3.0s)**: Customer hears silence after goodbye before carrier terminates. Wastes carrier minutes. | **Lower (e.g. 0.1s)**: **Major Bug!** The carrier cuts the call while the agent is still speaking the last word ("नमस्कार!"). | `1.2s` provides the exact acoustic buffer for the final TTS packet to play out through the customer's phone speaker. |
| **`inactivity watchdog`**<br>`sarvam_telephony_service.py` | `15.0 seconds` | **Higher (e.g. 60s)**: If caller hangs up without socket closure, line stays open and drains customer balance. | **Lower (e.g. 4s)**: Drops legitimate calls if there is a temporary network packet hiccup. | Telecom industry standard timeout for zero-packet detection. |

---

## 5. Algorithms & Computer Science Concepts Used

### 5.1 Finite State Machine (FSM)
* **Where**: [questionnaire_runtime_service.py](file:///d:/AI_voice/New%20folder%20(6)/Calling-Agent-SAAS-/backend/app/services/questionnaire_runtime_service.py) (`FastQuestionnaireOrchestrator`).
* **Why**: To achieve zero-latency conversational turns without paying the time or financial cost of an LLM.
* **How it works**:
  $$\text{State}_{t+1} = \delta(\text{State}_t, \text{CustomerInput})$$
  - States = Script question nodes ($Q_1, Q_2, \dots, Q_n$).
  - Transitions = Customer acknowledgment or valid answer.
  - Compute latency = **<2 milliseconds**.

### 5.2 Token Overlap Matching & Information Retrieval (IR)
* **Where**: `_qa_overlap_match()` in [questionnaire_runtime_service.py](file:///d:/AI_voice/New%20folder%20(6)/Calling-Agent-SAAS-/backend/app/services/questionnaire_runtime_service.py).
* **Why**: If a caller asks *"चने के बीज का क्या भाव है?"*, we need to match it against approved FAQ reference rows without using a slow vector database.
* **How it works**:
  - Drops grammatical stopwords (`_MATCH_STOPWORDS`: *जी, साहेब, का, की, के, है, में*).
  - Isolates distinctive semantic keywords (`_DISTINCTIVE_KEYWORDS`: *भाव, दर, एकड़, क्विंटल, किस्म*).
  - Calculates token intersection over union (Jaccard similarity). The highest scoring FAQ entry above threshold wins and is spoken aloud immediately.

### 5.3 G.711 $\mu$-law Companding Algorithm (ITU-T G.711)
* **Where**: [sarvam_telephony_service.py](file:///d:/AI_voice/New%20folder%20(6)/Calling-Agent-SAAS-/backend/app/services/sarvam_telephony_service.py).
* **Why**: Telephony networks transmit audio using 8-bit logarithmic samples at 64 kbps rather than uncompressed 16-bit linear PCM (128 kbps).
* **Formula**:
  $$F(x) = \operatorname{sgn}(x) \frac{\ln(1 + \mu |x|)}{\ln(1 + \mu)}, \quad \mu = 255$$
* **How it works**: Compresses high-amplitude sounds logarithmically and preserves resolution for low-amplitude human vocal frequencies. We use `audioop.lin2ulaw` to encode outgoing audio and `audioop.ulaw2lin` to decode incoming audio.

### 5.4 Dual-Tier Fallback Cascading Pattern
* **Architecture Pattern**:
  - **Tier 1 (Deterministic FSM)**: Checks if turn can be answered by the questionnaire script. (Takes ~1ms).
  - **Tier 2 (FAQ Semantic Matcher)**: Checks if turn matches an approved FAQ item. (Takes ~2ms).
  - **Tier 3 (LLM Generative Recovery)**: If and only if Tier 1 and Tier 2 fail, it queries Google Gemini with dynamic system context. (Takes ~800-1200ms).
* **Benefit**: Over 85% of conversation turns in a structured lead call are handled at Tier 1 and Tier 2, dropping average call latency below 200ms!

---

## 6. Top Viva Questions & Model Answers

### Q1: "Why did you build a hybrid architecture instead of simply piping all audio into ChatGPT or Gemini?"
> **Answer:**
> *"There are three major reasons: First, **Latency**. In telephonic conversations, any delay over 500ms feels like an unnatural lag. An LLM takes 1.5 to 3 seconds to generate a response, whereas our deterministic questionnaire engine executes in less than 2 milliseconds. Second, **Hallucination Control**. In enterprise workflows like agriculture seeds or admissions, an LLM might invent prices or eligibility terms. Our FSM guarantees 0% hallucination on core facts. Third, **Cost Efficiency**. Running an LLM API call on every single greeting, acknowledgement, and routine question increases operational cost by 10x."*

### Q2: "How does the system know when the customer has finished speaking?"
> **Answer:**
> *"We use an **Adaptive Voice Activity Detection (VAD) and Silence Window Algorithm** over the WebSocket stream. When the caller speaks, their 8kHz audio packets accumulate in a memory buffer. We dynamically calculate the silence window based on utterance length: for short answers (<1.5s of audio), we wait for **1.10s** of continuous silence; for longer answers like multi-part names or addresses, we expand the threshold to **1.35s**. Once this silence threshold is reached, we conclude speech input and dispatch the accumulated WAV buffer to Sarvam STT."*

### Q3: "What happens if a customer says they are busy or want a callback?"
> **Answer:**
> *"The system has a dedicated pre-turn regex intent detector (`is_callback_request`). It recognizes natural Indic phrases like 'थोड़ी देर बाद कॉल करो', 'उद्या फोन करा', or 'busy right now'. Instead of treating this as a rejection or continuing to ask questions, it promises a callback in the customer's native language, sets the call disposition in the database to `callback_requested` for our automated follow-up dialer, and terminates the carrier call cleanly."*

### Q4: "Why do we use 8000 Hz mu-law audio instead of 44100 Hz MP3 or 16000 Hz WAV?"
> **Answer:**
> *"Public Switched Telephone Networks (PSTN) operate under the international standard ITU-T G.711. Telephony carrier trunks like VoBiz and Twilio exchange audio in G.711 $\mu$-law format at 8000 samples per second, 8 bits per sample (64 kbps). Streaming higher sample rates like 44.1kHz or compressed MP3 is incompatible with carrier streaming codecs and causes severe audio distortion."*

### Q5: "How does the agent prevent duplicate questions or getting stuck in a loop?"
> **Answer:**
> *"The orchestrator maintains a set of `asked_indices` extracted from the conversation history using normalize-for-match algorithms. The function `next_unasked_question()` always advances to the lowest index that has not been spoken yet. Furthermore, if a customer gives a conversational filler like 'ठीक है' without answering, the orchestrator detects this via regex and politely re-prompts the specific pending question instead of advancing blindly or repeating earlier questions."*

### Q6: "How do you reconstruct the audio recording when calls are streamed as live chunks?"
> **Answer:**
> *"During the call, incoming user chunks and synthesized agent audio chunks are sequentially buffered with relative timestamps. Upon call termination, `storage/audio_generator.py` aligns the two audio tracks chronologically into a dual-channel or merged 8kHz mono WAV container and persists it to disk/S3 so managers can review the recording from the frontend dashboard."*

---

## 7. Viva Day Checklist & Demo Tips

1. **Keep the local server ready**:
   - Backend: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
   - Frontend: `npm run dev`
2. **Show the Live Dashboard**: Point out the active lines indicator, Indic Neural TTS status (`Hi/En/Mr/Ta`), and response time KPI (<200ms).
3. **Show a Real Transcript**: Open Call History, click on an interested call (e.g. `Samruddhi Agritech Lead Executive`), and show how the transcript is color-coded by speaker with accurate timestamps.
4. **Show the Questionnaire Builder**: Demonstrate how easily a business can configure 5 questions in Marathi or Hindi and have the agent conduct that call without code changes.
5. **Confidence is Key**: Use technical terms confidently — *ITU-T G.711 $\mu$-law companding, Full-Duplex WebSockets, Finite State Machine, Token-Overlap Jaccard Matching, Adaptive VAD Silence Thresholding*.
