"""The orders CSV: where it lives, how to read it, and what its rows mean.

get_orders.py writes data/grounded_cafe_orders.csv; every other script reads
it. Anything both sides must agree on is defined here, once, so the writer and
the readers cannot drift apart. That includes the counting rules: which lines
are redemptions, and whether a redemption is a coffee or a meal. Three scripts
used to spell those out separately.

Two things about the CSV are easy to get wrong, so every reader goes through
here instead of reading the columns by hand:

- Not every row is a sale. Refunds (RETURN) and orders with no items (EMPTY)
  are written too, so that nothing Square returned is lost. Counting them as
  sales would be wrong.
- A line can carry several discounts, e.g. "100%" on top of "Student
  Discount". They share one row, as parallel lists in discount_name and
  discount_amounts. discount_saved is the line's total across all of them, so
  it is NOT the amount any single discount saved.
"""

from pathlib import Path

# Paths are resolved from this file, not the working directory, so every
# script behaves the same whether cron or a human runs it.
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "grounded_cafe_orders.csv"

# Joins several values in one CSV cell, e.g. a line carrying two discounts.
SEPARATOR = "; "

# record_type values. Only SALE rows are sales.
SALE, RETURN, EMPTY = "SALE", "RETURN", "EMPTY"

# get_orders.py writes these two under exactly these names, whatever the till
# calls them, because the rules below match on them.
STUDENT_DISCOUNT = "Student Discount"
PAID_FORWARD_DISCOUNT = "Paid Forward Redemption"

# $0 items given away at the TUSA-funded night event on 17 June 2026. TUSA
# paid for them, so no donation was drawn down and they are not redemptions:
# see docs/adr/0001-institution-funded-giveaways-are-not-redemptions.md.
# Excluded by name, not left to chance: they currently carry no discount at
# all, so they would slip back in the moment one of them ever did.
EXCLUDED_GIVEAWAY_ITEMS = {"Student Meal", "Student Drink"}


def is_sale(row):
    """True for a sold line. Rows from a CSV older than record_type are sales."""
    return row.get("record_type", SALE) == SALE


def item_name(row):
    # Stripped because live order data carries trailing whitespace the
    # catalog does not.
    return (row.get("item_name") or "").strip()


def quantity(row):
    """Items on the line, not rows: one row can be "2 x Chicken Toastie"."""
    return int(float(row.get("quantity") or 0))


def discounts(row):
    """{discount name: dollars saved} for every discount on this line."""
    names = [n for n in (row.get("discount_name") or "").split(SEPARATOR) if n]
    raw_amounts = row.get("discount_amounts") or ""
    # "".split(SEPARATOR) is [""], not [], which would look like one amount.
    amounts = raw_amounts.split(SEPARATOR) if raw_amounts else []

    # A CSV from before discount_amounts existed had one discount per row,
    # with its amount in discount_saved.
    if len(amounts) != len(names):
        amounts = [row.get("discount_saved") or 0] * len(names)

    result = {}
    for name, amount in zip(names, amounts):
        result[name] = result.get(name, 0.0) + float(amount or 0)
    return result


def is_redemption(row):
    """A donated item handed over free. The only definition in the project.

    Only the Paid Forward Redemption discount makes a line a redemption. A $0
    line is not one just for being free, and the TUSA-funded giveaways never
    are.
    """
    return (
        is_sale(row)
        and item_name(row) not in EXCLUDED_GIVEAWAY_ITEMS
        and PAID_FORWARD_DISCOUNT in discounts(row)
    )


def redeemed_unit(row):
    """"coffees" or "meals" for a redemption, None for anything else.

    Coffee and Drink both count as coffees. A redemption on an Unmapped or
    Exclude line is counted as neither: check the CSV if totals look off.
    """
    if not is_redemption(row):
        return None
    category = row.get("category", "")
    if category in ("Coffee", "Drink"):
        return "coffees"
    if category == "Food":
        return "meals"
    return None
