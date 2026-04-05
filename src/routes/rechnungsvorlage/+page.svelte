<script>
  import { onMount } from 'svelte';
  import { currentUser, showToast } from '$lib/stores.js';
  import { apiCall } from '$lib/api.js';

  const B = {
    rechnung_nr: '202658155', datum: '04.04.2026', order_id: '22-14426-19402',
    liefer_datum: '04.04.2026', zahlungsziel: '11.04.2026',
    kaeufer_name: 'Vitali Dubs', kaeufer_strasse: 'Packstation 118',
    kaeufer_extra: 'Postnummer: 49045164',
    kaeufer_plz: '57078', kaeufer_ort: 'Siegen',
    artikel_name: 'Microsoft Windows 10 Pro Produktschlüssel Key MS Software Professional Original',
    artikel_nr: '1054', menge: 1, einzelpreis: 15.57,
    netto_betrag: 13.08, steuer_betrag: 2.49, brutto_betrag: 15.57, steuersatz: 19,
    kunde_nr: '34025',
  };

  const fmt = (n) => Number(n || 0).toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  let v = $state({
    schriftart: 'Arial',
    akzentfarbe: '#1d4ed8',
    seitenrand: 28,
    logo: { base64: '', breite: 130 },
    wasserzeichen: { sichtbar: true, text: 'Entwurf' },
    block_absender: 'Import & Produkte Vertrieb · Auf der Schläfe 1 · 57078 Siegen',
    block_empfaenger: 'Vitali Dubs\nPackstation 118\nPostnummer: 49045164\n57078 Siegen',
    block_kontakt: 'So erreichen Sie uns\n\nE-Mail      import_vertrieb@mail.de\nTelefon    0271 50149974\nMobil       0177 6776548\n\nSteuer-Nr.   342/5058/2211\nUSt-IdNr.    DE815720228\n\nDatum       04.04.2026\nKunde       34025\nRechnung  202658155',
    block_einleitung: 'Sehr geehrte Damen und Herren,\nnachfolgend berechnen wir Ihnen wie vorab besprochen:',
    block_abschluss: 'Vielen Dank für Ihren Auftrag!\n\nBitte begleichen Sie den offenen Betrag bis zum 11.04.2026.\n\nMit freundlichen Grüßen\nImport & Produkte Vertrieb',
    block_zahlung: 'Bereits bezahlt über eBay',
    zahlung_sichtbar: true,
    tabelle: {
      kopf_hg: '#1d4ed8',
      kopf_farbe: '#ffffff',
      zeige_artnr: true,
      zeige_menge: true,
      zeige_ep: true,
      zeige_betrag: true,
    },
    summen: { breite: 280, kleinunternehmer: false },
    footer_spalten: 4,
    footer: [
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
  let aktuellerFokus = $state('');

  onMount(async () => {
    if ($currentUser) {
      try {
        const data = await apiCall('vorlage-laden', { user_id: $currentUser.id });
        if (data?.vorlage) v = { ...v, ...data.vorlage };
      } catch (e) {}
    }
  });

  async function speichern() {
    speichertLaeuft = true;
    try {
      await apiCall('vorlage-speichern', { user_id: $currentUser?.id, vorlage: v });
      showToast('Vorlage gespeichert ✓');
    } catch (e) { showToast('Fehler: ' + e.message); }
    finally { speichertLaeuft = false; }
  }

  async function pdfVorschau() {
    pdfLaeuft = true; zeigtPDF = true;
    try {
      const data = await apiCall('rechnung-vorschau', { user_id: $currentUser?.id, vorlage: v, beispiel: B });
      vorschauPDF = data.pdf_base64 || '';
    } catch (e) { showToast('Fehler: ' + e.message); zeigtPDF = false; }
    finally { pdfLaeuft = false; }
  }

  function handleLogoUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => { v.logo.base64 = ev.target.result; };
    reader.readAsDataURL(file);
  }

  function applyTheme(farbe) {
    v.akzentfarbe = farbe;
    v.tabelle.kopf_hg = farbe;
  }

  const themen = [
    { n: 'Schwarz', c: '#1a1a1a' }, { n: 'Blau', c: '#1d4ed8' },
    { n: 'Grün', c: '#15803d' }, { n: 'Rot', c: '#b91c1c' },
    { n: 'Lila', c: '#6d28d9' }, { n: 'Orange', c: '#c2410c' },
  ];

  function footerText(i) { return v.footer[i] ?? ''; }
  function setFooter(i, text) {
    const arr = [...v.footer];
    arr[i] = text;
    v.footer = arr;
  }
</script>

<div class="rw">

  <!-- TOOLBAR -->
  <div class="rw-bar">
    <div class="rw-bar-l">
      <b class="rw-title">🧾 Rechnungsvorlage</b>
      <div class="sep"></div>

      <label class="rw-lbl">Schrift</label>
      <select class="rw-sel" bind:value={v.schriftart}>
        {#each ['Arial','Helvetica','Georgia','Times New Roman','Verdana','Tahoma','Courier New'] as f}
          <option>{f}</option>
        {/each}
      </select>

      <div class="sep"></div>
      <label class="rw-lbl">Farbthema</label>
      {#each themen as t}
        <button class="rw-dot" style="background:{t.c};"
          class:active={v.akzentfarbe === t.c}
          onclick={() => applyTheme(t.c)} title={t.n}></button>
      {/each}

      <div class="sep"></div>
      <label class="rw-btn">
        🖼 Logo hochladen
        <input type="file" accept="image/*" onchange={handleLogoUpload} style="display:none" />
      </label>
      {#if v.logo.base64}
        <input type="number" class="rw-num" min="40" max="300" bind:value={v.logo.breite} title="Logo-Breite px" />
        <button class="rw-btn" onclick={() => v.logo.base64 = ''}>✕ Logo</button>
      {/if}

      <div class="sep"></div>
      <label class="rw-lbl">Footer-Spalten</label>
      {#each [1,2,3,4] as n}
        <button class="rw-col-btn" class:active={v.footer_spalten === n}
          onclick={() => v.footer_spalten = n}>{n}</button>
      {/each}

      <div class="sep"></div>
      <label class="rw-lbl">Rand</label>
      <input type="number" class="rw-num" min="10" max="60" bind:value={v.seitenrand} />px

      <div class="sep"></div>
      <label class="rw-check"><input type="checkbox" bind:checked={v.wasserzeichen.sichtbar} /> Entwurf</label>
      <label class="rw-check"><input type="checkbox" bind:checked={v.zahlung_sichtbar} /> Bezahlt-Badge</label>
      <label class="rw-check"><input type="checkbox" bind:checked={v.summen.kleinunternehmer} /> § 19 UStG</label>
    </div>

    <div class="rw-bar-r">
      {#if zeigtPDF}
        <button class="rw-btn" onclick={() => zeigtPDF = false}>← Editor</button>
      {:else}
        <button class="rw-btn" onclick={pdfVorschau} disabled={pdfLaeuft}>
          {pdfLaeuft ? '⏳' : '🖨'} PDF
        </button>
      {/if}
      <button class="rw-btn rw-save" onclick={speichern} disabled={speichertLaeuft}>
        {speichertLaeuft ? 'Speichert…' : '💾 Speichern'}
      </button>
    </div>
  </div>

  <!-- SUBBAR: Tabelle + Hinweis -->
  <div class="rw-sub">
    <span class="rw-lbl">Tabellenspalten:</span>
    <label><input type="checkbox" bind:checked={v.tabelle.zeige_artnr} /> Art.-Nr.</label>
    <label><input type="checkbox" bind:checked={v.tabelle.zeige_menge} /> Menge</label>
    <label><input type="checkbox" bind:checked={v.tabelle.zeige_ep} /> Einzelpreis</label>
    <label><input type="checkbox" bind:checked={v.tabelle.zeige_betrag} /> Betrag</label>
    <div class="sep"></div>
    <span class="rw-lbl">Summen-Breite:</span>
    <input type="number" class="rw-num" min="150" max="450" bind:value={v.summen.breite} />px
    {#if aktuellerFokus}
      <div class="sep"></div>
      <span class="rw-hint">✏️ <b>{aktuellerFokus}</b> — Enter = neue Zeile &nbsp;·&nbsp; Leerzeilen für mehr Abstand</span>
    {:else}
      <div class="sep"></div>
      <span class="rw-hint-idle">💡 Jeden Block anklicken und wie in Word bearbeiten — Enter drücken für neue Zeilen</span>
    {/if}
  </div>

  <!-- CANVAS -->
  <div class="rw-canvas">
    {#if zeigtPDF && vorschauPDF}
      <iframe src="data:application/pdf;base64,{vorschauPDF}" title="PDF" class="rw-pdf"></iframe>
    {:else}

    <div class="rw-a4" style="font-family:{v.schriftart},sans-serif; --ak:{v.akzentfarbe}; --rand:{v.seitenrand}px;">

      {#if v.wasserzeichen.sichtbar}
        <div class="rw-wz">{v.wasserzeichen.text}</div>
      {/if}

      <!-- HEADER: Links (Logo+Absender+Empfänger) | Rechts (Kontakt) -->
      <div class="rw-header" style="padding: var(--rand) var(--rand) 0;">

        <div class="rw-hl">
          {#if v.logo.base64}
            <label class="rw-logo-img-lbl" title="Klicken zum Wechseln">
              <input type="file" accept="image/*" onchange={handleLogoUpload} style="display:none" />
              <img src={v.logo.base64} alt="Logo"
                style="width:{v.logo.breite}px; max-height:90px; object-fit:contain; display:block;" />
            </label>
          {:else}
            <label class="rw-logo-drop" style="width:{v.logo.breite}px;">
              <input type="file" accept="image/*" onchange={handleLogoUpload} style="display:none" />
              🖼 Logo hochladen
            </label>
          {/if}

          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div class="rw-e rw-absender"
            contenteditable="true"
            onfocus={() => aktuellerFokus = 'Absenderzeile'}
            onblur={() => aktuellerFokus = ''}
            oninput={(e) => v.block_absender = e.currentTarget.innerText}
            data-label="Absenderzeile"
          >{v.block_absender}</div>

          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div class="rw-e rw-empfaenger"
            contenteditable="true"
            onfocus={() => aktuellerFokus = 'Empfänger-Adresse'}
            onblur={() => aktuellerFokus = ''}
            oninput={(e) => v.block_empfaenger = e.currentTarget.innerText}
            data-label="Empfänger-Adresse"
          >{v.block_empfaenger}</div>
        </div>

        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="rw-e rw-kontakt"
          contenteditable="true"
          onfocus={() => aktuellerFokus = 'Kontakt-Block (rechts)'}
          onblur={() => aktuellerFokus = ''}
          oninput={(e) => v.block_kontakt = e.currentTarget.innerText}
          data-label="Kontakt-Block"
        >{v.block_kontakt}</div>

      </div>

      <!-- TRENNLINIE -->
      <div style="padding: 14px var(--rand) 0;">
        <hr style="border:none; border-top:1px solid #bbb; margin:0;" />
      </div>

      <!-- BODY -->
      <div class="rw-body" style="padding: 14px var(--rand) 0;">

        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="rw-e rw-text"
          contenteditable="true"
          onfocus={() => aktuellerFokus = 'Einleitungstext'}
          onblur={() => aktuellerFokus = ''}
          oninput={(e) => v.block_einleitung = e.currentTarget.innerText}
          data-label="Einleitungstext"
        >{v.block_einleitung}</div>

        <div style="margin:14px 0 2px;">
          <div style="font-size:15px; font-weight:700; color:#1a1a1a;">Rechnung {B.rechnung_nr}</div>
          <div style="font-size:9px; color:#999; margin-bottom:12px;">Das Rechnungsdatum entspricht dem Leistungsdatum</div>
        </div>

        <table class="rw-table">
          <thead>
            <tr style="background:{v.tabelle.kopf_hg};">
              <th class="rw-th" style="color:{v.tabelle.kopf_farbe}; width:32px;">Pos</th>
              {#if v.tabelle.zeige_artnr}
                <th class="rw-th" style="color:{v.tabelle.kopf_farbe}; width:68px;">Art-Nr.</th>
              {/if}
              <th class="rw-th" style="color:{v.tabelle.kopf_farbe};">Bezeichnung</th>
              {#if v.tabelle.zeige_menge}
                <th class="rw-th rw-thr" style="color:{v.tabelle.kopf_farbe}; width:54px;">Menge</th>
              {/if}
              {#if v.tabelle.zeige_ep}
                <th class="rw-th rw-thr" style="color:{v.tabelle.kopf_farbe}; width:88px;">Einzelpreis</th>
              {/if}
              {#if v.tabelle.zeige_betrag}
                <th class="rw-th rw-thr" style="color:{v.tabelle.kopf_farbe}; width:78px;">Betrag</th>
              {/if}
            </tr>
          </thead>
          <tbody>
            <tr style="border-bottom:1px solid #e2e8f0;">
              <td class="rw-td">1</td>
              {#if v.tabelle.zeige_artnr}
                <td class="rw-td" style="color:#666;">{B.artikel_nr}</td>
              {/if}
              <td class="rw-td">{B.artikel_name}</td>
              {#if v.tabelle.zeige_menge}
                <td class="rw-td rw-tdr">{B.menge}</td>
              {/if}
              {#if v.tabelle.zeige_ep}
                <td class="rw-td rw-tdr">{fmt(B.einzelpreis)}</td>
              {/if}
              {#if v.tabelle.zeige_betrag}
                <td class="rw-td rw-tdr">{fmt(B.einzelpreis)} €</td>
              {/if}
            </tr>
          </tbody>
        </table>

        <div style="width:{v.summen.breite}px; margin-left:auto; margin-bottom:16px;">
          <table class="rw-sum">
            <tbody>
              <tr>
                <td class="rw-sl">Nettobetrag</td>
                <td class="rw-sr">{fmt(B.netto_betrag)} €</td>
              </tr>
              {#if v.summen.kleinunternehmer}
                <tr>
                  <td colspan="2" style="padding:4px 8px; font-size:9px; color:#888; font-style:italic;">
                    Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.
                  </td>
                </tr>
              {:else}
                <tr>
                  <td class="rw-sl">Umsatzsteuer {B.steuersatz}%</td>
                  <td class="rw-sr">{fmt(B.steuer_betrag)} €</td>
                </tr>
              {/if}
              <tr class="rw-stotal">
                <td class="rw-sl" style="font-weight:700;">Rechnungsbetrag</td>
                <td class="rw-sr" style="font-weight:700;">{fmt(B.brutto_betrag)} €</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="rw-e rw-text"
          contenteditable="true"
          onfocus={() => aktuellerFokus = 'Abschlusstext'}
          onblur={() => aktuellerFokus = ''}
          oninput={(e) => v.block_abschluss = e.currentTarget.innerText}
          data-label="Abschlusstext"
        >{v.block_abschluss}</div>

        {#if v.zahlung_sichtbar}
          <div style="margin-top:14px;">
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <span class="rw-e rw-badge"
              contenteditable="true"
              onfocus={() => aktuellerFokus = 'Bezahlt-Badge'}
              onblur={() => aktuellerFokus = ''}
              oninput={(e) => v.block_zahlung = e.currentTarget.innerText}
              data-label="Bezahlt-Badge"
            >{v.block_zahlung}</span>
          </div>
        {/if}

      </div>

      <!-- FOOTER: 1–4 Spalten, jede ein freies Textfeld -->
      <div class="rw-footer" style="padding: 8px var(--rand); grid-template-columns: repeat({v.footer_spalten}, 1fr);">
        {#each Array(v.footer_spalten) as _, i}
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div class="rw-e rw-fcol"
            contenteditable="true"
            onfocus={() => aktuellerFokus = `Footer Spalte ${i+1}`}
            onblur={() => aktuellerFokus = ''}
            oninput={(e) => setFooter(i, e.currentTarget.innerText)}
            data-label="Footer Sp. {i+1}"
          >{footerText(i)}</div>
        {/each}
      </div>

    </div>
    {/if}
  </div>
</div>

<style>
  .rw { display:flex; flex-direction:column; height:100%; width:100%; background:#d4d8de; overflow:hidden; }

  .rw-bar {
    display:flex; align-items:center; justify-content:space-between;
    padding:4px 14px; background:#fff; border-bottom:1px solid #ddd;
    flex-shrink:0; gap:5px; flex-wrap:wrap; min-height:42px;
    box-shadow:0 1px 4px rgba(0,0,0,0.07);
  }
  .rw-bar-l { display:flex; align-items:center; gap:5px; flex-wrap:wrap; }
  .rw-bar-r { display:flex; align-items:center; gap:8px; }

  .rw-sub {
    display:flex; align-items:center; gap:8px; flex-wrap:wrap;
    padding:4px 14px; background:#f8fafc; border-bottom:1px solid #e9ecef;
    flex-shrink:0; font-size:0.72rem; color:#555;
  }
  .rw-sub label { display:flex; align-items:center; gap:3px; cursor:pointer; }
  .rw-sub input[type=checkbox] { accent-color:var(--primary,#1d4ed8); }
  .rw-hint { color:#2563eb; font-size:0.7rem; }
  .rw-hint-idle { color:#94a3b8; font-size:0.7rem; font-style:italic; }

  .rw-title { font-size:0.84rem; font-weight:700; color:#1e293b; white-space:nowrap; }
  .sep { width:1px; height:18px; background:#e2e8f0; flex-shrink:0; }
  .rw-lbl { font-size:0.71rem; color:#777; white-space:nowrap; }
  .rw-sel {
    border:1px solid #ddd; border-radius:4px; padding:2px 5px;
    font-size:0.74rem; background:#fff; color:#333; cursor:pointer; outline:none;
  }
  .rw-num {
    width:46px; border:1px solid #ddd; border-radius:4px; padding:2px 4px;
    font-size:0.74rem; background:#fff; color:#333; outline:none;
  }
  .rw-dot {
    width:15px; height:15px; border-radius:50%;
    border:1.5px solid rgba(0,0,0,0.12); cursor:pointer; flex-shrink:0; transition:transform 0.1s;
  }
  .rw-dot:hover { transform:scale(1.3); }
  .rw-dot.active { outline:2.5px solid #111; outline-offset:2px; }

  .rw-col-btn {
    width:22px; height:22px; border-radius:4px;
    border:1px solid #ddd; font-size:0.72rem; font-weight:600;
    background:#fff; color:#555; cursor:pointer;
    display:flex; align-items:center; justify-content:center; transition:all 0.1s;
  }
  .rw-col-btn.active { background:var(--primary,#1d4ed8); color:#fff; border-color:var(--primary,#1d4ed8); }

  .rw-btn {
    background:transparent; border:1px solid #ddd; border-radius:4px;
    padding:3px 8px; font-size:0.74rem; color:#555; cursor:pointer;
    display:flex; align-items:center; gap:3px; font-family:inherit;
    transition:all 0.12s; white-space:nowrap;
  }
  .rw-btn:hover { border-color:#999; color:#222; }
  .rw-save {
    background:var(--primary,#1d4ed8); color:#fff;
    border-color:var(--primary,#1d4ed8); font-weight:600;
  }
  .rw-save:hover { filter:brightness(1.08); }
  .rw-save:disabled { opacity:0.55; cursor:not-allowed; }

  .rw-check {
    display:flex; align-items:center; gap:4px;
    font-size:0.73rem; color:#555; cursor:pointer; white-space:nowrap;
  }
  .rw-check input { accent-color:var(--primary,#1d4ed8); }

  .rw-canvas {
    flex:1; overflow-y:auto; overflow-x:auto;
    padding:24px 20px 40px;
    display:flex; flex-direction:column; align-items:center;
  }

  /* A4 — flex-column, Footer via margin-top:auto ans Ende */
  .rw-a4 {
    width:794px; min-height:1123px; background:#fff;
    box-shadow:0 4px 32px rgba(0,0,0,0.17);
    border-radius:2px; position:relative;
    display:flex; flex-direction:column; flex-shrink:0;
  }

  .rw-wz {
    position:absolute; top:50%; left:50%;
    transform:translate(-50%,-50%) rotate(-35deg);
    font-size:90px; font-weight:900;
    color:rgba(0,0,0,0.055); pointer-events:none; z-index:10;
    white-space:nowrap; user-select:none;
  }

  .rw-header { display:grid; grid-template-columns:1fr auto; gap:24px; align-items:flex-start; }
  .rw-hl { display:flex; flex-direction:column; }

  .rw-logo-img-lbl { display:inline-block; margin-bottom:8px; cursor:pointer; }
  .rw-logo-drop {
    display:flex; align-items:center; justify-content:center;
    height:52px; background:#f1f5f9; border:2px dashed #cbd5e1;
    border-radius:5px; font-size:0.73rem; color:#94a3b8;
    cursor:pointer; margin-bottom:8px; transition:all 0.15s;
  }
  .rw-logo-drop:hover { border-color:var(--ak,#1d4ed8); color:var(--ak,#1d4ed8); }

  .rw-body { flex:1; }

  .rw-table { width:100%; border-collapse:collapse; margin-bottom:0; }
  .rw-th { padding:7px 10px; text-align:left; font-size:11px; font-weight:700; }
  .rw-thr { text-align:right; }
  .rw-td { padding:8px 10px; font-size:11px; color:#1a1a1a; vertical-align:top; }
  .rw-tdr { text-align:right; }

  .rw-sum { width:100%; border-collapse:collapse; border-top:1px solid #ccc; }
  .rw-sl { padding:5px 8px; font-size:11px; color:#555; text-align:right; }
  .rw-sr { padding:5px 8px; font-size:11px; color:#1a1a1a; text-align:right; white-space:nowrap; }
  .rw-stotal { border-top:1px solid #1a1a1a; border-bottom:2px solid #1a1a1a; }
  .rw-stotal .rw-sl, .rw-stotal .rw-sr { font-size:12px; padding:6px 8px; }

  .rw-badge {
    display:inline-block;
    background:#f0fdf4; color:#16a34a;
    border:1.5px solid #86efac; border-radius:5px;
    padding:4px 14px; font-size:11px; font-weight:700;
  }

  /* Footer: margin-top:auto = immer unten */
  .rw-footer {
    margin-top:auto;
    border-top:1px solid #ccc;
    display:grid;
    gap:10px;
    flex-shrink:0;
  }
  .rw-fcol {
    font-size:8px !important;
    line-height:1.75; color:#333;
    white-space:pre-wrap; word-break:break-word;
  }

  /* ═══════════════════════════════════════════════════════════════
     CONTENTEDITABLE BLOCKS — Word-Feeling
     white-space:pre-wrap = Enter macht echte Leerzeilen
  ═══════════════════════════════════════════════════════════════ */
  :global(.rw-e) {
    outline:none; border-radius:2px;
    transition:background 0.1s, box-shadow 0.1s;
    min-height:1em;
    white-space:pre-wrap;
    word-break:break-word;
    cursor:text;
    position:relative;
  }
  :global(.rw-e:hover) {
    background:rgba(29,78,216,0.04);
    box-shadow:0 0 0 1px rgba(29,78,216,0.2);
  }
  :global(.rw-e:focus) {
    background:rgba(29,78,216,0.06);
    box-shadow:0 0 0 2px rgba(29,78,216,0.35);
  }
  :global(.rw-e[data-label]:focus::before) {
    content: attr(data-label);
    display:block;
    position:absolute; top:-18px; left:0;
    font-size:9px; font-weight:700;
    color:#fff; background:rgba(29,78,216,0.85);
    padding:1px 6px; border-radius:3px;
    pointer-events:none; white-space:nowrap; z-index:99;
  }
  :global(.rw-e:empty::after) {
    content: '← hier klicken und bearbeiten';
    color:#ccc; font-style:italic; pointer-events:none;
  }

  .rw-absender { font-size:8px; color:#888; margin-bottom:10px; display:block; }
  .rw-empfaenger { font-size:11px; color:#1a1a1a; line-height:1.7; display:block; }
  .rw-kontakt { font-size:11px; color:#333; line-height:1.75; text-align:right; min-width:180px; max-width:240px; }
  .rw-text { font-size:11px; color:#333; line-height:1.6; margin-bottom:12px; display:block; }

  .rw-pdf {
    width:794px; height:1123px; flex-shrink:0;
    background:#fff; border:none; border-radius:2px;
    box-shadow:0 4px 28px rgba(0,0,0,0.18);
  }

  @media (max-width:860px) {
    .rw-a4, .rw-pdf { width:100%; min-width:0; }
  }
</style>
