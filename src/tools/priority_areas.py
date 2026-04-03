"""Priority area classification and discount logic for Israeli RMI calculations.

Classifies settlements into national priority areas (A, B, frontline)
and returns applicable discount factors for each payment type.
"""

import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------


def _load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "rates_config.json"
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Settlement -> priority area mapping
# NOTE: This is a SAMPLE dict (~20 per area). In production, load the full
# list of ~450 moshavim from a reference Excel / DB table.
# ---------------------------------------------------------------------------

_PRIORITY_AREA_MAP: dict[str, str] = {
    # Area A (periphery - deep south / north)
    "ירוחם": "A",
    "ערד": "A",
    "מצפה רמון": "A",
    "שדה בוקר": "A",
    "רביבים": "A",
    "כסייפה": "A",
    "נאות הכיכר": "A",
    "באר מילכה": "A",
    "עין יהב": "A",
    "פארן": "A",
    "צופר": "A",
    "עידן": "A",
    "חצבה": "A",
    "ספיר": "A",
    "יטבתה": "A",
    "קטורה": "A",
    "אליפז": "A",
    "לוטן": "A",
    "גרופית": "A",
    "שיזפון": "A",
    # Area B (moderate periphery)
    "קריית שמונה": "B",
    "מטולה": "B",
    "שלומי": "B",
    "מעלות תרשיחא": "B",
    "חצור הגלילית": "B",
    "צפת": "B",
    "טבריה": "B",
    "בית שאן": "B",
    "עפולה": "B",
    "מגדל העמק": "B",
    "נצרת עילית": "B",
    "כרמיאל": "B",
    "עכו": "B",
    "דימונה": "B",
    "אופקים": "B",
    "נתיבות": "B",
    "שדרות": "B",
    "ירוחם": "A",  # override stays A
    "מעלה אדומים": "B",
    "אריאל": "B",
    # Frontline (kav imut - border communities)
    "שתולה": "frontline",
    "מנרה": "frontline",
    "מרגליות": "frontline",
    "יפתח": "frontline",
    "דובב": "frontline",
    "אביבים": "frontline",
    "מלכיה": "frontline",
    "נטועה": "frontline",
    "זרעית": "frontline",
    "שומרה": "frontline",
    "בצת": "frontline",
    "כפר גלעדי": "frontline",
    "דן": "frontline",
    "סנהדריה": "frontline",
    "מסגב": "frontline",
    "נירים": "frontline",
    "כיסופים": "frontline",
    "עין השלושה": "frontline",
    "נחל עוז": "frontline",
    "כרם שלום": "frontline",
}


def get_priority_area(settlement_name: str) -> str | None:
    """Look up the national priority area for a settlement.

    Args:
        settlement_name: Name of the settlement (Hebrew).

    Returns:
        "A", "B", "frontline", or None if the settlement is not in a
        priority area or not found in the lookup table.
    """
    if not settlement_name or not isinstance(settlement_name, str):
        return None
    # Strip whitespace for fuzzy-ish matching
    clean = settlement_name.strip()
    return _PRIORITY_AREA_MAP.get(clean)


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
