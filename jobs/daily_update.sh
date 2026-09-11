#!/bin/bash
# Cron entry point. Resolves the project root from this script's own location,
# so the crontab line doesn't need to set a working directory.
set -e
cd "$(dirname "$0")/.."

mkdir -p data logs

set -a
source ./.env
set +a

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting daily Grounded Cafe update"

python3 jobs/get_orders.py
if [ $? -ne 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] get_orders.py failed, aborting before pushing stale data"
    exit 1
fi

python3 jobs/update_grounded.py
python3 jobs/update_social_cafe.py

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Done"
