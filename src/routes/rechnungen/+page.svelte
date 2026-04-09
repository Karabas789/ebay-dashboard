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

  // ══ EIN UNIVERSELLES MODAL ════════════════════════════════════════
  // modus: 'neu' | 'detail' | 'bearbeiten'
  let modalOffen = $state(false);
  let modalModus = $state('neu');
  let modalRechnung = $state(null);   // bei detail/bearbeiten: die Rechnung
  let modalLaeuft = $state(false);

  // Formularfelder (neu + bearbeiten)
  let form = $state({
    order_id: '', kaeufer_name: '', kaeufer_email: '',
    kaeufer_strasse: '', kaeufer_plz: '', kaeufer_ort: '', kaeufer_land: 'DE',
    artikel_name: '', ebay_artikel_id: '', artikel_sku: '',
    menge: 1, einzelpreis: ''
  });
  let bestellungLaeuft = $state(false);
  let bestellungFehler = $state('');
  let duplikatRechnung = $state(null);
  let aenderungsgrund = $state('');

  // E-Mail Modal
  let sendenModal = $state(false);
  let sendenRechnung = $state(null);
  let sendenEmail = $state('');
  let sendenLaeuft = $state(false);

  // Storno Modal
  let stornoModal = $state(false);
  let stornoRechnung = $state(null);
  let stornoLaeuft = $state(false);

  // Auto-Rechnung Toggle
  let autoRechnungAktiv = $state(true);
  let toggleLaeuft = $state(false);

  // Schnellsuche
  let schnellsucheOrderId = $state('');
  let schnellsucheLaeuft = $state(false);
  let schnellsucheFehler = $state('');

  // E-Rechnung Dropdown
  let eRechnungMenuOffen = $state(false);
  let eRechnungRechnung = $state(null);

  // ── Helpers ──────────────────────────────────────────────────────
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
      artikel_name: '', ebay_artikel_id: '', artikel_sku: '',
      menge: 1, einzelpreis: ''
    };
    bestellungFehler = '';
    duplikatRechnung = null;
    aenderungsgrund = '';
  }

  // ── Modal öffnen ──────────────────────────────────────────────────

  // Neu: leeres Formular (oder vorausgefüllt)
  function oeffneNeuModal(vorbelegung = null) {
    resetForm();
    if (vorbelegung) form = { ...form, ...vorbelegung };
    modalRechnung = null;
    modalModus = 'neu';
    modalOffen = true;
  }

  // Detail: Rechnung anzeigen (read-only)
  function oeffneDetailModal(r) {
    resetForm();
    modalRechnung = r;
    modalModus = 'detail';
    modalOffen = true;
  }

  // Bearbeiten: Rechnung editieren (mit Änderungsgrund)
  function oeffneBearbeitenModal(r) {
    resetForm();
    form = {
      order_id:        r.order_id        || '',
      kaeufer_name:    r.kaeufer_name    || '',
      kaeufer_email:   r.kaeufer_email   || '',
      kaeufer_strasse: r.kaeufer_strasse || '',
      kaeufer_plz:     r.kaeufer_plz     || '',
      kaeufer_ort:     r.kaeufer_ort     || '',
      kaeufer_land:    r.kaeufer_land    || 'DE',
      artikel_name:    r.artikel_name    || '',
      ebay_artikel_id: r.ebay_artikel_id || '',
      artikel_sku:     r.artikel_sku     || '',
      menge:           r.artikel_menge   || 1,
      einzelpreis:     parseFloat(r.einzelpreis) || parseFloat(r.brutto_betrag) || 0,
    };
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
  }

  // ── Bestellnummer laden (im Formular) ────────────────────────────
  function onOrderIdInput() {
    bestellungFehler = '';
    duplikatRechnung = null;
  }

  async function ladeBestellungDaten() {
    if (!form.order_id?.trim()) return;

    // Duplikat-Prüfung
    if (modalModus === 'neu') {
      const dup = findeVorhandeneRechnung(form.order_id);
      if (dup) { duplikatRechnung = dup; return; }
    }
    duplikatRechnung = null;

    bestellungLaeuft = true;
    bestellungFehler = '';
    try {
      const data = await apiCall('bestellung-laden', {
        user_id: $currentUser?.id,
        order_id: form.order_id.trim()
      });
      if (data?.bestellung) {
        const norm = normalisiereBestellung(data.bestellung);
        form = { ...form, ...norm };
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

  // ── Schnellsuche ──────────────────────────────────────────────────
  async function schnellsucheNachOrder() {
    if (!schnellsucheOrderId.trim()) return;
    const term = schnellsucheOrderId.trim().toLowerCase();

    // Lokal suchen
    const lok = rechnungen.filter(r =>
      r.rechnung_nr?.toLowerCase().includes(term) ||
      r.kaeufer_name?.toLowerCase().includes(term) ||
      r.kaeufer_email?.toLowerCase().includes(term) ||
      r.artikel_name?.toLowerCase().includes(term) ||
      r.order_id?.toLowerCase().includes(term)
    );
    if (lok.length === 1) {
      oeffneDetailModal(lok[0]);
      schnellsucheOrderId = '';
      return;
    }
    if (lok.length > 1) {
      suchbegriff = schnellsucheOrderId.trim();
      schnellsucheOrderId = '';
      return;
    }

    // API
    schnellsucheLaeuft = true;
    schnellsucheFehler = '';
    try {
      const data = await apiCall('bestellung-laden', {
        user_id: $currentUser.id,
        suchbegriff: schnellsucheOrderId.trim()
      });
      if (data?.bestellung) {
        const b = data.bestellung;
        const norm = normalisiereBestellung(b);
        // Rechnung bereits vorhanden? → Detail anzeigen
        const vorh = findeVorhandeneRechnung(norm.order_id);
        if (vorh) {
          oeffneDetailModal(vorh);
        } else {
          // Kein Duplikat → Formular vorausgefüllt öffnen
          oeffneNeuModal(norm);
        }
        schnellsucheOrderId = '';
      } else {
        // Nichts in API → leeres Formular mit eingetragener Bestellnr.
        oeffneNeuModal({ order_id: schnellsucheOrderId.trim() });
        schnellsucheOrderId = '';
      }
    } catch(e) {
      schnellsucheFehler = 'Nichts gefunden';
    } finally {
      schnellsucheLaeuft = false;
    }
  }

  // ── Rechnung erstellen (neu) ──────────────────────────────────────
  async function erstelleRechnung() {
    if (!form.kaeufer_name || !form.artikel_name || !form.einzelpreis) {
      showToast('Bitte alle Pflichtfelder ausfüllen.'); return;
    }
    const dup = findeVorhandeneRechnung(form.order_id);
    if (dup) { duplikatRechnung = dup; return; }

    modalLaeuft = true;
    try {
      await apiCall('rechnung-erstellen', {
        user_id:         $currentUser.id,
        typ:             'rechnung',
        order_id:        form.order_id || '',
        kaeufer_name:    form.kaeufer_name,
        kaeufer_email:   form.kaeufer_email,
        kaeufer_strasse: form.kaeufer_strasse,
        kaeufer_plz:     form.kaeufer_plz,
        kaeufer_ort:     form.kaeufer_ort,
        kaeufer_land:    form.kaeufer_land,
        artikel_name:    form.artikel_name,
        ebay_artikel_id: form.ebay_artikel_id,
        menge:           Number(form.menge),
        einzelpreis:     Number(form.einzelpreis)
      });
      showToast('✅ Rechnung erstellt');
      schliesseModal();
      await ladeRechnungen();
    } catch(e) {
      showToast('Fehler: ' + e.message);
    } finally {
      modalLaeuft = false;
    }
  }

  // ── Rechnung bearbeiten (storno + neu mit Änderungsvermerk) ───────
  async function speichereBearbeitung() {
    if (!form.kaeufer_name || !form.artikel_name || !form.einzelpreis) {
      showToast('Bitte alle Pflichtfelder ausfüllen.'); return;
    }
    if (!aenderungsgrund.trim()) {
      showToast('Bitte Grund der Änderung angeben.'); return;
    }

    modalLaeuft = true;
    try {
      // Alte Rechnung stornieren
      await apiCall('rechnung-stornieren', {
        user_id: $currentUser.id,
        invoice_id: modalRechnung.id
      });
      // Neue Rechnung mit Änderungsvermerk erstellen
      await apiCall('rechnung-erstellen', {
        user_id:           $currentUser.id,
        typ:               'rechnung',
        order_id:          form.order_id || '',
        kaeufer_name:      form.kaeufer_name,
        kaeufer_email:     form.kaeufer_email,
        kaeufer_strasse:   form.kaeufer_strasse,
        kaeufer_plz:       form.kaeufer_plz,
        kaeufer_ort:       form.kaeufer_ort,
        kaeufer_land:      form.kaeufer_land,
        artikel_name:      form.artikel_name,
        ebay_artikel_id:   form.ebay_artikel_id,
        menge:             Number(form.menge),
        einzelpreis:       Number(form.einzelpreis),
        aenderungsgrund:   aenderungsgrund.trim(),
        aenderungsdatum:   new Date().toISOString(),
        vorgaenger_nr:     modalRechnung.rechnung_nr
      });
      showToast('✅ Rechnung aktualisiert');
      schliesseModal();
      await ladeRechnungen();
    } catch(e) {
      showToast('Fehler: ' + e.message);
    } finally {
      modalLaeuft = false;
    }
  }

  // ── Auto-Rechnung ─────────────────────────────────────────────────
  async function ladeAutoRechnungStatus() {
    try {
      const data = await apiCall('auto-rechnung-einstellungen', { user_id: $currentUser.id }, 'GET');
      autoRechnungAktiv = data?.auto_rechnung_aktiv ?? true;
    } catch(e) {}
  }

  async function toggleAutoRechnung() {
    toggleLaeuft = true;
    const neuerWert = !autoRechnungAktiv;
    try {
      await apiCall('auto-rechnung-einstellungen', { user_id: $currentUser.id, aktiv: neuerWert }, 'POST');
      autoRechnungAktiv = neuerWert;
      showToast(neuerWert ? 'Auto-Rechnung aktiviert' : 'Auto-Rechnung deaktiviert');
    } catch(e) {
      showToast('Fehler beim Speichern');
    } finally {
      toggleLaeuft = false;
    }
  }

  // ── E-Mail senden ─────────────────────────────────────────────────
  function oeffneSendenModal(r) {
    sendenRechnung = r;
    sendenEmail = r.kaeufer_email || '';
    sendenModal = true;
    schliesseModal();
  }

  async function sendeRechnung() {
    if (!sendenEmail) { showToast('Bitte E-Mail eingeben.'); return; }
    sendenLaeuft = true;
    try {
      await apiCall('rechnung-senden', { invoice_id: sendenRechnung.id, user_id: $currentUser.id, to_email: sendenEmail });
      showToast('Rechnung gesendet');
      sendenModal = false;
      await ladeRechnungen();
    } catch(e) { showToast('Fehler: ' + e.message); } finally { sendenLaeuft = false; }
  }

  // ── Stornieren ────────────────────────────────────────────────────
  function oeffneStornoModal(r) {
    stornoRechnung = r;
    stornoModal = true;
    schliesseModal();
  }

  async function erstelleStorno() {
    stornoLaeuft = true;
    try {
      await apiCall('rechnung-stornieren', { user_id: $currentUser.id, invoice_id: stornoRechnung.id });
      showToast('Stornorechnung erstellt');
      stornoModal = false;
      await ladeRechnungen();
    } catch(e) { showToast('Fehler: ' + e.message); } finally { stornoLaeuft = false; }
  }

  // ── Bulk Aktionen ─────────────────────────────────────────────────
  async function bulkDrucken() {
    const liste = rechnungen.filter(r => ausgewaehlt.has(r.id));
    for (const r of liste) { await ladePDF(r); await new Promise(res => setTimeout(res, 400)); }
  }

  async function bulkEmailSenden() {
    const liste = rechnungen.filter(r => ausgewaehlt.has(r.id));
    let gesendet = 0;
    for (const r of liste) {
      if (!r.kaeufer_email) continue;
      try { await apiCall('rechnung-senden', { invoice_id: r.id, user_id: $currentUser.id, to_email: r.kaeufer_email }); gesendet++; } catch(e) {}
    }
    showToast(`${gesendet} Rechnung(en) gesendet`);
    await ladeRechnungen();
  }

  function bulkExportCSV() {
    const liste = rechnungen.filter(r => ausgewaehlt.has(r.id));
    const header = ['Rechnungsnr.','Datum','Kaeufer','E-Mail','Strasse','PLZ','Ort','Artikel','Bestellnr.','Netto','MwSt.','Brutto','Status'];
    const zeilen = liste.map(r => [
      r.rechnung_nr, fmtDatum(r.erstellt_am), r.kaeufer_name, r.kaeufer_email || '',
      r.kaeufer_strasse || '', r.kaeufer_plz || '', r.kaeufer_ort || '',
      r.artikel_name, r.order_id || '',
      fmt(r.netto_betrag), fmt(r.steuer_betrag), fmt(r.brutto_betrag), r.status
    ].map(v => `"${String(v || '').replace(/"/g, '""')}"`).join(';'));
    const csv = [header.join(';'), ...zeilen].join('\n');
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `rechnungen-export-${new Date().toISOString().slice(0,10)}.csv`;
    a.click(); URL.revokeObjectURL(url);
  }

  // ── E-Rechnung ────────────────────────────────────────────────────
  function oeffneERechnungMenu(r, e) {
    e.stopPropagation();
    if (eRechnungRechnung?.id === r.id && eRechnungMenuOffen) { eRechnungMenuOffen = false; eRechnungRechnung = null; }
    else { eRechnungRechnung = r; eRechnungMenuOffen = true; }
  }

  async function erstelleERechnung(rechnung, format) {
    eRechnungMenuOffen = false; eRechnungRechnung = null;
    showToast('E-Rechnung wird erstellt...');
    try {
      const data = await apiCall('e-rechnung-erstellen', { invoice_id: rechnung.id, user_id: $currentUser.id, format });
      if (format === 'xrechnung') {
        const blob = new Blob([data.xml], { type: 'application/xml' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a'); a.href = url; a.download = (rechnung.rechnung_nr || 'XRechnung') + '.xml'; a.click(); URL.revokeObjectURL(url);
      } else {
        const b64 = data.pdf_base64 || data.pdf;
        if (!b64) { showToast('Kein Ergebnis erhalten.'); return; }
        const blob = new Blob([Uint8Array.from(atob(b64), c => c.charCodeAt(0))], { type: 'application/pdf' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a'); a.href = url; a.download = (rechnung.rechnung_nr || 'ERechnung') + '.pdf'; a.click(); URL.revokeObjectURL(url);
      }
      showToast('E-Rechnung erstellt');
    } catch(e) { showToast('Fehler: ' + e.message); }
  }

  // ── Derived / Filter ──────────────────────────────────────────────
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
  let summeNetto     = $derived(gefiltert.filter(r => r.status !== 'storniert' && r.rechnung_typ === 'rechnung').reduce((s, r) => s + (parseFloat(r.netto_betrag) || 0), 0));
  let summeStorno    = $derived(gefiltert.filter(r => r.rechnung_typ === 'storno').reduce((s, r) => s + (parseFloat(r.brutto_betrag) || 0), 0));
  let kpiGesamt      = $derived(rechnungen.filter(r => r.rechnung_typ === 'rechnung').length);
  let kpiGesendet    = $derived(rechnungen.filter(r => r.status === 'gesendet').length);
  let kpiAusstehend  = $derived(rechnungen.filter(r => r.status === 'erstellt' && r.rechnung_typ === 'rechnung').length);
  let kpiStorniert   = $derived(rechnungen.filter(r => r.rechnung_typ === 'storno').length);
  let kpiBrutto      = $derived(rechnungen.filter(r => r.rechnung_typ === 'rechnung' && r.status !== 'storniert').reduce((s, r) => s + (parseFloat(r.brutto_betrag) || 0), 0));
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
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = (rechnung.rechnung_nr || 'Rechnung') + '.pdf'; a.click(); URL.revokeObjectURL(url);
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
  function fmt(n) { return Number(n || 0).toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
  function fmtDatum(d) { if (!d) return '-'; return new Date(d).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' }); }
  function statusBadge(r) {
    if (r.rechnung_typ === 'storno') return { label: 'Storno', cls: 'badge-storniert' };
    const map = { erstellt: { label: 'Erstellt', cls: 'badge-erstellt' }, gesendet: { label: 'Gesendet', cls: 'badge-gesendet' }, storniert: { label: 'Storniert', cls: 'badge-storniert' } };
    return map[r.status] || { label: r.status, cls: '' };
  }
  const filterTabs = [
    { key: 'alle', label: 'Alle' }, { key: 'rechnungen', label: 'Rechnungen' },
    { key: 'stornos', label: 'Stornos' }, { key: 'erstellt', label: 'Erstellt' }, { key: 'gesendet', label: 'Gesendet' }
  ];
  function tabCount(key) {
    if (key === 'alle') return rechnungen.length;
    if (key === 'rechnungen') return rechnungen.filter(r => r.rechnung_typ === 'rechnung' && r.status !== 'storniert').length;
    if (key === 'stornos') return rechnungen.filter(r => r.rechnung_typ === 'storno').length;
    if (key === 'erstellt') return rechnungen.filter(r => r.status === 'erstellt').length;
    if (key === 'gesendet') return rechnungen.filter(r => r.status === 'gesendet').length;
    return 0;
  }
</script>

<!-- PAGE -->
<div class="page-container" onclick={() => { if (eRechnungMenuOffen) { eRechnungMenuOffen = false; eRechnungRechnung = null; } }}>

  <!-- Header -->
  <div class="page-hdr">
    <div>
      <div class="page-title">Rechnungen</div>
      <div class="page-sub">Automatisch erstellte Rechnungen verwalten</div>
    </div>
    <div class="hdr-actions">
      <div class="hdr-suche">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--text3);flex-shrink:0;"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
        <input class="hdr-suche-input" type="text" placeholder="Name, Rechnungs-Nr., Bestellnr. ..."
          bind:value={schnellsucheOrderId}
          onkeydown={(e) => e.key === 'Enter' && schnellsucheNachOrder()} />
        {#if schnellsucheFehler}<span class="hdr-suche-fehler">{schnellsucheFehler}</span>{/if}
        <button class="btn-primary btn-sm" onclick={schnellsucheNachOrder} disabled={schnellsucheLaeuft || !schnellsucheOrderId.trim()}>
          {schnellsucheLaeuft ? '...' : 'Suchen'}
        </button>
      </div>
      <div class="toggle-wrap">
        <span class="toggle-label">Auto-Rechnung</span>
        <button class="toggle-btn {autoRechnungAktiv ? 'toggle-an' : 'toggle-aus'}" onclick={toggleAutoRechnung} disabled={toggleLaeuft}>
          <span class="toggle-thumb"></span>
        </button>
        <span class="toggle-status {autoRechnungAktiv ? 'status-an' : 'status-aus'}">{autoRechnungAktiv ? 'Aktiv' : 'Inaktiv'}</span>
      </div>
      <button class="btn-ghost" onclick={ladeRechnungen} disabled={loading}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/></svg>
        Aktualisieren
      </button>
      <button class="btn-primary" onclick={() => oeffneNeuModal()}>+ Rechnung erstellen</button>
    </div>
  </div>

  <!-- KPI Cards -->
  <div class="kpi-grid">
    <div class="kpi-card"><div class="kpi-label">Gesamt</div><div class="kpi-value">{kpiGesamt}</div></div>
    <div class="kpi-card"><div class="kpi-label">Gesendet</div><div class="kpi-value kpi-blue">{kpiGesendet}</div></div>
    <div class="kpi-card"><div class="kpi-label">Ausstehend</div><div class="kpi-value kpi-yellow">{kpiAusstehend}</div></div>
    <div class="kpi-card"><div class="kpi-label">Storniert</div><div class="kpi-value kpi-red">{kpiStorniert}</div></div>
    <div class="kpi-card kpi-card-wide"><div class="kpi-label">Umsatz Brutto (aktive)</div><div class="kpi-value kpi-blue">{fmt(kpiBrutto)} EUR</div></div>
    <div class="kpi-card"><div class="kpi-label">Diesen Monat</div><div class="kpi-value">{kpiDieserMonat}</div></div>
  </div>

  <!-- Toolbar -->
  <div class="toolbar">
    <div class="filter-tabs">
      {#each filterTabs as tab (tab.key)}
        <button class="filter-tab {aktiverFilter === tab.key ? 'active' : ''}" onclick={() => setFilter(tab.key)}>
          {tab.label}<span class="tab-count">{tabCount(tab.key)}</span>
        </button>
      {/each}
    </div>
    <div class="toolbar-right">
      <select class="select-klein" bind:value={proSeite} onchange={() => aktuelleSeite = 1}>
        <option value={20}>20 / Seite</option><option value={50}>50 / Seite</option><option value={100}>100 / Seite</option>
      </select>
    </div>
  </div>

  <!-- Bulk-Aktionsleiste -->
  {#if ausgewaehlt.size > 0}
    <div class="bulk-bar">
      <span><strong>{ausgewaehlt.size}</strong> Rechnung{ausgewaehlt.size > 1 ? 'en' : ''} ausgewählt</span>
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
        <button class="btn-ghost btn-sm" onclick={bulkDrucken}>PDFs laden</button>
        <button class="btn-ghost btn-sm" onclick={bulkEmailSenden}>Per E-Mail senden</button>
        <button class="btn-ghost btn-sm" onclick={bulkExportCSV}>CSV exportieren</button>
      </div>
    </div>
  {/if}

  <!-- Tabelle -->
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
            <th class="th-check" onclick={(e) => e.stopPropagation()}>
              <label class="chk-label"><input type="checkbox" checked={alleAusgewaehlt} onchange={toggleAlleAuswaehlen} /></label>
            </th>
            <th>Nummer</th><th>Datum</th><th>Käufer</th><th>Artikel</th>
            <th class="th-right">Netto</th><th class="th-right">MwSt.</th><th class="th-right">Brutto</th>
            <th>Status</th><th class="th-actions">Aktionen</th>
          </tr>
        </thead>
        <tbody>
          {#each sichtbar as r (r.id)}
            {@const badge = statusBadge(r)}
            <tr class="tbl-row" onclick={() => oeffneDetailModal(r)}>
              <td class="td-check" onclick={(e) => e.stopPropagation()}>
                <label class="chk-label"><input type="checkbox" checked={ausgewaehlt.has(r.id)} onchange={() => toggleAuswahl(r.id)} /></label>
              </td>
              <td class="td-nr">{r.rechnung_nr || '-'}</td>
              <td class="td-datum">{fmtDatum(r.erstellt_am)}</td>
              <td class="td-kaeufer">{r.kaeufer_name || '-'}</td>
              <td class="td-artikel">{r.artikel_name || '-'}</td>
              <td class="td-right">{fmt(r.netto_betrag)} EUR</td>
              <td class="td-right">{fmt(r.steuer_betrag)} EUR</td>
              <td class="td-right td-bold">{fmt(r.brutto_betrag)} EUR</td>
              <td><span class="badge {badge.cls}">{badge.label}</span></td>
              <td class="td-actions" onclick={(e) => e.stopPropagation()}>
                <button class="icon-btn" title="Details" onclick={() => oeffneDetailModal(r)}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                </button>
                <button class="icon-btn" title="PDF" onclick={() => ladePDF(r)}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                </button>
                {#if r.status !== 'storniert' && r.rechnung_typ !== 'storno'}
                  <button class="icon-btn" title="E-Mail senden" onclick={() => oeffneSendenModal(r)}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
                  </button>
                  <button class="icon-btn icon-btn-edit" title="Bearbeiten" onclick={() => oeffneBearbeitenModal(r)}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                  </button>
                  <div class="erechnungs-wrap" onclick={(e) => e.stopPropagation()}>
                    <button class="icon-btn icon-btn-erechnung" title="E-Rechnung" onclick={(e) => oeffneERechnungMenu(r, e)}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
                    </button>
                    {#if eRechnungMenuOffen && eRechnungRechnung?.id === r.id}
                      <div class="erechnung-menu">
                        <button onclick={() => erstelleERechnung(r, 'zugferd_en16931')}>ZUGFeRD 2.4 EN16931 PDF</button>
                        <button onclick={() => erstelleERechnung(r, 'zugferd_extended')}>ZUGFeRD 2.4 EXTENDED PDF (BETA)</button>
                        <button onclick={() => erstelleERechnung(r, 'xrechnung')}>XRechnung 3.0.2 XML</button>
                      </div>
                    {/if}
                  </div>
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

  <!-- Pagination -->
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


<!-- ═══════════════════════════════════════════════════════════════════
     DAS EINE UNIVERSELLE MODAL
     modus = 'neu'        → Rechnung erstellen (Formular)
     modus = 'detail'     → Rechnung anzeigen (read-only)
     modus = 'bearbeiten' → Rechnung bearbeiten (editierbar + Änderungsgrund)
════════════════════════════════════════════════════════════════════ -->
{#if modalOffen}
  <div class="modal-overlay" onclick={schliesseModal}>
    <div class="modal-box modal-universal" onclick={(e) => e.stopPropagation()}>

      <!-- ══ DETAIL (Rechnung anzeigen, read-only) ══════════════════ -->
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
          {#if r.rechnung_typ === 'storno'}
            <div class="hinweis hinweis-rot">Stornorechnung zu einer vorherigen Rechnung</div>
          {/if}
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
            <div class="bm-section-titel">Artikel</div>
            <div class="bm-grid">
              <div class="bm-field bm-full"><div class="bm-label">Bezeichnung</div><div class="bm-value">{r.artikel_name || '-'}</div></div>
              {#if r.ebay_artikel_id}<div class="bm-field"><div class="bm-label">eBay Artikel-ID</div><div class="bm-value" style="font-family:monospace">{r.ebay_artikel_id}</div></div>{/if}
              <div class="bm-field"><div class="bm-label">Menge</div><div class="bm-value">{r.artikel_menge || 1}</div></div>
            </div>
          </div>

          {#if r.order_id}
            <div class="bm-section">
              <div class="bm-section-titel">eBay-Bestellnummer</div>
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
              <div class="bm-section-titel">Gesendet an</div>
              <div style="font-size:0.82rem;color:var(--text2)">{r.email_gesendet_an}</div>
            </div>
          {/if}
        </div>

        <div class="modal-footer">
          <button class="btn-ghost btn-sm" onclick={schliesseModal}>Schließen</button>
          <button class="btn-secondary btn-sm" onclick={() => ladePDF(r)}>PDF</button>
          {#if r.status !== 'storniert' && r.rechnung_typ !== 'storno'}
            <button class="btn-secondary btn-sm" onclick={() => oeffneSendenModal(r)}>E-Mail</button>
            <div class="erechnungs-wrap" style="position:relative" onclick={(e) => e.stopPropagation()}>
              <button class="btn-secondary btn-sm" onclick={(e) => oeffneERechnungMenu(r, e)}>E-Rechnung ▾</button>
              {#if eRechnungMenuOffen && eRechnungRechnung?.id === r.id}
                <div class="erechnung-menu" style="bottom:auto;top:calc(100% + 4px)">
                  <button onclick={() => erstelleERechnung(r, 'zugferd_en16931')}>ZUGFeRD 2.4 EN16931 PDF</button>
                  <button onclick={() => erstelleERechnung(r, 'zugferd_extended')}>ZUGFeRD 2.4 EXTENDED PDF (BETA)</button>
                  <button onclick={() => erstelleERechnung(r, 'xrechnung')}>XRechnung 3.0.2 XML</button>
                </div>
              {/if}
            </div>
            <button class="btn-secondary btn-sm" onclick={() => oeffneBearbeitenModal(r)}>✏️ Bearbeiten</button>
            <button class="btn-danger btn-sm" onclick={() => oeffneStornoModal(r)}>Stornieren</button>
          {/if}
        </div>

      <!-- ══ NEU / BEARBEITEN (Formular) ════════════════════════════ -->
      {:else if modalModus === 'neu' || modalModus === 'bearbeiten'}

        <div class="modal-hdr">
          <div>
            <span class="modal-titel">
              {#if modalModus === 'bearbeiten'}✏️ Rechnung bearbeiten — {modalRechnung?.rechnung_nr}{:else}Neue Rechnung erstellen{/if}
            </span>
          </div>
          <button class="icon-btn" onclick={schliesseModal}>✕</button>
        </div>

        <div class="modal-body">

          {#if modalModus === 'bearbeiten'}
            <div class="hinweis hinweis-gelb">
              Die bestehende Rechnung wird storniert und eine neue mit den geänderten Daten erstellt. Der Änderungsgrund wird intern gespeichert.
            </div>
          {/if}

          <!-- Bestellnummer + Laden -->
          <div class="form-group" style="margin-bottom:14px">
            <label>eBay Bestellnr.</label>
            <div style="display:flex;gap:8px">
              <input bind:value={form.order_id} placeholder="12-34567-89012" style="flex:1"
                oninput={onOrderIdInput}
                onkeydown={(e) => e.key === 'Enter' && ladeBestellungDaten()} />
              <button class="btn-primary btn-sm" onclick={ladeBestellungDaten}
                disabled={bestellungLaeuft || !form.order_id} style="white-space:nowrap">
                {bestellungLaeuft ? '...' : 'Laden'}
              </button>
            </div>
            {#if bestellungFehler}<p class="form-fehler">{bestellungFehler}</p>{/if}
          </div>

          <!-- Duplikat-Warnung (nur bei neu) -->
          {#if duplikatRechnung}
            <div class="hinweis hinweis-rot" style="margin-bottom:14px">
              ⚠️ Für diese Bestellung existiert bereits <strong>{duplikatRechnung.rechnung_nr}</strong>.
              <button class="btn-link" onclick={() => oeffneDetailModal(duplikatRechnung)}>Anzeigen →</button>
            </div>
          {/if}

          <!-- Rechnung vorhanden → grüner Badge (nur bei neu) -->
          {#if modalModus === 'neu' && form.order_id && !duplikatRechnung && !bestellungLaeuft}
            {@const vorh = findeVorhandeneRechnung(form.order_id)}
            {#if vorh}
              <div class="hinweis hinweis-gruen" style="margin-bottom:14px">
                ✅ Rechnung <strong>{vorh.rechnung_nr}</strong> bereits vorhanden.
                <button class="btn-link" onclick={() => oeffneDetailModal(vorh)}>Anzeigen →</button>
              </div>
            {/if}
          {/if}

          <div class="form-grid">
            <div class="form-group"><label>Käufer *</label><input bind:value={form.kaeufer_name} placeholder="Max Mustermann" /></div>
            <div class="form-group"><label>E-Mail</label><input bind:value={form.kaeufer_email} type="email" placeholder="max@example.com" /></div>
            <div class="form-group"><label>Straße</label><input bind:value={form.kaeufer_strasse} placeholder="Musterstr. 1" /></div>
            <div class="form-group form-2col">
              <div class="form-group"><label>PLZ</label><input bind:value={form.kaeufer_plz} placeholder="12345" /></div>
              <div class="form-group"><label>Ort</label><input bind:value={form.kaeufer_ort} placeholder="Berlin" /></div>
            </div>
            <div class="form-group form-2col">
              <div class="form-group"><label>Land</label><input bind:value={form.kaeufer_land} placeholder="DE" /></div>
            </div>
            <div class="form-group"><label>Artikel *</label><input bind:value={form.artikel_name} placeholder="Produktname" /></div>
            <div class="form-group form-2col">
              <div class="form-group"><label>eBay Artikel-ID</label><input bind:value={form.ebay_artikel_id} placeholder="123456789012" /></div>
              <div class="form-group">
                <label>Variante (SKU)</label>
                <input value={form.artikel_sku || ''} readonly placeholder="—" style="background:var(--surface2);color:var(--primary);font-family:monospace;font-size:0.82rem;" />
              </div>
            </div>
            <div class="form-group form-2col">
              <div class="form-group"><label>Menge *</label><input bind:value={form.menge} type="number" min="1" /></div>
              <div class="form-group"><label>Einzelpreis Brutto *</label><input bind:value={form.einzelpreis} type="number" step="0.01" placeholder="9.99" /></div>
            </div>
          </div>

          <!-- Änderungsgrund (nur bei bearbeiten) -->
          {#if modalModus === 'bearbeiten'}
            <div class="form-group" style="margin-top:18px">
              <label>Grund der Änderung * <span style="font-weight:400;color:var(--text3)">(wird intern gespeichert)</span></label>
              <textarea
                bind:value={aenderungsgrund}
                placeholder="z. B. Käufer hat neue Lieferadresse mitgeteilt"
                rows="3"
                style="background:var(--surface);border:1px solid var(--border);color:var(--text);padding:8px 12px;border-radius:8px;font-size:0.85rem;outline:none;resize:vertical;font-family:inherit;width:100%;box-sizing:border-box;"
              ></textarea>
              {#if modalModus === 'bearbeiten' && !aenderungsgrund.trim()}
                <p class="form-fehler">Pflichtfeld — bitte Grund angeben</p>
              {/if}
            </div>
          {/if}

        </div>

        <div class="modal-footer">
          <button class="btn-ghost" onclick={schliesseModal}>Abbrechen</button>
          {#if modalModus === 'neu'}
            <button class="btn-primary" onclick={erstelleRechnung}
              disabled={modalLaeuft || !!duplikatRechnung}>
              {modalLaeuft ? '⏳ Erstelle...' : '🧾 Rechnung erstellen'}
            </button>
          {:else}
            <button class="btn-primary" onclick={speichereBearbeitung}
              disabled={modalLaeuft || !aenderungsgrund.trim()}>
              {modalLaeuft ? '⏳ Speichere...' : '💾 Änderung speichern'}
            </button>
          {/if}
        </div>

      {/if}
    </div>
  </div>
{/if}


<!-- ═══ MODAL: E-MAIL SENDEN ═══ -->
{#if sendenModal}
  <div class="modal-overlay" onclick={() => sendenModal = false}>
    <div class="modal-box modal-klein" onclick={(e) => e.stopPropagation()}>
      <div class="modal-hdr">
        <span class="modal-titel">Rechnung senden</span>
        <button class="icon-btn" onclick={() => sendenModal = false}>✕</button>
      </div>
      <div class="modal-body">
        <p class="modal-info">Rechnung <strong>{sendenRechnung?.rechnung_nr}</strong> per E-Mail senden.</p>
        <div class="form-group"><label>E-Mail</label><input bind:value={sendenEmail} type="email" placeholder="kaeufer@example.com" /></div>
      </div>
      <div class="modal-footer">
        <button class="btn-ghost" onclick={() => sendenModal = false}>Abbrechen</button>
        <button class="btn-primary" onclick={sendeRechnung} disabled={sendenLaeuft}>{sendenLaeuft ? 'Sende...' : 'Senden'}</button>
      </div>
    </div>
  </div>
{/if}

<!-- ═══ MODAL: STORNO ═══ -->
{#if stornoModal}
  <div class="modal-overlay" onclick={() => stornoModal = false}>
    <div class="modal-box modal-klein" onclick={(e) => e.stopPropagation()}>
      <div class="modal-hdr">
        <span class="modal-titel">Rechnung stornieren</span>
        <button class="icon-btn" onclick={() => stornoModal = false}>✕</button>
      </div>
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
  .btn-primary:hover:not(:disabled) { background:var(--primary-hover, #1d4ed8); }
  .btn-primary:disabled { opacity:0.6; cursor:not-allowed; }
  .btn-ghost { background:transparent; border:1px solid var(--border); color:var(--text2); padding:8px 16px; border-radius:8px; font-size:0.84rem; cursor:pointer; display:flex; align-items:center; gap:6px; }
  .btn-ghost:hover:not(:disabled) { border-color:var(--primary); color:var(--primary); }
  .btn-ghost:disabled { opacity:0.6; cursor:not-allowed; }
  .btn-secondary { background:var(--surface2); border:1px solid var(--border); color:var(--text); padding:8px 16px; border-radius:8px; font-size:0.84rem; cursor:pointer; }
  .btn-secondary:hover { background:var(--border); }
  .btn-danger { background:#ef4444; color:#fff; border:none; padding:8px 16px; border-radius:8px; font-size:0.84rem; cursor:pointer; }
  .btn-danger:hover:not(:disabled) { background:#dc2626; }
  .btn-danger:disabled { opacity:0.6; cursor:not-allowed; }
  .btn-sm { padding:6px 12px; font-size:0.8rem; }
  .btn-link { background:none; border:none; color:var(--primary); font-size:0.82rem; cursor:pointer; text-decoration:underline; padding:0; font-weight:600; }
  .icon-btn { background:transparent; border:none; color:var(--text2); padding:5px; border-radius:6px; cursor:pointer; display:inline-flex; align-items:center; transition:color 0.15s, background 0.15s; }
  .icon-btn:hover { color:var(--primary); background:var(--surface2); }
  .icon-btn-edit:hover { color:#7c3aed; background:#f5f3ff; }
  .icon-btn-danger:hover { color:#ef4444; background:#fef2f2; }
  .icon-btn-erechnung:hover { color:#0891b2; background:#ecfeff; }
  .erechnungs-wrap { position:relative; display:inline-flex; }
  .erechnung-menu { position:absolute; bottom:calc(100% + 4px); right:0; background:var(--surface); border:1px solid var(--border); border-radius:8px; box-shadow:0 4px 16px rgba(0,0,0,0.14); z-index:200; min-width:230px; overflow:hidden; }
  .erechnung-menu button { display:block; width:100%; text-align:left; padding:9px 14px; background:transparent; border:none; color:var(--text); font-size:0.81rem; cursor:pointer; white-space:nowrap; }
  .erechnung-menu button:hover { background:var(--surface2); color:var(--primary); }
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
  .th-actions { width:170px; }
  .tbl-row { border-bottom:1px solid var(--border); cursor:pointer; transition:background 0.12s; }
  .tbl-row:last-child { border-bottom:none; }
  .tbl-row:hover { background:var(--surface2); }
  .tabelle td { padding:10px 12px; color:var(--text); vertical-align:middle; }
  .td-check { width:36px; padding:0 !important; }
  .td-nr { font-weight:600; white-space:nowrap; color:var(--primary); }
  .td-datum { white-space:nowrap; color:var(--text2); font-size:0.8rem; }
  .td-kaeufer { max-width:180px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .td-artikel { max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--text2); }
  .td-right { text-align:right; white-space:nowrap; }
  .td-bold { font-weight:600; }
  .td-actions { white-space:nowrap; }
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
  /* Modal */
  .modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.45); z-index:1000; display:flex; align-items:center; justify-content:center; padding:20px; }
  .modal-box { background:var(--surface); border:1px solid var(--border); border-radius:14px; width:100%; max-width:560px; max-height:90vh; display:flex; flex-direction:column; box-shadow:0 20px 60px rgba(0,0,0,0.2); }
  .modal-klein { max-width:400px; }
  .modal-universal { max-width:600px; }
  .modal-hdr { display:flex; align-items:center; justify-content:space-between; padding:18px 20px 14px; border-bottom:1px solid var(--border); flex-shrink:0; }
  .modal-titel { font-size:1rem; font-weight:600; color:var(--text); }
  .modal-sub { font-size:0.75rem; color:var(--text3); margin-top:2px; font-family:monospace; }
  .modal-body { padding:20px; overflow-y:auto; flex:1; }
  .modal-footer { display:flex; gap:8px; justify-content:flex-end; padding:14px 20px 18px; border-top:1px solid var(--border); flex-wrap:wrap; flex-shrink:0; }
  .modal-info { font-size:0.85rem; color:var(--text2); margin-bottom:14px; line-height:1.5; }
  .modal-info strong { color:var(--text); }
  /* Hinweise */
  .hinweis { border-radius:8px; padding:10px 14px; font-size:0.82rem; margin-bottom:14px; line-height:1.5; display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
  .hinweis-rot { background:#fef2f2; border:1px solid #fecaca; color:#dc2626; }
  .hinweis-gruen { background:#f0fdf4; border:1px solid #bbf7d0; color:#16a34a; }
  .hinweis-gelb { background:#fffbeb; border:1px solid #fde68a; color:#92400e; }
  .hinweis-blau { background:#eff6ff; border:1px solid #bfdbfe; color:#1d4ed8; }
  /* Detail */
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
  /* Form */
  .form-grid { display:flex; flex-direction:column; gap:14px; }
  .form-group { display:flex; flex-direction:column; gap:5px; }
  .form-2col { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
  .form-group label { font-size:0.78rem; color:var(--text2); font-weight:500; }
  .form-group input { background:var(--surface); border:1px solid var(--border); color:var(--text); padding:8px 12px; border-radius:8px; font-size:0.85rem; outline:none; }
  .form-group input:focus { border-color:var(--primary); }
  .form-group input::placeholder { color:var(--text3); }
  .form-fehler { color:#ef4444; font-size:0.75rem; margin-top:3px; }
  /* Checkbox */
  .chk-label { display:flex; align-items:center; justify-content:center; width:100%; height:100%; min-height:20px; cursor:pointer; padding:4px; box-sizing:border-box; }
  .chk-label input[type="checkbox"] { width:15px; height:15px; cursor:pointer; accent-color:var(--primary); margin:0; }
</style>
