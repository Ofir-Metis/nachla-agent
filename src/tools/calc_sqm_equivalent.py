"""Equivalent sqm calculation from taba rights for Israeli RMI.

Calculates the equivalent sqm (meter aku) used for hivun and other
RMI calculations, including the dynamic 808 calculation.

All constants loaded from rates_config.json. Never hardcoded.
Every function returns an audit dict with: result, formula, rates_used, inputs.
"""

import json
from pathlib import Path


def _load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "rates_config.json"
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def calculate_sqm_equivalent(components: list[dict]) -> dict:
    """Calculate total equivalent sqm from a list of area components.

    Args:
        components: List of dicts, each with:
            - "type": one of "main", "mamad", "service", "auxiliary",
              "yard_effective", "yard_remainder", "yard_far", "pool",
              "basement_service", "basement_residential"
            - "area_sqm": float

    Returns:
        Audit dict with total equivalent sqm and per-component breakdown.
    """
    config = _load_config()
    coefficients = config["sqm_equivalent_coefficients"]
    valid_types = [
        k for k in coefficients if k not in ("effective_date", "expiry_date", "note")
    ]

    inputs = {"components": components}
    breakdown: list[dict] = []
    total = 0.0

    for comp in components:
        comp_type = comp.get("type", "")
        area_sqm = float(comp.get("area_sqm", 0))

        if comp_type not in valid_types:
            breakdown.append({
                "type": comp_type,
                "area_sqm": area_sqm,
                "error": f"סוג לא חוקי: {comp_type}. סוגים תקינים: {valid_types}",
            })
            continue

        coeff = float(coefficients[comp_type])
        equivalent = area_sqm * coeff
        total += equivalent

        breakdown.append({
            "type": comp_type,
            "area_sqm": area_sqm,
            "coefficient": coeff,
            "equivalent_sqm": round(equivalent, 2),
        })

    return {
        "result": round(total, 2),
        "breakdown": breakdown,
        "formula": "sum(area_sqm * coefficient) for each component",
        "rates_used": {k: v for k, v in coefficients.items() if k in valid_types},
        "inputs": inputs,
    }


def calculate_nachla_sqm_equivalent(
    plot_size_sqm: float,
    building_coverage_sqm: float,
    taba_rights: dict,
) -> dict:
    """Calculate full nachla equivalent sqm including yard components.

    Args:
        plot_size_sqm: Total residential plot size (sqm), e.g. 2500.
        building_coverage_sqm: Total building coverage (footprint) in sqm.
        taba_rights: Dict with building rights from taba:
            - "main_sqm": float (total main residential area)
            - "mamad_sqm": float (total mamad area)
            - "service_sqm": float (total service area)
            - "pool_sqm": float (optional, pool area)
            - "basement_service_sqm": float (optional)
            - "basement_residential_sqm": float (optional)

    Returns:
        Audit dict with total equivalent sqm and breakdown.
    """
    config = _load_config()
    yard_max = float(config["yard_effective_max_sqm"]["value"])

    inputs = {
        "plot_size_sqm": plot_size_sqm,
        "building_coverage_sqm": building_coverage_sqm,
        "taba_rights": taba_rights,
    }

    if plot_size_sqm <= 0:
        return {"error": "גודל מגרש חייב להיות חיובי", "inputs": inputs}

    # Build component list from taba rights
    components: list[dict] = []

    main = float(taba_rights.get("main_sqm", 0))
    if main > 0:
        components.append({"type": "main", "area_sqm": main})

    mamad = float(taba_rights.get("mamad_sqm", 0))
    if mamad > 0:
        components.append({"type": "mamad", "area_sqm": mamad})

    service = float(taba_rights.get("service_sqm", 0))
    if service > 0:
        components.append({"type": "service", "area_sqm": service})

    pool = float(taba_rights.get("pool_sqm", 0))
    if pool > 0:
        components.append({"type": "pool", "area_sqm": pool})

    basement_service = float(taba_rights.get("basement_service_sqm", 0))
    if basement_service > 0:
        components.append({"type": "basement_service", "area_sqm": basement_service})

    basement_res = float(taba_rights.get("basement_residential_sqm", 0))
    if basement_res > 0:
        components.append({"type": "basement_residential", "area_sqm": basement_res})

    # Calculate yard components
    total_yard = max(0.0, plot_size_sqm - building_coverage_sqm)
    yard_effective = min(yard_max, total_yard)
    yard_after_effective = total_yard - yard_effective
    yard_remainder = min(yard_max, yard_after_effective)
    yard_far = max(0.0, yard_after_effective - yard_remainder)

    if yard_effective > 0:
        components.append({"type": "yard_effective", "area_sqm": yard_effective})
    if yard_remainder > 0:
        components.append({"type": "yard_remainder", "area_sqm": yard_remainder})
    if yard_far > 0:
        components.append({"type": "yard_far", "area_sqm": yard_far})

    result = calculate_sqm_equivalent(components)

    # Augment with yard calculation details
    result["yard_details"] = {
        "total_yard_sqm": round(total_yard, 2),
        "yard_effective_sqm": round(yard_effective, 2),
        "yard_remainder_sqm": round(yard_remainder, 2),
        "yard_far_sqm": round(yard_far, 2),
    }
    result["inputs"] = inputs

    return result


def calculate_potential_sqm(
    taba_rights_sqm: float,
    existing_recognized_sqm: float,
) -> dict:
    """Calculate remaining buildable potential in equivalent sqm.

    Args:
        taba_rights_sqm: Total taba building rights (sqm).
        existing_recognized_sqm: Already built and recognized area (sqm).

    Returns:
        Audit dict with potential remaining sqm.
    """
    inputs = {
        "taba_rights_sqm": taba_rights_sqm,
        "existing_recognized_sqm": existing_recognized_sqm,
    }

    potential = max(0.0, taba_rights_sqm - existing_recognized_sqm)

    return {
        "result": round(potential, 2),
        "formula": f"max(0, {taba_rights_sqm} - {existing_recognized_sqm}) = {round(potential, 2)}",
        "rates_used": {},
        "inputs": inputs,
    }


def calculate_hivun_375_sqm(
    plot_size_sqm: float,
    taba_rights: dict,
    building_coverage_sqm: float | None = None,
) -> dict:
    """Dynamic 808 calculation for the 3.75% track.

    For a standard nachla (2.5 dunam, 375 sqm rights), the result
    should be approximately 808. If non-standard, the value will differ
    and a warning is included.

    Args:
        plot_size_sqm: Residential plot size (sqm).
        taba_rights: Dict with taba rights (same format as
            calculate_nachla_sqm_equivalent).
        building_coverage_sqm: Optional building coverage. If not provided,
            estimated from taba_rights.

    Returns:
        Audit dict with computed 375 sqm equivalent and standard comparison.
    """
    config = _load_config()
    default_808 = float(config["hivun_375_default_sqm"]["value"])
    standard_plot = float(config["standard_plot_size_sqm"]["value"])
    standard_rights = float(config["standard_taba_rights_sqm"]["value"])

    # Estimate building coverage if not provided
    if building_coverage_sqm is None:
        main = float(taba_rights.get("main_sqm", 0))
        service = float(taba_rights.get("service_sqm", 0))
        building_coverage_sqm = main + service

    nachla_result = calculate_nachla_sqm_equivalent(
        plot_size_sqm=plot_size_sqm,
        building_coverage_sqm=building_coverage_sqm,
        taba_rights=taba_rights,
    )

    if "error" in nachla_result:
        return nachla_result

    computed_sqm = nachla_result["result"]

    # Check if standard
    total_main = float(taba_rights.get("main_sqm", 0))
    total_service = float(taba_rights.get("service_sqm", 0))
    total_rights = total_main + total_service

    is_standard = (
        abs(plot_size_sqm - standard_plot) < 50
        and abs(total_rights - standard_rights) < 25
    )

    warning = None
    if not is_standard:
        warning = (
            f"נחלה לא סטנדרטית (מגרש {plot_size_sqm} מ\"ר, זכויות {total_rights} מ\"ר). "
            f"מ\"ר אקוויוולנטי מחושב: {computed_sqm} (ברירת מחדל סטנדרטית: {default_808})."
        )
    elif abs(computed_sqm - default_808) > 50:
        warning = (
            f"נחלה סטנדרטית אך מ\"ר אקוויוולנטי מחושב ({computed_sqm}) "
            f"שונה מ-{default_808}. יש לבדוק את הנתונים."
        )

    return {
        "result": round(computed_sqm, 2),
        "default_808": default_808,
        "is_standard": is_standard,
        "breakdown": nachla_result.get("breakdown", []),
        "yard_details": nachla_result.get("yard_details", {}),
        "formula": nachla_result.get("formula", ""),
        "rates_used": nachla_result.get("rates_used", {}),
        "inputs": {
            "plot_size_sqm": plot_size_sqm,
            "taba_rights": taba_rights,
            "building_coverage_sqm": building_coverage_sqm,
        },
        "warning": warning,
    }
