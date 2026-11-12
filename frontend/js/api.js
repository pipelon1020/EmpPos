// frontend/js/api.js

const BASE_URL = "";

function authHeaders(extra = {}) {
    const headers = { ...extra };
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    return headers;
}

// FastAPI a veces devuelve detail como string y otras (422) como lista
async function parseError(res, fallback) {
    try {
        const err = await res.json();
        if (typeof err.detail === "string") return err.detail;
        if (Array.isArray(err.detail)) {
            return err.detail.map(d => `${d.loc?.slice(1).join(".")}: ${d.msg}`).join(" | ");
        }
    } catch (_) {}
    return fallback;
}

async function request(method, path, body = null) {
    const headers = authHeaders({ "Content-Type": "application/json" });
    const options = { method, headers };
    if (body !== null) options.body = JSON.stringify(body);

    const res = await fetch(`${BASE_URL}${path}`, options);

    if (res.status === 401) {
        logout();
        throw new Error("Sesión expirada");
    }
    if (!res.ok) {
        throw new Error(await parseError(res, "Error en la solicitud"));
    }
    if (res.status === 204) return null;
    return res.json();
}

// ---------- Auth ----------
async function login(username, password) {
    const body = new URLSearchParams({ username, password });
    const res = await fetch(`${BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body
    });
    if (!res.ok) throw new Error(await parseError(res, "Credenciales incorrectas"));
    const data = await res.json();
    saveAuth(data.access_token, data.is_admin);
    return data;
}

// ---------- Products ----------
const getProducts    = () => request("GET", "/products/");        // solo activos
const getAllProducts = () => request("GET", "/products/todos");   // incluye inactivos (admin)
const createProduct  = (data) => request("POST", "/products/", data);          // {name, price, active}
const updateProduct  = (id, data) => request("PATCH", `/products/${id}`, data);
const deleteProduct  = (id) => request("DELETE", `/products/${id}`);

// ---------- Orders ----------
const closeOrder = (data) => request("POST", "/orders/", data);  // {name, payment_type, total, items:[...]}
const getOrders  = () => request("GET", "/orders/");
const getOrder   = (id) => request("GET", `/orders/${id}`);

// ---------- Reports (todos son POST con body) ----------
const getSummary        = (period) => request("POST", "/reports/summary", { period });
const getTopProducts    = (period, limit = 10) => request("POST", "/reports/top-products", { period, limit });
const getDailyBreakdown = (period) => request("POST", "/reports/daily-breakdown", { period });
const getReportByDate   = (dateFrom, dateTo) =>
    request("POST", "/reports/by-date", { date_from: dateFrom, date_to: dateTo });
const getInvoicesByDate = (dateFrom, dateTo) =>
    request("POST", "/reports/invoices-by-date", { date_from: dateFrom, date_to: dateTo });

// ---------- Backup (admin) ----------
const exportBackup = () => request("GET", "/backup/export");

// Importar pegando el JSON (objeto ya parseado)
const importBackup = (backup, replace = false) =>
    request("POST", `/backup/import?replace=${replace}`, backup);

// Importar subiendo el archivo .json (multipart: NO se pone Content-Type a mano)
async function importBackupFile(file, replace = false) {
    const form = new FormData();
    form.append("file", file);
    form.append("replace", replace);

    const res = await fetch(`${BASE_URL}/backup/import-file`, {
        method: "POST",
        headers: authHeaders(),
        body: form
    });
    if (res.status === 401) { logout(); throw new Error("Sesión expirada"); }
    if (!res.ok) throw new Error(await parseError(res, "Error al importar"));
    return res.json();
}

// Descargar el backup como archivo
async function downloadBackup() {
    const data = await exportBackup();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `backup_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
}

// ---------- Users (el router de auth no lo pasaste, lo dejé igual) ----------
const getUsers       = () => request("GET", "/auth/users");
const createUser     = (data) => request("POST", "/auth/users", data);
const toggleActive   = (username) => request("PATCH", `/auth/users/${username}/active`);
const changePassword = (data) => request("PATCH", "/auth/users/password", data);