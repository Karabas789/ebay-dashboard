<script>
  import { onMount } from 'svelte';
  import { currentUser, showToast } from '$lib/stores.js';
  import { apiCall } from '$lib/api.js';

  let rechnungen = $state([]);
  let loading = $state(false);
  let fehler = $state('');

  let aktiverFilter = $state('alle');
  let suchbegriff = $state('');
  let proSeite = $state(20);
  let aktuelleSeite = $state(1);

  let ausgewaehlt = $state(new Set());
  let alleAusgewaehlt = $state(false);

  let modalOffen = $state(false);
  let modalModus = $state('neu');
  let modalRechnung = $state(null);
  let modalLaeuft = $state(false);

  let form = $state({
    order_id: '', kaeufer_name: '', kaeufer_email: '',
    kaeufer_strasse: '', kaeufer_plz: '', kaeufer_ort: '', kaeufer_land: 'DE',
    freitext: ''
  });

  let positionen = $state([
    { bezeichnung: '', artikel_nr: '', ebay_artikel_id: '', menge: 1, einzelpreis: '', mwst_satz: 19, rabatt_pct: 0 }
  ]);

  const mwstOptionen = [
    { wert: 19, label: '19 %' },
    { wert: 7, label: '7 %' },
    { wert: 0, label: '0 %' },
  ];

  function addPosition() {
    positionen = [...positionen, { bezeichnung: '', artikel_nr: '', ebay_artikel_id: '', menge: 1, einzelpreis: '', mwst_satz: 19, rabatt_pct: 0 }];
  }

  function removePosition(idx) {
    if (positionen.length <= 1) return;
    positionen = positionen.filter((_, i) => i !== idx);
  }

  let berechnetePositionen = $derived.by(() => {
    return positionen.map((p, idx) => {
      const menge = parseInt(p.menge) || 1;
      const ep = parseFloat(p.einzelpreis) || 0;
      const ms = parseFloat(p.mwst_satz) || 0;
      const rp = parseFloat(p.rabatt_pct) || 0;
      const bruttoGesamt = (ep * menge) * (1 - rp / 100);
      const netto = bruttoGesamt / (1 + ms / 100);
      const steuer = bruttoGesamt - netto;
      return { ...p, pos_nr: idx + 1, netto, steuer, brutto: bruttoGesamt };
    });
  });

  let summeNettoBer = $derived(berechnetePositionen.reduce((s, p) => s + p.netto, 0));
  let summeSteuerBer = $derived(berechnetePositionen.reduce((s, p) => s + p.steuer, 0));
  let summeBruttoBer = $derived(berechnetePositionen.reduce((s, p) => s + p.brutto, 0));
  let bestellungLaeuft = $state(false);
  let bestellungFehler = $state('');
  let duplikatRechnung = $state(null);
  let aenderungsgrund = $state('');

  // --- E-Mail Modal (Einzel) ---
  let sendenModal = $state(false);
  let sendenRechnung = $state(null);
  let sendenEmail = $state('');
  let sendenLaeuft = $state(false);

  // --- Bulk E-Mail Modal ---
  let bulkEmailModal = $state(false);
  let bulkEmailListe = $state([]);    // Array von { rechnung, email, einschliessen }
  let bulkEmailLaeuft = $state(false);
  let bulkEmailFortschritt = $state(0);
  let bulkEmailErgebnis = $state(null); // { gesendet, fehler, liste }

  let stornoModal = $state(false);
  let stornoRechnung = $state(null);
  let stornoLaeuft = $state(false);

  let autoRechnungAktiv = $state(true);
  let toggleLaeuft = $state(false);

  let schnellsucheOrderId = $state('');
  let schnellsucheLaeuft = $state(false);
  let schnellsucheFehler = $state('');

  let eRechnungMenuOffen = $state(false);
  let eRechnungRechnung = $state(null);
  let eRechnungMenuPos = $state({ top: 0, left: 0 });

  function normalisiereBestellung(b) {
    return {
      order_id:        b.order_id        || '',
      kaeufer_name:    b.kaeufer_name    || b.buyer_name    || '',
      kaeufer_email:   b.kaeufer_email   || b.buyer_email   || '',
      kaeufer_strasse: b.kaeufer_strasse || b.buyer_strasse || '',
      kaeufer_plz:     b.kaeufer_plz     || b.buyer_plz     || '',
      kaeufer_ort:     b.kaeufer_ort     || b.buyer_ort     || '',
      kaeufer_land:    b.kaeufer_land    || b.buyer_land    || 'DE',
      artikel_name:    b.artikel_name    || '',
      ebay_artikel_id: b.ebay_artikel_id || '',
      artikel_sku:     b.sold_sku        || b.artikel_sku   || '',
      einzelpreis:     b.brutto_betrag   || b.einzelpreis   || '',
      menge:           b.artikel_menge   || b.menge         || 1,
    };
  }

  function findeVorhandeneRechnung(orderId) {
    if (!orderId?.trim()) return null;
    return rechnungen.find(r =>
      r.order_id &&
      r.order_id.toLowerCase() === orderId.trim().toLowerCase() &&
      r.rechnung_typ === 'rechnung' &&
      r.status !== 'storniert'
    ) || null;
  }

  function resetForm() {
    form = {
      order_id: '', kaeufer_name: '', kaeufer_email: '',
      kaeufer_strasse: '', kaeufer_plz: '', kaeufer_ort: '', kaeufer_land: 'DE',
      freitext: ''
    };
    positionen = [
      { bezeichnung: '', artikel_nr: '', ebay_artikel_id: '', menge: 1, einzelpreis: '', mwst_satz: 19, rabatt_pct: 0 }
    ];
    bestellungFehler = '';
    duplikatRechnung = null;
    aenderungsgrund = '';
  }

  function oeffneNeuModal(vorbelegung = null) {
    resetForm();
    if (vorbelegung) {
      form = { ...form, order_id: vorbelegung.order_id || '', kaeufer_name: vorbelegung.kaeufer_name || '', kaeufer_email: vorbelegung.kaeufer_email || '', kaeufer_strasse: vorbelegung.kaeufer_strasse || '', kaeufer_plz: vorbelegung.kaeufer_plz || '', kaeufer_ort: vorbelegung.kaeufer_ort || '', kaeufer_land: vorbelegung.kaeufer_land || 'DE' };
      positionen = [{
        bezeichnung: vorbelegung.artikel_name || '', artikel_nr: vorbelegung.artikel_sku || '',
        ebay_artikel_id: vorbelegung.ebay_artikel_id || '', menge: vorbelegung.menge || 1,
        einzelpreis: vorbelegung.einzelpreis || '', mwst_satz: 19, rabatt_pct: 0
      }];
    }
    modalRechnung = null;
    modalModus = 'neu';
    modalOffen = true;
  }

  function oeffneDetailModal(r) {
    resetForm();
    modalRechnung = r;
    modalModus = 'detail';
    modalOffen = true;
  }

  async function oeffneBearbeitenModal(r) {
    resetForm();
    form = {
      order_id: r.order_id || '', kaeufer_name: r.kaeufer_name || '',
      kaeufer_email: r.kaeufer_email || '', kaeufer_strasse: r.kaeufer_strasse || '',
      kaeufer_plz: r.kaeufer_plz || '', kaeufer_ort: r.kaeufer_ort || '',
      kaeufer_land: r.kaeufer_land || 'DE', freitext: r.freitext || ''
    };

    // Positionen aus invoice_items laden (falls vorhanden)
    if (Array.isArray(r.positionen) && r.positionen.length > 0) {
      positionen = r.positionen.map(p => ({
        bezeichnung: p.bezeichnung || '', artikel_nr: p.artikel_nr || '',
        ebay_artikel_id: p.ebay_artikel_id || '', menge: p.menge || 1,
        einzelpreis: p.einzelpreis || 0, mwst_satz: p.mwst_satz ?? 19, rabatt_pct: p.rabatt_pct || 0
      }));
    } else {
      // Fallback: alte Single-Item-Daten
      positionen = [{
        bezeichnung: r.artikel_name || '', artikel_nr: '',
        ebay_artikel_id: r.ebay_artikel_id || '', menge: r.artikel_menge || 1,
        einzelpreis: parseFloat(r.einzelpreis) || parseFloat(r.brutto_betrag) || 0,
        mwst_satz: r.steuersatz || 19, rabatt_pct: 0
      }];
    }
    modalRechnung = r;
    modalModus = 'bearbeiten';
    modalOffen = true;

  }

  function schliesseModal() {
    modalOffen = false;
    modalRechnung = null;
    bestellungFehler = '';
    duplikatRechnung = null;
    aenderungsgrund = '';
    eRechnungMenuOffen = false;
    eRechnungRechnung = null;
    nachholTab = 'manuell';
    nachholErgebnis = null;
    nachholBestellungen = [];
    // sendenEmail und sendenRechnung werden NICHT hier zurückgesetzt
  }

  function onOrderIdInput() {
    bestellungFehler = '';
    duplikatRechnung = null;
  }

  async function ladeBestellungDaten() {
    if (!form.order_id?.trim()) return;
    if (modalModus === 'neu') {
      const dup = findeVorhandeneRechnung(form.order_id);
      if (dup) { duplikatRechnung = dup; return; }
    }
    duplikatRechnung = null;
    bestellungLaeuft = true;
    bestellungFehler = '';
    try {
      const data = await apiCall('bestellung-laden', { user_id: $currentUser?.id, order_id: form.order_id.trim() });
      if (data?.bestellung) {
        form = { ...form, ...normalisiereBestellung(data.bestellung) };
        showToast('Bestelldaten geladen');
      } else {
        bestellungFehler = 'Keine Bestellung gefunden';
      }
    } catch(e) {
      bestellungFehler = 'Fehler beim Laden';
    } finally {
      bestellungLaeuft = false;
    }
  }

  async function schnellsucheNachOrder() {
    if (!schnellsucheOrderId.trim()) return;
    const term = schnellsucheOrderId.trim().toLowerCase();
    const lok = rechnungen.filter(r =>
      r.rechnung_nr?.toLowerCase().includes(term) ||
      r.kaeufer_name?.toLowerCase().includes(term) ||
      r.kaeufer_email?.toLowerCase().includes(term) ||
      r.artikel_name?.toLowerCase().includes(term) ||
      r.order_id?.toLowerCase().includes(term)
    );
    if (lok.length === 1) {
      const r = lok[0];
      oeffneNeuModal({ order_id: r.order_id||'', kaeufer_name: r.kaeufer_name||'', kaeufer_email: r.kaeufer_email||'', kaeufer_strasse: r.kaeufer_strasse||'', kaeufer_plz: r.kaeufer_plz||'', kaeufer_ort: r.kaeufer_ort||'', kaeufer_land: r.kaeufer_land||'DE', artikel_name: r.artikel_name||'', ebay_artikel_id: r.ebay_artikel_id||'', artikel_sku: r.artikel_sku||'', menge: r.artikel_menge||1, einzelpreis: r.einzelpreis||r.brutto_betrag||'' });
      schnellsucheOrderId = ''; return;
    }
    if (lok.length > 1) { suchbegriff = schnellsucheOrderId.trim(); schnellsucheOrderId = ''; return; }
    schnellsucheLaeuft = true; schnellsucheFehler = '';
    try {
      const data = await apiCall('bestellung-laden', { user_id: $currentUser.id, suchbegriff: schnellsucheOrderId.trim() });
      if (data?.bestellung) { oeffneNeuModal(normalisiereBestellung(data.bestellung)); }
      else { oeffneNeuModal({ order_id: schnellsucheOrderId.trim() }); }
      schnellsucheOrderId = '';
    } catch(e) { schnellsucheFehler = 'Nichts gefunden'; }
    finally { schnellsucheLaeuft = false; }
  }

  async function erstelleRechnung() {
    if (!form.kaeufer_name) {
      showToast('Bitte Käufername ausfüllen.'); return;
    }
    if (positionen.length === 0 || positionen.some(p => !p.bezeichnung || !p.einzelpreis)) {
      showToast('Bitte alle Positionen mit Bezeichnung und Preis ausfüllen.'); return;
    }
    if (form.order_id?.trim()) {
      const dup = findeVorhandeneRechnung(form.order_id);
      if (dup) { duplikatRechnung = dup; return; }
    }
    modalLaeuft = true;
    try {
      const posPayload = positionen.map(p => ({
        bezeichnung: p.bezeichnung, artikel_nr: p.artikel_nr || '',
        ebay_artikel_id: p.ebay_artikel_id || '',
        menge: Number(p.menge) || 1, einzelpreis: Number(p.einzelpreis) || 0,
        mwst_satz: Number(p.mwst_satz), rabatt_pct: Number(p.rabatt_pct) || 0
      }));
      await apiCall('rechnung-erstellen', {
        user_id: $currentUser.id, typ: 'rechnung',
        order_id: form.order_id || '', kaeufer_name: form.kaeufer_name,
        kaeufer_email: form.kaeufer_email, kaeufer_strasse: form.kaeufer_strasse,
        kaeufer_plz: form.kaeufer_plz, kaeufer_ort: form.kaeufer_ort,
        kaeufer_land: form.kaeufer_land,
        positionen: posPayload,
        freitext: form.freitext || ''
      });
      showToast('✅ Rechnung erstellt'); schliesseModal(); await ladeRechnungen();
    } catch(e) { showToast('Fehler: ' + e.message); } finally { modalLaeuft = false; }
  }

  async function speichereBearbeitung() {
    if (!form.kaeufer_name) {
      showToast('Bitte Käufername ausfüllen.'); return;
    }
    if (positionen.length === 0 || positionen.some(p => !p.bezeichnung || !p.einzelpreis)) {
      showToast('Bitte alle Positionen mit Bezeichnung und Preis ausfüllen.'); return;
    }
    if (!aenderungsgrund.trim()) {
      showToast('Bitte Grund der Änderung angeben.'); return;
    }
    modalLaeuft = true;
    try {
      const posPayload = positionen.map(p => ({
        bezeichnung: p.bezeichnung, artikel_nr: p.artikel_nr || '',
        ebay_artikel_id: p.ebay_artikel_id || '',
        menge: Number(p.menge) || 1, einzelpreis: Number(p.einzelpreis) || 0,
        mwst_satz: Number(p.mwst_satz), rabatt_pct: Number(p.rabatt_pct) || 0
      }));
      await apiCall('rechnung-bearbeiten', {
        user_id: $currentUser.id, invoice_id: modalRechnung.id,
        order_id: form.order_id || '', kaeufer_name: form.kaeufer_name,
        kaeufer_email: form.kaeufer_email, kaeufer_strasse: form.kaeufer_strasse,
        kaeufer_plz: form.kaeufer_plz, kaeufer_ort: form.kaeufer_ort,
        kaeufer_land: form.kaeufer_land,
        positionen: posPayload,
        freitext: form.freitext || '',
        aenderungsgrund: aenderungsgrund.trim(),
      });
      showToast('✅ Rechnung aktualisiert'); schliesseModal(); await ladeRechnungen();
    } catch(e) { showToast('Fehler: ' + e.message); } finally { modalLaeuft = false; }
  }

  async function ladeAutoRechnungStatus() {
    try {
      const data = await apiCall('auto-rechnung-einstellungen', { user_id: $currentUser.id }, 'GET');
      autoRechnungAktiv = data?.auto_rechnung_aktiv ?? true;
    } catch(e) {}
  }

  async function toggleAutoRechnung() {
    toggleLaeuft = true; const neuerWert = !autoRechnungAktiv;
    try {
      await apiCall('auto-rechnung-einstellungen', { user_id: $currentUser.id, aktiv: neuerWert });
      autoRechnungAktiv = neuerWert;
      showToast(neuerWert ? '✅ Auto-Rechnung aktiviert — Rechnungen werden nach Versand erstellt' : 'Auto-Rechnung deaktiviert');
    } catch(e) { showToast('Fehler beim Speichern'); } finally { toggleLaeuft = false; }
  }

  // --- Nachhol-Funktion: Versendete Bestellungen ohne Rechnung ---
  let nachholTab = $state('manuell'); // 'manuell' | 'nachholen'
  let nachholBestellungen = $state([]);
  let nachholLaeuft = $state(false);
  let nachholErstellen = $state(false);
  let nachholFortschritt = $state(0);
  let nachholErgebnis = $state(null);

  async function ladeVersendeteOhneRechnung() {
    nachholLaeuft = true;
    nachholBestellungen = [];
    nachholErgebnis = null;
    try {
      const data = await apiCall('orders-laden', { user_id: $currentUser.id, ebay_username: $currentUser.ebay_user_id });
      if (data?.success && data?.orders) {
        const versendete = data.orders.filter(o => o.status === 'versendet' && !o.archiviert);
        // Filtern: nur die, für die noch keine Rechnung existiert
        nachholBestellungen = versendete.filter(o => {
          const hatSchon = rechnungen.some(r =>
            r.order_id && o.order_id &&
            r.order_id.toLowerCase() === o.order_id.toLowerCase() &&
            r.rechnung_typ === 'rechnung' && r.status !== 'storniert'
          );
          return !hatSchon;
        }).map(o => ({ ...o, ausgewaehlt: true }));
      }
    } catch(e) {
      showToast('Fehler beim Laden der Bestellungen: ' + e.message);
    } finally {
      nachholLaeuft = false;
    }
  }

  async function nachholRechnungenErstellen() {
    const zuErstellen = nachholBestellungen.filter(o => o.ausgewaehlt);
    if (zuErstellen.length === 0) { showToast('Keine Bestellungen ausgewählt.'); return; }
    nachholErstellen = true;
    nachholFortschritt = 0;
    let erstellt = 0, fehlerCount = 0;
    for (let i = 0; i < zuErstellen.length; i++) {
      const o = zuErstellen[i];
      try {
        await apiCall('rechnung-erstellen', {
          user_id: $currentUser.id, typ: 'rechnung', order_id: o.order_id,
          kaeufer_name: o.buyer_name || o.buyer_username || '',
          kaeufer_email: o.buyer_email || '',
          kaeufer_strasse: o.buyer_strasse || '', kaeufer_plz: o.buyer_plz || '',
          kaeufer_ort: o.buyer_ort || '', kaeufer_land: o.buyer_land || 'DE',
          artikel_name: o.artikel_name || '', menge: o.menge || 1,
          einzelpreis: parseFloat(o.gesamt || 0) / (o.menge || 1),
          ebay_artikel_id: o.ebay_artikel_id || ''
        });
        erstellt++;
      } catch(e) { fehlerCount++; }
      nachholFortschritt = Math.round(((i + 1) / zuErstellen.length) * 100);
      await new Promise(res => setTimeout(res, 300));
    }
    nachholErgebnis = { erstellt, fehler: fehlerCount };
    nachholErstellen = false;
    showToast(`${erstellt} Rechnung(en) erstellt${fehlerCount > 0 ? `, ${fehlerCount} Fehler` : ''}`);
    await ladeRechnungen();
  }

  function oeffneSendenModal(r) {
    // Zuerst Detail-Modal schliessen OHNE reset
    modalOffen = false;
    eRechnungMenuOffen = false;
    eRechnungRechnung = null;
    // DANN E-Mail aus allen möglichen Feldnamen lesen
    const email = r.kaeufer_email || r.buyer_email || r.email || r.email_gesendet_an || '';
    sendenRechnung = r;
    sendenEmail = email;
    sendenModal = true;
  }

  async function sendeRechnung() {
    if (!sendenEmail) { showToast('Bitte E-Mail eingeben.'); return; }
    sendenLaeuft = true;
    try {
      await apiCall('rechnung-senden', { invoice_id: sendenRechnung.id, user_id: $currentUser.id, to_email: sendenEmail });
      showToast('✅ Rechnung gesendet an ' + sendenEmail);
      sendenModal = false;
      await ladeRechnungen();
    } catch(e) { showToast('Fehler: ' + e.message); } finally { sendenLaeuft = false; }
  }

  // --- Bulk E-Mail Modal öffnen ---
  function oeffneBulkEmailModal() {
    const liste = rechnungen.filter(r => ausgewaehlt.has(r.id) && r.rechnung_typ !== 'storno' && r.status !== 'storniert');
    bulkEmailListe = liste.map(r => ({
      rechnung: r,
      email: r.kaeufer_email || '',
      einschliessen: true,
      status: null // null | 'success' | 'error' | 'keine-email'
    }));
    bulkEmailErgebnis = null;
    bulkEmailFortschritt = 0;
    bulkEmailModal = true;
  }

  async function sendeBulkEmails() {
    const zuSenden = bulkEmailListe.filter(item => item.einschliessen && item.email?.trim());
    if (zuSenden.length === 0) { showToast('Keine Rechnungen zum Senden ausgewählt.'); return; }

    bulkEmailLaeuft = true;
    bulkEmailFortschritt = 0;
    let gesendet = 0;
    let fehlerCount = 0;

    for (let i = 0; i < bulkEmailListe.length; i++) {
      const item = bulkEmailListe[i];
      if (!item.einschliessen || !item.email?.trim()) {
        if (!item.email?.trim()) bulkEmailListe[i].status = 'keine-email';
        continue;
      }
      try {
        await apiCall('rechnung-senden', {
          invoice_id: item.rechnung.id,
          user_id: $currentUser.id,
          to_email: item.email.trim()
        });
        bulkEmailListe[i].status = 'success';
        gesendet++;
      } catch(e) {
        bulkEmailListe[i].status = 'error';
        fehlerCount++;
      }
      bulkEmailFortschritt = Math.round(((i + 1) / bulkEmailListe.length) * 100);
      // Kurze Pause um den Server nicht zu überlasten
      await new Promise(res => setTimeout(res, 300));
    }

    bulkEmailErgebnis = { gesendet, fehler: fehlerCount };
    bulkEmailLaeuft = false;
    showToast(`${gesendet} Rechnung(en) gesendet${fehlerCount > 0 ? `, ${fehlerCount} Fehler` : ''}`);
    await ladeRechnungen();
  }

  // --- Sonstige ---
  function oeffneStornoModal(r) { stornoRechnung = r; stornoModal = true; schliesseModal(); }
  async function erstelleStorno() {
    stornoLaeuft = true;
    try {
      await apiCall('rechnung-stornieren', { user_id: $currentUser.id, invoice_id: stornoRechnung.id });
      showToast('Stornorechnung erstellt'); stornoModal = false; await ladeRechnungen();
    } catch(e) { showToast('Fehler: ' + e.message); } finally { stornoLaeuft = false; }
  }

  async function bulkDrucken() {
    const liste = rechnungen.filter(r => ausgewaehlt.has(r.id));
    for (const r of liste) { await ladePDF(r); await new Promise(res => setTimeout(res, 400)); }
  }

  function bulkExportCSV() {
    const liste = rechnungen.filter(r => ausgewaehlt.has(r.id));
    const header = ['Rechnungsnr.','Datum','Kaeufer','E-Mail','Strasse','PLZ','Ort','Artikel','Bestellnr.','Netto','MwSt.','Brutto','Status'];
    const zeilen = liste.map(r => [r.rechnung_nr, fmtDatum(r.erstellt_am), r.kaeufer_name, r.kaeufer_email||'', r.kaeufer_strasse||'', r.kaeufer_plz||'', r.kaeufer_ort||'', r.artikel_name, r.order_id||'', fmt(r.netto_betrag), fmt(r.steuer_betrag), fmt(r.brutto_betrag), r.status].map(v => `"${String(v||'').replace(/"/g,'""')}"`).join(';'));
    const csv = [header.join(';'), ...zeilen].join('\n');
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `rechnungen-export-${new Date().toISOString().slice(0,10)}.csv`; a.click(); URL.revokeObjectURL(url);
  }

  function oeffneERechnungMenu(r, e) {
    e.stopPropagation();
    if (eRechnungRechnung?.id === r.id && eRechnungMenuOffen) {
      eRechnungMenuOffen = false; eRechnungRechnung = null; return;
    }
    const rect = e.currentTarget.getBoundingClientRect();
    const menuH = 126;
    const top = (window.innerHeight - rect.bottom >= menuH) ? rect.bottom + 4 : rect.top - menuH - 4;
    const left = Math.min(rect.left, window.innerWidth - 275);
    eRechnungMenuPos = { top, left };
    eRechnungRechnung = r;
    eRechnungMenuOffen = true;
  }

  async function erstelleERechnung(rechnung, format) {
    eRechnungMenuOffen = false; eRechnungRechnung = null;
    showToast('E-Rechnung wird erstellt...');
    try {
      const data = await apiCall('e-rechnung-erstellen', { invoice_id: rechnung.id, user_id: $currentUser.id, format });
      if (format === 'xrechnung') {
        const blob = new Blob([data.xml], { type: 'application/xml' });
        const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = (rechnung.rechnung_nr||'XRechnung') + '.xml'; a.click(); URL.revokeObjectURL(url);
      } else {
        const b64 = data.pdf_base64 || data.pdf;
        if (!b64) { showToast('Kein Ergebnis erhalten.'); return; }
        const blob = new Blob([Uint8Array.from(atob(b64), c => c.charCodeAt(0))], { type: 'application/pdf' });
        const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = (rechnung.rechnung_nr||'ERechnung') + '.pdf'; a.click(); URL.revokeObjectURL(url);
      }
      showToast('E-Rechnung erstellt');
    } catch(e) { showToast('Fehler: ' + e.message); }
  }

  let gefiltert = $derived.by(() => {
    let liste = rechnungen;
    if (!suchbegriff.trim()) {
      if (aktiverFilter === 'rechnungen') liste = liste.filter(r => r.rechnung_typ === 'rechnung' && r.status !== 'storniert');
      else if (aktiverFilter === 'stornos')  liste = liste.filter(r => r.rechnung_typ === 'storno');
      else if (aktiverFilter === 'erstellt') liste = liste.filter(r => r.status === 'erstellt');
      else if (aktiverFilter === 'gesendet') liste = liste.filter(r => r.status === 'gesendet');
    }
    if (suchbegriff.trim()) {
      const s = suchbegriff.toLowerCase();
      liste = liste.filter(r =>
        r.rechnung_nr?.toLowerCase().includes(s) || r.kaeufer_name?.toLowerCase().includes(s) ||
        r.kaeufer_email?.toLowerCase().includes(s) || r.kaeufer_strasse?.toLowerCase().includes(s) ||
        r.kaeufer_plz?.toLowerCase().includes(s) || r.kaeufer_ort?.toLowerCase().includes(s) ||
        r.artikel_name?.toLowerCase().includes(s) || r.ebay_artikel_id?.toLowerCase().includes(s) ||
        r.order_id?.toLowerCase().includes(s)
      );
    }
    return liste;
  });

  let gesamtSeiten   = $derived(Math.max(1, Math.ceil(gefiltert.length / proSeite)));
  let sichtbar       = $derived(gefiltert.slice((aktuelleSeite - 1) * proSeite, aktuelleSeite * proSeite));
  let summeNetto     = $derived(gefiltert.filter(r => r.status !== 'storniert' && r.rechnung_typ === 'rechnung').reduce((s, r) => s + (parseFloat(r.netto_betrag)||0), 0));
  let summeStorno    = $derived(gefiltert.filter(r => r.rechnung_typ === 'storno').reduce((s, r) => s + (parseFloat(r.brutto_betrag)||0), 0));
  let kpiGesamt      = $derived(rechnungen.filter(r => r.rechnung_typ === 'rechnung').length);
  let kpiGesendet    = $derived(rechnungen.filter(r => r.status === 'gesendet').length);
  let kpiAusstehend  = $derived(rechnungen.filter(r => r.status === 'erstellt' && r.rechnung_typ === 'rechnung').length);
  let kpiStorniert   = $derived(rechnungen.filter(r => r.rechnung_typ === 'storno').length);
  let kpiBrutto      = $derived(rechnungen.filter(r => r.rechnung_typ === 'rechnung' && r.status !== 'storniert').reduce((s, r) => s + (parseFloat(r.brutto_betrag)||0), 0));
  let kpiDieserMonat = $derived.by(() => {
    const jetzt = new Date();
    return rechnungen.filter(r => { const d = new Date(r.erstellt_am); return d.getFullYear() === jetzt.getFullYear() && d.getMonth() === jetzt.getMonth(); }).length;
  });

  onMount(() => { if ($currentUser) { ladeRechnungen(); ladeAutoRechnungStatus(); } });

  async function ladeRechnungen() {
    loading = true; fehler = '';
    try {
      const data = await apiCall('rechnungen-laden', { user_id: $currentUser.id, ebayusername: $currentUser.ebayuserid });
      rechnungen = Array.isArray(data) ? data : (data.rechnungen || []);
    } catch(e) { fehler = e.message; } finally { loading = false; }
  }

  async function ladePDF(rechnung) {
    try {
      showToast('PDF wird geladen...');
      const data = await apiCall('rechnung-pdf', { invoice_id: rechnung.id, user_id: $currentUser.id });
      const b64 = data.pdf_base64 || data.pdf;
      if (!b64) { showToast('Kein PDF vorhanden.'); return; }
      const blob = new Blob([Uint8Array.from(atob(b64), c => c.charCodeAt(0))], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = (rechnung.rechnung_nr||'Rechnung') + '.pdf'; a.click(); URL.revokeObjectURL(url);
    } catch(e) { showToast('Fehler: ' + e.message); }
  }

  function toggleAuswahl(id) {
    const neu = new Set(ausgewaehlt); neu.has(id) ? neu.delete(id) : neu.add(id); ausgewaehlt = neu;
    alleAusgewaehlt = sichtbar.length > 0 && sichtbar.every(r => neu.has(r.id));
  }
  function toggleAlleAuswaehlen() {
    if (alleAusgewaehlt) { ausgewaehlt = new Set(); alleAusgewaehlt = false; }
    else { ausgewaehlt = new Set(sichtbar.map(r => r.id)); alleAusgewaehlt = true; }
  }
  function setFilter(f) { aktiverFilter = f; aktuelleSeite = 1; ausgewaehlt = new Set(); alleAusgewaehlt = false; }
  function fmt(n) { return Number(n||0).toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
  function fmtDatum(d) { if (!d) return '-'; return new Date(d).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' }); }
  function statusBadge(r) {
    if (r.rechnung_typ === 'storno') return { label: 'Storno', cls: 'badge-storniert' };
    const map = { erstellt: { label: 'Erstellt', cls: 'badge-erstellt' }, gesendet: { label: 'Gesendet', cls: 'badge-gesendet' }, storniert: { label: 'Storniert', cls: 'badge-storniert' } };
    return map[r.status] || { label: r.status, cls: '' };
  }
  const filterTabs = [{ key: 'alle', label: 'Alle' }, { key: 'rechnungen', label: 'Rechnungen' }, { key: 'stornos', label: 'Stornos' }, { key: 'erstellt', label: 'Erstellt' }, { key: 'gesendet', label: 'Gesendet' }];
  function tabCount(key) {
    if (key === 'alle') return rechnungen.length;
    if (key === 'rechnungen') return rechnungen.filter(r => r.rechnung_typ === 'rechnung' && r.status !== 'storniert').length;
    if (key === 'stornos') return rechnungen.filter(r => r.rechnung_typ === 'storno').length;
    if (key === 'erstellt') return rechnungen.filter(r => r.status === 'erstellt').length;
    if (key === 'gesendet') return rechnungen.filter(r => r.status === 'gesendet').length;
    return 0;
  }

  // Anzahl auswählbare (keine Stornos) in Bulk-Auswahl
  let bulkSendbar = $derived(
    rechnungen.filter(r => ausgewaehlt.has(r.id) && r.rechnung_typ !== 'storno' && r.status !== 'storniert').length
  );
</script>

<div class="page-container" onclick={() => { if (eRechnungMenuOffen) { eRechnungMenuOffen = false; eRechnungRechnung = null; } }}>

  <div class="page-hdr">
    <div>
      <div class="page-title">Rechnungen</div>
      <div class="page-sub">Automatisch erstellte Rechnungen verwalten</div>
    </div>
    <div class="hdr-actions">
      <div class="hdr-suche">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--text3);flex-shrink:0;"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
        <input class="hdr-suche-input" type="text" placeholder="Name, Rechnungs-Nr., Bestellnr. ..." bind:value={schnellsucheOrderId} onkeydown={(e) => e.key === 'Enter' && schnellsucheNachOrder()} />
        {#if schnellsucheFehler}<span class="hdr-suche-fehler">{schnellsucheFehler}</span>{/if}
        <button class="btn-primary btn-sm" onclick={schnellsucheNachOrder} disabled={schnellsucheLaeuft || !schnellsucheOrderId.trim()}>{schnellsucheLaeuft ? '...' : 'Suchen'}</button>
      </div>
      <div class="toggle-wrap">
        <span class="toggle-label">Auto-Rechnung</span>
        <button class="toggle-btn {autoRechnungAktiv ? 'toggle-an' : 'toggle-aus'}" onclick={toggleAutoRechnung} disabled={toggleLaeuft}><span class="toggle-thumb"></span></button>
        <span class="toggle-status {autoRechnungAktiv ? 'status-an' : 'status-aus'}">{autoRechnungAktiv ? 'Aktiv' : 'Inaktiv'}</span>
      </div>
      <button class="btn-ghost" onclick={ladeRechnungen} disabled={loading}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/></svg>
        Aktualisieren
      </button>
      <button class="btn-primary" onclick={() => oeffneNeuModal()}>+ Rechnung erstellen</button>
    </div>
  </div>

  <div class="kpi-grid">
    <div class="kpi-card"><div class="kpi-label">Gesamt</div><div class="kpi-value">{kpiGesamt}</div></div>
    <div class="kpi-card"><div class="kpi-label">Gesendet</div><div class="kpi-value kpi-blue">{kpiGesendet}</div></div>
    <div class="kpi-card"><div class="kpi-label">Ausstehend</div><div class="kpi-value kpi-yellow">{kpiAusstehend}</div></div>
    <div class="kpi-card"><div class="kpi-label">Storniert</div><div class="kpi-value kpi-red">{kpiStorniert}</div></div>
    <div class="kpi-card kpi-card-wide"><div class="kpi-label">Umsatz Brutto (aktive)</div><div class="kpi-value kpi-blue">{fmt(kpiBrutto)} EUR</div></div>
    <div class="kpi-card"><div class="kpi-label">Diesen Monat</div><div class="kpi-value">{kpiDieserMonat}</div></div>
  </div>

  <div class="toolbar">
    <div class="filter-tabs">
      {#each filterTabs as tab (tab.key)}
        <button class="filter-tab {aktiverFilter === tab.key ? 'active' : ''}" onclick={() => setFilter(tab.key)}>{tab.label}<span class="tab-count">{tabCount(tab.key)}</span></button>
      {/each}
    </div>
    <div class="toolbar-right">
      <select class="select-klein" bind:value={proSeite} onchange={() => aktuelleSeite = 1}>
        <option value={20}>20 / Seite</option><option value={50}>50 / Seite</option><option value={100}>100 / Seite</option>
      </select>
    </div>
  </div>

  {#if ausgewaehlt.size > 0}
    <div class="bulk-bar">
      <span><strong>{ausgewaehlt.size}</strong> Rechnung{ausgewaehlt.size > 1 ? 'en' : ''} ausgewählt</span>
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
        <button class="btn-ghost btn-sm" onclick={bulkDrucken}>📥 PDFs laden</button>
        <button class="btn-email btn-sm" onclick={oeffneBulkEmailModal} disabled={bulkSendbar === 0}>
          📧 E-Mails senden ({bulkSendbar})
        </button>
        <button class="btn-ghost btn-sm" onclick={bulkExportCSV}>📊 CSV exportieren</button>
      </div>
    </div>
  {/if}

  <div class="tabellen-wrapper">
    {#if loading}
      <div class="status-info">Lade Rechnungen...</div>
    {:else if fehler}
      <div class="status-info status-fehler">{fehler}</div>
    {:else if sichtbar.length === 0}
      <div class="leer-state">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
        <p>Keine Rechnungen gefunden</p>
        <button class="btn-primary btn-sm" onclick={() => oeffneNeuModal()}>Erste Rechnung erstellen</button>
      </div>
    {:else}
      <table class="tabelle">
        <thead>
          <tr>
            <th class="th-check" onclick={(e) => e.stopPropagation()}><label class="chk-label"><input type="checkbox" checked={alleAusgewaehlt} onchange={toggleAlleAuswaehlen} /></label></th>
            <th>Nummer</th><th>Datum</th><th>Käufer</th><th>Artikel</th>
            <th class="th-right">Netto</th><th class="th-right">MwSt.</th><th class="th-right">Brutto</th>
            <th>Status</th><th class="th-actions">Aktionen</th>
          </tr>
        </thead>
        <tbody>
          {#each sichtbar as r (r.id)}
            {@const badge = statusBadge(r)}
            <tr class="tbl-row" onclick={() => oeffneDetailModal(r)}>
              <td class="td-check" onclick={(e) => e.stopPropagation()}><label class="chk-label"><input type="checkbox" checked={ausgewaehlt.has(r.id)} onchange={() => toggleAuswahl(r.id)} /></label></td>
              <td class="td-nr">{r.rechnung_nr || '-'}</td>
              <td class="td-datum">{fmtDatum(r.erstellt_am)}</td>
              <td class="td-kaeufer">
                <div>{r.kaeufer_name || '-'}</div>
                {#if r.kaeufer_email}<div class="td-email">{r.kaeufer_email}</div>{/if}
              </td>
              <td class="td-artikel">{r.artikel_name || '-'}</td>
              <td class="td-right">{fmt(r.netto_betrag)} EUR</td>
              <td class="td-right">{fmt(r.steuer_betrag)} EUR</td>
              <td class="td-right td-bold">{fmt(r.brutto_betrag)} EUR</td>
              <td>
                <span class="badge {badge.cls}">{badge.label}</span>
                {#if r.status === 'gesendet' && r.email_gesendet_an}
                  <div class="td-gesendet-an" title="Gesendet an: {r.email_gesendet_an}">✉ gesendet</div>
                {/if}
              </td>
              <td class="td-actions" onclick={(e) => e.stopPropagation()}>
                <button class="icon-btn" title="Details" onclick={() => oeffneDetailModal(r)}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                </button>
                <button class="icon-btn" title="PDF herunterladen" onclick={() => ladePDF(r)}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                </button>
                {#if r.status !== 'storniert' && r.rechnung_typ !== 'storno'}
                  <button class="icon-btn icon-btn-email" title="Per E-Mail senden" onclick={() => oeffneSendenModal(r)}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
                  </button>
                  <button class="icon-btn icon-btn-edit" title="Bearbeiten" onclick={() => oeffneBearbeitenModal(r)}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                  </button>
                  <button class="icon-btn icon-btn-erechnung" title="E-Rechnung erstellen" onclick={(e) => oeffneERechnungMenu(r, e)}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
                  </button>
                  <button class="icon-btn icon-btn-danger" title="Stornieren" onclick={() => oeffneStornoModal(r)}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6M9 6V4h6v2"/></svg>
                  </button>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>

  {#if gefiltert.length > 0}
    <div class="footer-bar">
      <div class="footer-summen">
        <span>Netto gesamt: <strong>{fmt(summeNetto)} EUR</strong></span>
        {#if summeStorno > 0}<span class="storno-summe">Stornos: <strong>{fmt(summeStorno)} EUR</strong></span>{/if}
        <span class="footer-count">{gefiltert.length} Einträge</span>
      </div>
      <div class="pagination">
        <button class="page-btn" disabled={aktuelleSeite <= 1} onclick={() => aktuelleSeite--}>&#8249;</button>
        {#each Array.from({ length: gesamtSeiten }, (_, i) => i + 1) as seite (seite)}
          {#if seite === 1 || seite === gesamtSeiten || Math.abs(seite - aktuelleSeite) <= 2}
            <button class="page-btn {aktuelleSeite === seite ? 'active' : ''}" onclick={() => aktuelleSeite = seite}>{seite}</button>
          {/if}
        {/each}
        <button class="page-btn" disabled={aktuelleSeite >= gesamtSeiten} onclick={() => aktuelleSeite++}>&#8250;</button>
      </div>
    </div>
  {/if}
</div>

<!-- E-Rechnung Dropdown fixed -->
{#if eRechnungMenuOffen && eRechnungRechnung}
  <div class="erechnung-dropdown-fixed"
    style="top:{eRechnungMenuPos.top}px;left:{eRechnungMenuPos.left}px"
    onclick={(e) => e.stopPropagation()}>
    <button onclick={() => erstelleERechnung(eRechnungRechnung, 'zugferd_en16931')}>ZUGFeRD 2.4 EN16931 PDF</button>
    <button onclick={() => erstelleERechnung(eRechnungRechnung, 'zugferd_extended')}>ZUGFeRD 2.4 EXTENDED PDF (BETA)</button>
    <button onclick={() => erstelleERechnung(eRechnungRechnung, 'xrechnung')}>XRechnung 3.0.2 XML</button>
  </div>
{/if}

<!-- DETAIL / NEU / BEARBEITEN MODAL -->
{#if modalOffen}
  <div class="modal-overlay" onclick={schliesseModal}>
    <div class="modal-box modal-universal" onclick={(e) => e.stopPropagation()}>

      {#if modalModus === 'detail' && modalRechnung}
        {@const r = modalRechnung}
        {@const badge = statusBadge(r)}
        <div class="modal-hdr">
          <div>
            <span class="modal-titel">{r.rechnung_nr || 'Rechnung'}</span>
            {#if r.order_id}<div class="modal-sub">{r.order_id}</div>{/if}
          </div>
          <button class="icon-btn" onclick={schliesseModal}>✕</button>
        </div>
        <div class="modal-body">
          <div class="detail-meta">
            <span class="badge {badge.cls}">{badge.label}</span>
            <span class="detail-datum">{fmtDatum(r.erstellt_am)}</span>
          </div>
          {#if r.rechnung_typ === 'storno'}<div class="hinweis hinweis-rot">Stornorechnung zu einer vorherigen Rechnung</div>{/if}
          {#if r.aenderungsgrund}
            <div class="hinweis hinweis-blau">
              <strong>Geändert am {fmtDatum(r.aenderungsdatum)}:</strong> {r.aenderungsgrund}
              {#if r.vorgaenger_nr}<span style="color:var(--text3);font-size:0.78rem;margin-left:6px">(vorher: {r.vorgaenger_nr})</span>{/if}
            </div>
          {/if}
          <div class="bm-section">
            <div class="bm-section-titel">Rechnungsempfänger</div>
            <div class="bm-grid">
              <div class="bm-field bm-full"><div class="bm-label">Name</div><div class="bm-value">{r.kaeufer_name || '-'}</div></div>
              {#if r.kaeufer_email}<div class="bm-field bm-full"><div class="bm-label">E-Mail</div><div class="bm-value" style="color:var(--primary)">{r.kaeufer_email}</div></div>{/if}
              {#if r.kaeufer_strasse}<div class="bm-field bm-full"><div class="bm-label">Adresse</div><div class="bm-value">{r.kaeufer_strasse}, {r.kaeufer_plz} {r.kaeufer_ort}, {r.kaeufer_land}</div></div>{/if}
            </div>
          </div>
          <div class="bm-section">
            <div class="bm-section-titel">Positionen</div>
            {#if Array.isArray(r.positionen) && r.positionen.length > 0}
              <table class="detail-pos-tabelle">
                <thead>
                  <tr><th>Pos</th><th>Bezeichnung</th><th class="th-right">Menge</th><th class="th-right">EP</th><th class="th-right">MwSt</th><th class="th-right">Betrag</th></tr>
                </thead>
                <tbody>
                  {#each r.positionen as p}
                    <tr>
                      <td>{p.pos_nr}</td>
                      <td>{p.bezeichnung || '-'}{#if p.artikel_nr}<span class="pos-artnr"> ({p.artikel_nr})</span>{/if}</td>
                      <td class="td-right">{p.menge}</td>
                      <td class="td-right">{fmt(p.einzelpreis)} €</td>
                      <td class="td-right">{p.mwst_satz}%</td>
                      <td class="td-right">{fmt(p.brutto_betrag)} €</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            {:else}
              <div class="bm-grid">
                <div class="bm-field bm-full"><div class="bm-label">Bezeichnung</div><div class="bm-value">{r.artikel_name || '-'}</div></div>
                {#if r.ebay_artikel_id}<div class="bm-field"><div class="bm-label">eBay Artikel-ID</div><div class="bm-value" style="font-family:monospace">{r.ebay_artikel_id}</div></div>{/if}
                <div class="bm-field"><div class="bm-label">Menge</div><div class="bm-value">{r.artikel_menge || 1}</div></div>
              </div>
            {/if}
          </div>
          {#if r.freitext}
            <div class="hinweis hinweis-gelb" style="margin-bottom:12px">{r.freitext}</div>
          {/if}

          {#if r.order_id}
            <div class="bm-section">
              <div class="bm-section-titel">Bestellnummer</div>
              <div style="font-family:monospace;font-size:0.82rem;color:var(--text)">{r.order_id}</div>
            </div>
          {/if}
          <div class="betraege-box">
            <div class="betrag-zeile"><span>Netto</span><span>{fmt(r.netto_betrag)} EUR</span></div>
            <div class="betrag-zeile"><span>MwSt. ({r.steuersatz || 19} %)</span><span>{fmt(r.steuer_betrag)} EUR</span></div>
            <div class="betrag-zeile betrag-brutto"><span>Brutto</span><span>{fmt(r.brutto_betrag)} EUR</span></div>
          </div>
          {#if r.email_gesendet_an}
            <div class="bm-section" style="margin-top:12px">
              <div class="bm-section-titel">E-Mail gesendet an</div>
              <div style="font-size:0.82rem;color:var(--text2)">{r.email_gesendet_an}</div>
            </div>
          {/if}
        </div>
        <div class="modal-footer">
          <button class="btn-ghost btn-sm" onclick={schliesseModal}>Schließen</button>
          <button class="btn-secondary btn-sm" onclick={() => ladePDF(r)}>📥 PDF</button>
          {#if r.status !== 'storniert' && r.rechnung_typ !== 'storno'}
            <button class="btn-email-sm" onclick={() => oeffneSendenModal(r)}>📧 E-Mail senden</button>
            <button class="btn-secondary btn-sm" onclick={(e) => oeffneERechnungMenu(r, e)}>E-Rechnung ▾</button>
            <button class="btn-secondary btn-sm" onclick={() => oeffneBearbeitenModal(r)}>✏️ Bearbeiten</button>
            <button class="btn-danger btn-sm" onclick={() => oeffneStornoModal(r)}>Stornieren</button>
          {/if}
        </div>

      {:else if modalModus === 'neu'}
        <div class="modal-hdr">
          <span class="modal-titel">Rechnung erstellen</span>
          <button class="icon-btn" onclick={schliesseModal}>✕</button>
        </div>
        <div class="modal-tabs">
          <button class="modal-tab" class:active={nachholTab === 'manuell'} onclick={() => nachholTab = 'manuell'}>📝 Manuell erstellen</button>
          <button class="modal-tab" class:active={nachholTab === 'nachholen'} onclick={() => { nachholTab = 'nachholen'; if (nachholBestellungen.length === 0 && !nachholLaeuft) ladeVersendeteOhneRechnung(); }}>📦 Versendete nachholen</button>
        </div>

        {#if nachholTab === 'manuell'}
        <div class="modal-body">
          <div class="form-group" style="margin-bottom:14px">
            <label>Bestellnr. / Referenz <span style="font-weight:400;color:var(--text3)">(optional)</span></label>
            <div style="display:flex;gap:8px">
              <input bind:value={form.order_id} placeholder="z. B. eBay-Bestellnr., Auftragsnr. ..." style="flex:1"
                oninput={onOrderIdInput} onkeydown={(e) => e.key === 'Enter' && form.order_id?.trim() && ladeBestellungDaten()} />
              {#if form.order_id?.trim()}
                <button class="btn-primary btn-sm" onclick={ladeBestellungDaten} disabled={bestellungLaeuft} style="white-space:nowrap">
                  {bestellungLaeuft ? '...' : 'Laden'}
                </button>
              {/if}
            </div>
            {#if bestellungFehler}<p class="form-fehler">{bestellungFehler}</p>{/if}
          </div>
          {#if duplikatRechnung}
            <div class="hinweis hinweis-rot" style="margin-bottom:14px">
              ⚠️ Für diese Bestellung existiert bereits <strong>{duplikatRechnung.rechnung_nr}</strong>.
              <button class="btn-link" onclick={() => oeffneDetailModal(duplikatRechnung)}>Anzeigen →</button>
            </div>
          {/if}
          <!-- Käufer-Daten -->
          <div class="form-grid">
            <div class="form-group"><label>Käufer *</label><input bind:value={form.kaeufer_name} placeholder="Max Mustermann" /></div>
            <div class="form-group"><label>E-Mail</label><input bind:value={form.kaeufer_email} type="email" placeholder="max@example.com" /></div>
            <div class="form-group"><label>Straße</label><input bind:value={form.kaeufer_strasse} placeholder="Musterstr. 1" /></div>
            <div class="form-group form-2col">
              <div class="form-group"><label>PLZ</label><input bind:value={form.kaeufer_plz} placeholder="12345" /></div>
              <div class="form-group"><label>Ort</label><input bind:value={form.kaeufer_ort} placeholder="Berlin" /></div>
            </div>
            <div class="form-group"><label>Land</label><input bind:value={form.kaeufer_land} placeholder="DE" /></div>
          </div>

          <!-- Positionen-Editor -->
          <div class="pos-section">
            <div class="pos-header">
              <span class="pos-titel">Positionen</span>
              <button class="btn-ghost btn-sm" type="button" onclick={addPosition}>+ Position</button>
            </div>
            {#each positionen as pos, i}
              <div class="pos-row">
                <div class="pos-nr">{i + 1}</div>
                <div class="pos-fields">
                  <div class="pos-field pos-field-wide">
                    <label>Bezeichnung *</label>
                    <input bind:value={positionen[i].bezeichnung} placeholder="Produktname" />
                  </div>
                  <div class="pos-field">
                    <label>Art-Nr.</label>
                    <input bind:value={positionen[i].artikel_nr} placeholder="SKU" />
                  </div>
                  <div class="pos-field">
                    <label>Menge</label>
                    <input bind:value={positionen[i].menge} type="number" min="1" />
                  </div>
                  <div class="pos-field">
                    <label>EP Brutto *</label>
                    <input bind:value={positionen[i].einzelpreis} type="number" step="0.01" placeholder="9.99" />
                  </div>
                  <div class="pos-field">
                    <label>MwSt.</label>
                    <select bind:value={positionen[i].mwst_satz}>
                      {#each mwstOptionen as opt}
                        <option value={opt.wert}>{opt.label}</option>
                      {/each}
                    </select>
                  </div>
                  <div class="pos-field pos-field-summe">
                    <label>Brutto</label>
                    <span class="pos-betrag">{fmt(berechnetePositionen[i]?.brutto || 0)} €</span>
                  </div>
                  {#if positionen.length > 1}
                    <button class="pos-remove" type="button" onclick={() => removePosition(i)} title="Entfernen">✕</button>
                  {/if}
                </div>
              </div>
            {/each}
            <div class="pos-summen">
              <div class="pos-summen-zeile"><span>Netto</span><span>{fmt(summeNettoBer)} €</span></div>
              <div class="pos-summen-zeile"><span>MwSt.</span><span>{fmt(summeSteuerBer)} €</span></div>
              <div class="pos-summen-zeile pos-summen-brutto"><span>Brutto</span><span>{fmt(summeBruttoBer)} €</span></div>
            </div>
          </div>

          <!-- Freitext -->
          <div class="form-group" style="margin-top:12px">
            <label>Freitext / Hinweis <span style="font-weight:400;color:var(--text3)">(optional, erscheint auf Rechnung)</span></label>
            <textarea bind:value={form.freitext} placeholder="z. B. Korrekturhinweis ..." rows="2"
              style="background:var(--surface);border:1px solid var(--border);color:var(--text);padding:8px 12px;border-radius:8px;font-size:0.85rem;outline:none;resize:vertical;font-family:inherit;width:100%;box-sizing:border-box;"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-ghost" onclick={schliesseModal}>Abbrechen</button>
          <button class="btn-primary" onclick={erstelleRechnung} disabled={modalLaeuft || !!duplikatRechnung}>
            {modalLaeuft ? '⏳ Erstelle...' : '🧾 Rechnung erstellen'}
          </button>
        </div>

        {:else}
        <!-- Tab: Nachholen -->
        <div class="modal-body">
          {#if nachholLaeuft}
            <div class="status-info">⏳ Lade versendete Bestellungen ohne Rechnung...</div>
          {:else if nachholErgebnis}
            <div class="nachhol-ergebnis">
              <div class="ergebnis-icon">{nachholErgebnis.fehler === 0 ? '✅' : '⚠️'}</div>
              <div class="ergebnis-text">
                <strong>{nachholErgebnis.erstellt}</strong> Rechnung{nachholErgebnis.erstellt !== 1 ? 'en' : ''} erstellt
                {#if nachholErgebnis.fehler > 0}
                  — <span style="color:#ef4444"><strong>{nachholErgebnis.fehler}</strong> Fehler</span>
                {/if}
              </div>
            </div>
            <div class="modal-footer">
              <button class="btn-primary" onclick={schliesseModal}>Schließen</button>
            </div>
          {:else if nachholErstellen}
            <div class="nachhol-progress-wrap">
              <div class="nachhol-progress-bar"><div class="nachhol-progress-fill" style="width:{nachholFortschritt}%"></div></div>
              <div class="nachhol-progress-text">{nachholFortschritt}%</div>
            </div>
            <p style="text-align:center;font-size:0.82rem;color:var(--text2)">Rechnungen werden erstellt...</p>
          {:else if nachholBestellungen.length === 0}
            <div class="nachhol-leer">
              <div style="font-size:2rem;margin-bottom:8px">🎉</div>
              <p style="color:var(--text2);font-size:0.85rem">Alle versendeten Bestellungen haben bereits eine Rechnung.</p>
            </div>
            <div class="modal-footer">
              <button class="btn-ghost" onclick={schliesseModal}>Schließen</button>
              <button class="btn-ghost btn-sm" onclick={ladeVersendeteOhneRechnung}>🔄 Erneut prüfen</button>
            </div>
          {:else}
            <div class="nachhol-info">
              <strong>{nachholBestellungen.length}</strong> versendete Bestellung{nachholBestellungen.length !== 1 ? 'en' : ''} ohne Rechnung gefunden.
              Wähle aus, für welche Rechnungen erstellt werden sollen.
            </div>
            <div class="nachhol-liste">
              <div class="nachhol-header">
                <label class="chk-label" style="width:auto;padding:0">
                  <input type="checkbox"
                    checked={nachholBestellungen.every(o => o.ausgewaehlt)}
                    onchange={() => { const alleSel = nachholBestellungen.every(o => o.ausgewaehlt); nachholBestellungen = nachholBestellungen.map(o => ({...o, ausgewaehlt: !alleSel})); }} />
                </label>
                <span class="nachhol-h-col">Bestellnr.</span>
                <span class="nachhol-h-col nachhol-h-name">Käufer</span>
                <span class="nachhol-h-col nachhol-h-artikel">Artikel</span>
                <span class="nachhol-h-col" style="text-align:right">Betrag</span>
              </div>
              {#each nachholBestellungen as o, i}
                <div class="nachhol-item" class:nachhol-deaktiviert={!o.ausgewaehlt}>
                  <label class="chk-label" style="width:auto;padding:0">
                    <input type="checkbox" bind:checked={nachholBestellungen[i].ausgewaehlt} />
                  </label>
                  <span class="nachhol-col nachhol-orderid">{o.order_id || '—'}</span>
                  <span class="nachhol-col nachhol-name">{o.buyer_name || '—'}</span>
                  <span class="nachhol-col nachhol-artikel">{o.artikel_name || '—'}</span>
                  <span class="nachhol-col" style="text-align:right;font-weight:600">{parseFloat(o.gesamt || 0).toFixed(2)} €</span>
                </div>
              {/each}
            </div>
            <div class="modal-footer">
              <button class="btn-ghost" onclick={schliesseModal}>Abbrechen</button>
              <button class="btn-ghost btn-sm" onclick={ladeVersendeteOhneRechnung}>🔄 Aktualisieren</button>
              <button class="btn-primary" onclick={nachholRechnungenErstellen}
                disabled={nachholBestellungen.filter(o => o.ausgewaehlt).length === 0}>
                🧾 {nachholBestellungen.filter(o => o.ausgewaehlt).length} Rechnung{nachholBestellungen.filter(o => o.ausgewaehlt).length !== 1 ? 'en' : ''} erstellen
              </button>
            </div>
          {/if}
        </div>
        {/if}

      {:else if modalModus === 'bearbeiten'}
        <div class="modal-hdr">
          <span class="modal-titel">✏️ Rechnung bearbeiten — {modalRechnung?.rechnung_nr}</span>
          <button class="icon-btn" onclick={schliesseModal}>✕</button>
        </div>
        <div class="modal-body">
          <div class="hinweis hinweis-gelb">Die Änderungen werden direkt an der Rechnung gespeichert. Bitte Grund angeben.</div>
          <div class="form-grid">
            <div class="form-group"><label>Bestellnr. / Referenz</label><input bind:value={form.order_id} placeholder="optional" /></div>
            <div class="form-group"><label>Käufer *</label><input bind:value={form.kaeufer_name} placeholder="Max Mustermann" /></div>
            <div class="form-group"><label>E-Mail</label><input bind:value={form.kaeufer_email} type="email" placeholder="max@example.com" /></div>
            <div class="form-group"><label>Straße</label><input bind:value={form.kaeufer_strasse} placeholder="Musterstr. 1" /></div>
            <div class="form-group form-2col">
              <div class="form-group"><label>PLZ</label><input bind:value={form.kaeufer_plz} placeholder="12345" /></div>
              <div class="form-group"><label>Ort</label><input bind:value={form.kaeufer_ort} placeholder="Berlin" /></div>
            </div>
            <div class="form-group"><label>Land</label><input bind:value={form.kaeufer_land} placeholder="DE" /></div>
            </div>
          <!-- Positionen-Editor -->
          <div class="pos-section">
            <div class="pos-header">
              <span class="pos-titel">Positionen</span>
              <button class="btn-ghost btn-sm" type="button" onclick={addPosition}>+ Position</button>
            </div>
            {#each positionen as pos, i}
              <div class="pos-row">
                <div class="pos-nr">{i + 1}</div>
                <div class="pos-fields">
                  <div class="pos-field pos-field-wide">
                    <label>Bezeichnung *</label>
                    <input bind:value={positionen[i].bezeichnung} placeholder="Produktname" />
                  </div>
                  <div class="pos-field">
                    <label>Art-Nr.</label>
                    <input bind:value={positionen[i].artikel_nr} placeholder="SKU" />
                  </div>
                  <div class="pos-field">
                    <label>Menge</label>
                    <input bind:value={positionen[i].menge} type="number" min="1" />
                  </div>
                  <div class="pos-field">
                    <label>EP Brutto *</label>
                    <input bind:value={positionen[i].einzelpreis} type="number" step="0.01" placeholder="9.99" />
                  </div>
                  <div class="pos-field">
                    <label>MwSt.</label>
                    <select bind:value={positionen[i].mwst_satz}>
                      {#each mwstOptionen as opt}
                        <option value={opt.wert}>{opt.label}</option>
                      {/each}
                    </select>
                  </div>
                  <div class="pos-field pos-field-summe">
                    <label>Brutto</label>
                    <span class="pos-betrag">{fmt(berechnetePositionen[i]?.brutto || 0)} €</span>
                  </div>
                  {#if positionen.length > 1}
                    <button class="pos-remove" type="button" onclick={() => removePosition(i)} title="Entfernen">✕</button>
                  {/if}
                </div>
              </div>
            {/each}
            <div class="pos-summen">
              <div class="pos-summen-zeile"><span>Netto</span><span>{fmt(summeNettoBer)} €</span></div>
              <div class="pos-summen-zeile"><span>MwSt.</span><span>{fmt(summeSteuerBer)} €</span></div>
              <div class="pos-summen-zeile pos-summen-brutto"><span>Brutto</span><span>{fmt(summeBruttoBer)} €</span></div>
            </div>
          </div>
          <!-- Freitext -->
          <div class="form-group" style="margin-top:12px">
            <label>Freitext / Hinweis <span style="font-weight:400;color:var(--text3)">(optional, erscheint auf Rechnung)</span></label>
            <textarea bind:value={form.freitext} placeholder="z. B. Korrekturhinweis ..." rows="2"
              style="background:var(--surface);border:1px solid var(--border);color:var(--text);padding:8px 12px;border-radius:8px;font-size:0.85rem;outline:none;resize:vertical;font-family:inherit;width:100%;box-sizing:border-box;"></textarea>
    </div>     
          <div class="form-group" style="margin-top:18px">
            <label>Grund der Änderung * <span style="font-weight:400;color:var(--text3)">(wird intern gespeichert)</span></label>
            <textarea bind:value={aenderungsgrund} placeholder="z. B. Käufer hat neue Lieferadresse mitgeteilt ..." rows="3"
              style="background:var(--surface);border:1px solid var(--border);color:var(--text);padding:8px 12px;border-radius:8px;font-size:0.85rem;outline:none;resize:vertical;font-family:inherit;width:100%;box-sizing:border-box;"></textarea>
            {#if !aenderungsgrund.trim()}<p class="form-fehler">Pflichtfeld</p>{/if}
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-ghost" onclick={schliesseModal}>Abbrechen</button>
          <button class="btn-primary" onclick={speichereBearbeitung} disabled={modalLaeuft || !aenderungsgrund.trim()}>
            {modalLaeuft ? '⏳ Speichere...' : '💾 Änderung speichern'}
          </button>
        </div>
      {/if}

    </div>
  </div>
{/if}

<!-- EINZEL E-MAIL MODAL -->
{#if sendenModal}
  <div class="modal-overlay" onclick={() => sendenModal = false}>
    <div class="modal-box modal-klein" onclick={(e) => e.stopPropagation()}>
      <div class="modal-hdr">
        <span class="modal-titel">📧 Rechnung per E-Mail senden</span>
        <button class="icon-btn" onclick={() => sendenModal = false}>✕</button>
      </div>
      <div class="modal-body">
        <div class="senden-info">
          <div class="senden-nr">{sendenRechnung?.rechnung_nr}</div>
          <div class="senden-kaeufer">{sendenRechnung?.kaeufer_name}</div>
          <div class="senden-betrag">{fmt(sendenRechnung?.brutto_betrag)} EUR</div>
        </div>
        <div class="form-group">
          <label>E-Mail-Adresse *</label>
          <input bind:value={sendenEmail} type="email" placeholder="kaeufer@example.com" />
          {#if !sendenRechnung?.kaeufer_email}
            <span class="hinweis-klein" style="color:#d97706">⚠️ Keine E-Mail in Rechnung hinterlegt</span>
          {/if}
        </div>
        <p style="font-size:0.78rem;color:var(--text3);margin-top:8px;line-height:1.5">
          Die Rechnung wird als PDF-Anhang mit deiner konfigurierten SMTP-Vorlage gesendet.
          (<a href="/einstellungen/email" style="color:var(--primary)">E-Mail Einstellungen</a>)
        </p>
      </div>
      <div class="modal-footer">
        <button class="btn-ghost" onclick={() => sendenModal = false}>Abbrechen</button>
        <button class="btn-primary" onclick={sendeRechnung} disabled={sendenLaeuft || !sendenEmail}>
          {sendenLaeuft ? '⏳ Sende...' : '📤 Jetzt senden'}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- BULK E-MAIL MODAL -->
{#if bulkEmailModal}
  <div class="modal-overlay" onclick={() => { if (!bulkEmailLaeuft) bulkEmailModal = false; }}>
    <div class="modal-box modal-bulk" onclick={(e) => e.stopPropagation()}>
      <div class="modal-hdr">
        <div>
          <span class="modal-titel">📧 Rechnungen per E-Mail senden</span>
          <div class="modal-sub">{bulkEmailListe.filter(i => i.einschliessen && i.email?.trim()).length} von {bulkEmailListe.length} Rechnungen werden gesendet</div>
        </div>
        {#if !bulkEmailLaeuft}
          <button class="icon-btn" onclick={() => bulkEmailModal = false}>✕</button>
        {/if}
      </div>
      <div class="modal-body">

        {#if bulkEmailErgebnis}
          <!-- Ergebnis anzeigen -->
          <div class="bulk-ergebnis">
            <div class="ergebnis-icon">{bulkEmailErgebnis.fehler === 0 ? '✅' : '⚠️'}</div>
            <div class="ergebnis-text">
              <strong>{bulkEmailErgebnis.gesendet}</strong> Rechnung{bulkEmailErgebnis.gesendet !== 1 ? 'en' : ''} erfolgreich gesendet
              {#if bulkEmailErgebnis.fehler > 0}
                — <span style="color:#ef4444"><strong>{bulkEmailErgebnis.fehler}</strong> Fehler</span>
              {/if}
            </div>
          </div>
          <div class="bulk-liste">
            {#each bulkEmailListe as item}
              <div class="bulk-item {item.status ? 'bulk-item-' + item.status : ''}">
                <div class="bulk-item-nr">{item.rechnung.rechnung_nr}</div>
                <div class="bulk-item-name">{item.rechnung.kaeufer_name}</div>
                <div class="bulk-item-email">{item.email || '—'}</div>
                <div class="bulk-item-status">
                  {#if item.status === 'success'}✅{:else if item.status === 'error'}❌{:else if item.status === 'keine-email'}⚠️ keine E-Mail{:else}—{/if}
                </div>
              </div>
            {/each}
          </div>
        {:else if bulkEmailLaeuft}
          <!-- Fortschritt -->
          <div class="bulk-progress-wrap">
            <div class="bulk-progress-bar">
              <div class="bulk-progress-fill" style="width:{bulkEmailFortschritt}%"></div>
            </div>
            <div class="bulk-progress-text">{bulkEmailFortschritt}%</div>
          </div>
          <div class="bulk-liste">
            {#each bulkEmailListe as item}
              <div class="bulk-item {item.status ? 'bulk-item-' + item.status : ''}">
                <div class="bulk-item-nr">{item.rechnung.rechnung_nr}</div>
                <div class="bulk-item-name">{item.rechnung.kaeufer_name}</div>
                <div class="bulk-item-email">{item.email || '—'}</div>
                <div class="bulk-item-status">
                  {#if item.status === 'success'}✅{:else if item.status === 'error'}❌{:else if item.status === 'keine-email'}⚠️{:else}⏳{/if}
                </div>
              </div>
            {/each}
          </div>
        {:else}
          <!-- Vorschau & Bearbeitung -->
          <p style="font-size:0.8rem;color:var(--text2);margin-bottom:12px;line-height:1.5">
            Überprüfe die E-Mail-Adressen. Du kannst einzelne Rechnungen abwählen oder E-Mail-Adressen korrigieren.
          </p>
          <div class="bulk-liste">
            {#each bulkEmailListe as item, i}
              <div class="bulk-item {!item.einschliessen ? 'bulk-item-deaktiviert' : ''}">
                <label class="chk-label" style="width:auto;height:auto;padding:0">
                  <input type="checkbox" bind:checked={item.einschliessen} style="width:14px;height:14px;accent-color:var(--primary)" />
                </label>
                <div class="bulk-item-nr">{item.rechnung.rechnung_nr}</div>
                <div class="bulk-item-name">{item.rechnung.kaeufer_name}</div>
                <input class="bulk-email-input" bind:value={item.email} type="email" placeholder="E-Mail eingeben..." disabled={!item.einschliessen} />
                {#if item.einschliessen && !item.email?.trim()}
                  <span style="color:#d97706;font-size:0.75rem;white-space:nowrap">⚠️ fehlt</span>
                {/if}
              </div>
            {/each}
          </div>
          {#if bulkEmailListe.some(i => i.einschliessen && !i.email?.trim())}
            <div class="hinweis hinweis-gelb" style="margin-top:10px">
              ⚠️ Rechnungen ohne E-Mail-Adresse werden übersprungen.
            </div>
          {/if}
        {/if}
      </div>
      <div class="modal-footer">
        {#if bulkEmailErgebnis}
          <button class="btn-primary" onclick={() => bulkEmailModal = false}>Schließen</button>
        {:else}
          <button class="btn-ghost" onclick={() => bulkEmailModal = false} disabled={bulkEmailLaeuft}>Abbrechen</button>
          <button class="btn-primary" onclick={sendeBulkEmails} disabled={bulkEmailLaeuft || bulkEmailListe.filter(i => i.einschliessen && i.email?.trim()).length === 0}>
            {bulkEmailLaeuft ? `⏳ Sende... ${bulkEmailFortschritt}%` : `📤 ${bulkEmailListe.filter(i => i.einschliessen && i.email?.trim()).length} Rechnungen senden`}
          </button>
        {/if}
      </div>
    </div>
  </div>
{/if}

<!-- STORNO MODAL -->
{#if stornoModal}
  <div class="modal-overlay" onclick={() => stornoModal = false}>
    <div class="modal-box modal-klein" onclick={(e) => e.stopPropagation()}>
      <div class="modal-hdr"><span class="modal-titel">Rechnung stornieren</span><button class="icon-btn" onclick={() => stornoModal = false}>✕</button></div>
      <div class="modal-body">
        <p class="modal-info">Möchtest du die Rechnung <strong>{stornoRechnung?.rechnung_nr}</strong> wirklich stornieren? Es wird eine Stornorechnung erstellt.</p>
      </div>
      <div class="modal-footer">
        <button class="btn-ghost" onclick={() => stornoModal = false}>Abbrechen</button>
        <button class="btn-danger" onclick={erstelleStorno} disabled={stornoLaeuft}>{stornoLaeuft ? 'Storniere...' : 'Jetzt stornieren'}</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .page-container { display:flex; flex-direction:column; gap:16px; padding:24px; width:100%; box-sizing:border-box; }
  .page-hdr { display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap; }
  .page-title { font-size:1.4rem; font-weight:700; color:var(--text); }
  .page-sub { font-size:0.83rem; color:var(--text2); margin-top:2px; }
  .hdr-actions { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
  .hdr-suche { display:flex; align-items:center; gap:8px; background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:6px 10px; }
  .hdr-suche-input { background:transparent; border:none; color:var(--text); font-size:0.83rem; outline:none; width:190px; }
  .hdr-suche-input::placeholder { color:var(--text3); }
  .hdr-suche-fehler { font-size:0.75rem; color:#ef4444; white-space:nowrap; }
  .toggle-wrap { display:flex; align-items:center; gap:8px; padding:6px 12px; background:var(--surface); border:1px solid var(--border); border-radius:8px; }
  .toggle-label { font-size:0.8rem; color:var(--text2); white-space:nowrap; }
  .toggle-btn { position:relative; width:40px; height:22px; border:none; border-radius:99px; cursor:pointer; transition:background 0.2s; padding:0; flex-shrink:0; }
  .toggle-an { background:var(--primary, #2563eb); }
  .toggle-aus { background:#d1d5db; }
  .toggle-btn:disabled { opacity:0.6; cursor:not-allowed; }
  .toggle-thumb { position:absolute; top:3px; width:16px; height:16px; background:#fff; border-radius:50%; transition:left 0.2s; box-shadow:0 1px 3px rgba(0,0,0,0.2); }
  .toggle-an .toggle-thumb { left:21px; }
  .toggle-aus .toggle-thumb { left:3px; }
  .toggle-status { font-size:0.78rem; font-weight:600; white-space:nowrap; }
  .status-an { color:var(--primary, #2563eb); }
  .status-aus { color:#9ca3af; }
  .btn-primary { background:var(--primary); color:#fff; border:none; padding:8px 16px; border-radius:8px; font-size:0.84rem; cursor:pointer; transition:background 0.15s; }
  .btn-primary:hover:not(:disabled) { filter:brightness(1.08); }
  .btn-primary:disabled { opacity:0.6; cursor:not-allowed; }
  .btn-ghost { background:transparent; border:1px solid var(--border); color:var(--text2); padding:8px 16px; border-radius:8px; font-size:0.84rem; cursor:pointer; display:flex; align-items:center; gap:6px; }
  .btn-ghost:hover:not(:disabled) { border-color:var(--primary); color:var(--primary); }
  .btn-ghost:disabled { opacity:0.6; cursor:not-allowed; }
  .btn-secondary { background:var(--surface2); border:1px solid var(--border); color:var(--text); padding:8px 16px; border-radius:8px; font-size:0.84rem; cursor:pointer; }
  .btn-secondary:hover { background:var(--border); }
  .btn-danger { background:#ef4444; color:#fff; border:none; padding:8px 16px; border-radius:8px; font-size:0.84rem; cursor:pointer; }
  .btn-danger:hover:not(:disabled) { background:#dc2626; }
  .btn-danger:disabled { opacity:0.6; cursor:not-allowed; }
  .btn-email { background:#0ea5e9; color:#fff; border:none; padding:8px 14px; border-radius:8px; font-size:0.84rem; cursor:pointer; font-weight:500; }
  .btn-email:hover:not(:disabled) { background:#0284c7; }
  .btn-email:disabled { opacity:0.6; cursor:not-allowed; }
  .btn-email-sm { background:#0ea5e9; color:#fff; border:none; padding:6px 12px; border-radius:8px; font-size:0.8rem; cursor:pointer; }
  .btn-email-sm:hover { background:#0284c7; }
  .btn-sm { padding:6px 12px; font-size:0.8rem; }
  .btn-link { background:none; border:none; color:var(--primary); font-size:0.82rem; cursor:pointer; text-decoration:underline; padding:0; font-weight:600; }
  .icon-btn { background:transparent; border:none; color:var(--text2); padding:5px; border-radius:6px; cursor:pointer; display:inline-flex; align-items:center; transition:color 0.15s, background 0.15s; }
  .icon-btn:hover { color:var(--primary); background:var(--surface2); }
  .icon-btn-email:hover { color:#0ea5e9; background:#f0f9ff; }
  .icon-btn-edit:hover { color:#7c3aed; background:#f5f3ff; }
  .icon-btn-danger:hover { color:#ef4444; background:#fef2f2; }
  .icon-btn-erechnung:hover { color:#0891b2; background:#ecfeff; }
  .erechnung-dropdown-fixed { position:fixed; background:var(--surface); border:1px solid var(--border); border-radius:8px; box-shadow:0 6px 24px rgba(0,0,0,0.18); z-index:9999; min-width:270px; overflow:hidden; }
  .erechnung-dropdown-fixed button { display:block; width:100%; text-align:left; padding:10px 16px; background:transparent; border:none; color:var(--text); font-size:0.82rem; cursor:pointer; white-space:nowrap; }
  .erechnung-dropdown-fixed button:hover { background:var(--surface2); color:var(--primary); }
  .kpi-grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(150px, 1fr)); gap:12px; }
  .kpi-card { background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:16px 18px; }
  .kpi-card-wide { grid-column:span 2; }
  .kpi-label { font-size:0.75rem; color:var(--text2); margin-bottom:6px; }
  .kpi-value { font-size:1.4rem; font-weight:700; color:var(--text); }
  .kpi-blue { color:var(--primary); }
  .kpi-yellow { color:#d97706; }
  .kpi-red { color:#ef4444; }
  .toolbar { display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap; }
  .filter-tabs { display:flex; gap:4px; flex-wrap:wrap; }
  .filter-tab { background:transparent; border:none; padding:7px 12px; border-radius:7px; font-size:0.82rem; color:var(--text2); cursor:pointer; display:flex; align-items:center; gap:5px; }
  .filter-tab:hover { background:var(--surface2); color:var(--text); }
  .filter-tab.active { background:var(--surface2); color:var(--text); font-weight:600; }
  .tab-count { background:var(--border); color:var(--text2); font-size:0.72rem; padding:1px 6px; border-radius:99px; }
  .filter-tab.active .tab-count { background:var(--primary-light); color:var(--primary); }
  .toolbar-right { display:flex; gap:10px; align-items:center; }
  .select-klein { background:var(--surface); border:1px solid var(--border); color:var(--text); padding:7px 10px; border-radius:8px; font-size:0.83rem; cursor:pointer; outline:none; }
  .bulk-bar { display:flex; align-items:center; justify-content:space-between; gap:12px; background:var(--primary-light); border:1px solid var(--border); border-radius:8px; padding:8px 14px; font-size:0.83rem; color:var(--primary); flex-wrap:wrap; }
  .tabellen-wrapper { background:var(--surface); border:1px solid var(--border); border-radius:10px; overflow:hidden; }
  .tabelle { width:100%; border-collapse:collapse; font-size:0.83rem; }
  .tabelle thead tr { background:var(--surface2); }
  .tabelle th { padding:10px 12px; text-align:left; font-weight:600; font-size:0.75rem; color:var(--text2); border-bottom:1px solid var(--border); white-space:nowrap; }
  .th-check { width:36px; }
  .th-right { text-align:right; }
  .th-actions { width:160px; }
  .tbl-row { border-bottom:1px solid var(--border); cursor:pointer; transition:background 0.12s; }
  .tbl-row:last-child { border-bottom:none; }
  .tbl-row:hover { background:var(--surface2); }
  .tabelle td { padding:10px 12px; color:var(--text); vertical-align:middle; }
  .td-check { width:36px; padding:0 !important; }
  .td-nr { font-weight:600; white-space:nowrap; color:var(--primary); }
  .td-datum { white-space:nowrap; color:var(--text2); font-size:0.8rem; }
  .td-kaeufer { max-width:180px; }
  .td-email { font-size:0.75rem; color:var(--text3); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:160px; }
  .td-artikel { max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--text2); }
  .td-right { text-align:right; white-space:nowrap; }
  .td-bold { font-weight:600; }
  .td-actions { white-space:nowrap; }
  .td-gesendet-an { font-size:0.72rem; color:#16a34a; margin-top:2px; }
  .badge { display:inline-block; padding:2px 8px; border-radius:99px; font-size:0.73rem; font-weight:500; white-space:nowrap; }
  .badge-erstellt { background:#fffbeb; color:#d97706; }
  .badge-gesendet { background:#f0fdf4; color:#16a34a; }
  .badge-storniert { background:#fef2f2; color:#dc2626; }
  .status-info { padding:40px; text-align:center; color:var(--text2); font-size:0.85rem; }
  .status-fehler { color:#ef4444; }
  .leer-state { padding:60px 40px; display:flex; flex-direction:column; align-items:center; gap:12px; color:var(--text3); text-align:center; }
  .leer-state p { color:var(--text2); font-size:0.9rem; }
  .footer-bar { display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap; padding-top:4px; }
  .footer-summen { display:flex; gap:20px; align-items:center; font-size:0.82rem; color:var(--text2); flex-wrap:wrap; }
  .footer-summen strong { color:var(--text); }
  .storno-summe { color:#ef4444; }
  .footer-count { color:var(--text3); }
  .pagination { display:flex; gap:4px; align-items:center; }
  .page-btn { min-width:32px; height:32px; background:var(--surface); border:1px solid var(--border); color:var(--text2); border-radius:7px; font-size:0.82rem; cursor:pointer; display:flex; align-items:center; justify-content:center; }
  .page-btn:hover:not(:disabled) { border-color:var(--primary); color:var(--primary); }
  .page-btn.active { background:var(--primary); border-color:var(--primary); color:#fff; font-weight:600; }
  .page-btn:disabled { opacity:0.4; cursor:not-allowed; }
  /* Modals */
  .modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.45); z-index:1000; display:flex; align-items:center; justify-content:center; padding:20px; }
  .modal-box { background:var(--surface); border:1px solid var(--border); border-radius:14px; width:100%; max-height:90vh; display:flex; flex-direction:column; box-shadow:0 20px 60px rgba(0,0,0,0.2); }
  .modal-klein { max-width:420px; }
  .modal-universal { max-width:720px; }
  .modal-bulk { max-width:680px; }
  .modal-hdr { display:flex; align-items:center; justify-content:space-between; padding:18px 20px 14px; border-bottom:1px solid var(--border); flex-shrink:0; }
  .modal-titel { font-size:1rem; font-weight:600; color:var(--text); }
  .modal-sub { font-size:0.75rem; color:var(--text3); margin-top:2px; }
  .modal-body { padding:20px; overflow-y:auto; flex:1; }
  .modal-footer { display:flex; gap:8px; justify-content:flex-end; padding:14px 20px 18px; border-top:1px solid var(--border); flex-wrap:wrap; flex-shrink:0; }
  .modal-info { font-size:0.85rem; color:var(--text2); margin-bottom:14px; line-height:1.5; }
  .modal-info strong { color:var(--text); }
  /* Senden Info Box */
  .senden-info { background:var(--surface2); border-radius:8px; padding:12px 14px; margin-bottom:16px; display:flex; gap:12px; align-items:center; flex-wrap:wrap; }
  .senden-nr { font-size:0.82rem; font-weight:700; color:var(--primary); white-space:nowrap; }
  .senden-kaeufer { font-size:0.82rem; color:var(--text); flex:1; }
  .senden-betrag { font-size:0.85rem; font-weight:700; color:var(--text); white-space:nowrap; }
  /* Bulk E-Mail Liste */
  .bulk-liste { display:flex; flex-direction:column; gap:6px; margin-top:8px; max-height:300px; overflow-y:auto; }
  .bulk-item { display:flex; align-items:center; gap:10px; padding:8px 12px; background:var(--surface2); border-radius:8px; border:1px solid var(--border); font-size:0.8rem; }
  .bulk-item-deaktiviert { opacity:0.45; }
  .bulk-item-success { border-color:#bbf7d0; background:#f0fdf4; }
  .bulk-item-error { border-color:#fecaca; background:#fef2f2; }
  .bulk-item-nr { font-weight:600; color:var(--primary); white-space:nowrap; min-width:90px; }
  .bulk-item-name { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--text); }
  .bulk-item-email { flex:1.5; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--text2); }
  .bulk-item-status { white-space:nowrap; min-width:24px; text-align:center; }
  .bulk-email-input { flex:1.5; background:var(--surface); border:1px solid var(--border); color:var(--text); padding:4px 8px; border-radius:6px; font-size:0.78rem; outline:none; min-width:0; }
  .bulk-email-input:focus { border-color:var(--primary); }
  .bulk-email-input:disabled { opacity:0.5; cursor:not-allowed; }
  .bulk-progress-wrap { display:flex; align-items:center; gap:12px; margin-bottom:14px; }
  .bulk-progress-bar { flex:1; height:8px; background:var(--border); border-radius:99px; overflow:hidden; }
  .bulk-progress-fill { height:100%; background:var(--primary); border-radius:99px; transition:width 0.3s; }
  .bulk-progress-text { font-size:0.8rem; font-weight:600; color:var(--primary); min-width:36px; text-align:right; }
  .bulk-ergebnis { display:flex; align-items:center; gap:12px; padding:12px 14px; background:var(--surface2); border-radius:8px; margin-bottom:12px; }
  .ergebnis-icon { font-size:1.4rem; }
  .ergebnis-text { font-size:0.85rem; color:var(--text); }
  /* Formulare */
  .hinweis { border-radius:8px; padding:10px 14px; font-size:0.82rem; margin-bottom:8px; line-height:1.5; display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
  .hinweis-rot { background:#fef2f2; border:1px solid #fecaca; color:#dc2626; }
  .hinweis-gruen { background:#f0fdf4; border:1px solid #bbf7d0; color:#16a34a; }
  .hinweis-gelb { background:#fffbeb; border:1px solid #fde68a; color:#92400e; }
  .hinweis-blau { background:#eff6ff; border:1px solid #bfdbfe; color:#1d4ed8; }
  .hinweis-klein { font-size:0.72rem; color:var(--text3); }
  .detail-meta { display:flex; align-items:center; justify-content:space-between; margin-bottom:16px; }
  .detail-datum { font-size:0.8rem; color:var(--text2); }
  .betraege-box { background:var(--surface2); border-radius:8px; padding:12px; display:flex; flex-direction:column; gap:6px; }
  .betrag-zeile { display:flex; justify-content:space-between; font-size:0.82rem; color:var(--text2); }
  .betrag-brutto { color:var(--text); font-weight:700; font-size:0.9rem; border-top:1px solid var(--border); padding-top:6px; margin-top:2px; }
  .bm-section { margin-bottom:18px; }
  .bm-section-titel { font-size:0.75rem; font-weight:700; color:var(--text3); text-transform:uppercase; letter-spacing:0.06em; margin-bottom:10px; padding-bottom:6px; border-bottom:1px solid var(--border); }
  .bm-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
  .bm-field { display:flex; flex-direction:column; gap:3px; }
  .bm-full { grid-column: 1 / -1; }
  .bm-label { font-size:0.72rem; color:var(--text3); font-weight:500; }
  .bm-value { font-size:0.85rem; color:var(--text); font-weight:500; line-height:1.4; }
  .form-grid { display:flex; flex-direction:column; gap:14px; }
  .form-group { display:flex; flex-direction:column; gap:5px; }
  .form-2col { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
  .form-group label { font-size:0.78rem; color:var(--text2); font-weight:500; }
  .form-group input { background:var(--surface); border:1px solid var(--border); color:var(--text); padding:8px 12px; border-radius:8px; font-size:0.85rem; outline:none; }
  .form-group input:focus { border-color:var(--primary); }
  .form-group input::placeholder { color:var(--text3); }
  .form-fehler { color:#ef4444; font-size:0.75rem; margin-top:3px; }
  .chk-label { display:flex; align-items:center; justify-content:center; width:100%; height:100%; min-height:20px; cursor:pointer; padding:4px; box-sizing:border-box; }
  .chk-label input[type="checkbox"] { width:15px; height:15px; cursor:pointer; accent-color:var(--primary); margin:0; }
  /* Modal Tabs */
  .modal-tabs { display:flex; border-bottom:1px solid var(--border); padding:0 20px; gap:4px; flex-shrink:0; }
  .modal-tab { background:none; border:none; border-bottom:2px solid transparent; padding:10px 16px; font-size:0.82rem; font-weight:600; color:var(--text2); cursor:pointer; transition:all 0.15s; white-space:nowrap; }
  .modal-tab:hover { color:var(--text); }
  .modal-tab.active { color:var(--primary); border-bottom-color:var(--primary); }
  /* Nachhol-Funktion */
  .nachhol-info { background:var(--surface2); border-radius:8px; padding:12px 14px; font-size:0.82rem; color:var(--text2); margin-bottom:12px; line-height:1.5; }
  .nachhol-info strong { color:var(--text); }
  .nachhol-liste { display:flex; flex-direction:column; gap:0; max-height:340px; overflow-y:auto; border:1px solid var(--border); border-radius:8px; }
  .nachhol-header { display:flex; align-items:center; gap:10px; padding:8px 12px; background:var(--surface2); font-size:0.72rem; font-weight:700; color:var(--text3); text-transform:uppercase; letter-spacing:0.5px; border-bottom:1px solid var(--border); position:sticky; top:0; z-index:1; }
  .nachhol-h-col { flex:1; min-width:0; }
  .nachhol-h-name { flex:1.2; }
  .nachhol-h-artikel { flex:1.5; }
  .nachhol-item { display:flex; align-items:center; gap:10px; padding:8px 12px; font-size:0.8rem; border-bottom:1px solid var(--border); transition:background 0.1s; }
  .nachhol-item:last-child { border-bottom:none; }
  .nachhol-item:hover { background:var(--surface2); }
  .nachhol-deaktiviert { opacity:0.4; }
  .nachhol-col { flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .nachhol-orderid { font-family:monospace; font-size:0.75rem; color:var(--primary); font-weight:600; }
  .nachhol-name { flex:1.2; }
  .nachhol-artikel { flex:1.5; color:var(--text2); }
  .nachhol-leer { text-align:center; padding:40px 20px; }
  .nachhol-ergebnis { display:flex; align-items:center; gap:12px; padding:16px; background:var(--surface2); border-radius:8px; margin-bottom:12px; }
  .nachhol-ergebnis .ergebnis-icon { font-size:1.4rem; }
  .nachhol-ergebnis .ergebnis-text { font-size:0.85rem; color:var(--text); }
  .nachhol-progress-wrap { display:flex; align-items:center; gap:12px; margin-bottom:14px; padding:0 20px; }
  .nachhol-progress-bar { flex:1; height:8px; background:var(--border); border-radius:99px; overflow:hidden; }
  .nachhol-progress-fill { height:100%; background:var(--primary); border-radius:99px; transition:width 0.3s; }
  .nachhol-progress-text { font-size:0.8rem; font-weight:600; color:var(--primary); min-width:36px; text-align:right; }
  /* Positionen-Editor */
  .pos-section { margin-top:16px; border:1px solid var(--border); border-radius:10px; overflow:hidden; }
  .pos-header { display:flex; align-items:center; justify-content:space-between; padding:10px 14px; background:var(--surface2); border-bottom:1px solid var(--border); }
  .pos-titel { font-size:0.82rem; font-weight:600; color:var(--text); }
  .pos-row { display:flex; gap:10px; padding:12px 14px; border-bottom:1px solid var(--border); align-items:flex-end; }
  .pos-row:last-of-type { border-bottom:none; }
  .pos-nr { font-size:0.8rem; font-weight:700; color:var(--text3); min-width:20px; padding-bottom:8px; }
  .pos-fields { display:flex; gap:8px; flex-wrap:wrap; flex:1; align-items:flex-end; }
  .pos-field { display:flex; flex-direction:column; gap:3px; }
  .pos-field label { font-size:0.72rem; color:var(--text3); font-weight:500; }
  .pos-field input, .pos-field select { background:var(--surface); border:1px solid var(--border); color:var(--text); padding:6px 10px; border-radius:6px; font-size:0.82rem; outline:none; }
  .pos-field input:focus, .pos-field select:focus { border-color:var(--primary); }
  .pos-field-wide { flex:2; min-width:160px; }
  .pos-field-wide input { width:100%; }
  .pos-field-summe { min-width:80px; }
  .pos-betrag { font-size:0.85rem; font-weight:600; color:var(--text); padding:6px 0; }
  .pos-remove { background:none; border:none; color:var(--text3); font-size:0.8rem; cursor:pointer; padding:6px; border-radius:4px; }
  .pos-remove:hover { color:#ef4444; background:#fef2f2; }
  .pos-summen { padding:10px 14px; background:var(--surface2); border-top:1px solid var(--border); display:flex; flex-direction:column; gap:4px; align-items:flex-end; }
  .pos-summen-zeile { display:flex; gap:20px; font-size:0.82rem; color:var(--text2); }
  .pos-summen-zeile span:last-child { min-width:80px; text-align:right; }
  .pos-summen-brutto { font-weight:700; color:var(--text); font-size:0.9rem; border-top:1px solid var(--border); padding-top:6px; margin-top:2px; }
  /* Detail-Positionen-Tabelle */
  .detail-pos-tabelle { width:100%; border-collapse:collapse; font-size:0.82rem; }
  .detail-pos-tabelle th { padding:6px 8px; text-align:left; font-size:0.72rem; color:var(--text3); font-weight:600; border-bottom:1px solid var(--border); }
  .detail-pos-tabelle td { padding:6px 8px; border-bottom:1px solid var(--border); color:var(--text); }
  .detail-pos-tabelle tr:last-child td { border-bottom:none; }
  .pos-artnr { font-size:0.72rem; color:var(--text3); }
</style>
