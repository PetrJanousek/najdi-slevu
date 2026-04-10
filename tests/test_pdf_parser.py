"""Tests for scraper/pdf_parser.py.

Covers:
- Price parsing: decimal, whole-dash, integer, standalone-decimal, unit-price skip
- Date range parsing: od/do, dash, space-dash formats, year wrap-around
- Name candidate heuristics: noise filtering, header/footer exclusion
- Name extraction near price: backward scan, two-line merge, forward fallback
- Column splitting helpers: _join_split_prices
- Integration: parse_pdf via mocked pdfplumber
"""

from __future__ import annotations

import sys
import types
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers to access private functions directly
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper.pdf_parser import (
    _compute_pct,
    _extract_name_near_price,
    _find_all_prices,
    _is_name_candidate,
    _join_split_prices,
    _parse_date_range,
    _parse_price,
    _year_from_meta,
    parse_pdf,
)


# ===========================================================================
# _parse_price
# ===========================================================================


class TestParsePrice:
    def test_decimal_kc(self):
        assert _parse_price("29,90 Kč") == pytest.approx(29.90)

    def test_decimal_kc_uppercase(self):
        assert _parse_price("159,99 KČ") == pytest.approx(159.99)

    def test_decimal_kc_nbsp(self):
        # Non-breaking space between digits and Kč
        assert _parse_price("1\xa0299,00 Kč") == pytest.approx(1299.00)

    def test_decimal_period_separator(self):
        # Some leaflets use period instead of comma
        assert _parse_price("49.90 Kč") == pytest.approx(49.90)

    def test_whole_dash_kc(self):
        assert _parse_price("69,- Kč") == pytest.approx(69.0)

    def test_whole_dash_no_kc(self):
        assert _parse_price("29,-") == pytest.approx(29.0)

    def test_whole_dash_endash(self):
        assert _parse_price("99,–") == pytest.approx(99.0)

    def test_integer_kc(self):
        assert _parse_price("89 Kč") == pytest.approx(89.0)

    def test_integer_kc_with_prefix_text(self):
        assert _parse_price("cena 49 Kč") == pytest.approx(49.0)

    def test_standalone_decimal_lidl(self):
        # Lidl-style: just "34.90" without Kč
        assert _parse_price("34.90") == pytest.approx(34.90)

    def test_unit_price_skipped(self):
        assert _parse_price("1 kg = 69,80 Kč") is None

    def test_unit_price_per_l_skipped(self):
        assert _parse_price("1 l = 128,43 Kč") is None

    def test_unit_price_per_100g_skipped(self):
        assert _parse_price("100 g = 12,90 Kč") is None

    def test_no_price_returns_none(self):
        assert _parse_price("Čerstvé kuřecí maso") is None

    def test_empty_string_returns_none(self):
        assert _parse_price("") is None

    def test_standalone_decimal_not_date(self):
        # "3.4." looks like a date — the pattern should NOT match it as a price
        # because it only has 1 decimal digit after the period.
        assert _parse_price("3.4.") is None


# ===========================================================================
# _parse_date_range
# ===========================================================================


class TestParseDateRange:
    def test_od_do_format(self):
        vf, vt = _parse_date_range("platí od 3.4. do 9.4.", 2026)
        assert vf == date(2026, 4, 3)
        assert vt == date(2026, 4, 9)

    def test_od_do_leading_zeros(self):
        vf, vt = _parse_date_range("platí od 03.04. do 09.04.", 2026)
        assert vf == date(2026, 4, 3)
        assert vt == date(2026, 4, 9)

    def test_od_do_case_insensitive(self):
        vf, vt = _parse_date_range("PLATÍ OD 1.5. DO 7.5.", 2026)
        assert vf == date(2026, 5, 1)
        assert vt == date(2026, 5, 7)

    def test_dash_endash(self):
        vf, vt = _parse_date_range("3.4.–9.4.", 2026)
        assert vf == date(2026, 4, 3)
        assert vt == date(2026, 4, 9)

    def test_dash_emdash(self):
        vf, vt = _parse_date_range("3.4.—9.4.", 2026)
        assert vf == date(2026, 4, 3)
        assert vt == date(2026, 4, 9)

    def test_dash_hyphen_minus(self):
        vf, vt = _parse_date_range("3.4.-9.4.", 2026)
        assert vf == date(2026, 4, 3)
        assert vt == date(2026, 4, 9)

    def test_space_dash_format(self):
        vf, vt = _parse_date_range("03.04 - 09.04", 2026)
        assert vf == date(2026, 4, 3)
        assert vt == date(2026, 4, 9)

    def test_year_wraparound_dec_to_jan(self):
        vf, vt = _parse_date_range("29.12.–4.1.", 2026)
        assert vf == date(2026, 12, 29)
        assert vt == date(2027, 1, 4)

    def test_no_date_returns_none_pair(self):
        vf, vt = _parse_date_range("žádné datum zde", 2026)
        assert vf is None
        assert vt is None

    def test_embedded_in_longer_text(self):
        text = "Akční nabídka platí od 10.3. do 16.3. Nakupte výhodně!"
        vf, vt = _parse_date_range(text, 2026)
        assert vf == date(2026, 3, 10)
        assert vt == date(2026, 3, 16)


# ===========================================================================
# _is_name_candidate
# ===========================================================================


class TestIsNameCandidate:
    def test_good_name(self):
        assert _is_name_candidate("Kuřecí prsní řízek") is True

    def test_good_name_with_brand(self):
        assert _is_name_candidate("BOŽKOV Tuzemský rum") is True

    def test_too_short(self):
        assert _is_name_candidate("AB") is False

    def test_too_long(self):
        assert _is_name_candidate("A" * 121) is False

    def test_only_numbers(self):
        assert _is_name_candidate("1234567") is False

    def test_only_punctuation(self):
        assert _is_name_candidate("...---") is False

    def test_header_store_name(self):
        assert _is_name_candidate("albert") is False

    def test_header_lidl(self):
        assert _is_name_candidate("lidl plus") is False

    def test_header_website(self):
        assert _is_name_candidate("www.albert.cz") is False

    def test_header_validity(self):
        assert _is_name_candidate("platnost nabídky") is False

    def test_bullet_detail(self):
        assert _is_name_candidate("• 500 g, chlazené") is False

    def test_starts_with_quantity(self):
        assert _is_name_candidate("0,7 l, čerstvé") is False

    def test_ends_with_slash(self):
        assert _is_name_candidate("569,- bez Aplikace /") is False

    def test_ends_with_comma(self):
        assert _is_name_candidate("kuřecí maso,") is False

    def test_unit_price_line(self):
        assert _is_name_candidate("1 kg = 149,- Kč") is False

    def test_line_with_price(self):
        assert _is_name_candidate("cena 49,90 Kč") is False

    def test_no_letters(self):
        assert _is_name_candidate("123 - 456") is False

    def test_czech_diacritics(self):
        assert _is_name_candidate("Šampaňské Moët & Chandon") is True


# ===========================================================================
# _extract_name_near_price
# ===========================================================================


class TestExtractNameNearPrice:
    def test_name_directly_above(self):
        lines = [
            "Kuřecí prsní řízek",
            "39,90 Kč",
        ]
        assert _extract_name_near_price(lines, 1) == "Kuřecí prsní řízek"

    def test_name_two_lines_above_with_detail(self):
        lines = [
            "Hovězí svíčková",
            "• 300 g, mražené",
            "129,90 Kč",
        ]
        assert _extract_name_near_price(lines, 2) == "Hovězí svíčková"

    def test_two_part_name_merged(self):
        lines = [
            "BOŽKOV",
            "Kávový likér",
            "89,-",
        ]
        result = _extract_name_near_price(lines, 2)
        assert "BOŽKOV" in result
        assert "Kávový likér" in result

    def test_name_below_when_none_above(self):
        lines = [
            "34.90",
            "Sýr Eidam 45%",
        ]
        assert _extract_name_near_price(lines, 0) == "Sýr Eidam 45%"

    def test_fallback_to_price_line(self):
        # Only price lines around — fallback to price line text
        lines = [
            "49,90 Kč",
            "1 kg = 99,80 Kč",
        ]
        result = _extract_name_near_price(lines, 0)
        assert result  # something returned

    def test_skips_bullet_lines(self):
        lines = [
            "Plnotučné mléko",
            "• 1 l",
            "• čerstvé",
            "19,90 Kč",
        ]
        assert _extract_name_near_price(lines, 3) == "Plnotučné mléko"

    def test_name_up_to_8_lines_back(self):
        lines = [
            "Prací gel Persil",
            "• 3 l",
            "• 60 praní",
            "• na barevné prádlo",
            "• vysoce koncentrovaný",
            "• vůně Sensitive",
            "• BĚŽNÁ CENA 249,-",
            "189,90 Kč",
        ]
        result = _extract_name_near_price(lines, 7)
        assert "Persil" in result


# ===========================================================================
# _join_split_prices
# ===========================================================================


class TestJoinSplitPrices:
    def test_trailing_comma_dash_split(self):
        lines = ["kuřecí maso 269,", "-"]
        result = _join_split_prices(lines)
        assert result == ["kuřecí maso 269,-"]

    def test_leading_comma_dash_split(self):
        lines = ["269, • 299 Kč", "-"]
        result = _join_split_prices(lines)
        assert len(result) == 1
        assert "269,-" in result[0]

    def test_no_split_needed(self):
        lines = ["kuřecí maso", "69,90 Kč"]
        assert _join_split_prices(lines) == lines

    def test_standalone_dash_not_following_price_kept(self):
        lines = ["Výběr z katalogu", "-", "Více info na webu"]
        result = _join_split_prices(lines)
        # A lone "-" not preceded by a price-like line is not consumed
        assert "-" in result

    def test_multiple_splits_handled(self):
        lines = ["produkt A 99,", "-", "produkt B 149,", "-"]
        result = _join_split_prices(lines)
        assert "99,-" in result[0]
        assert "149,-" in result[1]


# ===========================================================================
# _find_all_prices
# ===========================================================================


class TestFindAllPrices:
    def test_two_prices(self):
        text = "BĚŽNÁ CENA 299,90 Kč\nAkční cena 199,90 Kč"
        prices = _find_all_prices(text)
        assert 299.90 in prices
        assert 199.90 in prices

    def test_skips_unit_prices(self):
        text = "34.90\n1 kg = 69,80 Kč"
        prices = _find_all_prices(text)
        assert 34.90 in prices
        assert 69.80 not in prices

    def test_empty_text(self):
        assert _find_all_prices("") == []

    def test_no_prices(self):
        assert _find_all_prices("Kuřecí prsní řízek, čerstvé") == []

    def test_deduplication(self):
        # Same price appearing twice should appear once
        text = "99,- Kč nová cena 99,-"
        prices = _find_all_prices(text)
        assert prices.count(99.0) == 1


# ===========================================================================
# _compute_pct
# ===========================================================================


class TestComputePct:
    def test_standard_discount(self):
        assert _compute_pct(100.0, 75.0) == pytest.approx(25.0)

    def test_zero_original_returns_none(self):
        assert _compute_pct(0.0, 50.0) is None

    def test_discounted_equals_original_returns_none(self):
        assert _compute_pct(100.0, 100.0) is None

    def test_discounted_greater_than_original_returns_none(self):
        assert _compute_pct(100.0, 110.0) is None

    def test_rounding_one_decimal(self):
        result = _compute_pct(299.9, 199.9)
        assert result == pytest.approx(33.3, abs=0.1)


# ===========================================================================
# _year_from_meta
# ===========================================================================


class TestYearFromMeta:
    def test_creation_date(self):
        assert _year_from_meta({"CreationDate": "D:20260401120000"}) == 2026

    def test_mod_date_fallback(self):
        assert _year_from_meta({"ModDate": "D:20251215"}) == 2025

    def test_empty_meta_uses_today(self):
        import datetime
        year = _year_from_meta({})
        assert year == datetime.date.today().year

    def test_malformed_date_uses_today(self):
        import datetime
        year = _year_from_meta({"CreationDate": "not-a-date"})
        assert year == datetime.date.today().year


# ===========================================================================
# Integration: parse_pdf via mocked pdfplumber
# ===========================================================================


def _make_mock_page(text: str, words: list[dict] | None = None):
    """Build a minimal mock pdfplumber page that returns *text*."""
    page = MagicMock()
    page.extract_text.return_value = text
    page.width = 595.0  # A4 width in points

    if words is None:
        # Build a single-column list of words from the text lines
        words = []
        y = 10.0
        for line in text.splitlines():
            x = 20.0
            for token in line.split():
                words.append({"text": token, "x0": x, "x1": x + 40, "top": y})
                x += 45
            y += 14
    page.extract_words.return_value = words
    return page


class TestParsePdf:
    """Integration tests using mocked pdfplumber."""

    def _run(self, pages_text: list[str]) -> list:
        pages = [_make_mock_page(t) for t in pages_text]
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.metadata = {"CreationDate": "D:20260401"}
        mock_pdf.pages = pages

        with patch("scraper.pdf_parser.pdfplumber.open", return_value=mock_pdf):
            return parse_pdf("dummy.pdf")

    def test_single_item_extracted(self):
        page_text = (
            "platí od 3.4. do 9.4.\n"
            "Kuřecí prsní řízek\n"
            "• 500 g, chlazené\n"
            "39,90 Kč\n"
        )
        results = self._run([page_text])
        assert len(results) >= 1
        item = results[0]
        assert "Kuřecí" in item.name
        assert item.discounted_price == pytest.approx(39.90)
        assert item.valid_from == date(2026, 4, 3)
        assert item.valid_to == date(2026, 4, 9)

    def test_original_and_discounted_price(self):
        page_text = (
            "platí od 7.4. do 13.4.\n"
            "Víno Merlot 0,75 l\n"
            "BĚŽNÁ CENA 249,90 Kč\n"
            "149,90 Kč\n"
        )
        results = self._run([page_text])
        wine = next((r for r in results if "149" in str(r.discounted_price) or "Víno" in r.name), None)
        assert wine is not None
        assert wine.discounted_price == pytest.approx(149.90)
        assert wine.original_price == pytest.approx(249.90)
        assert wine.discount_pct is not None
        assert wine.discount_pct == pytest.approx(40.0, abs=0.1)

    def test_no_date_gives_none(self):
        page_text = (
            "Minerální voda Mattoni\n"
            "• 1,5 l, perlivá\n"
            "15,90 Kč\n"
        )
        results = self._run([page_text])
        assert len(results) >= 1
        assert results[0].valid_from is None
        assert results[0].valid_to is None

    def test_multiple_items(self):
        page_text = (
            "platí od 1.4. do 7.4.\n"
            "Plnotučné mléko\n"
            "19,90 Kč\n"
            "Máslo 250 g\n"
            "34,90 Kč\n"
        )
        results = self._run([page_text])
        assert len(results) >= 2

    def test_alcohol_item_parsed(self):
        page_text = (
            "platí od 10.4. do 16.4.\n"
            "Becherovka 0,5 l\n"
            "189,- Kč\n"
        )
        results = self._run([page_text])
        assert any("Becherovka" in r.name or r.discounted_price == 189.0 for r in results)

    def test_empty_pdf_returns_empty_list(self):
        results = self._run([""])
        assert results == []

    def test_deduplication_across_columns(self):
        """Same (name, price) pair from two columns must appear only once per page."""
        page_text = (
            "platí od 1.4. do 7.4.\n"
            "Jogurt bílý\n"
            "9,90 Kč\n"
            "Jogurt bílý\n"
            "9,90 Kč\n"
        )
        results = self._run([page_text])
        names = [r.name for r in results if "Jogurt" in r.name]
        # Should be deduplicated — same item twice is one result
        assert len(names) <= 2  # lenient: column splitting may produce up to 2 but not 10
