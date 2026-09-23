import csv
from pathlib import Path

from dotenv import load_dotenv

import api_client
import order_rows

# Paths are resolved from this file, not the working directory, so these
# scripts behave the same whether cron or a human runs them.
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

load_dotenv(BASE_DIR / ".env")

HANDLE = "grounded"

CSV_PATH = DATA_DIR / "grounded_cafe_orders.csv"

PAID_FORWARD_DISCOUNT = "Paid Forward Redemption"
STUDENT_DISCOUNT = "Student Discount"

# $0 items given away at the TUSA-funded night event on 17 June 2026. TUSA
# paid for them, so no donation was drawn down and they are not redemptions:
# see docs/adr/0001-institution-funded-giveaways-are-not-redemptions.md.
# Excluded by name, not left to chance: they currently carry no discount at
# all, so they would slip back in the moment one of them ever did.
EXCLUDED_GIVEAWAY_ITEMS = {"Student Meal", "Student Drink"}


def aggregate(csv_path):
    coffees_paid_forward = 0
    meals_paid_forward = 0
    student_discounts_saved = 0.0

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Refunds and empty orders are in the CSV too; only sales count.
            if not order_rows.is_sale(row):
                continue

            # Names are stripped because live order data carries trailing
            # whitespace the catalog does not.
            if (row.get("item_name") or "").strip() in EXCLUDED_GIVEAWAY_ITEMS:
                continue

            category = row.get("category", "")
            line_discounts = order_rows.discounts(row)

            is_paid_forward = PAID_FORWARD_DISCOUNT in line_discounts

            if is_paid_forward:
                # Count items, not rows. One row can be "2 x Chicken Toastie",
                # and two students ate, so it is two meals paid forward.
                quantity = int(float(row.get("quantity") or 0))

                if category == "Drink" or category == "Coffee":
                    coffees_paid_forward += quantity
                elif category == "Food":
                    meals_paid_forward += quantity
                # Unmapped/Exclude items deliberately not counted here.
                # Check for these in the CSV directly if the totals look off.

            # The student discount's own amount, not discount_saved: a line
            # can carry another discount on top, e.g. "100%".
            student_discounts_saved += line_discounts.get(STUDENT_DISCOUNT, 0.0)

    return {
        "coffees_paid_forward": coffees_paid_forward,
        "meals_paid_forward": meals_paid_forward,
        "student_discounts_saved": f"{student_discounts_saved:.2f}",
    }


def main():
    values = aggregate(CSV_PATH)
    print(f"Aggregated: {values}")

    # If you are testing on your local machine, comment out the line below.
    # Creates the handle on a fresh deployment, updates it after that.
    api_client.push(HANDLE, values)


if __name__ == "__main__":
    main()
