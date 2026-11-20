# Shop Inventory

A small inventory tool for a family shop: track items, record every stock
change (sold, received, damaged, ...), see who did what, and get an alert when
something needs reordering.

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy, SQLite
- **Frontend:** plain HTML + JavaScript (no build step), served by the backend
- **Tests:** pytest, fully offline

Design notes and "how do I change X" recipes: [docs/DESIGN.md](docs/DESIGN.md).

## Setup (Linux)

```bash
git clone <your-repo-url> shop-inventory
cd shop-inventory

# 1. Create a virtual environment and install dependencies
python3 -m venv .venv            # needs: sudo apt install python3-venv
.venv/bin/pip install -r requirements.txt
#    (or, with uv:  uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt)

# 2. Create the first login (there is no public sign-up page)
.venv/bin/python -m app.cli create-user mum
```

No configuration is required: there are no keys to generate and `.env` is
optional. Copy `.env.example` to `.env` only if you want to change a default
(database location, login duration, phone alerts).

## Run

```bash
.venv/bin/uvicorn --factory app.main:create_app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Interactive API docs are at http://127.0.0.1:8000/docs.

To use it from other devices in the shop (e.g. a tablet on the same Wi-Fi), use
`--host 0.0.0.0` and open `http://<this-computer's-ip>:8000`. Read the
"Running it for real" section in docs/DESIGN.md before exposing it beyond your
local network.

## Test

```bash
.venv/bin/pytest
```

Tests use an in-memory database and a fake notifier: they never read your
`.env`, never touch `data/inventory.db`, and never use the network.

## Project layout

```
app/
  main.py            create_app(): wires everything together
  config.py          settings from environment / .env
  database.py        engine, sessions, table creation
  models/            SQLAlchemy tables: User, Item, StockMovement
  schemas/           Pydantic request/response shapes + validation
  services/          business logic (no FastAPI imports)
  routes/            HTTP endpoints (thin: validate -> call service -> respond)
  notifications/     Notifier interface + log and webhook implementations
  security.py        password hashing, login tokens
  errors.py          exception classes + the single error response format
  logging_config.py  log format with per-request ids
  dependencies.py    FastAPI dependencies (db session, current user, notifier)
  cli.py             admin commands (create-user)
static/              the web UI (index.html, app.js, api.js, styles.css)
tests/               pytest suite; tests/fakes.py holds test stand-ins
data/                the SQLite database lives here (gitignored)
```

## API overview

All endpoints except login and health need `Authorization: Bearer <token>`.

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/login` | Log in, get a token |
| POST | `/api/auth/logout` | Log out (token stops working) |
| GET | `/api/auth/me` | Who am I |
| GET/POST | `/api/users` | List / add family members |
| GET | `/api/items?search=&category=&low_stock=true` | List items |
| POST | `/api/items` | Add item (optional `initial_quantity`) |
| GET/PATCH/DELETE | `/api/items/{id}` | View / edit / delete an item |
| POST | `/api/items/{id}/movements` | Record a stock change |
| GET | `/api/items/{id}/movements` | One item's history |
| GET | `/api/movements` | Recent activity, all items |
| GET | `/api/categories` | Categories in use |
| GET | `/api/health` | Is the server up |

Errors always look like:

```json
{"error": {"code": "insufficient_stock", "message": "Cannot remove 9 of TEA-100: only 4 in stock",
           "details": [], "request_id": "a80c953a"}}
```

## Low-stock phone alerts (optional)

Set `INVENTORY_LOW_STOCK_WEBHOOK_URL` in `.env` to an
[ntfy.sh](https://ntfy.sh) topic URL with a hard-to-guess name (e.g.
`https://ntfy.sh/our-shop-stock-k3j9x2`), install the ntfy app and subscribe
to that topic. Without it, alerts only go to the server log.

## Backups

All data is in `data/inventory.db`. Back it up safely while the app runs:

```bash
sqlite3 data/inventory.db ".backup 'backup-$(date +%F).db'"
```
