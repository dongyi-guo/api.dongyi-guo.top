"""Shared test setup.

The jobs are scripts, not an installed package, so they import each other by
bare name (`import order_rows`). Putting jobs/ on the path lets the tests
import them the same way the scripts do, rather than inventing a package
layout the pipeline doesn't use.
"""

import csv
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "jobs"))

import get_orders  # noqa: E402

# One row per line item, in the order get_orders.py writes them. Tests name
# only the fields they care about; everything else takes these defaults.
ROW_DEFAULTS = {
    "order_id": "ORDER1",
    "transaction_time": "2026-07-15T10:00:00+10:00",
    "item_name": "Flat White",
    "quantity": "1",
    "variation": "Regular",
    "total_amount": "5.00",
    "discount_name": "",
    "discount_saved": "0",
    "category": "Coffee",
    "record_type": "SALE",
    "discount_amounts": "",
}


@pytest.fixture
def write_orders_csv(tmp_path):
    """Write an orders CSV from partial rows, returning its path.

    Takes dicts holding only the fields a test cares about, so each test
    reads as the rule it is checking rather than as a wall of CSV.
    """

    def _write(rows, columns=None):
        columns = columns or get_orders.CSV_COLUMNS
        path = tmp_path / "grounded_cafe_orders.csv"

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns, restval="")
            writer.writeheader()
            for row in rows:
                full = {key: value for key, value in ROW_DEFAULTS.items() if key in columns}
                full.update(row)
                writer.writerow(full)

        return path

    return _write
