"""Shared helpers for pushing values to the API service.

Both daily jobs use these so the create-if-missing behaviour stays in one
place. The admin endpoints are internal (127.0.0.1), so this never goes out
over the public domain.
"""

import os

import requests


def base_url() -> str:
    return os.getenv("API_BASE_URL", "http://127.0.0.1:55500").rstrip("/")


def admin_headers() -> dict:
    token = os.getenv("API_ADMIN_TOKEN")
    if not token:
        raise SystemExit("Missing API_ADMIN_TOKEN in .env")
    return {"X-Admin-Token": token, "Content-Type": "application/json"}


def handle_exists(handle: str) -> bool:
    """A handle's public GET returns 200 when it exists, 404 when it doesn't."""
    response = requests.get(f"{base_url()}/{handle}", timeout=30)
    if response.status_code == 200:
        return True
    if response.status_code == 404:
        return False
    raise SystemExit(f"Unexpected {response.status_code} checking /{handle}: {response.text}")


def push(handle: str, values: dict) -> None:
    """Create the handle with these values, or update each one if it exists.

    Creating needs a single POST carrying every attribute, because the API
    rejects a handle with no key/value pairs.
    """
    headers = admin_headers()

    if not handle_exists(handle):
        response = requests.post(
            f"{base_url()}/_admin/api/handles",
            headers=headers,
            json={"handle": handle, "attributes": values},
            timeout=30,
        )
        if response.status_code >= 400:
            raise SystemExit(f"Failed to create /{handle}: {response.status_code} {response.text}")
        print(f"Created /{handle} with {len(values)} values")
        return

    for key, value in values.items():
        response = requests.put(
            f"{base_url()}/_admin/api/handles/{handle}/attributes/{key}",
            headers=headers,
            json={"value": value},
            timeout=30,
        )
        if response.status_code >= 400:
            print(f"Failed to update {key}: {response.status_code} {response.text}")
        else:
            print(f"Updated {key} = {value}")
