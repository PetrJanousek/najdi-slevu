from pathlib import Path
from typing import Optional

import typer

from scraper.display import show_discounts
from scraper.filters import filter_alcohol
from scraper.pdf_parser import parse_pdf

app = typer.Typer(add_completion=False)

_KNOWN_SUPERMARKETS = {"tesco", "albert", "billa", "penny", "kaufland", "lidl", "globus", "spar"}


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


if __name__ == "__main__":
    app()
