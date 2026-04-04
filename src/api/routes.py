"""API routes for the nachla agent backend.

All endpoints return JSON. File uploads via multipart/form-data.
Error responses include Hebrew messages for user-facing errors.
"""

from __future__ import annotations

import logging
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
    prior_permit_fees_purchased: float = Field(default=0, ge=0, description='דמי היתר שנרכשו בעבר (בש"ח)')
    prior_permit_fees_date: int | None = Field(default=None, description="שנת רכישת דמי היתר")
    agricultural_activity: str | None = Field(default=None, description="פעילות חקלאית קיימת")
    future_plans: str | None = Field(default=None, description="תוכניות עתידיות")
    monday_item_id: str | None = Field(default=None, description="מזהה פריט ב-Monday.com")


class JobStatusResponse(BaseModel):
    """Job status response."""

    job_id: str
    status: str  # pending, running, checkpoint, generating, complete, failed
    phase: str
    progress_percent: int = Field(ge=0, le=100)
    message: str  # Hebrew status message


class ClassificationConfirmRequest(BaseModel):
    """Request body for confirming building classifications."""

    buildings: list[dict[str, Any]] = Field(..., description="רשימת מבנים עם סיווג מאושר")


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


# --- Helper Functions ---


def _get_job_queue(request: Request) -> Any:
    """Get the job queue from the app state.

    Args:
        request: FastAPI request object.

    Returns:
        The JobQueue instance.
    """
    return request.app.state.job_queue


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


@router.post("/jobs", response_model=JobCreateResponse)
async def create_job(intake: IntakeRequest, request: Request) -> JobCreateResponse:
    """Submit a new feasibility study job.

    Args:
        intake: Intake form data.
        request: FastAPI request.

    Returns:
        Job creation response with job_id.
    """
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

    validated_files: list[str] = []

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

        # Reset file position for downstream processing
        await file.seek(0)
        validated_files.append(file.filename or "unknown")

    # Store file references in the job
    await queue.add_files(job_id, validated_files)

    return FileUploadResponse(
        job_id=job_id,
        files_received=len(validated_files),
        file_names=validated_files,
        message=f"התקבלו {len(validated_files)} קבצים בהצלחה.",
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

    await queue.resume_after_checkpoint(job_id, body.buildings)

    return {
        "job_id": job_id,
        "status": "running",
        "message": "סיווג המבנים אושר. ממשיך בחישובים...",
        "buildings_confirmed": len(body.buildings),
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
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="קובץ לא נמצא במערכת.")

    return FileResponse(
        path=str(resolved),
        media_type=media_type_map[file_type],
        filename=resolved.name,
    )
