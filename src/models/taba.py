"""Taba (zoning plan / תב"ע) data model.

Represents a zoning plan and its associated building rights for a nachla plot.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, computed_field, field_validator


class TabaRights(BaseModel):
    """Building rights for one unit type within a taba.

    Represents the permitted areas for a single residential unit
    as defined by the zoning plan.
    """

    main_area_sqm: float = Field(..., ge=0, description='שטח עיקרי מותר במ"ר')
    service_area_sqm: float = Field(..., ge=0, description='שטח שירות מותר במ"ר')
    # Default 12.0 is a data-entry convenience; calculations use rates_config.json mamad_exemption_sqm
    mamad_sqm: float = Field(default=12.0, ge=0, description='שטח ממ"ד סטנדרטי במ"ר')

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_area_sqm(self) -> float:
        """Total permitted area for this unit type."""
        return self.main_area_sqm + self.service_area_sqm + self.mamad_sqm


class Taba(BaseModel):
    """A zoning plan (תב"ע) applicable to a nachla plot.

    Contains the plan identification, permitted rights, split rules,
    and special provisions that govern what can be built on the plot.
    """

    # Plan identification
    taba_number: str = Field(..., min_length=1, description="מספר תב\"ע, e.g. '616-0902908'")
    taba_name: str = Field(..., min_length=1, description='שם התב"ע')
    status: str = Field(
        ...,
        description="סטטוס: approved / in_process / deposited",
    )
    approval_date: str | None = Field(default=None, description='תאריך אישור התב"ע')

    # Plot details
    plot_id: str = Field(..., description="מזהה מגרש, e.g. 'מגרש 68'")
    plot_size_sqm: float = Field(..., gt=0, description='שטח מגרש במ"ר (e.g. 2500 for 2.5 dunam)')

    # Building rights
    num_units_allowed: float = Field(..., ge=0, description="מספר יחידות דיור מותרות (e.g. 2.5)")
    unit_rights: list[TabaRights] = Field(default_factory=list, description="זכויות בנייה לכל יחידת דיור")
    # Default 55 is standard per most tabas; actual value comes from taba document
    attached_unit_sqm: float = Field(default=55, ge=0, description='שטח יחידה צמודת קיר במ"ר')
    attached_unit_allowed: bool = Field(default=True, description="האם מותרת יחידה צמודת קיר")
    plach_area_sqm: float = Field(default=0, ge=0, description='שטח פל"ח מותר במ"ר')

    # Split rules
    split_allowed: bool = Field(default=False, description='האם התב"ע מאפשרת פיצול')
    # Default 350 is a data-entry convenience; calculations use rates_config.json min_split_plot_sqm
    split_min_plot_sqm: float = Field(default=350, ge=0, description='שטח מגרש מינימלי לפיצול במ"ר')
    split_max_plots: int = Field(default=0, ge=0, description="מספר מגרשי פיצול מקסימלי")

    # Additional permissions
    pool_allowed: bool = Field(default=False, description="האם מותרת בריכת שחייה")
    building_lines: dict[str, float] = Field(
        default_factory=dict,
        description="קווי בניין (מרחקים מגבולות) - e.g. {'front': 5.0, 'side': 3.0, 'back': 3.0}",
    )
    coverage_percent: float | None = Field(default=None, ge=0, le=100, description="אחוז כיסוי מקסימלי")

    # Provisions and metadata
    special_provisions: list[str] = Field(default_factory=list, description='הוראות מיוחדות בתב"ע')
    is_primary: bool = Field(default=False, description='תב"ע עיקרית לנחלה זו')
    source: str = Field(default="", description="מקור מידע: govmap / xplan / manual")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"approved", "in_process", "deposited"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}, got '{v}'")
        return v
