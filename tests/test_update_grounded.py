"""The counting rules behind the published /grounded figures.

Vocabulary is CONTEXT.md's: a REDEMPTION is a donated item handed over free,
and it is drawn down from a DONATION. Anything TUSA funded is neither.
"""

import pytest

import update_grounded


def test_a_line_carrying_the_redemption_discount_is_a_redemption(write_orders_csv):
    csv_path = write_orders_csv([
        {"item_name": "Flat White", "category": "Coffee",
         "discount_name": "Paid Forward Redemption", "discount_amounts": "5.00"},
    ])

    assert update_grounded.aggregate(csv_path)["coffees_paid_forward"] == 1


def test_food_redemptions_are_counted_as_meals(write_orders_csv):
    csv_path = write_orders_csv([
        {"item_name": "Toastie ~ Chicken", "category": "Food",
         "discount_name": "Paid Forward Redemption", "discount_amounts": "12.50"},
    ])

    figures = update_grounded.aggregate(csv_path)
    assert figures["meals_paid_forward"] == 1
    assert figures["coffees_paid_forward"] == 0


def test_tusa_funded_giveaway_items_are_not_redemptions(write_orders_csv):
    """The 17 June 2026 night event. See docs/adr/0001-...md."""
    csv_path = write_orders_csv([
        {"item_name": "Student Meal", "category": "Food", "total_amount": "0"},
        {"item_name": "Student Drink", "category": "Drink", "total_amount": "0"},
    ])

    figures = update_grounded.aggregate(csv_path)
    assert figures["meals_paid_forward"] == 0
    assert figures["coffees_paid_forward"] == 0


def test_a_giveaway_item_is_not_a_redemption_even_if_it_carries_the_discount(write_orders_csv):
    """Excluded by name, so a till change can't quietly reinstate them."""
    csv_path = write_orders_csv([
        {"item_name": "Student Meal", "category": "Food",
         "discount_name": "Paid Forward Redemption", "discount_amounts": "12.50"},
    ])

    assert update_grounded.aggregate(csv_path)["meals_paid_forward"] == 0


def test_item_names_are_matched_with_surrounding_whitespace_stripped(write_orders_csv):
    """Live order data carries trailing spaces the catalog does not."""
    csv_path = write_orders_csv([
        {"item_name": "Student Meal ", "category": "Food",
         "discount_name": "Paid Forward Redemption", "discount_amounts": "12.50"},
    ])

    assert update_grounded.aggregate(csv_path)["meals_paid_forward"] == 0


@pytest.mark.parametrize("category, figure", [
    ("Food", "meals_paid_forward"),
    ("Coffee", "coffees_paid_forward"),
    ("Drink", "coffees_paid_forward"),
])
def test_redemptions_are_counted_by_quantity_not_by_row(write_orders_csv, category, figure):
    """One row can read "2 x Chicken Toastie", and two students ate."""
    csv_path = write_orders_csv([
        {"category": category, "quantity": "2",
         "discount_name": "Paid Forward Redemption", "discount_amounts": "25.00"},
    ])

    assert update_grounded.aggregate(csv_path)[figure] == 2


def test_refunds_and_empty_orders_are_not_counted(write_orders_csv):
    csv_path = write_orders_csv([
        {"record_type": "RETURN", "category": "Coffee", "quantity": "-1",
         "discount_name": "Paid Forward Redemption", "discount_amounts": "-5.00"},
        {"record_type": "EMPTY", "category": "", "quantity": "0"},
    ])

    figures = update_grounded.aggregate(csv_path)
    assert figures["coffees_paid_forward"] == 0
    assert figures["student_discounts_saved"] == "0.00"


def test_student_discount_totals_the_amount_saved(write_orders_csv):
    csv_path = write_orders_csv([
        {"discount_name": "Student Discount", "discount_amounts": "1.20"},
        {"discount_name": "Student Discount", "discount_amounts": "0.90"},
    ])

    assert update_grounded.aggregate(csv_path)["student_discounts_saved"] == "2.10"


def test_student_discount_counts_only_its_own_share_of_a_multi_discount_line(write_orders_csv):
    """A line can carry "100%" on top of the student discount. Only $0.90 of
    that $4.50 was a student saving; the rest was the café giving it away."""
    csv_path = write_orders_csv([
        {"discount_name": "Student Discount; 100%", "discount_amounts": "0.90; 3.60",
         "discount_saved": "4.50"},
    ])

    assert update_grounded.aggregate(csv_path)["student_discounts_saved"] == "0.90"


def test_other_discounts_do_not_make_an_item_a_redemption(write_orders_csv):
    """A free coffee is not a redemption unless a donor paid for it."""
    csv_path = write_orders_csv([
        {"category": "Coffee", "discount_name": "100%", "discount_amounts": "5.00"},
        {"category": "Coffee", "discount_name": "Loyalty Card Freebie", "discount_amounts": "5.00"},
        {"category": "Coffee", "discount_name": "U-Connect Staff", "discount_amounts": "1.00"},
    ])

    assert update_grounded.aggregate(csv_path)["coffees_paid_forward"] == 0


def test_redemptions_with_no_usable_category_are_counted_nowhere(write_orders_csv):
    """Never guessed at: an Unmapped redemption is reported by neither figure."""
    csv_path = write_orders_csv([
        {"item_name": "", "category": "Unmapped",
         "discount_name": "Paid Forward Redemption", "discount_amounts": "5.00"},
    ])

    figures = update_grounded.aggregate(csv_path)
    assert figures["coffees_paid_forward"] == 0
    assert figures["meals_paid_forward"] == 0
