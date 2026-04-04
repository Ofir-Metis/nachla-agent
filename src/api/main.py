"""FastAPI backend for the nachla agent.

Provides REST API for:
- File upload and validation
- Job submission and status polling
- Report download
- Agent webhook endpoints
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.jobs import JobQueue
from api.routes import router

logger = logging.getLogger(__name__)

# Global job queue instance
job_queue = JobQueue()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler for startup and shutdown.

    Initializes the job queue on startup and cleans up on shutdown.
    """
    # Startup
    logger.info("Nachla Agent API starting up")
    app.state.job_queue = job_queue
    yield
    # Shutdown
    logger.info("Nachla Agent API shutting down")
    await job_queue.shutdown()


app = FastAPI(
    title="Nachla Agent API",
    description="בדיקת התכנות נחלות - API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for Chainlit frontend
_cors_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Basic health check endpoint (fast, for load balancers)."""
    return {"status": "ok", "service": "nachla-agent-api"}


@app.get("/health/detailed")
async def health_check_detailed() -> dict:
    """Detailed health check with all subsystem statuses."""
    from agent.health import HealthChecker

    checker = HealthChecker()
    return await checker.check_all()
