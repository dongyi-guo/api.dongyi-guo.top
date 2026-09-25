"""Publish the three impact figures to the /grounded handle.

Charity only: coffees and meals redeemed, and money saved by the student
discount. The counting rules live in order_rows.py, shared with the monthly
report, so the two cannot disagree.
"""

import csv

from dotenv import load_dotenv

import api_client
import order_rows

load_dotenv(order_rows.BASE_DIR / ".env")

HANDLE = "grounded"


def aggregate(csv_path):
    paid_forward = {"coffees": 0, "meals": 0}
    student_discounts_saved = 0.0

    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            # Refunds and empty orders are in the CSV too; only sales count.
            if not order_rows.is_sale(row):
                continue

            unit = order_rows.redeemed_unit(row)
            if unit:
                paid_forward[unit] += order_rows.quantity(row)

            # The student discount's own amount, not discount_saved: a line
            # can carry another discount on top, e.g. "100%".
            student_discounts_saved += order_rows.discounts(row).get(
                order_rows.STUDENT_DISCOUNT, 0.0
            )

    return {
        "coffees_paid_forward": paid_forward["coffees"],
        "meals_paid_forward": paid_forward["meals"],
        "student_discounts_saved": f"{student_discounts_saved:.2f}",
    }


def main():
    values = aggregate(order_rows.CSV_PATH)
    print(f"Aggregated: {values}")

    # If you are testing on your local machine, comment out the line below.
    # Creates the handle on a fresh deployment, updates it after that.
    api_client.push(HANDLE, values)


if __name__ == "__main__":
    main()
