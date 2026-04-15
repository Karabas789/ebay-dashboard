<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { currentUser, showToast } from '$lib/stores.js';
  import { apiCall } from '$lib/api.js';

  const tabs = [
    { key: 'csv',         label: '📄 CSV-Import',    verfuegbar: true },
    { key: 'woocommerce', label: '🛒 WooCommerce',    verfuegbar: false },
    { key: 'shopify',     label: '🛍️ Shopify',       verfuegbar: false },
    { key: 'shopware',    label: '⚙️ Shopware',       verfuegbar: false },
    { key: 'etsy',        label: '🧶 Etsy',           verfuegbar: false },
    { key: 'amazon',      label: '📦 Amazon',         verfuegbar: false },
  ];
  let aktiverTab = $state('csv');

  let datei = $state(null);
  let csvZeilen = $state([]);
  let spalten = $state([]);
  let mapping = $state({});
  let fallback = $state({});
  let vorschau = $state([]);
  let schritt = $state(1);
  let dragOver = $state(false);
  let fehler = $state('');
  let laeuft = $state(false);
  let ergebnis = $state(null);
  let shopName = $state('CSV-Import');
  let fortschritt = $state(0);

  const zielfelder = [
    { key: 'external_order_id', label: 'Bestell-ID',         pflicht: false, gruppe: 'bestellung', fallbackTyp: 'text' },
    { key: 'datum',             label: 'Datum',               pflicht: false, gruppe: 'bestellung', fallbackTyp: 'date' },
    { key: 'zahlungsart',       label: 'Zahlungsart',         pflicht: false, gruppe: 'bestellung', fallbackTyp: 'text' },
    { key: 'zahlungsstatus',    label: 'Zahlungsstatus',      pflicht: false, gruppe: 'bestellung', fallbackTyp: 'select', optionen: ['bezahlt','ausstehend','erstattet'] },
    { key: 'waehrung',          label: 'Währung',             pflicht: false, gruppe: 'bestellung', fallbackTyp: 'select', optionen: ['EUR','USD','GBP','CHF'] },
    { key: 'vorname',           label: 'Vorname',             pflicht: false, gruppe: 'kaeufer',    fallbackTyp: 'text' },
    { key: 'nachname',          label: 'Nachname / Name',     pflicht: true,  gruppe: 'kaeufer',    fallbackTyp: 'text' },
    { key: 'strasse',           label: 'Straße',              pflicht: false, gruppe: 'kaeufer',    fallbackTyp: 'text' },
    { key: 'plz',               label: 'PLZ',                 pflicht: false, gruppe: 'kaeufer',    fallbackTyp: 'text' },
    { key: 'ort',               label: 'Ort',                 pflicht: false, gruppe: 'kaeufer',    fallbackTyp: 'text' },
    { key: 'land',              label: 'Land',                pflicht: false, gruppe: 'kaeufer',    fallbackTyp: 'text' },
    { key: 'email',             label: 'E-Mail',              pflicht: false, gruppe: 'kaeufer',    fallbackTyp: 'text' },
    { key: 'artikel',           label: 'Artikel',             pflicht: true,  gruppe: 'artikel',    fallbackTyp: 'text' },
    { key: 'menge',             label: 'Menge',               pflicht: false, gruppe: 'artikel',    fallbackTyp: 'number' },
    { key: 'einzelpreis',       label: 'Einzelpreis (Brutto)',pflicht: false, gruppe: 'artikel',    fallbackTyp: 'number' },
    { key: 'gesamtpreis',       label: 'Gesamtpreis (Brutto)',pflicht: false, gruppe: 'artikel',    fallbackTyp: 'number' },
    { key: 'mwst_satz',         label: 'MwSt. Artikel %',    pflicht: false, gruppe: 'artikel',    fallbackTyp: 'number' },
    { key: 'rabatt',            label: 'Rabatt €',            pflicht: false, gruppe: 'artikel',    fallbackTyp: 'number' },
    { key: 'versandkosten',     label: 'Versandkosten €',     pflicht: false, gruppe: 'versand',    fallbackTyp: 'number' },
    { key: 'mwst_versand',      label: 'MwSt. Versand %',    pflicht: false, gruppe: 'versand',    fallbackTyp: 'number' },
  ];

  const gruppen = [
    { key: 'bestellung', label: '📋 Bestellung' },
    { key: 'kaeufer',    label: '👤 Käufer' },
    { key: 'artikel',    label: '📦 Artikel' },
    { key: 'versand',    label: '🚚 Versand' },
  ];

  function parseCsv(text) {
    // BOM entfernen
    const clean = text.replace(/^\uFEFF/, '');
    const zeilen = clean.trim().split(/\r?\n/);
    if (zeilen.length < 2) return { spalten: [], daten: [] };
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
    const m = {};
    const regeln = {
      external_order_id: ['bestellnummer', 'bestell', 'order', 'bestellnr', 'auftrag'],
      datum:             ['erstellt', 'datum', 'date', 'bestelldatum', 'kaufdatum', 'created'],
      zahlungsart:       ['zahlungsmethode', 'zahlungsart', 'zahlung', 'payment', 'paymethod'],
      zahlungsstatus:    ['zahlungsstatus', 'payment_status'],
      waehrung:          ['waehrung', 'währung', 'currency'],
      vorname:           ['vorname', 'firstname', 'first_name'],
      nachname:          ['rechnungsempfänger', 'nachname', 'name', 'lastname', 'last_name', 'kunde', 'billing_name'],
      strasse:           ['straße 1', 'strasse', 'straße', 'adresse', 'street', 'address'],
      plz:               ['postleitzahl', 'plz', 'zip', 'postal'],
      ort:               ['stadt', 'ort', 'city'],
      land:              ['land', 'country'],
      email:             ['e-mail', 'email', 'mail'],
      artikel:           ['produktnamen', 'artikel', 'produkt', 'product', 'bezeichnung', 'item', 'title'],
      menge:             ['menge der produkte', 'menge', 'qty', 'quantity', 'anzahl'],
      einzelpreis:       ['produktpreis', 'einzelpreis', 'unit_price', 'unitprice'],
      gesamtpreis:       ['gesamt', 'gesamtpreis', 'total', 'betrag', 'amount'],
      mwst_satz:         ['mwst', 'ust', 'steuer', 'tax', 'vat', 'steuern'],
      rabatt:            ['rabattbetrag', 'rabatt', 'discount', 'gutschein'],
      versandkosten:     ['versand', 'shipping', 'versandkosten', 'porto'],
      mwst_versand:      ['versand_mwst', 'shipping_tax'],
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

  function initFallbacks() {
    const fb = {};
    zielfelder.forEach(zf => {
      if (zf.key === 'land') fb[zf.key] = 'DE';
      else if (zf.key === 'mwst_satz') fb[zf.key] = '19';
      else if (zf.key === 'mwst_versand') fb[zf.key] = '19';
      else if (zf.key === 'menge') fb[zf.key] = '1';
      else if (zf.key === 'waehrung') fb[zf.key] = 'EUR';
      else if (zf.key === 'zahlungsstatus') fb[zf.key] = 'bezahlt';
      else fb[zf.key] = '';
    });
    return fb;
  }

  function getWert(zeile, key) {
    const csvSpalte = mapping[key];
    const csvWert = csvSpalte ? (zeile[csvSpalte] || '') : '';
    return csvWert || fallback[key] || '';
  }

  // ── Namensaufteilung: "Vorname Nachname" → { vorname, nachname }
  function splitName(fullName) {
    const parts = (fullName || '').trim().split(/\s+/);
    if (parts.length <= 1) return { vorname: '', nachname: parts[0] || '' };
    return { vorname: parts.slice(0, -1).join(' '), nachname: parts[parts.length - 1] };
  }

  // ── KERN: Gruppierung nach Bestellnummer ──
  function verarbeiteMapping() {
    fehler = '';
    const fehlend = zielfelder.filter(zf => zf.pflicht && !mapping[zf.key] && !fallback[zf.key]);
    if (fehlend.length > 0) {
      fehler = 'Pflichtfelder fehlen (CSV-Spalte oder Standardwert): ' + fehlend.map(f => f.label).join(', ');
      return;
    }

    // 1. Alle CSV-Zeilen zu Positionen machen
    const allePositionen = csvZeilen.map((zeile, idx) => {
      const einzelpreis = parseFloat(getWert(zeile, 'einzelpreis')?.replace(',', '.')) || 0;
      const gesamtpreis = parseFloat(getWert(zeile, 'gesamtpreis')?.replace(',', '.')) || 0;
      const menge = parseInt(getWert(zeile, 'menge')) || 1;
      let ep = einzelpreis;
      if (!ep && gesamtpreis) ep = gesamtpreis / menge;

      // Name aufteilen: wenn kein Vorname-Mapping, aber Nachname enthält "Vorname Nachname"
      let vorname = getWert(zeile, 'vorname');
      let nachname = getWert(zeile, 'nachname');
      if (!mapping['vorname'] && nachname && nachname.includes(' ')) {
        const split = splitName(nachname);
        vorname = split.vorname;
        nachname = split.nachname;
      }

      return {
        orderId: getWert(zeile, 'external_order_id') || `CSV-${idx + 1}`,
        datum: getWert(zeile, 'datum') || new Date().toISOString().split('T')[0],
        zahlungsart: getWert(zeile, 'zahlungsart'),
        zahlungsstatus: getWert(zeile, 'zahlungsstatus'),
        waehrung: getWert(zeile, 'waehrung') || 'EUR',
        vorname,
        nachname,
        strasse: getWert(zeile, 'strasse'),
        plz: getWert(zeile, 'plz'),
        ort: getWert(zeile, 'ort'),
        land: getWert(zeile, 'land') || 'DE',
        email: getWert(zeile, 'email'),
        bezeichnung: getWert(zeile, 'artikel'),
        menge,
        einzelpreis: ep,
        mwst_satz: parseInt(getWert(zeile, 'mwst_satz')) || 19,
        rabatt_pct: 0,
        versandkosten: parseFloat(getWert(zeile, 'versandkosten')?.replace(',', '.')) || 0,
        mwst_versand: parseInt(getWert(zeile, 'mwst_versand')) || 19,
      };
    });

    // 2. Nach Bestell-ID gruppieren
    const grouped = new Map();
    for (const pos of allePositionen) {
      const key = pos.orderId;
      if (!grouped.has(key)) {
        grouped.set(key, {
          external_order_id: pos.orderId,
          datum: pos.datum,
          zahlungsart: pos.zahlungsart,
          zahlungsstatus: pos.zahlungsstatus,
          waehrung: pos.waehrung,
          kaeufer: {
            vorname: pos.vorname,
            nachname: pos.nachname,
            strasse: pos.strasse,
            plz: pos.plz,
            ort: pos.ort,
            land: pos.land,
            email: pos.email,
          },
          positionen: [],
          versandkosten: pos.versandkosten,
          mwst_versand: pos.mwst_versand,
        });
      }
      const order = grouped.get(key);
      // Käuferdaten von erster Zeile mit Daten übernehmen (Folgezeilen sind oft leer)
      if (pos.vorname && !order.kaeufer.vorname) order.kaeufer.vorname = pos.vorname;
      if (pos.nachname && !order.kaeufer.nachname) order.kaeufer.nachname = pos.nachname;
      if (pos.strasse && !order.kaeufer.strasse) order.kaeufer.strasse = pos.strasse;
      if (pos.plz && !order.kaeufer.plz) order.kaeufer.plz = pos.plz;
      if (pos.ort && !order.kaeufer.ort) order.kaeufer.ort = pos.ort;
      if (pos.email && !order.kaeufer.email) order.kaeufer.email = pos.email;
      if (pos.zahlungsart && !order.zahlungsart) order.zahlungsart = pos.zahlungsart;
      if (pos.versandkosten && !order.versandkosten) order.versandkosten = pos.versandkosten;

      order.positionen.push({
        bezeichnung: pos.bezeichnung,
        menge: pos.menge,
        einzelpreis: pos.einzelpreis,
        mwst_satz: pos.mwst_satz,
        rabatt_pct: pos.rabatt_pct,
      });
    }

    vorschau = Array.from(grouped.values());
    schritt = 3;
  }

  async function importStarten() {
    if (vorschau.length === 0) return;
    laeuft = true;
    fehler = '';
    fortschritt = 0;
    let erstellt = 0, fehlerAnz = 0, details = [];
    for (let i = 0; i < vorschau.length; i++) {
      const order = vorschau[i];
      fortschritt = Math.round(((i + 1) / vorschau.length) * 100);
      try {
        const res = await apiCall('/shop-import-rechnung', {
          user_id: $currentUser.id,
          source: 'csv',
          shop_name: shopName,
          orders: [order]
        });
        if (res?.success) {
          erstellt++;
          details.push({ order_id: order.external_order_id, success: true, re_nr: res?.re_nr || '', positionen: order.positionen.length });
        } else {
          fehlerAnz++;
          details.push({ order_id: order.external_order_id, success: false, fehler: res?.error || res?.message || 'Unbekannter Fehler' });
        }
      } catch(e) {
        fehlerAnz++;
        details.push({ order_id: order.external_order_id, success: false, fehler: e.message });
      }
      await new Promise(res => setTimeout(res, 300));
    }
    ergebnis = { erstellt, fehler: fehlerAnz, details };
    schritt = 4;
    laeuft = false;
    fortschritt = 100;
    showToast(`✅ ${erstellt} Rechnung(en) erstellt${fehlerAnz > 0 ? `, ${fehlerAnz} Fehler` : ''}`);
  }

  function dateiLaden(file) {
    if (!file || !file.name.endsWith('.csv')) { fehler = 'Bitte eine CSV-Datei auswählen.'; return; }
    datei = file;
    fehler = '';
    const reader = new FileReader();
    reader.onload = (e) => {
      const { spalten: sp, daten } = parseCsv(e.target.result);
      if (sp.length === 0 || daten.length === 0) { fehler = 'CSV konnte nicht gelesen werden.'; return; }
      spalten = sp;
      csvZeilen = daten;
      mapping = autoMapping(sp);
      fallback = initFallbacks();
      schritt = 2;
    };
    reader.readAsText(file, 'UTF-8');
  }

  function onDrop(e) { e.preventDefault(); dragOver = false; const file = e.dataTransfer?.files?.[0]; if (file) dateiLaden(file); }
  function reset() { datei = null; csvZeilen = []; spalten = []; mapping = {}; fallback = {}; vorschau = []; schritt = 1; fehler = ''; ergebnis = null; fortschritt = 0; }
  function fmt(n) { return Number(n || 0).toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

  // Gesamtsumme einer Bestellung berechnen
  function orderSumme(order) {
    const artikelSumme = order.positionen.reduce((s, p) => s + (p.einzelpreis * p.menge), 0);
    return artikelSumme + (order.versandkosten || 0);
  }

  // Anzahl Gesamt-Positionen über alle Bestellungen
  let totalPositionen = $derived(vorschau.reduce((s, o) => s + o.positionen.length, 0));
</script>

<!-- ═══════════════════════════════════════════════════════ PAGE -->
<div class="page-container">

  <div class="page-hdr">
    <div>
      <div class="page-title">📥 Bestellungen importieren</div>
      <div class="page-sub">Rechnungen aus anderen Shops erstellen</div>
    </div>
    <div class="hdr-actions">
      <a href="/rechnungen" class="btn-ghost">← Zurück</a>
    </div>
  </div>

  <div class="shop-tabs">
    {#each tabs as tab (tab.key)}
      <button class="shop-tab {aktiverTab === tab.key ? 'active' : ''} {!tab.verfuegbar ? 'bald' : ''}"
        onclick={() => tab.verfuegbar && (aktiverTab = tab.key)} disabled={!tab.verfuegbar}>
        {tab.label}
        {#if !tab.verfuegbar}<span class="bald-badge">Bald</span>{/if}
      </button>
    {/each}
  </div>

  {#if aktiverTab === 'csv'}

    <div class="schritte">
      {#each ['Datei hochladen', 'Spalten zuordnen', 'Vorschau & Import', 'Ergebnis'] as s, i}
        <div class="schritt-item {schritt === i+1 ? 'aktiv' : ''} {schritt > i+1 ? 'fertig' : ''}">
          <div class="schritt-kreis">{schritt > i+1 ? '✓' : i+1}</div>
          <div class="schritt-label">{s}</div>
        </div>
        {#if i < 3}<div class="schritt-linie {schritt > i+1 ? 'fertig' : ''}"></div>{/if}
      {/each}
    </div>

    <!-- ═══════════════════ Schritt 1: Upload ═══════════════════ -->
    {#if schritt === 1}
      <div class="card">
        <div class="card-titel">CSV-Datei auswählen</div>
        <p class="card-hinweis">Unterstützt werden CSV-Dateien mit Komma- oder Semikolon-Trennzeichen (UTF-8). Die erste Zeile muss die Spaltenüberschriften enthalten. Bestellungen mit gleicher Bestell-ID werden automatisch zu Multi-Artikel-Rechnungen gruppiert.</p>
        <div class="form-group" style="margin-bottom:16px;max-width:400px">
          <label>Shop-Name (für Rechnungsfilter)</label>
          <input type="text" bind:value={shopName} placeholder="z.B. Mein WooCommerce Shop" />
        </div>
        <div class="drop-zone {dragOver ? 'drag-over' : ''}"
          ondragover={(e) => { e.preventDefault(); dragOver = true; }}
          ondragleave={() => dragOver = false}
          ondrop={onDrop}
          onclick={() => document.getElementById('csv-input').click()}>
          <div class="drop-icon">📄</div>
          <div class="drop-text">CSV-Datei hier ablegen oder klicken zum Auswählen</div>
          <div class="drop-hint">Komma- oder Semikolon-getrennt, UTF-8</div>
          <input id="csv-input" type="file" accept=".csv" style="display:none" onchange={(e) => dateiLaden(e.target.files?.[0])} />
        </div>
        {#if fehler}<div class="hinweis hinweis-rot">⚠️ {fehler}</div>{/if}
        <details class="beispiel-details">
          <summary>📋 Beispiel CSV-Format anzeigen</summary>
          <pre class="beispiel-code">bestell_id;datum;nachname;vorname;strasse;plz;ort;land;email;artikel;menge;einzelpreis;mwst_satz;versandkosten;zahlungsart
WOO-1001;2026-04-10;Mustermann;Max;Musterstr. 1;12345;Berlin;DE;max@example.com;Produkt A;2;29.99;19;4.99;PayPal
WOO-1001;;;;;;;;;Produkt B;1;15.00;19;;
WOO-1002;2026-04-11;Schmidt;Anna;Hauptstr. 5;80331;München;DE;anna@example.com;Produkt C;1;49.90;19;0;Vorkasse</pre>
          <p style="font-size:0.75rem;color:var(--text3);margin-top:6px;">Tipp: Zeilen mit gleicher Bestell-ID werden automatisch als Multi-Artikel-Bestellung zusammengefasst.</p>
        </details>
      </div>

    <!-- ═══════════════════ Schritt 2: Mapping ═══════════════════ -->
    {:else if schritt === 2}
      <div class="card">
        <div class="card-titel">Spalten zuordnen</div>
        <p class="card-hinweis">
          Datei: <strong>{datei?.name}</strong> — <strong>{csvZeilen.length}</strong> CSV-Zeilen erkannt.
          Wähle für jedes Feld die passende CSV-Spalte. Felder mit * sind Pflicht. Wenn eine Spalte fehlt, trage einen Standardwert ein.
        </p>

        {#each gruppen as gruppe}
          <div class="gruppe-titel">{gruppe.label}</div>
          <div class="mapping-grid">
            {#each zielfelder.filter(zf => zf.gruppe === gruppe.key) as zf}
              <div class="mapping-row">
                <div class="mapping-label">{zf.label}{zf.pflicht ? ' *' : ''}</div>
                <select class="mapping-select" bind:value={mapping[zf.key]}>
                  <option value="">— nicht zuordnen —</option>
                  {#each spalten as sp}
                    <option value={sp}>{sp}</option>
                  {/each}
                </select>
                <div class="mapping-preview {mapping[zf.key] ? '' : 'leer'}">
                  {mapping[zf.key] ? (csvZeilen[0]?.[mapping[zf.key]] || '—') : 'kein Wert'}
                </div>
                <div class="fallback-wrap">
                  {#if zf.fallbackTyp === 'select'}
                    <select class="fallback-input" bind:value={fallback[zf.key]} disabled={!!mapping[zf.key]}>
                      {#each (zf.optionen || []) as opt}
                        <option value={opt}>{opt}</option>
                      {/each}
                    </select>
                  {:else}
                    <input class="fallback-input" type={zf.fallbackTyp === 'number' ? 'text' : zf.fallbackTyp}
                      bind:value={fallback[zf.key]} placeholder="Standardwert" disabled={!!mapping[zf.key]} />
                  {/if}
                </div>
              </div>
            {/each}
          </div>
        {/each}

        {#if fehler}<div class="hinweis hinweis-rot" style="margin-top:12px">⚠️ {fehler}</div>{/if}
        <div class="card-footer">
          <button class="btn-ghost" onclick={reset}>← Zurück</button>
          <button class="btn-primary" onclick={verarbeiteMapping}>Vorschau anzeigen →</button>
        </div>
      </div>

    <!-- ═══════════════════ Schritt 3: Vorschau ═══════════════════ -->
    {:else if schritt === 3}
      <div class="card">
        <div class="card-titel">Vorschau — {vorschau.length} Bestellungen ({totalPositionen} Positionen)</div>
        <p class="card-hinweis">Prüfe die erkannten Daten bevor du den Import startest. Bestellungen mit mehreren Artikeln werden als eine Rechnung mit Multi-Positionen erstellt.</p>

        <div class="vorschau-tabelle-wrap">
          <table class="vorschau-tabelle">
            <thead>
              <tr>
                <th>#</th><th>Bestell-ID</th><th>Datum</th><th>Käufer</th>
                <th>Artikel</th><th style="text-align:center">Pos.</th>
                <th style="text-align:right">Versand</th>
                <th style="text-align:right">Gesamt</th><th>Zahlung</th>
              </tr>
            </thead>
            <tbody>
              {#each vorschau as order, i}
                {@const summe = orderSumme(order)}
                {@const isMulti = order.positionen.length > 1}
                <tr class:multi-row={isMulti}>
                  <td class="td-nr">{i + 1}</td>
                  <td class="td-mono">{order.external_order_id}</td>
                  <td>{order.datum}</td>
                  <td>
                    <div>{order.kaeufer.vorname} {order.kaeufer.nachname}</div>
                    {#if order.kaeufer.ort}<div class="td-sub">{order.kaeufer.plz} {order.kaeufer.ort}</div>{/if}
                  </td>
                  <td>
                    {#each order.positionen as pos, pi}
                      <div class="pos-line" class:pos-line-border={pi > 0}>
                        <span class="pos-name">{pos.bezeichnung}</span>
                        <span class="pos-detail">{pos.menge}× {fmt(pos.einzelpreis)} € ({pos.mwst_satz}%)</span>
                      </div>
                    {/each}
                  </td>
                  <td style="text-align:center">
                    {#if isMulti}
                      <span class="pos-badge">{order.positionen.length}</span>
                    {:else}
                      1
                    {/if}
                  </td>
                  <td style="text-align:right">{order.versandkosten ? fmt(order.versandkosten) + ' €' : '—'}</td>
                  <td style="text-align:right;font-weight:600">{fmt(summe)} €</td>
                  <td style="font-size:0.75rem;color:var(--text3)">{order.zahlungsart || '—'}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>

        {#if laeuft}
          <div class="progress-bar-wrap">
            <div class="progress-bar" style="width:{fortschritt}%"></div>
          </div>
          <div class="progress-text">{fortschritt}% — Erstelle Rechnungen...</div>
        {/if}

        {#if fehler}<div class="hinweis hinweis-rot">⚠️ {fehler}</div>{/if}
        <div class="card-footer">
          <button class="btn-ghost" onclick={() => schritt = 2} disabled={laeuft}>← Zurück</button>
          <button class="btn-primary" onclick={importStarten} disabled={laeuft}>
            {#if laeuft}⏳ Importiere ({fortschritt}%)...{:else}✅ {vorschau.length} Rechnungen erstellen{/if}
          </button>
        </div>
      </div>

    <!-- ═══════════════════ Schritt 4: Ergebnis ═══════════════════ -->
    {:else if schritt === 4}
      <div class="card">
        <div class="card-titel">Import abgeschlossen</div>
        <div class="ergebnis-box {ergebnis?.fehler > 0 ? 'ergebnis-warn' : 'ergebnis-ok'}">
          <div class="ergebnis-icon">{ergebnis?.fehler > 0 ? '⚠️' : '✅'}</div>
          <div>
            <div class="ergebnis-titel">{ergebnis?.erstellt} Rechnung(en) erfolgreich erstellt</div>
            {#if ergebnis?.fehler > 0}<div class="ergebnis-sub">{ergebnis.fehler} Fehler beim Import</div>{/if}
          </div>
        </div>
        <div class="detail-liste">
          {#each ergebnis?.details || [] as d}
            <div class="detail-item {d.success ? 'detail-ok' : 'detail-err'}">
              <span>{d.success ? '✅' : '❌'}</span>
              <span class="detail-id">{d.order_id}</span>
              <span class="detail-info">
                {#if d.success}
                  {d.re_nr}{d.positionen > 1 ? ` (${d.positionen} Positionen)` : ''}
                {:else}
                  {d.fehler}
                {/if}
              </span>
            </div>
          {/each}
        </div>
        <div class="card-footer">
          <button class="btn-ghost" onclick={reset}>Weiteren Import starten</button>
          <a href="/rechnungen" class="btn-primary">→ Zu den Rechnungen</a>
        </div>
      </div>
    {/if}

  {/if}

</div>

<style>
  .page-container { padding: 24px; }
  .page-hdr { display:flex; align-items:flex-start; justify-content:space-between; margin-bottom:24px; flex-wrap:wrap; gap:12px; }
  .page-title { font-size:1.3rem; font-weight:700; color:var(--text); }
  .page-sub { font-size:0.85rem; color:var(--text2); margin-top:2px; }
  .hdr-actions { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }

  .shop-tabs { display:flex; gap:4px; margin-bottom:24px; flex-wrap:wrap; border-bottom:1px solid var(--border); }
  .shop-tab { background:none; border:none; border-bottom:2px solid transparent; padding:10px 18px; font-size:0.85rem; font-weight:600; color:var(--text2); cursor:pointer; transition:all 0.15s; white-space:nowrap; position:relative; }
  .shop-tab:hover:not(:disabled) { color:var(--text); }
  .shop-tab.active { color:var(--primary); border-bottom-color:var(--primary); }
  .shop-tab.bald { opacity:0.5; cursor:not-allowed; }
  .bald-badge { font-size:0.6rem; background:var(--surface2); color:var(--text3); border-radius:4px; padding:1px 5px; margin-left:5px; font-weight:600; vertical-align:middle; }

  .schritte { display:flex; align-items:center; margin-bottom:28px; flex-wrap:wrap; }
  .schritt-item { display:flex; align-items:center; gap:8px; }
  .schritt-kreis { width:28px; height:28px; border-radius:50%; border:2px solid var(--border); background:var(--surface); color:var(--text3); font-size:0.78rem; font-weight:700; display:flex; align-items:center; justify-content:center; flex-shrink:0; transition:all 0.2s; }
  .schritt-item.aktiv .schritt-kreis { border-color:var(--primary); background:var(--primary); color:#fff; }
  .schritt-item.fertig .schritt-kreis { border-color:#16a34a; background:#16a34a; color:#fff; }
  .schritt-label { font-size:0.8rem; color:var(--text3); white-space:nowrap; }
  .schritt-item.aktiv .schritt-label { color:var(--primary); font-weight:600; }
  .schritt-item.fertig .schritt-label { color:#16a34a; }
  .schritt-linie { flex:1; height:2px; background:var(--border); min-width:20px; margin:0 8px; transition:background 0.2s; }
  .schritt-linie.fertig { background:#16a34a; }

  .card { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:24px; margin-bottom:16px; }
  .card-titel { font-size:1rem; font-weight:700; color:var(--text); margin-bottom:8px; }
  .card-hinweis { font-size:0.84rem; color:var(--text2); margin-bottom:18px; line-height:1.5; }
  .card-footer { display:flex; justify-content:flex-end; gap:10px; margin-top:20px; padding-top:16px; border-top:1px solid var(--border); }

  .drop-zone { border:2px dashed var(--border); border-radius:12px; padding:48px 24px; text-align:center; cursor:pointer; transition:all 0.2s; margin-bottom:16px; }
  .drop-zone:hover, .drop-zone.drag-over { border-color:var(--primary); background:color-mix(in srgb, var(--primary) 5%, transparent); }
  .drop-icon { font-size:2.5rem; margin-bottom:12px; }
  .drop-text { font-size:0.95rem; font-weight:600; color:var(--text); margin-bottom:6px; }
  .drop-hint { font-size:0.8rem; color:var(--text3); }

  .beispiel-details { margin-top:8px; }
  .beispiel-details summary { font-size:0.82rem; color:var(--primary); cursor:pointer; padding:4px 0; }
  .beispiel-code { background:var(--surface2); border:1px solid var(--border); border-radius:8px; padding:12px; font-size:0.75rem; color:var(--text2); overflow-x:auto; margin-top:8px; white-space:pre; }

  .gruppe-titel { font-size:0.75rem; font-weight:700; color:var(--text3); text-transform:uppercase; letter-spacing:0.06em; margin:20px 0 8px; padding-bottom:6px; border-bottom:1px solid var(--border); }
  .mapping-grid { display:flex; flex-direction:column; gap:4px; margin-bottom:8px; }
  .mapping-row { display:grid; grid-template-columns:180px 1fr 140px 160px; gap:8px; align-items:center; padding:6px 0; border-bottom:1px solid var(--border); }
  .mapping-row:last-child { border-bottom:none; }
  .mapping-label { font-size:0.82rem; font-weight:600; color:var(--text); }
  .mapping-select { background:var(--surface); border:1px solid var(--border); color:var(--text); padding:5px 8px; border-radius:7px; font-size:0.8rem; outline:none; }
  .mapping-select:focus { border-color:var(--primary); }
  .mapping-preview { font-size:0.75rem; color:var(--text3); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; background:var(--surface2); padding:4px 8px; border-radius:5px; }
  .mapping-preview.leer { opacity:0.5; font-style:italic; }
  .fallback-input { background:var(--surface2); border:1px solid var(--border); color:var(--text); padding:5px 8px; border-radius:7px; font-size:0.8rem; outline:none; width:100%; }
  .fallback-input:focus { border-color:var(--primary); }
  .fallback-input:disabled { opacity:0.4; cursor:not-allowed; }

  /* Vorschau */
  .vorschau-tabelle-wrap { overflow-x:auto; border:1px solid var(--border); border-radius:8px; margin-bottom:4px; max-height:500px; overflow-y:auto; }
  .vorschau-tabelle { width:100%; border-collapse:collapse; font-size:0.8rem; }
  .vorschau-tabelle th { padding:8px 10px; text-align:left; font-size:0.72rem; color:var(--text3); font-weight:600; border-bottom:2px solid var(--border); background:var(--surface2); position:sticky; top:0; z-index:1; }
  .vorschau-tabelle td { padding:7px 10px; border-bottom:1px solid var(--border); color:var(--text); vertical-align:top; }
  .vorschau-tabelle tr:last-child td { border-bottom:none; }
  .vorschau-tabelle tr:hover td { background:var(--surface2); }
  .vorschau-tabelle tr.multi-row td { background:color-mix(in srgb, var(--primary) 3%, transparent); }
  .td-nr { color:var(--text3); font-size:0.75rem; }
  .td-mono { font-family:monospace; font-size:0.78rem; color:var(--primary); font-weight:600; }
  .td-sub { font-size:0.7rem; color:var(--text3); margin-top:2px; }

  .pos-line { padding:2px 0; }
  .pos-line-border { border-top:1px dashed var(--border); margin-top:3px; padding-top:3px; }
  .pos-name { font-weight:600; font-size:0.8rem; }
  .pos-detail { display:block; font-size:0.7rem; color:var(--text3); }
  .pos-badge { display:inline-flex; align-items:center; justify-content:center; background:var(--primary); color:#fff; border-radius:10px; min-width:22px; height:20px; font-size:0.7rem; font-weight:700; padding:0 6px; }

  /* Progress */
  .progress-bar-wrap { height:6px; background:var(--surface2); border-radius:3px; margin-top:16px; overflow:hidden; }
  .progress-bar { height:100%; background:var(--primary); border-radius:3px; transition:width 0.3s ease; }
  .progress-text { font-size:0.78rem; color:var(--text2); text-align:center; margin-top:6px; }

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
  .detail-id { font-family:monospace; font-size:0.75rem; color:var(--primary); min-width:120px; }
  .detail-info { color:var(--text2); font-size:0.78rem; }

  .hinweis { border-radius:8px; padding:10px 14px; font-size:0.82rem; margin-bottom:8px; line-height:1.5; display:flex; align-items:center; gap:10px; }
  .hinweis-rot { background:#fef2f2; border:1px solid #fecaca; color:#dc2626; }
  .form-group { display:flex; flex-direction:column; gap:5px; }
  .form-group label { font-size:0.78rem; color:var(--text2); font-weight:500; }
  .form-group input { background:var(--surface); border:1px solid var(--border); color:var(--text); padding:8px 12px; border-radius:8px; font-size:0.85rem; outline:none; }
  .form-group input:focus { border-color:var(--primary); }

  .btn-primary { background:var(--primary); color:#fff; border:none; padding:8px 18px; border-radius:8px; font-size:0.85rem; font-weight:600; cursor:pointer; text-decoration:none; display:inline-flex; align-items:center; gap:6px; }
  .btn-primary:disabled { opacity:0.6; cursor:not-allowed; }
  .btn-ghost { background:var(--surface2); color:var(--text); border:1px solid var(--border); padding:8px 18px; border-radius:8px; font-size:0.85rem; font-weight:500; cursor:pointer; text-decoration:none; display:inline-flex; align-items:center; }
  .btn-ghost:hover { border-color:var(--primary); color:var(--primary); }

  @media (max-width: 768px) {
    .mapping-row { grid-template-columns:1fr; gap:4px; }
    .vorschau-tabelle { font-size:0.72rem; }
  }
</style>
