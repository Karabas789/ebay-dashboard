<script>
  import { onMount } from 'svelte';
  import { get2FAStatus, set2FA } from '$lib/api.js';

  let enabled = false;
  let loading = true;
  let saving = false;
  let message = '';
  let error = '';

  onMount(async () => {
    try {
      const data = await get2FAStatus();
      if (data.success) enabled = data.two_fa_enabled;
    } catch (e) {
      error = 'Status konnte nicht geladen werden.';
    } finally {
      loading = false;
    }
  });

  async function toggle() {
    saving = true;
    message = '';
    error = '';
    try {
      const data = await set2FA(!enabled);
      if (data.success) {
        enabled = data.two_fa_enabled;
        message = enabled
          ? '✅ 2FA aktiviert. Du wirst beim nächsten Login einen Code per E-Mail erhalten.'
          : '2FA wurde deaktiviert.';
      } else {
        error = data.message || 'Fehler beim Speichern.';
      }
    } catch (e) {
      error = 'Server nicht erreichbar.';
    } finally {
      saving = false;
    }
  }
</script>

<div class="page-header">
  <div>
    <h1 class="page-title">🔐 2-Faktor-Authentifizierung</h1>
    <p class="page-subtitle">Sichere deinen Account mit einem zusätzlichen Login-Code</p>
  </div>
</div>

<div class="settings-card">
  {#if loading}
    <div class="loading">Lade Status...</div>
  {:else}
    <div class="twofa-row">
      <div class="twofa-info">
        <div class="twofa-title">E-Mail-Bestätigung beim Login</div>
        <div class="twofa-desc">
          Wenn aktiviert, wird bei jedem Login auf einem unbekannten Gerät ein 6-stelliger Code
          an deine E-Mail-Adresse gesendet. Du kannst Geräte 30 Tage lang als vertrauenswürdig markieren.
        </div>
      </div>
      <button
        class="toggle {enabled ? 'active' : ''}"
        on:click={toggle}
        disabled={saving}
        title={enabled ? '2FA deaktivieren' : '2FA aktivieren'}
      >
        <span class="toggle-knob"></span>
      </button>
    </div>

    <div class="status-badge {enabled ? 'on' : 'off'}">
      {enabled ? '🟢 Aktiviert' : '⚪ Deaktiviert'}
    </div>

    {#if message}
      <div class="msg success">{message}</div>
    {/if}
    {#if error}
      <div class="msg error">{error}</div>
    {/if}

    <div class="info-box">
      <strong>Hinweis:</strong> Du benötigst Zugriff auf deine registrierte E-Mail-Adresse um dich anzumelden.
      Stelle sicher, dass diese erreichbar ist bevor du 2FA aktivierst.
    </div>
  {/if}
</div>

<style>
  .settings-card {
    background: white;
    border-radius: 16px;
    padding: 32px;
    max-width: 600px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  }
  .loading { color: #737373; }
  .twofa-row {
    display: flex;
    align-items: center;
    gap: 24px;
    margin-bottom: 16px;
  }
  .twofa-info { flex: 1; }
  .twofa-title { font-size: 16px; font-weight: 700; color: #171717; margin-bottom: 6px; }
  .twofa-desc { font-size: 13px; color: #737373; line-height: 1.6; }

  /* Toggle Switch */
      /* Neu */
    /* Toggle Switch */
.toggle {
  position: relative;
  width: 56px;
  height: 30px;
  background: #d1d5db;
  border: none;
  border-radius: 15px;
  cursor: pointer;
  transition: background 0.25s;
  flex-shrink: 0;
  padding: 0;
  box-sizing: border-box;
}
.toggle.active { background: #3777CF; }
.toggle:disabled { opacity: 0.5; cursor: not-allowed; }
.toggle-knob {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 24px;
  height: 24px;
  background: white;
  border-radius: 50%;
  transition: left 0.25s;
  box-shadow: 0 2px 4px rgba(0,0,0,0.25);
}
.toggle.active .toggle-knob { left: 29px; }

  .status-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
    margin-bottom: 16px;
  }
  .status-badge.on { background: #dcfce7; color: #15803d; }
  .status-badge.off { background: #f5f5f5; color: #737373; }

  .msg { padding: 12px 16px; border-radius: 10px; font-size: 13px; margin-bottom: 16px; }
  .msg.success { background: #dcfce7; color: #15803d; }
  .msg.error { background: #fee2e2; color: #dc2626; }

  .info-box {
    background: #f0f4ff;
    border-radius: 10px;
    padding: 14px 16px;
    font-size: 13px;
    color: #4b5563;
    line-height: 1.6;
    margin-top: 8px;
  }
</style>
