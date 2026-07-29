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
        if response.status_code != 200:
            print(f"Error fetching orders: {response.status_code} {response.text}")
            break
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
            "total_amount", "discount_name", "discount_saved", "redemption_flag"
        ])

        for order in all_orders:
            order_id = order.get("id")
            created_at_raw = order.get("created_at")
            created_at_hobart = to_hobart(created_at_raw) if created_at_raw else ""
            uid_to_name = match_discount(order)

            for item in order.get("line_items", []):
                total = item.get("total_money", {}).get("amount", 0)
                item_name = item.get("name")
                is_redemption = item_name in REDEMPTION_ITEMS

                # An item can technically have multiple discounts applied; capture each as its own row.
                applied = item.get("applied_discounts", [])
                tracked_applied = [a for a in applied if a.get("discount_uid") in uid_to_name]

                if not tracked_applied:
                    writer.writerow([
                        order_id, created_at_hobart, item_name, item.get("quantity"),
                        total / 100, "", 0, is_redemption
                    ])
                else:
                    for a in tracked_applied:
                        discount_name = uid_to_name[a.get("discount_uid")]
                        saved = a.get("applied_money", {}).get("amount", 0)
                        writer.writerow([
                            order_id, created_at_hobart, item_name, item.get("quantity"),
                            total / 100, discount_name, saved / 100, is_redemption
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