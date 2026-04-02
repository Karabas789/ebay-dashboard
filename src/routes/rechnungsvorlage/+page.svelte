<script>
  import { onMount } from 'svelte';
  import { currentUser, showToast } from '$lib/stores.js';
  import { apiCall } from '$lib/api.js';

  // Tabs
  let aktiverTab = $state('vorlage'); // 'vorlage' | 'vorschau'

  // Sektionen aufklappbar
  let offeneSektionen = $state(new Set(['logo', 'farben', 'firma', 'header', 'tabelle', 'footer']));
  function toggleSektion(key) {
    const neu = new Set(offeneSektionen);
    neu.has(key) ? neu.delete(key) : neu.add(key);
    offeneSektionen = neu;
  }

  const schriftarten = ['Arial', 'Helvetica', 'Times New Roman', 'Georgia', 'Courier New', 'Verdana'];

  // Vorlage-State
  let vorlage = $state({
    // Logo
    logo_base64: '',
    logo_position: 'links', // links | rechts | mitte
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
    titeltext: 'Rechnung',
    titelgroesse: 24,
    // Absenderblock / Firmendaten
    firmaname: '',
    firmastrasse: '',
    firmaplz: '',
    firmaort: '',
    firmaland: 'Deutschland',
    firmatelefon: '',
    firmaemail: '',
    firmawebsite: '',
    firmasteuernr: '',
    firmaustidnr: '',
    firmabankiban: '',
    firmabankbic: '',
    firmabankname: '',
    // Einleitungstext
    einleitungstext: 'Ihre Bestellung Nr. {order_id} vom {datum}.',
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
      betrag: 'Betrag',
    },
    // Footer
    footertext: 'Vielen Dank für Ihre Bestellung bei eBay.',
    footer_zeige_bank: true,
    footer_zeige_steuernr: true,
    footer_zeige_seite: true,
    footerfarbe: '#64748b',
    // Zahlungshinweis
    zahlungshinweis: 'Bereits bezahlt über eBay',
    zeige_zahlungshinweis: true,
    // Kleinunternehmer
    kleinunternehmer: false,
    kleinunternehmertext: 'Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.',
    // Wasserzeichen
    wasserzeichen: false,
    wasserzeichentext: 'ENTWURF',
  });

  let vorlageLaeuft = $state(false);
  let vorlageGeladen = $state(false);

  // Vorschau
  let vorschauPDF = $state('');
  let vorschauLaeuft = $state(false);

  // Beispieldaten für Vorschau
  const beispiel = {
    rechnungnr: 'RE-2026-00042',
    datum: '02.04.2026',
    order_id: '22-14426-19402',
    kaeufername: 'Hermann Jakob',
    kaeuferstrasse: 'Gneisenaustr. 12',
    kaeuferplz: '85051',
    kaeuferort: 'Ingolstadt',
    kaeuferland: 'Deutschland',
    artikelname: 'Jemako Intensivreiniger KalkEx Plus',
    artikelnr: '1054',
    menge: 1,
    einzelpreis: 15.9579,
    nettobetrag: 15.96,
    steuerbetrag: 3.03,
    bruttobetrag: 18.99,
    steuersatz: 19,
  };

  // Lifecycle
  onMount(() => {
    if ($currentUser) ladeVorlage();
    else vorlageGeladen = true;
  });

  async function ladeVorlage() {
    const timeout = setTimeout(() => { vorlageGeladen = true; }, 5000);
    try {
      const data = await apiCall('vorlage-laden', { userid: $currentUser.id });
      if (data?.vorlage) vorlage = { ...vorlage, ...data.vorlage };
    } catch(e) {
      // Webhook noch nicht vorhanden — Standardwerte nutzen
    } finally {
      clearTimeout(timeout);
      vorlageGeladen = true;
    }
  }

  async function speichereVorlage() {
    vorlageLaeuft = true;
    try {
      await apiCall('vorlage-speichern', { userid: $currentUser.id, vorlage });
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
      const data = await apiCall('rechnung-vorschau', { userid: $currentUser.id, vorlage, beispiel });
      vorschauPDF = data.pdfbase64;
    } catch(e) {
      showToast('Vorschau-Fehler: ' + e.message);
    } finally {
      vorschauLaeuft = false;
    }
  }

  // Logo Upload
  function handleLogoUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) { showToast('Logo max. 2 MB'); return; }
    const reader = new FileReader();
    reader.onload = (ev) => { vorlage.logo_base64 = ev.target.result; };
    reader.readAsDataURL(file);
  }
  function logoEntfernen() { vorlage.logo_base64 = ''; }

  // Live HTML-Vorschau (inline, kein Backend nötig)
  let vorschauHTML = $derived.by(() => {
    const v = vorlage;
    const b = beispiel;
    const fmt = n => Number(n||0).toLocaleString('de-DE', { minimumFractionDigits:2, maximumFractionDigits:2 });
    const w = '€';

    const logoHTML = v.logo_base64
      ? `<img src="${v.logo_base64}" style="height:${v.logo_breite/2}px;max-width:${v.logo_breite}px;object-fit:contain" alt="Logo">`
      : '';

    const firmaBlock = `
      <div style="font-size:15px;font-weight:700;margin-bottom:2px">${v.firmaname || 'Firmenname'}</div>
      ${v.header_zeige_adresse && v.firmastrasse ? `<div style="font-size:11px;color:#888;margin-bottom:2px">${v.firmastrasse}, ${v.firmaplz} ${v.firmaort}</div>` : ''}
      ${v.firmaustidnr ? `<div style="font-size:11px;color:#888">USt-IdNr. ${v.firmaustidnr}</div>` : ''}
    `;

    const kontaktBlock = v.header_zeige_kontakt ? `
      <div style="font-size:12px;color:#555;line-height:1.8">
        ${v.firmatelefon ? `<div>Tel ${v.firmatelefon}</div>` : ''}
        ${v.firmaemail ? `<div>E-Mail ${v.firmaemail}</div>` : ''}
        ${v.firmawebsite ? `<div>Web ${v.firmawebsite}</div>` : ''}
        ${v.firmasteuernr ? `<div>Steuer-Nr. ${v.firmasteuernr}</div>` : ''}
      </div>` : '';

    const steuerZeile = v.kleinunternehmer
      ? `<tr><td colspan="4" style="padding:8px 14px;font-size:11px;font-style:italic;color:#666">${v.kleinunternehmertext}</td></tr>`
      : `<tr>
          <td colspan="3" style="padding:8px 14px;text-align:right;font-size:12px;color:#666">MwSt. ${b.steuersatz}%</td>
          <td style="padding:8px 14px;text-align:right">${fmt(b.steuerbetrag)} ${w}</td>
         </tr>`;

    const wasserzeichenHTML = v.wasserzeichen
      ? `<div style="position:fixed;top:50%;left:50%;transform:translate(-50%,-50%) rotate(-35deg);font-size:80px;color:rgba(0,0,0,0.06);font-weight:900;pointer-events:none;z-index:0">${v.wasserzeichentext}</div>`
      : '';

    const einlText = v.einleitungstext
      .replace('{order_id}', b.order_id)
      .replace('{datum}', b.datum);

    const bankBlock = v.footer_zeige_bank && (v.firmabankiban || v.firmabankname)
      ? `<span style="margin-right:16px">Bank: ${v.firmabankname} | IBAN: ${v.firmabankiban} | BIC: ${v.firmabankbic}</span>`
      : '';

    const steuerBlock = v.footer_zeige_steuernr && v.firmasteuernr
      ? `<span>Steuer-Nr. ${v.firmasteuernr}</span>`
      : '';

    // Header layout
    let headerContent = '';
    if (v.logo_position === 'mitte') {
      headerContent = `<div style="text-align:center;margin-bottom:8px">${logoHTML}</div><div style="display:flex;justify-content:space-between">${v.header_zeige_firmenname ? firmaBlock : ''} ${kontaktBlock}</div>`;
    } else if (v.logo_position === 'rechts') {
      headerContent = `<div style="display:flex;justify-content:space-between;align-items:flex-start">${v.header_zeige_firmenname ? firmaBlock : ''} <div style="display:flex;flex-direction:column;align-items:flex-end;gap:8px">${logoHTML}${kontaktBlock}</div></div>`;
    } else {
      headerContent = `<div style="display:flex;justify-content:space-between;align-items:flex-start"><div style="display:flex;flex-direction:column;gap:6px">${logoHTML}${v.header_zeige_firmenname ? firmaBlock : ''}</div>${kontaktBlock}</div>`;
    }

    return `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
      *{margin:0;padding:0;box-sizing:border-box}
      body{font-family:${v.schriftart},Arial,sans-serif;font-size:${v.schriftgroesse}px;color:${v.schriftfarbe};background:#fff;padding:32px}
      table{width:100%;border-collapse:collapse;margin-bottom:16px}
      thead th{background:${v.tabellenfarbe};color:#fff;padding:9px 12px;text-align:left;font-size:12px}
      tbody td{padding:9px 12px;border-bottom:1px solid #e5e7eb}
      .right{text-align:right}
    </style></head><body>
    ${wasserzeichenHTML}
    ${headerContent}
    ${v.header_trennlinie ? `<hr style="border:none;border-top:${v.header_trennlinie_staerke}px solid ${v.header_trennlinie_farbe};margin:14px 0">` : '<div style="margin-bottom:14px"></div>'}
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:20px">
      <div>
        <div style="font-size:8px;color:#aaa;text-transform:uppercase;letter-spacing:1px;margin-bottom:2px">Rechnung an</div>
        <div style="font-weight:600">${b.kaeufername}</div>
        <div style="font-size:11px;color:#666">${b.kaeuferstrasse}</div>
        <div style="font-size:11px;color:#666">${b.kaeuferplz} ${b.kaeuferort}</div>
        <div style="font-size:11px;color:#666">${b.kaeuferland}</div>
      </div>
      <div style="text-align:right">
        <div style="font-size:${v.titelgroesse}px;font-weight:700;color:${v.akzentfarbe}">${v.titeltext}</div>
        <div style="font-size:12px;color:#555;margin-top:4px">${b.rechnungnr}</div>
        <div style="font-size:11px;color:#888">Datum: ${b.datum}</div>
        ${b.order_id ? `<div style="font-size:11px;color:#888">Bestellnr.: ${b.order_id}</div>` : ''}
      </div>
    </div>
    ${einlText ? `<p style="font-size:12px;color:#555;margin-bottom:14px">${einlText}</p>` : ''}
    <table>
      <thead><tr>
        ${v.tabelle_zeige_artnr ? `<th>${v.tabelle_kopfzeilen.artnr}</th>` : ''}
        <th>${v.tabelle_kopfzeilen.bezeichnung}</th>
        ${v.tabelle_zeige_menge ? `<th class="right">${v.tabelle_kopfzeilen.menge}</th>` : ''}
        ${v.tabelle_zeige_einzelpreis ? `<th class="right">${v.tabelle_kopfzeilen.einzelpreis}</th>` : ''}
        ${v.tabelle_zeige_betrag ? `<th class="right">${v.tabelle_kopfzeilen.betrag}</th>` : ''}
      </tr></thead>
      <tbody>
        <tr>
          ${v.tabelle_zeige_artnr ? `<td>${b.artikelnr}</td>` : ''}
          <td>${b.artikelname}</td>
          ${v.tabelle_zeige_menge ? `<td class="right">${b.menge}</td>` : ''}
          ${v.tabelle_zeige_einzelpreis ? `<td class="right">${fmt(b.einzelpreis)} ${w}</td>` : ''}
          ${v.tabelle_zeige_betrag ? `<td class="right">${fmt(b.nettobetrag)} ${w}</td>` : ''}
        </tr>
        <tr><td colspan="5" style="padding:8px 14px;text-align:right;font-size:12px;color:#666">Netto</td><td style="display:none"></td></tr>
        <tr>
          <td colspan="${[v.tabelle_zeige_artnr,v.tabelle_zeige_menge,v.tabelle_zeige_einzelpreis].filter(Boolean).length + 1}" style="padding:8px 14px;text-align:right;font-size:12px;color:#666">Netto</td>
          <td style="padding:8px 14px;text-align:right">${fmt(b.nettobetrag)} ${w}</td>
        </tr>
        ${steuerZeile}
        ${v.zeige_zahlungshinweis && v.zahlungshinweis ? `<tr><td colspan="5" style="padding:4px 14px;font-size:11px;color:#888;font-style:italic">${v.zahlungshinweis}</td></tr>` : ''}
        <tr style="background:${v.akzentfarbe}10">
          <td colspan="${[v.tabelle_zeige_artnr,v.tabelle_zeige_menge,v.tabelle_zeige_einzelpreis].filter(Boolean).length + 1}" style="padding:10px 14px;text-align:right;font-weight:700">Gesamt Brutto</td>
          <td style="padding:10px 14px;text-align:right;font-weight:700;color:${v.akzentfarbe}">${fmt(b.bruttobetrag)} ${w}</td>
        </tr>
      </tbody>
    </table>
    <div style="margin-top:24px;padding-top:12px;border-top:1px solid #e5e7eb;font-size:11px;color:${v.footerfarbe};line-height:1.8">
      ${v.footertext ? `<div>${v.footertext}</div>` : ''}
      <div style="margin-top:6px">${bankBlock} ${steuerBlock}</div>
    </div>
    </body></html>`;
  });
</script>

<div class="page">
  <div class="page-hdr">
    <div>
      <div class="page-title">Rechnungsvorlage</div>
      <div class="page-sub">Gestalte deine persönliche Rechnungsvorlage</div>
    </div>
    <div class="hdr-actions">
      <button class="tab-btn" class:active={aktiverTab === 'vorlage'} onclick={() => aktiverTab = 'vorlage'}>⚙️ Einstellungen</button>
      <button class="tab-btn" class:active={aktiverTab === 'vorschau'} onclick={() => aktiverTab = 'vorschau'}>👁 Vorschau</button>
      <button class="btn-secondary" onclick={generiereVorschau} disabled={vorschauLaeuft}>
        {vorschauLaeuft ? '⏳ Lädt…' : '🖨 PDF-Vorschau'}
      </button>
      <button class="btn-primary" onclick={speichereVorlage} disabled={vorlageLaeuft}>
        {vorlageLaeuft ? 'Speichert…' : '💾 Vorlage speichern'}
      </button>
    </div>
  </div>

  <div class="main-layout">
    <!-- LINKE SPALTE: Einstellungen -->
    {#if aktiverTab === 'vorlage'}
    <div class="einstellungen-spalte">

      <!-- LOGO -->
      <div class="sektion">
        <button class="sektion-hdr" onclick={() => toggleSektion('logo')}>
          🖼 Logo
          <span class="sektion-arrow">{offeneSektionen.has('logo') ? '▲' : '▼'}</span>
        </button>
        {#if offeneSektionen.has('logo')}
        <div class="sektion-body">
          {#if vorlage.logo_base64}
            <div class="logo-preview-row">
              <img src={vorlage.logo_base64} alt="Logo" style="max-height:60px;max-width:120px;object-fit:contain;border-radius:4px;border:1px solid var(--border)">
              <button class="btn-ghost btn-sm" onclick={logoEntfernen}>Entfernen</button>
            </div>
          {:else}
            <label class="upload-label">
              Logo hochladen (PNG, SVG, JPG — max. 2 MB)
              <input type="file" accept="image/*" onchange={handleLogoUpload} style="display:none">
            </label>
          {/if}
          <div class="form-row">
            <div class="form-group">
              <label for="logo-pos">Position</label>
              <select id="logo-pos" bind:value={vorlage.logo_position}>
                <option value="links">Links</option>
                <option value="rechts">Rechts</option>
                <option value="mitte">Mitte</option>
              </select>
            </div>
            <div class="form-group">
              <label for="logo-breite">Breite (px)</label>
              <input id="logo-breite" type="number" min="40" max="300" bind:value={vorlage.logo_breite}>
            </div>
          </div>
        </div>
        {/if}
      </div>

      <!-- FARBEN & SCHRIFT -->
      <div class="sektion">
        <button class="sektion-hdr" onclick={() => toggleSektion('farben')}>
          🎨 Farben & Schrift
          <span class="sektion-arrow">{offeneSektionen.has('farben') ? '▲' : '▼'}</span>
        </button>
        {#if offeneSektionen.has('farben')}
        <div class="sektion-body">
          <div class="form-row">
            <div class="form-group">
              <label for="akzentfarbe">Akzentfarbe</label>
              <div class="color-row">
                <input id="akzentfarbe" type="color" bind:value={vorlage.akzentfarbe} class="color-input">
                <span class="color-val">{vorlage.akzentfarbe}</span>
              </div>
            </div>
            <div class="form-group">
              <label for="tabellenfarbe">Tabellenfarbe</label>
              <div class="color-row">
                <input id="tabellenfarbe" type="color" bind:value={vorlage.tabellenfarbe} class="color-input">
                <span class="color-val">{vorlage.tabellenfarbe}</span>
              </div>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label for="schriftfarbe">Schriftfarbe</label>
              <div class="color-row">
                <input id="schriftfarbe" type="color" bind:value={vorlage.schriftfarbe} class="color-input">
                <span class="color-val">{vorlage.schriftfarbe}</span>
              </div>
            </div>
            <div class="form-group">
              <label for="hintergrundfarbe">Hintergrund</label>
              <div class="color-row">
                <input id="hintergrundfarbe" type="color" bind:value={vorlage.hintergrundfarbe} class="color-input">
                <span class="color-val">{vorlage.hintergrundfarbe}</span>
              </div>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label for="schriftart">Schriftart</label>
              <select id="schriftart" bind:value={vorlage.schriftart}>
                {#each schriftarten as s}
                  <option value={s}>{s}</option>
                {/each}
              </select>
            </div>
            <div class="form-group">
              <label for="schriftgroesse">Schriftgröße (px)</label>
              <input id="schriftgroesse" type="number" min="10" max="18" bind:value={vorlage.schriftgroesse}>
            </div>
          </div>
          <!-- Schnellauswahl Farbthema -->
          <div class="form-group">
            <label>Schnellauswahl Farbthema</label>
            <div class="themen-grid">
              {#each [
                { name:'Blau',   a:'#2563eb', t:'#2563eb', bg:'#f8fafc' },
                { name:'Grün',   a:'#16a34a', t:'#16a34a', bg:'#f0fdf4' },
                { name:'Rot',    a:'#dc2626', t:'#dc2626', bg:'#fef2f2' },
                { name:'Lila',   a:'#7c3aed', t:'#7c3aed', bg:'#f5f3ff' },
                { name:'Grau',   a:'#374151', t:'#374151', bg:'#f9fafb' },
                { name:'Orange', a:'#ea580c', t:'#ea580c', bg:'#fff7ed' },
              ] as thema}
                <button class="thema-btn" style="background:{thema.bg};border-color:{thema.a}"
                  onclick={() => { vorlage.akzentfarbe = thema.a; vorlage.tabellenfarbe = thema.t; vorlage.header_trennlinie_farbe = thema.a; vorlage.hintergrundfarbe = thema.bg; }}>
                  <span style="color:{thema.a}">{thema.name}</span>
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
          🏢 Firmendaten
          <span class="sektion-arrow">{offeneSektionen.has('firma') ? '▲' : '▼'}</span>
        </button>
        {#if offeneSektionen.has('firma')}
        <div class="sektion-body">
          <div class="form-group"><label for="firmaname">Firmenname *</label><input id="firmaname" bind:value={vorlage.firmaname} placeholder="Meine Firma GmbH"></div>
          <div class="form-group"><label for="firmastrasse">Straße & Hausnr.</label><input id="firmastrasse" bind:value={vorlage.firmastrasse} placeholder="Musterstr. 1"></div>
          <div class="form-row">
            <div class="form-group"><label for="firmaplz">PLZ</label><input id="firmaplz" bind:value={vorlage.firmaplz} placeholder="12345"></div>
            <div class="form-group"><label for="firmaort">Ort</label><input id="firmaort" bind:value={vorlage.firmaort} placeholder="Berlin"></div>
          </div>
          <div class="form-row">
            <div class="form-group"><label for="firmatelefon">Telefon</label><input id="firmatelefon" bind:value={vorlage.firmatelefon} placeholder="+49 221"></div>
            <div class="form-group"><label for="firmaemail">E-Mail</label><input id="firmaemail" bind:value={vorlage.firmaemail} placeholder="info@firma.de"></div>
          </div>
          <div class="form-row">
            <div class="form-group"><label for="firmawebsite">Website</label><input id="firmawebsite" bind:value={vorlage.firmawebsite} placeholder="www.firma.de"></div>
            <div class="form-group"><label for="firmasteuernr">Steuer-Nr.</label><input id="firmasteuernr" bind:value={vorlage.firmasteuernr} placeholder="34/250/58211"></div>
          </div>
          <div class="form-group"><label for="firmaustidnr">USt-IdNr.</label><input id="firmaustidnr" bind:value={vorlage.firmaustidnr} placeholder="DE123456789"></div>
          <div class="form-row">
            <div class="form-group"><label for="firmabankiban">IBAN</label><input id="firmabankiban" bind:value={vorlage.firmabankiban} placeholder="DE12 3456 7890"></div>
            <div class="form-group"><label for="firmabankbic">BIC</label><input id="firmabankbic" bind:value={vorlage.firmabankbic} placeholder="COBADEFFXXX"></div>
          </div>
          <div class="form-group"><label for="firmabankname">Bankname</label><input id="firmabankname" bind:value={vorlage.firmabankname} placeholder="Commerzbank"></div>
        </div>
        {/if}
      </div>

      <!-- HEADER -->
      <div class="sektion">
        <button class="sektion-hdr" onclick={() => toggleSektion('header')}>
          📄 Header
          <span class="sektion-arrow">{offeneSektionen.has('header') ? '▲' : '▼'}</span>
        </button>
        {#if offeneSektionen.has('header')}
        <div class="sektion-body">
          <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.header_zeige_logo}> <span>Logo anzeigen</span></label>
          <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.header_zeige_firmenname}> <span>Firmenname anzeigen</span></label>
          <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.header_zeige_adresse}> <span>Adresse anzeigen</span></label>
          <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.header_zeige_kontakt}> <span>Kontaktdaten anzeigen</span></label>
          <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.header_trennlinie}> <span>Trennlinie</span></label>
          {#if vorlage.header_trennlinie}
          <div class="form-row">
            <div class="form-group">
              <label for="trennliniefarbe">Linienfarbe</label>
              <div class="color-row">
                <input id="trennliniefarbe" type="color" bind:value={vorlage.header_trennlinie_farbe} class="color-input">
              </div>
            </div>
            <div class="form-group">
              <label for="trennliniestaerke">Linienstärke (px)</label>
              <input id="trennliniestaerke" type="number" min="1" max="10" bind:value={vorlage.header_trennlinie_staerke}>
            </div>
          </div>
          {/if}
          {#if vorlage.header_zeige_firmenname}
          <div class="form-group">
            <label for="titeltext">Rechnungstitel</label>
            <input id="titeltext" bind:value={vorlage.titeltext} placeholder="Rechnung">
          </div>
          <div class="form-group">
            <label for="einleitungstext">Einleitungstext</label>
            <textarea id="einleitungstext" bind:value={vorlage.einleitungstext} rows="2"
              placeholder="Ihre Bestellung Nr. {order_id} vom {datum}."></textarea>
            <span class="hint">Platzhalter: {'{order_id}'}, {'{datum}'}</span>
          </div>
          {/if}
        </div>
        {/if}
      </div>

      <!-- POSITIONSTABELLE -->
      <div class="sektion">
        <button class="sektion-hdr" onclick={() => toggleSektion('tabelle')}>
          📋 Positionstabelle
          <span class="sektion-arrow">{offeneSektionen.has('tabelle') ? '▲' : '▼'}</span>
        </button>
        {#if offeneSektionen.has('tabelle')}
        <div class="sektion-body">
          <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.tabelle_zeige_artnr}> <span>Art.-Nr. Spalte</span></label>
          <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.tabelle_zeige_menge}> <span>Menge Spalte</span></label>
          <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.tabelle_zeige_einzelpreis}> <span>Einzelpreis Spalte</span></label>
          <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.tabelle_zeige_betrag}> <span>Betrag Spalte</span></label>
          <div class="form-group"><label for="kz-artnr">Kopfzeile „Art.-Nr."</label><input id="kz-artnr" bind:value={vorlage.tabelle_kopfzeilen.artnr}></div>
          <div class="form-group"><label for="kz-bezeichnung">Kopfzeile „Bezeichnung"</label><input id="kz-bezeichnung" bind:value={vorlage.tabelle_kopfzeilen.bezeichnung}></div>
          <div class="form-row">
            <div class="form-group"><label for="kz-menge">Kopfzeile „Menge"</label><input id="kz-menge" bind:value={vorlage.tabelle_kopfzeilen.menge}></div>
            <div class="form-group"><label for="kz-einzelpreis">Kopfzeile „Einzelpreis"</label><input id="kz-einzelpreis" bind:value={vorlage.tabelle_kopfzeilen.einzelpreis}></div>
          </div>
          <div class="form-group"><label for="kz-betrag">Kopfzeile „Betrag"</label><input id="kz-betrag" bind:value={vorlage.tabelle_kopfzeilen.betrag}></div>
        </div>
        {/if}
      </div>

      <!-- FOOTER & SONSTIGES -->
      <div class="sektion">
        <button class="sektion-hdr" onclick={() => toggleSektion('footer')}>
          🦶 Footer & Sonstiges
          <span class="sektion-arrow">{offeneSektionen.has('footer') ? '▲' : '▼'}</span>
        </button>
        {#if offeneSektionen.has('footer')}
        <div class="sektion-body">
          <div class="form-group">
            <label for="footertext">Fußtext</label>
            <textarea id="footertext" bind:value={vorlage.footertext} rows="2"></textarea>
          </div>
          <div class="form-group">
            <label for="footerfarbe">Fußtext-Farbe</label>
            <div class="color-row">
              <input id="footerfarbe" type="color" bind:value={vorlage.footerfarbe} class="color-input">
              <span class="color-val">{vorlage.footerfarbe}</span>
            </div>
          </div>
          <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.footer_zeige_bank}> <span>Bankdaten im Footer</span></label>
          <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.footer_zeige_steuernr}> <span>Steuernummer im Footer</span></label>
          <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.footer_zeige_seite}> <span>Seitennummer</span></label>
          <div class="form-group" style="margin-top:12px">
            <label for="zahlungshinweis">Zahlungshinweis</label>
            <input id="zahlungshinweis" bind:value={vorlage.zahlungshinweis} placeholder="Bereits bezahlt über eBay">
          </div>
          <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.zeige_zahlungshinweis}> <span>Zahlungshinweis anzeigen</span></label>
          <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.kleinunternehmer}> <span>Kleinunternehmer (§ 19 UStG)</span></label>
          {#if vorlage.kleinunternehmer}
          <div class="form-group" style="margin-top:8px">
            <label for="kleinunternehmertext">Hinweistext</label>
            <textarea id="kleinunternehmertext" bind:value={vorlage.kleinunternehmertext} rows="2"></textarea>
          </div>
          {/if}
          <label class="toggle-item"><input type="checkbox" bind:checked={vorlage.wasserzeichen}> <span>Wasserzeichen</span></label>
          {#if vorlage.wasserzeichen}
          <div class="form-group" style="margin-top:8px">
            <label for="wasserzeichentext">Wasserzeichen-Text</label>
            <input id="wasserzeichentext" bind:value={vorlage.wasserzeichentext} placeholder="ENTWURF">
          </div>
          {/if}
        </div>
        {/if}
      </div>

    </div>
    {/if}

    <!-- RECHTE SPALTE: Live-Vorschau -->
    <div class="vorschau-spalte" class:vollbild={aktiverTab === 'vorschau'}>
      <div class="vorschau-header">
        <span class="vorschau-label">Live-Vorschau</span>
        <span class="vorschau-hint">Aktualisiert sich automatisch</span>
      </div>
      {#if aktiverTab === 'vorschau' && vorschauPDF}
        <iframe
          title="PDF-Vorschau"
          src={"data:application/pdf;base64," + vorschauPDF}
          class="pdf-frame"
        ></iframe>
      {:else}
        <iframe
          title="HTML-Vorschau"
          srcdoc={vorschauHTML}
          class="vorschau-frame"
        ></iframe>
      {/if}
    </div>

  </div>
</div>

<style>
  .page { display: flex; flex-direction: column; gap: 16px; padding: 24px; width: 100%; box-sizing: border-box; }
  .page-hdr { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
  .page-title { font-size: 1.4rem; font-weight: 700; color: var(--text); }
  .page-sub { font-size: 0.83rem; color: var(--text2); margin-top: 2px; }
  .hdr-actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
  .tab-btn { background: transparent; border: 1px solid var(--border); color: var(--text2); padding: 7px 14px; border-radius: 8px; font-size: 0.84rem; cursor: pointer; transition: all 0.15s; }
  .tab-btn.active { background: var(--surface2); color: var(--text); border-color: var(--primary); font-weight: 600; }
  .btn-primary { background: var(--primary); color: #fff; border: none; padding: 8px 16px; border-radius: 8px; font-size: 0.84rem; cursor: pointer; transition: background 0.15s; }
  .btn-primary:hover:not(:disabled) { background: var(--primary-hover, #1d4ed8); }
  .btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
  .btn-secondary { background: var(--surface2); border: 1px solid var(--border); color: var(--text); padding: 8px 16px; border-radius: 8px; font-size: 0.84rem; cursor: pointer; }
  .btn-ghost { background: transparent; border: 1px solid var(--border); color: var(--text2); padding: 7px 14px; border-radius: 8px; font-size: 0.84rem; cursor: pointer; }
  .btn-sm { padding: 5px 10px; font-size: 0.8rem; }
  .main-layout { display: grid; grid-template-columns: 360px 1fr; gap: 20px; align-items: flex-start; }
  .einstellungen-spalte { display: flex; flex-direction: column; gap: 10px; }
  .vorschau-spalte { position: sticky; top: 16px; border: 1px solid var(--border); border-radius: 12px; overflow: hidden; background: var(--surface); }
  .vorschau-spalte.vollbild { grid-column: 1 / -1; }
  .vorschau-header { display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; border-bottom: 1px solid var(--border); background: var(--surface2); }
  .vorschau-label { font-size: 0.82rem; font-weight: 600; color: var(--text); }
  .vorschau-hint { font-size: 0.75rem; color: var(--text3); }
  .vorschau-frame, .pdf-frame { width: 100%; height: 700px; border: none; background: #fff; }
  .sektion { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
  .sektion-hdr { width: 100%; display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; background: var(--surface2); border: none; color: var(--text); font-size: 0.88rem; font-weight: 600; cursor: pointer; text-align: left; }
  .sektion-arrow { font-size: 0.7rem; color: var(--text3); }
  .sektion-body { padding: 14px 16px; display: flex; flex-direction: column; gap: 12px; }
  .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .form-group { display: flex; flex-direction: column; gap: 4px; }
  .form-group label { font-size: 0.78rem; color: var(--text2); font-weight: 500; }
  .form-group input, .form-group select, .form-group textarea {
    background: var(--surface); border: 1px solid var(--border); color: var(--text);
    padding: 7px 10px; border-radius: 8px; font-size: 0.84rem; outline: none;
    transition: border-color 0.15s;
  }
  .form-group input:focus, .form-group select:focus, .form-group textarea:focus { border-color: var(--primary); }
  .color-row { display: flex; align-items: center; gap: 8px; }
  .color-input { width: 36px; height: 36px; padding: 2px; border-radius: 6px; border: 1px solid var(--border); cursor: pointer; }
  .color-val { font-size: 0.78rem; color: var(--text2); font-family: monospace; }
  .hint { font-size: 0.73rem; color: var(--text3); }
  .toggle-item { display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 0.84rem; color: var(--text); }
  .toggle-item input[type="checkbox"] { width: 16px; height: 16px; accent-color: var(--primary); cursor: pointer; }
  .themen-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-top: 4px; }
  .thema-btn { border: 2px solid; border-radius: 8px; padding: 6px 4px; font-size: 0.78rem; font-weight: 600; cursor: pointer; transition: opacity 0.15s; }
  .thema-btn:hover { opacity: 0.8; }
  .upload-label { display: block; border: 2px dashed var(--border); border-radius: 8px; padding: 16px; text-align: center; font-size: 0.82rem; color: var(--text2); cursor: pointer; transition: border-color 0.15s; }
  .upload-label:hover { border-color: var(--primary); color: var(--primary); }
  .logo-preview-row { display: flex; align-items: center; gap: 12px; }
  @media (max-width: 900px) {
    .main-layout { grid-template-columns: 1fr; }
    .vorschau-spalte { position: static; }
  }
</style>
