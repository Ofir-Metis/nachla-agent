"""Tests for agent workflow, system prompt, and orchestration logic.

Tests cover:
- Workflow phase transitions and ordering
- Checkpoint blocking without confirmation
- Checkpoint allowing with confirmation
- Monday.com status mapping
- Sanity checks (step 13)
- System prompt completeness
- Tool registration
- Audit log integration
"""

from __future__ import annotations

import pytest

from agent.audit_log import AuditLogger
from agent.system_prompt import build_system_prompt
from agent.workflow import (
    _MONDAY_STATUS_MAP,
    _PHASE_ORDER,
    WorkflowError,
    WorkflowPhase,
    WorkflowState,
    run_sanity_checks,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def workflow() -> WorkflowState:
    """Create a fresh WorkflowState."""
    return WorkflowState()


@pytest.fixture()
def workflow_at_checkpoint() -> WorkflowState:
    """Create a WorkflowState advanced to the checkpoint phase."""
    ws = WorkflowState()
    ws.advance(WorkflowPhase.INTAKE)
    ws.complete_current_phase()
    ws.advance(WorkflowPhase.TABA_ANALYSIS)
    ws.complete_current_phase()
    ws.advance(WorkflowPhase.BUILDING_MAPPING)
    ws.complete_current_phase()
    ws.advance(WorkflowPhase.CLASSIFICATION)
    ws.complete_current_phase()
    ws.advance(WorkflowPhase.CHECKPOINT)
    return ws


@pytest.fixture()
def system_prompt_default() -> str:
    """Build the default system prompt (no priority area)."""
    return build_system_prompt()


# ---------------------------------------------------------------------------
# Workflow Phase Transitions
# ---------------------------------------------------------------------------


class TestWorkflowPhaseTransitions:
    """Test that phase transitions follow the correct order."""

    def test_initial_phase_is_intake(self, workflow: WorkflowState) -> None:
        assert workflow.current_phase == WorkflowPhase.INTAKE

    def test_advance_to_next_phase(self, workflow: WorkflowState) -> None:
        workflow.advance(WorkflowPhase.INTAKE)
        assert workflow.current_phase == WorkflowPhase.INTAKE
        workflow.complete_current_phase()
        workflow.advance(WorkflowPhase.TABA_ANALYSIS)
        assert workflow.current_phase == WorkflowPhase.TABA_ANALYSIS

    def test_cannot_go_backwards(self, workflow: WorkflowState) -> None:
        workflow.advance(WorkflowPhase.INTAKE)
        workflow.complete_current_phase()
        workflow.advance(WorkflowPhase.TABA_ANALYSIS)
        workflow.complete_current_phase()
        with pytest.raises(WorkflowError):
            workflow.advance(WorkflowPhase.INTAKE)

    def test_complete_marks_phase(self, workflow: WorkflowState) -> None:
        workflow.complete_current_phase()
        assert WorkflowPhase.INTAKE in workflow.completed_phases

    def test_full_happy_path(self) -> None:
        """Walk through the entire workflow with confirmation."""
        ws = WorkflowState()
        # Intake through classification
        for phase in [
            WorkflowPhase.INTAKE,
            WorkflowPhase.TABA_ANALYSIS,
            WorkflowPhase.BUILDING_MAPPING,
            WorkflowPhase.CLASSIFICATION,
        ]:
            ws.advance(phase)
            ws.complete_current_phase()

        # Checkpoint
        ws.advance(WorkflowPhase.CHECKPOINT)
        ws.confirm_classifications()
        ws.complete_current_phase()

        # Post-checkpoint phases
        for phase in [
            WorkflowPhase.USAGE_FEES,
            WorkflowPhase.SQM_EQUIVALENT,
            WorkflowPhase.HIVUN,
            WorkflowPhase.REGULARIZATION,
        ]:
            ws.advance(phase)
            ws.complete_current_phase()

        # Skip optional phases
        ws.skip_phase(WorkflowPhase.SPLIT)
        ws.skip_phase(WorkflowPhase.AGRICULTURAL)

        ws.advance(WorkflowPhase.BETTERMENT)
        ws.complete_current_phase()
        ws.advance(WorkflowPhase.REPORT)
        ws.complete_current_phase()
        ws.advance(WorkflowPhase.REVIEW)
        ws.complete_current_phase()
        ws.advance(WorkflowPhase.EXPORT)
        ws.complete_current_phase()
        ws.advance(WorkflowPhase.COMPLETE)

        assert ws.current_phase == WorkflowPhase.COMPLETE
        assert ws.classifications_confirmed is True

    def test_phase_order_is_complete(self) -> None:
        """Verify all WorkflowPhase members appear in _PHASE_ORDER."""
        all_phases = set(WorkflowPhase)
        ordered_phases = set(_PHASE_ORDER)
        assert all_phases == ordered_phases, f"Missing from _PHASE_ORDER: {all_phases - ordered_phases}"


# ---------------------------------------------------------------------------
# Checkpoint Blocking
# ---------------------------------------------------------------------------


class TestCheckpointBlocking:
    """Test that the checkpoint blocks without user confirmation."""

    def test_checkpoint_blocks_without_confirmation(self, workflow_at_checkpoint: WorkflowState) -> None:
        """Cannot advance past checkpoint without confirmation."""
        ws = workflow_at_checkpoint
        assert ws.current_phase == WorkflowPhase.CHECKPOINT
        assert ws.classifications_confirmed is False

        # Try to advance to usage fees -- should fail
        ws.complete_current_phase()
        with pytest.raises(WorkflowError, match="classifications have not been confirmed"):
            ws.advance(WorkflowPhase.USAGE_FEES)

    def test_checkpoint_allows_with_confirmation(self, workflow_at_checkpoint: WorkflowState) -> None:
        """Can advance past checkpoint after user confirmation."""
        ws = workflow_at_checkpoint
        ws.confirm_classifications()
        ws.complete_current_phase()
        ws.advance(WorkflowPhase.USAGE_FEES)
        assert ws.current_phase == WorkflowPhase.USAGE_FEES

    def test_can_proceed_to_returns_false_without_confirmation(self, workflow_at_checkpoint: WorkflowState) -> None:
        ws = workflow_at_checkpoint
        ws.complete_current_phase()
        assert ws.can_proceed_to(WorkflowPhase.USAGE_FEES) is False

    def test_can_proceed_to_returns_true_with_confirmation(self, workflow_at_checkpoint: WorkflowState) -> None:
        ws = workflow_at_checkpoint
        ws.confirm_classifications()
        ws.complete_current_phase()
        assert ws.can_proceed_to(WorkflowPhase.USAGE_FEES) is True

    def test_late_phases_blocked_without_confirmation(self) -> None:
        """Even phases far past the checkpoint are blocked."""
        ws = WorkflowState()
        ws.classifications_confirmed = False
        # Directly check -- REPORT is well past the checkpoint
        assert ws.can_proceed_to(WorkflowPhase.REPORT) is False


# ---------------------------------------------------------------------------
# Monday.com Status Mapping
# ---------------------------------------------------------------------------


class TestMondayStatusMapping:
    """Test that each phase maps to a valid Monday.com status."""

    def test_all_phases_have_status(self) -> None:
        for phase in WorkflowPhase:
            assert phase in _MONDAY_STATUS_MAP, f"Phase {phase} missing from Monday status map"

    def test_intake_status(self) -> None:
        ws = WorkflowState(current_phase=WorkflowPhase.INTAKE)
        assert ws.get_monday_status() == "בבדיקה"

    def test_report_status(self) -> None:
        ws = WorkflowState(current_phase=WorkflowPhase.REPORT)
        assert ws.get_monday_status() == "טיוטה מוכנה"

    def test_review_status(self) -> None:
        ws = WorkflowState(current_phase=WorkflowPhase.REVIEW)
        assert ws.get_monday_status() == "בבקרה"

    def test_export_status(self) -> None:
        ws = WorkflowState(current_phase=WorkflowPhase.EXPORT)
        assert ws.get_monday_status() == "מאושר"

    def test_monday_update_template(self) -> None:
        ws = WorkflowState(current_phase=WorkflowPhase.BUILDING_MAPPING)
        msg = ws.get_monday_update(building_count="5")
        assert "5" in msg
        assert "מבנים" in msg


# ---------------------------------------------------------------------------
# Sanity Checks (Step 13)
# ---------------------------------------------------------------------------


class TestSanityChecks:
    """Test the step 13 sanity checks."""

    def test_classifications_confirmed_check_fails(self) -> None:
        ws = WorkflowState()
        ws.classifications_confirmed = False
        results = run_sanity_checks(ws)
        assert results["classifications_confirmed"]["passed"] is False

    def test_classifications_confirmed_check_passes(self) -> None:
        ws = WorkflowState()
        ws.classifications_confirmed = True
        results = run_sanity_checks(ws)
        assert results["classifications_confirmed"]["passed"] is True

    def test_sqm_equivalent_reasonable_check(self) -> None:
        ws = WorkflowState()
        ws.classifications_confirmed = True
        ws.calculation_results["sqm_equivalent"] = {"total_nachla_sqm": 1100}
        results = run_sanity_checks(ws)
        assert results["sqm_equivalent_reasonable"]["passed"] is True

    def test_sqm_equivalent_out_of_range(self) -> None:
        ws = WorkflowState()
        ws.classifications_confirmed = True
        ws.calculation_results["sqm_equivalent"] = {"total_nachla_sqm": 5000}
        results = run_sanity_checks(ws)
        assert results["sqm_equivalent_reasonable"]["passed"] is False

    def test_hivun_33_greater_than_375(self) -> None:
        ws = WorkflowState()
        ws.classifications_confirmed = True
        ws.calculation_results["hivun"] = {
            "hivun_375_cost": 280000,
            "hivun_33_cost": 3200000,
        }
        results = run_sanity_checks(ws)
        assert results["hivun_33_greater_than_375"]["passed"] is True

    def test_hivun_33_less_than_375_fails(self) -> None:
        ws = WorkflowState()
        ws.classifications_confirmed = True
        ws.calculation_results["hivun"] = {
            "hivun_375_cost": 3200000,
            "hivun_33_cost": 280000,
        }
        results = run_sanity_checks(ws)
        assert results["hivun_33_greater_than_375"]["passed"] is False

    def test_sanity_results_stored_in_state(self) -> None:
        ws = WorkflowState()
        ws.classifications_confirmed = True
        run_sanity_checks(ws)
        assert len(ws.sanity_check_results) > 0


# ---------------------------------------------------------------------------
# System Prompt Completeness
# ---------------------------------------------------------------------------


class TestSystemPrompt:
    """Test that the system prompt includes all required domain rules."""

    def test_prompt_includes_building_classification_table(self, system_prompt_default: str) -> None:
        assert "residential" in system_prompt_default.lower() or "בית מגורים" in system_prompt_default

    def test_prompt_includes_pergola_40_rule(self, system_prompt_default: str) -> None:
        assert "40%" in system_prompt_default

    def test_prompt_includes_basement_03_vs_07(self, system_prompt_default: str) -> None:
        assert "0.3" in system_prompt_default
        assert "0.7" in system_prompt_default

    def test_prompt_includes_pre_1965(self, system_prompt_default: str) -> None:
        assert "1965" in system_prompt_default

    def test_prompt_includes_usage_fee_exemptions(self, system_prompt_default: str) -> None:
        # First house exempt
        assert "בית ראשון" in system_prompt_default

    def test_prompt_includes_usage_fee_rates(self, system_prompt_default: str) -> None:
        assert "5%" in system_prompt_default
        assert "3%" in system_prompt_default
        assert "2%" in system_prompt_default

    def test_prompt_includes_permit_fee_rate(self, system_prompt_default: str) -> None:
        assert "91%" in system_prompt_default

    def test_prompt_includes_hivun_808(self, system_prompt_default: str) -> None:
        assert "808" in system_prompt_default

    def test_prompt_includes_post_2009_rule(self, system_prompt_default: str) -> None:
        assert "2009" in system_prompt_default

    def test_prompt_includes_bar_reshut_split_warning(self, system_prompt_default: str) -> None:
        assert "בר רשות" in system_prompt_default or "bar reshut" in system_prompt_default.lower()

    def test_prompt_includes_checkpoint_instruction(self, system_prompt_default: str) -> None:
        assert "checkpoint" in system_prompt_default.lower()
        assert "confirm" in system_prompt_default.lower()

    def test_prompt_includes_never_do_math(self, system_prompt_default: str) -> None:
        assert "NEVER perform arithmetic" in system_prompt_default

    def test_prompt_includes_audit_log_requirement(self, system_prompt_default: str) -> None:
        assert "audit" in system_prompt_default.lower()

    def test_prompt_includes_disclaimers(self, system_prompt_default: str) -> None:
        assert "הסתייגויות" in system_prompt_default or "disclaimers" in system_prompt_default.lower()

    def test_prompt_includes_priority_area_table(self, system_prompt_default: str) -> None:
        assert "עדיפות א'" in system_prompt_default or "Priority Area A" in system_prompt_default

    def test_prompt_includes_report_structure(self, system_prompt_default: str) -> None:
        assert "מבנה הדוח" in system_prompt_default or "Report Structure" in system_prompt_default

    def test_prompt_includes_decision_1523(self, system_prompt_default: str) -> None:
        assert "1523" in system_prompt_default

    def test_prompt_with_priority_area_a(self) -> None:
        prompt = build_system_prompt(priority_area="A")
        assert "Priority Area A" in prompt or "עדיפות א'" in prompt
        assert "51%" in prompt

    def test_prompt_with_priority_area_b(self) -> None:
        prompt = build_system_prompt(priority_area="B")
        assert "25%" in prompt

    def test_prompt_with_frontline(self) -> None:
        prompt = build_system_prompt(priority_area="frontline")
        assert "31%" in prompt or "Frontline" in prompt

    def test_prompt_with_no_priority(self) -> None:
        prompt = build_system_prompt(priority_area=None)
        assert "Standard rates" in prompt or "standard" in prompt.lower()

    def test_prompt_includes_all_calculation_tools(self, system_prompt_default: str) -> None:
        tool_names = [
            "calculate_dmei_heter",
            "calculate_dmei_shimush",
            "calculate_hivun_375",
            "calculate_hivun_33",
            "check_split_eligibility",
            "calculate_split_cost",
            "calculate_sqm_equivalent",
            "calculate_betterment_levy",
        ]
        for name in tool_names:
            assert name in system_prompt_default, f"Tool {name} missing from system prompt"

    def test_prompt_includes_building_status_types(self, system_prompt_default: str) -> None:
        statuses = ["תקין", "חריגה מהיתר", "ללא היתר", "סומן להריסה", "חורג מקווי בניין"]
        for status in statuses:
            assert status in system_prompt_default, f"Status '{status}' missing from prompt"

    def test_prompt_includes_mamad_12_sqm(self, system_prompt_default: str) -> None:
        assert "12" in system_prompt_default
        assert 'ממ"ד' in system_prompt_default

    def test_prompt_includes_split_350_sqm(self, system_prompt_default: str) -> None:
        assert "350" in system_prompt_default

    def test_prompt_includes_usage_fee_7_years(self, system_prompt_default: str) -> None:
        assert "7 שנים" in system_prompt_default

    def test_prompt_includes_usage_fee_2_years(self, system_prompt_default: str) -> None:
        assert "2 שנים" in system_prompt_default


# ---------------------------------------------------------------------------
# Tool Registration
# ---------------------------------------------------------------------------


class TestToolRegistration:
    """Test tool registration on the NachlaAgent."""

    def test_agent_creates_without_error(self) -> None:
        """Agent initializes without raising."""
        from agent.main_agent import NachlaAgent
        from config.settings import AppSettings

        settings = AppSettings()
        agent = NachlaAgent(settings=settings)
        assert agent is not None

    def test_tools_registered(self) -> None:
        """Registered tools dict is populated (may be empty if calc modules not importable)."""
        from agent.main_agent import NachlaAgent
        from config.settings import AppSettings

        settings = AppSettings()
        agent = NachlaAgent(settings=settings)
        # tools may be empty if calc imports fail, but should not raise
        assert isinstance(agent.tools, dict)

    def test_tool_descriptor_has_schema(self) -> None:
        from agent.main_agent import ToolDescriptor

        def sample_tool(area_sqm: float, name: str = "test") -> dict:
            return {"value": area_sqm}

        td = ToolDescriptor(
            name="sample",
            description="A sample tool",
            func=sample_tool,
        )
        assert td.parameter_schema["type"] == "object"
        props = td.parameter_schema["properties"]
        assert "area_sqm" in props
        assert props["area_sqm"]["type"] == "number"
        assert "name" in props
        assert props["name"]["type"] == "string"
        assert props["name"]["default"] == "test"

    def test_get_tool_schemas(self) -> None:
        from agent.main_agent import NachlaAgent
        from config.settings import AppSettings

        settings = AppSettings()
        agent = NachlaAgent(settings=settings)
        schemas = agent.get_tool_schemas()
        assert isinstance(schemas, list)
        for schema in schemas:
            assert "name" in schema
            assert "description" in schema
            assert "input_schema" in schema


# ---------------------------------------------------------------------------
# Audit Log Integration
# ---------------------------------------------------------------------------


class TestAuditLogIntegration:
    """Test that the agent properly integrates with the audit logger."""

    def test_agent_has_audit_logger(self) -> None:
        from agent.main_agent import NachlaAgent
        from config.settings import AppSettings

        agent = NachlaAgent(settings=AppSettings())
        assert isinstance(agent.audit_logger, AuditLogger)
        assert agent.audit_logger.entry_count == 0

    def test_post_tool_hook_logs(self) -> None:
        from agent.main_agent import PostToolUseHook

        audit = AuditLogger()
        hook = PostToolUseHook(audit)
        hook(
            tool_name="calculate_dmei_heter",
            inputs={"area_sqm": 100, "area_type": "main"},
            result={
                "cost_ils": 50000,
                "formula": "100 x 1.0 x 550 x 0.91 x 1.18",
                "rates_used": {"permit_rate": 0.91, "vat": 0.18},
            },
        )
        assert audit.entry_count == 1
        entries = audit.get_entries_by_type("calculation")
        assert len(entries) == 1
        assert entries[0]["tool_name"] == "calculate_dmei_heter"

    def test_stop_hook_detects_missing_report(self) -> None:
        from agent.main_agent import StopHook

        ws = WorkflowState()
        hook = StopHook()
        result = hook(ws)
        assert result is not None
        assert "missing" in result
        assert any("Report" in m for m in result["missing"])

    def test_stop_hook_passes_when_complete(self) -> None:
        from agent.main_agent import StopHook

        ws = WorkflowState()
        ws.classifications_confirmed = True
        ws.report_data = {"dummy": True}
        ws.sanity_check_results = {"check1": {"passed": True}}
        hook = StopHook()
        result = hook(ws)
        assert result is None


# ---------------------------------------------------------------------------
# Workflow Progress Summary
# ---------------------------------------------------------------------------


class TestWorkflowProgress:
    """Test workflow progress reporting."""

    def test_progress_summary_initial(self, workflow: WorkflowState) -> None:
        summary = workflow.get_progress_summary()
        assert summary["current_phase"] == WorkflowPhase.INTAKE
        assert summary["completed_count"] == 0
        assert summary["classifications_confirmed"] is False

    def test_progress_summary_after_some_phases(self, workflow_at_checkpoint: WorkflowState) -> None:
        ws = workflow_at_checkpoint
        summary = ws.get_progress_summary()
        assert summary["completed_count"] >= 4
        assert summary["progress_percent"] > 0

    def test_skip_phase_only_skippable(self, workflow: WorkflowState) -> None:
        workflow.skip_phase(WorkflowPhase.SPLIT)
        assert WorkflowPhase.SPLIT in workflow.completed_phases

    def test_skip_non_skippable_raises(self, workflow: WorkflowState) -> None:
        with pytest.raises(WorkflowError):
            workflow.skip_phase(WorkflowPhase.INTAKE)


# ---------------------------------------------------------------------------
# Settings Agent Fields
# ---------------------------------------------------------------------------


class TestSettingsAgentFields:
    """Test that agent-specific settings are present."""

    def test_agent_model_settings(self) -> None:
        from config.settings import AppSettings

        s = AppSettings()
        assert s.anthropic_model_main == "claude-sonnet-4-6"
        assert s.anthropic_model_complex == "claude-opus-4-6"
        assert s.mcp_config_path == ".mcp.json"
        assert s.max_report_generation_time == 300
        assert s.max_tool_retries == 3
        assert s.checkpoint_timeout == 0
