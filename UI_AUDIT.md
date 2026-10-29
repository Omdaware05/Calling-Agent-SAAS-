# UI Audit — frontend_1 vs backend (2026-10-29)

Scope: `frontend_1/src/**` against `backend/app/api/routes/*.py`, `backend/app/main.py`, `backend/app/models/*.py`. Every claim verified against the files named. No frontend code was changed by this audit.

## What the transcript-analyzer commit (7dfa543) already fixed vs what is still open

FIXED (backend side):
- Customer-info extraction did not exist end to end → `model/transcript_analyzer.py` now extracts name/phone/email/city/budget/callback-time and `lead_intelligence_service.py` stores it on the analysis + Lead (Lead `name`/`email` columns are now filled).
- No server-side Excel of leads with why-reasons → `GET /api/leads/export.xlsx?status=interested|not_interested` added.

STILL OPEN (frontend side — listed in full below):
- The UI still does not display the extracted name/email/city/budget or the why-interested / why-not reason lists (LeadsPage shows one truncated reasoning line; `LeadDocument` type lacks name/email/metadata).
- There is still no Not-Interested list/count/export view in the UI (backend deletes not-interested leads by design), no DNC list, no status filter on the Leads page, and the dead/broken items in section 2 are untouched.

---


## 1) MISSING — should be in the UI, is not (or only partially)

### Transcript analysis / WHY interested or not interested
- Partial only: `features/calls/CallDetailDrawer.tsx` shows status, confidence, `reasoning`, `rule_applied`, signals/keywords and follow-up info for ONE call (`GET/POST /calls/{id}/interest`, `backend/app/api/routes/calls.py:503-504`).
- No reason anywhere for NOT-interested calls as a list: backend deletes / never creates a Lead for them (`lead_intelligence_service.py`: lead created only if `is_interested and not opt_out`, otherwise existing lead deleted). No not-interested pipeline, list, count or export exists to show.
- `features/leads/LeadsPage.tsx` ("Interested Leads Pipeline"): reasoning is one truncated line (`line-clamp-1`); `interest_strength`, `signals`, `opt_out_detected`, `callback_requested`, `objection_detected` — all returned by `lead_intelligence_service.py` — are not shown.
- `features/calls/CallsPage.tsx`: no interest/disposition column at all (phone, state, provider, duration, initiated-at only); interest visible only after opening a call drawer. No filter by disposition/interest.

### Customer information extracted from calls
- None, end to end. The analyser returns no extracted name/email/budget/need (`lead_intelligence_service.py` returns only status/confidence/reasoning/signals/languages/keywords/followup/opt-out/callback), and creates the Lead with only `phone_number` — no `name`/`email`, although `backend/app/models/lead.py` has both.
- `LeadsPage.tsx` shows/exports no name or email; `LeadDocument` (`frontend_1/src/types/api.ts:378`) does not even declare `name`/`email`/`metadata`.
- `Contact.custom_fields` (`backend/app/models/contact.py`, `schemas/contact.py`) is never rendered: `ContactsPage.tsx` columns are phone, email, call turns, last-interest, registered only.

### Excel download filtered by interested / not-interested
- Client XLSX exists (`frontend_1/src/utils/excelExport.ts`, used by Leads/Calls/Follow-ups), but Leads export has NO status filter to split interested vs not-interested, no status dropdown on `LeadsPage.tsx` at all (only DataTable text search + all/day/week/month), and exports only already-loaded rows (cap below). Columns omit name/email.
- Calls Excel export (`CallsPage.tsx:76-88`) omits disposition, interest status, confidence and reasoning — the columns needed to work leads from Excel.
- Server CSV export exists (`backend/app/api/routes/reports.py:239`, `/reports/business/{id}/export?type=leads|calls`, includes Lead Reason/Status) but `ReportsPage.tsx:126` exposes only `type=leads`, only when a business is selected, with no status filter; the `calls` variant has no button.

### Callback scheduling visibility
- A page exists (`features/followups/FollowupsPage.tsx`, in Sidebar), but: no create/add-callback action anywhere (backend `followups.py` is also GET/PATCH only), no overdue / due-today / unscheduled filter, no calendar view.
- Backend `POST/GET /calls/{id}/analyze-followup|followup` (`calls.py:537-538`, 25-category detector) is never called — no function for it in `frontend_1/src/services/api/calls.ts`; only the follow-up block embedded in the interest payload is shown in `CallDetailDrawer.tsx`.

### DNC / opt-out visibility
- Backend sets `Contact.status="do_not_call"` on opt-out (`lead_intelligence_service.py`; `backend/app/models/contact.py`: `active, do_not_call, invalid`), but `ContactsPage.tsx` has no status column, no DNC filter/list, and no way to add/remove a number from DNC. `ContactResponse` does return `status` — the UI drops it.
- The interest payload's `opt_out_detected` is not displayed in `CallDetailDrawer.tsx`.

### Search / filter, pagination, empty & error states
- Leads: no agent filter (backend `leads.py` supports `agent_id`; `LeadsPage.tsx` calls `leadsApi.getLeads()` with no params), no status or score filter.
- Calls: search is phone-number only (`searchableKey="phone_number"`); no search by name/reason/transcript. Contacts/Follow-ups: text search over loaded rows only.
- Pagination is client-side only (`DataTable.tsx`, pageSize 10–12) over a capped fetch, so records beyond the cap are invisible AND absent from Excel export: Leads/Follow-ups send no limit → backend default `limit=50` (`leads.py`, `followups.py`); Calls `limit:100` (`CallsPage.tsx`); Contacts `limit:100` (`ContactsPage.tsx`). Backend lists return a bare list, no total count.
- No load-error state anywhere: `grep isError frontend_1/src/features` = 0 hits and `DataTable.tsx` has no error prop, so a failed query renders the empty state (e.g. "No leads captured yet") — indistinguishable from "no data". `components/ui/ErrorAlert.tsx` exists but is never used.
- Lead status vocabularies disagree: edit modal in `LeadsPage.tsx` offers new/contacted/qualified/converted/closed; backend `models/lead.py` uses new/interested/not_interested/qualified/closed — a lead cannot be set to interested/not_interested from the UI.

## 2) SHOULD NOT BE THERE — dead, broken, duplicated or misleading

### UI calling backend endpoints that do not exist (verified vs routes/*.py)
- Model Lab — USED in `ModelLabPage.tsx`, will 404: `services/api/modelLab.ts` calls `GET /api/model-lab/models/{id}`, `POST …/{id}/start|stop|test`, `POST /api/model-lab/terminal-logs/clear`, `POST /api/model-lab/session/start`, `POST …/session/{id}/turn|interrupt|end`, `GET /api/model-lab/benchmarks`, `POST /api/model-lab/telephony/call`, `POST /api/model-lab/classify-intent`. `backend/app/api/routes/general.py` defines only `GET /model-lab/models`, `/model-lab/gpu`, `/model-lab/runtime`, `GET /model-lab/terminal-logs`, `/model-lab/telephony/config`, `/model-lab/telephony/test-connection`.
- Model Config — USED in `ModelConfigPage.tsx`, will 404: `services/api/modelConfig.ts` calls `/api/model-providers/{id}/schema`, `GET|PUT /api/model-config/{type}`, `PATCH …/status`, `POST …/validate|test-draft|test|activate|deactivate`, `GET …/credentials-status|active`. Backend has only `GET /model-providers` (returns the model list, wrong shape) and `GET /model-config` (one runtime dict).
- `services/api/questionnaires.ts: importDocx → POST /questionnaires/import-docx` — no such route in `backend/app/api/routes/questionnaires.py` (only import-excel/excel-template); used by `features/questionnaires/DocxImportModal.tsx`, so that import always fails.
- Dead service functions (no backend; also unused by any page): `agents.ts: getAgentInterestAnalytics → GET /agents/{id}/analytics/interest`; `health.ts: getServiceHealth → GET /health/{service}` (backend `main.py` has only `GET /health`) and `getSystemInfo`.
- Invoices bypasses the API layer: `features/invoices/InvoicesPage.tsx:44,63,90,195` uses raw relative `fetch('/invoices…')` / `href="/invoices/…/pdf"` — not `apiClient`/`API_BASE_URL` (`services/api/client.ts`, default `http://localhost:8001`), no auth header, so it hits the frontend origin, not the backend. There is no `invoices.ts` service.

### Dead / orphan UI
- Header global search (`components/layout/Header.tsx`): input only sets local `searchQuery` state — no navigation, filtering or results. It does nothing.
- Orphan routes in `router.tsx` with no Sidebar entry: `/queue` (`QueuePage.tsx`, no link anywhere), `/model-lab`, `/settings/models`, `/settings/health`; `/active-calls` is reachable only from a Dashboard link.
- Unused components: `components/ui/ErrorAlert.tsx` and `features/dashboard/AgentSelectPopover.tsx` — 0 references elsewhere in `src`.

### Placeholder / fabricated data presented as real
- Model Lab "live terminal": backend `general.py:579` returns the same 4 hardcoded log lines on every call (timestamps regenerated); `ModelLabPage.tsx` polls it every 1.2s and renders it as a live terminal console.
- `LeadsPage.tsx:167`: leads with no reasoning display the invented text "Identified via post-call intent classifier." as if it were AI context.
- `features/health/HealthPage.tsx`: hard-coded fallback caller numbers `+918065354620` (VoBiz) and `+13344895368` (Twilio) shown when the API returns no number, plus hard-coded localhost service URLs (8000/8001/8002/9001) in a user-facing page.

### Duplicated / confusing navigation & exposed debug pages
- Health/debug page exposed as a normal route: `/settings/health` (`HealthPage.tsx`) — DB/Redis/MinIO/Dograh/GPU telemetry for end users; not linked, URL-only.
- Settings duplication: `/settings` already has tabs (Sarvam, VoBiz, Twilio, Transcript, Workspace in `SettingsPage.tsx`), yet separate routes `/settings/telephony`, `/settings/transcript`, `/settings/models`, `/settings/health` also exist; telephony config exists twice (Settings VoBiz/Twilio tabs AND Model Lab telephony config, both hitting `general.py`), and model configuration twice (Model Lab model list AND `ModelConfigPage`).
- Non-read-only "GET": opening `CallDetailDrawer.tsx` fires `GET /calls/{id}/interest`, which in `calls.py:503-538` is the same handler as `analyze-interest` — it re-runs analysis and can create/delete the lead and set DNC. A view action mutates data.
