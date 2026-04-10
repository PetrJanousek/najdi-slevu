"""Unit tests for repo.get_price_history and repo.compute_product_stats."""
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scraper.db.models import Base
from scraper.db.repo import (
    ProductStats,
    compute_product_stats,
    get_price_history,
    save_discounts,
    save_scrape_run,
)
from scraper.models import Discount as ParsedDiscount


@pytest.fixture
def session():
    """In-memory SQLite session with full schema."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as s:
        yield s


def _parsed(name: str, price: float = 19.90, original: float = 29.90) -> ParsedDiscount:
    return ParsedDiscount(
        name=name,
        original_price=original,
        discounted_price=price,
        discount_pct=round((1 - price / original) * 100, 1),
        valid_from=None,
        valid_to=None,
        raw_text=name,
    )


def _add_at(session, name, price, original, days_ago, supermarket=None):
    """Helper: save a discount with scraped_at set to *days_ago* days ago."""
    ts = datetime.now(tz=timezone.utc) - timedelta(days=days_ago)
    run = save_scrape_run(session, started_at=ts)
    rows = save_discounts(
        session, run,
        [_parsed(name, price, original)],
        supermarket_name=supermarket,
    )
    return rows[0]


# ---------------------------------------------------------------------------
# get_price_history
# ---------------------------------------------------------------------------

class TestGetPriceHistory:
    def test_empty_for_unknown_key(self, session):
        result = get_price_history(session, "lihoviny|-|700ml")
        assert result == []

    def test_returns_one_point(self, session):
        row = _add_at(session, "Rum Jamaica 0,7 l", 149.90, 199.90, days_ago=10)
        points = get_price_history(session, row.canonical_key)
        assert len(points) == 1
        assert points[0].discounted_price == pytest.approx(149.90)
        assert points[0].original_price == pytest.approx(199.90)

    def test_includes_supermarket(self, session):
        _add_at(session, "Rum Jamaica 0,7 l", 149.90, 199.90, days_ago=5, supermarket="lidl")
        row = _add_at(session, "Rum Jamaica 0,7 l", 139.90, 199.90, days_ago=1)
        points = get_price_history(session, row.canonical_key)
        supermarkets = {p.supermarket for p in points}
        assert "lidl" in supermarkets

    def test_multiple_points_ordered_by_time(self, session):
        _add_at(session, "Rum Jamaica 0,7 l", 179.90, 199.90, days_ago=30)
        _add_at(session, "Rum Jamaica 0,7 l", 149.90, 199.90, days_ago=10)
        _add_at(session, "Rum Jamaica 0,7 l", 139.90, 199.90, days_ago=1)
        # All have same canonical key; get the key from one of them
        run = save_scrape_run(session)
        rows = save_discounts(session, run, [_parsed("Rum Jamaica 0,7 l", 139.90, 199.90)])
        points = get_price_history(session, rows[0].canonical_key)
        prices = [p.discounted_price for p in points]
        # Should be ordered by scraped_at ascending
        assert prices[0] >= prices[-1] or len(prices) == 1 or prices == sorted(prices, reverse=True)
        assert len(points) >= 3


# ---------------------------------------------------------------------------
# compute_product_stats
# ---------------------------------------------------------------------------

class TestComputeProductStats:
    def test_no_history_returns_empty_stats(self, session):
        stats = compute_product_stats(session, "lihoviny|-|700ml")
        assert stats.lowest_ever is None
        assert stats.is_at_historical_low is False
        assert stats.fake_discount is False
        assert stats.times_on_sale_90d == 0

    def test_single_point_stats(self, session):
        row = _add_at(session, "Rum Jamaica 0,7 l", 149.90, 199.90, days_ago=5)
        stats = compute_product_stats(session, row.canonical_key)
        assert stats.lowest_ever == pytest.approx(149.90)
        assert stats.lowest_90d == pytest.approx(149.90)
        assert stats.median_90d == pytest.approx(149.90)
        assert stats.times_on_sale_90d == 1

    def test_lowest_ever_finds_global_min(self, session):
        _add_at(session, "Pivo Pilsner 0,5 l", 15.90, 24.90, days_ago=200)
        row = _add_at(session, "Pivo Pilsner 0,5 l", 18.90, 24.90, days_ago=10)
        stats = compute_product_stats(session, row.canonical_key)
        assert stats.lowest_ever == pytest.approx(15.90)

    def test_lowest_90d_excludes_old_records(self, session):
        _add_at(session, "Pivo Pilsner 0,5 l", 12.90, 24.90, days_ago=200)  # outside 90d
        row = _add_at(session, "Pivo Pilsner 0,5 l", 18.90, 24.90, days_ago=5)  # within 90d
        stats = compute_product_stats(session, row.canonical_key)
        assert stats.lowest_ever == pytest.approx(12.90)
        assert stats.lowest_90d == pytest.approx(18.90)

    def test_times_on_sale_90d(self, session):
        _add_at(session, "Sýr Eidam 250 g", 29.90, 39.90, days_ago=100)  # outside
        row = _add_at(session, "Sýr Eidam 250 g", 29.90, 39.90, days_ago=30)
        _add_at(session, "Sýr Eidam 250 g", 27.90, 39.90, days_ago=10)
        stats = compute_product_stats(session, row.canonical_key)
        assert stats.times_on_sale_90d == 2

    def test_is_at_historical_low_when_current_equals_lowest(self, session):
        _add_at(session, "Káva mletá 250 g", 89.90, 119.90, days_ago=200)
        row = _add_at(session, "Káva mletá 250 g", 79.90, 119.90, days_ago=5)
        stats = compute_product_stats(session, row.canonical_key)
        assert stats.is_at_historical_low is True
        assert stats.lowest_ever == pytest.approx(79.90)

    def test_not_at_historical_low_when_cheaper_exists(self, session):
        _add_at(session, "Káva mletá 250 g", 69.90, 119.90, days_ago=200)
        row = _add_at(session, "Káva mletá 250 g", 89.90, 119.90, days_ago=5)
        stats = compute_product_stats(session, row.canonical_key)
        assert stats.is_at_historical_low is False

    def test_median_90d_computed(self, session):
        _add_at(session, "Mléko plnotučné 1 l", 19.90, 24.90, days_ago=80)
        _add_at(session, "Mléko plnotučné 1 l", 21.90, 24.90, days_ago=50)
        row = _add_at(session, "Mléko plnotučné 1 l", 18.90, 24.90, days_ago=5)
        stats = compute_product_stats(session, row.canonical_key)
        assert stats.median_90d == pytest.approx(19.90)  # median of 18.90, 19.90, 21.90

    def test_fake_discount_not_triggered_with_one_point(self, session):
        row = _add_at(session, "Becherovka 0,5 l", 189.90, 249.90, days_ago=5)
        stats = compute_product_stats(session, row.canonical_key)
        assert stats.fake_discount is False

    def test_fake_discount_triggered_when_prices_stable(self, session):
        """Fake: both disc and orig barely move over 60 days."""
        row = _add_at(session, "Becherovka 0,5 l", 189.90, 229.90, days_ago=55)
        _add_at(session, "Becherovka 0,5 l", 190.90, 230.00, days_ago=30)
        _add_at(session, "Becherovka 0,5 l", 189.50, 229.00, days_ago=5)
        stats = compute_product_stats(session, row.canonical_key)
        assert stats.fake_discount is True

    def test_fake_discount_not_triggered_when_price_drops(self, session):
        """Real discount: big price drop compared to 60d median."""
        _add_at(session, "Becherovka 0,5 l", 249.90, 249.90, days_ago=55)
        _add_at(session, "Becherovka 0,5 l", 248.90, 249.90, days_ago=30)
        row = _add_at(session, "Becherovka 0,5 l", 179.90, 249.90, days_ago=2)
        stats = compute_product_stats(session, row.canonical_key)
        assert stats.fake_discount is False


# ---------------------------------------------------------------------------
# CLI: query history command
# ---------------------------------------------------------------------------

class TestQueryHistoryCLI:
    def test_history_no_results(self):
        from typer.testing import CliRunner
        from scraper.cli import app
        runner = CliRunner(mix_stderr=False)
        factory = MagicMock()
        session_ctx = MagicMock()
        session_ctx.__enter__ = MagicMock(return_value=MagicMock())
        session_ctx.__exit__ = MagicMock(return_value=False)
        factory.return_value = session_ctx
        with (
            patch("scraper.cli.make_engine"),
            patch("scraper.cli.make_session_factory", return_value=factory),
            patch("scraper.cli.search_discounts", return_value=[]),
        ):
            result = runner.invoke(app, ["query", "history", "rum"])
        assert result.exit_code == 0
        assert "No discounts found" in result.output

    def test_history_shows_table(self):
        from typer.testing import CliRunner
        from scraper.db.repo import PricePoint
        from scraper.cli import app
        runner = CliRunner(mix_stderr=False)
        fake_row = SimpleNamespace(
            canonical_key="lihoviny|-|700ml",
            name="Rum Jamaica 0,7 l",
        )
        fake_points = [
            PricePoint(
                scraped_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
                supermarket="lidl",
                discounted_price=149.90,
                original_price=199.90,
                canonical_key="lihoviny|-|700ml",
            )
        ]
        factory = MagicMock()
        session_ctx = MagicMock()
        session_ctx.__enter__ = MagicMock(return_value=MagicMock())
        session_ctx.__exit__ = MagicMock(return_value=False)
        factory.return_value = session_ctx
        with (
            patch("scraper.cli.make_engine"),
            patch("scraper.cli.make_session_factory", return_value=factory),
            patch("scraper.cli.search_discounts", return_value=[fake_row]),
            patch("scraper.cli.get_price_history", return_value=fake_points),
        ):
            result = runner.invoke(app, ["query", "history", "rum"])
        assert result.exit_code == 0
        assert "lihoviny" in result.output
