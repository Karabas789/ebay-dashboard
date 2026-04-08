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

  let vorschauRechnung = $state(null);
  let vorschauOffen = $state(false);

  let stornoModal = $state(false);
  let stornoRechnung = $state(null);
  let stornoLaeuft = $state(false);

  let erstellenModal = $state(false);
  let sendenModal = $state(false);
  let sendenRechnung = $state(null);
  let sendenEmail = $state('');
  let sendenLaeuft = $state(false);

  let autoRechnungAktiv = $state(true);
  let toggleLaeuft = $state(false);

  let schnellsucheOrderId = $state('');
  let schnellsucheLaeuft = $state(false);
  let schnellsucheErgebnis = $state(null);
  let schnellsucheFehler = $state('');
  let schnellsucheModalOffen = $state(false);

  let bearbeitenModal = $state(false);
  let bearbeitenRechnung = $state(null);
  let bearbeitenPositionen = $state([]);
  let bearbeitenLaeuft = $state(false);

  // E-Rechnung Dropdown
  let eRechnungMenuOffen = $state(false);
  let eRechnungRechnung = $state(null);

  let neueRechnung = $state({
    kaeufer_name: '', kaeufer_email: '', kaeufer_strasse: '', kaeufer_plz: '',
    kaeufer_ort: '', kaeufer_land: 'DE', artikel_name: '', ebay_artikel_id: '',
    menge: 1, einzelpreis: '', order_id: ''
  });
  let erstellenLaeuft = $state(false);
  let bestellungLaeuft = $state(false);
  let bestellungFehler = $state('');

  function clearBestellungLaden() { bestellungFehler = ''; }

  async function ladeBestellungDaten() {
    if (!neueRechnung.order_id) return;
    bestellungLaeuft = true;
    bestellungFehler = '';
    try {
      const data = await apiCall('bestellung-laden', {
        user_id: $currentUser?.id,
        order_id: neueRechnung.order_id
      });
      if (data?.bestellung) {
        const b = data.bestellung;
        neueRechnung = {
          ...neueRechnung,
          kaeufer_name: b.kaeufer_name || neueRechnung.kaeufer_name,
          kaeufer_email: b.kaeufer_email || neueRechnung.kaeufer_email,
          kaeufer_strasse: b.kaeufer_strasse || neueRechnung.kaeufer_strasse,
          kaeufer_plz: b.kaeufer_plz || neueRechnung.kaeufer_plz,
          kaeufer_ort: b.kaeufer_ort || neueRechnung.kaeufer_ort,
          kaeufer_land: b.kaeufer_land || neueRechnung.kaeufer_land,
          artikel_name: b.artikel_name || neueRechnung.artikel_name,
          ebay_artikel_id: b.ebay_artikel_id || neueRechnung.ebay_artikel_id,
          einzelpreis: b.brutto_betrag || neueRechnung.einzelpreis,
          menge: b.artikel_menge || neueRechnung.menge,
        };
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

  async function schnellsucheNachOrder() {
    if (!schnellsucheOrderId.trim()) return;
    const term = schnellsucheOrderId.trim().toLowerCase();

    // Zuerst lokal in bereits geladenen Rechnungen suchen
    const lokaleErgebnisse = rechnungen.filter(r =>
      r.rechnung_nr?.toLowerCase().includes(term) ||
      r.kaeufer_name?.toLowerCase().includes(term) ||
      r.kaeufer_email?.toLowerCase().includes(term) ||
      r.kaeufer_strasse?.toLowerCase().includes(term) ||
      r.kaeufer_plz?.toLowerCase().includes(term) ||
      r.kaeufer_ort?.toLowerCase().includes(term) ||
      r.artikel_name?.toLowerCase().includes(term) ||
      r.ebay_artikel_id?.toLowerCase().includes(term) ||
      r.order_id?.toLowerCase().includes(term)
    );

    if (lokaleErgebnisse.length > 0) {
      suchbegriff = schnellsucheOrderId.trim();
      schnellsucheOrderId = '';
      return;
    }

    // Wenn nichts lokal gefunden: Backend (bestellung-laden) anfragen
    schnellsucheLaeuft = true;
    schnellsucheFehler = '';
    schnellsucheErgebnis = null;
    try {
      const data = await apiCall('bestellung-laden', {
        user_id: $currentUser.id,
        suchbegriff: schnellsucheOrderId.trim()
      });
      if (data?.bestellung) {
        schnellsucheErgebnis = data.bestellung;
        schnellsucheModalOffen = true;
      } else {
        schnellsucheFehler = 'Nichts gefunden';
      }
    } catch(e) {
      schnellsucheFehler = 'Nichts gefunden';
    } finally {
      schnellsucheLaeuft = false;
    }
  }

  function schliesseSchnellsucheModal() {
    schnellsucheModalOffen = false;
    schnellsucheErgebnis = null;
    schnellsucheOrderId = '';
    schnellsucheFehler = '';
  }

  function rechnungAusSchnellsuche() {
    const b = schnellsucheErgebnis;
    neueRechnung = {
      order_id: b.order_id || schnellsucheOrderId,
      kaeufer_name: b.kaeufer_name || '',
      kaeufer_email: b.kaeufer_email || '',
      kaeufer_strasse: b.kaeufer_strasse || '',
      kaeufer_plz: b.kaeufer_plz || '',
      kaeufer_ort: b.kaeufer_ort || '',
      kaeufer_land: b.kaeufer_land || 'DE',
      artikel_name: b.artikel_name || '',
      ebay_artikel_id: b.ebay_artikel_id || '',
      einzelpreis: b.brutto_betrag || '',
      menge: b.artikel_menge || 1,
    };
    schliesseSchnellsucheModal();
    erstellenModal = true;
  }

  function oeffneBearbeitenModal(r) {
    bearbeitenRechnung = r;
    bearbeitenPositionen = [{
      artikel_name: r.artikel_name || '',
      ebay_artikel_id: r.ebay_artikel_id || '',
      menge: r.artikel_menge || 1,
      einzelpreis: parseFloat(r.einzelpreis) || parseFloat(r.brutto_betrag) || 0,
      entfernt: false
    }];
    bearbeitenModal = true;
  }

  function togglePosition(idx) {
    bearbeitenPositionen = bearbeitenPositionen.map((p, i) =>
      i === idx ? { ...p, entfernt: !p.entfernt } : p
    );
  }

  function updatePositionMenge(idx, wert) {
    bearbeitenPositionen = bearbeitenPositionen.map((p, i) =>
      i === idx ? { ...p, menge: Math.max(1, parseInt(wert) || 1) } : p
    );
  }

  async function speichereBearbeitung() {
    const aktivePositionen = bearbeitenPositionen.filter(p => !p.entfernt);
    if (aktivePositionen.length === 0) {
      showToast('Mindestens eine Position muss verbleiben.');
      return;
    }
    bearbeitenLaeuft = true;
    try {
      await apiCall('rechnung-stornieren', { user_id: $currentUser.id, invoice_id: bearbeitenRechnung.id });
      const pos = aktivePositionen[0];
      await apiCall('rechnung-erstellen', {
        user_id: $currentUser.id, typ: 'rechnung',
        order_id: bearbeitenRechnung.order_id || '',
        kaeufer_name: bearbeitenRechnung.kaeufer_name,
        kaeufer_email: bearbeitenRechnung.kaeufer_email || '',
        kaeufer_strasse: bearbeitenRechnung.kaeufer_strasse || '',
        kaeufer_plz: bearbeitenRechnung.kaeufer_plz || '',
        kaeufer_ort: bearbeitenRechnung.kaeufer_ort || '',
        kaeufer_land: bearbeitenRechnung.kaeufer_land || 'DE',
        artikel_name: pos.artikel_name,
        ebay_artikel_id: pos.ebay_artikel_id || '',
        menge: pos.menge, einzelpreis: pos.einzelpreis
      });
      showToast('Rechnung aktualisiert');
      bearbeitenModal = false;
      await ladeRechnungen();
    } catch(e) {
      showToast('Fehler: ' + e.message);
    } finally {
      bearbeitenLaeuft = false;
    }
  }

  // ── Bulk-Aktionen ────────────────────────────────────────
  async function bulkDrucken() {
    const liste = rechnungen.filter(r => ausgewaehlt.has(r.id));
    for (const r of liste) {
      await ladePDF(r);
      await new Promise(res => setTimeout(res, 400));
    }
  }

  async function bulkEmailSenden() {
    const liste = rechnungen.filter(r => ausgewaehlt.has(r.id));
    const ohneEmail = liste.filter(r => !r.kaeufer_email);
    if (ohneEmail.length > 0) showToast(`${ohneEmail.length} ohne E-Mail werden übersprungen`);
    let gesendet = 0;
    for (const r of liste) {
      if (!r.kaeufer_email) continue;
      try {
        await apiCall('rechnung-senden', { invoice_id: r.id, user_id: $currentUser.id, to_email: r.kaeufer_email });
        gesendet++;
      } catch(e) {}
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

  // ── E-Rechnung ────────────────────────────────────────────
  function oeffneERechnungMenu(r, e) {
    e.stopPropagation();
    if (eRechnungRechnung?.id === r.id && eRechnungMenuOffen) {
      eRechnungMenuOffen = false;
      eRechnungRechnung = null;
    } else {
      eRechnungRechnung = r;
      eRechnungMenuOffen = true;
    }
  }

  async function erstelleERechnung(rechnung, format) {
    eRechnungMenuOffen = false;
    eRechnungRechnung = null;
    showToast('E-Rechnung wird erstellt...');
    try {
      const data = await apiCall('e-rechnung-erstellen', {
        invoice_id: rechnung.id,
        user_id: $currentUser.id,
        format
      });
      if (format === 'xrechnung') {
        const blob = new Blob([data.xml], { type: 'application/xml' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = (rechnung.rechnung_nr || 'XRechnung') + '.xml';
        a.click(); URL.revokeObjectURL(url);
      } else {
        const b64 = data.pdf_base64 || data.pdf;
        if (!b64) { showToast('Kein Ergebnis erhalten.'); return; }
        const blob = new Blob([Uint8Array.from(atob(b64), c => c.charCodeAt(0))], { type: 'application/pdf' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = (rechnung.rechnung_nr || 'ERechnung') + '.pdf';
        a.click(); URL.revokeObjectURL(url);
      }
      showToast('E-Rechnung erstellt');
    } catch(e) {
      showToast('Fehler: ' + e.message);
    }
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
        r.rechnung_nr?.toLowerCase().includes(s) ||
        r.kaeufer_name?.toLowerCase().includes(s) ||
        r.kaeufer_email?.toLowerCase().includes(s) ||
        r.kaeufer_strasse?.toLowerCase().includes(s) ||
        r.kaeufer_plz?.toLowerCase().includes(s) ||
        r.kaeufer_ort?.toLowerCase().includes(s) ||
        r.artikel_name?.toLowerCase().includes(s) ||
        r.ebay_artikel_id?.toLowerCase().includes(s) ||
        r.order_id?.toLowerCase().includes(s)
      );
    }
    return liste;
  });

  let gesamtSeiten  = $derived(Math.max(1, Math.ceil(gefiltert.length / proSeite)));
  let sichtbar      = $derived(gefiltert.slice((aktuelleSeite - 1) * proSeite, aktuelleSeite * proSeite));
  let summeNetto    = $derived(gefiltert.filter(r => r.status !== 'storniert' && r.rechnung_typ === 'rechnung').reduce((s, r) => s + (parseFloat(r.netto_betrag) || 0), 0));
  let summeStorno   = $derived(gefiltert.filter(r => r.rechnung_typ === 'storno').reduce((s, r) => s + (parseFloat(r.brutto_betrag) || 0), 0));
  let kpiGesamt     = $derived(rechnungen.filter(r => r.rechnung_typ === 'rechnung').length);
  let kpiGesendet   = $derived(rechnungen.filter(r => r.status === 'gesendet').length);
  let kpiAusstehend = $derived(rechnungen.filter(r => r.status === 'erstellt' && r.rechnung_typ === 'rechnung').length);
  let kpiStorniert  = $derived(rechnungen.filter(r => r.rechnung_typ === 'storno').length);
  let kpiBrutto     = $derived(rechnungen.filter(r => r.rechnung_typ === 'rechnung' && r.status !== 'storniert').reduce((s, r) => s + (parseFloat(r.brutto_betrag) || 0), 0));
  let kpiDieserMonat = $derived.by(() => {
    const jetzt = new Date();
    return rechnungen.filter(r => {
      const d = new Date(r.erstellt_am);
      return d.getFullYear() === jetzt.getFullYear() && d.getMonth() === jetzt.getMonth();
    }).length;
  });
  let aktiveSumme = $derived(bearbeitenPositionen.filter(p => !p.entfernt).reduce((s, p) => s + p.einzelpreis * p.menge, 0));

  onMount(() => {
    if ($currentUser) { ladeRechnungen(); ladeAutoRechnungStatus(); }
  });

  async function ladeRechnungen() {
    loading = true; fehler = '';
    try {
      const data = await apiCall('rechnungen-laden', { user_id: $currentUser.id, ebayusername: $currentUser.ebayuserid });
      rechnungen = Array.isArray(data) ? data : (data.rechnungen || []);
    } catch (e) { fehler = e.message; } finally { loading = false; }
  }

  async function ladePDF(rechnung) {
    try {
      showToast('PDF wird geladen...');
      const data = await apiCall('rechnung-pdf', { invoice_id: rechnung.id, user_id: $currentUser.id });
      const b64 = data.pdf_base64 || data.pdf;
      if (!b64) { showToast('Kein PDF vorhanden.'); return; }
      const blob = new Blob([Uint8Array.from(atob(b64), c => c.charCodeAt(0))], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = (rechnung.rechnung_nr || 'Rechnung') + '.pdf';
      a.click(); URL.revokeObjectURL(url);
    } catch (e) { showToast('Fehler: ' + e.message); }
  }

  function oeffneVorschau(r) { vorschauRechnung = r; vorschauOffen = true; }
  function oeffneSendenModal(r) { sendenRechnung = r; sendenEmail = r.kaeufer_email || ''; sendenModal = true; }

  async function sendeRechnung() {
    if (!sendenEmail) { showToast('Bitte E-Mail eingeben.'); return; }
    sendenLaeuft = true;
    try {
      await apiCall('rechnung-senden', { invoice_id: sendenRechnung.id, user_id: $currentUser.id, to_email: sendenEmail });
      showToast('Rechnung gesendet');
      sendenModal = false; await ladeRechnungen();
    } catch (e) { showToast('Fehler: ' + e.message); } finally { sendenLaeuft = false; }
  }

  function oeffneStornoModal(r) { stornoRechnung = r; stornoModal = true; }

  async function erstelleStorno() {
    stornoLaeuft = true;
    try {
      await apiCall('rechnung-stornieren', { user_id: $currentUser.id, invoice_id: stornoRechnung.id });
      showToast('Stornorechnung erstellt');
      stornoModal = false; await ladeRechnungen();
    } catch (e) { showToast('Fehler: ' + e.message); } finally { stornoLaeuft = false; }
  }

  async function erstelleManuell() {
    if (!neueRechnung.kaeufer_name || !neueRechnung.artikel_name || !neueRechnung.einzelpreis) {
      showToast('Bitte alle Pflichtfelder ausfuellen.'); return;
    }
    erstellenLaeuft = true;
    try {
      await apiCall('rechnung-erstellen', {
        user_id: $currentUser.id, typ: 'rechnung',
        order_id: neueRechnung.order_id || '',
        kaeufer_name: neueRechnung.kaeufer_name, kaeufer_email: neueRechnung.kaeufer_email,
        kaeufer_strasse: neueRechnung.kaeufer_strasse, kaeufer_plz: neueRechnung.kaeufer_plz,
        kaeufer_ort: neueRechnung.kaeufer_ort, kaeufer_land: neueRechnung.kaeufer_land,
        artikel_name: neueRechnung.artikel_name, ebay_artikel_id: neueRechnung.ebay_artikel_id,
        menge: Number(neueRechnung.menge), einzelpreis: Number(neueRechnung.einzelpreis)
      });
      showToast('Rechnung erstellt');
      erstellenModal = false;
      neueRechnung = { kaeufer_name: '', kaeufer_email: '', kaeufer_strasse: '', kaeufer_plz: '', kaeufer_ort: '', kaeufer_land: 'DE', artikel_name: '', ebay_artikel_id: '', menge: 1, einzelpreis: '', order_id: '' };
      await ladeRechnungen();
    } catch (e) { showToast('Fehler: ' + e.message); } finally { erstellenLaeuft = false; }
  }

  function toggleAuswahl(id) {
    const neu = new Set(ausgewaehlt);
    neu.has(id) ? neu.delete(id) : neu.add(id);
    ausgewaehlt = neu;
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

      <!-- Schnellsuche im Header -->
      <div class="hdr-suche">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--text3);flex-shrink:0;">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
        <input
          class="hdr-suche-input"
          type="text"
          placeholder="Name, Rechnungs-Nr., Bestellnr. ..."
          bind:value={schnellsucheOrderId}
          onkeydown={(e) => e.key === 'Enter' && schnellsucheNachOrder()}
        />
        {#if schnellsucheFehler}
          <span class="hdr-suche-fehler">{schnellsucheFehler}</span>
        {/if}
        <button class="btn-primary btn-sm" onclick={schnellsucheNachOrder} disabled={schnellsucheLaeuft || !schnellsucheOrderId.trim()}>
          {schnellsucheLaeuft ? '...' : 'Suchen'}
        </button>
      </div>

      <!-- Auto-Rechnung Toggle -->
      <div class="toggle-wrap">
        <span class="toggle-label">Auto-Rechnung</span>
        <button
          class="toggle-btn {autoRechnungAktiv ? 'toggle-an' : 'toggle-aus'}"
          onclick={toggleAutoRechnung}
          disabled={toggleLaeuft}
        >
          <span class="toggle-thumb"></span>
        </button>
        <span class="toggle-status {autoRechnungAktiv ? 'status-an' : 'status-aus'}">
          {autoRechnungAktiv ? 'Aktiv' : 'Inaktiv'}
        </span>
      </div>

      <button class="btn-ghost" onclick={ladeRechnungen} disabled={loading}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>
          <path d="M21 3v5h-5M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/>
        </svg>
        Aktualisieren
      </button>
      <button class="btn-primary" onclick={() => erstellenModal = true}>
        + Rechnung erstellen
      </button>
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
        <option value={20}>20 / Seite</option>
        <option value={50}>50 / Seite</option>
        <option value={100}>100 / Seite</option>
      </select>
    </div>
  </div>

  <!-- Bulk-Aktionsleiste -->
  {#if ausgewaehlt.size > 0}
      <div class="bulk-bar">
    <span><strong>{ausgewaehlt.size}</strong> Rechnung{ausgewaehlt.size > 1 ? 'en' : ''} ausgewählt</span>
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
      <button class="btn-ghost btn-sm" onclick={bulkDrucken} title="PDFs herunterladen">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
        PDFs laden
      </button>
      <button class="btn-ghost btn-sm" onclick={bulkEmailSenden} title="An Käufer-Email senden">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
        Per E-Mail senden
      </button>
      <button class="btn-ghost btn-sm" onclick={bulkExportCSV} title="Als CSV exportieren">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
        CSV exportieren
      </button>
    </div>
  </div>
  {/if}

  <!-- Haupt-Bereich -->
  <div class="haupt-bereich">
    <div class="tabellen-wrapper">
      {#if loading}
        <div class="status-info">Lade Rechnungen...</div>
      {:else if fehler}
        <div class="status-info status-fehler">{fehler}</div>
      {:else if sichtbar.length === 0}
        <div class="leer-state">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          <p>Keine Rechnungen gefunden</p>
          <button class="btn-primary btn-sm" onclick={() => erstellenModal = true}>Erste Rechnung erstellen</button>
        </div>
      {:else}
        <table class="tabelle">
          <thead>
            <tr>
              <th class="th-check" onclick={(e) => e.stopPropagation()}>
                <input type="checkbox" checked={alleAusgewaehlt} onchange={toggleAlleAuswaehlen} />
              </th>
              <th>Nummer</th><th>Datum</th><th>Kaeufer</th><th>Artikel</th>
              <th class="th-right">Netto</th><th class="th-right">MwSt.</th><th class="th-right">Brutto</th>
              <th>Status</th><th class="th-actions">Aktionen</th>
            </tr>
          </thead>
          <tbody>
            {#each sichtbar as r (r.id)}
              {@const badge = statusBadge(r)}
              <tr class="tbl-row {vorschauRechnung?.id === r.id ? 'aktiv' : ''}" onclick={() => oeffneVorschau(r)}>
                <td class="td-check" onclick={(e) => { e.stopPropagation(); toggleAuswahl(r.id); }}>
                  <input type="checkbox" checked={ausgewaehlt.has(r.id)} onchange={() => toggleAuswahl(r.id)} />
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
                  <button class="icon-btn" title="Vorschau" onclick={() => oeffneVorschau(r)}>
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
                    <!-- E-Rechnung Dropdown -->
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

    <!-- Vorschau-Panel -->
    {#if vorschauOffen && vorschauRechnung}
      {@const badge = statusBadge(vorschauRechnung)}
      <div class="vorschau-panel">
        <div class="vorschau-hdr">
          <span class="vorschau-titel">{vorschauRechnung.rechnung_nr || 'Rechnung'}</span>
          <button class="icon-btn" onclick={() => { vorschauOffen = false; vorschauRechnung = null; }}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
        <div class="vorschau-body">
          <div class="vorschau-row">
            <span class="badge {badge.cls}">{badge.label}</span>
            <span class="vorschau-datum">{fmtDatum(vorschauRechnung.erstellt_am)}</span>
          </div>
          {#if vorschauRechnung.rechnung_typ === 'storno'}
            <div class="storno-hinweis">Stornorechnung zu einer vorherigen Rechnung</div>
          {/if}
          <div class="vorschau-section">
            <div class="vs-label">Rechnungsempfaenger</div>
            <div class="vs-value">{vorschauRechnung.kaeufer_name || '-'}</div>
            {#if vorschauRechnung.kaeufer_strasse}
              <div class="vs-sub">{vorschauRechnung.kaeufer_strasse}</div>
              <div class="vs-sub">{vorschauRechnung.kaeufer_plz} {vorschauRechnung.kaeufer_ort}, {vorschauRechnung.kaeufer_land}</div>
            {/if}
            {#if vorschauRechnung.kaeufer_email}
              <div class="vs-sub" style="color:var(--primary)">{vorschauRechnung.kaeufer_email}</div>
            {/if}
          </div>
          <div class="vorschau-section">
            <div class="vs-label">Artikel</div>
            <div class="pos-zeile">
              <div>
                <div class="pos-name">{vorschauRechnung.artikel_name || '-'}</div>
                {#if vorschauRechnung.ebay_artikel_id}
                  <div style="font-size:0.72rem;color:var(--text3)">eBay: {vorschauRechnung.ebay_artikel_id}</div>
                {/if}
              </div>
              <span class="pos-detail">{vorschauRechnung.artikel_menge || 1} x {fmt(vorschauRechnung.einzelpreis)} EUR</span>
            </div>
          </div>
          {#if vorschauRechnung.order_id}
            <div class="vorschau-section">
              <div class="vs-label">eBay-Bestellnummer</div>
              <div class="vs-value" style="font-family:monospace;font-size:0.8rem">{vorschauRechnung.order_id}</div>
            </div>
          {/if}
          <div class="betraege-box">
            <div class="betrag-zeile"><span>Netto</span><span>{fmt(vorschauRechnung.netto_betrag)} EUR</span></div>
            <div class="betrag-zeile"><span>MwSt. ({vorschauRechnung.steuersatz || 19} %)</span><span>{fmt(vorschauRechnung.steuer_betrag)} EUR</span></div>
            <div class="betrag-zeile betrag-brutto"><span>Brutto</span><span>{fmt(vorschauRechnung.brutto_betrag)} EUR</span></div>
          </div>
          {#if vorschauRechnung.email_gesendet_an}
            <div class="vorschau-section">
              <div class="vs-label">Gesendet an</div>
              <div class="vs-sub">{vorschauRechnung.email_gesendet_an}</div>
            </div>
          {/if}
          <div class="vorschau-aktionen">
            <button class="btn-secondary btn-sm" onclick={() => ladePDF(vorschauRechnung)}>PDF</button>
            {#if vorschauRechnung.status !== 'storniert' && vorschauRechnung.rechnung_typ !== 'storno'}
              <button class="btn-secondary btn-sm" onclick={() => oeffneSendenModal(vorschauRechnung)}>E-Mail</button>
              <!-- E-Rechnung im Vorschau-Panel -->
              <div class="erechnungs-wrap" style="position:relative" onclick={(e) => e.stopPropagation()}>
                <button class="btn-secondary btn-sm" onclick={(e) => oeffneERechnungMenu(vorschauRechnung, e)}>E-Rechnung ▾</button>
                {#if eRechnungMenuOffen && eRechnungRechnung?.id === vorschauRechnung.id}
                  <div class="erechnung-menu" style="bottom:auto;top:calc(100% + 4px)">
                    <button onclick={() => erstelleERechnung(vorschauRechnung, 'zugferd_en16931')}>ZUGFeRD 2.4 EN16931 PDF</button>
                    <button onclick={() => erstelleERechnung(vorschauRechnung, 'zugferd_extended')}>ZUGFeRD 2.4 EXTENDED PDF (BETA)</button>
                    <button onclick={() => erstelleERechnung(vorschauRechnung, 'xrechnung')}>XRechnung 3.0.2 XML</button>
                  </div>
                {/if}
              </div>
              <button class="btn-secondary btn-sm" onclick={() => oeffneBearbeitenModal(vorschauRechnung)}>Bearbeiten</button>
              <button class="btn-danger btn-sm" onclick={() => oeffneStornoModal(vorschauRechnung)}>Stornieren</button>
            {/if}
          </div>
        </div>
      </div>
    {/if}
  </div>

  <!-- Pagination -->
  {#if gefiltert.length > 0}
    <div class="footer-bar">
      <div class="footer-summen">
        <span>Netto gesamt: <strong>{fmt(summeNetto)} EUR</strong></span>
        {#if summeStorno > 0}<span class="storno-summe">Stornos: <strong>{fmt(summeStorno)} EUR</strong></span>{/if}
        <span class="footer-count">{gefiltert.length} Eintraege</span>
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

<!-- MODAL: SCHNELLSUCHE BESTELLDETAILS -->
{#if schnellsucheModalOffen && schnellsucheErgebnis}
  {@const b = schnellsucheErgebnis}
  <div class="modal-overlay" onclick={schliesseSchnellsucheModal}>
    <div class="modal-box modal-bestellung" onclick={(e) => e.stopPropagation()}>
      <div class="modal-hdr">
        <div>
          <span class="modal-titel">Bestellung gefunden</span>
          <div style="font-size:0.78rem;color:var(--text3);margin-top:2px;font-family:monospace">{b.order_id || schnellsucheOrderId}</div>
        </div>
        <button class="icon-btn" onclick={schliesseSchnellsucheModal}>X</button>
      </div>
      <div class="modal-body">
        <div style="margin-bottom:16px">
          {#if b.hat_rechnung}
            <span class="badge badge-gesendet">Rechnung bereits vorhanden</span>
          {:else}
            <span class="badge badge-erstellt">Noch keine Rechnung</span>
          {/if}
        </div>
        <div class="bm-section">
          <div class="bm-section-titel">Kaeufer</div>
          <div class="bm-grid">
            <div class="bm-field"><div class="bm-label">Name</div><div class="bm-value">{b.kaeufer_name || '-'}</div></div>
            <div class="bm-field"><div class="bm-label">E-Mail</div><div class="bm-value">{b.kaeufer_email || '-'}</div></div>
            <div class="bm-field"><div class="bm-label">Adresse</div><div class="bm-value">{b.kaeufer_strasse || '-'}, {b.kaeufer_plz || ''} {b.kaeufer_ort || ''}, {b.kaeufer_land || 'DE'}</div></div>
          </div>
        </div>
        <div class="bm-section">
          <div class="bm-section-titel">Artikel</div>
          <div class="bm-grid">
            <div class="bm-field" style="grid-column:1/-1"><div class="bm-label">Bezeichnung</div><div class="bm-value">{b.artikel_name || '-'}</div></div>
            {#if b.ebay_artikel_id}<div class="bm-field"><div class="bm-label">eBay Artikel-ID</div><div class="bm-value" style="font-family:monospace">{b.ebay_artikel_id}</div></div>{/if}
            <div class="bm-field"><div class="bm-label">Menge</div><div class="bm-value">{b.artikel_menge || 1}</div></div>
          </div>
        </div>
        <div class="bm-section">
          <div class="bm-section-titel">Zahlung</div>
          <div class="betraege-box" style="margin-top:8px">
            <div class="betrag-zeile"><span>Betrag (Brutto)</span><span style="font-weight:700;color:var(--primary);font-size:1.1rem">{fmt(b.brutto_betrag)} EUR</span></div>
            {#if b.zahlungsdatum}<div class="betrag-zeile"><span>Datum</span><span>{fmtDatum(b.zahlungsdatum)}</span></div>{/if}
          </div>
        </div>
        {#if b.versand_tracking || b.versand_anbieter}
          <div class="bm-section">
            <div class="bm-section-titel">Versand</div>
            <div class="bm-grid">
              {#if b.versand_anbieter}<div class="bm-field"><div class="bm-label">Anbieter</div><div class="bm-value">{b.versand_anbieter}</div></div>{/if}
              {#if b.versand_tracking}<div class="bm-field"><div class="bm-label">Tracking</div><div class="bm-value" style="font-family:monospace;color:var(--primary)">{b.versand_tracking}</div></div>{/if}
            </div>
          </div>
        {/if}
      </div>
      <div class="modal-footer">
        <button class="btn-ghost" onclick={schliesseSchnellsucheModal}>Schliessen</button>
        <button class="btn-primary" onclick={rechnungAusSchnellsuche}>Rechnung erstellen</button>
      </div>
    </div>
  </div>
{/if}

<!-- MODAL: RECHNUNG ERSTELLEN -->
{#if erstellenModal}
  <div class="modal-overlay" onclick={() => erstellenModal = false}>
    <div class="modal-box" onclick={(e) => e.stopPropagation()}>
      <div class="modal-hdr">
        <span class="modal-titel">Neue Rechnung erstellen</span>
        <button class="icon-btn" onclick={() => erstellenModal = false}>X</button>
      </div>
      <div class="modal-body">
        <div class="form-grid">
          <div class="form-group"><label>Kaeufer *</label><input bind:value={neueRechnung.kaeufer_name} placeholder="Max Mustermann" /></div>
          <div class="form-group"><label>E-Mail</label><input bind:value={neueRechnung.kaeufer_email} type="email" placeholder="max@example.com" /></div>
          <div class="form-group"><label>Strasse</label><input bind:value={neueRechnung.kaeufer_strasse} placeholder="Musterstr. 1" /></div>
          <div class="form-group form-2col">
            <div class="form-group"><label>PLZ</label><input bind:value={neueRechnung.kaeufer_plz} placeholder="12345" /></div>
            <div class="form-group"><label>Ort</label><input bind:value={neueRechnung.kaeufer_ort} placeholder="Berlin" /></div>
          </div>
          <div class="form-group">
            <label>eBay Bestellnr.</label>
            <div style="display:flex;gap:8px">
              <input bind:value={neueRechnung.order_id} placeholder="12-34567-89012" style="flex:1" oninput={clearBestellungLaden} />
              <button class="btn-primary btn-sm" onclick={ladeBestellungDaten} disabled={bestellungLaeuft || !neueRechnung.order_id} style="white-space:nowrap">
                {bestellungLaeuft ? '...' : 'Laden'}
              </button>
            </div>
            {#if bestellungFehler}<p style="color:#ef4444;font-size:0.75rem;margin-top:4px">{bestellungFehler}</p>{/if}
          </div>
          <div class="form-group form-2col"><div class="form-group"><label>Land</label><input bind:value={neueRechnung.kaeufer_land} placeholder="DE" /></div></div>
          <div class="form-group"><label>Artikel *</label><input bind:value={neueRechnung.artikel_name} placeholder="Produktname" /></div>
          <div class="form-group"><label>eBay Artikel-ID</label><input bind:value={neueRechnung.ebay_artikel_id} placeholder="123456789012" /></div>
          <div class="form-group form-2col">
            <div class="form-group"><label>Menge *</label><input bind:value={neueRechnung.menge} type="number" min="1" /></div>
            <div class="form-group"><label>Einzelpreis Brutto *</label><input bind:value={neueRechnung.einzelpreis} type="number" step="0.01" placeholder="9.99" /></div>
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-ghost" onclick={() => erstellenModal = false}>Abbrechen</button>
        <button class="btn-primary" onclick={erstelleManuell} disabled={erstellenLaeuft}>{erstellenLaeuft ? 'Erstelle...' : 'Rechnung erstellen'}</button>
      </div>
    </div>
  </div>
{/if}

<!-- MODAL: E-MAIL SENDEN -->
{#if sendenModal}
  <div class="modal-overlay" onclick={() => sendenModal = false}>
    <div class="modal-box modal-klein" onclick={(e) => e.stopPropagation()}>
      <div class="modal-hdr">
        <span class="modal-titel">Rechnung senden</span>
        <button class="icon-btn" onclick={() => sendenModal = false}>X</button>
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

<!-- MODAL: STORNO -->
{#if stornoModal}
  <div class="modal-overlay" onclick={() => stornoModal = false}>
    <div class="modal-box modal-klein" onclick={(e) => e.stopPropagation()}>
      <div class="modal-hdr">
        <span class="modal-titel">Rechnung stornieren</span>
        <button class="icon-btn" onclick={() => stornoModal = false}>X</button>
      </div>
      <div class="modal-body">
        <p class="modal-info">Moechtest du die Rechnung <strong>{stornoRechnung?.rechnung_nr}</strong> wirklich stornieren? Es wird eine Stornorechnung erstellt.</p>
      </div>
      <div class="modal-footer">
        <button class="btn-ghost" onclick={() => stornoModal = false}>Abbrechen</button>
        <button class="btn-danger" onclick={erstelleStorno} disabled={stornoLaeuft}>{stornoLaeuft ? 'Storniere...' : 'Jetzt stornieren'}</button>
      </div>
    </div>
  </div>
{/if}

<!-- MODAL: RECHNUNG BEARBEITEN -->
{#if bearbeitenModal && bearbeitenRechnung}
  <div class="modal-overlay" onclick={() => bearbeitenModal = false}>
    <div class="modal-box" onclick={(e) => e.stopPropagation()}>
      <div class="modal-hdr">
        <span class="modal-titel">Rechnung bearbeiten - {bearbeitenRechnung.rechnung_nr}</span>
        <button class="icon-btn" onclick={() => bearbeitenModal = false}>X</button>
      </div>
      <div class="modal-body">
        <div class="bearbeiten-hinweis">Die bestehende Rechnung wird storniert und eine neue erstellt.</div>
        <div class="bearbeiten-kaeufer">
          <span class="vs-label">Kaeufer</span>
          <span class="vs-value">{bearbeitenRechnung.kaeufer_name}</span>
          <span class="vs-sub">{bearbeitenRechnung.order_id || ''}</span>
        </div>
        <div class="vs-label" style="margin-top:12px;margin-bottom:8px">Positionen</div>
        {#each bearbeitenPositionen as pos, idx}
          <div class="bearbeiten-position {pos.entfernt ? 'pos-entfernt' : ''}">
            <div class="pos-check">
              <input type="checkbox" checked={!pos.entfernt} onchange={() => togglePosition(idx)} />
            </div>
            <div class="pos-details">
              <div class="pos-name" style="font-size:0.84rem">{pos.artikel_name}</div>
              {#if pos.ebay_artikel_id}<div style="font-size:0.72rem;color:var(--text3)">eBay: {pos.ebay_artikel_id}</div>{/if}
            </div>
            <div class="pos-menge">
              <label style="font-size:0.72rem;color:var(--text3)">Menge</label>
              <input type="number" min="1" value={pos.menge} oninput={(e) => updatePositionMenge(idx, e.target.value)} disabled={pos.entfernt} style="width:60px;padding:4px 8px;border-radius:6px;border:1px solid var(--border);background:var(--surface);color:var(--text);font-size:0.83rem;text-align:center" />
            </div>
            <div class="pos-preis">
              {fmt(pos.einzelpreis * (pos.entfernt ? 0 : pos.menge))} EUR
              {#if pos.entfernt}<span style="font-size:0.7rem;color:#ef4444;margin-left:4px">entfernt</span>{/if}
            </div>
          </div>
        {/each}
        <div class="betraege-box" style="margin-top:12px">
          <div class="betrag-zeile"><span>Netto (neu)</span><span>{fmt(aktiveSumme / 1.19)} EUR</span></div>
          <div class="betrag-zeile"><span>MwSt. 19%</span><span>{fmt(aktiveSumme - aktiveSumme / 1.19)} EUR</span></div>
          <div class="betrag-zeile betrag-brutto"><span>Brutto (neu)</span><span>{fmt(aktiveSumme)} EUR</span></div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-ghost" onclick={() => bearbeitenModal = false}>Abbrechen</button>
        <button class="btn-primary" onclick={speichereBearbeitung} disabled={bearbeitenLaeuft}>{bearbeitenLaeuft ? 'Speichere...' : 'Storno + Neue Rechnung'}</button>
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
  .haupt-bereich { display:flex; gap:16px; align-items:flex-start; }
  .tabellen-wrapper { flex:1; background:var(--surface); border:1px solid var(--border); border-radius:10px; overflow:hidden; min-width:0; }
  .tabelle { width:100%; border-collapse:collapse; font-size:0.83rem; }
  .tabelle thead tr { background:var(--surface2); }
  .tabelle th { padding:10px 12px; text-align:left; font-weight:600; font-size:0.75rem; color:var(--text2); border-bottom:1px solid var(--border); white-space:nowrap; }
  .th-check { width:36px; }
  .th-right { text-align:right; }
  .th-actions { width:170px; }
  .tbl-row { border-bottom:1px solid var(--border); cursor:pointer; transition:background 0.12s; }
  .tbl-row:last-child { border-bottom:none; }
  .tbl-row:hover { background:var(--surface2); }
  .tbl-row.aktiv { background:var(--primary-light); }
  .tabelle td { padding:10px 12px; color:var(--text); vertical-align:middle; }
  .td-check { width:36px; }
  .td-nr { font-weight:600; white-space:nowrap; color:var(--primary); }
  .td-datum { white-space:nowrap; color:var(--text2); font-size:0.8rem; }
  .td-kaeufer { max-width:150px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .td-artikel { max-width:160px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--text2); }
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
  .vorschau-panel { width:300px; flex-shrink:0; background:var(--surface); border:1px solid var(--border); border-radius:10px; overflow:hidden; display:flex; flex-direction:column; }
  .vorschau-hdr { display:flex; align-items:center; justify-content:space-between; padding:14px 16px; border-bottom:1px solid var(--border); background:var(--surface2); }
  .vorschau-titel { font-size:0.88rem; font-weight:600; color:var(--text); }
  .vorschau-body { padding:16px; display:flex; flex-direction:column; gap:14px; overflow-y:auto; }
  .vorschau-row { display:flex; align-items:center; justify-content:space-between; }
  .vorschau-datum { font-size:0.78rem; color:var(--text2); }
  .vorschau-section { display:flex; flex-direction:column; gap:3px; }
  .vs-label { font-size:0.72rem; font-weight:600; color:var(--text3); text-transform:uppercase; letter-spacing:0.05em; margin-bottom:5px; }
  .vs-value { font-size:0.85rem; color:var(--text); font-weight:500; }
  .vs-sub { font-size:0.78rem; color:var(--text2); margin-top:2px; }
  .pos-zeile { display:flex; justify-content:space-between; align-items:baseline; padding:4px 0; border-bottom:1px solid var(--border); }
  .pos-name { font-size:0.82rem; color:var(--text); flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .pos-detail { font-size:0.78rem; color:var(--text2); white-space:nowrap; margin-left:8px; }
  .betraege-box { background:var(--surface2); border-radius:8px; padding:12px; display:flex; flex-direction:column; gap:6px; }
  .betrag-zeile { display:flex; justify-content:space-between; font-size:0.82rem; color:var(--text2); }
  .betrag-brutto { color:var(--text); font-weight:700; font-size:0.9rem; border-top:1px solid var(--border); padding-top:6px; margin-top:2px; }
  .vorschau-aktionen { display:flex; gap:8px; flex-wrap:wrap; }
  .storno-hinweis { background:#fef2f2; border:1px solid #fecaca; border-radius:6px; padding:7px 10px; font-size:0.77rem; color:#dc2626; }
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
  .modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.45); z-index:1000; display:flex; align-items:center; justify-content:center; padding:20px; }
  .modal-box { background:var(--surface); border:1px solid var(--border); border-radius:14px; width:100%; max-width:560px; max-height:90vh; display:flex; flex-direction:column; box-shadow:0 20px 60px rgba(0,0,0,0.2); }
  .modal-klein { max-width:400px; }
  .modal-bestellung { max-width:620px; }
  .modal-hdr { display:flex; align-items:center; justify-content:space-between; padding:18px 20px 14px; border-bottom:1px solid var(--border); }
  .modal-titel { font-size:1rem; font-weight:600; color:var(--text); }
  .modal-body { padding:20px; overflow-y:auto; }
  .modal-footer { display:flex; gap:10px; justify-content:flex-end; padding:14px 20px 18px; border-top:1px solid var(--border); }
  .modal-info { font-size:0.85rem; color:var(--text2); margin-bottom:14px; line-height:1.5; }
  .modal-info strong { color:var(--text); }
  .form-grid { display:flex; flex-direction:column; gap:14px; }
  .form-group { display:flex; flex-direction:column; gap:5px; }
  .form-2col { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
  .form-group label { font-size:0.78rem; color:var(--text2); font-weight:500; }
  .form-group input { background:var(--surface); border:1px solid var(--border); color:var(--text); padding:8px 12px; border-radius:8px; font-size:0.85rem; outline:none; }
  .form-group input:focus { border-color:var(--primary); }
  .form-group input::placeholder { color:var(--text3); }
  .bm-section { margin-bottom:18px; }
  .bm-section-titel { font-size:0.75rem; font-weight:700; color:var(--text3); text-transform:uppercase; letter-spacing:0.06em; margin-bottom:10px; padding-bottom:6px; border-bottom:1px solid var(--border); }
  .bm-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
  .bm-field { display:flex; flex-direction:column; gap:3px; }
  .bm-label { font-size:0.72rem; color:var(--text3); font-weight:500; }
  .bm-value { font-size:0.85rem; color:var(--text); font-weight:500; line-height:1.4; }
  .bearbeiten-hinweis { background:#fffbeb; border:1px solid #fde68a; border-radius:8px; padding:10px 12px; font-size:0.8rem; color:#92400e; margin-bottom:14px; }
  .bearbeiten-kaeufer { display:flex; align-items:baseline; gap:8px; margin-bottom:4px; }
  .bearbeiten-position { display:flex; align-items:center; gap:10px; padding:10px 12px; border:1px solid var(--border); border-radius:8px; margin-bottom:8px; transition:opacity 0.2s; }
  .pos-entfernt { opacity:0.45; background:var(--surface2); }
  .pos-check { flex-shrink:0; }
  .pos-details { flex:1; min-width:0; }
  .pos-menge { display:flex; flex-direction:column; align-items:center; gap:2px; }
  .pos-preis { font-size:0.85rem; font-weight:600; color:var(--text); white-space:nowrap; min-width:70px; text-align:right; }
</style>
