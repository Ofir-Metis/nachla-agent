"""Plot splitting (pitzul) calculations for Israeli RMI.

All constants loaded from rates_config.json. Never hardcoded.
Every function returns an audit dict with: result, formula, rates_used, inputs.
"""

import json
from pathlib import Path


def _load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "rates_config.json"
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def check_split_eligibility(
    authorization_type: str,
    is_capitalized: bool,
    plot_size_sqm: float,
    taba_allows_split: bool,
) -> dict:
    """Check whether a plot is eligible for splitting.

    Args:
        authorization_type: "bar_reshut", "chocher", or "chocher_mehuvan".
        is_capitalized: True if the nachla is capitalized (at least 3.75%).
        plot_size_sqm: Size of the plot to be split (sqm).
        taba_allows_split: True if the taba allows splitting.

    Returns:
        Audit dict with eligibility result and blocking reasons.
    """
    config = _load_config()
    min_plot = float(config["min_split_plot_sqm"]["value"])

    inputs = {
        "authorization_type": authorization_type,
        "is_capitalized": is_capitalized,
        "plot_size_sqm": plot_size_sqm,
        "taba_allows_split": taba_allows_split,
    }

    blockers: list[str] = []
    warnings: list[str] = []

    # Bar reshut cannot split (finding #8)
    if authorization_type == "bar_reshut":
        blockers.append(
            "בר רשות לא יכול לפצל מגרש ללא הסדרת חוזה חכירה תחילה"
        )

    if not is_capitalized:
        blockers.append("המשק חייב להיות מהוון (לפחות 3.75%) לפני פיצול")

    if plot_size_sqm < min_plot:
        blockers.append(
            f"גודל מגרש מינימלי לפיצול: {min_plot} מ\"ר. המגרש הנוכחי: {plot_size_sqm} מ\"ר"
        )

    if not taba_allows_split:
        blockers.append("התב\"ע אינה מאפשרת פיצול")

    # Warning about aguda approval
    if not blockers:
        warnings.append(
            "פיצול דורש אישור האגודה השיתופית של המושב (עלול לחסום)"
        )

    eligible = len(blockers) == 0

    return {
        "result": {
            "eligible": eligible,
            "blockers": blockers,
            "warnings": warnings,
        },
        "formula": "all conditions must be met: chocher/mehuvan, capitalized, min plot, taba allows",
        "rates_used": {"min_split_plot_sqm": min_plot},
        "inputs": inputs,
    }


def calculate_split_cost(
    plot_value: float,
    paid_hivun_for_plot: float,
    capitalization_track: str,
    split_area_sqm: float = 0.0,
    priority_area: str | None = None,
    effective_date: str | None = None,
) -> dict:
    """Calculate the cost of splitting a plot.

    After 3.75%: 33% * plot_value - paid_hivun
    After 33%: 0 (included in purchase)
    Priority areas: 16.39% up to 160sqm, 20.14% for rest (A/B)

    Args:
        plot_value: Appraised value of the plot to be split (ILS).
        paid_hivun_for_plot: Hivun already paid for this plot (ILS).
        capitalization_track: "375" or "33".
        split_area_sqm: Total area of the split plot (sqm), used for
            priority area tiered calculation.
        priority_area: "A", "B", "frontline", or None.
        effective_date: Optional date string.

    Returns:
        Audit dict with result, formula, rates_used, inputs.
    """
    config = _load_config()

    inputs = {
        "plot_value": plot_value,
        "paid_hivun_for_plot": paid_hivun_for_plot,
        "capitalization_track": capitalization_track,
        "split_area_sqm": split_area_sqm,
        "priority_area": priority_area,
    }

    if plot_value < 0:
        return {"error": "שווי מגרש לא יכול להיות שלילי", "inputs": inputs}

    purchase_tax_rate = float(config["purchase_tax_rate"]["value"])

    # After 33%: split is included
    if capitalization_track == "33":
        return {
            "result": 0.0,
            "split_cost": 0.0,
            "purchase_tax": 0.0,
            "formula": "33% track - split included in purchase price",
            "rates_used": {"capitalization_track": "33"},
            "inputs": inputs,
            "note": "היטל השבחה עדיין חל על פיצול גם במסלול 33%.",
        }

    # After 3.75%: calculate split cost
    standard_rate = float(config["hivun_33_rate"]["value"])
    discounts = config.get("priority_area_discounts", {})
    house_exemption_sqm = float(config["house_exemption_sqm"]["value"])

    if priority_area in ("A", "B"):
        area_data = discounts.get(priority_area, {})
        if isinstance(area_data, dict):
            rate_160 = area_data.get("split_160")
            rate_rest = area_data.get("split_rest")

            if rate_160 is not None and rate_rest is not None:
                rate_160 = float(rate_160)
                rate_rest = float(rate_rest)

                # Tiered: 16.39% up to 160sqm, 20.14% for the rest
                sqm_at_160 = min(split_area_sqm, house_exemption_sqm)
                sqm_above_160 = max(0.0, split_area_sqm - house_exemption_sqm)

                # Proportional split of plot value
                if split_area_sqm > 0:
                    value_at_160 = plot_value * (sqm_at_160 / split_area_sqm)
                    value_above_160 = plot_value * (sqm_above_160 / split_area_sqm)
                else:
                    value_at_160 = plot_value
                    value_above_160 = 0.0

                split_cost = (value_at_160 * rate_160) + (value_above_160 * rate_rest)
                split_cost = max(0.0, split_cost - paid_hivun_for_plot)
                purchase_tax = split_cost * purchase_tax_rate
                total = split_cost + purchase_tax

                formula_str = (
                    f"({round(value_at_160, 2)} * {rate_160}) + ({round(value_above_160, 2)} * {rate_rest}) "
                    f"- {paid_hivun_for_plot} = {round(split_cost, 2)}; "
                    f"purchase_tax = {round(split_cost, 2)} * {purchase_tax_rate}"
                )

                return {
                    "result": round(total, 2),
                    "split_cost": round(split_cost, 2),
                    "purchase_tax": round(purchase_tax, 2),
                    "formula": formula_str,
                    "rates_used": {
                        "rate_up_to_160": rate_160,
                        "rate_above_160": rate_rest,
                        "purchase_tax_rate": purchase_tax_rate,
                        "priority_area": priority_area,
                        "effective_date": effective_date or "current",
                    },
                    "inputs": inputs,
                    "note": "היטל השבחה נוסף ייגבה בעת מימוש (מכירה).",
                }

    # Standard (no priority area): 33% - paid hivun
    split_cost = max(0.0, plot_value * standard_rate - paid_hivun_for_plot)
    purchase_tax = split_cost * purchase_tax_rate
    total = split_cost + purchase_tax

    formula_str = (
        f"{plot_value} * {standard_rate} - {paid_hivun_for_plot} = {round(split_cost, 2)}; "
        f"purchase_tax = {round(split_cost, 2)} * {purchase_tax_rate}"
    )

    return {
        "result": round(total, 2),
        "split_cost": round(split_cost, 2),
        "purchase_tax": round(purchase_tax, 2),
        "formula": formula_str,
        "rates_used": {
            "split_rate": standard_rate,
            "purchase_tax_rate": purchase_tax_rate,
            "priority_area": priority_area,
            "effective_date": effective_date or "current",
        },
        "inputs": inputs,
        "note": "היטל השבחה נוסף ייגבה בעת מימוש (מכירה).",
    }


def calculate_remaining_rights(
    total_rights_sqm: float,
    splits: list[dict] | None = None,
    regularizations: list[dict] | None = None,
) -> dict:
    """Track remaining building rights after splits and regularizations.

    Args:
        total_rights_sqm: Total taba building rights (sqm).
        splits: List of split dicts, each with "area_sqm".
        regularizations: List of regularization dicts, each with "area_sqm".

    Returns:
        Audit dict with remaining rights and breakdown.
    """
    splits = splits or []
    regularizations = regularizations or []

    inputs = {
        "total_rights_sqm": total_rights_sqm,
        "splits": splits,
        "regularizations": regularizations,
    }

    total_split = sum(float(s.get("area_sqm", 0)) for s in splits)
    total_regularized = sum(float(r.get("area_sqm", 0)) for r in regularizations)
    remaining = total_rights_sqm - total_split - total_regularized

    needs_additional_permit = remaining < 0

    return {
        "result": {
            "remaining_sqm": round(remaining, 2),
            "total_split_sqm": round(total_split, 2),
            "total_regularized_sqm": round(total_regularized, 2),
            "needs_additional_permit_fees": needs_additional_permit,
            "additional_permit_sqm": round(abs(remaining), 2) if needs_additional_permit else 0.0,
        },
        "formula": f"{total_rights_sqm} - {total_split} - {total_regularized} = {round(remaining, 2)}",
        "rates_used": {},
        "inputs": inputs,
        "warning": (
            f"שטח בנוי/מפוצל חורג מזכויות התב\"ע ב-{round(abs(remaining), 2)} מ\"ר. יש לרכוש דמי היתר על ההפרש."
            if needs_additional_permit
            else None
        ),
    }
