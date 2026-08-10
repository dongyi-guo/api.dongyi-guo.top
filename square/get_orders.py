import os
import csv
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("SQUARE_ACCESS_TOKEN")
LOCATION_ID = os.getenv("SQUARE_LOCATION_ID")

URL = "https://connect.squareup.com/v2/orders/search"
HEADERS = {
    "Square-Version": "2026-05-20",
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Start of range: midnight, 9 June 2026, Hobart time (+10:00 AEST).
# No end_at set deliberately, so this always pulls up to "now" on each run.
START_AT = "2026-06-09T00:00:00+10:00"

OUTPUT_FILE = "grounded_cafe_orders.csv"

# Catalog discount IDs, from list_discounts.py output.
STUDENT_DISCOUNT_ID = "74MGXZC7LS5AFWV63C35D6HS"
PAID_FORWARD_ID = "H7TH6PJXDDAPRJDK7HSB2YKD"

TRACKED_DISCOUNTS = {
    STUDENT_DISCOUNT_ID: "Student Discount",
    PAID_FORWARD_ID: "Paid Forward Redemption",
}

# Items that represent a $0 redemption of a previously paid-forward item,
# not a discount on a normally priced item.
REDEMPTION_ITEMS = {"Student Meal", "Student Drink"}

# Built from actual order data (grounded_cafe_orders.csv), not the catalog listing,
# since item names on orders drift from catalog names over time (typos, renames, spacing).
# Names are normalised (stripped) before lookup - see normalise_item_name().
ITEM_CATEGORY = {
    # Coffee
    "~ Cappuccino ~": "Coffee",
    "Cappuccino": "Coffee",
    "Latte": "Coffee",
    "Flat White": "Coffee",
    "Mocha": "Coffee",
    "Long Black": "Coffee",
    "Espresso": "Coffee",
    "Piccolo": "Coffee",
    "Babycino": "Coffee",
    "Iced Latte": "Coffee",
    "Iced Long Black": "Coffee",
    "Iced Mocha": "Coffee",

    # Drink (non-coffee)
    "Milkshake ~ Vanilla": "Drink",
    "Vanilla Milkshake": "Drink",
    "Chocolate Milkshake": "Drink",
    "Caramel Milkshake": "Drink",
    "Strawberry Milkshake": "Drink",
    "Banana Milkshake": "Drink",
    "Smoothie - Banana": "Drink",
    "Banana Smoothie": "Drink",
    "Smoothie ~ Mango": "Drink",
    "Mango Smoothie": "Drink",
    "Smoothie ~ Mixed Berry": "Drink",
    "Mixed Berry Smoothie": "Drink",
    "Tea ~ English Breakfast": "Drink",
    "English Breakfast": "Drink",
    "English Breakfast Tea": "Drink",
    "Earl Grey": "Drink",
    "Earl Grey Tea": "Drink",
    "Green": "Drink",
    "Green Tea": "Drink",
    "Peppermint": "Drink",
    "Peppermint Tea": "Drink",
    "Hot Chocolate": "Drink",
    "Matcha Latte": "Drink",
    "Chai Latte": "Drink",
    "Dirty Chai": "Drink",
    "Iced Chai Latte": "Drink",
    "Iced Chocolate": "Drink",
    "Iced Matcha": "Drink",
    "Iced Dirty Chai Latte": "Drink",
    "Packaged Protein Smoothie - Chocolate": "Drink",
    "Packaged  Protein Smoothie - Salted Caramel": "Drink",
    "Packaged Protein Smoothie - Salted Caramel": "Drink",
    "Packaged Protein Smoothie - Banana Honey": "Drink",
    "Packaged Protein Smoothie - Mango": "Drink",
    "Packaged Protein Smoothie - Vanilla": "Drink",
    "Packaged Apple Juice": "Drink",
    "TUSA After Dark - Drink": "Drink",
    "Student Drink": "Drink",

    # Food
    "Banana, Date & Walnut Loaf": "Food",
    "Friand": "Food",
    "Daily-Baked Savoury Muffin": "Food",
    "Moroccan Roast Veggie Rice Rolls": "Food",
    "Muffin ~ Egg & Cheese": "Food",
    "Egg & Cheese Muffin": "Food",
    "Toastie ~ The Reuben": "Food",
    "Reuben Toastie": "Food",
    "Ruban Toastie": "Food",  # typo variant of Reuben Toastie, seen in live order data
    "Toastie ~ Pumpkin": "Food",
    "Pumpkin Toastie": "Food",
    "Toastie ~ Chicken": "Food",
    "Chicken Toastie": "Food",
    "Soup": "Food",
    "Yoghurt Cup": "Food",
    "Toastie ~ Ham & Cheese": "Food",
    "Ham & Cheese Toastie": "Food",
    "Ham & Cheese Croissant": "Food",
    "Cookie ~ White Chocolate": "Food",
    "White Chocolate Cookie": "Food",
    "Choc Chip": "Food",
    "Choc Chip Cookie": "Food",
    "Choc-Chip Muffin": "Food",
    "Double Choc Chip Cookie": "Food",
    "Chocolate Brownie": "Food",
    "Biscoff": "Food",
    "Biscoff Cookie": "Food",
    "Nutella": "Food",
    "Nutella Cookie": "Food",
    "Raspberry & White Chocolate": "Food",
    "Beef Sausage Roll": "Food",
    "Beef Sausage Roll (HALAL)": "Food",
    "Beef Sausage Roll (Halal)": "Food",
    "Cheese & Spinach Bites": "Food",
    "Cheesy Balls (Chippas)": "Food",
    "Chippas": "Food",
    "Cheeseburger Pie": "Food",
    "Coconut Butter Chicken": "Food",
    "Curry Bowl": "Food",
    "Miso Mushroom Bowl": "Food",
    "Heat & Eat Meal": "Food",
    "House-Made Loaded Focaccia": "Food",
    "Meat-Lovers Loaded Focaccia": "Food",
    "Croissant": "Food",
    "Plain Croissant": "Food",
    "Basque Cheesecake": "Food",
    "Orange & Almond Cake (GF) (VEGAN)": "Food",
    "Sandwich ~ Egg Salad": "Food",
    "Egg Salad Sandwich": "Food",
    "Salad": "Food",
    "Mixed Berry & Yoghurt Muffin": "Food",
    "Muffin ~ Mixed Berry & Yoghurt": "Food",
    "TUSA After Dark - Food": "Food",
    "Student Meal": "Food",

    # Excluded: placeholder, till-reconciliation, or non-consumable entries
    "Pay-It Forward": "Exclude",
    "Tote Bag": "Exclude",
    "Stickers": "Exclude",
    "Cash Variance": "Exclude",
}


def normalise_item_name(name):
    """Strip whitespace so trailing-space variants (e.g. 'Soup ') still match the dict."""
    return name.strip() if name else name


def match_discount(order):
    """Map each order-level discount uid to its catalog discount name, only for tracked discounts."""
    uid_to_name = {}
    for d in order.get("discounts", []):
        catalog_id = d.get("catalog_object_id")
        if catalog_id in TRACKED_DISCOUNTS:
            uid_to_name[d.get("uid")] = TRACKED_DISCOUNTS[catalog_id]
    return uid_to_name


def to_hobart(utc_timestamp):
    """Convert a Square UTC timestamp (RFC 3339, trailing Z) to Hobart local time."""
    dt_utc = datetime.fromisoformat(utc_timestamp.replace("Z", "+00:00"))
    dt_hobart = dt_utc.astimezone(ZoneInfo("Australia/Hobart"))
    return dt_hobart.isoformat()


def fetch_all_orders():
    all_orders = []
    cursor = None

    while True:
        payload = {
            "location_ids": [LOCATION_ID],
            "query": {
                "filter": {
                    "date_time_filter": {
                        "created_at": {
                            "start_at": START_AT
                        }
                    },
                    "state_filter": {"states": ["COMPLETED"]}
                },
                "sort": {"sort_field": "CREATED_AT", "sort_order": "ASC"}
            },
            "limit": 500
        }
        if cursor:
            payload["cursor"] = cursor

        response = requests.post(URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        data = response.json()

        all_orders.extend(data.get("orders", []))
        cursor = data.get("cursor")

        if not cursor:
            break

    return all_orders


def write_csv(all_orders):
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "order_id", "transaction_time", "item_name", "quantity",
            "total_amount", "currency", "discount_name", "discount_saved", "category"
        ])

        for order in all_orders:
            order_id = order.get("id")
            created_at_raw = order.get("created_at")
            created_at_hobart = to_hobart(created_at_raw) if created_at_raw else ""
            uid_to_name = match_discount(order)

            for item in order.get("line_items", []):
                total = item.get("total_money", {}).get("amount", 0)
                currency = item.get("total_money", {}).get("currency", "AUD")
                item_name = item.get("name")
                category = ITEM_CATEGORY.get(normalise_item_name(item_name), "Unmapped")

                # An item can technically have multiple discounts applied; capture each as its own row.
                applied = item.get("applied_discounts", [])
                tracked_applied = [a for a in applied if a.get("discount_uid") in uid_to_name]

                if not tracked_applied:
                    writer.writerow([
                        order_id, created_at_hobart, item_name, item.get("quantity"),
                        total / 100, currency, "", 0, category
                    ])
                else:
                    for a in tracked_applied:
                        discount_name = uid_to_name[a.get("discount_uid")]
                        saved = a.get("applied_money", {}).get("amount", 0)
                        writer.writerow([
                            order_id, created_at_hobart, item_name, item.get("quantity"),
                            total / 100, currency, discount_name, saved / 100, category
                        ])


def main():
    if not TOKEN or not LOCATION_ID:
        raise SystemExit("Missing SQUARE_ACCESS_TOKEN or SQUARE_LOCATION_ID in .env")

    orders = fetch_all_orders()
    print(f"Total orders retrieved: {len(orders)}")

    write_csv(orders)
    print(f"Wrote {len(orders)} orders to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()