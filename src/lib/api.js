import { sessionExpired } from './stores.js';

const API = 'https://n8n.ai-online.cloud/webhook';

function getToken() {
  if (typeof localStorage === 'undefined') return null;
  return localStorage.getItem('dashboard_token');
}

function getUser() {
  if (typeof localStorage === 'undefined') return null;
  const raw = localStorage.getItem('dashboard_user');
  return raw ? JSON.parse(raw) : null;
}

function setAuth(token, user) {
  localStorage.setItem('dashboard_token', token);
  localStorage.setItem('dashboard_user', JSON.stringify(user));
}

function clearAuth() {
  localStorage.removeItem('dashboard_token');
  localStorage.removeItem('dashboard_user');
}

async function apiCall(path, body = {}, method = 'POST') {
  const token = getToken();
  const opts = {
    method,
    headers: {
      'Authorization': 'Bearer ' + (token || ''),
      'Content-Type': 'application/json'
    }
  };
  if (method !== 'GET') opts.body = JSON.stringify(body);
  const cleanPath = path.startsWith('/') ? path.slice(1) : path;
  const res = await fetch(API + '/' + cleanPath, opts);

  // Token ungültig / abgelaufen → Session-Modal anzeigen
  if (res.status === 401) {
    sessionExpired.set(true);
    throw new Error('Session abgelaufen');
  }

  const data = await res.json();

  // n8n gibt manchmal 200 zurück, aber success: false bei Auth-Problemen
  if (data && data.success === false && data.message && /token|autoris|auth/i.test(data.message)) {
    sessionExpired.set(true);
    throw new Error('Session abgelaufen');
  }

  return data;
}

async function login(email, password) {
  const res = await fetch(API + '/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  return res.json();
}

export { API, getToken, getUser, setAuth, clearAuth, apiCall, login };
