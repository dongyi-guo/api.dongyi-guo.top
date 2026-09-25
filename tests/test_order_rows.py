"""Reading a row of the orders CSV.

Small surface, but every aggregation goes through it, so a wrong answer here
is wrong in three published figures at once.
"""

import order_rows


def test_a_line_with_one_discount_reports_it_with_its_amount():
    row = {"discount_name": "Student Discount", "discount_amounts": "1.20"}

    assert order_rows.discounts(row) == {"Student Discount": 1.20}


def test_a_line_with_several_discounts_keeps_each_amount_with_its_own_name():
    """They share one row as parallel lists, in the same order."""
    row = {"discount_name": "Student Discount; 100%", "discount_amounts": "0.90; 3.60"}

    assert order_rows.discounts(row) == {"Student Discount": 0.90, "100%": 3.60}


def test_a_line_with_no_discount_reports_none():
    assert order_rows.discounts({"discount_name": "", "discount_amounts": ""}) == {}


def test_the_same_discount_twice_on_one_line_is_summed():
    row = {"discount_name": "Student Discount; Student Discount",
           "discount_amounts": "1.00; 0.50"}

    assert order_rows.discounts(row) == {"Student Discount": 1.50}


def test_a_csv_written_before_discount_amounts_existed_still_reads():
    """The old format had one discount per row, its amount in discount_saved."""
    row = {"discount_name": "Paid Forward Redemption", "discount_saved": "5.00"}

    assert order_rows.discounts(row) == {"Paid Forward Redemption": 5.00}


def test_a_sale_is_a_sale():
    assert order_rows.is_sale({"record_type": "SALE"}) is True


def test_refunds_and_empty_orders_are_not_sales():
    assert order_rows.is_sale({"record_type": "RETURN"}) is False
    assert order_rows.is_sale({"record_type": "EMPTY"}) is False


def test_a_row_from_a_csv_older_than_record_type_counts_as_a_sale():
    """That CSV held nothing but sales, so treating it as one is correct."""
    assert order_rows.is_sale({"order_id": "ORDER1"}) is True
