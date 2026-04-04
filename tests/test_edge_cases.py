"""Edge case tests for calculation tools.

Tests scenarios not covered by the 24 golden examples:
- Zero buildings, all-exempt, max buildings
- Non-standard plot sizes (1.5 dunam, 5 dunam)
- All priority area types on same calculation
- Mixed building types in one nachla
- Pre-1965 only nachla
- Frontline with unknown rates
"""

from __future__ import annotations

import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def _load_config() -> dict:
    config_path = Path(__file__).parent.parent / "src" / "config" / "rates_config.json"
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


CONFIG = _load_config()

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
from tools.calc_dmei_heter import (
    calculate_building_permit_fees,
    calculate_dmei_heter,
)
from tools.calc_hivun import (
    calculate_hivun_33,
    calculate_hivun_375,
    compare_tracks,
)
from tools.calc_sqm_equivalent import (
    calculate_hivun_375_sqm,
    calculate_nachla_sqm_equivalent,
)

# ===================================================================
# 1. Zero buildings
# ===================================================================


class TestZeroBuildings:
    def test_no_buildings_produces_zero_fees(self):
        """Nachla with no buildings has zero permit fees."""
        result = calculate_building_permit_fees(
            building_areas=[],
            shovi_per_sqm=10000,
            building_order=1,
        )
        assert result["result"] == 0.0

    def test_hivun_375_still_valid_without_buildings(self):
        """Hivun 3.75% can be calculated without building-specific data."""
        result = calculate_hivun_375(
            sqm_equivalent_375=806.25,
            shovi_per_sqm=10000,
        )
        assert "error" not in result
        assert result["gross_hivun"] > 0

    def test_hivun_33_still_valid_without_buildings(self):
        """Hivun 33% can be calculated from nachla sqm without buildings."""
        result = calculate_hivun_33(
            sqm_equivalent_nachla=972.5,
            sqm_potential=0,
            shovi_per_sqm=10000,
        )
        assert "error" not in result
        assert result["gross_purchase"] > 0


# ===================================================================
# 2. All exempt buildings
# ===================================================================


class TestAllExempt:
    def test_all_exempt_buildings_house1_under_160(self):
        """House 1 under 160sqm is fully exempt from permit fees."""
        result = calculate_building_permit_fees(
            building_areas=[{"type": "main", "area_sqm": 150}],
            shovi_per_sqm=10000,
            building_order=1,
        )
        assert result["result"] == 0.0

    def test_agricultural_building_exempt(self):
        """Agricultural buildings are exempt from permit fees."""
        result = calculate_building_permit_fees(
            building_areas=[{"type": "main", "area_sqm": 500}],
            shovi_per_sqm=10000,
            building_order=1,
            is_agricultural=True,
        )
        assert result["result"] == 0.0

    def test_pre_1965_building_exempt(self):
        """Pre-1965 buildings are exempt from permit fees."""
        result = calculate_building_permit_fees(
            building_areas=[{"type": "main", "area_sqm": 300}],
            shovi_per_sqm=10000,
            building_order=1,
            is_pre_1965=True,
        )
        assert result["result"] == 0.0


# ===================================================================
# 3. Max buildings - stress test
# ===================================================================


class TestMaxBuildings:
    def test_ten_buildings(self):
        """Nachla with 10 buildings does not crash or overflow."""
        for order in range(1, 11):
            result = calculate_building_permit_fees(
                building_areas=[{"type": "main", "area_sqm": 100 + order * 10}],
                shovi_per_sqm=10000,
                building_order=order,
            )
            assert "error" not in result or result.get("result") is not None
            # Should not raise exceptions

    def test_many_buildings_reasonable_total(self):
        """Sum of 10 buildings' permit fees is a finite positive number."""
        total = 0.0
        for order in range(1, 11):
            result = calculate_building_permit_fees(
                building_areas=[{"type": "main", "area_sqm": 200}],
                shovi_per_sqm=10000,
                building_order=order,
            )
            if "error" not in result:
                total += result.get("result", 0)
        assert 0 < total < 1e9  # Finite, positive, not absurdly large


# ===================================================================
# 4. Non-standard plot sizes
# ===================================================================


class TestNonStandardPlot:
    def test_small_plot_1500sqm(self):
        """1.5 dunam plot changes sqm equivalent (not 808)."""
        result = calculate_nachla_sqm_equivalent(
            plot_size_sqm=1500,
            building_coverage_sqm=400,
            taba_rights={
                "main_sqm": 300,
                "mamad_sqm": 24,
                "service_sqm": 76,
            },
        )
        assert "error" not in result
        # Smaller plot = less yard = lower total sqm equivalent
        assert result["result"] > 0
        # Should be less than the standard 808 equivalent yard portion
        yard_sqm = result.get("yard_details", {}).get("total_yard_sqm", 0)
        assert yard_sqm == 1100  # 1500 - 400

    def test_large_plot_5000sqm(self):
        """5 dunam plot produces different sqm equivalent with far yard."""
        result = calculate_nachla_sqm_equivalent(
            plot_size_sqm=5000,
            building_coverage_sqm=600,
            taba_rights={
                "main_sqm": 400,
                "mamad_sqm": 36,
                "service_sqm": 164,
            },
        )
        assert "error" not in result
        yard_details = result.get("yard_details", {})
        total_yard = yard_details.get("total_yard_sqm", 0)
        assert total_yard == 4400  # 5000 - 600
        # Should have effective + remainder + far yard
        assert yard_details.get("yard_effective_sqm", 0) == 1000
        assert yard_details.get("yard_remainder_sqm", 0) == 1000
        assert yard_details.get("yard_far_sqm", 0) == 2400

    def test_hivun_375_dynamic_sqm_non_standard(self):
        """Non-standard plot produces a warning about non-808 value."""
        result = calculate_hivun_375_sqm(
            plot_size_sqm=1500,
            taba_rights={
                "main_sqm": 200,
                "mamad_sqm": 12,
                "service_sqm": 50,
            },
        )
        assert "error" not in result
        assert result["is_standard"] is False
        # The result should differ from 808
        assert result["result"] != 808


# ===================================================================
# 5. All priority area types
# ===================================================================


class TestAllPriorityAreas:
    def test_same_calc_all_areas(self):
        """Same building data, compare results across all 4 area types."""
        base_params = {
            "sqm_equivalent_375": 806.25,
            "shovi_per_sqm": 10000,
        }

        results = {}
        for area in [None, "A", "B", "frontline"]:
            result = calculate_hivun_375(
                priority_area=area,
                **base_params,
            )
            assert "error" not in result
            results[area or "standard"] = result["result"]

        # Standard should be the most expensive
        assert results["standard"] > results["A"]
        assert results["standard"] > results["B"]
        assert results["standard"] > results["frontline"]

        # A has 51% discount, should be cheapest
        assert results["A"] < results["B"]
        assert results["A"] < results["frontline"]

    def test_priority_area_discounts_on_permit_fees(self):
        """Priority area discounts are correctly applied to permit fees."""
        base = calculate_dmei_heter(
            area_sqm=100,
            area_type="main",
            shovi_per_sqm=10000,
        )
        assert "error" not in base

        for area, expected_discount in [("A", 0.51), ("B", 0.25), ("frontline", 0.31)]:
            discounted = calculate_dmei_heter(
                area_sqm=100,
                area_type="main",
                shovi_per_sqm=10000,
                priority_area=area,
            )
            assert "error" not in discounted
            ratio = discounted["result"] / base["result"]
            expected_ratio = 1 - expected_discount
            assert abs(ratio - expected_ratio) < 0.001, f"Area {area}: expected ratio {expected_ratio}, got {ratio}"

    def test_usage_fee_priority_vs_standard(self):
        """Usage fee in priority areas is 3% vs 5% standard."""
        standard_rate = CONFIG["usage_fee_residential"]["value"]
        priority_rate = CONFIG["usage_fee_priority"]["value"]

        assert standard_rate == 0.05
        assert priority_rate == 0.03


# ===================================================================
# 6. Mixed building types
# ===================================================================


class TestMixedBuildingTypes:
    def test_main_and_service_combined(self):
        """Building with main + service areas calculates correctly."""
        result = calculate_building_permit_fees(
            building_areas=[
                {"type": "main", "area_sqm": 200},
                {"type": "service", "area_sqm": 50},
            ],
            shovi_per_sqm=10000,
            building_order=1,
        )
        assert "error" not in result
        # The total should reflect the different coefficients
        # main: (200-160) * 1.0 * 0.91 * 10000 * VAT for house 1 (160 exempt)
        # service: 50 * 0.5 * 0.91 * 10000 * VAT
        assert result["result"] > 0

    def test_building_with_mamad(self):
        """Building with main + mamad calculates correctly."""
        result = calculate_building_permit_fees(
            building_areas=[
                {"type": "main", "area_sqm": 200},
                {"type": "mamad", "area_sqm": 12},
            ],
            shovi_per_sqm=10000,
            building_order=1,
        )
        assert "error" not in result
        # First 12sqm mamad is exempt for house 1
        assert result["result"] > 0


# ===================================================================
# 7. Pre-1965 only nachla
# ===================================================================


class TestPre1965Only:
    def test_all_pre_1965_exempt(self):
        """All pre-1965 buildings produce zero permit fees."""
        for order in range(1, 4):
            result = calculate_building_permit_fees(
                building_areas=[{"type": "main", "area_sqm": 250}],
                shovi_per_sqm=10000,
                building_order=order,
                is_pre_1965=True,
            )
            assert result["result"] == 0.0


# ===================================================================
# 8. Capitalized (mehuvon) nachla
# ===================================================================


class TestCapitalizedNachla:
    def test_hivun_375_still_computable(self):
        """Even if nachla is capitalized, the 3.75% calculation works."""
        result = calculate_hivun_375(
            sqm_equivalent_375=806.25,
            shovi_per_sqm=10000,
        )
        assert "error" not in result
        assert result["result"] > 0

    def test_hivun_33_with_large_prior_deduction(self):
        """Large prior permit deduction reduces 33% amount significantly."""
        result_no_deduction = calculate_hivun_33(
            sqm_equivalent_nachla=972.5,
            sqm_potential=100,
            shovi_per_sqm=10000,
            prior_permit_fees_post_2009=0,
        )
        result_with_deduction = calculate_hivun_33(
            sqm_equivalent_nachla=972.5,
            sqm_potential=100,
            shovi_per_sqm=10000,
            prior_permit_fees_post_2009=200,
        )
        assert result_no_deduction["gross_purchase"] > result_with_deduction["gross_purchase"]
        # Difference should be exactly 200 * 10000 * 0.33
        diff = result_no_deduction["gross_purchase"] - result_with_deduction["gross_purchase"]
        expected_diff = 200 * 10000 * 0.33
        assert abs(diff - expected_diff) < 1


# ===================================================================
# 9. Input validation
# ===================================================================


class TestInputValidation:
    def test_negative_shovi_returns_error(self):
        """Negative shovi produces an error."""
        result = calculate_hivun_375(
            sqm_equivalent_375=806.25,
            shovi_per_sqm=-1000,
        )
        assert "error" in result

    def test_zero_sqm_375_returns_error(self):
        """Zero sqm equivalent returns an error."""
        result = calculate_hivun_375(
            sqm_equivalent_375=0,
            shovi_per_sqm=10000,
        )
        assert "error" in result

    def test_negative_plot_size_returns_error(self):
        """Negative plot size returns error in sqm equivalent calculation."""
        result = calculate_nachla_sqm_equivalent(
            plot_size_sqm=-100,
            building_coverage_sqm=400,
            taba_rights={"main_sqm": 300},
        )
        assert "error" in result

    def test_zero_shovi_hivun_33_returns_error(self):
        """Zero shovi in hivun 33% produces error."""
        result = calculate_hivun_33(
            sqm_equivalent_nachla=972.5,
            sqm_potential=0,
            shovi_per_sqm=0,
        )
        assert "error" in result


# ===================================================================
# 10. Audit trail completeness
# ===================================================================


class TestAuditTrail:
    def test_hivun_375_audit_trail(self):
        """Hivun 3.75% result has complete audit trail."""
        result = calculate_hivun_375(
            sqm_equivalent_375=806.25,
            shovi_per_sqm=10000,
        )
        assert "result" in result
        assert "formula" in result
        assert "rates_used" in result
        assert "inputs" in result
        assert "gross_hivun" in result
        assert "purchase_tax" in result

    def test_hivun_33_audit_trail(self):
        """Hivun 33% result has complete audit trail."""
        result = calculate_hivun_33(
            sqm_equivalent_nachla=972.5,
            sqm_potential=0,
            shovi_per_sqm=10000,
        )
        assert "result" in result
        assert "formula" in result
        assert "rates_used" in result
        assert "inputs" in result
        assert "gross_purchase" in result
        assert "purchase_tax" in result

    def test_permit_fee_audit_trail(self):
        """Permit fee result has audit trail with exemptions."""
        result = calculate_building_permit_fees(
            building_areas=[{"type": "main", "area_sqm": 200}],
            shovi_per_sqm=10000,
            building_order=1,
        )
        assert "result" in result
        assert "inputs" in result

    def test_sqm_equivalent_audit_trail(self):
        """Sqm equivalent result has yard breakdown."""
        result = calculate_nachla_sqm_equivalent(
            plot_size_sqm=2500,
            building_coverage_sqm=500,
            taba_rights={"main_sqm": 375, "mamad_sqm": 24, "service_sqm": 101},
        )
        assert "result" in result
        assert "breakdown" in result
        assert "yard_details" in result


# ===================================================================
# 11. Track comparison
# ===================================================================


class TestTrackComparison:
    def test_compare_tracks_returns_both(self):
        """Track comparison returns both tracks with recommendation."""
        r375 = calculate_hivun_375(
            sqm_equivalent_375=806.25,
            shovi_per_sqm=10000,
        )
        r33 = calculate_hivun_33(
            sqm_equivalent_nachla=972.5,
            sqm_potential=0,
            shovi_per_sqm=10000,
        )
        comparison = compare_tracks(r375, r33)
        assert "result" in comparison
        assert "track_375" in comparison["result"]
        assert "track_33" in comparison["result"]
        assert "difference" in comparison["result"]
        assert "recommendation" in comparison["result"]

    def test_375_always_cheaper_than_33_for_standard(self):
        """For standard nachla without priority, 3.75% is always cheaper."""
        r375 = calculate_hivun_375(
            sqm_equivalent_375=806.25,
            shovi_per_sqm=10000,
        )
        r33 = calculate_hivun_33(
            sqm_equivalent_nachla=972.5,
            sqm_potential=0,
            shovi_per_sqm=10000,
        )
        assert r375["result"] < r33["result"]
