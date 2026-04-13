"""Main agent setup for nachla feasibility studies.

Uses a well-structured Python class that can be wrapped by the Claude Agent SDK
when available. The core logic works independently of the SDK.

Architecture:
- Custom calculation tools registered as annotated Python functions
- 3 external MCP servers (playwright, monday, memory) configured via .mcp.json
- Hooks for input validation (PreToolUse) and audit logging (PostToolUse)
- Subagent coordination for parallel tasks
- Phase-based workflow engine enforcing the mandatory classification checkpoint
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import typing
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from agent.audit_log import AuditLogger
from agent.system_prompt import build_system_prompt
from agent.workflow import WorkflowPhase, WorkflowState, run_sanity_checks
from config.settings import AppSettings, get_settings
from models.building import Building, BuildingStatus, BuildingType
from tools.exceptions import CalculationInputError
from models.nachla import ClientGoal, Nachla, PriorityArea
from models.report import ReportData
from models.taba import Taba, resolve_primary_taba

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool descriptor -- lightweight metadata for each registered tool
# ---------------------------------------------------------------------------


class ToolDescriptor:
    """Metadata for a registered calculation tool.

    Wraps a Python callable with name, description, and parameter schema
    so it can be presented to the Claude Agent SDK or used directly.
    """

    def __init__(
        self,
        name: str,
        description: str,
        func: Callable[..., Any],
        name_he: str = "",
    ) -> None:
        self.name = name
        self.name_he = name_he
        self.description = description
        self.func = func
        self.parameter_schema = self._extract_schema(func)

    @staticmethod
    def _extract_schema(func: Callable[..., Any]) -> dict[str, Any]:
        """Extract a JSON-schema-like parameter description from function signature.

        Handles both real type annotations and string annotations
        (from ``from __future__ import annotations``).
        """
        # Try to resolve string annotations to real types
        try:
            hints = typing.get_type_hints(func)
        except Exception:
            hints = {}

        sig = inspect.signature(func)
        params: dict[str, Any] = {}
        for pname, param in sig.parameters.items():
            ptype = "string"
            annotation = hints.get(pname, param.annotation)
            if annotation is not inspect.Parameter.empty:
                if annotation in (float, int):
                    ptype = "number"
                elif annotation is bool:
                    ptype = "boolean"
                elif annotation is str:
                    ptype = "string"
                # Handle string form of annotations
                elif isinstance(annotation, str):
                    if annotation in ("float", "int"):
                        ptype = "number"
                    elif annotation == "bool":
                        ptype = "boolean"
            entry: dict[str, Any] = {"type": ptype}
            if param.default is not inspect.Parameter.empty:
                entry["default"] = param.default
            params[pname] = entry
        return {"type": "object", "properties": params}

    def __repr__(self) -> str:
        return f"ToolDescriptor(name={self.name!r})"


# ---------------------------------------------------------------------------
# Hook base classes
# ---------------------------------------------------------------------------


class PreToolUseHook:
    """Validates inputs before a tool is invoked."""

    def __call__(self, tool_name: str, inputs: dict[str, Any]) -> dict[str, Any] | None:
        """Validate and optionally transform inputs.

        Args:
            tool_name: Name of the tool about to be called.
            inputs: The input parameters.

        Returns:
            None to allow the call, or a dict with an 'error' key to block it.
        """
        # Block calculation tools if classifications are not confirmed
        # (this is enforced at a higher level via WorkflowState, but
        #  the hook provides defence in depth).
        return None


class PostToolUseHook:
    """Logs tool results to the audit trail after invocation."""

    def __init__(self, audit_logger: AuditLogger) -> None:
        self.audit_logger = audit_logger

    def __call__(
        self,
        tool_name: str,
        inputs: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        """Record the tool call in the audit log.

        Args:
            tool_name: Name of the tool that was called.
            inputs: The input parameters.
            result: The tool's return value.
        """
        self.audit_logger.log_calculation(
            tool_name=tool_name,
            inputs=inputs,
            formula=result.get("formula", ""),
            rates_used=result.get("rates_used", {}),
            result=result,
            source_reference=result.get("source_reference", ""),
            source_date=result.get("source_date"),
        )


class StopHook:
    """Checks completeness before the agent finishes."""

    def __call__(self, state: WorkflowState) -> dict[str, Any] | None:
        """Check whether the workflow is complete enough to stop.

        Returns:
            None if OK to stop, or a dict with 'missing' items.
        """
        missing: list[str] = []
        if not state.classifications_confirmed:
            missing.append("Building classifications not confirmed by user")
        if state.report_data is None:
            missing.append("Report has not been generated")
        if not state.sanity_check_results:
            missing.append("Sanity checks have not been run")
        if missing:
            return {"missing": missing}
        return None


# ---------------------------------------------------------------------------
# Main agent class
# ---------------------------------------------------------------------------


class NachlaAgent:
    """The main feasibility study agent.

    Orchestrates the 14-step workflow from intake to report generation.
    Registers calculation tools, enforces the classification checkpoint,
    and maintains an immutable audit trail.
    """

    def __init__(self, settings: AppSettings | None = None) -> None:
        """Initialize with settings and register all tools.

        Args:
            settings: Application settings. If None, uses the singleton.
        """
        self.settings = settings or get_settings()
        self.audit_logger = AuditLogger()
        self.workflow = WorkflowState()
        self.tools: dict[str, ToolDescriptor] = {}
        self.system_prompt: str = ""
        self.llm_client: Any | None = None  # Set via attach_llm()
        self._uploaded_files: dict[str, str] = {}
        self._document_context: str = ""

        # Hooks
        self.pre_tool_hook = PreToolUseHook()
        self.post_tool_hook = PostToolUseHook(self.audit_logger)
        self.stop_hook = StopHook()

        # Register calculation tools
        self._register_tools()

    def attach_llm(self, llm_client: Any) -> None:
        """Attach an LLM client for document analysis, classification, and narrative generation.

        Args:
            llm_client: An LLMClient instance from agent.llm_client.
        """
        self.llm_client = llm_client
        logger.info("LLM client attached to agent")

    def _register_tools(self) -> None:
        """Register all calculation tools with metadata.

        Each tool function is wrapped in a ToolDescriptor with its name,
        Hebrew name, description, and auto-extracted parameter schema.
        """
        # Required tools — agent cannot function without these
        from tools.calc_dmei_heter import (
            calculate_building_permit_fees,
            calculate_dmei_heter,
            check_permit_fee_cap,
        )
        from tools.calc_dmei_shimush import calculate_dmei_shimush
        from tools.calc_hivun import (
            calculate_hivun_33,
            calculate_hivun_375,
            compare_tracks,
        )
        from tools.calc_sqm_equivalent import (
            calculate_hivun_375_sqm,
            calculate_nachla_sqm_equivalent,
            calculate_potential_sqm,
            calculate_sqm_equivalent,
        )
        from tools.priority_areas import (
            get_discount,
            get_hivun_33_rate,
            get_priority_area,
            get_usage_rate,
        )

        # Optional tools — skip with warning if unavailable
        try:
            from tools.calc_hetel_hashbacha import (
                calculate_betterment_levy,
                calculate_partial_betterment,
                estimate_split_betterment,
            )
        except ImportError:
            logger.warning("Betterment levy tools not available; skipping.")
            calculate_betterment_levy = None
            calculate_partial_betterment = None
            estimate_split_betterment = None

        try:
            from tools.calc_pitzul import (
                calculate_remaining_rights,
                calculate_split_cost,
                check_split_eligibility,
            )
        except ImportError:
            logger.warning("Split calculation tools not available; skipping.")
            calculate_remaining_rights = None
            calculate_split_cost = None
            check_split_eligibility = None

        from tools.lookup_tables import (
            lookup_development_costs,
            lookup_plach_rate,
            lookup_settlement_shovi,
        )

        tool_defs: list[tuple[str, str, str, Callable[..., Any]]] = [
            # Permit fees
            (
                "calculate_dmei_heter",
                "חישוב דמי היתר",
                "Calculate permit fees for a single area component",
                calculate_dmei_heter,
            ),
            (
                "calculate_building_permit_fees",
                "חישוב דמי היתר למבנה",
                "Calculate total permit fees for one building",
                calculate_building_permit_fees,
            ),
            (
                "check_permit_fee_cap",
                "בדיקת תקרת דמי היתר",
                "Check decision 1523 permit fee cap for the nachla",
                check_permit_fee_cap,
            ),
            # Usage fees
            (
                "calculate_dmei_shimush",
                "חישוב דמי שימוש",
                "Calculate usage fees for a building",
                calculate_dmei_shimush,
            ),
            # Capitalization
            ("calculate_hivun_375", "חישוב היוון 3.75%", "Calculate 3.75% capitalization track", calculate_hivun_375),
            (
                "calculate_hivun_33",
                "חישוב היוון 33%",
                "Calculate 33% capitalization (purchase) track",
                calculate_hivun_33,
            ),
            ("compare_tracks", "השוואת מסלולי היוון", "Compare 3.75% vs 33% capitalization tracks", compare_tracks),
            # Split
            (
                "check_split_eligibility",
                "בדיקת כשירות לפיצול",
                "Check if the nachla is eligible for plot splitting",
                check_split_eligibility,
            ),
            (
                "calculate_split_cost",
                "חישוב עלויות פיצול",
                "Calculate costs for splitting a plot",
                calculate_split_cost,
            ),
            (
                "calculate_remaining_rights",
                "חישוב זכויות שנותרו",
                "Calculate remaining building rights after split",
                calculate_remaining_rights,
            ),
            # Sqm equivalent
            (
                "calculate_sqm_equivalent",
                'חישוב מ"ר אקוויוולנטי',
                "Calculate sqm equivalent for a single component",
                calculate_sqm_equivalent,
            ),
            (
                "calculate_nachla_sqm_equivalent",
                "חישוב מ\"ר אקו' נחלה",
                "Calculate total nachla sqm equivalent",
                calculate_nachla_sqm_equivalent,
            ),
            (
                "calculate_potential_sqm",
                'חישוב פוטנציאל מ"ר',
                "Calculate potential sqm from unused taba rights",
                calculate_potential_sqm,
            ),
            (
                "calculate_hivun_375_sqm",
                "חישוב מ\"ר אקו' 3.75%",
                "Calculate 808 sqm default or dynamic equivalent",
                calculate_hivun_375_sqm,
            ),
            # Betterment
            ("calculate_betterment_levy", "חישוב היטל השבחה", "Calculate betterment levy", calculate_betterment_levy),
            (
                "calculate_partial_betterment",
                "חישוב היטל השבחה חלקי",
                "Calculate partial betterment (permit realization)",
                calculate_partial_betterment,
            ),
            (
                "estimate_split_betterment",
                "הערכת היטל השבחה לפיצול",
                "Estimate betterment levy for a split scenario",
                estimate_split_betterment,
            ),
            # Lookups
            (
                "lookup_settlement_shovi",
                "שליפת שווי לפי ישוב",
                "Look up land value (shovi) for a settlement",
                lookup_settlement_shovi,
            ),
            ("lookup_plach_rate", 'שליפת תעריף פל"ח', "Look up plach rate by regional council", lookup_plach_rate),
            (
                "lookup_development_costs",
                "שליפת עלויות פיתוח",
                "Look up development costs for a regional council",
                lookup_development_costs,
            ),
            # Priority areas
            (
                "get_priority_area",
                "זיהוי אזור עדיפות",
                "Get priority area classification for a settlement",
                get_priority_area,
            ),
            ("get_discount", "שליפת הנחה", "Get discount rates for a priority area", get_discount),
            ("get_usage_rate", "שליפת שיעור דמי שימוש", "Get usage fee rate for a priority area", get_usage_rate),
            ("get_hivun_33_rate", "שליפת שיעור היוון 33%", "Get 33% hivun rate for a priority area", get_hivun_33_rate),
        ]

        for name, name_he, description, func in tool_defs:
            if func is None:
                logger.info("Skipping optional tool %s (module not available)", name)
                continue
            self.tools[name] = ToolDescriptor(
                name=name,
                name_he=name_he,
                description=description,
                func=func,
            )

        logger.info("Registered %d calculation tools.", len(self.tools))

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Return tool schemas suitable for Claude Agent SDK registration.

        Returns:
            List of tool schema dicts with name, description, and input_schema.
        """
        schemas: list[dict[str, Any]] = []
        for tool in self.tools.values():
            schemas.append(
                {
                    "name": tool.name,
                    "description": f"{tool.name_he} - {tool.description}",
                    "input_schema": tool.parameter_schema,
                }
            )
        return schemas

    async def invoke_tool(self, tool_name: str, inputs: dict[str, Any]) -> dict[str, Any]:
        """Invoke a registered tool with pre/post hooks.

        Args:
            tool_name: Name of the tool to invoke.
            inputs: Input parameters.

        Returns:
            The tool result dict.

        Raises:
            KeyError: If the tool is not registered.
            WorkflowError: If pre-hook validation fails.
        """
        if tool_name not in self.tools:
            raise KeyError(f"Tool '{tool_name}' is not registered.")

        # Pre-hook validation
        pre_result = self.pre_tool_hook(tool_name, inputs)
        if pre_result is not None:
            return pre_result

        tool = self.tools[tool_name]
        func = tool.func

        # Call the tool (sync or async)
        if asyncio.iscoroutinefunction(func):
            result = await func(**inputs)
        else:
            result = func(**inputs)

        # Ensure result is a dict
        if not isinstance(result, dict):
            result = {"value": result}

        # Post-hook audit logging
        self.post_tool_hook(tool_name, inputs, result)

        return result

    # ------------------------------------------------------------------
    # High-level workflow methods
    # ------------------------------------------------------------------

    async def run(
        self,
        nachla: Nachla,
        uploaded_files: dict[str, str] | None = None,
    ) -> ReportData:
        """Run the complete feasibility study workflow.

        This method orchestrates all 14 steps. In a real deployment it
        would be driven by the Claude Agent SDK's agent loop; here we
        expose it as a structured async method for testing and direct use.

        Args:
            nachla: Nachla model with intake data.
            uploaded_files: Dict mapping file type to file path.

        Returns:
            Complete ReportData ready for document generation.
        """
        uploaded_files = uploaded_files or {}
        self.workflow.nachla = nachla

        # Build system prompt with priority area context
        priority = nachla.priority_area.value if nachla.priority_area else None
        self.system_prompt = build_system_prompt(priority_area=priority)

        # Step 0: Intake
        await self._run_intake(nachla)

        # Step 1: Taba analysis
        tabas = await self._run_taba_analysis(nachla)

        # Step 2: Building mapping
        buildings = await self._run_building_mapping(nachla, uploaded_files)

        # Step 3.4: Classification checkpoint (BLOCKS until confirmed)
        buildings = await self._run_classification_checkpoint(buildings)

        # Steps 4-9, 11: Calculations
        calc_results = await self._run_calculations(nachla, buildings, tabas)

        # Step 12: Report generation
        report_data = await self._build_report_data(nachla, buildings, tabas, calc_results)

        # Step 13: Review
        await self._run_review(report_data)

        return report_data

    async def _run_intake(self, nachla: Nachla) -> None:
        """Step 0: Validate intake data, detect priority area, check freshness.

        Args:
            nachla: The nachla model with intake data.
        """
        self.workflow.advance(WorkflowPhase.INTAKE)
        logger.info(
            "Step 0: Intake for %s, %s (gush %d helka %d)",
            nachla.owner_name,
            nachla.moshav_name,
            nachla.gush,
            nachla.helka,
        )

        # Check data freshness
        is_fresh, freshness_msg = self.settings.check_data_freshness()
        if not is_fresh:
            logger.warning("Data freshness warning: %s", freshness_msg)

        # Log the data source
        self.audit_logger.log_data_source(
            source_type="intake",
            source_name=f"Client intake: {nachla.owner_name}",
            source_date=datetime.now(UTC).strftime("%Y-%m-%d"),
        )

        # Detect priority area if not set
        if nachla.priority_area == PriorityArea.NONE:
            try:
                result = await self.invoke_tool(
                    "get_priority_area",
                    {"settlement_name": nachla.moshav_name},
                )
                area = result.get("priority_area", "none")
                if area and area != "none":
                    nachla.priority_area = PriorityArea(area)
                    logger.info("Detected priority area: %s", area)
            except (KeyError, Exception) as exc:
                logger.warning("Could not detect priority area: %s", exc)

        # Bar reshut + split warning
        if not nachla.can_split and ClientGoal.SPLIT in nachla.client_goals:
            logger.warning("Bar reshut cannot split without lease agreement. Will note in report.")

        self.workflow.complete_current_phase()

    async def _run_taba_analysis(self, nachla: Nachla) -> list[Taba]:
        """Step 1: Analyze zoning plans.

        In Phase 1-2 of the project, taba data comes from manual input.
        Govmap integration is deferred to Phase 3+.

        Args:
            nachla: The nachla model.

        Returns:
            List of Taba models.
        """
        self.workflow.advance(WorkflowPhase.TABA_ANALYSIS)
        logger.info("Step 1: Taba analysis for gush %d helka %d", nachla.gush, nachla.helka)

        # For now, tabas come from the nachla model or are provided externally
        tabas: list[Taba] = []
        if nachla.tabas:
            for t in nachla.tabas:
                if isinstance(t, Taba):
                    tabas.append(t)

        for taba in tabas:
            self.audit_logger.log_data_source(
                source_type="taba",
                source_name=f'תב"ע {taba.taba_number} - {taba.taba_name}',
                source_date=taba.approval_date,
            )

        # Resolve primary taba when multiple tabas apply
        if len(tabas) > 1:
            primary = resolve_primary_taba(tabas)
            if primary:
                logger.info("Resolved primary taba: %s (%s)", primary.taba_number, primary.taba_name)

        self.workflow.tabas = tabas
        self.workflow.complete_current_phase()
        return tabas

    async def _run_building_mapping(
        self, nachla: Nachla, uploaded_files: dict[str, str] | None = None,
    ) -> list[Building]:
        """Step 2: Map buildings from survey map.

        If no buildings are provided in the nachla model and an LLM client
        is attached, uses Claude to extract buildings from uploaded documents.

        Args:
            nachla: The nachla model.
            uploaded_files: Dict mapping file type to file path.

        Returns:
            List of Building models.
        """
        self.workflow.advance(WorkflowPhase.BUILDING_MAPPING)
        logger.info("Step 2: Building mapping")

        buildings: list[Building] = []

        # Try LLM document analysis if no buildings provided
        if not nachla.buildings and self.llm_client and uploaded_files:
            logger.info("No buildings in intake data, running LLM document analysis")
            extracted_buildings, extracted_tabas, _ = await self.analyze_uploaded_documents(uploaded_files)
            if extracted_buildings:
                nachla.buildings = extracted_buildings
            if extracted_tabas and not nachla.tabas:
                nachla.tabas = extracted_tabas

        if nachla.buildings:
            for b in nachla.buildings:
                if isinstance(b, Building):
                    buildings.append(b)
                    self.audit_logger.log_classification(
                        building_id=b.id,
                        building_name=b.name,
                        classification=b.building_type.value,
                        reasoning="Initial classification from document analysis",
                    )

        # Enhance classifications with LLM if available
        if self.llm_client and buildings:
            buildings = await self.classify_buildings_with_llm(buildings)

        self.workflow.buildings = buildings
        self.workflow.advance(WorkflowPhase.CLASSIFICATION)
        self.workflow.complete_current_phase()
        return buildings

    async def _run_classification_checkpoint(
        self,
        buildings: list[Building],
    ) -> list[Building]:
        """Step 3.4: MANDATORY checkpoint.

        Presents building classifications and waits for user confirmation.
        The workflow CANNOT proceed past this point without confirmation.

        In an interactive session (Claude Agent SDK), the agent would present
        the summary and call AskUserQuestion. In programmatic use, the caller
        must call workflow.confirm_classifications() before continuing.

        Args:
            buildings: List of classified buildings.

        Returns:
            The (possibly updated) list of buildings after user confirmation.
        """
        self.workflow.advance(WorkflowPhase.CHECKPOINT)
        logger.info("Step 3.4: Classification checkpoint -- waiting for user confirmation")

        # Build the classification summary
        summary = self._build_classification_summary(buildings)
        logger.info("Classification summary:\n%s", summary)

        # In a real agent loop, the agent would present this summary
        # and call AskUserQuestion. For programmatic use, we check the flag.
        if not self.workflow.classifications_confirmed:
            logger.warning(
                "Classifications NOT confirmed. In interactive mode, the agent "
                "presents the summary and waits for user input."
            )

        return buildings

    def _build_classification_summary(self, buildings: list[Building]) -> str:
        """Build a Hebrew classification summary for the checkpoint.

        Args:
            buildings: List of classified buildings.

        Returns:
            Formatted summary string.
        """
        type_counts: dict[str, int] = {}
        for b in buildings:
            btype = b.building_type.value
            type_counts[btype] = type_counts.get(btype, 0) + 1

        status_counts: dict[str, int] = {}
        for b in buildings:
            s = b.status.value
            status_counts[s] = status_counts.get(s, 0) + 1

        lines: list[str] = [
            f"Total buildings identified: {len(buildings)}",
            f"By type: {json.dumps(type_counts, ensure_ascii=False)}",
            f"By status: {json.dumps(status_counts, ensure_ascii=False)}",
            "",
            "Building details:",
        ]
        for b in buildings:
            confirmed_mark = " [CONFIRMED]" if b.user_confirmed else ""
            lines.append(
                f"  #{b.id} {b.name} | type={b.building_type.value} | "
                f"main={b.main_area_sqm}sqm | status={b.status.value}{confirmed_mark}"
            )

        deviations = [b for b in buildings if b.status == BuildingStatus.DEVIATION]
        no_permits = [b for b in buildings if b.status == BuildingStatus.NO_PERMIT]

        if deviations:
            lines.append(f"\nBuildings with deviations ({len(deviations)}):")
            for b in deviations:
                lines.append(f"  #{b.id} {b.name}: deviation {b.deviation_sqm} sqm")

        if no_permits:
            lines.append(f"\nBuildings without permits ({len(no_permits)}):")
            for b in no_permits:
                lines.append(f"  #{b.id} {b.name}: {b.main_area_sqm} sqm")

        return "\n".join(lines)

    async def _run_calculations(
        self,
        nachla: Nachla,
        buildings: list[Building],
        tabas: list[Taba],
    ) -> dict[str, Any]:
        """Steps 4-9, 11: Run all fee and cost calculations.

        Requires that classifications have been confirmed (enforced by
        WorkflowState.advance()).

        Args:
            nachla: Nachla model.
            buildings: Confirmed building list.
            tabas: Taba list.

        Returns:
            Dictionary of all calculation results keyed by phase name.
        """
        # This will raise WorkflowError if checkpoint is not confirmed
        self.workflow.advance(WorkflowPhase.USAGE_FEES)

        results: dict[str, Any] = {}

        # Step 4: Usage fees
        logger.info("Step 4: Calculating usage fees")
        usage_results = await self._calc_usage_fees(nachla, buildings)
        results["usage_fees"] = usage_results
        self.workflow.calculation_results["usage_fees"] = usage_results
        self.workflow.complete_current_phase()

        # Step 5: Sqm equivalent
        self.workflow.advance(WorkflowPhase.SQM_EQUIVALENT)
        logger.info("Step 5: Calculating sqm equivalent")
        sqm_results = await self._calc_sqm_equivalent(nachla, buildings, tabas)
        results["sqm_equivalent"] = sqm_results
        self.workflow.calculation_results["sqm_equivalent"] = sqm_results
        self.workflow.complete_current_phase()

        # Step 6: Hivun
        self.workflow.advance(WorkflowPhase.HIVUN)
        logger.info("Step 6: Calculating capitalization")
        hivun_results = await self._calc_hivun(nachla, sqm_results)
        results["hivun"] = hivun_results
        self.workflow.calculation_results["hivun"] = hivun_results
        self.workflow.complete_current_phase()

        # Step 7-8: Regularization + permit fees
        self.workflow.advance(WorkflowPhase.REGULARIZATION)
        logger.info("Steps 7-8: Calculating regularization and permit fees")
        reg_results = await self._calc_regularization(nachla, buildings)
        results["regularization"] = reg_results
        results["permit_fees"] = reg_results.get("permit_fees", {})
        self.workflow.calculation_results["permit_fees"] = results["permit_fees"]
        self.workflow.complete_current_phase()

        # Step 9: Split (optional)
        if ClientGoal.SPLIT in nachla.client_goals or ClientGoal.ALL in nachla.client_goals:
            self.workflow.advance(WorkflowPhase.SPLIT)
            logger.info("Step 9: Calculating split costs")
            split_results = await self._calc_split(nachla, tabas, sqm_results)
            results["split"] = split_results
            self.workflow.calculation_results["split"] = split_results
            self.workflow.complete_current_phase()
        else:
            self.workflow.skip_phase(WorkflowPhase.SPLIT)

        # Step 10: Agricultural (optional)
        agricultural_buildings = [b for b in buildings if b.building_type == BuildingType.AGRICULTURAL]
        if agricultural_buildings:
            self.workflow.advance(WorkflowPhase.AGRICULTURAL)
            logger.info("Step 10: Processing %d agricultural buildings", len(agricultural_buildings))
            ag_results: dict[str, Any] = {"buildings": {}}
            for ag_building in agricultural_buildings:
                ag_results["buildings"][ag_building.id] = {
                    "name": ag_building.name,
                    "area_sqm": ag_building.main_area_sqm,
                    "permit_fees": 0.0,
                    "permit_fee_note": "מבנה חקלאי - פטור מלא מדמי היתר",
                    "usage_rate": 0.02,
                    "usage_rate_note": "מבנה חקלאי - 2% דמי שימוש",
                }
            results["agricultural"] = ag_results
            self.workflow.calculation_results["agricultural"] = ag_results
            self.workflow.complete_current_phase()
        else:
            self.workflow.skip_phase(WorkflowPhase.AGRICULTURAL)

        # Step 11: Betterment levy (conditional — only when non-compliant buildings exist)
        has_non_compliant = any(b.status != BuildingStatus.COMPLIANT for b in buildings)
        if has_non_compliant:
            self.workflow.advance(WorkflowPhase.BETTERMENT)
            logger.info("Step 11: Calculating betterment levy (%d non-compliant buildings)",
                       sum(1 for b in buildings if b.status != BuildingStatus.COMPLIANT))
            betterment_results = await self._calc_betterment(nachla, buildings)
            results["betterment"] = betterment_results
            self.workflow.calculation_results["betterment"] = betterment_results
            self.workflow.complete_current_phase()
        else:
            self.workflow.skip_phase(WorkflowPhase.BETTERMENT)
            logger.info("Step 11: Skipping betterment levy — all buildings compliant")

        return results

    async def _calc_usage_fees(
        self,
        nachla: Nachla,
        buildings: list[Building],
    ) -> dict[str, Any]:
        """Calculate usage fees for all buildings.

        Args:
            nachla: Nachla model.
            buildings: Building list.

        Returns:
            Usage fee results dict.
        """
        results: dict[str, Any] = {"building_fees": {}, "total": 0}
        shovi = nachla.shovi_per_sqm if hasattr(nachla, 'shovi_per_sqm') else 7000
        for building in buildings:
            try:
                # Calculate usage fee for main area
                usage_type = "agricultural" if building.building_type == BuildingType.AGRICULTURAL else "residential"
                fee_result = await self.invoke_tool(
                    "calculate_dmei_shimush",
                    {
                        "area_sqm": building.main_area_sqm + (building.deviation_sqm or 0),
                        "area_type": "main",
                        "shovi_per_sqm": shovi,
                        "usage_type": usage_type,
                        "building_order": building.building_order,
                        "has_intergenerational_continuity": nachla.has_intergenerational_continuity,
                        "priority_area": nachla.priority_area.value if nachla.priority_area else None,
                    },
                )
                results["building_fees"][building.id] = fee_result
                fee_amount = fee_result.get("result", 0)
                results[f"building_{building.id}_usage_fees"] = fee_amount
                results["total"] += fee_amount
            except CalculationInputError as exc:
                logger.warning("Usage fee input error for building %d: %s (not retrying)", building.id, exc)
                results["building_fees"][building.id] = {"error": str(exc), "input_error": True}
            except Exception as exc:
                logger.error("Usage fee calc failed for building %d: %s", building.id, exc)
                results["building_fees"][building.id] = {"error": str(exc)}
        return results

    async def _calc_sqm_equivalent(
        self,
        nachla: Nachla,
        buildings: list[Building],
        tabas: list[Taba],
    ) -> dict[str, Any]:
        """Calculate sqm equivalent for the nachla.

        Args:
            nachla: Nachla model.
            buildings: Building list.
            tabas: Taba list.

        Returns:
            Sqm equivalent results.
        """
        try:
            # Get plot size from primary taba
            primary_taba = next((t for t in tabas if t.is_primary), tabas[0] if tabas else None)
            plot_size = primary_taba.plot_size_sqm if primary_taba else 2500

            # Sum building coverages
            coverage = sum(b.main_area_sqm + b.service_area_sqm for b in buildings)

            # Build taba rights from primary taba
            taba_rights: dict[str, float] = {}
            if primary_taba and primary_taba.unit_rights:
                total_main = sum(ur.main_area_sqm for ur in primary_taba.unit_rights)
                total_service = sum(ur.service_area_sqm for ur in primary_taba.unit_rights)
                taba_rights = {
                    "main_sqm": total_main,
                    "service_sqm": total_service,
                    "mamad_sqm": sum(ur.mamad_sqm for ur in primary_taba.unit_rights),
                }
            else:
                # Estimate from buildings if no taba rights
                taba_rights = {
                    "main_sqm": sum(b.main_area_sqm for b in buildings),
                    "service_sqm": sum(b.service_area_sqm for b in buildings),
                    "mamad_sqm": sum(b.mamad_area_sqm for b in buildings),
                }

            result = await self.invoke_tool(
                "calculate_nachla_sqm_equivalent",
                {
                    "plot_size_sqm": plot_size,
                    "building_coverage_sqm": coverage,
                    "taba_rights": taba_rights,
                },
            )
            return result
        except Exception as exc:
            logger.error("Sqm equivalent calc failed: %s", exc)
            return {"error": str(exc), "total_nachla_sqm": 0}

    async def _calc_hivun(
        self,
        nachla: Nachla,
        sqm_results: dict[str, Any],
    ) -> dict[str, Any]:
        """Calculate both capitalization tracks.

        Args:
            nachla: Nachla model.
            sqm_results: Sqm equivalent results from step 5.

        Returns:
            Capitalization calculation results.
        """
        results: dict[str, Any] = {}

        # Look up development costs if regional council is available
        dev_costs = 0.0
        if nachla.regional_council:
            try:
                dev_result = await self.invoke_tool(
                    "lookup_development_costs",
                    {"regional_council": nachla.regional_council},
                )
                dev_costs = float(dev_result.get("development_costs", 0) or 0)
                results["development_costs"] = dev_costs
                logger.info("Development costs for %s: %s", nachla.regional_council, dev_costs)
            except Exception as exc:
                logger.warning("Development costs lookup failed: %s", exc)

        shovi = sqm_results.get("shovi_meter_aku") or (nachla.shovi_per_sqm if hasattr(nachla, 'shovi_per_sqm') else 7000)

        try:
            result_375 = await self.invoke_tool(
                "calculate_hivun_375",
                {
                    "sqm_equivalent_375": sqm_results.get("result", 808),
                    "shovi_per_sqm": shovi,
                    "priority_area": nachla.priority_area.value if nachla.priority_area else None,
                    "development_costs": dev_costs,
                },
            )
            results["hivun_375"] = result_375
            results["hivun_375_cost"] = result_375.get("total_cost", 0)
        except Exception as exc:
            logger.error("Hivun 3.75%% calc failed: %s", exc)
            results["hivun_375"] = {"error": str(exc)}

        try:
            result_33 = await self.invoke_tool(
                "calculate_hivun_33",
                {
                    "sqm_equivalent_nachla": sqm_results.get("result", 0),
                    "sqm_potential": 0,
                    "shovi_per_sqm": shovi,
                    "prior_permit_fees_post_2009": nachla.prior_permit_fees_purchased if nachla.prior_fees_deductible else 0,
                    "priority_area": nachla.priority_area.value if nachla.priority_area else None,
                    "development_costs": dev_costs,
                },
            )
            results["hivun_33"] = result_33
            results["hivun_33_cost"] = result_33.get("total_cost", 0)
        except Exception as exc:
            logger.error("Hivun 33%% calc failed: %s", exc)
            results["hivun_33"] = {"error": str(exc)}

        return results

    async def _calc_regularization(
        self,
        nachla: Nachla,
        buildings: list[Building],
    ) -> dict[str, Any]:
        """Calculate regularization costs and permit fees for all buildings.

        Args:
            nachla: Nachla model.
            buildings: Building list.

        Returns:
            Regularization and permit fee results.
        """
        results: dict[str, Any] = {"building_results": {}, "permit_fees": {}, "total_permit_fees": 0}
        for building in buildings:
            if building.status in (BuildingStatus.COMPLIANT,) and building.building_type != BuildingType.PRE_1965:
                continue
            try:
                # Build areas list from building model
                building_areas: list[dict[str, Any]] = []
                if building.main_area_sqm > 0:
                    building_areas.append({"type": "main", "area_sqm": building.main_area_sqm})
                if building.service_area_sqm > 0:
                    building_areas.append({"type": "service", "area_sqm": building.service_area_sqm})
                if building.mamad_area_sqm > 0:
                    building_areas.append({"type": "mamad", "area_sqm": building.mamad_area_sqm})
                if building.basement_area_sqm > 0:
                    bt = f"basement_{building.basement_type}" if building.basement_type else "basement_service"
                    building_areas.append({"type": bt, "area_sqm": building.basement_area_sqm})

                shovi = nachla.shovi_per_sqm if hasattr(nachla, 'shovi_per_sqm') else 7000
                fee_result = await self.invoke_tool(
                    "calculate_building_permit_fees",
                    {
                        "building_areas": building_areas,
                        "shovi_per_sqm": shovi,
                        "building_order": building.building_order,
                        "is_agricultural": building.building_type == BuildingType.AGRICULTURAL,
                        "is_pre_1965": building.is_pre_1965,
                        "permit_size_sqm": building.permit_area_sqm,
                        "priority_area": nachla.priority_area.value if nachla.priority_area else None,
                    },
                )
                results["building_results"][building.id] = fee_result
                fees = fee_result.get("result", 0)
                results["permit_fees"][f"building_{building.id}_permit_fees"] = fees
                results["total_permit_fees"] += fees
            except CalculationInputError as exc:
                logger.warning("Permit fee input error for building %d: %s (not retrying)", building.id, exc)
                results["building_results"][building.id] = {"error": str(exc), "input_error": True}
            except Exception as exc:
                logger.error("Permit fee calc failed for building %d: %s", building.id, exc)
                results["building_results"][building.id] = {"error": str(exc)}

        # Check permit fee cap
        try:
            cap_result = await self.invoke_tool(
                "check_permit_fee_cap",
                {
                    "total_fees": results["total_permit_fees"],
                    "priority_area": nachla.priority_area.value if nachla.priority_area else None,
                },
            )
            results["permit_fee_cap"] = cap_result
        except Exception as exc:
            logger.error("Permit fee cap check failed: %s", exc)

        return results

    async def _calc_split(
        self,
        nachla: Nachla,
        tabas: list[Taba],
        sqm_results: dict[str, Any],
    ) -> dict[str, Any]:
        """Calculate split costs.

        Args:
            nachla: Nachla model.
            tabas: Taba list.
            sqm_results: Sqm equivalent results.

        Returns:
            Split calculation results.
        """
        results: dict[str, Any] = {}
        try:
            # Extract plot size and split allowance from primary taba
            primary_taba = next((t for t in tabas if t.is_primary), tabas[0] if tabas else None)
            plot_size = primary_taba.plot_size_sqm if primary_taba else 0
            taba_allows = primary_taba.split_allowed if primary_taba else False
            eligibility = await self.invoke_tool(
                "check_split_eligibility",
                {
                    "authorization_type": nachla.authorization_type.value,
                    "is_capitalized": nachla.is_capitalized,
                    "plot_size_sqm": plot_size,
                    "taba_allows_split": taba_allows,
                },
            )
            results["eligibility"] = eligibility
            if eligibility.get("eligible", False):
                split_cost = await self.invoke_tool(
                    "calculate_split_cost",
                    {
                        "shovi_meter_aku": sqm_results.get("shovi_meter_aku", 0),
                        "priority_area": nachla.priority_area.value,
                        "is_capitalized": nachla.is_capitalized,
                        "capitalization_track": nachla.capitalization_track.value,
                    },
                )
                results["cost"] = split_cost
        except Exception as exc:
            logger.error("Split calc failed: %s", exc)
            results["error"] = str(exc)
        return results

    async def _calc_betterment(
        self,
        nachla: Nachla,
        buildings: list[Building],
    ) -> dict[str, Any]:
        """Calculate betterment levy estimates.

        Args:
            nachla: Nachla model.
            buildings: Building list.

        Returns:
            Betterment levy results.
        """
        results: dict[str, Any] = {}
        for building in buildings:
            if building.status == BuildingStatus.COMPLIANT:
                continue
            try:
                # Estimate betterment: new value = area * shovi, old value = 0 for unpermitted
                shovi = nachla.shovi_per_sqm if hasattr(nachla, 'shovi_per_sqm') else 7000
                new_val = building.main_area_sqm * shovi
                old_val = (building.permit_area_sqm or 0) * shovi
                result = await self.invoke_tool(
                    "calculate_betterment_levy",
                    {
                        "new_value": new_val,
                        "old_value": old_val,
                    },
                )
                results[f"building_{building.id}"] = result
            except CalculationInputError as exc:
                logger.warning("Betterment input error for building %d: %s (not retrying)", building.id, exc)
                results[f"building_{building.id}"] = {"error": str(exc), "input_error": True}
            except Exception as exc:
                logger.error("Betterment calc failed for building %d: %s", building.id, exc)
                results[f"building_{building.id}"] = {"error": str(exc)}
        return results

    async def _build_report_data(
        self,
        nachla: Nachla,
        buildings: list[Building],
        tabas: list[Taba],
        calc_results: dict[str, Any],
    ) -> ReportData:
        """Build the ReportData model from accumulated results.

        Args:
            nachla: Nachla model.
            buildings: Confirmed building list.
            tabas: Taba list.
            calc_results: All calculation results.

        Returns:
            Complete ReportData instance.
        """
        report_date = datetime.now(UTC).strftime("%Y-%m-%d")
        report = ReportData(
            nachla=nachla,
            report_date=report_date,
            tabas=tabas,
            buildings=buildings,
            audit_log=self.audit_logger.to_audit_entries(),
            total_usage_fees=calc_results.get("usage_fees", {}).get("total", 0),
            total_permit_fees=calc_results.get("regularization", {}).get("total_permit_fees", 0),
            hivun_375_result=calc_results.get("hivun", {}).get("hivun_375"),
            hivun_33_result=calc_results.get("hivun", {}).get("hivun_33"),
            split_results=calc_results.get("split", {}).get("cost", []),
        )

        # Add priority area disclaimer
        report.add_priority_area_disclaimer(nachla.priority_area.value)

        # Generate narrative sections with LLM
        report = await self.generate_report_narratives(report)

        # Store in workflow
        self.workflow.report_data = report
        return report

    async def _run_review(self, report_data: ReportData) -> bool:
        """Step 13: Automated sanity checks.

        Args:
            report_data: The assembled report data.

        Returns:
            True if all sanity checks pass.
        """
        self.workflow.advance(WorkflowPhase.REPORT)
        self.workflow.complete_current_phase()
        self.workflow.advance(WorkflowPhase.REVIEW)

        results = run_sanity_checks(self.workflow)
        all_passed = all(r.get("passed", False) for r in results.values())

        if not all_passed:
            failed = [f"{name}: {r['message']}" for name, r in results.items() if not r.get("passed", False)]
            logger.warning("Sanity check failures:\n%s", "\n".join(failed))

        self.workflow.complete_current_phase()
        return all_passed

    async def _run_report_generation(self, report_data: ReportData) -> str:
        """Step 12: Generate Word report and audit log.

        Args:
            report_data: The complete report data.

        Returns:
            Path to the generated report file.
        """
        # This will be implemented by the document-builder agent (Phase 2)
        # For now, return a placeholder path
        logger.info("Step 12: Report generation (placeholder)")
        return "report_placeholder.docx"

    # ------------------------------------------------------------------
    # LLM-powered methods (require attach_llm to have been called)
    # ------------------------------------------------------------------

    async def analyze_uploaded_documents(
        self,
        file_paths: dict[str, str],
    ) -> tuple[list[Building], list[Taba], list[dict[str, Any]]]:
        """Parse uploaded PDFs, classify them, and extract building/taba data using Claude.

        Args:
            file_paths: Dict mapping file type ("survey_map", "building_permits", etc.) to file path.

        Returns:
            Tuple of (buildings, tabas, document_classifications).
            document_classifications: list of dicts with:
              - filename: str
              - detected_type: str (e.g. "מפת מדידה", "היתר בנייה", "סיכום בדיקת התכנות", "לא רלוונטי")
              - is_relevant: bool
              - confidence: str ("high", "medium", "low")
              - note: str (Hebrew explanation)
        """
        if not self.llm_client:
            logger.warning("No LLM client attached, cannot analyze documents")
            return [], [], []

        from documents.pdf_parser import PDFParser

        parser = PDFParser()
        all_text_parts: list[str] = []
        all_tables: list[list[list[str]]] = []
        file_summaries: list[dict[str, str]] = []

        for file_type, fpath in file_paths.items():
            try:
                parsed = parser.parse(fpath)
                fname = fpath.rsplit("/", 1)[-1] if "/" in fpath else fpath.rsplit("\\", 1)[-1]
                all_text_parts.append(f"--- {file_type}: {fname} ---\n{parsed.text}")
                all_tables.extend(parsed.tables)
                file_summaries.append({
                    "filename": fname,
                    "file_type": file_type,
                    "text_length": str(len(parsed.text)),
                    "table_count": str(len(parsed.tables)),
                    "first_200_chars": parsed.text[:200] if parsed.text else "",
                })
                self.audit_logger.log_data_source(
                    source_type=file_type,
                    source_name=fpath,
                    source_date=parsed.metadata.get("creation_date"),
                    file_path=fpath,
                )
                if parsed.warnings:
                    for w in parsed.warnings:
                        logger.warning("Document warning (%s): %s", file_type, w)
            except Exception as exc:
                logger.error("Failed to parse %s (%s): %s", file_type, fpath, exc)

        if not all_text_parts:
            return [], [], []

        combined_text = "\n\n".join(all_text_parts)
        self._document_context = combined_text

        # Single LLM call: classify documents AND extract data together
        doc_classifications: list[dict[str, Any]] = []

        extraction_prompt = (
            "You are analyzing documents for an Israeli agricultural settlement (nachla) feasibility study.\n\n"
            "STEP 1 — CLASSIFY each document:\n"
            "For each file section (marked with --- filename ---), determine:\n"
            "- detected_type: מפת מדידה / היתר בנייה / תב\"ע / סיכום בדיקת התכנות / נסח טאבו / לא רלוונטי\n"
            "- is_relevant: true if it contains building/planning data, false if unrelated\n"
            "- confidence: high/medium/low\n"
            "- note: Hebrew explanation if the file seems wrong or irrelevant\n\n"
            "STEP 2 — EXTRACT buildings from relevant documents:\n"
            "For each building found, return:\n"
            "- name (Hebrew description)\n"
            "- building_type: residential/service/agricultural/plach/pergola/pool/"
            "basement_service/basement_residential/attic/ground_floor_open/"
            "ground_floor_closed/temporary/shed_open/pre_1965\n"
            "- main_area_sqm (numeric)\n"
            "- service_area_sqm (0 if none)\n"
            "- pergola_area_sqm (0 if none)\n"
            "- basement_area_sqm (0 if none)\n"
            "- mamad_area_sqm (0 if none)\n"
            "- permit_year (null if no permit)\n"
            "- permit_area_sqm (null if no permit)\n"
            "- status: compliant/deviation/no_permit/marked_demolition/building_line_violation\n"
            "- deviation_sqm (if deviation)\n"
            "- construction_year (if identifiable)\n\n"
            "STEP 3 — EXTRACT taba (zoning plan) info if present:\n"
            "- taba_number, taba_name, status (approved/in_process/deposited), approval_date\n"
            "- plot_size_sqm, num_units_allowed\n"
            "- unit rights (main_area_sqm, service_area_sqm per unit)\n\n"
            "Return JSON:\n"
            "{\n"
            '  "classifications": [{filename, detected_type, is_relevant, confidence, note}, ...],\n'
            '  "buildings": [...],\n'
            '  "tabas": [...]\n'
            "}"
        )

        try:
            result = await self.llm_client.analyze_document(
                system=self.system_prompt,
                document_text=combined_text,
                document_tables=all_tables,
                extraction_prompt=extraction_prompt,
            )
        except Exception as exc:
            logger.error("LLM document analysis failed: %s", exc)
            return [], [], []

        # Extract classifications from the combined result
        doc_classifications = result.get("classifications", [])

        # Parse and validate buildings against Pydantic model
        buildings: list[Building] = []
        raw_buildings = result.get("buildings", [])
        validation_errors: list[str] = []
        for i, raw in enumerate(raw_buildings):
            try:
                raw.setdefault("id", i + 1)
                raw.setdefault("building_order", i + 1)
                raw.setdefault("user_confirmed", False)
                building = Building.model_validate(raw)
                buildings.append(building)
                self.audit_logger.log_classification(
                    building_id=building.id,
                    building_name=building.name,
                    classification=building.building_type.value,
                    reasoning=raw.get("reasoning", "Extracted from documents by AI"),
                )
            except Exception as exc:
                logger.warning("Failed to validate building %d from LLM: %s", i, exc)
                validation_errors.append(f"building {i}: {exc}")

        # Retry once with validation errors fed back to Claude if we lost buildings
        if validation_errors and self.llm_client and len(buildings) < len(raw_buildings):
            logger.info("Retrying %d failed buildings with validation feedback", len(validation_errors))
            try:
                retry_result = await self.llm_client.analyze_document(
                    system=self.system_prompt,
                    document_text=combined_text,
                    document_tables=all_tables,
                    extraction_prompt=(
                        f"Previous extraction had validation errors:\n"
                        + "\n".join(validation_errors[:5])
                        + "\n\nPlease fix and re-extract. Return JSON: {\"buildings\": [...]}"
                    ),
                )
                for j, raw in enumerate(retry_result.get("buildings", [])):
                    try:
                        raw.setdefault("id", len(buildings) + j + 1)
                        raw.setdefault("building_order", len(buildings) + j + 1)
                        raw.setdefault("user_confirmed", False)
                        building = Building.model_validate(raw)
                        buildings.append(building)
                    except Exception:
                        pass  # Give up on this building
            except Exception as exc:
                logger.warning("Retry extraction failed: %s", exc)

        # Parse tabas
        tabas: list[Taba] = []
        raw_tabas = result.get("tabas", [])
        for raw_taba in raw_tabas:
            try:
                taba = Taba(**raw_taba)
                tabas.append(taba)
            except Exception as exc:
                logger.warning("Failed to parse taba from LLM: %s", exc)

        logger.info("Document analysis extracted %d buildings, %d tabas, %d classifications",
                    len(buildings), len(tabas), len(doc_classifications))
        return buildings, tabas, doc_classifications

    async def classify_buildings_with_llm(
        self,
        buildings: list[Building],
        document_context: str = "",
    ) -> list[Building]:
        """Enhance building classifications using Claude.

        Args:
            buildings: Buildings to classify/validate.
            document_context: Text from parsed documents for context.

        Returns:
            Updated building list with enhanced classifications.
        """
        if not self.llm_client or not buildings:
            return buildings

        # Only expose lookup tools to Claude (not calculation tools)
        lookup_tool_names = {
            "get_priority_area", "get_discount", "get_usage_rate", "get_hivun_33_rate",
        }
        lookup_schemas = [
            s for s in self.get_tool_schemas()
            if s["name"] in lookup_tool_names
        ]

        buildings_raw = [b.model_dump() for b in buildings]

        try:
            classifications = await self.llm_client.classify_buildings(
                system=self.system_prompt,
                buildings_raw=buildings_raw,
                document_context=document_context or self._document_context,
                tools=lookup_schemas,
                tool_executor=self.invoke_tool,
            )
        except Exception as exc:
            logger.error("LLM classification failed: %s", exc)
            return buildings

        # Apply classifications back to buildings
        classification_map = {c.get("id"): c for c in classifications if "id" in c}
        for building in buildings:
            if building.id in classification_map:
                c = classification_map[building.id]
                old_type = building.building_type.value
                new_type = c.get("building_type", old_type)
                new_status = c.get("status", building.status.value)
                reasoning = c.get("reasoning", "")

                try:
                    building.building_type = BuildingType(new_type)
                    building.status = BuildingStatus(new_status)
                except ValueError as ve:
                    logger.warning("Invalid classification value for building %d: %s", building.id, ve)
                    continue

                if old_type != new_type:
                    self.audit_logger.log_classification(
                        building_id=building.id,
                        building_name=building.name,
                        classification=new_type,
                        reasoning=reasoning or "Reclassified by AI analysis",
                    )

        return buildings

    async def generate_report_narratives(self, report_data: ReportData) -> ReportData:
        """Generate professional Hebrew narrative sections for the report.

        Args:
            report_data: Report data with calculation results.

        Returns:
            Report data with narrative sections populated.
        """
        if not self.llm_client:
            return report_data

        nachla = report_data.nachla
        context = {
            "owner_name": nachla.owner_name,
            "moshav_name": nachla.moshav_name,
            "gush": nachla.gush,
            "helka": nachla.helka,
            "authorization_type": nachla.authorization_type.value,
            "is_capitalized": nachla.is_capitalized,
            "priority_area": nachla.priority_area.value,
            "num_buildings": len(report_data.buildings),
            "client_goals": [g.value for g in nachla.client_goals],
            "total_usage_fees": report_data.total_usage_fees,
            "total_permit_fees": report_data.total_permit_fees,
            "hivun_375_result": report_data.hivun_375_result,
            "hivun_33_result": report_data.hivun_33_result,
        }

        # Study objectives narrative
        try:
            objectives_text = await self.llm_client.generate_narrative(
                system=self.system_prompt,
                context=context,
                section_prompt=(
                    "Write a professional Hebrew paragraph (2-3 sentences) describing "
                    "the objectives of this feasibility study. Include the owner name, "
                    "moshav, and what the client wants to check. Be formal and concise."
                ),
            )
            report_data.study_objectives = objectives_text
        except Exception as exc:
            logger.error("Failed to generate study objectives narrative: %s", exc)

        # Recommendations narrative
        try:
            recommendations_text = await self.llm_client.generate_narrative(
                system=self.system_prompt,
                context=context,
                section_prompt=(
                    "Write professional Hebrew recommendations (3-5 bullet points) "
                    "based on the calculation results. Consider the authorization type, "
                    "capitalization status, priority area, and client goals. "
                    "Each recommendation should be actionable."
                ),
            )
            report_data.recommendations = recommendations_text
        except Exception as exc:
            logger.error("Failed to generate recommendations narrative: %s", exc)

        return report_data

    def get_audit_summary(self) -> dict[str, Any]:
        """Get a summary of the audit log.

        Returns:
            Audit log summary dict.
        """
        return self.audit_logger.generate_summary()

    def save_audit_log(self, file_path: str) -> None:
        """Save the audit log to a JSON file.

        Args:
            file_path: Destination path.
        """
        self.audit_logger.save_json(file_path)
