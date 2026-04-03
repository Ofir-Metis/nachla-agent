"""Report data models for nachla feasibility study output.

Contains the structures for building cards, audit entries, and the
complete report data that gets rendered into Word/Excel documents.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

# Mandatory disclaimers from workflow step 12 (agent_workflow_flow.md section 12.2).
# These are automatically included in every report.
MANDATORY_DISCLAIMERS: list[str] = [
    "בדיקת התכנות זו אינה מהווה תחליף לייעוץ משפטי ו/או שומה",
    "אין להסתמך עליה לכל מטרה אחרת",
    "השימוש בה נאסר על כל צד שלישי",
    (
        'הערכות העלויות מבוססות על טבלאות רמ"י בתוקף ליום {report_date}. '
        'שווי בפועל ייקבע ע"י שמאי רמ"י במועד הגשת הבקשה ועשוי להיות שונה באופן מהותי.'
    ),
    "תוקף הבדיקה: 6 חודשים ממועד הפקת הדוח.",
    'הדוח אינו מהווה התחייבות של רמ"י לביצוע העסקה בתנאים המפורטים.',
    # Priority area disclaimer is conditional - added dynamically
    "הערכת זמני תהליך: הסדרה 6-18 חודשים, פיצול 12-36 חודשים, היוון 3-12 חודשים.",
]

# Fixed disclaimers from report template section 3
REPORT_HEADER_DISCLAIMERS: list[str] = [
    "שווי הזכויות הסתמך על נתונים ב{moshav_name} משנת {data_year}",
    'הבדיקה בוצעה על סמך גבולות התב"ע הנוכחית',
    "דמי ההיתר מתעדכנים בהתאם למועד ההגשה",
    "לא בוצעה שומה למשק... סדר גודל ראשוני בלבד",
    "לא כוללת חישובי אגרות בניה מיסים והיטלים",
    'בוצעה ע"פ מפת מדידה מיום {survey_date}',
]


class BuildingCard(BaseModel):
    """Summary card for a single building in the report.

    Contains the building's status, recommended action, calculated costs,
    and specific recommendations.
    """

    building_id: int = Field(..., description="מספר מבנה")
    building_name: str = Field(..., description="שם המבנה")
    status_description: str = Field(..., description="תיאור סטטוס בעברית")
    action: str = Field(
        ...,
        description="פעולה מומלצת: regularize / agricultural / demolish / compliant",
    )
    permit_fees: float = Field(default=0, ge=0, description='דמי היתר בש"ח')
    usage_fees: float = Field(default=0, ge=0, description='דמי שימוש בש"ח')
    betterment_levy: float = Field(default=0, ge=0, description='היטל השבחה בש"ח')
    total_cost: float = Field(default=0, ge=0, description='עלות כוללת בש"ח')
    recommendations: list[str] = Field(default_factory=list, description="המלצות ספציפיות למבנה")

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        allowed = {"regularize", "agricultural", "demolish", "compliant"}
        if v not in allowed:
            raise ValueError(f"action must be one of {allowed}, got '{v}'")
        return v


class AuditEntry(BaseModel):
    """Immutable audit log entry for a single calculation or tool invocation.

    Every calculation tool must produce an AuditEntry recording its inputs,
    the formula applied, rates used, and the result.
    """

    timestamp: str = Field(..., description="ISO 8601 timestamp of the calculation")
    tool_name: str = Field(..., description="Name of the calculation tool invoked")
    inputs: dict[str, Any] = Field(..., description="Input parameters passed to the tool")
    formula: str = Field(..., description="Formula or calculation description applied")
    rates_used: dict[str, Any] = Field(..., description="Regulatory rates and constants used (from rates_config.json)")
    result: dict[str, Any] = Field(..., description="Calculation output / result")
    user_overrides: dict[str, Any] = Field(
        default_factory=dict, description="Any values manually overridden by the user"
    )
    reasoning: str = Field(default="", description="הנמקת החלטה/סיווג")
    source_reference: str = Field(default="", description='מקור הנתונים (תב"ע, היתר, טבלת שווי)')
    source_date: str | None = Field(default=None, description="תאריך מקור הנתונים")


class ActionItem(BaseModel):
    """A recommended action item for the client's TO-DO list."""

    description: str = Field(..., description="תיאור הפעולה")
    priority: int = Field(..., ge=1, le=5, description="עדיפות: 1=גבוה, 5=נמוך")
    timeline_estimate: str = Field(..., description="הערכת זמן ביצוע")
    category: str = Field(
        ..., description="קטגוריה: הסדרה / היוון / פיצול / כללי"
    )


class ReportData(BaseModel):
    """Complete report data for a nachla feasibility study.

    Aggregates all analysis results, calculations, and recommendations
    into a single structure ready for document generation.
    """

    # Core references (using Any to avoid circular import issues with forward refs)
    nachla: Any = Field(..., description="Nachla data object")
    report_date: str = Field(..., description="תאריך הפקת הדוח (ISO format)")
    report_validity_months: int = Field(default=6, ge=1, description="תוקף הדוח בחודשים")

    # Associated data
    tabas: list[Any] = Field(default_factory=list, description='רשימת תב"עות')
    buildings: list[Any] = Field(default_factory=list, description="רשימת מבנים")
    building_cards: list[BuildingCard] = Field(default_factory=list, description="כרטיסי מבנה לדוח")

    # Capitalization results
    hivun_375_result: dict[str, Any] | None = Field(default=None, description="תוצאות חישוב היוון 3.75%")
    hivun_33_result: dict[str, Any] | None = Field(default=None, description="תוצאות חישוב היוון 33%")
    hivun_comparison: dict[str, Any] | None = Field(default=None, description="השוואת מסלולי היוון")

    # Split results
    split_results: list[dict[str, Any]] = Field(default_factory=list, description="תוצאות חישוב פיצול")

    # Cost summaries
    total_regularization_cost: float = Field(default=0, ge=0, description='עלות הסדרה כוללת בש"ח')
    total_usage_fees: float = Field(default=0, ge=0, description='סה"כ דמי שימוש בש"ח')
    total_permit_fees: float = Field(default=0, ge=0, description='סה"כ דמי היתר בש"ח')

    # Study objectives (report section 2)
    study_objectives: list[str] = Field(
        default_factory=list, description="מטרות בדיקת ההתכנות (נגזר ממטרות הלקוח)"
    )

    # Disclaimers and audit
    disclaimers: list[str] = Field(
        default_factory=lambda: list(MANDATORY_DISCLAIMERS),
        description="הסתייגויות - מאוכלסות אוטומטית עם כל ההסתייגויות החובה",
    )
    audit_log: list[AuditEntry] = Field(default_factory=list, description="יומן חישובים - רישום בלתי ניתן לשינוי")
    action_items: list[ActionItem] = Field(
        default_factory=list, description="רשימת פעולות מומלצות עם עדיפויות וזמנים"
    )
    recommendations: list[str] = Field(default_factory=list, description="המלצות פעולה כלליות")
    missing_data_warnings: list[str] = Field(default_factory=list, description="אזהרות על מידע חסר")

    # Appendices (report section 11)
    annotated_survey_map_path: str | None = Field(
        default=None, description="נתיב למפת מדידה מסומנת בצבעים (ירוק/צהוב/אדום)"
    )
    appendix_building_sizes: list[dict[str, Any]] = Field(
        default_factory=list, description="טבלת גדלי מבנים (נספח - משרד החקלאות)"
    )

    def add_priority_area_disclaimer(self, priority_area: str | None = None) -> None:
        """Add the conditional priority area disclaimer.

        Args:
            priority_area: The priority area type, or None if standard area.
        """
        if priority_area and priority_area != "none":
            disclaimer = f"הנתונים כוללים הנחות אזור עדיפות {priority_area}."
        else:
            disclaimer = "הנתונים אינם כוללים הנחות אזור עדיפות."
        if disclaimer not in self.disclaimers:
            self.disclaimers.append(disclaimer)

    def format_disclaimers(self, **kwargs: str) -> list[str]:
        """Format disclaimers with actual values (report_date, moshav_name, etc.).

        Args:
            **kwargs: Template variables like report_date, moshav_name, data_year, survey_date.

        Returns:
            List of formatted disclaimer strings.
        """
        formatted: list[str] = []
        for disclaimer in self.disclaimers:
            try:
                formatted.append(disclaimer.format(**kwargs))
            except KeyError:
                formatted.append(disclaimer)
        return formatted
