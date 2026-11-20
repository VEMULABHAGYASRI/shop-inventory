# Design notes

Why the code is shaped the way it is, and how to change it.

## Layers

```
HTTP request
  -> routes/      parse & validate input (schemas/), check login, call a service
  -> services/    business rules; raise errors from app/errors.py
  -> models/      SQLAlchemy tables
  -> database.py  SQLite
```

Each layer only calls the one below it. Consequences:

- **Services never import FastAPI.** They take a `Session` and plain values.
  That's why `app/cli.py` can reuse `auth_service.create_user`, and why
  business rules can be tested without HTTP.
- **Routes contain no logic.** If you find yourself writing an `if` about
  stock in a route, it belongs in a service.
- **Schemas != models.** A model is how data is stored; a schema is what the
  API accepts or returns. `User.password_hash` exists in the model but no
  response schema exposes it. `ItemUpdate` has no `quantity`, so the API
  physically can't set stock directly.

## Key decisions

**Stock changes only through movements.** `Item.quantity` is changed in one
place: `services/stock_service.apply_movement`. Each change writes a
`StockMovement` row (who, when, how much, why, quantity after). This makes
"where did 5 boxes go?" answerable, and it's why opening stock is recorded
as a movement rather than set directly.

**Atomic stock update.** The quantity is changed with a single
`UPDATE ... SET quantity = quantity + :change WHERE quantity + :change >= 0`.
Reading the value in Python, subtracting, and writing it back would let two
simultaneous sales of the last item both succeed. The database also has a
CHECK constraint so quantity can never be negative even if a bug slips past.

**Reason and sign must agree.** `sold`/`damaged` must be negative,
`received`/`returned` positive, `adjustment` either. Enforced in
`schemas/movement.py`, so bad input is a 422 before any logic runs.

**Money as integer cents.** `unit_price_cents = 1299` means 12.99. Floats
can't represent most decimal amounts exactly.

**Times stored in UTC.** The browser converts to local time for display.

**Replaceable external integration.** Low-stock alerts go through the
`Notifier` protocol (`notifications/base.py`). `create_app(settings,
notifier=...)` takes one as an argument; production builds it from config
(`notifications/factory.py`), tests pass `tests/fakes.FakeNotifier`. Alerts
fire only when an item *crosses* its reorder level, are sent after the
database commit, and a failing notifier is logged but never fails the sale.

**App factory instead of a global app.** Everything the app depends on is
passed into `create_app` and stored on `app.state`; dependencies in
`dependencies.py` read from there. Each test gets a fresh app with an
in-memory database.

**Errors.** Services raise `NotFoundError`, `ConflictError`,
`InsufficientStockError`, ... (`errors.py`). One set of handlers turns them,
validation errors, unknown URLs, and unexpected crashes into the same JSON
shape. Unexpected errors are logged with a traceback but the client only sees
`internal_error`, never internals.

**Logging.** Every request gets an 8-character id, included in every log line
for that request, in the `X-Request-ID` response header, and in error bodies.
When someone reports an error, search the log for the id.

**Authentication.** Passwords are hashed with scrypt (standard library,
random salt per user, parameters stored in the hash). Login returns a JWT
signed with `INVENTORY_SECRET_KEY`, valid for 12 hours by default. No public
sign-up: the first user is made with the CLI, then logged-in users can add
others. Unknown-username and wrong-password logins give the same message and
take the same time. The app refuses to start with a missing or short key.

**Frontend.** Plain JS modules, no build step. `api.js` is the only file that
calls the server. Server data is always inserted with `textContent`, never
`innerHTML`, to prevent script injection via item names or notes. The token is
kept in `localStorage`, which is simple but readable by any script on the
page. That's acceptable because the page loads no third-party scripts; keep
it that way.

## Known limits / possible next steps

- **No database migrations.** `create_all` creates missing tables but won't
  alter existing ones. Before your first schema change on real data, add
  Alembic (or, for a one-off, write the `ALTER TABLE` by hand after a backup).
- **All users are equal.** No admin/staff roles yet.
- **No pagination** on the item list. Fine for hundreds or a few thousand items.
- **Deleting an item deletes its history.** If you'd rather keep it, add an
  `archived` flag instead of deleting.

## Recipes

**Add a field to items (e.g. `supplier`):**
1. `models/item.py`: add the column.
2. `schemas/item.py`: add it to `ItemCreate`, `ItemUpdate`, `ItemOut`.
3. `static/index.html` + `static/app.js`: add the input and table column.
4. Add a test in `tests/test_items.py`.
5. Existing database: `sqlite3 data/inventory.db "ALTER TABLE items ADD COLUMN supplier VARCHAR(100)"`
   (back up first), or adopt Alembic.

**Add a new movement reason:** add it to `MovementReason` in
`schemas/movement.py` (and to `POSITIVE_ONLY`/`NEGATIVE_ONLY` if it has a
fixed sign), then add an `<option>` in `static/index.html`.

**Add a new kind of notifier (e.g. email):** create a class with a
`low_stock(self, alert)` method in `app/notifications/`, choose it in
`factory.py` based on a new setting in `config.py` and `.env.example`, and
test it the way `tests/test_notifications.py` tests the webhook.

## Running it for real

- Keep it on your local network. If you need access from outside, put it
  behind HTTPS (e.g. Caddy as a reverse proxy, or Tailscale) - never send
  passwords or tokens over plain HTTP across the internet.
- Run it as a service so it starts on boot (a systemd unit running the
  `uvicorn` command from the README with `WorkingDirectory` set to the project).
- Back up `data/inventory.db` regularly (command in the README).
