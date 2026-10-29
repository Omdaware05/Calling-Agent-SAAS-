# Transcript Analyzer — offline lead intelligence in ONE Python file

`model/transcript_analyzer.py` analyzes a call transcript and returns:

1. **Classification** — `INTERESTED` / `NOT_INTERESTED` / `CALLBACK_REQUESTED` /
   `NEEDS_INFORMATION` / `UNCERTAIN` (+ binary interested / not interested)
2. **WHY** — categorized reasons, each with the customer's exact words as
   evidence. Interested: asked about price, agreed to demo, wants details,
   expressed need, ready to proceed… Not interested: said no, opt-out/DNC,
   already has a product, price too high, no need, busy, trust concern,
   wrong number…
3. **Customer information extracted from the conversation** — name, phone,
   email, city, budget (normalized to INR; "2 lakh" → 200000), preferred
   callback time, product interest, business type. Extracted from *customer*
   turns only, so the agent's pitch never contaminates the data.
4. **Lead score 0–100** (opt-out = 0).
5. **Excel download** — a real `.xlsx` with sheets **All Results /
   Interested / Not Interested / Follow-ups**, or a single filtered sheet,
   ready to use "according to our need".

## Offline & low-end — by design

- **Python standard library only.** No pip installs, no internet, no API key,
  no GPU, no model download. Python 3.8+ on any PC, even low-end:
  ~40 ms per transcript, a few MB RAM.
- If the repo's richer classifier (`model/classifier/`, needs pydantic) is
  importable it is used for classification; otherwise the analyzer's built-in
  multilingual lexicon engine (English + Hindi Roman/Devanagari + Marathi)
  takes over automatically — same output shape either way.
- The `.xlsx` writer is also stdlib-only (zip + XML), verified to open in
  Excel and openpyxl.

## Usage

```bash
# one transcript
python model/transcript_analyzer.py call1.txt

# a whole folder of transcripts -> Excel + JSON
python model/transcript_analyzer.py --dir data/transcripts \
    --excel leads.xlsx --json leads.json

# only interested customers
python model/transcript_analyzer.py --dir data/transcripts \
    --excel interested.xlsx --filter interested
# filters: all | interested | not_interested | followups
```

In Python:

```python
from transcript_analyzer import analyze_transcript, export_excel
result = analyze_transcript(transcript_text)
result["classification"]      # "INTERESTED"
result["why_interested"]      # [{"code", "reason", "evidence"}, ...]
result["why_not_interested"]  # same shape
result["customer_info"]       # name, phone, email, city, budget_inr, ...
result["lead_score"]          # 0..100
export_excel([result], "leads.xlsx")   # or which="interested"
```

## How it is wired into the SaaS backend

- `backend/app/services/lead_intelligence_service.py` runs the analyzer on
  every analyzed call (fully offline) and stores `customer_info`,
  `why_interested`, `why_not_interested` in the analysis result and the
  Lead's metadata; extracted **name/email/phone now fill the Lead row**
  (previously name/email stayed empty). Classification of record remains
  Gemini → local classifier, exactly as before. To run the whole backend
  offline, simply leave `GEMINI_API_KEY` empty — the local path takes over.
- **Excel download endpoint:** `GET /api/leads/export.xlsx`
  (optional `?status=interested` / `?status=not_interested` / `?tenant_id=…`)
  exports leads with the extracted customer info and why-reasons as columns.

## Tests

```bash
cd model
python -m unittest tests.test_transcript_analyzer -v   # stdlib only, no pytest needed
```

Covers English/Hinglish/Hindi-Devanagari classification, opt-out, callback,
wrong number, price objection, full info extraction, agent-speech isolation,
and Excel validity (all + filtered sheets).
