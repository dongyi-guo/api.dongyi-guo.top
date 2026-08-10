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


def list_categories():
    params = {"types": "CATEGORY"}
    response = requests.get(URL, headers=HEADERS, params=params)
    if response.status_code != 200:
        print(response.status_code, response.text)
    response.raise_for_status()
    data = response.json()

    objects = data.get("objects", [])
    if not objects:
        print("No categories found on this account.")
        return

    for obj in objects:
        category = obj.get("category_data", {})
        print(f"Name: {category.get('name')}")
        print(f"ID: {obj.get('id')}")
        print("---")


if __name__ == "__main__":
    list_categories()