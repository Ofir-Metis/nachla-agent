"""Chainlit chat UI for nachla feasibility studies.

Hebrew RTL interface with:
- Structured intake form
- File upload for survey maps, permits, reference tables
- Agent streaming with step-by-step progress
- Classification checkpoint (interactive confirmation)
- Report download (Word, Excel, Audit Log)

NOTE: Chainlit renders Markdown, not raw HTML. All messages use Markdown formatting.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import chainlit as cl

from ui.components import (
    display_classification_table,
    display_download_links,
    display_intake_form,
    display_progress_step,
    display_report_summary,
    validate_uploaded_file,
)

logger = logging.getLogger(__name__)

# Workflow phase constants
PHASE_INTAKE = "intake"
PHASE_TABA = "taba_analysis"
PHASE_MAPPING = "building_mapping"
PHASE_CLASSIFICATION = "classification_checkpoint"
PHASE_CALCULATIONS = "calculations"
PHASE_REPORT = "report_generation"


@cl.on_chat_start
async def on_chat_start() -> None:
    """Initialize chat session with Hebrew welcome and intake form."""
    cl.user_session.set("phase", PHASE_INTAKE)
    cl.user_session.set("intake_data", None)
    cl.user_session.set("buildings", None)
    cl.user_session.set("classification_confirmed", False)
    cl.user_session.set("report_data", None)
    cl.user_session.set("uploaded_files", {})

    welcome_text = (
        "## ברוכים הבאים למערכת בדיקת התכנות נחלות\n\n"
        'מערכת זו מבצעת בדיקת התכנות לנחלות חקלאיות, כולל ניתוח תב"ע, '
        "מיפוי מבנים, חישוב עלויות, והפקת דוחות מקצועיים.\n\n"
        "**כדי להתחיל, אנא מלאו את טופס קליטת הלקוח.**"
    )

    await cl.Message(content=welcome_text).send()
    await display_intake_form()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Handle user messages and drive the workflow."""
    phase = cl.user_session.get("phase")

    if phase == PHASE_INTAKE:
        await _handle_intake_message(message)
    elif phase == PHASE_CLASSIFICATION:
        await _handle_classification_response(message)
    elif phase == PHASE_REPORT:
        await _handle_report_confirmation(message)
    else:
        await cl.Message(content="המערכת מעבדת את הנתונים. אנא המתינו.").send()


async def _handle_intake_message(message: cl.Message) -> None:
    """Process intake form responses and file uploads."""
    session_data: dict[str, Any] = cl.user_session.get("intake_data") or {}

    text = message.content.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            session_data.update(parsed)
            cl.user_session.set("intake_data", session_data)
    except (json.JSONDecodeError, ValueError):
        pass

    if message.elements:
        uploaded = cl.user_session.get("uploaded_files") or {}
        for element in message.elements:
            if hasattr(element, "path") and element.path:
                file_name = element.name if hasattr(element, "name") else "unknown"
                file_size = os.path.getsize(element.path) if os.path.exists(element.path) else 0
                mime_type = getattr(element, "mime", None)
                is_valid, error_msg = validate_uploaded_file(file_name, file_size, mime_type)
                if not is_valid:
                    await cl.Message(content=error_msg).send()
                    continue
                uploaded[file_name] = element.path
                await cl.Message(content=f'הקובץ "{file_name}" התקבל בהצלחה.').send()
        cl.user_session.set("uploaded_files", uploaded)

    required_fields = [
        "owner_name",
        "moshav_name",
        "gush",
        "helka",
        "num_existing_houses",
        "authorization_type",
        "is_capitalized",
        "capitalization_track",
        "client_goals",
        "has_intergenerational_continuity",
        "ownership_type",
        "has_demolition_orders",
    ]

    missing = [f for f in required_fields if f not in session_data]
    if missing:
        await _prompt_missing_fields(missing)
    else:
        await _start_processing(session_data)


async def _prompt_missing_fields(missing: list[str]) -> None:
    """Ask user for missing intake fields in Hebrew."""
    field_labels: dict[str, str] = {
        "owner_name": "שם בעל הנחלה",
        "moshav_name": "שם המושב",
        "gush": "גוש",
        "helka": "חלקה",
        "num_existing_houses": "מספר בתי מגורים קיימים",
        "authorization_type": "סוג הרשאה (bar_reshut / chocher / choze_chachira_mehuvon)",
        "is_capitalized": "האם המשק מהוון (true/false)",
        "capitalization_track": "מסלול היוון (375 / 33 / none)",
        "client_goals": "מטרות הלקוח (regularization / capitalization / split / all)",
        "has_intergenerational_continuity": "האם קיים רצף בין-דורי (true/false)",
        "ownership_type": "מבנה בעלות (single / partners / heirs)",
        "has_demolition_orders": "האם קיימים צווי הריסה (true/false)",
    }
    missing_labels = [field_labels.get(f, f) for f in missing]
    fields_text = "\n".join(f"- {label}" for label in missing_labels)

    await cl.Message(
        content=(
            "**חסרים הפרטים הבאים:**\n\n"
            f"{fields_text}\n\n"
            "אנא שלחו את הנתונים כ-JSON, לדוגמה:\n"
            '```json\n{"owner_name": "ישראל ישראלי", "moshav_name": "כפר ורבורג"}\n```'
        )
    ).send()


async def _start_processing(intake_data: dict[str, Any]) -> None:
    """Begin the agent workflow after intake is complete."""
    cl.user_session.set("phase", PHASE_TABA)

    await cl.Message(
        content=(
            "**קליטת הנתונים הושלמה בהצלחה.**\n\n"
            f"לקוח: {intake_data.get('owner_name', '')}\n"
            f"מושב: {intake_data.get('moshav_name', '')}\n"
            f"גוש/חלקה: {intake_data.get('gush', '')}/{intake_data.get('helka', '')}\n\n"
            "מתחיל בעיבוד..."
        )
    ).send()

    await display_progress_step(
        phase="קליטת לקוח",
        description="נתוני הלקוח נקלטו בהצלחה",
        status="complete",
    )

    await display_progress_step(
        phase='ניתוח תב"ע',
        description='מזהה תב"עות חלות על הנחלה...',
        status="running",
    )


async def _handle_classification_response(message: cl.Message) -> None:
    """Handle user response to classification checkpoint."""
    text = message.content.strip().lower()
    buildings = cl.user_session.get("buildings") or []

    if text in ("כן", "אישור", "מאשר", "נכון", "yes", "confirm"):
        for building in buildings:
            building["user_confirmed"] = True

        cl.user_session.set("buildings", buildings)
        cl.user_session.set("classification_confirmed", True)
        cl.user_session.set("phase", PHASE_CALCULATIONS)

        await cl.Message(
            content="**סיווג המבנים אושר.** ממשיך לחישוב עלויות..."
        ).send()

        await display_progress_step(
            phase="אישור סיווג",
            description="סיווג מבנים אושר על ידי המשתמש",
            status="complete",
        )

        await display_progress_step(
            phase="חישוב עלויות",
            description="מחשב דמי היתר, דמי שימוש, והיוון...",
            status="running",
        )

    else:
        try:
            corrections = json.loads(text)
            if isinstance(corrections, list):
                buildings = corrections
            elif isinstance(corrections, dict):
                bid = corrections.get("building_id") or corrections.get("id")
                for b in buildings:
                    if b.get("id") == bid:
                        b.update(corrections)
                        break
            cl.user_session.set("buildings", buildings)
            await display_classification_table(buildings)

        except (json.JSONDecodeError, ValueError):
            await cl.Message(
                content=(
                    "לא הצלחתי לפרש את התיקון. אנא שלחו:\n"
                    '- "כן" / "אישור" לאישור הסיווג\n'
                    "- JSON עם תיקונים, לדוגמה:\n"
                    '```json\n{"building_id": 3, "building_type": "agricultural"}\n```'
                )
            ).send()


async def _handle_report_confirmation(message: cl.Message) -> None:
    """Handle user confirmation to generate the final report."""
    text = message.content.strip().lower()

    if text in ("כן", "אישור", "מאשר", "yes", "confirm"):
        cl.user_session.set("phase", "generating")

        await display_progress_step(
            phase="הפקת דוח",
            description="מייצר דוח Word, טבלת Excel, ויומן חישובים...",
            status="running",
        )

        await cl.Message(content="**הדוח הופק בהצלחה.**").send()

        await display_download_links(
            {
                "word": "output/report.docx",
                "excel": "output/calculations.xlsx",
                "audit": "output/audit_log.json",
            }
        )

    elif text in ("לא", "ביטול", "no", "cancel"):
        await cl.Message(content="הפקת הדוח בוטלה. ניתן לבצע שינויים ולנסות שוב.").send()
    else:
        await cl.Message(content='אנא השיבו "כן" להפקת הדוח או "לא" לביטול.').send()


async def present_classification_checkpoint(buildings: list[dict[str, Any]]) -> None:
    """Present the classification checkpoint to the user.

    CRITICAL: This is the mandatory checkpoint from workflow step 3.4.
    Must wait for explicit user confirmation before proceeding.
    """
    cl.user_session.set("buildings", buildings)
    cl.user_session.set("phase", PHASE_CLASSIFICATION)
    cl.user_session.set("classification_confirmed", False)

    await display_progress_step(
        phase="אישור סיווג",
        description="ממתין לאישור סיווג מבנים",
        status="checkpoint",
    )

    await display_classification_table(buildings)


async def present_report_summary(report_data: dict[str, Any]) -> None:
    """Present report summary for user approval before generation."""
    cl.user_session.set("report_data", report_data)
    cl.user_session.set("phase", PHASE_REPORT)

    await display_report_summary(report_data)


@cl.on_settings_update
async def on_settings_update(settings: dict[str, Any]) -> None:
    """Handle settings changes."""
    cl.user_session.set("settings", settings)
    logger.info("Settings updated: %s", list(settings.keys()))
