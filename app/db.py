from contextlib import contextmanager
from typing import Generator
from sqlmodel import Session, SQLModel, create_engine

from app.config import get_app_settings


app_settings = get_app_settings()


engine = create_engine(
    app_settings.database_url, connect_args=app_settings.database_options
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_db_session() -> Generator[Session, None, None]:
    """Provides a database session.

    This generator function yields a SQLModel Session instance, ensuring
    it is properly closed after use when used with `contextlib.contextmanager`.

    Yields:
        sqlmodel.Session: A database session instance.
    """
    with Session(engine) as session:
        yield session


db_session = contextmanager(get_db_session)
"""
Provides a database session as a context manager.

This context manager can be used to obtain a `SQLModel.Session` instance,
ensuring that the session is properly closed after use.

Usage:
    with db_session() as session:
        # Perform database operations with 'session'
        ...
"""
