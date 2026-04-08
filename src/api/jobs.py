"""Async job queue for report generation.

Each report = 1 job. Agent runs in background worker.
Frontend polls for status. Classification checkpoint pauses the job.

Production: replace with Redis/Celery (Phase 5).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class JobState(StrEnum):
    """Possible states for a report generation job."""

    PENDING = "pending"
    RUNNING = "running"
    CHECKPOINT = "checkpoint"  # Waiting for classification confirmation
    GENERATING = "generating"  # Report being generated
    COMPLETE = "complete"
    FAILED = "failed"


# Hebrew status messages for each phase
PHASE_MESSAGES: dict[str, str] = {
    "intake": "קליטת נתוני לקוח",
    "taba_analysis": 'ניתוח תב"עות חלות',
    "building_mapping": "מיפוי וסיווג מבנים",
    "classification_checkpoint": "ממתין לאישור סיווג מבנים",
    "usage_fees": "חישוב דמי שימוש",
    "permit_fees": "חישוב דמי היתר",
    "capitalization": "חישוב היוון",
    "split": "חישוב פיצול",
    "report_assembly": "הרכבת דוח",
    "review": "בקרה ואישור",
    "output": "הפקת פלט סופי",
    "complete": "הושלם",
    "failed": "נכשל",
}


@dataclass
class Job:
    """A single report generation job.

    Tracks the full lifecycle of a feasibility study from intake
    through report generation and output.
    """

    id: str
    state: JobState = JobState.PENDING
    phase: str = "intake"
    progress: int = 0
    intake_data: dict[str, Any] = field(default_factory=dict)
    uploaded_files: list[str] = field(default_factory=list)
    buildings: list[dict[str, Any]] = field(default_factory=list)
    result: dict[str, Any] | None = None
    error: str | None = None

    # Internal asyncio event for checkpoint synchronization
    _checkpoint_event: asyncio.Event = field(default_factory=asyncio.Event)
    _confirmed_buildings: list[dict[str, Any]] = field(default_factory=list)

    @property
    def message(self) -> str:
        """Get the Hebrew status message for the current phase."""
        if self.state == JobState.FAILED and self.error:
            return f"שגיאה: {self.error}"
        return PHASE_MESSAGES.get(self.phase, self.phase)


class JobQueue:
    """In-memory async job queue.

    Manages job lifecycle including submission, status polling,
    checkpoint pausing/resuming, and cleanup.

    Production: replace with Redis/Celery (Phase 5).
    """

    def __init__(self) -> None:
        """Initialize the job queue."""
        self._jobs: dict[str, Job] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}

    async def submit(self, intake: dict[str, Any]) -> str:
        """Submit a new job.

        Args:
            intake: Intake form data matching Nachla model fields.

        Returns:
            Generated job_id string.
        """
        job_id = str(uuid.uuid4())
        job = Job(id=job_id, intake_data=intake)
        self._jobs[job_id] = job

        logger.info("Job %s submitted for %s", job_id, intake.get("owner_name", "unknown"))

        # Start background processing
        task = asyncio.create_task(self._run_job(job_id))
        self._tasks[job_id] = task

        return job_id

    async def get_status(self, job_id: str) -> Job | None:
        """Get current job status.

        Args:
            job_id: Job identifier.

        Returns:
            Job object if found, None otherwise.
        """
        return self._jobs.get(job_id)

    async def add_files(self, job_id: str, file_names: list[str]) -> None:
        """Add uploaded file references to a job.

        Args:
            job_id: Job identifier.
            file_names: List of uploaded file names.
        """
        job = self._jobs.get(job_id)
        if job:
            job.uploaded_files.extend(file_names)
            logger.info("Job %s: added %d files", job_id, len(file_names))

    async def pause_for_checkpoint(self, job_id: str, buildings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Pause job at classification checkpoint and wait for user confirmation.

        CRITICAL: This implements the mandatory checkpoint from workflow step 3.4.
        The job will not proceed until the user explicitly confirms classifications.

        Args:
            job_id: Job identifier.
            buildings: List of building dicts to present for classification.

        Returns:
            The user-confirmed building list (may be modified by user).
        """
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.state = JobState.CHECKPOINT
        job.phase = "classification_checkpoint"
        job.buildings = buildings
        job._checkpoint_event.clear()

        logger.info("Job %s paused at classification checkpoint with %d buildings", job_id, len(buildings))

        # Wait for user confirmation (blocks until resume_after_checkpoint is called)
        await job._checkpoint_event.wait()

        logger.info("Job %s resumed after checkpoint", job_id)
        return job._confirmed_buildings

    async def resume_after_checkpoint(self, job_id: str, confirmed_buildings: list[dict[str, Any]]) -> None:
        """Resume job after user confirms classifications.

        Args:
            job_id: Job identifier.
            confirmed_buildings: User-confirmed building classifications.
        """
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        if job.state != JobState.CHECKPOINT:
            raise ValueError(f"Job {job_id} is not at checkpoint (state: {job.state})")

        job._confirmed_buildings = confirmed_buildings
        job.buildings = confirmed_buildings
        job.state = JobState.RUNNING
        job.phase = "usage_fees"

        # Signal the waiting coroutine to continue
        job._checkpoint_event.set()

        logger.info("Job %s checkpoint confirmed with %d buildings", job_id, len(confirmed_buildings))

    async def _run_job(self, job_id: str) -> None:
        """Execute the job in background using the real NachlaAgent.

        Orchestrates the full workflow: document analysis, building mapping,
        classification checkpoint, calculations, report generation, and output.

        Args:
            job_id: Job identifier.
        """
        from agent.main_agent import NachlaAgent
        from agent.system_prompt import build_system_prompt
        from config.settings import get_settings
        from models.building import Building
        from models.nachla import Nachla

        job = self._jobs.get(job_id)
        if not job:
            return

        try:
            job.state = JobState.RUNNING
            settings = get_settings()

            # --- Create agent ---
            agent = NachlaAgent(settings)

            # Attach LLM client if API key is configured
            llm_client = None
            if settings.anthropic_api_key:
                from agent.llm_client import LLMClient
                llm_client = LLMClient(settings, audit_logger=agent.audit_logger)
                agent.attach_llm(llm_client)
                logger.info("Job %s: LLM client attached", job_id)
            else:
                logger.warning("Job %s: No ANTHROPIC_API_KEY, running without AI", job_id)

            # --- Build Nachla model from intake data ---
            nachla = Nachla(**job.intake_data)

            # Build system prompt
            priority = nachla.priority_area.value if nachla.priority_area else None
            agent.system_prompt = build_system_prompt(priority_area=priority)

            # Build uploaded file paths dict
            uploaded_files: dict[str, str] = {}
            for fpath in job.uploaded_files:
                if "survey" in fpath.lower() or "מדידה" in fpath:
                    uploaded_files["survey_map"] = fpath
                elif "permit" in fpath.lower() or "היתר" in fpath:
                    uploaded_files["building_permits"] = fpath
                else:
                    uploaded_files[fpath] = fpath

            # --- Phase 1: Intake ---
            job.phase = "intake"
            job.progress = 5
            await agent._run_intake(nachla)

            # --- Phase 2: Taba analysis ---
            job.phase = "taba_analysis"
            job.progress = 15
            tabas = await agent._run_taba_analysis(nachla)

            # --- Phase 3: Building mapping (uses LLM for document analysis) ---
            job.phase = "building_mapping"
            job.progress = 30
            buildings = await agent._run_building_mapping(nachla, uploaded_files)

            # --- Phase 3.4: Classification checkpoint ---
            if buildings:
                job.buildings = [b.model_dump() for b in buildings]
                confirmed_dicts = await self.pause_for_checkpoint(job_id, job.buildings)
                buildings = []
                for bd in confirmed_dicts:
                    try:
                        buildings.append(Building(**bd))
                    except Exception as exc:
                        logger.warning("Failed to parse confirmed building: %s", exc)
                agent.workflow.confirm_classifications()
            else:
                # No buildings found — skip checkpoint, proceed with empty list
                agent.workflow.classifications_confirmed = True
                logger.warning("Job %s: No buildings found, skipping checkpoint", job_id)

            # --- Phases 4-11: Calculations ---
            job.phase = "calculations"
            job.progress = 50
            calc_results = await agent._run_calculations(nachla, buildings, tabas)

            # --- Phase 12: Report assembly + narratives ---
            job.phase = "report"
            job.progress = 80
            job.state = JobState.GENERATING
            report_data = await agent._build_report_data(nachla, buildings, tabas, calc_results)

            # --- Phase 13: Review (sanity checks) ---
            job.phase = "review"
            job.progress = 90
            await agent._run_review(report_data)

            # --- Phase 14: Output (generate documents) ---
            job.phase = "output"
            job.progress = 95

            output_dir = settings.output_directory
            word_path = None
            audit_path = None

            try:
                from documents.word_generator import WordGenerator
                from pathlib import Path

                Path(output_dir).mkdir(parents=True, exist_ok=True)
                gen = WordGenerator()
                template_path = "data/templates/סיכום בדיקת התכנות טמפלט.docx"

                if Path(template_path).exists():
                    word_path = gen.generate_report(
                        report_data, template_path, f"{output_dir}/{job_id}.docx",
                    )
                    logger.info("Job %s: Word report generated at %s", job_id, word_path)
            except Exception as exc:
                logger.error("Job %s: Word generation failed: %s", job_id, exc)

            # Save audit log
            try:
                from pathlib import Path as P
                P(output_dir).mkdir(parents=True, exist_ok=True)
                audit_path = f"{output_dir}/{job_id}_audit.json"
                agent.save_audit_log(audit_path)
                logger.info("Job %s: Audit log saved at %s", job_id, audit_path)
            except Exception as exc:
                logger.error("Job %s: Audit log save failed: %s", job_id, exc)

            # --- Complete ---
            job.phase = "complete"
            job.progress = 100
            job.state = JobState.COMPLETE
            job.result = {
                "word_path": word_path,
                "excel_path": None,
                "audit_path": audit_path,
                "pdf_path": None,
                "total_regularization_cost": report_data.total_regularization_cost,
                "total_usage_fees": report_data.total_usage_fees,
                "total_permit_fees": report_data.total_permit_fees,
                "betterment_levy": report_data.betterment_levy if hasattr(report_data, "betterment_levy") else 0,
                "hivun_375_total": (
                    report_data.hivun_375_result.get("total_cost", 0)
                    if isinstance(report_data.hivun_375_result, dict)
                    else 0
                ),
                "hivun_33_total": (
                    report_data.hivun_33_result.get("total_cost", 0)
                    if isinstance(report_data.hivun_33_result, dict)
                    else 0
                ),
                "token_usage": llm_client.token_usage if llm_client else {},
                "cost_estimate": llm_client.estimate_cost() if llm_client else {},
            }
            logger.info("Job %s: complete", job_id)

        except asyncio.CancelledError:
            job.state = JobState.FAILED
            job.error = "העבודה בוטלה"
            logger.warning("Job %s cancelled", job_id)
        except Exception as exc:
            job.state = JobState.FAILED
            job.phase = "failed"
            job.error = str(exc)
            logger.exception("Job %s failed: %s", job_id, exc)

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job.

        Args:
            job_id: Job identifier.

        Returns:
            True if job was cancelled, False if not found or already complete.
        """
        task = self._tasks.get(job_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

    async def shutdown(self) -> None:
        """Cancel all running jobs and clean up.

        Called during application shutdown.
        """
        for job_id, task in self._tasks.items():
            if not task.done():
                task.cancel()
                logger.info("Cancelled job %s during shutdown", job_id)

        # Wait for all tasks to complete cancellation
        if self._tasks:
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)

        self._tasks.clear()
        logger.info("Job queue shutdown complete")

    def list_jobs(self, status_filter: str | None = None) -> list[Job]:
        """List all jobs, optionally filtered by status.

        Args:
            status_filter: Optional status string to filter by.

        Returns:
            List of matching Job objects.
        """
        jobs = list(self._jobs.values())
        if status_filter:
            jobs = [j for j in jobs if j.state == status_filter]
        return jobs
