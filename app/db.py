from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import get_app_settings


app_settings = get_app_settings()


engine = create_async_engine(
    app_settings.database_url, connect_args=app_settings.database_options
)


async def create_db_and_tables():
    """Creates database tables based on SQLModel metadata.

    This asynchronous function connects to the database using the configured engine,
    starts a transaction, and then synchronously creates all tables defined in
    `SQLModel.metadata`. This is typically used during application startup.
    """
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides an asynchronous database session.

    This asynchronous generator function yields a `sqlmodel.ext.asyncio.session.AsyncSession`
    instance. It ensures the session is properly closed after use, especially when
    wrapped by `contextlib.asynccontextmanager` or used directly as an async context manager.

    Yields:
        sqlmodel.ext.asyncio.session.AsyncSession: An asynchronous database session instance.
    """
    async with AsyncSession(engine) as session:
        yield session


async_db_session = asynccontextmanager(get_async_db_session)
"""
Provides an async database session as an async context manager.

This context manager can be used to obtain a 
`sqlmodel.ext.asyncio.session.AsyncSession` instance,
ensuring that the session is properly closed after use.

Usage:
    async with async_db_session() as session:
        # Perform database operations with 'session'
        ...
"""
