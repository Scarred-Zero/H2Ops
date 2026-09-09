from __future__ import annotations
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from src.core.config import settings

logger = logging.getLogger("database")


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for workers/scripts outside the request lifecycle."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

HYPERTABLE_METRICS = [
    ("telemetry_logs", "timestamp"),
]


async def init_db() -> None:
    """
    Dev/bootstrap only — creates tables and promotes telemetry_logs to a
    TimescaleDB hypertable. Production environments should use Alembic
    migrations instead, with `create_hypertable` issued in a migration.
    """
    import models  # noqa: F401  ensures models are registered on Base.metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        for table_name, time_column in HYPERTABLE_METRICS:
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb;"))
                await conn.execute(
                    text(
                        f"SELECT create_hypertable("
                        f"'{table_name}', '{time_column}', "
                        f"chunk_time_interval => INTERVAL '1 day', "
                        f"if_not_exists => TRUE);"
                    )
                )
                logger.info(f"Hypertable ensured on {table_name}({time_column})")
            except Exception as exc:
                logger.warning(f"Hypertable setup skipped for {table_name}: {exc}")
