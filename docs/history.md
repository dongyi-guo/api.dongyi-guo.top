# History and findings

What was investigated, what the data showed, and how the published numbers moved. Written
September 2026 so the reasoning survives the chat sessions it came from. Figures are as of the
date given and will have moved since; regenerate current ones with
`grounded/update_grounded_monthly.py`.

Decisions are in `docs/adr/`, terms in `CONTEXT.md`, open questions in `AGENTS.md`. This file
is the evidence behind them.

## Before September 2026

- Categorisation moved from a hand-kept item-name map to Square catalog IDs. `Unmapped` rows
  fell from 36.3% to 0.6%, and `/grounded` rose from 98 coffees / 109 meals to 125 / 121,
  because 39 redemption rows had been silently uncounted.
- A 7am order was once missed entirely because `START_AT` was written in UTC, not Hobart time.

## The June "boom" (investigated 22 September 2026)

**The question:** why were pay-it-forward numbers high in June and low in July and August?

**The answer:** two different recording methods, used at different times, never both at once.

| Method | Jun | Jul | Aug | Sep (to 22nd) |
|---|---|---|---|---|
| `Student Meal` / `Student Drink` items (rows) | 173 | 0 | 0 | 0 |
| `Paid Forward Redemption` discount (rows) | 0 | 21 | 27 | 25 |

- Every `Student Meal` / `Student Drink` row is from **one evening, 17 June 2026, 5–7pm**: a
  TUSA night event. 92 meal rows and 81 drink rows, 215 items, all $0, none carrying a discount.
  That day had 462 rows against a normal ~110–130.
- The `Paid Forward Redemption` discount first appears on **10 July 2026**.
- From 18 June to 9 July (22 days, 1,989 rows) nothing was redeemed at all. The scheme was
  dormant; the data isn't missing.
- The old rule counted `item in {Student Meal, Student Drink} OR discount == Paid Forward
  Redemption`. Its comment claimed the OR prevented double-counting, but no row ever matched
  both, so it simply added the two eras together. The student items were 173 of 246 counted
  rows, about 70% of the published figure.
- 17 June also had 68 `TUSA After Dark` items and **96 ordinary menu items with the `100%`
  discount**. Neither was ever counted as a redemption. The 96 are probably the same
  TUSA-funded night, but the ADR doesn't name them explicitly.

**Decision:** TUSA-funded giveaways are not redemptions (`docs/adr/0001`). A GitHub issue was
drafted to record it but never filed, because `gh` wasn't installed; the ADR is the record.

Dongyi also mentioned pay-it-forward records kept by their supervisor that don't appear in the
Square data. Not followed up.

## The donation side

The public donates through two catalog items:

| Item | Variation | Price | Means |
|---|---|---|---|
| `Pay-It Forward` | `Regular Coffee` | $4.50, **$5.00 from August 2026** | 1 coffee donated |
| `Pay-It Forward` | `Meal` | $12.50 | 1 meal donated |
| `JJ's Personal Pay-it Forward Tracker` | `Regular` | $12.50 | 1 meal donated, by one regular donor, from 31 August, usually alongside their own protein smoothie |

- Donations started on 16 June, the day before the launch event.
- At 10:14 on 17 June one card order bought 10 meals and 10 coffees ($172.72). Possibly TUSA,
  possibly one large donor. It counts as a real donation, because money came in.
- Menus checked (food menu of 17 August 2026, drinks menu): mains $11.50–$13.50, regular coffees
  $4.50–$5.50, plus a ~1.6% card surcharge ($12.50 → $12.70, $5.00 → $5.08).
- Every donation line and every `Paid Forward Redemption` line is a named catalog item, so no
  guessing by price was needed. The unnamed custom-amount lines are ordinary paid sales, mostly
  $4–7 drinks.
- Nobody at the café has a documented process for recording pay-it-forward. Only whoever runs
  the till knows which buttons get used. Less than one redemption per trading day is believed
  to be real.

## The ledger at 22 September 2026

Counted by quantity, 17 June event excluded.

| Month | Donated coffee / meal | Redeemed coffee / meal | Banked (running) | $ in | $ out |
|---|---|---|---|---|---|
| Jun | 26 / 18 | 0 / 0 | 26 / 18 | $342.00 | $0.00 |
| Jul | 21 / 17 | 10 / 11 | 37 / 24 | $307.00 | $174.00 |
| Aug | 8 / 7 | 22 / 5 | 23 / 26 | $127.50 | $157.00 |
| Sep | 7 / 12 | 16 / 18 | 14 / 20 | $185.00 | $255.50 |

This first hand count undercounted September's donated meals. The data holds 5 `Pay-It Forward`
meals and 13 `JJ's Personal Pay-it Forward Tracker` meals for 1–22 September, 18 in all, giving
60 donated meals in total. That is what `update_grounded_monthly.py` reports; trust the script.

- June wasn't quiet, it was saving up: 44 items donated, none redeemed until 10 July.
- Items and dollars disagree. 17 of 34 redeemed "meals" were snacks under $10 (muffins,
  friands, brownies), each using a $12.50 meal donation, and 10 redeemed coffees were
  $5.50–$6.00 drinks against a $5.00 donation. By dollars, **$375** was still banked.
- August's drop in coffee donations (8, against July's 21) coincides with the price rising to
  $5.00. Cause not established.

## What the orders CSV used to lose (fixed 22 September 2026)

| Problem | Effect |
|---|---|
| Only 2 of the 6 discounts were kept | 265 lines with `100%`, `Half-Price`, `U-Connect Staff` or `Loyalty Card Freebie` looked like they simply cost $0 |
| Refunds dropped | A refund is its own order with no line items. 16 refund orders (44 lines, −$230.23) were missing. 28 of the 44 are "To Be Invoiced", which looks like moving a sale to an invoice rather than a real refund |
| One row per discount | Lines with two discounts appeared twice (12 lines) |
| Most Square fields discarded | Original price, tax, surcharge, modifiers, notes, tender type |
| Orders with no items dropped | 3 cash-drawer `NO_SALE` orders |
| `Loaf / Loaves` category unmapped | New Square category with no bucket |
| Counting rows, not items | One row can be quantity 2 or 10 |

After the fix, the CSV matched Square's own order totals for all 8,061 orders, to the cent.

## Discounts seen on the till

`Student Discount` (20%), `100%`, `Paid Forward Redemption`, `U-Connect Staff`,
`Loyalty Card Freebie` (from 31 August 2026, a separate scheme), `Half-Price`, and
`Food Hub Volunteer Coffee` (first seen 24 September 2026, used once).

The `100%` discount outside 17 June: 51 lines from 10 July to 22 September, nearly all a single
coffee, 1–3 a day, much like the redemption pattern. If they were redemptions, redeemed coffees
would go from 48 to about 95 and the bank would be badly overdrawn, which suggests they are
mostly staff drinks or comps. Unconfirmed.

## Published figures over time

| When | `/grounded` coffees / meals | Why it moved |
|---|---|---|
| Before catalog IDs | 98 / 109 | |
| After catalog IDs | 125 / 121 | 39 uncounted rows found |
| 22 Sep 2026 | 47 / 33 | ADR 0001: 17 June giveaways removed |
| 23 Sep 2026 | 48 / 34 | Counting items, not rows |
| 25 Sep 2026 | 50 / 35 | Further trading |

- **Student discounts:** a figure of **$1,479** quoted for June 2026 was every discount added
  together, including one on a refund ($1,005.40 student + $451.60 `100%` + $17.25 `Half-Price`
  + $5.00 = $1,479.25). The student discount alone was $1,005.40. The monthly report now
  carries both, as `student_discounts_saved` and `all_discounts_saved`.
- **`/social-cafe`:** once the student items stopped counting as redemptions,
  `orders_excluding_redemptions` went from 7,890 to 8,028 and the average price per order from
  $8.90 to $8.80. The TUSA-funded orders now sit in the average, which is the honest result.
- `/grounded` publishes **redemptions**. Dongyi's monthly statements ("18 meals purchased for
  students") count **donations**. See the open question in `AGENTS.md`.

## Engineering notes, 22–25 September 2026

- `get_orders.py` rewritten to keep everything (commit `edf2bef`); tests added (`c67bb8c`);
  `jobs/` and `tools/` merged into `grounded/`, counting rules moved into `order_rows.py`, docs
  split into a plain-language README and a technical AGENTS.md.
- Tests found a real bug: `"".split("; ")` is `[""]`, which made single-discount rows from
  older CSVs read as $0.00.
- Mutation testing (deliberately breaking the code to check a test fails) found two gaps, both
  quantity tests covering food but not coffee.
- Mutation runs can lie: two edits of equal file size in the same second let Python reuse stale
  `__pycache__` bytecode. Clear it and set `PYTHONDONTWRITEBYTECODE=1`.
- `daily_update.sh` used `set -e` with a later `$?` check, so a failed Square pull aborted
  silently. Fixed and tested against a simulated outage.
- A change that restores a file to match the last commit is invisible to `git diff`. That is
  how a re-enabled `api_client.push` line once went unnoticed in review; grep the live file
  against `git show HEAD:` instead.
