"""main.py — daily pipeline runner.

Fetches unread supermarket leaflet PDFs from Gmail, parses each one,
and displays the results. Intended to be triggered by cron once a day.

Usage:
    python main.py [--alcohol-only] [--credentials credentials.json] [--token token.json]
"""

from __future__ import annotations

from pathlib import Path

import typer

from scraper.display import show_discounts
from scraper.filters import filter_alcohol
from scraper.gmail_client import fetch_leaflet_pdfs
from scraper.pdf_parser import parse_pdf

app = typer.Typer(add_completion=False)


@app.command()
def run(
    alcohol_only: bool = typer.Option(False, "--alcohol-only", help="Show only alcohol discounts"),
    credentials: Path = typer.Option(
        Path("credentials.json"), "--credentials", help="OAuth2 credentials file"
    ),
    token: Path = typer.Option(
        Path("token.json"), "--token", help="OAuth2 token cache file"
    ),
) -> None:
    """Fetch new leaflet PDFs from Gmail, parse discounts, and display them."""
    pdf_paths = fetch_leaflet_pdfs(
        credentials_path=credentials,
        token_path=token,
    )

    if not pdf_paths:
        typer.echo("No new leaflets found.")
        raise typer.Exit()

    for pdf_path in pdf_paths:
        typer.echo(f"\n=== {pdf_path.name} ===")
        discounts = parse_pdf(pdf_path)
        if alcohol_only:
            discounts = filter_alcohol(discounts)
        show_discounts(discounts)


if __name__ == "__main__":
    app()
