<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { currentUser, showToast } from '$lib/stores.js';
  import { apiCall } from '$lib/api.js';

  let loading = $state(true);
  let saving = $state(false);
  let testing = $state(false);

  let form = $state({
    smtp_host: '', smtp_port: 587, smtp_secure: false,
    smtp_user: '', smtp_pass_plain: '',
    from_name: '', from_email: '', reply_to: '',
    smtp_aktiv: false,
    email_betreff: 'Ihre Rechnung {{rechnung_nr}} von {{shop_name}}',
    email_body: '<p>Hallo {{kunden_name}},</p>\n<p>anbei erhalten Sie Ihre Rechnung <strong>{{rechnung_nr}}</strong> über <strong>{{brutto_betrag}} €</strong>.</p>\n<p>Vielen Dank für Ihren Einkauf!</p>\n<p>Mit freundlichen Grüßen<br>{{shop_name}}</p>'
  });

  const platzhalter = [
    { key: '{{rechnung_nr}}',  beschreibung: 'Rechnungsnummer' },
    { key: '{{kunden_name}}',  beschreibung: 'Name des Käufers' },
    { key: '{{brutto_betrag}}',beschreibung: 'Bruttobetrag' },
    { key: '{{shop_name}}',    beschreibung: 'Ihr Firmenname' }
  ];

  onMount(async () => {
    try {
      const data = await apiCall('rechnung-settings', {
        action: 'load',
        user_id: $currentUser.id
      });
      if (data?.data) {
        const d = data.data;
        form = {
          smtp_host:     d.smtp_host     || '',
          smtp_port:     d.smtp_port     ?? 587,
          smtp_secure:   d.smtp_secure   || false,
          smtp_user:     d.smtp_user     || '',
          smtp_pass_plain: '',
          from_name:     d.from_name     || '',
          from_email:    d.from_email    || '',
          reply_to:      d.reply_to      || '',
          smtp_aktiv:    d.smtp_aktiv    || false,
          email_betreff: d.email_betreff || 'Ihre Rechnung {{rechnung_nr}} von {{shop_name}}',
          email_body:    d.email_body    || ''
        };
      }
    } catch (e) {
      showToast('Fehler beim Laden: ' + e.message);
    } finally {
      loading = false;
    }
  });

  async function speichern() {
    saving = true;
    try {
      await apiCall('rechnung-settings', {
        action: 'save',
        user_id: $currentUser.id,
        ...form
      });
      showToast('E-Mail Einstellungen gespeichert ✓');
      form.smtp_pass_plain = '';
    } catch (e) {
      showToast('Fehler: ' + e.message);
    } finally {
      saving = false;
    }
  }

  async function testConnection() {
    if (!form.smtp_host || !form.smtp_user) {
      showToast('Bitte SMTP-Host und Benutzer ausfüllen.');
      return;
    }
    testing = true;
    try {
      const res = await fetch('https://email.ai-online.cloud/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host: form.smtp_host,
          port: form.smtp_port,
          secure: form.smtp_secure,
          user: form.smtp_user,
          pass: form.smtp_pass_plain || undefined
        })
      });
      const data = await res.json();
      if (data.success) {
        showToast('Verbindung erfolgreich ✓');
      } else {
        showToast('Verbindung fehlgeschlagen: ' + (data.message || 'Unbekannter Fehler'));
      }
    } catch (e) {
      showToast('Verbindungstest fehlgeschlagen: ' + e.message);
    } finally {
      testing = false;
    }
  }

  const BEKANNTE_ANBIETER = [
    { name: 'Gmail', host: 'smtp.gmail.com', port: 587, secure: false },
    { name: 'Outlook / Hotmail', host: 'smtp.office365.com', port: 587, secure: false },
    { name: 'Yahoo', host: 'smtp.mail.yahoo.com', port: 465, secure: true },
    { name: 'IONOS (1&1)', host: 'smtp.ionos.de', port: 587, secure: false },
    { name: 'Strato', host: 'smtp.strato.de', port: 587, secure: false },
    { name: 'GMX', host: 'mail.gmx.net', port: 587, secure: false },
    { name: 'web.de', host: 'smtp.web.de', port: 587, secure: false },
  ];

  function anbieterWaehlen(anbieter) {
    form.smtp_host = anbieter.host;
    form.smtp_port = anbieter.port;
    form.smtp_secure = anbieter.secure;
  }
</script>

<div class="page-container">
  <div class="page-hdr">
    <div class="hdr-left">
      <button class="btn-back" onclick={() => goto('/einstellungen')}>← Zurück</button>
      <div>
        <div class="page-title">📧 E-Mail / SMTP</div>
        <div class="page-sub">Rechnungen automatisch per E-Mail versenden</div>
      </div>
    </div>
    <button class="btn-primary" onclick={speichern} disabled={saving || loading}>
      {saving ? 'Speichern…' : 'Speichern'}
    </button>
  </div>

  {#if loading}
    <div class="loading-state">Lade Einstellungen…</div>
  {:else}
    <div class="sections">

      <!-- Aktivierung -->
      <div class="card">
        <div class="form-group">
          <label class="toggle-label">
            <input type="checkbox" bind:checked={form.smtp_aktiv} />
            <div>
              <div class="toggle-text">E-Mail-Versand aktivieren</div>
              <div class="toggle-sub">Rechnungen werden nach dem Erstellen automatisch an den Käufer gesendet</div>
            </div>
          </label>
        </div>
      </div>

      <!-- Schnellauswahl -->
      <div class="card">
        <div class="card-title">Schnellauswahl E-Mail-Anbieter</div>
        <div class="anbieter-grid">
          {#each BEKANNTE_ANBIETER as a}
            <button class="anbieter-btn" onclick={() => anbieterWaehlen(a)}>{a.name}</button>
          {/each}
        </div>
      </div>

      <!-- SMTP Server -->
      <div class="card">
        <div class="card-title">SMTP Server</div>
        <div class="form-grid">
          <div class="form-group form-col-3">
            <label>SMTP Host *</label>
            <input bind:value={form.smtp_host} placeholder="smtp.gmail.com" />
          </div>
          <div class="form-group">
            <label>Port</label>
            <input bind:value={form.smtp_port} type="number" placeholder="587" />
          </div>
          <div class="form-group form-full">
            <label class="toggle-label">
              <input type="checkbox" bind:checked={form.smtp_secure} />
              <span class="toggle-text">SSL/TLS verwenden (Port 465) — sonst STARTTLS (Port 587)</span>
            </label>
          </div>
          <div class="form-group">
            <label>Benutzername (E-Mail)</label>
            <input bind:value={form.smtp_user} placeholder="absender@gmail.com" />
          </div>
          <div class="form-group">
            <label>Passwort {form.smtp_user ? '(leer lassen = unverändert)' : ''}</label>
            <input bind:value={form.smtp_pass_plain} type="password" placeholder="••••••••••••" autocomplete="new-password" />
          </div>
        </div>
        <div class="test-row">
          <button class="btn-ghost" onclick={testConnection} disabled={testing}>
            {testing ? 'Teste…' : '🔌 Verbindung testen'}
          </button>
        </div>
      </div>

      <!-- Absender -->
      <div class="card">
        <div class="card-title">Absender</div>
        <div class="form-grid">
          <div class="form-group">
            <label>Absendername</label>
            <input bind:value={form.from_name} placeholder="Import & Produkte Vertrieb" />
          </div>
          <div class="form-group">
            <label>Absender-E-Mail</label>
            <input bind:value={form.from_email} type="email" placeholder="rechnungen@firma.de" />
          </div>
          <div class="form-group form-full">
            <label>Antwort-Adresse (Reply-To, optional)</label>
            <input bind:value={form.reply_to} type="email" placeholder="service@firma.de" />
          </div>
        </div>
      </div>

      <!-- E-Mail Vorlage -->
      <div class="card">
        <div class="card-title">E-Mail Vorlage</div>
        <div class="form-group" style="margin-bottom: 14px;">
          <label>Betreff</label>
          <input bind:value={form.email_betreff} placeholder="Ihre Rechnung {{rechnung_nr}}" />
        </div>
        <div class="form-group">
          <label>Nachrichtentext (HTML)</label>
          <textarea bind:value={form.email_body} rows="8"
            placeholder="<p>Hallo {{kunden_name}},...</p>"></textarea>
        </div>
        <div class="platzhalter-box">
          <div class="platzhalter-title">Verfügbare Platzhalter:</div>
          <div class="platzhalter-liste">
            {#each platzhalter as p}
              <span class="platzhalter-tag" title={p.beschreibung}>{p.key}</span>
            {/each}
          </div>
        </div>
      </div>

    </div>
  {/if}
</div>

<style>
  .page-container { padding: 24px; max-width: 1400px; margin: 0 auto; }
  .page-hdr { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
  .hdr-left { display: flex; align-items: center; gap: 16px; }
  .page-title { font-size: 1.3rem; font-weight: 700; color: var(--text); }
  .page-sub { font-size: 0.82rem; color: var(--text2); margin-top: 2px; }

  .btn-back {
    background: transparent; border: 1px solid var(--border); color: var(--text2);
    padding: 7px 14px; border-radius: 8px; font-size: 0.83rem; cursor: pointer;
    transition: all 0.15s; white-space: nowrap;
  }
  .btn-back:hover { border-color: var(--primary); color: var(--primary); }

  .btn-primary {
    background: var(--primary); color: #fff; border: none;
    padding: 9px 20px; border-radius: 8px; font-size: 0.85rem;
    cursor: pointer; transition: background 0.15s; white-space: nowrap;
  }
  .btn-primary:hover:not(:disabled) { background: var(--primary-hover, #1d4ed8); }
  .btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

  .btn-ghost {
    background: transparent; border: 1px solid var(--border); color: var(--text2);
    padding: 8px 16px; border-radius: 8px; font-size: 0.83rem; cursor: pointer;
    transition: all 0.15s;
  }
  .btn-ghost:hover:not(:disabled) { border-color: var(--primary); color: var(--primary); }
  .btn-ghost:disabled { opacity: 0.6; cursor: not-allowed; }

  .loading-state { padding: 40px; text-align: center; color: var(--text2); font-size: 0.85rem; }

  .sections { display: flex; flex-direction: column; gap: 16px; }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px 24px; }
  .card-title { font-size: 0.9rem; font-weight: 600; color: var(--text); margin-bottom: 16px; }

  .anbieter-grid { display: flex; flex-wrap: wrap; gap: 8px; }
  .anbieter-btn {
    background: var(--surface2); border: 1px solid var(--border); color: var(--text);
    padding: 6px 14px; border-radius: 20px; font-size: 0.8rem; cursor: pointer;
    transition: all 0.15s;
  }
  .anbieter-btn:hover { border-color: var(--primary); color: var(--primary); background: var(--primary-light); }

  .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .form-full { grid-column: 1 / -1; }
  .form-col-3 { grid-column: span 1; }

  .form-group { display: flex; flex-direction: column; gap: 5px; }
  .form-group label:not(.toggle-label) { font-size: 0.78rem; color: var(--text2); font-weight: 500; }
  .form-group input, .form-group textarea {
    background: var(--surface); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: 8px; font-size: 0.85rem;
    outline: none; transition: border-color 0.15s; font-family: inherit;
  }
  .form-group input:focus, .form-group textarea:focus { border-color: var(--primary); }
  .form-group input::placeholder, .form-group textarea::placeholder { color: var(--text3); }
  .form-group textarea { resize: vertical; }

  .toggle-label { display: flex; align-items: flex-start; gap: 10px; cursor: pointer; padding: 6px 0; }
  .toggle-label input[type="checkbox"] { margin-top: 3px; width: 16px; height: 16px; cursor: pointer; accent-color: var(--primary); flex-shrink: 0; }
  .toggle-text { font-size: 0.88rem; color: var(--text); font-weight: 500; line-height: 1.4; }
  .toggle-sub { font-size: 0.78rem; color: var(--text2); margin-top: 2px; }

  .test-row { margin-top: 14px; }

  .platzhalter-box { margin-top: 14px; padding: 12px 14px; background: var(--surface2); border-radius: 8px; border: 1px solid var(--border); }
  .platzhalter-title { font-size: 0.75rem; color: var(--text2); margin-bottom: 8px; font-weight: 500; }
  .platzhalter-liste { display: flex; flex-wrap: wrap; gap: 6px; }
  .platzhalter-tag {
    background: var(--primary-light); color: var(--primary);
    padding: 3px 10px; border-radius: 6px; font-size: 0.78rem;
    font-family: monospace; cursor: default;
  }
</style>
