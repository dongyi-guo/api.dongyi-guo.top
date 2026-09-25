# AGENTS.md

Project context for AI coding agents. Claude Code reaches this file through `CLAUDE.md`;
Codex, Cursor, Copilot and others read it directly. Read it in full before making changes:
several parts of this project have constraints that aren't visible from the code alone.

## What this project is

A minimal, self-hosted FastAPI service (`app/main.py`) that stores and serves flat, non-nested
JSON key/value data at custom "handles" (e.g. `/grounded`). Other projects pull live numbers
from its public `GET` endpoints; all writes are gated behind a single admin token.

Its first and currently only tenant is the **Grounded Café Impact Counter**: a public widget on
the TUSA/Grounded Social Enterprise website showing coffees paid forward, meals paid forward,
and money saved through student discounts. The numbers are calculated daily from real Square
POS sales and pushed into this API by cron, never entered by hand.

## Where things are

| File | Audience | Holds |
|---|---|---|
| `README.md` | People running the server | Plain-language setup, updating, day-to-day use, troubleshooting. No jargon: when you change it, keep it that way, and put technical detail here instead |
| `AGENTS.md` | Agents and developers | Everything technical. This file |
| `CLAUDE.md` | Claude Code | `@AGENTS.md` only. Claude Code reads that filename, other agents read this one |
| `CONTEXT.md` | Everyone | The glossary. Use its terms (Donation, Redemption, Banked, Order…) in code, tests and issues, and avoid the synonyms it lists |
| `docs/adr/` | Everyone | Decisions, one per file. If your change contradicts one, say so explicitly |
| `docs/history.md` | Everyone | Evidence: what was investigated, what the data showed, how the published numbers moved. Read before changing a counting rule |
| `docs/agents/` | Agent skills | Issue tracker and triage label configuration, see the end of this file |

There is no `SPEC.md`. Specs for new work are GitHub issues.

If a server step changes (a path, a cron line, a new `.env` key), update `README.md` too: it
is what a person follows on the server.

Folders are split by **what they serve**: `app/` is the generic service, `grounded/` is
everything for the Grounded tenant (cron jobs, the shared modules, the by-hand diagnostics),
`tests/` covers `grounded/`. The admin page (`index.html`, `styles/`, `scripts/`) sits at the
root because `app/main.py` serves it from there; `scripts/` is browser JavaScript, never Python.

Every script resolves its paths from `Path(__file__).resolve().parents[1]` (via
`order_rows.BASE_DIR`), never the working directory, so it behaves identically under cron and
by hand. Don't reintroduce bare relative paths like `open("grounded_cafe_orders.csv")`.

## Who depends on this API

Breaking a published key breaks these, so check them before renaming or removing anything:

- **The Grounded website's Impact Counter** fetches `/grounded` from its own JavaScript
  (not in this repo) and shows `coffees_paid_forward`, `meals_paid_forward`,
  `student_discounts_saved`.
- **Grounded Tool Hub** (repo `dongyi-guo/grounded-calc`, locally `~/grounded-calc`), the
  café's break-even calculator. `public/tools/social-cafe/live.js` fetches
  `https://api.dongyi-guo.top/social-cafe` and **requires** `avg_price_per_order`,
  `avg_orders_per_hour` and `hours_per_day`; it also reads `trading_days`, `total_orders`,
  `total_revenue` and `orders_excluding_redemptions`, deriving the pay-it-forward share as
  `1 - orders_excluding_redemptions / total_orders`. Its nginx CSP allows
  `connect-src https://api.dongyi-guo.top`, so moving this API to another domain needs that
  updated too. This is likely the project this one is being merged with.

## Open questions and unfinished work

Nothing here is decided. Don't settle any of it silently; raise it with Dongyi.

**Questions for the café (only the till operator knows):**

- **What is the `100%` discount used for?** 51 lines from 10 July to 22 September, mostly one
  coffee at a time, 1–3 a day, which looks like redemptions. If they are, redeemed coffees
  roughly double (48 → ~95) and the bank goes negative, so probably staff drinks or comps.
- **What is `Food Hub Volunteer Coffee`?** A new discount, first seen 24 September 2026. If it
  is a volunteer perk, fine. If it is pay-it-forward rung up a new way, it's a fourth mechanism.
- **Supervisor's records.** Dongyi mentioned pay-it-forward data kept by their supervisor that
  isn't in Square. Never followed up.

**Decisions Dongyi hasn't made:**

- **Should the public see donations or redemptions?** `/grounded`'s `coffees_paid_forward` /
  `meals_paid_forward` count **redemptions** (50 coffees / 35 meals on 25 Sep 2026). Dongyi's
  monthly statements say "meals purchased for students", which counts **donations** (62 coffees
  / 60 meals on 22 Sep). The two will never agree.
- **Items or dollars?** A $5 friand redeemed against a $12.50 meal donation counts as one meal.
  Items read better on a widget; only dollars give a true banked balance ($375 on 22 Sep).
- **Do snacks count as meals?** Half of redeemed "meals" are snacks under $10.
- **Should refunds be netted off `/social-cafe` revenue?** $230.23 so far, 28 of 44 lines
  "To Be Invoiced", which may be invoicing rather than refunding.
- **Publish banked figures?** `coffees_banked` / `meals_banked` exist in the monthly report but
  not on `/grounded`. A figure that can go down shows the scheme's health better than a lifetime
  total; a rolling 30-day or "this month" figure was also suggested.
- **The 96 `100%` lines on 17 June** are probably the same TUSA-funded night. They were never
  counted, so nothing changes, but ADR 0001 could name them.
- **Monthly cron date:** `date -d yesterday` vs `date -d "last month"`, see the monthly summary
  section below.
- **Admin page location:** `index.html`, `styles/`, `scripts/` could move into `app/` to tidy
  the root, but that changes where the live server finds them (`API_SITE_DIR`). Not done.

**Unfinished work:**

- **The live server still runs from `jobs/`** unless Dongyi has already done the one-off steps
  in `README.md` ("Moving from `jobs/` and `tools/` to `grounded/`"). Until the crontab points
  at `grounded/`, the 5pm update fails.
- **The public numbers drop** from 125 coffees / 121 meals to about 50 / 35 once the server
  runs code from commit `edf2bef` onward (ADR 0001 plus counting items). Anyone who quoted the
  old figures should be told why.
- **The GitHub issue for ADR 0001 was never filed** (`gh` wasn't installed). The ADR is the
  record; filing an issue is optional.

## Working with Dongyi

- Commits go straight to `main`, no pull requests. Dongyi normally pushes; push only when asked
  in that session.
- When Dongyi says "step by step" or "do exactly what I say", do only that and ask before extras.
- Never run `update_grounded.py` or `update_social_cafe.py` (they publish live) unless asked.
  Check whether the `api_client.push` line is commented out before assuming either way.
- `README.md` stays plain language for a person on the server; technical detail goes here.
- Money in reports to two decimal places.
- Verify before claiming: run it, compare against Square's own totals, and say plainly what
  couldn't be tested (e.g. GNU `date` isn't available on the Mac).

## Technical reference

### Pipeline

```
Square POS
   ↓  get_orders.py
data/grounded_cafe_orders.csv  (+ grounded_cafe_orders_raw.json)
   ↓  update_grounded.py          → /grounded       impact figures
   ↓  update_social_cafe.py       → /social-cafe    trading figures
   ↓  update_grounded_monthly.py  → data/grounded_monthly_summary.csv   (publishes nothing)
```

| File in `grounded/` | Runs | Does |
|---|---|---|
| `daily_update.sh` | Cron, 17:00 daily | Sources `.env`, runs the three daily scripts in order. Aborts before any push if `get_orders.py` fails. Keep the `if ! python3 …` form: under `set -e` a separate `$?` check never runs, so the abort was once silent |
| `get_orders.py` | Daily, via the above | Paginated `/v2/orders/search` from `START_AT`, all `COMPLETED` orders, UTC → `Australia/Hobart`, every discount and refund, categorised by catalog ID. Writes the CSV and raw JSON, full rewrite each run |
| `update_grounded.py` | Daily | `aggregate()` → `coffees_paid_forward`, `meals_paid_forward`, `student_discounts_saved` (string, 2dp) → `/grounded` |
| `update_social_cafe.py` | Daily | `aggregate()` → `total_orders`, `orders_excluding_redemptions`, `total_revenue`, `trading_days`, `hours_per_day`, `avg_orders_per_hour`, `avg_price_per_order` → `/social-cafe`. Averages unrounded on purpose: the Break-Even Calculator consumes them and formats itself |
| `update_grounded_monthly.py` | Cron, 1st of month, 17:30 | Writes the monthly summary. `--month YYYY-MM` required, `--cumulative` switches the printed view. Not in `daily_update.sh` so a reporting failure can't block the daily figures |
| `diagnostics.py` | By hand | Subcommands `locations`, `discounts`, `categories`, `coverage`, `student-share`. Catalog reads paginate via `cursor` |
| `order_rows.py` | Imported | The CSV contract and counting rules, see domain note 1 |
| `api_client.py` | Imported | `push(handle, values)`: POST to create a missing handle with all values at once (the API rejects an empty handle), PUT each attribute otherwise |

Scripts import each other by bare name (`import order_rows`), which works because Python puts
a script's own folder on `sys.path`. `tests/conftest.py` adds `grounded/` to the path for the
same reason. There is no package and no `__init__.py`; don't add one without changing how cron
invokes the scripts.

### The orders CSV

`data/grounded_cafe_orders.csv`: **one row per line item**, never duplicated. First nine
columns are the originals: `order_id`, `transaction_time`, `item_name`, `quantity`,
`variation`, `total_amount`, `discount_name`, `discount_saved`, `category`. Then: `record_type`,
`line_uid`, `catalog_object_id`, `square_category`, `base_price`, `variation_total_price`,
`gross_sales`, `total_discount`, `total_tax`, `card_surcharge`, `discount_amounts`,
`discount_ids`, `modifiers`, `note`, `closed_at`, `tender_types`, and on refund rows
`source_order_id`, `source_line_uid`, `refund_reason`. Money is dollars (Square sends integer
cents).

- **`record_type`** is `SALE`, `RETURN` or `EMPTY`. Refunds arrive from Square as separate
  orders with no `line_items`, and are written as negative `RETURN` rows. Orders with nothing on
  them (a cash-drawer `NO_SALE`) are `EMPTY`. Only `SALE` rows are sales.
- **Several discounts on one line share one row**: `discount_name` = `Student Discount; 100%`,
  `discount_amounts` = `0.90; 3.60`, in the same order. `discount_saved` is the line's total.
- Read rows through `order_rows` (`is_sale`, `discounts`, `quantity`, `is_redemption`,
  `redeemed_unit`), never by parsing these columns by hand. `"".split("; ")` is `[""]`, which
  once silently turned real amounts into $0.00.

`data/grounded_cafe_orders_raw.json` is every order exactly as Square returned it, written
atomically. Reach for it when the CSV lacks a field.

### The monthly summary

`data/grounded_monthly_summary.csv`: one row per calendar month. Each figure appears twice, for
the month alone and with a `_total` suffix since opening (9 June 2026). **Purchased** (donations
in), **redeemed** (items out) and **banked** (purchased minus redeemed, always cumulative) are
kept apart. `student_discounts_saved` and `all_discounts_saved` are kept apart too: the second
includes `100%`, `Half-Price`, `U-Connect Staff` and `Loyalty Card Freebie`, and a figure once
published as "saved in student discounts" was actually that one. Giveaway items are reported in
`excluded_giveaway_items` so their exclusion stays visible. A test checks that the lifetime
totals equal what `/grounded` publishes.

The cron line uses `$(date -d yesterday +\%Y-\%m)`: on the 1st, yesterday is in the month just
ended. `%` must be backslash-escaped in crontab or the command is cut at the first one.
`date -d` is GNU; macOS needs `date -v-1d`. Known weakness: a run delayed past the 1st reports
the current month instead; `date -d "last month"` would not. Not yet decided.

### Settings to maintain (top of `get_orders.py`)

- `START_AT`: earliest order, Hobart local time with explicit offset (domain note 6)
- `STUDENT_DISCOUNT_ID`, `PAID_FORWARD_ID`: written under the fixed names in `order_rows`
  whatever the till calls them. Every other discount keeps its catalog name
- `CATEGORY_BUCKET`: Square category name → `Coffee` / `Drink` / `Food` / `Exclude`. Primary
- `ITEM_CATEGORY`: item name → bucket, fallback for items no longer in the catalog

### Known limitations

- Refunds are recorded but nothing nets them off: every count is sales only.
  `all_discounts_saved` will differ slightly from a Square dashboard total that includes
  refunded lines.
- `START_AT` has a fixed `+10:00` offset, correct only while the range starts outside DST.
- `get_orders.py` re-downloads every order since opening on every run (no incremental fetch),
  and the raw JSON grows ~5 MB a month. Deliberate: a missed or partial run heals itself on the
  next one. Revisit only if it gets slow.
- Manual $0 price overrides at the till carry no discount, so they can't be told apart from
  anything else free. `base_price` shows what the item was worth.

### Tests

`python3 -m pytest`, from the root. Every test builds a small CSV or a few order dicts in
memory, so no credentials and no network. They cover the rules that have actually been wrong:
which lines are redemptions, items not rows, several discounts on one line, refunds not being
sales, and monthly totals summing to `/grounded`. When changing a rule, write the failing test
first.

## Critical domain knowledge (not obvious from the code)

**1. One definition of each rule, in `grounded/order_rows.py`.** The CSV's path, separator,
record types, the two pinned discount names, the giveaway exclusion, and `is_redemption()` /
`redeemed_unit()` all live there. `get_orders.py` writes with them; every reader reads with
them. The rules were once copied into three scripts and drifted. Don't re-define a constant or
re-implement the redemption rule locally: import it.

**2. Items ARE categorised in Square, and categorisation joins on catalog IDs.** An earlier
note claimed 0 of 67 items had a category. That was wrong: it read `item_data.category_id`,
which Square deprecated and which always reads null. The live fields are `reporting_category`
and `categories`; `diagnostics.py coverage` shows 89 of 90 categorised, the exception being
Square's own demo item.

`get_orders.py` therefore categorises by **catalog ID**: line items carry the variation id in
`catalog_object_id`, `build_catalog_lookups()` maps every variation to its Square category, and
`CATEGORY_BUCKET` translates ~24 Square category names into the four buckets this pipeline
reports (`Coffee`, `Drink`, `Food`, `Exclude`). IDs survive renames, so this does not drift. A
Square category with no entry in `CATEGORY_BUCKET` prints a loud warning.

**3. Item names drift, so the name map is only a FALLBACK.** The catalog has
`"Toastie ~ The Reuben"`, orders show `"Reuben Toastie"` and even `"Ruban Toastie"`, and
trailing whitespace appears (`"Soup "`). `ITEM_CATEGORY` is consulted only when the catalog
cannot explain a line, which in practice means items since deleted, such as the June 2026
`Student Meal` / `Student Drink`. Names are `.strip()`ped before lookup. Anything neither
source explains is tagged `"Unmapped"` rather than guessed at.

ID-based categorisation took `Unmapped` from 36.3% of rows to 0.6%. The remainder are line
items with no name at all: custom amounts rung at the till, about $1,700 in total. That is the
floor.

**4. Only the `Paid Forward Redemption` discount is a redemption. `Student Meal` / `Student Drink` are NOT.**
Those $0 items (and `TUSA After Dark - Food/Drink`) were only used on the 17 June 2026 night
event, which TUSA funded. Counting them once made them ~70% of the published figure and made
June look like a boom. Decided September 2026, see
`docs/adr/0001-institution-funded-giveaways-are-not-redemptions.md`. Don't re-add them.

The donation side is the `Pay-It Forward` item (variations `Regular Coffee`, `Meal`) and
`JJ's Personal Pay-it Forward Tracker` (a meal). Donations minus redemptions is **Banked**.

**5. `Student Discount` (20% off) is NOT the redemption mechanism above.** It applies to
normally-priced purchases by enrolled students, unrelated to pay-it-forward. Never merge the
two concepts in aggregation logic.

**6. All Square timestamps are UTC.** Hobart is UTC+10 (AEST) or UTC+11 (AEDT, roughly October
onward). `START_AT` must carry an explicit Hobart offset (e.g. `"2026-06-09T00:00:00+10:00"`),
or the boundary is silently off by 10-11 hours; a 7am order was once missed entirely this way.
Don't hardcode `+10:00` for a range that might cross a DST boundary.

**7. Square APIs are paginated (500 per page via `cursor`).** `get_orders.py` and
`diagnostics.py` loop until `cursor` is absent. Any new Square call needs the same.

**8. Never write `data/api_store.json` directly.** `app/main.py` uses file locking and atomic
writes (temp file, then `os.replace`) to prevent corruption. Scripts change values through the
HTTP admin API at `127.0.0.1:55500` (`grounded/api_client.py`), never on disk.

**9. Top-level URL mounts shadow the `/{handle}` route.** `/styles` and `/scripts` are mounted
as static directories, so they are in `RESERVED_HANDLES` in `app/main.py`. Any new top-level
mount must be added there too.

**10. `/grounded` and `/social-cafe` count orders differently, deliberately.** The impact
counter is charity-only. The trading stats count every order, free ones included, because
staff made the drink either way, but exclude wholly-redeemed orders from the price average
because a donor already paid. Don't "fix" the inconsistency. `CONTEXT.md` defines the terms.

**11. Every Square discount is recorded, but manual $0 overrides still can't be seen.**
`get_orders.py` once kept only `Student Discount` and `Paid Forward Redemption`, so `100%`,
`Half-Price`, `U-Connect Staff` and `Loyalty Card Freebie` lines looked like they simply cost
nothing. Since September 2026 all discounts are written; a line with several shares one row,
joined with `; ` in `discount_name` and `discount_amounts`. Staff sometimes zero a price by
hand with no discount at all, which leaves no marker, but `base_price` shows what it was worth.

## Running things

- `python3 -m pytest` runs the suite: no credentials, no network. Run it after any change to
  `grounded/`.
- **`update_grounded.py` and `update_social_cafe.py` push to the live site when run.** To
  check their output locally, call `aggregate(order_rows.CSV_PATH)` from Python instead of
  running `main()`.
- `get_orders.py` calls the live Square API and needs the credentials in `.env`.
- **To test the whole chain end to end without touching production**, on a dev machine whose
  `.env` has `API_BASE_URL=http://127.0.0.1:55500` and where nothing already listens on that
  port: source `.env`, start `uvicorn app.main:app --host 127.0.0.1 --port 55500` with
  `API_STORE_PATH` pointing at a scratch file, then run `./grounded/daily_update.sh`. Square is
  only read; every push lands in the scratch store. Check the handles with `curl`, then stop
  uvicorn. Never do this on the server, where 55500 *is* production.

## Credentials (`.env`, project root)

```
SQUARE_ACCESS_TOKEN=      # Square production access token
SQUARE_SANDBOX_TOKEN=     # Square sandbox token (testing only, not used by get_orders.py)
SQUARE_LOCATION_ID=       # Grounded Café's Square location ID
API_ADMIN_TOKEN=          # Must match Environment=API_ADMIN_TOKEN in the systemd unit
API_BASE_URL=http://127.0.0.1:55500   # Internal address, not the public domain
```

**Known issue, worth fixing if touching deployment config:** `API_ADMIN_TOKEN` also lives in
plaintext in `/etc/systemd/system/myapi.service` on the server. Acknowledged, not an oversight
to work around silently: flag it if asked to touch auth or secrets handling.

## Style and behaviour

- `get_orders.py` rewrites the CSV in full each run (mode `"w"`, not append). This is
  deliberate: idempotency means a re-run can never double-count.
- Fail loudly (abort, print to `cron.log`) rather than publish incomplete or guessed data.
  `daily_update.sh` aborts before pushing if the Square pull fails, and unknown items become
  `Unmapped` rather than guesses. Keep that posture in new code.

## Agent skills

### Issue tracker

Issues live in this repo's GitHub Issues, managed via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles, each label string equal to its name. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
