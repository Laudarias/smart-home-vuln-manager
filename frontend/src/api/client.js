const API_BASE_URL = import.meta.env.VITE_API_URL || '';

const getToken = () => localStorage.getItem('token');

const handleResponse = async (response) => {
  if (response.status === 401) {
    localStorage.removeItem('token');
    window.location.reload();
    throw new Error('No autenticado');
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Error desconocido' }));
    throw new Error(error.detail || 'Error en la petición');
  }

  return response.json();
};

const request = async (endpoint, options = {}) => {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  return handleResponse(response);
};

export const api = {
  // Auth
  login: (password) =>
    request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ password }),
    }),

  me: () => request('/api/auth/me'),

  changePassword: (current_password, new_password) =>
    request('/api/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password, new_password }),
    }),

  // Scans
  startScan: () =>
    request('/api/scans/discover', { method: 'POST' }),

  listScans: () => request('/api/scans'),

  scanStatus: () => request('/api/scans/status'),

  setInterval: (interval_minutes) =>
    request('/api/scans/interval', {
      method: 'PUT',
      body: JSON.stringify({ scan_interval_minutes: interval_minutes }),
    }),

  // Devices
  listDevices: () => request('/api/devices'),

  getDevice: (id) => request(`/api/devices/${id}`),

  resolveVuln: (deviceId, vulnId) =>
    request(`/api/devices/${deviceId}/vulnerabilities/${vulnId}/resolve`, {
      method: 'POST',
    }),
};
