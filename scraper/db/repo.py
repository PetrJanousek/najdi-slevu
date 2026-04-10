"""scraper/db/repo.py — repository functions for DB persistence.

All functions accept an explicit SQLAlchemy Session so they are easy to
unit-test against an in-memory SQLite database.
"""

from __future__ import annotations

import statistics
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from scraper.canonical import canonicalize
from scraper.db.models import Discount, HotDealHit, ScrapeRun, Supermarket, WatchlistItem
from scraper.models import Discount as ParsedDiscount


# ---------------------------------------------------------------------------
# Price history / stats data types
# ---------------------------------------------------------------------------

@dataclass
class PricePoint:
    """A single price observation from the DB."""
    scraped_at: datetime
    supermarket: Optional[str]
    discounted_price: float
    original_price: Optional[float]
    canonical_key: Optional[str]


@dataclass
class ProductStats:
    """Aggregated price statistics for one canonical product."""
    lowest_ever: Optional[float]
    lowest_90d: Optional[float]
    median_90d: Optional[float]
    times_on_sale_90d: int
    is_at_historical_low: bool  # current best == lowest ever
    fake_discount: bool         # suspiciously stable "discount"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_name(name: str) -> str:
    """Lowercase and strip diacritics for indexed search."""
    return "".join(
        c
        for c in unicodedata.normalize("NFD", name.lower())
        if unicodedata.category(c) != "Mn"
    )


def _get_or_create_supermarket(session: Session, name: str) -> Supermarket:
    sm = session.execute(
        select(Supermarket).where(Supermarket.name == name)
    ).scalar_one_or_none()
    if sm is None:
        sm = Supermarket(name=name)
        session.add(sm)
        session.flush()
    return sm


# ---------------------------------------------------------------------------
# ScrapeRun
# ---------------------------------------------------------------------------

def save_scrape_run(
    session: Session,
    pdf_filename: Optional[str] = None,
    started_at: Optional[datetime] = None,
) -> ScrapeRun:
    """Create and persist a ScrapeRun row.

    Parameters
    ----------
    session:
        Active SQLAlchemy session.
    pdf_filename:
        Name of the PDF that was parsed.
    started_at:
        Timestamp for the run. Defaults to UTC now.

    Returns
    -------
    ScrapeRun
        The newly created (and flushed) instance.
    """
    run = ScrapeRun(
        pdf_filename=pdf_filename,
        started_at=started_at or datetime.now(tz=timezone.utc),
    )
    session.add(run)
    session.flush()
    return run


# ---------------------------------------------------------------------------
# Discounts
# ---------------------------------------------------------------------------

def save_discounts(
    session: Session,
    run: ScrapeRun,
    parsed: list[ParsedDiscount],
    supermarket_name: Optional[str] = None,
) -> list[Discount]:
    """Persist a list of parsed Discount objects linked to *run*.

    Parameters
    ----------
    session:
        Active SQLAlchemy session.
    run:
        The ScrapeRun to link discounts to.
    parsed:
        Discount objects from the parser.
    supermarket_name:
        If provided, look up or create a Supermarket row and link it.

    Returns
    -------
    list[Discount]
        The newly created ORM rows (flushed but not committed).
    """
    supermarket: Optional[Supermarket] = None
    if supermarket_name:
        supermarket = _get_or_create_supermarket(session, supermarket_name)

    rows: list[Discount] = []
    # Dedup within this run: (supermarket_id, name_normalized, discounted_price, valid_from)
    seen: set[tuple] = set()

    for p in parsed:
        name_norm = _normalize_name(p.name)
        dedup_key = (
            supermarket.id if supermarket else None,
            name_norm,
            p.discounted_price,
            p.valid_from,
        )
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        cp = canonicalize(p.name)
        row = Discount(
            scrape_run_id=run.id,
            supermarket_id=supermarket.id if supermarket else None,
            name=p.name,
            name_normalized=name_norm,
            original_price=p.original_price,
            discounted_price=p.discounted_price,
            discount_pct=p.discount_pct,
            valid_from=p.valid_from,
            valid_to=p.valid_to,
            raw_text=p.raw_text,
            canonical_brand=cp.brand,
            canonical_product_type=cp.product_type,
            canonical_quantity_value=cp.quantity_value,
            canonical_quantity_unit=cp.quantity_unit,
            canonical_key=cp.canonical_key,
        )
        session.add(row)
        rows.append(row)

    session.flush()
    return rows


def get_active_discounts(
    session: Session,
    as_of: Optional[date] = None,
    supermarket_name: Optional[str] = None,
) -> list[Discount]:
    """Return discounts valid on *as_of* (defaults to today).

    Parameters
    ----------
    session:
        Active SQLAlchemy session.
    as_of:
        Date to filter on. A discount is active if valid_from <= as_of <= valid_to.
        When either bound is NULL it is treated as open-ended.
    supermarket_name:
        If provided, filter to this supermarket only.

    Returns
    -------
    list[Discount]
        Matching rows ordered by discounted_price ascending.
    """
    target = as_of or date.today()
    stmt = select(Discount)

    # Only filter by date if the columns are not NULL
    stmt = stmt.where(
        (Discount.valid_from == None) | (Discount.valid_from <= target)  # noqa: E711
    ).where(
        (Discount.valid_to == None) | (Discount.valid_to >= target)  # noqa: E711
    )

    if supermarket_name:
        stmt = stmt.join(Discount.supermarket).where(Supermarket.name == supermarket_name)

    stmt = stmt.order_by(Discount.discounted_price)
    return list(session.execute(stmt).scalars())


def search_discounts(session: Session, query: str) -> list[Discount]:
    """Return discounts whose normalized name contains *query*.

    The query is itself normalized (lowercased + diacritics stripped) before
    comparison, so "kava" finds "Káva" and vice versa.

    Parameters
    ----------
    session:
        Active SQLAlchemy session.
    query:
        Substring to search for.

    Returns
    -------
    list[Discount]
        Matching rows ordered by discounted_price ascending.
    """
    normalized = _normalize_name(query)
    stmt = (
        select(Discount)
        .where(Discount.name_normalized.contains(normalized))
        .order_by(Discount.discounted_price)
    )
    return list(session.execute(stmt).scalars())


# ---------------------------------------------------------------------------
# Price history & statistics
# ---------------------------------------------------------------------------

def get_price_history(
    session: Session,
    canonical_key: str,
) -> list[PricePoint]:
    """Return time-ordered price observations for *canonical_key*.

    Joins discounts → scrape_runs (for timestamp) and supermarkets (for name).
    """
    stmt = (
        select(Discount)
        .where(Discount.canonical_key == canonical_key)
        .order_by(ScrapeRun.started_at)
        .join(Discount.scrape_run)
        .outerjoin(Discount.supermarket)
    )
    rows = list(session.execute(stmt).scalars())
    return [
        PricePoint(
            scraped_at=row.scrape_run.started_at,
            supermarket=row.supermarket.name if row.supermarket else None,
            discounted_price=row.discounted_price,
            original_price=row.original_price,
            canonical_key=row.canonical_key,
        )
        for row in rows
    ]


def compute_product_stats(
    session: Session,
    canonical_key: str,
    as_of: Optional[datetime] = None,
) -> ProductStats:
    """Compute aggregated price statistics for *canonical_key*.

    Parameters
    ----------
    session:
        Active SQLAlchemy session.
    canonical_key:
        The canonical product key to aggregate.
    as_of:
        Reference timestamp (defaults to UTC now). Used to compute 90d/60d windows.

    Returns
    -------
    ProductStats
    """
    now = as_of or datetime.now(tz=timezone.utc)
    cutoff_90d = now - timedelta(days=90)
    cutoff_60d = now - timedelta(days=60)

    history = get_price_history(session, canonical_key)
    if not history:
        return ProductStats(
            lowest_ever=None,
            lowest_90d=None,
            median_90d=None,
            times_on_sale_90d=0,
            is_at_historical_low=False,
            fake_discount=False,
        )

    all_prices = [p.discounted_price for p in history]
    prices_90d = [
        p.discounted_price for p in history
        if _ensure_aware(p.scraped_at) >= cutoff_90d
    ]
    prices_60d = [
        p.discounted_price for p in history
        if _ensure_aware(p.scraped_at) >= cutoff_60d
    ]
    orig_60d = [
        p.original_price for p in history
        if _ensure_aware(p.scraped_at) >= cutoff_60d and p.original_price is not None
    ]

    lowest_ever = min(all_prices)
    lowest_90d = min(prices_90d) if prices_90d else None
    median_90d = statistics.median(prices_90d) if prices_90d else None
    median_60d_disc = statistics.median(prices_60d) if prices_60d else None
    median_60d_orig = statistics.median(orig_60d) if orig_60d else None

    # Current best price across all chains
    current_best = min(
        p.discounted_price for p in history
        if _ensure_aware(p.scraped_at) >= cutoff_90d
    ) if prices_90d else lowest_ever

    is_at_historical_low = (current_best is not None and current_best <= lowest_ever * 1.001)

    # Fake-discount heuristic: "discount" if both prices barely deviate from median
    fake_discount = False
    if median_60d_disc is not None and len(prices_60d) >= 2:
        latest = history[-1]
        disc_stable = (
            abs(latest.discounted_price - median_60d_disc) / (median_60d_disc or 1) <= 0.05
        )
        orig_stable = (
            median_60d_orig is not None
            and latest.original_price is not None
            and abs(latest.original_price - median_60d_orig) / (median_60d_orig or 1) <= 0.02
        )
        fake_discount = disc_stable and orig_stable

    return ProductStats(
        lowest_ever=lowest_ever,
        lowest_90d=lowest_90d,
        median_90d=median_90d,
        times_on_sale_90d=len(prices_90d),
        is_at_historical_low=is_at_historical_low,
        fake_discount=fake_discount,
    )


def _ensure_aware(dt: datetime) -> datetime:
    """Return a timezone-aware datetime; assume UTC if naive."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------

def add_watchlist_item(session: Session, keyword: str) -> WatchlistItem:
    """Add *keyword* to the watchlist, or return the existing row.

    Parameters
    ----------
    session:
        Active SQLAlchemy session.
    keyword:
        Keyword to watch for. Stored as-is but looked up case-insensitively.

    Returns
    -------
    WatchlistItem
        Existing or newly created instance.
    """
    existing = session.execute(
        select(WatchlistItem).where(WatchlistItem.keyword == keyword)
    ).scalar_one_or_none()
    if existing:
        return existing
    item = WatchlistItem(keyword=keyword)
    session.add(item)
    session.flush()
    return item


def list_watchlist(session: Session) -> list[WatchlistItem]:
    """Return all watchlist items ordered alphabetically."""
    stmt = select(WatchlistItem).order_by(WatchlistItem.keyword)
    return list(session.execute(stmt).scalars())


def remove_watchlist_item(session: Session, keyword: str) -> bool:
    """Remove *keyword* from the watchlist.

    Returns True if the item was found and deleted, False if not found.
    """
    item = session.execute(
        select(WatchlistItem).where(WatchlistItem.keyword == keyword)
    ).scalar_one_or_none()
    if item is None:
        return False
    session.delete(item)
    session.flush()
    return True
