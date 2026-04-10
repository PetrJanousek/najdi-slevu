"""Unit tests for scraper.cli watchlist subcommands (add, list, remove)."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from scraper.cli import app

runner = CliRunner(mix_stderr=False)


def _mock_session_factory():
    """Return a context manager mock that yields a session."""
    session_mock = MagicMock()
    session_ctx = MagicMock()
    session_ctx.__enter__ = MagicMock(return_value=session_mock)
    session_ctx.__exit__ = MagicMock(return_value=False)
    factory_mock = MagicMock(return_value=session_ctx)
    return factory_mock, session_mock


class TestWatchlistAdd:
    def test_adds_keyword(self):
        factory, session = _mock_session_factory()
        item = SimpleNamespace(id=1, keyword="rum")
        with (
            patch("scraper.cli.make_engine"),
            patch("scraper.cli.make_session_factory", return_value=factory),
            patch("scraper.cli.add_watchlist_item", return_value=item),
        ):
            result = runner.invoke(app, ["watchlist", "add", "rum"])
        assert result.exit_code == 0
        assert "rum" in result.output

    def test_normalizes_keyword_to_lowercase(self):
        factory, session = _mock_session_factory()
        item = SimpleNamespace(id=2, keyword="becherovka")
        captured = {}
        def fake_add(sess, kw):
            captured["kw"] = kw
            return item
        with (
            patch("scraper.cli.make_engine"),
            patch("scraper.cli.make_session_factory", return_value=factory),
            patch("scraper.cli.add_watchlist_item", side_effect=fake_add),
        ):
            runner.invoke(app, ["watchlist", "add", "Becherovka"])
        assert captured["kw"] == "becherovka"


class TestWatchlistList:
    def test_lists_keywords(self):
        factory, _ = _mock_session_factory()
        items = [SimpleNamespace(keyword="becherovka"), SimpleNamespace(keyword="rum")]
        with (
            patch("scraper.cli.make_engine"),
            patch("scraper.cli.make_session_factory", return_value=factory),
            patch("scraper.cli.list_watchlist", return_value=items),
        ):
            result = runner.invoke(app, ["watchlist", "list"])
        assert result.exit_code == 0
        assert "becherovka" in result.output
        assert "rum" in result.output

    def test_empty_watchlist_message(self):
        factory, _ = _mock_session_factory()
        with (
            patch("scraper.cli.make_engine"),
            patch("scraper.cli.make_session_factory", return_value=factory),
            patch("scraper.cli.list_watchlist", return_value=[]),
        ):
            result = runner.invoke(app, ["watchlist", "list"])
        assert result.exit_code == 0
        assert "empty" in result.output.lower()


class TestWatchlistRemove:
    def test_removes_keyword(self):
        factory, _ = _mock_session_factory()
        with (
            patch("scraper.cli.make_engine"),
            patch("scraper.cli.make_session_factory", return_value=factory),
            patch("scraper.cli.remove_watchlist_item", return_value=True),
        ):
            result = runner.invoke(app, ["watchlist", "remove", "rum"])
        assert result.exit_code == 0
        assert "removed" in result.output

    def test_remove_nonexistent_exits_with_error(self):
        factory, _ = _mock_session_factory()
        with (
            patch("scraper.cli.make_engine"),
            patch("scraper.cli.make_session_factory", return_value=factory),
            patch("scraper.cli.remove_watchlist_item", return_value=False),
        ):
            result = runner.invoke(app, ["watchlist", "remove", "rum"])
        assert result.exit_code == 1
        assert "not found" in result.output
