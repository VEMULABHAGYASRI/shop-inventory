// The only file that talks to the server.
// Adds the login token, and turns the API's error format into JS errors.

const TOKEN_KEY = "inventory_token";

export class ApiError extends Error {
  constructor(status, error) {
    super(error.message);
    this.status = status;
    this.code = error.code;
    this.details = error.details || [];
    this.requestId = error.request_id;
  }

  // A readable message, including per-field validation problems.
  describe() {
    const fields = this.details.map((d) => `${d.field}: ${d.message}`).join("; ");
    return fields ? `${this.message} (${fields})` : this.message;
  }
}

export const auth = {
  get token() { return localStorage.getItem(TOKEN_KEY); },
  set token(value) {
    if (value) localStorage.setItem(TOKEN_KEY, value);
    else localStorage.removeItem(TOKEN_KEY);
  },
  onLoggedOut: () => {},
};

async function request(method, path, body) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth.token) headers["Authorization"] = `Bearer ${auth.token}`;

  const resp = await fetch(path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (resp.status === 204) return null;
  const data = await resp.json().catch(() => null);

  if (!resp.ok) {
    const error = data?.error ?? { code: "http_error", message: `Server error (${resp.status})` };
    if (resp.status === 401 && path !== "/api/auth/login") {
      auth.token = null;
      auth.onLoggedOut();
    }
    throw new ApiError(resp.status, error);
  }
  return data;
}

function query(params) {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v) q.set(k, v);
  const s = q.toString();
  return s ? `?${s}` : "";
}

export const api = {
  login: (username, password) => request("POST", "/api/auth/login", { username, password }),
  logout: () => request("POST", "/api/auth/logout"),
  me: () => request("GET", "/api/auth/me"),
  listItems: (filters) => request("GET", `/api/items${query(filters)}`),
  listCategories: () => request("GET", "/api/categories"),
  createItem: (item) => request("POST", "/api/items", item),
  updateItem: (id, changes) => request("PATCH", `/api/items/${id}`, changes),
  deleteItem: (id) => request("DELETE", `/api/items/${id}`),
  recordMovement: (id, movement) => request("POST", `/api/items/${id}/movements`, movement),
  itemHistory: (id) => request("GET", `/api/items/${id}/movements`),
  recentActivity: () => request("GET", "/api/movements?limit=100"),
};
