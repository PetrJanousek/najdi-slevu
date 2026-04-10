"""Baseline parser tests for Tesco leaflet PDFs.

These tests require:
1. A Tesco PDF fixture at tests/fixtures/leaflets/tesco/<yyyy-mm-dd>.pdf
2. A hand-curated golden file at tests/fixtures/expected/tesco.json

Both are absent by default (PDFs are copyrighted and excluded from git).
Tests skip gracefully when either is missing.

To generate the golden draft once you have a PDF:
    python scripts/dump_parser_output.py tesco > tests/fixtures/expected/tesco.json
Then hand-curate tesco.json and re-run pytest.
"""
import json
import math
from pathlib import Path

import pytest

from scraper.pdf_parser import parse_pdf

EXPECTED_DIR = Path(__file__).parent.parent / "fixtures" / "expected"
MIN_DISCOUNTS = 10  # Minimum expected number of discounts in a full leaflet


def _load_golden(supermarket: str):
    path = EXPECTED_DIR / f"{supermarket}.json"
    if not path.exists():
        pytest.skip(f"Golden file not found: {path}")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def test_tesco_parser_returns_enough_discounts(sample_pdf):
    """Parser extracts at least MIN_DISCOUNTS items from a Tesco leaflet."""
    pdf_path = sample_pdf("tesco")
    discounts = parse_pdf(pdf_path)
    assert len(discounts) >= MIN_DISCOUNTS, (
        f"Expected ≥{MIN_DISCOUNTS} discounts, got {len(discounts)}"
    )


def test_tesco_parser_no_impossible_rows(sample_pdf):
    """All discounts have positive prices and sane discount percentages."""
    pdf_path = sample_pdf("tesco")
    discounts = parse_pdf(pdf_path)
    for d in discounts:
        assert d.discounted_price > 0, f"Non-positive price: {d}"
        if d.original_price is not None:
            assert d.original_price >= d.discounted_price, (
                f"Original price < discounted price: {d}"
            )
        if d.discount_pct is not None:
            assert 0 < d.discount_pct < 100, f"Impossible discount %: {d}"


def test_tesco_parser_dates_plausible(sample_pdf):
    """Date ranges, when present, span 1–21 days (typical leaflet window)."""
    from datetime import timedelta

    pdf_path = sample_pdf("tesco")
    discounts = parse_pdf(pdf_path)
    for d in discounts:
        if d.valid_from and d.valid_to:
            span = (d.valid_to - d.valid_from).days
            assert 0 <= span <= 21, f"Implausible date span {span} days: {d}"


def test_tesco_parser_golden_recall(sample_pdf):
    """≥90% of hand-curated golden items are found in parser output."""
    pdf_path = sample_pdf("tesco")
    golden = _load_golden("tesco")

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
    )
