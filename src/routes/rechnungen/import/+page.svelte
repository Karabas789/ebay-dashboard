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
  let editOrder = $state(null);
  let editIdx = $state(-1);

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
      external_order_id: ['bestellnummer', 'bestell-id', 'order_id', 'order id', 'bestellnr', 'auftragsnr'],
      datum:             ['erstellt', 'bestelldatum', 'datum', 'date', 'kaufdatum', 'created_at', 'order_date'],
      zahlungsart:       ['zahlungsmethode', 'zahlungsart', 'payment_method', 'paymethod'],
      zahlungsstatus:    ['zahlungsstatus', 'payment_status'],
      waehrung:          ['währung', 'waehrung', 'currency'],
      vorname:           ['vorname', 'firstname', 'first_name', 'billing_first'],
      nachname:          ['rechnungsempfänger', 'nachname', 'lastname', 'last_name', 'billing_name', 'kundenname', 'kunde'],
      strasse:           ['straße 1', 'strasse', 'straße', 'billing_street', 'street', 'adresse', 'address'],
      plz:               ['postleitzahl', 'plz', 'zip', 'postal_code', 'billing_zip'],
      ort:               ['stadt', 'ort', 'city', 'billing_city'],
      land:              ['land', 'country', 'billing_country'],
      email:             ['e-mail', 'email', 'mail', 'billing_email'],
      artikel:           ['produktnamen', 'produktname', 'artikel', 'produkt', 'product', 'bezeichnung', 'item_name', 'title'],
      menge:             ['menge der produkte', 'menge', 'qty', 'quantity', 'anzahl'],
      einzelpreis:       ['produktpreis', 'einzelpreis', 'unit_price', 'unitprice', 'item_price'],
      gesamtpreis:       ['gesamt', 'gesamtpreis', 'total', 'betrag', 'amount'],
      mwst_satz:         ['steuern', 'mwst', 'ust', 'steuer', 'tax', 'vat'],
      rabatt:            ['rabattbetrag', 'rabatt', 'discount'],
      versandkosten:     ['versand', 'shipping', 'versandkosten', 'porto'],
      mwst_versand:      ['versand_mwst', 'shipping_tax'],
    };
    const used = new Set();
    zielfelder.forEach(zf => {
      const patterns = regeln[zf.key] || [];
      let treffer = spaltenListe.find(sp => !used.has(sp) && patterns.some(r => sp.toLowerCase() === r));
      if (!treffer) treffer = spaltenListe.find(sp => !used.has(sp) && patterns.some(r => sp.toLowerCase().includes(r)));
      if (treffer) { m[zf.key] = treffer; used.add(treffer); }
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
  function splitName(fullName) {
    const parts = (fullName || '').trim().split(/\s+/);
    if (parts.length <= 1) return { vorname: '', nachname: parts[0] || '' };
    return { vorname: parts.slice(0, -1).join(' '), nachname: parts[parts.length - 1] };
  }
  function normalizeDatum(raw) {
    if (!raw) return new Date().toISOString().split('T')[0];
    const s = raw.trim();
    const deMatch = s.match(/^(\d{1,2})\.(\d{1,2})\.(\d{4})/);
    if (deMatch) return `${deMatch[3]}-${deMatch[2].padStart(2,'0')}-${deMatch[1].padStart(2,'0')}`;
    const isoMatch = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (isoMatch) return `${isoMatch[1]}-${isoMatch[2]}-${isoMatch[3]}`;
    const usMatch = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
    if (usMatch) return `${usMatch[3]}-${usMatch[1].padStart(2,'0')}-${usMatch[2].padStart(2,'0')}`;
    const d = new Date(s);
    if (!isNaN(d)) return d.toISOString().split('T')[0];
    return new Date().toISOString().split('T')[0];
  }
  function formatDatum(iso) {
    if (!iso) return '—';
    const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (m) return `${m[3]}.${m[2]}.${m[1]}`;
    return iso;
  }

  function verarbeiteMapping() {
    fehler = '';
    const fehlend = zielfelder.filter(zf => zf.pflicht && !mapping[zf.key] && !fallback[zf.key]);
    if (fehlend.length > 0) {
      fehler = 'Pflichtfelder fehlen: ' + fehlend.map(f => f.label).join(', ');
      return;
    }
    const allePositionen = csvZeilen.map((zeile, idx) => {
      const einzelpreis = parseFloat(getWert(zeile, 'einzelpreis')?.replace(',', '.')) || 0;
      const gesamtpreis = parseFloat(getWert(zeile, 'gesamtpreis')?.replace(',', '.')) || 0;
      const menge = parseInt(getWert(zeile, 'menge')) || 1;
      let ep = einzelpreis;
      if (!ep && gesamtpreis) ep = gesamtpreis / menge;
      let vorname = getWert(zeile, 'vorname');
      let nachname = getWert(zeile, 'nachname');
      if (!mapping['vorname'] && nachname && nachname.includes(' ')) {
        const split = splitName(nachname);
        vorname = split.vorname;
        nachname = split.nachname;
      }
      return {
        orderId: getWert(zeile, 'external_order_id') || `CSV-${idx + 1}`,
        datum: normalizeDatum(getWert(zeile, 'datum')),
        zahlungsart: getWert(zeile, 'zahlungsart'),
        zahlungsstatus: getWert(zeile, 'zahlungsstatus'),
        waehrung: getWert(zeile, 'waehrung') || 'EUR',
        vorname, nachname,
        strasse: getWert(zeile, 'strasse'),
        plz: getWert(zeile, 'plz'),
        ort: getWert(zeile, 'ort'),
        land: getWert(zeile, 'land') || 'DE',
        email: getWert(zeile, 'email'),
        bezeichnung: getWert(zeile, 'artikel'),
        menge, einzelpreis: ep,
        mwst_satz: parseInt(getWert(zeile, 'mwst_satz')) || 19,
        rabatt_pct: 0,
        versandkosten: parseFloat(getWert(zeile, 'versandkosten')?.replace(',', '.')) || 0,
      };
    });
    const grouped = new Map();
    for (const pos of allePositionen) {
      const key = pos.orderId;
      if (!grouped.has(key)) {
        grouped.set(key, {
          external_order_id: pos.orderId, datum: pos.datum, zahlungsart: pos.zahlungsart,
          zahlungsstatus: pos.zahlungsstatus, waehrung: pos.waehrung,
          kaeufer: { vorname: pos.vorname, nachname: pos.nachname, strasse: pos.strasse, plz: pos.plz, ort: pos.ort, land: pos.land, email: pos.email },
          positionen: [], versandkosten: pos.versandkosten,
        });
      }
      const order = grouped.get(key);
      if (pos.vorname && !order.kaeufer.vorname) order.kaeufer.vorname = pos.vorname;
      if (pos.nachname && !order.kaeufer.nachname) order.kaeufer.nachname = pos.nachname;
      if (pos.strasse && !order.kaeufer.strasse) order.kaeufer.strasse = pos.strasse;
      if (pos.plz && !order.kaeufer.plz) order.kaeufer.plz = pos.plz;
      if (pos.ort && !order.kaeufer.ort) order.kaeufer.ort = pos.ort;
      if (pos.email && !order.kaeufer.email) order.kaeufer.email = pos.email;
      if (pos.zahlungsart && !order.zahlungsart) order.zahlungsart = pos.zahlungsart;
      if (pos.versandkosten && !order.versandkosten) order.versandkosten = pos.versandkosten;
      order.positionen.push({ bezeichnung: pos.bezeichnung, menge: pos.menge, einzelpreis: pos.einzelpreis, mwst_satz: pos.mwst_satz, rabatt_pct: 0 });
    }
    vorschau = Array.from(grouped.values());
    schritt = 3;
  }

  function openEdit(idx) { editIdx = idx; editOrder = JSON.parse(JSON.stringify(vorschau[idx])); }
  function saveEdit() { if (editIdx >= 0 && editOrder) { vorschau[editIdx] = JSON.parse(JSON.stringify(editOrder)); vorschau = [...vorschau]; } editOrder = null; editIdx = -1; }
  function cancelEdit() { editOrder = null; editIdx = -1; }
  function addPosition() { if (!editOrder) return; editOrder.positionen = [...editOrder.positionen, { bezeichnung: '', menge: 1, einzelpreis: 0, mwst_satz: 19, rabatt_pct: 0 }]; }
  function removePosition(pi) { if (!editOrder || editOrder.positionen.length <= 1) return; editOrder.positionen = editOrder.positionen.filter((_, i) => i !== pi); }
  function removeOrder(idx) { vorschau = vorschau.filter((_, i) => i !== idx); }

  async function importStarten() {
    if (vorschau.length === 0) return;
    laeuft = true; fehler = ''; fortschritt = 0;
    let erstellt = 0, fehlerAnz = 0, details = [];
    for (let i = 0; i < vorschau.length; i++) {
      const order = vorschau[i];
      fortschritt = Math.round(((i + 1) / vorschau.length) * 100);
      try {
        const res = await apiCall('/shop-import-rechnung', { user_id: $currentUser.id, source: 'csv', shop_name: shopName, orders: [order] });
        if (res?.success) { erstellt++; details.push({ order_id: order.external_order_id, success: true, re_nr: res?.re_nr || '', positionen: order.positionen.length }); }
        else { fehlerAnz++; details.push({ order_id: order.external_order_id, success: false, fehler: res?.error || res?.message || 'Fehler' }); }
      } catch(e) { fehlerAnz++; details.push({ order_id: order.external_order_id, success: false, fehler: e.message }); }
      await new Promise(res => setTimeout(res, 300));
    }
    ergebnis = { erstellt, fehler: fehlerAnz, details };
    schritt = 4; laeuft = false; fortschritt = 100;
    showToast(`✅ ${erstellt} Rechnung(en) erstellt${fehlerAnz > 0 ? `, ${fehlerAnz} Fehler` : ''}`);
  }

  function dateiLaden(file) {
    if (!file || !file.name.endsWith('.csv')) { fehler = 'Bitte eine CSV-Datei auswählen.'; return; }
    datei = file; fehler = '';
    const reader = new FileReader();
    reader.onload = (e) => {
      const { spalten: sp, daten } = parseCsv(e.target.result);
      if (sp.length === 0 || daten.length === 0) { fehler = 'CSV konnte nicht gelesen werden.'; return; }
      spalten = sp; csvZeilen = daten; mapping = autoMapping(sp); fallback = initFallbacks(); schritt = 2;
    };
    reader.readAsText(file, 'UTF-8');
  }

  function onDrop(e) { e.preventDefault(); dragOver = false; const file = e.dataTransfer?.files?.[0]; if (file) dateiLaden(file); }
  function reset() { datei = null; csvZeilen = []; spalten = []; mapping = {}; fallback = {}; vorschau = []; schritt = 1; fehler = ''; ergebnis = null; fortschritt = 0; editOrder = null; editIdx = -1; }
  function fmt(n) { return Number(n || 0).toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
  function orderSumme(order) { return order.positionen.reduce((s, p) => s + (p.einzelpreis * p.menge), 0) + (order.versandkosten || 0); }
  let totalPositionen = $derived(vorschau.reduce((s, o) => s + o.positionen.length, 0));
</script>

<div class="page-container">
  <div class="page-hdr">
    <div>
      <div class="page-title">📥 Bestellungen importieren</div>
      <div class="page-sub">Rechnungen aus anderen Shops erstellen</div>
    </div>
    <a href="/rechnungen" class="btn-ghost">← Zurück</a>
  </div>

  <div class="shop-tabs">
    {#each tabs as tab (tab.key)}
      <button class="shop-tab {aktiverTab === tab.key ? 'active' : ''} {!tab.verfuegbar ? 'bald' : ''}" onclick={() => tab.verfuegbar && (aktiverTab = tab.key)} disabled={!tab.verfuegbar}>
        {tab.label}{#if !tab.verfuegbar}<span class="bald-badge">Bald</span>{/if}
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

    {#if schritt === 1}
      <div class="card">
        <div class="card-titel">CSV-Datei auswählen</div>
        <p class="card-hinweis">Bestellungen mit gleicher ID werden automatisch zu Multi-Artikel-Rechnungen gruppiert.</p>
        <div class="form-group" style="margin-bottom:16px;max-width:400px">
          <label>Shop-Name</label>
          <input type="text" bind:value={shopName} placeholder="z.B. Mein WooCommerce Shop" />
        </div>
        <div class="drop-zone {dragOver ? 'drag-over' : ''}" ondragover={(e) => { e.preventDefault(); dragOver = true; }} ondragleave={() => dragOver = false} ondrop={onDrop} onclick={() => document.getElementById('csv-input').click()}>
          <div class="drop-icon">📄</div>
          <div class="drop-text">CSV-Datei hier ablegen oder klicken</div>
          <div class="drop-hint">Komma- oder Semikolon-getrennt, UTF-8</div>
          <input id="csv-input" type="file" accept=".csv" style="display:none" onchange={(e) => dateiLaden(e.target.files?.[0])} />
        </div>
        {#if fehler}<div class="hinweis hinweis-rot">⚠️ {fehler}</div>{/if}
      </div>

    {:else if schritt === 2}
      <div class="card">
        <div class="card-titel">Spalten zuordnen</div>
        <p class="card-hinweis">Datei: <strong>{datei?.name}</strong> — <strong>{csvZeilen.length}</strong> Zeilen. Felder mit * sind Pflicht. Daten können im nächsten Schritt noch korrigiert werden.</p>
        {#each gruppen as gruppe}
          <div class="gruppe-titel">{gruppe.label}</div>
          <div class="mapping-grid">
            {#each zielfelder.filter(zf => zf.gruppe === gruppe.key) as zf}
              <div class="mapping-row">
                <div class="mapping-label">{zf.label}{zf.pflicht ? ' *' : ''}</div>
                <select class="mapping-select" bind:value={mapping[zf.key]}>
                  <option value="">— nicht zuordnen —</option>
                  {#each spalten as sp}<option value={sp}>{sp}</option>{/each}
                </select>
                <div class="mapping-preview {mapping[zf.key] ? '' : 'leer'}">{mapping[zf.key] ? (csvZeilen[0]?.[mapping[zf.key]] || '—') : 'kein Wert'}</div>
                <div class="fallback-wrap">
                  {#if zf.fallbackTyp === 'select'}
                    <select class="fallback-input" bind:value={fallback[zf.key]} disabled={!!mapping[zf.key]}>{#each (zf.optionen || []) as opt}<option value={opt}>{opt}</option>{/each}</select>
                  {:else}
                    <input class="fallback-input" type={zf.fallbackTyp === 'number' ? 'text' : zf.fallbackTyp} bind:value={fallback[zf.key]} placeholder="Standardwert" disabled={!!mapping[zf.key]} />
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

    {:else if schritt === 3}
      <div class="card">
        <div class="card-titel">Vorschau — {vorschau.length} Bestellungen ({totalPositionen} Positionen)</div>
        <p class="card-hinweis">Klicke ✏️ um Daten zu korrigieren oder 🗑️ um eine Bestellung zu entfernen.</p>
        <div class="vorschau-tabelle-wrap">
          <table class="vorschau-tabelle">
            <thead><tr><th>#</th><th>Bestell-ID</th><th>Datum</th><th>Käufer</th><th>Artikel</th><th style="text-align:center">Pos.</th><th style="text-align:right">Versand</th><th style="text-align:right">Gesamt</th><th>Zahlung</th><th style="width:70px"></th></tr></thead>
            <tbody>
              {#each vorschau as order, i}
                {@const summe = orderSumme(order)}
                {@const isMulti = order.positionen.length > 1}
                <tr class:multi-row={isMulti}>
                  <td class="td-nr">{i + 1}</td>
                  <td class="td-mono">{order.external_order_id}</td>
                  <td>{formatDatum(order.datum)}</td>
                  <td>
                    <div class="buyer-cell">{order.kaeufer.vorname} {order.kaeufer.nachname}</div>
                    {#if order.kaeufer.ort}<div class="td-sub">{order.kaeufer.plz} {order.kaeufer.ort}</div>{/if}
                    {#if order.kaeufer.email}<div class="td-sub">{order.kaeufer.email}</div>{/if}
                  </td>
                  <td>
                    {#each order.positionen as pos, pi}
                      <div class="pos-line" class:pos-line-border={pi > 0}>
                        <span class="pos-name">{pos.bezeichnung || '—'}</span>
                        <span class="pos-detail">{pos.menge}× {fmt(pos.einzelpreis)} € ({pos.mwst_satz}%)</span>
                      </div>
                    {/each}
                  </td>
                  <td style="text-align:center">{#if isMulti}<span class="pos-badge">{order.positionen.length}</span>{:else}1{/if}</td>
                  <td style="text-align:right">{order.versandkosten ? fmt(order.versandkosten) + ' €' : '—'}</td>
                  <td style="text-align:right;font-weight:600">{fmt(summe)} €</td>
                  <td class="td-sub">{order.zahlungsart || '—'}</td>
                  <td style="text-align:center">
                    <button class="btn-icon" title="Bearbeiten" onclick={() => openEdit(i)}>✏️</button>
                    <button class="btn-icon btn-icon-danger" title="Entfernen" onclick={() => removeOrder(i)}>🗑️</button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        {#if laeuft}<div class="progress-bar-wrap"><div class="progress-bar" style="width:{fortschritt}%"></div></div><div class="progress-text">{fortschritt}%</div>{/if}
        {#if fehler}<div class="hinweis hinweis-rot">⚠️ {fehler}</div>{/if}
        <div class="card-footer">
          <button class="btn-ghost" onclick={() => schritt = 2} disabled={laeuft}>← Zurück</button>
          <button class="btn-primary" onclick={importStarten} disabled={laeuft || vorschau.length === 0}>
            {#if laeuft}⏳ {fortschritt}%{:else}✅ {vorschau.length} Rechnungen erstellen{/if}
          </button>
        </div>
      </div>

    {:else if schritt === 4}
      <div class="card">
        <div class="card-titel">Import abgeschlossen</div>
        <div class="ergebnis-box {ergebnis?.fehler > 0 ? 'ergebnis-warn' : 'ergebnis-ok'}">
          <div class="ergebnis-icon">{ergebnis?.fehler > 0 ? '⚠️' : '✅'}</div>
          <div>
            <div class="ergebnis-titel">{ergebnis?.erstellt} Rechnung(en) erstellt</div>
            {#if ergebnis?.fehler > 0}<div class="ergebnis-sub">{ergebnis.fehler} Fehler</div>{/if}
          </div>
        </div>
        <div class="detail-liste">
          {#each ergebnis?.details || [] as d}
            <div class="detail-item {d.success ? 'detail-ok' : 'detail-err'}">
              <span>{d.success ? '✅' : '❌'}</span>
              <span class="detail-id">{d.order_id}</span>
              <span class="detail-info">{d.success ? `${d.re_nr}${d.positionen > 1 ? ` (${d.positionen} Pos.)` : ''}` : d.fehler}</span>
            </div>
          {/each}
        </div>
        <div class="card-footer">
          <button class="btn-ghost" onclick={reset}>Neuer Import</button>
          <a href="/rechnungen" class="btn-primary">→ Rechnungen</a>
        </div>
      </div>
    {/if}
  {/if}
</div>

{#if editOrder}
  <div class="modal-overlay open" onclick={(e) => { if (e.target === e.currentTarget) cancelEdit(); }}>
    <div class="modal edit-modal">
      <div class="modal-title">✏️ Bestellung {editOrder.external_order_id}</div>
      <div class="edit-section">
        <div class="edit-section-title">📋 Bestellung</div>
        <div class="edit-grid-2">
          <div class="edit-field"><label>Bestell-ID</label><input type="text" bind:value={editOrder.external_order_id} /></div>
          <div class="edit-field"><label>Datum</label><input type="date" bind:value={editOrder.datum} /></div>
          <div class="edit-field"><label>Zahlungsart</label><input type="text" bind:value={editOrder.zahlungsart} /></div>
          <div class="edit-field"><label>Versandkosten €</label><input type="number" step="0.01" bind:value={editOrder.versandkosten} /></div>
        </div>
      </div>
      <div class="edit-section">
        <div class="edit-section-title">👤 Käufer</div>
        <div class="edit-grid-2">
          <div class="edit-field"><label>Vorname</label><input type="text" bind:value={editOrder.kaeufer.vorname} /></div>
          <div class="edit-field"><label>Nachname *</label><input type="text" bind:value={editOrder.kaeufer.nachname} /></div>
          <div class="edit-field" style="grid-column:1/-1"><label>Straße</label><input type="text" bind:value={editOrder.kaeufer.strasse} /></div>
          <div class="edit-field"><label>PLZ</label><input type="text" bind:value={editOrder.kaeufer.plz} /></div>
          <div class="edit-field"><label>Ort</label><input type="text" bind:value={editOrder.kaeufer.ort} /></div>
          <div class="edit-field"><label>Land</label><input type="text" bind:value={editOrder.kaeufer.land} /></div>
          <div class="edit-field"><label>E-Mail</label><input type="email" bind:value={editOrder.kaeufer.email} /></div>
        </div>
      </div>
      <div class="edit-section">
        <div class="edit-section-title" style="display:flex;justify-content:space-between;align-items:center">
          <span>📦 Positionen ({editOrder.positionen.length})</span>
          <button class="btn-add-pos" onclick={addPosition}>+ Position</button>
        </div>
        {#each editOrder.positionen as pos, pi}
          <div class="edit-pos-row">
            <div class="edit-pos-nr">{pi + 1}</div>
            <div class="edit-pos-fields">
              <div class="edit-field" style="flex:2"><label>Bezeichnung</label><input type="text" bind:value={pos.bezeichnung} /></div>
              <div class="edit-field" style="flex:0 0 70px"><label>Menge</label><input type="number" min="1" bind:value={pos.menge} /></div>
              <div class="edit-field" style="flex:0 0 100px"><label>Einzelpreis €</label><input type="number" step="0.01" bind:value={pos.einzelpreis} /></div>
              <div class="edit-field" style="flex:0 0 70px"><label>MwSt %</label><input type="number" bind:value={pos.mwst_satz} /></div>
              {#if editOrder.positionen.length > 1}<button class="btn-remove-pos" onclick={() => removePosition(pi)}>×</button>{/if}
            </div>
          </div>
        {/each}
      </div>
      <div class="modal-actions">
        <button class="btn-cancel" onclick={cancelEdit}>Abbrechen</button>
        <button class="btn-primary" style="width:auto;padding:10px 26px" onclick={saveEdit}>💾 Übernehmen</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .page-container{padding: 24px; max-width: 1400px; margin: 0 auto;}.page-hdr{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:24px;flex-wrap:wrap;gap:12px}.page-title{font-size:1.3rem;font-weight:700;color:var(--text)}.page-sub{font-size:.85rem;color:var(--text2);margin-top:2px}
  .shop-tabs{display:flex;gap:4px;margin-bottom:24px;flex-wrap:wrap;border-bottom:1px solid var(--border)}.shop-tab{background:none;border:none;border-bottom:2px solid transparent;padding:10px 18px;font-size:.85rem;font-weight:600;color:var(--text2);cursor:pointer;transition:all .15s;white-space:nowrap}.shop-tab:hover:not(:disabled){color:var(--text)}.shop-tab.active{color:var(--primary);border-bottom-color:var(--primary)}.shop-tab.bald{opacity:.5;cursor:not-allowed}.bald-badge{font-size:.6rem;background:var(--surface2);color:var(--text3);border-radius:4px;padding:1px 5px;margin-left:5px;font-weight:600}
  .schritte{display:flex;align-items:center;margin-bottom:28px;flex-wrap:wrap}.schritt-item{display:flex;align-items:center;gap:8px}.schritt-kreis{width:28px;height:28px;border-radius:50%;border:2px solid var(--border);background:var(--surface);color:var(--text3);font-size:.78rem;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0}.schritt-item.aktiv .schritt-kreis{border-color:var(--primary);background:var(--primary);color:#fff}.schritt-item.fertig .schritt-kreis{border-color:#16a34a;background:#16a34a;color:#fff}.schritt-label{font-size:.8rem;color:var(--text3);white-space:nowrap}.schritt-item.aktiv .schritt-label{color:var(--primary);font-weight:600}.schritt-item.fertig .schritt-label{color:#16a34a}.schritt-linie{flex:1;height:2px;background:var(--border);min-width:20px;margin:0 8px}.schritt-linie.fertig{background:#16a34a}
  .card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:24px;margin-bottom:16px}.card-titel{font-size:1rem;font-weight:700;color:var(--text);margin-bottom:8px}.card-hinweis{font-size:.84rem;color:var(--text2);margin-bottom:18px;line-height:1.5}.card-footer{display:flex;justify-content:flex-end;gap:10px;margin-top:20px;padding-top:16px;border-top:1px solid var(--border)}
  .drop-zone{border:2px dashed var(--border);border-radius:12px;padding:48px 24px;text-align:center;cursor:pointer;transition:all .2s;margin-bottom:16px}.drop-zone:hover,.drop-zone.drag-over{border-color:var(--primary);background:color-mix(in srgb,var(--primary) 5%,transparent)}.drop-icon{font-size:2.5rem;margin-bottom:12px}.drop-text{font-size:.95rem;font-weight:600;color:var(--text);margin-bottom:6px}.drop-hint{font-size:.8rem;color:var(--text3)}
  .gruppe-titel{font-size:.75rem;font-weight:700;color:var(--text3);text-transform:uppercase;letter-spacing:.06em;margin:20px 0 8px;padding-bottom:6px;border-bottom:1px solid var(--border)}.mapping-grid{display:flex;flex-direction:column;gap:4px;margin-bottom:8px}.mapping-row{display:grid;grid-template-columns:180px 1fr 140px 160px;gap:8px;align-items:center;padding:6px 0;border-bottom:1px solid var(--border)}.mapping-row:last-child{border-bottom:none}.mapping-label{font-size:.82rem;font-weight:600;color:var(--text)}.mapping-select{background:var(--surface);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:7px;font-size:.8rem;outline:none}.mapping-select:focus{border-color:var(--primary)}.mapping-preview{font-size:.75rem;color:var(--text3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;background:var(--surface2);padding:4px 8px;border-radius:5px}.mapping-preview.leer{opacity:.5;font-style:italic}.fallback-input{background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:7px;font-size:.8rem;outline:none;width:100%}.fallback-input:focus{border-color:var(--primary)}.fallback-input:disabled{opacity:.4;cursor:not-allowed}
  .vorschau-tabelle-wrap{overflow-x:auto;border:1px solid var(--border);border-radius:8px;max-height:500px;overflow-y:auto}.vorschau-tabelle{width:100%;border-collapse:collapse;font-size:.8rem}.vorschau-tabelle th{padding:8px 10px;text-align:left;font-size:.72rem;color:var(--text3);font-weight:600;border-bottom:2px solid var(--border);background:var(--surface2);position:sticky;top:0;z-index:1}.vorschau-tabelle td{padding:7px 10px;border-bottom:1px solid var(--border);color:var(--text);vertical-align:top}.vorschau-tabelle tr:last-child td{border-bottom:none}.vorschau-tabelle tr:hover td{background:var(--surface2)}.vorschau-tabelle tr.multi-row td{background:color-mix(in srgb,var(--primary) 3%,transparent)}.td-nr{color:var(--text3);font-size:.75rem}.td-mono{font-family:monospace;font-size:.78rem;color:var(--primary);font-weight:600}.td-sub{font-size:.7rem;color:var(--text3);margin-top:1px}.buyer-cell{font-weight:600;font-size:.82rem}
  .pos-line{padding:2px 0}.pos-line-border{border-top:1px dashed var(--border);margin-top:3px;padding-top:3px}.pos-name{font-weight:600;font-size:.8rem}.pos-detail{display:block;font-size:.7rem;color:var(--text3)}.pos-badge{display:inline-flex;align-items:center;justify-content:center;background:var(--primary);color:#fff;border-radius:10px;min-width:22px;height:20px;font-size:.7rem;font-weight:700;padding:0 6px}
  .btn-icon{background:none;border:none;cursor:pointer;font-size:.85rem;padding:2px 4px;border-radius:4px;transition:background .15s}.btn-icon:hover{background:var(--surface2)}.btn-icon-danger:hover{background:#fef2f2}
  .progress-bar-wrap{height:6px;background:var(--surface2);border-radius:3px;margin-top:16px;overflow:hidden}.progress-bar{height:100%;background:var(--primary);border-radius:3px;transition:width .3s}.progress-text{font-size:.78rem;color:var(--text2);text-align:center;margin-top:6px}
  .ergebnis-box{display:flex;align-items:center;gap:16px;padding:16px 20px;border-radius:10px;margin-bottom:16px}.ergebnis-ok{background:#f0fdf4;border:1px solid #bbf7d0}.ergebnis-warn{background:#fffbeb;border:1px solid #fde68a}.ergebnis-icon{font-size:1.8rem}.ergebnis-titel{font-size:.95rem;font-weight:700;color:var(--text)}.ergebnis-sub{font-size:.82rem;color:#d97706;margin-top:2px}.detail-liste{display:flex;flex-direction:column;gap:4px;max-height:300px;overflow-y:auto;border:1px solid var(--border);border-radius:8px}.detail-item{display:flex;align-items:center;gap:10px;padding:8px 12px;font-size:.8rem;border-bottom:1px solid var(--border)}.detail-item:last-child{border-bottom:none}.detail-ok{background:#f0fdf4}.detail-err{background:#fef2f2}.detail-id{font-family:monospace;font-size:.75rem;color:var(--primary);min-width:120px}.detail-info{color:var(--text2);font-size:.78rem}
  .hinweis{border-radius:8px;padding:10px 14px;font-size:.82rem;margin-bottom:8px;line-height:1.5;display:flex;align-items:center;gap:10px}.hinweis-rot{background:#fef2f2;border:1px solid #fecaca;color:#dc2626}
  .form-group{display:flex;flex-direction:column;gap:5px}.form-group label{font-size:.78rem;color:var(--text2);font-weight:500}.form-group input{background:var(--surface);border:1px solid var(--border);color:var(--text);padding:8px 12px;border-radius:8px;font-size:.85rem;outline:none}.form-group input:focus{border-color:var(--primary)}
  .btn-primary{background:var(--primary);color:#fff;border:none;padding:8px 18px;border-radius:8px;font-size:.85rem;font-weight:600;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:6px}.btn-primary:disabled{opacity:.6;cursor:not-allowed}.btn-ghost{background:var(--surface2);color:var(--text);border:1px solid var(--border);padding:8px 18px;border-radius:8px;font-size:.85rem;font-weight:500;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center}.btn-ghost:hover{border-color:var(--primary);color:var(--primary)}
  .modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.5);backdrop-filter:blur(4px);z-index:1000;display:none;align-items:center;justify-content:center}.modal-overlay.open{display:flex}.edit-modal{background:var(--surface);border:1px solid var(--border);border-radius:18px;padding:28px;width:95%;max-width:720px;max-height:90vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,.2)}.modal-title{font-size:1.1rem;font-weight:800;margin-bottom:20px;color:var(--text)}.modal-actions{display:flex;gap:10px;justify-content:flex-end;margin-top:20px;padding-top:16px;border-top:1px solid var(--border)}.btn-cancel{background:transparent;border:1.5px solid var(--border);border-radius:9px;padding:10px 20px;font-size:13px;font-weight:600;color:var(--text2);cursor:pointer}.btn-cancel:hover{border-color:var(--text2);color:var(--text)}
  .edit-section{margin-bottom:16px}.edit-section-title{font-size:.78rem;font-weight:700;color:var(--text3);text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid var(--border)}.edit-grid-2{display:grid;grid-template-columns:1fr 1fr;gap:10px}.edit-field{display:flex;flex-direction:column;gap:3px}.edit-field label{font-size:.72rem;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:.5px}.edit-field input{background:var(--surface2);border:1.5px solid var(--border);border-radius:7px;padding:7px 10px;font-size:.85rem;color:var(--text);outline:none;font-family:inherit}.edit-field input:focus{border-color:var(--primary)}
  .edit-pos-row{display:flex;gap:10px;align-items:flex-end;margin-bottom:8px;padding:10px;background:var(--surface2);border-radius:8px;border:1px solid var(--border)}.edit-pos-nr{font-size:.85rem;font-weight:700;color:var(--text3);min-width:20px;padding-bottom:8px}.edit-pos-fields{display:flex;gap:8px;flex:1;flex-wrap:wrap;align-items:flex-end}.btn-add-pos{background:var(--primary);color:#fff;border:none;padding:4px 12px;border-radius:6px;font-size:.75rem;font-weight:600;cursor:pointer}.btn-remove-pos{background:none;border:none;color:#dc2626;font-size:1.2rem;cursor:pointer;padding:4px 8px;border-radius:4px;align-self:flex-end;margin-bottom:4px}.btn-remove-pos:hover{background:#fef2f2}
  @media(max-width:768px){.mapping-row{grid-template-columns:1fr;gap:4px}.edit-grid-2{grid-template-columns:1fr}.edit-pos-fields{flex-direction:column}}
</style>
