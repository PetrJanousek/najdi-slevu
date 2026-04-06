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

# "29.- Kč" or "29.-Kč" or "29,-" (whole number with dash/comma-dash)
_PRICE_WHOLE_DASH = re.compile(
    r"(?P<euros>\d[\d\s]*)[,\.][-–]\s*(?:Kč)?",
    re.IGNORECASE,
)

# "29 Kč" (plain integer, no cents marker) — lower priority
_PRICE_INTEGER = re.compile(
    r"(?P<euros>\d[\d\s]*)\s+Kč",
    re.IGNORECASE,
)

# Lines that look like headers/footers and should be excluded from name candidates
_HEADER_FOOTER_RE = re.compile(
    r"(strana|page|tel\.?|www\.|http|e-mail|otevírací|provozní|adresa"
    r"|platnost|platí|akce|nabídka|leták|tesco|albert|billa|penny|lidl"
    r"|kaufland|globus|interspar|spar|\d{3}\s?\d{3}\s?\d{3})",
    re.IGNORECASE,
)

# Lines that are too short or contain only numbers/punctuation (likely not names)
_NOISE_LINE_RE = re.compile(r"^[\d\s\.\,\-\%\+\/\(\)\*]+$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_price(text: str) -> Optional[float]:
    """Return the first price found in *text*, or None."""
    # Try decimal first (most specific)
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
    # Must contain at least one letter
    if not re.search(r"[A-Za-zÀ-žÁ-ž\u00C0-\u017E]", stripped):
        return False
    return True


def _extract_name_near_price(lines: list[str], price_line_idx: int) -> str:
    """Return the best name candidate from lines adjacent to *price_line_idx*."""
    candidates: list[str] = []
    for offset in (-1, -2, 1, 2):
        idx = price_line_idx + offset
        if 0 <= idx < len(lines):
            candidate = lines[idx].strip()
            if _is_name_candidate(candidate):
                candidates.append(candidate)
    if candidates:
        # Prefer lines above the price (offset -1, -2) which is the common layout
        return candidates[0]
    # Fall back: return a truncated version of the price line itself
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

        # Gather all text as (page_text, lines) pairs
        all_pages: list[tuple[str, list[str]]] = []
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines = text.splitlines()
            all_pages.append((text, lines))

        # Extract global date range from full document text (often on page 1)
        full_text = "\n".join(pt for pt, _ in all_pages)
        global_from, global_to = _parse_date_range(full_text, ref_year)

        for page_text, lines in all_pages:
            # Try to find a page-level date override
            page_from, page_to = _parse_date_range(page_text, ref_year)
            effective_from = page_from or global_from
            effective_to = page_to or global_to

            # Find all price occurrences and build Discount objects
            seen_names: set[str] = set()
            for i, line in enumerate(lines):
                price = _parse_price(line)
                if price is None:
                    continue

                name = _extract_name_near_price(lines, i)
                # Deduplicate within page to avoid repeated header prices etc.
                key = (name, price)
                if key in seen_names:
                    continue
                seen_names.add(key)  # type: ignore[arg-type]

                # Attempt to find a second price on the same or adjacent lines
                # (original vs. discounted price)
                original_price: Optional[float] = None
                context = "\n".join(
                    lines[max(0, i - 2) : i + 3]  # noqa: E203
                )
                prices_in_context = _find_all_prices(context)
                if len(prices_in_context) >= 2:
                    # Convention: higher price is original, lower is discounted
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
    """Return all price values found in *text*."""
    found: list[float] = []
    # Decimal prices
    for m in _PRICE_DECIMAL.finditer(text):
        euros = m.group("euros").replace(" ", "").replace("\xa0", "")
        cents = m.group("cents")
        try:
            found.append(float(f"{euros}.{cents}"))
        except ValueError:
            pass
    # Whole-number dash prices (only if no decimal already found for same spot)
    for m in _PRICE_WHOLE_DASH.finditer(text):
        euros = m.group("euros").replace(" ", "").replace("\xa0", "")
        try:
            val = float(euros)
            if val not in found:
                found.append(val)
        except ValueError:
            pass
    # Integer Kč prices
    for m in _PRICE_INTEGER.finditer(text):
        euros = m.group("euros").replace(" ", "").replace("\xa0", "")
        try:
            val = float(euros)
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
