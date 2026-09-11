import csv
from pathlib import Path

from dotenv import load_dotenv

import api_client

# Paths are resolved from this file, not the working directory, so these
# scripts behave the same whether cron or a human runs them.
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

load_dotenv(BASE_DIR / ".env")

HANDLE = "grounded"

CSV_PATH = DATA_DIR / "grounded_cafe_orders.csv"

REDEMPTION_ITEMS = {"Student Meal", "Student Drink"}
PAID_FORWARD_DISCOUNT = "Paid Forward Redemption"
STUDENT_DISCOUNT = "Student Discount"


def aggregate(csv_path):
    coffees_paid_forward = 0
    meals_paid_forward = 0
    student_discounts_saved = 0.0

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item_name = row.get("item_name", "")
            category = row.get("category", "")
            discount_name = row.get("discount_name", "")
            discount_saved = float(row.get("discount_saved") or 0)

            is_paid_forward = item_name in REDEMPTION_ITEMS or discount_name == PAID_FORWARD_DISCOUNT

            if is_paid_forward:
                if category == "Drink" or category == "Coffee":
                    coffees_paid_forward += 1
                elif category == "Food":
                    meals_paid_forward += 1
                # Unmapped/Exclude items deliberately not counted here.
                # Check for these in the CSV directly if the totals look off.

            if discount_name == STUDENT_DISCOUNT:
                student_discounts_saved += discount_saved

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
