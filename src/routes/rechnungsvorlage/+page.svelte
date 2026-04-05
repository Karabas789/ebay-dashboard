<script>
  import { onMount } from 'svelte';
  import { currentUser, showToast } from '$lib/stores.js';
  import { apiCall } from '$lib/api.js';

  // ── Beispieldaten (Vorschau) ────────────────────────────────────────────────
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

  // ── Vorlagen-State ──────────────────────────────────────────────────────────
  let v = $state({
    akzentfarbe: '#1a1a1a',
    schriftart: 'Arial',
    seitenrand: 28,

    logo: { base64: '', breite: 130, position: 'rechts' }, // links | rechts

    absenderzeile: {
      text: 'Import & Produkte Vertrieb · Auf der Schläfe 1 · 57078 Siegen',
      groesse: 8,
      position: 'links', // links | mitte | rechts
    },

    empfaenger: {
      position: 'links', // links | mitte | rechts
      groesse: 11,
    },

    kontakt_block: {
      titel: 'So erreichen Sie uns',
      email: 'import_vertrieb@mail.de',
      telefon: '0271 50149974',
      mobil: '0177 6776548',
      steuernr: '342/5058/2211',
      ust_idnr: 'DE815720228',
      groesse: 11,
    },

    einleitung: 'Sehr geehrte Damen und Herren,\nnachfolgend berechnen wir Ihnen wie vorab besprochen:',

    tabelle: {
      kopf_hg: '#1a1a1a',
      kopf_farbe: '#ffffff',
      zeige_artnr: true,
      zeige_menge: true,
      zeige_ep: true,
      zeige_betrag: true,
    },

    summen: {
      breite: 280,
      kleinunternehmer: false,
    },

    zahlung: {
      text: 'Bereits bezahlt über eBay',
      sichtbar: true,
      position: 'links', // links | mitte | rechts
    },

    abschluss: {
      text: 'Vielen Dank für Ihren Auftrag!\n\nBitte begleichen Sie den offenen Betrag bis zum [zahlungsziel].\n\nMit freundlichen Grüßen\nImport & Produkte Vertrieb',
    },

    wasserzeichen: { sichtbar: true, text: 'Entwurf' },

    footer: {
      spalte1_name: 'Import & Produkte Vertrieb',
      spalte1_inh: 'Inh. Oxana Dubs',
      spalte1_str: 'Auf der Schläfe 1',
      spalte1_plz: 'DE 57078 Siegen',
      spalte2_tel: 'Telefon: +49 271 50149974',
      spalte2_mob: 'Mobil:    +49 177 6776548',
      spalte2_mail: 'E-Mail:   ov-shop@mail.de',
      spalte3_titel: 'Bankverbindung: N26 Bank',
      spalte3_iban: 'IBAN: DE60 1001 1001 2829 9706 30',
      spalte3_bic: 'BIC: NTSBDEB1XXX',
      spalte4_titel: 'Finanzamt Siegen',
      spalte4_stnr: 'St.Nr. 342/5058/2200',
      spalte4_ust: 'USt. -ID: DE815720228',
      groesse: 8,
    },
  });

  let speichertLaeuft = $state(false);
  let pdfLaeuft = $state(false);
  let vorschauPDF = $state('');
  let zeigtPDF = $state(false);
  let zeigtEinstellungen = $state(false);

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

  // Hilfsfunktion: Text-Align aus Position
  function posAlign(pos) {
    return pos === 'rechts' ? 'flex-end' : pos === 'mitte' ? 'center' : 'flex-start';
  }

  function abschlussText() {
    return v.abschluss.text
      .replace('[zahlungsziel]', B.zahlungsziel)
      .replace('[datum]', B.datum);
  }
</script>

<!-- ══════════════════════════════════════════════════════════════════════════ -->
<!-- WRAPPER                                                                  -->
<!-- ══════════════════════════════════════════════════════════════════════════ -->
<div class="rw">

  <!-- ── TOOLBAR ────────────────────────────────────────────────────────────── -->
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

      <div class="sep"></div>
      <label class="rw-field-label">Farbthema</label>
      {#each themen as t}
        <button class="rw-dot" style="background:{t.c};"
          class:rw-dot-active={v.akzentfarbe === t.c}
          onclick={() => applyTheme(t.c)} title={t.n}></button>
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
      <button class="rw-btn" onclick={() => zeigtEinstellungen = !zeigtEinstellungen}>
        ⚙ Einstellungen {zeigtEinstellungen ? '▲' : '▼'}
      </button>

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
        <button class="rw-btn" onclick={pdfVorschau} disabled={pdfLaeuft}>{pdfLaeuft ? '⏳' : '🖨'} PDF Vorschau</button>
      {/if}
      <button class="rw-btn rw-btn-save" onclick={speichern} disabled={speichertLaeuft}>
        {speichertLaeuft ? 'Speichert…' : '💾 Speichern'}
      </button>
    </div>
  </div>

  <!-- ── EINSTELLUNGS-PANEL ─────────────────────────────────────────────────── -->
  {#if zeigtEinstellungen}
  <div class="rw-panel">
    <div class="rw-panel-grid">

      <!-- Logo -->
      <div class="rw-pg">
        <div class="rw-pg-title">Logo</div>
        <label class="rw-pl">Breite
          <input type="number" class="rw-num" min="40" max="300" bind:value={v.logo.breite} />px
        </label>
        <label class="rw-pl">Position
          <select class="rw-sel" bind:value={v.logo.position}>
            <option value="links">Links</option>
            <option value="rechts">Rechts</option>
          </select>
        </label>
      </div>

      <!-- Absenderzeile -->
      <div class="rw-pg">
        <div class="rw-pg-title">Absenderzeile</div>
        <label class="rw-pl">Größe
          <input type="number" class="rw-num" min="6" max="14" bind:value={v.absenderzeile.groesse} />pt
        </label>
        <label class="rw-pl">Position
          <select class="rw-sel" bind:value={v.absenderzeile.position}>
            <option value="links">Links</option>
            <option value="mitte">Mitte</option>
            <option value="rechts">Rechts</option>
          </select>
        </label>
      </div>

      <!-- Empfänger-Block -->
      <div class="rw-pg">
        <div class="rw-pg-title">Empfänger-Adresse</div>
        <label class="rw-pl">Größe
          <input type="number" class="rw-num" min="8" max="16" bind:value={v.empfaenger.groesse} />pt
        </label>
        <label class="rw-pl">Position
          <select class="rw-sel" bind:value={v.empfaenger.position}>
            <option value="links">Links</option>
            <option value="mitte">Mitte</option>
            <option value="rechts">Rechts</option>
          </select>
        </label>
      </div>

      <!-- Kontakt-Block -->
      <div class="rw-pg">
        <div class="rw-pg-title">Kontakt-Block</div>
        <label class="rw-pl">Größe
          <input type="number" class="rw-num" min="8" max="14" bind:value={v.kontakt_block.groesse} />pt
        </label>
      </div>

      <!-- Tabelle -->
      <div class="rw-pg">
        <div class="rw-pg-title">Tabellen-Spalten</div>
        <label class="rw-pl"><input type="checkbox" bind:checked={v.tabelle.zeige_artnr} /> Art.-Nr.</label>
        <label class="rw-pl"><input type="checkbox" bind:checked={v.tabelle.zeige_menge} /> Menge</label>
        <label class="rw-pl"><input type="checkbox" bind:checked={v.tabelle.zeige_ep} /> Einzelpreis</label>
        <label class="rw-pl"><input type="checkbox" bind:checked={v.tabelle.zeige_betrag} /> Betrag</label>
      </div>

      <!-- Summen -->
      <div class="rw-pg">
        <div class="rw-pg-title">Summen</div>
        <label class="rw-pl">Breite
          <input type="number" class="rw-num" min="150" max="450" bind:value={v.summen.breite} />px
        </label>
        <label class="rw-pl"><input type="checkbox" bind:checked={v.summen.kleinunternehmer} /> § 19 UStG</label>
      </div>

      <!-- Zahlung-Button -->
      <div class="rw-pg">
        <div class="rw-pg-title">„Bezahlt"-Badge</div>
        <label class="rw-pl"><input type="checkbox" bind:checked={v.zahlung.sichtbar} /> Sichtbar</label>
        <label class="rw-pl">Position
          <select class="rw-sel" bind:value={v.zahlung.position}>
            <option value="links">Links</option>
            <option value="mitte">Mitte</option>
            <option value="rechts">Rechts</option>
          </select>
        </label>
      </div>

      <!-- Footer -->
      <div class="rw-pg">
        <div class="rw-pg-title">Footer</div>
        <label class="rw-pl">Schriftgröße
          <input type="number" class="rw-num" min="6" max="11" bind:value={v.footer.groesse} />pt
        </label>
      </div>

    </div>
  </div>
  {/if}

  <!-- ── CANVAS ─────────────────────────────────────────────────────────────── -->
  <div class="rw-canvas">

    {#if zeigtPDF && vorschauPDF}
      <iframe src="data:application/pdf;base64,{vorschauPDF}" title="PDF Vorschau" class="rw-pdf"></iframe>

    {:else}
    <!-- ════════════════════════════════════════════════════════════════════ -->
    <!-- A4 DOKUMENT                                                         -->
    <!-- ════════════════════════════════════════════════════════════════════ -->
    <div class="rw-a4" style="font-family:{v.schriftart},sans-serif; --ak:{v.akzentfarbe}; --rand:{v.seitenrand}px;">

      {#if v.wasserzeichen.sichtbar}
        <div class="rw-wz">{v.wasserzeichen.text}</div>
      {/if}

      <!-- ── KOPF ──────────────────────────────────────────────────────────── -->
      <div class="rw-kopf" style="padding: var(--rand) var(--rand) 0;">

        <!-- Logo + Absenderzeile: Layout abhängig von logo.position -->
        <div class="rw-kopf-top" style="flex-direction: {v.logo.position === 'rechts' ? 'row' : 'row-reverse'};">

          <!-- Linke Seite: Absenderzeile + Empfänger-Adresse -->
          <div class="rw-kopf-links" style="align-items:{posAlign(v.absenderzeile.position)};">

            <!-- Absenderzeile (klein, grau) -->
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div class="rw-e"
              contenteditable="true"
              style="font-size:{v.absenderzeile.groesse}px; color:#888; margin-bottom:10px; display:block;"
              oninput={(e) => v.absenderzeile.text = e.currentTarget.innerText}
              data-ph="Absenderzeile (Firmenname · Straße · PLZ Ort)"
            >{v.absenderzeile.text}</div>

            <!-- Empfänger-Adresse -->
            <div style="align-self:{posAlign(v.empfaenger.position)};">
              <div style="font-size:{v.empfaenger.groesse}px; font-weight:700; color:#1a1a1a; line-height:1.7;">
                {B.kaeufer_name}
              </div>
              <div style="font-size:{v.empfaenger.groesse}px; color:#1a1a1a; line-height:1.7;">{B.kaeufer_strasse}</div>
              {#if B.kaeufer_extra}
                <div style="font-size:{v.empfaenger.groesse}px; color:#1a1a1a; line-height:1.7;">{B.kaeufer_extra}</div>
              {/if}
              <div style="font-size:{v.empfaenger.groesse}px; color:#1a1a1a; line-height:1.7;">{B.kaeufer_plz} {B.kaeufer_ort}</div>
            </div>
          </div>

          <!-- Rechte Seite: Logo + Kontakt-Block -->
          <div class="rw-kopf-rechts">

            <!-- Logo -->
            {#if v.logo.base64}
              <div style="margin-bottom:16px; text-align:right;">
                <img src={v.logo.base64} alt="Logo"
                  style="width:{v.logo.breite}px; max-height:80px; object-fit:contain;" />
              </div>
            {:else}
              <label class="rw-logo-drop" style="width:{v.logo.breite}px; margin-left:auto; margin-bottom:16px;">
                <input type="file" accept="image/*" onchange={handleLogoUpload} style="display:none" />
                🖼 Logo hochladen
              </label>
            {/if}

            <!-- Kontakt-Block -->
            <div class="rw-kontakt" style="font-size:{v.kontakt_block.groesse}px;">
              <!-- Titel -->
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <div class="rw-e rw-kontakt-titel"
                contenteditable="true"
                oninput={(e) => v.kontakt_block.titel = e.currentTarget.innerText}
              >{v.kontakt_block.titel}</div>

              <div class="rw-kontakt-row">
                <span class="rw-kl">E-Mail</span>
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <span class="rw-e rw-kv"
                  contenteditable="true"
                  oninput={(e) => v.kontakt_block.email = e.currentTarget.innerText}
                  data-ph="—"
                >{v.kontakt_block.email}</span>
              </div>
              <div class="rw-kontakt-row">
                <span class="rw-kl">Telefon</span>
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <span class="rw-e rw-kv"
                  contenteditable="true"
                  oninput={(e) => v.kontakt_block.telefon = e.currentTarget.innerText}
                  data-ph="—"
                >{v.kontakt_block.telefon}</span>
              </div>
              <div class="rw-kontakt-row">
                <span class="rw-kl">Mobil</span>
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <span class="rw-e rw-kv"
                  contenteditable="true"
                  oninput={(e) => v.kontakt_block.mobil = e.currentTarget.innerText}
                  data-ph="—"
                >{v.kontakt_block.mobil}</span>
              </div>

              <div class="rw-kontakt-spacer"></div>

              <div class="rw-kontakt-row">
                <span class="rw-kl">Steuer-Nr.</span>
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <span class="rw-e rw-kv rw-kv-bold"
                  contenteditable="true"
                  oninput={(e) => v.kontakt_block.steuernr = e.currentTarget.innerText}
                  data-ph="—"
                >{v.kontakt_block.steuernr}</span>
              </div>
              <div class="rw-kontakt-row">
                <span class="rw-kl">USt-IdNr.</span>
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <span class="rw-e rw-kv rw-kv-bold"
                  contenteditable="true"
                  oninput={(e) => v.kontakt_block.ust_idnr = e.currentTarget.innerText}
                  data-ph="—"
                >{v.kontakt_block.ust_idnr}</span>
              </div>

              <div class="rw-kontakt-spacer"></div>

              <div class="rw-kontakt-row">
                <span class="rw-kl">Datum</span>
                <span class="rw-kv rw-kv-bold">{B.datum}</span>
              </div>
              <div class="rw-kontakt-row">
                <span class="rw-kl">Kunde</span>
                <span class="rw-kv rw-kv-bold">{B.kunde_nr}</span>
              </div>
              <div class="rw-kontakt-row">
                <span class="rw-kl">Rechnung</span>
                <span class="rw-kv rw-kv-bold">{B.rechnung_nr}</span>
              </div>
            </div>

          </div>
        </div>

      </div><!-- /rw-kopf -->

      <!-- ── TRENNLINIE ────────────────────────────────────────────────────── -->
      <div style="padding:16px var(--rand) 0;">
        <hr class="rw-hr-line" />
      </div>

      <!-- ── INHALT (flex:1 — schiebt Footer nach unten) ────────────────────── -->
      <div class="rw-body" style="padding:14px var(--rand) 0;">

        <!-- Einleitung -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="rw-e"
          contenteditable="true"
          style="font-size:11px; color:#333; margin-bottom:12px; white-space:pre-line; display:block; line-height:1.55;"
          oninput={(e) => v.einleitung = e.currentTarget.innerText}
          data-ph="Einleitungstext…"
        >{v.einleitung}</div>

        <!-- Rechnungs-Titel -->
        <div style="margin-bottom:2px;">
          <div style="font-size:14px; font-weight:700; color:#1a1a1a;">Rechnung {B.rechnung_nr}</div>
          <div style="font-size:9px; color:#888; margin-bottom:10px;">Das Rechnungsdatum entspricht dem Leistungsdatum</div>
        </div>

        <!-- Positions-Tabelle -->
        <table class="rw-table">
          <thead>
            <tr style="background:{v.tabelle.kopf_hg};">
              <th class="rw-th" style="color:{v.tabelle.kopf_farbe}; width:36px;">Pos</th>
              {#if v.tabelle.zeige_artnr}
                <th class="rw-th" style="color:{v.tabelle.kopf_farbe}; width:70px;">Art-Nr.</th>
              {/if}
              <th class="rw-th" style="color:{v.tabelle.kopf_farbe};">Bezeichnung</th>
              {#if v.tabelle.zeige_menge}
                <th class="rw-th rw-thr" style="color:{v.tabelle.kopf_farbe}; width:52px;">Menge</th>
              {/if}
              {#if v.tabelle.zeige_ep}
                <th class="rw-th rw-thr" style="color:{v.tabelle.kopf_farbe}; width:90px;">Einzelpreis</th>
              {/if}
              {#if v.tabelle.zeige_betrag}
                <th class="rw-th rw-thr" style="color:{v.tabelle.kopf_farbe}; width:80px;">Betrag</th>
              {/if}
            </tr>
          </thead>
          <tbody>
            <tr class="rw-tr">
              <td class="rw-td">1</td>
              {#if v.tabelle.zeige_artnr}
                <td class="rw-td" style="color:#555;">{B.artikel_nr}</td>
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

        <!-- Summen -->
        <div style="width:{v.summen.breite}px; margin-left:auto; margin-top:0; margin-bottom:14px;">
          <table class="rw-summen-table">
            <tbody>
              <tr>
                <td class="rw-sum-l">Nettobetrag</td>
                <td class="rw-sum-r">{fmt(B.netto_betrag)} €</td>
              </tr>
              {#if v.summen.kleinunternehmer}
                <tr>
                  <td colspan="2" style="padding:5px 10px; font-size:9px; color:#888; font-style:italic;">
                    Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.
                  </td>
                </tr>
              {:else}
                <tr>
                  <td class="rw-sum-l">Umsatzsteuer {B.steuersatz}%</td>
                  <td class="rw-sum-r">{fmt(B.steuer_betrag)} €</td>
                </tr>
              {/if}
              <tr class="rw-sum-total">
                <td class="rw-sum-l" style="font-weight:700;">Rechnungsbetrag</td>
                <td class="rw-sum-r" style="font-weight:700;">{fmt(B.brutto_betrag)} €</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Abschlusstext -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="rw-e"
          contenteditable="true"
          style="font-size:11px; color:#333; white-space:pre-line; display:block; line-height:1.6; margin-bottom:14px;"
          oninput={(e) => v.abschluss.text = e.currentTarget.innerText}
          data-ph="Abschlusstext…"
        >{abschlussText()}</div>

        <!-- „Bereits bezahlt" Badge -->
        {#if v.zahlung.sichtbar}
          <div style="display:flex; justify-content:{posAlign(v.zahlung.position)}; margin-bottom:10px;">
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <span class="rw-e rw-badge"
              contenteditable="true"
              oninput={(e) => v.zahlung.text = e.currentTarget.innerText}
            >{v.zahlung.text}</span>
          </div>
        {/if}

      </div><!-- /rw-body -->

      <!-- ── FOOTER — margin-top:auto schiebt ihn ans Seitenende ────────────── -->
      <div class="rw-footer" style="padding:8px var(--rand); font-size:{v.footer.groesse}px;">
        <div class="rw-footer-grid">

          <!-- Spalte 1: Firma + Adresse -->
          <div>
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div class="rw-e" contenteditable="true"
              oninput={(e) => v.footer.spalte1_name = e.currentTarget.innerText}
              data-ph="Firmenname"
            >{v.footer.spalte1_name}</div>
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div class="rw-e" contenteditable="true"
              oninput={(e) => v.footer.spalte1_inh = e.currentTarget.innerText}
              data-ph="Inhaber"
            >{v.footer.spalte1_inh}</div>
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div class="rw-e" contenteditable="true"
              oninput={(e) => v.footer.spalte1_str = e.currentTarget.innerText}
              data-ph="Straße"
            >{v.footer.spalte1_str}</div>
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div class="rw-e" contenteditable="true"
              oninput={(e) => v.footer.spalte1_plz = e.currentTarget.innerText}
              data-ph="PLZ Ort"
            >{v.footer.spalte1_plz}</div>
          </div>

          <!-- Spalte 2: Telefon + Mobil + E-Mail -->
          <div>
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div class="rw-e" contenteditable="true"
              oninput={(e) => v.footer.spalte2_tel = e.currentTarget.innerText}
              data-ph="Telefon"
            >{v.footer.spalte2_tel}</div>
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div class="rw-e" contenteditable="true"
              oninput={(e) => v.footer.spalte2_mob = e.currentTarget.innerText}
              data-ph="Mobil"
            >{v.footer.spalte2_mob}</div>
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div class="rw-e" contenteditable="true"
              oninput={(e) => v.footer.spalte2_mail = e.currentTarget.innerText}
              data-ph="E-Mail"
            >{v.footer.spalte2_mail}</div>
          </div>

          <!-- Spalte 3: Bank -->
          <div>
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div class="rw-e" contenteditable="true"
              oninput={(e) => v.footer.spalte3_titel = e.currentTarget.innerText}
              data-ph="Bankverbindung"
            >{v.footer.spalte3_titel}</div>
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div class="rw-e" contenteditable="true"
              oninput={(e) => v.footer.spalte3_iban = e.currentTarget.innerText}
              data-ph="IBAN"
            >{v.footer.spalte3_iban}</div>
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div class="rw-e" contenteditable="true"
              oninput={(e) => v.footer.spalte3_bic = e.currentTarget.innerText}
              data-ph="BIC"
            >{v.footer.spalte3_bic}</div>
          </div>

          <!-- Spalte 4: Finanzamt -->
          <div>
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div class="rw-e" contenteditable="true"
              oninput={(e) => v.footer.spalte4_titel = e.currentTarget.innerText}
              data-ph="Finanzamt"
            >{v.footer.spalte4_titel}</div>
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div class="rw-e" contenteditable="true"
              oninput={(e) => v.footer.spalte4_stnr = e.currentTarget.innerText}
              data-ph="Steuer-Nr."
            >{v.footer.spalte4_stnr}</div>
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div class="rw-e" contenteditable="true"
              oninput={(e) => v.footer.spalte4_ust = e.currentTarget.innerText}
              data-ph="USt-ID"
            >{v.footer.spalte4_ust}</div>
          </div>

        </div>
      </div>

    </div><!-- /rw-a4 -->
    {/if}

  </div><!-- /rw-canvas -->
</div>

<style>
  /* ── Layout ────────────────────────────────────────────────────────────── */
  .rw {
    display: flex;
    flex-direction: column;
    height: 100%;
    width: 100%;
    background: #dde1e7;
    overflow: hidden;
  }

  /* ── Toolbar ──────────────────────────────────────────────────────────── */
  .rw-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 5px 14px;
    background: #fff;
    border-bottom: 1px solid #ddd;
    flex-shrink: 0;
    gap: 8px;
    flex-wrap: wrap;
    min-height: 44px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  }
  .rw-bar-l { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
  .rw-bar-r { display: flex; align-items: center; gap: 8px; }
  .rw-title { font-size: 0.85rem; font-weight: 700; color: #1e293b; white-space: nowrap; }
  .sep { width: 1px; height: 20px; background: #e2e8f0; flex-shrink: 0; }
  .rw-field-label { font-size: 0.72rem; color: #777; white-space: nowrap; }

  .rw-sel {
    border: 1px solid #ddd; border-radius: 5px; padding: 3px 6px;
    font-size: 0.76rem; background: #fff; color: #333; cursor: pointer; outline: none;
  }
  .rw-num {
    width: 48px; border: 1px solid #ddd; border-radius: 5px; padding: 3px 5px;
    font-size: 0.76rem; background: #fff; color: #333; outline: none;
  }
  .rw-dot {
    width: 16px; height: 16px; border-radius: 50%;
    border: 1.5px solid rgba(0,0,0,0.15); cursor: pointer; flex-shrink: 0; transition: transform 0.1s;
  }
  .rw-dot:hover { transform: scale(1.25); }
  .rw-dot-active { outline: 2px solid #000; outline-offset: 2px; }

  .rw-btn {
    background: transparent; border: 1px solid #ddd; border-radius: 5px;
    padding: 3px 9px; font-size: 0.76rem; color: #555; cursor: pointer;
    display: flex; align-items: center; gap: 4px; font-family: inherit;
    transition: all 0.12s; white-space: nowrap;
  }
  .rw-btn:hover { border-color: #999; color: #222; }
  .rw-btn-save {
    background: var(--primary, #2563eb); color: #fff;
    border-color: var(--primary, #2563eb); font-weight: 600;
  }
  .rw-btn-save:hover { filter: brightness(1.1); }
  .rw-btn-save:disabled { opacity: 0.6; cursor: not-allowed; }

  /* ── Einstellungs-Panel ────────────────────────────────────────────────── */
  .rw-panel {
    background: #f8fafc; border-bottom: 1px solid #e2e8f0;
    padding: 10px 16px; flex-shrink: 0;
    box-shadow: inset 0 -1px 0 #e2e8f0;
  }
  .rw-panel-grid {
    display: flex; gap: 20px; flex-wrap: wrap; align-items: flex-start;
  }
  .rw-pg {
    display: flex; flex-direction: column; gap: 5px;
    min-width: 130px;
  }
  .rw-pg-title {
    font-size: 0.68rem; font-weight: 700; color: #94a3b8;
    text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;
  }
  .rw-pl {
    display: flex; align-items: center; gap: 5px;
    font-size: 0.75rem; color: #555; cursor: pointer;
  }

  /* ── Canvas ─────────────────────────────────────────────────────────────── */
  .rw-canvas {
    flex: 1; overflow-y: auto; overflow-x: auto;
    padding: 28px 20px 40px;
    display: flex; flex-direction: column; align-items: center;
  }

  /* ── A4 — flex-column damit Footer via margin-top:auto ans Ende geht ─────── */
  .rw-a4 {
    width: 794px;
    min-height: 1123px;
    background: #fff;
    box-shadow: 0 4px 28px rgba(0,0,0,0.18);
    border-radius: 2px;
    position: relative;
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
  }

  /* ── Kopf-Bereich ────────────────────────────────────────────────────────── */
  .rw-kopf-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 20px;
  }
  .rw-kopf-links {
    flex: 1;
    display: flex;
    flex-direction: column;
  }
  .rw-kopf-rechts {
    flex-shrink: 0;
    min-width: 200px;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
  }

  /* ── Trennlinie ──────────────────────────────────────────────────────────── */
  .rw-hr-line {
    border: none;
    border-top: 1px solid #aaa;
    margin: 0;
  }

  /* ── Kontakt-Block (rechts oben) ─────────────────────────────────────────── */
  .rw-kontakt { text-align: right; min-width: 200px; }
  .rw-kontakt-titel {
    font-size: 1em; font-weight: 700; text-decoration: underline;
    margin-bottom: 4px; display: block;
  }
  .rw-kontakt-row {
    display: flex; justify-content: flex-end; align-items: baseline;
    gap: 10px; line-height: 1.75;
  }
  .rw-kl { color: #555; min-width: 65px; text-align: right; }
  .rw-kv { color: #1a1a1a; }
  .rw-kv-bold { font-weight: 700; }
  .rw-kontakt-spacer { height: 6px; }

  /* ── Logo Upload Placeholder ─────────────────────────────────────────────── */
  .rw-logo-drop {
    display: flex; align-items: center; justify-content: center;
    height: 50px; background: #f1f5f9; border: 2px dashed #cbd5e1;
    border-radius: 6px; font-size: 0.75rem; color: #94a3b8;
    cursor: pointer; transition: all 0.15s;
  }
  .rw-logo-drop:hover { border-color: var(--ak, #1a1a1a); color: var(--ak, #1a1a1a); }

  /* ── Wasserzeichen ───────────────────────────────────────────────────────── */
  .rw-wz {
    position: absolute; top: 50%; left: 50%;
    transform: translate(-50%, -50%) rotate(-35deg);
    font-size: 90px; font-weight: 900;
    color: rgba(0,0,0,0.06); pointer-events: none; z-index: 10;
    white-space: nowrap; user-select: none;
  }

  /* ── Inhalt (wächst → schiebt Footer ans Ende) ───────────────────────────── */
  .rw-body { flex: 1; }

  /* ── Tabelle ─────────────────────────────────────────────────────────────── */
  .rw-table { width: 100%; border-collapse: collapse; margin-bottom: 0; }
  .rw-th {
    padding: 7px 10px; text-align: left;
    font-size: 11px; font-weight: 700;
  }
  .rw-thr { text-align: right; }
  .rw-tr { border-bottom: 1px solid #e2e8f0; }
  .rw-td { padding: 8px 10px; font-size: 11px; color: #1a1a1a; vertical-align: top; }
  .rw-tdr { text-align: right; }

  /* ── Summen-Tabelle ──────────────────────────────────────────────────────── */
  .rw-summen-table { width: 100%; border-collapse: collapse; border-top: 1px solid #ccc; }
  .rw-sum-l { padding: 5px 10px; font-size: 11px; color: #555; text-align: right; }
  .rw-sum-r { padding: 5px 10px; font-size: 11px; color: #1a1a1a; text-align: right; white-space: nowrap; }
  .rw-sum-total { border-top: 1px solid #1a1a1a; border-bottom: 2px solid #1a1a1a; }
  .rw-sum-total .rw-sum-l,
  .rw-sum-total .rw-sum-r { font-weight: 700; font-size: 12px; padding: 6px 10px; }

  /* ── Bezahlt-Badge ───────────────────────────────────────────────────────── */
  .rw-badge {
    display: inline-block;
    background: #f0fdf4; color: #15803d;
    border: 1px solid #86efac; border-radius: 5px;
    padding: 4px 14px; font-size: 11px; font-weight: 700;
  }

  /* ── Footer — margin-top:auto drückt ihn ans Ende der A4-Seite ──────────── */
  .rw-footer {
    margin-top: auto;
    border-top: 1px solid #ccc;
    color: #333;
    flex-shrink: 0;
  }
  .rw-footer-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
  }
  .rw-footer-grid > div {
    line-height: 1.7;
    font-family: monospace;
  }

  /* ── Direkt editierbare Elemente ─────────────────────────────────────────── */
  :global(.rw-e) {
    outline: none; border-radius: 2px;
    transition: background 0.12s, box-shadow 0.12s;
    min-width: 6px;
  }
  :global(.rw-e:hover) {
    background: rgba(37,99,235,0.05);
    box-shadow: 0 0 0 1px rgba(37,99,235,0.2);
  }
  :global(.rw-e:focus) {
    background: rgba(37,99,235,0.07);
    box-shadow: 0 0 0 2px rgba(37,99,235,0.3);
  }
  :global(.rw-e:empty::before) {
    content: attr(data-ph);
    color: #ccc; font-style: italic; pointer-events: none;
  }

  /* ── PDF-Vorschau ────────────────────────────────────────────────────────── */
  .rw-pdf {
    width: 794px; height: 1123px; flex-shrink: 0;
    background: #fff; border: none; border-radius: 2px;
    box-shadow: 0 4px 28px rgba(0,0,0,0.18);
  }

  @media (max-width: 860px) {
    .rw-a4, .rw-pdf { width: 100%; min-width: 0; }
  }
</style>
