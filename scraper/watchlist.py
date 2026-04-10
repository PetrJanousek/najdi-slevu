"""watchlist.py — load user-defined keyword watchlist from YAML and match discounts.

The watchlist.yaml file at repo root contains a flat list of keywords.
Keywords are lowercased, stripped, and de-duplicated. Blank lines and
comment lines are ignored.

Example watchlist.yaml:
    - rum
    - Becherovka
    - slivovice
    - whisky

Personal watchlist.yaml files are gitignored. Commit only watchlist.example.yaml.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from scraper.models import Discount


def _strip_diacritics(text: str) -> str:
    """Return *text* with accents/diacritics removed (NFD decomposition).

    Examples:
        "káva" → "kava"
        "Becherovka" → "Becherovka"  (unchanged — no diacritics)
    """
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


def load_watchlist(path: str | Path = "watchlist.yaml") -> list[str]:
    """Load and normalize keywords from a YAML watchlist file.

    Parameters
    ----------
    path:
        Path to the YAML file. Defaults to ``watchlist.yaml`` in the current
        directory.

    Returns
    -------
    list[str]
        Sorted, deduplicated list of lowercased keyword strings. Returns an
        empty list if the file does not exist or contains no valid keywords.

    Raises
    ------
    yaml.YAMLError
        If the file exists but cannot be parsed as YAML.
    TypeError
        If the YAML root is not a list.
    """
    path = Path(path)
    if not path.exists():
        return []

    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        return []

    if not isinstance(data, list):
        raise TypeError(
            f"watchlist.yaml must contain a YAML list, got {type(data).__name__}"
        )

    keywords: list[str] = []
    for item in data:
        if item is None:
            continue
        keyword = str(item).strip().lower()
        if keyword:
            keywords.append(keyword)

    # Deduplicate while preserving first occurrence order
    seen: set[str] = set()
    unique: list[str] = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)

    return sorted(unique)


def match_discounts(
    discounts: list["Discount"],
    keywords: list[str],
) -> list["Discount"]:
    """Return discounts whose name contains at least one of *keywords*.

    Matching is:
    - Case-insensitive
    - Diacritic-insensitive: both the keyword and the discount name are
      stripped of accents before comparison. This allows a keyword like
      "kava" to match "Káva" and vice-versa.

    Parameters
    ----------
    discounts:
        List of Discount objects to filter.
    keywords:
        List of lowercase keyword strings (as returned by load_watchlist).

    Returns
    -------
    list[Discount]
        Discounts matching at least one keyword, in original order.
    """
    if not keywords:
        return []

    # Pre-compute stripped lowercase versions of the keywords once
    normalised_keywords = [_strip_diacritics(kw).lower() for kw in keywords]

    matched: list[Discount] = []
    for discount in discounts:
        name_lower = discount.name.lower() if discount.name else ""
        name_stripped = _strip_diacritics(name_lower)
        for kw_stripped in normalised_keywords:
            if kw_stripped in name_stripped:
                matched.append(discount)
                break  # No need to check further keywords for this discount

    return matched
