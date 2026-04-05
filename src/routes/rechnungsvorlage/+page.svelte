<script>
  import { onMount } from 'svelte';
  import { currentUser, showToast } from '$lib/stores.js';
  import { apiCall } from '$lib/api.js';

  const B = {
    rechnung_nr: '202658155', datum: '04.04.2026',
    zahlungsziel: '11.04.2026', kunde_nr: '34025',
    artikel_name: 'Microsoft Windows 10 Pro Produktschlüssel Key MS Software Professional Original',
    artikel_nr: '1054', menge: 1, einzelpreis: 15.57,
    netto_betrag: 13.08, steuer_betrag: 2.49, brutto_betrag: 15.57, steuersatz: 19,
  };

  const fmt = (n) => Number(n||0).toLocaleString('de-DE',{minimumFractionDigits:2,maximumFractionDigits:2});

  // ── State — wird NUR bei onblur geschrieben, nie bei oninput
  // Dadurch bleibt der Cursor stabil (kein Re-Render während Tippen)
  let v = $state({
    schriftart: 'Arial',
    akzentfarbe: '#1d4ed8',
    seitenrand: 28,
    logo: { base64: '', breite: 130 },
    briefpapier: { base64: '' },
    wasserzeichen: { sichtbar: true, text: 'Entwurf' },
    zahlung_sichtbar: true,
    zahlung_farbe: '#16a34a',
    zahlung_hg: '#f0fdf4',
    zahlung_rahmen: '#86efac',
    footer_spalten: 4,
    tabelle: { kopf_hg: '#1d4ed8', kopf_farbe: '#ffffff', zeige_artnr: true, zeige_menge: true, zeige_ep: true, zeige_betrag: true },
    summen: { breite: 280, kleinunternehmer: false },
    // Textinhalte — werden nur bei Blur gespeichert
    t_absender: 'Import & Produkte Vertrieb · Auf der Schläfe 1 · 57078 Siegen',
    t_empfaenger: 'Vitali Dubs\nPackstation 118\nPostnummer: 49045164\n57078 Siegen',
    t_kontakt: 'So erreichen Sie uns\n\nE-Mail      import_vertrieb@mail.de\nTelefon    0271 50149974\nMobil       0177 6776548\n\nSteuer-Nr.   342/5058/2211\nUSt-IdNr.    DE815720228\n\nDatum       04.04.2026\nKunde       34025\nRechnung  202658155',
    t_einleitung: 'Sehr geehrte Damen und Herren,\nnachfolgend berechnen wir Ihnen wie vorab besprochen:',
    t_abschluss: 'Vielen Dank für Ihren Auftrag!\n\nBitte begleichen Sie den offenen Betrag bis zum 11.04.2026.\n\nMit freundlichen Grüßen\nImport & Produkte Vertrieb',
    t_zahlung: 'Bereits bezahlt über eBay',
    t_footer: [
      'Import & Produkte Vertrieb\nInh. Oxana Dubs\nAuf der Schläfe 1\nDE 57078 Siegen',
      'Telefon: +49 271 50149974\nMobil:    +49 177 6776548\nE-Mail:   ov-shop@mail.de',
      'Bankverbindung: N26 Bank\nIBAN: DE60 1001 1001 2829 9706 30\nBIC: NTSBDEB1XXX',
      'Finanzamt Siegen\nSt.Nr. 342/5058/2200\nUSt. -ID: DE815720228',
    ],
  });

  let speichertLaeuft = $state(false);
  let pdfLaeuft = $state(false);
  let vorschauPDF = $state('');
  let zeigtPDF = $state(false);
  let aktiverBlock = $state('');

  // DOM-Referenzen für die editierbaren Blöcke
  // Wir initialisieren den Inhalt einmalig via onMount, danach NUR lesen bei Blur
  let elAbsender, elEmpfaenger, elKontakt, elEinleitung, elAbschluss, elZahlung;
  let elFooter = [];

  onMount(async () => {
    // Inhalte einmalig setzen
    if (elAbsender) elAbsender.innerText = v.t_absender;
    if (elEmpfaenger) elEmpfaenger.innerText = v.t_empfaenger;
    if (elKontakt) elKontakt.innerText = v.t_kontakt;
    if (elEinleitung) elEinleitung.innerText = v.t_einleitung;
    if (elAbschluss) elAbschluss.innerText = v.t_abschluss;
    if (elZahlung) elZahlung.innerText = v.t_zahlung;
    elFooter.forEach((el, i) => { if (el) el.innerText = v.t_footer[i] ?? ''; });

    if ($currentUser) {
      try {
        const data = await apiCall('vorlage-laden', { user_id: $currentUser.id });
        if (data?.vorlage) {
          v = { ...v, ...data.vorlage };
          // Nach Laden auch DOM aktualisieren
          if (elAbsender) elAbsender.innerText = v.t_absender;
          if (elEmpfaenger) elEmpfaenger.innerText = v.t_empfaenger;
          if (elKontakt) elKontakt.innerText = v.t_kontakt;
          if (elEinleitung) elEinleitung.innerText = v.t_einleitung;
          if (elAbschluss) elAbschluss.innerText = v.t_abschluss;
          if (elZahlung) elZahlung.innerText = v.t_zahlung;
          elFooter.forEach((el, i) => { if (el) el.innerText = v.t_footer[i] ?? ''; });
        }
      } catch(e) {}
    }
  });

  // Blur-Handler: nur dann State schreiben → kein Cursor-Reset während Tippen
  function saveAbsender(e) { v.t_absender = e.target.innerText; }
  function saveEmpfaenger(e) { v.t_empfaenger = e.target.innerText; }
  function saveKontakt(e) { v.t_kontakt = e.target.innerText; }
  function saveEinleitung(e) { v.t_einleitung = e.target.innerText; }
  function saveAbschluss(e) { v.t_abschluss = e.target.innerText; }
  function saveZahlung(e) { v.t_zahlung = e.target.innerText; }
  function saveFooter(i, e) {
    const arr = [...v.t_footer];
    arr[i] = e.target.innerText;
    v.t_footer = arr;
  }

  async function speichern() {
    // Vor dem Speichern aktuellen DOM-Inhalt lesen
    if (elAbsender) v.t_absender = elAbsender.innerText;
    if (elEmpfaenger) v.t_empfaenger = elEmpfaenger.innerText;
    if (elKontakt) v.t_kontakt = elKontakt.innerText;
    if (elEinleitung) v.t_einleitung = elEinleitung.innerText;
    if (elAbschluss) v.t_abschluss = elAbschluss.innerText;
    if (elZahlung) v.t_zahlung = elZahlung.innerText;
    elFooter.forEach((el, i) => { if (el) { const a=[...v.t_footer]; a[i]=el.innerText; v.t_footer=a; } });

    speichertLaeuft = true;
    try {
      await apiCall('vorlage-speichern', { user_id: $currentUser?.id, vorlage: v });
      showToast('Vorlage gespeichert ✓');
    } catch(e) { showToast('Fehler: ' + e.message); }
    finally { speichertLaeuft = false; }
  }

  async function pdfVorschau() {
    pdfLaeuft = true; zeigtPDF = true;
    try {
      const data = await apiCall('rechnung-vorschau', { user_id: $currentUser?.id, vorlage: v, beispiel: B });
      vorschauPDF = data.pdf_base64 || '';
    } catch(e) { showToast('Fehler: ' + e.message); zeigtPDF = false; }
    finally { pdfLaeuft = false; }
  }

  function handleLogoUpload(e) {
    const file = e.target.files?.[0]; if (!file) return;
    const r = new FileReader();
    r.onload = (ev) => { v.logo.base64 = ev.target.result; };
    r.readAsDataURL(file);
  }

  function handleBriefpapierUpload(e) {
    const file = e.target.files?.[0]; if (!file) return;
    const r = new FileReader();
    r.onload = (ev) => { v.briefpapier.base64 = ev.target.result; };
    r.readAsDataURL(file);
  }

  function applyTheme(farbe) {
    v.akzentfarbe = farbe;
    v.tabelle.kopf_hg = farbe;
  }

  const themen = [
    {n:'Schwarz',c:'#1a1a1a'},{n:'Blau',c:'#1d4ed8'},{n:'Grün',c:'#15803d'},
    {n:'Rot',c:'#b91c1c'},{n:'Lila',c:'#6d28d9'},{n:'Orange',c:'#c2410c'},
    {n:'Petrol',c:'#0e7490'},{n:'Gold',c:'#b45309'},
  ];

  const badgeThemen = [
    {n:'Grün',f:'#15803d',h:'#f0fdf4',r:'#86efac'},
    {n:'Blau',f:'#1d4ed8',h:'#eff6ff',r:'#93c5fd'},
    {n:'Grau',f:'#374151',h:'#f9fafb',r:'#d1d5db'},
    {n:'Orange',f:'#c2410c',h:'#fff7ed',r:'#fed7aa'},
  ];
</script>

<div class="rw">

  <!-- ═══════════════════════════ TOOLBAR ══════════════════════════════════ -->
  <div class="rw-bar">
    <div class="rw-bar-l">
      <b class="rw-title">🧾 Rechnungsvorlage</b>
      <div class="sep"></div>

      <span class="rw-lbl">Schrift</span>
      <select class="rw-sel" bind:value={v.schriftart}>
        {#each ['Arial','Helvetica','Georgia','Times New Roman','Verdana','Tahoma','Garamond','Courier New'] as f}
          <option>{f}</option>
        {/each}
      </select>

      <div class="sep"></div>
      <span class="rw-lbl">Farbthema</span>
      {#each themen as t}
        <button class="rw-dot" style="background:{t.c};" class:act={v.akzentfarbe===t.c}
          onclick={() => applyTheme(t.c)} title={t.n}></button>
      {/each}
      <input type="color" class="rw-color-pick" bind:value={v.akzentfarbe}
        oninput={() => v.tabelle.kopf_hg = v.akzentfarbe} title="Eigene Farbe" />

      <div class="sep"></div>
      <label class="rw-btn">🖼 Logo
        <input type="file" accept="image/*" onchange={handleLogoUpload} style="display:none" />
      </label>
      {#if v.logo.base64}
        <input type="number" class="rw-num" min="40" max="300" bind:value={v.logo.breite} title="Logo-Breite" />px
        <button class="rw-btn rw-btn-x" onclick={() => v.logo.base64=''}>✕</button>
      {/if}

      <div class="sep"></div>
      <label class="rw-btn">📄 Briefpapier
        <input type="file" accept="image/*,application/pdf" onchange={handleBriefpapierUpload} style="display:none" />
      </label>
      {#if v.briefpapier.base64}
        <button class="rw-btn rw-btn-x" onclick={() => v.briefpapier.base64=''}>✕</button>
      {/if}

      <div class="sep"></div>
      <span class="rw-lbl">Badge-Farbe</span>
      {#each badgeThemen as bt}
        <button class="rw-dot" style="background:{bt.h}; border:2px solid {bt.r};"
          class:act={v.zahlung_farbe===bt.f}
          onclick={() => { v.zahlung_farbe=bt.f; v.zahlung_hg=bt.h; v.zahlung_rahmen=bt.r; }}
          title={bt.n}></button>
      {/each}

      <div class="sep"></div>
      <span class="rw-lbl">Footer</span>
      {#each [1,2,3,4] as n}
        <button class="rw-col" class:act={v.footer_spalten===n}
          onclick={() => v.footer_spalten=n}>{n}</button>
      {/each}

      <div class="sep"></div>
      <span class="rw-lbl">Rand</span>
      <input type="number" class="rw-num" min="10" max="60" bind:value={v.seitenrand} />px
    </div>

    <div class="rw-bar-r">
      <label class="rw-check"><input type="checkbox" bind:checked={v.wasserzeichen.sichtbar}/> Entwurf</label>
      <label class="rw-check"><input type="checkbox" bind:checked={v.zahlung_sichtbar}/> Bezahlt-Badge</label>
      <label class="rw-check"><input type="checkbox" bind:checked={v.summen.kleinunternehmer}/> §19 UStG</label>
      <div class="sep"></div>
      {#if zeigtPDF}
        <button class="rw-btn" onclick={() => zeigtPDF=false}>← Editor</button>
      {:else}
        <button class="rw-btn" onclick={pdfVorschau} disabled={pdfLaeuft}>{pdfLaeuft?'⏳':'🖨'} PDF</button>
      {/if}
      <button class="rw-btn rw-save" onclick={speichern} disabled={speichertLaeuft}>
        {speichertLaeuft?'Speichert…':'💾 Speichern'}
      </button>
    </div>
  </div>

  <!-- SUBBAR -->
  <div class="rw-sub">
    <span class="rw-lbl">Spalten:</span>
    <label><input type="checkbox" bind:checked={v.tabelle.zeige_artnr}/> Art.-Nr.</label>
    <label><input type="checkbox" bind:checked={v.tabelle.zeige_menge}/> Menge</label>
    <label><input type="checkbox" bind:checked={v.tabelle.zeige_ep}/> Einzelpreis</label>
    <label><input type="checkbox" bind:checked={v.tabelle.zeige_betrag}/> Betrag</label>
    <div class="sep"></div>
    <span class="rw-lbl">Summen-Breite:</span>
    <input type="number" class="rw-num" min="150" max="450" bind:value={v.summen.breite}/>px
    <div class="sep"></div>
    {#if aktiverBlock}
      <span class="rw-hint">✏️ <b>{aktiverBlock}</b> — Enter = neue Zeile, mehrfach Enter = Leerzeilen für Abstand</span>
    {:else}
      <span class="rw-hint-idle">💡 Jeden Block direkt anklicken und bearbeiten — wie in Word</span>
    {/if}
  </div>

  <!-- ═══════════════════════════ CANVAS ═══════════════════════════════════ -->
  <div class="rw-canvas">
    {#if zeigtPDF && vorschauPDF}
      <iframe src="data:application/pdf;base64,{vorschauPDF}" title="PDF" class="rw-pdf"></iframe>
    {:else}

    <div class="rw-a4" style="
      font-family:{v.schriftart},sans-serif;
      --ak:{v.akzentfarbe};
      --rand:{v.seitenrand}px;
      {v.briefpapier.base64 ? 'background-image:url('+v.briefpapier.base64+'); background-size:cover; background-position:top center;' : ''}
    ">
      {#if v.wasserzeichen.sichtbar}
        <div class="rw-wz">{v.wasserzeichen.text}</div>
      {/if}

      <!-- HEADER -->
      <div class="rw-header" style="padding:var(--rand) var(--rand) 0;">
        <div class="rw-hl">
          {#if v.logo.base64}
            <label class="rw-logo-lbl" title="Klicken zum Wechseln">
              <input type="file" accept="image/*" onchange={handleLogoUpload} style="display:none"/>
              <img src={v.logo.base64} alt="Logo"
                style="width:{v.logo.breite}px;max-height:90px;object-fit:contain;display:block;cursor:pointer;"/>
            </label>
          {:else}
            <label class="rw-logo-drop" style="width:{v.logo.breite}px;">
              <input type="file" accept="image/*" onchange={handleLogoUpload} style="display:none"/>
              🖼 Logo hochladen
            </label>
          {/if}

          <div class="rw-e rw-absender"
            contenteditable="true"
            bind:this={elAbsender}
            onfocus={() => aktiverBlock='Absenderzeile'}
            onblur={saveAbsender}
            data-ph="Absenderzeile (Firmname · Straße · PLZ Ort)"
          ></div>

          <div class="rw-e rw-empfaenger"
            contenteditable="true"
            bind:this={elEmpfaenger}
            onfocus={() => aktiverBlock='Empfänger-Adresse'}
            onblur={saveEmpfaenger}
            data-ph="Empfänger-Adresse"
          ></div>
        </div>

        <div class="rw-e rw-kontakt"
          contenteditable="true"
          bind:this={elKontakt}
          onfocus={() => aktiverBlock='Kontakt-Block (rechts)'}
          onblur={saveKontakt}
          data-ph="Kontakt-Block"
        ></div>
      </div>

      <!-- TRENNLINIE -->
      <div style="padding:14px var(--rand) 0;">
        <hr style="border:none;border-top:1px solid #bbb;margin:0;"/>
      </div>

      <!-- BODY -->
      <div class="rw-body" style="padding:14px var(--rand) 0;">

        <div class="rw-e rw-text"
          contenteditable="true"
          bind:this={elEinleitung}
          onfocus={() => aktiverBlock='Einleitungstext'}
          onblur={saveEinleitung}
          data-ph="Einleitungstext"
        ></div>

        <div style="margin:14px 0 2px;">
          <div style="font-size:15px;font-weight:700;color:#1a1a1a;">Rechnung {B.rechnung_nr}</div>
          <div style="font-size:9px;color:#999;margin-bottom:12px;">Das Rechnungsdatum entspricht dem Leistungsdatum</div>
        </div>

        <table class="rw-table">
          <thead>
            <tr style="background:{v.tabelle.kopf_hg};">
              <th class="rw-th" style="color:{v.tabelle.kopf_farbe};width:32px;">Pos</th>
              {#if v.tabelle.zeige_artnr}<th class="rw-th" style="color:{v.tabelle.kopf_farbe};width:68px;">Art-Nr.</th>{/if}
              <th class="rw-th" style="color:{v.tabelle.kopf_farbe};">Bezeichnung</th>
              {#if v.tabelle.zeige_menge}<th class="rw-th rw-thr" style="color:{v.tabelle.kopf_farbe};width:54px;">Menge</th>{/if}
              {#if v.tabelle.zeige_ep}<th class="rw-th rw-thr" style="color:{v.tabelle.kopf_farbe};width:90px;">Einzelpreis</th>{/if}
              {#if v.tabelle.zeige_betrag}<th class="rw-th rw-thr" style="color:{v.tabelle.kopf_farbe};width:78px;">Betrag</th>{/if}
            </tr>
          </thead>
          <tbody>
            <tr style="border-bottom:1px solid #e2e8f0;">
              <td class="rw-td">1</td>
              {#if v.tabelle.zeige_artnr}<td class="rw-td" style="color:#666;">{B.artikel_nr}</td>{/if}
              <td class="rw-td">{B.artikel_name}</td>
              {#if v.tabelle.zeige_menge}<td class="rw-td rw-tdr">{B.menge}</td>{/if}
              {#if v.tabelle.zeige_ep}<td class="rw-td rw-tdr">{fmt(B.einzelpreis)}</td>{/if}
              {#if v.tabelle.zeige_betrag}<td class="rw-td rw-tdr">{fmt(B.einzelpreis)} €</td>{/if}
            </tr>
          </tbody>
        </table>

        <div style="width:{v.summen.breite}px;margin-left:auto;margin-bottom:16px;">
          <table class="rw-sum">
            <tbody>
              <tr><td class="rw-sl">Nettobetrag</td><td class="rw-sr">{fmt(B.netto_betrag)} €</td></tr>
              {#if v.summen.kleinunternehmer}
                <tr><td colspan="2" style="padding:4px 8px;font-size:9px;color:#888;font-style:italic;">Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.</td></tr>
              {:else}
                <tr><td class="rw-sl">Umsatzsteuer {B.steuersatz}%</td><td class="rw-sr">{fmt(B.steuer_betrag)} €</td></tr>
              {/if}
              <tr class="rw-stotal">
                <td class="rw-sl" style="font-weight:700;">Rechnungsbetrag</td>
                <td class="rw-sr" style="font-weight:700;">{fmt(B.brutto_betrag)} €</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="rw-e rw-text"
          contenteditable="true"
          bind:this={elAbschluss}
          onfocus={() => aktiverBlock='Abschlusstext'}
          onblur={saveAbschluss}
          data-ph="Abschlusstext"
        ></div>

        {#if v.zahlung_sichtbar}
          <div style="margin-top:14px;">
            <div class="rw-e rw-badge"
              contenteditable="true"
              bind:this={elZahlung}
              onfocus={() => aktiverBlock='Bezahlt-Badge'}
              onblur={saveZahlung}
              data-ph="Bezahlt-Text"
              style="color:{v.zahlung_farbe};background:{v.zahlung_hg};border-color:{v.zahlung_rahmen};"
            ></div>
          </div>
        {/if}

      </div>

      <!-- FOOTER -->
      <div class="rw-footer" style="padding:8px var(--rand);grid-template-columns:repeat({v.footer_spalten},1fr);">
        {#each Array(v.footer_spalten) as _, i}
          <div class="rw-e rw-fcol"
            contenteditable="true"
            bind:this={elFooter[i]}
            onfocus={() => aktiverBlock=`Footer Spalte ${i+1}`}
            onblur={(e) => saveFooter(i,e)}
            data-ph="Footer Spalte {i+1}"
          ></div>
        {/each}
      </div>

    </div>
    {/if}
  </div>
</div>

<style>
  .rw{display:flex;flex-direction:column;height:100%;width:100%;background:#d4d8de;overflow:hidden;}

  .rw-bar{
    display:flex;align-items:center;justify-content:space-between;
    padding:4px 14px;background:#fff;border-bottom:1px solid #ddd;
    flex-shrink:0;gap:5px;flex-wrap:wrap;min-height:44px;
    box-shadow:0 1px 4px rgba(0,0,0,0.07);
  }
  .rw-bar-l{display:flex;align-items:center;gap:5px;flex-wrap:wrap;}
  .rw-bar-r{display:flex;align-items:center;gap:6px;flex-wrap:wrap;}

  .rw-sub{
    display:flex;align-items:center;gap:8px;flex-wrap:wrap;
    padding:3px 14px;background:#f8fafc;border-bottom:1px solid #e9ecef;
    flex-shrink:0;font-size:0.71rem;color:#555;
  }
  .rw-sub label{display:flex;align-items:center;gap:3px;cursor:pointer;}
  .rw-sub input[type=checkbox]{accent-color:var(--primary,#1d4ed8);}
  .rw-hint{color:#2563eb;font-size:0.7rem;}
  .rw-hint-idle{color:#94a3b8;font-size:0.7rem;font-style:italic;}

  .rw-title{font-size:0.84rem;font-weight:700;color:#1e293b;white-space:nowrap;}
  .sep{width:1px;height:18px;background:#e2e8f0;flex-shrink:0;}
  .rw-lbl{font-size:0.71rem;color:#777;white-space:nowrap;}
  .rw-sel{border:1px solid #ddd;border-radius:4px;padding:2px 5px;font-size:0.74rem;background:#fff;color:#333;cursor:pointer;outline:none;}
  .rw-num{width:44px;border:1px solid #ddd;border-radius:4px;padding:2px 4px;font-size:0.74rem;background:#fff;color:#333;outline:none;}
  .rw-color-pick{width:24px;height:24px;padding:0;border:1px solid #ddd;border-radius:4px;cursor:pointer;background:none;}

  .rw-dot{width:16px;height:16px;border-radius:50%;border:1.5px solid rgba(0,0,0,0.15);cursor:pointer;flex-shrink:0;transition:transform 0.1s;}
  .rw-dot:hover{transform:scale(1.3);}
  .rw-dot.act{outline:2.5px solid #111;outline-offset:2px;}

  .rw-col{width:22px;height:22px;border-radius:4px;border:1px solid #ddd;font-size:0.72rem;font-weight:600;background:#fff;color:#555;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all 0.1s;}
  .rw-col.act{background:var(--primary,#1d4ed8);color:#fff;border-color:var(--primary,#1d4ed8);}

  .rw-btn{background:transparent;border:1px solid #ddd;border-radius:4px;padding:3px 8px;font-size:0.73rem;color:#555;cursor:pointer;display:flex;align-items:center;gap:3px;font-family:inherit;transition:all 0.12s;white-space:nowrap;}
  .rw-btn:hover{border-color:#999;color:#222;}
  .rw-btn-x{padding:3px 6px;color:#999;}
  .rw-save{background:var(--primary,#1d4ed8);color:#fff;border-color:var(--primary,#1d4ed8);font-weight:600;}
  .rw-save:hover{filter:brightness(1.08);}
  .rw-save:disabled{opacity:0.55;cursor:not-allowed;}
  .rw-check{display:flex;align-items:center;gap:4px;font-size:0.73rem;color:#555;cursor:pointer;white-space:nowrap;}
  .rw-check input{accent-color:var(--primary,#1d4ed8);}

  .rw-canvas{flex:1;overflow-y:auto;overflow-x:auto;padding:24px 20px 40px;display:flex;flex-direction:column;align-items:center;}

  .rw-a4{width:794px;min-height:1123px;background:#fff;box-shadow:0 4px 32px rgba(0,0,0,0.17);border-radius:2px;position:relative;display:flex;flex-direction:column;flex-shrink:0;}

  .rw-wz{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%) rotate(-35deg);font-size:90px;font-weight:900;color:rgba(0,0,0,0.055);pointer-events:none;z-index:10;white-space:nowrap;user-select:none;}

  .rw-header{display:grid;grid-template-columns:1fr auto;gap:24px;align-items:flex-start;}
  .rw-hl{display:flex;flex-direction:column;}

  .rw-logo-lbl{display:inline-block;margin-bottom:8px;cursor:pointer;}
  .rw-logo-drop{display:flex;align-items:center;justify-content:center;height:52px;background:#f1f5f9;border:2px dashed #cbd5e1;border-radius:5px;font-size:0.73rem;color:#94a3b8;cursor:pointer;margin-bottom:8px;transition:all 0.15s;min-width:100px;}
  .rw-logo-drop:hover{border-color:var(--ak,#1d4ed8);color:var(--ak,#1d4ed8);}

  .rw-body{flex:1;}

  .rw-table{width:100%;border-collapse:collapse;}
  .rw-th{padding:7px 10px;text-align:left;font-size:11px;font-weight:700;}
  .rw-thr{text-align:right;}
  .rw-td{padding:8px 10px;font-size:11px;color:#1a1a1a;vertical-align:top;}
  .rw-tdr{text-align:right;}

  .rw-sum{width:100%;border-collapse:collapse;border-top:1px solid #ccc;}
  .rw-sl{padding:5px 8px;font-size:11px;color:#555;text-align:right;}
  .rw-sr{padding:5px 8px;font-size:11px;color:#1a1a1a;text-align:right;white-space:nowrap;}
  .rw-stotal{border-top:1px solid #1a1a1a;border-bottom:2px solid #1a1a1a;}
  .rw-stotal .rw-sl,.rw-stotal .rw-sr{font-size:12px;padding:6px 8px;}

  .rw-badge{display:inline-block;border:1.5px solid;border-radius:5px;padding:4px 14px;font-size:11px;font-weight:700;cursor:text;}

  .rw-footer{margin-top:auto;border-top:1px solid #ccc;display:grid;gap:10px;flex-shrink:0;}
  .rw-fcol{font-size:8px!important;line-height:1.75;color:#333;white-space:pre-wrap;word-break:break-word;min-height:40px;}

  /* ═══════════════════════════════════════════════════════════════
     CONTENTEDITABLE — KEIN oninput → kein Cursor-Reset
     Nur onblur speichert den State
     white-space:pre-wrap = Enter = echte Leerzeilen
  ═══════════════════════════════════════════════════════════════ */
  :global(.rw-e){
    outline:none;border-radius:2px;
    transition:background 0.1s,box-shadow 0.1s;
    min-height:1.2em;
    white-space:pre-wrap;
    word-break:break-word;
    cursor:text;
  }
  :global(.rw-e:hover){
    background:rgba(29,78,216,0.04);
    box-shadow:0 0 0 1px rgba(29,78,216,0.2);
  }
  :global(.rw-e:focus){
    background:rgba(29,78,216,0.06);
    box-shadow:0 0 0 2px rgba(29,78,216,0.35);
  }
  :global(.rw-e:empty::before){
    content:attr(data-ph);
    color:#c0c7d0;font-style:italic;pointer-events:none;
  }

  .rw-absender{font-size:8px;color:#888;margin-bottom:10px;display:block;}
  .rw-empfaenger{font-size:11px;color:#1a1a1a;line-height:1.7;display:block;}
  .rw-kontakt{font-size:11px;color:#333;line-height:1.75;text-align:right;min-width:180px;max-width:240px;}
  .rw-text{font-size:11px;color:#333;line-height:1.6;margin-bottom:12px;display:block;}

  .rw-pdf{width:794px;height:1123px;flex-shrink:0;background:#fff;border:none;border-radius:2px;box-shadow:0 4px 28px rgba(0,0,0,0.18);}

  @media(max-width:860px){.rw-a4,.rw-pdf{width:100%;min-width:0;}}
</style>
