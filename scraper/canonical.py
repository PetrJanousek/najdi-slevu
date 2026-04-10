"""scraper/canonical.py — Product name canonicalization.

Converts raw scraped product names into normalized canonical keys that
allow cross-supermarket price comparison. The key is designed to match
the same physical product regardless of which chain sells it.

Canonical key format:
    ``{product_type}|{brand or "-"}|{quantity_value}{quantity_unit}``

Example:
    "Becherovka 0,5 l" → "lihoviny|becherovka|500ml"
    "Rum Jamaica 0.7l"  → "lihoviny|-|700ml"
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CanonicalProduct:
    """Normalized representation of a scraped product."""
    product_type: str          # e.g. "lihoviny", "pivo", "mléčné výrobky"
    brand: Optional[str]       # e.g. "becherovka", None if unknown
    quantity_value: Optional[float]   # e.g. 500.0
    quantity_unit: Optional[str]      # e.g. "ml", "g", "ks"
    canonical_key: str         # composite lookup key


# ---------------------------------------------------------------------------
# Stopwords — removed from product name before classification
# ---------------------------------------------------------------------------

_STOPWORDS = {
    "akce", "sleva", "novinka", "nový", "nova", "nové", "čerstvý", "čerstvé",
    "čerstvá", "bio", "eko", "organic", "premium", "special", "výběr",
    "výhodné", "výhodný", "výhodná", "zlevněno", "zlevněný", "akční",
    "cena", "týden", "týdne", "prodej", "nabídka",
    "různé", "různý", "různá", "druhy", "druh", "příchutě", "příchuť",
    "balení", "bal", "pack", "multipack", "mix",
}

# ---------------------------------------------------------------------------
# Unit normalization — map raw unit tokens to canonical (value_multiplier, unit)
# ---------------------------------------------------------------------------

# Order matters: longer matches should precede shorter ones (e.g. "kg" before "g")
_UNIT_MAP: list[tuple[re.Pattern, float, str]] = [
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*kg\b", re.IGNORECASE), 1000.0, "g"),
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*g\b", re.IGNORECASE), 1.0, "g"),
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*l\b", re.IGNORECASE), 1000.0, "ml"),
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*ml\b", re.IGNORECASE), 1.0, "ml"),
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*cl\b", re.IGNORECASE), 10.0, "ml"),
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*dl\b", re.IGNORECASE), 100.0, "ml"),
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*ks\b", re.IGNORECASE), 1.0, "ks"),
]

# ---------------------------------------------------------------------------
# Product type classification — keyword → product_type label (Czech)
# ---------------------------------------------------------------------------

_TYPE_RULES: list[tuple[frozenset[str], str]] = [
    (frozenset({"rum", "vodka", "gin", "whisky", "whiskey", "brandy", "cognac",
                "slivovice", "becherovka", "fernet", "borovicka", "likér",
                "liquer", "spirit", "lihoviny", "tuzemak", "tuzemský"}), "lihoviny"),
    (frozenset({"pivo", "beer", "lager", "ale", "ipa", "stout", "porter",
                "pilsner", "pilsener", "radler"}), "pivo"),
    (frozenset({"víno", "vino", "wine", "prosecco", "cava", "champagne",
                "sekt", "frizzante", "rosé", "rose"}), "víno"),
    (frozenset({"mléko", "mleko", "milk", "jogurt", "yogurt", "tvaroh",
                "smetana", "cream", "sýr", "syr", "cheese", "máslo",
                "maslo", "butter", "kefír", "kefir"}), "mléčné výrobky"),
    (frozenset({"chléb", "chleb", "bread", "rohlík", "rohlik", "houska",
                "bageta", "baguette", "toast", "pečivo"}), "pečivo"),
    (frozenset({"káva", "kava", "coffee", "espresso", "cappuccino",
                "latte", "instant"}), "káva"),
    (frozenset({"čaj", "caj", "tea", "zelený", "černý"}), "čaj"),
    (frozenset({"cola", "pepsi", "sprite", "fanta", "limonáda", "limonada",
                "džus", "dzus", "juice", "voda", "water", "minerálka",
                "mineralni", "sodovka", "kofola", "energy", "red bull"}), "nápoje"),
    (frozenset({"čokoláda", "cokolada", "chocolate", "bonbon", "pralinky",
                "sladkost", "cukroví", "cukrovi", "gummi", "gummy",
                "lentilky", "dražé", "haribo"}), "cukrovinky"),
    (frozenset({"chips", "chipsy", "brambůrky", "bramburky", "křupky",
                "krupky", "popcorn", "tyčinky", "pretzels", "snack"}), "snacky"),
    (frozenset({"šunka", "sunka", "ham", "salám", "salam", "salami",
                "klobása", "klobasa", "sausage", "párky", "parky",
                "wiener", "frankfurter", "maso", "meat", "kuře",
                "kure", "chicken", "vepřové", "veprove", "beef",
                "hovězí", "hovezi"}), "maso a uzeniny"),
]

# ---------------------------------------------------------------------------
# Brand loading
# ---------------------------------------------------------------------------

_BRANDS_FILE = Path(__file__).parent / "brands.txt"


def _load_brands() -> frozenset[str]:
    if not _BRANDS_FILE.exists():
        return frozenset()
    lines = _BRANDS_FILE.read_text(encoding="utf-8").splitlines()
    return frozenset(
        line.strip().lower()
        for line in lines
        if line.strip() and not line.startswith("#")
    )


_BRANDS: frozenset[str] = _load_brands()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_diacritics(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def _normalize(text: str) -> str:
    """Lowercase and strip diacritics."""
    return _strip_diacritics(text.lower())


def _extract_quantity(raw: str) -> tuple[Optional[float], Optional[str], str]:
    """Find the first quantity+unit in *raw*.

    Returns (value, unit, raw_with_quantity_removed).
    """
    for pattern, multiplier, unit in _UNIT_MAP:
        m = pattern.search(raw)
        if m:
            num_str = m.group(1).replace(",", ".")
            value = float(num_str) * multiplier
            remaining = raw[:m.start()] + raw[m.end():]
            return value, unit, remaining
    return None, None, raw


def _extract_brand(tokens: list[str]) -> tuple[Optional[str], list[str]]:
    """Try to match any 1–3 consecutive tokens as a known brand.

    Returns (brand_normalized, remaining_tokens).
    """
    # Try longest match first (3, 2, 1 tokens)
    for window in (3, 2, 1):
        for i in range(len(tokens) - window + 1):
            candidate = " ".join(tokens[i:i + window])
            if candidate in _BRANDS:
                remaining = tokens[:i] + tokens[i + window:]
                return candidate, remaining
    return None, tokens


def _classify_type(tokens: list[str]) -> str:
    """Map tokens to a product type label."""
    token_set = set(tokens)
    for keywords, label in _TYPE_RULES:
        if token_set & keywords:
            return label
    return "ostatní"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def canonicalize(raw_name: str) -> CanonicalProduct:
    """Convert a raw product name to a CanonicalProduct.

    Parameters
    ----------
    raw_name:
        The raw product name as scraped (may include price cues, units, etc.)

    Returns
    -------
    CanonicalProduct
    """
    # 1. Extract quantity before tokenizing (preserves decimal patterns)
    qty_value, qty_unit, name_no_qty = _extract_quantity(raw_name)

    # 2. Normalize and tokenize
    normalized = _normalize(name_no_qty)
    # Remove punctuation except hyphens within words
    cleaned = re.sub(r"[^\w\s-]", " ", normalized)
    tokens = [t for t in cleaned.split() if t and t not in _STOPWORDS and len(t) > 1]

    # 3. Extract brand
    brand, remaining_tokens = _extract_brand(tokens)

    # 4. Classify product type (from all tokens including brand area)
    product_type = _classify_type(tokens)

    # 5. Build canonical key
    qty_str = (
        f"{int(qty_value)}{qty_unit}" if qty_value is not None and qty_value == int(qty_value)
        else f"{qty_value}{qty_unit}" if qty_value is not None
        else ""
    )
    canonical_key = f"{product_type}|{brand or '-'}|{qty_str}"

    return CanonicalProduct(
        product_type=product_type,
        brand=brand,
        quantity_value=qty_value,
        quantity_unit=qty_unit,
        canonical_key=canonical_key,
    )
