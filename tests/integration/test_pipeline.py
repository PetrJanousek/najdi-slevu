"""Integration tests for the main.py pipeline.

Monkeypatches:
- scraper.gmail_client.fetch_leaflet_pdfs → returns a fake PDF path list
- scraper.pdf_parser.parse_pdf (in main module) → returns synthetic Discount objects

This verifies the pipeline glue (Gmail fetch → parse → display) without
hitting real Gmail or requiring real PDF fixtures.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from main import app
from scraper.models import Discount

runner = CliRunner(mix_stderr=False)

# Synthetic discounts that the mocked parser returns
_FAKE_DISCOUNTS = [
    Discount(
        name="Čerstvé mléko",
        original_price=29.90,
        discounted_price=19.90,
        discount_pct=33.4,
        valid_from=date(2026, 4, 7),
        valid_to=date(2026, 4, 13),
        raw_text="Čerstvé mléko 29,90 Kč → 19,90 Kč",
    ),
    Discount(
        name="Celozrnný chléb",
        original_price=None,
        discounted_price=39.90,
        discount_pct=None,
        valid_from=date(2026, 4, 7),
        valid_to=date(2026, 4, 13),
        raw_text="Celozrnný chléb 39,90 Kč",
    ),
]

_FAKE_PDF = Path("/fake/tesco/2026-04-07.pdf")


def _mock_fetch(credentials_path=None, token_path=None, **kwargs):
    return [_FAKE_PDF]


def _mock_parse(path):
    return _FAKE_DISCOUNTS


class TestPipelineGlue:
    def test_pipeline_prints_table(self):
        """Pipeline fetches PDFs, parses them, and outputs a Rich table."""
        with (
            patch("main.fetch_leaflet_pdfs", side_effect=_mock_fetch),
            patch("main.parse_pdf", side_effect=_mock_parse),
        ):
            result = runner.invoke(app, ["--credentials", "fake.json", "--token", "fake.json"])

        assert result.exit_code == 0
        assert "Čerstvé mléko" in result.output
        assert "Celozrnný chléb" in result.output

    def test_pipeline_prints_prices(self):
        """Discounted prices appear in the output."""
        with (
            patch("main.fetch_leaflet_pdfs", side_effect=_mock_fetch),
            patch("main.parse_pdf", side_effect=_mock_parse),
        ):
            result = runner.invoke(app, [])

        # Prices formatted as "XX,XX Kč" (Czech style)
        assert "19,90" in result.output
        assert "39,90" in result.output

    def test_pipeline_no_pdfs_exits_cleanly(self):
        """When Gmail returns no PDFs, pipeline exits with message — no crash."""
        with patch("main.fetch_leaflet_pdfs", return_value=[]):
            result = runner.invoke(app, [])

        assert result.exit_code == 0
        assert "No new leaflets" in result.output

    def test_pipeline_alcohol_only_filters(self):
        """--alcohol-only flag filters down to alcohol-related discounts."""
        with (
            patch("main.fetch_leaflet_pdfs", side_effect=_mock_fetch),
            patch("main.parse_pdf", side_effect=_mock_parse),
        ):
            result = runner.invoke(app, ["--alcohol-only"])

        # Neither fake discount contains alcohol keywords → table should be empty or absent
        # We just verify it doesn't crash
        assert result.exit_code == 0

    def test_pipeline_shows_pdf_filename_header(self):
        """Each PDF gets a filename header line in the output."""
        with (
            patch("main.fetch_leaflet_pdfs", side_effect=_mock_fetch),
            patch("main.parse_pdf", side_effect=_mock_parse),
        ):
            result = runner.invoke(app, [])

        assert "2026-04-07.pdf" in result.output

    def _db_watchlist_patch(self, keywords: list[str]):
        """Return patches that make main.py load *keywords* from the DB watchlist."""
        items = [SimpleNamespace(keyword=kw) for kw in keywords]
        session_mock = MagicMock()
        session_ctx = MagicMock()
        session_ctx.__enter__ = MagicMock(return_value=session_mock)
        session_ctx.__exit__ = MagicMock(return_value=False)
        factory_mock = MagicMock(return_value=session_ctx)
        return (
            patch("main.make_engine"),
            patch("main.make_session_factory", return_value=factory_mock),
            patch("main.list_watchlist", return_value=items),
        )

    def test_hot_deals_shown_when_watchlist_matches(self):
        """HOT DEALS panel appears when DB watchlist matches a discount."""
        p1, p2, p3 = self._db_watchlist_patch(["mléko"])
        with (
            patch("main.fetch_leaflet_pdfs", side_effect=_mock_fetch),
            patch("main.parse_pdf", side_effect=_mock_parse),
            p1, p2, p3,
        ):
            result = runner.invoke(app, [])

        assert result.exit_code == 0
        assert "HOT DEALS" in result.output

    def test_hot_deals_absent_when_no_watchlist_match(self):
        """HOT DEALS panel is absent when DB watchlist has no matching keywords."""
        p1, p2, p3 = self._db_watchlist_patch(["rum"])  # no rum in fakes
        with (
            patch("main.fetch_leaflet_pdfs", side_effect=_mock_fetch),
            patch("main.parse_pdf", side_effect=_mock_parse),
            p1, p2, p3,
        ):
            result = runner.invoke(app, [])

        assert result.exit_code == 0
        assert "HOT DEALS" not in result.output

    def test_hot_deals_absent_when_no_watchlist(self):
        """HOT DEALS panel absent when DB watchlist is empty."""
        p1, p2, p3 = self._db_watchlist_patch([])
        with (
            patch("main.fetch_leaflet_pdfs", side_effect=_mock_fetch),
            patch("main.parse_pdf", side_effect=_mock_parse),
            p1, p2, p3,
        ):
            result = runner.invoke(app, [])

        assert result.exit_code == 0
        assert "HOT DEALS" not in result.output
