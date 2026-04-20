<script>
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';

  let token = $derived($page.url.searchParams.get('token') || '');
  let password = $state('');
  let passwordWdh = $state('');
  let loading = $state(false);
  let success = $state(false);
  let error = $state('');

  async function handleSubmit() {
    error = '';
    if (!password || password.length < 6) { error = 'Passwort muss mindestens 6 Zeichen haben.'; return; }
    if (password !== passwordWdh) { error = 'Passwörter stimmen nicht überein.'; return; }
    if (!token) { error = 'Kein gültiger Reset-Link.'; return; }
    loading = true;
    try {
      const res = await fetch('https://n8n.ai-online.cloud/webhook/passwort-reset-bestaetigen', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, password })
      });
      const data = await res.json();
      if (data.success) {
        success = true;
        setTimeout(() => goto('/login'), 3000);
      } else {
        error = data.message || 'Fehler beim Zurücksetzen.';
      }
    } catch (e) {
      error = 'Server nicht erreichbar.';
    } finally {
      loading = false;
    }
  }
</script>

<div class="login-screen">
  <div class="login-card">
    <div class="login-header">
      <img src="https://assets.zyrosite.com/sKFGVgrqCU2eVSWO/logo_9-isvHGkTKpAcAmGO4.webp" alt="Logo" class="login-logo" />
      <div class="login-brand">eBay · Dashboard</div>
    </div>

    {#if success}
      <div class="success-box">
        <div class="success-icon">✅</div>
        <h2 class="login-title">Passwort geändert!</h2>
        <p class="login-subtitle">Dein Passwort wurde erfolgreich geändert. Du wirst in Kürze zum Login weitergeleitet...</p>
      </div>
    {:else}
      <h1 class="login-title">Neues Passwort</h1>
      <p class="login-subtitle">Gib dein neues Passwort ein.</p>

      {#if !token}
        <div class="error">Ungültiger oder fehlender Reset-Link.</div>
        <a href="/passwort-vergessen" class="btn btn-primary login-btn" style="text-align:center;text-decoration:none;display:block">Neuen Link anfordern</a>
      {:else}
        <div class="field">
          <label class="label" for="password">Neues Passwort</label>
          <input class="input" type="password" id="password" bind:value={password} placeholder="Mindestens 6 Zeichen" />
        </div>
        <div class="field">
          <label class="label" for="passwordWdh">Passwort wiederholen</label>
          <input class="input" type="password" id="passwordWdh" bind:value={passwordWdh} placeholder="Passwort wiederholen" />
        </div>

        {#if error}
          <div class="error">{error}</div>
        {/if}

        <button class="btn btn-primary login-btn" onclick={handleSubmit} disabled={loading}>
          {loading ? 'Wird gespeichert...' : 'Passwort speichern →'}
        </button>
      {/if}
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
  .login-title { font-size: 26px; font-weight: 800; margin: 16px 0 6px; color: #171717; }
  .login-subtitle { font-size: 13px; color: #737373; margin-bottom: 28px; line-height: 1.6; }
  .field { margin-bottom: 16px; }
  .label { display: block; font-size: 13px; font-weight: 600; color: #404040; margin-bottom: 6px; }
  .input {
    width: 100%; padding: 11px 14px; border: 1.5px solid #e5e5e5; border-radius: 10px;
    font-size: 14px; outline: none; box-sizing: border-box; font-family: inherit;
    transition: border-color 0.2s;
  }
  .input:focus { border-color: #3777CF; }
  .btn { border: none; border-radius: 10px; padding: 10px 20px; font-size: 14px; font-weight: 600; cursor: pointer; font-family: inherit; }
  .btn-primary { background: #3777CF; color: white; }
  .btn-primary:hover { background: #2d6ab8; }
  .btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
  .login-btn { width: 100%; padding: 13px; font-size: 15px; margin-top: 8px; }
  .error { color: #ef4444; font-size: 13px; margin-bottom: 8px; }
  .success-box { text-align: center; }
  .success-icon { font-size: 48px; margin: 8px 0 16px; }
</style>
