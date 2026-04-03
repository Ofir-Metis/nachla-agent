# Nachla Agent - AI Agent for בדיקת התכנות נחלות

## Project Overview
AI agent that performs feasibility studies (בדיקת התכנות) for Israeli agricultural settlements (nachala/moshavim). It analyzes buildings, zoning plans (תב"ע), calculates RMI fees, and generates professional Word/Excel reports.

## Tech Stack
- **Runtime:** Python 3.12+
- **Agent Engine:** Claude Agent SDK (claude-agent-sdk)
- **LLM:** Claude Sonnet 4.6 (main), Opus 4.6 (complex reasoning)
- **MCP Servers (3 only):** @playwright/mcp, @mondaycom/mcp, @modelcontextprotocol/server-memory
- **Document Processing:** Docling (PDF), docxtpl (Word generation), openpyxl/pandas (Excel)
- **Cloud Storage:** google-api-python-client (Google Drive), msgraph-sdk (OneDrive) - direct SDK, NOT MCP
- **UI:** Chainlit (prototype) -> React + FastAPI (production)
- **Database:** SQLite (dev) -> PostgreSQL (production)
- **Testing:** pytest + promptfoo

## Project Structure
```
nachla-agent/
├── CLAUDE.md                 # This file
├── .claude/
│   ├── agents/               # Custom subagent definitions
│   └── skills/               # Custom skills
├── src/
│   ├── tools/                # Custom calculation tools (Python)
│   │   ├── calc_dmei_heter.py
│   │   ├── calc_dmei_shimush.py
│   │   ├── calc_hivun.py
│   │   ├── calc_pitzul.py
│   │   ├── calc_sqm_equivalent.py
│   │   ├── calc_hetel_hashbacha.py
│   │   ├── lookup_tables.py
│   │   └── priority_areas.py
│   ├── models/               # Data models (Pydantic)
│   │   ├── building.py
│   │   ├── nachla.py
│   │   ├── taba.py
│   │   └── report.py
│   ├── config/               # Configuration
│   │   ├── rates_config.json # ALL regulatory constants with effective dates
│   │   └── settings.py
│   ├── api/                  # FastAPI backend
│   │   ├── main.py
│   │   ├── routes.py
│   │   └── jobs.py
│   ├── ui/                   # Chainlit frontend
│   │   ├── app.py
│   │   ├── components.py     # Custom UI components
│   │   └── auth.py           # Authentication
│   ├── documents/            # Document processing
│   │   ├── pdf_parser.py
│   │   ├── excel_reader.py
│   │   ├── word_generator.py
│   │   └── ocr.py
│   ├── integrations/         # External services
│   │   ├── monday_client.py
│   │   ├── onedrive_client.py
│   │   ├── gdrive_client.py
│   │   └── govmap_scraper.py
│   └── agent/                # Agent orchestration
│       ├── main_agent.py
│       ├── system_prompt.py
│       ├── workflow.py       # Phase-based workflow engine
│       └── audit_log.py
├── data/
│   ├── templates/            # Word/Excel report templates
│   └── reference/            # Reference data (user uploads)
├── tests/
│   ├── test_environment.py   # Environment validation (owned by agent-builder)
│   ├── test_calculations.py
│   ├── test_documents.py
│   ├── test_integrations.py
│   ├── test_agent.py
│   └── golden/               # Golden test data from 25 example reports
├── docs/
│   ├── agent_workflow_flow.md
│   ├── technical_blueprint.md
│   └── expert_review_consolidated.md
├── requirements.txt
├── pyproject.toml            # ruff + pytest config
├── .env.example              # Required environment variables
├── .gitignore
├── Dockerfile                # (Phase 5, owned by integration-builder)
├── docker-compose.yml        # (Phase 5, owned by integration-builder)
└── .mcp.json                 # 3 MCP servers: playwright, monday, memory
```

## Coding Standards
- Python 3.12+, type hints on all functions
- Pydantic v2 for all data models
- async/await for I/O operations
- All financial calculations MUST be deterministic Python (never LLM math)
- All regulatory constants from `rates_config.json` (never hardcoded)
- Hebrew text: always UTF-8, use `ensure_ascii=False` in JSON
- RTL handling: via Word template (docxtpl), not programmatic
- Error messages in English, user-facing text in Hebrew
- Every calculation tool returns an audit trail (inputs, formula, output)

## Forbidden Patterns
- NEVER hardcode tax rates, fee percentages, or regulatory constants
- NEVER let the LLM perform arithmetic - always use calculation tools
- NEVER use hobby/low-star MCP servers for production features
- NEVER store API keys in code or docker-compose - use .env or secrets
- NEVER skip the building classification confirmation checkpoint
- NEVER produce a report without an audit log

## Key Domain Rules
- VAT rate: 18% (configurable, was 17% before 2025)
- RMI permit fee rate: 91% (decision 1523)
- Hivun 3.75%: 808 sqm equivalent for STANDARD nachala (2.5 dunam, 375 sqm rights) - calculate dynamically if non-standard
- Priority area discounts affect ALL calculations differently
- Usage fees: 5% residential, 3% priority area, 2% agricultural
- Bar reshut cannot split plots without lease agreement
- Only post-2009 permit purchases deducted from 33% calculation
- Pre-1965 buildings are exempt from building permits
- Basement: 0.3 coefficient (service) or 0.7 (residential) - not always 0.7
- Permit fee cap: decision 1523 limits total permit fees per nachala - check after summing all buildings

## Test Commands
```bash
pytest tests/ -v                    # Run all tests
pytest tests/test_calculations.py   # Calculation unit tests only
python -m chainlit run src/ui/app.py  # Run UI
```
