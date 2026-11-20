// UI logic. Rule of thumb in this file: data from the server is only ever
// inserted with textContent (via the `cell`/`el` helpers), never innerHTML,
// so an item called "<script>..." is shown as text, not executed.
import { api, auth, ApiError } from "./api.js";

const $ = (sel) => document.querySelector(sel);
const NEGATIVE = new Set(["sold", "damaged"]);

// ---------- small helpers ----------
function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = text;
  if (className) node.className = className;
  return node;
}
const cell = (text, className) => el("td", text, className);

const formatPrice = (cents) => (cents / 100).toFixed(2);
const parsePrice = (text) => Math.round(parseFloat(text) * 100);
const formatTime = (iso) => new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z").toLocaleString();
const signed = (n) => (n > 0 ? `+${n}` : String(n));

function showError(target, err) {
  target.textContent = err instanceof ApiError ? err.describe() : String(err);
  target.hidden = false;
}

// Run an async UI action; show any error in the page banner.
async function guarded(fn) {
  const banner = $("#app-error");
  banner.hidden = true;
  try { await fn(); } catch (err) { showError(banner, err); }
}

// ---------- login / logout ----------
function showLogin() {
  $("#app-view").hidden = true;
  $("#login-view").hidden = false;
}

async function showApp() {
  const me = await api.me();
  $("#current-user").textContent = `Logged in as ${me.username}`;
  $("#login-view").hidden = true;
  $("#app-view").hidden = false;
  await refreshItems();
}

auth.onLoggedOut = showLogin;

$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  $("#login-error").textContent = "";
  try {
    const { access_token } = await api.login(form.get("username"), form.get("password"));
    auth.token = access_token;
    e.target.reset();
    await showApp();
  } catch (err) {
    showError($("#login-error"), err);
  }
});

$("#logout").addEventListener("click", () => {
  auth.token = null;
  showLogin();
});

// ---------- tabs ----------
document.querySelectorAll(".tab").forEach((btn) =>
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b === btn));
    $("#items-tab").hidden = btn.dataset.tab !== "items";
    $("#activity-tab").hidden = btn.dataset.tab !== "activity";
    guarded(btn.dataset.tab === "items" ? refreshItems : refreshActivity);
  }),
);

// ---------- items list ----------
let items = [];

async function refreshItems() {
  const filters = {
    search: $("#search").value.trim(),
    category: $("#category-filter").value,
    low_stock: $("#low-stock-filter").checked ? "true" : "",
  };
  const [list, categories] = await Promise.all([api.listItems(filters), api.listCategories()]);
  items = list;
  renderCategories(categories);
  renderItems();
}

function renderCategories(categories) {
  const select = $("#category-filter");
  const current = select.value;
  select.replaceChildren(el("option", "All categories"));
  select.firstChild.value = "";
  $("#category-list").replaceChildren();
  for (const c of categories) {
    const opt = el("option", c);
    opt.value = c;
    select.append(opt);
    $("#category-list").append(opt.cloneNode(true));
  }
  select.value = categories.includes(current) ? current : "";
}

function renderItems() {
  const body = $("#items-body");
  body.replaceChildren();
  $("#items-empty").hidden = items.length > 0;
  for (const item of items) {
    const row = el("tr", null, item.is_low_stock ? "low" : "");
    row.append(
      cell(item.sku, "mono"),
      cell(item.name),
      cell(item.category ?? ""),
      cell(item.quantity, "num strong"),
      cell(item.reorder_level, "num"),
      cell(formatPrice(item.unit_price_cents), "num"),
    );
    const actions = el("td", null, "row-actions");
    const button = (label, handler, cls) => {
      const b = el("button", label, cls);
      b.addEventListener("click", () => handler(item));
      actions.append(b);
    };
    button("Stock ±", openMoveDialog);
    button("History", openHistory, "secondary");
    button("Edit", openItemDialog, "secondary");
    row.append(actions);
    body.append(row);
  }
}

let searchTimer;
$("#search").addEventListener("input", () => {
  clearTimeout(searchTimer); // wait until typing pauses
  searchTimer = setTimeout(() => guarded(refreshItems), 250);
});
$("#category-filter").addEventListener("change", () => guarded(refreshItems));
$("#low-stock-filter").addEventListener("change", () => guarded(refreshItems));

// ---------- add / edit item ----------
let editing = null; // the item being edited, or null when adding

function openItemDialog(item = null) {
  editing = item;
  const form = $("#item-form");
  form.reset();
  $("#item-error").textContent = "";
  $("#item-dialog-title").textContent = item ? `Edit ${item.sku}` : "Add item";
  $("#initial-qty-label").hidden = !!item; // stock changes go through movements
  $("#delete-item").hidden = !item;
  if (item) {
    form.sku.value = item.sku;
    form.name.value = item.name;
    form.category.value = item.category ?? "";
    form.reorder_level.value = item.reorder_level;
    form.price.value = formatPrice(item.unit_price_cents);
  }
  $("#item-dialog").showModal();
}
$("#add-item").addEventListener("click", () => openItemDialog());

$("#item-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const data = {
    sku: form.sku.value,
    name: form.name.value,
    category: form.category.value.trim() || null,
    reorder_level: Number(form.reorder_level.value),
    unit_price_cents: parsePrice(form.price.value),
  };
  try {
    if (editing) await api.updateItem(editing.id, data);
    else await api.createItem({ ...data, initial_quantity: Number(form.initial_quantity.value || 0) });
    $("#item-dialog").close();
    await refreshItems();
  } catch (err) {
    showError($("#item-error"), err);
  }
});

$("#delete-item").addEventListener("click", async () => {
  if (!confirm(`Delete ${editing.name}? Its stock history is deleted too.`)) return;
  try {
    await api.deleteItem(editing.id);
    $("#item-dialog").close();
    await refreshItems();
  } catch (err) {
    showError($("#item-error"), err);
  }
});

// ---------- stock movements ----------
let moving = null;

function updateMoveHint() {
  const form = $("#move-form");
  const reason = form.reason.value;
  const adjustment = reason === "adjustment";
  form.amount.min = adjustment ? "" : "1";
  $("#move-hint").textContent = adjustment
    ? "Use a negative number to remove stock, positive to add."
    : NEGATIVE.has(reason) ? "This many will be removed from stock." : "This many will be added to stock.";
}

function openMoveDialog(item) {
  moving = item;
  const form = $("#move-form");
  form.reset();
  $("#move-error").textContent = "";
  $("#move-item-name").textContent = item.name;
  $("#move-current").textContent = item.quantity;
  updateMoveHint();
  $("#move-dialog").showModal();
}
$("#move-form").reason.addEventListener("change", updateMoveHint);

$("#move-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const reason = form.reason.value;
  const amount = Number(form.amount.value);
  // Users type "3 sold"; the API wants change = -3.
  const change = reason === "adjustment" ? amount : NEGATIVE.has(reason) ? -Math.abs(amount) : Math.abs(amount);
  try {
    await api.recordMovement(moving.id, { change, reason, note: form.note.value.trim() || null });
    $("#move-dialog").close();
    await refreshItems();
  } catch (err) {
    showError($("#move-error"), err);
  }
});

// ---------- history & activity ----------
function movementRow(m, withItem) {
  const row = el("tr");
  row.append(cell(formatTime(m.created_at)));
  if (withItem) row.append(cell(`${m.item.name} (${m.item.sku})`));
  row.append(
    cell(signed(m.change), `num ${m.change < 0 ? "neg" : "pos"}`),
    cell(m.reason),
    cell(m.quantity_after, "num"),
    cell(m.user.username),
    cell(m.note ?? "", "muted"),
  );
  return row;
}

async function openHistory(item) {
  await guarded(async () => {
    const history = await api.itemHistory(item.id);
    $("#history-item-name").textContent = item.name;
    $("#history-body").replaceChildren(...history.map((m) => movementRow(m, false)));
    $("#history-dialog").showModal();
  });
}

async function refreshActivity() {
  const feed = await api.recentActivity();
  $("#activity-body").replaceChildren(...feed.map((m) => movementRow(m, true)));
}

// Any button marked data-close closes its dialog.
document.querySelectorAll("[data-close]").forEach((b) =>
  b.addEventListener("click", () => b.closest("dialog").close()),
);

// ---------- start ----------
if (auth.token) guarded(showApp);
else showLogin();
