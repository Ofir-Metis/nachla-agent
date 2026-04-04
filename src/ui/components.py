"""Custom UI components for the nachla agent Chainlit interface.

All text is in Hebrew. Components handle RTL display.
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

# Hebrew labels for building status
BUILDING_STATUS_LABELS: dict[str, str] = {
    "compliant": "תקין - תואם היתר",
    "deviation": "חריגה מהיתר",
    "no_permit": "ללא היתר",
    "marked_demolition": "סומן להריסה",
    "building_line_violation": "חורג מקווי בניין",
}

# Hebrew labels for authorization types
AUTH_TYPE_LABELS: dict[str, str] = {
    "bar_reshut": "בר רשות",
    "chocher": "חוכר לדורות",
    "choze_chachira_mehuvon": "חוזה חכירה מהוון",
}

# Hebrew labels for client goals
CLIENT_GOAL_LABELS: dict[str, str] = {
    "regularization": "הסדרה",
    "capitalization": "היוון",
    "split": "פיצול",
    "all": "הכל",
}

# Hebrew labels for ownership types
OWNERSHIP_TYPE_LABELS: dict[str, str] = {
    "single": "בעלים יחיד",
    "partners": "שותפים",
    "heirs": "יורשים",
}

# Hebrew labels for workflow phases
PHASE_LABELS: dict[str, str] = {
    "קליטת לקוח": "קליטת לקוח",
    'ניתוח תב"ע': 'ניתוח תב"ע',
    "מיפוי מבנים": "מיפוי מבנים",
    "אישור סיווג": "אישור סיווג",
    "חישוב עלויות": "חישוב עלויות",
    "הפקת דוח": "הפקת דוח",
}

# Status indicators
STATUS_ICONS: dict[str, str] = {
    "pending": "[ממתין]",
    "running": "[בביצוע...]",
    "complete": "[הושלם]",
    "checkpoint": "[ממתין לאישור]",
    "failed": "[נכשל]",
}

# File upload constraints
ALLOWED_DOCUMENT_TYPES = ["application/pdf", "image/png", "image/jpeg", "image/tiff"]
ALLOWED_DOCUMENT_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"]
MAX_FILE_SIZE_MB = 50


async def display_intake_form() -> None:
    """Display the structured intake form and collect responses.

    Presents all 12 mandatory fields plus optional fields as a guided
    Hebrew form using Chainlit message interactions.
    """
    form_text = (
        '<div dir="rtl" style="text-align: right;">'
        "<h3>טופס קליטת לקוח</h3>"
        "<p>אנא שלחו את פרטי הנחלה בפורמט JSON:</p>"
        "```json\n"
        "{\n"
        '  "owner_name": "שם בעל הנחלה",\n'
        '  "moshav_name": "שם המושב",\n'
        '  "gush": 1234,\n'
        '  "helka": 56,\n'
        '  "num_existing_houses": 2,\n'
        '  "authorization_type": "bar_reshut",\n'
        '  "is_capitalized": false,\n'
        '  "client_goals": ["regularization"],\n'
        '  "has_intergenerational_continuity": true,\n'
        '  "ownership_type": "single",\n'
        '  "has_demolition_orders": false\n'
        "}\n"
        "```\n\n"
        "<strong>שדות חובה:</strong>\n"
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
        "<strong>לאחר שליחת הנתונים, תתבקשו להעלות קבצים:</strong>\n"
        "- מפת מדידה (PDF / תמונה)\n"
        "- היתרי בנייה (PDF / תמונות)\n"
        "- חוזה חכירה (אם קיים)\n"
        "- שומת מקרקעין (אם קיימת)\n"
        "</div>"
    )

    await cl.Message(content=form_text).send()


async def request_file_uploads() -> None:
    """Request file uploads from the user with Hebrew instructions.

    Prompts for survey map and building permits (mandatory),
    plus optional lease agreement and appraisal.
    """
    upload_text = (
        '<div dir="rtl" style="text-align: right;">'
        "<h3>העלאת מסמכים</h3>"
        "<p>אנא העלו את המסמכים הבאים:</p>"
        "<strong>חובה:</strong>\n"
        "- מפת מדידה (PDF או תמונה)\n"
        "- היתרי בנייה (PDF או תמונות)\n\n"
        "<strong>אופציונלי:</strong>\n"
        "- חוזה חכירה קיים (PDF)\n"
        "- שומת מקרקעין (PDF)\n\n"
        f"<em>פורמטים נתמכים: PDF, PNG, JPG, TIFF. גודל מקסימלי: {MAX_FILE_SIZE_MB} MB</em>"
        "</div>"
    )

    await cl.Message(content=upload_text).send()


def validate_uploaded_file(file_name: str, file_size_bytes: int, mime_type: str | None) -> tuple[bool, str]:
    """Validate an uploaded file by type and size.

    Args:
        file_name: Name of the uploaded file.
        file_size_bytes: Size in bytes.
        mime_type: MIME type of the file, or None.

    Returns:
        Tuple of (is_valid, error_message_hebrew). Error message is empty if valid.
    """
    # Check file extension
    ext = ""
    if "." in file_name:
        ext = "." + file_name.rsplit(".", 1)[-1].lower()

    if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
        return False, (f'סוג הקובץ "{ext}" אינו נתמך. הפורמטים הנתמכים: {", ".join(ALLOWED_DOCUMENT_EXTENSIONS)}')

    # Check MIME type if available
    if mime_type and mime_type not in ALLOWED_DOCUMENT_TYPES:
        return False, f'סוג קובץ MIME "{mime_type}" אינו נתמך.'

    # Check file size
    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size_bytes > max_bytes:
        size_mb = file_size_bytes / (1024 * 1024)
        return False, (f"הקובץ גדול מדי ({size_mb:.1f} MB). גודל מקסימלי מותר: {MAX_FILE_SIZE_MB} MB")

    return True, ""


async def display_classification_table(buildings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Display building classifications for user review.

    Shows a table where user can review and modify building types.
    Returns updated building list after user confirmation.

    CRITICAL: This is the mandatory checkpoint from workflow step 3.4.
    Must wait for explicit user confirmation before proceeding.

    Args:
        buildings: List of building dicts with classification data.

    Returns:
        The buildings list (possibly updated by user).
    """
    table_md = format_building_table(buildings)

    # Count statistics
    total = len(buildings)
    residential = sum(1 for b in buildings if b.get("building_type") == "residential")
    service = sum(1 for b in buildings if b.get("building_type") == "service")
    agricultural = sum(1 for b in buildings if b.get("building_type") == "agricultural")
    deviations = sum(1 for b in buildings if b.get("status") == "deviation")
    no_permit = sum(1 for b in buildings if b.get("status") == "no_permit")

    summary = (
        '<div dir="rtl" style="text-align: right;">'
        "<h3>סיווג מבנים - נקודת אישור</h3>"
        f"<p>זיהיתי <strong>{total}</strong> מבנים: "
        f"{residential} בתי מגורים, {service} שירות, {agricultural} חקלאי</p>"
    )

    if deviations > 0:
        summary += f"<p>מבנים חריגים: <strong>{deviations}</strong></p>"
    if no_permit > 0:
        summary += f"<p>מבנים ללא היתר: <strong>{no_permit}</strong></p>"

    summary += (
        "\n\n" + table_md + "\n\n"
        "<strong>האם הסיווג נכון?</strong>\n\n"
        'השיבו "כן" / "אישור" לאישור הסיווג.\n'
        "לתיקון, שלחו JSON עם השינויים, לדוגמה:\n"
        '```json\n{"building_id": 3, "building_type": "agricultural"}\n```'
        "</div>"
    )

    await cl.Message(content=summary).send()
    return buildings


async def display_progress_step(phase: str, description: str, status: str) -> None:
    """Show a workflow step with status indicator.

    Args:
        phase: Phase name in Hebrew.
        description: Description of current activity.
        status: One of 'pending', 'running', 'complete', 'checkpoint', 'failed'.
    """
    icon = STATUS_ICONS.get(status, "[?]")

    step_text = f'<div dir="rtl" style="text-align: right;"><strong>{icon} {phase}</strong>: {description}</div>'

    await cl.Message(content=step_text).send()


async def display_report_summary(report_data: dict[str, Any]) -> None:
    """Show report summary before generation (workflow step 13).

    Displays building count, deviation count, total costs, and
    capitalization comparison. Asks for user confirmation.

    Args:
        report_data: Complete report data dict.
    """
    cost_summary = format_cost_summary(report_data)

    buildings = report_data.get("buildings", [])
    total_buildings = len(buildings)
    total_deviations = sum(
        1 for b in buildings if isinstance(b, dict) and b.get("status") in ("deviation", "no_permit")
    )

    total_cost = report_data.get("total_regularization_cost", 0)

    summary_text = (
        '<div dir="rtl" style="text-align: right;">'
        "<h3>סיכום לפני הפקת דוח</h3>"
        f"<p>מצאתי <strong>{total_buildings}</strong> מבנים, "
        f"מתוכם <strong>{total_deviations}</strong> חריגים</p>"
        f'<p>עלות הסדרה מוערכת: <strong>{total_cost:,.0f} ש"ח</strong></p>'
    )

    # Capitalization comparison
    hivun_375 = report_data.get("hivun_375_result")
    hivun_33 = report_data.get("hivun_33_result")
    if hivun_375 and hivun_33:
        cost_375 = hivun_375.get("total_cost", 0) if isinstance(hivun_375, dict) else 0
        cost_33 = hivun_33.get("total_cost", 0) if isinstance(hivun_33, dict) else 0
        summary_text += (
            f'<p>עלות היוון 3.75%: <strong>{cost_375:,.0f} ש"ח</strong></p>'
            f'<p>עלות היוון 33%: <strong>{cost_33:,.0f} ש"ח</strong></p>'
        )

    summary_text += "\n\n" + cost_summary + "\n\n"

    summary_text += '<strong>האם לייצר את הדוח המלא?</strong>\n\nהשיבו "כן" להפקת הדוח או "לא" לביטול.</div>'

    await cl.Message(content=summary_text).send()


async def display_download_links(files: dict[str, str]) -> None:
    """Show download buttons for generated reports.

    Args:
        files: Dict mapping file type to file path.
            Keys: 'word', 'excel', 'audit'
    """
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

    download_text = (
        '<div dir="rtl" style="text-align: right;"><h3>הורדת דוחות</h3><p>הדוחות הבאים מוכנים להורדה:</p></div>'
    )

    await cl.Message(content=download_text, elements=elements).send()


async def display_monday_link(item_id: str, board_name: str = "") -> None:
    """Display a link to the Monday.com item.

    Args:
        item_id: Monday.com item ID.
        board_name: Optional board name for display.
    """
    board_info = f" ({board_name})" if board_name else ""
    link_text = (
        '<div dir="rtl" style="text-align: right;">'
        f"<p>פריט Monday.com{board_info}: "
        f"<strong>#{item_id}</strong></p>"
        "</div>"
    )

    await cl.Message(content=link_text).send()


async def display_cloud_upload_status(
    service: str, success: bool, url: str | None = None, error: str | None = None
) -> None:
    """Display cloud storage upload status.

    Args:
        service: Cloud service name ('google_drive' or 'onedrive').
        success: Whether upload succeeded.
        url: URL to uploaded file if successful.
        error: Error message if failed.
    """
    service_labels = {
        "google_drive": "Google Drive",
        "onedrive": "OneDrive",
    }
    service_name = service_labels.get(service, service)

    if success:
        link_part = f' - <a href="{url}">קישור</a>' if url else ""
        status_text = (
            f'<div dir="rtl" style="text-align: right;"><p>[הושלם] העלאה ל-{service_name} הצליחה{link_part}</p></div>'
        )
    else:
        error_part = f": {error}" if error else ""
        status_text = (
            f'<div dir="rtl" style="text-align: right;"><p>[נכשל] העלאה ל-{service_name} נכשלה{error_part}</p></div>'
        )

    await cl.Message(content=status_text).send()


def format_building_table(buildings: list[dict[str, Any]]) -> str:
    """Format buildings as a Hebrew markdown table for display.

    Args:
        buildings: List of building dicts.

    Returns:
        Markdown table string with RTL direction.
    """
    if not buildings:
        return '<div dir="rtl">לא נמצאו מבנים.</div>'

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
    """Format cost summary as Hebrew markdown for display.

    Args:
        report_data: Report data dict with cost fields.

    Returns:
        Markdown formatted cost summary.
    """
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
