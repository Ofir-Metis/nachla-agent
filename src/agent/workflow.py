"""Phase-based workflow engine for nachla feasibility studies.

Tracks workflow progress through 16 phases from intake to completion.
Enforces the mandatory classification checkpoint -- calculations cannot
proceed until the user has confirmed building classifications.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class WorkflowPhase(StrEnum):
    """All phases of the nachla feasibility study workflow."""

    INTAKE = "intake"
    TABA_ANALYSIS = "taba_analysis"
    BUILDING_MAPPING = "building_mapping"
    CLASSIFICATION = "classification"
    CHECKPOINT = "checkpoint"
    USAGE_FEES = "usage_fees"
    SQM_EQUIVALENT = "sqm_equivalent"
    HIVUN = "hivun"
    REGULARIZATION = "regularization"
    SPLIT = "split"
    AGRICULTURAL = "agricultural"
    BETTERMENT = "betterment"
    REPORT = "report"
    REVIEW = "review"
    EXPORT = "export"
    COMPLETE = "complete"


# Ordered list of phases for sequential validation.
_PHASE_ORDER: list[WorkflowPhase] = list(WorkflowPhase)

# Mapping from workflow phase to Monday.com status string.
_MONDAY_STATUS_MAP: dict[WorkflowPhase, str] = {
    WorkflowPhase.INTAKE: "בבדיקה",
    WorkflowPhase.TABA_ANALYSIS: "בבדיקה",
    WorkflowPhase.BUILDING_MAPPING: "בבדיקה",
    WorkflowPhase.CLASSIFICATION: "בבדיקה",
    WorkflowPhase.CHECKPOINT: "בבדיקה",
    WorkflowPhase.USAGE_FEES: "בחישובים",
    WorkflowPhase.SQM_EQUIVALENT: "בחישובים",
    WorkflowPhase.HIVUN: "בחישובים",
    WorkflowPhase.REGULARIZATION: "בחישובים",
    WorkflowPhase.SPLIT: "בחישובים",
    WorkflowPhase.AGRICULTURAL: "בחישובים",
    WorkflowPhase.BETTERMENT: "בחישובים",
    WorkflowPhase.REPORT: "טיוטה מוכנה",
    WorkflowPhase.REVIEW: "בבקרה",
    WorkflowPhase.EXPORT: "מאושר",
    WorkflowPhase.COMPLETE: "מאושר",
}

# Mapping from workflow phase to Monday.com update message template.
_MONDAY_UPDATE_MAP: dict[WorkflowPhase, str] = {
    WorkflowPhase.INTAKE: "קליטת לקוח הושלמה",
    WorkflowPhase.TABA_ANALYSIS: 'ניתוח תב"ע הושלם - {taba_count} תב"עות נמצאו',
    WorkflowPhase.BUILDING_MAPPING: "מיפוי מבנים הושלם - {building_count} מבנים זוהו",
    WorkflowPhase.CLASSIFICATION: "סיימתי ניתוח {building_count} מבנים, {deviation_count} חריגים",
    WorkflowPhase.CHECKPOINT: "ממתין לאישור סיווג מבנים",
    WorkflowPhase.HIVUN: "היוון 3.75%: {hivun_375}, 33%: {hivun_33}",
    WorkflowPhase.REPORT: "טיוטה מוכנה לבקרה",
    WorkflowPhase.REVIEW: "בקרה אוטומטית הושלמה",
    WorkflowPhase.EXPORT: "דוח סופי הופק",
    WorkflowPhase.COMPLETE: "בדיקת התכנות הושלמה",
}

# Phases that are allowed to be skipped (e.g., split is optional).
_SKIPPABLE_PHASES: frozenset[WorkflowPhase] = frozenset(
    {
        WorkflowPhase.SPLIT,
        WorkflowPhase.AGRICULTURAL,
        WorkflowPhase.BETTERMENT,
    }
)


class WorkflowError(Exception):
    """Raised when a workflow transition is invalid."""


class WorkflowState(BaseModel):
    """Tracks workflow progress and all accumulated data.

    The state object is the single source of truth for where we are
    in the workflow and what data has been collected so far.
    """

    current_phase: WorkflowPhase = Field(
        default=WorkflowPhase.INTAKE,
        description="Current workflow phase",
    )
    completed_phases: list[WorkflowPhase] = Field(
        default_factory=list,
        description="Phases that have been completed",
    )

    # Data collected through the workflow
    nachla: Any | None = Field(default=None, description="Nachla model")
    buildings: list[Any] = Field(default_factory=list, description="Building models")
    tabas: list[Any] = Field(default_factory=list, description="Taba models")

    # Critical checkpoint flag
    classifications_confirmed: bool = Field(
        default=False,
        description="Whether the user confirmed building classifications (checkpoint 3.4)",
    )

    # Calculation results keyed by phase name
    calculation_results: dict[str, Any] = Field(
        default_factory=dict,
        description="Accumulated calculation results from each phase",
    )

    # Report data
    report_data: Any | None = Field(default=None, description="ReportData model")

    # Integration
    monday_item_id: str | None = Field(default=None, description="Monday.com item ID")

    # Review results
    sanity_check_results: dict[str, Any] = Field(
        default_factory=dict,
        description="Results from step 13 sanity checks",
    )

    model_config = {"arbitrary_types_allowed": True}

    def can_proceed_to(self, phase: WorkflowPhase) -> bool:
        """Check if transition to the given phase is allowed.

        CRITICAL: Cannot pass CHECKPOINT unless classifications_confirmed is True.

        Args:
            phase: The target phase to transition to.

        Returns:
            True if the transition is allowed.
        """
        target_idx = _PHASE_ORDER.index(phase)
        current_idx = _PHASE_ORDER.index(self.current_phase)

        # Cannot go backwards
        if target_idx < current_idx:
            return False

        # Cannot skip the checkpoint
        checkpoint_idx = _PHASE_ORDER.index(WorkflowPhase.CHECKPOINT)
        if target_idx > checkpoint_idx and not self.classifications_confirmed:
            return False

        # Check that all required (non-skippable) phases between current and
        # target have been completed.
        for idx in range(current_idx, target_idx):
            intermediate = _PHASE_ORDER[idx]
            if (
                intermediate not in self.completed_phases
                and intermediate not in _SKIPPABLE_PHASES
                and idx != current_idx
            ):
                return False

        return True

    def advance(self, phase: WorkflowPhase) -> None:
        """Advance to the next phase if the transition is allowed.

        Args:
            phase: The target phase.

        Raises:
            WorkflowError: If the transition is not allowed.
        """
        if not self.can_proceed_to(phase):
            if (
                _PHASE_ORDER.index(phase) > _PHASE_ORDER.index(WorkflowPhase.CHECKPOINT)
                and not self.classifications_confirmed
            ):
                raise WorkflowError(
                    f"Cannot advance to {phase}: building classifications have not been "
                    "confirmed by the user (checkpoint 3.4). "
                    "Call confirm_classifications() first."
                )
            raise WorkflowError(
                f"Cannot advance from {self.current_phase} to {phase}: prerequisite phases are not complete."
            )

        # Mark the current phase as completed
        if self.current_phase not in self.completed_phases:
            self.completed_phases.append(self.current_phase)

        self.current_phase = phase

    def complete_current_phase(self) -> None:
        """Mark the current phase as completed without advancing.

        Useful when a phase finishes but the next phase is determined dynamically.
        """
        if self.current_phase not in self.completed_phases:
            self.completed_phases.append(self.current_phase)

    def confirm_classifications(self) -> None:
        """Mark building classifications as confirmed by the user.

        This is the gate that allows the workflow to proceed past the checkpoint.
        """
        self.classifications_confirmed = True

    def skip_phase(self, phase: WorkflowPhase) -> None:
        """Skip an optional phase (e.g., split not relevant for this nachla).

        Args:
            phase: The phase to skip.

        Raises:
            WorkflowError: If the phase is not skippable.
        """
        if phase not in _SKIPPABLE_PHASES:
            raise WorkflowError(f"Phase {phase} is not skippable.")
        if phase not in self.completed_phases:
            self.completed_phases.append(phase)

    def get_monday_status(self) -> str:
        """Map the current phase to a Monday.com status string.

        Returns:
            Hebrew status string for the Monday.com board.
        """
        return _MONDAY_STATUS_MAP.get(self.current_phase, "בבדיקה")

    def get_monday_update(self, **kwargs: str) -> str:
        """Get the Monday.com update message for the current phase.

        Args:
            **kwargs: Template variables (e.g., building_count, taba_count).

        Returns:
            Formatted Hebrew update message.
        """
        template = _MONDAY_UPDATE_MAP.get(self.current_phase, "")
        if not template:
            return ""
        try:
            return template.format(**kwargs)
        except KeyError:
            return template

    def get_progress_summary(self) -> dict[str, Any]:
        """Get a summary of workflow progress.

        Returns:
            Dictionary with current phase, completed count, total count,
            and whether the checkpoint has been passed.
        """
        total = len(_PHASE_ORDER)
        completed = len(self.completed_phases)
        return {
            "current_phase": self.current_phase,
            "completed_phases": list(self.completed_phases),
            "completed_count": completed,
            "total_phases": total,
            "progress_percent": round((completed / total) * 100, 1),
            "classifications_confirmed": self.classifications_confirmed,
            "monday_status": self.get_monday_status(),
        }


def run_sanity_checks(state: WorkflowState) -> dict[str, Any]:
    """Run step 13 sanity checks on the accumulated workflow data.

    Validates internal consistency of all calculations and data before
    the report is generated.

    Args:
        state: The current workflow state with all accumulated data.

    Returns:
        Dictionary with check results. Each key is a check name,
        value is a dict with 'passed' (bool) and 'message' (str).
    """
    results: dict[str, Any] = {}
    nachla = state.nachla
    buildings = state.buildings

    # Check 1: Building count consistency
    if nachla is not None and hasattr(nachla, "num_existing_houses"):
        residential_count = sum(
            1 for b in buildings if hasattr(b, "building_type") and b.building_type == "residential"
        )
        expected = nachla.num_existing_houses
        results["building_count_match"] = {
            "passed": residential_count == expected,
            "message": (f"Identified {residential_count} residential buildings, user declared {expected}."),
        }

    # Check 2: Usage fees = 0 for first house
    usage_results = state.calculation_results.get("usage_fees", {})
    if usage_results:
        first_house_fees = usage_results.get("building_1_usage_fees", 0)
        results["first_house_usage_exempt"] = {
            "passed": first_house_fees == 0,
            "message": (
                f"First house usage fees: {first_house_fees} "
                f"({'exempt as expected' if first_house_fees == 0 else 'ERROR: should be 0'})"
            ),
        }

    # Check 3: Sqm equivalent in reasonable range
    sqm_result = state.calculation_results.get("sqm_equivalent", {})
    if sqm_result:
        total_sqm = sqm_result.get("total_nachla_sqm", 0)
        is_reasonable = 800 <= total_sqm <= 1500
        results["sqm_equivalent_reasonable"] = {
            "passed": is_reasonable,
            "message": (
                f"Nachla sqm equivalent: {total_sqm} "
                f"({'within range 800-1500' if is_reasonable else 'WARNING: outside typical range'})"
            ),
        }

    # Check 4: 33% > 3.75%
    hivun_results = state.calculation_results.get("hivun", {})
    if hivun_results:
        cost_375 = hivun_results.get("hivun_375_cost", 0)
        cost_33 = hivun_results.get("hivun_33_cost", 0)
        if cost_375 > 0 and cost_33 > 0:
            results["hivun_33_greater_than_375"] = {
                "passed": cost_33 > cost_375,
                "message": (
                    f"3.75% cost: {cost_375:,.0f}, 33% cost: {cost_33:,.0f} "
                    f"({'33% > 3.75% as expected' if cost_33 > cost_375 else 'ERROR: 33% should be greater'})"
                ),
            }

    # Check 5: Permit fees > 0 for deviation/no_permit buildings
    for building in buildings:
        if not hasattr(building, "status"):
            continue
        if building.status in ("deviation", "no_permit"):
            bld_id = getattr(building, "id", "?")
            fees_key = f"building_{bld_id}_permit_fees"
            fees = state.calculation_results.get("permit_fees", {}).get(fees_key, None)
            if fees is not None:
                results[f"permit_fees_building_{bld_id}"] = {
                    "passed": fees > 0,
                    "message": (
                        f"Building {bld_id} ({building.status}): permit fees = {fees} "
                        f"({'OK' if fees > 0 else 'ERROR: should be > 0'})"
                    ),
                }

    # Check 6: Classifications confirmed
    results["classifications_confirmed"] = {
        "passed": state.classifications_confirmed,
        "message": (
            "Building classifications "
            + ("confirmed by user" if state.classifications_confirmed else "NOT confirmed -- cannot proceed")
        ),
    }

    # Check 7: Total building area <= plot area x coverage %
    if nachla is not None and state.tabas:
        primary_taba = next((t for t in state.tabas if getattr(t, "is_primary", False)), None)
        if primary_taba is None and state.tabas:
            primary_taba = state.tabas[0]
        if primary_taba is not None:
            plot_size = getattr(primary_taba, "plot_size_sqm", 0)
            coverage_pct = getattr(primary_taba, "coverage_percent", None)
            if plot_size > 0 and coverage_pct is not None and coverage_pct > 0:
                max_coverage = plot_size * (coverage_pct / 100.0)
                total_building_area = sum(
                    getattr(b, "main_area_sqm", 0) + getattr(b, "service_area_sqm", 0)
                    for b in buildings
                )
                ok = total_building_area <= max_coverage
                results["area_vs_coverage"] = {
                    "passed": ok,
                    "message": (
                        f"Total building area {total_building_area:.0f} sqm vs "
                        f"max coverage {max_coverage:.0f} sqm ({coverage_pct}% of {plot_size}). "
                        + ("OK" if ok else "WARNING: exceeds plot coverage limit")
                    ),
                }

    # Check 8: Map areas vs calculation input areas (where available)
    for building in buildings:
        bld_id = getattr(building, "id", None)
        if bld_id is None:
            continue
        map_area = getattr(building, "main_area_sqm", 0) + getattr(building, "service_area_sqm", 0)
        calc_area_key = f"building_{bld_id}_charged_area"
        calc_area = state.calculation_results.get("permit_fees", {}).get(calc_area_key, None)
        if calc_area is not None and map_area > 0:
            diff_pct = abs(calc_area - map_area) / map_area * 100
            ok = diff_pct < 10  # Allow 10% tolerance for exemptions/adjustments
            results[f"area_consistency_building_{bld_id}"] = {
                "passed": ok,
                "message": (
                    f"Building {bld_id}: map area {map_area:.0f}, calc area {calc_area:.0f} "
                    f"(diff {diff_pct:.1f}%). "
                    + ("OK" if ok else "WARNING: significant mismatch")
                ),
            }

    state.sanity_check_results = results
    return results
