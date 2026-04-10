# Running the Pipeline Manually

This guide explains how to run the Gmail → parse → display pipeline by hand.

## Prerequisites

1. **Python 3.11+** (the pipeline is tested against 3.11 in CI)
2. **Install dependencies:**
   ```bash
   pip install -e ".[dev]"   # or: pip install -r requirements.txt
   ```
3. **Gmail OAuth2 credentials** — follow [docs/gmail-oauth-setup.md](gmail-oauth-setup.md)
   to obtain `credentials.json` and `token.json`.

## Running

```bash
python main.py
```

On the first run, a browser window opens for Gmail OAuth. After authorisation,
`token.json` is written and reused on subsequent runs.

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `--alcohol-only` | Show only alcohol-related discounts | off |
| `--credentials PATH` | Path to OAuth2 client secrets file | `credentials.json` |
| `--token PATH` | Path to cached OAuth2 token file | `token.json` |

### Examples

```bash
# Default run — show all discounts from unread leaflet emails
python main.py

# Show only alcohol-related discounts
python main.py --alcohol-only

# Use non-default credentials paths
python main.py --credentials ~/.config/najdi-slevu/credentials.json \
               --token ~/.config/najdi-slevu/token.json
```

## Expected Output

```
=== abc123_tesco_letak.pdf ===
                 Slevy — Tesco
┌──────────────────────┬────────────┬────────────┬──────────┬────────────┬────────────┐
│ Name                 │ Orig. pric…│ Disc. price│ Discount%│ Valid from │ Valid to   │
├──────────────────────┼────────────┼────────────┼──────────┼────────────┼────────────┤
│ Čerstvé mléko 1 l    │ 29,90 Kč   │ 19,90 Kč   │  33.4 %  │ 07.04.2026 │ 13.04.2026 │
│ Celozrnný chléb      │     —      │ 39,90 Kč   │     —    │ 07.04.2026 │ 13.04.2026 │
└──────────────────────┴────────────┴────────────┴──────────┴────────────┴────────────┘

╭─ 🔥 HOT DEALS ─────────────────────────────────────╮
│ Name                 │ Disc. price│ Discount%│ Valid to   │
│ Čerstvé mléko 1 l    │ 19,90 Kč   │  33.4 %  │ 13.04.2026 │
╰─────────────────────────────────────────────────────╯
```

The **HOT DEALS** panel appears only when `watchlist.yaml` is present and at
least one discount name contains a keyword from the watchlist.

## Watchlist Setup

Copy the example watchlist and add your own keywords:

```bash
cp watchlist.example.yaml watchlist.yaml
# Then edit watchlist.yaml — one keyword per line
```

`watchlist.yaml` is gitignored (personal keywords stay local).

## Environment Variables

There are currently no required environment variables. Future database
integration (T-2.x) will introduce `NAJDI_SLEVU_DB`.

## Output Files

| Path | Description |
|------|-------------|
| `data/hot_deals.jsonl` | Appended JSON Lines log of watchlist matches |
| `token.json` | Cached Gmail OAuth2 token (reused on each run) |

Both files are gitignored.

## Parsing Individual PDFs

To test the parser without Gmail, use the CLI directly:

```bash
# Auto-detect supermarket from directory name
python -m scraper.cli tests/fixtures/leaflets/tesco/2026-04-07.pdf

# Explicitly name the supermarket
python -m scraper.cli path/to/leaflet.pdf --supermarket lidl

# Show only alcohol discounts
python -m scraper.cli path/to/leaflet.pdf --alcohol-only
```
