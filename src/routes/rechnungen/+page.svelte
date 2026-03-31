<script>
  import { onMount } from 'svelte';
  import { currentUser, showToast } from '$lib/stores.js';
  import { apiCall } from '$lib/api.js';

  // ── State ──────────────────────────────────────────────────────────────────
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

  let neueRechnung = $state({
    kaeufer: '', buyeremail: '', buyerstrasse: '', buyerplz: '',
    buyerort: '', buyerland: 'DE', artikelname: '', ebayartikelid: '',
    menge: 1, einzelpreis: '', orderid: ''
  });
  let erstellenLaeuft = $state(false);

  // ── Derived ────────────────────────────────────────────────────────────────
  let gefiltert = $derived.by(() => {
    let liste = rechnungen;
    if (aktiverFilter === 'rechnungen') liste = liste.filter(r => r.status !== 'storniert');
    else if (aktiverFilter === 'stornos') liste = liste.filter(r => r.status === 'storniert');
    else if (aktiverFilter === 'erstellt') liste = liste.filter(r => r.status === 'erstellt');
    else if (aktiverFilter === 'gesendet') liste = liste.filter(r => r.status === 'gesendet');
    if (suchbegriff.trim()) {
      const s = suchbegriff.toLowerCase();
      liste = liste.filter(r =>
        r.rechnungsnummer?.toLowerCase().includes(s) ||
        r.kaeuferdaten?.name?.toLowerCase().includes(s) ||
        r.positionen?.[0]?.artikelname?.toLowerCase().includes(s) ||
        r.orderid?.toLowerCase().includes(s)
      );
    }
    return liste;
  });

  let gesamtSeiten = $derived(Math.max(1, Math.ceil(gefiltert.length / proSeite)));

  let sichtbar = $derived(gefiltert.slice(
    (aktuelleSeite - 1) * proSeite,
    aktuelleSeite * proSeite
  ));

  let summeNetto = $derived(
    gefiltert.filter(r => r.status !== 'storniert')
      .reduce((s, r) => s + (r.betraege?.netto || 0), 0)
  );
  let summeStorno = $derived(
    gefiltert.filter(r => r.status === 'storniert')
      .reduce((s, r) => s + (r.betraege?.brutto || 0), 0)
  );

  let kpiGesamt    = $derived(rechnungen.length);
  let kpiGesendet  = $derived(rechnungen.filter(r => r.status === 'gesendet').length);
  let kpiAusstehend= $derived(rechnungen.filter(r => r.status === 'erstellt').length);
  let kpiStorniert = $derived(rechnungen.filter(r => r.status === 'storniert').length);
  let kpiBrutto    = $derived(
    rechnungen.filter(r => r.status !== 'storniert')
      .reduce((s, r) => s + (r.betraege?.brutto || 0), 0)
  );
  let kpiDieserMonat = $derived.by(() => {
    const jetzt = new Date();
    return rechnungen.filter(r => {
      const d = new Date(r.erstelltam);
      return d.getFullYear() === jetzt.getFullYear() && d.getMonth() === jetzt.getMonth();
    }).length;
  });

  // ── Lifecycle ──────────────────────────────────────────────────────────────
  onMount(() => {
    if ($currentUser) ladeRechnungen();
  });

  // ── Funktionen ─────────────────────────────────────────────────────────────
  async function ladeRechnungen() {
    loading = true;
    fehler = '';
    try {
      const data = await apiCall('rechnungen-laden', {
        userid: $currentUser.id,
        ebayusername: $currentUser.ebayuserid
      });
      rechnungen = Array.isArray(data) ? data : (data.rechnungen || []);
    } catch (e) {
      fehler = e.message;
    } finally {
      loading = false;
    }
  }

  async function ladePDF(rechnung) {
    try {
      showToast('PDF wird geladen…');
      const data = await apiCall('rechnung-pdf', {
        invoiceid: rechnung.id,
        userid: $currentUser.id
      });
      const b64 = data.pdfbase64 || data.pdf;
      if (!b64) { showToast('Kein PDF vorhanden.'); return; }
      const blob = new Blob(
        [Uint8Array.from(atob(b64), c => c.charCodeAt(0))],
        { type: 'application/pdf' }
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = (rechnung.rechnungsnummer || 'Rechnung') + '.pdf';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      showToast('Fehler: ' + e.message);
    }
  }

  function oeffneVorschau(r) {
    vorschauRechnung = r;
    vorschauOffen = true;
  }

  function oeffneSendenModal(r) {
    sendenRechnung = r;
    sendenEmail = r.kaeuferdaten?.email || '';
    sendenModal = true;
  }

  async function sendeRechnung() {
    if (!sendenEmail) { showToast('Bitte E-Mail eingeben.'); return; }
    sendenLaeuft = true;
    try {
      await apiCall('rechnung-senden', {
        invoiceid: sendenRechnung.id,
        userid: $currentUser.id,
        toemail: sendenEmail
      });
      showToast('Rechnung gesendet ✓');
      sendenModal = false;
      await ladeRechnungen();
    } catch (e) {
      showToast('Fehler: ' + e.message);
    } finally {
      sendenLaeuft = false;
    }
  }

  function oeffneStornoModal(r) {
    stornoRechnung = r;
    stornoModal = true;
  }

  async function erstelleStorno() {
    stornoLaeuft = true;
    try {
      await apiCall('rechnung-erstellen', {
        userid: $currentUser.id,
        typ: 'storno',
        originalid: stornoRechnung.id,
        orderid: stornoRechnung.orderid,
        kaeufer: stornoRechnung.kaeuferdaten?.name,
        artikelname: stornoRechnung.positionen?.[0]?.artikelname,
        menge: stornoRechnung.positionen?.[0]?.menge,
        einzelpreis: stornoRechnung.positionen?.[0]?.einzelpreis,
        ebayartikelid: stornoRechnung.positionen?.[0]?.ebayartikelid
      });
      showToast('Stornorechnung erstellt ✓');
      stornoModal = false;
      await ladeRechnungen();
    } catch (e) {
      showToast('Fehler: ' + e.message);
    } finally {
      stornoLaeuft = false;
    }
  }

  async function erstelleManuell() {
    if (!neueRechnung.kaeufer || !neueRechnung.artikelname || !neueRechnung.einzelpreis) {
      showToast('Bitte alle Pflichtfelder ausfüllen.');
      return;
    }
    erstellenLaeuft = true;
    try {
      await apiCall('rechnung-erstellen', {
        userid: $currentUser.id,
        typ: 'rechnung',
        orderid: neueRechnung.orderid || '',
        kaeufer: neueRechnung.kaeufer,
        buyeremail: neueRechnung.buyeremail,
        buyerstrasse: neueRechnung.buyerstrasse,
        buyerplz: neueRechnung.buyerplz,
        buyerort: neueRechnung.buyerort,
        buyerland: neueRechnung.buyerland,
        artikelname: neueRechnung.artikelname,
        ebayartikelid: neueRechnung.ebayartikelid,
        menge: Number(neueRechnung.menge),
        einzelpreis: Number(neueRechnung.einzelpreis)
      });
      showToast('Rechnung erstellt ✓');
      erstellenModal = false;
      neueRechnung = {
        kaeufer:'', buyeremail:'', buyerstrasse:'', buyerplz:'',
        buyerort:'', buyerland:'DE', artikelname:'', ebayartikelid:'',
        menge:1, einzelpreis:'', orderid:''
      };
      await ladeRechnungen();
    } catch (e) {
      showToast('Fehler: ' + e.message);
    } finally {
      erstellenLaeuft = false;
    }
  }

  function toggleAuswahl(id) {
    const neu = new Set(ausgewaehlt);
    neu.has(id) ? neu.delete(id) : neu.add(id);
    ausgewaehlt = neu;
    alleAusgewaehlt = sichtbar.length > 0 && sichtbar.every(r => neu.has(r.id));
  }

  function toggleAlleAuswaehlen() {
    if (alleAusgewaehlt) {
      ausgewaehlt = new Set();
      alleAusgewaehlt = false;
    } else {
      ausgewaehlt = new Set(sichtbar.map(r => r.id));
      alleAusgewaehlt = true;
    }
  }

  function setFilter(f) {
    aktiverFilter = f;
    aktuelleSeite = 1;
    ausgewaehlt = new Set();
    alleAusgewaehlt = false;
  }

  function fmt(n) {
    return Number(n || 0).toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function fmtDatum(d) {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' });
  }

  function statusBadge(status) {
    const map = {
      erstellt:  { label: 'Erstellt',  cls: 'badge-erstellt'  },
      gesendet:  { label: 'Gesendet',  cls: 'badge-gesendet'  },
      storniert: { label: 'Storniert', cls: 'badge-storniert' }
    };
    return map[status] || { label: status, cls: '' };
  }

  const filterTabs = [
    { key: 'alle',       label: 'Alle'       },
    { key: 'rechnungen', label: 'Rechnungen' },
    { key: 'stornos',    label: 'Stornos'    },
    { key: 'erstellt',   label: 'Erstellt'   },
    { key: 'gesendet',   label: 'Gesendet'   }
  ];

  function tabCount(key) {
    if (key === 'alle')       return rechnungen.length;
    if (key === 'rechnungen') return rechnungen.filter(r => r.status !== 'storniert').length;
    if (key === 'stornos')    return rechnungen.filter(r => r.status === 'storniert').length;
    if (key === 'erstellt')   return rechnungen.filter(r => r.status === 'erstellt').length;
    if (key === 'gesendet')   return rechnungen.filter(r => r.status === 'gesendet').length;
    return 0;
  }
</script>

<!-- PAGE -->
<div class="page-container">

  <!-- Header -->
  <div class="page-hdr">
    <div>
      <div class="page-title">Rechnungen</div>
      <div class="page-sub">Automatisch erstellte Rechnungen verwalten</div>
    </div>
    <div class="hdr-actions">
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
    <div class="kpi-card">
      <div class="kpi-label">Gesamt</div>
      <div class="kpi-value">{kpiGesamt}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Gesendet</div>
      <div class="kpi-value kpi-blue">{kpiGesendet}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Ausstehend</div>
      <div class="kpi-value kpi-yellow">{kpiAusstehend}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Storniert</div>
      <div class="kpi-value kpi-red">{kpiStorniert}</div>
    </div>
    <div class="kpi-card kpi-card-wide">
      <div class="kpi-label">Umsatz Brutto (aktive)</div>
      <div class="kpi-value kpi-blue">{fmt(kpiBrutto)} €</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Diesen Monat</div>
      <div class="kpi-value">{kpiDieserMonat}</div>
    </div>
  </div>

  <!-- Toolbar -->
  <div class="toolbar">
    <div class="filter-tabs">
      {#each filterTabs as tab (tab.key)}
        <button
          class="filter-tab {aktiverFilter === tab.key ? 'active' : ''}"
          onclick={() => setFilter(tab.key)}
        >
          {tab.label}
          <span class="tab-count">{tabCount(tab.key)}</span>
        </button>
      {/each}
    </div>
    <div class="toolbar-right">
      <input
        class="suche-input"
        type="text"
        placeholder="Suche Nr., Käufer, Artikel…"
        bind:value={suchbegriff}
      />
      <select class="select-klein" bind:value={proSeite} onchange={() => aktuelleSeite = 1}>
        <option value={20}>20 / Seite</option>
        <option value={50}>50 / Seite</option>
        <option value={100}>100 / Seite</option>
      </select>
    </div>
  </div>

  {#if ausgewaehlt.size > 0}
    <div class="bulk-bar">
      <span>{ausgewaehlt.size} ausgewählt</span>
      <button class="btn-ghost btn-sm" onclick={() => { ausgewaehlt = new Set(); alleAusgewaehlt = false; }}>
        Auswahl aufheben
      </button>
    </div>
  {/if}

  <!-- Haupt-Bereich -->
  <div class="haupt-bereich">

    <!-- Tabelle -->
    <div class="tabellen-wrapper">
      {#if loading}
        <div class="status-info">Lade Rechnungen…</div>
      {:else if fehler}
        <div class="status-info status-fehler">{fehler}</div>
      {:else if sichtbar.length === 0}
        <div class="leer-state">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
          <p>Keine Rechnungen gefunden</p>
          <button class="btn-primary btn-sm" onclick={() => erstellenModal = true}>
            Erste Rechnung erstellen
          </button>
        </div>
      {:else}
        <table class="tabelle">
          <thead>
            <tr>
              <th class="th-check">
                <input type="checkbox" checked={alleAusgewaehlt} onchange={toggleAlleAuswaehlen} />
              </th>
              <th>Nummer</th>
              <th>Datum</th>
              <th>Käufer</th>
              <th>Artikel</th>
              <th class="th-right">Netto</th>
              <th class="th-right">MwSt.</th>
              <th class="th-right">Brutto</th>
              <th>Status</th>
              <th class="th-actions">Aktionen</th>
            </tr>
          </thead>
          <tbody>
            {#each sichtbar as r (r.id)}
              {@const badge = statusBadge(r.status)}
              <tr
                class="tbl-row {vorschauRechnung?.id === r.id ? 'aktiv' : ''}"
                onclick={() => oeffneVorschau(r)}
              >
                <td class="td-check" onclick={(e) => { e.stopPropagation(); toggleAuswahl(r.id); }}>
                  <input type="checkbox" checked={ausgewaehlt.has(r.id)} onchange={() => toggleAuswahl(r.id)} />
                </td>
                <td class="td-nr">{r.rechnungsnummer || '—'}</td>
                <td class="td-datum">{fmtDatum(r.erstelltam)}</td>
                <td class="td-kaeufer">{r.kaeuferdaten?.name || '—'}</td>
                <td class="td-artikel">{r.positionen?.[0]?.artikelname || '—'}</td>
                <td class="td-right">{fmt(r.betraege?.netto)} €</td>
                <td class="td-right">{fmt(r.betraege?.mwst)} €</td>
                <td class="td-right td-bold">{fmt(r.betraege?.brutto)} €</td>
                <td><span class="badge {badge.cls}">{badge.label}</span></td>
                <td class="td-actions" onclick={(e) => e.stopPropagation()}>
                  <button class="icon-btn" title="Vorschau" onclick={() => oeffneVorschau(r)}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                      <circle cx="12" cy="12" r="3"/>
                    </svg>
                  </button>
                  <button class="icon-btn" title="PDF" onclick={() => ladePDF(r)}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                      <polyline points="7 10 12 15 17 10"/>
                      <line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                  </button>
                  {#if r.status !== 'storniert'}
                    <button class="icon-btn" title="E-Mail senden" onclick={() => oeffneSendenModal(r)}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                        <polyline points="22,6 12,13 2,6"/>
                      </svg>
                    </button>
                    <button class="icon-btn icon-btn-danger" title="Stornieren" onclick={() => oeffneStornoModal(r)}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6l-1 14H6L5 6"/>
                        <path d="M10 11v6M14 11v6M9 6V4h6v2"/>
                      </svg>
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
      {@const badge = statusBadge(vorschauRechnung.status)}
      <div class="vorschau-panel">
        <div class="vorschau-hdr">
          <span class="vorschau-titel">{vorschauRechnung.rechnungsnummer || 'Rechnung'}</span>
          <button class="icon-btn" onclick={() => { vorschauOffen = false; vorschauRechnung = null; }}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <div class="vorschau-body">
          <div class="vorschau-row">
            <span class="badge {badge.cls}">{badge.label}</span>
            <span class="vorschau-datum">{fmtDatum(vorschauRechnung.erstelltam)}</span>
          </div>
          <div class="vorschau-section">
            <div class="vs-label">Käufer</div>
            <div class="vs-value">{vorschauRechnung.kaeuferdaten?.name || '—'}</div>
            {#if vorschauRechnung.kaeuferdaten?.email}
              <div class="vs-sub">{vorschauRechnung.kaeuferdaten.email}</div>
            {/if}
            {#if vorschauRechnung.kaeuferdaten?.strasse}
              <div class="vs-sub">
                {vorschauRechnung.kaeuferdaten.strasse},
                {vorschauRechnung.kaeuferdaten.plz}
                {vorschauRechnung.kaeuferdaten.ort},
                {vorschauRechnung.kaeuferdaten.land}
              </div>
            {/if}
          </div>
          <div class="vorschau-section">
            <div class="vs-label">Positionen</div>
            {#each (vorschauRechnung.positionen || []) as pos}
              <div class="pos-zeile">
                <span class="pos-name">{pos.artikelname}</span>
                <span class="pos-detail">{pos.menge} × {fmt(pos.einzelpreis)} €</span>
              </div>
            {/each}
          </div>
          <div class="betraege-box">
            <div class="betrag-zeile">
              <span>Netto</span><span>{fmt(vorschauRechnung.betraege?.netto)} €</span>
            </div>
            <div class="betrag-zeile">
              <span>MwSt. (19 %)</span><span>{fmt(vorschauRechnung.betraege?.mwst)} €</span>
            </div>
            <div class="betrag-zeile betrag-brutto">
              <span>Brutto</span><span>{fmt(vorschauRechnung.betraege?.brutto)} €</span>
            </div>
          </div>
          <div class="vorschau-aktionen">
            <button class="btn-secondary btn-sm" onclick={() => ladePDF(vorschauRechnung)}>PDF</button>
            {#if vorschauRechnung.status !== 'storniert'}
              <button class="btn-secondary btn-sm" onclick={() => oeffneSendenModal(vorschauRechnung)}>E-Mail</button>
              <button class="btn-danger btn-sm" onclick={() => oeffneStornoModal(vorschauRechnung)}>Stornieren</button>
            {/if}
          </div>
        </div>
      </div>
    {/if}
  </div>

  <!-- Footer / Pagination -->
  {#if gefiltert.length > 0}
    <div class="footer-bar">
      <div class="footer-summen">
        <span>Netto gesamt: <strong>{fmt(summeNetto)} €</strong></span>
        {#if summeStorno > 0}
          <span class="storno-summe">Stornos: <strong>{fmt(summeStorno)} €</strong></span>
        {/if}
        <span class="footer-count">{gefiltert.length} Einträge</span>
      </div>
      <div class="pagination">
        <button class="page-btn" disabled={aktuelleSeite <= 1} onclick={() => aktuelleSeite--}>‹</button>
        {#each Array.from({ length: gesamtSeiten }, (_, i) => i + 1) as seite (seite)}
          {#if seite === 1 || seite === gesamtSeiten || Math.abs(seite - aktuelleSeite) <= 2}
            <button
              class="page-btn {aktuelleSeite === seite ? 'active' : ''}"
              onclick={() => aktuelleSeite = seite}
            >{seite}</button>
          {/if}
        {/each}
        <button class="page-btn" disabled={aktuelleSeite >= gesamtSeiten} onclick={() => aktuelleSeite++}>›</button>
      </div>
    </div>
  {/if}
</div>

<!-- MODAL: RECHNUNG ERSTELLEN -->
{#if erstellenModal}
  <div class="modal-overlay" onclick={() => erstellenModal = false}>
    <div class="modal-box" onclick={(e) => e.stopPropagation()}>
      <div class="modal-hdr">
        <span class="modal-titel">Neue Rechnung erstellen</span>
        <button class="icon-btn" onclick={() => erstellenModal = false}>✕</button>
      </div>
      <div class="modal-body">
        <div class="form-grid">
          <div class="form-group">
            <label>Käufer *</label>
            <input bind:value={neueRechnung.kaeufer} placeholder="Max Mustermann" />
          </div>
          <div class="form-group">
            <label>E-Mail</label>
            <input bind:value={neueRechnung.buyeremail} type="email" placeholder="max@example.com" />
          </div>
          <div class="form-group">
            <label>Straße</label>
            <input bind:value={neueRechnung.buyerstrasse} placeholder="Musterstr. 1" />
          </div>
          <div class="form-group form-2col">
            <div class="form-group">
              <label>PLZ</label>
              <input bind:value={neueRechnung.buyerplz} placeholder="12345" />
            </div>
            <div class="form-group">
              <label>Ort</label>
              <input bind:value={neueRechnung.buyerort} placeholder="Berlin" />
            </div>
          </div>
          <div class="form-group form-2col">
            <div class="form-group">
              <label>Land</label>
              <input bind:value={neueRechnung.buyerland} placeholder="DE" />
            </div>
            <div class="form-group">
              <label>Bestell-Nr.</label>
              <input bind:value={neueRechnung.orderid} placeholder="eBay Order ID" />
            </div>
          </div>
          <div class="form-group">
            <label>Artikel *</label>
            <input bind:value={neueRechnung.artikelname} placeholder="Artikelbezeichnung" />
          </div>
          <div class="form-group">
            <label>eBay Artikel-ID</label>
            <input bind:value={neueRechnung.ebayartikelid} placeholder="123456789" />
          </div>
          <div class="form-group form-2col">
            <div class="form-group">
              <label>Menge *</label>
              <input bind:value={neueRechnung.menge} type="number" min="1" />
            </div>
            <div class="form-group">
              <label>Einzelpreis netto (€) *</label>
              <input bind:value={neueRechnung.einzelpreis} type="number" step="0.01" placeholder="19.99" />
            </div>
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary" onclick={() => erstellenModal = false}>Abbrechen</button>
        <button class="btn-primary" onclick={erstelleManuell} disabled={erstellenLaeuft}>
          {erstellenLaeuft ? 'Erstelle…' : 'Rechnung erstellen'}
        </button>
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
        <button class="icon-btn" onclick={() => sendenModal = false}>✕</button>
      </div>
      <div class="modal-body">
        <p class="modal-info">
          Rechnung <strong>{sendenRechnung?.rechnungsnummer}</strong> als PDF versenden an:
        </p>
        <div class="form-group">
          <label>E-Mail-Adresse</label>
          <input bind:value={sendenEmail} type="email" placeholder="empfaenger@example.com" />
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary" onclick={() => sendenModal = false}>Abbrechen</button>
        <button class="btn-primary" onclick={sendeRechnung} disabled={sendenLaeuft}>
          {sendenLaeuft ? 'Sende…' : 'Senden'}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- MODAL: STORNO -->
{#if stornoModal}
  <div class="modal-overlay" onclick={() => stornoModal = false}>
    <div class="modal-box modal-klein" onclick={(e) => e.stopPropagation()}>
      <div class="modal-hdr">
        <span class="modal-titel">Stornorechnung erstellen</span>
        <button class="icon-btn" onclick={() => stornoModal = false}>✕</button>
      </div>
      <div class="modal-body">
        <p class="modal-info">
          Soll für <strong>{stornoRechnung?.rechnungsnummer}</strong> eine Stornorechnung erstellt werden?
          Diese Aktion kann nicht rückgängig gemacht werden.
        </p>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary" onclick={() => stornoModal = false}>Abbrechen</button>
        <button class="btn-danger" onclick={erstelleStorno} disabled={stornoLaeuft}>
          {stornoLaeuft ? 'Erstelle…' : 'Storno erstellen'}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .page-container { padding: 28px 32px; display: flex; flex-direction: column; gap: 20px; }

  .page-hdr { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
  .page-title { font-size: 1.35rem; font-weight: 700; color: var(--text); }
  .page-sub   { font-size: 0.82rem; color: var(--text2); margin-top: 2px; }
  .hdr-actions { display: flex; gap: 10px; align-items: center; }

  .btn-primary {
    background: var(--primary); color: #fff; border: none;
    padding: 8px 18px; border-radius: 8px; font-size: 0.84rem; font-weight: 500;
    cursor: pointer; transition: background 0.15s;
  }
  .btn-primary:hover:not(:disabled) { background: var(--primary-dark); }
  .btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

  .btn-secondary {
    background: transparent; color: var(--text); border: 1px solid var(--border);
    padding: 8px 16px; border-radius: 8px; font-size: 0.84rem;
    cursor: pointer; transition: background 0.15s;
  }
  .btn-secondary:hover { background: var(--surface2); }

  .btn-ghost {
    background: transparent; color: var(--text2); border: none;
    padding: 7px 12px; border-radius: 8px; font-size: 0.83rem;
    cursor: pointer; display: flex; align-items: center; gap: 6px;
    transition: color 0.15s, background 0.15s;
  }
  .btn-ghost:hover:not(:disabled) { color: var(--text); background: var(--surface2); }
  .btn-ghost:disabled { opacity: 0.5; cursor: not-allowed; }

  .btn-danger {
    background: #ef4444; color: #fff; border: none;
    padding: 8px 16px; border-radius: 8px; font-size: 0.84rem;
    cursor: pointer; transition: background 0.15s;
  }
  .btn-danger:hover:not(:disabled) { background: #dc2626; }
  .btn-danger:disabled { opacity: 0.6; cursor: not-allowed; }

  .btn-sm { padding: 6px 12px; font-size: 0.8rem; }

  .icon-btn {
    background: transparent; border: none; color: var(--text2);
    padding: 5px; border-radius: 6px; cursor: pointer;
    display: inline-flex; align-items: center;
    transition: color 0.15s, background 0.15s;
  }
  .icon-btn:hover { color: var(--primary); background: var(--surface2); }
  .icon-btn-danger:hover { color: #ef4444; background: #fef2f2; }

  .kpi-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; }
  .kpi-card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 16px 18px; }
  .kpi-card-wide { grid-column: span 2; }
  .kpi-label { font-size: 0.75rem; color: var(--text2); margin-bottom: 6px; }
  .kpi-value { font-size: 1.4rem; font-weight: 700; color: var(--text); font-variant-numeric: tabular-nums; }
  .kpi-blue   { color: var(--primary); }
  .kpi-yellow { color: #d97706; }
  .kpi-red    { color: #ef4444; }

  .toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
  .filter-tabs { display: flex; gap: 4px; flex-wrap: wrap; }
  .filter-tab {
    background: transparent; border: none; padding: 7px 12px; border-radius: 7px;
    font-size: 0.82rem; color: var(--text2); cursor: pointer;
    display: flex; align-items: center; gap: 5px;
    transition: background 0.15s, color 0.15s;
  }
  .filter-tab:hover { background: var(--surface2); color: var(--text); }
  .filter-tab.active { background: var(--surface2); color: var(--text); font-weight: 600; }
  .tab-count {
    background: var(--border); color: var(--text2);
    font-size: 0.72rem; padding: 1px 6px; border-radius: 99px;
  }
  .filter-tab.active .tab-count { background: var(--primary-light); color: var(--primary); }

  .toolbar-right { display: flex; gap: 10px; align-items: center; }
  .suche-input {
    background: var(--surface); border: 1px solid var(--border); color: var(--text);
    padding: 7px 12px; border-radius: 8px; font-size: 0.83rem; width: 220px;
    outline: none; transition: border-color 0.15s;
  }
  .suche-input:focus { border-color: var(--primary); }
  .suche-input::placeholder { color: var(--text3); }
  .select-klein {
    background: var(--surface); border: 1px solid var(--border); color: var(--text);
    padding: 7px 10px; border-radius: 8px; font-size: 0.83rem; cursor: pointer; outline: none;
  }

  .bulk-bar {
    display: flex; align-items: center; gap: 12px;
    background: var(--primary-light); border: 1px solid var(--border);
    border-radius: 8px; padding: 8px 14px; font-size: 0.83rem; color: var(--primary);
  }

  .haupt-bereich { display: flex; gap: 16px; align-items: flex-start; }
  .tabellen-wrapper {
    flex: 1; background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; overflow: hidden; min-width: 0;
  }

  .tabelle { width: 100%; border-collapse: collapse; font-size: 0.83rem; }
  .tabelle thead tr { background: var(--surface2); }
  .tabelle th {
    padding: 10px 12px; text-align: left; font-weight: 600;
    font-size: 0.75rem; color: var(--text2); border-bottom: 1px solid var(--border); white-space: nowrap;
  }
  .th-check { width: 36px; }
  .th-right { text-align: right; }
  .th-actions { width: 120px; }

  .tbl-row { border-bottom: 1px solid var(--border); cursor: pointer; transition: background 0.12s; }
  .tbl-row:last-child { border-bottom: none; }
  .tbl-row:hover { background: var(--surface2); }
  .tbl-row.aktiv { background: var(--primary-light); }

  .tabelle td { padding: 10px 12px; color: var(--text); vertical-align: middle; }
  .td-check { width: 36px; }
  .td-nr { font-weight: 600; white-space: nowrap; color: var(--primary); }
  .td-datum { white-space: nowrap; color: var(--text2); font-size: 0.8rem; }
  .td-kaeufer { max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .td-artikel { max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text2); }
  .td-right { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
  .td-bold { font-weight: 600; }
  .td-actions { white-space: nowrap; }

  .badge { display: inline-block; padding: 2px 8px; border-radius: 99px; font-size: 0.73rem; font-weight: 500; white-space: nowrap; }
  .badge-erstellt  { background: #fffbeb; color: #d97706; }
  .badge-gesendet  { background: #f0fdf4; color: #16a34a; }
  .badge-storniert { background: #fef2f2; color: #dc2626; }
  :global([data-theme="dark"]) .badge-erstellt  { background: rgba(217,119,6,.15);  color: #fbbf24; }
  :global([data-theme="dark"]) .badge-gesendet  { background: rgba(22,163,74,.15);  color: #4ade80; }
  :global([data-theme="dark"]) .badge-storniert { background: rgba(220,38,38,.15);  color: #f87171; }

  .status-info { padding: 40px; text-align: center; color: var(--text2); font-size: 0.85rem; }
  .status-fehler { color: #ef4444; }

  .leer-state {
    padding: 60px 40px; display: flex; flex-direction: column;
    align-items: center; gap: 12px; color: var(--text3); text-align: center;
  }
  .leer-state p { color: var(--text2); font-size: 0.9rem; }

  .vorschau-panel {
    width: 300px; flex-shrink: 0; background: var(--surface);
    border: 1px solid var(--border); border-radius: 10px;
    overflow: hidden; display: flex; flex-direction: column;
  }
  .vorschau-hdr {
    display: flex; align-items: center; justify-content: space-between;
    padding: 14px 16px; border-bottom: 1px solid var(--border); background: var(--surface2);
  }
  .vorschau-titel { font-size: 0.88rem; font-weight: 600; color: var(--text); }
  .vorschau-body  { padding: 16px; display: flex; flex-direction: column; gap: 14px; overflow-y: auto; }
  .vorschau-row   { display: flex; align-items: center; justify-content: space-between; }
  .vorschau-datum { font-size: 0.78rem; color: var(--text2); }

  .vs-label { font-size: 0.72rem; font-weight: 600; color: var(--text3); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 5px; }
  .vs-value { font-size: 0.85rem; color: var(--text); font-weight: 500; }
  .vs-sub   { font-size: 0.78rem; color: var(--text2); margin-top: 2px; }

  .pos-zeile { display: flex; justify-content: space-between; align-items: baseline; padding: 4px 0; border-bottom: 1px solid var(--border); }
  .pos-zeile:last-child { border-bottom: none; }
  .pos-name   { font-size: 0.82rem; color: var(--text); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .pos-detail { font-size: 0.78rem; color: var(--text2); white-space: nowrap; margin-left: 8px; }

  .betraege-box { background: var(--surface2); border-radius: 8px; padding: 12px; display: flex; flex-direction: column; gap: 6px; }
  .betrag-zeile { display: flex; justify-content: space-between; font-size: 0.82rem; color: var(--text2); }
  .betrag-brutto { color: var(--text); font-weight: 700; font-size: 0.9rem; border-top: 1px solid var(--border); padding-top: 6px; margin-top: 2px; }

  .vorschau-aktionen { display: flex; gap: 8px; flex-wrap: wrap; }

  .footer-bar { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; padding-top: 4px; }
  .footer-summen { display: flex; gap: 20px; align-items: center; font-size: 0.82rem; color: var(--text2); flex-wrap: wrap; }
  .footer-summen strong { color: var(--text); }
  .storno-summe { color: #ef4444; }
  .footer-count { color: var(--text3); }

  .pagination { display: flex; gap: 4px; align-items: center; }
  .page-btn {
    min-width: 32px; height: 32px; background: var(--surface); border: 1px solid var(--border);
    color: var(--text2); border-radius: 7px; font-size: 0.82rem; cursor: pointer;
    display: flex; align-items: center; justify-content: center; transition: all 0.12s;
  }
  .page-btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary); }
  .page-btn.active { background: var(--primary); border-color: var(--primary); color: #fff; font-weight: 600; }
  .page-btn:disabled { opacity: 0.4; cursor: not-allowed; }

  .modal-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.45);
    z-index: 1000; display: flex; align-items: center; justify-content: center; padding: 20px;
  }
  .modal-box {
    background: var(--surface); border: 1px solid var(--border); border-radius: 14px;
    width: 100%; max-width: 560px; max-height: 90vh;
    display: flex; flex-direction: column;
    box-shadow: 0 20px 60px rgba(0,0,0,0.2);
  }
  .modal-klein { max-width: 400px; }
  .modal-hdr { display: flex; align-items: center; justify-content: space-between; padding: 18px 20px 14px; border-bottom: 1px solid var(--border); }
  .modal-titel { font-size: 1rem; font-weight: 600; color: var(--text); }
  .modal-body { padding: 20px; overflow-y: auto; }
  .modal-footer { display: flex; gap: 10px; justify-content: flex-end; padding: 14px 20px 18px; border-top: 1px solid var(--border); }
  .modal-info { font-size: 0.85rem; color: var(--text2); margin-bottom: 14px; line-height: 1.5; }
  .modal-info strong { color: var(--text); }

  .form-grid { display: flex; flex-direction: column; gap: 14px; }
  .form-group { display: flex; flex-direction: column; gap: 5px; }
  .form-2col  { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .form-group label { font-size: 0.78rem; color: var(--text2); font-weight: 500; }
  .form-group input {
    background: var(--surface); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: 8px; font-size: 0.85rem;
    outline: none; transition: border-color 0.15s;
  }
  .form-group input:focus { border-color: var(--primary); }
  .form-group input::placeholder { color: var(--text3); }
</style>
