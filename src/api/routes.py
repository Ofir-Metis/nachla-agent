"""API routes for the nachla agent backend.

All endpoints return JSON. File uploads via multipart/form-data.
Error responses include Hebrew messages for user-facing errors.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

# File upload constraints
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


# --- Request/Response Models ---


class IntakeRequest(BaseModel):
    """Intake form data matching Nachla model fields."""

    owner_name: str = Field(..., min_length=1, description="שם בעל הנחלה")
    moshav_name: str = Field(..., min_length=1, description="שם המושב")
    gush: int = Field(..., gt=0, description="גוש")
    helka: int = Field(..., gt=0, description="חלקה")
    num_existing_houses: int = Field(..., ge=0, description="מספר בתי מגורים קיימים")
    authorization_type: str = Field(..., description="סוג הרשאה: bar_reshut / chocher / choze_chachira_mehuvon")
    is_capitalized: bool = Field(..., description="האם המשק מהוון")
    capitalization_track: str = Field(default="none", description="מסלול היוון: 375 / 33 / none")
    client_goals: list[str] = Field(..., min_length=1, description="מטרות הלקוח")
    has_intergenerational_continuity: bool = Field(..., description="האם קיים רצף בין-דורי")
    ownership_type: str = Field(..., description="מבנה בעלות: single / partners / heirs")
    has_demolition_orders: bool = Field(..., description="האם קיימים צווי הריסה")

    # Optional fields
    priority_area: str = Field(default="none", description="אזור עדיפות: none / A / B / frontline")
    prior_permit_fees_purchased: float = Field(default=0, ge=0, description='דמי היתר שנרכשו בעבר (בש"ח)')
    prior_permit_fees_date: int | None = Field(default=None, description="שנת רכישת דמי היתר")
    agricultural_activity: str | None = Field(default=None, description="פעילות חקלאית קיימת")
    future_plans: str | None = Field(default=None, description="תוכניות עתידיות")
    monday_item_id: str | None = Field(default=None, description="מזהה פריט ב-Monday.com")

    # Pre-extracted data from /api/v1/extract (validated by user before submission)
    pre_extracted_buildings: list[dict[str, Any]] | None = Field(default=None, description="מבנים שזוהו מהמסמכים ואושרו ע\"י המשתמש")
    pre_extracted_tabas: list[dict[str, Any]] | None = Field(default=None, description='תב"עות שזוהו מהמסמכים')


class JobStatusResponse(BaseModel):
    """Job status response."""

    job_id: str
    status: str  # pending, running, checkpoint, generating, complete, failed
    phase: str
    progress_percent: int = Field(ge=0, le=100)
    message: str  # Hebrew status message
    sub_steps: list[dict[str, str]] = Field(default_factory=list)


class BuildingConfirmItem(BaseModel):
    """A single building item in the classification confirmation request."""

    id: int
    building_type: str = Field(..., description="סוג מבנה - ערכי BuildingType")
    status: str = Field(..., description="סטטוס מבנה - ערכי BuildingStatus")
    main_area_sqm: float = Field(ge=0, description='שטח עיקרי במ"ר')
    name: str = ""
    basement_type: str | None = None
    pergola_roof_type: str | None = None
    is_pre_1965: bool = False


class ClassificationConfirmRequest(BaseModel):
    """Request body for confirming building classifications."""

    buildings: list[BuildingConfirmItem] = Field(..., description="רשימת מבנים עם סיווג מאושר")


class JobCreateResponse(BaseModel):
    """Response from job creation."""

    job_id: str
    status: str
    message: str


class FileUploadResponse(BaseModel):
    """Response from file upload."""

    job_id: str
    files_received: int
    file_names: list[str]
    message: str


class BuildingsResponse(BaseModel):
    """Response containing the building list for classification checkpoint."""

    job_id: str
    buildings: list[dict[str, Any]]
    count: int


class CloudExportFile(BaseModel):
    """A single file exported to cloud storage."""

    service: str
    file: str
    link: str


class CloudExportError(BaseModel):
    """An error during cloud export."""

    service: str
    error: str


class CloudExportResponse(BaseModel):
    """Response from cloud export operation."""

    status: str
    message: str
    target: str
    files: list[CloudExportFile] = Field(default_factory=list)
    errors: list[CloudExportError] = Field(default_factory=list)


class ResultsResponse(BaseModel):
    """Response containing cost summary for the results page."""

    job_id: str
    total_regularization_cost: float = 0
    total_usage_fees: float = 0
    total_permit_fees: float = 0
    betterment_levy: float = 0
    hivun_375_total: float | None = None
    hivun_33_total: float | None = None
    building_cards: list[dict[str, Any]] = []
    download_types: list[str] = []


class DocumentClassification(BaseModel):
    """AI classification result for a single uploaded document."""

    filename: str = ""
    detected_type: str = ""
    is_relevant: bool = True
    confidence: str = "medium"
    note: str = ""


class ExtractionResponse(BaseModel):
    """Response from document extraction (AI analysis of uploaded files)."""

    buildings: list[dict[str, Any]] = Field(default_factory=list)
    tabas: list[dict[str, Any]] = Field(default_factory=list)
    building_count: int = 0
    taba_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    document_classifications: list[DocumentClassification] = Field(default_factory=list)


# --- Helper Functions ---


def _get_job_queue(request: Request) -> Any:
    """Get the job queue from the app state.

    Args:
        request: FastAPI request object.

    Returns:
        The JobQueue instance.
    """
    return request.app.state.job_queue


def _classify_file_type(filename: str) -> str:
    """Classify an uploaded file into a document type based on its name."""
    name = filename.lower()
    if "survey" in name or "מדידה" in name or "מפת" in name:
        return "survey_map"
    if "permit" in name or "היתר" in name:
        return "building_permits"
    if "taba" in name or "תבע" in name or 'תב"ע' in name:
        return "taba_document"
    return "other_document"


def _validate_file_extension(filename: str) -> bool:
    """Check if file extension is allowed.

    Args:
        filename: Name of the uploaded file.

    Returns:
        True if extension is allowed.
    """
    if "." not in filename:
        return False
    ext = "." + filename.rsplit(".", 1)[-1].lower()
    return ext in ALLOWED_EXTENSIONS


# --- Endpoints ---


@router.post("/extract", response_model=ExtractionResponse)
async def extract_documents(request: Request, files: list[UploadFile] | None = None) -> ExtractionResponse:
    """Extract buildings and taba data from uploaded documents using AI.

    Standalone endpoint — does NOT create a job. Used during the upload
    step so users can validate extraction results before submitting.

    Args:
        request: FastAPI request.
        files: Uploaded PDF/image files.

    Returns:
        Extracted buildings and tabas.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="שירות AI אינו זמין כרגע — חסר מפתח API.",
        )

    if not files:
        raise HTTPException(status_code=400, detail="לא התקבלו קבצים לניתוח.")

    import uuid
    from pathlib import Path as _Path

    # Save files to temp directory
    extract_id = str(uuid.uuid4())[:8]
    upload_dir = _Path(os.getenv("OUTPUT_DIRECTORY", "output")) / "uploads" / f"extract-{extract_id}"
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_paths: dict[str, str] = {}
    warnings: list[str] = []

    for file in files:
        if not _validate_file_extension(file.filename or ""):
            raise HTTPException(
                status_code=400,
                detail=f'סוג הקובץ "{file.filename}" אינו נתמך.',
            )
        content = await file.read()
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=400, detail=f'הקובץ "{file.filename}" גדול מדי.')

        safe_name = _Path(file.filename or "unknown").name
        dest = upload_dir / safe_name
        dest.write_bytes(content)

        file_type = _classify_file_type(safe_name)
        file_paths[file_type] = str(dest)
        logger.info("Extract: saved %s as %s (%d bytes)", safe_name, file_type, len(content))

    # Run AI extraction
    try:
        from config.settings import get_settings
        from agent.main_agent import NachlaAgent
        from agent.system_prompt import build_system_prompt

        settings = get_settings()
        agent = NachlaAgent(settings)

        if settings.anthropic_api_key:
            from agent.llm_client import LLMClient
            llm_client = LLMClient(settings, audit_logger=agent.audit_logger)
            agent.attach_llm(llm_client)
            agent.system_prompt = build_system_prompt()

        buildings, tabas, doc_classifications = await agent.analyze_uploaded_documents(file_paths)

        building_dicts = [b.model_dump() for b in buildings]
        taba_dicts = [t.model_dump() for t in tabas]

        # Add classification-based warnings
        for cls in doc_classifications:
            if not cls.get("is_relevant", True):
                fname = cls.get("filename", "")
                note = cls.get("note", "")
                warnings.append(f"הקובץ \"{fname}\" אינו רלוונטי לבדיקת התכנות. {note}")
            elif cls.get("confidence") == "low":
                fname = cls.get("filename", "")
                detected = cls.get("detected_type", "")
                warnings.append(f"הקובץ \"{fname}\" זוהה כ-{detected} ברמת ודאות נמוכה. אנא ודאו שהעלתם את הקובץ הנכון.")

        missing_docs = []
        for cls in doc_classifications:
            if isinstance(cls, dict):
                pass  # classifications are per-file
        # Check if key document types are missing
        detected_types = {c.get("detected_type", "") for c in doc_classifications}
        if not any("מדידה" in t or "survey" in t.lower() for t in detected_types if t):
            warnings.append("לא זוהתה מפת מדידה במסמכים שהועלו. מפת מדידה נדרשת לזיהוי מבנים מדויק.")

        if not buildings:
            warnings.append("לא זוהו מבנים במסמכים שהועלו. ניתן להזין מבנים ידנית.")

        # Build classification objects
        classifications = []
        for cls in doc_classifications:
            try:
                classifications.append(DocumentClassification(**cls))
            except Exception:
                pass

        return ExtractionResponse(
            buildings=building_dicts,
            tabas=taba_dicts,
            building_count=len(buildings),
            taba_count=len(tabas),
            warnings=warnings,
            document_classifications=classifications,
        )

    except Exception as exc:
        logger.error("Document extraction failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="שגיאה בניתוח המסמכים. אנא נסו שנית.",
        )


@router.get("/jobs")
async def list_jobs(request: Request) -> list[dict]:
    """List all jobs (current session + DB history).

    Args:
        request: FastAPI request.

    Returns:
        List of job summaries.
    """
    queue = _get_job_queue(request)
    return await queue.list_jobs()


@router.post("/jobs", response_model=JobCreateResponse)
async def create_job(intake: IntakeRequest, request: Request) -> JobCreateResponse:
    """Submit a new feasibility study job.

    Args:
        intake: Intake form data.
        request: FastAPI request.

    Returns:
        Job creation response with job_id.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="שירות AI אינו זמין כרגע — חסר מפתח API. אנא פנו למנהל המערכת.",
        )

    queue = _get_job_queue(request)
    job_id = await queue.submit(intake.model_dump())

    return JobCreateResponse(
        job_id=job_id,
        status="pending",
        message="העבודה נוצרה בהצלחה. מתחיל בעיבוד...",
    )


@router.post("/jobs/{job_id}/files", response_model=FileUploadResponse)
async def upload_files(job_id: str, request: Request, files: list[UploadFile] | None = None) -> FileUploadResponse:
    """Upload documents for a job (survey map, permits, etc.).

    Args:
        job_id: Job identifier.
        request: FastAPI request.
        files: List of uploaded files.

    Returns:
        File upload response.

    Raises:
        HTTPException: If job not found or file validation fails.
    """
    queue = _get_job_queue(request)
    job = await queue.get_status(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="העבודה לא נמצאה. אנא ודאו את מספר העבודה.",
        )

    if not files:
        raise HTTPException(
            status_code=400,
            detail="לא התקבלו קבצים. אנא העלו לפחות קובץ אחד.",
        )

    from pathlib import Path as _Path

    # Create upload directory for this job
    upload_dir = _Path(os.getenv("OUTPUT_DIRECTORY", "output")) / "uploads" / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list[str] = []

    for file in files:
        # Validate extension
        if not _validate_file_extension(file.filename or ""):
            raise HTTPException(
                status_code=400,
                detail=(
                    f'סוג הקובץ "{file.filename}" אינו נתמך. הפורמטים הנתמכים: {", ".join(sorted(ALLOWED_EXTENSIONS))}'
                ),
            )

        # Validate size
        content = await file.read()
        if len(content) > MAX_FILE_SIZE_BYTES:
            size_mb = len(content) / (1024 * 1024)
            raise HTTPException(
                status_code=400,
                detail=(
                    f'הקובץ "{file.filename}" גדול מדי ({size_mb:.1f} MB). '
                    f"גודל מקסימלי מותר: {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB"
                ),
            )

        # Save file to disk
        safe_name = _Path(file.filename or "unknown").name  # strip path components
        dest = upload_dir / safe_name
        dest.write_bytes(content)
        saved_paths.append(str(dest))
        logger.info("Saved upload: %s (%d bytes)", dest, len(content))

    # Store file paths (not just names) in the job
    await queue.add_files(job_id, saved_paths)

    file_names = [_Path(p).name for p in saved_paths]
    return FileUploadResponse(
        job_id=job_id,
        files_received=len(saved_paths),
        file_names=file_names,
        message=f"התקבלו {len(saved_paths)} קבצים בהצלחה.",
    )


@router.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str, request: Request) -> JobStatusResponse:
    """Poll job status.

    Args:
        job_id: Job identifier.
        request: FastAPI request.

    Returns:
        Current job status.

    Raises:
        HTTPException: If job not found.
    """
    queue = _get_job_queue(request)
    job = await queue.get_status(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="העבודה לא נמצאה. אנא ודאו את מספר העבודה.",
        )

    return JobStatusResponse(
        job_id=job.id,
        status=job.state,
        phase=job.phase,
        progress_percent=job.progress,
        message=job.message,
    )


@router.post("/jobs/{job_id}/classify/confirm")
async def confirm_classification(
    job_id: str,
    body: ClassificationConfirmRequest,
    request: Request,
) -> dict[str, Any]:
    """Confirm building classifications (checkpoint endpoint).

    This is the critical checkpoint from workflow step 3.4.
    Resumes the paused job after user confirms classifications.

    Args:
        job_id: Job identifier.
        body: Confirmed building classifications.
        request: FastAPI request.

    Returns:
        Confirmation response.

    Raises:
        HTTPException: If job not found or not at checkpoint.
    """
    queue = _get_job_queue(request)
    job = await queue.get_status(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="העבודה לא נמצאה.",
        )

    if job.state != "checkpoint":
        raise HTTPException(
            status_code=400,
            detail=(f"העבודה אינה בשלב אישור סיווג. סטטוס נוכחי: {job.state}"),
        )

    confirmed = [b.model_dump() for b in body.buildings]
    await queue.resume_after_checkpoint(job_id, confirmed)

    return {
        "job_id": job_id,
        "status": "running",
        "message": "סיווג המבנים אושר. ממשיך בחישובים...",
        "buildings_confirmed": len(body.buildings),
    }


@router.get("/jobs/{job_id}/buildings", response_model=BuildingsResponse)
async def get_job_buildings(job_id: str, request: Request) -> BuildingsResponse:
    """Return the building list for the classification checkpoint table.

    Args:
        job_id: Job identifier.
        request: FastAPI request.

    Returns:
        Building list with count.

    Raises:
        HTTPException: If job not found or buildings not yet mapped.
    """
    queue = _get_job_queue(request)
    job = await queue.get_status(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="העבודה לא נמצאה",
        )

    if not job.buildings:
        raise HTTPException(
            status_code=400,
            detail="המבנים טרם מופו",
        )

    return BuildingsResponse(
        job_id=job.id,
        buildings=job.buildings,
        count=len(job.buildings),
    )


@router.get("/jobs/{job_id}/results", response_model=ResultsResponse)
async def get_job_results(job_id: str, request: Request) -> ResultsResponse:
    """Return cost summary for the results page before download.

    Args:
        job_id: Job identifier.
        request: FastAPI request.

    Returns:
        Cost summary with building cards and available download types.

    Raises:
        HTTPException: If job not found or not yet complete.
    """
    queue = _get_job_queue(request)
    job = await queue.get_status(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="העבודה לא נמצאה",
        )

    if job.state != "complete":
        raise HTTPException(
            status_code=400,
            detail="הבדיקה טרם הושלמה",
        )

    result = job.result or {}

    # Determine which download types are available
    file_key_map = {
        "word": "word_path",
        "excel": "excel_path",
        "audit": "audit_path",
        "pdf": "pdf_path",
    }
    download_types = [ft for ft, key in file_key_map.items() if result.get(key)]

    # Extract hivun totals — support both flat keys and nested result dicts
    hivun_375_total = result.get("hivun_375_total")
    if hivun_375_total is None:
        hivun_375 = result.get("hivun_375_result")
        hivun_375_total = hivun_375.get("result") or hivun_375.get("total_cost") if isinstance(hivun_375, dict) else None
    hivun_33_total = result.get("hivun_33_total")
    if hivun_33_total is None:
        hivun_33 = result.get("hivun_33_result")
        hivun_33_total = hivun_33.get("result") or hivun_33.get("total_cost") if isinstance(hivun_33, dict) else None

    return ResultsResponse(
        job_id=job.id,
        total_regularization_cost=result.get("total_regularization_cost", 0),
        total_usage_fees=result.get("total_usage_fees", 0),
        total_permit_fees=result.get("total_permit_fees", 0),
        betterment_levy=result.get("betterment_levy", 0),
        hivun_375_total=hivun_375_total,
        hivun_33_total=hivun_33_total,
        building_cards=result.get("building_cards", []),
        download_types=download_types,
    )


@router.get("/labels")
async def get_labels() -> dict[str, dict[str, str]]:
    """Return all Hebrew label dictionaries for the React frontend.

    Returns:
        Dict with all label dicts as nested objects.
    """
    from api.labels import (
        AUTH_TYPE_LABELS,
        BUILDING_STATUS_LABELS,
        BUILDING_TYPE_LABELS,
        CLIENT_GOAL_LABELS,
        OWNERSHIP_TYPE_LABELS,
    )

    return {
        "building_types": BUILDING_TYPE_LABELS,
        "building_statuses": BUILDING_STATUS_LABELS,
        "auth_types": AUTH_TYPE_LABELS,
        "client_goals": CLIENT_GOAL_LABELS,
        "ownership_types": OWNERSHIP_TYPE_LABELS,
    }


@router.get("/jobs/{job_id}/download/{file_type}")
async def download_report(job_id: str, file_type: str, request: Request) -> FileResponse:
    """Download generated report file.

    Args:
        job_id: Job identifier.
        file_type: One of 'word', 'excel', 'audit', 'pdf'.
        request: FastAPI request.

    Returns:
        File download response.

    Raises:
        HTTPException: If job not found, not complete, or file type invalid.
    """
    allowed_types = {"word", "excel", "audit", "pdf"}
    if file_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"סוג קובץ לא תקין. הסוגים הנתמכים: {', '.join(sorted(allowed_types))}",
        )

    queue = _get_job_queue(request)
    job = await queue.get_status(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="העבודה לא נמצאה.",
        )

    if job.state != "complete":
        raise HTTPException(
            status_code=400,
            detail="הדוח טרם הופק. אנא המתינו להשלמת העיבוד.",
        )

    # Get file path from job result
    if job.result is None:
        raise HTTPException(
            status_code=500,
            detail="שגיאה פנימית: תוצאות העבודה לא נמצאו.",
        )

    file_key_map = {
        "word": "word_path",
        "excel": "excel_path",
        "audit": "audit_path",
        "pdf": "pdf_path",
    }
    media_type_map = {
        "word": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "audit": "application/json",
        "pdf": "application/pdf",
    }

    file_path = job.result.get(file_key_map[file_type])
    if not file_path:
        raise HTTPException(
            status_code=404,
            detail=f"קובץ מסוג {file_type} לא נמצא בתוצאות העבודה.",
        )

    # Path traversal guard: ensure file is within expected output directory
    from pathlib import Path as _Path

    resolved = _Path(file_path).resolve()

    # Verify path is within the output directory to prevent path traversal
    output_root = _Path(os.getenv("OUTPUT_DIRECTORY", "output")).resolve()
    if not resolved.is_relative_to(output_root):
        raise HTTPException(
            status_code=403,
            detail="גישה לקובץ נדחתה — הנתיב מחוץ לתיקיית הפלט.",
        )

    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="קובץ לא נמצא במערכת.")

    return FileResponse(
        path=str(resolved),
        media_type=media_type_map[file_type],
        filename=resolved.name,
    )


@router.post("/jobs/{job_id}/cloud-export/{target}")
async def cloud_export(job_id: str, target: str, request: Request) -> CloudExportResponse:
    """Export completed job reports to cloud storage.

    Args:
        job_id: Job identifier.
        target: Cloud target — 'gdrive', 'onedrive', or 'all'.
        request: FastAPI request.

    Returns:
        Status with links to uploaded files.
    """
    valid_targets = {"gdrive", "onedrive", "all"}
    if target not in valid_targets:
        raise HTTPException(
            status_code=400,
            detail=f'יעד שמירה לא תקין. אפשרויות: {", ".join(sorted(valid_targets))}',
        )

    job_queue = _get_job_queue(request)
    job = await job_queue.get_status(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="העבודה לא נמצאה.")
    if job.state != "complete" or job.result is None:
        raise HTTPException(status_code=400, detail="הדוח טרם הופק.")

    results: dict[str, Any] = {"target": target, "files": []}
    targets = ["gdrive", "onedrive"] if target == "all" else [target]

    # Collect files to upload
    report_files: dict[str, str] = {}
    for key in ["word_path", "excel_path", "pdf_path", "audit_path"]:
        fpath = job.result.get(key)
        if fpath:
            report_files[key.replace("_path", "")] = fpath

    owner_name = job.intake_data.get("owner_name", "unknown")
    moshav_name = job.intake_data.get("moshav_name", "unknown")

    for t in targets:
        try:
            if t == "gdrive":
                if not os.getenv("GOOGLE_DRIVE_CREDENTIALS_PATH"):
                    results.setdefault("errors", []).append({
                        "service": "gdrive",
                        "error": "חסרים פרטי התחברות ל-Google Drive. אנא הגדירו GOOGLE_DRIVE_CREDENTIALS_PATH.",
                    })
                    continue
                from integrations.gdrive_client import GoogleDriveClient

                gdrive = GoogleDriveClient()
                if not await gdrive.authenticate():
                    results.setdefault("errors", []).append({
                        "service": "gdrive",
                        "error": "שגיאה בהתחברות ל-Google Drive.",
                    })
                    continue
                links = await gdrive.upload_report(owner_name, moshav_name, report_files)
                for file_key, link in links.items():
                    results["files"].append({"service": "gdrive", "file": file_key, "link": link})

            elif t == "onedrive":
                if not os.getenv("ONEDRIVE_CLIENT_ID"):
                    results.setdefault("errors", []).append({
                        "service": "onedrive",
                        "error": "חסרים פרטי התחברות ל-OneDrive. אנא הגדירו ONEDRIVE_CLIENT_ID.",
                    })
                    continue
                from integrations.onedrive_client import OneDriveClient

                od = OneDriveClient()
                if not await od.authenticate():
                    results.setdefault("errors", []).append({
                        "service": "onedrive",
                        "error": "שגיאה בהתחברות ל-OneDrive.",
                    })
                    continue
                links = await od.upload_report(owner_name, moshav_name, report_files)
                for file_key, link in links.items():
                    results["files"].append({"service": "onedrive", "file": file_key, "link": link})

        except Exception as exc:
            logger.error("Cloud export %s failed: %s", t, exc)
            results.setdefault("errors", []).append({
                "service": t,
                "error": "שגיאה בהעלאה לשירות הענן. אנא נסו שנית.",
            })

    has_errors = bool(results.get("errors"))
    return CloudExportResponse(
        status="partial" if has_errors else "ok",
        message="חלק מהקבצים לא הועלו" if has_errors else "הקבצים הועלו בהצלחה",
        target=target,
        files=results.get("files", []),
        errors=results.get("errors", []),
    )
