# Nachla Agent — Comprehensive Gap Analysis Report

Generated: 2026-04-08 | Based on 3-agent parallel audit of entire codebase

---

## Overall Status: ~70% Complete

Core calculation logic, workflow engine, React frontend, and Claude API integration are built. Critical gaps exist in integrations, data completeness, validation, and production hardening.

---

## BLOCKING ISSUES (Must fix before any real usage)

### B1. Monday.com Integration — All Methods Raise NotImplementedError
- **Files:** `src/integrations/monday_client.py` lines 102, 136, 161, 193
- **Impact:** No workflow status updates, no file attachments to Monday items
- **Fix:** Wire MCP calls or reimplement via REST API

### B2. Settlement/Priority Area Table — Only 80 of ~450 Settlements
- **Files:** `src/tools/priority_areas.py` (~60 entries), `src/tools/lookup_tables.py` (~15 entries)
- **Impact:** ~75% of nachlas get no priority area classification, missing discounts
- **Fix:** Obtain full RMI settlement classification list, load from reference file

### B3. Hebrew PDF Extraction — Never Validated with Real Documents
- **Impact:** Unknown if Docling/pdfplumber actually works on Hebrew planning docs and survey maps
- **Fix:** Test with 5 real Hebrew documents (expert review #6 go/no-go requirement)

### B4. Job Persistence — In-Memory Only, No Database Usage
- **Files:** `src/api/jobs.py` uses `dict[str, Job]` in memory
- **Impact:** Server restart loses all jobs. Not suitable for production.
- **Fix:** Persist jobs to PostgreSQL (tables already defined in `src/config/database.py`)

### B5. Pre-1965 Building Exemption — Not Checked in Calculation Tools
- **Files:** `src/tools/calc_dmei_heter.py`
- **Impact:** Pre-1965 buildings may be incorrectly charged permit fees
- **Fix:** Add `is_pre_1965` check before applying fees

### B6. Attic Height Rule — Not Enforced
- **Files:** System prompt documents ">1.80m" rule, model has `attic_usable` flag, but tools ignore it
- **Impact:** Unusable attics get charged as full area
- **Fix:** Check `attic_usable` in sqm equivalent and fee calculations

### B7. Permit Fee Cap — Function Exists But Never Called
- **Files:** `src/tools/calc_dmei_heter.py` has `check_permit_fee_cap()` but it's not called in workflow
- **Impact:** Total fees may exceed RMI decision 1523 cap
- **Fix:** Call after summing all building permit fees in `_run_calculations()`

### B8. Calculation Tool Registration — Silent Failure
- **Files:** `src/agent/main_agent.py` line 269
- **Impact:** If any tool module import fails, ALL tools silently unregistered. Agent becomes non-functional.
- **Fix:** Fail loudly with explicit error instead of `return`

### B9. No React Error Boundary
- **Files:** `frontend/src/App.tsx`
- **Impact:** Any component crash shows blank white page with no recovery
- **Fix:** Add ErrorBoundary component wrapping Routes

### B10. Calculation Error Recovery — Errors Silently Buried
- **Files:** `src/agent/main_agent.py` `_calc_*` methods
- **Impact:** Tool failure logged but result dict contains `{"error": "..."}` which cascades into report with missing data, no user warning
- **Fix:** Add retry logic using `settings.max_tool_retries`, surface errors to user

### B11. No API Key Validation at Job Intake
- **Files:** `src/api/jobs.py` line 220 — only logs warning if key missing
- **Impact:** User submits job, uploads files, waits — then job fails silently because no LLM
- **Fix:** Check API key in `create_job` endpoint, return clear error to frontend

---

## MEDIUM ISSUES (Should fix before launch)

### M1. Building Data Validation Incomplete
- **Files:** `src/models/building.py`
- **Gap:** No check for: pre_1965 + permit_year contradiction, pergola_roof_type required when pergola_area > 0, basement_type required when basement_area > 0
- **Fix:** Add Pydantic model validators

### M2. LLM-Returned Building Data Not Validated
- **Files:** `src/agent/main_agent.py` `analyze_uploaded_documents()`
- **Gap:** LLM can return invalid enum values or contradictory combinations
- **Fix:** Validate against Building model before appending to list

### M3. RBAC Defined But Not Enforced
- **Files:** `src/config/security.py` has permission matrix, routes don't check it
- **Fix:** Add middleware or decorator to protected routes

### M4. Data Freshness Check Never Called
- **Files:** `src/config/settings.py` has `check_data_freshness()` but workflow doesn't use it
- **Fix:** Call in `_run_intake()` and warn user if rates are stale

### M5. Betterment Levy Always Runs (Should Be Optional)
- **Files:** `src/agent/main_agent.py` line 801
- **Gap:** Phase 11 runs for every job even when not relevant
- **Fix:** Make conditional on client_goals or building statuses

### M6. Agricultural Building Phase Is a Stub
- **Files:** `src/agent/main_agent.py` lines 791-798
- **Gap:** Just marks complete without calculations
- **Fix:** Implement agricultural building-specific logic

### M7. Basement Coefficient Inconsistency
- **Gap:** System prompt says 0.3 (service) or 0.7 (residential), model supports both, but tools may apply inconsistently
- **Fix:** Audit all tools that use basement coefficient

### M8. 808 SQM Dynamic Calculation — Not Guaranteed
- **Gap:** Config has static 808, code mentions dynamic calc for non-standard nachlas but not enforced
- **Fix:** Implement and test dynamic 808 calculation in `calc_sqm_equivalent.py`

### M9. File Upload Progress — No Feedback
- **Files:** `frontend/src/lib/api.ts` `uploadFiles()`
- **Gap:** Large files (up to 50MB) upload with no progress indicator
- **Fix:** Use XMLHttpRequest with progress events or chunked upload

### M10. Frontend Dockerfile Missing HEALTHCHECK
- **Files:** `frontend/Dockerfile`
- **Fix:** Add `HEALTHCHECK CMD curl -f http://localhost:3000/ || exit 1`

### M11. CI/CD Missing Frontend Tests
- **Files:** `.github/workflows/ci.yml`
- **Gap:** Only Python tests run. No TypeScript compilation, ESLint, or React tests
- **Fix:** Add `npm run build` and `npx tsc --noEmit` steps

### M12. Workflow Documentation Outdated
- **Files:** `docs/agent_workflow_flow.md`, `CLAUDE.md`
- **Gap:** Docs say "14 steps" but code has 16 phases. Checkpoint not documented.
- **Fix:** Update docs to match implementation

### M13. Docker Compose Frontend Health Wait
- **Files:** `docker-compose.yml` line 48
- **Gap:** Frontend `depends_on: - app` has no `condition: service_healthy`
- **Fix:** Add health condition like the app service has

### M14. Rates Config Missing Some Values
- **Files:** `src/config/rates_config.json`
- **Gap:** Missing: betterment levy rate, PLACH commercial value lookup, permit fee cap amount
- **Fix:** Add missing rates with effective dates

---

## LOW / DEFERRED ITEMS (Phase 3+ or cleanup)

### L1. Govmap Scraping — Stub (Phase 3+)
- `govmap_scraper.py` returns None. Manual taba input works as interim. Deferred by design.

### L2. Chainlit UI — Dead Code
- `src/ui/app.py`, `auth.py`, `components.py` — replaced by React frontend. Should remove.

### L3. Excel Reader Helper Methods — Incomplete
- `src/documents/excel_reader.py` has undefined helper methods. Workaround: hardcoded lookup tables.

### L4. Redis — Configured But Not Used
- Docker runs Redis, settings define URL, but nothing connects to it. Deferred to Phase 5.

### L5. Golden Test Rate Validation
- Golden cases have hardcoded rates that may not match current rates_config. No cross-validation test.

### L6. OCR Engine Import Handling
- `src/documents/ocr.py` engine imports not wrapped in try-except. Missing engines crash instead of fallback.

### L7. PDF Parser Error Handling
- `pdf_parser.py parse()` doesn't handle exceptions from sub-methods gracefully.

### L8. Scanned PDF Detection Heuristic
- Uses `len(text) < 50` as scanned indicator. Short-text PDFs misidentified.

### L9. Hardcoded Mock Data in Frontend
- `api.ts fetchJobs()` catches ALL errors and returns mock data. Should only mock in development.

### L10. No Offline Detection in Frontend
- No network status indicator. Forms can be submitted with no network.

### L11. useWizard + WizardContext Duplication
- Two state systems for wizard steps. Works but poor architecture.

### L12. Nginx Missing CSP Header
- Has X-Frame-Options but no Content-Security-Policy.

### L13. No Frontend Unit Tests
- Zero React component tests exist.

### L14. No E2E Tests
- No Playwright/Cypress tests for full user flows.

### L15. rates_config.json Effective Dates Stale
- Some effective_date fields are 2020-era. Need review.

### L16. Promptfoo LLM Evaluation — Not Implemented
- CLAUDE.md mentions promptfoo for testing. Never set up.

### L17. Google Drive / OneDrive — Client Logic Unverified
- Client classes exist, routes wire them, but actual upload/download not tested end-to-end.

### L18. Database Migrations (Alembic) — Not Set Up
- Database tables defined in code but no migration system.

### L19. Rate Limiting — Config Exists, No Middleware
- `settings.rate_limit_per_minute = 60` but no enforcement.

### L20. PostgreSQL Credentials in .env
- Real dev credentials checked into `.env`. Should use `.env.example` pattern only.

---

## SUMMARY COUNTS

| Severity | Count |
|----------|-------|
| BLOCKING | 11 |
| MEDIUM | 14 |
| LOW/DEFERRED | 20 |
| **TOTAL** | **45** |

## RECOMMENDED PRIORITY ORDER

### Immediate (before any real user testing):
1. B2 — Get full 450-settlement table
2. B5 + B6 — Fix pre-1965 and attic exemptions in calc tools
3. B7 — Call permit fee cap after calculations
4. B8 — Make tool registration fail loudly
5. B10 — Add calculation retry logic
6. B11 — Validate API key at job intake

### Short-term (before beta launch):
7. B3 — Test Hebrew PDF extraction with real docs
8. B4 — Persist jobs to PostgreSQL
9. B1 — Wire Monday.com integration
10. B9 — Add React Error Boundary
11. M1-M2 — Building data validation
12. M3 — Enforce RBAC in routes

### Medium-term (before production):
13. M4-M8 — Domain logic fixes
14. M9-M14 — Infrastructure hardening
15. L1-L20 — Cleanup and deferred features
