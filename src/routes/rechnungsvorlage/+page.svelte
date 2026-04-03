<script>
  import { onMount } from 'svelte';
  import { currentUser, showToast } from '$lib/stores.js';
  import { apiCall } from '$lib/api.js';

  // ── Tabs ──────────────────────────────────────────────────────────────────
  let aktiverTab = $state('vorlage'); // 'vorlage' | 'vorschau'

  // ── Vorlage-State ─────────────────────────────────────────────────────────
  let vorlage = $state({
    // Logo
    logo_base64: '',
    logo_position: 'links',   // links | rechts | mitte
    logo_breite: 120,

    // Farben & Schrift
    akzentfarbe: '#2563eb',
    schriftfarbe: '#1e293b',
    hintergrundfarbe: '#f8fafc',
    tabellenfarbe: '#2563eb',
    schriftart: 'Arial',
    schriftgroesse: 13,

    // Header
    header_zeige_logo: true,
    header_zeige_firmenname: true,
    header_zeige_adresse: true,
    header_zeige_kontakt: true,
    header_trennlinie: true,
    header_trennlinie_farbe: '#2563eb',
    header_trennlinie_staerke: 3,

    // Rechnungstitel
    titel_text: 'Rechnung',
    titel_groesse: 24,

    // Absenderblock (Firmendaten)
    firma_name: '',
    firma_strasse: '',
    firma_plz: '',
    firma_ort: '',
    firma_land: 'Deutschland',
    firma_telefon: '',
    firma_email: '',
    firma_website: '',
    firma_steuernr: '',
    firma_ust_idnr: '',
    firma_bank_iban: '',
    firma_bank_bic: '',
    firma_bank_name: '',

    // Einleitungstext
    einleitungstext: 'Ihre Bestellung Nr. [order_id] vom [datum].',

    // Tabelle
    tabelle_zeige_artnr: true,
    tabelle_zeige_menge: true,
    tabelle_zeige_einzelpreis: true,
    tabelle_zeige_betrag: true,
    tabelle_kopfzeilen: {
      artnr: 'Art.-Nr.',
      bezeichnung: 'Bezeichnung',
      menge: 'Menge',
      einzelpreis: 'Einzelpreis',
      betrag: 'Betrag'
    },

    // Fußzeile
    footer_text: 'Vielen Dank für Ihre Bestellung bei eBay.',
    footer_zeige_bank: true,
    footer_zeige_steuernr: true,
    footer_zeige_seite: true,
    footer_farbe: '#64748b',

    // Zahlungshinweis
    zahlungshinweis: 'Bereits bezahlt über eBay',
    zeige_zahlungshinweis: true,

    // Kleinunternehmer
    kleinunternehmer: false,
    kleinunternehmer_text: 'Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.',

    // Wasserzeichen
    wasserzeichen: false,
    wasserzeichen_text: 'ENTWURF',
  });

  let vorlageLaeuft = $state(false);
  let vorlageGeladen = $state(false);

  // ── Vorschau ──────────────────────────────────────────────────────────────
  let vorschauPDF = $state('');
  let vorschauLaeuft = $state(false);

  // Beispieldaten für Vorschau
  const beispiel = {
    rechnung_nr: 'RE-2026-00042',
    datum: '02.04.2026',
    order_id: '22-14426-19402',
    kaeufer_name: 'Hermann Jakob',
    kaeufer_strasse: 'Gneisenaustr. 12',
    kaeufer_plz: '85051',
    kaeufer_ort: 'Ingolstadt',
    kaeufer_land: 'Deutschland',
    artikel_name: 'Jemako Intensivreiniger KalkEx Plus',
    artikel_nr: '1054',
    menge: 1,
    einzelpreis: 15.9579,
    netto_betrag: 15.96,
    steuer_betrag: 3.03,
    brutto_betrag: 18.99,
    steuersatz: 19
  };

  // ── Lifecycle ─────────────────────────────────────────────────────────────
  onMount(async () => {
    if ($currentUser) await ladeVorlage();
  });

 async function ladeVorlage() {
  vorlageGeladen = true;
  try {
    const data = await apiCall('vorlage-laden', { user_id: $currentUser.id });
    if (data && data.vorlage) {
      vorlage = { ...vorlage, ...data.vorlage };
    }
  } catch(e) {
    // Workflow noch nicht aktiv — Standardwerte werden verwendet
  }
}

  async function speichereVorlage() {
    vorlageLaeuft = true;
    try {
      await apiCall('vorlage-speichern', {
        user_id: $currentUser.id,
        vorlage
      });
      showToast('Vorlage gespeichert ✓');
    } catch(e) {
      showToast('Fehler: ' + e.message);
    } finally {
      vorlageLaeuft = false;
    }
  }

  async function generiereVorschau() {
    vorschauLaeuft = true;
    aktiverTab = 'vorschau';
    try {
      const data = await apiCall('rechnung-vorschau', {
        user_id: $currentUser.id,
        vorlage,
        beispiel
      });
      vorschauPDF = data.pdf_base64 || '';
    } catch(e) {
      showToast('Vorschau-Fehler: ' + e.message);
    } finally {
      vorschauLaeuft = false;
    }
  }

  // ── Logo Upload ───────────────────────────────────────────────────────────
  function handleLogoUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) { showToast('Logo max. 2 MB'); return; }
    const reader = new FileReader();
    reader.onload = (ev) => { vorlage.logo_base64 = ev.target.result; };
    reader.readAsDataURL(file);
  }

  function logoEntfernen() {
    vorlage.logo_base64 = '';
  }

  // ── Live HTML-Vorschau (inline, kein Backend nötig) ──────────────────────
  let vorschauHTML = $derived.by(() => {
    const v = vorlage;
    const b = beispiel;
    const fmt = (n) => Number(n||0).toLocaleString('de-DE', {minimumFractionDigits:2,maximumFractionDigits:2});
    const w = 'EUR';

    const logoHTML = v.logo_base64
      ? `<img src="${v.logo_base64}" style="height:${v.logo_breite/2}px;max-width:${v.logo_breite}px;object-fit:contain;" alt="Logo">`
      : '';

    const firmaBlock = `
      <div style="font-size:11px;color:#888;margin-bottom:2px;">${v.firma_strasse ? v.firma_strasse+' · '+v.firma_plz+' '+v.firma_ort : ''}</div>
      ${v.firma_ust_idnr ? `<div style="font-size:11px;color:#888;">USt-IdNr.: ${v.firma_ust_idnr}</div>` : ''}
    `;

    const kontaktBlock = v.header_zeige_kontakt ? `
      <div style="font-size:12px;color:#555;line-height:1.8;">
        ${v.firma_telefon ? `<div>Tel: ${v.firma_telefon}</div>` : ''}
        ${v.firma_email ? `<div>E-Mail: ${v.firma_email}</div>` : ''}
        ${v.firma_website ? `<div>Web: ${v.firma_website}</div>` : ''}
        ${v.firma_steuernr ? `<div>Steuer-Nr.: ${v.firma_steuernr}</div>` : ''}
        ${v.firma_ust_idnr ? `<div>USt-IdNr.: ${v.firma_ust_idnr}</div>` : ''}
      </div>` : '';

    const steuerZeile = v.kleinunternehmer
      ? `<tr><td colspan="4" style="padding:8px 14px;font-size:11px;font-style:italic;color:#666;">${v.kleinunternehmer_text}</td></tr>`
      : `<tr><td colspan="3" style="padding:8px 14px;text-align:right;font-size:12px;color:#666;">MwSt. ${b.steuersatz}%</td><td style="padding:8px 14px;text-align:right;">${fmt(b.steuer_betrag)} ${w}</td></tr>`;

    const wasserzeichenHTML = v.wasserzeichen
      ? `<div style="position:fixed;top:50%;left:50%;transform:translate(-50%,-50%) rotate(-35deg);font-size:80px;color:rgba(0,0,0,0.06);font-weight:900;pointer-events:none;z-index:0;">${v.wasserzeichen_text}</div>`
      : '';

    return `<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:${v.schriftart},Arial,sans-serif;font-size:${v.schriftgroesse}px;color:${v.schriftfarbe};background:#fff;padding:32px;}
table{width:100%;border-collapse:collapse;margin-bottom:16px}
thead th{background:${v.tabellenfarbe};color:#fff;padding:9px 12px;text-align:left;font-size:12px;}
tbody td{padding:9px 12px;border-bottom:1px solid #e2e8f0}
.right{text-align:right}
.total td{font-weight:700;color:${v.akzentfarbe};background:${v.hintergrundfarbe}}
</style></head><body>
${wasserzeichenHTML}

<!-- HEADER -->
<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:28px;padding-bottom:16px;border-bottom:${v.header_trennlinie ? v.header_trennlinie_staerke+'px solid '+v.header_trennlinie_farbe : 'none'};">
  <div>
    ${v.header_zeige_logo && logoHTML ? `<div style="margin-bottom:10px;">${logoHTML}</div>` : ''}
    ${v.header_zeige_firmenname && v.firma_name ? `<div style="font-size:18px;font-weight:800;color:${v.akzentfarbe}">${v.firma_name}</div>` : ''}
    ${v.header_zeige_adresse ? firmaBlock : ''}
  </div>
  <div style="text-align:right">
    ${kontaktBlock}
  </div>
</div>

<!-- RECHNUNGSINFO -->
<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:24px;">
  <div style="padding:12px;background:${v.hintergrundfarbe};border-radius:6px;">
    <div style="font-size:9px;font-weight:700;color:#999;text-transform:uppercase;margin-bottom:6px;">Rechnungsempfänger</div>
    <div style="font-weight:700;font-size:13px;">${b.kaeufer_name}</div>
    <div style="font-size:12px;color:#555;">${b.kaeufer_strasse}</div>
    <div style="font-size:12px;color:#555;">${b.kaeufer_plz} ${b.kaeufer_ort}</div>
    <div style="font-size:12px;color:#555;">${b.kaeufer_land}</div>
  </div>
  <div style="padding:12px;background:${v.hintergrundfarbe};border-radius:6px;text-align:right;">
    <div style="font-size:9px;font-weight:700;color:#999;text-transform:uppercase;margin-bottom:6px;">Rechnung</div>
    <div style="font-size:22px;font-weight:800;color:${v.akzentfarbe};">${v.titel_text}</div>
    <div style="color:#555;margin-top:4px;">Nr: <strong>${b.rechnung_nr}</strong></div>
    <div style="font-size:12px;color:#666;">Datum: ${b.datum}</div>
    <div style="font-size:12px;color:#666;">Bestellung: ${b.order_id}</div>
  </div>
</div>

<!-- EINLEITUNGSTEXT -->
${v.einleitungstext ? `<div style="margin-bottom:20px;font-size:13px;color:#555;padding:10px 14px;background:${v.hintergrundfarbe};border-radius:6px;">${v.einleitungstext.replace('[order_id]', b.order_id).replace('[datum]', b.datum)}</div>` : ''}

<!-- POSITIONEN -->
<table>
  <thead>
    <tr>
      ${v.tabelle_zeige_artnr ? `<th style="width:70px">${v.tabelle_kopfzeilen.artnr}</th>` : ''}
      <th>${v.tabelle_kopfzeilen.bezeichnung}</th>
      ${v.tabelle_zeige_menge ? `<th class="right" style="width:60px">${v.tabelle_kopfzeilen.menge}</th>` : ''}
      ${v.tabelle_zeige_einzelpreis ? `<th class="right" style="width:100px">${v.tabelle_kopfzeilen.einzelpreis}</th>` : ''}
      ${v.tabelle_zeige_betrag ? `<th class="right" style="width:100px">${v.tabelle_kopfzeilen.betrag}</th>` : ''}
    </tr>
  </thead>
  <tbody>
    <tr>
      ${v.tabelle_zeige_artnr ? `<td>${b.artikel_nr}</td>` : ''}
      <td><strong>${b.artikel_name}</strong></td>
      ${v.tabelle_zeige_menge ? `<td class="right">${b.menge}</td>` : ''}
      ${v.tabelle_zeige_einzelpreis ? `<td class="right">${fmt(b.einzelpreis)} ${w}</td>` : ''}
      ${v.tabelle_zeige_betrag ? `<td class="right">${fmt(b.einzelpreis * b.menge)} ${w}</td>` : ''}
    </tr>
  </tbody>
</table>

<!-- SUMMEN -->
<table style="width:280px;margin-left:auto">
  <tbody>
    <tr><td style="padding:8px 14px;color:#666;">Nettobetrag</td><td style="padding:8px 14px;text-align:right">${fmt(b.netto_betrag)} ${w}</td></tr>
    ${steuerZeile}
    <tr class="total"><td style="padding:10px 14px;">Gesamtbetrag</td><td style="padding:10px 14px;text-align:right;">${fmt(b.brutto_betrag)} ${w}</td></tr>
  </tbody>
</table>

<!-- ZAHLUNGSHINWEIS -->
${v.zeige_zahlungshinweis && v.zahlungshinweis ? `<div style="margin-top:12px;display:inline-block;background:#f0fdf4;color:#16a34a;border:1px solid #86efac;border-radius:6px;padding:5px 12px;font-size:12px;font-weight:700;">${v.zahlungshinweis}</div>` : ''}

<!-- BANKDATEN -->
${v.footer_zeige_bank && v.firma_bank_iban ? `<div style="margin-top:16px;padding:12px;background:${v.hintergrundfarbe};border-radius:6px;font-size:12px;"><strong>Bankverbindung:</strong> ${v.firma_bank_name ? v.firma_bank_name+' · ' : ''}IBAN: ${v.firma_bank_iban}${v.firma_bank_bic ? ' · BIC: '+v.firma_bank_bic : ''}</div>` : ''}

<!-- FOOTER -->
<div style="margin-top:28px;padding-top:12px;border-top:1px solid #e2e8f0;font-size:11px;color:${v.footer_farbe};text-align:center;">
  ${v.footer_text ? `<div>${v.footer_text}</div>` : ''}
  ${v.footer_zeige_steuernr && v.firma_steuernr ? `<div>Steuer-Nr.: ${v.firma_steuernr}${v.firma_ust_idnr ? ' · USt-IdNr.: '+v.firma_ust_idnr : ''}</div>` : ''}
</div>
</body></html>`;
  });

  // Sektion-Accordion
  let offeneSektionen = $state(new Set(['logo', 'farben', 'firma', 'header', 'tabelle', 'footer']));
  function toggleSektion(s) {
    const neu = new Set(offeneSektionen);
    neu.has(s) ? neu.delete(s) : neu.add(s);
    offeneSektionen = neu;
  }

  const schriftarten = ['Arial', 'Helvetica', 'Georgia', 'Times New Roman', 'Trebuchet MS', 'Verdana', 'Tahoma', 'Calibri'];
</script>

<div class="vb-container">

  <!-- Topbar -->
  <div class="vb-topbar">
    <div>
      <div class="vb-title">Rechnungsvorlage</div>
      <div class="vb-sub">Gestalte deine persönliche Rechnungsvorlage</div>
    </div>
    <div class="vb-topbar-actions">
      <div class="tab-switcher">
        <button class="tab-btn {aktiverTab === 'vorlage' ? 'active' : ''}" onclick={() => aktiverTab = 'vorlage'}>
          ⚙️ Einstellungen
        </button>
        <button class="tab-btn {aktiverTab === 'vorschau' ? 'active' : ''}" onclick={() => aktiverTab = 'vorschau'}>
          👁 Vorschau
        </button>
      </div>
      <button class="btn-ghost" onclick={generiereVorschau} disabled={vorschauLaeuft}>
        {vorschauLaeuft ? '⏳ Lädt…' : '🖨 PDF-Vorschau'}
      </button>
      <button class="btn-primary" onclick={speichereVorlage} disabled={vorlageLaeuft}>
        {vorlageLaeuft ? 'Speichert…' : '💾 Vorlage speichern'}
      </button>
    </div>
  </div>

  <!-- Body: Split-Layout -->
  <div class="vb-body">

    <!-- LINKE SEITE: Einstellungen -->
    {#if aktiverTab === 'vorlage'}
    <div class="vb-settings">

      <!-- LOGO -->
      <div class="sektion">
        <button class="sektion-hdr" onclick={() => toggleSektion('logo')}>
          <span>🖼 Logo</span>
          <span class="chevron {offeneSektionen.has('logo') ? 'offen' : ''}">›</span>
        </button>
        {#if offeneSektionen.has('logo')}
        <div class="sektion-body">
          {#if vorlage.logo_base64}
            <div class="logo-preview">
              <img src={vorlage.logo_base64} alt="Logo" style="max-height:60px;max-width:160px;object-fit:contain;" />
              <button class="btn-danger btn-sm" onclick={logoEntfernen}>Entfernen</button>
            </div>
          {:else}
            <label class="upload-zone">
              <input type="file" accept="image/*" onchange={handleLogoUpload} style="display:none" />
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
              <span>Logo hochladen (PNG, SVG, JPG — max. 2 MB)</span>
            </label>
          {/if}
          <div class="form-row">
            <div class="form-group">
              <label>Position</label>
              <select bind:value={vorlage.logo_position}>
                <option value="links">Links</option>
                <option value="rechts">Rechts</option>
                <option value="mitte">Mitte</option>
              </select>
            </div>
            <div class="form-group">
              <label>Breite (px)</label>
              <input type="number" min="40" max="300" bind:value={vorlage.logo_breite} />
            </div>
          </div>
        </div>
        {/if}
      </div>

      <!-- FARBEN & SCHRIFT -->
      <div class="sektion">
        <button class="sektion-hdr" onclick={() => toggleSektion('farben')}>
          <span>🎨 Farben & Schrift</span>
          <span class="chevron {offeneSektionen.has('farben') ? 'offen' : ''}">›</span>
        </button>
        {#if offeneSektionen.has('farben')}
        <div class="sektion-body">
          <div class="form-row">
            <div class="form-group">
              <label>Akzentfarbe</label>
              <div class="color-row">
                <input type="color" bind:value={vorlage.akzentfarbe} class="color-input" />
                <input type="text" bind:value={vorlage.akzentfarbe} class="color-text" />
              </div>
            </div>
            <div class="form-group">
              <label>Tabellenfarbe</label>
              <div class="color-row">
                <input type="color" bind:value={vorlage.tabellenfarbe} class="color-input" />
                <input type="text" bind:value={vorlage.tabellenfarbe} class="color-text" />
              </div>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Schriftfarbe</label>
              <div class="color-row">
                <input type="color" bind:value={vorlage.schriftfarbe} class="color-input" />
                <input type="text" bind:value={vorlage.schriftfarbe} class="color-text" />
              </div>
            </div>
            <div class="form-group">
              <label>Hintergrund</label>
              <div class="color-row">
                <input type="color" bind:value={vorlage.hintergrundfarbe} class="color-input" />
                <input type="text" bind:value={vorlage.hintergrundfarbe} class="color-text" />
              </div>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Schriftart</label>
              <select bind:value={vorlage.schriftart}>
                {#each schriftarten as s}
                  <option value={s}>{s}</option>
                {/each}
              </select>
            </div>
            <div class="form-group">
              <label>Schriftgröße (px)</label>
              <input type="number" min="10" max="18" bind:value={vorlage.schriftgroesse} />
            </div>
          </div>
          <!-- Farbthemen Schnellauswahl -->
          <div class="form-group">
            <label>Schnellauswahl Farbthema</label>
            <div class="themen-grid">
              {#each [
                { name:'Blau', a:'#2563eb', t:'#2563eb', bg:'#f8fafc' },
                { name:'Grün', a:'#16a34a', t:'#16a34a', bg:'#f0fdf4' },
                { name:'Rot', a:'#dc2626', t:'#dc2626', bg:'#fef2f2' },
                { name:'Lila', a:'#7c3aed', t:'#7c3aed', bg:'#f5f3ff' },
                { name:'Grau', a:'#374151', t:'#374151', bg:'#f9fafb' },
                { name:'Orange', a:'#ea580c', t:'#ea580c', bg:'#fff7ed' },
              ] as thema}
                <button
                  class="thema-btn"
                  style="border-color:{thema.a}"
                  onclick={() => { vorlage.akzentfarbe = thema.a; vorlage.tabellenfarbe = thema.t; vorlage.header_trennlinie_farbe = thema.a; vorlage.hintergrundfarbe = thema.bg; }}
                >
                  <span class="thema-farbe" style="background:{thema.a}"></span>
                  {thema.name}
                </button>
              {/each}
            </div>
          </div>
        </div>
        {/if}
      </div>

      <!-- FIRMENDATEN -->
      <div class="sektion">
        <button class="sektion-hdr" onclick={() => toggleSektion('firma')}>
          <span>🏢 Firmendaten</span>
          <span class="chevron {offeneSektionen.has('firma') ? 'offen' : ''}">›</span>
        </button>
        {#if offeneSektionen.has('firma')}
        <div class="sektion-body">
          <div class="form-group"><label>Firmenname *</label><input bind:value={vorlage.firma_name} placeholder="Meine Firma GmbH" /></div>
          <div class="form-group"><label>Straße & Hausnr.</label><input bind:value={vorlage.firma_strasse} placeholder="Musterstr. 1" /></div>
          <div class="form-row">
            <div class="form-group"><label>PLZ</label><input bind:value={vorlage.firma_plz} placeholder="12345" /></div>
            <div class="form-group"><label>Ort</label><input bind:value={vorlage.firma_ort} placeholder="Berlin" /></div>
          </div>
          <div class="form-row">
            <div class="form-group"><label>Telefon</label><input bind:value={vorlage.firma_telefon} placeholder="+49 221 …" /></div>
            <div class="form-group"><label>E-Mail</label><input bind:value={vorlage.firma_email} placeholder="info@firma.de" /></div>
          </div>
          <div class="form-row">
            <div class="form-group"><label>Website</label><input bind:value={vorlage.firma_website} placeholder="www.firma.de" /></div>
            <div class="form-group"><label>Steuer-Nr.</label><input bind:value={vorlage.firma_steuernr} placeholder="342/5058/2211" /></div>
          </div>
          <div class="form-group"><label>USt-IdNr.</label><input bind:value={vorlage.firma_ust_idnr} placeholder="DE123456789" /></div>
          <div class="form-row">
            <div class="form-group"><label>IBAN</label><input bind:value={vorlage.firma_bank_iban} placeholder="DE12 3456 7890 …" /></div>
            <div class="form-group"><label>BIC</label><input bind:value={vorlage.firma_bank_bic} placeholder="COBADEFFXXX" /></div>
          </div>
          <div class="form-group"><label>Bankname</label><input bind:value={vorlage.firma_bank_name} placeholder="Commerzbank" /></div>
        </div>
        {/if}
      </div>

      <!-- HEADER -->
      <div class="sektion">
        <button class="sektion-hdr" onclick={() => toggleSektion('header')}>
          <span>📄 Header</span>
          <span class="chevron {offeneSektionen.has('header') ? 'offen' : ''}">›</span>
        </button>
        {#if offeneSektionen.has('header')}
        <div class="sektion-body">
          <div class="toggle-list">
            <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.header_zeige_logo} /><span>Logo anzeigen</span></label>
            <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.header_zeige_firmenname} /><span>Firmenname anzeigen</span></label>
            <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.header_zeige_adresse} /><span>Adresse anzeigen</span></label>
            <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.header_zeige_kontakt} /><span>Kontaktdaten anzeigen</span></label>
            <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.header_trennlinie} /><span>Trennlinie</span></label>
          </div>
          {#if vorlage.header_trennlinie}
          <div class="form-row">
            <div class="form-group">
              <label>Linienfarbe</label>
              <div class="color-row">
                <input type="color" bind:value={vorlage.header_trennlinie_farbe} class="color-input" />
                <input type="text" bind:value={vorlage.header_trennlinie_farbe} class="color-text" />
              </div>
            </div>
            <div class="form-group">
              <label>Linienstärke (px)</label>
              <input type="number" min="1" max="10" bind:value={vorlage.header_trennlinie_staerke} />
            </div>
          </div>
          {/if}
          <div class="form-group">
            <label>Rechnungstitel</label>
            <input bind:value={vorlage.titel_text} placeholder="Rechnung" />
          </div>
          <div class="form-group">
            <label>Einleitungstext</label>
            <textarea bind:value={vorlage.einleitungstext} rows="2" placeholder="Ihre Bestellung Nr. [order_id] vom [datum]."></textarea>
            <span class="hint">Platzhalter: &#123;order_id&#125;, &#123;datum&#125;</span>
          </div>
        </div>
        {/if}
      </div>

      <!-- TABELLE -->
      <div class="sektion">
        <button class="sektion-hdr" onclick={() => toggleSektion('tabelle')}>
          <span>📋 Positionstabelle</span>
          <span class="chevron {offeneSektionen.has('tabelle') ? 'offen' : ''}">›</span>
        </button>
        {#if offeneSektionen.has('tabelle')}
        <div class="sektion-body">
          <div class="toggle-list">
            <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.tabelle_zeige_artnr} /><span>Art.-Nr. Spalte</span></label>
            <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.tabelle_zeige_menge} /><span>Menge Spalte</span></label>
            <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.tabelle_zeige_einzelpreis} /><span>Einzelpreis Spalte</span></label>
            <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.tabelle_zeige_betrag} /><span>Betrag Spalte</span></label>
          </div>
          <div class="form-group"><label>Kopfzeile „Art.-Nr."</label><input bind:value={vorlage.tabelle_kopfzeilen.artnr} /></div>
          <div class="form-group"><label>Kopfzeile „Bezeichnung"</label><input bind:value={vorlage.tabelle_kopfzeilen.bezeichnung} /></div>
          <div class="form-row">
            <div class="form-group"><label>Kopfzeile „Menge"</label><input bind:value={vorlage.tabelle_kopfzeilen.menge} /></div>
            <div class="form-group"><label>Kopfzeile „Einzelpreis"</label><input bind:value={vorlage.tabelle_kopfzeilen.einzelpreis} /></div>
          </div>
          <div class="form-group"><label>Kopfzeile „Betrag"</label><input bind:value={vorlage.tabelle_kopfzeilen.betrag} /></div>
        </div>
        {/if}
      </div>

      <!-- FOOTER & SONSTIGES -->
      <div class="sektion">
        <button class="sektion-hdr" onclick={() => toggleSektion('footer')}>
          <span>🦶 Footer & Sonstiges</span>
          <span class="chevron {offeneSektionen.has('footer') ? 'offen' : ''}">›</span>
        </button>
        {#if offeneSektionen.has('footer')}
        <div class="sektion-body">
          <div class="form-group">
            <label>Fußtext</label>
            <textarea bind:value={vorlage.footer_text} rows="2" placeholder="Vielen Dank für Ihre Bestellung."></textarea>
          </div>
          <div class="form-group">
            <label>Fußtext-Farbe</label>
            <div class="color-row">
              <input type="color" bind:value={vorlage.footer_farbe} class="color-input" />
              <input type="text" bind:value={vorlage.footer_farbe} class="color-text" />
            </div>
          </div>
          <div class="toggle-list">
            <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.footer_zeige_bank} /><span>Bankdaten im Footer</span></label>
            <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.footer_zeige_steuernr} /><span>Steuernummer im Footer</span></label>
            <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.footer_zeige_seite} /><span>Seitenummer</span></label>
          </div>
          <div class="form-group" style="margin-top:12px">
            <label>Zahlungshinweis</label>
            <input bind:value={vorlage.zahlungshinweis} placeholder="Bereits bezahlt über eBay" />
          </div>
          <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.zeige_zahlungshinweis} /><span>Zahlungshinweis anzeigen</span></label>
          <div style="margin-top:14px;border-top:1px solid var(--border);padding-top:14px">
            <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.kleinunternehmer} /><span>Kleinunternehmer (§ 19 UStG)</span></label>
            {#if vorlage.kleinunternehmer}
              <div class="form-group" style="margin-top:8px">
                <label>Hinweistext</label>
                <textarea bind:value={vorlage.kleinunternehmer_text} rows="2"></textarea>
              </div>
            {/if}
            <label class="toggle-item" style="margin-top:10px"><input type="checkbox" bind:checked={vorlage.wasserzeichen} /><span>Wasserzeichen</span></label>
            {#if vorlage.wasserzeichen}
              <div class="form-group" style="margin-top:8px">
                <label>Wasserzeichen-Text</label>
                <input bind:value={vorlage.wasserzeichen_text} placeholder="ENTWURF" />
              </div>
            {/if}
          </div>
        </div>
        {/if}
      </div>

    </div>
    {/if}

    <!-- RECHTE SEITE: Live-Vorschau -->
    <div class="vb-preview" class:vb-preview-fullscreen={aktiverTab === 'vorschau'}>
      <div class="preview-hdr">
        <span>Live-Vorschau</span>
        <span class="preview-hint">Aktualisiert sich automatisch</span>
      </div>
      <div class="preview-frame-wrap">
        {#if aktiverTab === 'vorschau' && vorschauPDF}
          <!-- PDF-Vorschau via base64 -->
          <iframe
            src="data:application/pdf;base64,{vorschauPDF}"
            title="PDF Vorschau"
            class="pdf-iframe"
          ></iframe>
        {:else}
          <!-- Live HTML-Vorschau -->
          <iframe
            srcdoc={vorschauHTML}
            title="HTML Vorschau"
            class="preview-iframe"
            sandbox="allow-same-origin"
          ></iframe>
        {/if}
      </div>
    </div>

  </div>
</div>

<style>
  .vb-container {
    display: flex; flex-direction: column;
    height: calc(100vh - 56px);
    background: var(--bg);
    margin: -28px -32px;
  }
  .vb-topbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 20px; background: var(--surface); border-bottom: 1px solid var(--border);
    flex-wrap: wrap; gap: 10px; flex-shrink: 0;
  }
  .vb-title { font-size: 1.1rem; font-weight: 700; color: var(--text); }
  .vb-sub   { font-size: 0.78rem; color: var(--text2); }
  .vb-topbar-actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .tab-switcher { display: flex; background: var(--surface2); border-radius: 8px; padding: 3px; gap: 2px; }
  .tab-btn { background: transparent; border: none; padding: 5px 12px; border-radius: 6px; font-size: 0.8rem; color: var(--text2); cursor: pointer; transition: all 0.15s; }
  .tab-btn.active { background: var(--surface); color: var(--text); font-weight: 600; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
  .btn-primary { background: var(--primary); color: #fff; border: none; padding: 7px 14px; border-radius: 8px; font-size: 0.83rem; cursor: pointer; transition: background 0.15s; }
  .btn-primary:hover:not(:disabled) { filter: brightness(1.1); }
  .btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
  .btn-ghost { background: transparent; border: 1px solid var(--border); color: var(--text2); padding: 7px 12px; border-radius: 8px; font-size: 0.83rem; cursor: pointer; transition: all 0.15s; }
  .btn-ghost:hover:not(:disabled) { border-color: var(--primary); color: var(--primary); }
  .btn-ghost:disabled { opacity: 0.6; cursor: not-allowed; }
  .btn-danger { background: #ef4444; color: #fff; border: none; padding: 6px 12px; border-radius: 6px; font-size: 0.8rem; cursor: pointer; }
  .btn-sm { padding: 5px 10px; font-size: 0.78rem; }

  .vb-body { display: flex; flex: 1; overflow: hidden; }

  /* Einstellungen-Panel: breiter für gut lesbare Felder */
  .vb-settings {
    width: 440px;
    flex-shrink: 0;
    overflow-y: auto;
    border-right: 1px solid var(--border);
    background: var(--surface);
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .sektion { border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
  .sektion-hdr {
    width: 100%; background: var(--surface2); border: none;
    padding: 10px 14px; display: flex; justify-content: space-between; align-items: center;
    font-size: 0.83rem; font-weight: 600; color: var(--text); cursor: pointer; transition: background 0.15s;
  }
  .sektion-hdr:hover { background: var(--border); }
  .chevron { font-size: 1rem; color: var(--text2); transform: rotate(90deg); transition: transform 0.2s; }
  .chevron.offen { transform: rotate(270deg); }
  .sektion-body { padding: 12px 14px; display: flex; flex-direction: column; gap: 10px; }
  .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .form-group { display: flex; flex-direction: column; gap: 4px; }
  .form-group label { font-size: 0.73rem; color: var(--text2); font-weight: 500; }
  .form-group input, .form-group select, .form-group textarea {
    background: var(--bg); border: 1px solid var(--border); color: var(--text);
    padding: 7px 10px; border-radius: 7px; font-size: 0.83rem; outline: none;
    transition: border-color 0.15s; font-family: inherit;
    width: 100%; box-sizing: border-box;
  }
  .form-group input:focus, .form-group select:focus, .form-group textarea:focus { border-color: var(--primary); }
  .form-group textarea { resize: vertical; min-height: 52px; }
  .hint { font-size: 0.71rem; color: var(--text3); }
  .color-row { display: flex; gap: 6px; align-items: center; }
  .color-input { width: 36px; height: 32px; padding: 2px; border-radius: 6px; border: 1px solid var(--border); cursor: pointer; background: var(--bg); flex-shrink: 0; }
  .color-text { flex: 1; min-width: 0; }
  .toggle-list { display: flex; flex-direction: column; gap: 8px; }
  .toggle-item { display: flex; align-items: center; gap: 8px; font-size: 0.82rem; color: var(--text); cursor: pointer; }
  .toggle-item input[type="checkbox"] { width: 15px; height: 15px; cursor: pointer; accent-color: var(--primary); flex-shrink: 0; }
  .themen-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
  .thema-btn {
    display: flex; align-items: center; gap: 5px; padding: 5px 8px;
    background: var(--bg); border: 2px solid transparent; border-radius: 8px;
    font-size: 0.75rem; color: var(--text); cursor: pointer; transition: all 0.15s;
  }
  .thema-btn:hover { background: var(--surface2); }
  .thema-farbe { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
  .upload-zone {
    display: flex; flex-direction: column; align-items: center; gap: 8px;
    padding: 16px; border: 2px dashed var(--border); border-radius: 10px;
    cursor: pointer; color: var(--text2); font-size: 0.81rem; text-align: center;
    transition: border-color 0.15s, background 0.15s;
  }
  .upload-zone:hover { border-color: var(--primary); background: var(--surface2); color: var(--primary); }
  .logo-preview { display: flex; align-items: center; justify-content: space-between; padding: 10px; background: var(--bg); border-radius: 8px; border: 1px solid var(--border); }

  /* Vorschau-Panel: scrollbar, A4-Seite zentriert */
  .vb-preview {
    flex: 1;
    display: flex;
    flex-direction: column;
    background: #cbd5e1;
    overflow: hidden;
  }
  .vb-preview-fullscreen { flex: 1; }
  .preview-hdr {
    padding: 8px 16px; background: var(--surface); border-bottom: 1px solid var(--border);
    font-size: 0.81rem; font-weight: 600; color: var(--text);
    display: flex; justify-content: space-between; align-items: center; flex-shrink: 0;
  }
  .preview-hint { font-size: 0.73rem; color: var(--text3); font-weight: 400; }

  /* Scrollbarer Bereich — A4 zentriert */
  .preview-frame-wrap {
    flex: 1;
    overflow: auto;
    padding: 24px;
    display: flex;
    justify-content: center;
    align-items: flex-start;
  }

  /* A4 bei 96dpi = 794×1123px */
  .preview-iframe {
    width: 794px;
    height: 1123px;
    flex-shrink: 0;
    background: white;
    border: none;
    border-radius: 2px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.3);
  }
  .pdf-iframe {
    width: 794px;
    height: 1123px;
    flex-shrink: 0;
    background: white;
    border: none;
    border-radius: 2px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.3);
  }

  @media (max-width: 1200px) {
    .vb-settings { width: 380px; }
  }
  @media (max-width: 900px) {
    .vb-body { flex-direction: column; }
    .vb-settings { width: 100%; border-right: none; border-bottom: 1px solid var(--border); max-height: 45vh; }
    .preview-iframe, .pdf-iframe { width: 100%; height: 600px; }
  }
</style>
