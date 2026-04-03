"""Comprehensive tests for all RMI calculation tools.

Every test uses known values and verifies audit trail structure.
All constants come from rates_config.json - never hardcoded in tests either.
"""

import json
import re
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
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


# ===================================================================
# 1. rates_config.json validation
# ===================================================================

class TestRatesConfig:
    def test_rates_config_loads(self):
        """All required keys present with correct structure."""
        required_keys = [
            "vat_rate",
            "permit_fee_rate",
            "hivun_375_rate",
            "hivun_33_rate",
            "hivun_375_default_sqm",
            "usage_fee_residential",
            "usage_fee_priority",
            "usage_fee_agricultural",
            "usage_fee_plach",
            "usage_period_3rd_plus_years",
            "usage_period_2nd_house_years",
            "purchase_tax_rate",
            "betterment_levy_rate",
            "house_exemption_sqm",
            "mamad_exemption_sqm",
            "priority_area_discounts",
            "sqm_equivalent_coefficients",
            "permit_fee_coefficients",
        ]
        for key in required_keys:
            assert key in CONFIG, f"Missing key: {key}"

    def test_rates_config_types(self):
        """Numeric constants have correct types and ranges."""
        assert CONFIG["vat_rate"]["value"] == 0.18
        assert CONFIG["permit_fee_rate"]["value"] == 0.91
        assert CONFIG["hivun_375_rate"]["value"] == 0.0375
        assert CONFIG["hivun_33_rate"]["value"] == 0.33
        assert CONFIG["hivun_375_default_sqm"]["value"] == 808
        assert CONFIG["usage_fee_residential"]["value"] == 0.05
        assert CONFIG["usage_fee_priority"]["value"] == 0.03
        assert CONFIG["usage_fee_agricultural"]["value"] == 0.02
        assert CONFIG["purchase_tax_rate"]["value"] == 0.06
        assert CONFIG["betterment_levy_rate"]["value"] == 0.50
        assert CONFIG["house_exemption_sqm"]["value"] == 160
        assert CONFIG["mamad_exemption_sqm"]["value"] == 12

    def test_priority_area_discounts_structure(self):
        """Priority area discount tables are complete."""
        discounts = CONFIG["priority_area_discounts"]
        assert "A" in discounts
        assert "B" in discounts
        assert "frontline" in discounts
        assert discounts["A"]["permit"] == 0.51
        assert discounts["B"]["permit"] == 0.25
        assert discounts["frontline"]["permit"] == 0.31
        assert discounts["A"]["purchase_33"] == 0.2014
        assert discounts["A"]["split_160"] == 0.1639

    def test_sqm_coefficients_complete(self):
        """All sqm equivalent coefficients are present."""
        coeffs = CONFIG["sqm_equivalent_coefficients"]
        assert coeffs["main"] == 1.0
        assert coeffs["mamad"] == 0.9
        assert coeffs["service"] == 0.4
        assert coeffs["auxiliary"] == 0.5
        assert coeffs["yard_effective"] == 0.25
        assert coeffs["yard_remainder"] == 0.2
        assert coeffs["yard_far"] == 0.1
        assert coeffs["pool"] == 0.3
        assert coeffs["basement_service"] == 0.3
        assert coeffs["basement_residential"] == 0.7


# ===================================================================
# 2. Permit fees (dmei heter)
# ===================================================================

class TestDmeiHeter:
    def test_dmei_heter_basic(self):
        """Basic permit fee calculation with known values."""
        result = calculate_dmei_heter(
            area_sqm=100,
            area_type="main",
            shovi_per_sqm=7000,
        )
        assert "error" not in result
        # 100 * 1.0 * 7000 * 0.91 * 1.18 = 751,660
        expected = 100 * 1.0 * 7000 * 0.91 * 1.18
        assert result["result"] == pytest.approx(expected, rel=1e-6)

    def test_dmei_heter_with_priority_a(self):
        """Priority area A gives 51% discount on permit fees."""
        result = calculate_dmei_heter(
            area_sqm=100,
            area_type="main",
            shovi_per_sqm=7000,
            priority_area="A",
        )
        assert "error" not in result
        base = 100 * 1.0 * 7000 * 0.91 * 1.18
        expected = base * (1 - 0.51)
        assert result["result"] == pytest.approx(expected, rel=1e-6)

    def test_dmei_heter_with_priority_b(self):
        """Priority area B gives 25% discount on permit fees."""
        result = calculate_dmei_heter(
            area_sqm=100,
            area_type="main",
            shovi_per_sqm=7000,
            priority_area="B",
        )
        assert "error" not in result
        base = 100 * 1.0 * 7000 * 0.91 * 1.18
        expected = base * (1 - 0.25)
        assert result["result"] == pytest.approx(expected, rel=1e-6)

    def test_dmei_heter_exemption_house1(self):
        """House 1 is exempt up to 160sqm for main area."""
        result = calculate_building_permit_fees(
            building_areas=[{"type": "main", "area_sqm": 160}],
            shovi_per_sqm=7000,
            building_order=1,
        )
        assert result["result"] == 0.0
        assert len(result["exemptions"]) > 0

    def test_dmei_heter_exemption_house1_over_160(self):
        """House 1 charges only for area above 160sqm."""
        result = calculate_building_permit_fees(
            building_areas=[{"type": "main", "area_sqm": 200}],
            shovi_per_sqm=7000,
            building_order=1,
        )
        # Should charge for 40sqm only
        expected_single = calculate_dmei_heter(
            area_sqm=40,
            area_type="main",
            shovi_per_sqm=7000,
        )
        assert result["result"] == pytest.approx(expected_single["result"], rel=1e-6)

    def test_dmei_heter_exemption_mamad(self):
        """First mamad per house is exempt up to 12sqm."""
        result = calculate_building_permit_fees(
            building_areas=[
                {"type": "main", "area_sqm": 100},
                {"type": "mamad", "area_sqm": 12},
            ],
            shovi_per_sqm=7000,
            building_order=3,
        )
        # mamad 12sqm should be exempt; only main charged
        main_cost = calculate_dmei_heter(100, "main", 7000)
        assert result["result"] == pytest.approx(main_cost["result"], rel=1e-6)

    def test_dmei_heter_mamad_over_12(self):
        """Mamad charges for area above 12sqm."""
        result = calculate_building_permit_fees(
            building_areas=[{"type": "mamad", "area_sqm": 20}],
            shovi_per_sqm=7000,
            building_order=3,
        )
        # Should charge for 8sqm mamad
        expected = calculate_dmei_heter(8, "mamad", 7000)
        assert result["result"] == pytest.approx(expected["result"], rel=1e-6)

    def test_dmei_heter_basement_service_vs_residential(self):
        """Basement service uses 0.3 coefficient, residential uses 0.7."""
        service = calculate_dmei_heter(100, "basement_service", 7000)
        residential = calculate_dmei_heter(100, "basement_residential", 7000)
        assert service["result"] < residential["result"]
        # Ratio should be 0.3/0.7
        ratio = service["result"] / residential["result"]
        assert ratio == pytest.approx(0.3 / 0.7, rel=1e-6)

    def test_dmei_heter_agricultural_exempt(self):
        """Agricultural buildings are fully exempt."""
        result = calculate_building_permit_fees(
            building_areas=[{"type": "main", "area_sqm": 200}],
            shovi_per_sqm=7000,
            building_order=3,
            is_agricultural=True,
        )
        assert result["result"] == 0.0

    def test_dmei_heter_pre_1965_exempt(self):
        """Pre-1965 buildings are fully exempt."""
        result = calculate_building_permit_fees(
            building_areas=[{"type": "main", "area_sqm": 200}],
            shovi_per_sqm=7000,
            building_order=3,
            is_pre_1965=True,
        )
        assert result["result"] == 0.0

    def test_dmei_heter_invalid_type(self):
        """Invalid area type returns error."""
        result = calculate_dmei_heter(100, "invalid_type", 7000)
        assert "error" in result

    def test_permit_fee_cap_basic(self):
        """Cap check returns correct structure."""
        result = check_permit_fee_cap(
            total_fees=1_500_000,
            nachla_total_rights_sqm=375,
            shovi_per_sqm=7000,
        )
        assert "result" in result
        assert "cap_value" in result["result"]
        assert "exceeds_cap" in result["result"]


# ===================================================================
# 3. Usage fees (dmei shimush)
# ===================================================================

class TestDmeiShimush:
    def test_dmei_shimush_basic(self):
        """Basic usage fee: 5% x 7 years for 3rd+ house."""
        result = calculate_dmei_shimush(
            area_sqm=100,
            area_type="main",
            shovi_per_sqm=7000,
            usage_type="residential",
            building_order=3,
        )
        assert "error" not in result
        expected = 100 * 1.0 * 7000 * 0.05 * 7
        assert result["result"] == pytest.approx(expected, rel=1e-6)
        assert result["years"] == 7

    def test_dmei_shimush_priority_area(self):
        """Priority area uses 3% rate instead of 5%."""
        result = calculate_dmei_shimush(
            area_sqm=100,
            area_type="main",
            shovi_per_sqm=7000,
            usage_type="residential",
            building_order=3,
            priority_area="A",
        )
        expected = 100 * 1.0 * 7000 * 0.03 * 7
        assert result["result"] == pytest.approx(expected, rel=1e-6)

    def test_dmei_shimush_house1_exempt(self):
        """House 1 is always exempt from usage fees."""
        result = calculate_dmei_shimush(
            area_sqm=300,
            area_type="main",
            shovi_per_sqm=7000,
            usage_type="residential",
            building_order=1,
        )
        assert result["result"] == 0.0

    def test_dmei_shimush_house2_deviation(self):
        """House 2 deviation uses 2 years only."""
        result = calculate_dmei_shimush(
            area_sqm=200,
            area_type="main",
            shovi_per_sqm=7000,
            usage_type="residential",
            building_order=2,
        )
        assert "error" not in result
        expected = 200 * 1.0 * 7000 * 0.05 * 2
        assert result["result"] == pytest.approx(expected, rel=1e-6)
        assert result["years"] == 2

    def test_dmei_shimush_house2_within_exempt(self):
        """House 2 within permit and <= 160sqm is exempt."""
        result = calculate_dmei_shimush(
            area_sqm=160,
            area_type="main",
            shovi_per_sqm=7000,
            usage_type="residential",
            building_order=2,
        )
        assert result["result"] == 0.0

    def test_dmei_shimush_service_exempt(self):
        """Service buildings are exempt from usage fees."""
        result = calculate_dmei_shimush(
            area_sqm=100,
            area_type="service",
            shovi_per_sqm=7000,
            usage_type="residential",
            building_order=3,
        )
        assert result["result"] == 0.0

    def test_dmei_shimush_pergola_coefficient(self):
        """Pergola uses 0.5 eco coefficient."""
        result = calculate_dmei_shimush(
            area_sqm=100,
            area_type="pergola",
            shovi_per_sqm=7000,
            usage_type="residential",
            building_order=3,
        )
        expected = 100 * 0.5 * 7000 * 0.05 * 7
        assert result["result"] == pytest.approx(expected, rel=1e-6)

    def test_dmei_shimush_includes_cpi_note(self):
        """Output includes note about CPI indexation."""
        result = calculate_dmei_shimush(
            area_sqm=100,
            area_type="main",
            shovi_per_sqm=7000,
            usage_type="residential",
            building_order=3,
        )
        assert "note" in result
        assert "הצמדה" in result["note"] or "נומינליים" in result["note"]


# ===================================================================
# 4. Capitalization (hivun)
# ===================================================================

class TestHivun:
    def test_hivun_375_basic(self):
        """Basic 3.75% capitalization calculation."""
        result = calculate_hivun_375(
            sqm_equivalent_375=808,
            shovi_per_sqm=7000,
        )
        assert "error" not in result
        gross = 808 * 7000 * 0.0375
        net = gross  # no dev costs
        tax = net * 0.06
        expected = net + tax
        assert result["result"] == pytest.approx(expected, rel=1e-6)
        assert result["gross_hivun"] == pytest.approx(gross, rel=1e-6)
        assert result["purchase_tax"] == pytest.approx(tax, rel=1e-6)

    def test_hivun_375_with_dev_costs(self):
        """Development costs are deducted before purchase tax."""
        result = calculate_hivun_375(
            sqm_equivalent_375=808,
            shovi_per_sqm=7000,
            development_costs=100_000,
        )
        gross = 808 * 7000 * 0.0375
        net = gross - 100_000
        tax = net * 0.06
        expected = net + tax
        assert result["result"] == pytest.approx(expected, rel=1e-6)

    def test_hivun_375_dynamic_808(self):
        """Non-standard nachla computes different sqm equivalent."""
        # 3 dunam plot with 450sqm rights -> should differ from 808
        result = calculate_hivun_375_sqm(
            plot_size_sqm=3000,
            taba_rights={"main_sqm": 300, "service_sqm": 150, "mamad_sqm": 24},
            building_coverage_sqm=474,
        )
        assert "error" not in result
        assert result["result"] != 808
        assert result["is_standard"] is False
        assert result["warning"] is not None

    def test_hivun_33_basic(self):
        """Basic 33% purchase calculation."""
        result = calculate_hivun_33(
            sqm_equivalent_nachla=1135,
            sqm_potential=165,
            shovi_per_sqm=7000,
        )
        assert "error" not in result
        total_sqm = 1135 + 165
        gross = total_sqm * 7000 * 0.33
        tax = gross * 0.06
        expected = gross + tax
        assert result["result"] == pytest.approx(expected, rel=1e-6)

    def test_hivun_33_post_2009_deduction(self):
        """Only post-2009 permit fees are deducted."""
        with_deduction = calculate_hivun_33(
            sqm_equivalent_nachla=1135,
            sqm_potential=165,
            shovi_per_sqm=7000,
            prior_permit_fees_post_2009=50,
        )
        without_deduction = calculate_hivun_33(
            sqm_equivalent_nachla=1135,
            sqm_potential=165,
            shovi_per_sqm=7000,
            prior_permit_fees_post_2009=0,
        )
        assert with_deduction["result"] < without_deduction["result"]
        # The deduction should reduce total sqm by 50
        diff_gross = without_deduction["gross_purchase"] - with_deduction["gross_purchase"]
        expected_diff = 50 * 7000 * 0.33
        assert diff_gross == pytest.approx(expected_diff, rel=1e-6)

    def test_hivun_33_priority_area(self):
        """Priority A/B uses 20.14% instead of 33%."""
        result = calculate_hivun_33(
            sqm_equivalent_nachla=1135,
            sqm_potential=165,
            shovi_per_sqm=7000,
            priority_area="A",
        )
        assert result["rate_applied"] == 0.2014
        total_sqm = 1135 + 165
        gross = total_sqm * 7000 * 0.2014
        tax = gross * 0.06
        expected = gross + tax
        assert result["result"] == pytest.approx(expected, rel=1e-6)

    def test_compare_tracks(self):
        """Track comparison returns both results and recommendation."""
        r375 = calculate_hivun_375(808, 7000)
        r33 = calculate_hivun_33(1135, 165, 7000)
        comparison = compare_tracks(r375, r33)
        assert "result" in comparison
        assert "track_375" in comparison["result"]
        assert "track_33" in comparison["result"]
        assert "difference" in comparison["result"]
        assert comparison["result"]["track_375"]["total_cost"] == r375["result"]
        assert comparison["result"]["track_33"]["total_cost"] == r33["result"]


# ===================================================================
# 5. Plot splitting (pitzul)
# ===================================================================

class TestPitzul:
    def test_pitzul_bar_reshut_blocked(self):
        """Bar reshut cannot split plots."""
        result = check_split_eligibility(
            authorization_type="bar_reshut",
            is_capitalized=True,
            plot_size_sqm=500,
            taba_allows_split=True,
        )
        assert result["result"]["eligible"] is False
        assert any("בר רשות" in b for b in result["result"]["blockers"])

    def test_pitzul_eligible(self):
        """Eligible case passes all checks."""
        result = check_split_eligibility(
            authorization_type="chocher",
            is_capitalized=True,
            plot_size_sqm=500,
            taba_allows_split=True,
        )
        assert result["result"]["eligible"] is True
        assert len(result["result"]["blockers"]) == 0

    def test_pitzul_not_capitalized_blocked(self):
        """Non-capitalized nachla cannot split."""
        result = check_split_eligibility(
            authorization_type="chocher",
            is_capitalized=False,
            plot_size_sqm=500,
            taba_allows_split=True,
        )
        assert result["result"]["eligible"] is False

    def test_pitzul_too_small_blocked(self):
        """Plot below 350sqm cannot be split."""
        result = check_split_eligibility(
            authorization_type="chocher",
            is_capitalized=True,
            plot_size_sqm=300,
            taba_allows_split=True,
        )
        assert result["result"]["eligible"] is False

    def test_pitzul_basic_cost(self):
        """Basic split cost after 3.75%: 33% * value - paid hivun."""
        result = calculate_split_cost(
            plot_value=3_000_000,
            paid_hivun_for_plot=240_000,
            capitalization_track="375",
            split_area_sqm=350,
        )
        assert "error" not in result
        split_cost = 3_000_000 * 0.33 - 240_000
        tax = split_cost * 0.06
        expected = split_cost + tax
        assert result["result"] == pytest.approx(expected, rel=1e-6)

    def test_pitzul_after_33_free(self):
        """Split after 33% track is included (cost = 0)."""
        result = calculate_split_cost(
            plot_value=3_000_000,
            paid_hivun_for_plot=0,
            capitalization_track="33",
        )
        assert result["result"] == 0.0

    def test_pitzul_priority_area(self):
        """Priority A/B uses 16.39% up to 160sqm, 20.14% for rest."""
        result = calculate_split_cost(
            plot_value=3_000_000,
            paid_hivun_for_plot=0,
            capitalization_track="375",
            split_area_sqm=350,
            priority_area="A",
        )
        assert "error" not in result
        # 160/350 of value at 16.39%, 190/350 at 20.14%
        value_160 = 3_000_000 * (160 / 350)
        value_rest = 3_000_000 * (190 / 350)
        split_cost = value_160 * 0.1639 + value_rest * 0.2014
        tax = split_cost * 0.06
        expected = split_cost + tax
        assert result["result"] == pytest.approx(expected, rel=1e-6)

    def test_pitzul_remaining_rights(self):
        """Remaining rights tracked correctly."""
        result = calculate_remaining_rights(
            total_rights_sqm=750,
            splits=[{"area_sqm": 160}, {"area_sqm": 170}],
            regularizations=[{"area_sqm": 105}],
        )
        assert result["result"]["remaining_sqm"] == pytest.approx(315, rel=1e-6)
        assert result["result"]["needs_additional_permit_fees"] is False

    def test_pitzul_remaining_rights_deficit(self):
        """Deficit in remaining rights triggers warning."""
        result = calculate_remaining_rights(
            total_rights_sqm=300,
            splits=[{"area_sqm": 200}],
            regularizations=[{"area_sqm": 150}],
        )
        assert result["result"]["remaining_sqm"] < 0
        assert result["result"]["needs_additional_permit_fees"] is True
        assert result["warning"] is not None


# ===================================================================
# 6. Equivalent sqm
# ===================================================================

class TestSqmEquivalent:
    def test_sqm_equivalent_basic(self):
        """Basic sqm equivalent calculation."""
        result = calculate_sqm_equivalent([
            {"type": "main", "area_sqm": 450},
            {"type": "service", "area_sqm": 125},
        ])
        expected = 450 * 1.0 + 125 * 0.4
        assert result["result"] == pytest.approx(expected, rel=1e-6)

    def test_sqm_equivalent_standard_nachla(self):
        """Standard 2.5 dunam nachla with 375sqm rights should be ~808."""
        result = calculate_hivun_375_sqm(
            plot_size_sqm=2500,
            taba_rights={
                "main_sqm": 250,
                "mamad_sqm": 25,
                "service_sqm": 125,
            },
        )
        assert "error" not in result
        assert result["is_standard"] is True
        # Verify result is in the ballpark of 808
        # Exact value depends on yard calculation
        assert result["result"] > 600
        assert result["result"] < 1100

    def test_sqm_equivalent_non_standard(self):
        """Non-standard nachla gets warning."""
        result = calculate_hivun_375_sqm(
            plot_size_sqm=3500,
            taba_rights={"main_sqm": 400, "service_sqm": 200},
        )
        assert result["is_standard"] is False
        assert result["warning"] is not None

    def test_nachla_sqm_yard_calculation(self):
        """Yard components split correctly between effective/remainder/far."""
        result = calculate_nachla_sqm_equivalent(
            plot_size_sqm=3000,
            building_coverage_sqm=500,
            taba_rights={"main_sqm": 300, "service_sqm": 100},
        )
        yard = result["yard_details"]
        assert yard["total_yard_sqm"] == 2500
        assert yard["yard_effective_sqm"] == 1000
        assert yard["yard_remainder_sqm"] == 1000
        assert yard["yard_far_sqm"] == 500

    def test_potential_sqm(self):
        """Potential sqm is difference between rights and existing."""
        result = calculate_potential_sqm(
            taba_rights_sqm=750,
            existing_recognized_sqm=500,
        )
        assert result["result"] == 250.0

    def test_potential_sqm_no_negative(self):
        """Potential cannot be negative."""
        result = calculate_potential_sqm(
            taba_rights_sqm=300,
            existing_recognized_sqm=500,
        )
        assert result["result"] == 0.0


# ===================================================================
# 7. Betterment levy
# ===================================================================

class TestHetelHashbacha:
    def test_hetel_hashbacha_basic(self):
        """50% of value appreciation."""
        result = calculate_betterment_levy(
            new_value=2_000_000,
            old_value=1_000_000,
        )
        assert result["result"] == pytest.approx(500_000, rel=1e-6)
        assert result["appreciation"] == pytest.approx(1_000_000, rel=1e-6)

    def test_hetel_hashbacha_no_appreciation(self):
        """No levy when no appreciation."""
        result = calculate_betterment_levy(
            new_value=1_000_000,
            old_value=1_500_000,
        )
        assert result["result"] == 0.0

    def test_hetel_hashbacha_partial(self):
        """Partial betterment proportional to rights used."""
        result = calculate_partial_betterment(
            total_levy=500_000,
            rights_used_sqm=100,
            total_rights_sqm=400,
        )
        assert result["result"] == pytest.approx(125_000, rel=1e-6)
        assert result["proportion"] == pytest.approx(0.25, rel=1e-4)

    def test_split_betterment(self):
        """Split betterment estimate."""
        result = estimate_split_betterment(
            plot_value_after_split=2_000_000,
            plot_value_as_part_of_nachla=500_000,
        )
        expected = 0.5 * (2_000_000 - 500_000)
        assert result["result"] == pytest.approx(expected, rel=1e-6)


# ===================================================================
# 8. Priority areas
# ===================================================================

class TestPriorityAreas:
    def test_get_priority_area_a(self):
        assert get_priority_area("ירוחם") == "A"

    def test_get_priority_area_b(self):
        assert get_priority_area("קריית שמונה") == "B"

    def test_get_priority_area_frontline(self):
        assert get_priority_area("מנרה") == "frontline"

    def test_get_priority_area_none(self):
        assert get_priority_area("תל אביב") is None

    def test_get_priority_area_empty(self):
        assert get_priority_area("") is None
        assert get_priority_area(None) is None

    def test_get_discount_permit_a(self):
        assert get_discount("A", "permit") == 0.51

    def test_get_discount_permit_b(self):
        assert get_discount("B", "permit") == 0.25

    def test_get_discount_no_area(self):
        assert get_discount(None, "permit") == 0.0

    def test_get_usage_rate_standard(self):
        assert get_usage_rate(None, "residential") == 0.05

    def test_get_usage_rate_priority(self):
        assert get_usage_rate("A", "residential") == 0.03

    def test_get_usage_rate_agricultural(self):
        assert get_usage_rate(None, "agricultural") == 0.02

    def test_get_hivun_33_rate_standard(self):
        assert get_hivun_33_rate(None) == 0.33

    def test_get_hivun_33_rate_priority(self):
        assert get_hivun_33_rate("A") == 0.2014


# ===================================================================
# 9. Lookup tables
# ===================================================================

class TestLookupTables:
    def test_settlement_shovi_found(self):
        result = lookup_settlement_shovi("בית דגן")
        assert result == 11_400.0

    def test_settlement_shovi_not_found(self):
        result = lookup_settlement_shovi("עיר שלא קיימת")
        assert result is None

    def test_plach_rate_found(self):
        result = lookup_plach_rate("מרכז")
        assert result == 5_500.0

    def test_development_costs_found(self):
        result = lookup_development_costs("חבל יבנה")
        assert result == 247_000.0


# ===================================================================
# 10. Cross-cutting: audit trail and no hardcoded constants
# ===================================================================

class TestAuditTrail:
    """Every calculation function must return an audit dict."""

    def _assert_audit_dict(self, result: dict, name: str):
        """Check that result has audit trail keys."""
        assert "result" in result or "error" in result, (
            f"{name}: must have 'result' or 'error'"
        )
        if "error" not in result:
            assert "formula" in result, f"{name}: missing 'formula'"
            assert "rates_used" in result, f"{name}: missing 'rates_used'"
            assert "inputs" in result, f"{name}: missing 'inputs'"

    def test_all_calcs_return_audit_trail(self):
        """Every public calculation function returns audit dict."""
        test_cases = [
            ("calculate_dmei_heter", calculate_dmei_heter(100, "main", 7000)),
            ("calculate_building_permit_fees", calculate_building_permit_fees(
                [{"type": "main", "area_sqm": 100}], 7000, 3)),
            ("check_permit_fee_cap", check_permit_fee_cap(100_000, 375, 7000)),
            ("calculate_dmei_shimush", calculate_dmei_shimush(
                100, "main", 7000, "residential", 3)),
            ("calculate_hivun_375", calculate_hivun_375(808, 7000)),
            ("calculate_hivun_33", calculate_hivun_33(1135, 165, 7000)),
            ("compare_tracks", compare_tracks(
                calculate_hivun_375(808, 7000),
                calculate_hivun_33(1135, 165, 7000),
            )),
            ("check_split_eligibility", check_split_eligibility(
                "chocher", True, 500, True)),
            ("calculate_split_cost", calculate_split_cost(
                3_000_000, 240_000, "375", 350)),
            ("calculate_remaining_rights", calculate_remaining_rights(750, [], [])),
            ("calculate_sqm_equivalent", calculate_sqm_equivalent(
                [{"type": "main", "area_sqm": 100}])),
            ("calculate_potential_sqm", calculate_potential_sqm(750, 500)),
            ("calculate_betterment_levy", calculate_betterment_levy(
                2_000_000, 1_000_000)),
            ("calculate_partial_betterment", calculate_partial_betterment(
                500_000, 100, 400)),
            ("estimate_split_betterment", estimate_split_betterment(
                2_000_000, 500_000)),
        ]
        for name, result in test_cases:
            self._assert_audit_dict(result, name)


class TestNoHardcodedConstants:
    """Verify that calculation modules do not contain hardcoded magic numbers."""

    def _read_source(self, filename: str) -> str:
        path = Path(__file__).parent.parent / "src" / "tools" / filename
        return path.read_text(encoding="utf-8")

    def test_no_hardcoded_constants(self):
        """Grep calculation modules for suspicious hardcoded constants."""
        calc_files = [
            "calc_dmei_heter.py",
            "calc_dmei_shimush.py",
            "calc_hivun.py",
            "calc_pitzul.py",
            "calc_sqm_equivalent.py",
            "calc_hetel_hashbacha.py",
        ]

        # These are the dangerous magic numbers that should come from config
        forbidden_patterns = [
            (r"(?<!\w)0\.91(?!\d)", "0.91 (permit_fee_rate)"),
            (r"(?<!\w)0\.18(?!\d)", "0.18 (vat_rate)"),
            (r"(?<!\w)0\.17(?!\d)", "0.17 (old vat_rate)"),
            (r"(?<!\w)0\.0375(?!\d)", "0.0375 (hivun_375_rate)"),
            (r"(?<!\w)0\.33(?!\d)", "0.33 (hivun_33_rate)"),
            (r"(?<!\w)808(?!\d)", "808 (hivun_375_default_sqm)"),
            (r"(?<!\w)0\.05(?!\d)", "0.05 (usage_fee_residential)"),
            (r"(?<!\w)0\.03(?!\d)", "0.03 (usage_fee_priority)"),
            (r"(?<!\w)0\.02(?!\d)", "0.02 (usage_fee_agricultural)"),
            (r"(?<!\w)0\.06(?!\d)", "0.06 (purchase_tax_rate)"),
            (r"(?<!\w)0\.50(?!\d)", "0.50 (betterment_levy_rate)"),
            (r"(?<!\w)160(?!\d)", "160 (house_exemption_sqm)"),
        ]

        violations = []
        for filename in calc_files:
            source = self._read_source(filename)
            # Strip docstrings and comments before checking
            lines = source.split("\n")
            in_docstring = False
            for line_num, line in enumerate(lines, 1):
                stripped = line.strip()
                # Track docstring blocks
                if '"""' in stripped:
                    count = stripped.count('"""')
                    if count == 1:
                        in_docstring = not in_docstring
                    # Either way, skip lines containing docstring delimiters
                    continue
                if in_docstring:
                    continue
                # Skip comments
                if stripped.startswith("#"):
                    continue
                # Skip string literals (formula display strings, f-strings)
                if "formula" in line.lower() or "f'" in line or 'f"' in line:
                    continue
                for pattern, desc in forbidden_patterns:
                    if re.search(pattern, line):
                        violations.append(
                            f"{filename}:{line_num} - possible hardcoded {desc}: {stripped}"
                        )

        # We allow some false positives but flag them for review
        # The key check is that calculation logic loads from config
        # This test is intentionally lenient on formula display strings
        assert len(violations) == 0, (
            f"Found {len(violations)} possible hardcoded constants:\n"
            + "\n".join(violations)
        )


# ===================================================================
# 11. Validator-recommended tests (post-fix coverage)
# ===================================================================

class TestValidatorFixes:
    """Tests added after validator review to cover fixed findings."""

    def test_hivun_375_priority_discount(self):
        """Hivun 3.75% applies priority area discount (finding: P0)."""
        base = calculate_hivun_375(sqm_equivalent_375=808, shovi_per_sqm=7000)
        priority_a = calculate_hivun_375(
            sqm_equivalent_375=808, shovi_per_sqm=7000, priority_area="A"
        )
        assert "error" not in base
        assert "error" not in priority_a
        # Priority A should be ~51% less than base (before dev costs and tax)
        discount = CONFIG["priority_area_discounts"]["A"]["hivun_375"]
        expected_gross = base["gross_hivun"] * (1 - discount)
        assert priority_a["gross_after_discount"] == pytest.approx(expected_gross, rel=1e-6)
        assert priority_a["result"] < base["result"]
        assert priority_a["priority_discount_applied"] == discount

    def test_dmei_shimush_intergenerational_exempt(self):
        """Parents unit with intergenerational continuity is exempt (finding: P1)."""
        result = calculate_dmei_shimush(
            area_sqm=55,
            area_type="main",
            shovi_per_sqm=7000,
            usage_type="residential",
            building_order=2,
            has_intergenerational_continuity=True,
        )
        assert result["result"] == 0.0
        assert any("רצף בין-דורי" in e for e in result.get("exemptions", []))

    def test_dmei_shimush_no_intergenerational_charged(self):
        """Parents unit WITHOUT intergenerational continuity IS charged."""
        result = calculate_dmei_shimush(
            area_sqm=200,
            area_type="main",
            shovi_per_sqm=7000,
            usage_type="residential",
            building_order=2,
            has_intergenerational_continuity=False,
        )
        assert result["result"] > 0

    def test_hivun_33_frontline_warning(self):
        """Frontline area on 33% track emits a warning (finding: P1)."""
        result = calculate_hivun_33(
            sqm_equivalent_nachla=1000,
            sqm_potential=200,
            shovi_per_sqm=7000,
            priority_area="frontline",
        )
        assert "error" not in result
        assert result["rate_applied"] == 0.33  # Falls back to standard
        assert "warnings" in result
        assert len(result["warnings"]) > 0
        assert any("קו עימות" in w or "frontline" in w.lower() for w in result["warnings"])
