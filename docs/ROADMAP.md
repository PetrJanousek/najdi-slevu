# najdi-slevu — Multi-Phase Roadmap

## Context

`najdi-slevu` is a Czech supermarket discount scraper. Today it already does the end-to-end workflow once: fetch unread leaflet emails from Gmail (6 supermarkets — Tesco, Albert, Billa, Penny, Lidl, Kaufland), parse their PDF attachments with a single unified regex-based parser (`scraper/pdf_parser.py`, 513 LOC), and render the extracted discounts as a rich terminal table. It has no database, no tests, no notifications, and no UI beyond the terminal. One open beads issue (`najdi-slevu-smj`) tracks parser tuning against real PDFs.

**Goal:** grow this from the current CLI prototype into a public iOS product, in small, *individually runnable and testable* increments — every step leaves the project in a working, demonstrable state.

**Scope of this roadmap:** a full-featured **personal dev MVP running on Petr's own phone**. The end state of Phase 4 is "I can install this on my iPhone via Xcode/TestFlight and use it daily." Everything required to promote that MVP into a real public App Store release is **explicitly deferred** and will be handled in a separate roadmap after the MVP proves its worth:

- Scheduled/automated scraping (cron/launchd/VPS job) — deferred, manual runs only for MVP
- GDPR / privacy policy / data-subject rights endpoints — deferred
- Rate limiting, abuse prevention, WAF — deferred
- Backup strategy for the SQLite price-history database — deferred
- App Store name reservation, screenshots, review submission — deferred
- Analytics, crash reporting, monitoring — deferred
- Multi-region / Postgres / horizontal scale — deferred

The one "real release" concern that is **NOT** deferred is the legal/IP investigation below — it could kill the project and must be answered before significant effort is invested.

**Key constraints (decided upfront with the user):**

- **Audience:** public product eventually → Phase 3 backend must include real auth from day one of the backend phase (but Phase 2 stays single-user to keep the MVP small).
- **Phase 1b notifications:** terminal output + JSONL log file only. No Telegram/email/push until Phase 3.
- **Hosting during Phase 1–2:** local SQLite, manual runs on the user's Mac/laptop. No cloud, no cron yet.
- **iOS stack:** native SwiftUI.
- **Watched items rule (MVP):** simple case-insensitive keyword substring list in YAML.
- **Multi-user:** single-user schema in Phase 2, migrate to multi-user in Phase 3.
- **Sample leaflet PDFs** from all 6 supermarkets exist outside the repo and will be moved into `tests/fixtures/leaflets/<supermarket>/` as step 0.
- **Plan language:** English.
- **Watched-item alerts:** integrated into `main.py` (one command = full run).
- **Scheduling (cron/launchd):** deliberately deferred to the very end of the roadmap — we have only a handful of saved leaflets right now and will collect more over time through manual runs.

---

## How to read this plan

Each phase is split into **numbered slices**. A slice is the smallest unit that leaves the project runnable and testable. Every slice has:

- **Claude steps** — concrete engineering work an AI agent executes.
- **User steps** — what the human (Petr) needs to do in parallel or after: collecting PDFs, eyeballing output, approving PRs, running things on a device, etc.
- **Runnable state** — how to verify the slice works end-to-end before moving on.

Phases gate each other. Inside a phase, slices are mostly sequential, but some are explicitly parallelizable.

---

# Investigation L — Legal / IP risk (supermarket leaflet content)

**This is a research task, not an engineering task.** It must complete before Phase 3 begins (when the app becomes public-facing via a backend) and should ideally complete before Phase 2 (when we start accumulating a price-history database that derives value from leaflet content). It can run in parallel with Phase 0–1 work.

**The question:** Can an independent third party (Petr, operating `najdi-slevu`) lawfully ingest, parse, store, and redistribute Czech supermarket discount data derived from weekly leaflet PDFs received via Gmail subscription — first as a personal-use dev MVP on his own phone, and eventually as a public iOS product?

**Why it matters:** Leaflets are copyrighted marketing material owned by Lidl, Tesco, Billa, Albert, Penny, and Kaufland. Every incumbent competitor is either the supermarket itself (Lidl Plus, Kaufland, etc.) or a Czech-established aggregator (Kupi.cz backed by Seznam, Moje Letáky, Portmonka backed by MAFRA) — none of which are obviously small indie operators. Their legal posture may rely on B2B partnerships, licenses, or press-extract exemptions unavailable to an individual. Discovering a fundamental legal block at App Store submission would waste the entire iOS phase.

**Scope of the investigation (Claude, acting as research assistant — not legal counsel):**

1. **Copyright status of leaflet content under Czech / EU law.**
   - Are the *images and layout* of supermarket leaflets protected? (Almost certainly yes.)
   - Are the *factual data* — product name, price, validity period — protected as such, or only the creative expression around them? Check the EU `Database Directive 96/9/EC` (sui generis database right) and Czech implementation. Facts themselves are not copyrightable, but a substantial extraction from a protected database may be.
   - Does Czech law recognize a "press extract" / news-reporting / fair-use-equivalent exemption that could cover price aggregation for consumer-information purposes?

2. **Existing Czech aggregator precedent.**
   - How do Kupi.cz, Moje Letáky, Promotheus, Portmonka, and Tiendeo actually source their data? Public filings, interviews, terms of service, or "about" pages may reveal whether they license leaflets from retailers, use a B2B API, or scrape.
   - Are any of them known to have been sued or received cease-and-desist letters? Search for: `kupi.cz žaloba`, `letáky autorská práva`, `Kaufland vs aggregator`, etc.
   - If the pattern is "all major players have commercial partnerships with retailers," that's a strong signal that unilateral scraping is legally fragile even if technically possible.

3. **Gmail-based ingestion specifically.**
   - Does the act of subscribing to a supermarket's marketing newsletter with a personal email, then programmatically parsing the PDFs, create any additional issue beyond the base copyright question? (Newsletter terms of service, CAN-SPAM / Czech equivalent, automated processing clauses.)
   - Check Gmail's Terms of Service and Google API Services User Data Policy for any restriction on using Gmail content as an input to a published product.

4. **Redistribution surface.**
   - Is there a material legal difference between:
     a) A personal CLI on Petr's laptop (Phase 1–2),
     b) A personal iOS app only Petr uses (end of Phase 4, dev install), and
     c) A public App Store release serving arbitrary users?
   - Most likely yes — (a) and (b) fall under personal-use doctrine in most jurisdictions, (c) does not. Confirm this for Czech/EU law.

5. **Mitigation options if the straight path is blocked.**
   - Store only *extracted factual data* (name, price, date) and never redistribute the original PDF, leaflet images, or verbatim marketing copy. Does this materially reduce risk?
   - Attribute every price back to the source supermarket with a deep link to their official page (safe-harbor-style attribution).
   - Add a documented takedown process (`legal@najdislevu.cz` → 48h removal) before public release.
   - Reach out to each supermarket's B2B/affiliate team proactively to discuss partnership or at least get written non-objection.
   - Fall back to a **user-supplied data model**: the app only processes leaflets the *user themselves* forwards from their own inbox — shifting the ingestion legal posture onto the end user (similar to how read-it-later apps work).

**Deliverable:** `docs/legal-investigation.md` summarizing:
- What Claude found in public sources (cite every source).
- A **traffic-light assessment** for each scenario a/b/c above: Green / Yellow / Red, with reasoning.
- A list of **open questions that require an actual lawyer** before any public release. This is the hand-off document for a €200–500 consultation with a Czech IT lawyer at the end of the MVP.
- Recommended mitigations to adopt during MVP so that the "real release" phase starts from the safest possible posture.

**Explicitly out of scope for this investigation:**
- Actually consulting a lawyer (that happens post-MVP, on the real-release track).
- Drafting terms of service or privacy policy (deferred with the rest of the real-release concerns).
- Making the go/no-go call on public release. Claude researches, Petr decides.

**Runnable state:** `docs/legal-investigation.md` exists and answers the five scope questions with cited sources. Petr has read it and recorded a gut-level decision ("proceed with MVP / proceed with mitigation X / abandon") in a `bd remember` note.

---

# Phase 0 — Groundwork (no product change)

Establishes test infrastructure and moves this plan into the repo. Nothing user-visible changes.

### 0.1 — Commit this plan as `docs/ROADMAP.md`
- **Claude:** copy the approved plan to `docs/ROADMAP.md`, commit.
- **User:** review and merge.
- **Runnable state:** plan visible in the repo.

### 0.2 — Establish `tests/` with pytest
- **Claude:**
  - Add `pytest`, `pytest-cov` to `pyproject.toml` dev deps.
  - Create `tests/__init__.py`, `tests/conftest.py`, `tests/unit/`, `tests/fixtures/`.
  - Add `pytest` config block to `pyproject.toml` (`testpaths`, `pythonpath`).
  - Write one sanity test (`tests/unit/test_models.py`) that imports `Discount` and constructs it.
  - Add `.github/workflows/ci.yml` running `pytest` on push/PR (Python 3.11).
- **User:** `uv sync` / `pip install -e '.[dev]'`, run `pytest` locally.
- **Runnable state:** `pytest` exits 0, CI green on a throwaway PR.

### 0.3 — Stage sample PDFs as fixtures
- **User:** drop your saved PDFs into `tests/fixtures/leaflets/<supermarket>/<yyyy-mm-dd>.pdf` for each of tesco/albert/billa/penny/lidl/kaufland. If any supermarket's PDFs are too large/copyright-sensitive, put them in `.gitignore` and document them in `tests/fixtures/leaflets/README.md`.
- **Claude:** create the directory scaffold + README explaining naming convention; add a pytest fixture `sample_pdf(supermarket)` in `conftest.py` that skips the test if the file is missing.
- **Runnable state:** `pytest -k fixtures` passes, skipping missing PDFs gracefully.

---

# Phase 1 — Make the current workflow rock-solid

Goal: the existing email → parse → terminal pipeline works reliably on *every* supermarket's leaflet and has regression tests. Closes `najdi-slevu-smj`.

**Accuracy target (project-wide, applies to every per-supermarket slice in 1.1):** for each supermarket's golden fixture, the parser must achieve **≥90% recall against the hand-curated minimum-set** and **zero impossible rows** (`discounted_price > original_price`, negative prices, dates outside the leaflet's validity window). Recall below 90% means the slice is not done. This is the bar before that supermarket's parser test is allowed to land green.

### 1.1 — Parser baseline tests (one supermarket at a time)
For each of the 6 supermarkets, a separate slice:

- **Claude:**
  - For supermarket X: run the current parser against the fixture PDF, save raw output to `tests/fixtures/expected/<X>.json`.
  - Manually spot-check with user (see "User steps") and hand-curate the expected JSON into a **golden file**: a *minimum* set of discounts that MUST appear (e.g., 10 well-known items) plus a minimum total count threshold.
  - Write `tests/unit/test_parser_<X>.py` that asserts:
    - `parse_pdf(fixture)` returns ≥ N discounts.
    - Every item in `expected_min.json` appears in the output (by name substring + price match).
    - No discount has `discounted_price > original_price`.
    - Dates (if present) fall within a plausible window.
- **User:** open the raw JSON, mark which items are real vs. garbage. Decide the threshold.
- **Runnable state:** `pytest tests/unit/test_parser_<X>.py` passes.

Run slices 1.1a–1.1f in order of likely ease: Tesco → Albert → Billa → Penny → Kaufland → Lidl (Lidl's period-based price format is known to be trickiest).

### 1.2 — Fix parser bugs surfaced in 1.1
- **Claude:** per-supermarket fixes in `scraper/pdf_parser.py`. Prefer targeted regex refinements or supermarket-specific heuristics gated by detection (e.g., "if Lidl layout → use price pattern 4 first"). Every fix lands with a failing-then-passing test.
- **User:** review diffs; watch for overfitting to one leaflet at the expense of others.
- **Runnable state:** all six `test_parser_<X>.py` files pass.

### 1.3 — Add `--supermarket` flag to the CLI
- **Claude:** extend `scraper/cli.py` to accept `--supermarket lidl` (skip filename guessing, force the code path). Useful for manual debugging.
- **Runnable state:** `python -m scraper.cli parse tests/fixtures/leaflets/lidl/2026-04-01.pdf --supermarket lidl` prints a table.

### 1.4 — Mock-Gmail end-to-end test
- **Claude:** write `tests/integration/test_pipeline.py` that monkeypatches `gmail_client.fetch_leaflet_pdfs` to return the fixture PDFs, runs `main.main()`, and asserts the rich table prints expected substrings to captured stdout.
- **Runnable state:** `pytest tests/integration/` passes; `main.py` proven to glue everything together without hitting Gmail.

### 1.5 — Gmail client hardening
- **Claude:**
  - Handle transient Gmail API errors with one retry.
  - Skip non-PDF attachments gracefully instead of crashing.
  - Log which sender produced zero discounts (helps diagnose parser regressions).
  - Unit tests for the helpers that don't need real Gmail.
- **User:** run `python main.py` for real once; confirm it still works against your live inbox.
- **Runnable state:** real `python main.py` run produces output and marks emails read.

### 1.6 — Close `najdi-slevu-smj`
- **Claude:** `bd close najdi-slevu-smj` with a note linking to the commit that introduced parser tests.

---

# Phase 1b — Watched items (still terminal-only)

Goal: declare items you care about; each manual run highlights them prominently and logs them to a file.

### 1b.1 — Watchlist config loader
- **Claude:**
  - New file `scraper/watchlist.py`.
  - Support `watchlist.yaml` at repo root with schema:
    ```yaml
    items:
      - máslo
      - olivový olej
      - káva zrnková
    ```
  - Add `pyyaml` dep.
  - Function `load_watchlist(path) -> list[str]` — lowercases, strips, ignores blanks.
  - Unit tests.
- **User:** create your own `watchlist.yaml` (gitignored; commit only `watchlist.example.yaml`).

### 1b.2 — Matcher
- **Claude:**
  - `scraper/watchlist.py`: `match_discounts(discounts, keywords) -> list[Discount]` — case-insensitive substring match on `discount.name`.
  - Unit tests covering Czech diacritics edge cases (`káva` vs `kava`).
- **Runnable state:** tests pass.

### 1b.3 — Integrate into `main.py`
- **Claude:** after the normal rich table, if any watchlist matches exist, render a separate **"HOT DEALS"** rich panel above/below the main table in bold. Unchanged if no matches. Gate on `watchlist.yaml` existing — no config, no panel.
- **User:** try it with a real run.
- **Runnable state:** `python main.py` shows the HOT DEALS section when items match.

### 1b.4 — Persist matches to `data/hot_deals.jsonl`
- **Claude:** append one JSON line per match per run: `{timestamp, supermarket, name, discounted_price, original_price, valid_from, valid_to, matched_keyword}`. File at `data/hot_deals.jsonl` (gitignored). Create `data/` if missing.
- **Runnable state:** after a run, `tail data/hot_deals.jsonl` shows entries.

### 1b.5 — Phase 1 wrap-up
- **Claude:** document manual-run instructions in `docs/running.md` (how to invoke `python main.py`, env vars, expected output). No scheduler setup yet — see "Deferred: Scheduling" at the end of this roadmap.
- **Runnable state:** `python main.py` works manually and the doc explains how.

**End of Phase 1: you have a reliable, tested, manually-run scraper that flags watched items. No DB, no cloud, no app.**

---

# Phase 2 — Database persistence

Goal: stop throwing away every run. Store discounts and queries in SQLite. Still single-user, still local, still terminal.

### 2.1 — Add SQLAlchemy + Alembic
- **Claude:**
  - Add `sqlalchemy>=2`, `alembic` deps.
  - Create `scraper/db/__init__.py`, `scraper/db/models.py`, `scraper/db/session.py`.
  - Configure Alembic (`alembic/env.py` → uses `scraper.db.models.Base`). DB path from env `NAJDI_SLEVU_DB`, default `data/najdi_slevu.sqlite`.
- **Runnable state:** `alembic current` runs with no schema yet.

### 2.2 — Schema v1
- **Claude:** tables (single-user — no `user_id` yet):
  - `supermarkets(id, code, display_name)` — seeded with the 6.
  - `scrape_runs(id, started_at, finished_at, source)` — one row per `main.py` run.
  - `discounts(id, scrape_run_id, supermarket_id, name, name_normalized, original_price, discounted_price, discount_pct, valid_from, valid_to, raw_text, created_at)`
  - `watchlist_items(id, keyword, created_at)` — replaces `watchlist.yaml` (with import command).
  - `hot_deal_hits(id, discount_id, watchlist_item_id, notified_at)`
  - Index on `(supermarket_id, valid_from)` and `name_normalized`.
- Alembic migration `0001_initial.py`.
- **User:** `alembic upgrade head` once locally.

### 2.3 — Repository layer
- **Claude:** `scraper/db/repo.py` with `save_scrape_run()`, `save_discounts()`, `get_active_discounts()`, `search_discounts(query)`, `get_price_history(name_normalized)`, `add_watchlist_item()`, `list_watchlist()`, `remove_watchlist_item()`. Unit tests against an in-memory SQLite.

### 2.4 — Wire `main.py` to persist
- **Claude:** after parsing, create a `scrape_run` row and persist discounts. Dedup within a single run by `(supermarket_id, name_normalized, discounted_price, valid_from)`.
- **Runnable state:** after running `main.py`, `sqlite3 data/najdi_slevu.sqlite 'select count(*) from discounts;'` shows rows.

### 2.5 — `scraper query` command
- **Claude:** new Typer subcommand(s):
  - `scraper query list [--supermarket lidl] [--min-discount 20]` — rich table from DB.
  - `scraper query search <keyword>`.
  - `scraper query history <keyword>` — price trend for matching items over time.
- Tests for each.
- **Runnable state:** can browse historical data without re-running the scraper.

### 2.6 — Watchlist in DB
- **Claude:**
  - `scraper watchlist add/list/remove <keyword>` subcommands.
  - `scraper watchlist import watchlist.yaml` — one-off migration.
  - `main.py` now reads watchlist from DB. **Remove the `watchlist.yaml` existence gate from Phase 1b.3** — the HOT DEALS panel is now gated on "DB watchlist has ≥1 row." YAML remains only as an import source, not a runtime config.
- **User:** import your yaml once.

### 2.7 — Product canonicalization (the moat)

**Why this slice exists as its own step:** cross-chain price history is the single feature no Czech competitor offers, and it depends entirely on being able to say "Máslo Madeta 250g" at Lidl and "máslo Madeta čerstvé 250 g" at Kaufland are *the same product*. Keyword substring matching (sufficient for watchlist) is **not** sufficient here. Without this slice, the `/discounts/{id}/history` endpoint in Phase 3.2 will return a single row per query and the product's core differentiator will be vaporware.

- **Claude:**
  - New module `scraper/canonical.py` with a `canonicalize(raw_name: str) -> CanonicalProduct` function returning a structured form: `{brand, product_type, descriptors, quantity_value, quantity_unit, canonical_key}`.
  - Tokenization: lowercase, strip diacritics-normalized copy kept alongside the original, split on whitespace and punctuation.
  - Unit extraction: regex for `g / kg / ml / l / ks / balení / pack` with numeric value. Normalize to base units (grams, milliliters, pieces).
  - Brand stripping: maintain a small curated list of common CZ FMCG brands (Madeta, Pilos, Opavia, Hamé, etc.) in `scraper/brands.txt`. Extract and store separately; don't discard.
  - Stopword / marketing-word removal: "akce", "sleva", "novinka", "nově", "extra", "family", "pack", percentage strings, etc.
  - `canonical_key` = `f"{product_type}|{brand or '-'}|{quantity_value}{quantity_unit}"` — this is what gets indexed for price history grouping.
  - Golden-file tests: `tests/unit/test_canonical.py` with ~30 hand-picked pairs that must canonicalize to the same key, and ~10 that must not (e.g., "Máslo 250g" vs "Máslo 500g" must differ; "Máslo Madeta 250g" at Lidl vs "máslo MADETA 250 g" at Kaufland must match).
  - Alembic migration `0002_canonicalization.py`: add columns `canonical_brand`, `canonical_product_type`, `canonical_quantity_value`, `canonical_quantity_unit`, `canonical_key` to `discounts`, plus an index on `canonical_key`. Backfill existing rows with a one-off script.
  - Update `repo.save_discounts()` to populate these columns on insert.
- **User:** review the canonicalization output on a batch of real discounts and flag obvious misses. Expect ~1 hour of tuning.
- **Runnable state:** `pytest tests/unit/test_canonical.py` passes. A new query `scraper query history <keyword>` (deferred to 2.8) will return multi-row history across chains.

### 2.8 — Price history + fake-discount detection
- **Claude:**
  - `repo.get_price_history(canonical_key) -> list[PricePoint]` returning every recorded price for a product across all chains, ordered by date. Each point includes `supermarket`, `discounted_price`, `original_price`, `valid_from`, `valid_to`, `scrape_run_id`.
  - `repo.compute_product_stats(canonical_key)` returning: `lowest_price_ever`, `lowest_price_90d`, `median_price_90d`, `times_on_sale_90d`, `is_currently_at_historical_low: bool`.
  - **Fake-discount detection heuristic:** a discount is flagged `fake_discount=True` when `original_price` in the current row is within 2% of the median observed `original_price` over the last 60 days, AND `discounted_price` is within 5% of the median observed `discounted_price` over the same window. Translation: "this has been 'on sale' at this exact price continuously." Unit test with synthetic data.
  - New `scraper query history <keyword>` command: takes a keyword, canonicalizes it, finds the best-matching `canonical_key`(s) in the DB, and prints a rich table of price points across chains with a sparkline column.
  - Update the main discount table (`main.py` / `scraper/display.py`) to add two columns: `HIST LOW` (showing `✓` if current `discounted_price` equals the all-time low for that canonical key) and `FAKE?` (showing `⚠` when the fake-discount heuristic fires).
- **Runnable state:** two consecutive runs against slightly different fixture data show the new-price flag; `scraper query history máslo` returns a multi-chain history; at least one synthetic fake-discount fixture triggers the `⚠` column.

**End of Phase 2: durable local history, queryable, still a single-user terminal tool. Perfect stopping point if iOS plans slip.**

---

# Phase 3 — Backend API (FastAPI, multi-user, cloud-ready)

Goal: expose the database via an authenticated HTTP API that an iOS app can consume. This is where we introduce users and a proper deployment target.

### 3.1 — FastAPI skeleton
- **Claude:**
  - New package `backend/` with FastAPI app, `uvicorn` dev server.
  - `GET /health` returning `{status: ok, version}`.
  - Reuses `scraper/db` for the DB layer.
  - Dockerfile (multi-stage, Python slim).
  - `backend/tests/` with one TestClient test.
- **User:** `uvicorn backend.main:app --reload` locally.

### 3.2 — Read-only public endpoints
- **Claude:**
  - `GET /supermarkets` — list with codes and display names.
  - `GET /discounts` — paginated, filters: `supermarket`, `min_discount_pct`, `valid_on=<date>`, `q=<search>`.
  - `GET /discounts/{id}`.
  - `GET /discounts/{id}/history` — price history for the same normalized name.
  - OpenAPI auto-docs available at `/docs`.
- **Runnable state:** `curl localhost:8000/discounts?supermarket=lidl` returns JSON.

### 3.3 — Multi-user migration
- **Claude:**
  - Alembic migration `0002_multiuser`: add `users(id, email, password_hash, created_at)`, add `user_id` to `watchlist_items` and `hot_deal_hits`. Backfill with a synthetic "local" user so existing data survives.
  - Update repository layer to accept `user_id` everywhere watchlist is touched.
- **User:** `alembic upgrade head`.

### 3.4 — Auth (email + password, JWT)
- **Claude:**
  - `POST /auth/register`, `POST /auth/login` returning JWT.
  - `passlib[bcrypt]` for password hashing, `python-jose` for JWT.
  - `get_current_user` dependency for protected routes.
  - Tests.
- **Runnable state:** register → login → get JWT → hit a protected endpoint.

### 3.5 — User watchlist endpoints
- **Claude:** `GET/POST/DELETE /me/watchlist`. Tests.
- **Runnable state:** a user can manage their own watchlist over HTTP.

### 3.6 — Device registration + APNs
- **Claude:**
  - `POST /me/devices` (device_token, platform=ios).
  - `devices(id, user_id, token, platform, created_at, last_seen_at)` table.
  - APNs HTTP/2 client (`aioapns` or `httpx` + JWT).
  - Background task: after each scrape run, match new discounts against each user's watchlist and send an APNs push per match (with dedup per `(user, discount)`).
  - Dev mode logs push payload instead of sending.
- **User:** create an Apple Developer account and APNs auth key (instructions in `docs/apns-setup.md`).
- **Runnable state:** curl-triggered mock scrape emits a logged push payload.

### 3.7 — Scrape trigger integration
- **Claude:** keep `main.py` as the scraper that writes to the same SQLite DB the backend reads from. No backend-triggered scraping yet. Still run manually in this phase.

### 3.8 — Deployment
- **Claude:**
  - Docker Compose with `backend` + volume-mounted SQLite.
  - Deploy script to a small VPS (Hetzner CX11 or Fly.io Machines).
  - Caddy reverse proxy with automatic HTTPS on a domain.
  - GitHub Actions: on push to `main`, build image and deploy.
- **User:** buy domain, provision VPS, add DNS, add secrets to GH Actions.
- **Runnable state:** `https://api.najdi-slevu.cz/health` returns 200 from the VPS.

**End of Phase 3: backend is live, authenticated, pushes notifications — but no clients use it yet except curl/Postman.**

---

# Phase 4 — iOS app (SwiftUI)

Goal: ship a native iOS app, increment by increment, so every TestFlight build is a complete, usable (if minimal) app.

### 4.1 — "Hello world" SwiftUI project
- **User:** create Xcode project `NajdiSlevu`, minimum iOS 17, SwiftUI + SwiftData, bundle id `cz.najdislevu.app`, commit under `ios/`.
- **Claude:** generate `.gitignore` for Xcode, CI step that runs `xcodebuild test` on macOS runner (optional), app icon stub.
- **Runnable state:** empty app runs on simulator.

### 4.2 — API client + Discounts list (read-only, unauthenticated)
- **Claude:**
  - `APIClient` actor with async methods matching `GET /supermarkets`, `GET /discounts`.
  - `DiscountsListView` grouped by supermarket.
  - Pull-to-refresh.
- **User:** point `API_BASE_URL` at your VPS or a local tunnel.
- **Runnable state:** open the app → see today's discounts.

### 4.3 — Discount detail + supermarket filter
- **Claude:** detail view with full info, history chart (line chart via Swift Charts using `/discounts/{id}/history`), filter picker at the top of the list.
- **Runnable state:** tap a discount → full detail and price trend.

### 4.4 — Search
- **Claude:** search bar calling `GET /discounts?q=`. Debounced.
- **Runnable state:** type "máslo" → filtered list.

### 4.5 — Auth (sign up + log in)
- **Claude:** keychain storage for JWT, login/register screens, logout, 401 → force re-auth, `AuthSession` observable.
- **Runnable state:** create account inside the app, stay logged in across relaunches.

### 4.6 — Watchlist CRUD
- **Claude:** "Watchlist" tab. Add keyword, swipe-to-delete. Wire to `/me/watchlist`.
- **Runnable state:** add "káva", see it sync to the backend DB.

### 4.7 — Push notifications
- **Claude:**
  - Request notification permission.
  - Register device token with `POST /me/devices` after login.
  - Handle incoming APNs payload → deep-link to the matching discount's detail.
- **User:** enable push capability in Xcode/Apple Dev portal.
- **Runnable state:** trigger a scrape with a matching discount → push lands on your phone.

### 4.8 — Polish pass
- **Claude:** empty states, error handling, loading skeletons, localization (cs + en), dark mode check, analytics opt-in (optional).
- **Runnable state:** app feels like a real app.

### 4.9 — TestFlight → App Store
- **User:** App Store Connect listing, screenshots, privacy policy, submit for review. Claude drafts copy + privacy policy.
- **Runnable state:** friends can install via TestFlight; eventually app is live.

---

## Verification checklist (end-to-end, any phase)

After any slice, you should be able to run the appropriate commands below and get meaningful output. No slice ends "in progress".

| Phase | Verification command(s) |
|---|---|
| 0 | `pytest` green, CI badge green, `ls tests/fixtures/leaflets/` shows 6 dirs |
| 1 | `pytest tests/unit/test_parser_*.py` green; `python main.py` prints discounts |
| 1b | `python main.py` prints HOT DEALS panel; `tail data/hot_deals.jsonl` |
| 2 | `scraper query list --supermarket lidl`; `sqlite3 data/najdi_slevu.sqlite` inspectable |
| 3 | `curl https://api.najdi-slevu.cz/discounts` returns JSON; curl-based push trigger logs payload |
| 4 | TestFlight install, log in, add watchlist, receive push |

---

## Critical files (by phase)

- **Phase 0:** `pyproject.toml`, `tests/conftest.py`, `tests/fixtures/leaflets/README.md`, `.github/workflows/ci.yml`, `docs/ROADMAP.md`
- **Phase 1:** `scraper/pdf_parser.py`, `scraper/cli.py`, `tests/unit/test_parser_*.py`, `tests/integration/test_pipeline.py`, `scraper/gmail_client.py`
- **Phase 1b:** `scraper/watchlist.py`, `scraper/display.py`, `main.py`, `watchlist.example.yaml`, `data/hot_deals.jsonl`
- **Phase 2:** `scraper/db/models.py`, `scraper/db/session.py`, `scraper/db/repo.py`, `scraper/canonical.py`, `scraper/brands.txt`, `alembic/`, `main.py`, `scraper/cli.py`
- **Phase 3:** `backend/main.py`, `backend/auth.py`, `backend/routers/*.py`, `backend/apns.py`, `Dockerfile`, `docker-compose.yml`, `.github/workflows/deploy.yml`
- **Phase 4:** `ios/NajdiSlevu/` (Xcode project), `ios/NajdiSlevu/APIClient.swift`, `ios/NajdiSlevu/Views/*.swift`

---

## Reusable code / patterns already present

- `scraper.models.Discount` — already the right shape; reuse as-is, it maps cleanly to a DB row.
- `scraper.display.show_discounts` — stays the terminal renderer; backend serializes `Discount` separately.
- `scraper.filters.filter_alcohol` — same pattern the watchlist matcher will follow; don't merge them, they serve different purposes.
- Beads issue tracker already in place; each slice above becomes a bead after plan approval.

---

## Beads issue creation (after plan approval)

When the user approves this roadmap, Claude will create the following bead hierarchy **in a single batch** (using parallel subagents). Each phase is an **epic**; each slice above becomes a **task** blocked by the previous slice in its phase. Phases are linked by cross-phase dependencies (Phase 2 depends on Phase 1 closing, etc.).

- Epic: **Phase 0 — Groundwork** → tasks 0.1, 0.2, 0.3
- Epic: **Phase 1 — Parser hardening** → tasks 1.1a–1.1f, 1.2, 1.3, 1.4, 1.5, 1.6
- Epic: **Phase 1b — Watched items** → tasks 1b.1–1b.5
- Investigation: **Legal / IP risk** → single research task producing `docs/legal-investigation.md`
- Epic: **Phase 2 — DB persistence** → tasks 2.1–2.8
- Epic: **Phase 3 — Backend API** → tasks 3.1–3.8
- Epic: **Phase 4 — iOS app** → tasks 4.1–4.9
- Final: **Deferred scheduling** → single task

Each bead will include `--description` (why), `--acceptance` (how we know it's done), and link to this roadmap.

---

## User's actionable checklist (outside Claude)

Things **only you** can do, in rough order:

1. ☐ Approve this roadmap.
2. ☐ Phase 0.3: copy your saved PDFs into `tests/fixtures/leaflets/<supermarket>/`.
3. ☐ Phase 1.1: spend ~30 min per supermarket eyeballing parser output and telling Claude which items are garbage.
4. ☐ Phase 1.5: run `python main.py` against real Gmail once to confirm the hardening didn't break it.
5. ☐ Phase 1b.1: write your personal `watchlist.yaml`.
6. ☐ Phase 2.2: run `alembic upgrade head` once.
7. ☐ Phase 3.6: Apple Developer account + APNs auth key.
8. ☐ Phase 3.8: buy domain, provision VPS, configure DNS, add GH Actions secrets.
9. ☐ Phase 4.1: create Xcode project skeleton (Claude can't do this — Xcode GUI only for first bootstrap).
10. ☐ Phase 4.7: enable push entitlement in Xcode/Apple portal.
11. ☐ Phase 4.9: App Store Connect listing, screenshots, submission.
12. ☐ Final: set up the scheduler once enough data is flowing (see below).

Everything else is Claude's job.

---

## Deferred: Scheduling

Automating daily runs (cron on the Mac, systemd timer on a server, or a scheduled job on the VPS) is deliberately **deferred to the very end of the roadmap**. Reason: we currently only have a handful of saved leaflet PDFs and will collect more over time via manual runs. Running `python main.py` by hand during Phases 1–3 gives us direct feedback, keeps the dev loop tight, and avoids debugging scheduler issues on top of parser/DB/API issues. Once Phase 3 is live and Phase 4 depends on regularly-updated data, the **final slice** of the project is:

- ☐ Set up a scheduled runner (cron/launchd on Mac for Phase 1–2, or a scheduled container job on the VPS for Phase 3+).
- ☐ Wire its logs to a file and add a `bd remember` note about the exact invocation.

Until then, runs are manual.

---

## Out of scope (deliberately)

- OCR fallback for image-only PDFs.
- Non-Czech supermarkets or locales.
- Android app.
- Recipe / meal-planning features.
- Public web UI (the iOS app is the client; `/docs` is the only web surface).
- Complex ML product matching (substring keyword matching is explicitly the MVP).

These may become their own phases later but are not part of this roadmap.
