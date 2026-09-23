# Grounded Cafe Square Data Pipeline

This folder holds the scheduled half of the Grounded Cafe pipeline: pulling Square order
data, normalising it into a clean CSV, and publishing the aggregated impact stats to the
API service. Everything here runs from cron.

The manual setup and troubleshooting commands live in `tools/diagnostics.py`, documented
in `tools/README.md`.

The main flow is:

1. Pull the relevant orders from Square
2. Convert and classify the line items
3. Write a CSV for downstream analysis
4. Aggregate the key totals
5. Push those totals to the API handle used by the Grounded site

## Scripts in this folder

- `get_orders.py` — main data pull script. Queries Square for completed orders, paginates through all results, records every discount and refund, categorises items, and writes `data/grounded_cafe_orders.csv` plus a raw JSON snapshot.
- `update_grounded.py` — reads the generated CSV and pushes the aggregated values to the `grounded` handle on the API service.
- `update_social_cafe.py` — reads the same CSV for trading statistics (orders per hour, price per order and the totals behind them) and pushes them to the `social-cafe` handle. Kept separate from `update_grounded.py` because the two count orders differently: see `CONTEXT.md`.
- `api_client.py` — shared push helper used by both, so create-if-missing lives in one place.
- `order_rows.py` — shared CSV reader helpers. Every script that reads the CSV uses these to skip non-sale rows and to read a line's discounts.
- `update_grounded_monthly.py` — reads the same CSV and writes `data/grounded_monthly_summary.csv`, a month-by-month breakdown of what was purchased, redeemed and banked. Pushes nothing anywhere. Run monthly by cron, separately from the daily chain. Takes `--month YYYY-MM` for a single month and `--cumulative` for totals since opening; the CSV always holds both views regardless.
- `daily_update.sh` — wrapper script used by cron. Runs the order pull and then the Grounded update in sequence, aborting if the Square data fetch fails.

## Prerequisites

Each script resolves its paths from its own file location, so you can run them from any
directory. The examples below assume the project root.

- Python 3.9 or later
- A Square production access token
- A Square sandbox token (for testing/diagnostics)
- The correct `SQUARE_LOCATION_ID` for Grounded Cafe
- The API admin token and base URL required by `update_grounded.py`

Install Python dependencies from the project root:

```bash
pip install -r requirements.txt
```

## Environment setup

Create a `.env` file in the project root with values like:

```env
SQUARE_ACCESS_TOKEN=your_production_token_here
SQUARE_SANDBOX_TOKEN=your_sandbox_token_here
SQUARE_LOCATION_ID=your_location_id_here
API_ADMIN_TOKEN=your_api_admin_token_here
API_BASE_URL=http://127.0.0.1:55500
```

`SQUARE_LOCATION_ID` is usually discovered first using `python3 tools/diagnostics.py locations`.

## Typical flow

First-time setup (finding the location ID, confirming discount IDs, checking catalog
categories) is done with `tools/diagnostics.py`. See `tools/README.md`.

### 1. Run the main data pull

```bash
python3 jobs/get_orders.py
```

This script:

- calls the Square Orders Search API
- filters for `COMPLETED` orders from `START_AT` onward
- paginates through all matching results using the `cursor` field
- converts timestamps from UTC to `Australia/Hobart` time
- matches tracked discounts such as `Student Discount` and `Paid Forward Redemption`
- normalises and classifies item names like `Coffee`, `Drink`, `Food`, `Exclude`, or `Unmapped`
- writes the results to `data/grounded_cafe_orders.csv`

The CSV is overwritten on each run, rather than appended to.

### 2. Aggregate and push the numbers

```bash
python3 jobs/update_grounded.py
python3 jobs/update_social_cafe.py
```

This reads the CSV and pushes the aggregated values to the API service with the admin token. In production, the intended entry point is normally `daily_update.sh`.

### 3. The scheduled cron job

```bash
./jobs/daily_update.sh
```

This is the script used to automate the daily run. It does the following:

```bash
python3 jobs/get_orders.py
python3 jobs/update_grounded.py
python3 jobs/update_social_cafe.py
```

It exits early if the order pull fails so stale numbers are not published.

## Output files

`data/grounded_cafe_orders.csv` has **one row per line item**, never duplicated. The first nine
columns are the original ones:

`order_id`, `transaction_time`, `item_name`, `quantity`, `variation`, `total_amount`,
`discount_name`, `discount_saved`, `category`

After them come the fields needed to explain a line: `record_type`, `line_uid`,
`catalog_object_id`, raw `square_category`, `base_price`, `variation_total_price`,
`gross_sales`, `total_discount`, `total_tax`, `card_surcharge`, `discount_amounts`,
`discount_ids`, `modifiers`, `note`, plus the order's `closed_at` and `tender_types`. Refund
rows also carry `source_order_id`, `source_line_uid` and `refund_reason`.

Three things to know before reading it:

- **`record_type`** is `SALE`, `RETURN` or `EMPTY`. Refunds are written as negative rows, and
  orders with no items (e.g. a cash-drawer `NO_SALE`) as `EMPTY`. Only `SALE` rows are sales.
- **Every discount is recorded**, not a tracked subset. If a line has several, they share one
  row: `discount_name` = `Student Discount; 100%` and `discount_amounts` = `0.90; 3.60`, in
  the same order. `discount_saved` is the line's **total** discount, not any one discount's.
- Read rows through `order_rows.py` (`is_sale`, `discounts`) rather than parsing these columns
  by hand.

`data/grounded_cafe_orders_raw.json` is every order exactly as Square returned it. Reach for it
when the CSV doesn't have a field you need.

`data/grounded_monthly_summary.csv` is written by `update_grounded_monthly.py`, one row per
calendar month, for reporting rather than for the website. Each figure appears twice: once for
the month alone, and once with a `_total` suffix for the running total since opening. It keeps
three things apart that have been confused before:

- **purchased** — coffees and meals the public bought for a stranger (money in)
- **redeemed** — coffees and meals handed over free to a student (an item out)
- **banked** — purchased minus redeemed since opening, i.e. what is still waiting to be
  claimed. Always a running total, because a coffee bought in June can be claimed in August

It also carries `student_discounts_saved` alongside `all_discounts_saved`. They are not the
same: the second includes `100%`, `Half-Price`, `U-Connect Staff` and `Loyalty Card Freebie`,
which are not student savings. A figure once published as "saved in student discounts" was
actually the second one.

Items are counted by **quantity**, not by row, because one row can be `2 x Chicken Toastie`.
The `Student Meal` / `Student Drink` giveaway items are never redemptions anywhere in this
pipeline; they are reported in `excluded_giveaway_items` so the exclusion stays visible.

## Configuration notes

The key settings live near the top of `get_orders.py`:

- `START_AT` — the earliest order timestamp to include, using Hobart local time with an explicit offset
- `STUDENT_DISCOUNT_ID` and `PAID_FORWARD_ID` — discounts pinned to a fixed name in the CSV, because the aggregation scripts match on them. All other discounts are recorded under their catalog name
- `CATEGORY_BUCKET` — maps Square categories to our four buckets; the primary categorisation
- `ITEM_CATEGORY` — fallback name map for items no longer in the catalog

## Known limitations

- The item names on orders may drift from the catalog names, so manual maintenance of `ITEM_CATEGORY` is sometimes required.
- `get_orders.py` only reads completed orders. Refunds are recorded as `RETURN` rows, but the aggregation scripts don't net them off yet; they count sales only, as they always have. `update_grounded_monthly.py`'s `all_discounts_saved` is therefore sales only too, and will differ slightly from a Square dashboard total that includes refunded lines.
- The pipeline relies on a fixed `+10:00` offset for `START_AT` unless the date range crosses daylight saving changes.

## File summary

| File | Purpose | Typical usage |
| --- | --- | --- |
| `get_orders.py` | Core order extraction and CSV generation | Daily / scheduled |
| `update_grounded.py` | Aggregates CSV output and pushes values to the API | Daily / scheduled |
| `daily_update.sh` | Wrapper for the full automated run | Cron |
