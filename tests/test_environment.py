"""Environment validation tests - verify all dependencies are installed and working."""

import importlib
import json
import os
import sys


def test_python_version():
    """Python 3.10+ required."""
    assert sys.version_info >= (3, 10), f"Python 3.10+ required, got {sys.version}"


def test_core_imports():
    """All core packages can be imported."""
    packages = [
        "claude_agent_sdk",
        "chainlit",
        "fastapi",
        "uvicorn",
        "pydantic",
        "pydantic_settings",
    ]
    for pkg in packages:
        mod = importlib.import_module(pkg)
        assert mod is not None, f"Failed to import {pkg}"


def test_document_imports():
    """All document processing packages can be imported."""
    packages = [
        "docling",
        "pdfplumber",
        "docx",
        "docxtpl",
        "openpyxl",
        "pandas",
        "xlsxwriter",
    ]
    for pkg in packages:
        mod = importlib.import_module(pkg)
        assert mod is not None, f"Failed to import {pkg}"


def test_integration_imports():
    """All integration packages can be imported."""
    packages = [
        "googleapiclient",
        "msgraph_core",
        "playwright",
    ]
    for pkg in packages:
        mod = importlib.import_module(pkg)
        assert mod is not None, f"Failed to import {pkg}"


def test_testing_imports():
    """Testing tools available."""
    import pytest
    import httpx

    assert pytest is not None
    assert httpx is not None


def test_project_structure():
    """Required directories exist."""
    required_dirs = [
        "src/tools",
        "src/models",
        "src/config",
        "src/api",
        "src/ui",
        "src/documents",
        "src/integrations",
        "src/agent",
        "data/templates",
        "data/reference",
        "tests/golden",
        "docs",
        ".claude/agents",
    ]
    for d in required_dirs:
        assert os.path.isdir(d), f"Missing directory: {d}"


def test_agent_definitions_exist():
    """All 8 agent definitions exist."""
    agents = [
        "calc-builder",
        "doc-builder",
        "integration-builder",
        "agent-builder",
        "ui-builder",
        "validator-code",
        "validator-domain",
        "validator-ux",
    ]
    for agent in agents:
        path = f".claude/agents/{agent}.md"
        assert os.path.isfile(path), f"Missing agent: {path}"


def test_reference_data_present():
    """Reference data files copied."""
    ref_files = os.listdir("data/reference")
    assert len(ref_files) >= 5, f"Expected 5+ reference files, found {len(ref_files)}"


def test_template_present():
    """Word template file exists."""
    template_files = os.listdir("data/templates")
    assert len(template_files) >= 1, f"Expected template files, found {len(template_files)}"


def test_golden_data_present():
    """25 example reports copied for testing."""
    golden_path = "tests/golden/בדיקות התכנות"
    assert os.path.isdir(golden_path), f"Missing golden test data directory: {golden_path}"
    examples = os.listdir(golden_path)
    assert len(examples) >= 20, f"Expected 20+ examples, found {len(examples)}"


def test_init_files_exist():
    """All Python packages have __init__.py."""
    packages = [
        "src", "src/tools", "src/models", "src/config", "src/api",
        "src/ui", "src/documents", "src/integrations", "src/agent",
    ]
    for pkg in packages:
        init_path = os.path.join(pkg, "__init__.py")
        assert os.path.isfile(init_path), f"Missing {init_path}"


def test_env_example_exists():
    """.env.example has all required keys."""
    assert os.path.isfile(".env.example"), "Missing .env.example"
    with open(".env.example", encoding="utf-8") as f:
        content = f.read()
    required_keys = ["ANTHROPIC_API_KEY", "MONDAY_API_TOKEN", "MONDAY_BOARD_ID",
                     "ONEDRIVE_CLIENT_ID", "GOOGLE_DRIVE_CREDENTIALS_PATH", "LOG_LEVEL"]
    for key in required_keys:
        assert key in content, f".env.example missing key: {key}"


def test_mcp_config():
    """.mcp.json has correct MCP servers (3 only)."""
    assert os.path.isfile(".mcp.json"), "Missing .mcp.json"
    with open(".mcp.json", encoding="utf-8") as f:
        config = json.load(f)
    servers = config.get("mcpServers", {})
    assert "playwright" in servers, "Missing playwright MCP"
    assert "monday" in servers, "Missing monday MCP"
    assert "memory" in servers, "Missing memory MCP"
    assert len(servers) == 3, f"Expected exactly 3 MCP servers, found {len(servers)}: {list(servers.keys())}"
    # Should NOT have removed servers
    assert "filesystem" not in servers, "filesystem MCP should be removed (SDK built-in)"
    assert "excel" not in servers, "excel MCP should be removed (use openpyxl)"
    assert "pdf" not in servers, "pdf MCP should be removed (use Docling)"


def test_claude_md_exists():
    """CLAUDE.md project config exists."""
    assert os.path.isfile("CLAUDE.md"), "Missing CLAUDE.md"
    with open("CLAUDE.md", encoding="utf-8") as f:
        content = f.read()
    assert "rates_config.json" in content, "CLAUDE.md should reference rates_config"
    assert "hardcode" in content.lower() or "hardcoded" in content.lower(), "CLAUDE.md should warn against hardcoding"


def test_pyproject_toml():
    """pyproject.toml configured correctly."""
    assert os.path.isfile("pyproject.toml"), "Missing pyproject.toml"
    with open("pyproject.toml", encoding="utf-8") as f:
        content = f.read()
    assert "ruff" in content, "pyproject.toml should configure ruff"
    assert "pytest" in content, "pyproject.toml should configure pytest"


def test_utf8_encoding():
    """Hebrew text handling works."""
    test_text = "בדיקת התכנות נחלות"
    encoded = test_text.encode("utf-8")
    decoded = encoded.decode("utf-8")
    assert decoded == test_text, "UTF-8 Hebrew encoding/decoding failed"

    # JSON roundtrip
    data = {"name": "משפחת רונן", "moshav": "כפר ורבורג"}
    json_str = json.dumps(data, ensure_ascii=False)
    assert "משפחת" in json_str, "JSON should preserve Hebrew with ensure_ascii=False"
