# Grounded Cafe Square Data Pipeline

This folder contains the scripts used to pull Grounded Cafe's Square order data, normalise it into a clean CSV, and publish the aggregated impact stats to the API service.

The project now includes a small set of related scripts for discovery, data export, validation, and automation. The main flow is:

1. Pull the relevant orders from Square
2. Convert and classify the line items
3. Write a CSV for downstream analysis
4. Aggregate the key totals
5. Push those totals to the API handle used by the Grounded site

## Scripts in this folder

- `get_orders.py` — main data pull script. Queries Square for completed orders, paginates through all results, matches tracked discounts, categorises items, and writes `grounded_cafe_orders.csv`.
- `update_grounded.py` — reads the generated CSV and pushes the aggregated values to the `grounded` handle on the API service.
- `daily_update.sh` — wrapper script used by cron. Runs the order pull and then the Grounded update in sequence, aborting if the Square data fetch fails.
- `get_locations.py` — retrieves the Square location list so the correct `SQUARE_LOCATION_ID` can be identified.
- `list_discounts.py` — lists configured discounts from the Square catalog so you can confirm the tracked discount IDs used in the pipeline.
- `list_categories.py` — lists any catalog categories currently configured in Square.
- `check_categories.py` — checks whether items in the Square catalog are assigned to categories; useful for diagnosing why the pipeline uses a manual item-to-category map.
- `calc_portion_discounts.py` — small diagnostic script for calculating how many rows are student-related and what proportion of the CSV they represent.

## Prerequisites

Run commands from within this `square/` folder.

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

Create a `.env` file in this folder with values like:

```env
SQUARE_ACCESS_TOKEN=your_production_token_here
SQUARE_SANDBOX_TOKEN=your_sandbox_token_here
SQUARE_LOCATION_ID=your_location_id_here
API_ADMIN_TOKEN=your_api_admin_token_here
API_BASE_URL=http://127.0.0.1:55500
```

`SQUARE_LOCATION_ID` is usually discovered first using `get_locations.py`.

## Typical setup flow

### 1. Find the Square location ID

```bash
python3 get_locations.py
```

This prints the list of locations on the account. Copy the Grounded Cafe location ID to `SQUARE_LOCATION_ID` in `.env`.

### 2. Check the configured discounts

```bash
python3 list_discounts.py
```

Use this to confirm the exact discount IDs and names used by the pipeline, especially the tracked values in `get_orders.py`.

### 3. Check catalog categories

```bash
python3 list_categories.py
python3 check_categories.py
```

These are diagnostics. If Square item categories are not populated, the pipeline relies on the manual `ITEM_CATEGORY` lookup inside `get_orders.py`.

### 4. Run the main data pull

```bash
python3 get_orders.py
```

This script:

- calls the Square Orders Search API
- filters for `COMPLETED` orders from `START_AT` onward
- paginates through all matching results using the `cursor` field
- converts timestamps from UTC to `Australia/Hobart` time
- matches tracked discounts such as `Student Discount` and `Paid Forward Redemption`
- normalises and classifies item names like `Coffee`, `Drink`, `Food`, `Exclude`, or `Unmapped`
- writes the results to `grounded_cafe_orders.csv`

The CSV is overwritten on each run, rather than appended to.

### 5. Aggregate and push the numbers

```bash
python3 update_grounded.py
```

This reads the CSV and pushes the aggregated values to the API service with the admin token. In production, the intended entry point is normally `daily_update.sh`.

### 6. The scheduled cron job

```bash
./daily_update.sh
```

This is the script used to automate the daily run. It does the following:

```bash
python3 get_orders.py
python3 update_grounded.py
```

It exits early if the order pull fails so stale numbers are not published.

## Output file

`grounded_cafe_orders.csv` is the main output of the pipeline. It contains one row per discounted or non-discounted line item, with fields such as:

- `order_id`
- `transaction_time`
- `item_name`
- `quantity`
- `total_amount`
- `currency`
- `discount_name`
- `discount_saved`
- `category`

## Configuration notes

The key settings live near the top of `get_orders.py`:

- `START_AT` — the earliest order timestamp to include, using Hobart local time with an explicit offset
- `STUDENT_DISCOUNT_ID` and `PAID_FORWARD_ID` — tracked discount IDs for the key discount types
- `REDEMPTION_ITEMS` — item names treated as pay-it-forward redemptions
- `ITEM_CATEGORY` — manual category map used to classify menu items consistently

## Known limitations

- The item names on orders may drift from the catalog names, so manual maintenance of `ITEM_CATEGORY` is sometimes required.
- `get_orders.py` only reads completed orders; refunded or cancelled orders are not treated specially unless the API state changes and the script is re-run.
- The pipeline relies on a fixed `+10:00` offset for `START_AT` unless the date range crosses daylight saving changes.

## File summary

| File | Purpose | Typical usage |
| --- | --- | --- |
| `get_orders.py` | Core order extraction and CSV generation | Daily / scheduled |
| `update_grounded.py` | Aggregates CSV output and pushes values to the API | Daily / scheduled |
| `daily_update.sh` | Wrapper for the full automated run | Cron |
| `get_locations.py` | Retrieves Square Location IDs | Setup / one-time |
| `list_discounts.py` | Lists catalog discounts | Setup / troubleshooting |
| `list_categories.py` | Lists catalog categories | Setup / troubleshooting |
| `check_categories.py` | Checks category coverage | Diagnostics |
| `calc_portion_discounts.py` | Quick student-related ratio check | Diagnostics |
| `.env` | Storage for Square and API credentials | Runtime |
