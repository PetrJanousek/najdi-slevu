from pathlib import Path
from typing import Optional

import typer

from scraper.db.repo import (
    add_watchlist_item,
    compute_product_stats,
    get_active_discounts,
    get_price_history,
    list_watchlist,
    remove_watchlist_item,
    search_discounts,
)
from scraper.db.session import make_engine, make_session_factory
from scraper.display import show_discounts, show_discounts_with_stats, show_price_history
from scraper.filters import filter_alcohol
from scraper.models import Discount as ParsedDiscount
from scraper.pdf_parser import parse_pdf

app = typer.Typer(add_completion=False)
query_app = typer.Typer(help="Query discounts stored in the SQLite database.")
app.add_typer(query_app, name="query")
watchlist_app = typer.Typer(help="Manage the keyword watchlist in the database.")
app.add_typer(watchlist_app, name="watchlist")

_KNOWN_SUPERMARKETS = {"tesco", "albert", "billa", "penny", "kaufland", "lidl", "globus", "spar"}


# ---------------------------------------------------------------------------
# parse — parse a PDF file directly
# ---------------------------------------------------------------------------

@app.command()
def main(
    pdf_path: Path = typer.Argument(..., help="Path to the supermarket leaflet PDF"),
    alcohol_only: bool = typer.Option(False, "--alcohol-only", help="Show only alcohol discounts"),
    supermarket: Optional[str] = typer.Option(
        None,
        "--supermarket",
        help=(
            "Supermarket name hint (e.g. 'lidl'). Skips filename guessing and labels the table. "
            f"Known values: {', '.join(sorted(_KNOWN_SUPERMARKETS))}"
        ),
    ),
) -> None:
    """Extract and display discounts from a Czech supermarket leaflet PDF."""
    # Resolve supermarket name: explicit flag > stem of filename
    resolved = supermarket.lower() if supermarket else _guess_supermarket(pdf_path)

    discounts = parse_pdf(pdf_path)
    if alcohol_only:
        discounts = filter_alcohol(discounts)
    show_discounts(discounts, supermarket=resolved)


def _guess_supermarket(path: Path) -> Optional[str]:
    """Try to infer supermarket from the parent directory name."""
    parts = path.parts
    for part in reversed(parts[:-1]):
        if part.lower() in _KNOWN_SUPERMARKETS:
            return part.lower()
    return None


# ---------------------------------------------------------------------------
# query list — list discounts from DB
# ---------------------------------------------------------------------------

@query_app.command("list")
def query_list(
    supermarket: Optional[str] = typer.Option(
        None, "--supermarket", help="Filter by supermarket name"
    ),
    min_discount: Optional[float] = typer.Option(
        None, "--min-discount", help="Minimum discount percentage to show"
    ),
) -> None:
    """List active discounts from the database."""
    engine = make_engine()
    Session = make_session_factory(engine)

    with Session() as session:
        rows = get_active_discounts(session, supermarket_name=supermarket)
        filtered = [
            r for r in rows
            if min_discount is None or (r.discount_pct is not None and r.discount_pct >= min_discount)
        ]
        if not filtered:
            typer.echo("No active discounts found." if not rows else "No discounts match the given filters.")
            raise typer.Exit()

        # Compute stats for each unique canonical_key
        seen_keys: set[str] = set()
        stats_map: dict = {}
        for r in filtered:
            if r.canonical_key and r.canonical_key not in seen_keys:
                seen_keys.add(r.canonical_key)
                stats_map[r.canonical_key] = compute_product_stats(session, r.canonical_key)

    show_discounts_with_stats(filtered, stats_map, supermarket=supermarket)


# ---------------------------------------------------------------------------
# query search — search discounts by keyword
# ---------------------------------------------------------------------------

@query_app.command("search")
def query_search(
    keyword: str = typer.Argument(..., help="Keyword to search for (diacritic-insensitive)"),
) -> None:
    """Search discounts in the database by keyword."""
    engine = make_engine()
    Session = make_session_factory(engine)

    with Session() as session:
        rows = search_discounts(session, keyword)

    if not rows:
        typer.echo(f"No discounts found for '{keyword}'.")
        raise typer.Exit()

    parsed = [
        ParsedDiscount(
            name=r.name,
            original_price=r.original_price,
            discounted_price=r.discounted_price,
            discount_pct=r.discount_pct,
            valid_from=r.valid_from,
            valid_to=r.valid_to,
            raw_text=r.raw_text or "",
        )
        for r in rows
    ]

    show_discounts(parsed)


# ---------------------------------------------------------------------------
# query history — show price history for a keyword
# ---------------------------------------------------------------------------

@query_app.command("history")
def query_history(
    keyword: str = typer.Argument(..., help="Keyword to look up price history for"),
) -> None:
    """Show cross-chain price history for products matching a keyword."""
    engine = make_engine()
    Session = make_session_factory(engine)

    with Session() as session:
        rows = search_discounts(session, keyword)
        if not rows:
            typer.echo(f"No discounts found for '{keyword}'.")
            raise typer.Exit()

        # Collect unique canonical keys from matching rows
        seen: set[str] = set()
        for r in rows:
            if r.canonical_key and r.canonical_key not in seen:
                seen.add(r.canonical_key)
                points = get_price_history(session, r.canonical_key)
                if points:
                    show_price_history(points, r.canonical_key)


# ---------------------------------------------------------------------------
# watchlist — manage keyword watchlist in the DB
# ---------------------------------------------------------------------------

@watchlist_app.command("add")
def watchlist_add(
    keyword: str = typer.Argument(..., help="Keyword to add to the watchlist"),
) -> None:
    """Add a keyword to the watchlist."""
    engine = make_engine()
    Session = make_session_factory(engine)
    with Session() as session:
        item = add_watchlist_item(session, keyword.lower().strip())
        session.commit()
    typer.echo(f"Watchlist: added '{item.keyword}' (id={item.id}).")


@watchlist_app.command("list")
def watchlist_list() -> None:
    """List all keywords in the watchlist."""
    engine = make_engine()
    Session = make_session_factory(engine)
    with Session() as session:
        items = list_watchlist(session)
    if not items:
        typer.echo("Watchlist is empty.")
        raise typer.Exit()
    for item in items:
        typer.echo(item.keyword)


@watchlist_app.command("remove")
def watchlist_remove(
    keyword: str = typer.Argument(..., help="Keyword to remove from the watchlist"),
) -> None:
    """Remove a keyword from the watchlist."""
    engine = make_engine()
    Session = make_session_factory(engine)
    with Session() as session:
        removed = remove_watchlist_item(session, keyword.lower().strip())
        session.commit()
    if removed:
        typer.echo(f"Watchlist: removed '{keyword}'.")
    else:
        typer.echo(f"Watchlist: '{keyword}' not found.")
        raise typer.Exit(code=1)
