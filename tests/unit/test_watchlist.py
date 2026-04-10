"""Unit tests for scraper.watchlist.load_watchlist."""
import textwrap

import pytest

from scraper.watchlist import load_watchlist


class TestLoadWatchlist:
    def test_basic_keywords(self, tmp_path):
        f = tmp_path / "watchlist.yaml"
        f.write_text("- rum\n- Becherovka\n- slivovice\n", encoding="utf-8")
        result = load_watchlist(f)
        assert result == ["becherovka", "rum", "slivovice"]  # sorted

    def test_lowercases_keywords(self, tmp_path):
        f = tmp_path / "watchlist.yaml"
        f.write_text("- WHISKY\n- Víno\n", encoding="utf-8")
        result = load_watchlist(f)
        assert "whisky" in result
        assert "víno" in result

    def test_strips_whitespace(self, tmp_path):
        f = tmp_path / "watchlist.yaml"
        f.write_text("- '  rum  '\n- '  pivo'\n", encoding="utf-8")
        result = load_watchlist(f)
        assert "rum" in result
        assert "pivo" in result

    def test_ignores_blanks(self, tmp_path):
        f = tmp_path / "watchlist.yaml"
        f.write_text("- rum\n- ''\n- pivo\n", encoding="utf-8")
        result = load_watchlist(f)
        assert "" not in result
        assert len(result) == 2

    def test_deduplicates(self, tmp_path):
        f = tmp_path / "watchlist.yaml"
        f.write_text("- rum\n- Rum\n- RUM\n", encoding="utf-8")
        result = load_watchlist(f)
        assert result.count("rum") == 1

    def test_missing_file_returns_empty(self, tmp_path):
        result = load_watchlist(tmp_path / "nonexistent.yaml")
        assert result == []

    def test_empty_file_returns_empty(self, tmp_path):
        f = tmp_path / "watchlist.yaml"
        f.write_text("", encoding="utf-8")
        result = load_watchlist(f)
        assert result == []

    def test_null_yaml_returns_empty(self, tmp_path):
        f = tmp_path / "watchlist.yaml"
        f.write_text("~\n", encoding="utf-8")
        result = load_watchlist(f)
        assert result == []

    def test_none_items_skipped(self, tmp_path):
        f = tmp_path / "watchlist.yaml"
        f.write_text("- rum\n- ~\n- pivo\n", encoding="utf-8")
        result = load_watchlist(f)
        assert result == ["pivo", "rum"]

    def test_non_list_raises_type_error(self, tmp_path):
        f = tmp_path / "watchlist.yaml"
        f.write_text("keywords: rum\n", encoding="utf-8")
        with pytest.raises(TypeError, match="must contain a YAML list"):
            load_watchlist(f)

    def test_returns_sorted(self, tmp_path):
        f = tmp_path / "watchlist.yaml"
        f.write_text("- pivo\n- rum\n- becherovka\n", encoding="utf-8")
        result = load_watchlist(f)
        assert result == sorted(result)

    def test_example_file_is_parseable(self):
        """watchlist.example.yaml must be parseable and return a non-empty list."""
        result = load_watchlist("watchlist.example.yaml")
        assert len(result) > 0
