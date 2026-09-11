# Context

Shared vocabulary for this project. These terms caused real confusion and real
mistakes, so they are written down. This file is a glossary only, no code.

## Order

One unique `order_id` from Square. **Not** one row of the CSV: the CSV has one
row per line item, so a customer buying a coffee and a muffin is two rows and
one order. As of the September 2026 export, 10,154 rows were 7,141 orders.

An order counts as an order even when it brought in no money. The ingredients
were bought either way.

## Redemption

A free item that somebody else already paid for, through the pay-it-forward
scheme. Recognised two ways, and both must be counted:

- a line carrying the **Paid Forward Redemption** discount, or
- a **Student Meal** or **Student Drink** item, which are $0 catalog items used
  during the June 2026 hard launch to record the same real-world act.

Whether the hard-launch giveaway was genuinely donor-funded is **unresolved**.
If it was funded by the café as a promotion, those items are marketing spend
rather than redemptions, and the published impact figures would fall by about
84%. Nobody currently knows. Do not "tidy" this either way without an answer.

## Not a redemption

A free item is **not** a redemption just because it cost $0. Staff comps,
loyalty freebies and launch giveaways are all free to the customer but were
paid for by nobody: they cost the café money and earned none. The data usually
cannot tell these apart, because the till records a manual price override with
no discount attached at all.

## Student Discount

20% off for enrolled students, on normally priced items. Unrelated to the
pay-it-forward scheme, despite sharing the word "student" with the redemption
items above. Never merge the two.

## Trading day

A date on which at least one order was placed. Derived from the data rather
than from a calendar, so closures and semester breaks need no maintenance.

## Trading hour

A flat 6.75 hours per trading day, the 8:00 to 14:45 window. A deliberate
simplification: occasional evening events ran longer, and are not counted as
extra hours.

## Impact figures vs trading figures

Two different questions, two different handles, two different definitions of
which orders count:

- **Impact** (`/grounded`) answers "how much was given away". Charity only.
- **Trading** (`/social-cafe`) answers "how busy are we and what does an order
  bring in". Commercial only.

They count orders differently on purpose. Averages of price exclude orders that
were wholly redemptions, because a donor already paid. Counts of throughput
include every order, because staff made every drink.

## Category

Which of four buckets a line item falls into: `Coffee`, `Drink`, `Food` or
`Exclude`. This is *our* taxonomy, deliberately coarser than Square's own
category list. `Coffee` and `Drink` are counted together everywhere downstream,
so the split between them is presentational.

`Exclude` means the line is not a consumable sale: merchandise, the
pay-it-forward donation product itself, till reconciliation.

## Unmapped

A line item whose category could not be determined, from the catalog or from
the retired-name fallback. It is never guessed at. Unmapped lines are not
counted toward the impact figures, so a rising Unmapped count silently
understates them: check it after a run.
