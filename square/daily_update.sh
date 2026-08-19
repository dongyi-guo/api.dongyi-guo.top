#!/bin/bash
# Cron entry point. Runs from within square/, so cd there first if cron's
# working directory isn't already set correctly (see crontab note below).
set -e
cd "$(dirname "$0")"

set -a
source .env
set +a

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting daily Grounded Cafe update"

python3 get_orders.py
if [ $? -ne 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] get_orders.py failed, aborting before pushing stale data"
    exit 1
fi

python3 update_grounded.py

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Done"