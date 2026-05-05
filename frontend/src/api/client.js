/**
 * Cliente HTTP centralizado para la API del backend.
 *
 * - Lee la URL base de la variable de entorno VITE_API_URL
 *   (o usa "/" si está vacía — cuando FastAPI sirve el frontend directamente).
 * - Adjunta el token JWT en cada petición autenticada.
 * - Redirige al login si el servidor responde 401.
 */

const BASE_URL = import.meta.env.VITE_API_URL?.replace(/\/$/, "") ?? "";

function getToken() {
  return localStorage.getItem("auth_token");
}

export function saveToken(token) {
  localStorage.setItem("auth_token", token);
}

export function clearToken() {
  localStorage.removeItem("auth_token");
}

async function request(path, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers ?? {}),
  };

  const response = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (response.status === 401) {
    clearToken();
    window.location.href = "/login";
    throw new Error("Sesión expirada");
  }

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(err.detail ?? "Error desconocido");
  }

  // 204 No Content
  if (response.status === 204) return null;
  return response.json();
}

// ── Auth ──────────────────────────────────────────────────────────────────

export const authApi = {
  login: (password) =>
    request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ password }),
    }),

  changePassword: (currentPassword, newPassword) =>
    request("/api/auth/change-password", {
      method: "POST",
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    }),

  status: () => request("/api/auth/status"),
};

// ── Dispositivos ──────────────────────────────────────────────────────────

export const devicesApi = {
  getAll: () => request("/api/devices/"),
  getById: (id) => request(`/api/devices/${id}`),
  getVulnerabilities: (id) => request(`/api/devices/${id}/vulnerabilities`),
};

// ── Escaneos ──────────────────────────────────────────────────────────────

export const scansApi = {
  getAll: () => request("/api/scans/"),
  startScan: () => request("/api/scans/discover", { method: "POST" }),
  getStatus: () => request("/api/scans/status"),
  updateSettings: (scanIntervalMinutes) =>
    request("/api/scans/settings", {
      method: "POST",
      body: JSON.stringify({ scan_interval_minutes: scanIntervalMinutes }),
    }),
};