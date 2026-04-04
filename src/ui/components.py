"""Custom UI components for the nachla agent Chainlit interface.

All text is in Hebrew. Chainlit renders Markdown — no raw HTML used.
"""

from __future__ import annotations

from typing import Any

import chainlit as cl

# Hebrew labels for building types
BUILDING_TYPE_LABELS: dict[str, str] = {
    "residential": "בית מגורים",
    "service": "מבנה שירות / מחסן",
    "agricultural": "מבנה חקלאי / סככה",
    "plach": 'מבנה פל"ח (עסקי)',
    "pergola": "פרגולה",
    "pool": "בריכת שחייה",
    "basement_service": "מרתף שירות",
    "basement_residential": "מרתף מגורים",
    "attic": "עליית גג",
    "ground_floor_open": "קומת עמודים פתוחה",
    "ground_floor_closed": "קומת עמודים סגורה",
    "temporary": "מבנה ארעי/קל/נייד",
    "shed_open": "סככה פתוחה",
    "pre_1965": "מבנה לפני 1965",
}

BUILDING_STATUS_LABELS: dict[str, str] = {
    "compliant": "תקין - תואם היתר",
    "deviation": "חריגה מהיתר",
    "no_permit": "ללא היתר",
    "marked_demolition": "סומן להריסה",
    "building_line_violation": "חורג מקווי בניין",
}

AUTH_TYPE_LABELS: dict[str, str] = {
    "bar_reshut": "בר רשות",
    "chocher": "חוכר לדורות",
    "choze_chachira_mehuvon": "חוזה חכירה מהוון",
}

CLIENT_GOAL_LABELS: dict[str, str] = {
    "regularization": "הסדרה",
    "capitalization": "היוון",
    "split": "פיצול",
    "all": "הכל",
}

OWNERSHIP_TYPE_LABELS: dict[str, str] = {
    "single": "בעלים יחיד",
    "partners": "שותפים",
    "heirs": "יורשים",
}

PHASE_LABELS: dict[str, str] = {
    "קליטת לקוח": "קליטת לקוח",
    'ניתוח תב"ע': 'ניתוח תב"ע',
    "מיפוי מבנים": "מיפוי מבנים",
    "אישור סיווג": "אישור סיווג",
    "חישוב עלויות": "חישוב עלויות",
    "הפקת דוח": "הפקת דוח",
}

STATUS_ICONS: dict[str, str] = {
    "pending": "[ממתין]",
    "running": "[בביצוע...]",
    "complete": "[הושלם]",
    "checkpoint": "[ממתין לאישור]",
    "failed": "[נכשל]",
}

ALLOWED_DOCUMENT_TYPES = ["application/pdf", "image/png", "image/jpeg", "image/tiff"]
ALLOWED_DOCUMENT_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"]
MAX_FILE_SIZE_MB = 50


async def display_intake_form() -> None:
    """Display the structured intake form with all 12 mandatory fields."""
    form_text = (
        "### טופס קליטת לקוח\n\n"
        "אנא שלחו את פרטי הנחלה בפורמט JSON:\n"
        "```json\n"
        "{\n"
        '  "owner_name": "שם בעל הנחלה",\n'
        '  "moshav_name": "שם המושב",\n'
        '  "gush": 1234,\n'
        '  "helka": 56,\n'
        '  "num_existing_houses": 2,\n'
        '  "authorization_type": "bar_reshut",\n'
        '  "is_capitalized": false,\n'
        '  "capitalization_track": "none",\n'
        '  "client_goals": ["regularization"],\n'
        '  "has_intergenerational_continuity": true,\n'
        '  "ownership_type": "single",\n'
        '  "has_demolition_orders": false\n'
        "}\n"
        "```\n\n"
        "**שדות חובה:**\n\n"
        "| # | שדה | סוג | אפשרויות |\n"
        "|---|------|------|----------|\n"
        "| 1 | שם בעל הנחלה (owner_name) | טקסט | - |\n"
        "| 2 | שם המושב (moshav_name) | טקסט | - |\n"
        "| 3 | גוש (gush) | מספר | - |\n"
        "| 4 | חלקה (helka) | מספר | - |\n"
        "| 5 | מספר בתי מגורים קיימים (num_existing_houses) | מספר | - |\n"
        "| 6 | סוג הרשאה (authorization_type) | בחירה | bar_reshut / chocher / choze_chachira_mehuvon |\n"
        "| 7 | האם מהוון (is_capitalized) | כן/לא | true / false |\n"
        "| 8 | מסלול היוון (capitalization_track) | בחירה | 375 / 33 / none |\n"
        "| 9 | מטרות הלקוח (client_goals) | רשימה | regularization / capitalization / split / all |\n"
        "| 10 | רצף בין-דורי (has_intergenerational_continuity) | כן/לא | true / false |\n"
        "| 11 | מבנה בעלות (ownership_type) | בחירה | single / partners / heirs |\n"
        "| 12 | צווי הריסה (has_demolition_orders) | כן/לא | true / false |\n\n"
        "**לאחר שליחת הנתונים, תתבקשו להעלות קבצים:**\n"
        "- מפת מדידה (PDF / תמונה)\n"
        "- היתרי בנייה (PDF / תמונות)\n"
        "- חוזה חכירה (אם קיים)\n"
        "- שומת מקרקעין (אם קיימת)"
    )

    await cl.Message(content=form_text).send()


async def request_file_uploads() -> None:
    """Request file uploads from the user with Hebrew instructions."""
    upload_text = (
        "### העלאת מסמכים\n\n"
        "אנא העלו את המסמכים הבאים:\n\n"
        "**חובה:**\n"
        "- מפת מדידה (PDF או תמונה)\n"
        "- היתרי בנייה (PDF או תמונות)\n\n"
        "**אופציונלי:**\n"
        "- חוזה חכירה קיים (PDF)\n"
        "- שומת מקרקעין (PDF)\n\n"
        f"*פורמטים נתמכים: PDF, PNG, JPG, TIFF. גודל מקסימלי: {MAX_FILE_SIZE_MB} MB*"
    )

    await cl.Message(content=upload_text).send()


def validate_uploaded_file(file_name: str, file_size_bytes: int, mime_type: str | None) -> tuple[bool, str]:
    """Validate an uploaded file by type and size.

    Returns:
        Tuple of (is_valid, error_message_hebrew). Error message is empty if valid.
    """
    ext = ""
    if "." in file_name:
        ext = "." + file_name.rsplit(".", 1)[-1].lower()

    if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
        return False, (f'סוג הקובץ "{ext}" אינו נתמך. הפורמטים הנתמכים: {", ".join(ALLOWED_DOCUMENT_EXTENSIONS)}')

    if mime_type and mime_type not in ALLOWED_DOCUMENT_TYPES:
        return False, f'סוג קובץ MIME "{mime_type}" אינו נתמך.'

    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size_bytes > max_bytes:
        size_mb = file_size_bytes / (1024 * 1024)
        return False, (f"הקובץ גדול מדי ({size_mb:.1f} MB). גודל מקסימלי מותר: {MAX_FILE_SIZE_MB} MB")

    return True, ""


async def display_classification_table(buildings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Display building classifications for user review (checkpoint step 3.4)."""
    table_md = format_building_table(buildings)

    total = len(buildings)
    residential = sum(1 for b in buildings if b.get("building_type") == "residential")
    service = sum(1 for b in buildings if b.get("building_type") == "service")
    agricultural = sum(1 for b in buildings if b.get("building_type") == "agricultural")
    deviations = sum(1 for b in buildings if b.get("status") == "deviation")
    no_permit = sum(1 for b in buildings if b.get("status") == "no_permit")

    summary = (
        "### סיווג מבנים - נקודת אישור\n\n"
        f"זיהיתי **{total}** מבנים: "
        f"{residential} בתי מגורים, {service} שירות, {agricultural} חקלאי\n\n"
    )

    if deviations > 0:
        summary += f"מבנים חריגים: **{deviations}**\n\n"
    if no_permit > 0:
        summary += f"מבנים ללא היתר: **{no_permit}**\n\n"

    summary += (
        table_md + "\n\n"
        "**האם הסיווג נכון?**\n\n"
        'השיבו "כן" / "אישור" לאישור הסיווג.\n'
        "לתיקון, שלחו JSON עם השינויים, לדוגמה:\n"
        '```json\n{"building_id": 3, "building_type": "agricultural"}\n```'
    )

    await cl.Message(content=summary).send()
    return buildings


async def display_progress_step(phase: str, description: str, status: str) -> None:
    """Show a workflow step with status indicator."""
    icon = STATUS_ICONS.get(status, "[?]")
    step_text = f"**{icon} {phase}**: {description}"
    await cl.Message(content=step_text).send()


async def display_report_summary(report_data: dict[str, Any]) -> None:
    """Show report summary before generation (workflow step 13)."""
    cost_summary = format_cost_summary(report_data)

    buildings = report_data.get("buildings", [])
    total_buildings = len(buildings)
    total_deviations = sum(
        1 for b in buildings if isinstance(b, dict) and b.get("status") in ("deviation", "no_permit")
    )

    total_cost = report_data.get("total_regularization_cost", 0)

    summary_text = (
        "### סיכום לפני הפקת דוח\n\n"
        f"מצאתי **{total_buildings}** מבנים, "
        f"מתוכם **{total_deviations}** חריגים\n\n"
        f'עלות הסדרה מוערכת: **{total_cost:,.0f} ש"ח**\n\n'
    )

    hivun_375 = report_data.get("hivun_375_result")
    hivun_33 = report_data.get("hivun_33_result")
    if hivun_375 and hivun_33:
        cost_375 = hivun_375.get("total_cost", 0) if isinstance(hivun_375, dict) else 0
        cost_33 = hivun_33.get("total_cost", 0) if isinstance(hivun_33, dict) else 0
        summary_text += (
            f'עלות היוון 3.75%: **{cost_375:,.0f} ש"ח**\n\n'
            f'עלות היוון 33%: **{cost_33:,.0f} ש"ח**\n\n'
        )

    summary_text += cost_summary + "\n\n"
    summary_text += '**האם לייצר את הדוח המלא?**\n\nהשיבו "כן" להפקת הדוח או "לא" לביטול.'

    await cl.Message(content=summary_text).send()


async def display_download_links(files: dict[str, str]) -> None:
    """Show download buttons for generated reports."""
    file_labels: dict[str, str] = {
        "word": "דוח בדיקת התכנות (Word)",
        "excel": "טבלת תחשיבים (Excel)",
        "audit": "יומן חישובים (Audit Log)",
        "pdf": "סיכום מנהלים (PDF)",
    }

    elements: list[cl.File] = []
    for file_type, file_path in files.items():
        label = file_labels.get(file_type, file_type)
        elements.append(cl.File(name=label, path=file_path, display="inline"))

    await cl.Message(content="### הורדת דוחות\n\nהדוחות הבאים מוכנים להורדה:", elements=elements).send()


async def display_monday_link(item_id: str, board_name: str = "") -> None:
    """Display a link to the Monday.com item."""
    board_info = f" ({board_name})" if board_name else ""
    await cl.Message(content=f"פריט Monday.com{board_info}: **#{item_id}**").send()


async def display_cloud_upload_status(
    service: str, success: bool, url: str | None = None, error: str | None = None
) -> None:
    """Display cloud storage upload status."""
    service_labels = {
        "google_drive": "Google Drive",
        "onedrive": "OneDrive",
    }
    service_name = service_labels.get(service, service)

    if success:
        link_part = f" - [קישור]({url})" if url else ""
        await cl.Message(content=f"[הושלם] העלאה ל-{service_name} הצליחה{link_part}").send()
    else:
        error_part = f": {error}" if error else ""
        await cl.Message(content=f"[נכשל] העלאה ל-{service_name} נכשלה{error_part}").send()


def format_building_table(buildings: list[dict[str, Any]]) -> str:
    """Format buildings as a markdown table."""
    if not buildings:
        return "לא נמצאו מבנים."

    header = "| # | שם מבנה | סוג | סטטוס | שטח עיקרי | שטח כולל | חריגה |\n"
    separator = "|---|---------|------|--------|-----------|----------|-------|\n"

    rows = []
    for b in buildings:
        bid = b.get("id", "?")
        name = b.get("name", "-")
        btype = BUILDING_TYPE_LABELS.get(b.get("building_type", ""), b.get("building_type", "-"))
        status = BUILDING_STATUS_LABELS.get(b.get("status", ""), b.get("status", "-"))
        main_area = b.get("main_area_sqm", 0)
        total_area = b.get("total_area_sqm", main_area)
        deviation = b.get("deviation_sqm", 0) or 0

        deviation_str = f'{deviation:.0f} מ"ר' if deviation > 0 else "-"

        rows.append(
            f'| {bid} | {name} | {btype} | {status} | {main_area:.0f} מ"ר | {total_area:.0f} מ"ר | {deviation_str} |'
        )

    return header + separator + "\n".join(rows)


def format_cost_summary(report_data: dict[str, Any]) -> str:
    """Format cost summary as markdown."""
    total_regularization = report_data.get("total_regularization_cost", 0)
    total_usage = report_data.get("total_usage_fees", 0)
    total_permit = report_data.get("total_permit_fees", 0)

    building_cards = report_data.get("building_cards", [])

    summary = "**סיכום עלויות:**\n\n"
    summary += "| פריט | סכום |\n"
    summary += "|------|------|\n"
    summary += f'| דמי היתר | {total_permit:,.0f} ש"ח |\n'
    summary += f'| דמי שימוש | {total_usage:,.0f} ש"ח |\n'
    summary += f'| **סה"כ הסדרה** | **{total_regularization:,.0f} ש"ח** |\n'

    if building_cards:
        summary += "\n**פירוט לפי מבנה:**\n\n"
        summary += '| מבנה | דמי היתר | דמי שימוש | סה"כ |\n'
        summary += "|------|----------|-----------|------|\n"

        for card in building_cards:
            if isinstance(card, dict):
                name = card.get("building_name", "?")
                permit = card.get("permit_fees", 0)
                usage = card.get("usage_fees", 0)
                total = card.get("total_cost", 0)
                summary += f"| {name} | {permit:,.0f} | {usage:,.0f} | {total:,.0f} |\n"

    return summary
