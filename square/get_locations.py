import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("SQUARE_ACCESS_TOKEN")

url = "https://connect.squareup.com/v2/locations"
headers = {
    "Square-Version": "2026-05-20",
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

response = requests.get(url, headers=headers)
response.raise_for_status()
data = response.json()

for location in data.get("locations", []):
    print(f"Name: {location.get('name')}")
    print(f"ID: {location.get('id')}")
    print(f"Status: {location.get('status')}")
    print("---")