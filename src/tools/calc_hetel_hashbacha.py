"""Betterment levy (hetel hashbacha) calculations for Israeli RMI.

All constants loaded from rates_config.json. Never hardcoded.
Every function returns an audit dict with: result, formula, rates_used, inputs.
"""

import json
from pathlib import Path


def _load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "rates_config.json"
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def calculate_betterment_levy(
    new_value: float,
    old_value: float,
    effective_date: str | None = None,
) -> dict:
    """Calculate betterment levy (hetel hashbacha).

    Formula: betterment_rate * (new_value - old_value)

    Args:
        new_value: Property value after the improvement / new taba (ILS).
        old_value: Property value before the improvement (ILS).
        effective_date: Optional date string.

    Returns:
        Audit dict with result, formula, rates_used, inputs.
    """
    config = _load_config()

    inputs = {
        "new_value": new_value,
        "old_value": old_value,
    }

    if new_value < 0 or old_value < 0:
        return {"error": "ערכי נכס לא יכולים להיות שליליים", "inputs": inputs}

    levy_rate = float(config["betterment_levy_rate"]["value"])
    appreciation = new_value - old_value

    if appreciation <= 0:
        return {
            "result": 0.0,
            "appreciation": round(appreciation, 2),
            "formula": f"{levy_rate} * ({new_value} - {old_value}) = 0 (no appreciation)",
            "rates_used": {
                "betterment_levy_rate": levy_rate,
                "effective_date": effective_date or "current",
            },
            "inputs": inputs,
            "note": "אין השבחה - אין היטל.",
        }

    levy = levy_rate * appreciation

    return {
        "result": round(levy, 2),
        "appreciation": round(appreciation, 2),
        "formula": f"{levy_rate} * ({new_value} - {old_value}) = {round(levy, 2)}",
        "rates_used": {
            "betterment_levy_rate": levy_rate,
            "effective_date": effective_date or "current",
        },
        "inputs": inputs,
        "note": "היטל השבחה ייגבה בעת מימוש (מכירה או היתר בנייה).",
    }


def calculate_partial_betterment(
    total_levy: float,
    rights_used_sqm: float,
    total_rights_sqm: float,
    effective_date: str | None = None,
) -> dict:
    """Calculate partial betterment levy for permits (not full realization).

    When a permit is issued (not a sale), the levy is proportional
    to the rights used vs total rights.

    Args:
        total_levy: Full betterment levy amount (ILS).
        rights_used_sqm: Rights used in this permit (sqm).
        total_rights_sqm: Total taba rights (sqm).
        effective_date: Optional date string.

    Returns:
        Audit dict with partial levy result.
    """
    inputs = {
        "total_levy": total_levy,
        "rights_used_sqm": rights_used_sqm,
        "total_rights_sqm": total_rights_sqm,
    }

    if total_rights_sqm <= 0:
        return {"error": "סה\"כ זכויות חייב להיות חיובי", "inputs": inputs}

    if rights_used_sqm < 0:
        return {"error": "זכויות מנוצלות לא יכולות להיות שליליות", "inputs": inputs}

    if total_levy < 0:
        return {"error": "היטל השבחה לא יכול להיות שלילי", "inputs": inputs}

    proportion = rights_used_sqm / total_rights_sqm
    proportion = min(1.0, proportion)
    partial_levy = total_levy * proportion

    return {
        "result": round(partial_levy, 2),
        "proportion": round(proportion, 4),
        "formula": f"{total_levy} * ({rights_used_sqm} / {total_rights_sqm}) = {round(partial_levy, 2)}",
        "rates_used": {
            "effective_date": effective_date or "current",
        },
        "inputs": inputs,
        "note": "היטל חלקי בגין היתר בנייה. יתרת ההיטל תיגבה בעת מימוש מלא (מכירה).",
    }


def estimate_split_betterment(
    plot_value_after_split: float,
    plot_value_as_part_of_nachla: float,
    effective_date: str | None = None,
) -> dict:
    """Estimate betterment levy for split transactions.

    The appreciation is the difference between the plot's value as
    an independent unit vs its value as part of the nachla.

    Args:
        plot_value_after_split: Value of the plot as independent unit (ILS).
        plot_value_as_part_of_nachla: Value as part of the nachla (ILS).
        effective_date: Optional date string.

    Returns:
        Audit dict with estimated levy.
    """
    config = _load_config()

    inputs = {
        "plot_value_after_split": plot_value_after_split,
        "plot_value_as_part_of_nachla": plot_value_as_part_of_nachla,
    }

    if plot_value_after_split < 0 or plot_value_as_part_of_nachla < 0:
        return {"error": "ערכי מגרש לא יכולים להיות שליליים", "inputs": inputs}

    levy_rate = float(config["betterment_levy_rate"]["value"])
    appreciation = plot_value_after_split - plot_value_as_part_of_nachla

    if appreciation <= 0:
        return {
            "result": 0.0,
            "appreciation": round(appreciation, 2),
            "formula": "no appreciation from split",
            "rates_used": {
                "betterment_levy_rate": levy_rate,
                "effective_date": effective_date or "current",
            },
            "inputs": inputs,
        }

    levy = levy_rate * appreciation

    return {
        "result": round(levy, 2),
        "appreciation": round(appreciation, 2),
        "formula": (
            f"{levy_rate} * ({plot_value_after_split} - {plot_value_as_part_of_nachla}) "
            f"= {round(levy, 2)}"
        ),
        "rates_used": {
            "betterment_levy_rate": levy_rate,
            "effective_date": effective_date or "current",
        },
        "inputs": inputs,
        "note": (
            "הערכה בלבד. היטל ההשבחה ייקבע ע\"י שמאי הוועדה המקומית. "
            "ייגבה בעת מכירת המגרש המפוצל."
        ),
    }
