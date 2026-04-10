"""persistence.py — persist watchlist matches to a JSONL log file."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from scraper.models import Discount

DEFAULT_JSONL_PATH = Path("data/hot_deals.jsonl")


def persist_matches(
    discounts: list[Discount],
    keywords: list[str],
    *,
    supermarket: Optional[str] = None,
    output_path: Path = DEFAULT_JSONL_PATH,
) -> None:
    """Append one JSON line per matched discount to *output_path*.

    Creates ``data/`` (or any parent directory) if it does not exist.

    Parameters
    ----------
    discounts:
        Discount objects that matched watchlist keywords (already filtered).
    keywords:
        The full keyword list; used to record which keyword triggered the match.
    supermarket:
        Optional supermarket name inferred from the PDF filename.
    output_path:
        Path to the JSONL output file.  Defaults to ``data/hot_deals.jsonl``.
    """
    if not discounts:
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(tz=timezone.utc).isoformat()

    with output_path.open("a", encoding="utf-8") as f:
        for discount in discounts:
            matched_keyword = _find_matched_keyword(discount, keywords)
            record = {
                "timestamp": timestamp,
                "supermarket": supermarket,
                "name": discount.name,
                "discounted_price": discount.discounted_price,
                "original_price": discount.original_price,
                "valid_from": discount.valid_from.isoformat() if discount.valid_from else None,
                "valid_to": discount.valid_to.isoformat() if discount.valid_to else None,
                "matched_keyword": matched_keyword,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _find_matched_keyword(discount: Discount, keywords: list[str]) -> Optional[str]:
    """Return the first keyword that matches *discount.name*, or None."""
    import unicodedata

    def strip(text: str) -> str:
        return "".join(
            c
            for c in unicodedata.normalize("NFD", text.lower())
            if unicodedata.category(c) != "Mn"
        )

    name_stripped = strip(discount.name or "")
    for kw in keywords:
        if strip(kw) in name_stripped:
            return kw
    return None
