"""Tests for the immutable, append-only audit logging system."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from agent.audit_log import AuditLogger
from models.report import AuditEntry


class TestAuditLogger:
    """Test suite for AuditLogger."""

    def _make_logger_with_calculation(self) -> AuditLogger:
        """Helper: create a logger with one calculation entry."""
        logger = AuditLogger()
        logger.log_calculation(
            tool_name="calculate_dmei_heter",
            inputs={"building_area": 120, "land_value": 5000},
            formula="dmei_heter = area * value * rate",
            rates_used={"permit_rate": 0.91, "vat": 0.18},
            result={"dmei_heter": 546000, "with_vat": 644280},
            source_reference="טבלת דמי היתר לפי ישובים",
            source_date="2026-01-01",
        )
        return logger

    def test_log_calculation(self) -> None:
        """Log a calculation and verify entry fields."""
        logger = self._make_logger_with_calculation()

        assert logger.entry_count == 1
        entries = logger.entries
        entry = entries[0]
        assert entry["type"] == "calculation"
        assert entry["tool_name"] == "calculate_dmei_heter"
        assert entry["inputs"]["building_area"] == 120
        assert entry["formula"] == "dmei_heter = area * value * rate"
        assert entry["rates_used"]["permit_rate"] == 0.91
        assert entry["result"]["dmei_heter"] == 546000
        assert entry["source_reference"] == "טבלת דמי היתר לפי ישובים"
        assert entry["source_date"] == "2026-01-01"
        assert "entry_id" in entry
        assert "timestamp" in entry

    def test_log_classification(self) -> None:
        """Log a classification decision and verify fields."""
        logger = AuditLogger()
        logger.log_classification(
            building_id=3,
            building_name="מבנה מגורים",
            classification="residential",
            reasoning="Building matches residential pattern based on permit and location",
            confidence="high",
        )

        assert logger.entry_count == 1
        entry = logger.entries[0]
        assert entry["type"] == "classification"
        assert entry["building_id"] == 3
        assert entry["building_name"] == "מבנה מגורים"
        assert entry["classification"] == "residential"
        assert entry["confidence"] == "high"

    def test_log_user_override(self) -> None:
        """Log a user override and verify fields."""
        logger = AuditLogger()
        logger.log_user_override(
            field="building_3_type",
            original_value="service",
            new_value="residential",
            reason="User confirmed building is residential based on actual use",
        )

        assert logger.entry_count == 1
        entry = logger.entries[0]
        assert entry["type"] == "user_override"
        assert entry["field"] == "building_3_type"
        assert entry["original_value"] == "service"
        assert entry["new_value"] == "residential"
        assert entry["reason"] == "User confirmed building is residential based on actual use"

    def test_log_data_source(self) -> None:
        """Log a data source consultation and verify fields."""
        logger = AuditLogger()
        logger.log_data_source(
            source_type="taba",
            source_name='תב"ע מש/1/2020',
            source_date="2020-05-15",
            file_path="/data/taba_2020.pdf",
        )

        assert logger.entry_count == 1
        entry = logger.entries[0]
        assert entry["type"] == "data_source"
        assert entry["source_type"] == "taba"
        assert entry["source_name"] == 'תב"ע מש/1/2020'
        assert entry["source_date"] == "2020-05-15"
        assert entry["file_path"] == "/data/taba_2020.pdf"

    def test_immutable_entries(self) -> None:
        """Entries property returns a copy, not a reference."""
        logger = self._make_logger_with_calculation()

        entries_a = logger.entries
        entries_b = logger.entries

        # They should be equal but not the same object
        assert entries_a == entries_b
        assert entries_a is not entries_b

        # Mutating the copy should not affect the logger
        entries_a[0]["tool_name"] = "MUTATED"
        assert logger.entries[0]["tool_name"] == "calculate_dmei_heter"

    def test_sequential_ids(self) -> None:
        """Entry IDs are sequential starting from 1."""
        logger = AuditLogger()
        logger.log_data_source("taba", "first", None)
        logger.log_data_source("permit", "second", None)
        logger.log_data_source("survey_map", "third", None)

        entries = logger.entries
        assert [e["entry_id"] for e in entries] == [1, 2, 3]

    def test_thread_safety(self) -> None:
        """Multiple threads can log concurrently without data loss."""
        logger = AuditLogger()
        num_threads = 10
        entries_per_thread = 50
        barrier = threading.Barrier(num_threads)

        def worker(thread_id: int) -> None:
            barrier.wait()
            for i in range(entries_per_thread):
                logger.log_calculation(
                    tool_name=f"tool_{thread_id}_{i}",
                    inputs={"thread": thread_id, "iteration": i},
                    formula="test",
                    rates_used={},
                    result={"ok": True},
                )

        threads = [threading.Thread(target=worker, args=(tid,)) for tid in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert logger.entry_count == num_threads * entries_per_thread

        # All entry_ids should be unique
        ids = [e["entry_id"] for e in logger.entries]
        assert len(set(ids)) == num_threads * entries_per_thread

    def test_json_export(self) -> None:
        """Export to JSON with Hebrew text preserved."""
        logger = AuditLogger()
        logger.log_classification(
            building_id=1,
            building_name="מבנה חקלאי",
            classification="agricultural",
            reasoning="שימוש חקלאי מאושר",
        )

        json_str = logger.to_json()
        parsed = json.loads(json_str)

        assert len(parsed) == 1
        assert parsed[0]["building_name"] == "מבנה חקלאי"
        assert parsed[0]["reasoning"] == "שימוש חקלאי מאושר"
        # Verify Hebrew is NOT escaped
        assert "מבנה חקלאי" in json_str
        assert "\\u" not in json_str

    def test_save_json(self, tmp_path: Path) -> None:
        """Save audit log to a JSON file and read it back."""
        logger = self._make_logger_with_calculation()

        file_path = tmp_path / "subdir" / "audit.json"
        logger.save_json(str(file_path))

        assert file_path.exists()
        content = file_path.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert len(parsed) == 1
        assert parsed[0]["tool_name"] == "calculate_dmei_heter"

    def test_generate_summary(self) -> None:
        """Summary includes correct counts and rates."""
        logger = AuditLogger()
        logger.log_calculation(
            tool_name="calc_a",
            inputs={},
            formula="a",
            rates_used={"vat": 0.18, "permit_rate": 0.91},
            result={"total": 100},
        )
        logger.log_calculation(
            tool_name="calc_b",
            inputs={},
            formula="b",
            rates_used={"vat": 0.18, "usage_fee": 0.05},
            result={"total": 200},
        )
        logger.log_classification(
            building_id=1,
            building_name="test",
            classification="residential",
            reasoning="test",
        )
        logger.log_user_override(field="x", original_value=1, new_value=2)
        logger.log_data_source(source_type="taba", source_name="t", source_date=None)

        summary = logger.generate_summary()
        assert summary["total_entries"] == 5
        assert summary["calculations"] == 2
        assert summary["classifications"] == 1
        assert summary["user_overrides"] == 1
        assert summary["data_sources"] == 1
        assert summary["rates_used_summary"]["vat"] == 0.18
        assert summary["rates_used_summary"]["permit_rate"] == 0.91
        assert summary["rates_used_summary"]["usage_fee"] == 0.05
        assert summary["timestamp_range"]["first"] is not None
        assert summary["timestamp_range"]["last"] is not None

    def test_to_audit_entries(self) -> None:
        """Convert to AuditEntry pydantic models for all entry types."""
        logger = AuditLogger()
        logger.log_calculation(
            tool_name="calculate_dmei_heter",
            inputs={"area": 100},
            formula="area * rate",
            rates_used={"rate": 0.91},
            result={"total": 91},
            source_reference="ref",
            source_date="2026-01-01",
        )
        logger.log_classification(
            building_id=1,
            building_name="test",
            classification="residential",
            reasoning="reason",
        )
        logger.log_user_override(
            field="building_1_type",
            original_value="service",
            new_value="residential",
            reason="user says so",
        )
        logger.log_data_source(
            source_type="taba",
            source_name="test taba",
            source_date="2025-06-01",
        )

        audit_entries = logger.to_audit_entries()
        assert len(audit_entries) == 4
        assert all(isinstance(e, AuditEntry) for e in audit_entries)

        # Calculation entry
        calc = audit_entries[0]
        assert calc.tool_name == "calculate_dmei_heter"
        assert calc.inputs == {"area": 100}
        assert calc.rates_used == {"rate": 0.91}
        assert calc.source_reference == "ref"

        # Classification entry
        cls_entry = audit_entries[1]
        assert cls_entry.tool_name == "building_classification"
        assert cls_entry.reasoning == "reason"

        # Override entry
        ovr = audit_entries[2]
        assert ovr.tool_name == "user_override"
        assert ovr.user_overrides["building_1_type"]["original"] == "service"

        # Data source entry
        ds = audit_entries[3]
        assert ds.tool_name == "data_source_scan"
        assert ds.source_reference == "test taba"

    def test_get_entries_by_type(self) -> None:
        """Filter entries by type works correctly."""
        logger = AuditLogger()
        logger.log_calculation(
            tool_name="calc",
            inputs={},
            formula="f",
            rates_used={},
            result={},
        )
        logger.log_classification(
            building_id=1,
            building_name="b",
            classification="residential",
            reasoning="r",
        )
        logger.log_classification(
            building_id=2,
            building_name="b2",
            classification="service",
            reasoning="r2",
        )

        calcs = logger.get_entries_by_type("calculation")
        assert len(calcs) == 1
        assert calcs[0]["tool_name"] == "calc"

        classifications = logger.get_entries_by_type("classification")
        assert len(classifications) == 2

        overrides = logger.get_entries_by_type("user_override")
        assert len(overrides) == 0

    def test_clear(self) -> None:
        """Clear resets all entries and the ID counter."""
        logger = self._make_logger_with_calculation()
        assert logger.entry_count == 1

        logger.clear()
        assert logger.entry_count == 0
        assert logger.entries == []

        # New entries should start at ID 1 again
        logger.log_data_source("taba", "new", None)
        assert logger.entries[0]["entry_id"] == 1

    def test_empty_summary(self) -> None:
        """Summary on empty logger returns zeroes."""
        logger = AuditLogger()
        summary = logger.generate_summary()
        assert summary["total_entries"] == 0
        assert summary["calculations"] == 0
        assert summary["timestamp_range"]["first"] is None
        assert summary["timestamp_range"]["last"] is None
