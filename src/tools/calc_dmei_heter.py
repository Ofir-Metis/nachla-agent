"""Permit fee (dmei heter) calculations for Israeli RMI.

All constants loaded from rates_config.json. Never hardcoded.
Every function returns an audit dict with: result, formula, rates_used, inputs.
"""

import json
from pathlib import Path

from tools.exceptions import CalculationInputError


def _load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "rates_config.json"
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def calculate_dmei_heter(
    area_sqm: float,
    area_type: str,
    shovi_per_sqm: float,
    priority_area: str | None = None,
    effective_date: str | None = None,
) -> dict:
    """Calculate permit fees for a single area component.

    Formula: area_sqm * coefficient * shovi_per_sqm * permit_rate * (1 + vat)
    Then apply priority area discount on the total.

    Args:
        area_sqm: Area in square meters.
        area_type: One of "main", "service", "pool", "basement_service",
                   "basement_residential", "mamad".
        shovi_per_sqm: Equivalent sqm value in ILS.
        priority_area: "A", "B", "frontline", or None.
        effective_date: Optional date string for rate lookup.

    Returns:
        Audit dict with result, formula, rates_used, inputs.
    """
    config = _load_config()

    coefficients = config["permit_fee_coefficients"]
    valid_types = [k for k in coefficients if k not in ("effective_date", "expiry_date", "note")]

    if area_type not in valid_types:
        raise CalculationInputError(
            f"סוג שטח לא חוקי: {area_type}. סוגים תקינים: {valid_types}"
        )

    if area_sqm < 0:
        raise CalculationInputError("שטח לא יכול להיות שלילי")

    if shovi_per_sqm <= 0:
        raise CalculationInputError("שווי למ\"ר חייב להיות חיובי")

    coefficient = float(coefficients[area_type])
    permit_rate = float(config["permit_fee_rate"]["value"])
    vat_rate = float(config["vat_rate"]["value"])

    cost_before_discount = area_sqm * coefficient * shovi_per_sqm * permit_rate * (1 + vat_rate)

    # Priority area discount on permit fees
    discount_pct = 0.0
    if priority_area:
        discounts = config.get("priority_area_discounts", {})
        area_discounts = discounts.get(priority_area, {})
        if isinstance(area_discounts, dict):
            raw = area_discounts.get("permit")
            if raw is not None:
                discount_pct = float(raw)

    cost_after_discount = cost_before_discount * (1 - discount_pct)

    formula_str = (
        f"{area_sqm} * {coefficient} * {shovi_per_sqm} * {permit_rate} * (1 + {vat_rate})"
    )
    if discount_pct > 0:
        formula_str += f" * (1 - {discount_pct})"

    return {
        "result": round(cost_after_discount, 2),
        "result_before_discount": round(cost_before_discount, 2),
        "formula": formula_str,
        "rates_used": {
            "coefficient": coefficient,
            "permit_rate": permit_rate,
            "vat_rate": vat_rate,
            "priority_discount": discount_pct,
            "effective_date": effective_date or "current",
        },
        "inputs": {
            "area_sqm": area_sqm,
            "area_type": area_type,
            "shovi_per_sqm": shovi_per_sqm,
            "priority_area": priority_area,
        },
    }


def calculate_building_permit_fees(
    building_areas: list[dict],
    shovi_per_sqm: float,
    building_order: int,
    is_agricultural: bool = False,
    is_pre_1965: bool = False,
    permit_size_sqm: float | None = None,
    priority_area: str | None = None,
    effective_date: str | None = None,
) -> dict:
    """Calculate total permit fees for one building, handling exemptions.

    Args:
        building_areas: List of dicts, each with "type" and "area_sqm".
                        e.g. [{"type": "main", "area_sqm": 200}, {"type": "mamad", "area_sqm": 14}]
        shovi_per_sqm: Equivalent sqm value in ILS.
        building_order: 1 = first house, 2 = second, 3+ = third etc.
        is_agricultural: True if agricultural building (fully exempt).
        is_pre_1965: True if built before 1965 (fully exempt).
        permit_size_sqm: Existing permit size in sqm (for exemption calc).
        priority_area: "A", "B", "frontline", or None.
        effective_date: Optional date string.

    Returns:
        Audit dict with total result, per-component breakdown, exemptions applied.
    """
    config = _load_config()
    house_exemption = float(config["house_exemption_sqm"]["value"])
    mamad_exemption = float(config["mamad_exemption_sqm"]["value"])

    inputs = {
        "building_areas": building_areas,
        "shovi_per_sqm": shovi_per_sqm,
        "building_order": building_order,
        "is_agricultural": is_agricultural,
        "is_pre_1965": is_pre_1965,
        "permit_size_sqm": permit_size_sqm,
        "priority_area": priority_area,
    }

    # Full exemptions
    if is_agricultural:
        return {
            "result": 0.0,
            "components": [],
            "exemptions": ["מבנה חקלאי - פטור מלא מדמי היתר"],
            "formula": "agricultural building - fully exempt",
            "rates_used": {},
            "inputs": inputs,
        }

    if is_pre_1965:
        return {
            "result": 0.0,
            "components": [],
            "exemptions": ["מבנה לפני 1965 - פטור מדמי היתר"],
            "formula": "pre-1965 building - fully exempt",
            "rates_used": {},
            "inputs": inputs,
        }

    exemptions: list[str] = []
    components: list[dict] = []
    total = 0.0
    mamad_exemption_used = False

    # Determine main area exemption for houses 1 and 2
    main_exempt_sqm = 0.0
    if building_order in (1, 2):
        # Exempt up to 160sqm or permit size, whichever is higher
        base_exempt = house_exemption
        if permit_size_sqm is not None and permit_size_sqm > base_exempt:
            base_exempt = permit_size_sqm
        main_exempt_sqm = base_exempt
        exemptions.append(
            f"בית {building_order} - פטור עד {main_exempt_sqm} מ\"ר שטח עיקרי"
        )

    for area in building_areas:
        area_type = area.get("type", "")
        area_sqm = float(area.get("area_sqm", 0))

        chargeable_sqm = area_sqm

        # Apply main area exemption
        if area_type == "main" and main_exempt_sqm > 0:
            chargeable_sqm = max(0.0, area_sqm - main_exempt_sqm)
            main_exempt_sqm = max(0.0, main_exempt_sqm - area_sqm)

        # Apply mamad exemption (first mamad per house only)
        if area_type == "mamad" and not mamad_exemption_used:
            exempt = min(mamad_exemption, area_sqm)
            chargeable_sqm = max(0.0, area_sqm - exempt)
            mamad_exemption_used = True
            exemptions.append(f"ממ\"ד ראשון - פטור עד {mamad_exemption} מ\"ר")

        if chargeable_sqm <= 0:
            components.append({
                "type": area_type,
                "original_sqm": area_sqm,
                "chargeable_sqm": 0.0,
                "cost": 0.0,
                "note": "exempt",
            })
            continue

        calc = calculate_dmei_heter(
            area_sqm=chargeable_sqm,
            area_type=area_type,
            shovi_per_sqm=shovi_per_sqm,
            priority_area=priority_area,
            effective_date=effective_date,
        )

        if "error" in calc:
            components.append({
                "type": area_type,
                "original_sqm": area_sqm,
                "chargeable_sqm": chargeable_sqm,
                "error": calc["error"],
            })
            continue

        cost = calc["result"]
        total += cost
        components.append({
            "type": area_type,
            "original_sqm": area_sqm,
            "chargeable_sqm": chargeable_sqm,
            "cost": round(cost, 2),
            "formula": calc["formula"],
        })

    return {
        "result": round(total, 2),
        "components": components,
        "exemptions": exemptions,
        "formula": "sum of all chargeable components after exemptions",
        "rates_used": {
            "house_exemption_sqm": float(config["house_exemption_sqm"]["value"]),
            "mamad_exemption_sqm": float(config["mamad_exemption_sqm"]["value"]),
            "permit_rate": float(config["permit_fee_rate"]["value"]),
            "vat_rate": float(config["vat_rate"]["value"]),
            "priority_area": priority_area,
        },
        "inputs": inputs,
    }


def check_permit_fee_cap(
    total_fees: float,
    nachla_total_rights_sqm: float | None = None,
    shovi_per_sqm: float | None = None,
    priority_area: str | None = None,
    num_housing_units: int = 1,
    effective_date: str | None = None,
) -> dict:
    """Check if total permit fees exceed the decision 1523/1553 cap.

    Two cap mechanisms:
    1. Decision 1523: cap = total_rights * shovi * permit_rate * (1+vat)
    2. Decision 1553: for priority areas, fixed caps per housing unit

    The lower of the two caps applies.

    Args:
        total_fees: Sum of all permit fees for the nachla.
        nachla_total_rights_sqm: Total taba rights (for 1523 cap calculation).
        shovi_per_sqm: Equivalent sqm value.
        priority_area: "A", "B", "frontline", or None.
        num_housing_units: Number of housing units (1 or 2).
        effective_date: Optional date string.

    Returns:
        Audit dict with cap check result.
    """
    config = _load_config()
    permit_rate = float(config["permit_fee_rate"]["value"])
    vat_rate = float(config["vat_rate"]["value"])

    cap_1523 = None
    cap_1553 = None
    effective_cap = None

    # Decision 1523 cap
    if nachla_total_rights_sqm is not None and shovi_per_sqm is not None:
        cap_1523 = nachla_total_rights_sqm * shovi_per_sqm * permit_rate * (1 + vat_rate)

    # Decision 1553 cap (priority areas only)
    if priority_area in ("A", "B", "frontline"):
        caps_1553 = config.get("decision_1553_caps", {})
        if num_housing_units >= 2:
            cap_1553 = float(caps_1553.get("priority_cap_two_units", 900000))
        else:
            cap_1553 = float(caps_1553.get("priority_cap_per_unit", 450000))

    # Determine effective cap (lowest applicable)
    caps = [c for c in (cap_1523, cap_1553) if c is not None]
    if caps:
        effective_cap = min(caps)

    exceeds_cap = effective_cap is not None and total_fees > effective_cap
    capped_fees = min(total_fees, effective_cap) if effective_cap is not None else total_fees

    if exceeds_cap:
        if effective_cap == cap_1553:
            recommendation = (
                f"סה\"כ דמי ההיתר חורגים מתקרת החלטה 1553 ({effective_cap:,.0f} ש\"ח). "
                "הסכום הוגבל לתקרה."
            )
        else:
            recommendation = (
                f"סה\"כ דמי ההיתר חורגים מתקרת החלטה 1523 ({effective_cap:,.0f} ש\"ח). "
                "יש לבדוק מול רמ\"י."
            )
    elif effective_cap is not None:
        recommendation = "דמי ההיתר בגבולות התקרה."
    else:
        recommendation = "לא ניתן לחשב תקרה - חסרים נתוני זכויות ושווי."

    return {
        "result": {
            "total_fees": round(total_fees, 2),
            "capped_fees": round(capped_fees, 2),
            "cap_1523": round(cap_1523, 2) if cap_1523 is not None else None,
            "cap_1553": round(cap_1553, 2) if cap_1553 is not None else None,
            "effective_cap": round(effective_cap, 2) if effective_cap is not None else None,
            "exceeds_cap": exceeds_cap,
            "recommendation": recommendation,
        },
        "formula": "effective_cap = min(decision_1523_cap, decision_1553_cap)",
        "rates_used": {
            "permit_rate": permit_rate,
            "vat_rate": vat_rate,
            "priority_area": priority_area,
            "num_housing_units": num_housing_units,
            "effective_date": effective_date or "current",
        },
        "inputs": {
            "total_fees": total_fees,
            "nachla_total_rights_sqm": nachla_total_rights_sqm,
            "shovi_per_sqm": shovi_per_sqm,
            "priority_area": priority_area,
            "num_housing_units": num_housing_units,
        },
    }
