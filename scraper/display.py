"""Display utilities for rendering Discount objects as rich terminal tables."""

from __future__ import annotations

from datetime import date
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.text import Text

from scraper.models import Discount

console = Console()


def _format_price(price: Optional[float]) -> str:
    """Format a price value in Czech style: 'XX,XX Kč'."""
    if price is None:
        return "\u2014"
    formatted = f"{price:,.2f}".replace(",", " ").replace(".", ",")
    return f"{formatted}\u00a0K\u010d"


def _format_date(d: Optional[date]) -> str:
    """Format a date as 'DD.MM.YYYY'."""
    if d is None:
        return "\u2014"
    return d.strftime("%d.%m.%Y")


def _format_discount_pct(pct: Optional[float]) -> Text:
    """Format discount percentage, coloring green if > 20%."""
    if pct is None:
        return Text("\u2014")
    label = f"{pct:.1f}\u00a0%"
    if pct > 20:
        return Text(label, style="bold green")
    return Text(label)


def show_discounts(discounts: list[Discount]) -> None:
    """Render a list of Discount objects as a rich table and print to stdout.

    Args:
        discounts: List of Discount objects to display.
    """
    table = Table(
        title="Slevy",
        show_header=True,
        header_style="bold cyan",
        show_lines=False,
        expand=False,
    )

    table.add_column("Name", style="", no_wrap=False, min_width=20)
    table.add_column("Orig. price", justify="right", no_wrap=True)
    table.add_column("Disc. price", justify="right", no_wrap=True)
    table.add_column("Discount%", justify="right", no_wrap=True)
    table.add_column("Valid from", justify="center", no_wrap=True)
    table.add_column("Valid to", justify="center", no_wrap=True)

    for discount in discounts:
        table.add_row(
            discount.name or "\u2014",
            _format_price(discount.original_price),
            _format_price(discount.discounted_price),
            _format_discount_pct(discount.discount_pct),
            _format_date(discount.valid_from),
            _format_date(discount.valid_to),
        )

    console.print(table)
