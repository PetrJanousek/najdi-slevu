"""Sanity tests for the Discount model."""
from scraper.models import Discount


def test_discount_import():
    """Discount can be imported and instantiated."""
    d = Discount(
        name="Mléko",
        original_price=25.90,
        discounted_price=19.90,
        discount_pct=23.2,
        valid_from=None,
        valid_to=None,
        raw_text="Mléko 25.90 -> 19.90",
    )
    assert d.name == "Mléko"
    assert d.discounted_price == 19.90
