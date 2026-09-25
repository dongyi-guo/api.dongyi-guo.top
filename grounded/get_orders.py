import os
import csv
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

import order_rows
from order_rows import SALE, RETURN, EMPTY

# The CSV's location and format are shared with every script that reads it,
# so they are defined in order_rows.py rather than here.
DATA_DIR = order_rows.DATA_DIR

load_dotenv(order_rows.BASE_DIR / ".env")

TOKEN = os.getenv("SQUARE_ACCESS_TOKEN")
LOCATION_ID = os.getenv("SQUARE_LOCATION_ID")

URL = "https://connect.squareup.com/v2/orders/search"
CATALOG_URL = "https://connect.squareup.com/v2/catalog/list"
HEADERS = {
    "Square-Version": "2026-05-20",
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Start of range: midnight, 9 June 2026, Hobart time (+10:00 AEST).
# No end_at set deliberately, so this always pulls up to "now" on each run.
START_AT = "2026-06-09T00:00:00+10:00"

OUTPUT_FILE = order_rows.CSV_PATH
# Every order exactly as Square returned it. The CSV is a flattened view and
# will always leave something out; this is what to reach for when it does.
RAW_OUTPUT_FILE = DATA_DIR / "grounded_cafe_orders_raw.json"

# Catalog discount IDs, from "diagnostics.py discounts" output.
STUDENT_DISCOUNT_ID = "74MGXZC7LS5AFWV63C35D6HS"
PAID_FORWARD_ID = "H7TH6PJXDDAPRJDK7HSB2YKD"

# EVERY discount is written to the CSV. These two are pinned to a fixed name
# because the aggregation scripts match on them, and the till has shown the
# student discount as both "Student Discount" and "Student Discount (20%)".
# Any other discount is written under its current catalog name, or, for an
# ad-hoc discount typed in at the till, the name on the order.
PINNED_DISCOUNT_NAMES = {
    STUDENT_DISCOUNT_ID: order_rows.STUDENT_DISCOUNT,
    PAID_FORWARD_ID: order_rows.PAID_FORWARD_DISCOUNT,
}

# Square's own categories, mapped to the four buckets this pipeline reports in.
# This is the PRIMARY source of an item's category: it is keyed on catalog IDs,
# which don't change when somebody renames a product. Only ~25 category names to
# maintain, against 120+ item names that drift constantly.
#
# "Coffee" and "Drink" are both counted as drinks downstream, so the split between
# them is presentational only. "Exclude" means not a consumable sale.
CATEGORY_BUCKET = {
    "Hot Drinks": "Coffee",
    "Iced Drinks": "Coffee",
    "Teas": "Drink",
    "Milkshakes": "Drink",
    "Smoothies": "Drink",
    "Mocktails": "Drink",
    "Pre-Packaged Drinks": "Drink",
    "Produced Drinks": "Drink",
    "Drinks Menu": "Drink",
    "Toasties": "Food",
    "Pies": "Food",
    "Sweet Muffins": "Food",
    "Savoury Muffins": "Food",
    "Croissants": "Food",
    "Petite Fours": "Food",
    "Cups": "Food",
    "Parcels": "Food",
    "Daily Specials": "Food",
    "Fridge Cabinet Food": "Food",
    "HotBox Cabinet Food": "Food",
    "Above Cabinets Displays": "Food",
    "Loaf / Loaves": "Food",
    "Merchandise": "Exclude",
    "Pay it forward": "Exclude",
}

# FALLBACK ONLY, for line items the catalog can no longer explain: products that
# have since been deleted or archived, such as the Student Meal / Student Drink
# items from the June 2026 launch. Historical orders still name them, but they no
# longer exist in the catalog, so there is no ID to join on. Built from actual
# order data, and names are normalised (stripped) before lookup.
ITEM_CATEGORY = {
    # Retired items: sold historically, no longer in the catalog, so no ID to join on.
    "Fruit Cup": "Food",
    "Salad of the Day": "Food",
    "Catering": "Food",
    "Turmeric Latte": "Coffee",

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


def fetch_catalog(types):
    """Fetch catalog objects of the given types, following the cursor."""
    objects = []
    cursor = None

    while True:
        params = {"types": types}
        if cursor:
            params["cursor"] = cursor
        response = requests.get(CATALOG_URL, headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        objects.extend(data.get("objects", []))
        cursor = data.get("cursor")
        if not cursor:
            return objects


def build_catalog_lookups():
    """Read the catalog once, returning what the CSV needs from it.

    - variation id -> one of our buckets, via Square's category
    - variation id -> Square's own category name, written to the CSV as-is
    - discount id  -> the discount's current catalog name

    Order line items carry the variation id in catalog_object_id, so this is what
    lets us categorise by ID instead of by name. Note the category lives on
    `reporting_category` / `categories`; the older `category_id` field is
    deprecated and reads as null, which is why this once looked like no item had
    a category at all.
    """
    objects = fetch_catalog("ITEM,CATEGORY,DISCOUNT")
    # Always a string, never None: an unnamed category reads as "", which
    # simply matches nothing in CATEGORY_BUCKET.
    category_names = {
        obj["id"]: (obj.get("category_data", {}).get("name") or "").strip()
        for obj in objects if obj.get("type") == "CATEGORY"
    }
    discount_names = {
        obj["id"]: (obj.get("discount_data", {}).get("name") or "").strip()
        for obj in objects if obj.get("type") == "DISCOUNT"
    }

    buckets = {}
    square_categories = {}
    unknown = set()

    for obj in objects:
        if obj.get("type") != "ITEM":
            continue
        data = obj.get("item_data", {})
        reporting = data.get("reporting_category") or next(iter(data.get("categories") or []), None)
        name = category_names.get(reporting["id"], "") if reporting else ""
        bucket = CATEGORY_BUCKET.get(name)

        if name and bucket is None:
            unknown.add(name)

        for variation in data.get("variations", []):
            if name:
                square_categories[variation["id"]] = name
            if bucket:
                buckets[variation["id"]] = bucket

    if unknown:
        print(f"WARNING: Square categories with no bucket in CATEGORY_BUCKET: {sorted(unknown)}")
        print("         Their items fall back to the name map, or land as Unmapped.")

    print(f"Catalog: {len(buckets)} variations categorised from Square, "
          f"{len(discount_names)} discounts")
    return buckets, square_categories, discount_names


def categorise(item, variation_categories):
    """Category by catalog ID first, falling back to the name map, then Unmapped."""
    by_id = variation_categories.get(item.get("catalog_object_id"))
    if by_id:
        return by_id
    return ITEM_CATEGORY.get(normalise_item_name(item.get("name")), "Unmapped")


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

    # for i, order in enumerate(all_orders, start=1):
    #     has_pay_it_forward = any(
    #         item.get("name") == "Pay-It Forward"
    #         for item in order.get("line_items", [])
    #     )
    #     if has_pay_it_forward:
    #         print(f"\nOrder {i} attributes:")
    #         for key, value in order.items():
    #             print(f"  {key}: {value}")

    return all_orders


# The first nine columns are the original ones, minus currency. Everything
# after them was added so that no useful field Square returns is lost.
CSV_COLUMNS = [
    "order_id", "transaction_time", "item_name", "quantity", "variation",
    "total_amount", "discount_name", "discount_saved", "category",
    # Line detail
    "record_type", "line_uid", "catalog_object_id", "square_category",
    "base_price", "variation_total_price", "gross_sales", "total_discount",
    "total_tax", "card_surcharge", "discount_amounts", "discount_ids",
    "modifiers", "note",
    # Order context, repeated on every line of the order
    "closed_at", "tender_types",
    # Returns only: which sale is being refunded, and why
    "source_order_id", "source_line_uid", "refund_reason",
]

def dollars(obj, key, sign=1):
    """A Square money field in dollars. Square stores cents as integers."""
    return sign * (obj.get(key) or {}).get("amount", 0) / 100


def join(values):
    return order_rows.SEPARATOR.join(str(v) for v in values)


def describe_modifiers(modifiers):
    """e.g. 'Oat (+0.50); Dine-In'. Free modifiers are named without a price."""
    parts = []
    for m in modifiers or []:
        price = (m.get("total_price_money") or m.get("base_price_money") or {}).get("amount", 0)
        name = (m.get("name") or "").strip()
        parts.append(f"{name} (+{price / 100:.2f})" if price else name)
    return join(parts)


def line_discounts(line, uid_to_discount):
    """(names, amounts, catalog ids) for every discount applied to one line.

    A line can carry several discounts at once, e.g. "100%" on top of
    "Student Discount". They share one row, in the same order across the
    three columns, rather than duplicating the line once per discount.
    """
    names, amounts, ids = [], [], []
    for a in line.get("applied_discounts", []):
        name, catalog_id = uid_to_discount.get(a.get("discount_uid"), ("Unknown discount", ""))
        names.append(name)
        amounts.append(f"{a.get('applied_money', {}).get('amount', 0) / 100:.2f}")
        ids.append(catalog_id or "")
    return names, amounts, ids


def discount_map(discounts, catalog_discount_names):
    """uid -> (display name, catalog id) for an order's or a return's discounts."""
    mapped = {}
    for d in discounts or []:
        catalog_id = d.get("catalog_object_id")
        name = (
            PINNED_DISCOUNT_NAMES.get(catalog_id)
            or catalog_discount_names.get(catalog_id)
            or (d.get("name") or "").strip()
            or "Unnamed discount"
        )
        mapped[d.get("uid")] = (name, catalog_id)
    return mapped


def order_context(order):
    return {
        "order_id": order.get("id"),
        "transaction_time": to_hobart(order["created_at"]) if order.get("created_at") else "",
        "closed_at": to_hobart(order["closed_at"]) if order.get("closed_at") else "",
        "tender_types": join(t.get("type") for t in order.get("tenders", [])),
        "refund_reason": join(r.get("reason", "") for r in order.get("refunds", [])),
    }


def line_row(line, context, record_type, uid_to_discount, lookups, sign=1):
    """One CSV row for a sale line (sign 1) or a returned line (sign -1).

    Returns are written negative, quantity and money both, so summing a column
    across sales and returns gives the net figure.
    """
    buckets, square_categories = lookups
    names, amounts, ids = line_discounts(line, uid_to_discount)
    quantity = float(line.get("quantity") or 0) * sign

    return {
        **context,
        "item_name": line.get("name"),
        "quantity": f"{quantity:g}",
        "variation": line.get("variation_name"),
        "total_amount": dollars(line, "total_money", sign),
        "discount_name": join(names),
        "discount_saved": dollars(line, "total_discount_money", sign),
        "category": categorise(line, buckets),
        "record_type": record_type,
        "line_uid": line.get("uid"),
        "catalog_object_id": line.get("catalog_object_id", ""),
        "square_category": square_categories.get(line.get("catalog_object_id"), ""),
        "base_price": dollars(line, "base_price_money"),
        "variation_total_price": dollars(line, "variation_total_price_money", sign),
        "gross_sales": dollars(line, "gross_sales_money", sign) or dollars(line, "gross_return_money", sign),
        "total_discount": dollars(line, "total_discount_money", sign),
        "total_tax": dollars(line, "total_tax_money", sign),
        "card_surcharge": dollars(line, "total_service_charge_money", sign),
        "discount_amounts": join(amounts),
        "discount_ids": join(ids),
        "modifiers": describe_modifiers(line.get("modifiers") or line.get("return_modifiers")),
        "note": (line.get("note") or "").strip(),
    }


def build_rows(all_orders, lookups, catalog_discount_names):
    for order in all_orders:
        context = order_context(order)
        uid_to_discount = discount_map(order.get("discounts"), catalog_discount_names)
        line_items = order.get("line_items", [])

        for line in line_items:
            yield line_row(line, context, SALE, uid_to_discount, lookups)

        # A refund arrives as its own order with no line_items, only returns.
        # These used to be dropped, which left refunded sales counted as sales.
        for ret in order.get("returns", []):
            return_discounts = discount_map(ret.get("return_discounts"), catalog_discount_names)
            for line in ret.get("return_line_items", []):
                row = line_row(line, context, RETURN, return_discounts, lookups, sign=-1)
                row["source_order_id"] = ret.get("source_order_id", "")
                row["source_line_uid"] = line.get("source_line_item_uid", "")
                yield row

        # An order with neither, e.g. opening the cash drawer (a NO_SALE
        # tender). Written so the row count matches Square, never counted.
        if not line_items and not order.get("returns"):
            yield {**context, "record_type": EMPTY, "quantity": "0", "total_amount": 0}


def write_csv(all_orders, lookups, catalog_discount_names):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    counts = {SALE: 0, RETURN: 0, EMPTY: 0}

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, restval="")
        writer.writeheader()
        for row in build_rows(all_orders, lookups, catalog_discount_names):
            counts[row["record_type"]] += 1
            writer.writerow(row)

    return counts


def write_raw(all_orders):
    """Snapshot every order untouched, so the CSV is never the only record."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp = RAW_OUTPUT_FILE.with_suffix(".json.tmp")
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(all_orders, f)
    os.replace(temp, RAW_OUTPUT_FILE)


def main():
    if not TOKEN or not LOCATION_ID:
        raise SystemExit("Missing SQUARE_ACCESS_TOKEN or SQUARE_LOCATION_ID in .env")

    buckets, square_categories, discount_names = build_catalog_lookups()

    orders = fetch_all_orders()
    print(f"Total orders retrieved: {len(orders)}")

    # Printed in the order the work happens, so a run that dies halfway says
    # where it got to. The last line is the last step, not a hang.
    write_raw(orders)
    print(f"Raw snapshot written to {RAW_OUTPUT_FILE}")

    counts = write_csv(orders, (buckets, square_categories), discount_names)
    print(f"Wrote {len(orders)} orders to {OUTPUT_FILE}: "
          f"{counts[SALE]} sale lines, {counts[RETURN]} returned lines, "
          f"{counts[EMPTY]} orders with no items")
    print("Done.")


if __name__ == "__main__":
    main()
