# Master Prompt for Autonomous Implementation

Copy everything below and paste it into a fresh Claude Code session opened in `C:\Users\Ofir\nachla-agent`.

Start Claude Code with: `claude --permission-mode acceptEdits`

---

## THE PROMPT (copy from here)

You are implementing the nachla-agent project — an AI agent for Israeli agricultural settlement feasibility studies. There is a comprehensive, triple-validated implementation plan that covers 45 gap items across 6 sprints.

**Your mission: Execute all 6 sprints to 100% completion. Do not defer anything. Do not ask for permission. Do not stop until every item is done.**

## Step 0: Read the Plan

Read these files FIRST before writing any code:
1. `docs/implementation_plan_v3_final.md` — the full plan (read every line)
2. `docs/gap_analysis_report.md` — the 45 gap items
3. `CLAUDE.md` — project standards and forbidden patterns

## Execution Rules

1. **Work sprint by sprint in order** (1→2→3→4→5→6). Do NOT skip ahead.
2. **For each sprint item**, implement it fully, test it, then move to the next item.
3. **After each sprint**, run the designated validator agent:
   - Sprint 1: spawn `validator-ux` agent to review all frontend changes
   - Sprint 2: spawn `validator-domain` agent to verify calculation accuracy
   - Sprint 3: spawn `validator-code` agent to check code quality
   - Sprint 4: spawn `validator-code` agent to check persistence patterns
   - Sprint 5: spawn `validator-code` agent to check integration patterns
   - Sprint 6: spawn ALL THREE validator agents in parallel
4. **After each sprint**, run a smoke test: `python -m pytest tests/ -v --ignore=tests/test_documents.py` and fix any failures YOU caused.
5. **After each sprint**, rebuild Docker and verify: `docker compose up -d --build frontend` (for Sprint 1) or `docker compose up -d --build` (for later sprints).
6. **After each sprint**, commit and push: descriptive commit message with sprint number.
7. **Track progress** using TaskCreate/TaskUpdate tools. Create tasks for each sprint item.
8. **Use specialized agents** for heavy work:
   - `calc-builder` agent for Sprint 2 (calculation tool changes)
   - `ui-builder` agent for Sprint 1 (frontend changes)
   - `integration-builder` agent for Sprints 4-5 (database, Monday.com)
   - `agent-builder` agent for Sprint 3 (validation, error handling)
9. **Never hardcode** regulatory constants — always use `rates_config.json`
10. **Never let Claude do math** — all calculations must be deterministic Python tools
11. **All user-facing text in Hebrew**, error messages in English for logs
12. **Test after every file edit** — don't batch untested changes

## Items Confirmed Already Resolved (DO NOT re-implement)

These were found to already be working in the codebase by the Opus validators:
- M3 (RBAC enforcement) — `src/api/middleware.py` has working `AuthMiddleware`
- M4 (data freshness check) — `src/agent/main_agent.py:527` calls `check_data_freshness()`
- L19 (rate limiting) — `src/api/middleware.py` has `RateLimitMiddleware`
- B7 (permit fee cap) — `src/agent/main_agent.py:976` calls `check_permit_fee_cap()`. AUDIT correctness, don't re-implement.

## Sprint 1: Frontend Fixes (Fixes B9, M9, M10, M13, L9, L10, L12 + scroll issue)

Use the `ui-builder` agent for this sprint.

### 1.1 Sticky Mobile Navigation
- File: `frontend/src/components/ui/FormNav.tsx`
- On viewports < 640px: make nav bar `sticky bottom-0` with parchment background + blur
- Also apply to ConfirmPage.tsx inline nav and CheckpointPage.tsx approve button
- TEST: open Chrome at 1920x1080, verify button visible without scrolling on ALL pages

### 1.2 React Error Boundary
- Install `react-error-boundary` in frontend
- Create `frontend/src/components/ErrorBoundary.tsx` reusing existing `ErrorState` component
- Wrap `<App />` in `main.tsx`

### 1.3 File Upload Progress
- Create `uploadFilesWithProgress(jobId, files, onProgress)` in `frontend/src/lib/api.ts` using XMLHttpRequest
- Add progress state to `ConfirmPage.tsx` (NOT UploadSlot — upload happens during confirm)
- Split "שולח..." into "שולח נתונים..." then "מעלה קבצים... {n}%"

### 1.4 Mock Data — Dev Only
- In `frontend/src/lib/api.ts` `fetchJobs()`, gate MOCK_JOBS behind `import.meta.env.DEV`

### 1.5 Offline Detection
- Create `frontend/src/hooks/useOnlineStatus.ts` using `useSyncExternalStore`
- Show Hebrew banner in AppHeader when offline
- Disable "התחל ניתוח" on ConfirmPage when offline

### 1.6 Nginx Healthcheck + CSP + Docker Health
- Add `/healthz` to `frontend/nginx.conf`
- Add HEALTHCHECK to `frontend/Dockerfile`
- Add CSP header to `nginx.conf`
- Update `docker-compose.yml`: frontend depends_on app with condition: service_healthy

### 1.7 TanStack Query Retry
- Update `frontend/src/hooks/useJobPolling.ts`: no retry for 4xx, exponential backoff for 5xx

**After Sprint 1:** Spawn `validator-ux` agent. Rebuild Docker. Commit: "Sprint 1: Frontend fixes — sticky nav, error boundary, upload progress"

## Sprint 2: Domain Data (Fixes B2, B5, B6, M8, M14 + Decision 1553, taba conflicts, dev costs)

Use the `calc-builder` agent for this sprint.

### 2.1 Settlement Table
- Create `data/reference/settlements_priority.json` with all ~450 settlements (research from RMI official sources at apps.land.gov.il)
- Update `src/tools/priority_areas.py` to load from JSON file instead of hardcoded dict
- Add fuzzy Hebrew name matching

### 2.2 Pre-1965 Exemption
- In `src/tools/calc_dmei_heter.py`: add early return when `is_pre_1965=True` (exempt from permit fees only)
- NOTE: `permit_year` != `construction_year`. Pre-1965 building CAN have a permit for expansion.

### 2.3 Attic Height Rule
- Add `attic_usable: 1.0`, `attic_unusable: 0.0` to rates_config.json coefficients
- Enforce in calc_sqm_equivalent, calc_dmei_heter, calc_dmei_shimush

### 2.4 Decision 1553 Caps
- Add `priority_cap_per_unit: 450000`, `priority_cap_two_units: 900000` to rates_config.json
- Implement 1553 branch in `check_permit_fee_cap()`

### 2.5 Dynamic 808 SQM
- Always calculate dynamically in `calc_sqm_equivalent.py`, warn if different from 808

### 2.6 Missing Rates
- Add betterment_levy_rate, attic coefficients, Decision 1553 caps
- Review existing effective_dates for staleness

### 2.7 Taba Conflict Resolution
- Add logic: later overrides earlier, parcel-specific overrides comprehensive

### 2.8 Dev Cost Wiring
- Wire `lookup_development_costs()` into hivun phase in main_agent.py

### 2.9 Hebrew PDF Validation
- Test with real Hebrew documents. Document results as go/no-go.

**After Sprint 2:** Spawn `validator-domain` agent. Run golden tests. Commit: "Sprint 2: Domain data — settlements, pre-1965, attic, Decision 1553"

## Sprint 3: Validation & Error Handling (Fixes B8, B10, B11, M1, M2, M5, M6, M7)

Use the `agent-builder` agent for this sprint.

### 3.1 Building Pydantic Validators
- Add cross-field validators to `src/models/building.py`

### 3.2 LLM Output Validation
- Wrap LLM results in Building.model_validate() with try/except

### 3.3 Tool Registration — Fail Loudly
- Required tools crash on import failure, optional tools skip with warning

### 3.4 Calculation Error Classification
- CalculationInputError (don't retry) vs TransientError (retry)

### 3.5 API Key Check at Intake
- FastAPI dependency returning 503 if ANTHROPIC_API_KEY missing

### 3.6 Betterment Levy Conditional
- Run only when non-compliant buildings OR taba increases rights

### 3.7 Agricultural Building Logic
- Exempt from permit fees, 2% usage rate

### 3.8 Basement Coefficient Audit
- Add test cases for 0.3 (service) vs 0.7 (residential) across all tools

### 3.9 Path Traversal Fix
- Verify download endpoint path is within output_directory

### 3.10 Fix cloud_export Bug
- Change `job_queue.get_job()` to `await job_queue.get_status()`

**After Sprint 3:** Spawn `validator-code` agent. Run pytest. Commit: "Sprint 3: Validation — building validators, error handling, security fixes"

## Sprint 4: Job Persistence & API (Fixes B4, L18)

Use the `integration-builder` agent.

### 4.1 PostgreSQL Job Persistence
- Write state transitions to DB alongside in-memory
- Checkpoint recovery: CHECKPOINT jobs → FAILED on restart
- Set up Alembic with `alembic stamp head` for existing schema

### 4.2 Job Listing Endpoint
- Add `GET /api/v1/jobs` returning real jobs from DB

### 4.3 Cloud Storage Verification
- Test gdrive_client and onedrive_client with real credentials

### 4.4 Report Template Verification
- Generate sample report, verify Hebrew quality, check all disclaimers

**After Sprint 4:** Spawn `validator-code` agent. Test server restart recovery. Commit: "Sprint 4: Job persistence, API completeness"

## Sprint 5: External Integrations (Fix B1)

Use the `integration-builder` agent.

### 5.1 Monday.com GraphQL Implementation
- Replace NotImplementedError with real httpx GraphQL calls
- Remove stale `except NotImplementedError` catch in retry wrapper
- Wire status updates at each phase transition in _run_job()

**After Sprint 5:** Spawn `validator-code` agent. Commit: "Sprint 5: Monday.com integration"

## Sprint 6: Testing, CI/CD, Cleanup

### 6.1 GitHub Actions CI
- Python job + Frontend job + Docker build job

### 6.2 Documentation Update
- CLAUDE.md, workflow docs, deployment guide

### 6.3 Cleanup
- Remove src/ui/ dead Chainlit code
- Ensure .env is gitignored properly

### 6.4 Test Coverage
- Basement coefficient tests, MAMAD exemption tests, golden rate validation, API contract tests

**After Sprint 6:** Spawn ALL THREE validators in parallel. Run full E2E test. Final commit: "Sprint 6: Testing, CI/CD, production readiness"

## Final Steps

After all 6 sprints:
1. `docker compose down && docker compose up -d --build`
2. Test full flow in browser: Dashboard → Intake → Upload → Confirm → Processing → Checkpoint → Results → Download
3. `git push origin master`
4. Report completion status

**BEGIN NOW. Start with Sprint 1.1 (Sticky Mobile Navigation).**
