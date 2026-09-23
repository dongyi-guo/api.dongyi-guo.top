# AGENTS.md

Project context for AI coding agents (Claude Code, or any other agent reading this file). Read this in full before making changes, several parts of this project have non-obvious constraints that aren't visible from the code alone.

## What this project is

A minimal, self-hosted FastAPI service (`app/main.py`) that stores and serves flat, non-nested JSON key/value data at custom "handles" (e.g. `/grounded`). It exists so other projects can pull live numbers from a simple public `GET` endpoint, with all writes gated behind a single admin token.

Its first and currently only real tenant is the **Grounded Café Impact Counter**: a public statistics widget on the TUSA/Grounded Social Enterprise website showing coffees paid forward, meals paid forward, and money saved through student discounts. These numbers are calculated daily from real Square POS sales data and pushed into this API automatically via cron, not entered manually.

## Architecture

```
Square POS (external, not in this repo)
      ↓
jobs/get_orders.py               — pulls the day's orders from Square, writes a CSV
      ↓
data/grounded_cafe_orders.csv    — working file, not served to anyone directly
data/grounded_cafe_orders_raw.json — every order as Square returned it, nothing dropped
      ↓
jobs/update_grounded.py          — aggregates the CSV into 3 impact numbers, pushes them
jobs/update_social_cafe.py       — aggregates the same CSV into 7 trading numbers, pushes them
jobs/update_grounded_monthly.py  — monthly, writes a reporting CSV, pushes NOTHING
      ↓
app/main.py (FastAPI, on 127.0.0.1:55500, reverse-proxied by Nginx)
      ↓
Grounded website's own JavaScript — fetches /grounded, renders the numbers
```

`jobs/update_grounded_monthly.py` is the odd one out: it is the only job that publishes
nothing. It writes `data/grounded_monthly_summary.csv` for reporting to the cafe and TUSA,
on its own monthly cron line, deliberately not in `daily_update.sh` so a reporting failure
can never stop the daily figures.

`jobs/daily_update.sh` is the single cron entry point (runs at 5pm daily), it runs `get_orders.py` then `update_grounded.py` in sequence, and deliberately aborts before the push step if the Square fetch fails, to avoid publishing stale or incomplete data.

## Folder layout

Folders are split by **how a file is used**, not by language:

| Path | Holds |
|---|---|
| `index.html`, `styles/`, `scripts/` | The admin front end, served at `/`, `/styles/…`, `/scripts/…`. `scripts/` is browser JavaScript only, never Python |
| `app/` | The FastAPI service. Referenced as `app.main:app` by the systemd unit |
| `jobs/` | Everything cron runs, and only that |
| `tools/` | Run by hand, never scheduled |
| `data/`, `logs/` | Runtime output, both gitignored, both created on demand |
| `.env` | Credentials, in the project root, gitignored |

Every script resolves its paths from `Path(__file__).resolve().parents[1]`, not the
working directory, so they behave identically under cron and by hand. Don't reintroduce
bare relative paths like `open("grounded_cafe_orders.csv")`.

## Root-level files

| File | Purpose |
|---|---|
| `app/main.py` | FastAPI app. Handle CRUD, admin token auth via `secrets.compare_digest`, atomic writes (write-to-temp then `os.replace`) to avoid corruption, no in-memory caching (every request re-reads the store file from disk) |
| `requirements.txt` | All dependencies for the whole project: FastAPI and Uvicorn for the service, `requests` and `python-dotenv` for the jobs and tools |
| `data/api_store.json` | Runtime-generated data store. Gitignored. Structure: `{"handle_name": {"key": "value", ...}}`, one flat layer only, nested objects/arrays are rejected by validation |
| `index.html`, `styles/admin.css`, `scripts/admin.js` | Admin panel frontend. Unlocks with the admin token, allows manual CRUD on any handle |
| `README.md` | Project-level setup docs (server, systemd, Nginx, cron) |

## `jobs/` and `tools/`

| File | Purpose | Run frequency |
|---|---|---|
| `get_orders.py` | Pulls paginated Square orders via `/v2/orders/search`, filters/sorts by `created_at`, converts timestamps to `Australia/Hobart`, records every discount and refund, categorises items, writes `data/grounded_cafe_orders.csv` (one row per line item, full rewrite each run, not append) and `data/grounded_cafe_orders_raw.json` | Daily via cron |
| `update_grounded.py` | Reads the CSV, aggregates `coffees_paid_forward`, `meals_paid_forward`, `student_discounts_saved`, pushes them to `/grounded` | Daily via cron, after `get_orders.py` |
| `update_social_cafe.py` | Reads the same CSV for trading stats, pushes 7 values to `/social-cafe`. Counts orders differently from `update_grounded.py` **on purpose** | Daily via cron, after `update_grounded.py` |
| `api_client.py` | Shared push helper: creates a handle if absent, updates it otherwise | Imported by both |
| `order_rows.py` | Shared CSV reading: `is_sale()` skips `RETURN`/`EMPTY` rows, `discounts()` splits a line's several discounts. Every CSV reader must use it | Imported by all readers |
| `update_grounded_monthly.py` | Reads the CSV, writes `data/grounded_monthly_summary.csv` (one row per month, monthly and cumulative columns). Publishes nothing. Requires `--month YYYY-MM`; `--cumulative` switches the printed view to totals since opening | Monthly via cron, 1st of the month |
| `daily_update.sh` | Cron entry point. Resolves the project root from its own path, sources the root `.env`, runs both scripts in order, logs to `logs/cron.log`, aborts early if the fetch fails | Called by cron at 5pm daily |
| `diagnostics.py` | All one-off diagnostics behind subcommands: `locations` (Square location IDs), `discounts` (configured discounts and their catalog IDs), `categories` (catalog categories on the account), `coverage` (what fraction of catalog items have a category assigned, as of last check 89 of 90), `student-share` (student-related share of the CSV rows). Paginates catalog reads via `cursor`, same as `get_orders.py` | As needed |
| `README.md` | Technical docs, one in each of `jobs/` and `tools/` |

## Critical domain knowledge (not obvious from the code)

**1. Items ARE categorised in Square, and categorisation joins on catalog IDs.** An earlier
note in this file claimed the opposite, that 0 of 67 items had a category. That was wrong:
it came from reading `item_data.category_id`, which Square deprecated and which always
reads as null. The live fields are `reporting_category` and `categories`. Checked via
`diagnostics.py coverage`: 89 of 90 items are categorised, the one exception being Square's
own demo item.

`get_orders.py` therefore categorises by **catalog ID**: order line items carry the variation
id in `catalog_object_id`, `build_catalog_lookups()` maps every variation to its Square
category, and `CATEGORY_BUCKET` translates ~24 Square category names into the four buckets
this pipeline reports (`Coffee`, `Drink`, `Food`, `Exclude`). IDs survive renames, so this
does not drift. A Square category with no entry in `CATEGORY_BUCKET` prints a loud warning.

**2. Item names drift, which is why the name map is now only a FALLBACK.** Confirmed examples: catalog has `"Toastie ~ The Reuben"`, but live orders show `"Reuben Toastie"` and even a typo variant `"Ruban Toastie"`. Trailing whitespace has also appeared (`"Soup "`). `ITEM_CATEGORY` is consulted only when the catalog cannot explain a line item, which in
practice means products that were sold historically and have since been deleted or archived,
such as the `Student Meal` / `Student Drink` items from the June 2026 launch. Names are
normalised (`.strip()`) before lookup. Anything neither source explains is tagged `"Unmapped"`
rather than guessed at.

Switching to ID-based categorisation took `Unmapped` from 36.3% of rows to 0.6%, and took the
published impact figures from 98/109 to 125/121, because 39 pay-it-forward rows had been
silently uncounted. The remaining `Unmapped` rows are all line items with no name at all:
custom amounts rung at the till with no product selected, worth about $1,700 in total. They
cannot be categorised from the data, and that is the floor.

**3. Only the `Paid Forward Redemption` discount is a redemption. `Student Meal` / `Student Drink` are NOT.**
   Those $0 items (and `TUSA After Dark - Food/Drink`) were only ever used on the 17 June 2026
   night event, which TUSA funded. They were once counted as redemptions, which made them about 70% of the
   published figure and made June look like a boom. Decided September 2026 that they don't count, see
   `docs/adr/0001-institution-funded-giveaways-are-not-redemptions.md`. Don't re-add them.

   The donation side is the `Pay-It Forward` item (variations `Regular Coffee`, `Meal`) and
   `JJ's Personal Pay-it Forward Tracker` (a meal). Donations minus redemptions is **Banked**,
   see `CONTEXT.md`.

**4. `Student Discount` (a 20% off discount) is tracked separately and is NOT the same thing as the redemption items above.** It applies to normally-priced purchases by currently enrolled students, unrelated to the pay-it-forward mechanism. Do not merge these two concepts when editing aggregation logic.

**5. All Square timestamps are UTC.** Hobart is UTC+10 (AEST) or UTC+11 (AEDT, daylight saving, roughly October onward). `get_orders.py`'s `START_AT` constant must be written with an explicit Hobart offset (e.g. `"2026-06-09T00:00:00+10:00"`), not a bare UTC time, or the filter boundary will silently be off by 10-11 hours. There was a real incident where a 7am order was missed entirely because of this. If editing date logic here, be deliberate about which offset applies to the date range in question, and don't hardcode `+10:00` if the range might cross a DST boundary.

**6. The Orders API is paginated (500 per page via `cursor`).** `get_orders.py` already loops until `cursor` is absent. Any new Square API calls added to this project should be checked for the same pagination requirement, Square does not return everything in one response for accounts with meaningful order volume.

**7. `data/api_store.json` should never be written to directly.** `app/main.py` uses file locking and atomic writes specifically to prevent corruption from concurrent access. Any script that needs to change stored values (like `update_grounded.py`) must go through the HTTP admin API (`127.0.0.1:55500`, internal, doesn't need to go through the public domain/Nginx), never edit the JSON file on disk directly.

**8. Top-level URL mounts shadow the `/{handle}` route.** `/styles` and `/scripts` are
mounted as static directories, so a handle with either name would be unreachable rather
than merely conflicting. Both are in `RESERVED_HANDLES` in `app/main.py`. Any new
top-level mount must be added there too.

**9. `/grounded` and `/social-cafe` count orders differently, deliberately.** The impact
counter is charity-only. The trading stats treat every order as an order, including free
ones, because staff made the drink either way, but exclude wholly-redeemed orders from the
price average because a donor already paid. Two denominators, one file each, commented in
both. Don't "fix" the inconsistency. `CONTEXT.md` is the source of truth for these terms.

**10. Every Square discount is now recorded, but manual $0 overrides still can't be seen.**
`get_orders.py` once kept only `Student Discount` and `Paid Forward Redemption`, so `100%`,
`Half-Price`, `U-Connect Staff` and `Loyalty Card Freebie` lines arrived with a blank
`discount_name` and looked like they simply cost nothing. Fixed September 2026: all discounts
are written. A line with several shares one row, joined with `; ` in `discount_name` and
`discount_amounts`. Staff sometimes zero the price manually with no discount at all, which
still leaves no marker, but `base_price` now shows what the item was worth.

## Credentials (`.env`, project root)

```
SQUARE_ACCESS_TOKEN=      # Square production access token
SQUARE_SANDBOX_TOKEN=     # Square sandbox token (testing only, not used by get_orders.py directly)
SQUARE_LOCATION_ID=       # Grounded Café's Square location ID
API_ADMIN_TOKEN=          # Must match Environment=API_ADMIN_TOKEN in the systemd service file
API_BASE_URL=http://127.0.0.1:55500   # Internal address, not the public domain
```

**Known issue, worth fixing if touching deployment config:** `API_ADMIN_TOKEN` currently also lives in plaintext inside `/etc/systemd/system/myapi.service` on the server. This is a known, acknowledged weak point, not an oversight to silently work around, flag it if asked to touch auth or secrets handling in this project.

## Known bloat / cleanup not yet done

Nothing outstanding. The previously listed items are resolved: the five one-off
diagnostic scripts are consolidated into `tools/diagnostics.py`, and the root
`requirements.txt` already covers the jobs' and tools' dependencies (`requests`,
`python-dotenv`) alongside the API's.

## Style/behavioural notes for whoever (human or agent) works on this next

- CSV output from `get_orders.py` is a full rewrite each run (mode `"w"`, not append), this is deliberate, don't change it to append without understanding why idempotency matters here.
- Prefer failing loudly (aborting the pipeline, printing to `cron.log`) over silently publishing incomplete or guessed data, this principle is already baked into `daily_update.sh`'s abort-on-fetch-failure logic and the `Unmapped` category fallback. Keep that posture in any new code added here.

## Agent skills

### Issue tracker

Issues live in this repo's GitHub Issues, managed via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles, each label string equal to its name. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
