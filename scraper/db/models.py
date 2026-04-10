"""scraper/db/models.py — SQLAlchemy ORM models (schema v1, single-user).

Populated in T-2.2. This file defines the declarative Base only.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass
