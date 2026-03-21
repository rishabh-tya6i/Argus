from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./phishguard.db")


class Base(DeclarativeBase):
    pass


if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Create tables if they do not exist.

    In production environments, prefer Alembic migrations instead of relying on
    this helper, but it is useful for local development and tests.
    """
    from . import db_models  # noqa: F401 - ensure models are imported

    # Attempt to create the vector extension if using PostgreSQL
    if engine.dialect.name == "postgresql":
        try:
            with engine.begin() as conn:
                from sqlalchemy import text
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception:
            # Ignore errors if extension already exists or concurrent creation fails
            pass

    Base.metadata.create_all(bind=engine)

