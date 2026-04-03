"""Usage fee (dmei shimush) calculations for Israeli RMI.

All constants loaded from rates_config.json. Never hardcoded.
Every function returns an audit dict with: result, formula, rates_used, inputs.
"""

import json
from pathlib import Path


def _load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "rates_config.json"
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def calculate_dmei_shimush(
    area_sqm: float,
    area_type: str,
    shovi_per_sqm: float,
    usage_type: str,
    building_order: int,
    has_intergenerational_continuity: bool = False,
    priority_area: str | None = None,
    effective_date: str | None = None,
) -> dict:
    """Calculate usage fees for a building or deviation.

    Formula: area * eco_coefficient * shovi * usage_rate * years

    Args:
        area_sqm: Chargeable area in square meters.
        area_type: "main", "service", or "pergola".
        shovi_per_sqm: Equivalent sqm value in ILS.
        usage_type: "residential", "agricultural", or "plach".
        building_order: 1=first house, 2=second, 3+=third.
        has_intergenerational_continuity: True if parents unit with
            intergenerational continuity (affects exemption).
        priority_area: "A", "B", "frontline", or None.
        effective_date: Optional date string.

    Returns:
        Audit dict with result, formula, rates_used, inputs.
    """
    config = _load_config()

    inputs = {
        "area_sqm": area_sqm,
        "area_type": area_type,
        "shovi_per_sqm": shovi_per_sqm,
        "usage_type": usage_type,
        "building_order": building_order,
        "has_intergenerational_continuity": has_intergenerational_continuity,
        "priority_area": priority_area,
    }

    # --- Input validation ---
    eco_coefficients = config["usage_fee_coefficients"]
    valid_types = [k for k in eco_coefficients if k not in ("effective_date", "expiry_date", "note")]

    if area_type not in valid_types:
        return {
            "error": f"סוג שטח לא חוקי: {area_type}. סוגים תקינים: {valid_types}",
            "inputs": inputs,
        }

    if area_sqm < 0:
        return {"error": "שטח לא יכול להיות שלילי", "inputs": inputs}

    if shovi_per_sqm <= 0:
        return {"error": "שווי למ\"ר חייב להיות חיובי", "inputs": inputs}

    valid_usage = ("residential", "agricultural", "plach")
    if usage_type not in valid_usage:
        return {
            "error": f"סוג שימוש לא חוקי: {usage_type}. סוגים תקינים: {list(valid_usage)}",
            "inputs": inputs,
        }

    # --- Exemption checks ---
    exemptions: list[str] = []

    # House 1: always exempt (even with deviation)
    if building_order == 1:
        return {
            "result": 0.0,
            "exemptions": ["בית ראשון - פטור מדמי שימוש (גם אם יש חריגה)"],
            "formula": "house 1 - exempt",
            "rates_used": {},
            "inputs": inputs,
            "note": "הסכומים נומינליים. בפועל ייתכנו הצמדה למדד וריבית פיגורים.",
        }

    # Parents unit with intergenerational continuity: exempt
    # Per workflow step 4.1: parents unit charged only if NO intergenerational continuity
    if has_intergenerational_continuity and building_order == 2:
        return {
            "result": 0.0,
            "exemptions": ["יחידת הורים עם רצף בין-דורי - פטור מדמי שימוש"],
            "formula": "parents unit with intergenerational continuity - exempt",
            "rates_used": {},
            "inputs": inputs,
        }

    # Agricultural buildings: exempt
    if usage_type == "agricultural" and area_type != "main":
        return {
            "result": 0.0,
            "exemptions": ["מבנה חקלאי - פטור מדמי שימוש"],
            "formula": "agricultural building - exempt",
            "rates_used": {},
            "inputs": inputs,
        }

    # Service buildings: exempt from usage fees
    if area_type == "service":
        return {
            "result": 0.0,
            "exemptions": ["מבנה שירות - פטור מדמי שימוש"],
            "formula": "service building - exempt",
            "rates_used": {},
            "inputs": inputs,
        }

    # House 2 within permit and <= 160sqm: exempt
    house_exemption_sqm = float(config["house_exemption_sqm"]["value"])
    if building_order == 2 and area_sqm <= house_exemption_sqm:
        exemptions.append(
            f"בית שני בתוך היתר ועד {house_exemption_sqm} מ\"ר - פטור"
        )
        return {
            "result": 0.0,
            "exemptions": exemptions,
            "formula": "house 2 within permit and <= exemption threshold - exempt",
            "rates_used": {"house_exemption_sqm": house_exemption_sqm},
            "inputs": inputs,
        }

    # --- Calculate usage fee ---
    eco_coeff = float(eco_coefficients[area_type])

    # Determine usage rate
    if priority_area in ("A", "B", "frontline") and usage_type == "residential":
        usage_rate = float(config["usage_fee_priority"]["value"])
    elif usage_type == "agricultural":
        usage_rate = float(config["usage_fee_agricultural"]["value"])
    elif usage_type == "plach":
        usage_rate = float(config["usage_fee_plach"]["value"])
    else:
        usage_rate = float(config["usage_fee_residential"]["value"])

    # Determine period (years)
    if building_order == 2:
        years = int(config["usage_period_2nd_house_years"]["value"])
    else:
        years = int(config["usage_period_3rd_plus_years"]["value"])

    annual_fee = area_sqm * eco_coeff * shovi_per_sqm * usage_rate
    total_fee = annual_fee * years

    formula_str = (
        f"{area_sqm} * {eco_coeff} * {shovi_per_sqm} * {usage_rate} * {years}"
    )

    return {
        "result": round(total_fee, 2),
        "annual_fee": round(annual_fee, 2),
        "years": years,
        "exemptions": exemptions,
        "formula": formula_str,
        "rates_used": {
            "eco_coefficient": eco_coeff,
            "usage_rate": usage_rate,
            "years": years,
            "priority_area": priority_area,
            "effective_date": effective_date or "current",
        },
        "inputs": inputs,
        "note": "הסכומים נומינליים. בפועל ייתכנו הצמדה למדד וריבית פיגורים (יכולים להוסיף 20-40%).",
    }
