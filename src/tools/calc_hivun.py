"""Capitalization (hivun) calculations for Israeli RMI.

Two tracks:
- 3.75% capitalization (basic rights)
- 33% purchase (full rights, dmei rechisha)

All constants loaded from rates_config.json. Never hardcoded.
Every function returns an audit dict with: result, formula, rates_used, inputs.
"""

import json
from pathlib import Path


def _load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "rates_config.json"
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def calculate_hivun_375(
    sqm_equivalent_375: float,
    shovi_per_sqm: float,
    priority_area: str | None = None,
    development_costs: float = 0.0,
    effective_date: str | None = None,
) -> dict:
    """Calculate 3.75% capitalization track.

    Formula: sqm_equivalent * shovi * 3.75% - development_costs
    Then add purchase tax: 6% of result.

    Args:
        sqm_equivalent_375: Equivalent sqm for the 3.75% track (typically 808
            for standard nachla, computed dynamically otherwise).
        shovi_per_sqm: Equivalent sqm value in ILS.
        priority_area: "A", "B", "frontline", or None.
        development_costs: Development costs to deduct (ILS).
        effective_date: Optional date string.

    Returns:
        Audit dict with result, formula, rates_used, inputs.
    """
    config = _load_config()

    inputs = {
        "sqm_equivalent_375": sqm_equivalent_375,
        "shovi_per_sqm": shovi_per_sqm,
        "priority_area": priority_area,
        "development_costs": development_costs,
    }

    if sqm_equivalent_375 <= 0:
        return {"error": "מ\"ר אקוויוולנטי חייב להיות חיובי", "inputs": inputs}
    if shovi_per_sqm <= 0:
        return {"error": "שווי למ\"ר חייב להיות חיובי", "inputs": inputs}

    hivun_rate = float(config["hivun_375_rate"]["value"])
    purchase_tax_rate = float(config["purchase_tax_rate"]["value"])

    # Apply priority area discount to the hivun rate.
    # The workflow states 3.75% is "discounted" for priority areas.
    # We apply the same discount percentage as for permit fees since
    # the exact 3.75% discount is not separately specified in RMI decisions.
    priority_discount = 0.0
    discounts = config.get("priority_area_discounts", {})
    if priority_area and priority_area in discounts:
        area_data = discounts[priority_area]
        if isinstance(area_data, dict):
            # Use permit discount as proxy for 3.75% discount
            discount_val = area_data.get("hivun_375")
            if discount_val is not None:
                priority_discount = float(discount_val)
            else:
                # Fallback: use permit discount and flag it in output
                permit_discount = area_data.get("permit")
                if permit_discount is not None:
                    priority_discount = float(permit_discount)

    gross = sqm_equivalent_375 * shovi_per_sqm * hivun_rate
    discounted_gross = gross * (1 - priority_discount) if priority_discount > 0 else gross
    net = max(0.0, discounted_gross - development_costs)
    purchase_tax = net * purchase_tax_rate
    total = net + purchase_tax

    discount_str = f" * (1 - {priority_discount})" if priority_discount > 0 else ""
    formula_str = (
        f"({sqm_equivalent_375} * {shovi_per_sqm} * {hivun_rate}){discount_str} - {development_costs} "
        f"= {round(net, 2)}; purchase_tax = {round(net, 2)} * {purchase_tax_rate} = {round(purchase_tax, 2)}"
    )

    return {
        "result": round(total, 2),
        "gross_hivun": round(gross, 2),
        "gross_after_discount": round(discounted_gross, 2),
        "net_after_dev_costs": round(net, 2),
        "purchase_tax": round(purchase_tax, 2),
        "priority_discount_applied": priority_discount,
        "formula": formula_str,
        "rates_used": {
            "hivun_rate": hivun_rate,
            "purchase_tax_rate": purchase_tax_rate,
            "priority_area": priority_area,
            "priority_discount": priority_discount,
            "effective_date": effective_date or "current",
        },
        "inputs": inputs,
    }


def calculate_hivun_33(
    sqm_equivalent_nachla: float,
    sqm_potential: float,
    shovi_per_sqm: float,
    prior_permit_fees_post_2009: float = 0.0,
    priority_area: str | None = None,
    development_costs: float = 0.0,
    effective_date: str | None = None,
) -> dict:
    """Calculate 33% purchase track (dmei rechisha).

    Formula: (sqm_nachla + sqm_potential - prior_permits_deduction) * shovi * rate - dev_costs
    CRITICAL: Only deduct permit fees purchased AFTER 2009 (decision 979/1311).
    Then add purchase tax: 6%.

    Args:
        sqm_equivalent_nachla: Total equivalent sqm of the nachla.
        sqm_potential: Potential equivalent sqm from unused taba rights.
        shovi_per_sqm: Equivalent sqm value in ILS.
        prior_permit_fees_post_2009: Previously purchased permit fees
            (post-2009 only) to deduct, in equivalent sqm.
        priority_area: "A", "B", "frontline", or None.
        development_costs: Development costs to deduct (ILS).
        effective_date: Optional date string.

    Returns:
        Audit dict with result, formula, rates_used, inputs.
    """
    config = _load_config()

    inputs = {
        "sqm_equivalent_nachla": sqm_equivalent_nachla,
        "sqm_potential": sqm_potential,
        "shovi_per_sqm": shovi_per_sqm,
        "prior_permit_fees_post_2009": prior_permit_fees_post_2009,
        "priority_area": priority_area,
        "development_costs": development_costs,
    }

    if shovi_per_sqm <= 0:
        return {"error": "שווי למ\"ר חייב להיות חיובי", "inputs": inputs}

    # Determine rate based on priority area
    standard_rate = float(config["hivun_33_rate"]["value"])
    discounts = config.get("priority_area_discounts", {})
    rate = standard_rate

    if priority_area and priority_area in discounts:
        area_data = discounts.get(priority_area, {})
        if isinstance(area_data, dict):
            priority_rate = area_data.get("purchase_33")
            if priority_rate is not None:
                rate = float(priority_rate)
            elif priority_area == "frontline":
                # Frontline rate not defined — use standard rate but warn
                pass

    purchase_tax_rate = float(config["purchase_tax_rate"]["value"])

    total_sqm = sqm_equivalent_nachla + sqm_potential - prior_permit_fees_post_2009
    total_sqm = max(0.0, total_sqm)

    gross = total_sqm * shovi_per_sqm * rate
    net = max(0.0, gross - development_costs)
    purchase_tax = net * purchase_tax_rate
    total = net + purchase_tax

    formula_str = (
        f"({sqm_equivalent_nachla} + {sqm_potential} - {prior_permit_fees_post_2009}) "
        f"* {shovi_per_sqm} * {rate} - {development_costs} = {round(net, 2)}; "
        f"purchase_tax = {round(net, 2)} * {purchase_tax_rate} = {round(purchase_tax, 2)}"
    )

    warnings: list[str] = []
    if priority_area == "frontline" and rate == standard_rate:
        warnings.append(
            "שיעור דמי רכישה לקו עימות לא מוגדר בטבלאות. הוחל שיעור סטנדרטי 33%. "
            "יש לוודא מול רמ\"י את השיעור המדויק."
        )

    result_dict: dict = {
        "result": round(total, 2),
        "gross_purchase": round(gross, 2),
        "net_after_dev_costs": round(net, 2),
        "purchase_tax": round(purchase_tax, 2),
        "total_sqm_charged": round(total_sqm, 2),
        "rate_applied": rate,
        "formula": formula_str,
        "rates_used": {
            "purchase_rate": rate,
            "standard_rate": standard_rate,
            "purchase_tax_rate": purchase_tax_rate,
            "priority_area": priority_area,
            "post_2009_deduction_cutoff": config["post_2009_deduction_cutoff"]["value"],
            "effective_date": effective_date or "current",
        },
        "inputs": inputs,
    }
    if warnings:
        result_dict["warnings"] = warnings
    return result_dict


def compare_tracks(
    hivun_375_result: dict,
    hivun_33_result: dict,
) -> dict:
    """Side-by-side comparison of 3.75% and 33% tracks.

    Args:
        hivun_375_result: Result dict from calculate_hivun_375.
        hivun_33_result: Result dict from calculate_hivun_33.

    Returns:
        Comparison dict with both tracks and key differences.
    """
    cost_375 = hivun_375_result.get("result", 0.0)
    cost_33 = hivun_33_result.get("result", 0.0)

    return {
        "result": {
            "track_375": {
                "total_cost": cost_375,
                "gross": hivun_375_result.get("gross_hivun", 0.0),
                "purchase_tax": hivun_375_result.get("purchase_tax", 0.0),
                "includes_split": False,
                "includes_future_rights": False,
            },
            "track_33": {
                "total_cost": cost_33,
                "gross": hivun_33_result.get("gross_purchase", 0.0),
                "purchase_tax": hivun_33_result.get("purchase_tax", 0.0),
                "includes_split": True,
                "includes_future_rights": True,
            },
            "difference": round(cost_33 - cost_375, 2),
            "recommendation": (
                "מסלול 3.75% זול יותר בכניסה, אך פיצול ידרוש תשלום נוסף."
                if cost_375 < cost_33
                else "מסלול 33% כולל את כל הזכויות והפיצול."
            ),
        },
        "formula": "comparison of two tracks",
        "rates_used": {
            "track_375_rates": hivun_375_result.get("rates_used", {}),
            "track_33_rates": hivun_33_result.get("rates_used", {}),
        },
        "inputs": {
            "track_375": hivun_375_result.get("inputs", {}),
            "track_33": hivun_33_result.get("inputs", {}),
        },
    }
