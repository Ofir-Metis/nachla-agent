# Technical Blueprint - AI Agent for בדיקת התכנות נחלות

## How to Build It: Complete Architecture & Tool Stack

---

## 1. Core Engine: Claude Agent SDK

The agent will be built on the **Claude Agent SDK** (Python) - Anthropic's official SDK that packages Claude Code as a library. This gives us a battle-tested agent runtime out of the box.

### Why Claude Agent SDK (not raw API):

| Feature | Raw Claude API | Claude Agent SDK |
|---|---|---|
| Agent loop | Build yourself | Built-in, battle-tested |
| Tool management | Manual | Decorator-based, automatic |
| File operations | Custom code | Built-in (Read, Write, Edit, Glob, Grep) |
| Web access | Custom code | Built-in (WebSearch, WebFetch) |
| Shell commands | Custom code | Built-in (Bash) |
| Subagents | Not available | Built-in parallel subagents |
| MCP integration | Manual setup | Native support |
| Hooks (pre/post tool) | Not available | Built-in hook system |
| Error handling | Manual | Built-in retry + error feedback |

### SDK Architecture:

```
┌─────────────────────────────────────────────────────────┐
│                    Claude Agent SDK                      │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Built-in     │  │ Custom Tools │  │ MCP Servers   │  │
│  │ Tools        │  │ (Python)     │  │ (3 only)      │  │
│  │              │  │              │  │               │  │
│  │ - Read       │  │ - calc_dmei  │  │ - Playwright  │  │
│  │ - Write      │  │   _heter     │  │   (govmap)    │  │
│  │ - Edit       │  │ - calc_     │  │ - Monday.com  │  │
│  │ - Bash       │  │   hivun     │  │   (workflow)  │  │
│  │ - Glob       │  │ - parse_    │  │ - Memory      │  │
│  │ - Grep       │  │   taba      │  │   (sessions)  │  │
│  │ - WebSearch  │  │ - classify  │  │               │  │
│  │ - WebFetch   │  │   building  │  │               │  │
│  │ - Agent      │  │ - generate  │  │               │  │
│  │   (subagent) │  │   _report   │  │               │  │
│  │ - Ask User   │  │ - read_excel│  │               │  │
│  │              │  │ - upload_   │  │               │  │
│  │              │  │   gdrive    │  │               │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Hooks: PreToolUse | PostToolUse | Stop | etc.    │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Installation:
```bash
pip install claude-agent-sdk
```

### Basic Agent Setup:

> **⚠️ Note:** The code examples below show the LOGIC, not the exact SDK API signature.
> Verify against the [actual Claude Agent SDK docs](https://platform.claude.com/docs/en/agent-sdk/python)
> as the SDK is pre-1.0 (v0.1.x) and the API may change between versions.

```python
# === rates_config.json - ALL constants externalized with effective dates ===
RATES_CONFIG = {
    "vat_rate": {"value": 0.18, "effective": "2025-01-01", "note": "was 0.17 before 2025"},
    "permit_fee_rate": {"value": 0.91, "effective": "2020-01-01", "note": "decision 1523"},
    "hivun_375_sqm": {"value": 808, "effective": "2020-01-01", "note": "standard 2.5 dunam; calculate dynamically if non-standard"},
    "hivun_375_rate": {"value": 0.0375},
    "hivun_33_rate": {"value": 0.33},
    "usage_fee_residential": {"value": 0.05},
    "usage_fee_agricultural": {"value": 0.02},
    "usage_fee_priority_area": {"value": 0.03},
    "priority_area_discounts": {
        "A": {"permit": 0.51, "purchase_33": 0.3886, "split_160": 0.1639, "split_rest": 0.2014},
        "B": {"permit": 0.25, "purchase_33": 0.3886, "split_160": 0.1639, "split_rest": 0.2014},
        "frontline": {"permit": 0.31}
    }
}

# === Example tool with configurable rates ===
def calculate_dmei_heter(
    area_sqm: float,
    area_type: str,  # "main" | "service" | "pool" | "basement_service" | "basement_residential"
    shovi_meter_aku: float,
    priority_area: str = None,  # None | "A" | "B" | "frontline"
    effective_date: str = None
) -> dict:
    """Calculate permit fees (דמי היתר) with configurable rates and priority area discounts."""
    multipliers = {"main": 1.0, "service": 0.5, "pool": 0.3, "basement_service": 0.3, "basement_residential": 0.7}
    if area_type not in multipliers:
        return {"error": f"Unknown area_type: {area_type}. Valid: {list(multipliers.keys())}"}

    mult = multipliers[area_type]
    rate = RATES_CONFIG["permit_fee_rate"]["value"]  # 0.91
    vat = RATES_CONFIG["vat_rate"]["value"]  # 0.18

    cost = area_sqm * mult * shovi_meter_aku * rate * (1 + vat)

    # Apply priority area discount
    discount = 0
    if priority_area and priority_area in RATES_CONFIG["priority_area_discounts"]:
        discount = RATES_CONFIG["priority_area_discounts"][priority_area].get("permit", 0)
        cost = cost * (1 - discount)

    return {
        "cost_ils": round(cost),
        "per_sqm": round(cost / area_sqm) if area_sqm > 0 else 0,
        "formula": f"{area_sqm} × {mult} × {shovi_meter_aku} × {rate} × {1+vat}",
        "priority_discount": f"{discount*100}%" if discount else "none",
        "rates_used": {"permit_rate": rate, "vat": vat, "effective": effective_date or "current"}
    }
```

### References:
- [Claude Agent SDK Python](https://github.com/anthropics/claude-agent-sdk-python)
- [Agent SDK Overview](https://platform.claude.com/docs/en/agent-sdk/overview)
- [Hooks Documentation](https://platform.claude.com/docs/en/agent-sdk/hooks)
- [Subagents Documentation](https://platform.claude.com/docs/en/agent-sdk/subagents)

---

## 2. MCP Servers - Plug-and-Play Capabilities

MCP (Model Context Protocol) servers extend the agent with external capabilities. These are battle-tested, open-source components:

### MCP Servers - Reduced to Essential Only (per expert review):

> **Principle:** Keep only MCP servers that provide capabilities the SDK doesn't have built-in.
> Everything else → custom Python tools (easier to test, debug, maintain).

**Removed (redundant with SDK built-ins or low value):**
- ~~server-filesystem~~ → SDK has Read/Write/Edit/Glob/Grep built-in
- ~~server-fetch~~ → SDK has WebFetch built-in
- ~~server-sequential-thinking~~ → prompt trick, no real capability
- ~~@negokaz/excel-mcp-server~~ → only 4,500 downloads; use openpyxl directly
- ~~mcp-pdf~~ → use Docling/pdfplumber as custom Python tools
- ~~ultimate_mcp_server~~ → untested mega-dependency, red flag

**Removed (hobby projects, not production-ready):**
- ~~piotr-agier/google-drive-mcp~~ → 39 stars, solo developer. Use `google-api-python-client` directly
- ~~ftaricano/mcp-onedrive-sharepoint~~ → Microsoft deprecated their own MCP. Use `msgraph-sdk` directly
- ~~Aanerud/MCP-Microsoft-Office~~ → 117 tools = massive scope creep

### Keep Only These MCP Servers:

| MCP Server | Source | Why Keep |
|---|---|---|
| **@playwright/mcp** | [Microsoft](https://github.com/microsoft/playwright-mcp) | Web scraping - no SDK alternative. Needed for govmap (Phase 3+) |
| **@mondaydotcomorg/monday-api-mcp** | [Official Monday.com](https://github.com/mondaycom/mcp) | Official, well-maintained, hosted. Core workflow integration |
| **@modelcontextprotocol/server-memory** | [Official](https://github.com/modelcontextprotocol/servers) | Session persistence across conversations |

### Cloud Storage - Direct SDK Integration (not MCP):

```python
# Google Drive - using official google-api-python-client (~10 lines)
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def upload_to_gdrive(file_path, folder_id, credentials):
    service = build('drive', 'v3', credentials=credentials)
    media = MediaFileUpload(file_path)
    file = service.files().create(
        body={'name': os.path.basename(file_path), 'parents': [folder_id]},
        media_body=media
    ).execute()
    return file.get('id')

# OneDrive - using official msgraph-sdk (~10 lines)
from msgraph import GraphServiceClient

async def upload_to_onedrive(file_path, folder_path, client):
    with open(file_path, 'rb') as f:
        await client.me.drive.root.item_by_path(
            f"{folder_path}/{os.path.basename(file_path)}"
        ).content.put(f)
```

### Monday.com Integration Details:

The agent connects to Monday.com for:
1. **Reading client data** - pull גוש/חלקה, שם לקוח, שם מושב from the board
2. **Updating status** - move items through workflow groups (e.g., "בבדיקה" → "טיוטה" → "בקרה" → "מאושר")
3. **Posting updates** - add progress notes ("סיימתי ניתוח תב"ע, עוברים לחישובים")
4. **Attaching files** - link the generated report to the Monday item

Configuration:
```json
{
  "mondaycom": {
    "type": "http",
    "url": "https://mcp.monday.com/mcp",
    "headers": {
      "Authorization": "Bearer ${MONDAY_API_TOKEN}"
    }
  }
}
```

Alternatively, run locally:
```bash
npx @mondaydotcomorg/monday-api-mcp
```

### Cloud Storage Logic:

The agent asks the user which storage to use, then routes accordingly:
```
User preference → Google Drive?  → upload_to_gdrive() (google-api-python-client)
                → OneDrive?      → upload_to_onedrive() (msgraph-sdk)
                → Both?          → upload to both via direct SDK calls
```

### ~~Power MCP Server Option (All-in-One) - NOT RECOMMENDED:~~

> **Expert review:** ultimate_mcp_server is an untested mega-dependency with unknown stability.
> It contradicts the modular architecture. **Do not use.** Build focused custom tools instead.

### MCP Configuration (.mcp.json) - Minimal (3 servers only):

```json
{
  "mcpServers": {
    "playwright": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@playwright/mcp", "--persistent"]
    },
    "mondaycom": {
      "type": "http",
      "url": "https://mcp.monday.com/mcp",
      "headers": {
        "Authorization": "Bearer ${MONDAY_API_TOKEN}"
      }
    },
    "memory": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    }
  }
}
```

Everything else is a **custom Python tool** within the agent process (no IPC overhead, easier debugging).
```

### MCP Server Directories (11,000+ servers available):
- [Official MCP Registry](https://registry.modelcontextprotocol.io/) - primary source of truth (launched Sep 2025)
- [Official Reference Servers](https://github.com/modelcontextprotocol/servers)
- [PulseMCP](https://www.pulsemcp.com/servers) - 11,180+ servers, updated daily
- [awesome-mcp-servers (wong2)](https://github.com/wong2/awesome-mcp-servers)
- [awesome-mcp-servers (appcypher)](https://github.com/appcypher/awesome-mcp-servers)
- [TensorBlock catalog](https://github.com/TensorBlock/awesome-mcp-servers) - 7,260+ servers
- [Glama](https://glama.ai/mcp/servers) - curated with security/quality scorecards
- [mcp.so](https://mcp.so/) - community-driven directory
- [mcpservers.org](https://mcpservers.org/)

---

## 3. Document Processing Stack

### 3.1 PDF Parsing - For תב"עות, היתרים, מפות מדידה

| Library | Best For | Hebrew | Tables | GitHub Stars |
|---|---|---|---|---|
| **Docling** (IBM) | Complex PDFs with layout understanding | **⚠️ UNVERIFIED for Hebrew** - must test Week 0 | Excellent (TableFormer AI) | 20k+ |
| **pdfplumber** | Table extraction from native PDFs | Needs testing | Excellent | 7k+ |
| **PyMuPDF (fitz)** | Fast text extraction, image handling | Good | Basic | 5k+ |
| **pymupdf4llm** | LLM-optimized PDF extraction | Good | Good | New |

**Recommendation:** Use **Docling** as primary (best table extraction via AI), **pdfplumber** as fallback for simpler PDFs.

```python
# Docling - 5 lines to parse any document
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("taba_616-0902908.pdf")
markdown = result.document.export_to_markdown()
tables = result.document.tables  # Structured table data
```

**Docling features relevant to us:**
- Parses PDF, DOCX, XLSX, images
- AI-powered table structure recognition (TableFormer)
- Layout understanding (reading order, headers/footers)
- Exports to Markdown, JSON, HTML
- Integrates with LlamaIndex and LangChain
- MIT license, weekly releases
- [Docling GitHub](https://github.com/docling-project/docling)

### 3.2 Word Document Generation - For דוח בדיקת התכנות

| Library | Best For | Template Support | Hebrew RTL |
|---|---|---|---|
| **docxtpl** (python-docx-template) | Filling Word templates with data | Jinja2 tags in Word | Via template |
| **python-docx** | Full programmatic control | Manual | Manual RTL setup |
| **docx2pdf** | Converting final DOCX to PDF | N/A | Preserves formatting |

**Recommendation:** Use **docxtpl** - create the template in Word (with all Hebrew/RTL formatting), then fill it programmatically.

```python
from docxtpl import DocxTemplate

doc = DocxTemplate("template_bdikat_hitkhnut.docx")
context = {
    "client_name": "משפחת רונן",
    "moshav": "כפר ורבורג",
    "date": "20/10/2025",
    "buildings": [
        {"name": "בית מגורים ראשון", "area": 234, "status": "חריגה מהיתר", "cost": 350000},
        {"name": "בית מגורים שלישי", "area": 105, "status": "ללא היתר", "cost": 780000},
    ],
    "total_hesdara": 1130000,
    "hivun_375": 280000,
    "hivun_33": 3200000,
}
doc.render(context)
doc.save("bdikat_hitkhnut_ronen.docx")
```

**Key advantage:** The existing Word template (טמפלט בדיקת התכנות) can be used directly - just add `{{ variable }}` tags to it. All Hebrew formatting, RTL, fonts, headers, footers, images are preserved from the template.

**Critical Hebrew/RTL tips for docxtpl:**
1. Design the template in Word first - Word handles RTL natively
2. Use fonts: David, FrankRuehl, or Arial for Hebrew body text
3. Hebrew uses "complex script" (cs) font slot in Word
4. Set section direction to RTL so page numbers appear on the left
5. Mixed Hebrew/English text is handled automatically by Word's bidi algorithm
6. For tables: RTL direction is preserved from the template

References:
- [docxtpl GitHub](https://github.com/elapouya/python-docx-template)
- [docxtpl Documentation](https://docxtpl.readthedocs.io/)

### 3.3 Excel Processing - For תחשיבים and reference tables

| Library | Reading | Writing | Formulas |
|---|---|---|---|
| **openpyxl** | Yes | Yes | Read formulas as text, write formulas |
| **pandas** | Yes (via openpyxl) | Yes | No formula support |
| **xlsxwriter** | No | Yes (fast) | Write formulas |

**Recommendation:** Use **openpyxl** for reading existing Excel files (reference tables), **pandas** for data manipulation, **xlsxwriter** for generating calculation spreadsheets.

### 3.4 OCR for Hebrew - For scanned maps and documents

| Service | Hebrew Quality | Speed | Cost |
|---|---|---|---|
| **Google Cloud Vision API** | Excellent | Fast | $1.50/1000 pages |
| **Azure Document Intelligence** | Very Good | Fast | $1/1000 pages |
| **Tesseract + Hebrew** | Moderate | Slow | Free |
| **Docling (built-in OCR)** | Good | Moderate | Free |

**Additional option:**
- **EasyOCR** (20k+ stars) - supports Hebrew, runs locally (PyTorch), better than Tesseract, free

**Recommendation:** Start with **Docling's built-in OCR**. Escalate to **Google Cloud Vision** for complex scanned documents (מפות מדידה ישנות). Use **EasyOCR** as free middle ground.

---

## 4. Web Scraping - govmap.gov.il & Planning Data

### The Challenge:
govmap.gov.il is a JavaScript-heavy GIS application built on **ArcGIS/Esri** technology. The site has a "rich API" mentioned at the bottom of the page, but no public documentation exists in English. You can contact govmap@mapi.gov.il or register in the portal for API access.

### Strategy: Intercept REST APIs, don't scrape the UI
The map interface makes XHR requests to `https://ags.govmap.gov.il/...` endpoints. These are standard ArcGIS REST services. The best approach is to intercept these API calls using Playwright's `page.route()` and call them directly with `requests` (much faster than browser automation).

### Solution: Playwright MCP Server

```
Agent → Playwright MCP → Browser → govmap.gov.il
                                  → XPLAN
                                  → Municipal committee sites
```

The [Microsoft Playwright MCP](https://github.com/microsoft/playwright-mcp) server provides:
- Full browser automation (click, type, navigate, screenshot)
- Accessibility snapshots (structured page content without screenshots)
- Persistent browser profiles (save login sessions)
- ~27,000 tokens per task (efficient)

### ⚠️ govmap Integration = Phase 3+ (deferred)

> **Expert review finding:** The code sample below is pseudocode that **will not work**.
> govmap uses a custom ArcGIS widget framework - there is no `#search-input` element.
> Phase 1-2 should use **manual taba data input**.
> Phase 3+ builds govmap integration after contacting govmap team for API access.

**Correct approach (Phase 3):**
1. Contact govmap@mapi.gov.il for API access
2. Reverse-engineer the ArcGIS REST endpoints at `ags.govmap.gov.il`
3. Use Playwright's `page.route()` to intercept XHR requests and capture the JSON responses
4. Call the REST endpoints directly with `httpx` (much faster than browser automation)

**Phase 1-2 fallback:**
```python
def input_taba_data_manually() -> dict:
    """User manually enters taba data extracted from govmap/XPLAN."""
    return {
        "taba_number": "ask_user",
        "housing_units": "ask_user",
        "main_area_sqm": "ask_user",
        "service_area_sqm": "ask_user",
        # ... structured input form
    }
```

### QGIS Plugin:
The [Israeli Open Data Loader](https://plugins.qgis.org/plugins/israeli_opendata_loader/) QGIS plugin provides access to Israeli open data resources - could be a reference for data source URLs.

---

## 5. Calculation Engine - Deterministic Python Functions

**Critical principle:** The LLM decides WHAT to calculate. Python does the math. Never let the LLM do arithmetic.

### Tool Registry:

```python
# Each calculation is a separate tool with clear inputs/outputs

@tool
def calc_dmei_heter(area_sqm: float, type: str, shovi_aku: float) -> dict:
    """Calculate דמי היתר (permit fees)."""
    ...

@tool
def calc_dmei_shimush(area_sqm: float, type: str, shovi_aku: float, years: int) -> dict:
    """Calculate דמי שימוש (usage fees)."""
    ...

def calc_hivun_375(shovi_meter_aku: float, plot_sqm: float = 2500,
                    taba_rights_sqm: float = 375, priority_area: str = None) -> dict:
    """Calculate היוון 3.75%. Dynamically calculates sqm_aku if non-standard nachala."""
    # Default 808 for standard nachala (2.5 dunam, 375 sqm rights)
    # Calculate dynamically if plot or rights differ from standard
    if plot_sqm == 2500 and taba_rights_sqm == 375:
        sqm_aku = RATES_CONFIG["hivun_375_sqm"]["value"]  # 808
    else:
        sqm_aku = calc_sqm_equivalent_dynamic(plot_sqm, taba_rights_sqm)
        # Warning if differs significantly from 808

    rate = RATES_CONFIG["hivun_375_rate"]["value"]  # 0.0375
    cost = sqm_aku * shovi_meter_aku * rate

    # Priority area discount
    if priority_area:
        discount = RATES_CONFIG["priority_area_discounts"].get(priority_area, {})
        # Apply relevant discount

    return {"cost_ils": round(cost), "sqm_aku_used": sqm_aku,
            "formula": f"{sqm_aku} × {shovi_meter_aku} × {rate}",
            "warning": "Non-standard nachala: 808 recalculated" if sqm_aku != 808 else None}

def calc_hivun_33(total_sqm_aku: float, potential_sqm_aku: float,
                   purchased_heter: float, purchased_after_2009: bool,
                   shovi_aku: float, priority_area: str = None) -> dict:
    """Calculate היוון 33% (דמי רכישה). Only post-2009 purchases are deducted."""
    # Only deduct purchases made AFTER 2009 (decision 979/1311)
    deduction = purchased_heter if purchased_after_2009 else 0
    base = (total_sqm_aku + potential_sqm_aku - deduction)

    rate = RATES_CONFIG["hivun_33_rate"]["value"]  # 0.33
    if priority_area in ["A", "B"]:
        rate = RATES_CONFIG["priority_area_discounts"][priority_area]["purchase_33"]

    cost = base * shovi_aku * rate
    return {"cost_ils": round(cost),
            "formula": f"({total_sqm_aku}+{potential_sqm_aku}-{deduction}) × {shovi_aku} × {rate}",
            "rate_used": rate, "deduction_applied": deduction,
            "note": "Only post-2009 purchases deducted" if not purchased_after_2009 and purchased_heter > 0 else None}

@tool
def calc_sqm_equivalent(taba_rights: dict, plot_size_sqm: float) -> dict:
    """Calculate מ"ר אקוויוולנטי from תב"ע rights (not existing buildings!)."""
    coefficients = {
        "main": 1.0, "mamad": 0.9, "service": 0.4,
        "auxiliary": 0.5, "yard_effective": 0.25,
        "yard_remainder": 0.2, "yard_far": 0.1,
        "pool": 0.3, "basement": 0.7
    }
    ...

@tool
def calc_pitzul(plot_sqm: float, sqm_aku: float, shovi_aku: float,
                after_33: bool) -> dict:
    """Calculate פיצול מגרש (plot splitting) costs."""
    ...

@tool
def calc_hetel_hashbacha(old_rights: dict, new_rights: dict,
                          shovi_aku: float, mimush_type: str) -> dict:
    """Calculate היטל השבחה (betterment levy)."""
    ...

@tool
def lookup_shovi_aku(moshav_name: str) -> dict:
    """Look up שווי מ"ר אקוויוולנטי for a settlement from reference table."""
    ...

@tool
def lookup_dmei_heter_plach(merhav: str, shimush: str) -> dict:
    """Look up פל"ח permit fees by planning area and usage type."""
    ...
```

---

## 6. Subagents - Parallel Processing

The Claude Agent SDK supports **subagents** - separate agent instances for focused subtasks. Each runs in its own conversation.

### Useful Subagents for Our Workflow:

```python
# The main agent spawns subagents for parallel work:

# Subagent 1: תב"ע Analyzer
taba_agent = SubAgent(
    name="taba_analyzer",
    instructions="You analyze תב"ע documents and extract building rights...",
    tools=[search_taba_govmap, extract_zoning_table, parse_taba_conditions]
)

# Subagent 2: Building Classifier
building_agent = SubAgent(
    name="building_classifier",
    instructions="You classify buildings from survey maps and compare to permits...",
    tools=[parse_survey_map, compare_to_permit, classify_building]
)

# Subagent 3: Cost Calculator
calc_agent = SubAgent(
    name="cost_calculator",
    instructions="You calculate all financial costs for hesdara, hivun, pitzul...",
    tools=[calc_dmei_heter, calc_dmei_shimush, calc_hivun_375, calc_hivun_33, calc_pitzul]
)
```

**Benefits:**
- Each subagent has focused context (not polluted with unrelated data)
- Run in parallel when independent
- Only the final result returns to the parent (saves tokens)
- Each can have its own tools and system prompt

---

## 7. Hooks - Quality Control & Audit

Hooks intercept the agent at specific points for validation:

```python
from claude_agent_sdk import Hook

@hook("PreToolUse")
def validate_calculation_inputs(tool_name, tool_input):
    """Validate inputs before any calculation tool runs."""
    if tool_name.startswith("calc_"):
        # Ensure all numeric inputs are positive
        for key, value in tool_input.items():
            if isinstance(value, (int, float)) and value < 0:
                return {"block": True, "message": f"Invalid negative value for {key}"}
    return {"block": False}

@hook("PostToolUse")
def log_calculations(tool_name, tool_input, tool_output):
    """Log every calculation for audit trail."""
    if tool_name.startswith("calc_"):
        audit_log.append({
            "tool": tool_name,
            "input": tool_input,
            "output": tool_output,
            "timestamp": datetime.now().isoformat()
        })

@hook("Stop")
def validate_report_completeness(final_response):
    """Before the agent stops, verify the report has all required sections."""
    required = ["ניתוח תב\"ע", "מתווה הסדרה", "היוון", "סיכום עלויות"]
    missing = [s for s in required if s not in final_response]
    if missing:
        return {"continue": True, "message": f"Missing sections: {missing}"}
```

---

## 8. Reference Data Management

### Loading Reference Tables into Agent Context:

```python
import pandas as pd

# Load all reference tables at startup
DMEI_HETER_TABLE = pd.read_excel("דמי היתר לפי ישובים.xlsx")
PLACH_TABLE = pd.read_excel("דמי היתר פלח לפי מרחב.xlsx")
LAND_VALUES = pd.read_excel("ערכי קרקע לשימושים נלווים.xlsx")
RMI_RULES = pd.read_excel("הנחיות והחלטות רמי.xlsx")

# Convert to lookup tools
@tool
def lookup_shovi_aku(moshav_name: str) -> dict:
    """Look up שווי מ"ר אקו' for a moshav."""
    match = DMEI_HETER_TABLE[DMEI_HETER_TABLE["שם המושב"] == moshav_name]
    if match.empty:
        return {"found": False, "message": f"לא נמצא שווי למושב {moshav_name}"}
    row = match.iloc[0]
    return {
        "found": True,
        "moshav": moshav_name,
        "shovi_aku": row["דמי היתר"],
        "date": str(row["תאריך הנתון"]),
        "validity": row.get("תאריך תוקף", "לא צוין")
    }
```

### Alternative: Load into SQLite via MCP

```sql
-- Import Excel tables into SQLite for querying
CREATE TABLE dmei_heter (
    moshav TEXT PRIMARY KEY,
    shovi_aku REAL,
    date_updated TEXT,
    validity TEXT
);

CREATE TABLE plach_rates (
    merhav TEXT,
    shimush TEXT,
    dmei_heter REAL,
    date_from TEXT
);
```

Then use custom Python lookup tools (via openpyxl/pandas) to query this data. No need for SQLite MCP - direct Python is simpler and more debuggable.

---

## 9. Security Architecture

> **Expert review: Security was entirely missing. This is non-negotiable for client data.**

### 9.1 Secrets Management
- **Never** store API keys in environment variables on shared machines
- Use: Docker secrets (minimum), AWS Secrets Manager / HashiCorp Vault (production)
- Rotate keys: ANTHROPIC_API_KEY, MONDAY_API_TOKEN, Google/Microsoft OAuth tokens

### 9.2 Access Control (RBAC)
```
Roles:
- admin:     full access, system config, rate updates
- appraiser: create/edit/view own reports, submit for review
- reviewer:  view/approve/reject reports, cannot create
- client:    view own report only (read-only link)
```

### 9.3 Data Isolation
- Each user/client combination has isolated data
- Database: row-level security (PostgreSQL RLS) or tenant column
- File storage: separate folders per client, no cross-access

### 9.4 Input Sanitization
- File uploads go through validation before parsing (type check, size limit, virus scan)
- Reject: `.exe`, `.bat`, `.sh`, password-protected PDFs, files > 50MB

### 9.5 Audit Logging (Immutable)
- Every calculation, classification decision, and user override logged with timestamp
- Logs stored in append-only table (no UPDATE/DELETE)
- For legal defensibility of report numbers

### 9.6 Privacy Compliance (חוק הגנת הפרטיות)
- Client data (names, property details, financial info) = personal data
- Define retention policy (e.g., 7 years per tax regulations)
- Encryption at rest (database) and in transit (HTTPS)
- Data deletion on client request

---

## 10. API Layer & Job Queue

> **Expert review: Without this, two users cannot run reports simultaneously.**

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│ Frontend │────→│ FastAPI       │────→│ Job Worker    │
│ (React)  │←────│ + WebSocket   │←────│ (Agent runs)  │
└──────────┘     │ + Job Queue   │     └──────────────┘
                 └──────┬───────┘
                        │
                 ┌──────▼───────┐
                 │ PostgreSQL    │
                 │ + Redis cache │
                 └──────────────┘
```

- **FastAPI** serves the REST API + WebSocket for streaming
- **Redis** or **asyncio queue** manages report jobs
- Each report = a job with status tracking (queued → running → completed/failed)
- Frontend polls for status or gets WebSocket updates
- Agent runs in a worker process - isolated from the API server

---

## 11. Hebrew PDF Validation (Week 0 Go/No-Go)

> **Expert review: This must be tested BEFORE any development begins.**

```
Week 0 test plan:
1. Take 5 real Hebrew planning documents (תב"ע PDFs)
2. Run Docling extraction on each
3. Check: Is Hebrew text extracted correctly? (not reversed, not garbled)
4. Check: Are tables extracted with correct structure?
5. Check: Is RTL reading order preserved?

If Docling fails → fallback options:
  a. PyMuPDF with custom Hebrew post-processing
  b. pdf2image + Google Cloud Vision OCR
  c. pdfplumber for tables + PyMuPDF for text

If ALL fail → the document processing architecture needs redesign.
This is a GO/NO-GO gate. Do not proceed to Phase 1 without passing.
```

---

## 12. Chat UI - Chainlit

**Chainlit** is purpose-built for LLM chat apps with tool-use visualization.

| Feature | Chainlit | Streamlit | Gradio |
|---|---|---|---|
| Chat-native | Yes | Bolted on | Bolted on |
| Tool call visualization | Built-in | Manual | Manual |
| File uploads | Built-in multimodal | Basic | Basic |
| Streaming | Native | Basic | Basic |
| Step-by-step display | Built-in | Manual | Manual |
| Authentication | Built-in | Manual | Basic |
| Async support | Native | Limited | Limited |

```python
import chainlit as cl
from agent import RealEstateAgent

@cl.on_chat_start
async def start():
    agent = RealEstateAgent()
    cl.user_session.set("agent", agent)
    await cl.Message(content="שלום! אני סוכן בדיקת התכנות. אנא העלה מפת מדידה והיתרי בנייה.").send()

@cl.on_message
async def main(message: cl.Message):
    agent = cl.user_session.get("agent")

    # Handle file uploads
    if message.elements:
        for file in message.elements:
            await agent.ingest_document(file.path, file.name)

    # Run agent with streaming
    async with cl.Step(name="ניתוח") as step:
        response = await agent.run(message.content)
        step.output = response.summary

    await cl.Message(content=response.text).send()
```

**Note:** The original Chainlit team stepped back from active development in May 2025. It's now community-maintained. For production, consider **React + FastAPI** with WebSocket streaming.

References:
- [Chainlit GitHub](https://github.com/Chainlit/chainlit) (12k+ stars)

---

## 13. Testing & Evaluation

### Test Strategy:

```
┌─────────────────────────────────────────┐
│ Level 1: Unit Tests (calculations)       │
│   - Every calc tool tested with known    │
│     inputs/outputs from real reports     │
│   - 25 example reports = test cases      │
├─────────────────────────────────────────┤
│ Level 2: Integration Tests (tools)       │
│   - Document parsing produces expected   │
│     structure from known PDFs            │
│   - Web scraping returns valid data      │
├─────────────────────────────────────────┤
│ Level 3: Agent Tests (end-to-end)        │
│   - Given client X's docs, does the      │
│     agent produce a report matching      │
│     the reference report?                │
│   - Golden dataset from 25 examples      │
├─────────────────────────────────────────┤
│ Level 4: LLM-as-Judge                    │
│   - Claude Opus evaluates report         │
│     quality, completeness, accuracy      │
└─────────────────────────────────────────┘
```

### Additional Test Requirements (from expert review):

- **Level 3 acceptance criteria:** All financial figures must be within **1%** of reference report values
- **Mock layer:** All external services (govmap, Monday.com, cloud storage) must be mockable for CI tests
- **Edge case tests:** zero-area buildings, negative values, missing data, plots at settlement boundaries, multiple tabas on same parcel, non-standard plot sizes
- **Rate change regression:** When a rate is updated in `rates_config.json`, verify ALL affected calculations still produce correct results
- **Failure injection:** What happens when govmap is down? Claude API returns 529? PDF is corrupt? Agent must degrade gracefully
- **Load testing:** 10 concurrent reports without interference or data corruption
- **LLM-as-Judge caveat:** Use as supplement only, not sole quality gate (known bias toward own output)

### Tools:
- **Promptfoo** - prompt testing and regression ([promptfoo.dev](https://www.promptfoo.dev/))
- **pytest** - unit/integration tests for calculations
- **Arize Phoenix** - open source LLM observability ([GitHub](https://github.com/Arize-AI/phoenix))

---

## 14. Deployment

### Docker Compose Stack (Development):

```yaml
services:
  api:
    build: .
    ports: ["8000:8000"]
    restart: unless-stopped
    mem_limit: 2g
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
    env_file: .env  # Never inline secrets!
    volumes:
      - ./data:/app/data
      - ./uploads:/app/uploads
      - ./reports:/app/reports
    depends_on: [db, redis]

  db:
    image: postgres:16
    restart: unless-stopped
    volumes: [pgdata:/var/lib/postgresql/data]
    environment:
      POSTGRES_DB: agent_db
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    secrets: [db_password]

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  caddy:  # Reverse proxy with automatic HTTPS
    image: caddy:2
    ports: ["80:80", "443:443"]
    volumes: [./Caddyfile:/etc/caddy/Caddyfile]

volumes:
  pgdata:
secrets:
  db_password:
    file: ./secrets/db_password.txt
```

### Cost Estimate (revised per expert review):

| Component | Cost/Month (Estimate) |
|---|---|
| Claude Sonnet API (~50 reports/mo, ~$1-4 per report with retries) | ~$100-250 |
| Hosting (Cloud Run / small VM) | ~$20-50 |
| PostgreSQL managed | ~$15-30 |
| Redis managed | ~$10-15 |
| Google Cloud Vision OCR (optional) | ~$5-10 |
| **Total** | **~$150-355/month** |

---

## 15. Complete Tech Stack Summary

```
┌─────────────────────────────────────────────────────────┐
│                     FRONTEND                             │
│  Chainlit (prototype) → React + FastAPI (production)     │
├─────────────────────────────────────────────────────────┤
│                   AGENT ENGINE                           │
│  Claude Agent SDK (Python)                               │
│  - Model: Claude Sonnet 4 (fast) / Opus 4 (complex)     │
│  - Hooks: validation, audit logging, completeness check  │
│  - Subagents: taba_analyzer, building_classifier, calc   │
├─────────────────────────────────────────────────────────┤
│              MCP SERVERS (3 only)                         │
│  @playwright/mcp        → Web scraping (Phase 3+)         │
│  @mondaycom/mcp         → Read/update Monday.com boards   │
│  @mcp/server-memory     → Client context persistence      │
├─────────────────────────────────────────────────────────┤
│                 CUSTOM TOOLS (Python)                     │
│  calc_dmei_heter     │ calc_dmei_shimush    │ calc_hivun   │
│  calc_pitzul         │ calc_hetel_hashbacha │ calc_sqm_eq  │
│  lookup_shovi_aku    │ lookup_plach_rates   │ classify_bld │
│  lookup_priority_area│ generate_report      │ parse_pdf    │
│  upload_gdrive       │ upload_onedrive      │ read_excel   │
│  generate_audit_log  │ validate_data_fresh  │ ask_user     │
├─────────────────────────────────────────────────────────┤
│               DOCUMENT PROCESSING                        │
│  Docling (IBM)     → PDF/DOCX parsing + table extraction │
│  pdfplumber        → Fallback PDF table extraction       │
│  docxtpl           → Word report generation from template│
│  openpyxl/pandas   → Excel reading + writing             │
│  Google Vision API → OCR for Hebrew scanned docs         │
├─────────────────────────────────────────────────────────┤
│                   DATA LAYER                             │
│  SQLite (prototype) → PostgreSQL (production)            │
│  Reference tables: דמי היתר, פלח, ערכי קרקע, הנחיות     │
│  25 example reports for training/testing                  │
├─────────────────────────────────────────────────────────┤
│               TESTING & MONITORING                       │
│  pytest + promptfoo + Arize Phoenix                      │
│  Golden dataset: 25 reports as regression tests          │
│  Structured logging with audit trail                     │
└─────────────────────────────────────────────────────────┘
```

---

## 16. Implementation Phases

### ⚠️ Timelines revised per expert review (original was 2x optimistic)

### Week 0: Validation Gates (1 week)
- [ ] **GO/NO-GO: Hebrew PDF extraction** - test Docling with 5 real תב"ע documents
- [ ] Fix VAT to 18% and externalize ALL constants into `rates_config.json`
- [ ] Obtain complete RMI settlement table (450+ settlements, not 110)
- [ ] Obtain priority area classification table (all settlements)
- [ ] Obtain development cost tables by regional council

### Phase 1: POC (Weeks 1-4)
- [ ] Set up Claude Agent SDK with basic tools
- [ ] Build `rates_config.json` with all constants + effective dates
- [ ] Build priority area module (affects ALL calculations)
- [ ] Implement 8 calculation tools with configurable rates + priority discounts
- [ ] Build audit trail / calculation logging
- [ ] Load reference tables as custom Python lookup tools (openpyxl, not MCP)
- [ ] Create Word report template with docxtpl tags
- [ ] Add user confirmation checkpoint after building classification
- [ ] Test with 1 example (כפר ורבורג - רונן)
- [ ] Basic Chainlit UI
- [ ] Monday.com MCP integration (read/update)

### Phase 2: Document Processing (Weeks 5-12)
- [ ] Hebrew PDF parsing (validated in Week 0)
- [ ] Build survey map parser (מפת מדידה) - with quality assessment
- [ ] Expand building classification (basement, attic, ground floor, pre-1965, mobile)
- [ ] **Manual taba data input** (defer govmap scraping!)
- [ ] Direct SDK integration for Google Drive + OneDrive (not hobby MCPs)
- [ ] Test with 5 diverse examples
- [ ] Domain expert review of calculation outputs

### Phase 3: Full Agent (Weeks 13-18)
- [ ] Contact govmap team for API access
- [ ] govmap.gov.il integration (REST API interception via Playwright)
- [ ] Add subagents (taba, buildings, calculations)
- [ ] Implement hooks (validation, audit, completeness)
- [ ] Add memory MCP for session persistence
- [ ] Full report generation with all sections + audit log
- [ ] Test with all 25 examples
- [ ] Regression test suite with mock layer for external services
- [ ] Load testing (10 concurrent reports)

### Phase 4: Production (Weeks 19-24)
- [ ] FastAPI + job queue layer (concurrent users)
- [ ] React frontend (replace Chainlit)
- [ ] PostgreSQL (replace SQLite) with row-level security
- [ ] Security: RBAC, secrets management, encryption, data isolation
- [ ] Docker deployment with health checks, restart policies, resource limits
- [ ] Reverse proxy with TLS (nginx/Caddy)
- [ ] Authentication + multi-user
- [ ] Monitoring (Arize Phoenix) + cost tracking
- [ ] Human review workflow with field-level overrides
- [ ] CI/CD pipeline with agent regression tests
- [ ] Documentation and user training

### Total realistic timeline: **24 weeks (6 months)**

---

## Sources

- [Claude Agent SDK Python - GitHub](https://github.com/anthropics/claude-agent-sdk-python)
- [Agent SDK Docs](https://platform.claude.com/docs/en/agent-sdk/overview)
- [Building Agents with Claude Agent SDK - Anthropic](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
- [Official MCP Servers - GitHub](https://github.com/modelcontextprotocol/servers)
- [Playwright MCP - Microsoft](https://github.com/microsoft/playwright-mcp)
- [Ultimate MCP Server - GitHub](https://github.com/Dicklesworthstone/ultimate_mcp_server)
- [awesome-mcp-servers](https://github.com/wong2/awesome-mcp-servers)
- [Docling - IBM/GitHub](https://github.com/docling-project/docling)
- [docxtpl - GitHub](https://github.com/elapouya/python-docx-template)
- [Chainlit - GitHub](https://github.com/Chainlit/chainlit)
- [Promptfoo](https://www.promptfoo.dev/docs/providers/claude-agent-sdk/)
- [Arize Phoenix - GitHub](https://github.com/Arize-AI/phoenix)
- [MCP Servers Directory](https://mcpservers.org/)
- [govmap.gov.il](https://www.govmap.gov.il/)
