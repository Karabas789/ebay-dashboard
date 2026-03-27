<script>
  import { goto } from '$app/navigation';
  import { login, setAuth } from '$lib/api.js';
  import { currentUser } from '$lib/stores.js';

  let email = '';
  let password = '';
  let error = '';
  let loading = false;

  async function handleLogin() {
    error = '';
    if (!email || !password) { error = 'Bitte alle Felder ausfüllen.'; return; }
    loading = true;
    try {
      const data = await login(email, password);
      if (data.success) {
        const user = { ...data.user, trial_end: data.trial_end, plan: data.user.plan || 'starter' };
        setAuth(data.token, user);
        currentUser.set(user);
        goto('/');
      } else {
        error = data.message || 'E-Mail oder Passwort falsch.';
      }
    } catch (e) {
      error = 'Server nicht erreichbar.';
    } finally {
      loading = false;
    }
  }

  function onKeydown(e) {
    if (e.key === 'Enter') handleLogin();
  }
</script>

<svelte:window on:keydown={onKeydown} />

<div class="login-screen">
  <div class="login-card">
    <div class="login-header">
      <img src="https://assets.zyrosite.com/sKFGVgrqCU2eVSWO/logo_9-isvHGkTKpAcAmGO4.webp" alt="Logo" class="login-logo" />
      <div class="login-brand">eBay · Dashboard</div>
    </div>
    <h1 class="login-title">Willkommen zurück.</h1>
    <p class="login-subtitle">Melde dich an um fortzufahren</p>

    <div class="field">
      <label class="label" for="email">E-Mail Adresse</label>
      <input class="input" type="email" id="email" bind:value={email} placeholder="name@shop.de" autocomplete="email" />
    </div>

    <div class="field">
      <label class="label" for="password">Passwort</label>
      <input class="input" type="password" id="password" bind:value={password} placeholder="••••••••" autocomplete="current-password" />
    </div>

    {#if error}
      <div class="error">{error}</div>
    {/if}

    <button class="btn btn-primary login-btn" on:click={handleLogin} disabled={loading}>
      {loading ? 'Einloggen...' : 'Einloggen →'}
    </button>
  </div>
</div>

<style>
  .login-screen {
    position: fixed; inset: 0; display: flex; align-items: center; justify-content: center;
    background: linear-gradient(135deg, #071A52 0%, #0F2E93 50%, #1a3fad 100%);
  }
  .login-card {
    background: var(--surface); border-radius: 20px; padding: 48px 40px;
    width: 420px; max-width: 95vw; box-shadow: 0 20px 60px rgba(0,0,0,0.3);
  }
  .login-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
  .login-logo { width: 36px; height: 36px; border-radius: 8px; }
  .login-brand { font-size: 12px; font-weight: 600; color: var(--text2); letter-spacing: 2px; text-transform: uppercase; }
  .login-title { font-size: 28px; font-weight: 800; margin: 16px 0 6px; }
  .login-subtitle { font-size: 13px; color: var(--text2); margin-bottom: 32px; }
  .field { margin-bottom: 16px; }
  .login-btn { width: 100%; justify-content: center; padding: 13px; font-size: 15px; margin-top: 8px; }
  .login-btn:disabled { opacity: 0.6; cursor: not-allowed; }
  .error { color: var(--danger); font-size: 13px; margin-top: -4px; margin-bottom: 8px; }
</style>
