"""Unit tests for scraper/db/repo.py using in-memory SQLite."""
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scraper.db.models import Base
from scraper.db.repo import (
    add_watchlist_item,
    get_active_discounts,
    list_watchlist,
    remove_watchlist_item,
    save_discounts,
    save_scrape_run,
    search_discounts,
)
from scraper.models import Discount as ParsedDiscount


@pytest.fixture
def session():
    """In-memory SQLite session with all tables created."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as s:
        yield s


def _make_parsed(name: str, price: float = 19.90, **kwargs) -> ParsedDiscount:
    return ParsedDiscount(
        name=name,
        original_price=kwargs.get("original_price", 29.90),
        discounted_price=price,
        discount_pct=kwargs.get("discount_pct", 33.4),
        valid_from=kwargs.get("valid_from"),
        valid_to=kwargs.get("valid_to"),
        raw_text=name,
    )


# ---------------------------------------------------------------------------
# ScrapeRun
# ---------------------------------------------------------------------------

class TestSaveScrapeRun:
    def test_creates_run(self, session):
        run = save_scrape_run(session, pdf_filename="tesco.pdf")
        assert run.id is not None
        assert run.pdf_filename == "tesco.pdf"

    def test_custom_started_at(self, session):
        ts = datetime(2026, 4, 7, 12, 0, 0, tzinfo=timezone.utc)
        run = save_scrape_run(session, started_at=ts)
        assert run.started_at == ts


# ---------------------------------------------------------------------------
# Discounts
# ---------------------------------------------------------------------------

class TestSaveDiscounts:
    def test_saves_discounts(self, session):
        run = save_scrape_run(session)
        parsed = [_make_parsed("Mléko"), _make_parsed("Chleba")]
        rows = save_discounts(session, run, parsed)
        assert len(rows) == 2
        assert rows[0].name == "Mléko"

    def test_normalizes_name(self, session):
        run = save_scrape_run(session)
        rows = save_discounts(session, run, [_make_parsed("Káva mletá")])
        assert rows[0].name_normalized == "kava mleta"

    def test_links_supermarket(self, session):
        run = save_scrape_run(session)
        rows = save_discounts(session, run, [_make_parsed("Rum")], supermarket_name="lidl")
        assert rows[0].supermarket is not None
        assert rows[0].supermarket.name == "lidl"

    def test_reuses_supermarket(self, session):
        run = save_scrape_run(session)
        save_discounts(session, run, [_make_parsed("Rum")], supermarket_name="lidl")
        save_discounts(session, run, [_make_parsed("Pivo")], supermarket_name="lidl")
        # Should still have only one supermarket row
        from sqlalchemy import select
        from scraper.db.models import Supermarket
        count = session.execute(select(Supermarket)).scalars().all()
        assert len(count) == 1


class TestGetActiveDiscounts:
    def _add_discount(self, session, name, valid_from=None, valid_to=None):
        run = save_scrape_run(session)
        return save_discounts(session, run, [
            _make_parsed(name, valid_from=valid_from, valid_to=valid_to)
        ])[0]

    def test_returns_discounts_valid_today(self, session):
        today = date(2026, 4, 10)
        self._add_discount(
            session, "Mléko",
            valid_from=date(2026, 4, 7),
            valid_to=date(2026, 4, 13),
        )
        result = get_active_discounts(session, as_of=today)
        assert len(result) == 1

    def test_excludes_expired(self, session):
        today = date(2026, 4, 10)
        self._add_discount(
            session, "Staré",
            valid_from=date(2026, 3, 1),
            valid_to=date(2026, 3, 7),
        )
        result = get_active_discounts(session, as_of=today)
        assert len(result) == 0

    def test_null_dates_always_active(self, session):
        self._add_discount(session, "Vždy platné")
        result = get_active_discounts(session, as_of=date(2026, 4, 10))
        assert len(result) == 1

    def test_filter_by_supermarket(self, session):
        run = save_scrape_run(session)
        save_discounts(session, run, [_make_parsed("Tesco zboží")], supermarket_name="tesco")
        save_discounts(session, run, [_make_parsed("Lidl zboží")], supermarket_name="lidl")
        result = get_active_discounts(session, supermarket_name="tesco")
        assert len(result) == 1
        assert result[0].name == "Tesco zboží"


class TestSearchDiscounts:
    def test_finds_by_substring(self, session):
        run = save_scrape_run(session)
        save_discounts(session, run, [_make_parsed("Rum Jamaica 0,7 l")])
        result = search_discounts(session, "rum")
        assert len(result) == 1

    def test_diacritic_insensitive(self, session):
        run = save_scrape_run(session)
        save_discounts(session, run, [_make_parsed("Káva mletá 250g")])
        result = search_discounts(session, "kava")
        assert len(result) == 1

    def test_no_match_returns_empty(self, session):
        run = save_scrape_run(session)
        save_discounts(session, run, [_make_parsed("Mléko")])
        assert search_discounts(session, "rum") == []


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------

class TestWatchlist:
    def test_add_item(self, session):
        item = add_watchlist_item(session, "rum")
        assert item.id is not None
        assert item.keyword == "rum"

    def test_add_duplicate_returns_existing(self, session):
        item1 = add_watchlist_item(session, "rum")
        item2 = add_watchlist_item(session, "rum")
        assert item1.id == item2.id

    def test_list_watchlist_sorted(self, session):
        add_watchlist_item(session, "pivo")
        add_watchlist_item(session, "rum")
        add_watchlist_item(session, "becherovka")
        result = list_watchlist(session)
        assert [i.keyword for i in result] == ["becherovka", "pivo", "rum"]

    def test_remove_item(self, session):
        add_watchlist_item(session, "rum")
        removed = remove_watchlist_item(session, "rum")
        assert removed is True
        assert list_watchlist(session) == []

    def test_remove_nonexistent_returns_false(self, session):
        assert remove_watchlist_item(session, "rum") is False
