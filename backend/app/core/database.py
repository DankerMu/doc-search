from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from .config import settings

async_engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    try:
        from .. import models  # noqa: F401
    except ModuleNotFoundError as exc:
        expected_name = f"{__package__.rsplit('.', 1)[0]}.models"
        if exc.name != expected_name:
            raise

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
