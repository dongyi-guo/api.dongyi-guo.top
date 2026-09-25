"""Turning Square's orders into CSV rows.

Square money is integer cents; the CSV is dollars. A refund arrives as its
own order carrying no line_items, only returns, which is how refunds went
unnoticed for months.
"""

import get_orders

# variation id -> bucket, and variation id -> Square's own category name
LOOKUPS = ({"VAR_COFFEE": "Coffee", "VAR_FOOD": "Food"},
           {"VAR_COFFEE": "Hot Drinks", "VAR_FOOD": "Toasties"})
CATALOG_DISCOUNTS = {"DISC_UCONNECT": "U-Connect Staff"}


def money(cents):
    return {"amount": cents, "currency": "AUD"}


def sale(line_items, discounts=None, **order):
    return {
        "id": "ORDER1",
        "created_at": "2026-07-15T00:00:00Z",
        "line_items": line_items,
        "discounts": discounts or [],
        **order,
    }


def line(**overrides):
    return {
        "uid": "LINE1",
        "name": "Flat White",
        "variation_name": "Regular",
        "quantity": "1",
        "catalog_object_id": "VAR_COFFEE",
        "base_price_money": money(500),
        "gross_sales_money": money(500),
        "total_money": money(500),
        "total_discount_money": money(0),
        **overrides,
    }


def rows_for(orders):
    return list(get_orders.build_rows(orders, LOOKUPS, CATALOG_DISCOUNTS))


def test_a_sold_line_becomes_one_sale_row_in_dollars():
    rows = rows_for([sale([line()])])

    assert len(rows) == 1
    assert rows[0]["record_type"] == "SALE"
    assert rows[0]["item_name"] == "Flat White"
    assert rows[0]["total_amount"] == 5.00
    assert rows[0]["category"] == "Coffee"
    assert rows[0]["square_category"] == "Hot Drinks"


def test_a_line_with_two_discounts_stays_one_row():
    """One row per line item, never duplicated per discount."""
    orders = [sale(
        [line(applied_discounts=[{"discount_uid": "D1", "applied_money": money(90)},
                                 {"discount_uid": "D2", "applied_money": money(360)}],
              total_discount_money=money(450), total_money=money(0))],
        discounts=[{"uid": "D1", "catalog_object_id": get_orders.STUDENT_DISCOUNT_ID},
                   {"uid": "D2", "name": "100%"}],
    )]

    rows = rows_for(orders)

    assert len(rows) == 1
    assert rows[0]["discount_name"] == "Student Discount; 100%"
    assert rows[0]["discount_amounts"] == "0.90; 3.60"
    assert rows[0]["discount_saved"] == 4.50


def test_the_matched_discounts_keep_a_fixed_name_whatever_square_calls_them():
    """The till has shown this as both "Student Discount" and
    "Student Discount (20%)"; the aggregations match on the name."""
    orders = [sale(
        [line(applied_discounts=[{"discount_uid": "D1", "applied_money": money(120)}])],
        discounts=[{"uid": "D1", "name": "Student Discount (20%)",
                    "catalog_object_id": get_orders.STUDENT_DISCOUNT_ID}],
    )]

    assert rows_for(orders)[0]["discount_name"] == "Student Discount"


def test_an_untracked_discount_is_recorded_under_its_catalog_name():
    """Four discounts were once dropped, so their lines looked simply free."""
    orders = [sale(
        [line(applied_discounts=[{"discount_uid": "D1", "applied_money": money(100)}])],
        discounts=[{"uid": "D1", "catalog_object_id": "DISC_UCONNECT"}],
    )]

    assert rows_for(orders)[0]["discount_name"] == "U-Connect Staff"


def test_a_refund_becomes_a_negative_return_row_linked_to_the_sale():
    orders = [{
        "id": "REFUND1",
        "created_at": "2026-07-16T00:00:00Z",
        "refunds": [{"reason": "Mischarge"}],
        "returns": [{
            "source_order_id": "ORDER1",
            "return_line_items": [{
                "uid": "RLINE1",
                "source_line_item_uid": "LINE1",
                "name": "Flat White",
                "quantity": "1",
                "catalog_object_id": "VAR_COFFEE",
                "base_price_money": money(500),
                "gross_return_money": money(500),
                "total_money": money(500),
                "total_discount_money": money(0),
            }],
        }],
    }]

    rows = rows_for(orders)

    assert len(rows) == 1
    assert rows[0]["record_type"] == "RETURN"
    assert rows[0]["quantity"] == "-1"
    assert rows[0]["total_amount"] == -5.00
    assert rows[0]["source_order_id"] == "ORDER1"
    assert rows[0]["source_line_uid"] == "LINE1"
    assert rows[0]["refund_reason"] == "Mischarge"


def test_an_order_with_nothing_on_it_is_still_written():
    """Opening the cash drawer. Written so the row count matches Square."""
    rows = rows_for([{"id": "NOSALE1", "created_at": "2026-07-15T00:00:00Z",
                      "tenders": [{"type": "NO_SALE"}]}])

    assert len(rows) == 1
    assert rows[0]["record_type"] == "EMPTY"
    assert rows[0]["tender_types"] == "NO_SALE"


def test_an_item_the_catalog_cannot_explain_falls_back_to_the_name_map():
    """Items deleted from the catalog leave no id to join on."""
    rows = rows_for([sale([line(name="Student Meal", catalog_object_id=None)])])

    assert rows[0]["category"] == "Food"


def test_an_item_neither_source_explains_is_never_guessed_at():
    rows = rows_for([sale([line(name="", catalog_object_id=None)])])

    assert rows[0]["category"] == "Unmapped"


def test_timestamps_are_converted_to_hobart_local_time():
    """Square returns UTC. A 7am order was once missed entirely over this."""
    rows = rows_for([sale([line()], created_at="2026-07-14T21:00:00Z")])

    assert rows[0]["transaction_time"].startswith("2026-07-15T07:00:00")


def test_modifiers_are_named_with_their_price():
    rows = rows_for([sale([line(modifiers=[
        {"name": "Oat", "total_price_money": money(50)},
        {"name": "Dine-In", "total_price_money": money(0)},
    ])])])

    assert rows[0]["modifiers"] == "Oat (+0.50); Dine-In"
