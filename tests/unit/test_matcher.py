"""Unit tests for scraper.watchlist.match_discounts."""
from datetime import date

import pytest

from scraper.models import Discount
from scraper.watchlist import match_discounts, _strip_diacritics


def _make_discount(name: str, price: float = 29.90) -> Discount:
    return Discount(
        name=name,
        original_price=None,
        discounted_price=price,
        discount_pct=None,
        valid_from=None,
        valid_to=None,
        raw_text=name,
    )


class TestStripDiacritics:
    def test_removes_czech_accents(self):
        assert _strip_diacritics("káva") == "kava"
        assert _strip_diacritics("Becherovka") == "Becherovka"
        assert _strip_diacritics("slivovice") == "slivovice"
        assert _strip_diacritics("Švestková") == "Svestkova"

    def test_empty_string(self):
        assert _strip_diacritics("") == ""

    def test_no_diacritics_unchanged(self):
        assert _strip_diacritics("rum") == "rum"


class TestMatchDiscounts:
    def test_basic_match(self):
        discounts = [_make_discount("Rum Jamaica"), _make_discount("Mléko")]
        result = match_discounts(discounts, ["rum"])
        assert len(result) == 1
        assert result[0].name == "Rum Jamaica"

    def test_case_insensitive(self):
        discounts = [_make_discount("RUM ZLATÝ")]
        result = match_discounts(discounts, ["rum"])
        assert len(result) == 1

    def test_keyword_with_upper_case(self):
        discounts = [_make_discount("rum z Jamajky")]
        result = match_discounts(discounts, ["Rum"])
        assert len(result) == 1

    def test_diacritic_insensitive_keyword_vs_name(self):
        """Keyword 'kava' should match discount name 'Káva'."""
        discounts = [_make_discount("Káva mletá 250g")]
        result = match_discounts(discounts, ["kava"])
        assert len(result) == 1

    def test_diacritic_insensitive_name_vs_keyword(self):
        """Keyword 'káva' should match discount name 'Kava' (no accent)."""
        discounts = [_make_discount("Kava mletá")]
        result = match_discounts(discounts, ["káva"])
        assert len(result) == 1

    def test_diacritic_both_have_accents(self):
        """Keyword 'švestková' (accented) matches 'Svestkova slivovice' (no accents)."""
        discounts = [_make_discount("Svestkova slivovice")]
        result = match_discounts(discounts, ["švestková"])
        assert len(result) == 1

    def test_partial_match(self):
        """Substring match: 'pivo' matches 'Pivo světlé 0,5 l'."""
        discounts = [_make_discount("Pivo světlé 0,5 l")]
        result = match_discounts(discounts, ["pivo"])
        assert len(result) == 1

    def test_no_match(self):
        discounts = [_make_discount("Mléko"), _make_discount("Chleba")]
        result = match_discounts(discounts, ["rum"])
        assert result == []

    def test_multiple_keywords(self):
        discounts = [
            _make_discount("Rum Jamaica"),
            _make_discount("Becherovka"),
            _make_discount("Mléko"),
        ]
        result = match_discounts(discounts, ["rum", "becherovka"])
        assert len(result) == 2

    def test_each_discount_returned_once(self):
        """A discount matching multiple keywords appears only once."""
        discounts = [_make_discount("Rum Becherovka Special")]
        result = match_discounts(discounts, ["rum", "becherovka"])
        assert len(result) == 1

    def test_empty_keywords_returns_empty(self):
        discounts = [_make_discount("Rum")]
        assert match_discounts(discounts, []) == []

    def test_empty_discounts_returns_empty(self):
        assert match_discounts([], ["rum"]) == []

    def test_preserves_order(self):
        discounts = [
            _make_discount("Víno červené"),
            _make_discount("Pivo"),
            _make_discount("Rum"),
        ]
        result = match_discounts(discounts, ["vino", "pivo", "rum"])
        assert [d.name for d in result] == ["Víno červené", "Pivo", "Rum"]

    def test_none_name_does_not_crash(self):
        """Discounts with empty name string should be handled gracefully."""
        d = _make_discount("")
        result = match_discounts([d], ["rum"])
        assert result == []
