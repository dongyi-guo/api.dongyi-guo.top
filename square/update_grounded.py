import csv
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_ADMIN_TOKEN = os.getenv("API_ADMIN_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:55500")

CSV_PATH = "grounded_cafe_orders.csv"

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


def push_to_api(values: dict):
    if not API_ADMIN_TOKEN:
        raise SystemExit("Missing API_ADMIN_TOKEN in .env")

    headers = {
        "X-Admin-Token": API_ADMIN_TOKEN,
        "Content-Type": "application/json",
    }

    for key, value in values.items():
        url = f"{API_BASE_URL}/_admin/api/handles/grounded/attributes/{key}"
        response = requests.put(url, headers=headers, json={"value": value})
        if response.status_code >= 400:
            print(f"Failed to update {key}: {response.status_code} {response.text}")
        else:
            print(f"Updated {key} = {value}")


def main():
    values = aggregate(CSV_PATH)
    print(f"Aggregated: {values}")
    push_to_api(values)


if __name__ == "__main__":
    main()