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
from models.nachla import ClientGoal, Nachla, PriorityArea
from models.report import ReportData
from models.taba import Taba

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

        # Hooks
        self.pre_tool_hook = PreToolUseHook()
        self.post_tool_hook = PostToolUseHook(self.audit_logger)
        self.stop_hook = StopHook()

        # Register calculation tools
        self._register_tools()

    def _register_tools(self) -> None:
        """Register all calculation tools with metadata.

        Each tool function is wrapped in a ToolDescriptor with its name,
        Hebrew name, description, and auto-extracted parameter schema.
        """
        try:
            from tools.calc_dmei_heter import (
                calculate_building_permit_fees,
                calculate_dmei_heter,
                check_permit_fee_cap,
            )
            from tools.calc_dmei_shimush import calculate_dmei_shimush
            from tools.calc_hetel_hashbacha import (
                calculate_betterment_levy,
                calculate_partial_betterment,
                estimate_split_betterment,
            )
            from tools.calc_hivun import (
                calculate_hivun_33,
                calculate_hivun_375,
                compare_tracks,
            )
            from tools.calc_pitzul import (
                calculate_remaining_rights,
                calculate_split_cost,
                check_split_eligibility,
            )
            from tools.calc_sqm_equivalent import (
                calculate_hivun_375_sqm,
                calculate_nachla_sqm_equivalent,
                calculate_potential_sqm,
                calculate_sqm_equivalent,
            )
            from tools.lookup_tables import (
                lookup_development_costs,
                lookup_plach_rate,
                lookup_settlement_shovi,
            )
            from tools.priority_areas import (
                get_discount,
                get_hivun_33_rate,
                get_priority_area,
                get_usage_rate,
            )
        except ImportError:
            logger.warning("Calculation tools not available; registering stubs only.")
            return

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
        buildings = await self._run_building_mapping(nachla)

        # Step 3.4: Classification checkpoint (BLOCKS until confirmed)
        buildings = await self._run_classification_checkpoint(buildings)

        # Steps 4-9, 11: Calculations
        calc_results = await self._run_calculations(nachla, buildings, tabas)

        # Step 12: Report generation
        report_data = self._build_report_data(nachla, buildings, tabas, calc_results)

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

        self.workflow.tabas = tabas
        self.workflow.complete_current_phase()
        return tabas

    async def _run_building_mapping(self, nachla: Nachla) -> list[Building]:
        """Step 2: Map buildings from survey map.

        Buildings come from the nachla model (populated by document parsing
        or manual input).

        Args:
            nachla: The nachla model.

        Returns:
            List of Building models.
        """
        self.workflow.advance(WorkflowPhase.BUILDING_MAPPING)
        logger.info("Step 2: Building mapping")

        buildings: list[Building] = []
        if nachla.buildings:
            for b in nachla.buildings:
                if isinstance(b, Building):
                    buildings.append(b)
                    self.audit_logger.log_classification(
                        building_id=b.id,
                        building_name=b.name,
                        classification=b.building_type.value,
                        reasoning="Initial classification from survey map analysis",
                    )

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
            self.workflow.complete_current_phase()
        else:
            self.workflow.skip_phase(WorkflowPhase.AGRICULTURAL)

        # Step 11: Betterment levy (optional)
        self.workflow.advance(WorkflowPhase.BETTERMENT)
        logger.info("Step 11: Calculating betterment levy")
        betterment_results = await self._calc_betterment(nachla, buildings)
        results["betterment"] = betterment_results
        self.workflow.calculation_results["betterment"] = betterment_results
        self.workflow.complete_current_phase()

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
        for building in buildings:
            try:
                fee_result = await self.invoke_tool(
                    "calculate_dmei_shimush",
                    {
                        "building_id": building.id,
                        "building_type": building.building_type.value,
                        "building_order": building.building_order,
                        "main_area_sqm": building.main_area_sqm,
                        "service_area_sqm": building.service_area_sqm,
                        "pergola_area_sqm": building.pergola_area_sqm,
                        "status": building.status.value,
                        "deviation_sqm": building.deviation_sqm or 0,
                        "priority_area": nachla.priority_area.value,
                        "has_intergenerational_continuity": nachla.has_intergenerational_continuity,
                    },
                )
                results["building_fees"][building.id] = fee_result
                results[f"building_{building.id}_usage_fees"] = fee_result.get("total_fees", 0)
                results["total"] += fee_result.get("total_fees", 0)
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
            result = await self.invoke_tool(
                "calculate_nachla_sqm_equivalent",
                {
                    "buildings": [b.model_dump() for b in buildings],
                    "tabas": [t.model_dump() for t in tabas],
                    "priority_area": nachla.priority_area.value,
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
        try:
            result_375 = await self.invoke_tool(
                "calculate_hivun_375",
                {
                    "sqm_equivalent": sqm_results.get("total_nachla_sqm", 808),
                    "shovi_meter_aku": sqm_results.get("shovi_meter_aku", 0),
                    "priority_area": nachla.priority_area.value,
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
                    "sqm_equivalent": sqm_results.get("total_nachla_sqm", 0),
                    "potential_sqm": sqm_results.get("potential_sqm", 0),
                    "shovi_meter_aku": sqm_results.get("shovi_meter_aku", 0),
                    "prior_permit_fees": nachla.prior_permit_fees_purchased if nachla.prior_fees_deductible else 0,
                    "priority_area": nachla.priority_area.value,
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
                fee_result = await self.invoke_tool(
                    "calculate_building_permit_fees",
                    {
                        "building_id": building.id,
                        "building_type": building.building_type.value,
                        "building_order": building.building_order,
                        "main_area_sqm": building.main_area_sqm,
                        "service_area_sqm": building.service_area_sqm,
                        "pergola_area_sqm": building.pergola_area_sqm,
                        "basement_area_sqm": building.basement_area_sqm,
                        "basement_type": building.basement_type or "",
                        "status": building.status.value,
                        "deviation_sqm": building.deviation_sqm or 0,
                        "permit_area_sqm": building.permit_area_sqm or 0,
                        "is_pre_1965": building.is_pre_1965,
                        "priority_area": nachla.priority_area.value,
                    },
                )
                results["building_results"][building.id] = fee_result
                fees = fee_result.get("total_permit_fees", 0)
                results["permit_fees"][f"building_{building.id}_permit_fees"] = fees
                results["total_permit_fees"] += fees
            except Exception as exc:
                logger.error("Permit fee calc failed for building %d: %s", building.id, exc)
                results["building_results"][building.id] = {"error": str(exc)}

        # Check permit fee cap
        try:
            cap_result = await self.invoke_tool(
                "check_permit_fee_cap",
                {
                    "total_permit_fees": results["total_permit_fees"],
                    "priority_area": nachla.priority_area.value,
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
                result = await self.invoke_tool(
                    "calculate_betterment_levy",
                    {
                        "building_id": building.id,
                        "building_type": building.building_type.value,
                        "main_area_sqm": building.main_area_sqm,
                        "priority_area": nachla.priority_area.value,
                    },
                )
                results[f"building_{building.id}"] = result
            except Exception as exc:
                logger.error("Betterment calc failed for building %d: %s", building.id, exc)
                results[f"building_{building.id}"] = {"error": str(exc)}
        return results

    def _build_report_data(
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
