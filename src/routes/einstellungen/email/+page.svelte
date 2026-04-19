<script>
  import { onMount } from 'svelte';
  import { currentUser, showToast } from '$lib/stores.js';
  import { apiCall } from '$lib/api.js';
  import { goto } from '$app/navigation';

  // ═══════════════════════════════════════════════════════
  // Tab-Switch
  // ═══════════════════════════════════════════════════════
  let tab = $state('versand'); // 'versand' | 'empfang' | 'kauf'

  // ═══════════════════════════════════════════════════════
  // VERSAND (SMTP)
  // ═══════════════════════════════════════════════════════
  let speichertLaeuft = $state(false);
  let testLaeuft = $state(false);
  let configLaeuft = $state(false);

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
  let testStatus = $state(null);
  let testNachricht = $state('');

  const anbieterVorlagen = [
    { name: 'Hostinger', host: 'smtp.hostinger.com', port: 465, secure: true, hinweis: 'E-Mail-Passwort aus Hostinger hPanel' },
    { name: 'Gmail', host: 'smtp.gmail.com', port: 587, secure: false, hinweis: 'App-Passwort verwenden (nicht dein Google-Passwort)' },
    { name: 'Gmail (SSL)', host: 'smtp.gmail.com', port: 465, secure: true, hinweis: 'App-Passwort verwenden' },
    { name: 'Outlook / Hotmail', host: 'smtp.office365.com', port: 587, secure: false, hinweis: 'Microsoft-Konto-Passwort' },
    { name: 'Strato', host: 'smtp.strato.de', port: 587, secure: false, hinweis: 'E-Mail-Passwort verwenden' },
    { name: '1&1 IONOS', host: 'smtp.ionos.de', port: 587, secure: false, hinweis: 'E-Mail-Passwort verwenden' },
    { name: 'GMX', host: 'mail.gmx.net', port: 587, secure: false, hinweis: 'GMX-Passwort verwenden' },
    { name: 'Web.de', host: 'smtp.web.de', port: 587, secure: false, hinweis: 'Web.de-Passwort verwenden' },
    { name: 'T-Online', host: 'securesmtp.t-online.de', port: 587, secure: false, hinweis: 'T-Online Passwort verwenden' },
  ];

  function wendeAnbieterAn(anbieter) {
    cfg = { ...cfg, smtp_host: anbieter.host, smtp_port: anbieter.port, smtp_secure: anbieter.secure };
    showToast('Anbieter gewählt: ' + anbieter.name + ' — ' + anbieter.hinweis);
  }

  async function ladeVersandConfig() {
    if (!$currentUser) return;
    configLaeuft = true;
    try {
      const data = await apiCall('email-config-laden', { user_id: $currentUser.id });
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
    } catch(e) {
      console.warn('Email-Config nicht geladen:', e?.message || e);
    } finally {
      configLaeuft = false;
    }
  }

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
      showToast('Bitte zuerst SMTP-Host und Benutzername ausfüllen.'); return;
    }
    testLaeuft = true;
    testStatus = null;
    testNachricht = '';
    try {
      await apiCall('email-config-speichern', { user_id: $currentUser.id, ...cfg });
      await apiCall('smtp-testen', { user_id: $currentUser.id, to_email: testEmail });
      testStatus = 'success';
      testNachricht = 'Test-E-Mail erfolgreich gesendet an ' + testEmail;
      showToast('✅ Test-E-Mail gesendet an ' + testEmail);
    } catch(e) {
      testStatus = 'error';
      testNachricht = e.message || 'Verbindung fehlgeschlagen. Bitte SMTP-Daten prüfen.';
      showToast('Fehler: ' + e.message);
    } finally {
      testLaeuft = false;
    }
  }

  const variablen = [
    { key: '{{rechnung_nr}}', beschreibung: 'Rechnungsnummer' },
    { key: '{{kaeufer_name}}', beschreibung: 'Name des Käufers' },
    { key: '{{datum}}', beschreibung: 'Rechnungsdatum' },
    { key: '{{brutto_betrag}}', beschreibung: 'Bruttobetrag' },
    { key: '{{firmenname}}', beschreibung: 'Eigener Firmenname' },
  ];

  // ═══════════════════════════════════════════════════════
  // EMPFANG (IMAP)
  // ═══════════════════════════════════════════════════════
  let imapLaeuft = $state(false);
  let imapSpeichertLaeuft = $state(false);
  let imapTestLaeuft = $state(false);
  let imapLoeschenLaeuft = $state(false);
  let imapPasswortZeigen = $state(false);
  let imapTestStatus = $state(null);
  let imapTestNachricht = $state('');
  let imapTestFolders = $state([]);

  let imap = $state({
    email: '',
    host: 'imap.hostinger.com',
    port: 993,
    user_name: '',
    pass: '',
    folder: 'INBOX',
    processed_folder: 'Rechnungen',
    filter_betreff: '',
    aktiv: false
  });

  let imapConfigExistiert = $state(false);
  let lastCheck = $state(null);
  let lastError = $state(null);

  const imapAnbieter = [
    { name: 'Hostinger', host: 'imap.hostinger.com', port: 993, hinweis: 'E-Mail-Passwort aus Hostinger hPanel' },
    { name: 'Gmail', host: 'imap.gmail.com', port: 993, hinweis: 'App-Passwort verwenden' },
    { name: 'Outlook', host: 'outlook.office365.com', port: 993, hinweis: 'Microsoft-Konto-Passwort' },
    { name: 'IONOS', host: 'imap.ionos.de', port: 993, hinweis: 'E-Mail-Passwort verwenden' },
    { name: 'Strato', host: 'imap.strato.de', port: 993, hinweis: 'E-Mail-Passwort verwenden' },
    { name: 'GMX', host: 'imap.gmx.net', port: 993, hinweis: 'GMX-Passwort verwenden' },
  ];

  function wendeImapAnbieterAn(a) {
    imap = { ...imap, host: a.host, port: a.port };
    showToast('Anbieter: ' + a.name + ' — ' + a.hinweis);
  }

  async function ladeImapConfig() {
    if (!$currentUser) return;
    imapLaeuft = true;
    try {
      const res = await apiCall('imap-config', { user_id: $currentUser.id, action: 'load' });
      if (res?.config) {
        imap = {
          email:            res.config.email            || '',
          host:             res.config.host             || 'imap.hostinger.com',
          port:             res.config.port             || 993,
          user_name:        res.config.user_name        || '',
          pass:             '',
          folder:           res.config.folder           || 'INBOX',
          processed_folder: res.config.processed_folder || 'Rechnungen',
          filter_betreff:   res.config.filter_betreff   || '',
          aktiv:            res.config.aktiv            || false
        };
        imapConfigExistiert = true;
        lastCheck = res.config.last_check || null;
        lastError = res.config.last_error || null;
      } else {
        imapConfigExistiert = false;
      }
    } catch(e) {
      console.warn('IMAP-Config nicht geladen:', e?.message || e);
    } finally {
      imapLaeuft = false;
    }
  }

  async function imapSpeichern() {
    if (!imap.host || !imap.user_name) {
      showToast('Bitte IMAP-Host und Benutzername ausfüllen.'); return;
    }
    imapSpeichertLaeuft = true;
    try {
      await apiCall('imap-config', { user_id: $currentUser.id, action: 'save', ...imap });
      showToast('✅ IMAP-Einstellungen gespeichert');
      imapConfigExistiert = true;
      imap.pass = '';
    } catch(e) {
      showToast('Fehler: ' + e.message);
    } finally {
      imapSpeichertLaeuft = false;
    }
  }

  async function imapTesten() {
    if (!imap.host || !imap.user_name) {
      showToast('Bitte IMAP-Host und Benutzername ausfüllen.'); return;
    }
    if (!imap.pass) {
      showToast('Bitte Passwort zum Testen eingeben.'); return;
    }
    imapTestLaeuft = true;
    imapTestStatus = null;
    imapTestNachricht = '';
    imapTestFolders = [];
    try {
      const res = await apiCall('imap-config', {
        user_id: $currentUser.id,
        action: 'test',
        host: imap.host,
        port: imap.port,
        user_name: imap.user_name,
        pass: imap.pass,
        folder: imap.folder,
        processed_folder: imap.processed_folder
      });
      if (res?.success) {
        imapTestStatus = 'success';
        let msg = '✅ Verbindung OK';
        if (typeof res.messages_new === 'number') msg += ' — ' + res.messages_new + ' ungelesene Mails';
        if (res.processed_folder_created) msg += ' — Ordner "' + res.processed_folder + '" automatisch angelegt';
        else if (res.processed_folder_warning) msg += ' — ⚠️ ' + res.processed_folder_warning;
        imapTestNachricht = msg;
        imapTestFolders = res.folders || [];
      } else {
        imapTestStatus = 'error';
        imapTestNachricht = res?.error || 'Verbindung fehlgeschlagen';
        imapTestFolders = res?.folders || [];
      }
    } catch(e) {
      imapTestStatus = 'error';
      imapTestNachricht = e.message;
    } finally {
      imapTestLaeuft = false;
    }
  }

  async function imapLoeschen() {
    if (!confirm('IMAP-Konfiguration wirklich löschen?\n\nDer 30-Minuten-Import wird damit deaktiviert.')) return;
    imapLoeschenLaeuft = true;
    try {
      await apiCall('imap-config', { user_id: $currentUser.id, action: 'delete' });
      showToast('✅ IMAP-Konfiguration gelöscht');
      imap = {
        email: '', host: 'imap.hostinger.com', port: 993, user_name: '', pass: '',
        folder: 'INBOX', processed_folder: 'Rechnungen', filter_betreff: '', aktiv: false
      };
      imapConfigExistiert = false;
      lastCheck = null;
      lastError = null;
    } catch(e) {
      showToast('Fehler: ' + e.message);
    } finally {
      imapLoeschenLaeuft = false;
    }
  }

  function formatDatum(iso) {
    if (!iso) return '—';
    try { return new Date(iso).toLocaleString('de-DE'); } catch { return iso; }
  }

  // ═══════════════════════════════════════════════════════
  // KAUF-NACHRICHT (eBay-Nachricht nach Kauf)
  // ═══════════════════════════════════════════════════════
  let kaufLaeuft = $state(false);
  let kaufSpeichertLaeuft = $state(false);
  let kaufVorlageRef = $state(null);

  let kauf = $state({
    kauf_nachricht_aktiv: false,
    kauf_nachricht_betreff: 'Danke für deinen Kauf!',
    kauf_nachricht_vorlage: 'Hallo {{buyer}},\n\nvielen Dank für deinen Kauf von "{{artikel}}" (Bestellung {{order_id}}).\n\nWir versenden die Ware schnellstmöglich.\n\nViele Grüße'
  });

  const kaufPlatzhalter = [
    { key: '{{buyer}}',    beschreibung: 'eBay-Username des Käufers' },
    { key: '{{artikel}}',  beschreibung: 'Artikelname' },
    { key: '{{menge}}',    beschreibung: 'Verkaufte Menge' },
    { key: '{{preis}}',    beschreibung: 'Stückpreis mit €-Zeichen' },
    { key: '{{order_id}}', beschreibung: 'eBay-Bestell-ID' }
  ];

  function kaufPlatzhalterEinfuegen(key) {
    const ta = kaufVorlageRef;
    if (!ta) {
      kauf.kauf_nachricht_vorlage = (kauf.kauf_nachricht_vorlage || '') + key;
      return;
    }
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const val = kauf.kauf_nachricht_vorlage || '';
    kauf.kauf_nachricht_vorlage = val.slice(0, start) + key + val.slice(end);
    setTimeout(() => {
      ta.focus();
      ta.selectionStart = ta.selectionEnd = start + key.length;
    }, 0);
  }

  function kaufVorschauText() {
    let t = kauf.kauf_nachricht_vorlage || '';
    return t
      .replace(/{{buyer}}/gi, 'max_mustermann')
      .replace(/{{artikel}}/gi, 'Windows 11 Pro Produktschlüssel')
      .replace(/{{menge}}/gi, '1')
      .replace(/{{preis}}/gi, '19,99 €')
      .replace(/{{order_id}}/gi, '12-34567-89012');
  }

  function kaufVorschauBetreff() {
    return (kauf.kauf_nachricht_betreff || '')
      .replace(/{{buyer}}/gi, 'max_mustermann')
      .replace(/{{artikel}}/gi, 'Windows 11 Pro Produktschlüssel')
      .replace(/{{order_id}}/gi, '12-34567-89012');
  }

  async function ladeKaufConfig() {
    if (!$currentUser) return;
    kaufLaeuft = true;
    try {
      const data = await apiCall('kauf-nachricht-config', { action: 'load', user_id: $currentUser.id });
      if (data?.config) {
        kauf = {
          kauf_nachricht_aktiv:   data.config.kauf_nachricht_aktiv   ?? false,
          kauf_nachricht_betreff: data.config.kauf_nachricht_betreff || kauf.kauf_nachricht_betreff,
          kauf_nachricht_vorlage: data.config.kauf_nachricht_vorlage || kauf.kauf_nachricht_vorlage
        };
      }
    } catch(e) {
      console.warn('Kauf-Nachricht-Config nicht geladen:', e?.message || e);
    } finally {
      kaufLaeuft = false;
    }
  }

  async function kaufSpeichern() {
    if (!kauf.kauf_nachricht_betreff?.trim()) { showToast('Bitte Betreff eingeben.'); return; }
    if (!kauf.kauf_nachricht_vorlage?.trim()) { showToast('Bitte Nachrichten-Text eingeben.'); return; }
    kaufSpeichertLaeuft = true;
    try {
      await apiCall('kauf-nachricht-config', {
        action: 'save',
        user_id: $currentUser.id,
        kauf_nachricht_aktiv:   kauf.kauf_nachricht_aktiv,
        kauf_nachricht_betreff: kauf.kauf_nachricht_betreff,
        kauf_nachricht_vorlage: kauf.kauf_nachricht_vorlage
      });
      showToast('✅ Kauf-Nachricht gespeichert');
    } catch(e) {
      showToast('Fehler: ' + e.message);
    } finally {
      kaufSpeichertLaeuft = false;
    }
  }

  // ═══════════════════════════════════════════════════════
  // Init
  // ═══════════════════════════════════════════════════════
  onMount(async () => {
    testEmail = $currentUser?.email || '';
    await ladeVersandConfig();
    await ladeImapConfig();
    await ladeKaufConfig();
  });
</script>

<div class="page-container">
  <div class="page-hdr">
    <div class="hdr-left">
      <button class="btn-back" onclick={() => goto('/einstellungen')}>← Zurück</button>
      <div>
        <div class="page-title">📧 E-Mail</div>
        <div class="page-sub">Rechnungen versenden (SMTP), empfangen (IMAP) und eBay-Nachrichten nach Kauf</div>
      </div>
    </div>
    {#if tab === 'versand'}
      <button class="btn-primary" onclick={speichern} disabled={speichertLaeuft}>
        {speichertLaeuft ? '⏳ Speichert…' : '💾 Speichern'}
      </button>
    {:else if tab === 'empfang'}
      <button class="btn-primary" onclick={imapSpeichern} disabled={imapSpeichertLaeuft}>
        {imapSpeichertLaeuft ? '⏳ Speichert…' : '💾 Speichern'}
      </button>
    {:else}
      <button class="btn-primary" onclick={kaufSpeichern} disabled={kaufSpeichertLaeuft}>
        {kaufSpeichertLaeuft ? '⏳ Speichert…' : '💾 Speichern'}
      </button>
    {/if}
  </div>

  <!-- TABS -->
  <div class="tab-bar">
    <button class="tab-btn" class:active={tab === 'versand'} onclick={() => tab = 'versand'}>
      📤 Versand (SMTP)
    </button>
    <button class="tab-btn" class:active={tab === 'empfang'} onclick={() => tab = 'empfang'}>
      📥 Empfang (IMAP)
      {#if imap.aktiv}
        <span class="tab-badge">aktiv</span>
      {/if}
    </button>
    <button class="tab-btn" class:active={tab === 'kauf'} onclick={() => tab = 'kauf'}>
      💬 Kauf-Nachricht (eBay)
      {#if kauf.kauf_nachricht_aktiv}
        <span class="tab-badge">aktiv</span>
      {/if}
    </button>
  </div>

  <!-- ═══════════════════════════════════════════════ -->
  <!-- TAB: VERSAND (SMTP)                              -->
  <!-- ═══════════════════════════════════════════════ -->
  {#if tab === 'versand'}
    {#if configLaeuft}
      <div class="config-laedt">⏳ Einstellungen werden geladen…</div>
    {/if}

    <div class="card">
      <div class="card-titel">⚡ Anbieter-Schnellauswahl</div>
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

    <div class="card">
      <div class="card-titel">🔌 SMTP-Verbindung</div>
      <div class="form-grid">
        <div class="form-group form-span2">
          <label>SMTP-Host *</label>
          <input bind:value={cfg.smtp_host} placeholder="z. B. smtp.hostinger.com" />
        </div>
        <div class="form-group">
          <label>Port</label>
          <input bind:value={cfg.smtp_port} type="number" placeholder="465" />
        </div>
        <div class="form-group">
          <label>Sicherheit</label>
          <div class="toggle-row">
            <label class="check-label">
              <input type="checkbox" bind:checked={cfg.smtp_secure} />
              SSL/TLS (Port 465)
            </label>
            <span class="hinweis-klein">Port 587 = STARTTLS &nbsp;·&nbsp; Port 465 = SSL/TLS</span>
          </div>
        </div>
        <div class="form-group">
          <label>Benutzername (E-Mail-Adresse) *</label>
          <input bind:value={cfg.smtp_user} type="email" placeholder="deine@email.de" />
        </div>
        <div class="form-group">
          <label>Passwort {cfg.smtp_pass ? '' : '(leer lassen = Passwort nicht ändern)'}</label>
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
          <span class="hinweis-klein">Das Passwort wird Base64-kodiert in der Datenbank gespeichert</span>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-titel">✉️ Absender</div>
      <div class="card-sub">Name und Adresse die beim Empfänger angezeigt werden</div>
      <div class="form-grid">
        <div class="form-group">
          <label>Absendername</label>
          <input bind:value={cfg.absender_name} placeholder="z. B. Mein eBay Shop" />
        </div>
        <div class="form-group">
          <label>Absender-E-Mail</label>
          <input bind:value={cfg.absender_email} type="email" placeholder="rechnungen@meinshop.de (leer = SMTP-User)" />
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-titel">📝 E-Mail Vorlage</div>
      <div class="card-sub">Vorlage für Betreff und Text beim Rechnungsversand. Variablen werden automatisch ersetzt.</div>
      <div class="variablen-hinweis">
        <span class="var-titel">Variablen:</span>
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
          <input bind:value={cfg.betreff_vorlage} placeholder={'Ihre Rechnung {{rechnung_nr}}'} />
        </div>
        <div class="form-group form-span2">
          <label>E-Mail Text</label>
          <textarea bind:value={cfg.text_vorlage} rows="8" placeholder="E-Mail-Text..."></textarea>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-titel">🤖 Automatischer Versand</div>
      <div class="auto-row">
        <div>
          <div class="auto-titel">Nach Rechnungserstellung automatisch senden</div>
          <div class="auto-sub">
            Wenn aktiviert, wird die Rechnung sofort nach automatischer Erstellung per E-Mail an den Käufer gesendet —
            aber nur wenn eine E-Mail-Adresse vom Käufer vorhanden ist.
          </div>
        </div>
        <button class="toggle-btn {cfg.auto_versand ? 'toggle-an' : 'toggle-aus'}"
          onclick={() => cfg.auto_versand = !cfg.auto_versand}>
          <span class="toggle-thumb"></span>
        </button>
      </div>
      {#if cfg.auto_versand}
        <div class="auto-aktiv-hinweis">✅ Auto-Versand aktiv</div>
      {:else}
        <div class="auto-inaktiv-hinweis">⏸ Auto-Versand inaktiv — Rechnungen manuell aus der Rechnungsliste senden</div>
      {/if}
    </div>

    <div class="card card-test">
      <div class="card-titel">🧪 Verbindung testen</div>
      <div class="card-sub">Einstellungen werden zuerst gespeichert, dann wird eine Test-E-Mail gesendet.</div>
      <div class="test-row">
        <input bind:value={testEmail} type="email" placeholder="test@example.com" style="flex:1;min-width:200px" />
        <button class="btn-primary" onclick={testSenden} disabled={testLaeuft}>
          {testLaeuft ? '⏳ Sende…' : '📤 Test-E-Mail senden'}
        </button>
      </div>
      {#if testStatus === 'success'}
        <div class="test-result test-ok">✅ {testNachricht}</div>
      {:else if testStatus === 'error'}
        <div class="test-result test-fehler">❌ {testNachricht}</div>
      {/if}
    </div>

    <div class="info-box">
      <div class="info-titel">💡 Hinweise</div>
      <ul class="info-liste">
        <li>Für <strong>Gmail</strong>: <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noreferrer">App-Passwort</a> erstellen (kein normales Google-Passwort)</li>
        <li>Zugangsdaten werden <strong>pro User</strong> separat gespeichert</li>
        <li>Passwort wird Base64-kodiert gespeichert und nie im Frontend angezeigt</li>
        <li>Rechnungen können einzeln oder als Batch per E-Mail gesendet werden</li>
      </ul>
    </div>
  {/if}

  <!-- ═══════════════════════════════════════════════ -->
  <!-- TAB: EMPFANG (IMAP)                              -->
  <!-- ═══════════════════════════════════════════════ -->
  {#if tab === 'empfang'}
    {#if imapLaeuft}
      <div class="config-laedt">⏳ IMAP-Einstellungen werden geladen…</div>
    {/if}

    <div class="card card-info">
      <div class="card-titel">📥 Wie funktioniert der Email-Import?</div>
      <ul class="info-liste" style="margin:0;padding-left:18px">
        <li>Alle <strong>30 Minuten</strong> werden ungelesene Mails aus deinem IMAP-Postfach abgeholt</li>
        <li>Emails mit <strong>PDF-Anhang</strong> werden automatisch von der KI analysiert (Mistral)</li>
        <li>Analysierte Rechnungen erscheinen unter <strong>Buchhaltung → Eingangsrechnungen → 📥 Posteingang</strong></li>
        <li>Du prüfst jede Rechnung manuell und klickst <strong>„Speichern"</strong> oder <strong>„Verwerfen"</strong></li>
        <li>Nach der Freigabe wird die Mail in den Ordner <strong>„{imap.processed_folder}"</strong> verschoben</li>
      </ul>
    </div>

    <div class="card">
      <div class="card-titel">⚡ Anbieter-Schnellauswahl</div>
      <div class="anbieter-grid">
        {#each imapAnbieter as a}
          <button class="anbieter-btn" class:aktiv={imap.host === a.host && imap.port === a.port}
            onclick={() => wendeImapAnbieterAn(a)} title={a.hinweis}>
            {a.name}
          </button>
        {/each}
      </div>
    </div>

    <div class="card">
      <div class="card-titel">🔌 IMAP-Verbindung</div>
      <div class="form-grid">
        <div class="form-group">
          <label>Verarbeitungs-Email</label>
          <input bind:value={imap.email} type="email" placeholder="belege@ai-online.cloud" />
          <span class="hinweis-klein">Nur Info — zeigt an welches Postfach gerade importiert wird</span>
        </div>
        <div class="form-group">
          <label>IMAP-Host *</label>
          <input bind:value={imap.host} placeholder="imap.hostinger.com" />
        </div>
        <div class="form-group">
          <label>Port</label>
          <input bind:value={imap.port} type="number" placeholder="993" />
          <span class="hinweis-klein">Standard: 993 (SSL/TLS)</span>
        </div>
        <div class="form-group">
          <label>Benutzername *</label>
          <input bind:value={imap.user_name} type="email" placeholder="belege@ai-online.cloud" />
        </div>
        <div class="form-group">
          <label>Passwort {imapConfigExistiert && !imap.pass ? '(leer lassen = nicht ändern)' : ''}</label>
          <div class="input-row">
            {#if imapPasswortZeigen}
              <input bind:value={imap.pass} type="text" placeholder="Passwort eingeben" style="flex:1" />
            {:else}
              <input bind:value={imap.pass} type="password" placeholder="Passwort eingeben" style="flex:1" />
            {/if}
            <button class="btn-ghost btn-sm" onclick={() => imapPasswortZeigen = !imapPasswortZeigen}>
              {imapPasswortZeigen ? '🙈' : '👁'}
            </button>
          </div>
          <span class="hinweis-klein">Das Passwort wird Base64-kodiert gespeichert</span>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-titel">📁 Ordner</div>
      <div class="form-grid">
        <div class="form-group">
          <label>Eingangsordner</label>
          <input bind:value={imap.folder} placeholder="INBOX" />
          <span class="hinweis-klein">In diesem Ordner wird nach neuen Rechnungen gesucht</span>
        </div>
        <div class="form-group">
          <label>Verarbeitet-Ordner</label>
          <input bind:value={imap.processed_folder} placeholder="Rechnungen" />
          <span class="hinweis-klein">Wird automatisch angelegt beim Verbindungstest</span>
        </div>
        <div class="form-group form-span2">
          <label>Betreff-Filter (optional)</label>
          <input bind:value={imap.filter_betreff} placeholder="z.B. Rechnung — leer = alle Mails prüfen" />
          <span class="hinweis-klein">Nur Mails mit diesem Text im Betreff werden verarbeitet. Leer lassen um alle Mails mit PDF-Anhang zu importieren.</span>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-titel">🤖 Automatischer Abruf</div>
      <div class="auto-row">
        <div>
          <div class="auto-titel">Alle 30 Minuten neue Mails abholen</div>
          <div class="auto-sub">
            Wenn aktiv, prüft das System alle 30 Minuten das IMAP-Postfach auf neue Mails mit PDF-Anhang.
            Die Anhänge werden von der KI analysiert und erscheinen im Posteingang der Eingangsrechnungen zur Freigabe.
          </div>
        </div>
        <button class="toggle-btn {imap.aktiv ? 'toggle-an' : 'toggle-aus'}"
          onclick={() => imap.aktiv = !imap.aktiv}>
          <span class="toggle-thumb"></span>
        </button>
      </div>
      {#if imap.aktiv}
        <div class="auto-aktiv-hinweis">✅ Import aktiv — nächster Lauf alle 30 Min</div>
      {:else}
        <div class="auto-inaktiv-hinweis">⏸ Import inaktiv — erst aktivieren wenn Verbindungstest erfolgreich</div>
      {/if}
    </div>

    <div class="card card-test">
      <div class="card-titel">🧪 Verbindung testen</div>
      <div class="card-sub">Prüft die Zugangsdaten, öffnet den Eingangsordner und legt den Verarbeitet-Ordner automatisch an, falls er fehlt.</div>
      <div class="test-row">
        <button class="btn-primary" onclick={imapTesten} disabled={imapTestLaeuft}>
          {imapTestLaeuft ? '⏳ Prüfe…' : '🔌 Verbindung jetzt testen'}
        </button>
        {#if imapConfigExistiert}
          <button class="btn-ghost btn-sm" onclick={imapLoeschen} disabled={imapLoeschenLaeuft} style="margin-left:auto">
            {imapLoeschenLaeuft ? '⏳ Lösche…' : '🗑️ Konfiguration löschen'}
          </button>
        {/if}
      </div>
      {#if imapTestStatus === 'success'}
        <div class="test-result test-ok">{imapTestNachricht}</div>
        {#if imapTestFolders.length > 0}
          <div class="folders-list">
            <span class="folders-titel">Verfügbare Ordner:</span>
            {#each imapTestFolders as f}
              <span class="folder-chip">{f}</span>
            {/each}
          </div>
        {/if}
      {:else if imapTestStatus === 'error'}
        <div class="test-result test-fehler">❌ {imapTestNachricht}</div>
        {#if imapTestFolders.length > 0}
          <div class="folders-list">
            <span class="folders-titel">Gefundene Ordner (benutze einen davon):</span>
            {#each imapTestFolders as f}
              <span class="folder-chip">{f}</span>
            {/each}
          </div>
        {/if}
      {/if}
    </div>

    {#if imapConfigExistiert && (lastCheck || lastError)}
      <div class="card card-status">
        <div class="card-titel">📊 Status</div>
        <div class="status-grid">
          <div>
            <div class="status-label">Letzter Abruf</div>
            <div class="status-val">{formatDatum(lastCheck)}</div>
          </div>
          {#if lastError}
            <div style="grid-column:1/-1">
              <div class="status-label" style="color:#dc2626">Letzter Fehler</div>
              <div class="status-error">{lastError}</div>
            </div>
          {/if}
        </div>
      </div>
    {/if}
  {/if}

  <!-- ═══════════════════════════════════════════════ -->
  <!-- TAB: KAUF-NACHRICHT (eBay)                       -->
  <!-- ═══════════════════════════════════════════════ -->
  {#if tab === 'kauf'}
    {#if kaufLaeuft}
      <div class="config-laedt">⏳ Einstellungen werden geladen…</div>
    {/if}

    <div class="card card-info">
      <div class="card-titel">💬 Wie funktioniert die Kauf-Nachricht?</div>
      <ul class="info-liste" style="margin:0;padding-left:18px">
        <li>Sobald ein Käufer einen Artikel kauft, sendet das System automatisch eine Nachricht <strong>über das eBay-Postfach</strong> an den Käufer</li>
        <li>Die Nachricht wird direkt aus eBay heraus zugestellt — <strong>nicht per E-Mail</strong></li>
        <li>Platzhalter wie <code>{'{{buyer}}'}</code> oder <code>{'{{artikel}}'}</code> werden automatisch durch echte Werte ersetzt</li>
        <li>Der Versand erfolgt im selben Workflow wie die Lagerreduzierung — keine zusätzliche Einrichtung nötig</li>
      </ul>
    </div>

    <div class="card">
      <div class="card-titel">🤖 Automatischer Versand</div>
      <div class="auto-row">
        <div>
          <div class="auto-titel">Nach jedem Kauf automatisch Nachricht senden</div>
          <div class="auto-sub">
            Wenn aktiviert, wird nach jedem Verkauf die unten konfigurierte Nachricht an den Käufer gesendet.
            Der Versand passiert sofort nach der Lagerreduzierung.
          </div>
        </div>
        <button class="toggle-btn {kauf.kauf_nachricht_aktiv ? 'toggle-an' : 'toggle-aus'}"
          onclick={() => kauf.kauf_nachricht_aktiv = !kauf.kauf_nachricht_aktiv}>
          <span class="toggle-thumb"></span>
        </button>
      </div>
      {#if kauf.kauf_nachricht_aktiv}
        <div class="auto-aktiv-hinweis">✅ Auto-Versand aktiv — jede neue Bestellung bekommt eine Nachricht</div>
      {:else}
        <div class="auto-inaktiv-hinweis">⏸ Auto-Versand inaktiv — Käufer erhalten keine automatische Nachricht</div>
      {/if}
    </div>

    <div class="card">
      <div class="card-titel">📝 Nachrichten-Vorlage</div>
      <div class="card-sub">Vorlage für Betreff und Text. Klick auf einen Platzhalter um ihn an der Cursor-Position einzufügen.</div>
      <div class="variablen-hinweis">
        <span class="var-titel">Platzhalter:</span>
        {#each kaufPlatzhalter as v}
          <button class="var-chip" onclick={() => kaufPlatzhalterEinfuegen(v.key)} title={v.beschreibung}>
            {v.key}
          </button>
        {/each}
      </div>
      <div class="form-grid">
        <div class="form-group form-span2">
          <label>Betreff *</label>
          <input bind:value={kauf.kauf_nachricht_betreff} placeholder="Danke für deinen Kauf!" />
          <span class="hinweis-klein">Wird als eBay-Nachrichten-Betreff verwendet</span>
        </div>
        <div class="form-group form-span2">
          <label>Nachrichten-Text *</label>
          <textarea bind:this={kaufVorlageRef} bind:value={kauf.kauf_nachricht_vorlage} rows="10"
            placeholder={'Hallo {{buyer}}, ...'}></textarea>
          <span class="hinweis-klein">Zeilenumbrüche werden übernommen. Keine HTML-Kenntnisse nötig.</span>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-titel">👁 Vorschau</div>
      <div class="card-sub">So sieht der Käufer deine Nachricht (mit Beispieldaten).</div>
      <div class="vorschau-box">
        <div class="vorschau-meta">
          <span class="vorschau-label">An:</span>
          <span class="vorschau-val">max_mustermann (eBay-Postfach)</span>
        </div>
        <div class="vorschau-meta">
          <span class="vorschau-label">Betreff:</span>
          <span class="vorschau-val"><strong>{kaufVorschauBetreff()}</strong></span>
        </div>
        <div class="vorschau-trenner"></div>
        <div class="vorschau-body">{kaufVorschauText()}</div>
      </div>
    </div>

    <div class="info-box">
      <div class="info-titel">💡 Hinweise</div>
      <ul class="info-liste">
        <li>Die Nachricht wird über die <strong>eBay Trading API</strong> gesendet (<code>AddMemberMessageAAQToPartner</code>) — erscheint beim Käufer im eBay-Postfach</li>
        <li>Jeder gesendete Versand wird in der Tabelle <code>kauf_nachrichten</code> protokolliert</li>
        <li>Die Vorlage gilt für <strong>alle</strong> Artikel — keine artikelspezifischen Vorlagen</li>
        <li>Beispielwerte in der Vorschau: <code>{'{{buyer}}'}</code> = max_mustermann, <code>{'{{preis}}'}</code> = 19,99 €</li>
      </ul>
    </div>
  {/if}
</div>

<style>
  .page-container { padding: 24px; max-width: 1200px; margin: 0 auto; }
  .page-hdr { display:flex; align-items:center; justify-content:space-between; gap:16px; margin-bottom:16px; }
  .page-title { font-size:1.4rem; font-weight:700; color:var(--text); }
  .page-sub { font-size:0.83rem; color:var(--text2); margin-top:2px; }
  .hdr-left { display:flex; align-items:center; gap:16px; }
  .btn-back {
    background: transparent; border: 1px solid var(--border); color: var(--text2);
    padding: 7px 14px; border-radius: 8px; font-size: 0.83rem; cursor: pointer;
    transition: all 0.15s; white-space: nowrap;
  }
  .btn-back:hover { border-color: var(--primary); color: var(--primary); }
  .config-laedt { font-size:0.8rem; color:var(--text2); padding:6px 12px; background:var(--surface2); border-radius:8px; margin-bottom:12px; }

  /* Tabs */
  .tab-bar { display:flex; gap:4px; border-bottom:1px solid var(--border); margin-bottom:16px; }
  .tab-btn {
    background:transparent; border:none; border-bottom:2px solid transparent;
    padding:10px 20px; font-size:0.88rem; color:var(--text2); cursor:pointer;
    font-weight:500; transition:all 0.15s; display:inline-flex; align-items:center; gap:8px;
  }
  .tab-btn:hover { color:var(--text); }
  .tab-btn.active { color:var(--primary); border-bottom-color:var(--primary); font-weight:600; }
  .tab-badge {
    background:#16a34a; color:#fff; font-size:0.65rem; padding:2px 6px;
    border-radius:10px; font-weight:600;
  }

  .card { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:20px 24px; display:flex; flex-direction:column; gap:14px; margin-bottom:16px; }
  .card-titel { font-size:0.9rem; font-weight:700; color:var(--text); }
  .card-sub { font-size:0.8rem; color:var(--text2); margin-top:-8px; }
  .card-test { border-color:var(--primary); }
  .card-info { background:var(--primary-light); border-color:var(--primary); }
  .card-status { background:var(--surface2); }

  .anbieter-grid { display:flex; gap:8px; flex-wrap:wrap; }
  .anbieter-btn { background:var(--surface2); border:1px solid var(--border); color:var(--text); padding:6px 14px; border-radius:8px; font-size:0.8rem; cursor:pointer; transition:all 0.15s; }
  .anbieter-btn:hover { border-color:var(--primary); color:var(--primary); }
  .anbieter-btn.aktiv { background:var(--primary); color:#fff; border-color:var(--primary); font-weight:600; }

  .form-grid { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
  .form-span2 { grid-column:1 / -1; }
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
  .auto-aktiv-hinweis { background:#f0fdf4; border:1px solid #bbf7d0; color:#16a34a; padding:8px 14px; border-radius:8px; font-size:0.8rem; }
  .auto-inaktiv-hinweis { background:var(--surface2); border:1px solid var(--border); color:var(--text2); padding:8px 14px; border-radius:8px; font-size:0.8rem; }
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
  .test-row input { background:var(--surface); border:1px solid var(--border); color:var(--text); padding:8px 12px; border-radius:8px; font-size:0.85rem; outline:none; box-sizing:border-box; }
  .test-row input:focus { border-color:var(--primary); }
  .test-result { padding:10px 14px; border-radius:8px; font-size:0.82rem; margin-top:4px; }
  .test-ok { background:#f0fdf4; border:1px solid #bbf7d0; color:#15803d; }
  .test-fehler { background:#fef2f2; border:1px solid #fecaca; color:#dc2626; }

  .folders-list { display:flex; flex-wrap:wrap; gap:6px; padding:10px 12px; background:var(--surface2); border-radius:8px; align-items:center; }
  .folders-titel { font-size:0.75rem; font-weight:600; color:var(--text2); white-space:nowrap; }
  .folder-chip { background:var(--surface); border:1px solid var(--border); color:var(--text); padding:2px 8px; border-radius:5px; font-size:0.72rem; font-family:monospace; }

  .status-grid { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
  .status-label { font-size:0.75rem; color:var(--text2); font-weight:500; }
  .status-val { font-size:0.85rem; color:var(--text); font-weight:500; }
  .status-error { font-size:0.78rem; color:#991b1b; background:#fef2f2; padding:8px 12px; border-radius:6px; border:1px solid #fecaca; margin-top:4px; line-height:1.5; }

  .vorschau-box {
    background:var(--surface2); border:1px solid var(--border); border-radius:10px;
    padding:16px 18px; display:flex; flex-direction:column; gap:6px;
  }
  .vorschau-meta { display:flex; gap:10px; font-size:0.82rem; }
  .vorschau-label { color:var(--text2); font-weight:600; min-width:60px; }
  .vorschau-val { color:var(--text); }
  .vorschau-trenner { height:1px; background:var(--border); margin:8px 0; }
  .vorschau-body {
    white-space:pre-wrap; font-size:0.85rem; color:var(--text); line-height:1.6;
    font-family:inherit;
  }

  .info-box { background:var(--surface2); border:1px solid var(--border); border-radius:10px; padding:16px 20px; }
  .info-titel { font-size:0.82rem; font-weight:700; color:var(--text); margin-bottom:10px; }
  .info-liste { margin:0; padding-left:18px; display:flex; flex-direction:column; gap:6px; }
  .info-liste li { font-size:0.8rem; color:var(--text2); line-height:1.5; }
  .info-liste a { color:var(--primary); }
  .info-liste code { background:var(--surface); padding:1px 5px; border-radius:4px; font-size:0.78rem; color:var(--primary); border:1px solid var(--border); }

  .btn-primary { background:var(--primary); color:#fff; border:none; padding:8px 16px; border-radius:8px; font-size:0.84rem; cursor:pointer; }
  .btn-primary:hover:not(:disabled) { filter:brightness(1.08); }
  .btn-primary:disabled { opacity:0.6; cursor:not-allowed; }
  .btn-ghost { background:transparent; border:1px solid var(--border); color:var(--text2); padding:8px 12px; border-radius:8px; font-size:0.84rem; cursor:pointer; }
  .btn-ghost:hover { border-color:var(--primary); color:var(--primary); }
  .btn-sm { padding:6px 10px; font-size:0.8rem; }

  @media(max-width:600px) {
    .form-grid { grid-template-columns:1fr; }
    .form-span2 { grid-column:1; }
    .status-grid { grid-template-columns:1fr; }
  }
</style>
