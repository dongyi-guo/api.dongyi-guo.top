# Diagnostics

One-off checks for the Grounded Cafe Square pipeline. Nothing in this folder runs on a
schedule. Reach for these when setting up credentials for the first time, or when the
daily numbers look wrong and you need to see what Square actually holds.

All of them read the `.env` file in the project root, and resolve paths from their own
location, so you can run them from any directory.

```bash
python3 tools/diagnostics.py <command>
```

| Command | What it answers |
| --- | --- |
| `locations` | Which Square locations exist, and what their IDs are. Use this to fill in `SQUARE_LOCATION_ID` during first-time setup. |
| `discounts` | Which discounts are configured in the catalog, with their IDs and values. Use this to confirm the tracked IDs near the top of `jobs/get_orders.py`. |
| `categories` | Which catalog categories exist on the account. |
| `coverage` | How many catalog items actually have a category assigned. As of the last check this was 0 of 67, which is why the pipeline classifies items through the manual `ITEM_CATEGORY` map instead of asking Square. |
| `student-share` | What share of the rows in the generated CSV are student-related. A rough volume check, not an impact number. |

The four catalog commands need `SQUARE_ACCESS_TOKEN`. `student-share` needs no token, but
does need `data/grounded_cafe_orders.csv`, so run `jobs/get_orders.py` first.

## Typical first-time setup

```bash
python3 tools/diagnostics.py locations    # copy the ID into .env
python3 tools/diagnostics.py discounts    # confirm the tracked discount IDs
python3 tools/diagnostics.py coverage     # confirm categories are still unassigned
```

## When the numbers look wrong

Start with the CSV rather than these commands. Any item name the pipeline does not
recognise is written to the CSV as `Unmapped` rather than guessed at, and unmapped rows
are not counted in the published totals. Check for them first:

```bash
grep Unmapped data/grounded_cafe_orders.csv
```

If unmapped rows show up, the fix is to add the new item name to `ITEM_CATEGORY` in
`jobs/get_orders.py`. Item names drift between the Square catalog and live order data,
including typos, so this map needs occasional hand maintenance.
