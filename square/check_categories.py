import os

import requests
from dotenv import load_dotenv

_ = load_dotenv()

TOKEN = os.getenv("SQUARE_ACCESS_TOKEN")

URL = "https://connect.squareup.com/v2/catalog/list"
HEADERS = {
    "Square-Version": "2026-05-20",
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}


def check_item_categories():
    params = {"types": "ITEM,CATEGORY"}
    response = requests.get(URL, headers=HEADERS, params=params)
    if response.status_code != 200:
        print(response.status_code, response.text)
    response.raise_for_status()
    data = response.json()

    objects = data.get("objects", [])

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
        category_id = item_data.get("category_id")

        if category_id and category_id in category_names:
            categorised.append((name, category_names[category_id]))
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


if __name__ == "__main__":
    check_item_categories()
