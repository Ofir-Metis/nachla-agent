"""govmap.gov.il integration.

Phase 4: Structured manual taba input with validation.
Phase 5: Playwright-based scraping of govmap ArcGIS REST APIs.

Architecture per technical_blueprint.md section 4:
- govmap uses ArcGIS/Esri technology
- REST endpoints at ags.govmap.gov.il
- Intercept XHR via Playwright page.route() (Phase 5)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ArcGIS REST endpoint constants (for Phase 5 Playwright integration)
GOVMAP_BASE_URL = "https://ags.govmap.gov.il"
GOVMAP_TABA_SERVICE = f"{GOVMAP_BASE_URL}/arcgis/rest/services/PlanningData/MapServer"
XPLAN_BASE_URL = "https://xplan.gov.il"

# Manual input field definitions (shared between schema and validation)
_MANUAL_FIELDS: list[dict[str, Any]] = [
    {"name": "taba_number", "label": 'מספר תב"ע', "type": "str", "required": True},
    {"name": "taba_name", "label": 'שם התב"ע', "type": "str", "required": True},
    {
        "name": "status",
        "label": "סטטוס",
        "type": "choice",
        "options": ["approved", "in_process", "deposited"],
        "required": True,
    },
    {"name": "plot_size_sqm", "label": 'שטח מגרש במ"ר', "type": "float", "required": True},
    {"name": "num_units_allowed", "label": 'מספר יח"ד מותרות', "type": "float", "required": True},
    {"name": "main_area_sqm", "label": 'שטח עיקרי מותר למ"ר', "type": "float", "required": True},
    {"name": "service_area_sqm", "label": 'שטח שירות מותר למ"ר', "type": "float", "required": True},
    {"name": "plach_area_sqm", "label": 'שטח פל"ח מותר במ"ר', "type": "float", "required": False, "default": 0},
    {"name": "split_allowed", "label": "האם מותר פיצול", "type": "bool", "required": True},
    {
        "name": "split_min_plot_sqm",
        "label": "שטח מינימלי לפיצול",
        "type": "float",
        "required": False,
        "default": 350,
    },
    {"name": "pool_allowed", "label": "האם מותרת בריכה", "type": "bool", "required": False, "default": False},
    {
        "name": "attached_unit_allowed",
        "label": "האם מותרת יחידה צמודת קיר",
        "type": "bool",
        "required": False,
        "default": True,
    },
]


class GovmapClient:
    """Govmap data retrieval with manual input fallback.

    Phase 4: Returns structured manual input form.
    Phase 5: Will use Playwright to scrape govmap.gov.il.
    """

    def is_available(self) -> bool:
        """Check if automated govmap scraping is available."""
        return False  # Phase 5

    async def get_tabas_for_plot(self, gush: int, helka: int) -> list[dict] | None:
        """Attempt automated taba retrieval. Returns None if unavailable."""
        if not self.is_available():
            logger.info(
                "Govmap scraping not available (Phase 4). "
                "Manual taba input required for gush=%d, helka=%d",
                gush,
                helka,
            )
            return None
        # Phase 5: Playwright implementation
        return None

    def get_manual_input_schema(self) -> dict[str, Any]:
        """Return the schema for manual taba data input.

        Used when automated scraping is unavailable.
        Returns a dict describing what fields the user must provide manually.
        """
        return {
            "description": 'נא להזין נתוני תב"ע ידנית (הזנה אוטומטית מ-govmap לא זמינה)',
            "fields": _MANUAL_FIELDS,
        }

    def validate_manual_input(self, data: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate manually entered taba data.

        Returns (is_valid, list_of_error_messages_in_hebrew).
        """
        errors: list[str] = []

        for field in _MANUAL_FIELDS:
            name = field["name"]
            required = field.get("required", False)
            field_type = field["type"]
            label = field["label"]

            value = data.get(name)

            # Check required fields
            if required and (value is None or value == ""):
                errors.append(f"שדה חובה חסר: {label}")
                continue

            # Skip validation for missing optional fields
            if value is None or value == "":
                continue

            # Type validation
            if field_type == "str":
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"{label}: חייב להיות טקסט לא ריק")

            elif field_type == "float":
                try:
                    float_val = float(value)
                    if float_val < 0:
                        errors.append(f"{label}: ערך לא יכול להיות שלילי")
                except (TypeError, ValueError):
                    errors.append(f"{label}: חייב להיות מספר")

            elif field_type == "bool":
                if not isinstance(value, bool):
                    errors.append(f"{label}: חייב להיות ערך בוליאני (true/false)")

            elif field_type == "choice":
                options = field.get("options", [])
                if value not in options:
                    errors.append(f"{label}: ערך לא חוקי '{value}'. אפשרויות: {', '.join(options)}")

        # Cross-field validations
        plot_size = data.get("plot_size_sqm")
        main_area = data.get("main_area_sqm")
        service_area = data.get("service_area_sqm")

        if plot_size is not None and main_area is not None and service_area is not None:
            try:
                total_building = float(main_area) + float(service_area)
                plot_float = float(plot_size)
                if plot_float > 0 and total_building > plot_float:
                    errors.append(
                        f"שטח בנייה כולל ({total_building:.0f} מ\"ר) חורג משטח המגרש ({plot_float:.0f} מ\"ר)"
                    )
            except (TypeError, ValueError):
                pass  # Already caught by individual field validation

        split_allowed = data.get("split_allowed")
        split_min = data.get("split_min_plot_sqm")
        if split_allowed is True and split_min is not None:
            try:
                if float(split_min) <= 0:
                    errors.append("שטח מינימלי לפיצול חייב להיות גדול מ-0 כאשר פיצול מותר")
            except (TypeError, ValueError):
                pass

        is_valid = len(errors) == 0
        return is_valid, errors

    def manual_input_to_taba(self, data: dict[str, Any]) -> dict[str, Any]:
        """Convert validated manual input to a Taba-compatible dict.

        Maps the manual input fields to the Taba model structure.
        The returned dict can be used to construct a Taba model instance.
        """
        # Apply defaults for optional fields
        defaults: dict[str, Any] = {}
        for field in _MANUAL_FIELDS:
            if "default" in field:
                defaults[field["name"]] = field["default"]

        # Merge defaults with provided data
        merged = {**defaults, **{k: v for k, v in data.items() if v is not None}}

        main_area = float(merged.get("main_area_sqm", 0))
        service_area = float(merged.get("service_area_sqm", 0))

        return {
            "taba_number": merged["taba_number"],
            "taba_name": merged["taba_name"],
            "status": merged["status"],
            "plot_id": "",  # To be filled by caller (e.g., from gush/helka)
            "plot_size_sqm": float(merged["plot_size_sqm"]),
            "num_units_allowed": float(merged["num_units_allowed"]),
            "unit_rights": [
                {
                    "main_area_sqm": main_area,
                    "service_area_sqm": service_area,
                }
            ],
            "plach_area_sqm": float(merged.get("plach_area_sqm", 0)),
            "split_allowed": bool(merged.get("split_allowed", False)),
            "split_min_plot_sqm": float(merged.get("split_min_plot_sqm", 350)),
            "pool_allowed": bool(merged.get("pool_allowed", False)),
            "attached_unit_allowed": bool(merged.get("attached_unit_allowed", True)),
            "source": "manual",
            "is_primary": False,
        }
