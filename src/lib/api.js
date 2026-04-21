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
  localStorage.removeItem('dashboard_device_token');
}

async function apiCall(path, body = {}, method = 'POST') {
  const token = getToken();
  const cleanPath = path.startsWith('/') ? path.slice(1) : path;

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

  const sessionErrorPhrases = ['nicht autorisiert', 'session abgelaufen', 'nicht authentifiziert'];
  if (data && data.success === false && data.message) {
    const msg = data.message.toLowerCase();
    if (sessionErrorPhrases.some(phrase => msg.includes(phrase))) {
      sessionExpired.set(true);
      throw new Error('Session abgelaufen');
    }
  }

  return data;
}

async function login(email, password, deviceToken = null) {
  const body = { email, password };
  if (deviceToken) body.device_token = deviceToken;
  const res = await fetch(API + '/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  return res.json();
}

async function verify2FA(userId, code, rememberDevice = false) {
  const res = await fetch(API + '/2fa-verify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, code, remember_device: rememberDevice })
  });
  return res.json();
}

async function get2FAStatus() {
  return apiCall('2fa-settings', { action: 'status' });
}

async function set2FA(enabled) {
  return apiCall('2fa-settings', { action: enabled ? 'enable' : 'disable' });
}

export { API, getToken, getUser, setAuth, clearAuth, apiCall, login, verify2FA, get2FAStatus, set2FA };
