<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { currentUser, showToast } from '$lib/stores.js';
  import { apiCall } from '$lib/api.js';

  // --- Tabs für spätere Shop-Anbindungen ---
  const tabs = [
    { key: 'csv',         label: '📄 CSV-Import',    verfuegbar: true },
    { key: 'woocommerce', label: '🛒 WooCommerce',    verfuegbar: false },
    { key: 'shopify',     label: '🛍️ Shopify',       verfuegbar: false },
    { key: 'shopware',    label: '⚙️ Shopware',       verfuegbar: false },
    { key: 'etsy',        label: '🧶 Etsy',           verfuegbar: false },
    { key: 'amazon',      label: '📦 Amazon',         verfuegbar: false },
  ];
  let aktiverTab = $state('csv');

  // --- CSV State ---
  let datei = $state(null);
  let csvZeilen = $state([]);      // rohe geparste Zeilen
  let spalten = $state([]);        // CSV-Spaltenköpfe
  let mapping = $state({});        // { zielfeld: csvSpalte }
  let vorschau = $state([]);       // normalisierte Orders für Anzeige
  let schritt = $state(1);         // 1=Upload, 2=Mapping, 3=Vorschau, 4=Ergebnis
  let dragOver = $state(false);
  let fehler = $state('');
  let laeuft = $state(false);
  let ergebnis = $state(null);     // { erstellt, fehler, details }
  let shopName = $state('CSV-Import');

  // Zielfelder die gemappt werden müssen/können
  const zielfelder = [
    { key: 'external_order_id', label: 'Bestell-ID',    pflicht: false },
    { key: 'datum',             label: 'Datum',          pflicht: false },
    { key: 'vorname',           label: 'Vorname',        pflicht: false },
    { key: 'nachname',          label: 'Nachname',       pflicht: true  },
    { key: 'strasse',           label: 'Straße',         pflicht: false },
    { key: 'plz',               label: 'PLZ',            pflicht: false },
    { key: 'ort',               label: 'Ort',            pflicht: false },
    { key: 'land',              label: 'Land',           pflicht: false },
    { key: 'email',             label: 'E-Mail',         pflicht: false },
    { key: 'artikel',           label: 'Artikel',        pflicht: true  },
    { key: 'menge',             label: 'Menge',          pflicht: false },
    { key: 'einzelpreis',       label: 'Einzelpreis',    pflicht: true  },
    { key: 'mwst_satz',         label: 'MwSt. %',        pflicht: false },
  ];

  function parseCsv(text) {
    const zeilen = text.trim().split('\n');
    if (zeilen.length < 2) return { spalten: [], daten: [] };

    // Trennzeichen erkennen: Semikolon oder Komma
    const erstZeile = zeilen[0];
    const trenner = (erstZeile.split(';').length > erstZeile.split(',').length) ? ';' : ',';

    const kopf = erstZeile.split(trenner).map(s => s.trim().replace(/^"|"$/g, ''));
    const daten = zeilen.slice(1).filter(z => z.trim()).map(zeile => {
      const werte = zeile.split(trenner).map(s => s.trim().replace(/^"|"$/g, ''));
      const obj = {};
      kopf.forEach((k, i) => obj[k] = werte[i] || '');
      return obj;
    });
    return { spalten: kopf, daten };
  }

  function autoMapping(spaltenListe) {
    // Versucht automatisch Spalten zuzuordnen anhand von Schlüsselwörtern
    const m = {};
    const regeln = {
      external_order_id: ['bestell', 'order', 'bestellnr', 'auftrag'],
      datum:             ['datum', 'date', 'bestelldatum'],
      vorname:           ['vorname', 'firstname', 'first_name'],
      nachname:          ['nachname', 'name', 'lastname', 'last_name', 'kunde'],
      strasse:           ['strasse', 'straße', 'adresse', 'street', 'address'],
      plz:               ['plz', 'postleitzahl', 'zip', 'postal'],
      ort:               ['ort', 'stadt', 'city'],
      land:              ['land', 'country'],
      email:             ['email', 'e-mail', 'mail'],
      artikel:           ['artikel', 'produkt', 'product', 'bezeichnung', 'item', 'name'],
      menge:             ['menge', 'qty', 'quantity', 'anzahl'],
      einzelpreis:       ['preis', 'price', 'einzelpreis', 'betrag', 'amount', 'gesamt'],
      mwst_satz:         ['mwst', 'ust', 'steuer', 'tax', 'vat'],
    };
    zielfelder.forEach(zf => {
      const treffer = spaltenListe.find(sp => {
        const spLow = sp.toLowerCase();
        return (regeln[zf.key] || []).some(r => spLow.includes(r));
      });
      if (treffer) m[zf.key] = treffer;
    });
    return m;
  }

  function verarbeiteMapping() {
    fehler = '';
    // Pflichtfelder prüfen
    const fehlend = zielfelder.filter(zf => zf.pflicht && !mapping[zf.key]);
    if (fehlend.length > 0) {
      fehler = 'Pflichtfelder nicht gemappt: ' + fehlend.map(f => f.label).join(', ');
      return;
    }
    // Normalisieren
    vorschau = csvZeilen.map((zeile, idx) => {
      const get = (key) => mapping[key] ? (zeile[mapping[key]] || '') : '';
      return {
        external_order_id: get('external_order_id') || `CSV-${idx + 1}`,
        datum: get('datum') || new Date().toISOString().split('T')[0],
        kaeufer: {
          vorname:  get('vorname'),
          nachname: get('nachname'),
          strasse:  get('strasse'),
          plz:      get('plz'),
          ort:      get('ort'),
          land:     get('land') || 'DE',
          email:    get('email'),
        },
        positionen: [{
          artikel:      get('artikel'),
          menge:        parseInt(get('menge')) || 1,
          einzelpreis:  parseFloat(get('einzelpreis')?.replace(',', '.')) || 0,
          mwst_satz:    parseInt(get('mwst_satz')) || 19,
        }]
      };
    });
    schritt = 3;
  }

  async function importStarten() {
    if (vorschau.length === 0) return;
    laeuft = true;
    fehler = '';
    let erstellt = 0, fehlerAnz = 0, details = [];
    for (let i = 0; i < vorschau.length; i++) {
      const order = vorschau[i];
      try {
        const res = await apiCall('shop-import-rechnung', {
          user_id: $currentUser.id,
          source: 'csv',
          shop_name: shopName,
          orders: [order]
        });
        erstellt++;
        details.push({ order_id: order.external_order_id, success: true, re_nr: res?.re_nr || '' });
      } catch(e) {
        fehlerAnz++;
        details.push({ order_id: order.external_order_id, success: false, fehler: e.message });
      }
      // Kurze Pause zwischen Requests
      await new Promise(res => setTimeout(res, 200));
    }
    ergebnis = { erstellt, fehler: fehlerAnz, details };
    schritt = 4;
    laeuft = false;
    showToast(`✅ ${erstellt} Rechnung(en) erstellt${fehlerAnz > 0 ? `, ${fehlerAnz} Fehler` : ''}`);
  }

  function dateiLaden(file) {
    if (!file || !file.name.endsWith('.csv')) {
      fehler = 'Bitte eine CSV-Datei auswählen.';
      return;
    }
    datei = file;
    fehler = '';
    const reader = new FileReader();
    reader.onload = (e) => {
      const { spalten: sp, daten } = parseCsv(e.target.result);
      if (sp.length === 0 || daten.length === 0) {
        fehler = 'CSV konnte nicht gelesen werden. Prüfe Format und Trennzeichen (Komma oder Semikolon).';
        return;
      }
      spalten = sp;
      csvZeilen = daten;
      mapping = autoMapping(sp);
      schritt = 2;
    };
    reader.readAsText(file, 'UTF-8');
  }

  function onDrop(e) {
    e.preventDefault();
    dragOver = false;
    const file = e.dataTransfer?.files?.[0];
    if (file) dateiLaden(file);
  }

  function reset() {
    datei = null; csvZeilen = []; spalten = []; mapping = {};
    vorschau = []; schritt = 1; fehler = ''; ergebnis = null;
  }

  function fmt(n) {
    return Number(n || 0).toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
</script>

<div class="page-container">

  <!-- Header -->
  <div class="page-hdr">
    <div>
      <div class="page-title">📥 Bestellungen importieren</div>
      <div class="page-sub">Rechnungen aus anderen Shops erstellen</div>
    </div>
    <div class="hdr-actions">
      <a href="/rechnungen" class="btn-ghost">← Zurück</a>
    </div>
  </div>

  <!-- Shop-Tabs -->
  <div class="shop-tabs">
    {#each tabs as tab (tab.key)}
      <button
        class="shop-tab {aktiverTab === tab.key ? 'active' : ''} {!tab.verfuegbar ? 'bald' : ''}"
        onclick={() => tab.verfuegbar && (aktiverTab = tab.key)}
        disabled={!tab.verfuegbar}
      >
        {tab.label}
        {#if !tab.verfuegbar}<span class="bald-badge">Bald</span>{/if}
      </button>
    {/each}
  </div>

  <!-- CSV Import -->
  {#if aktiverTab === 'csv'}

    <!-- Schritte-Anzeige -->
    <div class="schritte">
      {#each ['Datei hochladen', 'Spalten zuordnen', 'Vorschau & Import', 'Ergebnis'] as s, i}
        <div class="schritt-item {schritt === i+1 ? 'aktiv' : ''} {schritt > i+1 ? 'fertig' : ''}">
          <div class="schritt-kreis">{schritt > i+1 ? '✓' : i+1}</div>
          <div class="schritt-label">{s}</div>
        </div>
        {#if i < 3}<div class="schritt-linie {schritt > i+1 ? 'fertig' : ''}"></div>{/if}
      {/each}
    </div>

    <div class="import-body">

      <!-- Schritt 1: Upload -->
      {#if schritt === 1}
        <div class="card">
          <div class="card-titel">CSV-Datei auswählen</div>
          <p class="card-hinweis">Unterstützt werden CSV-Dateien mit Komma- oder Semikolon-Trennzeichen (UTF-8). Die erste Zeile muss die Spaltenüberschriften enthalten.</p>

          <!-- Shop-Name -->
          <div class="form-group" style="margin-bottom:16px">
            <label>Shop-Name (für Rechnungsfilter)</label>
            <input type="text" bind:value={shopName} placeholder="z.B. Mein WooCommerce Shop" />
          </div>

          <!-- Drag & Drop Zone -->
          <div
            class="drop-zone {dragOver ? 'drag-over' : ''}"
            ondragover={(e) => { e.preventDefault(); dragOver = true; }}
            ondragleave={() => dragOver = false}
            ondrop={onDrop}
            onclick={() => document.getElementById('csv-input').click()}
          >
            <div class="drop-icon">📄</div>
            <div class="drop-text">CSV-Datei hier ablegen oder klicken zum Auswählen</div>
            <div class="drop-hint">Komma- oder Semikolon-getrennt, UTF-8</div>
            <input id="csv-input" type="file" accept=".csv" style="display:none"
              onchange={(e) => dateiLaden(e.target.files?.[0])} />
          </div>

          {#if fehler}<div class="hinweis hinweis-rot">⚠️ {fehler}</div>{/if}

          <!-- Beispiel-Format -->
          <details class="beispiel-details">
            <summary>📋 Beispiel CSV-Format anzeigen</summary>
            <pre class="beispiel-code">bestell_id;datum;nachname;vorname;strasse;plz;ort;land;email;artikel;menge;einzelpreis;mwst_satz
WOO-1001;2026-04-10;Mustermann;Max;Musterstr. 1;12345;Berlin;DE;max@example.com;Produkt A;2;29.99;19
WOO-1002;2026-04-11;Schmidt;Anna;Hauptstr. 5;80331;München;DE;anna@example.com;Produkt B;1;49.90;19</pre>
          </details>
        </div>

      <!-- Schritt 2: Spalten-Mapping -->
      {:else if schritt === 2}
        <div class="card">
          <div class="card-titel">Spalten zuordnen</div>
          <p class="card-hinweis">
            Datei: <strong>{datei?.name}</strong> — <strong>{csvZeilen.length}</strong> Bestellungen erkannt.
            Wähle für jedes Feld die passende CSV-Spalte. Felder mit * sind Pflichtfelder.
          </p>

          <div class="mapping-grid">
            {#each zielfelder as zf}
              <div class="mapping-row">
                <div class="mapping-label">{zf.label}{zf.pflicht ? ' *' : ''}</div>
                <select class="mapping-select" bind:value={mapping[zf.key]}>
                  <option value="">— nicht zuordnen —</option>
                  {#each spalten as sp}
                    <option value={sp}>{sp}</option>
                  {/each}
                </select>
                {#if mapping[zf.key]}
                  <div class="mapping-preview">{csvZeilen[0]?.[mapping[zf.key]] || '—'}</div>
                {:else}
                  <div class="mapping-preview leer">kein Wert</div>
                {/if}
              </div>
            {/each}
          </div>

          {#if fehler}<div class="hinweis hinweis-rot" style="margin-top:12px">⚠️ {fehler}</div>{/if}

          <div class="card-footer">
            <button class="btn-ghost" onclick={reset}>← Zurück</button>
            <button class="btn-primary" onclick={verarbeiteMapping}>Vorschau anzeigen →</button>
          </div>
        </div>

      <!-- Schritt 3: Vorschau -->
      {:else if schritt === 3}
        <div class="card">
          <div class="card-titel">Vorschau — {vorschau.length} Bestellungen</div>
          <p class="card-hinweis">Prüfe die erkannten Daten. Starte dann den Import um Rechnungen zu erstellen.</p>

          <div class="vorschau-tabelle-wrap">
            <table class="vorschau-tabelle">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Bestell-ID</th>
                  <th>Datum</th>
                  <th>Käufer</th>
                  <th>Artikel</th>
                  <th>Menge</th>
                  <th>Einzelpreis</th>
                  <th>MwSt.</th>
                  <th>Brutto</th>
                </tr>
              </thead>
              <tbody>
                {#each vorschau as order, i}
                  {@const pos = order.positionen[0]}
                  {@const brutto = pos.einzelpreis * pos.menge * (1 + pos.mwst_satz / 100)}
                  <tr>
                    <td class="td-nr">{i + 1}</td>
                    <td class="td-mono">{order.external_order_id}</td>
                    <td>{order.datum}</td>
                    <td>{order.kaeufer.vorname} {order.kaeufer.nachname}</td>
                    <td>{pos.artikel}</td>
                    <td style="text-align:center">{pos.menge}</td>
                    <td style="text-align:right">{fmt(pos.einzelpreis)} €</td>
                    <td style="text-align:center">{pos.mwst_satz} %</td>
                    <td style="text-align:right;font-weight:600">{fmt(brutto)} €</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>

          {#if fehler}<div class="hinweis hinweis-rot">⚠️ {fehler}</div>{/if}

          <div class="card-footer">
            <button class="btn-ghost" onclick={() => schritt = 2}>← Zurück</button>
            <button class="btn-primary" onclick={importStarten} disabled={laeuft}>
              {#if laeuft}⏳ Importiere...{:else}✅ {vorschau.length} Rechnungen erstellen{/if}
            </button>
          </div>
        </div>

      <!-- Schritt 4: Ergebnis -->
      {:else if schritt === 4}
        <div class="card">
          <div class="card-titel">Import abgeschlossen</div>

          <div class="ergebnis-box {ergebnis?.fehler > 0 ? 'ergebnis-warn' : 'ergebnis-ok'}">
            <div class="ergebnis-icon">{ergebnis?.fehler > 0 ? '⚠️' : '✅'}</div>
            <div>
              <div class="ergebnis-titel">{ergebnis?.erstellt} Rechnung(en) erfolgreich erstellt</div>
              {#if ergebnis?.fehler > 0}
                <div class="ergebnis-sub">{ergebnis.fehler} Fehler beim Import</div>
              {/if}
            </div>
          </div>

          <!-- Detail-Liste -->
          <div class="detail-liste">
            {#each ergebnis?.details || [] as d}
              <div class="detail-item {d.success ? 'detail-ok' : 'detail-err'}">
                <span class="detail-status">{d.success ? '✅' : '❌'}</span>
                <span class="detail-id">{d.order_id}</span>
                <span class="detail-info">{d.success ? d.re_nr : d.fehler}</span>
              </div>
            {/each}
          </div>

          <div class="card-footer">
            <button class="btn-ghost" onclick={reset}>Weiteren Import starten</button>
            <a href="/rechnungen" class="btn-primary">→ Zu den Rechnungen</a>
          </div>
        </div>
      {/if}

    </div>
  {/if}

</div>

<style>
  .page-container { padding: 24px; }
  .page-hdr { display:flex; align-items:flex-start; justify-content:space-between; margin-bottom:24px; flex-wrap:wrap; gap:12px; }
  .page-title { font-size:1.3rem; font-weight:700; color:var(--text); }
  .page-sub { font-size:0.85rem; color:var(--text2); margin-top:2px; }
  .hdr-actions { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }

  /* Shop Tabs */
  .shop-tabs { display:flex; gap:4px; margin-bottom:24px; flex-wrap:wrap; border-bottom:1px solid var(--border); padding-bottom:0; }
  .shop-tab { background:none; border:none; border-bottom:2px solid transparent; padding:10px 18px; font-size:0.85rem; font-weight:600; color:var(--text2); cursor:pointer; transition:all 0.15s; white-space:nowrap; position:relative; }
  .shop-tab:hover:not(:disabled) { color:var(--text); }
  .shop-tab.active { color:var(--primary); border-bottom-color:var(--primary); }
  .shop-tab.bald { opacity:0.5; cursor:not-allowed; }
  .bald-badge { font-size:0.6rem; background:var(--surface2); color:var(--text3); border-radius:4px; padding:1px 5px; margin-left:5px; font-weight:600; vertical-align:middle; }

  /* Schritte */
  .schritte { display:flex; align-items:center; margin-bottom:28px; flex-wrap:wrap; gap:0; }
  .schritt-item { display:flex; align-items:center; gap:8px; }
  .schritt-kreis { width:28px; height:28px; border-radius:50%; border:2px solid var(--border); background:var(--surface); color:var(--text3); font-size:0.78rem; font-weight:700; display:flex; align-items:center; justify-content:center; flex-shrink:0; transition:all 0.2s; }
  .schritt-item.aktiv .schritt-kreis { border-color:var(--primary); background:var(--primary); color:#fff; }
  .schritt-item.fertig .schritt-kreis { border-color:#16a34a; background:#16a34a; color:#fff; }
  .schritt-label { font-size:0.8rem; color:var(--text3); white-space:nowrap; }
  .schritt-item.aktiv .schritt-label { color:var(--primary); font-weight:600; }
  .schritt-item.fertig .schritt-label { color:#16a34a; }
  .schritt-linie { flex:1; height:2px; background:var(--border); min-width:20px; margin:0 8px; transition:background 0.2s; }
  .schritt-linie.fertig { background:#16a34a; }

  /* Card */
  .import-body { max-width:860px; }
  .card { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:24px; margin-bottom:16px; }
  .card-titel { font-size:1rem; font-weight:700; color:var(--text); margin-bottom:8px; }
  .card-hinweis { font-size:0.84rem; color:var(--text2); margin-bottom:18px; line-height:1.5; }
  .card-footer { display:flex; justify-content:flex-end; gap:10px; margin-top:20px; padding-top:16px; border-top:1px solid var(--border); }

  /* Drop Zone */
  .drop-zone { border:2px dashed var(--border); border-radius:12px; padding:48px 24px; text-align:center; cursor:pointer; transition:all 0.2s; margin-bottom:16px; }
  .drop-zone:hover, .drop-zone.drag-over { border-color:var(--primary); background:color-mix(in srgb, var(--primary) 5%, transparent); }
  .drop-icon { font-size:2.5rem; margin-bottom:12px; }
  .drop-text { font-size:0.95rem; font-weight:600; color:var(--text); margin-bottom:6px; }
  .drop-hint { font-size:0.8rem; color:var(--text3); }

  /* Beispiel */
  .beispiel-details { margin-top:8px; }
  .beispiel-details summary { font-size:0.82rem; color:var(--primary); cursor:pointer; padding:4px 0; }
  .beispiel-code { background:var(--surface2); border:1px solid var(--border); border-radius:8px; padding:12px; font-size:0.75rem; color:var(--text2); overflow-x:auto; margin-top:8px; white-space:pre; }

  /* Mapping */
  .mapping-grid { display:flex; flex-direction:column; gap:8px; }
  .mapping-row { display:grid; grid-template-columns:160px 1fr 160px; gap:10px; align-items:center; padding:8px 0; border-bottom:1px solid var(--border); }
  .mapping-row:last-child { border-bottom:none; }
  .mapping-label { font-size:0.82rem; font-weight:600; color:var(--text); }
  .mapping-select { background:var(--surface); border:1px solid var(--border); color:var(--text); padding:6px 10px; border-radius:7px; font-size:0.82rem; outline:none; }
  .mapping-select:focus { border-color:var(--primary); }
  .mapping-preview { font-size:0.78rem; color:var(--text3); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; background:var(--surface2); padding:4px 8px; border-radius:5px; }
  .mapping-preview.leer { color:var(--text3); opacity:0.5; font-style:italic; }

  /* Vorschau-Tabelle */
  .vorschau-tabelle-wrap { overflow-x:auto; border:1px solid var(--border); border-radius:8px; margin-bottom:4px; max-height:400px; overflow-y:auto; }
  .vorschau-tabelle { width:100%; border-collapse:collapse; font-size:0.8rem; }
  .vorschau-tabelle th { padding:8px 10px; text-align:left; font-size:0.72rem; color:var(--text3); font-weight:600; border-bottom:2px solid var(--border); background:var(--surface2); position:sticky; top:0; }
  .vorschau-tabelle td { padding:7px 10px; border-bottom:1px solid var(--border); color:var(--text); }
  .vorschau-tabelle tr:last-child td { border-bottom:none; }
  .vorschau-tabelle tr:hover td { background:var(--surface2); }
  .td-nr { color:var(--text3); font-size:0.75rem; min-width:24px; }
  .td-mono { font-family:monospace; font-size:0.78rem; color:var(--primary); }

  /* Ergebnis */
  .ergebnis-box { display:flex; align-items:center; gap:16px; padding:16px 20px; border-radius:10px; margin-bottom:16px; }
  .ergebnis-ok { background:#f0fdf4; border:1px solid #bbf7d0; }
  .ergebnis-warn { background:#fffbeb; border:1px solid #fde68a; }
  .ergebnis-icon { font-size:1.8rem; }
  .ergebnis-titel { font-size:0.95rem; font-weight:700; color:var(--text); }
  .ergebnis-sub { font-size:0.82rem; color:#d97706; margin-top:2px; }
  .detail-liste { display:flex; flex-direction:column; gap:4px; max-height:300px; overflow-y:auto; border:1px solid var(--border); border-radius:8px; }
  .detail-item { display:flex; align-items:center; gap:10px; padding:8px 12px; font-size:0.8rem; border-bottom:1px solid var(--border); }
  .detail-item:last-child { border-bottom:none; }
  .detail-ok { background:#f0fdf4; }
  .detail-err { background:#fef2f2; }
  .detail-status { flex-shrink:0; }
  .detail-id { font-family:monospace; font-size:0.75rem; color:var(--primary); min-width:120px; }
  .detail-info { color:var(--text2); font-size:0.78rem; }

  /* Shared */
  .hinweis { border-radius:8px; padding:10px 14px; font-size:0.82rem; margin-bottom:8px; line-height:1.5; display:flex; align-items:center; gap:10px; }
  .hinweis-rot { background:#fef2f2; border:1px solid #fecaca; color:#dc2626; }
  .form-group { display:flex; flex-direction:column; gap:5px; }
  .form-group label { font-size:0.78rem; color:var(--text2); font-weight:500; }
  .form-group input { background:var(--surface); border:1px solid var(--border); color:var(--text); padding:8px 12px; border-radius:8px; font-size:0.85rem; outline:none; }
  .form-group input:focus { border-color:var(--primary); }

  /* Buttons (geerbt aus app.css, nur Ergänzung) */
  .btn-primary { background:var(--primary); color:#fff; border:none; padding:8px 18px; border-radius:8px; font-size:0.85rem; font-weight:600; cursor:pointer; text-decoration:none; display:inline-flex; align-items:center; gap:6px; }
  .btn-primary:disabled { opacity:0.6; cursor:not-allowed; }
  .btn-ghost { background:var(--surface2); color:var(--text); border:1px solid var(--border); padding:8px 18px; border-radius:8px; font-size:0.85rem; font-weight:500; cursor:pointer; text-decoration:none; display:inline-flex; align-items:center; }
  .btn-ghost:hover { border-color:var(--primary); color:var(--primary); }
</style>
