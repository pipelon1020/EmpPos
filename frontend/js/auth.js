// frontend/js/auth.js

const AUTH_KEY = "pos_token";
const IS_ADMIN_KEY = "pos_is_admin";

function saveAuth(token, isAdmin) {
    localStorage.setItem(AUTH_KEY, token);
    localStorage.setItem(IS_ADMIN_KEY, isAdmin);
}

function getToken() {
    return localStorage.getItem(AUTH_KEY);
}

function isAdmin() {
    return localStorage.getItem(IS_ADMIN_KEY) === "true";
}

function isLoggedIn() {
    return !!getToken();
}

function logout() {
    localStorage.removeItem(AUTH_KEY);
    localStorage.removeItem(IS_ADMIN_KEY);
    window.location.href = "/login.html";
}

function requireAuth() {
    if (!isLoggedIn()) {
        window.location.href = "/login.html";
    }
}

function requireAdmin() {
    requireAuth();
    if (!isAdmin()) {
        window.location.href = "/index.html";
    }
}