"""Unit tests for CLI --supermarket flag and _guess_supermarket helper."""
from pathlib import Path

from scraper.cli import _guess_supermarket


class TestGuessSupport:
    def test_known_supermarket_in_parent_dir(self):
        path = Path("tests/fixtures/leaflets/lidl/2026-04-01.pdf")
        assert _guess_supermarket(path) == "lidl"

    def test_known_supermarket_grandparent(self):
        path = Path("/data/leaflets/tesco/april/2026-04-01.pdf")
        assert _guess_supermarket(path) == "tesco"

    def test_unknown_returns_none(self):
        path = Path("some/random/file.pdf")
        assert _guess_supermarket(path) is None

    def test_case_insensitive(self):
        path = Path("tests/fixtures/leaflets/Kaufland/2026-04-01.pdf")
        assert _guess_supermarket(path) == "kaufland"
