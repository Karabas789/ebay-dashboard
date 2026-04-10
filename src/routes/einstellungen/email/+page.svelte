<script>
  import { onMount } from 'svelte';
  import { currentUser, showToast } from '$lib/stores.js';
  import { apiCall } from '$lib/api.js';

  let speichertLaeuft = $state(false);
  let testLaeuft = $state(false);
  let geladen = $state(false);

  let cfg = $state({
    smtp_host: '',
    smtp_port: 587,
    smtp_user: '',
    smtp_pass: '',
    smtp_secure: false,
    absender_name: '',
    absender_email: '',
    betreff_vorlage: 'Ihre Rechnung {{rechnung_nr}}',
    text_vorlage: 'Sehr geehrte(r) {{kaeufer_name}},\n\nanbei erhalten Sie Ihre Rechnung {{rechnung_nr}} vom {{datum}} als PDF-Anhang.\n\nRechnungsbetrag: {{brutto_betrag}} EUR\n\nVielen Dank für Ihren Einkauf!\n\nMit freundlichen Grüßen',
    auto_versand: false,
  });

  let testEmail = $state('');
  let passwortZeigen = $state(false);

  const anbieterVorlagen = [
    { name: 'Gmail', host: 'smtp.gmail.com', port: 587, secure: false, hinweis: 'App-Passwort verwenden' },
    { name: 'Gmail (SSL)', host: 'smtp.gmail.com', port: 465, secure: true, hinweis: 'App-Passwort verwenden' },
    { name: 'Outlook / Hotmail', host: 'smtp.office365.com', port: 587, secure: false, hinweis: 'Microsoft-Konto-Passwort' },
    { name: 'Strato', host: 'smtp.strato.de', port: 587, secure: false, hinweis: 'E-Mail-Passwort' },
    { name: '1&1 IONOS', host: 'smtp.ionos.de', port: 587, secure: false, hinweis: 'E-Mail-Passwort' },
    { name: 'GMX', host: 'mail.gmx.net', port: 587, secure: false, hinweis: 'GMX-Passwort' },
    { name: 'Web.de', host: 'smtp.web.de', port: 587, secure: false, hinweis: 'Web.de-Passwort' },
    { name: 'T-Online', host: 'securesmtp.t-online.de', port: 587, secure: false, hinweis: 'T-Online Passwort' },
  ];

  function wendeAnbieterAn(anbieter) {
    cfg = { ...cfg, smtp_host: anbieter.host, smtp_port: anbieter.port, smtp_secure: anbieter.secure };
    showToast('Anbieter gewählt: ' + anbieter.name + ' — ' + anbieter.hinweis);
  }

  onMount(() => {
    // Sofort geladen = true setzen damit die Seite angezeigt wird
    // Dann asynchron Config nachladen
    testEmail = $currentUser?.email || '';
    geladen = true;

    if ($currentUser) {
      apiCall('email-config-laden', { user_id: $currentUser.id })
        .then(data => {
          if (data?.config) {
            cfg = {
              smtp_host:       data.config.smtp_host       || '',
              smtp_port:       data.config.smtp_port       || 587,
              smtp_user:       data.config.smtp_user       || '',
              smtp_pass:       '',
              smtp_secure:     data.config.smtp_secure     || false,
              absender_name:   data.config.absender_name   || '',
              absender_email:  data.config.absender_email  || '',
              betreff_vorlage: data.config.betreff_vorlage || cfg.betreff_vorlage,
              text_vorlage:    data.config.text_vorlage    || cfg.text_vorlage,
              auto_versand:    data.config.auto_versand    || false,
            };
          }
        })
        .catch(e => console.warn('Email-Config nicht geladen:', e));
    }
  });

  async function speichern() {
    if (!cfg.smtp_host || !cfg.smtp_user) {
      showToast('Bitte SMTP-Host und Benutzername ausfüllen.'); return;
    }
    speichertLaeuft = true;
    try {
      await apiCall('email-config-speichern', { user_id: $currentUser.id, ...cfg });
      showToast('✅ E-Mail-Einstellungen gespeichert');
    } catch(e) {
      showToast('Fehler: ' + e.message);
    } finally {
      speichertLaeuft = false;
    }
  }

  async function testSenden() {
    if (!testEmail) { showToast('Bitte Test-E-Mail-Adresse eingeben.'); return; }
    if (!cfg.smtp_host || !cfg.smtp_user) {
      showToast('Bitte zuerst SMTP-Einstellungen speichern.'); return;
    }
    testLaeuft = true;
    try {
      await apiCall('email-config-speichern', { user_id: $currentUser.id, ...cfg });
      await apiCall('email-test-senden', { user_id: $currentUser.id, to_email: testEmail });
      showToast('✅ Test-E-Mail gesendet an ' + testEmail);
    } catch(e) {
      showToast('Fehler beim Senden: ' + e.message);
    } finally {
      testLaeuft = false;
    }
  }

  const variablen = [
    { key: '{{rechnung_nr}}', beschreibung: 'Rechnungsnummer' },
    { key: '{{kaeufer_name}}', beschreibung: 'Name des Käufers' },
    { key: '{{datum}}', beschreibung: 'Rechnungsdatum' },
    { key: '{{brutto_betrag}}', beschreibung: 'Bruttobetrag' },
  ];
</script>

<div class="page-container">
  <div class="page-hdr">
    <div>
      <div class="page-title">📧 E-Mail Einstellungen</div>
      <div class="page-sub">SMTP-Konfiguration für den automatischen Rechnungsversand</div>
    </div>
    <button class="btn-primary" onclick={speichern} disabled={speichertLaeuft}>
      {speichertLaeuft ? '⏳ Speichert…' : '💾 Speichern'}
    </button>
  </div>

  {#if geladen}

  <!-- ANBIETER SCHNELLAUSWAHL -->
  <div class="card">
    <div class="card-titel">Anbieter-Schnellauswahl</div>
    <div class="card-sub">Klicke auf deinen E-Mail-Anbieter um Host und Port automatisch auszufüllen</div>
    <div class="anbieter-grid">
      {#each anbieterVorlagen as a}
        <button class="anbieter-btn" class:aktiv={cfg.smtp_host === a.host && cfg.smtp_port === a.port}
          onclick={() => wendeAnbieterAn(a)} title={a.hinweis}>
          {a.name}
        </button>
      {/each}
    </div>
  </div>

  <!-- SMTP EINSTELLUNGEN -->
  <div class="card">
    <div class="card-titel">SMTP-Verbindung</div>
    <div class="form-grid">
      <div class="form-group form-span2">
        <label>SMTP-Host *</label>
        <input bind:value={cfg.smtp_host} placeholder="z. B. smtp.gmail.com" />
      </div>
      <div class="form-group">
        <label>Port</label>
        <input bind:value={cfg.smtp_port} type="number" placeholder="587" />
      </div>
      <div class="form-group">
        <label>Sicherheit</label>
        <div class="toggle-row">
          <label class="check-label">
            <input type="checkbox" bind:checked={cfg.smtp_secure} />
            SSL/TLS (Port 465)
          </label>
          <span class="hinweis-klein">Port 587 = STARTTLS · Port 465 = SSL/TLS</span>
        </div>
      </div>
      <div class="form-group">
        <label>Benutzername (E-Mail-Adresse) *</label>
        <input bind:value={cfg.smtp_user} type="email" placeholder="deine@email.de" />
      </div>
      <div class="form-group">
        <label>Passwort {cfg.smtp_pass ? '' : '(leer = unverändertes Passwort)'}</label>
        <div class="input-row">
          {#if passwortZeigen}
            <input bind:value={cfg.smtp_pass} type="text" placeholder="Passwort eingeben" style="flex:1" />
          {:else}
            <input bind:value={cfg.smtp_pass} type="password" placeholder="Passwort eingeben" style="flex:1" />
          {/if}
          <button class="btn-ghost btn-sm" onclick={() => passwortZeigen = !passwortZeigen}>
            {passwortZeigen ? '🙈' : '👁'}
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- ABSENDER -->
  <div class="card">
    <div class="card-titel">Absender</div>
    <div class="form-grid">
      <div class="form-group">
        <label>Absendername</label>
        <input bind:value={cfg.absender_name} placeholder="z. B. Mein Shop" />
      </div>
      <div class="form-group">
        <label>Absender-E-Mail</label>
        <input bind:value={cfg.absender_email} type="email" placeholder="rechnungen@meinshop.de" />
      </div>
    </div>
  </div>

  <!-- E-MAIL VORLAGE -->
  <div class="card">
    <div class="card-titel">E-Mail Vorlage</div>
    <div class="variablen-hinweis">
      <span class="var-titel">Variablen (klicken zum Kopieren):</span>
      {#each variablen as v}
        <button class="var-chip"
          onclick={() => { navigator.clipboard?.writeText(v.key); showToast(v.key + ' kopiert'); }}
          title={v.beschreibung}>
          {v.key}
        </button>
      {/each}
    </div>
    <div class="form-grid">
      <div class="form-group form-span2">
        <label>Betreff</label>
        <input bind:value={cfg.betreff_vorlage} placeholder="Ihre Rechnung {{rechnung_nr}}" />
      </div>
      <div class="form-group form-span2">
        <label>E-Mail Text</label>
        <textarea bind:value={cfg.text_vorlage} rows="8" placeholder="E-Mail-Text..."></textarea>
      </div>
    </div>
  </div>

  <!-- AUTO-VERSAND -->
  <div class="card">
    <div class="card-titel">Automatischer Versand</div>
    <div class="auto-row">
      <div>
        <div class="auto-titel">Nach Rechnungserstellung automatisch senden</div>
        <div class="auto-sub">Wenn aktiviert, wird die Rechnung sofort nach automatischer Erstellung per E-Mail an den Käufer gesendet (nur wenn E-Mail-Adresse vorhanden)</div>
      </div>
      <button class="toggle-btn {cfg.auto_versand ? 'toggle-an' : 'toggle-aus'}"
        onclick={() => cfg.auto_versand = !cfg.auto_versand}>
        <span class="toggle-thumb"></span>
      </button>
    </div>
  </div>

  <!-- TEST E-MAIL -->
  <div class="card card-test">
    <div class="card-titel">Verbindung testen</div>
    <div class="card-sub">Sendet eine Test-E-Mail um die SMTP-Einstellungen zu überprüfen. Einstellungen werden dabei automatisch gespeichert.</div>
    <div class="test-row">
      <input bind:value={testEmail} type="email" placeholder="test@example.com" style="flex:1" />
      <button class="btn-primary" onclick={testSenden} disabled={testLaeuft}>
        {testLaeuft ? '⏳ Sende…' : '📤 Test senden'}
      </button>
    </div>
  </div>

  {:else}
    <div class="lade-status">Lade Einstellungen…</div>
  {/if}

</div>

<style>
  .page-container { display:flex; flex-direction:column; gap:20px; padding:24px; width:100%; box-sizing:border-box; max-width:860px; }
  .page-hdr { display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap; }
  .page-title { font-size:1.4rem; font-weight:700; color:var(--text); }
  .page-sub { font-size:0.83rem; color:var(--text2); margin-top:2px; }
  .card { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:20px 24px; display:flex; flex-direction:column; gap:14px; }
  .card-titel { font-size:0.9rem; font-weight:700; color:var(--text); }
  .card-sub { font-size:0.8rem; color:var(--text2); margin-top:-8px; }
  .card-test { border-color:var(--primary); }
  .anbieter-grid { display:flex; gap:8px; flex-wrap:wrap; }
  .anbieter-btn { background:var(--surface2); border:1px solid var(--border); color:var(--text); padding:6px 14px; border-radius:8px; font-size:0.8rem; cursor:pointer; transition:all 0.15s; }
  .anbieter-btn:hover { border-color:var(--primary); color:var(--primary); }
  .anbieter-btn.aktiv { background:var(--primary); color:#fff; border-color:var(--primary); font-weight:600; }
  .form-grid { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
  .form-span2 { grid-column: 1 / -1; }
  .form-group { display:flex; flex-direction:column; gap:5px; }
  .form-group label { font-size:0.78rem; color:var(--text2); font-weight:500; }
  .form-group input, .form-group textarea { background:var(--surface); border:1px solid var(--border); color:var(--text); padding:8px 12px; border-radius:8px; font-size:0.85rem; outline:none; font-family:inherit; width:100%; box-sizing:border-box; }
  .form-group input:focus, .form-group textarea:focus { border-color:var(--primary); }
  .form-group textarea { resize:vertical; line-height:1.6; }
  .input-row { display:flex; gap:8px; align-items:center; }
  .toggle-row { display:flex; flex-direction:column; gap:4px; padding-top:4px; }
  .check-label { display:flex; align-items:center; gap:8px; font-size:0.85rem; color:var(--text); cursor:pointer; }
  .check-label input { accent-color:var(--primary); width:15px; height:15px; }
  .hinweis-klein { font-size:0.72rem; color:var(--text3); }
  .auto-row { display:flex; align-items:center; justify-content:space-between; gap:16px; }
  .auto-titel { font-size:0.85rem; font-weight:600; color:var(--text); margin-bottom:4px; }
  .auto-sub { font-size:0.78rem; color:var(--text2); max-width:560px; line-height:1.5; }
  .toggle-btn { position:relative; width:44px; height:24px; border:none; border-radius:99px; cursor:pointer; transition:background 0.2s; padding:0; flex-shrink:0; }
  .toggle-an { background:var(--primary, #2563eb); }
  .toggle-aus { background:#d1d5db; }
  .toggle-thumb { position:absolute; top:3px; width:18px; height:18px; background:#fff; border-radius:50%; transition:left 0.2s; box-shadow:0 1px 3px rgba(0,0,0,0.2); }
  .toggle-an .toggle-thumb { left:23px; }
  .toggle-aus .toggle-thumb { left:3px; }
  .variablen-hinweis { display:flex; align-items:center; gap:8px; flex-wrap:wrap; padding:8px 12px; background:var(--surface2); border-radius:8px; }
  .var-titel { font-size:0.75rem; font-weight:600; color:var(--text2); white-space:nowrap; }
  .var-chip { background:var(--surface); border:1px solid var(--border); color:var(--primary); padding:2px 8px; border-radius:5px; font-size:0.75rem; font-family:monospace; cursor:pointer; transition:all 0.1s; }
  .var-chip:hover { background:var(--primary); color:#fff; border-color:var(--primary); }
  .test-row { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
  .test-row input { background:var(--surface); border:1px solid var(--border); color:var(--text); padding:8px 12px; border-radius:8px; font-size:0.85rem; outline:none; min-width:200px; box-sizing:border-box; }
  .test-row input:focus { border-color:var(--primary); }
  .btn-primary { background:var(--primary); color:#fff; border:none; padding:8px 16px; border-radius:8px; font-size:0.84rem; cursor:pointer; white-space:nowrap; }
  .btn-primary:hover:not(:disabled) { filter:brightness(1.08); }
  .btn-primary:disabled { opacity:0.6; cursor:not-allowed; }
  .btn-ghost { background:transparent; border:1px solid var(--border); color:var(--text2); padding:8px 12px; border-radius:8px; font-size:0.84rem; cursor:pointer; }
  .btn-ghost:hover { border-color:var(--primary); color:var(--primary); }
  .btn-sm { padding:6px 10px; font-size:0.8rem; }
  .lade-status { padding:40px; text-align:center; color:var(--text2); font-size:0.85rem; }
  @media(max-width:600px) {
    .form-grid { grid-template-columns:1fr; }
    .form-span2 { grid-column:1; }
  }
</style>
