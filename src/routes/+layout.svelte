<script>
  import { onMount } from 'svelte';
  import { currentUser, showToast } from '$lib/stores.js';
  import { apiCall } from '$lib/api.js';

  const B = {
    rechnung_nr: 'RE-2026-00042', datum: '02.04.2026', order_id: '22-14426-19402',
    kaeufer_name: 'Hermann Jakob', kaeufer_strasse: 'Gneisenaustr. 12',
    kaeufer_plz: '85051', kaeufer_ort: 'Ingolstadt', kaeufer_land: 'Deutschland',
    artikel_name: 'Jemako Intensivreiniger KalkEx Plus', artikel_nr: '1054',
    menge: 1, einzelpreis: 15.96, netto_betrag: 15.96,
    steuer_betrag: 3.03, brutto_betrag: 18.99, steuersatz: 19
  };

  const fmt = (n) => Number(n||0).toLocaleString('de-DE', {minimumFractionDigits:2, maximumFractionDigits:2});

  let v = $state({
    akzentfarbe: '#2563eb',
    schriftart: 'Arial',
    seitenrand: 32,
    logo: { base64: '', breite: 120 },
    firmenname: { text: '', groesse: 20, farbe: '#2563eb', gewicht: '700' },
    absenderzeile: { text: '' },
    adresse: { strasse: '', plz: '', ort: '' },
    kontakt: { telefon: '', email: '', mobil: '', steuernr: '', ust_idnr: '' },
    trennlinie: { farbe: '#2563eb', staerke: 2 },
    empfaenger_label: 'Rechnungsempfänger',
    rechnung_titel: 'Rechnung',
    einleitung: 'Ihre Bestellung Nr. [order_id] vom [datum].',
    tabelle: { kopf_hg: '#2563eb', kopf_farbe: '#ffffff', zeige_artnr: true, zeige_menge: true, zeige_ep: true, zeige_betrag: true },
    summen: { total_farbe: '#2563eb', total_hg: '#f8fafc', breite: 260, kleinunternehmer: false },
    zahlung_text: 'Bereits bezahlt über eBay',
    bank: { name: '', iban: '', bic: '', sichtbar: true },
    footer: { text: 'Vielen Dank für Ihre Bestellung bei eBay.', sichtbar: true, zeige_steuernr: true, zeige_seite: true },
    wasserzeichen: { sichtbar: false, text: 'ENTWURF' },
  });

  let speichertLaeuft = $state(false);
  let pdfLaeuft = $state(false);
  let vorschauPDF = $state('');
  let zeigtPDF = $state(false);

  onMount(async () => {
    if ($currentUser) {
      try {
        const data = await apiCall('vorlage-laden', { user_id: $currentUser.id });
        if (data?.vorlage) v = { ...v, ...data.vorlage };
      } catch(e) {}
    }
  });

  async function speichern() {
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
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => { v.logo.base64 = ev.target.result; };
    reader.readAsDataURL(file);
  }

  function applyTheme(farbe) {
    v.akzentfarbe = farbe;
    v.firmenname.farbe = farbe;
    v.trennlinie.farbe = farbe;
    v.tabelle.kopf_hg = farbe;
    v.summen.total_farbe = farbe;
  }

  const themen = [
    {n:'Blau', c:'#2563eb'}, {n:'Grün', c:'#16a34a'}, {n:'Rot', c:'#dc2626'},
    {n:'Lila', c:'#7c3aed'}, {n:'Grau', c:'#374151'}, {n:'Orange', c:'#ea580c'},
  ];
</script>

<div class="rw">

  <!-- TOOLBAR -->
  <div class="rw-bar">
    <div class="rw-bar-l">
      <b class="rw-title">🧾 Rechnungsvorlage</b>
      <div class="sep"></div>

      <label class="rw-field-label">Schrift</label>
      <select class="rw-sel" bind:value={v.schriftart}>
        {#each ['Arial','Helvetica','Georgia','Times New Roman','Verdana','Tahoma'] as f}
          <option>{f}</option>
        {/each}
      </select>

      <label class="rw-field-label">Rand</label>
      <input type="number" class="rw-num" min="10" max="60" bind:value={v.seitenrand} />px

      <div class="sep"></div>
      <label class="rw-field-label">Farbe</label>
      {#each themen as t}
        <button class="rw-dot" style="background:{t.c};" class:rw-dot-active={v.akzentfarbe===t.c} onclick={() => applyTheme(t.c)} title={t.n}></button>
      {/each}

      <div class="sep"></div>
      <label class="rw-btn">
        🖼 Logo hochladen
        <input type="file" accept="image/*" onchange={handleLogoUpload} style="display:none" />
      </label>
      {#if v.logo.base64}
        <button class="rw-btn" onclick={() => v.logo.base64 = ''}>✕ Logo</button>
      {/if}

      <div class="sep"></div>
      <label class="rw-btn" style="gap:5px;">
        <input type="checkbox" bind:checked={v.wasserzeichen.sichtbar} />
        Entwurf-Stempel
      </label>
    </div>
    <div class="rw-bar-r">
      {#if zeigtPDF}
        <button class="rw-btn" onclick={() => zeigtPDF = false}>← Editor</button>
      {:else}
        <button class="rw-btn" onclick={pdfVorschau} disabled={pdfLaeuft}>{pdfLaeuft ? '⏳' : '🖨'} PDF</button>
      {/if}
      <button class="rw-btn rw-btn-save" onclick={speichern} disabled={speichertLaeuft}>
        {speichertLaeuft ? 'Speichert…' : '💾 Speichern'}
      </button>
    </div>
  </div>

  <!-- CANVAS -->
  <div class="rw-canvas">

    {#if zeigtPDF && vorschauPDF}
      <iframe src="data:application/pdf;base64,{vorschauPDF}" title="PDF" class="rw-pdf"></iframe>
    {:else}

    <!-- A4 -->
    <div class="rw-a4" style="font-family:{v.schriftart},sans-serif; --ak:{v.akzentfarbe}; --rand:{v.seitenrand}px;">

      {#if v.wasserzeichen.sichtbar}
        <div class="rw-wz">{v.wasserzeichen.text}</div>
      {/if}

      <!-- HEADER -->
      <div class="rw-header" style="padding:var(--rand) var(--rand) 0;">
        <div class="rw-hl">
          <!-- Logo -->
          {#if v.logo.base64}
            <img src={v.logo.base64} alt="Logo" style="width:{v.logo.breite}px; max-height:70px; object-fit:contain; display:block; margin-bottom:6px;" />
          {:else}
            <label class="rw-logo-drop" style="width:{v.logo.breite}px;">
              <input type="file" accept="image/*" onchange={handleLogoUpload} style="display:none" />
              🖼 Logo hier hochladen
            </label>
          {/if}

          <!-- Firmenname direkt editierbar -->
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div class="rw-e rw-firmname"
            contenteditable="true"
            style="font-size:{v.firmenname.groesse}px; color:{v.firmenname.farbe}; font-weight:{v.firmenname.gewicht};"
            oninput={(e) => v.firmenname.text = e.currentTarget.innerText}
            data-ph="Firmenname eingeben"
          >{v.firmenname.text}</div>

          <!-- Absenderzeile -->
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div class="rw-e" style="font-size:9px; color:#888; margin-top:1px;"
            contenteditable="true"
            oninput={(e) => v.absenderzeile.text = e.currentTarget.innerText}
            data-ph="Firmenname · Straße · PLZ Ort (kleine Zeile)"
          >{v.absenderzeile.text}</div>

          <!-- Adresse -->
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div class="rw-e" style="font-size:11px; color:#555; margin-top:2px;"
            contenteditable="true"
            oninput={(e) => v.adresse.strasse = e.currentTarget.innerText}
            data-ph="Straße & Nr."
          >{v.adresse.strasse}</div>
          <div style="display:flex; gap:5px;">
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <span class="rw-e" style="font-size:11px; color:#555;"
              contenteditable="true"
              oninput={(e) => v.adresse.plz = e.currentTarget.innerText}
              data-ph="PLZ"
            >{v.adresse.plz}</span>
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <span class="rw-e" style="font-size:11px; color:#555;"
              contenteditable="true"
              oninput={(e) => v.adresse.ort = e.currentTarget.innerText}
              data-ph="Ort"
            >{v.adresse.ort}</span>
          </div>
        </div>

        <!-- Kontakt rechts -->
        <div class="rw-hr" style="font-size:11px; color:#555;">
          {#each [
            {label:'Telefon', key:'telefon'},
            {label:'Mobil', key:'mobil'},
            {label:'E-Mail', key:'email'},
            {label:'Steuer-Nr.', key:'steuernr'},
            {label:'USt-IdNr.', key:'ust_idnr'},
          ] as row}
            <div class="rw-kontakt-row">
              <span class="rw-kontakt-label">{row.label}</span>
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <span class="rw-e"
                contenteditable="true"
                oninput={(e) => v.kontakt[row.key] = e.currentTarget.innerText}
                data-ph="—"
              >{v.kontakt[row.key]}</span>
            </div>
          {/each}
        </div>
      </div>

      <!-- TRENNLINIE -->
      <div style="padding:10px var(--rand) 14px;">
        <hr style="border:none; border-top:{v.trennlinie.staerke}px solid {v.trennlinie.farbe}; margin:0;" />
      </div>

      <!-- INHALT -->
      <div class="rw-body" style="padding:0 var(--rand);">

        <!-- Info-Grid -->
        <div class="rw-grid2">
          <!-- Empfänger -->
          <div style="background:#f8fafc; border-radius:6px; padding:12px;">
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div class="rw-e" style="font-size:9px; font-weight:700; color:#999; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:6px;"
              contenteditable="true"
              oninput={(e) => v.empfaenger_label = e.currentTarget.innerText}
            >{v.empfaenger_label}</div>
            <div style="font-size:13px; font-weight:700;">{B.kaeufer_name}</div>
            <div style="font-size:12px; color:#555; line-height:1.6;">{B.kaeufer_strasse}</div>
            <div style="font-size:12px; color:#555;">{B.kaeufer_plz} {B.kaeufer_ort}</div>
            <div style="font-size:12px; color:#555;">{B.kaeufer_land}</div>
          </div>

          <!-- Rechnungsinfo -->
          <div style="background:#f8fafc; border-radius:6px; padding:12px; text-align:right;">
            <div style="font-size:9px; font-weight:700; color:#999; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:4px;">Rechnung</div>
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div class="rw-e" style="font-size:22px; font-weight:800; color:{v.akzentfarbe}; display:block; text-align:right;"
              contenteditable="true"
              oninput={(e) => v.rechnung_titel = e.currentTarget.innerText}
            >{v.rechnung_titel}</div>
            <div style="font-size:12px; color:#555; margin-top:6px; line-height:1.8;">
              <div>Nr: <strong>{B.rechnung_nr}</strong></div>
              <div>Datum: {B.datum}</div>
              <div>Bestellung: {B.order_id}</div>
            </div>
          </div>
        </div>

        <!-- Einleitung -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="rw-e" style="font-size:12px; color:#555; background:#f8fafc; border-radius:6px; padding:10px 14px; margin-bottom:16px; display:block;"
          contenteditable="true"
          oninput={(e) => v.einleitung = e.currentTarget.innerText}
        >{v.einleitung.replace('[order_id]', B.order_id).replace('[datum]', B.datum)}</div>

        <!-- Tabelle -->
        <table class="rw-table" style="margin-bottom:8px;">
          <thead>
            <tr style="background:{v.tabelle.kopf_hg};">
              {#if v.tabelle.zeige_artnr}<th style="color:{v.tabelle.kopf_farbe}; font-size:11px; width:70px;">Art.-Nr.</th>{/if}
              <th style="color:{v.tabelle.kopf_farbe}; font-size:11px;">Bezeichnung</th>
              {#if v.tabelle.zeige_menge}<th style="color:{v.tabelle.kopf_farbe}; font-size:11px; text-align:right; width:60px;">Menge</th>{/if}
              {#if v.tabelle.zeige_ep}<th style="color:{v.tabelle.kopf_farbe}; font-size:11px; text-align:right; width:100px;">Einzelpreis</th>{/if}
              {#if v.tabelle.zeige_betrag}<th style="color:{v.tabelle.kopf_farbe}; font-size:11px; text-align:right; width:100px;">Betrag</th>{/if}
            </tr>
          </thead>
          <tbody>
            <tr style="border-bottom:1px solid #e2e8f0;">
              {#if v.tabelle.zeige_artnr}<td style="padding:8px 12px; font-size:12px;">{B.artikel_nr}</td>{/if}
              <td style="padding:8px 12px; font-size:12px;"><strong>{B.artikel_name}</strong></td>
              {#if v.tabelle.zeige_menge}<td style="padding:8px 12px; font-size:12px; text-align:right;">{B.menge}</td>{/if}
              {#if v.tabelle.zeige_ep}<td style="padding:8px 12px; font-size:12px; text-align:right;">{fmt(B.einzelpreis)} EUR</td>{/if}
              {#if v.tabelle.zeige_betrag}<td style="padding:8px 12px; font-size:12px; text-align:right;">{fmt(B.einzelpreis)} EUR</td>{/if}
            </tr>
          </tbody>
        </table>

        <!-- Tabellen-Spalten Optionen -->
        <div class="rw-opts">
          <span class="rw-opts-label">Spalten:</span>
          <label><input type="checkbox" bind:checked={v.tabelle.zeige_artnr} /> Art.-Nr.</label>
          <label><input type="checkbox" bind:checked={v.tabelle.zeige_menge} /> Menge</label>
          <label><input type="checkbox" bind:checked={v.tabelle.zeige_ep} /> Einzelpreis</label>
          <label><input type="checkbox" bind:checked={v.tabelle.zeige_betrag} /> Betrag</label>
        </div>

        <!-- Summen -->
        <div style="width:{v.summen.breite}px; margin-left:auto; margin-bottom:12px;">
          <table style="width:100%; border-collapse:collapse;">
            <tr>
              <td style="padding:6px 12px; color:#666; font-size:12px;">Nettobetrag</td>
              <td style="padding:6px 12px; text-align:right; font-size:12px;">{fmt(B.netto_betrag)} EUR</td>
            </tr>
            {#if v.summen.kleinunternehmer}
              <tr><td colspan="2" style="padding:6px 12px; font-size:10px; color:#888; font-style:italic;">Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.</td></tr>
            {:else}
              <tr>
                <td style="padding:6px 12px; color:#666; font-size:12px; text-align:right;">MwSt. {B.steuersatz}%</td>
                <td style="padding:6px 12px; text-align:right; font-size:12px;">{fmt(B.steuer_betrag)} EUR</td>
              </tr>
            {/if}
            <tr style="background:{v.summen.total_hg};">
              <td style="padding:9px 12px; font-weight:700; font-size:13px; color:{v.summen.total_farbe};">Gesamtbetrag</td>
              <td style="padding:9px 12px; text-align:right; font-weight:700; font-size:13px; color:{v.summen.total_farbe};">{fmt(B.brutto_betrag)} EUR</td>
            </tr>
          </table>
          <label class="rw-mini-toggle"><input type="checkbox" bind:checked={v.summen.kleinunternehmer} /> Kleinunternehmer § 19 UStG</label>
        </div>

        <!-- Zahlung -->
        <div style="margin-bottom:12px;">
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <span class="rw-e" style="display:inline-block; background:#f0fdf4; color:#16a34a; border:1px solid #86efac; border-radius:6px; padding:5px 14px; font-size:12px; font-weight:700;"
            contenteditable="true"
            oninput={(e) => v.zahlung_text = e.currentTarget.innerText}
          >{v.zahlung_text}</span>
        </div>

        <!-- Bank -->
        {#if v.bank.sichtbar}
          <div style="background:#f8fafc; border-radius:6px; padding:12px; font-size:11px; margin-bottom:6px; display:flex; gap:20px; flex-wrap:wrap;">
            <div>
              <div style="font-size:9px; color:#999; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:3px;">Bankverbindung</div>
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <span class="rw-e" contenteditable="true" oninput={(e) => v.bank.name = e.currentTarget.innerText} data-ph="Bankname">{v.bank.name}</span>
            </div>
            <div>
              <div style="font-size:9px; color:#999; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:3px;">IBAN</div>
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <span class="rw-e" contenteditable="true" oninput={(e) => v.bank.iban = e.currentTarget.innerText} data-ph="DE12 3456 …">{v.bank.iban}</span>
            </div>
            <div>
              <div style="font-size:9px; color:#999; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:3px;">BIC</div>
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <span class="rw-e" contenteditable="true" oninput={(e) => v.bank.bic = e.currentTarget.innerText} data-ph="XXXXDEXX">{v.bank.bic}</span>
            </div>
          </div>
        {/if}
        <label class="rw-mini-toggle"><input type="checkbox" bind:checked={v.bank.sichtbar} /> Bankdaten anzeigen</label>

      </div><!-- /rw-body -->

      <!-- FOOTER — flex pusht ihn ans Ende -->
      {#if v.footer.sichtbar}
        <div class="rw-footer" style="padding:10px var(--rand); border-top:1px solid #e2e8f0; font-size:10px; color:#64748b; text-align:center;">
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div class="rw-e" contenteditable="true" oninput={(e) => v.footer.text = e.currentTarget.innerText}>{v.footer.text}</div>
          {#if v.footer.zeige_steuernr && v.kontakt.steuernr}
            <div style="margin-top:2px;">Steuer-Nr.: {v.kontakt.steuernr}{v.kontakt.ust_idnr ? ' · USt-IdNr.: ' + v.kontakt.ust_idnr : ''}</div>
          {/if}
          {#if v.footer.zeige_seite}<div style="margin-top:2px; opacity:0.5;">Seite 1</div>{/if}
        </div>
      {/if}

    </div><!-- /rw-a4 -->

    <!-- Einstellungen-Leiste unter A4 -->
    <div class="rw-settingsbar">
      <div class="rw-sg">
        <span class="rw-sl">Logo-Breite</span>
        <input type="number" class="rw-num" min="40" max="300" bind:value={v.logo.breite} />px
      </div>
      <div class="rw-sg">
        <span class="rw-sl">Summen-Breite</span>
        <input type="number" class="rw-num" min="150" max="450" bind:value={v.summen.breite} />px
      </div>
      <div class="rw-sg">
        <span class="rw-sl">Footer</span>
        <label><input type="checkbox" bind:checked={v.footer.sichtbar} /> Sichtbar</label>
        <label><input type="checkbox" bind:checked={v.footer.zeige_steuernr} /> Steuer-Nr.</label>
        <label><input type="checkbox" bind:checked={v.footer.zeige_seite} /> Seitenzahl</label>
      </div>
    </div>

    {/if}
  </div><!-- /rw-canvas -->

</div>

<style>
  .rw { display:flex; flex-direction:column; height:100%; width:100%; background:#dde1e7; overflow:hidden; }

  /* Toolbar */
  .rw-bar {
    display:flex; align-items:center; justify-content:space-between;
    padding:5px 14px; background:#fff; border-bottom:1px solid #ddd;
    flex-shrink:0; gap:8px; flex-wrap:wrap; min-height:44px;
    box-shadow:0 1px 4px rgba(0,0,0,0.08);
  }
  .rw-bar-l { display:flex; align-items:center; gap:6px; flex-wrap:wrap; }
  .rw-bar-r { display:flex; align-items:center; gap:8px; }
  .rw-title { font-size:0.85rem; font-weight:700; color:#1e293b; white-space:nowrap; }
  .sep { width:1px; height:20px; background:#e2e8f0; flex-shrink:0; }
  .rw-field-label { font-size:0.72rem; color:#777; white-space:nowrap; }

  .rw-sel {
    border:1px solid #ddd; border-radius:5px; padding:3px 6px;
    font-size:0.76rem; background:#fff; color:#333; cursor:pointer; outline:none;
  }
  .rw-num {
    width:48px; border:1px solid #ddd; border-radius:5px; padding:3px 5px;
    font-size:0.76rem; background:#fff; color:#333; outline:none;
  }
  .rw-dot {
    width:16px; height:16px; border-radius:50%; border:1.5px solid rgba(0,0,0,0.15);
    cursor:pointer; flex-shrink:0; transition:transform 0.1s;
  }
  .rw-dot:hover { transform:scale(1.25); }
  .rw-dot-active { outline:2px solid #000; outline-offset:2px; }

  .rw-btn {
    background:transparent; border:1px solid #ddd; border-radius:5px;
    padding:3px 9px; font-size:0.76rem; color:#555; cursor:pointer;
    display:flex; align-items:center; gap:4px; font-family:inherit;
    transition:all 0.12s; white-space:nowrap;
  }
  .rw-btn:hover { border-color:#999; color:#222; }
  .rw-btn-save {
    background:var(--primary,#2563eb); color:#fff; border-color:var(--primary,#2563eb);
    font-weight:600;
  }
  .rw-btn-save:hover { filter:brightness(1.1); }
  .rw-btn-save:disabled { opacity:0.6; cursor:not-allowed; }

  /* Canvas */
  .rw-canvas {
    flex:1; overflow-y:auto; overflow-x:auto;
    padding:28px 20px 40px;
    display:flex; flex-direction:column; align-items:center;
  }

  /* A4 — nutzt flex-direction:column damit Footer ans Ende gedrückt wird */
  .rw-a4 {
    width:794px;
    min-height:1123px;
    background:#fff;
    box-shadow:0 4px 28px rgba(0,0,0,0.18);
    border-radius:2px;
    position:relative;
    display:flex;
    flex-direction:column;
    flex-shrink:0;
  }

  .rw-header { display:flex; justify-content:space-between; align-items:flex-start; gap:16px; }
  .rw-hl { flex:1; }
  .rw-hr { flex-shrink:0; min-width:170px; }

  .rw-kontakt-row { display:flex; justify-content:flex-end; align-items:baseline; gap:8px; line-height:1.9; }
  .rw-kontakt-label { font-size:9px; color:#aaa; white-space:nowrap; }

  /* Body nimmt verfügbaren Platz, Footer wird ans Ende gedrückt */
  .rw-body { flex:1; }

  /* Footer — kein absolute mehr, wird durch flex ans Ende gedrückt */
  .rw-footer { flex-shrink:0; }

  /* Wasserzeichen */
  .rw-wz {
    position:absolute; top:50%; left:50%;
    transform:translate(-50%,-50%) rotate(-35deg);
    font-size:80px; font-weight:900;
    color:rgba(0,0,0,0.07); pointer-events:none; z-index:10;
    white-space:nowrap; user-select:none;
  }

  /* Logo Upload */
  .rw-logo-drop {
    display:flex; align-items:center; justify-content:center;
    height:48px; background:#f1f5f9; border:2px dashed #cbd5e1;
    border-radius:6px; font-size:0.75rem; color:#94a3b8;
    cursor:pointer; margin-bottom:6px; transition:all 0.15s;
  }
  .rw-logo-drop:hover { border-color:var(--ak,#2563eb); color:var(--ak,#2563eb); }

  /* Direkt editierbare Elemente */
  .rw-e {
    outline:none; border-radius:3px;
    transition:background 0.12s, box-shadow 0.12s;
    min-width:10px;
  }
  .rw-e:hover {
    background:rgba(37,99,235,0.05);
    box-shadow:0 0 0 1px rgba(37,99,235,0.2);
  }
  .rw-e:focus {
    background:rgba(37,99,235,0.07);
    box-shadow:0 0 0 2px rgba(37,99,235,0.3);
  }
  .rw-e:empty::before {
    content:attr(data-ph);
    color:#ccc; font-style:italic; pointer-events:none;
  }
  .rw-firmname { display:block; }

  /* Grid */
  .rw-grid2 { display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:14px; }

  /* Tabelle */
  .rw-table { width:100%; border-collapse:collapse; }
  .rw-table thead th { padding:8px 12px; text-align:left; }

  /* Spalten-Optionen (dezent im Dokument) */
  .rw-opts {
    display:flex; align-items:center; gap:10px; flex-wrap:wrap;
    font-size:0.72rem; color:#94a3b8; margin-bottom:14px;
    padding:4px 0; border-top:1px dashed #f1f5f9;
  }
  .rw-opts label { display:flex; align-items:center; gap:3px; cursor:pointer; }
  .rw-opts input { accent-color:var(--ak,#2563eb); }
  .rw-opts-label { font-weight:700; text-transform:uppercase; letter-spacing:0.05em; }

  /* Mini-Toggles */
  .rw-mini-toggle {
    display:flex; align-items:center; gap:4px;
    font-size:0.7rem; color:#aaa; cursor:pointer; margin-top:3px; margin-bottom:6px;
  }
  .rw-mini-toggle input { accent-color:var(--ak,#2563eb); }

  /* Settings-Bar unter A4 */
  .rw-settingsbar {
    width:794px; margin-top:14px;
    background:#fff; border:1px solid #e2e8f0; border-radius:8px;
    padding:10px 16px; display:flex; gap:20px; flex-wrap:wrap;
    font-size:0.75rem; color:#555; box-shadow:0 1px 4px rgba(0,0,0,0.05);
  }
  .rw-sg { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
  .rw-sl { font-size:0.68rem; font-weight:700; color:#aaa; text-transform:uppercase; letter-spacing:0.05em; }
  .rw-settingsbar label { display:flex; align-items:center; gap:4px; cursor:pointer; }
  .rw-settingsbar input[type=checkbox] { accent-color:var(--primary,#2563eb); }

  /* PDF */
  .rw-pdf { width:794px; height:1123px; flex-shrink:0; background:#fff; border:none; border-radius:2px; box-shadow:0 4px 28px rgba(0,0,0,0.18); }

  @media (max-width:860px) {
    .rw-a4, .rw-settingsbar, .rw-pdf { width:100%; min-width:0; }
  }
</style>
