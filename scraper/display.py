"""Display utilities for rendering Discount objects as rich terminal tables."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from scraper.models import Discount

if TYPE_CHECKING:
    from scraper.db.repo import PricePoint, ProductStats

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


def _format_bool_flag(value: bool, true_label: str = "YES", false_label: str = "") -> Text:
    if value:
        return Text(true_label, style="bold red")
    return Text(false_label)


def show_discounts(discounts: list[Discount], supermarket: Optional[str] = None) -> None:
    """Render a list of Discount objects as a rich table and print to stdout.

    Args:
        discounts: List of Discount objects to display.
        supermarket: Optional supermarket name shown in the table title.
    """
    title = f"Slevy — {supermarket.capitalize()}" if supermarket else "Slevy"
    table = Table(
        title=title,
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


def show_discounts_with_stats(
    rows: list,
    stats_map: dict,
    supermarket: Optional[str] = None,
) -> None:
    """Render ORM Discount rows with HIST LOW and FAKE? columns.

    Parameters
    ----------
    rows:
        ORM Discount rows (from db.models).
    stats_map:
        Mapping from canonical_key → ProductStats. Rows with no entry get
        empty stats columns.
    supermarket:
        Optional table title suffix.
    """
    title = f"Slevy — {supermarket.capitalize()}" if supermarket else "Slevy"
    table = Table(
        title=title,
        show_header=True,
        header_style="bold cyan",
        show_lines=False,
        expand=False,
    )
    table.add_column("Name", style="", no_wrap=False, min_width=20)
    table.add_column("Disc. price", justify="right", no_wrap=True)
    table.add_column("Discount%", justify="right", no_wrap=True)
    table.add_column("Valid from", justify="center", no_wrap=True)
    table.add_column("Valid to", justify="center", no_wrap=True)
    table.add_column("HIST LOW", justify="center", no_wrap=True)
    table.add_column("FAKE?", justify="center", no_wrap=True)

    for row in rows:
        stats = stats_map.get(row.canonical_key) if row.canonical_key else None
        hist_low = _format_bool_flag(stats.is_at_historical_low, "LOW") if stats else Text("")
        fake = _format_bool_flag(stats.fake_discount, "FAKE?") if stats else Text("")
        table.add_row(
            row.name or "—",
            _format_price(row.discounted_price),
            _format_discount_pct(row.discount_pct),
            _format_date(row.valid_from),
            _format_date(row.valid_to),
            hist_low,
            fake,
        )

    console.print(table)


def show_price_history(points: list, canonical_key: str) -> None:
    """Render price history for a canonical product key as a rich table.

    Parameters
    ----------
    points:
        List of PricePoint objects from repo.get_price_history().
    canonical_key:
        The canonical key being displayed (used in the table title).
    """
    table = Table(
        title=f"Price history — {canonical_key}",
        show_header=True,
        header_style="bold magenta",
        show_lines=False,
        expand=False,
    )
    table.add_column("Date", justify="center", no_wrap=True)
    table.add_column("Supermarket", no_wrap=True)
    table.add_column("Disc. price", justify="right", no_wrap=True)
    table.add_column("Orig. price", justify="right", no_wrap=True)

    for p in points:
        scraped = p.scraped_at.strftime("%d.%m.%Y") if isinstance(p.scraped_at, datetime) else str(p.scraped_at)
        table.add_row(
            scraped,
            p.supermarket or "—",
            _format_price(p.discounted_price),
            _format_price(p.original_price),
        )

    console.print(table)


def show_hot_deals(discounts: list[Discount]) -> None:
    """Render watchlist-matched discounts as a bold HOT DEALS panel.

    Args:
        discounts: Discount objects that matched watchlist keywords.
    """
    table = Table(
        show_header=True,
        header_style="bold red",
        show_lines=False,
        expand=False,
        border_style="red",
    )
    table.add_column("Name", style="bold", no_wrap=False, min_width=20)
    table.add_column("Disc. price", justify="right", no_wrap=True)
    table.add_column("Discount%", justify="right", no_wrap=True)
    table.add_column("Valid to", justify="center", no_wrap=True)

    for discount in discounts:
        table.add_row(
            discount.name or "\u2014",
            _format_price(discount.discounted_price),
            _format_discount_pct(discount.discount_pct),
            _format_date(discount.valid_to),
        )

    panel = Panel(
        table,
        title="\U0001f525 HOT DEALS",
        title_align="left",
        border_style="bold red",
    )
    console.print(panel)
