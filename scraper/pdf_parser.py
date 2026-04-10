"""pdf_parser.py — extract Discount objects from Czech supermarket leaflet PDFs.

Uses pdfplumber to read text and regex patterns to identify:
- Czech date ranges (valid_from / valid_to)
- Czech price formats (original_price / discounted_price)
- Item names via proximity heuristics
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Optional

import pdfplumber

from scraper.models import Discount


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Czech date range patterns, all produce named groups: d1, m1, d2, m2
# "platí od 3.4. do 9.4." or "platí od 03.04. do 09.04."
_DATE_OD_DO = re.compile(
    r"plat[íi]\s+od\s+(?P<d1>\d{1,2})\.(?P<m1>\d{1,2})\.\s*do\s+(?P<d2>\d{1,2})\.(?P<m2>\d{1,2})\.",
    re.IGNORECASE,
)

# "3.4.–9.4." or "03.04. – 09.04." (en-dash, em-dash, hyphen-minus)
_DATE_DASH = re.compile(
    r"(?P<d1>\d{1,2})\.(?P<m1>\d{1,2})\.\s*[–—\-]\s*(?P<d2>\d{1,2})\.(?P<m2>\d{1,2})\.",
)

# "3.4. - 9.4." (space-hyphen-space variant — covered by _DATE_DASH above,
# but also handles "DD.MM. - DD.MM." with trailing dot-space)
_DATE_SPACE_DASH = re.compile(
    r"(?P<d1>\d{1,2})\.(?P<m1>\d{1,2})\s*-\s*(?P<d2>\d{1,2})\.(?P<m2>\d{1,2})",
)

_DATE_PATTERNS = [_DATE_OD_DO, _DATE_DASH, _DATE_SPACE_DASH]

# Price patterns — each must produce a named group `price` (and optionally `cents`)
# "29,90 Kč" or "29,90 Kč"
_PRICE_DECIMAL = re.compile(
    r"(?P<euros>\d[\d\s]*)[\.,](?P<cents>\d{2})\s*Kč",
    re.IGNORECASE,
)

# "29.- Kč" or "29.-Kč" or "29,-" or "29, -" (whole number with dash/comma-dash)
_PRICE_WHOLE_DASH = re.compile(
    r"(?P<euros>\d[\d\s]*)[,\.]\s*[-–]\s*(?:Kč)?",
    re.IGNORECASE,
)

# "29 Kč" (plain integer, no cents marker) — lower priority
# Negative lookbehind prevents matching "15 Kč" from inside "427,15 Kč"
_PRICE_INTEGER = re.compile(
    r"(?<![,.\d])(?P<euros>\d[\d\s]*)\s+Kč",
    re.IGNORECASE,
)

# Lidl-style standalone decimal: "34.90" or "19.90" — no Kč suffix, period separator
# Only matches when not part of a larger number or date (1-4 integer digits, exactly 2 decimals)
_PRICE_STANDALONE_DECIMAL = re.compile(
    r"(?<![.\d])(?P<euros>\d{1,4})\.(?P<cents>\d{2})(?!\d)",
)

# Lines that are unit prices (per kg/l/100g) — used to skip these as primary prices
_UNIT_PRICE_RE = re.compile(
    r"\b(1\s*kg|1\s*l|100\s*g|1\s*ks)\s*=",
    re.IGNORECASE,
)

# Lines that look like headers/footers and should be excluded from name candidates
_HEADER_FOOTER_RE = re.compile(
    r"(strana|page|tel\.?|www\.|http|e-mail|otevírací|provozní|adresa"
    r"|platnost|platí|akce|nabídka|leták|tesco|albert|billa|penny|lidl"
    r"|kaufland|globus|interspar|spar|\d{3}\s?\d{3}\s?\d{3}"
    r"|běžná cena|bez aplikace|s aplikací|aplikace|cena za 100|1 kg =|100 g ="
    r"|ušetřete|super cena|s lidl plus|nabídka|více na www)",
    re.IGNORECASE,
)

# Lines that are too short or contain only numbers/punctuation (likely not names)
_NOISE_LINE_RE = re.compile(r"^[\d\s\.\,\-\%\+\/\(\)\*•]+$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_price(text: str) -> Optional[float]:
    """Return the first price found in *text*, or None.

    Unit-price lines (e.g. "1 kg = 69,80 Kč") are skipped — they describe
    a normalised unit cost, not the shelf price of the item.
    """
    if _UNIT_PRICE_RE.search(text):
        return None

    # Try decimal with Kč first (most specific)
    m = _PRICE_DECIMAL.search(text)
    if m:
        euros = m.group("euros").replace(" ", "").replace("\xa0", "")
        cents = m.group("cents")
        try:
            return float(f"{euros}.{cents}")
        except ValueError:
            pass

    # Whole-number with dash (e.g. "29.-")
    m = _PRICE_WHOLE_DASH.search(text)
    if m:
        euros = m.group("euros").replace(" ", "").replace("\xa0", "")
        try:
            return float(euros)
        except ValueError:
            pass

    # Plain integer with Kč
    m = _PRICE_INTEGER.search(text)
    if m:
        euros = m.group("euros").replace(" ", "").replace("\xa0", "")
        try:
            return float(euros)
        except ValueError:
            pass

    # Standalone decimal without Kč suffix (e.g. Lidl "34.90")
    m = _PRICE_STANDALONE_DECIMAL.search(text)
    if m:
        try:
            return float(f"{m.group('euros')}.{m.group('cents')}")
        except ValueError:
            pass

    return None


def _parse_date_range(text: str, year: int) -> tuple[Optional[date], Optional[date]]:
    """Return (valid_from, valid_to) extracted from *text*, or (None, None)."""
    for pat in _DATE_PATTERNS:
        m = pat.search(text)
        if m:
            try:
                d = m.groupdict()
                valid_from = date(year, int(d["m1"]), int(d["d1"]))
                valid_to = date(year, int(d["m2"]), int(d["d2"]))
                # Handle year wrap-around (e.g. Dec → Jan)
                if valid_to < valid_from:
                    valid_to = valid_to.replace(year=year + 1)
                return valid_from, valid_to
            except (ValueError, KeyError):
                continue
    return None, None


def _is_name_candidate(line: str) -> bool:
    """Return True if *line* looks like a product name."""
    stripped = line.strip()
    if len(stripped) < 3 or len(stripped) > 120:
        return False
    if _NOISE_LINE_RE.match(stripped):
        return False
    if _HEADER_FOOTER_RE.search(stripped):
        return False
    # Bullet lines are product details (weight, volume, origin), not names
    if stripped.startswith("•"):
        return False
    # Lines starting with a volume/quantity number like "0,7 l," or "500 g,"
    if re.match(r"^\d+[,\.]", stripped):
        return False
    # Lines ending with "/" are price fragments like "569,- bez Aplikace /"
    if stripped.endswith("/"):
        return False
    # Lines ending with "," are product detail lines (description, multi-column)
    if stripped.endswith(","):
        return False
    # Unit price lines like "1 l = 428,43 Kč" are not names
    if _UNIT_PRICE_RE.search(stripped):
        return False
    # Must contain at least one letter
    if not re.search(r"[A-Za-zÀ-žÁ-ž\u00C0-\u017E]", stripped):
        return False
    # Lines that contain a price are not names
    if _parse_price(stripped) is not None:
        return False
    return True


def _extract_name_near_price(lines: list[str], price_line_idx: int) -> str:
    """Return the best name candidate scanning backward then forward from *price_line_idx*.

    Product names in Czech leaflets typically appear above the price block,
    sometimes several lines up (after detail bullets and 'BĚŽNÁ CENA' markers).
    Scan back up to 8 lines first, then fall back to 2 lines forward.
    """
    # Prefer scanning backward — names appear above prices
    for offset in range(1, 9):
        idx = price_line_idx - offset
        if idx < 0:
            break
        candidate = lines[idx].strip()
        if _is_name_candidate(candidate):
            # Check if the line directly above is also a name part (e.g. "BOŽKOV" / "Kávový")
            prev_idx = idx - 1
            if prev_idx >= 0:
                prev = lines[prev_idx].strip()
                if _is_name_candidate(prev):
                    return f"{prev} {candidate}"
            return candidate
    # Fall back: check lines below
    for offset in (1, 2):
        idx = price_line_idx + offset
        if 0 <= idx < len(lines):
            candidate = lines[idx].strip()
            if _is_name_candidate(candidate):
                return candidate
    # Last resort: truncated price line
    return lines[price_line_idx].strip()[:80]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_pdf(path: str | Path) -> list[Discount]:
    """Parse a Czech supermarket leaflet PDF and return a list of Discount objects.

    Parameters
    ----------
    path:
        Filesystem path to the PDF file.

    Returns
    -------
    list[Discount]
        One entry per detected discounted price. Fields that cannot be parsed
        are set to None.
    """
    path = Path(path)
    results: list[Discount] = []

    with pdfplumber.open(path) as pdf:
        # Determine the reference year from PDF metadata or fall back to today
        meta = pdf.metadata or {}
        ref_year: int = _year_from_meta(meta)

        # Gather columns per page: each column is treated as independent text
        # page_cols: list of (full_page_text, list_of_(col_text, col_lines))
        page_cols: list[tuple[str, list[tuple[str, list[str]]]]] = []
        for page in pdf.pages:
            full_text = page.extract_text() or ""
            col_texts = _split_page_into_columns(page)
            cols: list[tuple[str, list[str]]] = []
            for ct in col_texts:
                lines = _join_split_prices(ct.splitlines())
                cols.append(("\n".join(lines), lines))
            page_cols.append((full_text, cols))

        # Extract global date range from full document text
        all_full_text = "\n".join(ft for ft, _ in page_cols)
        global_from, global_to = _parse_date_range(all_full_text, ref_year)

        for full_page_text, cols in page_cols:
            # Try to find a page-level date override from the raw page text
            page_from, page_to = _parse_date_range(full_page_text, ref_year)
            effective_from = page_from or global_from
            effective_to = page_to or global_to

            # Process each column independently — deduplicate per page (not per column)
            seen_names: set[str] = set()
            for _col_text, lines in cols:
                for i, line in enumerate(lines):
                    price = _parse_price(line)
                    if price is None:
                        continue

                    name = _extract_name_near_price(lines, i)
                    key = (name, price)
                    if key in seen_names:
                        continue
                    seen_names.add(key)  # type: ignore[arg-type]

                    original_price: Optional[float] = None
                    context = "\n".join(lines[max(0, i - 2) : i + 3])  # noqa: E203
                    prices_in_context = _find_all_prices(context)
                    if len(prices_in_context) >= 2:
                        prices_in_context.sort()
                        discounted_price = prices_in_context[0]
                        original_price = prices_in_context[-1]
                        discount_pct = _compute_pct(original_price, discounted_price)
                    else:
                        discounted_price = price
                        discount_pct = None

                    results.append(
                        Discount(
                            name=name,
                            original_price=original_price,
                            discounted_price=discounted_price,
                            discount_pct=discount_pct,
                            valid_from=effective_from,
                            valid_to=effective_to,
                            raw_text=context.strip(),
                        )
                    )

    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _split_page_into_columns(page, intra_gap: float = 40.0) -> list[str]:
    """Split a page into text columns using per-line x-gap voting.

    Algorithm:
    1. Group words into text rows by y-coordinate.
    2. Within each row, find clusters of consecutive words separated by a gap
       wider than *intra_gap* points — each cluster boundary is a potential
       column boundary.
    3. Vote: column boundaries that appear in at least 10% of rows (or ≥2 rows)
       are considered real columns.
    4. Assign every word to its column and reconstruct per-column text.

    Falls back to a single plain-text extraction if fewer than 2 columns found.
    """
    words = page.extract_words(keep_blank_chars=False)
    if not words:
        return [page.extract_text() or ""]

    page_width = float(page.width)
    Y_TOL = 3.0

    # Step 1: group words into rows
    rows: list[list[dict]] = []
    for w in sorted(words, key=lambda x: x["top"]):
        placed = False
        for row in rows:
            if abs(row[0]["top"] - w["top"]) <= Y_TOL:
                row.append(w)
                placed = True
                break
        if not placed:
            rows.append([w])

    # Step 2: collect column-start votes from each row
    votes: list[float] = []
    for row in rows:
        row.sort(key=lambda w: w["x0"])
        cluster_start = row[0]["x0"]
        votes.append(cluster_start)
        for i in range(1, len(row)):
            gap = row[i]["x0"] - row[i - 1]["x1"]
            if gap > intra_gap:
                cluster_start = row[i]["x0"]
                votes.append(cluster_start)

    # Step 3: cluster votes → significant column starts
    votes.sort()
    CLUSTER_TOL = 20.0
    clusters: list[list[float]] = []
    for x in votes:
        if clusters and abs(x - clusters[-1][-1]) <= CLUSTER_TOL:
            clusters[-1].append(x)
        else:
            clusters.append([x])

    min_support = max(2, len(rows) * 0.10)
    # Use the minimum x in each cluster so that the leftmost word of a column
    # is reliably included (mean can drift right of the true column edge).
    col_starts = sorted(
        min(c)
        for c in clusters
        if len(c) >= min_support
    )

    if len(col_starts) < 2:
        return [page.extract_text() or ""]

    # Step 4: assign words to columns and reconstruct text
    col_ends = col_starts[1:] + [page_width]
    MARGIN = 10.0
    columns: list[list[dict]] = [[] for _ in col_starts]
    for word in words:
        for idx, (start, end) in enumerate(zip(col_starts, col_ends)):
            if word["x0"] >= start - MARGIN and word["x0"] < end:
                columns[idx].append(word)
                break

    result: list[str] = []
    for col_words in columns:
        if not col_words:
            continue
        col_words.sort(key=lambda w: (w["top"], w["x0"]))
        lines: list[str] = []
        cur_words: list[str] = []
        cur_y: float | None = None
        for w in col_words:
            y = w["top"]
            if cur_y is None or abs(y - cur_y) <= Y_TOL:
                cur_words.append(w["text"])
                cur_y = y if cur_y is None else (cur_y + y) / 2
            else:
                lines.append(" ".join(cur_words))
                cur_words = [w["text"]]
                cur_y = y
        if cur_words:
            lines.append(" ".join(cur_words))
        result.append("\n".join(lines))

    return result


def _join_split_prices(lines: list[str]) -> list[str]:
    """Fix prices split across lines due to mixed font sizes in the PDF.

    Handles two cases where '269,-' gets split:
    1. Line ends with '269,' and the next line is just '-'
       e.g. ['some text 269,', '-'] → ['some text 269,-']
    2. Line starts with '269,' followed by other-column content, next line is '-'
       e.g. ['269, • 299 Kč', '-'] → ['269,- • 299 Kč']
    """
    _TRAILING_COMMA = re.compile(r"\d+,\s*$")
    _LEADING_COMMA = re.compile(r"^(\d+,)(\s)")
    result: list[str] = []
    skip_next = False
    for i, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue
        next_is_dash = i + 1 < len(lines) and lines[i + 1].strip() == "-"
        if next_is_dash:
            if _TRAILING_COMMA.search(line):
                result.append(line.rstrip() + "-")
                skip_next = True
                continue
            if _LEADING_COMMA.match(line.strip()):
                result.append(_LEADING_COMMA.sub(r"\1-\2", line, count=1))
                skip_next = True
                continue
        result.append(line)
    return result


def _year_from_meta(meta: dict) -> int:
    """Try to extract a year from PDF metadata; fall back to current year."""
    import datetime

    for key in ("CreationDate", "ModDate"):
        val = meta.get(key, "")
        if val:
            # PDF date format: "D:YYYYMMDDHHmmSS..."
            m = re.search(r"D:(\d{4})", str(val))
            if m:
                return int(m.group(1))
    return datetime.date.today().year


def _find_all_prices(text: str) -> list[float]:
    """Return all price values found in *text*, skipping unit-price lines."""
    # Filter out unit-price lines before searching
    filtered = "\n".join(
        line for line in text.splitlines() if not _UNIT_PRICE_RE.search(line)
    )
    found: list[float] = []
    # Decimal prices with Kč
    for m in _PRICE_DECIMAL.finditer(filtered):
        euros = m.group("euros").replace(" ", "").replace("\xa0", "")
        cents = m.group("cents")
        try:
            found.append(float(f"{euros}.{cents}"))
        except ValueError:
            pass
    # Whole-number dash prices
    for m in _PRICE_WHOLE_DASH.finditer(filtered):
        euros = m.group("euros").replace(" ", "").replace("\xa0", "")
        try:
            val = float(euros)
            if val not in found:
                found.append(val)
        except ValueError:
            pass
    # Integer Kč prices
    for m in _PRICE_INTEGER.finditer(filtered):
        euros = m.group("euros").replace(" ", "").replace("\xa0", "")
        try:
            val = float(euros)
            if val not in found:
                found.append(val)
        except ValueError:
            pass
    # Standalone decimal prices (Lidl-style, no Kč)
    for m in _PRICE_STANDALONE_DECIMAL.finditer(filtered):
        try:
            val = float(f"{m.group('euros')}.{m.group('cents')}")
            if val not in found:
                found.append(val)
        except ValueError:
            pass
    return found


def _compute_pct(original: float, discounted: float) -> Optional[float]:
    """Return discount percentage rounded to one decimal, or None."""
    if original <= 0 or discounted >= original:
        return None
    return round((1 - discounted / original) * 100, 1)
