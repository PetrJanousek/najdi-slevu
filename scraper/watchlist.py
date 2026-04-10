"""watchlist.py — load user-defined keyword watchlist from YAML.

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

from pathlib import Path

import yaml


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
