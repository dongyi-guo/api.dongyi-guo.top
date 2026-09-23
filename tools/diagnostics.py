"""One-off diagnostics for the Grounded Cafe Square pipeline.

Not part of the daily cron run. Use these when setting up credentials or
working out why the pipeline classified something the way it did.

    python3 diagnostics.py locations       # Square location IDs
    python3 diagnostics.py discounts       # catalog discounts and their IDs
    python3 diagnostics.py categories      # catalog categories that exist
    python3 diagnostics.py coverage        # how many items have a category
    python3 diagnostics.py student-share   # student-related share of the CSV
"""

import argparse
import csv
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# Paths are resolved from this file, not the working directory, so these
# scripts behave the same whether cron or a human runs them.
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

load_dotenv(BASE_DIR / ".env")

# The CSV's row format is defined next to the job that writes it.
sys.path.insert(0, str(BASE_DIR / "jobs"))
import order_rows  # noqa: E402

TOKEN = os.getenv("SQUARE_ACCESS_TOKEN")

LOCATIONS_URL = "https://connect.squareup.com/v2/locations"
CATALOG_URL = "https://connect.squareup.com/v2/catalog/list"
HEADERS = {
    "Square-Version": "2026-05-20",
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

CSV_PATH = DATA_DIR / "grounded_cafe_orders.csv"
STUDENT_ITEMS = ("Student Meal", "Student Drink")
STUDENT_DISCOUNT = "Student Discount"


def _get(url, params=None):
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code != 200:
        print(response.status_code, response.text)
    response.raise_for_status()
    return response.json()


def fetch_catalog(types):
    """Fetch catalog objects of the given types, following the cursor.

    The catalog endpoint is paginated the same way the Orders API is, so
    this loops until Square stops handing back a cursor.
    """
    objects = []
    cursor = None

    while True:
        params = {"types": types}
        if cursor:
            params["cursor"] = cursor

        data = _get(CATALOG_URL, params)
        objects.extend(data.get("objects", []))

        cursor = data.get("cursor")
        if not cursor:
            return objects


def locations():
    data = _get(LOCATIONS_URL)

    for location in data.get("locations", []):
        print(f"Name: {location.get('name')}")
        print(f"ID: {location.get('id')}")
        print(f"Status: {location.get('status')}")
        print("---")


def discounts():
    objects = fetch_catalog("DISCOUNT")
    if not objects:
        print("No discount objects found on this account.")
        return

    for obj in objects:
        discount = obj.get("discount_data", {})
        discount_type = discount.get("discount_type")

        if discount_type == "FIXED_PERCENTAGE":
            value = f"{discount.get('percentage')}%"
        elif discount_type == "FIXED_AMOUNT":
            amount = discount.get("amount_money", {}).get("amount", 0)
            currency = discount.get("amount_money", {}).get("currency", "AUD")
            value = f"{amount / 100:.2f} {currency}"
        else:
            value = f"({discount_type})"

        print(f"Name: {discount.get('name')}")
        print(f"ID: {obj.get('id')}")
        print(f"Value: {value}")
        print("---")


def categories():
    objects = fetch_catalog("CATEGORY")
    if not objects:
        print("No categories found on this account.")
        return

    for obj in objects:
        category = obj.get("category_data", {})
        print(f"Name: {category.get('name')}")
        print(f"ID: {obj.get('id')}")
        print("---")


def coverage():
    """Report how many catalog items reference a category.

    Reads `reporting_category`, falling back to the `categories` list. The older
    `category_id` field is deprecated and always reads as null, and checking it
    was why this once reported that no item had a category at all.
    """
    objects = fetch_catalog("ITEM,CATEGORY")

    category_names = {
        obj["id"]: obj.get("category_data", {}).get("name")
        for obj in objects if obj.get("type") == "CATEGORY"
    }

    items = [obj for obj in objects if obj.get("type") == "ITEM"]

    categorised = []
    uncategorised = []

    for obj in items:
        item_data = obj.get("item_data", {})
        name = item_data.get("name")
        reporting = item_data.get("reporting_category") or next(iter(item_data.get("categories") or []), None)
        category = category_names.get(reporting["id"]) if reporting else None

        if category:
            categorised.append((name, category))
        else:
            uncategorised.append(name)

    print(f"Total items: {len(items)}")
    print(f"Categorised: {len(categorised)}")
    print(f"Uncategorised: {len(uncategorised)}")
    print()

    if uncategorised:
        print("=== Items with NO category assigned ===")
        for name in uncategorised:
            print(f"- {name}")
        print()

    print("=== Sample of categorised items (first 15) ===")
    for name, category in categorised[:15]:
        print(f"{name:<40} -> {category}")


def student_share():
    """Share of CSV rows that are student-related.

    Counts both the $0 student catalog items and the 20% Student Discount,
    which are separate mechanisms, so this is a rough volume check only.
    """
    student_related = 0
    total_rows = 0

    try:
        handle = open(CSV_PATH, newline="")
    except FileNotFoundError:
        print(f"{CSV_PATH} not found. Run jobs/get_orders.py first.")
        sys.exit(1)

    with handle as f:
        for row in csv.DictReader(f):
            if not order_rows.is_sale(row):
                continue
            total_rows += 1
            if row["item_name"] in STUDENT_ITEMS or STUDENT_DISCOUNT in order_rows.discounts(row):
                student_related += 1

    if not total_rows:
        print(f"{CSV_PATH} has no rows.")
        return

    print(f"Total rows: {total_rows}")
    print(f"Student-related rows: {student_related}")
    print(f"Proportion: {student_related / total_rows:.1%}")


COMMANDS = {
    "locations": locations,
    "discounts": discounts,
    "categories": categories,
    "coverage": coverage,
    "student-share": student_share,
}

NEEDS_TOKEN = ("locations", "discounts", "categories", "coverage")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("command", choices=sorted(COMMANDS))
    args = parser.parse_args()

    if args.command in NEEDS_TOKEN and not TOKEN:
        print("SQUARE_ACCESS_TOKEN is not set. Check the .env file in the project root.")
        sys.exit(1)

    COMMANDS[args.command]()


if __name__ == "__main__":
    main()
