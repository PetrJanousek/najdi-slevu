"""scraper/db/models.py — SQLAlchemy ORM models (schema v1, single-user).

Tables:
- supermarkets        Known supermarket chains
- scrape_runs         One row per pipeline execution
- discounts           Parsed discount rows, linked to a scrape_run
- watchlist_items     Keywords the user watches for
- hot_deal_hits       Discounts that matched a watchlist keyword

Indexes:
- idx_discounts_supermarket_valid_from  (supermarket_id, valid_from)
- idx_discounts_name_normalized         (name_normalized)
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


class Supermarket(Base):
    __tablename__ = "supermarkets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    discounts: Mapped[list["Discount"]] = relationship(back_populates="supermarket")


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    pdf_filename: Mapped[Optional[str]] = mapped_column(String(256))

    discounts: Mapped[list["Discount"]] = relationship(back_populates="scrape_run")


class Discount(Base):
    __tablename__ = "discounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scrape_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scrape_runs.id", ondelete="CASCADE"), nullable=False
    )
    supermarket_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("supermarkets.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    name_normalized: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    original_price: Mapped[Optional[float]] = mapped_column(Float)
    discounted_price: Mapped[float] = mapped_column(Float, nullable=False)
    discount_pct: Mapped[Optional[float]] = mapped_column(Float)
    valid_from: Mapped[Optional[date]] = mapped_column(Date)
    valid_to: Mapped[Optional[date]] = mapped_column(Date)
    raw_text: Mapped[Optional[str]] = mapped_column(Text)

    scrape_run: Mapped["ScrapeRun"] = relationship(back_populates="discounts")
    supermarket: Mapped[Optional["Supermarket"]] = relationship(back_populates="discounts")
    hot_deal_hits: Mapped[list["HotDealHit"]] = relationship(back_populates="discount")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    keyword: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)

    hits: Mapped[list["HotDealHit"]] = relationship(back_populates="watchlist_item")


class HotDealHit(Base):
    __tablename__ = "hot_deal_hits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    discount_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("discounts.id", ondelete="CASCADE"), nullable=False
    )
    watchlist_item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("watchlist_items.id", ondelete="CASCADE"), nullable=False
    )
    matched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    discount: Mapped["Discount"] = relationship(back_populates="hot_deal_hits")
    watchlist_item: Mapped["WatchlistItem"] = relationship(back_populates="hits")


# Composite index: look up discounts by (supermarket, valid_from)
Index(
    "idx_discounts_supermarket_valid_from",
    Discount.supermarket_id,
    Discount.valid_from,
)
