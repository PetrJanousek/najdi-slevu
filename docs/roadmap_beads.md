# Roadmap → Beads Translation (DRAFT — not yet created in `bd`)

This file translates `docs/ROADMAP.md` into a flat list of **epics, tasks, and subtasks** with explicit dependencies, suitable for one-shot creation in `bd` (beads) once Petr has reviewed it. **No real beads have been created yet.** Read this file, mark anything wrong/missing/over-scoped, then we batch-create the real beads.

## How to read this file

- **Epics** group related tasks. Each epic gets its own bd issue with `--type=feature` and is the *parent* of its tasks (expressed in beads via dependencies — every task in an epic depends on the epic itself, and the epic stays open until all its tasks close).
- **Tasks** are concrete units of work. Each gets `--type=task` (or `--type=feature` for substantial chunks) and lists explicit `depends-on` IDs.
- **Placeholder IDs** like `T-2.3` are roadmap-local — beads will assign real opaque IDs (`najdi-slevu-xxx`) when created. We keep a mapping at conversion time.
- **Priority** uses bd's P0–P4 scale (P0=critical, P2=medium default, P4=backlog).
- **Cross-epic dependencies** are called out explicitly in the *Dependencies* line. Within an epic, the default is "this task depends on the previous task in the same epic" unless stated otherwise.

## Intentional exclusion: Legal investigation

`Investigation L — Legal / IP risk` from `ROADMAP.md` is **deliberately not tracked in beads**. Per Petr's decision, it is a standalone personal research task — Petr investigates it himself at his own pace, it does not block any engineering work, and `EPIC-3` (the backend epic) is **not** gated on it. It stays documented in `ROADMAP.md` as a reference but never becomes a bd issue.

## Parallelization model — read this first

The roadmap was a strictly sequential plan (Phase 1 → 1b → 2 → 3 → 4). For the beads version we **break Phase 4 (iOS) out of the critical path** so design and frontend implementation can run in parallel with the backend work.

- **`EPIC-4a` (iOS design) has zero upstream dependencies.** It can start on day one, in parallel with everything else. This is the "design epic on its own" Petr asked for.
- A small **API contract epic** (`EPIC-API`) sits between the DB work and both the backend and the iOS implementation. Both sides code against the contract so neither blocks the other.
- **`EPIC-4b` (iOS implementation)** builds the entire app against bundled mock JSON — no real backend needed. It depends only on `EPIC-4a` (design artifacts) and `EPIC-API` (contract).
- **`EPIC-4c` (integration)** is a small final epic that swaps the iOS mock layer for the real backend. Some API churn is accepted as the cost of parallelism.

## Dependency graph (high-level)

```
EPIC-0 (groundwork)
   │
   └──> EPIC-1 (parser hardening)
           │
           └──> EPIC-1b (watchlist)
                   │
                   └──> EPIC-2 (DB + canonicalization + price history)
                           │
                           └──> EPIC-API (OpenAPI contract + fixtures) ──┐
                                   │                                    │
                                   ├──> EPIC-3 (backend)                │
                                   │       │                            │
                                   │       └──────────────┐             │
                                   │                      │             │
                                   └──> EPIC-4b (iOS impl, mocks) ──┐   │
                                           ▲                        │   │
                                           │                        │   │
EPIC-4a (iOS design) ──────────────────────┘                        │   │
(zero dependencies — starts day one)                                │   │
                                                                    ▼   ▼
                                                           EPIC-4c (BE↔FE
                                                           integration)
```

Critical path length is shorter than the linear roadmap because `EPIC-4a` runs in parallel from day one and `EPIC-4b` runs in parallel with `EPIC-3`.

---

# EPIC-0 — Groundwork

**Type:** feature | **Priority:** P0
**Description:** Test infrastructure and fixtures. Nothing user-visible. Prereq for all backend/scraper engineering work.
**Acceptance:** `pytest` runs green; CI runs pytest on PRs; sample PDF fixtures committed (or `.gitignored` with documented placement).

## T-0.1 — Commit ROADMAP.md + roadmap_beads.md (already done; keep as a marker)
**Type:** task | **Priority:** P0
**Depends on:** EPIC-0
**Description:** Document marker — `docs/ROADMAP.md` and `docs/roadmap_beads.md` exist on `main`. May already be merged at the time beads are created; if so, close immediately.
**Acceptance:** Both files visible on `main`.

## T-0.2 — Pytest setup + CI
**Type:** task | **Priority:** P0
**Depends on:** T-0.1
**Description:** Add `pytest`, `pytest-cov` to dev deps. Create `tests/__init__.py`, `tests/conftest.py`, `tests/unit/`, `tests/fixtures/`. Add pytest config to `pyproject.toml`. Write one sanity test importing `Discount`. Add `.github/workflows/ci.yml` running `pytest` on push/PR (Python 3.11).
**Acceptance:** `pytest` exits 0 locally; CI green on a throwaway PR.

## T-0.3 — Stage sample PDFs as fixtures
**Type:** task | **Priority:** P0
**Depends on:** T-0.2
**Description:** Petr drops saved PDFs into `tests/fixtures/leaflets/<supermarket>/<yyyy-mm-dd>.pdf`. Claude scaffolds the directory tree, writes `tests/fixtures/leaflets/README.md` with naming convention, adds a `sample_pdf(supermarket)` fixture in `conftest.py` that skips tests when files are missing. Copyright-sensitive PDFs go in `.gitignore`.
**Acceptance:** `pytest -k fixtures` passes (skipping missing PDFs gracefully).

---

# EPIC-1 — Parser hardening

**Type:** feature | **Priority:** P1
**Depends on:** EPIC-0
**Description:** Existing email→parse→terminal pipeline must work reliably on every supermarket's leaflet and have regression tests. Closes `najdi-slevu-smj`.
**Acceptance:** All six per-supermarket parser tests pass with ≥90% recall against hand-curated minimum sets and zero impossible rows; integration test against monkeypatched Gmail passes; one real Gmail run succeeds.

## T-1.1a — Tesco parser baseline test
**Type:** task | **Priority:** P1
**Depends on:** T-0.3
**Description:** Run current parser against the Tesco fixture, save raw output to `tests/fixtures/expected/tesco.json`. Hand-curate a minimum-set golden file with Petr. Write `tests/unit/test_parser_tesco.py` asserting ≥N discounts, every minimum-set item appears (substring + price match), no impossible rows, dates in plausible window.
**Acceptance:** ≥90% recall against the curated minimum set; test passes.

## T-1.1b — Albert parser baseline test
**Type:** task | **Priority:** P1
**Depends on:** T-1.1a
**Description:** Same as T-1.1a for Albert.
**Acceptance:** ≥90% recall; test passes.

## T-1.1c — Billa parser baseline test
**Type:** task | **Priority:** P1
**Depends on:** T-1.1b
**Description:** Same as T-1.1a for Billa.
**Acceptance:** ≥90% recall; test passes.

## T-1.1d — Penny parser baseline test
**Type:** task | **Priority:** P1
**Depends on:** T-1.1c
**Description:** Same as T-1.1a for Penny.
**Acceptance:** ≥90% recall; test passes.

## T-1.1e — Kaufland parser baseline test
**Type:** task | **Priority:** P1
**Depends on:** T-1.1d
**Description:** Same as T-1.1a for Kaufland.
**Acceptance:** ≥90% recall; test passes.

## T-1.1f — Lidl parser baseline test (the trickiest)
**Type:** task | **Priority:** P1
**Depends on:** T-1.1e
**Description:** Same as T-1.1a for Lidl. Lidl's period-based price format is known to be the hardest. May surface architectural issues — escalate if so.
**Acceptance:** ≥90% recall; test passes.

## T-1.2 — Fix parser bugs surfaced in 1.1
**Type:** task | **Priority:** P1
**Depends on:** T-1.1f
**Description:** Per-supermarket fixes in `scraper/pdf_parser.py`. Prefer targeted regex refinements or supermarket-specific heuristics gated by detection. Every fix lands as a failing-then-passing test. Watch for overfitting one leaflet at the expense of others.
**Acceptance:** All six `test_parser_<X>.py` files pass simultaneously.

## T-1.3 — `--supermarket` CLI flag
**Type:** task | **Priority:** P3
**Depends on:** T-1.2
**Description:** Extend `scraper/cli.py` to accept `--supermarket lidl` and skip filename guessing. Useful for manual debugging.
**Acceptance:** `python -m scraper.cli parse tests/fixtures/leaflets/lidl/2026-04-01.pdf --supermarket lidl` prints a table.

## T-1.4 — Mock-Gmail integration test
**Type:** task | **Priority:** P2
**Depends on:** T-1.2
**Description:** Write `tests/integration/test_pipeline.py` that monkeypatches `gmail_client.fetch_leaflet_pdfs` to return fixture PDFs, runs `main.main()`, and asserts the rich table prints expected substrings to captured stdout.
**Acceptance:** `pytest tests/integration/` passes; pipeline glue verified without hitting real Gmail.

## T-1.5 — Gmail client hardening
**Type:** task | **Priority:** P2
**Depends on:** T-1.4
**Description:** Handle transient Gmail API errors with one retry. Skip non-PDF attachments gracefully. Log which sender produced zero discounts. Unit tests for helpers that don't need real Gmail.
**Acceptance:** Real `python main.py` run produces output and marks emails read; unit tests pass.

## T-1.6 — Close `najdi-slevu-smj`
**Type:** task | **Priority:** P3
**Depends on:** T-1.5
**Description:** `bd close najdi-slevu-smj` with a note linking to the commit that introduced parser tests.
**Acceptance:** Issue closed.

---

# EPIC-1b — Watched items (terminal-only)

**Type:** feature | **Priority:** P2
**Depends on:** EPIC-1
**Description:** Declare items you care about; each manual run highlights them prominently and logs them to a JSONL file. Still terminal-only.
**Acceptance:** `python main.py` shows a HOT DEALS panel when watched keywords match; matches append to `data/hot_deals.jsonl`.

## T-1b.1 — Watchlist YAML loader
**Type:** task | **Priority:** P2
**Depends on:** EPIC-1b
**Description:** New file `scraper/watchlist.py`. Support `watchlist.yaml` at repo root with a flat list of keywords. Add `pyyaml` dep. Function `load_watchlist(path) -> list[str]` lowercases, strips, ignores blanks. Unit tests. Petr writes his own gitignored `watchlist.yaml`; commit only `watchlist.example.yaml`.
**Acceptance:** Unit tests pass; `watchlist.example.yaml` committed.

## T-1b.2 — Matcher
**Type:** task | **Priority:** P2
**Depends on:** T-1b.1
**Description:** `scraper/watchlist.py: match_discounts(discounts, keywords) -> list[Discount]` with case-insensitive substring match on `discount.name`. Cover Czech diacritics (`káva` vs `kava`).
**Acceptance:** Unit tests pass including diacritics edge cases.

## T-1b.3 — Integrate HOT DEALS panel into `main.py`
**Type:** task | **Priority:** P2
**Depends on:** T-1b.2
**Description:** After the normal rich table, if any watchlist matches exist, render a separate HOT DEALS rich panel above/below the main table in bold. Gate on `watchlist.yaml` existing for now (this gate is removed in T-2.6).
**Acceptance:** `python main.py` shows the HOT DEALS section when items match; unchanged when none.

## T-1b.4 — Persist matches to JSONL
**Type:** task | **Priority:** P3
**Depends on:** T-1b.3
**Description:** Append one JSON line per match per run to `data/hot_deals.jsonl` (gitignored). Schema: `{timestamp, supermarket, name, discounted_price, original_price, valid_from, valid_to, matched_keyword}`. Create `data/` if missing.
**Acceptance:** After a run, `tail data/hot_deals.jsonl` shows entries.

## T-1b.5 — Document manual-run instructions
**Type:** task | **Priority:** P3
**Depends on:** T-1b.4
**Description:** `docs/running.md` with how to invoke `python main.py`, env vars, expected output. No scheduler setup.
**Acceptance:** `docs/running.md` exists and is accurate.

---

# EPIC-2 — Database persistence

**Type:** feature | **Priority:** P1
**Depends on:** EPIC-1b
**Description:** Stop throwing away every run. Store discounts in SQLite. Single-user, local. Adds canonicalization (the moat) and price-history.
**Acceptance:** SQLite DB persists discounts across runs; canonicalization groups equivalent products across chains; `scraper query history <keyword>` shows multi-chain price history.

## T-2.1 — SQLAlchemy + Alembic setup
**Type:** task | **Priority:** P1
**Depends on:** EPIC-2
**Description:** Add `sqlalchemy>=2`, `alembic` deps. Create `scraper/db/__init__.py`, `models.py`, `session.py`. Configure Alembic (`alembic/env.py` → `scraper.db.models.Base`). DB path from env `NAJDI_SLEVU_DB`, default `data/najdi_slevu.sqlite`.
**Acceptance:** `alembic current` runs cleanly with no schema yet.

## T-2.2 — Schema v1 (single-user)
**Type:** task | **Priority:** P1
**Depends on:** T-2.1
**Description:** Tables: `supermarkets`, `scrape_runs`, `discounts` (with `name_normalized`), `watchlist_items`, `hot_deal_hits`. Indexes on `(supermarket_id, valid_from)` and `name_normalized`. Alembic migration `0001_initial.py`. Petr runs `alembic upgrade head` once.
**Acceptance:** Migration applies; schema visible in SQLite browser.

## T-2.3 — Repository layer
**Type:** task | **Priority:** P1
**Depends on:** T-2.2
**Description:** `scraper/db/repo.py` with `save_scrape_run`, `save_discounts`, `get_active_discounts`, `search_discounts`, `add_watchlist_item`, `list_watchlist`, `remove_watchlist_item`. Unit tests against in-memory SQLite.
**Acceptance:** Unit tests pass.

## T-2.4 — Wire `main.py` to persist
**Type:** task | **Priority:** P1
**Depends on:** T-2.3
**Description:** After parsing, create a `scrape_run` row and persist discounts. Dedup within a single run by `(supermarket_id, name_normalized, discounted_price, valid_from)`.
**Acceptance:** After running `main.py`, `sqlite3 data/najdi_slevu.sqlite 'select count(*) from discounts;'` shows rows.

## T-2.5 — `scraper query` subcommands
**Type:** task | **Priority:** P2
**Depends on:** T-2.4
**Description:** Typer subcommands: `query list [--supermarket lidl] [--min-discount 20]`, `query search <keyword>`. (`query history` is added in T-2.8.)
**Acceptance:** Both subcommands print rich tables from DB; tests pass.

## T-2.6 — Watchlist in DB
**Type:** task | **Priority:** P2
**Depends on:** T-2.5
**Description:** `scraper watchlist add/list/remove <keyword>`. `scraper watchlist import watchlist.yaml` one-off migration. `main.py` reads watchlist from DB. **Remove the YAML existence gate from T-1b.3** — HOT DEALS panel is now gated on "DB watchlist has ≥1 row."
**Acceptance:** Petr imports his YAML once; subsequent runs read watchlist exclusively from DB.

## T-2.7 — Product canonicalization (the moat)
**Type:** feature | **Priority:** P1
**Depends on:** T-2.6
**Description:** New `scraper/canonical.py` with `canonicalize(raw_name) -> CanonicalProduct`. Tokenization, unit extraction (g/kg/ml/l/ks → base units), brand stripping (curated `scraper/brands.txt`), stopword removal (`akce`, `sleva`, `novinka`...). Build `canonical_key = f"{product_type}|{brand or '-'}|{quantity_value}{quantity_unit}"`. Alembic migration `0002_canonicalization.py` adds `canonical_brand`, `canonical_product_type`, `canonical_quantity_value`, `canonical_quantity_unit`, `canonical_key` columns + index. Backfill existing rows.
**Acceptance:** `tests/unit/test_canonical.py` passes with ~30 must-match pairs and ~10 must-not-match pairs. Petr spot-reviews real-data canonicalization output for ~1h.
**Why this is its own slice:** without it, cross-chain price history is impossible — and price history is the product's first-mover differentiator per the competitive analysis.

## T-2.8 — Price history + fake-discount detection
**Type:** feature | **Priority:** P1
**Depends on:** T-2.7
**Description:** `repo.get_price_history(canonical_key)` returns time-ordered price points across chains. `repo.compute_product_stats(canonical_key)` returns lowest-ever, lowest-90d, median-90d, times-on-sale-90d, is-currently-at-historical-low. Fake-discount heuristic: flag when both `original_price` is within 2% of 60d median AND `discounted_price` within 5% of 60d median ("on sale at the same price continuously"). New `scraper query history <keyword>` command prints multi-chain history. Add `HIST LOW` and `FAKE?` columns to the main display table.
**Acceptance:** Two consecutive runs against slightly different fixtures show new-price flag; `scraper query history máslo` returns multi-chain history; synthetic fake-discount fixture triggers `⚠`.

---

# EPIC-API — API contract (the bridge)

**Type:** feature | **Priority:** P1
**Depends on:** EPIC-2
**Description:** A single OpenAPI 3.1 spec at `api/openapi.yaml` describing every endpoint the iOS app will consume. This file is the **contract** that lets `EPIC-3` (backend) and `EPIC-4b` (iOS impl) proceed in parallel without blocking each other. Both sides code against the spec; integration (`EPIC-4c`) is the only place they re-converge. Some churn in the spec is accepted as the cost of parallelism.
**Acceptance:** `api/openapi.yaml` exists, validates against the OpenAPI 3.1 schema, and contains every endpoint listed in `ROADMAP.md` Phases 3.2 / 3.4 / 3.5 / 3.6. Sample fixture JSON exists at `api/fixtures/<endpoint>.json` for each endpoint and is valid against the spec.

## T-API.1 — Draft OpenAPI 3.1 spec for all planned endpoints
**Type:** task | **Priority:** P1
**Depends on:** EPIC-API
**Description:** Write `api/openapi.yaml` covering: `GET /health`, `GET /supermarkets`, `GET /discounts` (with filters: `supermarket`, `min_discount_pct`, `valid_on`, `q`, pagination), `GET /discounts/{id}`, `GET /discounts/{id}/history`, `POST /auth/register`, `POST /auth/login`, `GET/POST/DELETE /me/watchlist`, `POST /me/devices`. Include request/response schemas for `Supermarket`, `Discount`, `PricePoint`, `User`, `WatchlistItem`, `Device`, `AuthToken`, `Error`.
**Acceptance:** `openapi-spec-validator api/openapi.yaml` exits 0; spec rendered in Swagger UI is browsable.

## T-API.2 — Generate canned fixture JSON for every endpoint
**Type:** task | **Priority:** P1
**Depends on:** T-API.1
**Description:** For each endpoint in the spec, write a representative response JSON to `api/fixtures/<endpoint>.json`. Use realistic Czech data (real supermarket names, plausible product names like `máslo Madeta 250 g`, prices in CZK). These fixtures power the iOS mock API layer in `EPIC-4b` so the iOS app can be developed end-to-end before the real backend exists.
**Acceptance:** Every fixture validates against the corresponding response schema in the spec; iOS-side JSON decoding will work without modification when the real backend is wired in.

## T-API.3 — Generate Swift model stubs from spec
**Type:** task | **Priority:** P2
**Depends on:** T-API.1
**Description:** Use `swift-openapi-generator` (Apple's official tool) to generate Swift `Codable` model types and an `APIClient` protocol from `api/openapi.yaml`. Commit generated code under `ios/NajdiSlevu/Generated/`. This enforces the FE/BE contract at compile time — when the spec changes, Swift code fails to compile until updated.
**Acceptance:** `swift build` succeeds with the generated models; Xcode autocomplete shows the types.

---

# EPIC-3 — Backend API (FastAPI, multi-user, cloud-ready)

**Type:** feature | **Priority:** P1
**Depends on:** EPIC-API
**Description:** Implement the API contract from `EPIC-API` as a FastAPI service. Authenticated, multi-user, deployable. Reuses `scraper/db` for storage. Note: scheduling, GDPR endpoints, rate limiting, and backups are explicitly **deferred to a separate post-MVP roadmap** per Petr's instruction.
**Acceptance:** All endpoints in `api/openapi.yaml` are implemented and pass contract tests; deployed to a small VPS with HTTPS; `curl https://api.najdi-slevu.cz/discounts` returns JSON matching the spec.

## T-3.1 — FastAPI skeleton
**Type:** task | **Priority:** P1
**Depends on:** EPIC-3
**Description:** New package `backend/` with FastAPI app, `uvicorn` dev server. `GET /health` returning `{status, version}`. Reuses `scraper/db`. Dockerfile (multi-stage Python slim). `backend/tests/` with one TestClient test.
**Acceptance:** `uvicorn backend.main:app --reload` runs; `curl localhost:8000/health` works.

## T-3.2 — Read-only public endpoints
**Type:** task | **Priority:** P1
**Depends on:** T-3.1
**Description:** Implement `GET /supermarkets`, `GET /discounts` (with all filters), `GET /discounts/{id}`, `GET /discounts/{id}/history`. Generate OpenAPI auto-docs at `/docs` and verify they match `api/openapi.yaml`.
**Acceptance:** `curl localhost:8000/discounts?supermarket=lidl` returns JSON; contract test confirms shape matches spec.

## T-3.3 — Multi-user migration
**Type:** task | **Priority:** P1
**Depends on:** T-3.2
**Description:** Alembic migration `0003_multiuser.py`: add `users(id, email, password_hash, created_at)`, add `user_id` to `watchlist_items` and `hot_deal_hits`. Backfill with synthetic "local" user so existing data survives. Update repository layer to accept `user_id`.
**Acceptance:** `alembic upgrade head` succeeds; existing data accessible under "local" user.

## T-3.4 — Auth (email + password, JWT)
**Type:** task | **Priority:** P1
**Depends on:** T-3.3
**Description:** `POST /auth/register`, `POST /auth/login` returning JWT. `passlib[bcrypt]` for password hashing, `python-jose` for JWT. `get_current_user` dependency for protected routes. Tests.
**Acceptance:** Register → login → JWT → hit a protected endpoint successfully.

## T-3.5 — User watchlist endpoints
**Type:** task | **Priority:** P2
**Depends on:** T-3.4
**Description:** `GET/POST/DELETE /me/watchlist`. Tests.
**Acceptance:** A user can manage their watchlist over HTTP.

## T-3.6 — Device registration + APNs (dev mode, logs only)
**Type:** task | **Priority:** P2
**Depends on:** T-3.5
**Description:** `POST /me/devices` (token, platform). New `devices` table. APNs HTTP/2 client (`aioapns` or `httpx` + JWT). Background task: after each scrape run, match new discounts against each user's watchlist and emit a push per match (dedup per `(user, discount)`). **Dev mode logs payload to stdout instead of sending** — this is important because Petr is deliberately delaying the Apple Developer account purchase; the backend must work end-to-end without APNs credentials until T-4c.4.
**Acceptance:** A curl-triggered mock scrape with a matching watchlist item logs a push payload to stdout.

## T-3.7 — Document manual-scrape integration
**Type:** task | **Priority:** P3
**Depends on:** T-3.6
**Description:** Document that `main.py` is still run manually and writes to the same SQLite DB the backend reads from. No scheduling. Update `docs/running.md`.
**Acceptance:** `docs/running.md` updated.

## T-3.8 — Deployment (Hetzner / Fly.io + Caddy)
**Type:** task | **Priority:** P2
**Depends on:** T-3.7
**Description:** Docker Compose with `backend` + volume-mounted SQLite. Deploy script to small VPS. Caddy reverse proxy with auto HTTPS on a domain. GitHub Actions: build image and deploy on push to `main`. Petr buys domain, provisions VPS, configures DNS, adds GH Actions secrets.
**Acceptance:** `https://api.najdi-slevu.cz/health` returns 200 from the VPS.

---

# EPIC-4a — iOS design (standalone, no dependencies)

**Type:** feature | **Priority:** P1
**Depends on:** *(none — starts day one, parallel with all backend work)*
**Description:** Visual and interaction design for the iOS app. **Fully independent** — no engineering dependency. Output is a small set of artifacts (wireframes, design system, mockups, app icon) checked into `design/` and used as the spec for `EPIC-4b`. Scope is calibrated for a personal dev MVP — no marketing site, no App Store screenshots, no n-persona research. **Tooling: Figma or Canva** — not Excalidraw. Commit exported PNG/SVG alongside a link to the source file.
**Acceptance:** `design/` contains wireframes for every primary screen, a one-page design system, high-fidelity mockups for the four most-used screens, and an app icon SVG/PNG at all required iOS sizes.

## T-4a.1 — User flows + information architecture
**Type:** task | **Priority:** P1
**Depends on:** EPIC-4a
**Description:** Map out the primary user flows in **Figma** (or Canva): (1) opening the app and browsing today's discounts, (2) searching for a specific product, (3) adding an item to the watchlist, (4) viewing a discount detail with price history, (5) receiving a push notification and deep-linking to a discount, (6) logging in / signing up. Export as `design/user-flows.png` and commit alongside a link to the Figma file in `design/README.md`. Define the tab-bar structure (likely: Discounts | Search | Watchlist | Settings).
**Acceptance:** `design/user-flows.png` exists and covers all six flows; Figma source linked in `design/README.md`.

## T-4a.2 — Low-fidelity wireframes for every primary screen
**Type:** task | **Priority:** P1
**Depends on:** T-4a.1
**Description:** Wireframe each screen identified in T-4a.1 in **Figma**: discounts list (grouped by supermarket), discount detail with chart, search results, watchlist tab, login/register, settings. Greyscale, focus on layout and information density. Export PNGs to `design/wireframes/`.
**Acceptance:** Wireframes for ≥8 screens committed as PNGs with Figma source linked.

## T-4a.3 — Visual design system (colors, type, spacing, icons)
**Type:** task | **Priority:** P1
**Depends on:** T-4a.2
**Description:** Define a minimal design system in `design/design-system.md`: color palette (primary, secondary, success/discount-green, warning/fake-discount-yellow, semantic colors for each supermarket brand if used), typography scale (SF Pro), spacing scale (4/8/12/16/24/32), corner radii, elevation/shadow rules, dark-mode variants. Pick an icon set (SF Symbols is the default for iOS-native feel). Build the Figma component library alongside the markdown. Commit color tokens as a Swift file stub at `design/Colors.swift` for direct use in `EPIC-4b`.
**Acceptance:** `design/design-system.md` exists; Figma library linked; `design/Colors.swift` ready to drop into the Xcode project.

## T-4a.4 — High-fidelity mockups for the four hero screens
**Type:** task | **Priority:** P2
**Depends on:** T-4a.3
**Description:** Hi-fi **Figma** mockups for: (1) Discounts list, (2) Discount detail with price-history chart and `HIST LOW` / `FAKE?` badges, (3) Watchlist tab with add/delete, (4) Search results. Both light and dark mode. Export PNGs to `design/mockups/`.
**Acceptance:** 8 PNGs (4 screens × 2 modes) committed with Figma source linked.

## T-4a.5 — App icon
**Type:** task | **Priority:** P2
**Depends on:** T-4a.3
**Description:** Design app icon in **Figma** or **Canva**. Constraint: must read clearly at 60×60 on a home screen. Suggested motif: stylized leaflet + percent-off mark, or a minimal "NS" monogram. Export to all required iOS sizes (`AppIcon.appiconset`) and commit under `design/icon/`.
**Acceptance:** Full `AppIcon.appiconset` ready to drop into Xcode.

## T-4a.6 — Czech UI copy + microcopy review
**Type:** task | **Priority:** P3
**Depends on:** T-4a.4
**Description:** Write all visible UI strings in Czech in a single `design/copy.md` file (English fallbacks alongside). Cover button labels, empty states, error messages, push-notification body templates, onboarding copy. This file becomes the source for `Localizable.strings` in T-4b.10.
**Acceptance:** `design/copy.md` covers every screen in the wireframes.

## T-4a.7 — Accessibility checklist
**Type:** task | **Priority:** P3
**Depends on:** T-4a.4
**Description:** Document accessibility requirements: minimum tap target 44pt, dynamic type support, VoiceOver labels for icon-only buttons, sufficient color contrast (WCAG AA), no information conveyed by color alone (the `FAKE?` badge needs an icon, not just yellow). Commit at `design/accessibility.md`.
**Acceptance:** Checklist exists; will be referenced as acceptance criteria for `EPIC-4b` polish task.

---

# EPIC-4b — iOS implementation against mock backend

**Type:** feature | **Priority:** P1
**Depends on:** EPIC-API, EPIC-4a
**Description:** Build the entire iOS app using the OpenAPI contract and canned fixture JSON from `EPIC-API` — **without** depending on a real running backend, and **without** an Apple Developer account (push is simulated via local notifications; real APNs is deferred to T-4c.4). Every screen works end-to-end against the mock layer. Runs in parallel with `EPIC-3`. The mock layer is the only thing replaced in `EPIC-4c`.
**Acceptance:** A free-provisioning development build runs on Petr's iPhone (via Xcode personal team, no paid Apple Developer account), all screens are navigable, all data comes from the bundled mock layer, and switching `APIClient.baseURL` to a real server is the only code change needed for integration.

## T-4b.1 — Xcode project skeleton + repo layout
**Type:** task | **Priority:** P1
**Depends on:** EPIC-4b
**Description:** Petr creates Xcode project `NajdiSlevu`, min iOS 17, SwiftUI + SwiftData, bundle id `cz.najdislevu.app`, **signed with a free personal Apple ID team** (no paid Apple Developer account needed at this stage), commits under `ios/`. Claude adds Xcode `.gitignore`, drops in `design/Colors.swift` and `AppIcon.appiconset` from `EPIC-4a`, generates a stub `App.swift` with a tab-bar shell matching the IA from T-4a.1.
**Acceptance:** Empty app builds and runs on simulator and on Petr's physical iPhone via free provisioning, with the right tab bar and app icon.

## T-4b.2 — Mock APIClient using fixture JSON
**Type:** task | **Priority:** P1
**Depends on:** T-4b.1, T-API.2
**Description:** `APIClient` actor with async methods matching every endpoint in `api/openapi.yaml`. Implementation reads from bundled fixture JSON files (copied from `api/fixtures/`) with a simulated 200ms delay so loading states are testable. Behind a protocol (`APIClientProtocol`) so the real implementation in `EPIC-4c` is a drop-in. Uses the Swift types generated in T-API.3.
**Acceptance:** Calling `apiClient.getDiscounts(supermarket: .lidl)` returns deserialized `Discount` models from the fixture file.

## T-4b.3 — Discounts list view (grouped by supermarket)
**Type:** task | **Priority:** P1
**Depends on:** T-4b.2
**Description:** `DiscountsListView` matching the hi-fi mockup from T-4a.4. Grouped by supermarket. Pull-to-refresh. Loading skeleton, empty state, error state per the design system. Filter picker at the top (supermarket selector).
**Acceptance:** Open the app → see today's mock discounts grouped by chain. Looks like the mockup in light and dark mode.

## T-4b.4 — Discount detail + price history chart
**Type:** task | **Priority:** P1
**Depends on:** T-4b.3
**Description:** Detail view with full info (name, price, discount %, validity dates, supermarket badge). Swift Charts line chart consuming `/discounts/{id}/history` mock data. `HIST LOW` and `FAKE?` badges with icons (per T-4a.7 accessibility — never color-only).
**Acceptance:** Tap a discount → full detail with rendered chart and badges; matches mockup.

## T-4b.5 — Search
**Type:** task | **Priority:** P2
**Depends on:** T-4b.4
**Description:** Search tab with debounced input (300ms) calling `apiClient.searchDiscounts(q:)`. Results list reuses the discount-row view from T-4b.3. Recent-searches persistence in SwiftData.
**Acceptance:** Type "máslo" → debounced filtered results from mock data.

## T-4b.6 — Auth screens (login + register, against mock)
**Type:** task | **Priority:** P2
**Depends on:** T-4b.5
**Description:** Login and register screens matching the design system. `AuthSession` observable. Keychain storage for the (mock) JWT. Logout. Mock `apiClient.login` returns a fake JWT after 200ms; `apiClient.register` always succeeds. 401-handling stub for later real-server use.
**Acceptance:** Create a mock account in the app, stay "logged in" across relaunches.

## T-4b.7 — Watchlist tab CRUD (against mock)
**Type:** task | **Priority:** P2
**Depends on:** T-4b.6
**Description:** Watchlist tab. List of saved keywords with swipe-to-delete. Add-keyword sheet. Wired to mock `/me/watchlist` endpoints (in-memory store inside the mock client so changes persist within a session).
**Acceptance:** Add "káva" → appears in list → swipe to delete.

## T-4b.8 — Simulated push notifications (no Apple Dev account)
**Type:** task | **Priority:** P2
**Depends on:** T-4b.7
**Description:** Request notification permission. Generate a fake device token. Call mock `POST /me/devices`. Implement deep-link handler: tapping a notification with payload `{discount_id: 123}` navigates to that discount's detail. Provide an in-app debug button "Simulate push" that triggers a **local** notification (`UNUserNotificationCenter`) with a sample payload — this lets us test the deep-link flow end-to-end without APNs and without an Apple Developer account. Real APNs is deferred to T-4c.4.
**Acceptance:** Tap "Simulate push" → local notification appears → tap notification → discount detail opens.

## T-4b.9 — Loading / empty / error states polish
**Type:** task | **Priority:** P3
**Depends on:** T-4b.8
**Description:** Sweep every screen for the three states. Use the loading skeletons from T-4b.3 consistently. Error states have a retry button. Empty states have helpful copy from `design/copy.md`.
**Acceptance:** Every screen handles all three states gracefully on a slow-network simulation.

## T-4b.10 — Localization (Czech primary, English fallback)
**Type:** task | **Priority:** P3
**Depends on:** T-4b.9
**Description:** Wire `design/copy.md` strings into `Localizable.strings` (cs + en). Set Czech as the development language. Test by switching device language.
**Acceptance:** All visible strings come from the localization files; switching to English in iOS Settings flips the UI.

## T-4b.11 — Run on Petr's physical iPhone (free provisioning)
**Type:** task | **Priority:** P1
**Depends on:** T-4b.10
**Description:** Sign with free personal team certificate (no paid Apple Developer account), install on Petr's physical iPhone via Xcode. Use the app for a few days against mock data to find friction points. Note: free-provisioning apps expire after 7 days; Petr re-signs weekly until the real Apple Developer account is acquired.
**Acceptance:** App icon appears on Petr's home screen; he uses it for ≥3 days and files at least 1 polish issue per friction point.

---

# EPIC-4c — Backend ↔ frontend integration

**Type:** feature | **Priority:** P1
**Depends on:** EPIC-3, EPIC-4b
**Description:** Replace the iOS mock API layer with calls to the deployed backend. Because both sides were built against `api/openapi.yaml`, this should be a small, mostly-mechanical epic. If it isn't, that's a signal that the contract was incomplete and we fix the spec, not the divergence. **This is also the first epic where a paid Apple Developer account becomes necessary** (for T-4c.4 real APNs). Petr decides the timing.
**Acceptance:** Petr's iPhone app talks to the live backend on the VPS, end-to-end: real auth, real watchlist sync, real push notifications.

## T-4c.1 — Real APIClient implementation
**Type:** task | **Priority:** P1
**Depends on:** EPIC-4c
**Description:** Implement `LiveAPIClient: APIClientProtocol` using `URLSession` against `https://api.najdi-slevu.cz`. Inject via build configuration: Debug builds default to mock, Release builds default to live, both overridable via env var or in-app debug switch. Handle network errors with the same error type the mock used.
**Acceptance:** Toggling the debug switch from "Mock" to "Live" in the running app immediately swaps data sources without a relaunch.

## T-4c.2 — End-to-end auth against real backend
**Type:** task | **Priority:** P1
**Depends on:** T-4c.1
**Description:** Register a new account from the iOS app, receive a real JWT, store in keychain, hit a protected endpoint successfully. Verify 401 handling forces re-auth.
**Acceptance:** A fresh account created from the iPhone is visible in the backend DB.

## T-4c.3 — End-to-end watchlist sync
**Type:** task | **Priority:** P1
**Depends on:** T-4c.2
**Description:** Add a watchlist item from the iPhone → row appears in backend `watchlist_items`. Delete from iPhone → row disappears. Watchlist persists across iPhone reinstalls.
**Acceptance:** Verified manually + 1 SQL spot-check.

## T-4c.4 — End-to-end push notification (Apple Dev account now required)
**Type:** task | **Priority:** P2
**Depends on:** T-4c.3
**Description:** **This is the moment Petr buys the $99/yr Apple Developer account** — deliberately delayed as long as possible. Create APNs auth key, enable push capability in Xcode (paid team), iPhone registers a real device token via `POST /me/devices`. Trigger a manual scrape that hits a watchlist item → APNs delivers a real push to the iPhone → tapping it opens the matching discount detail. This is the moment the moat feature works end-to-end.
**Acceptance:** Petr receives a real push on his iPhone from a manually-triggered scrape, taps it, and lands on the right screen.

## T-4c.5 — Manual integration smoke test
**Type:** task | **Priority:** P2
**Depends on:** T-4c.4
**Description:** Ten-minute manual test plan run after every backend deploy: open app, browse, search, add watchlist item, trigger scrape on backend, receive push, tap it. Document the script in `docs/manual-smoke-test.md`.
**Acceptance:** `docs/manual-smoke-test.md` exists and Petr has run it once successfully.

---

# Conversion notes (when we're ready to create real beads)

Once Petr approves this file:

1. **Create epics first** (9 issues): EPIC-0, EPIC-1, EPIC-1b, EPIC-2, EPIC-API, EPIC-3, EPIC-4a, EPIC-4b, EPIC-4c. Each as `bd create --type=feature --priority=P1` (or P0 for EPIC-0). Record the returned `najdi-slevu-XXX` IDs in a table at the top of this file as `EPIC-0 → najdi-slevu-abc`, etc.
2. **Create tasks per epic**, in order, in parallel using subagents (one subagent per epic). Each task gets `--type=task` (or `--type=feature` for the larger ones marked above), the right priority, and a description that copies the *Description* + *Acceptance* fields here.
3. **Wire dependencies last**, in a single batch of `bd dep add` commands generated from the *Depends on* lines in this file. Cross-epic dependencies are the important ones — within-epic sequential dependencies can also be expressed.
4. **Run `bd lint`** after creation to catch any missing acceptance criteria or orphan issues.
5. **Run `bd ready`** to verify the dependency graph: only `T-0.1` (inside EPIC-0) and `T-4a.1` (inside EPIC-4a, zero deps) should appear initially. That's the signal that parallelism is wired correctly.

**Not in beads (intentional):** the Legal/IP investigation from `ROADMAP.md` stays out of bd — it's Petr's personal research track and must not block or clutter the engineering queue.

Estimated total: **9 epics + ~55 tasks ≈ 64 beads issues**.
