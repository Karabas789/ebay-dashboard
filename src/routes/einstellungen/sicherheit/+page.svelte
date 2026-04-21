<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
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

<div class="page-container">
  <div class="page-hdr">
    <div class="hdr-left">
      <button class="btn-back" onclick={() => goto('/einstellungen')}>← Zurück</button>
      <div>
        <div class="page-title">🔐 2-Faktor-Authentifizierung</div>
        <div class="page-sub">Sichere deinen Account mit einem zusätzlichen Login-Code</div>
      </div>
    </div>
  </div>

  <div class="card">
    {#if loading}
      <div class="loading">Lade Status…</div>
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
          class="toggle-btn {enabled ? 'toggle-an' : 'toggle-aus'}"
          onclick={toggle}
          disabled={saving}
          title={enabled ? '2FA deaktivieren' : '2FA aktivieren'}
        >
          <span class="toggle-thumb"></span>
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
</div>

<style>
  .page-container { padding: 24px; max-width: 1200px; margin: 0 auto; }
  .page-hdr { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 20px; }
  .hdr-left { display: flex; align-items: center; gap: 16px; }
  .page-title { font-size: 1.3rem; font-weight: 700; color: var(--text); }
  .page-sub { font-size: 0.82rem; color: var(--text2); margin-top: 2px; }
  .btn-back {
    background: transparent; border: 1px solid var(--border); color: var(--text2);
    padding: 7px 14px; border-radius: 8px; font-size: 0.83rem; cursor: pointer;
    transition: all 0.15s; white-space: nowrap;
  }
  .btn-back:hover { border-color: var(--primary); color: var(--primary); }

  .card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 12px; padding: 24px; max-width: 640px;
    display: flex; flex-direction: column; gap: 16px;
  }
  .loading { color: var(--text2); font-size: 0.85rem; }

  .twofa-row { display: flex; align-items: center; gap: 24px; }
  .twofa-info { flex: 1; }
  .twofa-title { font-size: 0.9rem; font-weight: 700; color: var(--text); margin-bottom: 6px; }
  .twofa-desc { font-size: 0.8rem; color: var(--text2); line-height: 1.6; }

  .toggle-btn { position: relative; width: 44px; height: 24px; border: none; border-radius: 99px; cursor: pointer; transition: background 0.2s; padding: 0; flex-shrink: 0; }
  .toggle-an { background: var(--primary, #2563eb); }
  .toggle-aus { background: #d1d5db; }
  .toggle-btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .toggle-thumb { position: absolute; top: 3px; width: 18px; height: 18px; background: #fff; border-radius: 50%; transition: left 0.2s; box-shadow: 0 1px 3px rgba(0,0,0,0.2); }
  .toggle-an .toggle-thumb { left: 23px; }
  .toggle-aus .toggle-thumb { left: 3px; }

  .status-badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; }
  .status-badge.on { background: #dcfce7; color: #15803d; }
  .status-badge.off { background: var(--surface2); color: var(--text2); }

  .msg { padding: 12px 16px; border-radius: 10px; font-size: 0.82rem; }
  .msg.success { background: #dcfce7; color: #15803d; }
  .msg.error { background: #fee2e2; color: #dc2626; }

  .info-box {
    background: var(--primary-light, #f0f4ff); border-radius: 10px;
    padding: 14px 16px; font-size: 0.8rem; color: var(--text2); line-height: 1.6;
  }
</style>
