from pathlib import Path
from typing import Optional

import typer

from scraper.db.repo import get_active_discounts, search_discounts
from scraper.db.session import make_engine, make_session_factory
from scraper.display import show_discounts
from scraper.filters import filter_alcohol
from scraper.models import Discount as ParsedDiscount
from scraper.pdf_parser import parse_pdf

app = typer.Typer(add_completion=False)
query_app = typer.Typer(help="Query discounts stored in the SQLite database.")
app.add_typer(query_app, name="query")

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

    if not rows:
        typer.echo("No active discounts found.")
        raise typer.Exit()

    # Convert ORM rows to ParsedDiscount for display
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
        if min_discount is None or (r.discount_pct is not None and r.discount_pct >= min_discount)
    ]

    if not parsed:
        typer.echo("No discounts match the given filters.")
        raise typer.Exit()

    show_discounts(parsed, supermarket=supermarket)


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
