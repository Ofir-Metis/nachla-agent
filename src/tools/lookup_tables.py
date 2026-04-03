"""Reference table lookups for settlements, PLACH rates, and development costs.

In production these should be loaded from Excel reference files or a database.
The dicts below are SAMPLE data for development and testing.
"""

import json
from pathlib import Path


def _load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "rates_config.json"
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Sample settlement shovi (equivalent sqm value in ILS)
# NOTE: Full table should cover ~450 moshavim. Load from reference Excel.
# ---------------------------------------------------------------------------

_SETTLEMENT_SHOVI: dict[str, float] = {
    "בית דגן": 11_400.0,
    "גן יבנה": 8_200.0,
    "באר טוביה": 7_500.0,
    "גאליה": 9_800.0,
    "כפר אחים": 6_500.0,
    "כפר מרדכי": 7_800.0,
    "בניה": 8_100.0,
    "עזריקם": 6_200.0,
    "ניר בנים": 5_900.0,
    "חצב": 5_400.0,
    "משמר השבעה": 10_200.0,
    "בית עובד": 9_500.0,
    "כפר ביל\"ו": 8_800.0,
    "גבעת ברנר": 9_100.0,
    "נחלה_טסט": 7_000.0,
}


def lookup_settlement_shovi(settlement_name: str) -> float | None:
    """Look up the equivalent sqm value (shovi meter aku) for a settlement.

    Args:
        settlement_name: Name of the settlement in Hebrew.

    Returns:
        The shovi value in ILS per equivalent sqm, or None if not found.
    """
    if not settlement_name or not isinstance(settlement_name, str):
        return None
    return _SETTLEMENT_SHOVI.get(settlement_name.strip())


# ---------------------------------------------------------------------------
# Sample PLACH rates by planning region
# ---------------------------------------------------------------------------

_PLACH_RATES: dict[str, float] = {
    "מרכז": 5_500.0,
    "שרון": 4_800.0,
    "שפלה": 4_200.0,
    "צפון": 3_000.0,
    "דרום": 2_800.0,
    "ירושלים": 6_000.0,
    "חיפה": 4_500.0,
}


def lookup_plach_rate(region: str) -> float | None:
    """Look up PLACH (commercial use) rates by planning region.

    Args:
        region: Planning region name in Hebrew.

    Returns:
        PLACH rate in ILS per sqm, or None if not found.
    """
    if not region or not isinstance(region, str):
        return None
    return _PLACH_RATES.get(region.strip())


# ---------------------------------------------------------------------------
# Sample development costs by regional council
# ---------------------------------------------------------------------------

_DEVELOPMENT_COSTS: dict[str, float] = {
    "חבל יבנה": 247_000.0,
    "גדרות": 220_000.0,
    "באר טוביה": 195_000.0,
    "שפיר": 210_000.0,
    "יואב": 180_000.0,
    "לכיש": 165_000.0,
    "שקמה": 155_000.0,
    "גן רווה": 230_000.0,
    "עמק חפר": 260_000.0,
    "מטה יהודה": 200_000.0,
    "מועצה_טסט": 100_000.0,
}


def lookup_development_costs(regional_council: str) -> float | None:
    """Look up development costs by regional council.

    Development costs are deducted from hivun (capitalization) payments.

    Args:
        regional_council: Regional council name in Hebrew.

    Returns:
        Development costs in ILS, or None if not found.
    """
    if not regional_council or not isinstance(regional_council, str):
        return None
    return _DEVELOPMENT_COSTS.get(regional_council.strip())
