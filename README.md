# Dongyi's API Service

A small web service that holds a few live numbers and hands them to other websites.

Right now it powers the [Impact Counter on the Grounded Social Enterprise Café website](https://www.groundedsocialenterprise.org/impact): how many coffees and meals the public has paid forward for students, and how much students have saved with their discount. Every day at 5pm the server reads the café's sales from Square (the café's till system), works out those numbers, and publishes them. Nobody has to type anything in.

TUSA / Grounded may take this over one day, so this README covers everything needed to run it.

## How it works, in one picture

```
Square (the café's till)
      ↓   every day at 5pm, the server downloads the sales
The server works out the numbers
      ↓   and publishes them at a web address, e.g. api.dongyi-guo.top/grounded
The Grounded website reads that address and shows the numbers to visitors
```

Each set of numbers lives at its own address, called a **handle**. There are two:

| Address | What it shows |
|---|---|
| `/grounded` | Coffees and meals paid forward, and money saved by the student discount. This is what the public Impact Counter shows |
| `/social-cafe` | How busy the café is: orders, revenue, orders per hour |

## What's in this folder

| Folder or file | What it is |
|---|---|
| `app/` | The web service itself |
| `index.html`, `styles/`, `scripts/` | The admin page, where you can view and edit numbers by hand |
| `grounded/` | Everything for the Grounded Café: downloading sales, working out the numbers, publishing them |
| `tests/` | Automatic checks that the numbers are worked out correctly |
| `docs/` | Records of past decisions, and notes for AI assistants |
| `data/`, `logs/` | Created by the server as it runs. Not stored in git |
| `.env` | Passwords and keys. Never stored in git |

## Setting it up on a new server

Everything below assumes the project lives at `/home/admin/api.dongyi-guo.top`. If yours lives somewhere else, change that path wherever it appears.

### 1. Get a server and a domain name

You need a server that's always on, with a domain name pointing at it. There are easier options like [Hostinger](https://www.hostinger.com/au), and lots of server and domain providers. I use Amazon AWS EC2, but you can do it like a [CHAD](https://landchad.net/).

### 2. Copy the project over and install what it needs

```bash
git clone <this repository> /home/admin/api.dongyi-guo.top
cd /home/admin/api.dongyi-guo.top
pip install -r requirements.txt
```

You need Python 3.9 or newer. `requirements.txt` is the full list of Python packages the project uses, all in one file.

### 3. Add the passwords file

Create a file called `.env` in the project folder:

```
SQUARE_ACCESS_TOKEN=      # Key to read the café's sales from Square
SQUARE_SANDBOX_TOKEN=     # Square's test key (only for testing)
SQUARE_LOCATION_ID=       # Which café in Square to read
API_ADMIN_TOKEN=          # Your admin password for this service. Make one up
API_BASE_URL=http://127.0.0.1:55500
```

**Why a separate file:** these are secrets. Keeping them out of the code means the code can be shared and stored in git without leaking them.

If you don't know the location ID, this looks it up once the Square key is filled in:

```bash
python3 grounded/diagnostics.py locations
```

### 4. Keep the service running

The server needs to start the service when it boots, and restart it if it ever crashes. On most Linux servers that's done by `systemd`. Create `/etc/systemd/system/myapi.service`:

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

Put the same admin password here as in `.env`, then start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now myapi
```

Two things to get right:

- **It must say `app.main:app`**, not `main:app`. This is the one mistake that takes the whole site down.
- **Run `daemon-reload` after every edit to this file.** Without it, the server keeps using the old version.

### 5. Put it on the web

The service only listens inside the server, which keeps it private by default. To reach it from the internet, set up Nginx or Apache to pass your domain's visitors through to `127.0.0.1:55500`. Again, you can learn how to do it like a [CHAD](https://landchad.net/).

### 6. Schedule the daily update

Run `crontab -e` (the server's built-in scheduler) and add these two lines:

```
0 17 * * * /home/admin/api.dongyi-guo.top/grounded/daily_update.sh >> /home/admin/api.dongyi-guo.top/logs/cron.log 2>&1
30 17 1 * * /usr/bin/python3 /home/admin/api.dongyi-guo.top/grounded/update_grounded_monthly.py --month $(date -d yesterday +\%Y-\%m) >> /home/admin/api.dongyi-guo.top/logs/cron.log 2>&1
```

- **The first line** runs every day at 5pm. It downloads the sales and publishes both sets of numbers. If the download fails, it stops before publishing anything. **Why:** a failed download would otherwise publish wrong numbers.
- **The second line** runs on the 1st of each month at 5:30pm and writes a month-by-month report to `data/grounded_monthly_summary.csv`, for reporting to the café and TUSA. It publishes nothing. **Why it's separate:** if the report ever fails, the daily numbers still update. **Why 5:30pm:** it waits until the 5pm download has finished.
- Everything they print goes to `logs/cron.log`. That's the first place to look if something seems off.

Type the `\%` exactly as shown. Without the backslash, the scheduler cuts the line short.

### 7. Check it worked

```bash
./grounded/daily_update.sh                          # run the update now, instead of waiting for 5pm
curl https://api.dongyi-guo.top/grounded            # should show the three numbers
```

The first run also creates `/grounded` and `/social-cafe`, so there's nothing to set up in the admin page.

## Updating the server after a change

Whenever the code changes, on the server:

```bash
cd /home/admin/api.dongyi-guo.top
git status                      # should say "nothing to commit"
git pull
pip install -r requirements.txt
```

**Why `git status` first:** if someone edited files directly on the server, `git pull` can clash with those edits. Better to find out before pulling.

If the change touched `app/`, also run `sudo systemctl restart myapi`. **Why:** the service loads its code once at startup. The daily update doesn't need a restart, because it runs fresh each time.

### One-off: moving from `jobs/` and `tools/` to `grounded/` (September 2026)

The update scripts moved from `jobs/` and `tools/` into one folder, `grounded/`. A server that was set up before this move needs three extra steps after `git pull`:

1. **Fix the schedule.** Run `crontab -e`, and in both lines change `/jobs/` to `/grounded/`. **Why:** the scheduler still points at the old folder, so the 5pm update will fail until you change it.
2. **Delete the old folders.** Git removes the files it knows about, but can leave behind empty folders holding Python's cache files. Check they hold nothing else, then delete them:
   ```bash
   find jobs tools -type f        # should list only .pyc files, or nothing at all
   rm -rf jobs tools
   ```
3. **Run the update once by hand** (step 7 above), so you know it works before 5pm.

No restart is needed: the web service itself didn't change.

## Using it day to day

The numbers update themselves at 5pm. You only need the commands below if you want to look closer.

**Get a month's report:**

```bash
python3 grounded/update_grounded_monthly.py --month 2026-07               # July alone
python3 grounded/update_grounded_monthly.py --month 2026-07 --cumulative  # everything from opening to the end of July
```

**Refresh the numbers now** instead of waiting for 5pm:

```bash
./grounded/daily_update.sh
```

This publishes to the live website, exactly as the 5pm run does.

**Edit a number by hand:** open the admin page at your domain, unlock it with the admin password, and change it there. The 5pm run will overwrite it again, so this is only for a quick fix.

## When something goes wrong

**The website shows "502 Bad Gateway".** The service isn't running. See why:

```bash
sudo journalctl -u myapi -n 50 --no-pager
```

If it says `Could not import module "main"`, the service file says `main:app` where it should say `app.main:app` (step 4). Fix it, run `sudo systemctl daemon-reload`, then restart.

**The numbers didn't update.** Look at the end of the log:

```bash
tail -50 logs/cron.log
```

A line saying `get_orders.py failed, aborting` means Square couldn't be reached, or the Square key in `.env` has expired. Nothing wrong was published; the numbers just stayed as they were.

**The numbers look too low.** Some items sold at the till might not be recognised as coffee or food. Check for them:

```bash
grep Unmapped data/grounded_cafe_orders.csv
```

A few are normal: they're amounts typed in at the till without choosing a product. A lot of them usually means the café added a new category of product in Square. The update prints a warning naming it, and a developer needs to add it to the list in `grounded/get_orders.py`.

**The admin page says the data can't be loaded.** Unlock it with the admin password and use **Reset store**. It backs up the broken file before starting fresh.

## For developers and AI assistants

- **`AGENTS.md`**: the technical detail. How the numbers are worked out, what's in each file, and the traps to avoid. Read this before changing any code.
- **`CONTEXT.md`**: what the words mean. "Redemption", "banked" and "order" each have one exact meaning here.
- **`docs/adr/`**: why past decisions were made, such as not counting the TUSA-funded giveaways from 17 June 2026.
- **`docs/history.md`**: what was found in the café's data, and why the public numbers changed over time.
- **`CLAUDE.md`**: one line pointing Claude Code to `AGENTS.md`.

To run the automatic checks: `python3 -m pytest`. They need no passwords and no internet.
