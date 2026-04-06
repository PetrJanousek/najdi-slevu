import re
from .models import Discount

_ALCOHOL_KEYWORDS = [
    "víno", "červené", "bílé", "růžové", "pivo",
    "whisky", "whiskey", "rum", "vodka", "gin",
    "sekt", "prosecco", "šampaňské", "likér",
    "brandy", "cognac", "bourbon", "tequila",
    "aperitiv", "vermut", "portské",
]

_PATTERN = re.compile(
    "|".join(re.escape(k) for k in _ALCOHOL_KEYWORDS),
    re.IGNORECASE,
)


def filter_alcohol(discounts: list[Discount]) -> list[Discount]:
    """Return only discounts whose name matches Czech alcohol keywords."""
    return [d for d in discounts if _PATTERN.search(d.name)]
