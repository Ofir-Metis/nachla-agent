"""Nachla (agricultural settlement property) data model.

Represents the complete property record for a nachla including ownership,
authorization status, priority area classification, and associated buildings/tabas.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator


class AuthorizationType(StrEnum):
    """Type of land authorization held by the nachla owner."""

    BAR_RESHUT = "bar_reshut"  # בר רשות
    CHOCHER = "chocher"  # חוכר לדורות
    CHOZE_CHACHIRA_MEHUVON = "choze_chachira_mehuvon"  # חוזה חכירה מהוון


class PriorityArea(StrEnum):
    """National priority area classification affecting all fee calculations."""

    NONE = "none"  # רגיל
    A = "A"  # עדיפות א'
    B = "B"  # עדיפות ב'
    FRONTLINE = "frontline"  # קו עימות


class OwnershipType(StrEnum):
    """Ownership structure of the nachla."""

    SINGLE = "single"  # בעלים יחיד
    PARTNERS = "partners"  # שותפים
    HEIRS = "heirs"  # יורשים


class ClientGoal(StrEnum):
    """Goals the client wants to achieve with the feasibility study."""

    REGULARIZATION = "regularization"  # הסדרה
    CAPITALIZATION = "capitalization"  # היוון
    SPLIT = "split"  # פיצול
    ALL = "all"  # הכל


class CapitalizationTrack(StrEnum):
    """Capitalization track for the nachla."""

    TRACK_375 = "375"  # 3.75%
    TRACK_33 = "33"  # 33%
    NONE = "none"  # לא מהוון


class Nachla(BaseModel):
    """Complete property record for a nachla (agricultural settlement).

    Contains all intake data, ownership details, authorization status,
    and references to associated buildings and zoning plans (tabas).
    """

    # Core identification
    owner_name: str = Field(..., min_length=1, description="שם בעל הנחלה")
    moshav_name: str = Field(..., min_length=1, description="שם המושב")
    gush: int = Field(..., gt=0, description="גוש")
    helka: int = Field(..., gt=0, description="חלקה")
    num_existing_houses: int = Field(..., ge=0, description="מספר בתי מגורים קיימים")

    # Legal status
    authorization_type: AuthorizationType = Field(..., description="סוג הרשאה: בר רשות / חוכר / חוזה מהוון")
    is_capitalized: bool = Field(..., description="האם המשק מהוון")
    capitalization_track: CapitalizationTrack = Field(
        default=CapitalizationTrack.NONE, description="מסלול היוון: 3.75% / 33% / לא מהוון"
    )

    # Client goals and context
    client_goals: list[ClientGoal] = Field(..., min_length=1, description="מטרות הלקוח")
    has_intergenerational_continuity: bool = Field(..., description="רצף בין-דורי")
    ownership_type: OwnershipType = Field(..., description="מבנה בעלות")
    has_demolition_orders: bool = Field(..., description="האם קיימים צווי הריסה או הליכי אכיפה")

    # Priority area (auto-detected from moshav)
    priority_area: PriorityArea = Field(
        default=PriorityArea.NONE, description="אזור עדיפות לאומית - מזוהה אוטומטית לפי מושב"
    )

    # Prior permit fees (expert review #23: only post-2009 counts for 33% deduction)
    prior_permit_fees_purchased: float = Field(default=0, ge=0, description='דמי היתר שנרכשו בעבר (בש"ח)')
    prior_permit_fees_date: int | None = Field(
        default=None,
        ge=2000,
        le=2100,
        description="שנת רכישת דמי היתר - רק אחרי 2009 מנוכים מחישוב 33%",
    )

    # Mandatory document uploads (workflow step 0, fields #4-5)
    survey_map_path: str | None = Field(default=None, description="נתיב למפת מדידה (PDF/תמונה)")
    building_permits_paths: list[str] = Field(
        default_factory=list, description="נתיבים להיתרי בנייה (PDF/תמונות)"
    )

    # Optional documents and context
    existing_lease_pdf: str | None = Field(default=None, description="נתיב לחוזה חכירה קיים (PDF)")
    appraisal_pdf: str | None = Field(default=None, description="נתיב לשומת מקרקעין (PDF)")
    agricultural_activity: str | None = Field(default=None, description="פעילות חקלאית קיימת")
    future_plans: str | None = Field(default=None, description="תוכניות עתידיות (בנייה, מכירה, פיצול)")

    # Associated data (forward references resolved at runtime)
    buildings: list = Field(default_factory=list, description="רשימת מבנים בנחלה")
    tabas: list = Field(default_factory=list, description='רשימת תב"עות חלות')

    # Integration
    monday_item_id: str | None = Field(default=None, description="מזהה פריט ב-Monday.com")

    @field_validator("gush")
    @classmethod
    def validate_gush(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("gush must be a positive integer")
        return v

    @field_validator("helka")
    @classmethod
    def validate_helka(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("helka must be a positive integer")
        return v

    @model_validator(mode="after")
    def validate_capitalization_consistency(self) -> Nachla:
        """Ensure capitalization track matches is_capitalized flag."""
        if self.is_capitalized and self.capitalization_track == CapitalizationTrack.NONE:
            raise ValueError("capitalization_track must be set when is_capitalized is True")
        if not self.is_capitalized and self.capitalization_track != CapitalizationTrack.NONE:
            raise ValueError("capitalization_track must be 'none' when is_capitalized is False")
        return self

    @model_validator(mode="after")
    def validate_bar_reshut_split(self) -> Nachla:
        """Warn if bar reshut tries to split - cannot split without lease agreement.

        Expert review #8: bar reshut cannot split plots without first establishing
        a lease agreement (choze chachira).
        """
        if self.authorization_type == AuthorizationType.BAR_RESHUT and ClientGoal.SPLIT in self.client_goals:
            # We don't raise an error - the agent should warn the user.
            # The split goal is allowed but will require lease establishment first.
            pass
        return self

    @model_validator(mode="after")
    def validate_prior_permit_date(self) -> Nachla:
        """Validate prior permit fee date when fees are specified.

        Expert review #23: only post-2009 permit purchases are deductible
        from the 33% calculation.
        """
        if self.prior_permit_fees_purchased > 0 and self.prior_permit_fees_date is None:
            raise ValueError(
                "prior_permit_fees_date must be specified when prior_permit_fees_purchased > 0 "
                "(only post-2009 purchases are deductible from 33% calculation)"
            )
        return self

    @property
    def can_split(self) -> bool:
        """Whether the nachla can proceed with split based on authorization type."""
        return self.authorization_type != AuthorizationType.BAR_RESHUT

    @property
    def prior_fees_deductible(self) -> bool:
        """Whether prior permit fees qualify for 33% deduction (post-2009 only)."""
        return (
            self.prior_permit_fees_purchased > 0
            and self.prior_permit_fees_date is not None
            and self.prior_permit_fees_date > 2009
        )
