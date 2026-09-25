# Context

Shared vocabulary for this project. These terms caused real confusion and real
mistakes, so they are written down. This file is a glossary only, no code.

## Order

One unique `order_id` from Square. **Not** one row of the CSV: the CSV has one
row per line item, so a customer buying a coffee and a muffin is two rows and
one order. As of the September 2026 export, 10,154 rows were 7,141 orders.

An order counts as an order even when it brought in no money. The ingredients
were bought either way.

## Donation

A coffee or meal bought by a member of the public for a stranger to claim
later. Money comes in and nothing is handed over. Donations come in two units,
a **coffee** and a **meal**, each worth a fixed menu price at the time of sale.
The monthly report and the café's own statements call these **purchased**
("18 meals purchased for students"); that means donations, never redemptions.
_Avoid_: pay-it-forward purchase, PIF sale, credit

## Redemption

A donated coffee or meal being handed over, free, to the student who claims
it. Every redemption draws down an earlier donation. Counted in items, not
rows or dollars: one redemption of a $5 snack uses up a whole meal donation.
_Avoid_: pay-it-forward (ambiguous: it names the whole scheme, not either side
of it), paid forward. The published keys `coffees_paid_forward` and
`meals_paid_forward` predate this glossary and mean **redemptions**.

## Banked

Donations not yet redeemed: coffees and meals the public has paid for that are
still waiting to be claimed. Counted per unit, coffees and meals separately.

## Not a redemption: institution-funded giveaways

An item given away free because an institution covered the cost, such as TUSA
paying for the 17 June 2026 night event, is **not** a redemption. Nobody from
the public donated it, so no donation was drawn down. This covers the
**Student Meal**, **Student Drink** and **TUSA After Dark** items. Decided
September 2026; see `docs/adr/0001-institution-funded-giveaways-are-not-redemptions.md`.

## Not a redemption

A free item is **not** a redemption just because it cost $0. Staff comps,
loyalty freebies and launch giveaways are all free to the customer but were
paid for by nobody: they cost the café money and earned none. The data usually
cannot tell these apart, because the till records a manual price override with
no discount attached at all.

## Refund

A sale reversed afterwards. Square records it as a separate order pointing
back at the original sale. A refund is not an order and not a sale, and it
does not undo a donation or a redemption in any published figure. Some
"refunds" are the till moving a sale onto an invoice, not money going back.

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
