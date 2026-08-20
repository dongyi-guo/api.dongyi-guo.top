# Dongyi's API Service

This is my API service hub for other project's testing purposes, it serves dynamic, non-nested, flat JSON responses.

Currently this API service is serving the automated [Impact Counter for Grounded Social Enterprise Café](https://www.groundedsocialenterprise.org/impact). TUSA / Grounded may want to migrate this, this README file will also provide all the necessary information.

## Saved API Handles and Values

Upon deployment of the API site, `api_store.json` will be genereated to store saved handle and values, it is intentionally to be server-local. 

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

If it is broken and the admin UI reports that `api_store.json` cannot be loaded, unlock with the admin token and use **Reset store**. The reset action backs up the broken file before writing the default `/value` handle.

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
Environment=API_STORE_PATH=/home/admin/api.dongyi-guo.top/api_store.json
Environment=API_STATIC_DIR=/home/admin/api.dongyi-guo.top/static
Environment=API_CORS_ORIGINS=*
ExecStart=/home/admin/.local/bin/uvicorn main:app --host 127.0.0.1 --port 55500 --proxy-headers
Restart=always
RestartSec=3
[Install]
WantedBy=multi-user.target
```

Change as your need, make sure you put a token / password as you want, and change the absolute path based on your server.

## .env File

Under `square/` sub-directory, create an `.env` file so the project can read requried private information:

```
SQUARE_ACCESS_TOKEN=      # Square production access token
SQUARE_SANDBOX_TOKEN=     # Square sandbox token (for testing only)
SQUARE_LOCATION_ID=       # Grounded Café's Square location ID
API_ADMIN_TOKEN=          # Must match the token in myapi.service
API_BASE_URL=http://127.0.0.1:55500   # Internal address of the API server
```

## Sqaure API

All works related to Sqaure API is located under `square/` subfolder.

This folder contains:
 
| File | Purpose |
|---|---|
| `daily_update.sh` | The script cron actually runs. Runs the two Python scripts below in order, and stops early if the Square data pull fails, to avoid publishing stale numbers. |
| `get_orders.py` | Pulls the day's completed orders from Square, processes discounts and categories, writes `grounded_cafe_orders.csv` |
| `update_grounded.py` | Reads that CSV, counts up the three stats, and pushes them to the `/grounded` API handle |
| `get_locations.py`, `list_discounts.py`, `check_categories.py` | Diagnostic/reference scripts, not run automatically, used when setting up or troubleshooting |
| `.env` | Holds all credentials this pipeline needs (see Section 4.3) |
| `README.md` | Technical documentation for the scripts themselves, more detailed than this handover document |

TLDR is: `get_orders.py` is the core retrieving all the transactions from Square API and generate a CSV file based on the information ( `grounded_cafe_orders.csv` ), `update_grounded.py` interprets the CSV file for the count, and update the count to the API service. `daily_update.sh` is the wrapper for both so run it will do both `.py` files.

## Cron Job

A cron job is a scheduled repeating task that set in desired time point, interval and many other configuring flexibilities.

For updating the data from Square POS, counting the desired number, and updated to the Grounded website. A cron job can be set to make this automatically so the data fits the automatically updated date for Impact Counter.

Currently, this update happens 5pm everyday:

```
0 17 * * * /home/admin/api.dongyi-guo.top/square/daily_update.sh >> /home/admin/api.dongyi-guo.top/square/cron.log 2>&1
```
