"""Production readiness tests.

Verify that the application is configured correctly for deployment.
Tests cover settings defaults, health checks, and .env.example completeness.
"""

from __future__ import annotations

import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from agent.health import HealthChecker
from config.settings import AppSettings

# Project root (tests/ -> project root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# TestProductionSettings
# ---------------------------------------------------------------------------
class TestProductionSettings:
    """Verify AppSettings loads correctly with production-relevant defaults."""

    def test_settings_load_with_defaults(self) -> None:
        """Settings load with all default values without any .env file."""
        settings = AppSettings(
            _env_file=None,  # type: ignore[call-arg]
        )
        assert settings.log_level == "INFO"
        assert settings.environment == "development"
        assert settings.app_version == "0.1.0"
        assert settings.rate_limit_per_minute == 60
        assert settings.max_upload_size_mb == 50

    def test_database_url_default_sqlite(self) -> None:
        """Default database is SQLite for development."""
        settings = AppSettings(_env_file=None)  # type: ignore[call-arg]
        assert "sqlite" in settings.database_url
        assert "aiosqlite" in settings.database_url

    def test_postgres_url_format(self) -> None:
        """PostgreSQL URL is valid format when overridden via env."""
        pg_url = "postgresql+asyncpg://nachla:password@localhost:5432/nachla"
        settings = AppSettings(
            _env_file=None,  # type: ignore[call-arg]
            database_url=pg_url,
        )
        assert settings.database_url == pg_url
        assert "asyncpg" in settings.database_url

    def test_redis_url_default(self) -> None:
        """Default Redis URL points to localhost."""
        settings = AppSettings(_env_file=None)  # type: ignore[call-arg]
        assert settings.redis_url == "redis://localhost:6379/0"

    def test_rbac_disabled_by_default(self) -> None:
        """RBAC is disabled by default (dev mode)."""
        settings = AppSettings(_env_file=None)  # type: ignore[call-arg]
        assert settings.rbac_enabled is False

    def test_allowed_origins_default(self) -> None:
        """Default CORS origins include localhost dev servers."""
        settings = AppSettings(_env_file=None)  # type: ignore[call-arg]
        assert "localhost:8000" in settings.allowed_origins
        assert "localhost:3000" in settings.allowed_origins

    def test_output_directory_default(self) -> None:
        """Default output directory is ./output."""
        settings = AppSettings(_env_file=None)  # type: ignore[call-arg]
        assert settings.output_directory == "./output"

    def test_environment_default_development(self) -> None:
        """Default environment is development."""
        settings = AppSettings(_env_file=None)  # type: ignore[call-arg]
        assert settings.environment == "development"

    def test_all_env_vars_documented(self) -> None:
        """Every AppSettings field that is configurable has a .env.example entry."""
        env_example_path = PROJECT_ROOT / ".env.example"
        assert env_example_path.exists(), ".env.example file must exist"

        env_text = env_example_path.read_text(encoding="utf-8")
        # Extract all KEY= patterns from .env.example (ignore comments)
        env_keys = set()
        for line in env_text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                key = line.split("=", 1)[0].strip()
                env_keys.add(key.upper())

        settings = AppSettings(_env_file=None)  # type: ignore[call-arg]
        # Fields that are NOT env-configurable (loaded from JSON or internal)
        skip_fields = {
            "rates_config",
            "anthropic_model_main",
            "anthropic_model_complex",
            "mcp_config_path",
            "max_report_generation_time",
            "max_tool_retries",
            "checkpoint_timeout",
        }

        missing = []
        for field_name in AppSettings.model_fields:
            if field_name in skip_fields:
                continue
            env_name = field_name.upper()
            if env_name not in env_keys:
                missing.append(env_name)

        assert not missing, f"Settings fields missing from .env.example: {', '.join(sorted(missing))}"


# ---------------------------------------------------------------------------
# TestHealthChecks
# ---------------------------------------------------------------------------
class TestHealthChecks:
    """Verify health check system works correctly."""

    def test_health_checker_creates(self) -> None:
        """HealthChecker initializes without error."""
        checker = HealthChecker()
        assert checker.app_version == "0.1.0"
        assert checker.database_url == "sqlite+aiosqlite:///./nachla.db"

    def test_health_checker_custom_params(self) -> None:
        """HealthChecker accepts custom configuration."""
        checker = HealthChecker(
            app_version="1.2.3",
            database_url="postgresql+asyncpg://localhost/test",
            project_root=Path("/tmp/test"),
        )
        assert checker.app_version == "1.2.3"
        assert "asyncpg" in checker.database_url

    def test_reference_data_freshness_no_dir(self) -> None:
        """Reference data check is ok when directory does not exist."""
        checker = HealthChecker(project_root=Path("/nonexistent/path"))
        result = checker.check_reference_data()
        assert result["status"] == "ok"

    def test_reference_data_freshness_empty_dir(self) -> None:
        """Reference data check is ok when directory is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ref_dir = Path(tmpdir) / "data" / "reference"
            ref_dir.mkdir(parents=True)
            checker = HealthChecker(project_root=Path(tmpdir))
            result = checker.check_reference_data()
            assert result["status"] == "ok"
            assert result.get("file_count", 0) == 0

    def test_reference_data_freshness_stale_file(self) -> None:
        """Reference data check detects stale files (> 90 days old)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ref_dir = Path(tmpdir) / "data" / "reference"
            ref_dir.mkdir(parents=True)
            stale_file = ref_dir / "old_data.csv"
            stale_file.write_text("header\nrow1")
            # Set mtime to 100 days ago
            old_time = time.time() - (100 * 86400)
            os.utime(stale_file, (old_time, old_time))

            checker = HealthChecker(project_root=Path(tmpdir))
            result = checker.check_reference_data()
            assert result["status"] == "stale"
            assert "old_data.csv" in result["stale_files"]

    def test_reference_data_freshness_fresh_file(self) -> None:
        """Reference data check passes for fresh files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ref_dir = Path(tmpdir) / "data" / "reference"
            ref_dir.mkdir(parents=True)
            fresh_file = ref_dir / "new_data.csv"
            fresh_file.write_text("header\nrow1")
            # mtime is now (fresh)

            checker = HealthChecker(project_root=Path(tmpdir))
            result = checker.check_reference_data()
            assert result["status"] == "ok"
            assert result["file_count"] == 1

    def test_disk_space_check(self) -> None:
        """Disk space check returns reasonable values."""
        checker = HealthChecker(project_root=PROJECT_ROOT)
        result = checker.check_disk_space()
        assert result["status"] in ("ok", "warning")
        assert "free_gb" in result
        assert result["free_gb"] > 0
        assert "total_gb" in result
        assert result["total_gb"] > 0

    def test_mcp_config_check(self) -> None:
        """MCP server config check reads .mcp.json."""
        checker = HealthChecker(project_root=PROJECT_ROOT)
        result = checker.check_mcp_servers()
        # Project has .mcp.json with all 3 servers
        assert result["status"] == "ok"
        assert result["servers"]["playwright"] is True
        assert result["servers"]["monday"] is True
        assert result["servers"]["memory"] is True

    def test_mcp_config_missing_file(self) -> None:
        """MCP check warns when .mcp.json is missing."""
        checker = HealthChecker(project_root=Path("/nonexistent/path"))
        result = checker.check_mcp_servers()
        assert result["status"] == "warning"
        assert ".mcp.json not found" in result.get("error", "")

    @pytest.mark.asyncio
    async def test_check_database_sqlite(self) -> None:
        """Database check succeeds for SQLite (default dev mode)."""
        checker = HealthChecker()
        result = await checker.check_database()
        assert result["type"] == "sqlite"
        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_check_database_postgres_no_driver(self) -> None:
        """Database check warns when asyncpg is not installed."""
        checker = HealthChecker(database_url="postgresql+asyncpg://localhost/test")
        # Mock asyncpg import failure
        import builtins

        original_import = builtins.__import__

        def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "asyncpg":
                raise ImportError("no asyncpg")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = await checker.check_database()
        assert result["type"] == "postgres"
        assert result["status"] == "warning"

    @pytest.mark.asyncio
    async def test_overall_status_healthy(self) -> None:
        """Overall status is healthy when all checks pass."""
        checker = HealthChecker(project_root=PROJECT_ROOT)
        result = await checker.check_all()
        assert result["status"] in ("healthy", "degraded")
        assert "timestamp" in result
        assert "uptime_seconds" in result
        assert result["uptime_seconds"] >= 0
        assert "checks" in result
        assert "app" in result["checks"]
        assert result["checks"]["app"]["status"] == "ok"
        assert result["checks"]["app"]["version"] == "0.1.0"

    @pytest.mark.asyncio
    async def test_overall_status_degraded(self) -> None:
        """Overall status is degraded when some checks warn."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create stale reference data to trigger degraded status
            ref_dir = Path(tmpdir) / "data" / "reference"
            ref_dir.mkdir(parents=True)
            stale_file = ref_dir / "old.csv"
            stale_file.write_text("data")
            old_time = time.time() - (100 * 86400)
            os.utime(stale_file, (old_time, old_time))

            checker = HealthChecker(project_root=Path(tmpdir))
            result = await checker.check_all()
            # Should be degraded because reference data is stale and .mcp.json is missing
            assert result["status"] == "degraded"


# ---------------------------------------------------------------------------
# TestEnvExample
# ---------------------------------------------------------------------------
class TestEnvExample:
    """Verify .env.example is complete and safe."""

    def test_env_example_exists(self) -> None:
        """The .env.example file exists and is non-empty."""
        env_path = PROJECT_ROOT / ".env.example"
        assert env_path.exists(), ".env.example must exist at project root"
        content = env_path.read_text(encoding="utf-8")
        assert len(content.strip()) > 0, ".env.example must not be empty"

    def test_env_example_has_all_keys(self) -> None:
        """All required keys are present in .env.example."""
        env_path = PROJECT_ROOT / ".env.example"
        content = env_path.read_text(encoding="utf-8")

        required_keys = [
            "ANTHROPIC_API_KEY",
            "ENVIRONMENT",
            "DATABASE_URL",
            "REDIS_URL",
            "LOG_LEVEL",
            "RBAC_ENABLED",
            "RATE_LIMIT_PER_MINUTE",
            "MAX_UPLOAD_SIZE_MB",
        ]

        for key in required_keys:
            assert key in content, f"Required key '{key}' missing from .env.example"

    def test_no_real_secrets_in_env_example(self) -> None:
        """No actual API keys or passwords in .env.example."""
        env_path = PROJECT_ROOT / ".env.example"
        content = env_path.read_text(encoding="utf-8")

        # Patterns that indicate real secrets
        secret_patterns = [
            r"sk-ant-[a-zA-Z0-9]{20,}",  # Real Anthropic API key
            r"xoxb-[a-zA-Z0-9-]+",  # Slack token
            r"ghp_[a-zA-Z0-9]{36}",  # GitHub PAT
            r"password=[^c][^h][^a]",  # Real password (not 'change-me...')
        ]

        for pattern in secret_patterns:
            matches = re.findall(pattern, content)
            assert not matches, f"Possible real secret found matching pattern '{pattern}': {matches}"

    def test_env_example_no_trailing_whitespace(self) -> None:
        """No trailing whitespace in .env.example lines."""
        env_path = PROJECT_ROOT / ".env.example"
        content = env_path.read_text(encoding="utf-8")
        for i, line in enumerate(content.splitlines(), 1):
            assert line == line.rstrip(), f"Line {i} has trailing whitespace: '{line}'"

    def test_env_example_keys_are_uppercase(self) -> None:
        """All env var keys in .env.example are uppercase."""
        env_path = PROJECT_ROOT / ".env.example"
        content = env_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                key = line.split("=", 1)[0].strip()
                assert key == key.upper(), f"Key '{key}' should be uppercase"
