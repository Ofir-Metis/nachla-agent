"""Database configuration: SQLite (dev) -> PostgreSQL (production).

Uses SQLAlchemy async engine with asyncpg driver for PostgreSQL.
Falls back to aiosqlite for SQLite in development.

Migration-ready but not auto-migrating -- use Alembic for production schema changes.
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# Naming convention for constraints (Alembic-friendly)
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)

# --- Schema definitions matching Pydantic models ---

jobs_table = Table(
    "jobs",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("state", String(20), nullable=False, default="pending"),
    Column("phase", String(50), nullable=False, default="intake"),
    Column("progress", Integer, nullable=False, default=0),
    Column("owner_name", String(255), nullable=False),
    Column("moshav_name", String(255), nullable=False),
    Column("gush", Integer, nullable=False),
    Column("helka", Integer, nullable=False),
    Column("intake_data", JSON, nullable=False),
    Column("buildings", JSON, nullable=True),
    Column("result", JSON, nullable=True),
    Column("error", Text, nullable=True),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)

audit_log_table = Table(
    "audit_log",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("job_id", String(36), nullable=False, index=True),
    Column("phase", String(50), nullable=False),
    Column("tool_name", String(100), nullable=False),
    Column("inputs", JSON, nullable=False),
    Column("formula", Text, nullable=True),
    Column("output", JSON, nullable=False),
    Column("timestamp", DateTime, nullable=False),
)

calculations_table = Table(
    "calculations",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("job_id", String(36), nullable=False, index=True),
    Column("building_id", String(50), nullable=True),
    Column("calc_type", String(50), nullable=False),
    Column("amount", Float, nullable=False),
    Column("vat_amount", Float, nullable=False),
    Column("total", Float, nullable=False),
    Column("details", JSON, nullable=True),
    Column("created_at", DateTime, nullable=False),
)

# Default SQLite URL for development
DEFAULT_SQLITE_URL = "sqlite+aiosqlite:///./data/nachla_dev.db"

# Module-level engine and session factory
_engine: AsyncEngine | None = None
_session_factory: sessionmaker | None = None


async def get_engine(database_url: str | None = None) -> AsyncEngine:
    """Create or return the async database engine.

    If database_url is None, checks DATABASE_URL env var, then falls back
    to SQLite for development.

    For production, expects a postgresql+asyncpg:// URL.

    Args:
        database_url: Optional database connection URL.

    Returns:
        SQLAlchemy AsyncEngine instance.
    """
    global _engine  # noqa: PLW0603

    if _engine is not None:
        return _engine

    url = database_url or os.getenv("DATABASE_URL")

    if url is None:
        url = DEFAULT_SQLITE_URL
        logger.info("No DATABASE_URL set, using SQLite for development: %s", url)
    else:
        # Convert standard postgres:// to asyncpg driver URL if needed
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        logger.info("Using database: %s", url.split("@")[-1] if "@" in url else url)

    engine_kwargs: dict = {
        "echo": os.getenv("SQL_ECHO", "false").lower() == "true",
    }

    # PostgreSQL-specific pool settings
    if "postgresql" in url:
        engine_kwargs.update(
            {
                "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
                "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
                "pool_timeout": 30,
                "pool_recycle": 1800,
            }
        )

    _engine = create_async_engine(url, **engine_kwargs)
    return _engine


async def get_session_factory() -> sessionmaker:
    """Get or create the async session factory.

    Returns:
        A sessionmaker configured for async sessions.
    """
    global _session_factory  # noqa: PLW0603

    if _session_factory is not None:
        return _session_factory

    engine = await get_engine()
    _session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session (for use as a dependency).

    Yields:
        An AsyncSession that is automatically closed after use.
    """
    factory = await get_session_factory()
    async with factory() as session:
        yield session


async def create_tables() -> None:
    """Create all tables defined in metadata.

    For development/testing only. Use Alembic migrations in production.
    """
    engine = await get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    logger.info("Database tables created")


async def dispose_engine() -> None:
    """Dispose of the database engine and reset module state.

    Should be called during application shutdown.
    """
    global _engine, _session_factory  # noqa: PLW0603

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database engine disposed")
