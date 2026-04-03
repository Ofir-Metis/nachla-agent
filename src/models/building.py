"""Building data model for nachla feasibility studies.

Represents a single building structure within a nachla (agricultural settlement),
including its classification, areas, permit status, and computed properties.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, computed_field, model_validator


class BuildingType(StrEnum):
    """Classification of building types in a nachla."""

    RESIDENTIAL = "residential"  # בית מגורים
    SERVICE = "service"  # מבנה שירות / מחסן
    AGRICULTURAL = "agricultural"  # מבנה חקלאי / סככה
    PLACH = "plach"  # מבנה פל"ח (עסקי)
    PERGOLA = "pergola"  # פרגולה
    POOL = "pool"  # בריכת שחייה
    BASEMENT_SERVICE = "basement_service"  # מרתף שירות
    BASEMENT_RESIDENTIAL = "basement_residential"  # מרתף מגורים
    ATTIC = "attic"  # עליית גג
    GROUND_FLOOR_OPEN = "ground_floor_open"  # קומת עמודים פתוחה
    GROUND_FLOOR_CLOSED = "ground_floor_closed"  # קומת עמודים סגורה
    TEMPORARY = "temporary"  # מבנה ארעי/קל/נייד
    SHED_OPEN = "shed_open"  # סככה פתוחה
    PRE_1965 = "pre_1965"  # מבנה לפני 1965


class BuildingStatus(StrEnum):
    """Status of a building relative to its permit."""

    COMPLIANT = "compliant"  # תקין - תואם היתר
    DEVIATION = "deviation"  # חריגה מהיתר
    NO_PERMIT = "no_permit"  # ללא היתר
    MARKED_DEMOLITION = "marked_demolition"  # סומן להריסה
    BUILDING_LINE_VIOLATION = "building_line_violation"  # חורג מקווי בניין


class PergolaRoofType(StrEnum):
    """Type of pergola roof covering."""

    OPAQUE = "opaque"  # קירוי אטום > 40%
    TRANSPARENT = "transparent"  # סנטף שקוף > 60% מעבר אור
    NONE = "none"


# DEFAULT display-only coefficients for the Building model's `eco_coefficient` property.
# WARNING: These are NOT used in any financial calculation. Each calc tool loads its
# own context-specific coefficients from rates_config.json:
#   - Permit fees: src/config/rates_config.json -> permit_fee_coefficients
#   - Usage fees:  src/config/rates_config.json -> usage_fee_coefficients
#   - Sqm equiv:   src/config/rates_config.json -> sqm_equivalent_coefficients
# This dict exists only for model-level classification display. Values are approximate.
_ECO_COEFFICIENTS: dict[BuildingType, float] = {
    BuildingType.RESIDENTIAL: 1.0,
    BuildingType.SERVICE: 0.5,
    BuildingType.AGRICULTURAL: 0.0,  # Exempt
    BuildingType.PLACH: 1.0,
    BuildingType.PERGOLA: 0.5,  # Per workflow step 4.2 usage fee context
    BuildingType.POOL: 0.3,  # Matches rates_config.json
    BuildingType.BASEMENT_SERVICE: 0.3,
    BuildingType.BASEMENT_RESIDENTIAL: 0.7,
    BuildingType.ATTIC: 1.0,  # 1.0 if usable (>1.80m); attic_usable flag determines
    BuildingType.GROUND_FLOOR_OPEN: 0.0,  # Per workflow: "not counted as area"
    BuildingType.GROUND_FLOOR_CLOSED: 0.5,  # Service use default
    BuildingType.TEMPORARY: 0.5,
    BuildingType.SHED_OPEN: 0.0,  # Open shed, typically exempt
    BuildingType.PRE_1965: 0.0,  # Exempt from permits
}


class Building(BaseModel):
    """A single building structure within a nachla.

    Captures physical attributes, permit status, area measurements,
    and classification data needed for RMI fee calculations.
    """

    id: int = Field(..., description="Building number from survey map (מספר מבנה במפת מדידה)")
    name: str = Field(..., description="Building name, e.g. 'בית מגורים ראשון'")
    building_type: BuildingType = Field(..., description="סוג מבנה")
    status: BuildingStatus = Field(..., description="סטטוס מבנה ביחס להיתר")

    # Area measurements (sqm)
    main_area_sqm: float = Field(..., ge=0, description='שטח עיקרי במ"ר')
    service_area_sqm: float = Field(default=0, ge=0, description='שטח שירות במ"ר')
    pergola_area_sqm: float = Field(default=0, ge=0, description='שטח פרגולה במ"ר')
    basement_area_sqm: float = Field(default=0, ge=0, description='שטח מרתף במ"ר')
    basement_type: Literal["service", "residential"] | None = Field(
        default=None, description="סוג מרתף: שירות (0.3) או מגורים (0.7)"
    )
    attic_area_sqm: float = Field(default=0, ge=0, description='שטח עליית גג במ"ר')
    attic_usable: bool = Field(default=False, description="גובה > 1.80 מ' - עליית גג שמישה")
    mamad_area_sqm: float = Field(default=0, ge=0, description='שטח ממ"ד במ"ר')

    # Permit information
    permit_year: int | None = Field(default=None, ge=1900, le=2100, description="שנת היתר בנייה")
    permit_area_sqm: float | None = Field(default=None, ge=0, description='שטח לפי היתר במ"ר')
    deviation_sqm: float | None = Field(default=None, ge=0, description='שטח חריגה מעבר להיתר במ"ר')

    # Classification details
    is_within_residential_plot: bool = Field(default=True, description="האם בתוך חלקת המגורים")
    building_order: int = Field(default=1, ge=1, description="סדר מבנה: 1=בית ראשון, 2=שני וכו'")
    has_kitchen: bool | None = Field(default=None, description="האם יש מטבח (רלוונטי ליח' דיור)")
    has_separate_entrance: bool | None = Field(default=None, description="האם יש כניסה נפרדת")
    pergola_roof_type: PergolaRoofType | None = Field(default=None, description="סוג קירוי פרגולה")
    construction_year: int | None = Field(default=None, ge=1800, le=2100, description="שנת בנייה")
    is_pre_1965: bool = Field(default=False, description="מבנה לפני 1965 - פטור מהיתר בנייה")

    notes: str = Field(default="", description="הערות נוספות")
    user_confirmed: bool = Field(default=False, description='סיווג אושר ע"י המשתמש (checkpoint)')

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_area_sqm(self) -> float:
        """Total area including all components (before applying coefficients)."""
        return (
            self.main_area_sqm
            + self.service_area_sqm
            + self.pergola_area_sqm
            + self.basement_area_sqm
            + self.attic_area_sqm
            + self.mamad_area_sqm
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def eco_coefficient(self) -> float:
        """Equivalent coefficient based on building type.

        Used to convert gross area to weighted equivalent area for RMI calculations.
        """
        return _ECO_COEFFICIENTS.get(self.building_type, 1.0)

    @model_validator(mode="after")
    def validate_basement_type_required(self) -> Building:
        """Ensure basement_type is set when basement_area > 0."""
        if self.basement_area_sqm > 0 and self.basement_type is None:
            raise ValueError("basement_type must be specified when basement_area_sqm > 0")
        return self

    @model_validator(mode="after")
    def validate_pre_1965_consistency(self) -> Building:
        """Ensure pre-1965 flag is consistent with construction year."""
        if self.construction_year is not None and self.construction_year < 1965:
            object.__setattr__(self, "is_pre_1965", True)
        return self

    @model_validator(mode="after")
    def validate_deviation(self) -> Building:
        """Ensure deviation data is consistent with status."""
        if self.status == BuildingStatus.DEVIATION and self.deviation_sqm is None:
            raise ValueError("deviation_sqm must be specified when status is 'deviation'")
        return self

    @model_validator(mode="after")
    def validate_pergola_roof(self) -> Building:
        """Ensure pergola_roof_type is set for pergola buildings."""
        if self.building_type == BuildingType.PERGOLA and self.pergola_roof_type is None:
            raise ValueError("pergola_roof_type must be specified for pergola buildings")
        return self
