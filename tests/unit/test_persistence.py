"""Unit tests for scraper.persistence.persist_matches."""
import json
from datetime import date
from pathlib import Path

from scraper.models import Discount
from scraper.persistence import persist_matches, _find_matched_keyword


def _make_discount(name: str, price: float = 19.90) -> Discount:
    return Discount(
        name=name,
        original_price=29.90,
        discounted_price=price,
        discount_pct=33.4,
        valid_from=date(2026, 4, 7),
        valid_to=date(2026, 4, 13),
        raw_text=name,
    )


class TestPersistMatches:
    def test_creates_jsonl_file(self, tmp_path):
        out = tmp_path / "data" / "hot_deals.jsonl"
        discounts = [_make_discount("Rum Jamaica")]
        persist_matches(discounts, ["rum"], output_path=out)
        assert out.exists()

    def test_creates_parent_directories(self, tmp_path):
        out = tmp_path / "deep" / "nested" / "hot_deals.jsonl"
        persist_matches([_make_discount("Rum")], ["rum"], output_path=out)
        assert out.exists()

    def test_one_line_per_discount(self, tmp_path):
        out = tmp_path / "out.jsonl"
        discounts = [_make_discount("Rum"), _make_discount("Becherovka")]
        persist_matches(discounts, ["rum", "becherovka"], output_path=out)
        lines = out.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

    def test_appends_on_second_call(self, tmp_path):
        out = tmp_path / "out.jsonl"
        persist_matches([_make_discount("Rum")], ["rum"], output_path=out)
        persist_matches([_make_discount("Pivo")], ["pivo"], output_path=out)
        lines = out.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

    def test_record_schema(self, tmp_path):
        out = tmp_path / "out.jsonl"
        d = _make_discount("Rum Jamaica")
        persist_matches([d], ["rum"], supermarket="lidl", output_path=out)
        record = json.loads(out.read_text(encoding="utf-8").strip())
        assert "timestamp" in record
        assert record["supermarket"] == "lidl"
        assert record["name"] == "Rum Jamaica"
        assert record["discounted_price"] == 19.90
        assert record["original_price"] == 29.90
        assert record["valid_from"] == "2026-04-07"
        assert record["valid_to"] == "2026-04-13"
        assert record["matched_keyword"] == "rum"

    def test_no_output_for_empty_discounts(self, tmp_path):
        out = tmp_path / "out.jsonl"
        persist_matches([], ["rum"], output_path=out)
        assert not out.exists()

    def test_supermarket_none_allowed(self, tmp_path):
        out = tmp_path / "out.jsonl"
        persist_matches([_make_discount("Rum")], ["rum"], output_path=out)
        record = json.loads(out.read_text(encoding="utf-8").strip())
        assert record["supermarket"] is None

    def test_valid_dates_none_allowed(self, tmp_path):
        out = tmp_path / "out.jsonl"
        d = Discount(
            name="Rum",
            original_price=None,
            discounted_price=29.90,
            discount_pct=None,
            valid_from=None,
            valid_to=None,
            raw_text="Rum",
        )
        persist_matches([d], ["rum"], output_path=out)
        record = json.loads(out.read_text(encoding="utf-8").strip())
        assert record["valid_from"] is None
        assert record["valid_to"] is None


class TestFindMatchedKeyword:
    def test_finds_match(self):
        d = _make_discount("Rum Jamaica")
        assert _find_matched_keyword(d, ["rum", "pivo"]) == "rum"

    def test_returns_none_when_no_match(self):
        d = _make_discount("Mléko")
        assert _find_matched_keyword(d, ["rum"]) is None

    def test_diacritic_insensitive(self):
        d = _make_discount("Káva mletá")
        assert _find_matched_keyword(d, ["kava"]) == "kava"
