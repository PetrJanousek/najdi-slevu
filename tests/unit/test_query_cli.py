"""Unit tests for scraper.cli query subcommands (list and search)."""
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from scraper.cli import app

runner = CliRunner(mix_stderr=False)


def _fake_row(
    name: str,
    price: float = 19.90,
    discount_pct: float = 33.4,
    valid_from=None,
    valid_to=None,
) -> SimpleNamespace:
    """Create a fake ORM Discount row as a SimpleNamespace."""
    return SimpleNamespace(
        name=name,
        discounted_price=price,
        original_price=29.90,
        discount_pct=discount_pct,
        valid_from=valid_from or date(2026, 4, 7),
        valid_to=valid_to or date(2026, 4, 13),
        raw_text=name,
        canonical_key=None,
    )


def _mock_session_ctx(rows):
    """Return a context manager mock that yields a session returning *rows*."""
    session_mock = MagicMock()
    session_ctx = MagicMock()
    session_ctx.__enter__ = MagicMock(return_value=session_mock)
    session_ctx.__exit__ = MagicMock(return_value=False)
    factory_mock = MagicMock(return_value=session_ctx)
    return factory_mock, rows


class TestQueryList:
    def test_lists_discounts(self):
        fakes = [_fake_row("Rum Jamaica"), _fake_row("Becherovka")]
        factory, _ = _mock_session_ctx(fakes)
        with (
            patch("scraper.cli.make_engine"),
            patch("scraper.cli.make_session_factory", return_value=factory),
            patch("scraper.cli.get_active_discounts", return_value=fakes),
            patch("scraper.cli.compute_product_stats"),
        ):
            result = runner.invoke(app, ["query", "list"])
        assert result.exit_code == 0
        assert "Rum Jamaica" in result.output

    def test_no_discounts_exits_cleanly(self):
        factory, _ = _mock_session_ctx([])
        with (
            patch("scraper.cli.make_engine"),
            patch("scraper.cli.make_session_factory", return_value=factory),
            patch("scraper.cli.get_active_discounts", return_value=[]),
        ):
            result = runner.invoke(app, ["query", "list"])
        assert result.exit_code == 0
        assert "No active discounts" in result.output

    def test_min_discount_filter(self):
        fakes = [
            _fake_row("Big discount", discount_pct=50.0),
            _fake_row("Small discount", discount_pct=5.0),
        ]
        factory, _ = _mock_session_ctx(fakes)
        with (
            patch("scraper.cli.make_engine"),
            patch("scraper.cli.make_session_factory", return_value=factory),
            patch("scraper.cli.get_active_discounts", return_value=fakes),
            patch("scraper.cli.compute_product_stats"),
        ):
            result = runner.invoke(app, ["query", "list", "--min-discount", "20"])
        assert "Big discount" in result.output
        assert "Small discount" not in result.output


class TestQuerySearch:
    def test_search_finds_result(self):
        fakes = [_fake_row("Rum Jamaica")]
        factory, _ = _mock_session_ctx(fakes)
        with (
            patch("scraper.cli.make_engine"),
            patch("scraper.cli.make_session_factory", return_value=factory),
            patch("scraper.cli.search_discounts", return_value=fakes),
        ):
            result = runner.invoke(app, ["query", "search", "rum"])
        assert result.exit_code == 0
        assert "Rum Jamaica" in result.output

    def test_search_no_results(self):
        factory, _ = _mock_session_ctx([])
        with (
            patch("scraper.cli.make_engine"),
            patch("scraper.cli.make_session_factory", return_value=factory),
            patch("scraper.cli.search_discounts", return_value=[]),
        ):
            result = runner.invoke(app, ["query", "search", "rum"])
        assert result.exit_code == 0
        assert "No discounts found" in result.output
