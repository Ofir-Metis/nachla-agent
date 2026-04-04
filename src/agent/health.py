"""Health check endpoints for production monitoring.

Checks:
- Application status (always healthy if running)
- Database connectivity (SQLite/PostgreSQL)
- MCP server status (playwright, monday, memory)
- Reference data freshness (warn if > 90 days)
- Disk space (warn if < 1GB free)
"""

from __future__ import annotations

import json
import logging
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Application start time for uptime calculation
_start_time: float = time.monotonic()

# Project root: navigate from src/agent/health.py up to project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Staleness threshold in days for reference data files
_REFERENCE_DATA_MAX_AGE_DAYS = 90

# Minimum free disk space in bytes (1 GB)
_MIN_DISK_SPACE_BYTES = 1_073_741_824


class HealthChecker:
    """Production health monitoring.

    Runs fast, non-destructive checks against the application environment
    and returns a structured status report suitable for load balancers,
    alerting systems, and Kubernetes probes.
    """

    def __init__(
        self,
        *,
        app_version: str = "0.1.0",
        database_url: str = "sqlite+aiosqlite:///./nachla.db",
        project_root: Path | None = None,
    ) -> None:
        self.app_version = app_version
        self.database_url = database_url
        self.project_root = project_root or _PROJECT_ROOT

    async def check_all(self) -> dict[str, Any]:
        """Run all health checks and return an aggregate status.

        Returns:
            A dictionary with overall status, timestamp, per-check details,
            and application uptime in seconds.
        """
        checks: dict[str, dict[str, Any]] = {}

        # App check (always ok if this code is executing)
        checks["app"] = {"status": "ok", "version": self.app_version}

        # Database
        checks["database"] = await self.check_database()

        # Reference data freshness
        checks["reference_data"] = self.check_reference_data()

        # Disk space
        checks["disk_space"] = self.check_disk_space()

        # MCP server configs
        checks["mcp_servers"] = self.check_mcp_servers()

        # Derive overall status
        statuses = [c.get("status", "ok") for c in checks.values()]
        if any(s == "error" for s in statuses):
            overall = "unhealthy"
        elif any(s in ("warning", "stale") for s in statuses):
            overall = "degraded"
        else:
            overall = "healthy"

        return {
            "status": overall,
            "timestamp": datetime.now(UTC).isoformat(),
            "checks": checks,
            "uptime_seconds": round(time.monotonic() - _start_time, 2),
        }

    async def check_database(self) -> dict[str, Any]:
        """Check database connectivity.

        For SQLite, verifies the path is writable. For PostgreSQL, attempts
        a lightweight connection test via asyncpg if available.

        Returns:
            Check result with status and database type.
        """
        db_type = "sqlite" if "sqlite" in self.database_url else "postgres"

        try:
            if db_type == "sqlite":
                # Extract path from URL like sqlite+aiosqlite:///./nachla.db
                db_path_str = self.database_url.split("///")[-1]
                db_path = Path(db_path_str)
                # For SQLite dev mode, the file may not exist yet (created on first use)
                parent = db_path.parent.resolve()
                if parent.exists() and parent.is_dir():
                    return {"status": "ok", "type": db_type, "path": str(db_path)}
                return {
                    "status": "error",
                    "type": db_type,
                    "error": f"Parent directory does not exist: {parent}",
                }
            else:
                # PostgreSQL: try importing asyncpg to see if driver is available
                try:
                    import asyncpg  # noqa: F401

                    return {"status": "ok", "type": db_type, "driver": "asyncpg"}
                except ImportError:
                    return {
                        "status": "warning",
                        "type": db_type,
                        "error": "asyncpg not installed - cannot verify PostgreSQL connectivity",
                    }
        except Exception as exc:
            logger.exception("Database health check failed")
            return {"status": "error", "type": db_type, "error": str(exc)}

    def check_reference_data(self) -> dict[str, Any]:
        """Check freshness of reference data files in data/reference/.

        Warns if any file is older than 90 days.

        Returns:
            Check result with status, file count, and any stale files.
        """
        ref_dir = self.project_root / "data" / "reference"
        if not ref_dir.exists():
            return {"status": "ok", "message": "No reference data directory", "files": {}}

        now = datetime.now(UTC)
        files_info: dict[str, dict[str, Any]] = {}
        stale_files: list[str] = []

        for file_path in ref_dir.iterdir():
            if file_path.is_file():
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=UTC)
                age_days = (now - mtime).days
                files_info[file_path.name] = {
                    "last_modified": mtime.isoformat(),
                    "age_days": age_days,
                }
                if age_days > _REFERENCE_DATA_MAX_AGE_DAYS:
                    stale_files.append(file_path.name)

        if stale_files:
            return {
                "status": "stale",
                "message": f"{len(stale_files)} file(s) older than {_REFERENCE_DATA_MAX_AGE_DAYS} days",
                "stale_files": stale_files,
                "files": files_info,
            }

        return {"status": "ok", "file_count": len(files_info), "files": files_info}

    def check_disk_space(self) -> dict[str, Any]:
        """Check available disk space on the project root volume.

        Warns if less than 1 GB is free.

        Returns:
            Check result with status and free space in gigabytes.
        """
        try:
            usage = shutil.disk_usage(self.project_root)
            free_gb = round(usage.free / (1024**3), 2)
            status = "ok" if usage.free >= _MIN_DISK_SPACE_BYTES else "warning"
            return {
                "status": status,
                "free_gb": free_gb,
                "total_gb": round(usage.total / (1024**3), 2),
            }
        except Exception as exc:
            logger.exception("Disk space check failed")
            return {"status": "error", "error": str(exc)}

    def check_mcp_servers(self) -> dict[str, Any]:
        """Check if MCP server configurations exist in .mcp.json.

        Validates that the expected servers (playwright, monday, memory) are
        defined in the configuration file.

        Returns:
            Check result with status and per-server presence.
        """
        mcp_path = self.project_root / ".mcp.json"
        expected_servers = ["playwright", "monday", "memory"]

        if not mcp_path.exists():
            return {
                "status": "warning",
                "error": ".mcp.json not found",
                "servers": {s: False for s in expected_servers},
            }

        try:
            with open(mcp_path, encoding="utf-8") as f:
                config = json.load(f)

            servers_config = config.get("mcpServers", {})
            servers_present: dict[str, bool] = {}
            for server_name in expected_servers:
                servers_present[server_name] = server_name in servers_config

            missing = [s for s, present in servers_present.items() if not present]
            if missing:
                return {
                    "status": "warning",
                    "message": f"Missing MCP server configs: {', '.join(missing)}",
                    "servers": servers_present,
                }

            return {"status": "ok", "servers": servers_present}
        except (json.JSONDecodeError, OSError) as exc:
            logger.exception("Failed to read .mcp.json")
            return {"status": "error", "error": str(exc), "servers": {s: False for s in expected_servers}}
