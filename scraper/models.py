from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Discount:
    name: str
    original_price: Optional[float]
    discounted_price: float
    discount_pct: Optional[float]
    valid_from: Optional[date]
    valid_to: Optional[date]
    raw_text: str = field(repr=False)
