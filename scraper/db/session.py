"""scraper/db/session.py — SQLAlchemy engine and session factory."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Default DB path; can be overridden via NAJDI_SLEVU_DB env var
_DEFAULT_DB_PATH = Path("data/najdi_slevu.sqlite")


def get_db_url() -> str:
    """Return the SQLite connection URL.

    Uses the NAJDI_SLEVU_DB environment variable if set, otherwise falls back
    to ``data/najdi_slevu.sqlite`` relative to the current working directory.
    """
    raw = os.environ.get("NAJDI_SLEVU_DB", str(_DEFAULT_DB_PATH))
    # Ensure the parent directory exists
    db_path = Path(raw)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


def make_engine(url: str | None = None):
    """Create and return a SQLAlchemy engine.

    Parameters
    ----------
    url:
        Connection URL. Defaults to the result of get_db_url().
    """
    return create_engine(url or get_db_url(), echo=False)


def make_session_factory(engine=None) -> sessionmaker:
    """Return a configured sessionmaker bound to *engine*."""
    if engine is None:
        engine = make_engine()
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
