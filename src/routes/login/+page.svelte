<script>
  import { goto } from '$app/navigation';
  import { login, verify2FA, setAuth } from '$lib/api.js';
  import { currentUser } from '$lib/stores.js';

  let email = '';
  let password = '';
  let error = '';
  let loading = false;

  // 2FA State
  let step = 'login'; // 'login' | '2fa'
  let twoFaCode = '';
  let twoFaUserId = null;
  let rememberDevice = false;

  function getDeviceToken() {
    if (typeof localStorage === 'undefined') return null;
    return localStorage.getItem('dashboard_device_token');
  }

  async function handleLogin() {
    error = '';
    if (!email || !password) { error = 'Bitte alle Felder ausfüllen.'; return; }
    loading = true;
    try {
      const deviceToken = getDeviceToken();
      const data = await login(email, password, deviceToken);

      if (data.requires_2fa) {
        twoFaUserId = data.user_id;
        step = '2fa';
      } else if (data.success) {
        finishLogin(data);
      } else {
        error = data.message || 'E-Mail oder Passwort falsch.';
      }
    } catch (e) {
      error = 'Server nicht erreichbar.';
    } finally {
      loading = false;
    }
  }

  async function handle2FA() {
    error = '';
    if (!twoFaCode || twoFaCode.length !== 6) { error = 'Bitte 6-stelligen Code eingeben.'; return; }
    loading = true;
    try {
      const data = await verify2FA(twoFaUserId, twoFaCode, rememberDevice);
      if (data.success) {
        if (rememberDevice && data.device_token) {
          localStorage.setItem('dashboard_device_token', data.device_token);
        }
        finishLogin(data);
      } else {
        error = data.message || 'Ungültiger Code.';
      }
    } catch (e) {
      error = 'Server nicht erreichbar.';
    } finally {
      loading = false;
    }
  }

  function finishLogin(data) {
    const user = { ...data.user, trial_end: data.trial_end, plan: data.user.plan || 'starter' };
    setAuth(data.token, user);
    currentUser.set(user);
    goto('/');
  }

  function onKeydown(e) {
    if (e.key === 'Enter') {
      if (step === 'login') handleLogin();
      else handle2FA();
    }
  }

  function backToLogin() {
    step = 'login';
    twoFaCode = '';
    error = '';
  }
</script>

<svelte:window on:keydown={onKeydown} />

<div class="login-screen">
  <div class="login-card">
    <div class="login-header">
      <img src="https://assets.zyrosite.com/sKFGVgrqCU2eVSWO/logo_9-isvHGkTKpAcAmGO4.webp" alt="Logo" class="login-logo" />
      <div class="login-brand">eBay · Dashboard</div>
    </div>

    {#if step === 'login'}
      <h1 class="login-title">Willkommen zurück.</h1>
      <p class="login-subtitle">Melde dich an um fortzufahren</p>

      <div class="field">
        <label class="label" for="email">E-Mail Adresse</label>
        <input class="input" type="email" id="email" bind:value={email} placeholder="name@shop.de" autocomplete="email" />
      </div>

      <div class="field">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <label class="label" for="password" style="margin-bottom:0">Passwort</label>
          <a href="/passwort-vergessen" style="font-size:12px;color:#3777CF;text-decoration:none">Passwort vergessen?</a>
        </div>
        <input class="input" type="password" id="password" bind:value={password} placeholder="••••••••" autocomplete="current-password" />
      </div>

      {#if error}
        <div class="error">{error}</div>
      {/if}

      <button class="btn btn-primary login-btn" on:click={handleLogin} disabled={loading}>
        {loading ? 'Einloggen...' : 'Einloggen →'}
      </button>

    {:else}
      <h1 class="login-title">Bestätigung</h1>
      <p class="login-subtitle">Wir haben einen Code an deine E-Mail gesendet.</p>

      <div class="field">
        <label class="label" for="code">6-stelliger Code</label>
        <input
          class="input code-input"
          type="text"
          id="code"
          bind:value={twoFaCode}
          placeholder="123456"
          maxlength="6"
          inputmode="numeric"
          autocomplete="one-time-code"
        />
      </div>

      <div class="remember-row">
        <label class="remember-label">
          <input type="checkbox" bind:checked={rememberDevice} />
          Dieses Gerät 30 Tage merken
        </label>
      </div>

      {#if error}
        <div class="error">{error}</div>
      {/if}

      <button class="btn btn-primary login-btn" on:click={handle2FA} disabled={loading}>
        {loading ? 'Prüfen...' : 'Bestätigen →'}
      </button>

      <button class="btn-back" on:click={backToLogin}>← Zurück</button>
    {/if}
  </div>
</div>

<style>
  .login-screen {
    position: fixed; inset: 0; display: flex; align-items: center; justify-content: center;
    background: linear-gradient(135deg, #0a0a1a 0%, #1a2560 50%, #2D43A8 100%);
  }
  .login-card {
    background: white; border-radius: 20px; padding: 48px 40px;
    width: 420px; max-width: 95vw; box-shadow: 0 20px 60px rgba(0,0,0,0.3);
  }
  .login-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
  .login-logo { width: 36px; height: 36px; border-radius: 8px; }
  .login-brand { font-size: 12px; font-weight: 600; color: #737373; letter-spacing: 2px; text-transform: uppercase; }
  .login-title { font-size: 28px; font-weight: 800; margin: 16px 0 6px; color: #171717; }
  .login-subtitle { font-size: 13px; color: #737373; margin-bottom: 32px; }
  .field { margin-bottom: 16px; }
  .login-btn { width: 100%; justify-content: center; padding: 13px; font-size: 15px; margin-top: 8px; }
  .login-btn:disabled { opacity: 0.6; cursor: not-allowed; }
  .error { color: #ef4444; font-size: 13px; margin-top: -4px; margin-bottom: 8px; }
  .label { display: block; font-size: 13px; font-weight: 600; color: #404040; margin-bottom: 6px; }
  .input {
    width: 100%; padding: 11px 14px; border: 1.5px solid #e5e5e5; border-radius: 10px;
    font-size: 14px; outline: none; box-sizing: border-box; font-family: inherit;
    transition: border-color 0.2s;
  }
  .input:focus { border-color: #3777CF; }
  .code-input { font-size: 24px; letter-spacing: 8px; text-align: center; font-weight: 700; }
  .remember-row { margin-bottom: 12px; }
  .remember-label { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #555; cursor: pointer; }
  .remember-label input { width: 16px; height: 16px; cursor: pointer; }
  .btn { border: none; border-radius: 10px; padding: 10px 20px; font-size: 14px; font-weight: 600; cursor: pointer; font-family: inherit; }
  .btn-primary { background: #3777CF; color: white; }
  .btn-primary:hover { background: #2d6ab8; }
  .btn-back { background: none; border: none; color: #737373; font-size: 13px; cursor: pointer; margin-top: 12px; display: block; text-align: center; width: 100%; padding: 8px; }
  .btn-back:hover { color: #3777CF; }
</style>
