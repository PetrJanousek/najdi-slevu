"""Baseline parser tests for Lidl leaflet PDFs.

These tests require:
1. A Lidl PDF fixture at tests/fixtures/leaflets/lidl/<yyyy-mm-dd>.pdf
2. A hand-curated golden file at tests/fixtures/expected/lidl.json

Both are absent by default (PDFs are copyrighted and excluded from git).
Tests skip gracefully when either is missing.

To generate the golden draft once you have a PDF:
    python scripts/dump_parser_output.py lidl > tests/fixtures/expected/lidl.json
Then hand-curate lidl.json and re-run pytest.

## Lidl-specific notes

Lidl leaflets use a period-separated decimal format without a Kč suffix:
    "34.90"  →  34.90 CZK
This is handled by the `_PRICE_STANDALONE_DECIMAL` pattern in pdf_parser.py.
If recall is lower than expected, check whether date/price extraction is
confused by the mixed format; escalate as architectural issue if needed.
"""
import json
import math
from pathlib import Path

import pytest

from scraper.pdf_parser import parse_pdf

EXPECTED_DIR = Path(__file__).parent.parent / "fixtures" / "expected"
MIN_DISCOUNTS = 10


def _load_golden(supermarket: str):
    path = EXPECTED_DIR / f"{supermarket}.json"
    if not path.exists():
        pytest.skip(f"Golden file not found: {path}")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def test_lidl_parser_returns_enough_discounts(sample_pdf):
    """Parser extracts at least MIN_DISCOUNTS items from a Lidl leaflet."""
    pdf_path = sample_pdf("lidl")
    discounts = parse_pdf(pdf_path)
    assert len(discounts) >= MIN_DISCOUNTS, (
        f"Expected ≥{MIN_DISCOUNTS} discounts, got {len(discounts)}"
    )


def test_lidl_parser_no_impossible_rows(sample_pdf):
    """All discounts have positive prices and sane discount percentages."""
    pdf_path = sample_pdf("lidl")
    discounts = parse_pdf(pdf_path)
    for d in discounts:
        assert d.discounted_price > 0, f"Non-positive price: {d}"
        if d.original_price is not None:
            assert d.original_price >= d.discounted_price, (
                f"Original price < discounted price: {d}"
            )
        if d.discount_pct is not None:
            assert 0 < d.discount_pct < 100, f"Impossible discount %: {d}"


def test_lidl_parser_dates_plausible(sample_pdf):
    """Date ranges, when present, span 1–21 days (typical leaflet window)."""
    pdf_path = sample_pdf("lidl")
    discounts = parse_pdf(pdf_path)
    for d in discounts:
        if d.valid_from and d.valid_to:
            span = (d.valid_to - d.valid_from).days
            assert 0 <= span <= 21, f"Implausible date span {span} days: {d}"


def test_lidl_parser_golden_recall(sample_pdf):
    """≥90% of hand-curated golden items are found in parser output.

    Note: Lidl uses period-decimal prices without Kč. If recall falls below
    90%, check whether _PRICE_STANDALONE_DECIMAL in pdf_parser.py is matching
    correctly and consider filing an architectural issue.
    """
    pdf_path = sample_pdf("lidl")
    golden = _load_golden("lidl")

    discounts = parse_pdf(pdf_path)

    matched = 0
    missing = []
    for item in golden:
        name_fragment = item["name_contains"].lower()
        expected_price = item["discounted_price"]
        found = any(
            name_fragment in d.name.lower()
            and math.isclose(d.discounted_price, expected_price, abs_tol=0.02)
            for d in discounts
        )
        if found:
            matched += 1
        else:
            missing.append(item)

    recall = matched / len(golden) if golden else 1.0
    assert recall >= 0.90, (
        f"Recall {recall:.0%} below 90%. Missing items:\n"
        + "\n".join(f"  {m}" for m in missing)
        + "\n\nNote: Lidl uses '34.90'-style prices (no Kč). "
        "If many items are missing, check _PRICE_STANDALONE_DECIMAL in pdf_parser.py."
    )
