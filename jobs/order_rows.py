"""Reading rows of data/grounded_cafe_orders.csv, as get_orders.py writes them.

Two things about the CSV are easy to get wrong, so every script that reads it
goes through here instead of reading the columns by hand:

- Not every row is a sale. Refunds (RETURN) and orders with no items (EMPTY)
  are written too, so that nothing Square returned is lost. Counting them as
  sales would be wrong.
- A line can carry several discounts, e.g. "100%" on top of "Student
  Discount". They share one row, as parallel lists in discount_name and
  discount_amounts. discount_saved is the line's total across all of them, so
  it is NOT the amount any single discount saved.
"""

SEPARATOR = "; "  # must match MULTI_SEPARATOR in get_orders.py


def is_sale(row):
    """True for a sold line. Rows from a CSV older than record_type are sales."""
    return row.get("record_type", "SALE") == "SALE"


def discounts(row):
    """{discount name: dollars saved} for every discount on this line."""
    names = [n for n in (row.get("discount_name") or "").split(SEPARATOR) if n]
    amounts = (row.get("discount_amounts") or "").split(SEPARATOR)

    # A CSV from before discount_amounts existed had one discount per row,
    # with its amount in discount_saved.
    if len(amounts) != len(names):
        amounts = [row.get("discount_saved") or 0] * len(names)

    result = {}
    for name, amount in zip(names, amounts):
        result[name] = result.get(name, 0.0) + float(amount or 0)
    return result
