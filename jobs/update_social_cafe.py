"""Publish the cafe's trading statistics to the /social-cafe handle.

Deliberately separate from update_grounded.py. That script answers a charity
question ("how many coffees were given away"); this one answers a commercial
one ("how busy are we, and what does an order bring in"). They count orders
differently on purpose, so keeping them apart stops one definition leaking
into the other.

Definitions, agreed with the cafe:

- An ORDER is one unique order_id. Every order counts toward total_orders,
  including the free ones: the ingredients were bought either way.
- A REDEMPTION is a line covered by the Paid Forward Redemption discount, or
  a Student Meal / Student Drink item. Same rule update_grounded.py uses, on
  purpose: there should only ever be one definition of this in the project.
  An order is left out of the price average only when EVERY line in it is a
  redemption, because a donor already paid for it. An order that was free for
  any other reason (a comp, a loyalty freebie, a launch giveaway) stays in and
  drags the average down, which is honest: it cost money and earned none.
- An HOUR is a flat 6.75, the 8:00-14:45 trading window, times the number of
  distinct days that saw at least one order. Both come from the CSV, so
  closures and semester breaks need no maintenance. Evening events are not
  counted as extra hours.
"""

import csv
import datetime as dt
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

import api_client

# Paths are resolved from this file, not the working directory, so these
# scripts behave the same whether cron or a human runs them.
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

load_dotenv(BASE_DIR / ".env")

CSV_PATH = DATA_DIR / "grounded_cafe_orders.csv"
HANDLE = "social-cafe"

# Trading window: 8:00am to 2:45pm. Change this if the shop's hours change.
HOURS_PER_DAY = 6.75

REDEMPTION_ITEMS = {"Student Meal", "Student Drink"}
PAID_FORWARD_DISCOUNT = "Paid Forward Redemption"


def is_redemption(row: dict) -> bool:
    return row.get("item_name") in REDEMPTION_ITEMS or row.get("discount_name") == PAID_FORWARD_DISCOUNT


def read_rows(csv_path: Path):
    """Yield usable rows, skipping any the pipeline could not have written.

    The daily run always produces clean output, so a skip here means someone
    has hand-edited the file. Counting them loudly beats silently averaging
    over junk.
    """
    skipped = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                row["_time"] = dt.datetime.fromisoformat(row["transaction_time"])
                row["_amount"] = float(row["total_amount"] or 0)
            except (ValueError, TypeError):
                skipped += 1
                continue
            yield row

    if skipped:
        print(f"WARNING: skipped {skipped} unparseable row(s) in {csv_path.name}")


def aggregate(csv_path: Path) -> dict:
    orders = defaultdict(list)
    days = set()

    for row in read_rows(csv_path):
        orders[row["order_id"]].append(row)
        days.add(row["_time"].date())

    if not orders:
        raise SystemExit(f"No usable rows in {csv_path}, refusing to publish.")

    counted = {
        order_id: rows
        for order_id, rows in orders.items()
        if not all(is_redemption(row) for row in rows)
    }

    total_revenue = sum(row["_amount"] for rows in orders.values() for row in rows)
    counted_revenue = sum(row["_amount"] for rows in counted.values() for row in rows)

    # Wholly-redeemed orders are $0 by definition, so these should match. If
    # they ever don't, the redemption rule has drifted and the average below
    # would quietly stop meaning what it says.
    if abs(total_revenue - counted_revenue) > 0.005:
        print(
            f"WARNING: ${total_revenue - counted_revenue:.2f} of revenue sits on "
            "orders treated as pure redemptions; average excludes it."
        )

    trading_hours = len(days) * HOURS_PER_DAY

    return {
        "total_orders": len(orders),
        "orders_excluding_redemptions": len(counted),
        "total_revenue": round(total_revenue, 2),
        "trading_days": len(days),
        "hours_per_day": HOURS_PER_DAY,
        # Left unrounded on purpose: the Break-Even Calculator needs the
        # precision, and formatting is the consumer's job.
        "avg_orders_per_hour": len(orders) / trading_hours,
        "avg_price_per_order": counted_revenue / len(counted),
    }


def main():
    values = aggregate(CSV_PATH)
    for key, value in values.items():
        print(f"  {key:30} {value}")

    # If you are testing on your local machine, comment out the line below.
    api_client.push(HANDLE, values)


if __name__ == "__main__":
    main()
