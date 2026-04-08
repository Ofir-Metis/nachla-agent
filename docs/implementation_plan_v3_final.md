# Nachla Agent — Final Implementation Plan v3

## Based on: 3-agent gap analysis + 3-agent research + 3-agent Opus validation

---

## Validation Results Applied

Three Opus 4.6 validators reviewed plan v2 and identified 17 issues. All are addressed below:

- **validator-code:** 7 critical items — B3 moved earlier, checkpoint recovery added, path traversal fix, cloud_export bug, pre-1965 vs permit_year clarified, M3/M4/L19 acknowledged as already resolved
- **validator-domain:** 5 regulatory issues — Decision 1553 implementation detailed, taba conflict resolution added, dev cost wiring added, betterment trigger broadened, report disclaimers added
- **validator-ux:** 7 UX issues — Sprint order reversed (frontend first), sticky mobile nav added, upload progress rewritten, API contract tests added, cloud storage verified, job listing endpoint added

---

## Revised Sprint Order (User-Impact First)

| Sprint | Focus | Rationale |
|--------|-------|-----------|
| **1** | Frontend fixes + sticky nav | Unblocks user testing immediately |
| **2** | Domain data + calculations | Fix regulatory accuracy |
| **3** | Validation + error handling | Prevent bad data cascading |
| **4** | Job persistence + API completeness | Enable real usage |
| **5** | Monday.com + cloud storage | External integrations |
| **6** | Testing, CI/CD, cleanup | Production readiness |

After EVERY sprint: run full intake-to-results smoke test via browser.

---

## Sprint 1: Frontend Fixes (Unblock Users)

**Agent:** `ui-builder`
**Fixes:** B9, M9, M10, M13, L9, L10, L12 + scroll/nav issue

### 1.1 Sticky Mobile Navigation
- **File:** `frontend/src/components/ui/FormNav.tsx`
- On viewports < 640px: `position: sticky; bottom: 0; background: rgba(255,253,248,0.95); backdrop-filter: blur(4px); border-top: 1px solid #D8D0C4; z-index: 20;`
- Also apply to ConfirmPage inline nav buttons and CheckpointPage approve button
- Test on Chrome Windows at 1920x1080 (real viewport ~940px after chrome)

### 1.2 React Error Boundary
- Install `react-error-boundary`
- Create `frontend/src/components/ErrorBoundary.tsx` reusing `ErrorState` component
- Wrap `<App />` in `main.tsx` and individual route pages

### 1.3 File Upload Progress (Corrected)
- **Where:** Progress belongs in `ConfirmPage.tsx` (NOT UploadSlot — files are uploaded during confirm submission)
- Create `uploadFilesWithProgress(jobId, files, onProgress)` in `api.ts` using XMLHttpRequest
- Add `uploadProgress: number | null` state to ConfirmPage
- Split "שולח..." into two sub-states: "שולח נתונים..." then "מעלה קבצים... {n}%"
- Show progress bar between spinner and button

### 1.4 Mock Data — Development Only
- Gate `MOCK_JOBS` behind `import.meta.env.DEV`
- Production errors propagate to ErrorBoundary

### 1.5 Offline Detection
- Add `useOnlineStatus()` hook using `useSyncExternalStore`
- Show Hebrew banner in AppHeader when offline
- Disable "התחל ניתוח" button on ConfirmPage when offline

### 1.6 Nginx Healthcheck + CSP
- Add `/healthz` endpoint to `nginx.conf`
- Add HEALTHCHECK to `frontend/Dockerfile` using `wget`
- Add `Content-Security-Policy` header for Google Fonts + same-origin API
- Update `docker-compose.yml`: frontend `depends_on` app with `condition: service_healthy`

### 1.7 TanStack Query Retry
- No retry for 4xx, exponential backoff for 5xx
- Slow down polling after errors in `useJobPolling.ts`

### Sprint 1 Validation:
- `validator-ux` agent: verify scroll, sticky nav, Hebrew text
- Manual: full intake flow in Chrome Windows at 1920x1080

---

## Sprint 2: Domain Data Completeness

**Agent:** `calc-builder`
**Fixes:** B2, B5, B6, B7, M8, M14 + Decision 1553, taba conflicts, dev costs

### 2.1 Full Settlement Priority Area Table
- Source: Official RMI PDF from `apps.land.gov.il`
- Create `data/reference/settlements_priority.json` (~450 settlements)
- Replace hardcoded maps in `priority_areas.py` and `lookup_tables.py`
- Add fuzzy Hebrew name matching (strip niqqud, normalize whitespace)

### 2.2 Pre-1965 Exemption in Calc Tools
- Exempt from permit fees only (NOT usage, capitalization, purchase)
- **Clarification:** `permit_year` is NOT the same as `construction_year`. A pre-1965 building CAN have a post-1965 permit (for expansion). Validate against `construction_year`, not `permit_year`.
- Add audit trail: "pre-1965 construction — exempt from permit fees"

### 2.3 Attic Height Rule
- Add `attic_usable: 1.0` and `attic_unusable: 0.0` to `rates_config.json`
- Enforce in `calc_sqm_equivalent.py`, `calc_dmei_heter.py`, `calc_dmei_shimush.py`

### 2.4 Permit Fee Cap (Decision 1523 + 1553)
- **Verify existing call:** `main_agent.py` line 976 already calls `check_permit_fee_cap()`. Audit correctness rather than re-implementing.
- **Add Decision 1553 caps:** `priority_cap_per_unit: 450000`, `priority_cap_two_units: 900000` to `rates_config.json`
- Implement 1553 branch in `check_permit_fee_cap()`: if priority area, apply `min(fees, cap)`
- Add to system prompt so agent can explain the cap

### 2.5 Dynamic 808 SQM
- Always calculate dynamically, compare to 808, warn if different
- Yard tiers: effective (first 1000 * 0.25), remainder (next 1000 * 0.20), far (beyond * 0.10)

### 2.6 Missing Rates
- Add: `betterment_levy_rate: 0.50`, attic coefficients, Decision 1553 caps
- Review ALL existing effective_dates for staleness (some are 2020-era)

### 2.7 Taba Conflict Resolution (NEW)
- Add logic: later taba overrides earlier; parcel-specific overrides comprehensive
- When multiple tabas apply, select primary by: (1) most recent approval date, (2) most specific to plot
- Add `is_primary` field resolution in `_run_taba_analysis()`

### 2.8 Development Cost Wiring (NEW)
- Ensure `lookup_development_costs()` is called during hivun phase
- Pass result to both `calculate_hivun_375()` and `calculate_hivun_33()` in `main_agent.py`

### 2.9 Hebrew PDF Validation (Moved from Sprint 6)
- Test with 3-5 real Hebrew planning documents
- Verify text extraction, table extraction, Hebrew character order
- Go/no-go gate: if Hebrew extraction fails, document fallback plan

### Sprint 2 Validation:
- `validator-domain` agent: verify every calculation against RMI rules
- Run golden test cases against updated tools

---

## Sprint 3: Validation & Error Handling

**Agent:** `agent-builder` + `calc-builder`
**Fixes:** B8, B10, B11, M1, M2, M5, M6, M7

### 3.1 Building Data Validation (Pydantic)
- Add model_validators to `building.py`:
  - `construction_year < 1965` AND `is_pre_1965=False` → auto-correct to True
  - `is_pre_1965=True` AND `construction_year >= 1965` → raise ValueError
  - `building_type="agricultural"` AND `has_kitchen=True` → raise ValueError
  - `building_type="pool"` AND `basement_area_sqm > 0` → raise ValueError
  - `pergola_area_sqm > 0` AND `pergola_roof_type is None` → raise ValueError
  - `deviation_sqm > main_area_sqm` → raise ValueError (suspicious)
- NOTE: `is_pre_1965=True` with `permit_year >= 1965` is VALID (expansion permit)

### 3.2 LLM Output Validation
- Wrap LLM building dicts in `Building.model_validate()` with try/except
- Skip invalid buildings, log warnings
- Retry once with validation errors fed back to Claude

### 3.3 Tool Registration — Fail Loudly
- Define `REQUIRED_TOOLS` set. If required tool import fails, raise RuntimeError.
- Optional tools log warning and skip.

### 3.4 Calculation Error Classification
- `CalculationInputError(ValueError)` — bad input, don't retry
- `TransientError(RuntimeError)` — config file locked, retry
- Surface errors in report warning section

### 3.5 API Key Check at Intake
- FastAPI dependency: return 503 if ANTHROPIC_API_KEY missing
- Also warn at startup in lifespan handler

### 3.6 Betterment Levy — Conditional + Broadened
- Run when: non-compliant buildings exist OR new taba increases rights
- Skip when: all compliant AND no taba changes

### 3.7 Agricultural Building Logic
- Exempt from permit fees, usage fee rate = 2%
- Mark in building cards with appropriate action

### 3.8 Basement Coefficient Audit (M7)
- Test that 0.3 (service) and 0.7 (residential) are correctly applied across all tools
- Add explicit test cases for each basement type

### 3.9 Path Traversal Fix (Security)
- In download endpoint: verify resolved path is within `settings.output_directory`
- `if not str(resolved).startswith(str(output_root)): raise HTTPException(403)`

### 3.10 Fix cloud_export Bug
- `routes.py` calls `job_queue.get_job()` which doesn't exist — change to `await job_queue.get_status()`

### Sprint 3 Validation:
- `validator-code` agent: security, type safety, error handling
- Run full test suite

---

## Sprint 4: Job Persistence & API Completeness

**Agent:** `integration-builder`
**Fixes:** B4, L18 + job listing endpoint, cloud storage verification

### 4.1 Persist Jobs to PostgreSQL
- Keep asyncio tasks + write state transitions to DB
- **Checkpoint recovery:** Jobs stuck in CHECKPOINT state after restart → mark as FAILED with "שרת נכבה במהלך ממתין לאישור — יש להגיש מחדש"
- Add Alembic: `alembic init`, use `alembic stamp head` for existing schema
- Audit log entries also persisted to DB

### 4.2 Job Listing Endpoint (NEW)
- Add `GET /api/v1/jobs` endpoint to `routes.py`
- Query DB for all jobs, return list matching `JobSummary` frontend type
- Remove mock data fallback from frontend (already gated in Sprint 1.4)

### 4.3 Cloud Storage Verification (NEW)
- Test `gdrive_client.py` upload/download with real credentials
- Test `onedrive_client.py` upload/download with real credentials
- Add try/except in routes with Hebrew error messages if credentials missing

### 4.4 Report Template Verification (NEW)
- Verify `data/templates/סיכום בדיקת התכנות טמפלט.docx` produces correct output
- Generate sample report, review Hebrew quality
- Ensure all mandatory disclaimers from system prompt are in template
- Verify 6-month validity period is included

### Sprint 4 Validation:
- `validator-code` agent: DB patterns, API contracts
- Manual: submit job → restart server → verify job state preserved or gracefully failed

---

## Sprint 5: External Integrations

**Agent:** `integration-builder`
**Fixes:** B1

### 5.1 Monday.com Client
- Replace NotImplementedError with real GraphQL calls via httpx
- `read_item()`, `update_status()`, `post_update()`, `attach_file()`
- Remove stale `except NotImplementedError` catch in retry wrapper
- Wrap all calls in try/except — Monday failures NEVER block workflow
- Auth: `MONDAY_API_TOKEN` from .env

### 5.2 Monday.com Workflow Integration
- Call `update_status()` at each phase transition in `_run_job()`
- Call `attach_file()` after report generation
- Fire-and-forget pattern with logging

### Sprint 5 Validation:
- `validator-code` agent: integration patterns, error handling
- Manual: verify Monday.com board updates with real API token

---

## Sprint 6: Testing, CI/CD, Cleanup

**Agent:** `agent-builder`
**Fixes:** M11, M12, L2, L5, L13, L14, L16

### 6.1 CI/CD Pipeline
- Python job: ruff lint + pytest (with path-based filtering)
- Frontend job: TypeScript check + ESLint + Vite build
- Docker build job (depends on both)
- Use pip cache + npm cache

### 6.2 Documentation Update
- CLAUDE.md: 16 phases, document checkpoint, update file structure
- `docs/agent_workflow_flow.md`: match code
- Add `docs/deployment.md`: Docker instructions

### 6.3 Cleanup
- Remove `src/ui/` (dead Chainlit code)
- Rename `.env` to `.env.example` if it contains placeholders
- Ensure `.env` is in `.gitignore` (already is)

### 6.4 Test Coverage
- Add basement coefficient test cases (M7)
- Add MAMAD per-house exemption test
- Add golden test rate validation (compare expected vs calculated)
- Verify API contract: frontend types match backend response models

### Sprint 6 Validation:
- All 3 validators (code, domain, UX) — final gate
- Full end-to-end manual test: intake → upload → confirm → processing → checkpoint → results → download → cloud export

---

## Items Confirmed Already Resolved (from validator feedback)

| Gap ID | Claimed Missing | Actually |
|--------|----------------|----------|
| M3 | RBAC not enforced | `middleware.py` has working `AuthMiddleware` with RBAC |
| M4 | Data freshness never called | `main_agent.py:527` calls `check_data_freshness()` in `_run_intake()` |
| L19 | Rate limiting not implemented | `middleware.py` has `RateLimitMiddleware` |
| B7 | Permit fee cap never called | `main_agent.py:976` calls `check_permit_fee_cap()` — audit correctness, don't re-implement |

---

## Selective Validation Protocol (Revised)

Instead of 3 validators after every sprint:

| Sprint | Validators to Run |
|--------|------------------|
| 1 (Frontend) | `validator-ux` only |
| 2 (Domain) | `validator-domain` only |
| 3 (Validation) | `validator-code` only |
| 4 (Persistence) | `validator-code` only |
| 5 (Integrations) | `validator-code` only |
| 6 (Final) | ALL THREE validators |

Plus: smoke test the full intake-to-results flow after EVERY sprint.

---

## Total Items Addressed: 45/45

All 11 BLOCKING, 14 MEDIUM, and 20 LOW/DEFERRED items from the gap analysis are either:
- Explicitly planned in a sprint, OR
- Confirmed already resolved in the codebase, OR
- Explicitly deferred with documented rationale
