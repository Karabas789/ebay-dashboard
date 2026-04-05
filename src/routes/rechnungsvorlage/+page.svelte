<script>
  import { onMount } from 'svelte';
  import { currentUser, showToast } from '$lib/stores.js';
  import { apiCall } from '$lib/api.js';

  // ─── Beispieldaten ────────────────────────────────────────────────────────
  const B = {
    rechnung_nr: 'RE-2026-00042', datum: '02.04.2026', order_id: '22-14426-19402',
    kaeufer_name: 'Hermann Jakob', kaeufer_strasse: 'Gneisenaustr. 12',
    kaeufer_plz: '85051', kaeufer_ort: 'Ingolstadt', kaeufer_land: 'Deutschland',
    artikel_name: 'Jemako Intensivreiniger KalkEx Plus', artikel_nr: '1054',
    menge: 1, einzelpreis: 15.9579, netto_betrag: 15.96,
    steuer_betrag: 3.03, brutto_betrag: 18.99, steuersatz: 19
  };

  const fmt = (n) => Number(n||0).toLocaleString('de-DE', {minimumFractionDigits:2,maximumFractionDigits:2});

  // ─── Vorlage State ────────────────────────────────────────────────────────
  // Jeder Block hat: sichtbar, plus eigene Stilfelder
  let v = $state({
    // Globale Einstellungen
    schriftart: 'Arial',
    seitenrand: 32,
    hintergrundfarbe_seite: '#ffffff',

    // Block: Logo
    logo: {
      sichtbar: true,
      base64: '',
      breite: 120,
      position: 'links', // links | rechts | mitte
      ausrichtung_vertikal: 'oben', // oben | mitte
    },

    // Block: Firmenname
    firmenname: {
      sichtbar: true,
      text: '',
      groesse: 20,
      farbe: '#2563eb',
      gewicht: '800',
      ausrichtung: 'left',
      margin_top: 0,
      margin_bottom: 4,
    },

    // Block: Firmenadresse
    firmenadresse: {
      sichtbar: true,
      strasse: '', plz: '', ort: '', land: 'Deutschland',
      groesse: 11,
      farbe: '#888888',
      zeilenabstand: 1.6,
    },

    // Block: Kontaktdaten (rechts im Header)
    kontakt: {
      sichtbar: true,
      telefon: '', email: '', website: '', steuernr: '', ust_idnr: '',
      groesse: 11,
      farbe: '#555555',
      ausrichtung: 'right',
      zeilenabstand: 1.8,
      zeige_telefon: true,
      zeige_email: true,
      zeige_website: true,
      zeige_steuernr: true,
      zeige_ust: true,
    },

    // Block: Header-Trennlinie
    trennlinie: {
      sichtbar: true,
      farbe: '#2563eb',
      staerke: 3,
      margin_top: 16,
      margin_bottom: 20,
    },

    // Block: Rechnungsinfo (Titel + Nr + Datum)
    rechnungsinfo: {
      sichtbar: true,
      titel_text: 'Rechnung',
      titel_groesse: 22,
      titel_farbe: '#2563eb',
      titel_gewicht: '800',
      nr_groesse: 13,
      nr_farbe: '#1e293b',
      hintergrund: '#f8fafc',
      border_radius: 6,
      ausrichtung: 'right',
    },

    // Block: Empfänger
    empfaenger: {
      sichtbar: true,
      label_text: 'Rechnungsempfänger',
      label_groesse: 9,
      label_farbe: '#999999',
      name_groesse: 13,
      name_gewicht: '700',
      adresse_groesse: 12,
      adresse_farbe: '#555555',
      hintergrund: '#f8fafc',
      border_radius: 6,
    },

    // Block: Einleitungstext
    einleitung: {
      sichtbar: true,
      text: 'Ihre Bestellung Nr. [order_id] vom [datum].',
      groesse: 13,
      farbe: '#555555',
      hintergrund: '#f8fafc',
      border_radius: 6,
    },

    // Block: Tabelle
    tabelle: {
      sichtbar: true,
      zeige_artnr: true,
      zeige_menge: true,
      zeige_einzelpreis: true,
      zeige_betrag: true,
      kopf_text: 'Art.-Nr.',
      kopf_bezeichnung: 'Bezeichnung',
      kopf_menge: 'Menge',
      kopf_einzelpreis: 'Einzelpreis',
      kopf_betrag: 'Betrag',
      kopf_hintergrund: '#2563eb',
      kopf_textfarbe: '#ffffff',
      kopf_groesse: 12,
      zeilen_groesse: 13,
      zeilen_farbe: '#1e293b',
      zeilen_padding: 9,
      trennlinie_farbe: '#e2e8f0',
    },

    // Block: Summen
    summen: {
      sichtbar: true,
      breite: 280,
      total_farbe: '#2563eb',
      total_hintergrund: '#f8fafc',
      total_groesse: 14,
      label_farbe: '#666666',
      kleinunternehmer: false,
      kleinunternehmer_text: 'Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.',
    },

    // Block: Zahlungshinweis
    zahlung: {
      sichtbar: true,
      text: 'Bereits bezahlt über eBay',
      hintergrund: '#f0fdf4',
      textfarbe: '#16a34a',
      borderfarbe: '#86efac',
      groesse: 12,
    },

    // Block: Bankdaten
    bank: {
      sichtbar: true,
      iban: '', bic: '', name: '',
      groesse: 12,
      hintergrund: '#f8fafc',
    },

    // Block: Footer
    footer: {
      sichtbar: true,
      text: 'Vielen Dank für Ihre Bestellung bei eBay.',
      farbe: '#64748b',
      groesse: 11,
      zeige_steuernr: true,
      zeige_seite: true,
      trennlinie_farbe: '#e2e8f0',
    },

    // Block: Wasserzeichen
    wasserzeichen: {
      sichtbar: false,
      text: 'ENTWURF',
      farbe: 'rgba(0,0,0,0.06)',
      groesse: 80,
    },
  });

  // ─── Aktiver Block ────────────────────────────────────────────────────────
  let aktiverBlock = $state(null); // 'logo' | 'firmenname' | 'firmenadresse' | ...

  function waehlBlock(name, e) {
    e?.stopPropagation();
    aktiverBlock = aktiverBlock === name ? null : name;
  }

  // Klick auf Vorschau-Hintergrund → Auswahl aufheben
  function deselect() { aktiverBlock = null; }

  // ─── Logo Upload ──────────────────────────────────────────────────────────
  function handleLogoUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) { showToast('Logo max. 2 MB'); return; }
    const reader = new FileReader();
    reader.onload = (ev) => { v.logo.base64 = ev.target.result; };
    reader.readAsDataURL(file);
  }

  // ─── Speichern / Laden ────────────────────────────────────────────────────
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
    pdfLaeuft = true;
    zeigtPDF = true;
    try {
      const data = await apiCall('rechnung-vorschau', { user_id: $currentUser?.id, vorlage: v, beispiel: B });
      vorschauPDF = data.pdf_base64 || '';
    } catch(e) { showToast('Fehler: ' + e.message); zeigtPDF = false; }
    finally { pdfLaeuft = false; }
  }

  // ─── Resizable Divider ────────────────────────────────────────────────────
  let bodyEl = $state(null);
  let panelBreite = $state(340);
  let isDragging = $state(false);

  function startDrag(e) {
    isDragging = true; e.preventDefault();
    const onMove = (ev) => {
      if (!bodyEl) return;
      const rect = bodyEl.getBoundingClientRect();
      // Panel ist rechts — Breite = rechter Rand minus Mausposition
      const fromRight = rect.right - (ev.clientX ?? ev.touches?.[0]?.clientX);
      panelBreite = Math.min(Math.max(fromRight, 260), rect.width - 300);
    };
    const onUp = () => { isDragging = false; window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  }

  // ─── Block-Definitionen für Panel-Navigation ─────────────────────────────
  const BLOECKE = [
    { id: 'global',       icon: '🌐', label: 'Global' },
    { id: 'logo',         icon: '🖼', label: 'Logo' },
    { id: 'firmenname',   icon: '🏢', label: 'Firmenname' },
    { id: 'firmenadresse',icon: '📍', label: 'Adresse' },
    { id: 'kontakt',      icon: '📞', label: 'Kontakt' },
    { id: 'trennlinie',   icon: '➖', label: 'Trennlinie' },
    { id: 'rechnungsinfo',icon: '🧾', label: 'Rech.-Info' },
    { id: 'empfaenger',   icon: '👤', label: 'Empfänger' },
    { id: 'einleitung',   icon: '✉️', label: 'Einleitung' },
    { id: 'tabelle',      icon: '📋', label: 'Tabelle' },
    { id: 'summen',       icon: '💰', label: 'Summen' },
    { id: 'zahlung',      icon: '✅', label: 'Zahlung' },
    { id: 'bank',         icon: '🏦', label: 'Bankdaten' },
    { id: 'footer',       icon: '🦶', label: 'Footer' },
    { id: 'wasserzeichen',icon: '💧', label: 'Wasserz.' },
  ];

  const schriftarten = ['Arial','Helvetica','Georgia','Times New Roman','Trebuchet MS','Verdana','Tahoma','Calibri'];
  const gewichte = ['400','500','600','700','800'];
  const ausrichtungen = [{v:'left',l:'Links'},{v:'center',l:'Mitte'},{v:'right',l:'Rechts'}];
</script>

<div class="vb-container">

  <!-- ╔══ TOPBAR ══════════════════════════════════════════════════════════╗ -->
  <div class="vb-topbar">
    <div>
      <div class="vb-title">🧾 Rechnungsvorlage</div>
      <div class="vb-sub">Klicke auf einen Block in der Vorschau um ihn zu bearbeiten</div>
    </div>
    <div class="vb-actions">
      {#if zeigtPDF}
        <button class="vb-btn-ghost" onclick={() => zeigtPDF = false}>← Zurück zum Editor</button>
      {:else}
        <button class="vb-btn-ghost" onclick={pdfVorschau} disabled={pdfLaeuft}>
          {pdfLaeuft ? '⏳ Lädt…' : '🖨 PDF-Vorschau'}
        </button>
      {/if}
      <button class="vb-btn-primary" onclick={speichern} disabled={speichertLaeuft}>
        {speichertLaeuft ? 'Speichert…' : '💾 Speichern'}
      </button>
    </div>
  </div>

  <!-- ╔══ BODY ═════════════════════════════════════════════════════════════╗ -->
  <div class="vb-body" bind:this={bodyEl}>

    <!-- ── VORSCHAU (links, scrollbar) ────────────────────────────────────── -->
    <div class="vb-preview-area">
      <div class="vb-preview-scroll">

        {#if zeigtPDF && vorschauPDF}
          <!-- PDF Mode -->
          <iframe src="data:application/pdf;base64,{vorschauPDF}" title="PDF" class="pdf-iframe"></iframe>
        {:else}
          <!-- Visueller Editor -->
          <!-- svelte-ignore a11y_click_events_have_key_events -->
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div
            class="a4-page"
            style="font-family:{v.schriftart},Arial,sans-serif; padding:{v.seitenrand}px; padding-bottom:80px; background:{v.hintergrundfarbe_seite}; --a4-pad:{v.seitenrand}px;"
            onclick={deselect}
          >

            {#if v.wasserzeichen.sichtbar}
              <div class="wasserzeichen" style="font-size:{v.wasserzeichen.groesse}px;color:{v.wasserzeichen.farbe};">{v.wasserzeichen.text}</div>
            {/if}

            <!-- ── HEADER ── -->
            <div class="a4-header">

              <!-- Logo + Firmenname + Adresse (links) -->
              <div class="header-links" style="text-align:{v.logo.position === 'rechts' ? 'right' : v.logo.position === 'mitte' ? 'center' : 'left'}">

                {#if v.logo.sichtbar}
                  <!-- svelte-ignore a11y_click_events_have_key_events -->
                  <!-- svelte-ignore a11y_no_static_element_interactions -->
                  <div
                    class="editable-block"
                    class:aktiv={aktiverBlock === 'logo'}
                    onclick={(e) => waehlBlock('logo', e)}
                    style="display:inline-block; margin-bottom:8px;"
                  >
                    {#if v.logo.base64}
                      <img src={v.logo.base64} alt="Logo" style="width:{v.logo.breite}px; max-height:{v.logo.breite * 0.6}px; object-fit:contain; display:block;" />
                    {:else}
                      <div class="logo-placeholder" style="width:{v.logo.breite}px;">
                        <span>🖼 Logo</span>
                      </div>
                    {/if}
                  </div>
                {/if}

                {#if v.firmenname.sichtbar}
                  <!-- svelte-ignore a11y_click_events_have_key_events -->
                  <!-- svelte-ignore a11y_no_static_element_interactions -->
                  <div
                    class="editable-block"
                    class:aktiv={aktiverBlock === 'firmenname'}
                    onclick={(e) => waehlBlock('firmenname', e)}
                    style="
                      font-size:{v.firmenname.groesse}px;
                      color:{v.firmenname.farbe};
                      font-weight:{v.firmenname.gewicht};
                      text-align:{v.firmenname.ausrichtung};
                      margin-top:{v.firmenname.margin_top}px;
                      margin-bottom:{v.firmenname.margin_bottom}px;
                    "
                  >{v.firmenname.text || 'Mein Firmenname'}</div>
                {/if}

                {#if v.firmenadresse.sichtbar}
                  <!-- svelte-ignore a11y_click_events_have_key_events -->
                  <!-- svelte-ignore a11y_no_static_element_interactions -->
                  <div
                    class="editable-block"
                    class:aktiv={aktiverBlock === 'firmenadresse'}
                    onclick={(e) => waehlBlock('firmenadresse', e)}
                    style="font-size:{v.firmenadresse.groesse}px; color:{v.firmenadresse.farbe}; line-height:{v.firmenadresse.zeilenabstand};"
                  >
                    {#if v.firmenadresse.strasse}<div>{v.firmenadresse.strasse}</div>{/if}
                    {#if v.firmenadresse.plz || v.firmenadresse.ort}<div>{v.firmenadresse.plz} {v.firmenadresse.ort}</div>{/if}
                    {#if !v.firmenadresse.strasse && !v.firmenadresse.plz}<div style="color:#aaa;font-style:italic;">Straße, PLZ Ort</div>{/if}
                  </div>
                {/if}
              </div>

              <!-- Kontakt (rechts) -->
              {#if v.kontakt.sichtbar}
                <!-- svelte-ignore a11y_click_events_have_key_events -->
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <div
                  class="editable-block header-rechts"
                  class:aktiv={aktiverBlock === 'kontakt'}
                  onclick={(e) => waehlBlock('kontakt', e)}
                  style="font-size:{v.kontakt.groesse}px; color:{v.kontakt.farbe}; line-height:{v.kontakt.zeilenabstand}; text-align:{v.kontakt.ausrichtung};"
                >
                  {#if v.kontakt.zeige_telefon && v.kontakt.telefon}<div>Tel: {v.kontakt.telefon}</div>{/if}
                  {#if v.kontakt.zeige_email && v.kontakt.email}<div>{v.kontakt.email}</div>{/if}
                  {#if v.kontakt.zeige_website && v.kontakt.website}<div>{v.kontakt.website}</div>{/if}
                  {#if v.kontakt.zeige_steuernr && v.kontakt.steuernr}<div>Steuer-Nr.: {v.kontakt.steuernr}</div>{/if}
                  {#if v.kontakt.zeige_ust && v.kontakt.ust_idnr}<div>USt-IdNr.: {v.kontakt.ust_idnr}</div>{/if}
                  {#if !v.kontakt.telefon && !v.kontakt.email && !v.kontakt.website}
                    <div style="color:#aaa;font-style:italic;">Telefon / E-Mail</div>
                  {/if}
                </div>
              {/if}
            </div>

            <!-- ── TRENNLINIE ── -->
            {#if v.trennlinie.sichtbar}
              <!-- svelte-ignore a11y_click_events_have_key_events -->
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <div
                class="editable-block"
                class:aktiv={aktiverBlock === 'trennlinie'}
                onclick={(e) => waehlBlock('trennlinie', e)}
                style="margin-top:{v.trennlinie.margin_top}px; margin-bottom:{v.trennlinie.margin_bottom}px;"
              >
                <hr style="border:none; border-top:{v.trennlinie.staerke}px solid {v.trennlinie.farbe}; margin:0;" />
              </div>
            {/if}

            <!-- ── INFO-GRID (Empfänger + Rechnungsinfo) ── -->
            <div class="a4-infogrid">

              {#if v.empfaenger.sichtbar}
                <!-- svelte-ignore a11y_click_events_have_key_events -->
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <div
                  class="editable-block a4-box"
                  class:aktiv={aktiverBlock === 'empfaenger'}
                  onclick={(e) => waehlBlock('empfaenger', e)}
                  style="background:{v.empfaenger.hintergrund}; border-radius:{v.empfaenger.border_radius}px; padding:12px;"
                >
                  <div style="font-size:{v.empfaenger.label_groesse}px; font-weight:700; color:{v.empfaenger.label_farbe}; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:6px;">{v.empfaenger.label_text}</div>
                  <div style="font-weight:{v.empfaenger.name_gewicht}; font-size:{v.empfaenger.name_groesse}px;">{B.kaeufer_name}</div>
                  <div style="font-size:{v.empfaenger.adresse_groesse}px; color:{v.empfaenger.adresse_farbe};">{B.kaeufer_strasse}</div>
                  <div style="font-size:{v.empfaenger.adresse_groesse}px; color:{v.empfaenger.adresse_farbe};">{B.kaeufer_plz} {B.kaeufer_ort}</div>
                  <div style="font-size:{v.empfaenger.adresse_groesse}px; color:{v.empfaenger.adresse_farbe};">{B.kaeufer_land}</div>
                </div>
              {/if}

              {#if v.rechnungsinfo.sichtbar}
                <!-- svelte-ignore a11y_click_events_have_key_events -->
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <div
                  class="editable-block a4-box"
                  class:aktiv={aktiverBlock === 'rechnungsinfo'}
                  onclick={(e) => waehlBlock('rechnungsinfo', e)}
                  style="background:{v.rechnungsinfo.hintergrund}; border-radius:{v.rechnungsinfo.border_radius}px; padding:12px; text-align:{v.rechnungsinfo.ausrichtung};"
                >
                  <div style="font-size:9px; font-weight:700; color:#999; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:6px;">Rechnung</div>
                  <div style="font-size:{v.rechnungsinfo.titel_groesse}px; font-weight:{v.rechnungsinfo.titel_gewicht}; color:{v.rechnungsinfo.titel_farbe};">{v.rechnungsinfo.titel_text}</div>
                  <div style="font-size:{v.rechnungsinfo.nr_groesse}px; color:{v.rechnungsinfo.nr_farbe}; margin-top:4px;">Nr: <strong>{B.rechnung_nr}</strong></div>
                  <div style="font-size:12px; color:#666;">Datum: {B.datum}</div>
                  <div style="font-size:12px; color:#666;">Bestellung: {B.order_id}</div>
                </div>
              {/if}

            </div>

            <!-- ── EINLEITUNG ── -->
            {#if v.einleitung.sichtbar}
              <!-- svelte-ignore a11y_click_events_have_key_events -->
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <div
                class="editable-block"
                class:aktiv={aktiverBlock === 'einleitung'}
                onclick={(e) => waehlBlock('einleitung', e)}
                style="margin-bottom:18px; font-size:{v.einleitung.groesse}px; color:{v.einleitung.farbe}; background:{v.einleitung.hintergrund}; border-radius:{v.einleitung.border_radius}px; padding:10px 14px;"
              >
                {v.einleitung.text.replace('[order_id]', B.order_id).replace('[datum]', B.datum)}
              </div>
            {/if}

            <!-- ── TABELLE ── -->
            {#if v.tabelle.sichtbar}
              <!-- svelte-ignore a11y_click_events_have_key_events -->
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <div
                class="editable-block"
                class:aktiv={aktiverBlock === 'tabelle'}
                onclick={(e) => waehlBlock('tabelle', e)}
                style="margin-bottom:16px;"
              >
                <table class="a4-table">
                  <thead>
                    <tr style="background:{v.tabelle.kopf_hintergrund};">
                      {#if v.tabelle.zeige_artnr}<th style="color:{v.tabelle.kopf_textfarbe};font-size:{v.tabelle.kopf_groesse}px;width:70px;">{v.tabelle.kopf_text}</th>{/if}
                      <th style="color:{v.tabelle.kopf_textfarbe};font-size:{v.tabelle.kopf_groesse}px;">{v.tabelle.kopf_bezeichnung}</th>
                      {#if v.tabelle.zeige_menge}<th style="color:{v.tabelle.kopf_textfarbe};font-size:{v.tabelle.kopf_groesse}px;text-align:right;width:60px;">{v.tabelle.kopf_menge}</th>{/if}
                      {#if v.tabelle.zeige_einzelpreis}<th style="color:{v.tabelle.kopf_textfarbe};font-size:{v.tabelle.kopf_groesse}px;text-align:right;width:100px;">{v.tabelle.kopf_einzelpreis}</th>{/if}
                      {#if v.tabelle.zeige_betrag}<th style="color:{v.tabelle.kopf_textfarbe};font-size:{v.tabelle.kopf_groesse}px;text-align:right;width:100px;">{v.tabelle.kopf_betrag}</th>{/if}
                    </tr>
                  </thead>
                  <tbody>
                    <tr style="border-bottom:1px solid {v.tabelle.trennlinie_farbe};">
                      {#if v.tabelle.zeige_artnr}<td style="padding:{v.tabelle.zeilen_padding}px 12px;font-size:{v.tabelle.zeilen_groesse}px;color:{v.tabelle.zeilen_farbe};">{B.artikel_nr}</td>{/if}
                      <td style="padding:{v.tabelle.zeilen_padding}px 12px;font-size:{v.tabelle.zeilen_groesse}px;color:{v.tabelle.zeilen_farbe};"><strong>{B.artikel_name}</strong></td>
                      {#if v.tabelle.zeige_menge}<td style="padding:{v.tabelle.zeilen_padding}px 12px;font-size:{v.tabelle.zeilen_groesse}px;color:{v.tabelle.zeilen_farbe};text-align:right;">{B.menge}</td>{/if}
                      {#if v.tabelle.zeige_einzelpreis}<td style="padding:{v.tabelle.zeilen_padding}px 12px;font-size:{v.tabelle.zeilen_groesse}px;color:{v.tabelle.zeilen_farbe};text-align:right;">{fmt(B.einzelpreis)} EUR</td>{/if}
                      {#if v.tabelle.zeige_betrag}<td style="padding:{v.tabelle.zeilen_padding}px 12px;font-size:{v.tabelle.zeilen_groesse}px;color:{v.tabelle.zeilen_farbe};text-align:right;">{fmt(B.einzelpreis * B.menge)} EUR</td>{/if}
                    </tr>
                  </tbody>
                </table>
              </div>
            {/if}

            <!-- ── SUMMEN ── -->
            {#if v.summen.sichtbar}
              <!-- svelte-ignore a11y_click_events_have_key_events -->
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <div
                class="editable-block"
                class:aktiv={aktiverBlock === 'summen'}
                onclick={(e) => waehlBlock('summen', e)}
                style="width:{v.summen.breite}px; margin-left:auto; margin-bottom:12px;"
              >
                <table style="width:100%; border-collapse:collapse;">
                  <tbody>
                    <tr><td style="padding:7px 12px; color:{v.summen.label_farbe}; font-size:13px;">Nettobetrag</td><td style="padding:7px 12px; text-align:right; font-size:13px;">{fmt(B.netto_betrag)} EUR</td></tr>
                    {#if v.summen.kleinunternehmer}
                      <tr><td colspan="2" style="padding:7px 12px; font-size:11px; font-style:italic; color:#666;">{v.summen.kleinunternehmer_text}</td></tr>
                    {:else}
                      <tr><td style="padding:7px 12px; text-align:right; font-size:12px; color:{v.summen.label_farbe};">MwSt. {B.steuersatz}%</td><td style="padding:7px 12px; text-align:right; font-size:12px;">{fmt(B.steuer_betrag)} EUR</td></tr>
                    {/if}
                    <tr style="background:{v.summen.total_hintergrund};"><td style="padding:10px 12px; font-weight:700; font-size:{v.summen.total_groesse}px; color:{v.summen.total_farbe};">Gesamtbetrag</td><td style="padding:10px 12px; text-align:right; font-weight:700; font-size:{v.summen.total_groesse}px; color:{v.summen.total_farbe};">{fmt(B.brutto_betrag)} EUR</td></tr>
                  </tbody>
                </table>
              </div>
            {/if}

            <!-- ── ZAHLUNGSHINWEIS ── -->
            {#if v.zahlung.sichtbar}
              <!-- svelte-ignore a11y_click_events_have_key_events -->
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <div
                class="editable-block"
                class:aktiv={aktiverBlock === 'zahlung'}
                onclick={(e) => waehlBlock('zahlung', e)}
                style="display:inline-block; background:{v.zahlung.hintergrund}; color:{v.zahlung.textfarbe}; border:1px solid {v.zahlung.borderfarbe}; border-radius:6px; padding:5px 12px; font-size:{v.zahlung.groesse}px; font-weight:700; margin-bottom:12px;"
              >{v.zahlung.text}</div>
            {/if}

            <!-- ── BANKDATEN ── -->
            {#if v.bank.sichtbar && v.bank.iban}
              <!-- svelte-ignore a11y_click_events_have_key_events -->
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <div
                class="editable-block"
                class:aktiv={aktiverBlock === 'bank'}
                onclick={(e) => waehlBlock('bank', e)}
                style="background:{v.bank.hintergrund}; border-radius:6px; padding:12px; font-size:{v.bank.groesse}px; margin-bottom:12px;"
              >
                <strong>Bankverbindung:</strong> {v.bank.name ? v.bank.name + ' · ' : ''}IBAN: {v.bank.iban}{v.bank.bic ? ' · BIC: ' + v.bank.bic : ''}
              </div>
            {:else if v.bank.sichtbar}
              <!-- svelte-ignore a11y_click_events_have_key_events -->
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <div class="editable-block block-placeholder" class:aktiv={aktiverBlock === 'bank'} onclick={(e) => waehlBlock('bank', e)}>🏦 Bankdaten (IBAN eingeben)</div>
            {/if}

            <!-- ── FOOTER ── -->
            {#if v.footer.sichtbar}
              <!-- svelte-ignore a11y_click_events_have_key_events -->
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <div
                class="editable-block a4-footer"
                class:aktiv={aktiverBlock === 'footer'}
                onclick={(e) => waehlBlock('footer', e)}
                style="padding-top:12px; border-top:1px solid {v.footer.trennlinie_farbe}; font-size:{v.footer.groesse}px; color:{v.footer.farbe}; text-align:center;"
              >
                {#if v.footer.text}<div>{v.footer.text}</div>{/if}
                {#if v.footer.zeige_steuernr && v.kontakt.steuernr}<div>Steuer-Nr.: {v.kontakt.steuernr}{v.kontakt.ust_idnr ? ' · USt-IdNr.: ' + v.kontakt.ust_idnr : ''}</div>{/if}
                {#if v.footer.zeige_seite}<div style="margin-top:4px; opacity:0.6;">Seite 1</div>{/if}
              </div>
            {/if}

          </div><!-- /a4-page -->
        {/if}

      </div><!-- /vb-preview-scroll -->
    </div><!-- /vb-preview-area -->

    <!-- ── DIVIDER ─────────────────────────────────────────────────────────── -->
    <div class="vb-divider" class:dragging={isDragging} onmousedown={startDrag} role="separator" aria-label="Breite anpassen"></div>

    <!-- ── EINSTELLUNGS-PANEL (rechts) ────────────────────────────────────── -->
    <div class="vb-panel" style="width:{panelBreite}px;">

      <!-- Block-Navigation (horizontales Scrollen) -->
      <div class="panel-nav">
        {#each BLOECKE as b}
          <button
            class="nav-btn"
            class:aktiv={aktiverBlock === b.id}
            onclick={() => aktiverBlock = b.id}
          >{b.icon}<span>{b.label}</span></button>
        {/each}
      </div>

      <!-- Panel-Inhalt -->
      <div class="panel-content">

        {#if !aktiverBlock}
          <div class="panel-hint">
            <div style="font-size:2rem;">👆</div>
            <div>Klicke auf einen Block in der Vorschau<br/>oder wähle oben eine Kategorie</div>
          </div>
        {/if}

        <!-- ═══ GLOBAL ════════════════════════════════════════════════════ -->
        {#if aktiverBlock === 'global'}
          <div class="panel-section">
            <div class="ps-title">🌐 Globale Einstellungen</div>
            <div class="ps-row">
              <label>Schriftart</label>
              <select bind:value={v.schriftart}>
                {#each schriftarten as s}<option value={s}>{s}</option>{/each}
              </select>
            </div>
            <div class="ps-row">
              <label>Seitenrand (px)</label>
              <input type="number" min="10" max="60" bind:value={v.seitenrand} />
            </div>
            <div class="ps-row">
              <label>Seitenhintergrund</label>
              <div class="color-row"><input type="color" bind:value={v.hintergrundfarbe_seite} class="clr" /><input type="text" bind:value={v.hintergrundfarbe_seite} /></div>
            </div>
            <div class="ps-divider"></div>
            <div class="ps-label">Schnellthemen</div>
            <div class="themen-grid">
              {#each [
                {n:'Blau',  c:'#2563eb'}, {n:'Grün',  c:'#16a34a'},
                {n:'Rot',   c:'#dc2626'}, {n:'Lila',  c:'#7c3aed'},
                {n:'Grau',  c:'#374151'}, {n:'Orange',c:'#ea580c'},
              ] as t}
                <button class="thema-btn" style="--tc:{t.c}" onclick={() => {
                  v.firmenname.farbe = t.c;
                  v.trennlinie.farbe = t.c;
                  v.rechnungsinfo.titel_farbe = t.c;
                  v.tabelle.kopf_hintergrund = t.c;
                  v.summen.total_farbe = t.c;
                }}>
                  <span class="thema-dot" style="background:{t.c}"></span>{t.n}
                </button>
              {/each}
            </div>
          </div>
        {/if}

        <!-- ═══ LOGO ══════════════════════════════════════════════════════ -->
        {#if aktiverBlock === 'logo'}
          <div class="panel-section">
            <div class="ps-title">🖼 Logo</div>
            <label class="ps-toggle"><input type="checkbox" bind:checked={v.logo.sichtbar} /> Sichtbar</label>
            {#if v.logo.sichtbar}
              {#if v.logo.base64}
                <div class="logo-preview-small">
                  <img src={v.logo.base64} alt="Logo" style="max-height:50px;max-width:140px;object-fit:contain;" />
                  <button class="vb-btn-danger vb-btn-sm" onclick={() => v.logo.base64 = ''}>Entfernen</button>
                </div>
              {:else}
                <label class="upload-zone">
                  <input type="file" accept="image/*" onchange={handleLogoUpload} style="display:none" />
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                  PNG / SVG / JPG — max. 2 MB
                </label>
              {/if}
              <div class="ps-row">
                <label>Position</label>
                <div class="btn-group">
                  {#each [{v:'links',l:'Links'},{v:'mitte',l:'Mitte'},{v:'rechts',l:'Rechts'}] as o}
                    <button class="bg-btn" class:aktiv={v.logo.position === o.v} onclick={() => v.logo.position = o.v}>{o.l}</button>
                  {/each}
                </div>
              </div>
              <div class="ps-row"><label>Breite (px)</label><input type="number" min="40" max="400" bind:value={v.logo.breite} /></div>
            {/if}
          </div>
        {/if}

        <!-- ═══ FIRMENNAME ═════════════════════════════════════════════════ -->
        {#if aktiverBlock === 'firmenname'}
          <div class="panel-section">
            <div class="ps-title">🏢 Firmenname</div>
            <label class="ps-toggle"><input type="checkbox" bind:checked={v.firmenname.sichtbar} /> Sichtbar</label>
            {#if v.firmenname.sichtbar}
              <div class="ps-row"><label>Text</label><input bind:value={v.firmenname.text} placeholder="Meine Firma GmbH" /></div>
              <div class="ps-row2">
                <div class="ps-row"><label>Größe (px)</label><input type="number" min="10" max="48" bind:value={v.firmenname.groesse} /></div>
                <div class="ps-row"><label>Gewicht</label><select bind:value={v.firmenname.gewicht}>{#each gewichte as g}<option value={g}>{g}</option>{/each}</select></div>
              </div>
              <div class="ps-row"><label>Farbe</label><div class="color-row"><input type="color" bind:value={v.firmenname.farbe} class="clr" /><input type="text" bind:value={v.firmenname.farbe} /></div></div>
              <div class="ps-row">
                <label>Ausrichtung</label>
                <div class="btn-group">
                  {#each ausrichtungen as a}<button class="bg-btn" class:aktiv={v.firmenname.ausrichtung === a.v} onclick={() => v.firmenname.ausrichtung = a.v}>{a.l}</button>{/each}
                </div>
              </div>
              <div class="ps-row2">
                <div class="ps-row"><label>Abstand oben</label><input type="number" min="0" max="40" bind:value={v.firmenname.margin_top} /></div>
                <div class="ps-row"><label>Abstand unten</label><input type="number" min="0" max="40" bind:value={v.firmenname.margin_bottom} /></div>
              </div>
            {/if}
          </div>
        {/if}

        <!-- ═══ FIRMENADRESSE ══════════════════════════════════════════════ -->
        {#if aktiverBlock === 'firmenadresse'}
          <div class="panel-section">
            <div class="ps-title">📍 Firmenadresse</div>
            <label class="ps-toggle"><input type="checkbox" bind:checked={v.firmenadresse.sichtbar} /> Sichtbar</label>
            {#if v.firmenadresse.sichtbar}
              <div class="ps-row"><label>Straße & Nr.</label><input bind:value={v.firmenadresse.strasse} placeholder="Musterstr. 1" /></div>
              <div class="ps-row2">
                <div class="ps-row"><label>PLZ</label><input bind:value={v.firmenadresse.plz} placeholder="12345" /></div>
                <div class="ps-row"><label>Ort</label><input bind:value={v.firmenadresse.ort} placeholder="Berlin" /></div>
              </div>
              <div class="ps-row2">
                <div class="ps-row"><label>Größe (px)</label><input type="number" min="8" max="16" bind:value={v.firmenadresse.groesse} /></div>
                <div class="ps-row"><label>Zeilenabstand</label><input type="number" min="1" max="3" step="0.1" bind:value={v.firmenadresse.zeilenabstand} /></div>
              </div>
              <div class="ps-row"><label>Farbe</label><div class="color-row"><input type="color" bind:value={v.firmenadresse.farbe} class="clr" /><input type="text" bind:value={v.firmenadresse.farbe} /></div></div>
            {/if}
          </div>
        {/if}

        <!-- ═══ KONTAKT ════════════════════════════════════════════════════ -->
        {#if aktiverBlock === 'kontakt'}
          <div class="panel-section">
            <div class="ps-title">📞 Kontaktdaten</div>
            <label class="ps-toggle"><input type="checkbox" bind:checked={v.kontakt.sichtbar} /> Sichtbar</label>
            {#if v.kontakt.sichtbar}
              <div class="ps-row"><label>Telefon</label><input bind:value={v.kontakt.telefon} placeholder="+49 221 …" /></div>
              <div class="ps-row"><label>E-Mail</label><input bind:value={v.kontakt.email} placeholder="info@firma.de" /></div>
              <div class="ps-row"><label>Website</label><input bind:value={v.kontakt.website} placeholder="www.firma.de" /></div>
              <div class="ps-row"><label>Steuer-Nr.</label><input bind:value={v.kontakt.steuernr} placeholder="342/5058/2211" /></div>
              <div class="ps-row"><label>USt-IdNr.</label><input bind:value={v.kontakt.ust_idnr} placeholder="DE123456789" /></div>
              <div class="ps-divider"></div>
              <div class="ps-label">Anzeigen</div>
              <label class="ps-toggle"><input type="checkbox" bind:checked={v.kontakt.zeige_telefon} /> Telefon</label>
              <label class="ps-toggle"><input type="checkbox" bind:checked={v.kontakt.zeige_email} /> E-Mail</label>
              <label class="ps-toggle"><input type="checkbox" bind:checked={v.kontakt.zeige_website} /> Website</label>
              <label class="ps-toggle"><input type="checkbox" bind:checked={v.kontakt.zeige_steuernr} /> Steuer-Nr.</label>
              <label class="ps-toggle"><input type="checkbox" bind:checked={v.kontakt.zeige_ust} /> USt-IdNr.</label>
              <div class="ps-divider"></div>
              <div class="ps-row2">
                <div class="ps-row"><label>Größe (px)</label><input type="number" min="8" max="16" bind:value={v.kontakt.groesse} /></div>
                <div class="ps-row"><label>Zeilenabstand</label><input type="number" min="1" max="3" step="0.1" bind:value={v.kontakt.zeilenabstand} /></div>
              </div>
              <div class="ps-row"><label>Farbe</label><div class="color-row"><input type="color" bind:value={v.kontakt.farbe} class="clr" /><input type="text" bind:value={v.kontakt.farbe} /></div></div>
              <div class="ps-row">
                <label>Ausrichtung</label>
                <div class="btn-group">
                  {#each ausrichtungen as a}<button class="bg-btn" class:aktiv={v.kontakt.ausrichtung === a.v} onclick={() => v.kontakt.ausrichtung = a.v}>{a.l}</button>{/each}
                </div>
              </div>
            {/if}
          </div>
        {/if}

        <!-- ═══ TRENNLINIE ═════════════════════════════════════════════════ -->
        {#if aktiverBlock === 'trennlinie'}
          <div class="panel-section">
            <div class="ps-title">➖ Trennlinie</div>
            <label class="ps-toggle"><input type="checkbox" bind:checked={v.trennlinie.sichtbar} /> Sichtbar</label>
            {#if v.trennlinie.sichtbar}
              <div class="ps-row"><label>Farbe</label><div class="color-row"><input type="color" bind:value={v.trennlinie.farbe} class="clr" /><input type="text" bind:value={v.trennlinie.farbe} /></div></div>
              <div class="ps-row2">
                <div class="ps-row"><label>Stärke (px)</label><input type="number" min="1" max="10" bind:value={v.trennlinie.staerke} /></div>
                <div class="ps-row"><label>Abstand oben</label><input type="number" min="0" max="40" bind:value={v.trennlinie.margin_top} /></div>
              </div>
              <div class="ps-row"><label>Abstand unten</label><input type="number" min="0" max="40" bind:value={v.trennlinie.margin_bottom} /></div>
            {/if}
          </div>
        {/if}

        <!-- ═══ RECHNUNGSINFO ══════════════════════════════════════════════ -->
        {#if aktiverBlock === 'rechnungsinfo'}
          <div class="panel-section">
            <div class="ps-title">🧾 Rechnungs-Info Box</div>
            <label class="ps-toggle"><input type="checkbox" bind:checked={v.rechnungsinfo.sichtbar} /> Sichtbar</label>
            {#if v.rechnungsinfo.sichtbar}
              <div class="ps-row"><label>Titel-Text</label><input bind:value={v.rechnungsinfo.titel_text} placeholder="Rechnung" /></div>
              <div class="ps-row2">
                <div class="ps-row"><label>Titel-Größe</label><input type="number" min="12" max="40" bind:value={v.rechnungsinfo.titel_groesse} /></div>
                <div class="ps-row"><label>Gewicht</label><select bind:value={v.rechnungsinfo.titel_gewicht}>{#each gewichte as g}<option value={g}>{g}</option>{/each}</select></div>
              </div>
              <div class="ps-row"><label>Titel-Farbe</label><div class="color-row"><input type="color" bind:value={v.rechnungsinfo.titel_farbe} class="clr" /><input type="text" bind:value={v.rechnungsinfo.titel_farbe} /></div></div>
              <div class="ps-row"><label>Text-Farbe</label><div class="color-row"><input type="color" bind:value={v.rechnungsinfo.nr_farbe} class="clr" /><input type="text" bind:value={v.rechnungsinfo.nr_farbe} /></div></div>
              <div class="ps-row"><label>Hintergrund</label><div class="color-row"><input type="color" bind:value={v.rechnungsinfo.hintergrund} class="clr" /><input type="text" bind:value={v.rechnungsinfo.hintergrund} /></div></div>
              <div class="ps-row">
                <label>Ausrichtung</label>
                <div class="btn-group">
                  {#each ausrichtungen as a}<button class="bg-btn" class:aktiv={v.rechnungsinfo.ausrichtung === a.v} onclick={() => v.rechnungsinfo.ausrichtung = a.v}>{a.l}</button>{/each}
                </div>
              </div>
              <div class="ps-row"><label>Border-Radius</label><input type="number" min="0" max="20" bind:value={v.rechnungsinfo.border_radius} /></div>
            {/if}
          </div>
        {/if}

        <!-- ═══ EMPFÄNGER ══════════════════════════════════════════════════ -->
        {#if aktiverBlock === 'empfaenger'}
          <div class="panel-section">
            <div class="ps-title">👤 Empfänger-Block</div>
            <label class="ps-toggle"><input type="checkbox" bind:checked={v.empfaenger.sichtbar} /> Sichtbar</label>
            {#if v.empfaenger.sichtbar}
              <div class="ps-row"><label>Label-Text</label><input bind:value={v.empfaenger.label_text} /></div>
              <div class="ps-row2">
                <div class="ps-row"><label>Label-Größe</label><input type="number" min="7" max="14" bind:value={v.empfaenger.label_groesse} /></div>
                <div class="ps-row"><label>Label-Farbe</label><div class="color-row"><input type="color" bind:value={v.empfaenger.label_farbe} class="clr" /></div></div>
              </div>
              <div class="ps-row2">
                <div class="ps-row"><label>Name-Größe</label><input type="number" min="10" max="20" bind:value={v.empfaenger.name_groesse} /></div>
                <div class="ps-row"><label>Name-Gewicht</label><select bind:value={v.empfaenger.name_gewicht}>{#each gewichte as g}<option value={g}>{g}</option>{/each}</select></div>
              </div>
              <div class="ps-row2">
                <div class="ps-row"><label>Adress-Größe</label><input type="number" min="8" max="16" bind:value={v.empfaenger.adresse_groesse} /></div>
                <div class="ps-row"><label>Adress-Farbe</label><div class="color-row"><input type="color" bind:value={v.empfaenger.adresse_farbe} class="clr" /></div></div>
              </div>
              <div class="ps-row"><label>Hintergrund</label><div class="color-row"><input type="color" bind:value={v.empfaenger.hintergrund} class="clr" /><input type="text" bind:value={v.empfaenger.hintergrund} /></div></div>
              <div class="ps-row"><label>Border-Radius</label><input type="number" min="0" max="20" bind:value={v.empfaenger.border_radius} /></div>
            {/if}
          </div>
        {/if}

        <!-- ═══ EINLEITUNG ═════════════════════════════════════════════════ -->
        {#if aktiverBlock === 'einleitung'}
          <div class="panel-section">
            <div class="ps-title">✉️ Einleitungstext</div>
            <label class="ps-toggle"><input type="checkbox" bind:checked={v.einleitung.sichtbar} /> Sichtbar</label>
            {#if v.einleitung.sichtbar}
              <div class="ps-row"><label>Text</label><textarea bind:value={v.einleitung.text} rows="3" placeholder="Ihre Bestellung Nr. [order_id] vom [datum]."></textarea><span class="hint">Platzhalter: [order_id], [datum]</span></div>
              <div class="ps-row2">
                <div class="ps-row"><label>Größe (px)</label><input type="number" min="10" max="18" bind:value={v.einleitung.groesse} /></div>
                <div class="ps-row"><label>Border-Radius</label><input type="number" min="0" max="20" bind:value={v.einleitung.border_radius} /></div>
              </div>
              <div class="ps-row"><label>Textfarbe</label><div class="color-row"><input type="color" bind:value={v.einleitung.farbe} class="clr" /><input type="text" bind:value={v.einleitung.farbe} /></div></div>
              <div class="ps-row"><label>Hintergrund</label><div class="color-row"><input type="color" bind:value={v.einleitung.hintergrund} class="clr" /><input type="text" bind:value={v.einleitung.hintergrund} /></div></div>
            {/if}
          </div>
        {/if}

        <!-- ═══ TABELLE ════════════════════════════════════════════════════ -->
        {#if aktiverBlock === 'tabelle'}
          <div class="panel-section">
            <div class="ps-title">📋 Positionstabelle</div>
            <label class="ps-toggle"><input type="checkbox" bind:checked={v.tabelle.sichtbar} /> Sichtbar</label>
            {#if v.tabelle.sichtbar}
              <div class="ps-label">Spalten anzeigen</div>
              <label class="ps-toggle"><input type="checkbox" bind:checked={v.tabelle.zeige_artnr} /> Art.-Nr.</label>
              <label class="ps-toggle"><input type="checkbox" bind:checked={v.tabelle.zeige_menge} /> Menge</label>
              <label class="ps-toggle"><input type="checkbox" bind:checked={v.tabelle.zeige_einzelpreis} /> Einzelpreis</label>
              <label class="ps-toggle"><input type="checkbox" bind:checked={v.tabelle.zeige_betrag} /> Betrag</label>
              <div class="ps-divider"></div>
              <div class="ps-label">Kopfzeilen-Texte</div>
              <div class="ps-row"><label>Art.-Nr.</label><input bind:value={v.tabelle.kopf_text} /></div>
              <div class="ps-row"><label>Bezeichnung</label><input bind:value={v.tabelle.kopf_bezeichnung} /></div>
              <div class="ps-row2">
                <div class="ps-row"><label>Menge</label><input bind:value={v.tabelle.kopf_menge} /></div>
                <div class="ps-row"><label>Einzelpreis</label><input bind:value={v.tabelle.kopf_einzelpreis} /></div>
              </div>
              <div class="ps-row"><label>Betrag</label><input bind:value={v.tabelle.kopf_betrag} /></div>
              <div class="ps-divider"></div>
              <div class="ps-label">Kopfzeilen-Style</div>
              <div class="ps-row"><label>Hintergrund</label><div class="color-row"><input type="color" bind:value={v.tabelle.kopf_hintergrund} class="clr" /><input type="text" bind:value={v.tabelle.kopf_hintergrund} /></div></div>
              <div class="ps-row"><label>Textfarbe</label><div class="color-row"><input type="color" bind:value={v.tabelle.kopf_textfarbe} class="clr" /><input type="text" bind:value={v.tabelle.kopf_textfarbe} /></div></div>
              <div class="ps-row2">
                <div class="ps-row"><label>Kopf-Größe</label><input type="number" min="9" max="16" bind:value={v.tabelle.kopf_groesse} /></div>
                <div class="ps-row"><label>Zeilen-Größe</label><input type="number" min="9" max="16" bind:value={v.tabelle.zeilen_groesse} /></div>
              </div>
              <div class="ps-row"><label>Zeilen-Farbe</label><div class="color-row"><input type="color" bind:value={v.tabelle.zeilen_farbe} class="clr" /><input type="text" bind:value={v.tabelle.zeilen_farbe} /></div></div>
              <div class="ps-row"><label>Trennlinie-Farbe</label><div class="color-row"><input type="color" bind:value={v.tabelle.trennlinie_farbe} class="clr" /><input type="text" bind:value={v.tabelle.trennlinie_farbe} /></div></div>
            {/if}
          </div>
        {/if}

        <!-- ═══ SUMMEN ═════════════════════════════════════════════════════ -->
        {#if aktiverBlock === 'summen'}
          <div class="panel-section">
            <div class="ps-title">💰 Summen-Block</div>
            <label class="ps-toggle"><input type="checkbox" bind:checked={v.summen.sichtbar} /> Sichtbar</label>
            {#if v.summen.sichtbar}
              <div class="ps-row"><label>Breite (px)</label><input type="number" min="160" max="450" bind:value={v.summen.breite} /></div>
              <div class="ps-row"><label>Gesamt-Farbe</label><div class="color-row"><input type="color" bind:value={v.summen.total_farbe} class="clr" /><input type="text" bind:value={v.summen.total_farbe} /></div></div>
              <div class="ps-row"><label>Gesamt-Hintergrund</label><div class="color-row"><input type="color" bind:value={v.summen.total_hintergrund} class="clr" /><input type="text" bind:value={v.summen.total_hintergrund} /></div></div>
              <div class="ps-row2">
                <div class="ps-row"><label>Gesamt-Größe</label><input type="number" min="11" max="20" bind:value={v.summen.total_groesse} /></div>
                <div class="ps-row"><label>Label-Farbe</label><div class="color-row"><input type="color" bind:value={v.summen.label_farbe} class="clr" /></div></div>
              </div>
              <div class="ps-divider"></div>
              <label class="ps-toggle"><input type="checkbox" bind:checked={v.summen.kleinunternehmer} /> Kleinunternehmer (§ 19 UStG)</label>
              {#if v.summen.kleinunternehmer}
                <div class="ps-row"><label>Hinweistext</label><textarea bind:value={v.summen.kleinunternehmer_text} rows="2"></textarea></div>
              {/if}
            {/if}
          </div>
        {/if}

        <!-- ═══ ZAHLUNG ════════════════════════════════════════════════════ -->
        {#if aktiverBlock === 'zahlung'}
          <div class="panel-section">
            <div class="ps-title">✅ Zahlungshinweis</div>
            <label class="ps-toggle"><input type="checkbox" bind:checked={v.zahlung.sichtbar} /> Sichtbar</label>
            {#if v.zahlung.sichtbar}
              <div class="ps-row"><label>Text</label><input bind:value={v.zahlung.text} /></div>
              <div class="ps-row"><label>Textfarbe</label><div class="color-row"><input type="color" bind:value={v.zahlung.textfarbe} class="clr" /><input type="text" bind:value={v.zahlung.textfarbe} /></div></div>
              <div class="ps-row"><label>Hintergrund</label><div class="color-row"><input type="color" bind:value={v.zahlung.hintergrund} class="clr" /><input type="text" bind:value={v.zahlung.hintergrund} /></div></div>
              <div class="ps-row"><label>Rahmen-Farbe</label><div class="color-row"><input type="color" bind:value={v.zahlung.borderfarbe} class="clr" /><input type="text" bind:value={v.zahlung.borderfarbe} /></div></div>
              <div class="ps-row"><label>Schriftgröße</label><input type="number" min="10" max="18" bind:value={v.zahlung.groesse} /></div>
            {/if}
          </div>
        {/if}

        <!-- ═══ BANK ═══════════════════════════════════════════════════════ -->
        {#if aktiverBlock === 'bank'}
          <div class="panel-section">
            <div class="ps-title">🏦 Bankdaten</div>
            <label class="ps-toggle"><input type="checkbox" bind:checked={v.bank.sichtbar} /> Sichtbar</label>
            {#if v.bank.sichtbar}
              <div class="ps-row"><label>IBAN</label><input bind:value={v.bank.iban} placeholder="DE12 3456 7890 …" /></div>
              <div class="ps-row"><label>BIC</label><input bind:value={v.bank.bic} placeholder="COBADEFFXXX" /></div>
              <div class="ps-row"><label>Bankname</label><input bind:value={v.bank.name} placeholder="Commerzbank" /></div>
              <div class="ps-row"><label>Hintergrund</label><div class="color-row"><input type="color" bind:value={v.bank.hintergrund} class="clr" /><input type="text" bind:value={v.bank.hintergrund} /></div></div>
              <div class="ps-row"><label>Schriftgröße</label><input type="number" min="9" max="16" bind:value={v.bank.groesse} /></div>
            {/if}
          </div>
        {/if}

        <!-- ═══ FOOTER ═════════════════════════════════════════════════════ -->
        {#if aktiverBlock === 'footer'}
          <div class="panel-section">
            <div class="ps-title">🦶 Footer</div>
            <label class="ps-toggle"><input type="checkbox" bind:checked={v.footer.sichtbar} /> Sichtbar</label>
            {#if v.footer.sichtbar}
              <div class="ps-row"><label>Text</label><textarea bind:value={v.footer.text} rows="2" placeholder="Vielen Dank …"></textarea></div>
              <div class="ps-row"><label>Textfarbe</label><div class="color-row"><input type="color" bind:value={v.footer.farbe} class="clr" /><input type="text" bind:value={v.footer.farbe} /></div></div>
              <div class="ps-row"><label>Trennlinie-Farbe</label><div class="color-row"><input type="color" bind:value={v.footer.trennlinie_farbe} class="clr" /><input type="text" bind:value={v.footer.trennlinie_farbe} /></div></div>
              <div class="ps-row"><label>Schriftgröße</label><input type="number" min="8" max="14" bind:value={v.footer.groesse} /></div>
              <label class="ps-toggle"><input type="checkbox" bind:checked={v.footer.zeige_steuernr} /> Steuer-Nr. anzeigen</label>
              <label class="ps-toggle"><input type="checkbox" bind:checked={v.footer.zeige_seite} /> Seitennummer</label>
            {/if}
          </div>
        {/if}

        <!-- ═══ WASSERZEICHEN ══════════════════════════════════════════════ -->
        {#if aktiverBlock === 'wasserzeichen'}
          <div class="panel-section">
            <div class="ps-title">💧 Wasserzeichen</div>
            <label class="ps-toggle"><input type="checkbox" bind:checked={v.wasserzeichen.sichtbar} /> Sichtbar</label>
            {#if v.wasserzeichen.sichtbar}
              <div class="ps-row"><label>Text</label><input bind:value={v.wasserzeichen.text} placeholder="ENTWURF" /></div>
              <div class="ps-row2">
                <div class="ps-row"><label>Größe (px)</label><input type="number" min="30" max="150" bind:value={v.wasserzeichen.groesse} /></div>
              </div>
              <div class="ps-row"><label>Farbe</label><div class="color-row"><input type="color" bind:value={v.wasserzeichen.farbe} class="clr" /></div></div>
            {/if}
          </div>
        {/if}

      </div><!-- /panel-content -->
    </div><!-- /vb-panel -->

  </div><!-- /vb-body -->
</div><!-- /vb-container -->

<style>
  .vb-container { display:flex; flex-direction:column; height:100%; width:100%; background:var(--bg); overflow:hidden; }

  /* Topbar */
  .vb-topbar {
    display:flex; align-items:center; justify-content:space-between;
    padding:10px 20px; background:var(--surface); border-bottom:1px solid var(--border);
    flex-shrink:0; gap:10px; flex-wrap:wrap;
  }
  .vb-title { font-size:1rem; font-weight:700; color:var(--text); }
  .vb-sub   { font-size:0.74rem; color:var(--text2); }
  .vb-actions { display:flex; gap:8px; align-items:center; }
  .vb-btn-primary { background:var(--primary); color:#fff; border:none; padding:7px 14px; border-radius:8px; font-size:0.83rem; cursor:pointer; font-family:inherit; transition:filter 0.15s; }
  .vb-btn-primary:hover:not(:disabled) { filter:brightness(1.1); }
  .vb-btn-primary:disabled { opacity:0.6; cursor:not-allowed; }
  .vb-btn-ghost { background:transparent; border:1px solid var(--border); color:var(--text2); padding:7px 12px; border-radius:8px; font-size:0.83rem; cursor:pointer; font-family:inherit; transition:all 0.15s; }
  .vb-btn-ghost:hover:not(:disabled) { border-color:var(--primary); color:var(--primary); }
  .vb-btn-ghost:disabled { opacity:0.6; cursor:not-allowed; }
  .vb-btn-danger { background:#ef4444; color:#fff; border:none; padding:5px 10px; border-radius:6px; font-size:0.78rem; cursor:pointer; font-family:inherit; }
  .vb-btn-sm { padding:4px 9px; font-size:0.75rem; }

  /* Body */
  .vb-body { display:flex; flex:1; overflow:hidden; min-height:0; }

  /* Vorschau-Bereich (links) */
  .vb-preview-area { flex:1; overflow:hidden; display:flex; flex-direction:column; background:#cbd5e1; min-width:0; }
  .vb-preview-scroll { flex:1; overflow:auto; padding:24px; display:flex; justify-content:center; align-items:flex-start; }

  /* A4 Seite */
  .a4-page {
    width: 794px;
    min-height: 1123px;
    flex-shrink: 0;
    background: white;
    box-shadow: 0 4px 32px rgba(0,0,0,0.25);
    border-radius: 2px;
    position: relative;
    box-sizing: border-box;
    cursor: default;
    padding-bottom: 80px; /* Platz für absolut positionierten Footer */
  }

  /* Footer immer am unteren Rand der A4-Seite */
  .a4-footer {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    padding-left: var(--a4-pad, 32px);
    padding-right: var(--a4-pad, 32px);
    margin: 0;
  }

  /* Klickbare Blöcke */
  .editable-block {
    position: relative;
    border-radius: 4px;
    transition: outline 0.1s;
    cursor: pointer;
    outline: 2px solid transparent;
  }
  .editable-block:hover { outline: 2px dashed #94a3b8; }
  .editable-block.aktiv { outline: 2px solid var(--primary, #2563eb) !important; background-color: rgba(37,99,235,0.04); }

  /* Header Layout */
  .a4-header { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0; }
  .header-links { flex:1; }
  .header-rechts { flex-shrink:0; margin-left:20px; }

  /* Info-Grid */
  .a4-infogrid { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:18px; }
  .a4-box { min-height:80px; }

  /* Tabelle */
  .a4-table { width:100%; border-collapse:collapse; }
  .a4-table thead th { padding:9px 12px; text-align:left; }
  .a4-table tbody td { }

  /* Logo Placeholder */
  .logo-placeholder {
    height:50px; background:#f1f5f9; border:2px dashed #cbd5e1;
    border-radius:6px; display:flex; align-items:center; justify-content:center;
    font-size:0.8rem; color:#94a3b8;
  }

  /* Block-Placeholder */
  .block-placeholder {
    padding:10px 14px; background:#f8fafc; border:2px dashed #cbd5e1;
    border-radius:6px; font-size:0.82rem; color:#94a3b8;
    margin-bottom:10px;
  }

  /* Wasserzeichen */
  .wasserzeichen {
    position:absolute; top:50%; left:50%;
    transform:translate(-50%,-50%) rotate(-35deg);
    font-weight:900; pointer-events:none; z-index:0; white-space:nowrap;
  }

  /* PDF iframe */
  .pdf-iframe { width:794px; height:1123px; flex-shrink:0; background:white; border:none; border-radius:2px; box-shadow:0 4px 24px rgba(0,0,0,0.3); }

  /* Divider */
  .vb-divider {
    width:4px; flex-shrink:0; background:var(--border); cursor:col-resize;
    transition:background 0.15s, width 0.1s;
    display:flex; align-items:center; justify-content:center;
  }
  .vb-divider::after { content:''; width:2px; height:32px; background:var(--text3); border-radius:2px; opacity:0.5; }
  .vb-divider:hover, .vb-divider.dragging { background:var(--primary); width:5px; }
  .vb-divider:hover::after, .vb-divider.dragging::after { background:white; opacity:1; }

  /* Panel (rechts) */
  .vb-panel {
    flex-shrink:0; background:var(--surface);
    display:flex; flex-direction:column; overflow:hidden;
    border-left:1px solid var(--border);
  }

  /* Panel Navigation */
  .panel-nav {
    display:flex; gap:1px; padding:6px 6px 0;
    overflow-x:auto; flex-shrink:0;
    border-bottom:1px solid var(--border);
    scrollbar-width:thin;
    scrollbar-color: var(--border) transparent;
  }
  .panel-nav::-webkit-scrollbar { height:3px; }
  .panel-nav::-webkit-scrollbar-thumb { background:var(--border); border-radius:2px; }
  .nav-btn {
    display:flex; flex-direction:column; align-items:center; gap:1px;
    padding:4px 5px; border:none; border-radius:6px 6px 0 0;
    background:transparent; color:var(--text2); cursor:pointer;
    font-size:0.6rem; white-space:nowrap; flex-shrink:0;
    font-family:inherit; transition:all 0.15s;
    border-bottom:2px solid transparent; min-width:38px;
  }
  .nav-btn span { font-size:0.58rem; }
  .nav-btn:hover { background:var(--surface2); color:var(--text); }
  .nav-btn.aktiv { color:var(--primary); border-bottom-color:var(--primary); background:var(--surface2); font-weight:700; }

  /* Panel Content */
  .panel-content { flex:1; overflow-y:auto; padding:14px; display:flex; flex-direction:column; gap:0; }

  .panel-hint {
    flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center;
    gap:12px; color:var(--text3); font-size:0.82rem; text-align:center; padding:20px;
  }

  /* Panel Section */
  .panel-section { display:flex; flex-direction:column; gap:10px; }
  .ps-title { font-size:0.88rem; font-weight:700; color:var(--text); margin-bottom:2px; }
  .ps-label { font-size:0.68rem; font-weight:700; color:var(--text3); text-transform:uppercase; letter-spacing:0.07em; margin-top:4px; }
  .ps-divider { height:1px; background:var(--border); margin:4px 0; }
  .ps-row { display:flex; flex-direction:column; gap:3px; }
  .ps-row label { font-size:0.71rem; color:var(--text2); font-weight:500; }
  .ps-row input, .ps-row select, .ps-row textarea {
    background:var(--bg); border:1px solid var(--border); color:var(--text);
    padding:6px 9px; border-radius:6px; font-size:0.81rem; outline:none;
    transition:border-color 0.15s; font-family:inherit; width:100%; box-sizing:border-box;
  }
  .ps-row input:focus, .ps-row select:focus, .ps-row textarea:focus { border-color:var(--primary); }
  .ps-row textarea { resize:vertical; min-height:48px; }
  .ps-row2 { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
  .ps-toggle { display:flex; align-items:center; gap:7px; font-size:0.81rem; color:var(--text); cursor:pointer; }
  .ps-toggle input[type="checkbox"] { width:14px; height:14px; accent-color:var(--primary); flex-shrink:0; cursor:pointer; }

  /* Color row */
  .color-row { display:flex; gap:5px; align-items:center; }
  .color-row input[type="text"] { flex:1; min-width:0; }
  .clr { width:32px; height:28px; padding:2px; border-radius:5px; border:1px solid var(--border); cursor:pointer; background:var(--bg); flex-shrink:0; }

  /* Button group (links/mitte/rechts) */
  .btn-group { display:flex; gap:3px; }
  .bg-btn {
    flex:1; padding:5px; border:1px solid var(--border); border-radius:6px;
    background:var(--bg); color:var(--text2); font-size:0.75rem;
    cursor:pointer; transition:all 0.15s; font-family:inherit;
  }
  .bg-btn:hover { border-color:var(--primary); color:var(--primary); }
  .bg-btn.aktiv { background:var(--primary); color:#fff; border-color:var(--primary); font-weight:600; }

  /* Themen */
  .themen-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:5px; }
  .thema-btn {
    display:flex; align-items:center; gap:5px; padding:5px 7px;
    background:var(--bg); border:2px solid transparent; border-radius:7px;
    font-size:0.73rem; color:var(--text); cursor:pointer; transition:all 0.15s;
    font-family:inherit;
  }
  .thema-btn:hover { border-color:var(--tc); background:var(--surface2); }
  .thema-dot { width:11px; height:11px; border-radius:50%; flex-shrink:0; }

  /* Upload zone */
  .upload-zone {
    display:flex; flex-direction:column; align-items:center; gap:6px;
    padding:12px; border:2px dashed var(--border); border-radius:8px;
    cursor:pointer; color:var(--text2); font-size:0.78rem; text-align:center;
    transition:border-color 0.15s, background 0.15s;
  }
  .upload-zone:hover { border-color:var(--primary); background:var(--surface2); color:var(--primary); }
  .logo-preview-small { display:flex; align-items:center; justify-content:space-between; padding:8px; background:var(--bg); border-radius:7px; border:1px solid var(--border); }

  /* Hint */
  .hint { font-size:0.68rem; color:var(--text3); }

  /* Responsive */
  @media (max-width:900px) {
    .vb-body { flex-direction:column; }
    .vb-panel { width:100% !important; max-height:50vh; border-left:none; border-top:1px solid var(--border); }
    .a4-page, .pdf-iframe { width:100%; min-height:unset; padding-bottom:60px; }
    .a4-footer { padding-left:16px; padding-right:16px; }
  }
</style>
