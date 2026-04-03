"""Immutable, append-only audit logging for all calculations and decisions.

Per workflow step 12 (agent_workflow_flow.md section 12, "yoman hishuvim"):
the audit log is a companion document that records:
- Every data source scanned (taba, permit, value table) + date
- Every formula applied with exact inputs and outputs
- Every classification decision with reasoning
- Every user override
- All rates/constants used (VAT, permit rate, discounts)
"""

from __future__ import annotations

import copy
import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from models.report import AuditEntry

# Valid entry types for filtering
ENTRY_TYPES = frozenset({"calculation", "classification", "user_override", "data_source"})


class AuditLogger:
    """Immutable, append-only audit logger for all calculations and decisions.

    Records every tool call, classification decision, and user override.
    Thread-safe for concurrent access via threading.Lock.
    """

    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._next_id = 1

    def _append(self, entry: dict[str, Any]) -> None:
        """Append an entry with auto-generated id and timestamp (internal, under lock)."""
        entry["entry_id"] = self._next_id
        entry["timestamp"] = datetime.now(UTC).isoformat()
        self._next_id += 1
        self._entries.append(entry)

    def log_calculation(
        self,
        tool_name: str,
        inputs: dict[str, Any],
        formula: str,
        rates_used: dict[str, Any],
        result: dict[str, Any],
        source_reference: str = "",
        source_date: str | None = None,
    ) -> None:
        """Log a calculation tool invocation.

        Args:
            tool_name: Name of the calc tool (e.g., "calculate_dmei_heter").
            inputs: All input parameters.
            formula: The formula string used.
            rates_used: All rates/constants from config that were applied.
            result: The calculation result dict.
            source_reference: Data source (e.g., "tabela dmei heter lefi yishuvim").
            source_date: Date of the source data.
        """
        with self._lock:
            self._append(
                {
                    "type": "calculation",
                    "tool_name": tool_name,
                    "inputs": inputs,
                    "formula": formula,
                    "rates_used": rates_used,
                    "result": result,
                    "source_reference": source_reference,
                    "source_date": source_date,
                }
            )

    def log_classification(
        self,
        building_id: int,
        building_name: str,
        classification: str,
        reasoning: str,
        confidence: str = "high",
    ) -> None:
        """Log a building classification decision.

        Args:
            building_id: Building number from survey map.
            building_name: Building description.
            classification: The assigned type (e.g., "residential", "service").
            reasoning: Why this classification was chosen.
            confidence: "high", "medium", or "low".
        """
        with self._lock:
            self._append(
                {
                    "type": "classification",
                    "building_id": building_id,
                    "building_name": building_name,
                    "classification": classification,
                    "reasoning": reasoning,
                    "confidence": confidence,
                }
            )

    def log_user_override(
        self,
        field: str,
        original_value: Any,
        new_value: Any,
        reason: str = "",
    ) -> None:
        """Log when a user overrides an agent decision.

        Args:
            field: What was changed (e.g., "building_3_type").
            original_value: The agent's original value.
            new_value: The user's override value.
            reason: User's stated reason (if any).
        """
        with self._lock:
            self._append(
                {
                    "type": "user_override",
                    "field": field,
                    "original_value": original_value,
                    "new_value": new_value,
                    "reason": reason,
                }
            )

    def log_data_source(
        self,
        source_type: str,
        source_name: str,
        source_date: str | None,
        file_path: str | None = None,
    ) -> None:
        """Log a data source that was consulted.

        Args:
            source_type: "taba", "permit", "reference_table", "survey_map".
            source_name: Human-readable name.
            source_date: Date of the source data.
            file_path: Path to the source file.
        """
        with self._lock:
            self._append(
                {
                    "type": "data_source",
                    "source_type": source_type,
                    "source_name": source_name,
                    "source_date": source_date,
                    "file_path": file_path,
                }
            )

    @property
    def entries(self) -> list[dict[str, Any]]:
        """Return a deep copy of all entries (immutable access)."""
        with self._lock:
            return copy.deepcopy(self._entries)

    @property
    def entry_count(self) -> int:
        """Number of entries logged."""
        with self._lock:
            return len(self._entries)

    def get_entries_by_type(self, entry_type: str) -> list[dict[str, Any]]:
        """Filter entries by type.

        Args:
            entry_type: One of "calculation", "classification", "user_override", "data_source".

        Returns:
            Deep copy of matching entries.
        """
        with self._lock:
            return copy.deepcopy([e for e in self._entries if e.get("type") == entry_type])

    def to_json(self, indent: int = 2) -> str:
        """Export the full audit log as JSON string (UTF-8, ensure_ascii=False).

        Args:
            indent: JSON indentation level.

        Returns:
            JSON string with Hebrew text preserved.
        """
        with self._lock:
            return json.dumps(
                self._entries,
                indent=indent,
                ensure_ascii=False,
                default=str,
            )

    def save_json(self, file_path: str) -> None:
        """Save audit log to a JSON file.

        Args:
            file_path: Destination path for the JSON file.
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = self.to_json()
        path.write_text(content, encoding="utf-8")

    def to_audit_entries(self) -> list[AuditEntry]:
        """Convert calculation entries to list of AuditEntry pydantic models.

        Only entries of type "calculation" map directly to AuditEntry.
        Classification and override entries are converted with appropriate
        field mapping so no data is lost.

        Returns:
            List of AuditEntry instances from src.models.report.
        """
        result: list[AuditEntry] = []
        with self._lock:
            for entry in self._entries:
                entry_type = entry.get("type")
                if entry_type == "calculation":
                    result.append(
                        AuditEntry(
                            timestamp=entry["timestamp"],
                            tool_name=entry["tool_name"],
                            inputs=entry["inputs"],
                            formula=entry["formula"],
                            rates_used=entry["rates_used"],
                            result=entry["result"],
                            source_reference=entry.get("source_reference", ""),
                            source_date=entry.get("source_date"),
                        )
                    )
                elif entry_type == "classification":
                    result.append(
                        AuditEntry(
                            timestamp=entry["timestamp"],
                            tool_name="building_classification",
                            inputs={
                                "building_id": entry["building_id"],
                                "building_name": entry["building_name"],
                            },
                            formula="classification_decision",
                            rates_used={},
                            result={
                                "classification": entry["classification"],
                                "confidence": entry["confidence"],
                            },
                            reasoning=entry["reasoning"],
                        )
                    )
                elif entry_type == "user_override":
                    result.append(
                        AuditEntry(
                            timestamp=entry["timestamp"],
                            tool_name="user_override",
                            inputs={"field": entry["field"]},
                            formula="manual_override",
                            rates_used={},
                            result={"new_value": entry["new_value"]},
                            user_overrides={
                                entry["field"]: {
                                    "original": entry["original_value"],
                                    "new": entry["new_value"],
                                }
                            },
                            reasoning=entry.get("reason", ""),
                        )
                    )
                elif entry_type == "data_source":
                    result.append(
                        AuditEntry(
                            timestamp=entry["timestamp"],
                            tool_name="data_source_scan",
                            inputs={
                                "source_type": entry["source_type"],
                                "source_name": entry["source_name"],
                            },
                            formula="data_source_consultation",
                            rates_used={},
                            result={"consulted": True},
                            source_reference=entry["source_name"],
                            source_date=entry.get("source_date"),
                        )
                    )
        return result

    def generate_summary(self) -> dict[str, Any]:
        """Generate a summary of the audit log.

        Returns:
            Dictionary with total counts by type, unique rates used across
            all calculations, and the timestamp range.
        """
        with self._lock:
            calcs = [e for e in self._entries if e["type"] == "calculation"]
            classifications = [e for e in self._entries if e["type"] == "classification"]
            overrides = [e for e in self._entries if e["type"] == "user_override"]
            sources = [e for e in self._entries if e["type"] == "data_source"]

            # Collect all unique rates used across calculations
            rates_summary: dict[str, Any] = {}
            for calc in calcs:
                for key, value in calc.get("rates_used", {}).items():
                    rates_summary[key] = value

            # Timestamp range
            timestamps = [e["timestamp"] for e in self._entries]
            timestamp_range: dict[str, str | None] = {"first": None, "last": None}
            if timestamps:
                timestamp_range["first"] = timestamps[0]
                timestamp_range["last"] = timestamps[-1]

            return {
                "total_entries": len(self._entries),
                "calculations": len(calcs),
                "classifications": len(classifications),
                "user_overrides": len(overrides),
                "data_sources": len(sources),
                "rates_used_summary": rates_summary,
                "timestamp_range": timestamp_range,
            }

    def clear(self) -> None:
        """Clear all entries (for testing only -- normally audit logs are immutable)."""
        with self._lock:
            self._entries.clear()
            self._next_id = 1
