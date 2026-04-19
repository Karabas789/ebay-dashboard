<script>
  import { onMount } from 'svelte';
  import { apiCall } from '$lib/api.js';
  import { currentUser, showToast } from '$lib/stores.js';

  // ─── State ──────────────────────────────────────────────
  let allProdukte = $state([]);
  let loading = $state(true);
  let error = $state('');

  // Search / Filter
  let searchQuery = $state('');
  let filterMode = $state('alle'); // 'alle', 'einzeln', 'varianten', 'niedrig', 'ausverkauft'

  // Product Modal
  let showProductModal = $state(false);
  let editProduct = $state(null);
  let productForm = $state({
    name: '', artikelnummer: '', ebay_artikel_id: '', preis: '',
    lagerbestand: '', versanddauer: '', bild_url: '', beschreibung: '',
    inhaltsstoffe: '', hinweise: ''
  });

  // Varianten Modal
  let showVariantenModal = $state(false);
  let variantenProduct = $state(null);
  let variantenInputs = $state({});
  let savingVarianten = $state(false);
  let variantenOriginal = $state({}); // snapshot beim Öffnen
  let savingVarianteId = $state(null); // ID der gerade einzeln gespeicherten Variante

  // Import Modals
  let showImportModal = $state(false);
  let importOptions = $state({ nur_neu: false, update_preis: false, update_lager: false, update_name: false, update_bild: false });
  let showVariantenImportModal = $state(false);
  let variantenImportOptions = $state({ nur_neu: false, update_preis: false, update_lager: false, update_bild: false });

  // Export Modal
  let showExportModal = $state(false);
  let exportFormat = $state('overview'); // 'raw' | 'overview'
  let exportSearchQuery = $state('');
  let exportSelected = $state(new Set());
  let exportMergeMap = $state({});

  // SKU Generator Modal
  let showSkuModal = $state(false);
  let generatedSkus = $state([]);
  let skuSaving = $state(false);
  let skuStatus = $state('');

  // Inline editing (for single products)
  let inlineEdits = $state({});

  // Lager-Abgleich
  let showAbgleichModal = $state(false);
  let abgleichLoading = $state(false);
  let abgleichResult = $state(null);

  // ─── Derived ────────────────────────────────────────────
  let filteredProducts = $derived.by(() => {
    let products = allProdukte;

    // Search filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      products = products.filter(p =>
        (p.name || '').toLowerCase().includes(q) ||
        String(p.ebay_artikel_id || '').includes(q) ||
        (p.artikelnummer || '').toLowerCase().includes(q)
      );
    }

    // Category filter
    if (filterMode === 'einzeln') {
      products = products.filter(p => !p.varianten || p.varianten.length === 0);
    } else if (filterMode === 'varianten') {
      products = products.filter(p => p.varianten && p.varianten.length > 0);
    } else if (filterMode === 'niedrig') {
      products = products.filter(p => {
        const lager = getProductStock(p);
        return lager > 0 && lager <= 10;
      });
    } else if (filterMode === 'ausverkauft') {
      products = products.filter(p => getProductStock(p) === 0);
    }

    return products;
  });

  let einzelProducts = $derived(filteredProducts.filter(p => !p.varianten || p.varianten.length === 0));
  let variantenProducts = $derived(filteredProducts.filter(p => p.varianten && p.varianten.length > 0));

  let stats = $derived.by(() => {
    const total = allProdukte.length;
    const einzel = allProdukte.filter(p => !p.varianten || p.varianten.length === 0).length;
    const mitVar = allProdukte.filter(p => p.varianten && p.varianten.length > 0).length;
    const niedrig = allProdukte.filter(p => { const l = getProductStock(p); return l > 0 && l <= 10; }).length;
    const ausverkauft = allProdukte.filter(p => getProductStock(p) === 0).length;
    return { total, einzel, mitVar, niedrig, ausverkauft };
  });

  let exportSearchResults = $derived.by(() => {
    if (!exportSearchQuery.trim()) return [];
    const q = exportSearchQuery.toLowerCase();
    return allProdukte.filter(p =>
      (p.name || '').toLowerCase().includes(q) ||
      String(p.ebay_artikel_id || '').includes(q)
    );
  });

  // ─── Helpers ────────────────────────────────────────────
  function getProductStock(p) {
    const varianten = p.varianten || [];
    return varianten.length > 0
      ? varianten.reduce((sum, v) => sum + (v.lagerbestand ?? 0), 0)
      : (p.lagerbestand ?? 0);
  }

  function getStockColor(lager) {
    if (lager === 0) return 'var(--danger, #ef4444)';
    if (lager <= 10) return 'var(--warning, #f59e0b)';
    return 'var(--success, #22c55e)';
  }

  function getStockLabel(lager) {
    if (lager === 0) return '🔴 Ausverkauft';
    if (lager <= 10) return '🟡 Niedrig';
    return '🟢 OK';
  }

  function getProductImage(p) {
    return p.bild_url || (p.varianten || []).find(v => v.bild_url)?.bild_url || '';
  }

  function escHtml(str) {
    return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // ─── API Calls ──────────────────────────────────────────
  async function loadProdukte() {
    loading = true;
    error = '';
    try {
      const data = await apiCall('/produkte-laden', {
        user_id: $currentUser?.id,
        ebay_username: $currentUser?.ebay_user_id
      });
      allProdukte = data.data || [];
      // Init inline edits for single products
      const newEdits = {};
      for (const p of allProdukte) {
        if (!p.varianten || p.varianten.length === 0) {
          newEdits[p.id] = {
            lager: p.lagerbestand ?? 0,
            ebayMenge: p.min_lagerbestand ?? (p.lagerbestand ?? 0),
            preis: p.preis ? parseFloat(p.preis).toFixed(2) : '0.00'
          };
        }
      }
      inlineEdits = newEdits;
    } catch (e) {
      error = 'Verbindungsfehler beim Laden der Produkte';
      console.error(e);
    } finally {
      loading = false;
    }
  }

  // Save single product stock inline
  async function saveBestand(productId) {
    const edits = inlineEdits[productId];
    if (!edits) return;

    try {
      const data = await apiCall('/produkte-bestand-update', {
        id: productId,
        lagerbestand: parseInt(edits.lager) || 0,
        min_lagerbestand: parseInt(edits.ebayMenge) || 0,
        ebay_menge: parseInt(edits.ebayMenge) || 0,
        preis: parseFloat(edits.preis) || 0,
        user_id: $currentUser?.id,
        ebay_username: $currentUser?.ebay_user_id
      });
      if (data.success) {
        showToast('Bestand gespeichert ✓', 'success');
        await loadProdukte();
      } else {
        showToast(data.message || 'Fehler', 'error');
      }
    } catch (e) {
      showToast('Verbindungsfehler', 'error');
    }
  }

  // Get inline edit values for a product (read-only, no state mutation)
  function getInlineEdit(p) {
    return inlineEdits[p.id] || {
      lager: p.lagerbestand ?? 0,
      ebayMenge: p.min_lagerbestand ?? (p.lagerbestand ?? 0),
      preis: p.preis ? parseFloat(p.preis).toFixed(2) : '0.00'
    };
  }

  // ─── Varianten Modal ───────────────────────────────────
  function openVariantenModal(productId) {
    const p = allProdukte.find(x => x.id === productId);
    if (!p) return;
    variantenProduct = p;
    const inputs = {};
    const original = {};
    (p.varianten || []).forEach(v => {
      const entry = {
        lager: v.lagerbestand ?? 0,
        ebayMenge: v.min_lagerbestand ?? 3,
        preis: v.preis ? parseFloat(v.preis).toFixed(2) : '0.00'
      };
      inputs[v.id] = { ...entry };
      original[v.id] = { ...entry };
    });
    variantenInputs = inputs;
    variantenOriginal = original;
    showVariantenModal = true;
  }

  function hasVariantenChanges() {
    for (const [id, curr] of Object.entries(variantenInputs)) {
      const orig = variantenOriginal[id];
      if (!orig) continue;
      if (
        String(curr.lager) !== String(orig.lager) ||
        String(curr.ebayMenge) !== String(orig.ebayMenge) ||
        String(curr.preis) !== String(orig.preis)
      ) return true;
    }
    return false;
  }

  function closeVariantenModal() {
    if (hasVariantenChanges()) {
      if (!confirm('Es gibt ungespeicherte Änderungen. Trotzdem schließen?')) return;
    }
    showVariantenModal = false;
  }

  async function saveAlleVarianten() {
    if (!variantenProduct) return;
    savingVarianten = true;
    let ok = 0, err = 0;

    for (const v of variantenProduct.varianten || []) {
      const inputs = variantenInputs[v.id] || {};
      try {
        const data = await apiCall('/variante-bestand-update', {
          id: v.id,
          lagerbestand: parseInt(inputs.lager) || 0,
          preis: parseFloat(inputs.preis) || 0,
          ebay_menge: parseInt(inputs.ebayMenge) || 0
        });
        if (data.success && data.variante?.id) {
          v.lagerbestand = parseInt(inputs.lager) || 0;
          v.preis = parseFloat(inputs.preis) || 0;
          v.min_lagerbestand = parseInt(inputs.ebayMenge) || 0;
          v.id = data.variante.id;
          ok++;
        } else if (data.success && !data.variante?.id) {
          err++;
        } else {
          err++;
        }
      } catch (e) {
        err++;
      }
    }

    savingVarianten = false;
    if (err === 0) {
      showToast(`✅ Alle ${ok} Varianten gespeichert!`, 'success');
      openVariantenModal(variantenProduct.id);
    } else if (ok === 0) {
      showToast('⚠️ Varianten-IDs veraltet. Bitte Seite neu laden (F5).', 'error');
    } else {
      showToast(`⚠️ ${ok} gespeichert, ${err} Fehler.`, 'error');
      openVariantenModal(variantenProduct.id);
    }
  }

  async function saveEinzelneVariante(varianteId) {
    if (!variantenProduct) return;
    const v = variantenProduct.varianten?.find(x => x.id === varianteId);
    if (!v) return;
    const inputs = variantenInputs[varianteId] || {};
    savingVarianteId = varianteId;
    try {
      const data = await apiCall('/variante-bestand-update', {
        id: varianteId,
        lagerbestand: parseInt(inputs.lager) || 0,
        preis: parseFloat(inputs.preis) || 0,
        ebay_menge: parseInt(inputs.ebayMenge) || 0
      });
      if (data.success && data.variante?.id) {
        v.lagerbestand = parseInt(inputs.lager) || 0;
        v.preis = parseFloat(inputs.preis) || 0;
        v.min_lagerbestand = parseInt(inputs.ebayMenge) || 0;
        variantenOriginal[varianteId] = {
          lager: parseInt(inputs.lager) || 0,
          ebayMenge: parseInt(inputs.ebayMenge) || 0,
          preis: parseFloat(inputs.preis).toFixed(2)
        };
        variantenInputs[varianteId].preis = parseFloat(inputs.preis).toFixed(2);
        showToast('✅ Variante gespeichert', 'success');
      } else {
        showToast('⚠️ Fehler beim Speichern', 'error');
      }
    } catch (e) {
      showToast('Verbindungsfehler', 'error');
    } finally {
      savingVarianteId = null;
    }
  }

  // ─── Product Modal ─────────────────────────────────────
  function openProductModal(p = null) {
    editProduct = p;
    productForm = {
      name: p?.name || '',
      artikelnummer: p?.artikelnummer || '',
      ebay_artikel_id: p?.ebay_artikel_id || '',
      preis: p?.preis || '',
      lagerbestand: p?.lagerbestand || '',
      versanddauer: p?.versanddauer || '',
      bild_url: p?.bild_url || '',
      beschreibung: p?.beschreibung || '',
      inhaltsstoffe: p?.inhaltsstoffe || '',
      hinweise: p?.hinweise || ''
    };
    showProductModal = true;
  }

  async function saveProduct() {
    if (!productForm.name.trim()) {
      showToast('Produktname fehlt', 'error');
      return;
    }
    try {
      const data = await apiCall('/produkte-bestand-update', {
        id: editProduct?.id || null,
        ...productForm,
        preis: parseFloat(productForm.preis) || 0,
        lagerbestand: parseInt(productForm.lagerbestand) || 0,
        user_id: $currentUser?.id
      });
      if (data.success) {
        showToast(editProduct ? 'Produkt aktualisiert ✓' : 'Produkt gespeichert ✓', 'success');
        showProductModal = false;
        await loadProdukte();
      } else {
        showToast(data.message || 'Fehler', 'error');
      }
    } catch (e) {
      showToast('Verbindungsfehler', 'error');
    }
  }

  // ─── Import ────────────────────────────────────────────
  async function startProduktImport() {
    showImportModal = false;
    showToast('📦 Produkte werden importiert...', 'success');
    try {
      const data = await apiCall('/ebay-produkte-importieren', {
        nur_neu: importOptions.nur_neu,
        update_preis: !importOptions.nur_neu && importOptions.update_preis,
        update_lager: !importOptions.nur_neu && importOptions.update_lager,
        update_name: !importOptions.nur_neu && importOptions.update_name,
        update_bild: !importOptions.nur_neu && importOptions.update_bild
      });
      if (data.success) {
        showToast(`✅ ${data.importiert} Produkte importiert!`, 'success');
        await loadProdukte();
      } else {
        showToast(data.message || 'Fehler beim Import', 'error');
      }
    } catch (e) {
      showToast('Verbindungsfehler', 'error');
    }
  }

  async function startVariantenImport() {
    showVariantenImportModal = false;
    showToast('🔄 Varianten werden geladen...', 'success');
    try {
      const data = await apiCall('/varianten-importieren', {
        nur_neu: variantenImportOptions.nur_neu,
        update_preis: variantenImportOptions.update_preis,
        update_lager: variantenImportOptions.update_lager,
        update_bild: variantenImportOptions.update_bild
      });
      if (data.success) {
        showToast('✅ Varianten importiert!', 'success');
        await loadProdukte();
      } else {
        showToast(data.message || 'Fehler beim Varianten-Import', 'error');
      }
    } catch (e) {
      showToast('Verbindungsfehler', 'error');
    }
  }

  // ─── CSV Export ────────────────────────────────────────
  function toggleExportProduct(ebayId) {
    const newSet = new Set(exportSelected);
    if (newSet.has(ebayId)) {
      newSet.delete(ebayId);
      const newMap = { ...exportMergeMap };
      delete newMap[ebayId];
      exportMergeMap = newMap;
    } else {
      newSet.add(ebayId);
    }
    exportSelected = newSet;
  }

  function removeExportProduct(ebayId) {
    const newSet = new Set(exportSelected);
    newSet.delete(ebayId);
    exportSelected = newSet;
    const newMap = { ...exportMergeMap };
    delete newMap[ebayId];
    exportMergeMap = newMap;
  }

  function getFilteredExportProdukte() {
    if (!exportSelected.size) return allProdukte;
    return allProdukte.filter(p => exportSelected.has(String(p.ebay_artikel_id || '')));
  }

  function downloadCSV(csv, prefix) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' }));
    a.download = prefix + new Date().toISOString().slice(0, 10) + '.csv';
    a.click();
  }

  function doExportCSV() {
    showExportModal = false;
    if (exportFormat === 'raw') exportRawCSV();
    else exportOverviewCSV();
  }

  function exportRawCSV() {
    const produkte = getFilteredExportProdukte();
    const rows = [['Name','eBay-ID','Artikelnummer','Preis','Lagerbestand','Variante','Verpackungseinheit','Produktart','eBay-SKU']];
    for (const p of produkte) {
      if (!p.varianten || !p.varianten.length) {
        rows.push([p.name||'', p.ebay_artikel_id||'', p.artikelnummer||'', p.preis||'', p.lagerbestand||0,'','','','']);
      } else {
        for (const v of p.varianten) {
          rows.push([p.name||'', p.ebay_artikel_id||'', p.artikelnummer||'', v.preis||'', v.lagerbestand||0, v.verpackungseinheit||'', v.verpackungseinheit||'', v.produktart||'', v.ebay_sku||'']);
        }
      }
    }
    const esc = v => '"' + String(v).replace(/"/g, '""') + '"';
    downloadCSV(rows.map(r => r.map(c => esc(c)).join(',')).join('\n'), 'lagerbestand_rohdaten_');
    showToast(`✅ Rohdaten exportiert (${produkte.length} Produkte)`, 'success');
  }

  function exportOverviewCSV() {
    const produkte = getFilteredExportProdukte();
    const BASISNAME_MAP = {};
    for (const [id, name] of Object.entries(exportMergeMap)) {
      if (name && name.trim()) BASISNAME_MAP[id] = name.trim();
    }

    function extractPackInfo(ve, pa) {
      ve = (ve || '').trim(); pa = (pa || '').trim();
      const mVE = ve.match(/^(\d+)[xX]\s+(.+)$/);
      if (mVE) {
        const lb = { 1: 'Einzeln', 2: 'DuoPack', 3: 'TrioPack' };
        return { baseVe: mVE[2].trim(), basePa: pa, packLabel: lb[parseInt(mVE[1])] || 'Einzeln' };
      }
      const pats = [
        { re: /TrioPack|Trio\s+Pack/i, l: 'TrioPack' },
        { re: /DuoPack|Duo\s+Pack/i, l: 'DuoPack' },
        { re: /Einzelst(?:ück)?\.?|Einzel\s+Stück/i, l: 'Einzeln' }
      ];
      for (const { re, l } of pats) {
        if (re.test(pa)) {
          let bp = pa.replace(re, '').replace(/\s{2,}/g, ' ').trim();
          if (ve && bp.toLowerCase().startsWith(ve.toLowerCase())) bp = bp.slice(ve.length).trim();
          return { baseVe: ve, basePa: bp || pa, packLabel: l };
        }
      }
      return { baseVe: ve, basePa: pa, packLabel: 'Einzeln' };
    }

    function sortKeyVe(ve) {
      const s = (ve || '').toLowerCase().trim();
      let m;
      m = s.match(/(\d+(?:[.,]\d+)?)\s*(ml|l)\b/); if (m) { let v = parseFloat(m[1].replace(',', '.')); if (m[2] === 'ml') v /= 1000; return [1, v, s]; }
      m = s.match(/(\d+)\s*(?:watt|w)\b/i); if (m) return [2, parseInt(m[1]), s];
      m = s.match(/(\d+)\s*mm/); if (m) return [3, parseInt(m[1]), s];
      m = s.match(/^(\d+)/); if (m) return [4, parseInt(m[1]), s];
      return [9, 0, s];
    }
    function cmpKey(a, b) { for (let i = 0; i < a.length; i++) { if (a[i] < b[i]) return -1; if (a[i] > b[i]) return 1; } return 0; }

    const grouped = {};
    for (const p of produkte) {
      const ebayId = String(p.ebay_artikel_id || '').trim();
      const merged = !!BASISNAME_MAP[ebayId];
      const cleanName = (BASISNAME_MAP[ebayId] || p.name || '').replace(/\s*\[.*?\]\s*/g, '').trim();
      const varianten = Array.isArray(p.varianten) ? p.varianten : [];
      if (!varianten.length) {
        const key = '0||' + cleanName + '||||';
        if (!grouped[key]) grouped[key] = { isSingle: true, Name: cleanName, EbayId: merged ? '' : ebayId, Groesse: '', Variante: '', Einzeln: 0, DuoPack: 0, TrioPack: 0 };
        grouped[key].Einzeln += (p.lagerbestand || 0);
      } else {
        for (const v of varianten) {
          const { baseVe, basePa, packLabel } = extractPackInfo(v.verpackungseinheit, v.produktart);
          const key = '1||' + cleanName + '||' + baseVe + '||' + basePa;
          if (!grouped[key]) grouped[key] = { isSingle: false, Name: cleanName, EbayId: merged ? '' : ebayId, Groesse: baseVe, Variante: basePa, Einzeln: 0, DuoPack: 0, TrioPack: 0 };
          grouped[key][packLabel] = (grouped[key][packLabel] || 0) + (v.lagerbestand || 0);
        }
      }
    }

    const sorted = Object.values(grouped).sort((a, b) => {
      if (a.isSingle !== b.isSingle) return a.isSingle ? -1 : 1;
      const nc = a.Name.toLowerCase().localeCompare(b.Name.toLowerCase(), 'de'); if (nc) return nc;
      const vc = cmpKey(sortKeyVe(a.Groesse), sortKeyVe(b.Groesse)); if (vc) return vc;
      return a.Variante.toLowerCase().localeCompare(b.Variante.toLowerCase(), 'de');
    });

    const esc = v => '"' + String(v).replace(/"/g, '""') + '"';
    const rows = [['Name','eBay-ID','Groesse_Typ','Variante','Einzeln','DuoPack','TrioPack','Gesamt_Einheiten','Gesamt_Packungen','Nachbestellen'].join(',')];
    for (const g of sorted) {
      const e = g.Einzeln || 0, d = g.DuoPack || 0, t = g.TrioPack || 0;
      rows.push([esc(g.Name), esc(g.EbayId), esc(g.Groesse), esc(g.Variante), e, d, t, e + d * 2 + t * 3, e + d + t, (e + d + t) <= 3 ? 'JA' : 'OK'].join(','));
    }
    const label = exportSelected.size ? exportSelected.size + ' Produkte' : 'alle Produkte';
    downloadCSV(rows.join('\n'), 'lagerbestand_uebersicht_');
    showToast(`✅ Exportiert: ${sorted.length} Zeilen (${label})`, 'success');
  }

  // ─── SKU Generator ─────────────────────────────────────
  function openSkuGenerator() {
    generatedSkus = [];
    skuStatus = '';
    if (!allProdukte.length) { showToast('Bitte zuerst Produkte laden', 'error'); return; }

    const missing = [];
    let skuCounter = 1;
    for (const p of allProdukte) {
      if (!p.varianten || !p.varianten.length) continue;
      for (const v of p.varianten) {
        if (!v.ebay_sku) {
          const rawBase = (v.verpackungseinheit || v.produktart || v.specific_name || 'V');
          const base = rawBase.replace(/[^a-zA-Z0-9 ]/g, '').replace(/\s+/g, '-').replace(/-+/g, '-').trim().substring(0, 35);
          const nr = String(skuCounter).padStart(3, '0');
          skuCounter++;
          missing.push({
            variante_id: v.id,
            produkt_name: p.name,
            variante_name: v.verpackungseinheit || v.produktart || '—',
            sku_vorschlag: base + '-' + nr,
            sku: base + '-' + nr
          });
        }
      }
    }

    generatedSkus = missing;
    skuStatus = missing.length ? `${missing.length} Variante(n) ohne SKU gefunden` : '';
    showSkuModal = true;
  }

  async function saveGeneratedSkus() {
    if (!generatedSkus.length) return;
    skuSaving = true;

    const skuList = generatedSkus.filter(g => g.sku?.trim());
    const byProdukt = {};
    for (const g of skuList) {
      const v = allProdukte.flatMap(p => p.varianten || []).find(x => x.id === g.variante_id);
      const p = allProdukte.find(x => x.varianten?.some(vv => vv.id === g.variante_id));
      if (!v || !p) continue;
      const pid = p.id;
      const ebayId = String(p.ebay_artikel_id || '');
      if (!byProdukt[pid]) byProdukt[pid] = { ebay_artikel_id: ebayId, varianten: [], produkt: p };
      byProdukt[pid].varianten.push({
        id: v.id, sku: g.sku,
        verpackungseinheit: v.verpackungseinheit || '',
        produktart: v.produktart || '',
        specific_name: v.specific_name || 'Ausfuehrung'
      });
    }

    const produkte = Object.values(byProdukt);
    let ebayOk = 0, ebayErr = 0, errProdukte = 0;

    for (let i = 0; i < produkte.length; i++) {
      const gruppe = produkte[i];
      skuStatus = `Produkt ${i + 1} / ${produkte.length} – ${gruppe.ebay_artikel_id}...`;

      try {
        const d = await apiCall('/varianten-sku-bulk', {
          ebay_artikel_id: gruppe.ebay_artikel_id,
          varianten: gruppe.varianten
        });
        if (d.success) {
          for (const v of gruppe.varianten) {
            const lv = allProdukte.flatMap(p => p.varianten || []).find(x => x.id === v.id);
            if (lv) lv.ebay_sku = v.sku;
          }
          const ack = d.ebay_ack || '';
          if (ack === 'Success' || ack === 'Warning') ebayOk++;
          else ebayErr++;
        } else errProdukte++;
      } catch (e) { errProdukte++; }
      await new Promise(r => setTimeout(r, 600));
    }

    skuSaving = false;
    if (errProdukte === 0 && ebayErr === 0) {
      skuStatus = `✅ ${skuList.length} SKUs gespeichert, eBay: ${ebayOk} Listings`;
      showToast(`${skuList.length} SKUs gespeichert & bei eBay registriert!`, 'success');
      setTimeout(() => { showSkuModal = false; loadProdukte(); }, 2000);
    } else if (ebayErr > 0) {
      skuStatus = `DB: OK, eBay: ${ebayOk} OK / ${ebayErr} Fehler`;
      showToast(`DB OK – ${ebayErr} eBay Fehler`, 'error');
    } else {
      skuStatus = `Fehler bei ${errProdukte} Produkten`;
      showToast('Fehler beim Speichern', 'error');
    }
  }

  // ─── Lifecycle ─────────────────────────────────────────
  async function doLagerAbgleich() {
    abgleichLoading = true;
    abgleichResult = null;
    try {
      const data = await apiCall('/lager-abgleich', {
        user_id: $currentUser.id,
        ebay_username: $currentUser.ebay_user_id
      });
      abgleichResult = data;
      if (data.success) {
        await loadProdukte();
      }
    } catch (e) {
      abgleichResult = { success: false, message: 'Verbindungsfehler: ' + e.message };
    } finally {
      abgleichLoading = false;
    }
  }

  onMount(() => {
    loadProdukte();
  });
</script>

<!-- ═══════════════════════════════════════════════════════ -->
<!-- HEADER -->
<div class="page-header">
  <div class="page-header-left">
    <h1 class="page-title">Produkte</h1>
    <p class="page-subtitle">Produktverwaltung & Lagerbestand</p>
  </div>
  <div class="page-header-actions">
    <button class="btn btn-primary" onclick={() => showImportModal = true}>📦 eBay Import</button>
    <button class="btn btn-primary" onclick={() => showVariantenImportModal = true}>🔄 Varianten</button>
    <button class="btn btn-primary" onclick={() => { exportSelected = new Set(); exportMergeMap = {}; exportSearchQuery = ''; showExportModal = true; }}>⬇️ Bestand</button>
    <button class="btn btn-abgleich" onclick={() => { showAbgleichModal = true; abgleichResult = null; }}>⚖️ Lager abgleichen</button>
    <!-- <button class="btn btn-primary" onclick={openSkuGenerator}>🏷️ SKU</button> -->
  </div>
</div>

<!-- STATS BAR -->
{#if !loading && allProdukte.length > 0}
<div class="stats-bar">
  <button class="stat-chip" class:active={filterMode === 'alle'} onclick={() => filterMode = 'alle'}>
    Alle <span class="stat-count">{stats.total}</span>
  </button>
  <button class="stat-chip" class:active={filterMode === 'einzeln'} onclick={() => filterMode = 'einzeln'}>
    📦 Einzelartikel <span class="stat-count">{stats.einzel}</span>
  </button>
  <button class="stat-chip" class:active={filterMode === 'varianten'} onclick={() => filterMode = 'varianten'}>
    📋 Varianten <span class="stat-count">{stats.mitVar}</span>
  </button>
  {#if stats.niedrig > 0}
  <button class="stat-chip chip-warning" class:active={filterMode === 'niedrig'} onclick={() => filterMode = 'niedrig'}>
    🟡 Niedrig <span class="stat-count">{stats.niedrig}</span>
  </button>
  {/if}
  {#if stats.ausverkauft > 0}
  <button class="stat-chip chip-danger" class:active={filterMode === 'ausverkauft'} onclick={() => filterMode = 'ausverkauft'}>
    🔴 Ausverkauft <span class="stat-count">{stats.ausverkauft}</span>
  </button>
  {/if}
</div>
{/if}

<!-- SEARCH -->
{#if !loading && allProdukte.length > 0}
<div class="search-bar">
  <span class="search-icon">🔍</span>
  <input type="text" class="search-input" placeholder="Produkte suchen... (Name, eBay-ID, Artikelnummer)" bind:value={searchQuery} />
  {#if searchQuery}
    <button class="search-clear" onclick={() => searchQuery = ''}>✕</button>
  {/if}
</div>
{/if}

<!-- LOADING -->
{#if loading}
<div class="empty-state">
  <div class="spinner"></div>
  <p>Lade Produkte...</p>
</div>

<!-- ERROR -->
{:else if error}
<div class="empty-state">
  <div class="empty-icon">⚠️</div>
  <p>{error}</p>
  <button class="btn btn-primary" onclick={loadProdukte}>Erneut versuchen</button>
</div>

<!-- NO PRODUCTS -->
{:else if allProdukte.length === 0}
<div class="empty-state">
  <div class="empty-icon">📦</div>
  <p>Keine Produkte gefunden</p>
  <button class="btn btn-primary" onclick={() => showImportModal = true}>📦 Von eBay importieren</button>
</div>

<!-- NO RESULTS -->
{:else if filteredProducts.length === 0}
<div class="empty-state">
  <div class="empty-icon">🔍</div>
  <p>Keine Produkte für diese Filterung</p>
</div>

<!-- PRODUCT GRID -->
{:else}
<div class="products-grid">
  <!-- Einzelartikel Section -->
  {#if einzelProducts.length > 0 && (filterMode === 'alle' || filterMode === 'einzeln' || filterMode === 'niedrig' || filterMode === 'ausverkauft')}
  <div class="section-divider">
    <span class="section-label">📦 Einzelartikel ({einzelProducts.length})</span>
    <div class="section-line"></div>
  </div>
  {#each einzelProducts as p (p.id)}
    {@const lager = getProductStock(p)}
    {@const lagerColor = getStockColor(lager)}
    {@const statusLabel = getStockLabel(lager)}
    {@const bild = getProductImage(p)}
    {@const edit = getInlineEdit(p)}
    <div class="product-card">
      {#if bild}
        <img src={bild} alt="" class="product-image" onerror={(e) => e.target.style.display = 'none'} />
      {/if}
      <div class="product-header">
        <div class="product-name">{p.name || '—'}</div>
        <span class="stock-badge" style="color: {lagerColor}">{statusLabel}</span>
      </div>
      <div class="product-meta">eBay: {p.ebay_artikel_id || '—'}</div>

      <div class="product-stats">
        <div class="stat-box">
          <div class="stat-label">PREIS</div>
          <div class="stat-value">{p.preis ? parseFloat(p.preis).toFixed(2) + ' €' : '—'}</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">LAGERBESTAND</div>
          <div class="stat-value" style="color: {lagerColor}">{lager} St.</div>
        </div>
      </div>

      <div class="product-actions">
        {#if inlineEdits[p.id]}
        <div class="inline-edit-grid">
          <div class="inline-field">
            <label class="inline-label">Lager neu</label>
            <input type="number" class="inline-input" bind:value={inlineEdits[p.id].lager} min="0" />
          </div>
          <div class="inline-field">
            <label class="inline-label ebay-label">eBay-Menge</label>
            <input type="number" class="inline-input ebay-input" bind:value={inlineEdits[p.id].ebayMenge} min="0" title="Anzahl die auf eBay angezeigt wird" />
          </div>
          <div class="inline-field">
            <label class="inline-label">Preis (€)</label>
            <input type="number" class="inline-input" bind:value={inlineEdits[p.id].preis} min="0" step="0.01" />
          </div>
          <button class="btn-save-inline" onclick={() => saveBestand(p.id)} title="Speichern">💾</button>
        </div>
        {/if}
      </div>
    </div>
  {/each}
  {/if}

  <!-- Varianten-Artikel Section -->
  {#if variantenProducts.length > 0 && (filterMode === 'alle' || filterMode === 'varianten' || filterMode === 'niedrig' || filterMode === 'ausverkauft')}
  <div class="section-divider section-varianten">
    <span class="section-label varianten-label">📋 Varianten-Artikel ({variantenProducts.length})</span>
    <div class="section-line varianten-line"></div>
  </div>
  {#each variantenProducts as p (p.id)}
    {@const lager = getProductStock(p)}
    {@const lagerColor = getStockColor(lager)}
    {@const statusLabel = getStockLabel(lager)}
    {@const bild = getProductImage(p)}
    <div class="product-card">
      {#if bild}
        <img src={bild} alt="" class="product-image" onerror={(e) => e.target.style.display = 'none'} />
      {/if}
      <div class="product-header">
        <div class="product-name">{p.name || '—'}</div>
        <span class="stock-badge" style="color: {lagerColor}">{statusLabel}</span>
      </div>
      <div class="product-meta">eBay: {p.ebay_artikel_id || '—'}</div>

      <div class="product-stats">
        <div class="stat-box">
          <div class="stat-label">PREIS</div>
          <div class="stat-value">{p.preis ? parseFloat(p.preis).toFixed(2) + ' €' : '—'}</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">LAGERBESTAND</div>
          <div class="stat-value" style="color: {lagerColor}">{lager} St.</div>
        </div>
      </div>

      <div class="product-actions">
        <button class="btn-varianten" onclick={() => openVariantenModal(p.id)}>
          📋 {p.varianten.length} Varianten bearbeiten
        </button>
      </div>
    </div>
  {/each}
  {/if}
</div>
{/if}


<!-- ═══════════════════════════════════════════════════════ -->
<!-- PRODUCT MODAL -->
{#if showProductModal}
<div class="modal-overlay">
  <div class="modal">
    <div class="modal-title">{editProduct ? 'Produkt bearbeiten' : 'Neues Produkt'}</div>
    <div class="modal-grid">
      <div class="modal-field full">
        <label>Produktname</label>
        <input type="text" bind:value={productForm.name} placeholder="z.B. VETOM 1.1 Kapseln" />
      </div>
      <div class="modal-field">
        <label>Artikelnummer</label>
        <input type="text" bind:value={productForm.artikelnummer} placeholder="VETOM-1.1" />
      </div>
      <div class="modal-field">
        <label>eBay Artikel-ID</label>
        <input type="text" bind:value={productForm.ebay_artikel_id} placeholder="196684822091" />
      </div>
      <div class="modal-field">
        <label>Preis (€)</label>
        <input type="number" bind:value={productForm.preis} placeholder="19.90" step="0.01" />
      </div>
      <div class="modal-field">
        <label>Lagerbestand</label>
        <input type="number" bind:value={productForm.lagerbestand} placeholder="10" />
      </div>
      <div class="modal-field">
        <label>Versanddauer</label>
        <input type="text" bind:value={productForm.versanddauer} placeholder="1-3 Werktage" />
      </div>
      <div class="modal-field full">
        <label>Bild-URL</label>
        <div class="bild-input-row">
          <input type="text" bind:value={productForm.bild_url} placeholder="https://i.ebayimg.com/..." />
          {#if productForm.bild_url}
            <img src={productForm.bild_url} alt="" class="bild-preview" onerror={(e) => e.target.style.display = 'none'} />
          {/if}
        </div>
      </div>
      <div class="modal-field full">
        <label>Beschreibung</label>
        <input type="text" bind:value={productForm.beschreibung} placeholder="Kurze Produktbeschreibung" />
      </div>
      <div class="modal-field full">
        <label>Inhaltsstoffe / Eigenschaften</label>
        <input type="text" bind:value={productForm.inhaltsstoffe} placeholder="Bacillus subtilis, Maisstärke..." />
      </div>
      <div class="modal-field full">
        <label>Hinweise</label>
        <input type="text" bind:value={productForm.hinweise} placeholder="Lagerung, Sicherheitshinweise..." />
      </div>
    </div>
    <div class="modal-actions">
      <button class="btn btn-cancel" onclick={() => showProductModal = false}>Abbrechen</button>
      <button class="btn btn-primary" onclick={saveProduct}>💾 Speichern</button>
    </div>
  </div>
</div>
{/if}


<!-- ═══════════════════════════════════════════════════════ -->
<!-- VARIANTEN MODAL -->
{#if showVariantenModal && variantenProduct}
<div class="modal-overlay" onclick={(e) => { if (e.target === e.currentTarget) showVariantenModal = false; }}>
  <div class="modal modal-wide">
    <div class="varianten-modal-header">
      <div class="varianten-modal-info">
        {#if getProductImage(variantenProduct)}
          <img src={getProductImage(variantenProduct)} alt="" class="varianten-modal-bild" onerror={(e) => e.target.style.display = 'none'} />
        {/if}
        <div>
          <div class="modal-title" style="margin-bottom: 4px;">{variantenProduct.name || 'Varianten'}</div>
          <div class="varianten-modal-sub">eBay: {variantenProduct.ebay_artikel_id || '—'} · {variantenProduct.varianten?.length || 0} Varianten</div>
          <div class="varianten-hint">💡 eBay-Menge = wie viel auf eBay angezeigt wird (nicht echter Lagerbestand)</div>
        </div>
      </div>
      <button class="btn-close-subtle" onclick={closeVariantenModal}>✕ Schließen</button>
    </div>

    <div class="varianten-list">
      {#each (variantenProduct.varianten || []) as v (v.id)}
        {@const vLager = v.lagerbestand ?? 0}
        {@const vMin = v.min_lagerbestand ?? 3}
        {@const vColor = vLager === 0 ? 'var(--danger, #ef4444)' : vLager <= vMin ? 'var(--warning, #f59e0b)' : 'var(--success, #22c55e)'}
        {@const vStatus = vLager === 0 ? '🔴' : vLager <= vMin ? '🟡' : '🟢'}
        <div class="variante-card">
          {#if v.bild_url}
            <img src={v.bild_url} alt="" class="variante-bild" onerror={(e) => e.target.style.display = 'none'} />
          {/if}
          <div class="variante-content">
            <div class="variante-header">
              <div>
                <div class="variante-name">{vStatus} {v.produktart || '—'}</div>
                {#if v.verpackungseinheit}
                  <div class="variante-pack">📦 {v.verpackungseinheit}</div>
                {/if}
              </div>
              <div class="variante-stock" style="color: {vColor}">
                {vLager} St.
                <span class="variante-stock-label">aktuell</span>
              </div>
            </div>
            <div class="variante-inputs">
              <div class="variante-field">
                <label>Lager neu</label>
                <input type="number" bind:value={variantenInputs[v.id].lager} min="0" />
              </div>
              <div class="variante-field">
                <label>eBay-Menge</label>
                <input type="number" bind:value={variantenInputs[v.id].ebayMenge} min="0" title="Anzahl die auf eBay angezeigt wird" />
              </div>
              <div class="variante-field">
                <label>Preis (€)</label>
                <input type="number" bind:value={variantenInputs[v.id].preis} min="0" step="0.01" />
              </div>
            </div>
            {@const isChanged = variantenOriginal[v.id] && (
              String(variantenInputs[v.id].lager) !== String(variantenOriginal[v.id].lager) ||
              String(variantenInputs[v.id].ebayMenge) !== String(variantenOriginal[v.id].ebayMenge) ||
              String(variantenInputs[v.id].preis) !== String(variantenOriginal[v.id].preis)
            )}
            <div class="variante-save-row">
              {#if isChanged}
                <button class="btn-variante-einzeln" onclick={() => saveEinzelneVariante(v.id)} disabled={savingVarianteId === v.id}>
                  {savingVarianteId === v.id ? '⏳' : '💾'} Speichern
                </button>
              {/if}
            </div>
          </div>
        </div>
      {/each}
    </div>

    <div class="varianten-modal-footer">
      <button class="btn btn-cancel" onclick={closeVariantenModal}>Schließen</button>
      <button class="btn btn-varianten-save" onclick={saveAlleVarianten} disabled={savingVarianten}>
        {savingVarianten ? '⏳ Speichere...' : '💾 Alle speichern'}
      </button>
    </div>
  </div>
</div>
{/if}


<!-- ═══════════════════════════════════════════════════════ -->
<!-- IMPORT MODAL -->
{#if showImportModal}
<div class="modal-overlay" onclick={(e) => { if (e.target === e.currentTarget) showImportModal = false; }}>
  <div class="modal modal-sm">
    <div class="modal-header-row">
      <div class="modal-title">📦 Von eBay importieren</div>
      <button class="btn-close-x" onclick={() => showImportModal = false}>✕</button>
    </div>
    <p class="modal-desc">
      Wähle was bei <strong>bereits vorhandenen</strong> Produkten aktualisiert werden soll.<br>
      <span class="text-success">Neue Produkte</span> werden immer vollständig importiert.
    </p>
    <div class="import-options">
      <label class="import-option">
        <input type="checkbox" bind:checked={importOptions.nur_neu} />
        <span>Nur neue Produkte importieren <span class="text-muted">(vorhandene nicht anfassen)</span></span>
      </label>
      {#if !importOptions.nur_neu}
      <div class="import-sub-options">
        <div class="import-sub-label">Bei vorhandenen Produkten aktualisieren:</div>
        <label class="import-option"><input type="checkbox" bind:checked={importOptions.update_lager} /><span>Lagerbestand <span class="text-muted">(von eBay übernehmen)</span></span></label>
        <label class="import-option"><input type="checkbox" bind:checked={importOptions.update_preis} /><span>Preis <span class="text-muted">(von eBay übernehmen)</span></span></label>
        <label class="import-option"><input type="checkbox" bind:checked={importOptions.update_name} /><span>Produktname <span class="text-muted">(von eBay übernehmen)</span></span></label>
        <label class="import-option"><input type="checkbox" bind:checked={importOptions.update_bild} /><span>Bild-URL <span class="text-muted">(von eBay übernehmen)</span></span></label>
      </div>
      {/if}
    </div>
    <div class="modal-actions">
      <button class="btn btn-cancel" onclick={() => showImportModal = false}>Abbrechen</button>
      <button class="btn btn-primary" onclick={startProduktImport}>📦 Importieren</button>
    </div>
  </div>
</div>
{/if}


<!-- ═══════════════════════════════════════════════════════ -->
<!-- VARIANTEN IMPORT MODAL -->
{#if showVariantenImportModal}
<div class="modal-overlay" onclick={(e) => { if (e.target === e.currentTarget) showVariantenImportModal = false; }}>
  <div class="modal modal-sm">
    <div class="modal-header-row">
      <div class="modal-title">🔄 Varianten laden</div>
      <button class="btn-close-x" onclick={() => showVariantenImportModal = false}>✕</button>
    </div>
    <p class="modal-desc">
      Wähle was bei <strong>bereits vorhandenen</strong> Varianten aktualisiert werden soll.<br>
      <span class="text-success">Neue Varianten</span> werden immer vollständig importiert.
    </p>
    <div class="import-options">
      <label class="import-option">
        <input type="checkbox" bind:checked={variantenImportOptions.nur_neu} />
        <span>Nur neue Varianten importieren <span class="text-muted">(vorhandene nicht anfassen)</span></span>
      </label>
      {#if !variantenImportOptions.nur_neu}
      <div class="import-sub-options">
        <div class="import-sub-label">Bei vorhandenen Varianten aktualisieren:</div>
        <label class="import-option"><input type="checkbox" bind:checked={variantenImportOptions.update_lager} /><span>Lagerbestand</span></label>
        <label class="import-option"><input type="checkbox" bind:checked={variantenImportOptions.update_preis} /><span>Preis</span></label>
        <label class="import-option"><input type="checkbox" bind:checked={variantenImportOptions.update_bild} /><span>Bild-URL</span></label>
      </div>
      {/if}
    </div>
    <div class="modal-actions">
      <button class="btn btn-cancel" onclick={() => showVariantenImportModal = false}>Abbrechen</button>
      <button class="btn btn-success" onclick={startVariantenImport}>🔄 Importieren</button>
    </div>
  </div>
</div>
{/if}


<!-- ═══════════════════════════════════════════════════════ -->
<!-- CSV EXPORT MODAL -->
{#if showExportModal}
<div class="modal-overlay" onclick={(e) => { if (e.target === e.currentTarget) showExportModal = false; }}>
  <div class="modal modal-export">
    <div class="modal-title" style="margin-bottom: 16px;">⬇️ Lagerbestand exportieren</div>

    <!-- Format -->
    <div class="export-section">
      <div class="export-section-label">Format</div>
      <div class="export-format-options">
        <label class="export-format-option" class:selected={exportFormat === 'raw'}>
          <input type="radio" name="export-format" value="raw" bind:group={exportFormat} />
          <div><div class="format-title">Alle Produkte</div><div class="format-desc">Kompletter Bestand als CSV</div></div>
        </label>
        <label class="export-format-option" class:selected={exportFormat === 'overview'}>
          <input type="radio" name="export-format" value="overview" bind:group={exportFormat} />
          <div><div class="format-title">Produkte auswählen</div><div class="format-desc">Gruppiert · Duo/TrioPack-Spalten</div></div>
        </label>
      </div>
      {#if exportFormat === 'overview'}
      <div class="export-hint">💡 Gleiche Artikel zusammenführen: Produkt auswählen → im Feld "Zusammenführen als" den gleichen Namen eingeben</div>
      {/if}
    </div>

    <!-- Produktfilter nur bei "Produkte auswählen" zeigen -->
    {#if exportFormat === 'overview'}
    <!-- Search -->
    <div class="export-section">
      <div class="export-section-header">
        <div class="export-section-label">Produkte filtern <span class="text-muted text-normal">(leer = alle exportieren)</span></div>
        <span class="export-count-badge">{exportSelected.size ? exportSelected.size + ' ausgewählt' : 'alle'}</span>
      </div>
      <div class="search-bar compact">
        <span class="search-icon">🔍</span>
        <input type="text" class="search-input" placeholder="Produkt suchen..." bind:value={exportSearchQuery} />
      </div>
    </div>

    <!-- Search Results -->
    {#if exportSearchResults.length > 0}
    <div class="export-results">
      {#each exportSearchResults as p}
        {@const id = String(p.ebay_artikel_id || '')}
        {@const isAdded = exportSelected.has(id)}
        {@const cleanName = (p.name || '').replace(/\s*\[.*?\]\s*/g, '').trim()}
        {@const varCount = Array.isArray(p.varianten) ? p.varianten.length : 0}
        <button class="export-result-item" class:selected={isAdded} onclick={() => toggleExportProduct(id)}>
          <div class="export-result-info">
            <div class="export-result-name">{cleanName.length > 52 ? cleanName.substring(0, 52) + '…' : cleanName}</div>
            <div class="export-result-meta">ID: {id} · {varCount} Varianten</div>
          </div>
          {#if isAdded}
            <span class="export-result-badge added">✓</span>
          {:else}
            <span class="export-result-badge add">+</span>
          {/if}
        </button>
      {/each}
    </div>
    {/if}

    <!-- Selected Products -->
    <div class="export-section-label" style="margin-top: 10px;">Ausgewählte Produkte</div>
    <div class="export-selected-list">
      {#if exportSelected.size === 0}
        <div class="export-empty">Noch keine Produkte ausgewählt – alle werden exportiert</div>
      {:else}
        {#each [...exportSelected] as id}
          {@const p = allProdukte.find(x => String(x.ebay_artikel_id) === String(id))}
          {@const cleanName = ((p && p.name) || id).replace(/\s*\[.*?\]\s*/g, '').trim()}
          <div class="export-selected-item">
            <div class="export-selected-info">
              <div class="export-selected-name" title={cleanName}>
                {cleanName.length > 48 ? cleanName.substring(0, 48) + '…' : cleanName}
                <span class="text-muted">({id})</span>
              </div>
              {#if exportFormat === 'overview'}
              <div class="export-merge-row">
                <span class="export-merge-label">Zusammenführen als:</span>
                <input type="text" class="export-merge-input" placeholder="leer = eigener Name"
                  value={exportMergeMap[id] || ''}
                  oninput={(e) => { exportMergeMap = { ...exportMergeMap, [id]: e.target.value }; }} />
              </div>
              {/if}
            </div>
            <button class="btn-remove" onclick={() => removeExportProduct(id)}>✕</button>
          </div>
        {/each}
      {/if}
    </div>
    {/if}<!-- Ende Produktfilter -->

    <div class="modal-actions" style="border-top: 1px solid var(--border); padding-top: 14px; margin-top: 16px;">
      <button class="btn btn-cancel" onclick={() => showExportModal = false}>Abbrechen</button>
      <button class="btn btn-primary" onclick={doExportCSV}>⬇️ Exportieren</button>
    </div>
  </div>
</div>
{/if}


<!-- ═══════════════════════════════════════════════════════ -->
<!-- SKU GENERATOR MODAL -->
{#if showSkuModal}
<div class="modal-overlay" onclick={(e) => { if (e.target === e.currentTarget) showSkuModal = false; }}>
  <div class="modal modal-sku">
    <div class="modal-title">🏷️ SKUs automatisch generieren</div>
    <p class="modal-desc">
      Varianten ohne eBay-SKU bekommen automatisch eine SKU zugewiesen. Format: <strong>Produktname-Variante</strong> (z.B. "Osram-9Watt").
    </p>

    {#if generatedSkus.length === 0}
      <div class="sku-all-done">✅ Alle Varianten haben bereits eine SKU!</div>
    {:else}
      <div class="sku-list">
        {#each generatedSkus as item, i}
          <div class="sku-item">
            <div class="sku-item-info">
              <div class="sku-item-name">{item.produkt_name}</div>
              <div class="sku-item-variant">Variante: {item.variante_name}</div>
            </div>
            <input type="text" class="sku-input" bind:value={generatedSkus[i].sku} />
          </div>
        {/each}
      </div>
    {/if}

    {#if skuStatus}
      <div class="sku-status">{skuStatus}</div>
    {/if}

    <div class="modal-actions">
      <button class="btn btn-cancel" onclick={() => showSkuModal = false}>Schließen</button>
      {#if generatedSkus.length > 0}
        <button class="btn btn-sku-save" onclick={saveGeneratedSkus} disabled={skuSaving}>
          {skuSaving ? '⏳ Speichere...' : '💾 Alle SKUs speichern'}
        </button>
      {/if}
    </div>
  </div>
</div>
{/if}



<!-- ═══════════════════════════════════════════════════════ LAGER-ABGLEICH MODAL -->
{#if showAbgleichModal}
  <div class="modal-overlay" onclick={(e) => { if (e.target === e.currentTarget && !abgleichLoading) showAbgleichModal = false; }}>
    <div class="modal-box" style="max-width:560px;">
      <div class="modal-title">⚖️ Lagerbestand abgleichen</div>

      {#if !abgleichResult}
        <div style="background:var(--surface2);border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:20px;font-size:13px;line-height:1.7;color:var(--text2);">
          <div style="font-weight:700;color:var(--text);margin-bottom:6px;">Was passiert hier?</div>
          Prüft alle Bestellungen wo der Lagerbestand noch <strong>nicht abgezogen</strong> wurde (z.B. nach n8n-Störung) und gleicht automatisch ab.
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" onclick={() => showAbgleichModal = false}>Abbrechen</button>
          <button class="btn btn-primary" style="background:#0891b2;" onclick={doLagerAbgleich} disabled={abgleichLoading}>
            {#if abgleichLoading}Gleiche ab...{:else}⚖️ Jetzt abgleichen{/if}
          </button>
        </div>
      {:else if abgleichResult.success}
        <div style="padding:14px 16px;background:#f0fdf4;border:1px solid #86efac;border-radius:10px;margin-bottom:16px;">
          <span style="font-weight:700;color:#16a34a;">{abgleichResult.message}</span>
        </div>
        {#if abgleichResult.produkte && abgleichResult.produkte.length > 0}
          <div style="display:flex;flex-direction:column;gap:8px;max-height:320px;overflow-y:auto;margin-bottom:16px;">
            {#each abgleichResult.produkte as p}
              <div style="background:var(--surface2);border:1px solid var(--border);border-radius:10px;padding:12px 14px;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                  <span style="font-size:13px;font-weight:600;">{p.produkt_name}</span>
                  {#if p.typ === 'auto_var'}
                    <span style="background:#eff6ff;color:#2563eb;font-size:10px;font-weight:700;padding:2px 8px;border-radius:6px;">Variante</span>
                  {:else}
                    <span style="background:#f0fdf4;color:#16a34a;font-size:10px;font-weight:700;padding:2px 8px;border-radius:6px;">✅ OK</span>
                  {/if}
                </div>
                <div style="font-size:12px;color:var(--text2);margin-top:4px;">
                  Vorher: {p.lager_vorher} → Verkauft: -{p.verkauft} → Nachher: {p.lager_nachher}
                  {#if p.variante_name}<br/>Variante: {p.variante_name}{/if}
                </div>
              </div>
            {/each}
          </div>
        {:else}
          <div style="text-align:center;padding:24px;color:var(--text3);font-size:13px;">
            Alle Bestellungen waren bereits abgeglichen 👍
          </div>
        {/if}
        <div class="modal-actions">
          <button class="btn btn-secondary" onclick={() => showAbgleichModal = false}>Schließen</button>
        </div>
      {:else}
        <div style="padding:14px;background:#fef2f2;border:1px solid #fca5a5;border-radius:10px;color:#dc2626;font-size:13px;margin-bottom:16px;">
          ❌ {abgleichResult.message || 'Fehler'}
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" onclick={() => showAbgleichModal = false}>Schließen</button>
        </div>
      {/if}
    </div>
  </div>
{/if}

<style>
  /* ─── Page Header ───────────────────────────────── */
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
    margin-bottom: 24px;
    flex-wrap: wrap;
  }
  .page-title {
    font-size: 22px;
    font-weight: 800;
    color: var(--text);
    margin: 0;
  }
  .page-subtitle {
    font-size: 13px;
    color: var(--text2);
    margin: 4px 0 0 0;
  }
  .page-header-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  /* ─── Buttons ───────────────────────────────────── */
  .btn {
    border: none;
    border-radius: 10px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.15s;
  }
  .btn-primary { background: var(--primary); color: white; }
  .btn-primary:hover { background: var(--primary-dark); }
  .btn-cancel { background: var(--surface2); border: 1.5px solid var(--border); color: var(--text2); }
  .btn-cancel:hover { border-color: var(--text3); }
  .btn-success { background: #22c55e; color: white; }
  .btn-success:hover { background: #16a34a; }
  .btn-secondary {
    background: var(--surface);
    border: 1.5px solid var(--border);
    color: var(--text2);
  }
  .btn-secondary:hover {
    border-color: var(--primary);
    color: var(--primary);
    background: var(--primary-light, rgba(55, 119, 207, 0.05));
  }

  /* ─── Stats Bar ─────────────────────────────────── */
  .stats-bar {
    display: flex;
    gap: 8px;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }
  .stat-chip {
    background: var(--surface);
    border: 1.5px solid var(--border);
    border-radius: 20px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
    color: var(--text2);
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
  }
  .stat-chip:hover { border-color: var(--primary); color: var(--text); }
  .stat-chip.active { background: var(--surface2); color: var(--text); border-color: var(--text3); font-weight: 700; }
  .stat-count {
    background: var(--surface2);
    padding: 1px 7px;
    border-radius: 10px;
    font-size: 11px;
    margin-left: 4px;
  }
  .stat-chip.active .stat-count { background: var(--primary); color: white; }

  /* ─── Search ────────────────────────────────────── */
  .search-bar {
    position: relative;
    margin-bottom: 20px;
  }
  .search-bar.compact { margin-bottom: 10px; }
  .search-icon {
    position: absolute;
    left: 12px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 14px;
    pointer-events: none;
  }
  .search-input {
    width: 100%;
    padding: 10px 36px 10px 36px;
    border: 1.5px solid var(--border);
    border-radius: 10px;
    background: var(--surface);
    color: var(--text);
    font-family: inherit;
    font-size: 13px;
    outline: none;
    transition: border-color 0.2s;
    box-sizing: border-box;
  }
  .search-input:focus { border-color: var(--primary); }
  .search-clear {
    position: absolute;
    right: 10px;
    top: 50%;
    transform: translateY(-50%);
    background: none;
    border: none;
    font-size: 14px;
    color: var(--text3);
    cursor: pointer;
  }

  /* ─── Grid ──────────────────────────────────────── */
  .products-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 20px;
    align-items: start;
  }

  /* ─── Section Dividers ──────────────────────────── */
  .section-divider {
    grid-column: 1 / -1;
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 4px;
  }
  .section-label {
    font-size: 13px;
    font-weight: 700;
    color: var(--text2);
    letter-spacing: 1px;
    text-transform: uppercase;
    white-space: nowrap;
  }
  .section-line {
    flex: 1;
    height: 1px;
    background: var(--border);
  }
  .varianten-label { color: #7c3aed; }
  .varianten-line { background: #7c3aed; opacity: 0.3; }

  /* ─── Product Card ──────────────────────────────── */
  .product-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    display: flex;
    flex-direction: column;
    transition: all 0.2s;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    position: relative;
    overflow: hidden;
  }
  .product-card:hover {
    border-color: var(--primary);
    transform: translateY(-2px);
    box-shadow: 0 4px 6px rgba(0,0,0,0.07);
  }
  .product-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: var(--primary);
    transform: scaleX(0);
    transition: transform 0.2s;
  }
  .product-card:hover::before { transform: scaleX(1); }

  .product-image {
    width: 100%;
    height: 120px;
    object-fit: contain;
    border-radius: 8px;
    background: var(--surface2);
    margin-bottom: 12px;
    border: 1px solid var(--border);
  }
  .product-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 8px;
  }
  .product-name {
    font-size: 13px;
    font-weight: 600;
    color: var(--text);
    line-height: 1.4;
    flex: 1;
    padding-right: 8px;
  }
  .stock-badge {
    font-size: 11px;
    font-weight: 600;
    white-space: nowrap;
  }
  .product-meta {
    font-size: 11px;
    color: var(--text3);
    margin-bottom: 12px;
  }

  .product-stats {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 14px;
  }
  .stat-box {
    background: var(--surface2);
    border-radius: 8px;
    padding: 10px;
    text-align: center;
  }
  .stat-label {
    font-size: 10px;
    color: var(--text3);
    margin-bottom: 4px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .stat-value {
    font-size: 14px;
    font-weight: 700;
    color: var(--text);
  }

  .product-actions { margin-top: auto; padding-top: 12px; }

  /* ─── Inline Edit ───────────────────────────────── */
  .inline-edit-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr auto;
    gap: 6px;
    align-items: end;
  }
  .inline-field { display: flex; flex-direction: column; }
  .inline-label {
    font-size: 9px;
    color: var(--text3);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 4px;
  }
  .inline-label.ebay-label { color: #7c3aed; }
  .inline-input {
    width: 100%;
    padding: 8px;
    border: 1.5px solid var(--border);
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    text-align: center;
    background: var(--surface2);
    color: var(--text);
    outline: none;
    font-family: inherit;
    box-sizing: border-box;
  }
  .inline-input:focus { border-color: var(--primary); }
  .inline-input.ebay-input {
    border-color: #a78bfa;
    color: #7c3aed;
  }
  .btn-save-inline {
    background: #22c55e;
    border: none;
    border-radius: 8px;
    padding: 8px 10px;
    color: white;
    font-size: 16px;
    cursor: pointer;
    line-height: 1;
  }
  .btn-save-inline:hover { background: #16a34a; }

  /* Varianten Button on Card */
  .product-actions .btn-varianten {
    width: 100%;
    background: #7c3aed;
    border: none;
    border-radius: 8px;
    padding: 10px;
    color: white;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    font-family: inherit;
  }
  .product-actions .btn-varianten:hover { background: #6d28d9; }

  /* ─── Empty State ───────────────────────────────── */
  .empty-state {
    text-align: center;
    padding: 60px 20px;
    color: var(--text3);
  }
  .empty-icon { font-size: 48px; margin-bottom: 12px; }
  .spinner {
    width: 24px; height: 24px;
    border: 3px solid var(--border);
    border-top-color: var(--primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin: 0 auto 12px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ─── Modal Base ────────────────────────────────── */
  .modal-overlay {
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: rgba(0,0,0,0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
  }
  .modal {
    background: var(--surface);
    border-radius: 16px;
    padding: 28px;
    width: 520px;
    max-width: 95vw;
    max-height: 90vh;
    overflow-y: auto;
    box-shadow: 0 20px 60px rgba(0,0,0,0.2);
  }
  .modal-sm { max-width: 420px; }
  .modal-wide { width: 660px; }
  .modal-export { max-width: 600px; display: flex; flex-direction: column; }
  .modal-sku { max-width: 580px; }
  .modal-title {
    font-size: 18px;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 16px;
  }
  .modal-desc {
    font-size: 13px;
    color: var(--text2);
    margin-bottom: 18px;
    line-height: 1.6;
  }
  .modal-header-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }
  .modal-header-row .modal-title { margin-bottom: 0; }
  .btn-close-x {
    background: none;
    border: none;
    font-size: 18px;
    color: var(--text3);
    cursor: pointer;
    padding: 4px;
  }
  .modal-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 20px;
  }
  .modal-field { display: flex; flex-direction: column; }
  .modal-field.full { grid-column: 1 / -1; }
  .modal-field label {
    font-size: 12px;
    font-weight: 600;
    color: var(--text2);
    margin-bottom: 6px;
  }
  .modal-field input {
    padding: 9px 12px;
    border: 1.5px solid var(--border);
    border-radius: 8px;
    background: var(--surface2);
    color: var(--text);
    font-family: inherit;
    font-size: 13px;
    outline: none;
    box-sizing: border-box;
  }
  .modal-field input:focus { border-color: var(--primary); }
  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 8px;
  }
  .bild-input-row { display: flex; gap: 8px; align-items: center; }
  .bild-input-row input { flex: 1; }
  .bild-preview {
    width: 48px; height: 48px;
    object-fit: contain;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: var(--surface2);
  }

  /* ─── Varianten Modal ───────────────────────────── */
  .varianten-modal-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 8px;
    gap: 16px;
  }
  .varianten-modal-info {
    display: flex;
    gap: 14px;
    align-items: center;
    flex: 1;
    min-width: 0;
  }
  .varianten-modal-bild {
    width: 64px; height: 64px;
    object-fit: contain;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: var(--surface2);
    flex-shrink: 0;
  }
  .varianten-modal-sub {
    font-size: 12px;
    color: var(--text3);
  }
  .varianten-hint {
    font-size: 11px;
    color: #f59e0b;
    margin-top: 3px;
  }
  .btn-close-subtle {
    background: var(--surface2);
    border: 1.5px solid var(--border);
    border-radius: 8px;
    padding: 8px 14px;
    cursor: pointer;
    font-size: 13px;
    color: var(--text2);
    flex-shrink: 0;
    font-family: inherit;
  }
  .varianten-list {
    margin-top: 16px;
    max-height: 60vh;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .variante-card {
    background: var(--surface2);
    border: 1.5px solid var(--border);
    border-radius: 12px;
    padding: 14px;
    display: flex;
    gap: 12px;
  }
  .variante-bild {
    width: 72px; height: 72px;
    object-fit: contain;
    border-radius: 8px;
    background: var(--surface);
    border: 1px solid var(--border);
    flex-shrink: 0;
    align-self: center;
  }
  .variante-content { flex: 1; min-width: 0; }
  .variante-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 10px;
  }
  .variante-name { font-size: 13px; font-weight: 700; color: var(--text); }
  .variante-pack { font-size: 11px; color: var(--text3); margin-top: 2px; }
  .variante-stock { font-size: 12px; font-weight: 700; text-align: right; }
  .variante-stock-label { font-size: 11px; color: var(--text3); font-weight: 400; display: block; }
  .variante-inputs {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 6px;
  }
  .variante-field { display: flex; flex-direction: column; }
  .variante-field label {
    font-size: 9px;
    color: var(--text3);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 4px;
  }
  .variante-field input {
    width: 100%;
    padding: 7px 8px;
    border: 1.5px solid var(--border);
    border-radius: 7px;
    font-size: 13px;
    font-weight: 600;
    text-align: center;
    background: var(--surface);
    color: var(--text);
    outline: none;
    font-family: inherit;
    box-sizing: border-box;
  }
  .variante-field input:focus { border-color: var(--primary); }
  .varianten-modal-footer {
    margin-top: 20px;
    padding-top: 16px;
    border-top: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .btn-varianten-save {
    background: #7c3aed;
    border: none;
    border-radius: 10px;
    padding: 10px 24px;
    color: white;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    font-family: inherit;
  }
  .btn-varianten-save:hover { background: #6d28d9; }
  .btn-varianten-save:disabled { opacity: 0.6; cursor: not-allowed; }

  /* ─── Import Options ────────────────────────────── */
  .import-options {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 20px;
  }
  .import-option {
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
  }
  .import-option input[type="checkbox"] {
    width: 16px; height: 16px;
    accent-color: var(--primary);
  }
  .import-sub-options {
    border-top: 1px solid var(--border);
    padding-top: 12px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .import-sub-label {
    font-size: 12px;
    color: var(--text3);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .text-success { color: #22c55e; font-weight: 600; }
  .text-muted { color: var(--text3); font-weight: 400; font-size: 12px; }
  .text-normal { text-transform: none; letter-spacing: 0; }

  /* ─── Export Modal ──────────────────────────────── */
  .export-section { margin-bottom: 16px; }
  .export-section-label {
    font-size: 11px;
    font-weight: 700;
    color: var(--text2);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
  }
  .export-section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
  }
  .export-count-badge {
    font-size: 11px;
    background: var(--primary);
    color: white;
    padding: 2px 9px;
    border-radius: 10px;
  }
  .export-format-options { display: flex; gap: 8px; }
  .export-format-option {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
    padding: 10px 13px;
    border: 1.5px solid var(--border);
    border-radius: 9px;
    transition: all 0.15s;
  }
  .export-format-option.selected { border-color: var(--primary); background: var(--primary-light); }
  .export-format-option input { accent-color: var(--primary); }
  .format-title { font-size: 13px; font-weight: 600; }
  .format-desc { font-size: 11px; color: var(--text3); }
  .format-badge {
    font-size: 10px;
    background: var(--primary);
    color: white;
    padding: 1px 6px;
    border-radius: 6px;
    margin-left: 3px;
  }
  .export-hint {
    margin-top: 8px;
    font-size: 11px;
    color: var(--text3);
    background: var(--surface2);
    border-radius: 7px;
    padding: 7px 10px;
  }
  .export-results {
    display: flex;
    flex-direction: column;
    gap: 4px;
    max-height: 160px;
    overflow-y: auto;
    margin-bottom: 10px;
  }
  .export-result-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 11px;
    background: var(--surface2);
    border: 1.5px solid var(--border);
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.15s;
    width: 100%;
    text-align: left;
    font-family: inherit;
  }
  .export-result-item:hover { border-color: var(--primary); }
  .export-result-item.selected { border-color: #22c55e; }
  .export-result-info { flex: 1; min-width: 0; }
  .export-result-name { font-size: 12px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--text); }
  .export-result-meta { font-size: 11px; color: var(--text3); margin-top: 1px; }
  .export-result-badge { font-size: 12px; flex-shrink: 0; }
  .export-result-badge.added { background: #22c55e; color: white; padding: 2px 9px; border-radius: 6px; font-weight: 700; }
  .export-result-badge.add { font-size: 18px; color: var(--primary); }

  .export-selected-list {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 5px;
    min-height: 60px;
    max-height: 220px;
  }
  .export-empty { font-size: 12px; color: var(--text3); text-align: center; padding: 14px; }
  .export-selected-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 10px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
  }
  .export-selected-info { flex: 1; min-width: 0; }
  .export-selected-name { font-size: 12px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--text); }
  .export-merge-row { display: flex; align-items: center; gap: 6px; margin-top: 5px; }
  .export-merge-label { font-size: 10px; color: var(--text3); flex-shrink: 0; }
  .export-merge-input {
    flex: 1;
    padding: 3px 7px;
    border: 1px solid var(--border);
    border-radius: 5px;
    font-size: 11px;
    background: var(--surface);
    color: var(--primary);
    font-weight: 600;
    outline: none;
    font-family: inherit;
  }
  .btn-remove {
    background: none;
    border: none;
    color: #ef4444;
    cursor: pointer;
    font-size: 15px;
    flex-shrink: 0;
    padding: 0 2px;
  }

  /* ─── SKU Generator ─────────────────────────────── */
  .sku-all-done {
    text-align: center;
    padding: 20px;
    color: #22c55e;
    font-weight: 600;
  }
  .sku-list {
    max-height: 50vh;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 20px;
  }
  .sku-item {
    background: var(--surface2);
    border: 1.5px solid var(--border);
    border-radius: 10px;
    padding: 12px 14px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    align-items: center;
  }
  .sku-item-name { font-size: 12px; font-weight: 700; color: var(--text); }
  .sku-item-variant { font-size: 11px; color: var(--text3); }
  .sku-input {
    background: var(--surface);
    border: 1.5px solid #a78bfa;
    border-radius: 7px;
    padding: 7px 10px;
    font-size: 13px;
    font-weight: 600;
    color: #7c3aed;
    outline: none;
    width: 100%;
    font-family: inherit;
    box-sizing: border-box;
  }
  .sku-status {
    font-size: 13px;
    color: var(--text2);
    min-height: 20px;
    margin-bottom: 8px;
  }
  .btn-sku-save {
    background: #7c3aed;
    border: none;
    border-radius: 10px;
    padding: 10px 24px;
    color: white;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    font-family: inherit;
  }
  .btn-sku-save:disabled { opacity: 0.6; cursor: not-allowed; }

  /* ── Abgleich Button ─────────────────────────────────── */
  .btn-abgleich {
    background: var(--surface) !important;
    border: 1.5px solid #0891b2 !important;
    color: #0891b2 !important;
  }
  .btn-abgleich:hover {
    background: rgba(8,145,178,0.08) !important;
  }
</style>
