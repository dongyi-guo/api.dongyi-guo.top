import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("SQUARE_ACCESS_TOKEN")

URL = "https://connect.squareup.com/v2/catalog/list"
HEADERS = {
    "Square-Version": "2026-05-20",
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}


def list_discounts():
    params = {"types": "DISCOUNT"}
    response = requests.get(URL, headers=HEADERS, params=params)
    response.raise_for_status()
    data = response.json()

    objects = data.get("objects", [])
    if not objects:
        print("No discount objects found on this account.")
        return

    for obj in objects:
        discount = obj.get("discount_data", {})
        name = discount.get("name")
        discount_id = obj.get("id")
        discount_type = discount.get("discount_type")

        if discount_type == "FIXED_PERCENTAGE":
            value = f"{discount.get('percentage')}%"
        elif discount_type == "FIXED_AMOUNT":
            amount = discount.get("amount_money", {}).get("amount", 0)
            currency = discount.get("amount_money", {}).get("currency", "AUD")
            value = f"{amount / 100:.2f} {currency}"
        else:
            value = f"({discount_type})"

        print(f"Name: {name}")
        print(f"ID: {discount_id}")
        print(f"Value: {value}")
        print("---")


if __name__ == "__main__":
    list_discounts()