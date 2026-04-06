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
  const cleanPath = path.startsWith('/') ? path.slice(1) : path;

  // NEU: Bei GET → body als Query-String anhängen
  let url = API + '/' + cleanPath;
  if (method === 'GET' && body && Object.keys(body).length > 0) {
    url += '?' + new URLSearchParams(body).toString();
  }

  const opts = {
    method,
    headers: {
      'Authorization': 'Bearer ' + (token || ''),
      'Content-Type': 'application/json'
    }
  };
  if (method !== 'GET') opts.body = JSON.stringify(body);

  const res = await fetch(url, opts);

  if (res.status === 401) {
    sessionExpired.set(true);
    throw new Error('Session abgelaufen');
  }

  const data = await res.json();

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
