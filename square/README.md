# Grounded Cafe Square Data Pipeline

Scripts for retrieving sales data from Grounded Cafe's Square POS account via the Square Orders API, and producing a CSV suitable for calculating pay-it-forward and student discount statistics.

## Prerequisites

This README lives inside the `square/` subfolder of the `api.dongyi-guo.top` project, alongside all the scripts it describes. Run all commands from within this folder.

- Python 3.9 or later (uses `zoneinfo`, which requires 3.9+)
- A Square **production** access token and a **sandbox** access token, generated from the Square Developer Console
- Install dependencies from `requirements.txt`:

``` bash
pip install -r requirements.txt
```

## 1. Set up your `.env` file

Create a file named `.env` in the same folder as these scripts. Do not commit this file to any Git repository; add it to `.gitignore` if this folder is version controlled.

```
SQUARE_ACCESS_TOKEN=your_production_token_here
SQUARE_SANDBOX_TOKEN=your_sandbox_token_here
SQUARE_LOCATION_ID=your_location_id_here
```

`SQUARE_LOCATION_ID` is not known yet at this point. It's retrieved in Step 2 below, then added to `.env` afterwards.

## 2. Retrieve the Location ID

Run:

``` bash
python3 square/get_locations.py
```

This calls Square's Locations API and prints every location on the account, along with its `id` and `status`. Find the entry corresponding to Grounded Cafe and copy its `id` value into `.env` as `SQUARE_LOCATION_ID`.

**Only needs to be run once**, unless the business adds a new physical location or the existing location is reconfigured in Square.

## 3. Retrieve configured discounts (optional, reference only)

``` bash
python3 square/list_discounts.py
```

Lists every discount defined in the Square Catalog, with its `name`, `id`, and value (percentage or fixed amount). Used to confirm the exact discount names and catalog IDs referenced inside `get_orders.py` (currently `Student Discount (20%)` and `Paid Forward Redemption`).

**Only needs to be re-run if a new discount type is added** or an existing one is renamed in Square, in which case the `STUDENT_DISCOUNT_ID` / `PAID_FORWARD_ID` constants inside `get_orders.py` will need updating to match.

## 4. Check catalog category coverage (optional, diagnostic only)

``` bash
python3 square/check_categories.py
```

Reports how many catalog items have a Square category assigned. As of the last check, Grounded Cafe's Square account has categories defined (e.g. "Hot Drinks", "Toasties / Sandwiches / Muffins") but **none of the 67 items are actually assigned to a category**. Because of this, `get_orders.py` uses a manually maintained lookup dictionary (`ITEM_CATEGORY`) instead of pulling categories automatically.

**Re-run this periodically** to check whether categories have since been assigned in Square. If item counts eventually show full coverage, the manual dictionary in `get_orders.py` can be replaced with an automatic category join instead, which would remove the ongoing maintenance burden described in Step 5.

## 5. Run the main data pull

``` bash
python3 square/get_orders.py
```

This is the core script. It:

1. Queries the Square Orders API (`/v2/orders/search`) for all `COMPLETED` orders from `START_AT` onward, filtered and sorted by `created_at`.
2. Pages through results automatically using Square's `cursor` field, so all matching orders are retrieved, not just the first page.
3. Converts every timestamp from UTC to `Australia/Hobart` local time.
4. Matches each line item's discounts against the tracked discount IDs from Step 3.
5. Categorises each line item as `Coffee`, `Drink`, `Food`, `Exclude`, or `Unmapped`, using the `ITEM_CATEGORY` dictionary.
6. Writes everything to `grounded_cafe_orders.csv` in the same folder, overwriting any previous version of that file completely (the file is not appended to; every run produces a fresh, complete file).

### Output columns

| Column             | Description                                                                      |
| ------------------ | -------------------------------------------------------------------------------- |
| `order_id`         | Square's unique order identifier                                                 |
| `transaction_time` | When the order was created, converted to Hobart local time                       |
| `item_name`        | Item name as it appears on the order (may differ slightly from the catalog name) |
| `quantity`         | Quantity of that item in the order                                               |
| `total_amount`     | Price charged for that item, in dollars                                          |
| `currency`         | Currency code (expected: `AUD`)                                                  |
| `discount_name`    | Name of the tracked discount applied to this item, if any                        |
| `discount_saved`   | Dollar amount saved via that discount                                            |
| `category`         | `Coffee`, `Drink`, `Food`, `Exclude`, or `Unmapped`                              |

### Before trusting a run's output

Open the CSV and check the `category` column for any `Unmapped` rows. These indicate an item name not currently listed in `ITEM_CATEGORY`, either because it's genuinely new on the menu, or because the name on the order doesn't match what's in the dictionary (this has happened before, e.g. `Reuben Toastie` vs `Ruban Toastie` vs `Toastie ~ The Reuben`, all the same item). Add any missing names to the dictionary in `get_orders.py` and re-run.

## 6. Configuration you may need to change

All of the following are defined near the top of `get_orders.py`:

- **`START_AT`**: the earliest date orders are pulled from, in Hobart local time with explicit UTC offset (e.g. `"2026-06-09T00:00:00+10:00"`). No `end_at` is set, so every run always pulls up to the current moment.
- **`STUDENT_DISCOUNT_ID`, `PAID_FORWARD_ID`**: catalog discount IDs from Step 3. Update these if the discounts are ever recreated in Square (which would generate new IDs).
- **`REDEMPTION_ITEMS`**: item names treated as free redemptions (currently `Student Meal`, `Student Drink`, from the hard launch event).
- **`ITEM_CATEGORY`**: the manually maintained name-to-category lookup described in Step 5. This is the main thing that will need occasional updates as the menu changes.

## Notes and known limitations

- **Daylight saving**: `START_AT` uses a fixed `+10:00` offset (AEST). If querying date ranges that cross into daylight saving (roughly October onward), the offset needs to be `+11:00` for those dates, or Hobart's local midnight will be calculated incorrectly.
- **Menu drift**: the cafe's menu is not fixed and item names are not always consistent between the Square Catalog and what appears on individual orders. `ITEM_CATEGORY` requires manual maintenance; there is currently no automated way to categorise new items reliably, since Square's own category feature is not populated on this account (see Step 4).
- **Refunds**: this pipeline reads the Orders API only. If an order is refunded after being pulled, that won't be reflected unless the script is re-run and the order's state has changed accordingly.
- **Square API rate limits are undocumented** by Square directly; there is no fixed published number. In practice, this pipeline's volume (a handful of paginated requests per run) is far below anything likely to trigger throttling. Recommended run frequency is daily rather than more frequent, since the data itself doesn't need to be near-real-time for reporting purposes.

## File summary

| File                  | Purpose                         | Run frequency                     |
| --------------------- | ------------------------------- | --------------------------------- |
| `get_locations.py`    | Get Square location ID          | Once, or if location changes      |
| `list_discounts.py`   | List all configured discounts   | Occasionally, if discounts change |
| `check_categories.py` | Check catalog category coverage | Occasionally, as a diagnostic     |
| `get_orders.py`       | Main data pull and CSV output   | Daily (recommended)               |