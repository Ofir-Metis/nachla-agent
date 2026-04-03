# Master Build Prompt for Claude Code
## Copy-paste this into a new Claude Code session at C:\Users\Ofir\nachla-agent

---

```
You are building "Nachla Agent" — an AI agent that performs feasibility studies (בדיקת התכנות) for Israeli agricultural settlements. The project is fully set up and ready to build.

## BEFORE YOU START

1. Read CLAUDE.md (project rules, forbidden patterns, domain rules)
2. Read DEV_PLAN.md (full 5-phase build plan with agent roster)
3. Read docs/agent_workflow_flow.md (the 14-step agent workflow)
4. Read docs/technical_blueprint.md (architecture and tech stack)
5. Read docs/expert_review_consolidated.md (30 validated findings)
6. Run: source venv/Scripts/activate && python -m pytest tests/ -v (verify 16/16 pass)

## YOUR BUILD PROCESS

For each phase, follow this exact loop:

### STEP 1: PLAN
Enter plan mode. List every file you will create/modify. Map each file to its owner agent from .claude/agents/. List exit criteria from DEV_PLAN.md. Get my approval before writing any code.

### STEP 2: BUILD (parallel where possible)
For each builder agent scope, launch a subagent with worktree isolation:

- **calc-builder** (read .claude/agents/calc-builder.md): Build src/tools/, src/config/rates_config.json, tests/test_calculations.py
- **doc-builder** (read .claude/agents/doc-builder.md): Build src/documents/, tagged Word template
- **integration-builder** (read .claude/agents/integration-builder.md): Build src/integrations/
- **agent-builder** (read .claude/agents/agent-builder.md): Build src/agent/, src/models/, src/config/settings.py
- **ui-builder** (read .claude/agents/ui-builder.md): Build src/ui/, src/api/

Each builder MUST:
- Read CLAUDE.md before writing any code
- Read the relevant docs/ files for domain context
- Use rates_config.json for ALL constants (never hardcode)
- Include priority area discounts in ALL calculations
- Write tests alongside code
- Run pytest after completing their scope

### STEP 3: VERIFY (run tests)
After all builders complete:
```bash
source venv/Scripts/activate
export PYTHONIOENCODING=utf-8
python -m pytest tests/ -v
```
Fix any failures before proceeding to validation.

### STEP 4: VALIDATE (3 specialist reviewers)
Launch 3 validator subagents in PARALLEL, all using opus model with effort: max and read-only access (no Write/Edit):

**Validator 1 — Code Quality** (read .claude/agents/validator-code.md):
"Review ALL code in src/ and tests/. Check: architecture matches blueprint, no hardcoded constants, all tools return audit trails, security (no exposed keys, input validation), Python quality (type hints, Pydantic, async), tests pass and cover edge cases. Report PASS/FAIL per file with line numbers."

**Validator 2 — Domain Accuracy** (read .claude/agents/validator-domain.md):
"Review ALL calculation code and business logic. Verify: every formula matches docs/agent_workflow_flow.md, priority area discounts applied to ALL payment types, VAT is 18% from config, 808 is dynamic, usage fees are 5%/3%/2% by type, bar reshut blocks split, post-2009 deduction rule, permit fee cap applied, basement 0.3/0.7 split, all building types classified. Report CORRECT/INCORRECT per formula with financial impact."

**Validator 3 — UX & Output** (read .claude/agents/validator-ux.md):
"Review UI code and report generation. Check: all text in Hebrew, RTL direction set, intake form has all 12+ mandatory fields, classification checkpoint exists and blocks, Monday.com status updates at every step, error states in Hebrew, report matches template structure, all 8+ disclaimers present, audit log generated, cloud storage upload works. Report PASS/FAIL per check."

### STEP 5: FIX
Read all 3 validator reports. Fix every finding. Run tests again. If any validator reported FAIL:
- Fix the code
- Run tests
- Re-run ONLY the validators that reported FAIL
- Repeat until all 3 report PASS

### STEP 6: COMMIT
```bash
git add -A
git commit -m "Phase N complete — validated by 3 specialist reviewers"
git push origin master
```

### STEP 7: NEXT PHASE
Move to the next phase and repeat from STEP 1.

## PHASE ORDER

**Phase 1** (Weeks 1-4): Calculation Engine
- rates_config.json + 8 calc tools + priority areas + data models + unit tests
- Exit: all calc tests pass, validators PASS

**Phase 2** (Weeks 5-8): Document Processing
- PDF parser + Excel reader + Word generator + audit log
- Exit: Hebrew PDFs parse, Word template fills, audit log works

**Phase 3** (Weeks 9-14): Agent + UI + Integrations
- Main agent + system prompt + hooks + Chainlit UI + FastAPI + Monday.com + OneDrive
- Exit: end-to-end flow works (intake → report → upload)

**Phase 4** (Weeks 15-18): Full Testing
- Golden test suite from 25 examples + govmap integration + edge cases
- Exit: 25/25 reports match within 1%

**Phase 5** (Weeks 19-24): Production
- Security + Docker + PostgreSQL + React + CI/CD
- Exit: production-ready deployment

## CRITICAL RULES (from expert review — violations cost clients hundreds of thousands of ILS)

1. NEVER hardcode constants — ALL from rates_config.json with effective dates
2. NEVER let the LLM do math — all arithmetic in Python tools
3. NEVER skip the building classification confirmation checkpoint
4. NEVER produce a report without an audit log
5. Priority area discounts affect ALL calculations (permit fees, hivun, split, usage fees) — missing this causes 40% of reports to be wrong
6. VAT is 18% (not 17%) — configurable, loaded from config
7. 808 sqm equivalent is dynamic (not fixed) for non-standard nachala
8. Bar reshut cannot split — must check authorization type
9. Only post-2009 permit purchases deducted from 33% calculation
10. Usage fees: 7 years for 3rd+ house, 2 years for 2nd house, conditional for parents unit

## START NOW

Begin with Phase 1. Enter plan mode first. List every file you will create and the exit criteria. Then ask for my approval to proceed.
```

---

## How to Use This Prompt

1. Open a new Claude Code terminal
2. Navigate to the project: `cd C:\Users\Ofir\nachla-agent`
3. Activate venv: `source venv/Scripts/activate`
4. Start Claude Code
5. Paste the prompt above (everything between the ``` markers)
6. Claude will enter plan mode and present the Phase 1 plan for approval
7. Approve, then let it build autonomously with the validate-fix loop

## Tips for Best Results

- **Don't interrupt during build** — let each phase complete its full loop
- **Review validator reports** — they catch real bugs
- **If context gets long**, start a new session and say: "Continue from Phase N. Read DEV_PLAN.md and CLAUDE.md. Run tests to see current state."
- **Save progress often** — Claude commits after each validated phase
- **If a phase is too large**, tell Claude to split it into sub-phases

Sources:
- [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices)
- [Custom Subagents](https://code.claude.com/docs/en/sub-agents)
- [Agent Teams](https://code.claude.com/docs/en/agent-teams)
- [Claude Prompting Best Practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
- [shanraisshan/claude-code-best-practice](https://github.com/shanraisshan/claude-code-best-practice)
- [GSD-2 Spec-Driven Development](https://github.com/gsd-build/gsd-2)
