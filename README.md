# Dongyi's API Service

This is my API service hub for other project's testing purposes, it serves dynamic, non-nested, flat JSON responses.

Currently this API service is serving the automated [Impact Counter for Grounded Social Enterprise Café](https://www.groundedsocialenterprise.org/impact). TUSA / Grounded may want to migrate this, this README file will also provide all the necessary information.

## Project Structure

```
index.html              Admin page, served at /
styles/admin.css        Served at /styles/admin.css
scripts/admin.js        Browser JavaScript, served at /scripts/admin.js
app/main.py             The FastAPI service itself
jobs/                   Everything cron runs: daily_update.sh, get_orders.py, update_grounded.py
tools/diagnostics.py    Run by hand for setup and troubleshooting, never by cron
data/                   Runtime files, gitignored: api_store.json, grounded_cafe_orders.csv
logs/cron.log           Cron output, gitignored
.env                    Credentials, gitignored
```

Folders are split by how a file is used, not by what language it is written in.
Anything under `jobs/` runs on a schedule; anything under `tools/` only runs when
you run it. Both `data/` and `logs/` are created automatically on first use.

Each folder that holds scripts has its own README: `jobs/README.md` for the scheduled
pipeline, `tools/README.md` for the manual diagnostics.

## Saved API Handles and Values

Upon deployment of the API site, `data/api_store.json` will be generated to store saved handle and values, it is intentionally to be server-local. 

A valid JSON will have structure as:

```json
{
  "value": { // Public Handle
    "value": 42 // Key / Value Pairs
  }
}
```

The top-level key is the public handle, so this example serves `GET /value` and `POST /value`.

**Each handle value must be one flat object of key/value pairs. Nested objects and arrays are rejected.**

If it is broken and the admin UI reports that `data/api_store.json` cannot be loaded, unlock with the admin token and use **Reset store**. The reset action backs up the broken file before writing the default `/value` handle.

## Your Server

You will need a server with a public domain name, there are easier options like [Hostinger](https://www.hostinger.com/au), and there are lots of server providers and domain providers. I use Amazon AWS EC2, but you can do it like a [CHAD](https://landchad.net/).

## Python

This service requires python, make sure you have python installed and created your virtual environment if required on your server. 

Then install the dependencies:

```bash
pip install -r requirements.txt
```

## Nginx / Apache

Use Nginx or Apache to setup this folder as web service, again, you can learn how to do it like a [CHAD](https://landchad.net/).

## System Service

You can write your own service file in your supported system service that your server uses such as `systemd` , `OpenRC`, `SysVinit` or `runit` as there are some environment values to fire up the project. I use `systemd` and wrote a `myapi.service`: 

```
[Unit]
Description=Dongyi's Dynamic FastAPI Service
After=network.target

[Service]
User=admin
WorkingDirectory=/home/admin/api.dongyi-guo.top
Environment=API_ADMIN_TOKEN=[Your Token]
Environment=API_STORE_PATH=/home/admin/api.dongyi-guo.top/data/api_store.json
Environment=API_CORS_ORIGINS=*
ExecStart=/home/admin/.local/bin/uvicorn app.main:app --host 127.0.0.1 --port 55500 --proxy-headers
Restart=always
RestartSec=3
[Install]
WantedBy=multi-user.target
```

Change as your need, make sure you put a token / password as you want, and change the absolute path based on your server.

Two details matter here:

- The app is `app.main:app`, not `main:app`, because `main.py` lives in `app/`. Getting
  this wrong is the one mistake that takes the site down, with `Could not import module "main"`
  in the journal and a 502 from Nginx.
- There is no `API_STATIC_DIR`. The site files are served from `WorkingDirectory`.
  Set `API_SITE_DIR` only if you keep them somewhere else.

After any edit to this file run `sudo systemctl daemon-reload` before restarting, or
systemd will keep using the version it already cached.

## .env File

In the project root, create an `.env` file so the project can read required private information:

```
SQUARE_ACCESS_TOKEN=      # Square production access token
SQUARE_SANDBOX_TOKEN=     # Square sandbox token (for testing only)
SQUARE_LOCATION_ID=       # Grounded Café's Square location ID
API_ADMIN_TOKEN=          # Must match the token in myapi.service
API_BASE_URL=http://127.0.0.1:55500   # Internal address of the API server
```

## Square API

The Square work is split by how often it runs. `jobs/` is what cron touches, `tools/` is what you touch.

| File | Purpose |
|---|---|
| `jobs/daily_update.sh` | The script cron actually runs. Runs the two Python scripts below in order, and stops early if the Square data pull fails, to avoid publishing stale numbers. |
| `jobs/get_orders.py` | Pulls the day's completed orders from Square, processes discounts and categories, writes `data/grounded_cafe_orders.csv` |
| `jobs/update_grounded.py` | Reads that CSV, counts up the three impact stats, and pushes them to the `/grounded` API handle |
| `jobs/update_social_cafe.py` | Reads the same CSV for trading statistics, and pushes them to the `/social-cafe` API handle |
| `jobs/update_grounded_monthly.py` | Reads the same CSV and writes `data/grounded_monthly_summary.csv`, a month-by-month breakdown for reporting. Publishes nothing. `--month YYYY-MM` for one month, `--cumulative` for totals since opening |
| `jobs/order_rows.py` | Shared CSV reading helpers, used by every script that reads the orders CSV |
| `jobs/api_client.py` | Shared push helper. Creates a handle if it does not exist yet, updates it if it does |
| `tools/diagnostics.py` | Diagnostic subcommands (`locations`, `discounts`, `categories`, `coverage`, `student-share`), not run automatically, used when setting up or troubleshooting |
| `.env` | Holds all credentials this pipeline needs, in the project root |
| `jobs/README.md`, `tools/README.md` | Technical documentation for the scripts themselves, more detailed than this handover document |

TLDR is: `get_orders.py` is the core retrieving all the transactions from Square API and generate a CSV file based on the information ( `data/grounded_cafe_orders.csv` ), `update_grounded.py` interprets the CSV file for the count, and update the count to the API service. `daily_update.sh` is the wrapper for both so run it will do both `.py` files.

Every script resolves its paths from its own location, so you can run any of them
from anywhere:

```bash
python3 tools/diagnostics.py coverage
```

### Published handles

| Handle | Answers | Keys |
|---|---|---|
| `/grounded` | How much was given away | `coffees_paid_forward`, `meals_paid_forward`, `student_discounts_saved` |
| `/social-cafe` | How busy the café is and what an order brings in | `total_orders`, `orders_excluding_redemptions`, `total_revenue`, `trading_days`, `hours_per_day`, `avg_orders_per_hour`, `avg_price_per_order` |

The two handles count orders differently, on purpose. See `CONTEXT.md` for the
definitions. The averages are published unrounded, so a consumer such as the
Break-Even Calculator keeps full precision and does its own formatting.

Both handles are created automatically on first push, so a fresh deployment
needs no manual setup in the admin panel.

## Cron Job

A cron job is a scheduled repeating task that set in desired time point, interval and many other configuring flexibilities.

For updating the data from Square POS, counting the desired number, and updated to the Grounded website. A cron job can be set to make this automatically so the data fits the automatically updated date for Impact Counter.

Currently, this update happens 5pm everyday:

```
0 17 * * * /home/admin/api.dongyi-guo.top/jobs/daily_update.sh >> /home/admin/api.dongyi-guo.top/logs/cron.log 2>&1
```

### Monthly summary

A second, separate job writes the month-by-month reporting CSV. It publishes nothing, so it is
deliberately not part of `daily_update.sh`: a failure here must never stop the daily figures,
and it only needs to run once a month.

It runs on the 1st at 5:30pm, half an hour after the daily job, so the orders CSV it reads has
already been refreshed and the month just ended is complete:

```
30 17 1 * * /usr/bin/python3 /home/admin/api.dongyi-guo.top/jobs/update_grounded_monthly.py --month $(date -d yesterday +\%Y-\%m) >> /home/admin/api.dongyi-guo.top/logs/cron.log 2>&1
```

`--month` is required, so cron has to name one. Running on the 1st, *yesterday* is always the
last day of the month just finished, which is the month to report. The `%` signs must be
backslash-escaped in a crontab, or cron truncates the command at the first one.

That `date -d` is GNU date, which is what the Linux server has. On macOS the equivalent is
`date -v-1d +%Y-%m`, so don't copy this line straight into a local crontab.

Install both with `crontab -e`. The CSV is rewritten in full each run and always holds every
month, so running this by hand at any time is safe and never duplicates a month.

By hand, it reports either view of any month:

```bash
python3 jobs/update_grounded_monthly.py --month 2026-07               # July alone
python3 jobs/update_grounded_monthly.py --month 2026-07 --cumulative  # since 9 June
```

## Troubleshooting

### 502 from Nginx

Nginx is up but the app is not listening, which means the service failed to start:

```bash
sudo journalctl -u myapi -n 50 --no-pager
```

`Could not import module "main"` means the unit is on the wrong command. `ExecStart` must
say `app.main:app`, because `main.py` lives in `app/`. Fix it, then run
`sudo systemctl daemon-reload` before starting again. The reload is the step that is easy
to miss, and without it systemd keeps running the cached old unit.

### The impact numbers look too low

Any item name the pipeline does not recognise is written to the CSV as `Unmapped` and is
not counted in the published totals, deliberately, so it fails loudly rather than
guessing. Check for them after a run:

```bash
grep Unmapped data/grounded_cafe_orders.csv
```

The fix is to add the missing item name to `ITEM_CATEGORY` in `jobs/get_orders.py`. Item
names drift between the Square catalog and live order data, including typos, so this map
needs occasional hand maintenance.
