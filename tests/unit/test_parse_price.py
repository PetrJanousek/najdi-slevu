"""Unit tests for scraper.pdf_parser._parse_price and related helpers.

These tests exercise the parsing logic with synthetic strings — no PDF files
needed. They form a regression net for T-1.2 parser hardening.
"""
import pytest
from scraper.pdf_parser import (
    _parse_price,
    _parse_date_range,
    _is_name_candidate,
    _find_all_prices,
    _join_split_prices,
    _compute_pct,
)
from datetime import date


# ---------------------------------------------------------------------------
# _parse_price
# ---------------------------------------------------------------------------

class TestParsePrice:
    def test_decimal_czk(self):
        assert _parse_price("Mléko 29,90 Kč") == pytest.approx(29.90)

    def test_decimal_czk_uppercase(self):
        assert _parse_price("Jogurt 49,90 KČ") == pytest.approx(49.90)

    def test_whole_dash(self):
        assert _parse_price("Pivo 29,- Kč") == pytest.approx(29.0)

    def test_whole_dash_no_czk(self):
        assert _parse_price("Rum 269,-") == pytest.approx(269.0)

    def test_whole_dash_en_dash(self):
        assert _parse_price("Sýr 149,–") == pytest.approx(149.0)

    def test_integer_czk(self):
        assert _parse_price("Chléb 25 Kč") == pytest.approx(25.0)

    def test_lidl_standalone_decimal(self):
        """Lidl-style: period-separated decimal without Kč."""
        assert _parse_price("34.90") == pytest.approx(34.90)

    def test_lidl_standalone_decimal_in_context(self):
        assert _parse_price("Máslo 34.90 500g") == pytest.approx(34.90)

    def test_unit_price_skipped(self):
        """Lines like '1 kg = 69,80 Kč' must be skipped."""
        assert _parse_price("1 kg = 69,80 Kč") is None

    def test_unit_price_100g_skipped(self):
        assert _parse_price("100 g = 12,50 Kč") is None

    def test_unit_price_1l_skipped(self):
        assert _parse_price("1 l = 428,43 Kč") is None

    def test_no_price(self):
        assert _parse_price("Čerstvé ovoce a zelenina") is None

    def test_price_with_nbsp(self):
        """Non-breaking space in "1\xa0990 Kč" must be handled."""
        assert _parse_price("Televize 1\xa0990 Kč") == pytest.approx(1990.0)

    def test_price_zero_not_returned(self):
        """A zero price should be treated as None by callers (but _parse_price may return 0.0)."""
        # Parser shouldn't crash on "0 Kč"
        result = _parse_price("0 Kč")
        # Acceptable: 0.0 or None; must not raise
        assert result is None or result == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# _parse_date_range
# ---------------------------------------------------------------------------

class TestParseDateRange:
    def test_od_do_format(self):
        valid_from, valid_to = _parse_date_range("platí od 3.4. do 9.4.", 2026)
        assert valid_from == date(2026, 4, 3)
        assert valid_to == date(2026, 4, 9)

    def test_od_do_with_leading_zeros(self):
        valid_from, valid_to = _parse_date_range("platí od 03.04. do 09.04.", 2026)
        assert valid_from == date(2026, 4, 3)
        assert valid_to == date(2026, 4, 9)

    def test_dash_format(self):
        valid_from, valid_to = _parse_date_range("3.4.–9.4.", 2026)
        assert valid_from == date(2026, 4, 3)
        assert valid_to == date(2026, 4, 9)

    def test_dash_format_with_spaces(self):
        valid_from, valid_to = _parse_date_range("03.04. – 09.04.", 2026)
        assert valid_from == date(2026, 4, 3)
        assert valid_to == date(2026, 4, 9)

    def test_hyphen_format(self):
        valid_from, valid_to = _parse_date_range("3.4. - 9.4.", 2026)
        assert valid_from == date(2026, 4, 3)
        assert valid_to == date(2026, 4, 9)

    def test_year_wrap_december_to_january(self):
        """Dec 28 → Jan 4 should bump valid_to to next year."""
        valid_from, valid_to = _parse_date_range("28.12.–4.1.", 2025)
        assert valid_from == date(2025, 12, 28)
        assert valid_to == date(2026, 1, 4)

    def test_no_date_returns_none_none(self):
        valid_from, valid_to = _parse_date_range("Výrazné slevy každý den", 2026)
        assert valid_from is None
        assert valid_to is None

    def test_invalid_date_returns_none_none(self):
        """Bad date like day=99 should not crash, returns None, None."""
        valid_from, valid_to = _parse_date_range("platí od 99.4. do 100.4.", 2026)
        assert valid_from is None
        assert valid_to is None


# ---------------------------------------------------------------------------
# _is_name_candidate
# ---------------------------------------------------------------------------

class TestIsNameCandidate:
    def test_valid_product_name(self):
        assert _is_name_candidate("Čerstvé mléko plnotučné") is True

    def test_too_short(self):
        assert _is_name_candidate("AB") is False

    def test_too_long(self):
        assert _is_name_candidate("A" * 121) is False

    def test_noise_only_digits(self):
        assert _is_name_candidate("123.45") is False

    def test_bullet_line_excluded(self):
        assert _is_name_candidate("• 500 g, původ: ČR") is False

    def test_header_tesco_excluded(self):
        assert _is_name_candidate("tesco leták") is False

    def test_header_www_excluded(self):
        assert _is_name_candidate("www.example.com") is False

    def test_price_line_excluded(self):
        """Lines containing a price are not product names."""
        assert _is_name_candidate("29,90 Kč") is False

    def test_unit_price_excluded(self):
        assert _is_name_candidate("1 kg = 69,80 Kč") is False

    def test_line_starting_with_quantity(self):
        assert _is_name_candidate("0,7 l, sklenice") is False

    def test_line_ending_with_slash(self):
        assert _is_name_candidate("269,- bez Aplikace /") is False

    def test_line_ending_with_comma(self):
        assert _is_name_candidate("Jogurt, různé druhy,") is False

    def test_no_letters(self):
        assert _is_name_candidate("2026") is False


# ---------------------------------------------------------------------------
# _find_all_prices
# ---------------------------------------------------------------------------

class TestFindAllPrices:
    def test_finds_multiple_prices(self):
        text = "Běžná cena 49,90 Kč\nAkční cena 29,90 Kč"
        prices = _find_all_prices(text)
        assert pytest.approx(29.90) in prices
        assert pytest.approx(49.90) in prices

    def test_skips_unit_price_lines(self):
        text = "1 kg = 299,80 Kč\n29,90 Kč"
        prices = _find_all_prices(text)
        assert pytest.approx(29.90) in prices
        # 299.80 should not appear (it's a unit price)
        assert not any(abs(p - 299.80) < 0.01 for p in prices)

    def test_lidl_standalone_included(self):
        prices = _find_all_prices("34.90")
        assert pytest.approx(34.90) in prices


# ---------------------------------------------------------------------------
# _join_split_prices
# ---------------------------------------------------------------------------

class TestJoinSplitPrices:
    def test_trailing_comma_joined(self):
        result = _join_split_prices(["some text 269,", "-"])
        assert result == ["some text 269,-"]

    def test_leading_comma_joined(self):
        result = _join_split_prices(["269, • 299 Kč", "-"])
        assert result == ["269,- • 299 Kč"]

    def test_no_join_without_dash_next(self):
        result = _join_split_prices(["269,", "Kč"])
        assert result == ["269,", "Kč"]

    def test_ordinary_lines_unchanged(self):
        lines = ["Máslo", "29,90 Kč", "• 250 g"]
        assert _join_split_prices(lines) == lines


# ---------------------------------------------------------------------------
# _compute_pct
# ---------------------------------------------------------------------------

class TestComputePct:
    def test_basic(self):
        assert _compute_pct(100.0, 75.0) == pytest.approx(25.0)

    def test_rounding(self):
        assert _compute_pct(49.90, 29.90) == pytest.approx(40.1, abs=0.1)

    def test_zero_original_returns_none(self):
        assert _compute_pct(0.0, 0.0) is None

    def test_discounted_gte_original_returns_none(self):
        assert _compute_pct(25.0, 30.0) is None
        assert _compute_pct(25.0, 25.0) is None
