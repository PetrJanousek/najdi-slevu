#!/usr/bin/env python3
"""Dump parser output for a supermarket's PDF fixtures to stdout as JSON.

Usage:
    python scripts/dump_parser_output.py <supermarket>

Example:
    python scripts/dump_parser_output.py tesco

The output can be redirected to tests/fixtures/expected/<supermarket>.json and
then hand-curated to create a golden file for baseline parser tests.
"""
import json
import sys
from pathlib import Path

# Allow running from repo root without install
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper.pdf_parser import parse_pdf

FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "leaflets"


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <supermarket>", file=sys.stderr)
        sys.exit(1)

    supermarket = sys.argv[1].lower()
    leaflet_dir = FIXTURES_DIR / supermarket

    if not leaflet_dir.is_dir():
        print(f"No fixture directory: {leaflet_dir}", file=sys.stderr)
        sys.exit(1)

    pdfs = sorted(leaflet_dir.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {leaflet_dir}", file=sys.stderr)
        sys.exit(1)

    all_discounts = []
    for pdf_path in pdfs:
        discounts = parse_pdf(pdf_path)
        for d in discounts:
            all_discounts.append({
                "name": d.name,
                "original_price": d.original_price,
                "discounted_price": d.discounted_price,
                "discount_pct": d.discount_pct,
                "valid_from": d.valid_from.isoformat() if d.valid_from else None,
                "valid_to": d.valid_to.isoformat() if d.valid_to else None,
            })

    print(json.dumps(all_discounts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
