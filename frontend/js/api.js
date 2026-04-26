// frontend/js/api.js

const BASE_URL = "";

async function request(method, path, body = null) {
    const headers = { "Content-Type": "application/json" };
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const options = { method, headers };
    if (body) options.body = JSON.stringify(body);

    const res = await fetch(`${BASE_URL}${path}`, options);

    if (res.status === 401) {
        logout();
        return;
    }

    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Error en la solicitud");
    }

    if (res.status === 204) return null;
    return res.json();
}

// Auth
async function login(username, password) {
    const body = new URLSearchParams({ username, password });
    const res = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body
    });
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Credenciales incorrectas");
    }
    const data = await res.json();
    saveAuth(data.access_token, data.is_admin);
    return data;
}

// Products
const getProducts = () => request("GET", "/products/");
const createProduct = (data) => request("POST", "/products/", data);
const updateProduct = (id, data) => request("PATCH", `/products/${id}`, data);
const deleteProduct = (id) => request("DELETE", `/products/${id}`);

// Orders
const closeOrder = (data) => request("POST", "/orders/", data);
const getOrders = () => request("GET", "/orders/");

// Reports
const getSummary = (period) => request("GET", `/reports/summary?period=${period}`);
const getTopProducts = (period) => request("GET", `/reports/top-products?period=${period}`);
const getDailyBreakdown = (period) => request("GET", `/reports/daily-breakdown?period=${period}`);

// Users
const getUsers = () => request("GET", "/auth/users");
const createUser = (data) => request("POST", "/auth/users", data);
const toggleActive = (username) => request("PATCH", `/auth/users/${username}/active`);
const changePassword = (data) => request("PATCH", "/auth/users/password", data);