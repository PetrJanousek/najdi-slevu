from pathlib import Path

import typer

from scraper.display import show_discounts
from scraper.filters import filter_alcohol
from scraper.pdf_parser import parse_pdf

app = typer.Typer(add_completion=False)


@app.command()
def main(
    pdf_path: Path = typer.Argument(..., help="Path to the supermarket leaflet PDF"),
    alcohol_only: bool = typer.Option(False, "--alcohol-only", help="Show only alcohol discounts"),
) -> None:
    """Extract and display discounts from a Czech supermarket leaflet PDF."""
    discounts = parse_pdf(pdf_path)
    if alcohol_only:
        discounts = filter_alcohol(discounts)
    show_discounts(discounts)


if __name__ == "__main__":
    app()
