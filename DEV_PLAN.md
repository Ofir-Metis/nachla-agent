# Development Plan - Nachla Agent
## Multi-Agent Claude Code Build

---

## Architecture: How the Build Works

```
┌─────────────────────────────────────────────────────────────┐
│                    YOU (Team Lead)                            │
│  Launch each phase, review validator reports, approve/fix    │
└────────────────────────┬────────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
   ┌────────────┐ ┌────────────┐ ┌────────────┐
   │ Builder    │ │ Builder    │ │ Builder    │   ← Parallel in worktrees
   │ Agents     │ │ Agents     │ │ Agents     │
   │ (Opus 4.6) │ │ (Opus 4.6) │ │ (Opus 4.6) │
   └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
         │              │              │
         └──────────────┼──────────────┘
                        ▼
              ┌─────────────────┐
              │  Merge to main  │
              └────────┬────────┘
                       ▼
          ┌────────────┼────────────┐
          ▼            ▼            ▼
   ┌────────────┐┌────────────┐┌────────────┐
   │ Validator  ││ Validator  ││ Validator  │   ← 3 Opus reviewers
   │ CODE       ││ DOMAIN     ││ UX         │      read-only, find issues
   │ (security, ││ (formulas, ││ (Hebrew,   │
   │  arch,     ││  RMI rules,││  workflow, │
   │  quality)  ││  accuracy) ││  reports)  │
   └─────┬──────┘└─────┬──────┘└─────┬──────┘
         │             │             │
         └─────────────┼─────────────┘
                       ▼
              ┌─────────────────┐
              │  Fix Agent      │   ← Reads validator reports, fixes code
              │  (Opus 4.6)     │
              └────────┬────────┘
                       ▼
              ┌─────────────────┐
              │  Re-validate    │   ← Validators run again until clean
              └────────┬────────┘
                       ▼
              ┌─────────────────┐
              │  Phase Complete  │   ← Move to next phase
              └─────────────────┘
```

## Agent Roster

### Builder Agents (write code, run in worktrees):
| Agent | File | Scope |
|---|---|---|
| **calc-builder** | `.claude/agents/calc-builder.md` | Calculation tools, rates config, priority areas |
| **doc-builder** | `.claude/agents/doc-builder.md` | PDF parsing, Word generation, Excel reading |
| **integration-builder** | `.claude/agents/integration-builder.md` | Monday.com, OneDrive, Google Drive, govmap |
| **agent-builder** | `.claude/agents/agent-builder.md` | Main agent, system prompt, hooks, audit log |
| **ui-builder** | `.claude/agents/ui-builder.md` | Chainlit UI, FastAPI backend, job queue |

### Validator Agents (read-only, review code):
| Agent | File | Reviews |
|---|---|---|
| **validator-code** | `.claude/agents/validator-code.md` | Architecture, security, Python quality, tests |
| **validator-domain** | `.claude/agents/validator-domain.md` | Formula accuracy, RMI rules, regulatory completeness |
| **validator-ux** | `.claude/agents/validator-ux.md` | Hebrew quality, UX flow, report format, deliverables |

---

## Phase 0: Project Setup (Run Once)

### Step 0.1: Initialize project
```bash
cd nachla-agent
python -m venv venv
venv\Scripts\activate   # Windows
pip install claude-agent-sdk chainlit fastapi uvicorn pydantic
pip install docling pdfplumber python-docx docxtpl openpyxl pandas xlsxwriter
pip install playwright msgraph-sdk google-api-python-client
pip install pytest pytest-asyncio httpx
playwright install chromium
pip freeze > requirements.txt
```

### Step 0.2: Copy reference documents
```bash
# Copy the spec documents to docs/
cp ../agent_workflow_flow.md docs/
cp ../technical_blueprint.md docs/
cp ../expert_review_consolidated.md docs/

# Copy example reports to tests/golden/
cp -r "../בדיקות התכנות" tests/golden/

# Copy reference tables to data/reference/
cp "../טבלאות חומרים"/*.xlsx data/reference/
cp "../חומרים נוספים"/*.pdf data/reference/

# Copy Word template
cp "../חומרים נוספים/סיכום בדיקת התכנות טמפלט.docx" data/templates/
cp "../בדיקות התכנות/טמפלט/תחשיבים טמפלט.xlsx" data/templates/
```

### Step 0.3: Hebrew PDF validation (GO/NO-GO)
```bash
# Test Docling with 5 real Hebrew PDFs
python -c "
from docling.document_converter import DocumentConverter
converter = DocumentConverter()
for pdf in ['data/reference/טבלה של משרד החקלאות.pdf']:
    result = converter.convert(pdf)
    print(result.document.export_to_markdown()[:500])
"
```
If Hebrew extraction fails → fall back to PyMuPDF + pdfplumber before proceeding.

### Step 0.4: Initial commit
```bash
git add -A
git commit -m "Initial project setup with structure, agents, and reference data"
git push -u origin main
```

---

## Phase 1: Calculation Engine + Config (Weeks 1-4)

### What gets built:
- `rates_config.json` with all constants
- 8 calculation tools with priority area support
- Data models (Pydantic)
- Lookup tools for reference tables
- Unit tests for all calculations

### Builder agents to run (in parallel worktrees):

**Agent 1: calc-builder**
```
Prompt: "Read docs/agent_workflow_flow.md and docs/technical_blueprint.md.
Build ALL calculation tools in src/tools/ and the rates_config.json.
Include priority area discounts for every calculation.
Test with values from the example reports in tests/golden/.
Run pytest to verify all tests pass."
```

**Agent 2: agent-builder** (models only in this phase)
```
Prompt: "Read docs/agent_workflow_flow.md.
Build Pydantic data models in src/models/ for: Building, Nachla, Taba, Report.
Include all fields mentioned in the workflow steps 0-3.
Include enums for: BuildingType, AuthorizationType, PriorityArea, BuildingStatus."
```

### After build - run 3 validators:
```
Launch validator-code, validator-domain, validator-ux (read-only, opus 4.6)
Each reviews the Phase 1 code and produces a findings report.
Fix agent addresses all findings. Re-validate until clean.
```

### Phase 1 exit criteria:
- [ ] All 8 calc tools pass unit tests
- [ ] rates_config.json has all constants with dates
- [ ] Priority area discounts work on all calculations
- [ ] Validator-code: PASS
- [ ] Validator-domain: PASS (all formulas correct)
- [ ] Validator-ux: N/A this phase

---

## Phase 2: Document Processing + Word Template (Weeks 5-8)

### What gets built:
- PDF parser with Hebrew validation
- Excel reader for reference tables
- Word report generator (docxtpl)
- Excel report generator
- Audit log generator

### Builder agents:

**Agent 1: doc-builder**
```
Prompt: "Read docs/technical_blueprint.md section 3.
Build document processing in src/documents/.
Test PDF parsing with Hebrew documents in data/reference/.
Build Word report generator using the template in data/templates/.
Add Jinja2 tags to the Word template for all dynamic fields from the workflow."
```

**Agent 2: agent-builder** (audit log)
```
Prompt: "Build src/agent/audit_log.py - immutable calculation logging.
Every tool call is recorded with timestamp, inputs, formula, output, rates used.
Generate a companion audit log document alongside each report."
```

### After build - run 3 validators, fix, re-validate.

### Phase 2 exit criteria:
- [ ] Hebrew PDFs parse correctly (text + tables)
- [ ] Word template generates professional Hebrew reports
- [ ] Excel reader handles all reference table formats
- [ ] Audit log captures every calculation
- [ ] Tests pass

---

## Phase 3: Agent Orchestration + UI (Weeks 9-14)

### What gets built:
- Main agent with Claude Agent SDK
- System prompt with full domain knowledge
- Hooks (validation, audit, completeness)
- Chainlit UI with Hebrew interface
- FastAPI backend
- Classification checkpoint

### Builder agents:

**Agent 1: agent-builder**
```
Prompt: "Build the main agent in src/agent/ using Claude Agent SDK.
Register all calculation tools as in-process MCP tools.
Configure 3 external MCP servers (playwright, monday, memory).
Build the system prompt from docs/agent_workflow_flow.md.
Implement hooks: PreToolUse (input validation), PostToolUse (audit log), Stop (completeness).
Build workflow phases: intake → analysis → checkpoint → calculations → report."
```

**Agent 2: ui-builder**
```
Prompt: "Build the Chainlit UI in src/ui/ with Hebrew RTL interface.
Build the FastAPI backend in src/api/ with job queue.
Create intake form with all mandatory fields from workflow step 0.
Create file upload fields for: survey map, permits, reference tables.
Create classification checkpoint as interactive table.
Create report download section (Word, Excel, PDF, Audit Log).
All text in Hebrew."
```

**Agent 3: integration-builder**
```
Prompt: "Build Monday.com client using @mondaycom/mcp.
Build OneDrive client using msgraph-sdk (direct SDK).
Build Google Drive client using google-api-python-client (direct SDK).
Build govmap placeholder (manual input form for Phase 1, browser scraping later).
Create .mcp.json with 3 servers: playwright, monday, memory."
```

### After build - run 3 validators, fix, re-validate.

### Phase 3 exit criteria:
- [ ] Agent runs end-to-end: intake → report generation
- [ ] UI works in Hebrew with file uploads
- [ ] Classification checkpoint blocks until user confirms
- [ ] Monday.com status updates work
- [ ] OneDrive upload works
- [ ] All calculations verified against example reports
- [ ] 3 validators PASS

---

## Phase 4: Full Testing + Polish (Weeks 15-18)

### What gets built:
- Test against all 25 example reports
- govmap.gov.il browser integration
- Error handling and edge cases
- Performance optimization

### Builder agents:

**Agent 1: calc-builder** (golden test suite)
```
Prompt: "Create golden test cases from ALL 25 example reports in tests/golden/.
Extract the input data and expected output numbers from each report.
Verify the agent produces matching results (within 1% tolerance).
Fix any calculation discrepancies."
```

**Agent 2: integration-builder** (govmap)
```
Prompt: "Build govmap.gov.il integration using Playwright MCP.
Navigate to govmap, search by gush/helka, intercept ArcGIS REST API responses.
Extract taba list and basic zoning data.
Fall back to manual input if scraping fails."
```

### After build - run 3 validators, fix, re-validate.

### Phase 4 exit criteria:
- [ ] 25/25 example reports produce correct results
- [ ] govmap integration works (or graceful fallback)
- [ ] All edge cases handled
- [ ] 3 validators PASS

---

## Phase 5: Production Hardening (Weeks 19-24)

### What gets built:
- Security (RBAC, secrets, encryption)
- Docker deployment
- PostgreSQL migration
- React frontend (replace Chainlit)
- CI/CD pipeline
- Monitoring

### Builder agents:

**Agent 1: integration-builder** (security + deployment)
```
Prompt: "Add security: RBAC roles, secrets management, input sanitization.
Create Dockerfile and docker-compose.yml with PostgreSQL, Redis, Caddy.
Add health checks, restart policies, resource limits.
Create CI/CD with GitHub Actions."
```

**Agent 2: ui-builder** (React frontend)
```
Prompt: "Replace Chainlit with React + Next.js frontend.
WebSocket streaming for agent responses.
Full Hebrew RTL support.
Authentication with role-based access."
```

### After build - run 3 validators, fix, re-validate.

---

## How to Run Each Phase

### Step 1: Launch builder agents (parallel)
```bash
# In the nachla-agent directory, run builders in parallel worktrees:
# Claude Code will handle worktree creation automatically

# Example - launching calc-builder:
claude "You are the calc-builder agent. Read .claude/agents/calc-builder.md for your instructions. Read docs/agent_workflow_flow.md and docs/technical_blueprint.md for domain context. Build everything in your scope. Run tests when done." --agent calc-builder -w calc-phase1
```

### Step 2: Merge builder branches
```bash
# After all builders complete, merge their worktrees to main
git merge calc-phase1
git merge models-phase1
# Resolve any conflicts
```

### Step 3: Run 3 validators
```bash
# Launch all 3 validators in parallel (read-only, no worktrees needed)
claude "Review ALL code in src/ and tests/. Follow your checklist. Report findings." --agent validator-code
claude "Review ALL calculation code and business logic. Follow your checklist." --agent validator-domain
claude "Review UI code and report templates. Follow your checklist." --agent validator-ux
```

### Step 4: Fix findings
```bash
# Launch a fix agent that reads validator reports and fixes issues
claude "Read the validator findings. Fix every issue found. Run tests after each fix."
```

### Step 5: Re-validate until clean
```bash
# Repeat Step 3-4 until all 3 validators report PASS
```

### Step 6: Commit and move to next phase
```bash
git add -A
git commit -m "Phase N complete - validated by 3 specialist reviewers"
git push
```

---

## Reference Data Requirements (User Uploads)

The agent does NOT come pre-loaded with settlement data. Users upload:

| Upload Field | File | Description |
|---|---|---|
| **מפת מדידה** | PDF/image | Survey map of the property |
| **היתרי בנייה** | PDF(s) | All existing building permits |
| **טבלת דמי היתר** | Excel | RMI permit fees by settlement (דמי היתר לפי ישובים) |
| **טבלת דמי פל"ח** | Excel | PLACH fees by area (דמי היתר פלח לפי מרחב) |
| **הנחיות רמ"י** | Excel | RMI rules and decisions |
| **ערכי קרקע** | PDF | Land values for auxiliary uses |
| **טבלת משרד החקלאות** | PDF | Agriculture ministry building standards |
| **חוזה חכירה** (optional) | PDF | Existing lease agreement |
| **שומה** (optional) | PDF | Property appraisal |

These are uploaded once per workspace and reused across all reports for that workspace.

---

## Success Metrics

| Metric | Target |
|---|---|
| Calculation accuracy vs reference reports | Within 1% |
| Report generation time | < 5 minutes |
| Hebrew text quality | Professional grade |
| Building classification accuracy | > 90% (with user confirmation) |
| API cost per report | < $5 |
| Uptime | 99% (production) |
