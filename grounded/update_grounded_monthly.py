"""Month-by-month reporting for the pay-it-forward scheme.

Unlike the other jobs in this folder, this one publishes nothing. It reads
`data/grounded_cafe_orders.csv` and writes `data/grounded_monthly_summary.csv`,
one row per calendar month, for reporting to the cafe and to TUSA.

    python3 grounded/update_grounded_monthly.py --month 2026-07
    python3 grounded/update_grounded_monthly.py --month 2026-07 --cumulative

--month is required: a report without a month on it invites being read as
whatever the reader assumes. Two views of that month, answering different
questions:

- MONTHLY (default) is that month alone. July means what happened in July.
- CUMULATIVE (--cumulative) is everything since opening on 9 June 2026 up to
  the end of that month, i.e. what the figures read at the time.

The CSV always holds both views, so cron can write it once and either view can
be read back from it. The arguments choose what gets printed.

Three quantities, deliberately kept apart, because they have been confused
before:

- PURCHASED: coffees and meals the public bought for a stranger. Money in.
- REDEEMED:  coffees and meals handed over free to a student. An item out.
- BANKED:    purchased minus redeemed, i.e. what is still waiting to be
             claimed. Only meaningful since opening, so it is always
             cumulative, in both views.

Redemptions are counted by the same rule update_grounded.py publishes, from
order_rows.py: by quantity, not by row, and never the $0 Student Meal /
Student Drink items from the TUSA-funded 17 June 2026 night event. See
docs/adr/0001-institution-funded-giveaways-are-not-redemptions.md.
"""

import argparse
import csv
from collections import defaultdict

import order_rows

# Spelled out rather than read from __doc__, which is None when Python runs
# with -OO and docstrings are stripped.
DESCRIPTION = "Month-by-month reporting for the pay-it-forward scheme."

CSV_PATH = order_rows.CSV_PATH
OUTPUT_FILE = order_rows.DATA_DIR / "grounded_monthly_summary.csv"

# The donation side. "Pay-It Forward" carries the unit in its variation name;
# the tracker item is one regular donor's own, and is always a meal.
DONATION_ITEM = "Pay-It Forward"
DONATION_TRACKER_ITEM = "JJ's Personal Pay-it Forward Tracker"
COFFEE_VARIATION = "Regular Coffee"

OPENED_ON = "9 June 2026"

# Monthly figures, then the same figures accumulated since opening. Banked
# appears once: it is cumulative by nature.
MONTHLY_FIELDS = [
    "coffees_purchased", "meals_purchased",
    "coffees_redeemed", "meals_redeemed",
    "student_discounts_saved", "all_discounts_saved",
    "excluded_giveaway_items",
]
COLUMNS = (
    ["month"]
    + MONTHLY_FIELDS
    + [f"{name}_total" for name in MONTHLY_FIELDS]
    + ["coffees_banked", "meals_banked"]
)

MONEY_FIELDS = {"student_discounts_saved", "all_discounts_saved"}


def empty_month():
    return {name: 0.0 if name in MONEY_FIELDS else 0 for name in MONTHLY_FIELDS}


def aggregate_by_month(csv_path):
    """Return {"YYYY-MM": {figure: value}} for every month present."""
    months = defaultdict(empty_month)

    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            # Refunds and empty orders are in the CSV too; only sales count.
            if not order_rows.is_sale(row):
                continue

            # get_orders.py has already converted these to Hobart local time,
            # so the first 7 characters are the local month.
            month = (row.get("transaction_time") or "")[:7]
            if not month:
                continue

            item_name = order_rows.item_name(row)
            line_discounts = order_rows.discounts(row)
            quantity = order_rows.quantity(row)

            bucket = months[month]

            bucket["student_discounts_saved"] += line_discounts.get(
                order_rows.STUDENT_DISCOUNT, 0.0
            )
            bucket["all_discounts_saved"] += sum(line_discounts.values())

            # Counted only so the exclusion is visible rather than silently
            # missing. order_rows.is_redemption already refuses them.
            if item_name in order_rows.EXCLUDED_GIVEAWAY_ITEMS:
                bucket["excluded_giveaway_items"] += quantity
                continue

            if item_name == DONATION_ITEM:
                unit = "coffees" if row.get("variation") == COFFEE_VARIATION else "meals"
                bucket[f"{unit}_purchased"] += quantity
            elif item_name == DONATION_TRACKER_ITEM:
                bucket["meals_purchased"] += quantity

            unit = order_rows.redeemed_unit(row)
            if unit:
                bucket[f"{unit}_redeemed"] += quantity

    return months


def build_rows(months):
    """One row per month, carrying the monthly view and the cumulative view."""
    totals = defaultdict(float)
    rows = []

    for month in sorted(months):
        data = months[month]
        for name in MONTHLY_FIELDS:
            totals[name] += data[name]

        row = {"month": month}
        for name in MONTHLY_FIELDS:
            row[name] = data[name]
            row[f"{name}_total"] = totals[name]

        # Banked is purchased minus redeemed since opening, never a single
        # month's figure: a coffee bought in June can be claimed in August.
        row["coffees_banked"] = totals["coffees_purchased"] - totals["coffees_redeemed"]
        row["meals_banked"] = totals["meals_purchased"] - totals["meals_redeemed"]
        rows.append(row)

    return rows


def formatted(row):
    """The row as it is written to the CSV: money to 2dp, counts as integers."""
    out = {}
    for key, value in row.items():
        if key == "month":
            out[key] = value
        elif key.replace("_total", "") in MONEY_FIELDS:
            out[key] = f"{value:.2f}"
        else:
            out[key] = int(value)
    return out


def write_csv(rows):
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, restval="")
        writer.writeheader()
        writer.writerows(formatted(row) for row in rows)


def view_of(row, cumulative):
    """Pick one view's figures out of a row, under their plain names."""
    suffix = "_total" if cumulative else ""
    return {name: row[f"{name}{suffix}"] for name in MONTHLY_FIELDS}


def print_report(rows, cumulative):
    heading = (
        f"Cumulative since opening on {OPENED_ON}"
        if cumulative else "Each month on its own"
    )
    print(heading)
    print()

    for row in rows:
        figures = view_of(row, cumulative)
        print(f"{row['month']}")
        print(f"  {int(figures['meals_purchased'])} meals purchased for students "
              "under 'Pay it Forward'")
        print(f"  {int(figures['coffees_purchased'])} coffees purchased for students "
              "under 'Pay it Forward'")
        print(f"  ${figures['student_discounts_saved']:,.2f} saved in student discounts")
        print(f"  redeemed: {int(figures['meals_redeemed'])} meals, "
              f"{int(figures['coffees_redeemed'])} coffees")
        # Banked is cumulative in both views, so it is labelled as such.
        print(f"  banked to date: {int(row['meals_banked'])} meals, "
              f"{int(row['coffees_banked'])} coffees")
        if figures["excluded_giveaway_items"]:
            print(f"  ({int(figures['excluded_giveaway_items'])} TUSA-funded giveaway "
                  "items excluded, not redemptions)")
        print()


def main():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        "--month", metavar="YYYY-MM", required=True,
        help="the month to report, e.g. 2026-07",
    )
    parser.add_argument(
        "--cumulative", action="store_true",
        help=f"report totals since opening on {OPENED_ON}, rather than that month alone",
    )
    args = parser.parse_args()

    if not CSV_PATH.exists():
        # Fail loudly rather than writing an empty summary that looks real.
        raise SystemExit(f"{CSV_PATH} not found. Run get_orders.py first.")

    months = aggregate_by_month(CSV_PATH)
    if not months:
        raise SystemExit(f"No usable rows in {CSV_PATH}, refusing to write a summary.")

    rows = build_rows(months)
    # The CSV holds every month and both views, whichever view was asked for,
    # so a cron run always writes the same complete file.
    write_csv(rows)
    print(f"Wrote {len(rows)} months to {OUTPUT_FILE}\n")

    rows = [row for row in rows if row["month"] == args.month]
    if not rows:
        raise SystemExit(
            f"No data for {args.month}. Months available: "
            f"{', '.join(sorted(months))}"
        )

    print_report(rows, cumulative=args.cumulative)


if __name__ == "__main__":
    main()
