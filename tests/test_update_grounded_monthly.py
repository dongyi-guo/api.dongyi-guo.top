"""The monthly reporting figures.

PURCHASED, REDEEMED and BANKED are three different questions, and conflating
them is how a figure once published as "saved in student discounts" turned
out to be every discount added together.
"""

import pytest

import update_grounded
import update_grounded_monthly as monthly


def rows_by_month(csv_path):
    return {row["month"]: row for row in monthly.build_rows(monthly.aggregate_by_month(csv_path))}


def test_a_donated_coffee_is_purchased_not_redeemed(write_orders_csv):
    """Money in, nothing handed over."""
    csv_path = write_orders_csv([
        {"item_name": "Pay-It Forward", "variation": "Regular Coffee",
         "category": "Exclude", "total_amount": "5.00"},
    ])

    row = rows_by_month(csv_path)["2026-07"]
    assert row["coffees_purchased"] == 1
    assert row["coffees_redeemed"] == 0


def test_the_donation_unit_comes_from_the_variation_name(write_orders_csv):
    csv_path = write_orders_csv([
        {"item_name": "Pay-It Forward", "variation": "Meal",
         "category": "Exclude", "total_amount": "12.50"},
    ])

    row = rows_by_month(csv_path)["2026-07"]
    assert row["meals_purchased"] == 1
    assert row["coffees_purchased"] == 0


def test_the_personal_tracker_item_is_a_donated_meal(write_orders_csv):
    csv_path = write_orders_csv([
        {"item_name": "JJ's Personal Pay-it Forward Tracker", "variation": "Regular",
         "category": "Exclude", "total_amount": "12.50"},
    ])

    assert rows_by_month(csv_path)["2026-07"]["meals_purchased"] == 1


def test_donations_are_counted_by_quantity(write_orders_csv):
    csv_path = write_orders_csv([
        {"item_name": "Pay-It Forward", "variation": "Meal", "quantity": "10",
         "category": "Exclude", "total_amount": "125.00"},
    ])

    assert rows_by_month(csv_path)["2026-07"]["meals_purchased"] == 10


@pytest.mark.parametrize("category, figure", [
    ("Coffee", "coffees_redeemed"),
    ("Drink", "coffees_redeemed"),
    ("Food", "meals_redeemed"),
])
def test_redemptions_are_counted_by_quantity(write_orders_csv, category, figure):
    csv_path = write_orders_csv([
        {"category": category, "quantity": "2",
         "discount_name": "Paid Forward Redemption", "discount_amounts": "10.00"},
    ])

    assert rows_by_month(csv_path)["2026-07"][figure] == 2


def test_banked_is_what_was_purchased_and_not_yet_claimed(write_orders_csv):
    """A coffee bought in June can be claimed in August, so banked is always
    counted since opening, never within one month."""
    csv_path = write_orders_csv([
        {"transaction_time": "2026-06-20T10:00:00+10:00", "item_name": "Pay-It Forward",
         "variation": "Regular Coffee", "category": "Exclude", "quantity": "3"},
        {"transaction_time": "2026-08-20T10:00:00+10:00", "category": "Coffee",
         "discount_name": "Paid Forward Redemption", "discount_amounts": "5.00"},
    ])

    months = rows_by_month(csv_path)
    assert months["2026-06"]["coffees_banked"] == 3
    assert months["2026-08"]["coffees_banked"] == 2
    # The August redemption belongs to August, not to the month it was bought.
    assert months["2026-08"]["coffees_redeemed"] == 1
    assert months["2026-06"]["coffees_redeemed"] == 0


def test_each_month_reports_itself_and_the_running_total_separately(write_orders_csv):
    csv_path = write_orders_csv([
        {"transaction_time": "2026-06-20T10:00:00+10:00",
         "discount_name": "Student Discount", "discount_amounts": "1.00"},
        {"transaction_time": "2026-07-20T10:00:00+10:00",
         "discount_name": "Student Discount", "discount_amounts": "2.50"},
    ])

    july = rows_by_month(csv_path)["2026-07"]
    assert july["student_discounts_saved"] == 2.50
    assert july["student_discounts_saved_total"] == 3.50


def test_student_discounts_are_reported_apart_from_every_other_discount(write_orders_csv):
    """Staff comps and freebies are not savings passed to a student."""
    csv_path = write_orders_csv([
        {"discount_name": "Student Discount", "discount_amounts": "1.00"},
        {"discount_name": "100%", "discount_amounts": "5.00"},
        {"discount_name": "Loyalty Card Freebie", "discount_amounts": "5.00"},
    ])

    row = rows_by_month(csv_path)["2026-07"]
    assert row["student_discounts_saved"] == 1.00
    assert row["all_discounts_saved"] == 11.00


def test_tusa_funded_giveaways_are_reported_but_never_counted(write_orders_csv):
    """Visible, so the exclusion cannot be mistaken for missing data."""
    csv_path = write_orders_csv([
        {"item_name": "Student Meal", "category": "Food", "quantity": "2",
         "total_amount": "0"},
    ])

    row = rows_by_month(csv_path)["2026-07"]
    assert row["excluded_giveaway_items"] == 2
    assert row["meals_redeemed"] == 0
    assert row["meals_purchased"] == 0


def test_a_refunded_donation_does_not_cancel_out_the_one_that_was_kept(write_orders_csv):
    """Refund rows are negative, so counting them would silently subtract."""
    csv_path = write_orders_csv([
        {"item_name": "Pay-It Forward", "variation": "Regular Coffee",
         "category": "Exclude"},
        {"record_type": "RETURN", "item_name": "Pay-It Forward",
         "variation": "Regular Coffee", "quantity": "-1", "category": "Exclude"},
    ])

    assert rows_by_month(csv_path)["2026-07"]["coffees_purchased"] == 1


def test_a_month_with_nothing_countable_in_it_is_not_reported(write_orders_csv):
    csv_path = write_orders_csv([
        {"record_type": "RETURN", "quantity": "-1"},
    ])

    assert rows_by_month(csv_path) == {}


def test_lifetime_totals_equal_what_update_grounded_publishes(write_orders_csv):
    """Two files, one counting rule. If they drift, the monthly report stops
    summing to the published figure and nobody notices for a month."""
    csv_path = write_orders_csv([
        {"transaction_time": "2026-07-10T10:00:00+10:00", "category": "Coffee",
         "discount_name": "Paid Forward Redemption", "discount_amounts": "5.00"},
        {"transaction_time": "2026-08-10T10:00:00+10:00", "category": "Food",
         "quantity": "2", "discount_name": "Paid Forward Redemption",
         "discount_amounts": "25.00"},
        {"transaction_time": "2026-08-11T10:00:00+10:00",
         "discount_name": "Student Discount", "discount_amounts": "1.20"},
        {"transaction_time": "2026-06-17T18:00:00+10:00", "item_name": "Student Meal",
         "category": "Food", "total_amount": "0"},
    ])

    published = update_grounded.aggregate(csv_path)
    last_month = sorted(rows_by_month(csv_path).values(), key=lambda r: r["month"])[-1]

    assert last_month["coffees_redeemed_total"] == published["coffees_paid_forward"]
    assert last_month["meals_redeemed_total"] == published["meals_paid_forward"]
    assert (f"{last_month['student_discounts_saved_total']:.2f}"
            == published["student_discounts_saved"])
