# Expert Review - Consolidated Report
## 3 Opus Specialists Reviewed the Agent Architecture

---

## P0 - CRITICAL (Must fix before any development)

### 1. Missing: National Priority Area Module (אזורי עדיפות לאומית)
**Source: Domain Expert**

Without this, the agent gives wrong results for ~40% of Israeli nachala properties.

Priority areas affect ALL calculations differently:
| Payment Type | Standard | Priority A | Priority B | Frontline |
|---|---|---|---|---|
| דמי היתר | 91% | 91% × (1-51%) | 91% × (1-25%) | 91% × (1-31%) |
| היוון 3.75% | 3.75% | Discounted | Discounted | Discounted |
| דמי רכישה 33% | 33% | 20.14% | 20.14% | Lower |
| פיצול | 33% | 16.39% (up to 160sqm) | 16.39% | Lower |
| דמי שימוש | 5% | **3%** (not 5%) | **3%** | 3% |

**Impact:** Hundreds of thousands of ILS per report in peripheral areas.

**Fix:** Add a priority area lookup table (all settlements classified). Apply discounts to every calculation tool automatically.

---

### 2. VAT Rate is Wrong (1.17 should be 1.18)
**Source: Workflow Architect + Domain Expert**

The document uses 17% VAT (×1.17) throughout. Israeli VAT is **18% (×1.18)** as of 2025. This is already producing wrong calculations.

**Fix:** Make VAT a configurable parameter with effective date. Never hardcode tax rates.

---

### 3. All Hardcoded Constants Must Be Externalized
**Source: All 3 reviewers**

Constants that will change and are currently hardcoded:
| Constant | Current Value | Risk |
|---|---|---|
| VAT rate | 1.17 (wrong) | Changes by government decision |
| RMI permit rate | 91% | Can change by RMI decision |
| Hivun 3.75% | 3.75% | Policy constant |
| Hivun 33% | 33% | Policy constant |
| 808 sqm equivalent | 808 | **Not always fixed** (see #4) |
| Usage fee rate | 5% | Not always 5% (see #5) |
| Usage fee period | 7 years | Different per building type |

**Fix:** Create `rates_config.json` with all constants, their effective dates, and expiry dates. Every calc tool takes an optional `effective_date` parameter.

---

### 4. The 808 Constant is NOT Always Fixed
**Source: Domain Expert**

808 is the standard value for a 2.5 dunam plot with 375 sqm standard rights. But:
- If plot > 2.5 dunam (some tabas allow 3 dunam) → 808 increases
- If taba rights differ from 375 sqm → components change
- RMI uses 808 as default for standard nachala but it's a **derived value**, not absolute

**Fix:** Calculate 808 dynamically from taba rights data. Display warning if result differs from 808. Use 808 as fallback only when taba data is unavailable.

---

### 5. Usage Fees (דמי שימוש) Are Not Always 5%
**Source: Domain Expert**

| Usage Type | Rate |
|---|---|
| Residential (מגורים) | 5% |
| Agricultural deviation (חקלאי חורג) | 2% |
| PLACH (פל"ח) | 5% of **commercial** value (different base!) |
| Priority areas (residential) | **3%** not 5% |

Also missing: CPI indexation and late payment interest (can add 20-40%).

**Fix:** Make the rate type-dependent and area-dependent. Add indexation calculation.

---

### 6. Hebrew PDF Extraction Not Validated
**Source: Principal Engineer**

Docling "Good Hebrew support" claim is unverified. Hebrew PDF extraction is notoriously difficult (bidirectional text, ligatures, non-standard fonts in older government documents).

**Fix:** **Week 1 go/no-go test:** Extract text and tables from 5 real Hebrew planning documents using Docling. If it fails, the entire doc processing pipeline must be redesigned. Do this before any other development.

---

### 7. Only 110 Settlements in Reference Table (Need ~450)
**Source: Domain Expert**

Israel has ~450 moshavim. The table has 110. The agent will fail for **75% of nachala properties** due to missing price data.

**Fix:** Obtain the complete RMI price table covering all agricultural settlements.

---

### 8. Missing: Bar Reshut vs Chocher (בר רשות vs חוכר)
**Source: Domain Expert**

Most nachala owners are still "bar reshut" (permission holders), not "chocher" (leaseholders). A bar reshut **cannot split plots** without first establishing a lease agreement. This fundamentally changes the workflow.

Stage 0 asks "is the farm capitalized?" but doesn't ask about the legal status of land tenure.

**Fix:** Add mandatory field: "סוג הרשאה: בר רשות / חוכר לדורות / חוזה חכירה מהוון". Branch the workflow based on the answer.

---

## P1 - HIGH (Must fix before POC goes to production)

### 9. No Confirmation Checkpoint After Building Classification
**Source: Workflow Architect**

Classification errors cascade through every calculation. Currently the only review is at Step 13 (end), which is too late.

**Fix:** Add mandatory user confirmation after Step 3: "Found X buildings, Y deviations. Confirm before calculating fees."

---

### 10. Missing Building Types in Classification
**Source: Domain Expert**

Not covered: קומת עמודים (open/closed), מרתף (service vs residential), עליית גג, מבנים ארעיים/קלים/ניידים (caravans), סככות פתוחות, pre-1965 buildings (exempt from permit).

**Fix:** Expand classification table. Add pre-1965 exemption check.

---

### 11. No Audit Trail / Calculation Log
**Source: Workflow Architect + Principal Engineer**

In a regulated domain, every number must trace back to source data and formula. Currently there's no logging mechanism.

**Fix:** Generate a companion "calculation log" document: each data source, each formula with inputs/outputs, each classification decision with reasoning, each user override.

---

### 12. Cut MCP Servers from 10+ to 4-5
**Source: Principal Engineer**

Redundancies identified:
- `server-filesystem` → redundant with SDK built-in Read/Write/Edit
- `server-fetch` → redundant with SDK built-in WebFetch
- `server-sequential-thinking` → prompt trick, no real value
- `@negokaz/excel-mcp-server` → only 4,500 downloads; use openpyxl directly
- `mcp-pdf` + Docling + pdfplumber → 3 PDF tools, pick 1 primary + 1 fallback
- `ultimate_mcp_server` → red flag, untested mega-dependency

**Recommended MCP list (keep only):**
| MCP Server | Why Keep |
|---|---|
| **@playwright/mcp** | Web scraping - no alternative |
| **@mondaycom/mcp** | Official, well-maintained |
| **Google Drive or OneDrive** (direct SDK, not hobby MCP) | Production reliability |
| **@mcp/server-memory** | Session persistence |

Everything else → custom Python tools (easier to test, debug, maintain).

---

### 13. Replace Hobby Cloud Storage MCPs with Direct SDKs
**Source: Principal Engineer**

- `piotr-agier/google-drive-mcp` → 39 GitHub stars, solo developer
- `ftaricano/mcp-onedrive-sharepoint` → small community project
- Microsoft deprecated their own OneDrive+SharePoint MCP (March 2026)

**Fix:** Use `google-api-python-client` and `msgraph-sdk` directly. These are maintained by Google and Microsoft. File upload is 10-20 lines of code each.

---

### 14. Add API/Job Queue Layer
**Source: Principal Engineer**

No REST API between frontend and agent. Cannot handle concurrent users, retry failed jobs, or decouple runtime from UI.

**Fix:** Add FastAPI + async job queue. Each report = a job. Agent runs in worker. Frontend polls for status.

---

### 15. Security Section Missing Entirely
**Source: Principal Engineer**

Missing: secrets management, RBAC, data isolation between users, file upload sanitization, immutable audit logging, Israeli privacy law compliance (חוק הגנת הפרטיות).

**Fix:** Add full security architecture before handling real client data.

---

### 16. Missing: RMI Permit Fee Discounts for Priority Areas
**Source: Domain Expert**

The document applies priority area discounts only to היוון but NOT to דמי היתר. Decision 1523 specifies discounts on permit fees too (51%/25%/31%).

**Fix:** Apply priority area discounts to ALL calculation tools, not just hivun.

---

### 17. Missing: Permit Fee Cap (תקרת דמי היתר)
**Source: Domain Expert**

RMI decision 1523 limits total permit fees per nachala. The agent doesn't mention this mechanism.

**Fix:** Add cap check after summing all permit fees.

---

## P2 - MEDIUM (Fix during development)

### 18. Step Ordering Issues
**Source: Workflow Architect**

- Step 10 (agriculture) too late → should be after Step 3, before calculations
- Step 11 (betterment levy) after Step 8 (summary table) → table has empty columns
- Steps 1 and 2 can only be partially parallel (building location needs taba data)

### 19. Missing Monday.com Statuses
**Source: Workflow Architect**

No "failed" or "waiting for client" statuses. Add: "חסר מידע - ממתין ללקוח" and "נכשל - דורש טיפול ידני".

### 20. Defer govmap.gov.il Scraping to Phase 3+
**Source: Principal Engineer**

govmap is an ArcGIS app with no documented API. The code samples in the blueprint won't work (no `#search-input` element exists). Reverse-engineering the REST endpoints requires significant effort.

**Fix:** Phase 1-2: manual taba data input. Phase 3+: govmap integration after contacting govmap team for API access.

### 21. Timeline is 2x Optimistic
**Source: Principal Engineer**

Realistic timeline: **16-24 weeks (4-6 months)**, not 8-12 weeks. Phase 2 alone (Hebrew PDF + survey maps + govmap + classification) is 6-8 weeks.

### 22. Missing: Basement/Attic/Ground Floor Classification
**Source: Domain Expert**

- Basement coefficient 0.7 is not always correct (0.5 for service basement)
- Attic (עליית גג) not mentioned at all
- Closed ground floor (קומת עמודים סגורה) needs explicit classification rules

### 23. Missing: Prior Permit Fee Purchase Date
**Source: Domain Expert**

When deducting previously purchased permit fees from 33% calculation, only fees paid **after 2009** (decision 979/1311) qualify. The agent asks IF fees were purchased but not WHEN.

### 24. Missing Report Disclaimers
**Source: Domain Expert**

Add:
- "Values based on RMI tables as of [date]. Actual value determined by RMI appraiser and may differ substantially."
- "Report validity: 6 months from date of issue."
- "Does not include priority area discounts [if not calculated] / includes priority area [X] discounts [if calculated]."

### 25. Missing: Aguda Approval for Split
**Source: Domain Expert**

Split and sale require approval from the moshav's cooperative association (אגודה שיתופית). This can block transactions.

### 26. @tool Decorator Code Samples Wrong
**Source: Principal Engineer**

The SDK examples in the blueprint don't match the actual Claude Agent SDK API signature. Must be rewritten.

### 27. Missing: Data Freshness Validation
**Source: Workflow Architect**

No check whether reference tables are current. If tables are stale, all calculations are wrong silently.

**Fix:** Add "last updated" timestamp check with warning if data > 90 days old.

### 28. Missing: Split Ownership / Inheritance
**Source: Workflow Architect**

Workflow assumes single owner. In practice, nachala ownership is frequently shared among heirs.

### 29. Missing: Process Timeline Estimates
**Source: Domain Expert**

Agent should provide estimated timelines: הסדרה (6-18 months), פיצול (12-36 months), היוון (3-12 months).

### 30. Missing: Development Cost Tables
**Source: Domain Expert**

היוון deducts "development costs" but the blueprint doesn't specify where these come from. There are tables by regional council.

---

## Summary: Action Plan

### Before Development (Week 0):
1. Fix VAT to 1.18 and externalize ALL constants
2. Validate Hebrew PDF extraction with 5 real documents (go/no-go)
3. Obtain complete RMI settlement table (450+ settlements)
4. Add "bar reshut / chocher" field to intake

### Phase 1 POC (Weeks 1-4):
5. Build priority area module (affects ALL calculations)
6. Build 6 calc tools with configurable rates + priority discounts
7. Add user confirmation checkpoint after building classification
8. Generate audit trail / calculation log
9. Cut MCP servers to 4-5

### Phase 2 Documents (Weeks 5-12):
10. Hebrew PDF parsing (validated in week 0)
11. Expand building classification (basement, attic, pre-1965, etc.)
12. Manual taba input (defer govmap scraping)

### Phase 3 Full Agent (Weeks 13-18):
13. govmap.gov.il integration (after API access secured)
14. Subagents + hooks
15. Full report with all disclaimers
16. Test with 25 examples

### Phase 4 Production (Weeks 19-24):
17. Security (RBAC, encryption, audit)
18. API layer + job queue
19. Direct Google/Microsoft SDK integration (replace hobby MCPs)
20. React frontend + PostgreSQL

**Total realistic timeline: 24 weeks (6 months)**
