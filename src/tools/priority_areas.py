"""Priority area classification and discount logic for Israeli RMI calculations.

Classifies settlements into national priority areas (A, B, frontline)
and returns applicable discount factors for each payment type.
"""

import json
import re
import unicodedata
from pathlib import Path

# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------


def _load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "rates_config.json"
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Settlement -> priority area mapping (loaded from reference JSON)
# ---------------------------------------------------------------------------

_SETTLEMENTS_FILE = Path(__file__).parent.parent.parent / "data" / "reference" / "settlements_priority.json"

_settlement_cache: dict[str, str] | None = None


def _normalize_hebrew(name: str) -> str:
    """Normalize a Hebrew settlement name for fuzzy matching.

    Strips niqqud (vowel marks), normalizes whitespace, removes
    quotes and hyphens, and lowercases.
    """
    # Remove niqqud (Hebrew points in Unicode range 0x0591-0x05C7)
    cleaned = ""
    for ch in name:
        if unicodedata.category(ch) in ("Mn",):  # Mark, Nonspacing (niqqud)
            continue
        cleaned += ch
    # Remove quotes, hyphens, double-quotes
    cleaned = re.sub(r'["\'\-–—]', "", cleaned)
    # Normalize whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _load_settlements() -> dict[str, str]:
    """Load and cache settlement priority area map from JSON reference."""
    global _settlement_cache
    if _settlement_cache is not None:
        return _settlement_cache

    _settlement_cache = {}

    if _SETTLEMENTS_FILE.exists():
        with open(_SETTLEMENTS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        raw = data.get("settlements", {})
        for name, area in raw.items():
            if isinstance(area, str) and area in ("A", "B", "frontline"):
                _settlement_cache[_normalize_hebrew(name)] = area
    else:
        import logging
        logging.getLogger(__name__).warning(
            "Settlement priority file not found: %s", _SETTLEMENTS_FILE
        )

    return _settlement_cache


def get_priority_area(settlement_name: str) -> str | None:
    """Look up the national priority area for a settlement.

    Uses fuzzy matching: strips niqqud, normalizes whitespace and punctuation.

    Args:
        settlement_name: Name of the settlement (Hebrew).

    Returns:
        "A", "B", "frontline", or None if the settlement is not in a
        priority area or not found in the lookup table.
    """
    if not settlement_name or not isinstance(settlement_name, str):
        return None

    settlements = _load_settlements()
    normalized = _normalize_hebrew(settlement_name)

    # Exact match after normalization
    if normalized in settlements:
        return settlements[normalized]

    # Partial match: check if input is a substring of a known settlement or vice versa
    # Require match length >= 3 characters to avoid false positives
    for key, area in settlements.items():
        if len(normalized) >= 3 and normalized in key:
            return area
        if len(key) >= 3 and key in normalized:
            return area

    return None


def get_discount(priority_area: str | None, payment_type: str) -> float:
    """Return the discount factor or reduced rate for a given payment type.

    For *permit* fees the returned value is the **discount percentage**
    (e.g. 0.51 means 51% off).

    For *purchase_33*, *split_160*, *split_rest* the returned value is
    the **replacement rate** (e.g. 0.2014 replaces 0.33).

    For *usage* the returned value is the **replacement rate** (0.03
    replaces 0.05).

    Args:
        priority_area: "A", "B", "frontline", or None.
        payment_type: One of "permit", "purchase_33", "split_160",
                      "split_rest", "usage".

    Returns:
        The discount factor / replacement rate, or 0.0 if no discount
        applies.
    """
    if not priority_area:
        return 0.0

    config = _load_config()
    discounts = config.get("priority_area_discounts", {})
    area_data = discounts.get(priority_area)
    if not area_data or not isinstance(area_data, dict):
        return 0.0

    value = area_data.get(payment_type)
    if value is None:
        return 0.0
    return float(value)


def get_usage_rate(priority_area: str | None, usage_type: str) -> float:
    """Return the applicable usage fee rate considering priority area.

    Args:
        priority_area: "A", "B", "frontline", or None.
        usage_type: "residential", "agricultural", or "plach".

    Returns:
        The usage fee rate as a decimal (e.g. 0.05, 0.03, 0.02).
    """
    config = _load_config()

    if usage_type == "agricultural":
        return float(config["usage_fee_agricultural"]["value"])
    if usage_type == "plach":
        return float(config["usage_fee_plach"]["value"])

    # Residential: check priority area
    if priority_area in ("A", "B", "frontline"):
        return float(config["usage_fee_priority"]["value"])
    return float(config["usage_fee_residential"]["value"])


def get_hivun_33_rate(priority_area: str | None) -> float:
    """Return the applicable 33% purchase rate considering priority area.

    Standard: 0.33.  Priority A/B: 0.2014.

    Args:
        priority_area: "A", "B", "frontline", or None.

    Returns:
        The purchase rate as a decimal.
    """
    config = _load_config()
    if priority_area in ("A", "B"):
        rate = get_discount(priority_area, "purchase_33")
        if rate > 0:
            return rate
    return float(config["hivun_33_rate"]["value"])
