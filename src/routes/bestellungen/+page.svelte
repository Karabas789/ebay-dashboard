<script>
  import { onMount } from 'svelte';
  import { currentUser } from '$lib/stores.js';
  import { apiCall } from '$lib/api.js';

  let allOrders = $state([]);
  let allProdukte = $state([]);
  let allRechnungen = $state([]);
  let ordersFilter = $state('alle');
  let searchQuery = $state('');
  let loading = $state(true);
  let selectedOrderIds = $state(new Set());

  let showTrackingModal = $state(false);
  let trackingOrderId = $state(null);
  let trackingOrderEbayId = $state('');
  let trackingCarrier = $state('DHL Germany');
  let trackingNumber = $state('');
  let trackingSaving = $state(false);

  let showMsgModal = $state(false);
  let orderMessageBuyer = $state(null);
  let orderMessageBuyerName = $state('');
  let msgSubject = $state('');
  let msgText = $state('');
  let msgSending = $state(false);

  let showArchiveConfirm = $state(false);
  let archiveConfirmAction = $state('archive');
  let archiveWorking = $state(false);

  let showDetailModal = $state(false);
  let detailOrder = $state(null);

  let eRechnungDropdownOpen = $state(false);
  let eRechnungWorking = $state(false);
  let rechnungWorking = $state(false);

  // ── Gruppierung: allOrders-Zeilen → gruppierte Bestellungen ──
  let groupedOrders = $derived.by(() => {
    const map = new Map();
    for (const row of allOrders) {
      const key = String(row.order_id);
      if (!map.has(key)) {
        map.set(key, {
          order_id: row.order_id,
          id: row.id,
          buyer_name: row.buyer_name,
          buyer_username: row.buyer_username,
          buyer_email: row.buyer_email,
          buyer_strasse: row.buyer_strasse,
          buyer_plz: row.buyer_plz,
          buyer_ort: row.buyer_ort,
          buyer_land: row.buyer_land,
          buyer_telefon: row.buyer_telefon,
          bestelldatum: row.bestelldatum,
          erstellt_am: row.erstellt_am,
          status: row.status,
          archiviert: row.archiviert,
          tracking_nummer: row.tracking_nummer,
          versanddienstleister: row.versanddienstleister,
          versendet_am: row.versendet_am,
          hat_rechnung: false,
          invoice_id: null,
          items: []
        });
      }
      const group = map.get(key);
      group.items.push({
        artikel_name: row.artikel_name,
        ebay_artikel_id: row.ebay_artikel_id,
        sold_sku: row.sold_sku,
        menge: parseInt(row.menge) || 1,
        preis: row.preis,
        gesamt: row.gesamt,
        einzelpreis: row.einzelpreis
      });
      if (row.hat_rechnung) { group.hat_rechnung = true; group.invoice_id = row.invoice_id || group.invoice_id; }
      if (row.tracking_nummer && !group.tracking_nummer) {
        group.tracking_nummer = row.tracking_nummer;
        group.versanddienstleister = row.versanddienstleister;
      }
    }
    for (const group of map.values()) {
      group.gesamt_summe = group.items.reduce((sum, item) => sum + parseFloat(item.gesamt || 0), 0);
      group.gesamt_menge = group.items.reduce((sum, item) => sum + (item.menge || 1), 0);
      group.artikel_count = group.items.length;
    }
    return Array.from(map.values());
  });

  let filteredOrders = $derived.by(() => {
    let orders = groupedOrders;
    const q = searchQuery.toLowerCase();
    if (ordersFilter === 'archiviert') {
      orders = orders.filter(o => o.archiviert || o.status === 'archiviert');
    } else {
      orders = orders.filter(o => !o.archiviert && o.status !== 'archiviert');
      if (ordersFilter !== 'alle') orders = orders.filter(o => o.status === ordersFilter);
    }
    if (q) {
      orders = orders.filter(o =>
        (o.order_id || '').toLowerCase().includes(q) ||
        (o.buyer_name || '').toLowerCase().includes(q) ||
        (o.buyer_username || '').toLowerCase().includes(q) ||
        o.items.some(item =>
          (item.artikel_name || '').toLowerCase().includes(q) ||
          (item.sold_sku || '').toLowerCase().includes(q) ||
          (item.ebay_artikel_id || '').toLowerCase().includes(q)
        )
      );
    }
    return orders;
  });

  let hasSelected = $derived(selectedOrderIds.size > 0);
  let isArchivView = $derived(ordersFilter === 'archiviert');
  let selectedCount = $derived(selectedOrderIds.size);
  let singleSelected = $derived(selectedOrderIds.size === 1);
  let countAlle = $derived(groupedOrders.filter(o => !o.archiviert && o.status !== 'archiviert').length);
  let countBezahlt = $derived(groupedOrders.filter(o => !o.archiviert && o.status !== 'archiviert' && o.status === 'bezahlt').length);
  let countVersendet = $derived(groupedOrders.filter(o => !o.archiviert && o.status !== 'archiviert' && o.status === 'versendet').length);
  let countArchiviert = $derived(groupedOrders.filter(o => o.archiviert || o.status === 'archiviert').length);
  let allFilteredSelected = $derived(
    filteredOrders.length > 0 && filteredOrders.every(o => selectedOrderIds.has(String(o.order_id)))
  );

  onMount(() => { loadBestellungen(); loadProdukte(); });

  async function loadProdukte() {
    try {
      const data = await apiCall('/produkte-laden', { user_id: $currentUser.id, ebay_username: $currentUser.ebay_user_id });
      if (data.success || Array.isArray(data.data)) allProdukte = data.data || [];
    } catch (e) { console.warn('Produkte für Bilder nicht ladbar:', e); }
  }

  async function loadBestellungen() {
    loading = true;
    try {
      const data = await apiCall('/orders-laden', { user_id: $currentUser.id, ebay_username: $currentUser.ebay_user_id });
      if (data.success) { allOrders = data.orders || []; }
      else { showToast('Fehler beim Laden der Bestellungen', 'error'); }
    } catch (e) { showToast('Verbindungsfehler: ' + e.message, 'error'); }
    finally { loading = false; }
  }

  async function doArchiveOrUnarchive() {
    archiveWorking = true;
    let ok = 0;
    const action = archiveConfirmAction === 'unarchive' ? 'unarchive' : undefined;
    for (const id of selectedOrderIds) {
      try {
        const body = { order_id: id, user_id: $currentUser.id };
        if (action) body.action = action;
        const data = await apiCall('/orders-archivieren', body);
        if (data.success) ok++;
      } catch (e) {}
    }
    selectedOrderIds = new Set();
    showArchiveConfirm = false;
    archiveWorking = false;
    const verb = archiveConfirmAction === 'unarchive' ? 'wiederhergestellt' : 'archiviert';
    showToast(`✅ ${ok} Bestellung(en) ${verb}`, 'success');
    await loadBestellungen();
  }

  async function doSaveTracking() {
    if (!trackingNumber.trim()) { showToast('Bitte Sendungsnummer eingeben', 'error'); return; }
    trackingSaving = true;
    try {
      const data = await apiCall('/order-tracking', {
        order_id: trackingOrderId, tracking_nummer: trackingNumber.trim(),
        versanddienstleister: trackingCarrier, user_id: $currentUser.id, ebay_username: $currentUser.ebay_user_id
      });
      if (data.success) {
        showToast('Gespeichert und eBay informiert', 'success');
        showTrackingModal = false;
        await loadBestellungen();
        await autoCreateRechnungAfterTracking(trackingOrderId);
      } else { showToast('Fehler beim Speichern', 'error'); }
    } catch (e) { showToast('Verbindungsfehler', 'error'); }
    finally { trackingSaving = false; }
  }

  async function doSendMessage() {
    if (!msgText.trim()) { showToast('Bitte Nachricht eingeben', 'error'); return; }
    msgSending = true;
    try {
      const data = await apiCall('/antwort-senden', {
        recipient: orderMessageBuyer, subject: msgSubject, reply: msgText,
        user_id: $currentUser.id, ebay_username: $currentUser.ebay_user_id
      });
      if (data.success) {
        showToast('✅ Nachricht gesendet!', 'success');
        showMsgModal = false; msgSubject = ''; msgText = '';
      } else { showToast('Fehler: ' + (data.message || 'Unbekannter Fehler'), 'error'); }
    } catch (e) { showToast('Verbindungsfehler', 'error'); }
    finally { msgSending = false; }
  }

  async function autoCreateRechnungAfterTracking(orderId) {
    try {
      const order = groupedOrders.find(o => String(o.order_id) === String(orderId));
      if (!order) return;
      const sd = await apiCall('/rechnung-settings', { action: 'load', user_id: $currentUser.id });
      if (!sd.success || !sd.data?.auto_rechnung) return;
      const existiert = allRechnungen.some(r => String(r.order_id) === String(orderId) && r.rechnung_typ === 'rechnung');
      if (existiert) return;
      const res = await erstelleRechnungFuerOrder(order);
      if (res?.success) {
        showToast('Rechnung ' + res.rechnung_nr + ' erstellt', 'success');
        if (sd.data?.auto_email && order.buyer_email) {
          await apiCall('/rechnung-senden', { invoice_id: res.invoice_id, user_id: $currentUser.id, to_email: order.buyer_email });
        }
      }
    } catch (e) { console.warn('Auto-Rechnung:', e); }
  }

  async function erstelleRechnungAusBestellung(order) {
    if (!order) return;
    rechnungWorking = true;
    try {
      const res = await erstelleRechnungFuerOrder(order);
      if (res?.success) {
        showToast('✅ Rechnung ' + res.rechnung_nr + ' erstellt', 'success');
        await loadBestellungen();
        const updated = groupedOrders.find(o => String(o.order_id) === String(order.order_id));
        if (updated) detailOrder = updated;
      } else { showToast('Fehler beim Erstellen der Rechnung', 'error'); }
    } catch (e) { showToast('Verbindungsfehler', 'error'); }
    finally { rechnungWorking = false; }
  }

  // ── Multi-Positionen: sendet positionen-Array an WF-RE-01 ──
  async function erstelleRechnungFuerOrder(order) {
    return await apiCall('/rechnung-erstellen', {
      user_id: $currentUser.id,
      typ: 'rechnung',
      order_id: order.order_id,
      kaeufer_name: order.buyer_name || order.buyer_username || '',
      kaeufer_username: order.buyer_username || '',
      kaeufer_strasse: order.buyer_strasse || '',
      kaeufer_plz: order.buyer_plz || '',
      kaeufer_ort: order.buyer_ort || '',
      kaeufer_land: order.buyer_land || '',
      kaeufer_email: order.buyer_email || '',
      positionen: order.items.map(item => ({
        bezeichnung: item.artikel_name || '',
        menge: item.menge || 1,
        einzelpreis: parseFloat(item.gesamt || 0) / (item.menge || 1),
        artikel_nr: item.sold_sku || '',
        ebay_artikel_id: item.ebay_artikel_id || '',
        mwst_satz: 19
      }))
    });
  }

  async function erstelleERechnungAusBestellung(order, format) {
    if (!order?.invoice_id) { showToast('Zuerst eine Rechnung erstellen', 'error'); return; }
    eRechnungWorking = true;
    eRechnungDropdownOpen = false;
    try {
      const res = await apiCall('/e-rechnung-erstellen', { user_id: $currentUser.id, invoice_id: order.invoice_id, format });
      if (res?.success) {
        showToast('✅ E-Rechnung (' + format + ') erstellt', 'success');
        if (res.download_url) { window.open(res.download_url, '_blank'); }
        else if (res.pdf_base64) { downloadBase64(res.pdf_base64, 'application/pdf', `e-rechnung-${order.invoice_id}.pdf`); }
        else if (res.xml_content) { downloadText(res.xml_content, 'application/xml', `xrechnung-${order.invoice_id}.xml`); }
      } else { showToast('Fehler: ' + (res?.message || 'E-Rechnung konnte nicht erstellt werden'), 'error'); }
    } catch (e) { showToast('Verbindungsfehler', 'error'); }
    finally { eRechnungWorking = false; }
  }

  function downloadBase64(base64, mimeType, filename) {
    const a = document.createElement('a'); a.href = `data:${mimeType};base64,${base64}`; a.download = filename; a.click();
  }
  function downloadText(text, mimeType, filename) {
    const blob = new Blob([text], { type: mimeType }); const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = filename; a.click(); URL.revokeObjectURL(url);
  }

  function getTrackingUrl(nummer, dienstleister) {
    if (!nummer) return null;
    const d = (dienstleister || '').toLowerCase();
    if (d.includes('dhl') || d.includes('deutsche post')) return `https://www.dhl.de/de/privatkunden/pakete-empfangen/verfolgen.html?idc=${nummer}`;
    if (d.includes('hermes')) return `https://www.myhermes.de/empfangen/sendungsverfolgung/#${nummer}`;
    if (d.includes('dpd')) return `https://tracking.dpd.de/status/de_DE/parcel/${nummer}`;
    if (d.includes('ups')) return `https://www.ups.com/track?tracknum=${nummer}`;
    return null;
  }

  function formatDate(dt) {
    if (!dt) return '—';
    const d = new Date(dt);
    if (isNaN(d)) return dt;
    return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' });
  }

  function statusLabel(status) {
    if (status === 'versendet') return '✅ Versendet';
    if (status === 'archiviert') return '📁 Archiv';
    if (status === 'storniert') return '❌ Storniert';
    return '💛 Bezahlt';
  }

  function toggleSelectAll(e) {
    if (e.target.checked) {
      const newSet = new Set(selectedOrderIds); filteredOrders.forEach(o => newSet.add(String(o.order_id))); selectedOrderIds = newSet;
    } else {
      const newSet = new Set(selectedOrderIds); filteredOrders.forEach(o => newSet.delete(String(o.order_id))); selectedOrderIds = newSet;
    }
  }
  function toggleOrderSelect(id, checked) {
    const newSet = new Set(selectedOrderIds);
    if (checked) newSet.add(String(id)); else newSet.delete(String(id));
    selectedOrderIds = newSet;
  }
  function openTrackingModal(orderId, carrier, tracking) {
    trackingOrderId = orderId; trackingOrderEbayId = orderId;
    trackingCarrier = carrier || 'DHL Germany'; trackingNumber = tracking || ''; showTrackingModal = true;
  }
  function openMsgModal() {
    if (selectedOrderIds.size !== 1) return;
    const id = Array.from(selectedOrderIds)[0];
    const order = groupedOrders.find(o => String(o.order_id) === String(id));
    orderMessageBuyer = order?.buyer_username || null;
    orderMessageBuyerName = order?.buyer_name || orderMessageBuyer || 'Käufer';
    msgSubject = ''; msgText = ''; showMsgModal = true;
  }
  function openDetailModal(order) { detailOrder = order; eRechnungDropdownOpen = false; showDetailModal = true; }

  function getItemImage(item) {
    const prod = allProdukte.find(p => String(p.ebay_artikel_id) === String(item.ebay_artikel_id));
    return prod?.bild_url || prod?.varianten?.find(v => v.bild_url)?.bild_url || '';
  }
  function getOrderImage(order) {
    for (const item of order.items) {
      const img = getItemImage(item);
      if (img) return img;
    }
    return '';
  }

  function varianteAusSku(sku) {
    if (!sku) return '';
    return sku.replace(/-\d{2,3}$/, '').replace(/-/g, ' ');
  }

  let _toast = $state({ msg: '', type: 'success', visible: false });
  let _toastTimer = null;
  function showToast(msg, type = 'success') {
    if (_toastTimer) clearTimeout(_toastTimer);
    _toast = { msg, type, visible: true };
    _toastTimer = setTimeout(() => { _toast = { ..._toast, visible: false }; }, 3500);
  }
</script>

<!-- ═══════════════════════════════════════════════════════ PAGE HEADER -->
<div class="page-hdr">
  <div>
    <div class="page-hdr-title">Bestellungen</div>
    <div class="page-hdr-sub">Alle eingehenden eBay-Bestellungen</div>
  </div>
  <button class="btn-refresh" onclick={() => loadBestellungen()} disabled={loading}>
    {#if loading}<span class="spinner-sm"></span>{:else}🔄{/if} Aktualisieren
  </button>
</div>

<!-- ═══════════════════════════════════════════════════════ TOOLBAR -->
<div class="orders-toolbar">
  <div class="orders-filter">
    <button class="orders-filter-btn {ordersFilter === 'alle' ? 'active' : ''}" onclick={() => { ordersFilter = 'alle'; selectedOrderIds = new Set(); }}>
      Alle {#if countAlle > 0}<span class="filter-badge">{countAlle}</span>{/if}
    </button>
    <button class="orders-filter-btn {ordersFilter === 'bezahlt' ? 'active' : ''}" onclick={() => { ordersFilter = 'bezahlt'; selectedOrderIds = new Set(); }}>
      💛 Bezahlt {#if countBezahlt > 0}<span class="filter-badge">{countBezahlt}</span>{/if}
    </button>
    <button class="orders-filter-btn {ordersFilter === 'versendet' ? 'active' : ''}" onclick={() => { ordersFilter = 'versendet'; selectedOrderIds = new Set(); }}>
      ✅ Versendet {#if countVersendet > 0}<span class="filter-badge">{countVersendet}</span>{/if}
    </button>
    <button class="orders-filter-btn {ordersFilter === 'archiviert' ? 'active' : ''}" onclick={() => { ordersFilter = 'archiviert'; selectedOrderIds = new Set(); }}>
      📁 Archiv {#if countArchiviert > 0}<span class="filter-badge">{countArchiviert}</span>{/if}
    </button>
  </div>

  <div style="display:flex;gap:8px;align-items:center;flex:1;min-width:200px;flex-wrap:wrap;">
    <div class="search-wrap" style="flex:1;max-width:300px;">
      <input class="search-box" bind:value={searchQuery} placeholder="Bestellung, Käufer, Artikel..." />
    </div>
    {#if hasSelected && !isArchivView}
      <button class="btn-action-warn" onclick={() => { archiveConfirmAction = 'archive'; showArchiveConfirm = true; }}>📁 Archivieren ({selectedCount})</button>
    {/if}
    {#if hasSelected && isArchivView}
      <button class="btn-action-primary" onclick={() => { archiveConfirmAction = 'unarchive'; showArchiveConfirm = true; }}>↩️ Zurück ({selectedCount})</button>
    {/if}
    {#if singleSelected && !isArchivView}
      <button class="btn-action-primary" onclick={openMsgModal}>✉️ Nachricht</button>
    {/if}
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════ TABLE -->
<div class="orders-table-wrap">
  <table class="orders-table">
    <thead>
      <tr>
        <th style="width:38px;text-align:center;">
          <input type="checkbox" checked={allFilteredSelected} onchange={toggleSelectAll} style="cursor:pointer;" />
        </th>
        <th>Datum</th><th>Bestellung</th><th>Käufer</th><th>Artikel</th>
        <th style="text-align:center;">Menge</th>
        <th style="text-align:right;">Gesamt</th>
        <th>Status</th><th>Tracking</th>
      </tr>
    </thead>
    <tbody>
      {#if loading}
        <tr><td colspan="9" class="table-loading"><div class="spinner"></div> Lade Bestellungen...</td></tr>
      {:else if filteredOrders.length === 0}
        <tr><td colspan="9" class="table-empty">{searchQuery ? 'Keine Ergebnisse für „' + searchQuery + '"' : 'Keine Bestellungen gefunden'}</td></tr>
      {:else}
        {#each filteredOrders as o (o.order_id)}
          {@const isSelected = selectedOrderIds.has(String(o.order_id))}
          {@const trackUrl = getTrackingUrl(o.tracking_nummer, o.versanddienstleister)}
          {@const bild = getOrderImage(o)}
          {@const isSingle = o.artikel_count === 1}
          {@const firstItem = o.items[0]}
          <tr class:selected={isSelected}>
            <td style="text-align:center;">
              <input type="checkbox" checked={isSelected} onchange={(e) => toggleOrderSelect(o.order_id, e.target.checked)} style="cursor:pointer;width:15px;height:15px;" />
            </td>
            <td class="col-date">{formatDate(o.bestelldatum || o.erstellt_am)}</td>
            <td>
              <a href="#" class="order-id-link" onclick={(e) => { e.preventDefault(); openDetailModal(o); }}>{o.order_id}</a>
            </td>
            <td>
              <div class="buyer-name">{o.buyer_name || '—'}</div>
              {#if o.buyer_ort || o.buyer_land}<div class="buyer-location">{o.buyer_ort || ''} {o.buyer_land || ''}</div>{/if}
            </td>
            <td class="col-artikel">
              <div style="display:flex;align-items:center;gap:8px;">
                {#if bild}
                  <img src={bild} alt="" style="width:72px;height:72px;object-fit:contain;border-radius:6px;border:1px solid var(--border);background:var(--surface2);flex-shrink:0;" onerror={(e) => { e.currentTarget.style.display='none'; }} />
                {/if}
                <div style="min-width:0;">
                  {#if isSingle}
                    <div class="artikel-name">
                      {#if firstItem.ebay_artikel_id}
                        <a href="https://www.ebay.de/itm/{firstItem.ebay_artikel_id}" target="_blank" class="artikel-ebay-link">{firstItem.artikel_name || '—'}</a>
                      {:else}{firstItem.artikel_name || '—'}{/if}
                    </div>
                    {#if firstItem.sold_sku}<div class="artikel-sku">SKU: {firstItem.sold_sku}</div>{/if}
                  {:else}
                    <div class="artikel-name">
                      <a href="#" class="artikel-multi-link" onclick={(e) => { e.preventDefault(); openDetailModal(o); }}>
                        📦 {o.artikel_count} Artikel
                      </a>
                    </div>
                    <div class="artikel-multi-preview">
                      {o.items.map(i => i.sold_sku ? varianteAusSku(i.sold_sku) : (i.artikel_name || '?')).join(' · ')}
                    </div>
                  {/if}
                </div>
              </div>
            </td>
            <td style="text-align:center;">{o.gesamt_menge}</td>
            <td style="text-align:right;font-weight:700;">{o.gesamt_summe.toFixed(2)} €</td>
            <td>
              <span class="badge badge-{o.status}">{statusLabel(o.status)}</span>
              {#if o.hat_rechnung}<span class="badge badge-rechnung" title="Rechnung vorhanden">🧾 RE</span>{/if}
            </td>
            <td class="col-tracking">
              {#if o.tracking_nummer}
                {#if trackUrl}
                  <a href={trackUrl} target="_blank" class="tracking-link">📦 {o.tracking_nummer}</a>
                {:else}
                  <span class="tracking-plain">{o.tracking_nummer}</span>
                {/if}
              {:else}
                <span class="no-tracking">—</span>
              {/if}
              {#if o.status !== 'versendet' && o.status !== 'archiviert' && o.status !== 'storniert'}
                <button class="btn-add-tracking" onclick={() => openTrackingModal(o.order_id, o.versanddienstleister, o.tracking_nummer)}>+ Tracking</button>
              {/if}
            </td>
          </tr>
        {/each}
      {/if}
    </tbody>
  </table>
</div>

<!-- ═══════════════════════════════════════════════════════ TRACKING MODAL -->
{#if showTrackingModal}
  <div class="modal-overlay open" onclick={(e) => { if (e.target === e.currentTarget) showTrackingModal = false; }}>
    <div class="modal" style="max-width:480px;">
      <div class="modal-title">📦 Sendungsnummer eintragen</div>
      <div style="font-size:12px;color:var(--text2);margin-bottom:24px;">Bestellung: {trackingOrderEbayId}</div>
      <div class="modal-field">
        <label>Versanddienstleister</label>
        <select bind:value={trackingCarrier}>
          <option>DHL Germany</option><option>Deutsche Post (DHL)</option><option>Hermes</option>
          <option>DPD</option><option>UPS</option><option>GLS</option><option>FedEx</option><option>Other</option>
        </select>
      </div>
      <div class="modal-field">
        <label>Sendungsnummer</label>
        <input type="text" bind:value={trackingNumber} placeholder="z.B. 00340435080463070955" onkeydown={(e) => e.key === 'Enter' && doSaveTracking()} />
      </div>
      <div class="modal-actions">
        <button class="btn-cancel" onclick={() => showTrackingModal = false}>Abbrechen</button>
        <button class="btn-primary" style="width:auto;padding:10px 26px;" onclick={doSaveTracking} disabled={trackingSaving}>
          {trackingSaving ? 'Speichern...' : '💾 Speichern & eBay melden'}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- ═══════════════════════════════════════════════════════ NACHRICHT MODAL -->
{#if showMsgModal}
  <div class="modal-overlay open" onclick={(e) => { if (e.target === e.currentTarget) showMsgModal = false; }}>
    <div class="modal" style="max-width:520px;">
      <div class="modal-title">✉️ Nachricht an Käufer</div>
      <div style="font-size:13px;color:var(--text2);margin-bottom:16px;padding:10px 14px;background:var(--surface2);border-radius:8px;">
        <strong>Käufer:</strong> {orderMessageBuyerName}
      </div>
      <div class="modal-field" style="margin-bottom:14px;">
        <label>Betreff</label>
        <input type="text" bind:value={msgSubject} placeholder="Betreff der Nachricht" />
      </div>
      <div class="modal-field" style="margin-bottom:14px;">
        <label>Nachricht</label>
        <textarea bind:value={msgText} placeholder="Ihre Nachricht an den Käufer..." style="resize:vertical;min-height:120px;"></textarea>
      </div>
      <div class="modal-actions">
        <button class="btn-cancel" onclick={() => showMsgModal = false}>Abbrechen</button>
        <button class="btn-primary" style="width:auto;padding:10px 26px;" onclick={doSendMessage} disabled={msgSending}>
          {msgSending ? 'Sende...' : '✉️ Senden'}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- ═══════════════════════════════════════════════════════ ARCHIV-CONFIRM MODAL -->
{#if showArchiveConfirm}
  <div class="modal-overlay open" onclick={(e) => { if (e.target === e.currentTarget && !archiveWorking) showArchiveConfirm = false; }}>
    <div class="modal" style="max-width:380px;text-align:center;">
      <div style="font-size:36px;margin-bottom:12px;">{archiveConfirmAction === 'unarchive' ? '↩️' : '📁'}</div>
      <div class="modal-title" style="font-size:16px;">
        {selectedCount} Bestellung(en) {archiveConfirmAction === 'unarchive' ? 'wiederherstellen?' : 'archivieren?'}
      </div>
      <div style="font-size:13px;color:var(--text2);margin-bottom:24px;">
        {archiveConfirmAction === 'unarchive' ? 'Die Bestellungen werden wieder in der Hauptliste angezeigt.' : 'Archivierte Bestellungen findest du im Archiv-Tab.'}
      </div>
      <div class="modal-actions" style="justify-content:center;">
        <button class="btn-cancel" onclick={() => showArchiveConfirm = false} disabled={archiveWorking}>Abbrechen</button>
        <button class="btn-primary" style="width:auto;padding:10px 26px;background:{archiveConfirmAction === 'unarchive' ? 'var(--primary)' : '#f59e0b'};" onclick={doArchiveOrUnarchive} disabled={archiveWorking}>
          {archiveWorking ? 'Bitte warten...' : (archiveConfirmAction === 'unarchive' ? '↩️ Wiederherstellen' : '📁 Archivieren')}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- ═══════════════════════════════════════════════════════ DETAIL MODAL — eBay-Style -->
{#if showDetailModal && detailOrder}
  {@const o = detailOrder}
  {@const trackUrl = getTrackingUrl(o.tracking_nummer, o.versanddienstleister)}
  <div class="modal-overlay open" onclick={(e) => { if (e.target === e.currentTarget) { showDetailModal = false; eRechnungDropdownOpen = false; } }}>
    <div class="modal detail-modal">

      <!-- Header -->
      <div class="detail-header">
        <div>
          <div class="detail-header-label">BESTELLUNG</div>
          <div class="detail-header-id">{o.order_id}</div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px;">
          <span class="badge badge-{o.status}" style="font-size:13px;padding:5px 16px;">{statusLabel(o.status)}</span>
          {#if o.hat_rechnung}
            <span class="badge badge-rechnung" style="font-size:11px;padding:3px 10px;">🧾 Rechnung</span>
          {/if}
        </div>
      </div>

      <!-- eBay-Style 2-Column Layout -->
      <div class="detail-layout">

        <!-- Links: Artikel-Liste -->
        <div class="detail-left">
          <div class="artikel-section">
            <div class="artikel-section-title">Artikel</div>

            {#each o.items as item, idx}
              {@const itemBild = getItemImage(item)}
              {@const ep = parseFloat(item.gesamt || 0) / (item.menge || 1)}
              {@const itemGesamt = parseFloat(item.gesamt || 0)}

              {#if idx > 0}<div class="artikel-divider"></div>{/if}

              <!-- Spaltenköpfe nur beim ersten Artikel -->
              {#if idx === 0}
                <div class="artikel-cols-header">
                  <div></div>
                  <div class="ach-stk">Stückzahl</div>
                  <div class="ach-ep">Artikelpreis</div>
                  <div class="ach-sum">Artikel insgesamt</div>
                </div>
              {/if}

              <div class="artikel-item">
                <div class="ai-info">
                  <div style="display:flex;gap:12px;align-items:flex-start;">
                    {#if itemBild}
                      <img src={itemBild} alt="" class="ai-bild" onerror={(e) => { e.currentTarget.style.display='none'; }} />
                    {:else}
                      <div class="ai-bild-ph">📦</div>
                    {/if}
                    <div>
                      <div class="ai-name">
                        {#if item.ebay_artikel_id}
                          <a href="https://www.ebay.de/itm/{item.ebay_artikel_id}" target="_blank">{item.artikel_name || '—'}</a>
                        {:else}{item.artikel_name || '—'}{/if}
                      </div>
                      {#if item.sold_sku}
                        <div class="ai-variante">Ausführung: <strong>{varianteAusSku(item.sold_sku)}</strong></div>
                        <div class="ai-sku">Bestandseinheit (SKU): {item.sold_sku}</div>
                      {/if}
                      <div class="ai-meta">Artikelnummer: {item.ebay_artikel_id || '—'}</div>
                    </div>
                  </div>
                </div>
                <div class="ai-stk">{item.menge || 1}</div>
                <div class="ai-ep">{ep.toFixed(2)} €</div>
                <div class="ai-sum">{itemGesamt.toFixed(2)} €</div>
              </div>
            {/each}
          </div>

          <!-- Käufer + Versand unterhalb der Artikel -->
          <div class="detail-bottom-cards">
            <div class="dbc-card">
              <div class="dbc-title">👤 Käufer</div>
              <div style="font-weight:600;">{o.buyer_name || '—'}</div>
              {#if o.buyer_username}<div class="dbc-sub">@{o.buyer_username}</div>{/if}
              {#if o.buyer_email}<div class="dbc-email">📧 {o.buyer_email}</div>{/if}
              {#if o.buyer_strasse}
                <div class="dbc-addr">{o.buyer_strasse}<br/>{o.buyer_plz || ''} {o.buyer_ort || ''}<br/>{o.buyer_land || ''}</div>
              {/if}
            </div>
            <div class="dbc-card">
              <div class="dbc-title">🚚 Versand</div>
              {#if o.tracking_nummer}
                <div style="font-size:12px;color:var(--text2);">{o.versanddienstleister || 'Versanddienstleister'}</div>
                {#if trackUrl}
                  <a href={trackUrl} target="_blank" class="tracking-link" style="font-size:13px;margin-top:4px;">📦 {o.tracking_nummer}</a>
                {:else}
                  <div style="font-size:13px;font-weight:600;margin-top:4px;">{o.tracking_nummer}</div>
                {/if}
              {:else}
                <div style="color:var(--text3);font-size:13px;">Noch nicht versendet</div>
                {#if o.status !== 'archiviert' && o.status !== 'storniert'}
                  <button class="btn-add-tracking" style="margin-top:8px;" onclick={() => { showDetailModal = false; openTrackingModal(o.order_id, o.versanddienstleister, ''); }}>+ Tracking eintragen</button>
                {/if}
              {/if}
            </div>
          </div>
        </div>

        <!-- Rechts: Zahlungsübersicht -->
        <div class="detail-right">
          <div class="summary-box">
            <div class="summary-title">Vom Käufer bezahlt</div>
            <div class="summary-row">
              <span>Zwischensumme ({o.artikel_count})</span>
              <span class="sr-val">{o.gesamt_summe.toFixed(2)} €</span>
            </div>
            <div class="summary-row">
              <span>Versand</span>
              <span class="sr-val">0,00 €</span>
            </div>
            <div class="summary-total-row">
              <span>Gesamtbetrag</span>
              <span class="sr-total">{o.gesamt_summe.toFixed(2)} €</span>
            </div>
          </div>

          <div class="summary-date">
            {formatDate(o.bestelldatum || o.erstellt_am)}
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="modal-actions" style="flex-wrap:wrap;margin-top:24px;">
        <button class="btn-cancel" onclick={() => { showDetailModal = false; eRechnungDropdownOpen = false; }}>Schließen</button>

        {#if o.status !== 'archiviert' && o.status !== 'storniert'}
          <button class="btn-secondary" onclick={() => { showDetailModal = false; selectedOrderIds = new Set([String(o.order_id)]); openMsgModal(); }}>
            ✉️ Nachricht
          </button>

          {#if !o.hat_rechnung}
            <button class="btn-primary" style="width:auto;padding:10px 20px;" onclick={() => erstelleRechnungAusBestellung(o)} disabled={rechnungWorking}>
              {rechnungWorking ? '⏳ Erstelle...' : '🧾 Rechnung erstellen'}
            </button>
          {/if}

          {#if o.hat_rechnung && o.invoice_id}
            <div style="position:relative;">
              <button class="btn-erechnung" onclick={() => eRechnungDropdownOpen = !eRechnungDropdownOpen} disabled={eRechnungWorking}>
                {#if eRechnungWorking}
                  ⏳ Erstelle...
                {:else}
                  <span class="btn-erechnung-label">📄 E-Rechnung</span>
                  <span class="btn-erechnung-divider"></span>
                  <span class="btn-erechnung-chevron" class:open={eRechnungDropdownOpen}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                      <polyline points="6 9 12 15 18 9"></polyline>
                    </svg>
                  </span>
                {/if}
              </button>
              {#if eRechnungDropdownOpen}
                <div class="erechnung-dropdown">
                  <button onclick={() => erstelleERechnungAusBestellung(o, 'zugferd_en16931')}>
                    <span class="dd-icon">🇩🇪</span>
                    <div><div class="dd-label">ZUGFeRD EN16931</div><div class="dd-sub">PDF + eingebettetes XML</div></div>
                  </button>
                  <button onclick={() => erstelleERechnungAusBestellung(o, 'zugferd_extended')}>
                    <span class="dd-icon">🇪🇺</span>
                    <div><div class="dd-label">ZUGFeRD EXTENDED</div><div class="dd-sub">Erweitertes Format (Beta)</div></div>
                  </button>
                  <button onclick={() => erstelleERechnungAusBestellung(o, 'xrechnung')}>
                    <span class="dd-icon">📋</span>
                    <div><div class="dd-label">XRechnung</div><div class="dd-sub">XML-Download (B2B/Behörden)</div></div>
                  </button>
                </div>
              {/if}
            </div>
          {/if}
        {/if}
      </div>
    </div>
  </div>
{/if}

<!-- ═══════════════════════════════════════════════════════ TOAST -->
{#if _toast.visible}
  <div class="toast toast-{_toast.type}">{_toast.msg}</div>
{/if}

<style>
  /* ── Page Header ───────────────────────────────────────── */
  .page-hdr { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
  .page-hdr-title { font-size: 22px; font-weight: 800; color: var(--text); }
  .page-hdr-sub { font-size: 13px; color: var(--text2); margin-top: 2px; }
  .btn-refresh { display: flex; align-items: center; gap: 6px; background: var(--surface); border: 1.5px solid var(--border); border-radius: 9px; padding: 8px 16px; font-size: 13px; font-weight: 600; color: var(--text); cursor: pointer; transition: border-color 0.15s, background 0.15s; }
  .btn-refresh:hover { border-color: var(--primary); background: var(--primary-light); color: var(--primary); }
  .btn-refresh:disabled { opacity: 0.6; cursor: not-allowed; }

  /* ── Toolbar ────────────────────────────────────────────── */
  .orders-toolbar { display: flex; gap: 10px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
  .orders-filter { display: flex; gap: 6px; flex-wrap: wrap; }
  .orders-filter-btn { background: var(--surface); border: 1.5px solid var(--border); border-radius: 8px; padding: 6px 14px; font-size: 12px; font-weight: 600; cursor: pointer; color: var(--text2); transition: all 0.15s; display: flex; align-items: center; gap: 5px; }
  .orders-filter-btn:hover, .orders-filter-btn.active { border-color: var(--primary); background: var(--primary-light); color: var(--primary); }
  .filter-badge { background: var(--primary); color: white; border-radius: 10px; padding: 1px 7px; font-size: 10px; font-weight: 700; }
  .btn-action-warn { background: #f59e0b; border: none; border-radius: 9px; padding: 7px 14px; color: white; font-size: 12px; font-weight: 600; cursor: pointer; white-space: nowrap; }
  .btn-action-primary { background: var(--primary); border: none; border-radius: 9px; padding: 7px 14px; color: white; font-size: 12px; font-weight: 600; cursor: pointer; white-space: nowrap; }
  .btn-action-primary:disabled { opacity: 0.6; cursor: not-allowed; }
  .search-wrap { position: relative; }
  .search-box { width: 100%; background: var(--surface); border: 1.5px solid var(--border); border-radius: 9px; padding: 8px 14px; font-size: 13px; color: var(--text); outline: none; transition: border-color 0.15s; }
  .search-box:focus { border-color: var(--primary); }

  /* ── Table ──────────────────────────────────────────────── */
  .orders-table-wrap { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius, 12px); box-shadow: var(--shadow); overflow: hidden; }
  .orders-table { width: 100%; border-collapse: collapse; font-size: 13px; }
  .orders-table th { background: var(--surface2); padding: 10px 14px; text-align: left; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: var(--text2); border-bottom: 1px solid var(--border); }
  .orders-table td { padding: 12px 14px; border-bottom: 1px solid var(--border); color: var(--text); vertical-align: middle; }
  .orders-table tr:last-child td { border-bottom: none; }
  .orders-table tr:hover td { background: var(--surface2); }
  .orders-table tr.selected td { background: var(--primary-light); }
  .table-loading, .table-empty { text-align: center; padding: 48px; color: var(--text3); }
  .table-loading { display: flex; align-items: center; justify-content: center; gap: 10px; }

  .col-date { white-space: nowrap; color: var(--text2); }
  .order-id-link { color: var(--primary); font-weight: 600; font-size: 12px; text-decoration: none; cursor: pointer; }
  .order-id-link:hover { text-decoration: underline; }
  .buyer-name { font-weight: 600; }
  .buyer-location { font-size: 11px; color: var(--text3); margin-top: 2px; }
  .col-artikel { max-width: 220px; }
  .artikel-name { font-size: 13px; }
  .artikel-sku { font-size: 11px; color: var(--primary); font-weight: 600; margin-top: 3px; font-family: monospace; }
  .artikel-ebay-link { color: var(--text); text-decoration: none; }
  .artikel-ebay-link:hover { color: var(--primary); text-decoration: underline; }
  .artikel-multi-link { color: var(--primary); font-weight: 700; text-decoration: none; cursor: pointer; }
  .artikel-multi-link:hover { text-decoration: underline; }
  .artikel-multi-preview { font-size: 11px; color: var(--text3); margin-top: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 180px; }
  .col-tracking { min-width: 140px; }
  .tracking-link { color: var(--primary); text-decoration: none; font-weight: 600; font-size: 12px; display: block; }
  .tracking-link:hover { text-decoration: underline; }
  .tracking-plain { font-size: 12px; }
  .no-tracking { color: var(--text3); font-size: 12px; }
  .btn-add-tracking { margin-top: 4px; display: block; background: var(--primary); border: none; border-radius: 6px; padding: 4px 10px; color: white; font-size: 11px; font-weight: 600; cursor: pointer; transition: opacity 0.15s; }
  .btn-add-tracking:hover { opacity: 0.85; }

  /* ── Badges ─────────────────────────────────────────────── */
  .badge { display: inline-block; font-size: 11px; font-weight: 700; padding: 2px 10px; border-radius: 20px; white-space: nowrap; }
  .badge-versendet { background: #f0fdf4; color: #16a34a; }
  .badge-storniert { background: #fef2f2; color: #dc2626; }
  .badge-bezahlt   { background: #fffbeb; color: #d97706; }
  .badge-archiviert { background: var(--surface2); color: var(--text2); }
  .badge-rechnung { background: #eff6ff; color: #2563eb; margin-top: 4px; }
  :global([data-theme="dark"]) .badge-versendet { background: rgba(34,197,94,0.15); color: #86efac; }
  :global([data-theme="dark"]) .badge-storniert { background: rgba(239,68,68,0.15); color: #fca5a5; }
  :global([data-theme="dark"]) .badge-bezahlt   { background: rgba(245,158,11,0.15); color: #fcd34d; }
  :global([data-theme="dark"]) .badge-rechnung  { background: rgba(37,99,235,0.15); color: #93c5fd; }

  /* ── Detail Modal — eBay-Style ─────────────────────────── */
  .detail-modal { max-width: 880px; max-height: 90vh; overflow-y: auto; }

  .detail-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
  .detail-header-label { font-size: 11px; font-weight: 700; color: var(--text3); text-transform: uppercase; letter-spacing: 1px; }
  .detail-header-id { font-size: 22px; font-weight: 800; color: var(--text); margin-top: 2px; }

  .detail-layout { display: grid; grid-template-columns: 1fr 240px; gap: 24px; }

  /* -- Linke Seite: Artikel -- */
  .detail-left { min-width: 0; }

  .artikel-section { border: 1px solid var(--border); border-radius: 10px; background: var(--surface); overflow: hidden; }
  .artikel-section-title { font-size: 15px; font-weight: 800; padding: 16px 20px 12px; color: var(--text); }

  .artikel-cols-header { display: grid; grid-template-columns: 1fr 70px 90px 100px; padding: 0 20px 8px; gap: 8px; }
  .artikel-cols-header > div { font-size: 11px; color: var(--text3); }
  .ach-stk, .ach-ep, .ach-sum { text-align: right; }

  .artikel-divider { height: 1px; background: var(--border); margin: 0 20px; }

  .artikel-item { display: grid; grid-template-columns: 1fr 70px 90px 100px; padding: 16px 20px; gap: 8px; align-items: center; }

  .ai-bild { width: 64px; height: 64px; object-fit: contain; border-radius: 6px; border: 1px solid var(--border); background: var(--surface2); flex-shrink: 0; }
  .ai-bild-ph { width: 64px; height: 64px; background: var(--surface2); border-radius: 6px; border: 1px solid var(--border); display: flex; align-items: center; justify-content: center; font-size: 24px; flex-shrink: 0; }
  .ai-name { font-size: 13px; font-weight: 600; line-height: 1.4; }
  .ai-name a { color: var(--primary); text-decoration: none; }
  .ai-name a:hover { text-decoration: underline; }
  .ai-variante { font-size: 12px; margin-top: 4px; color: var(--text); }
  .ai-sku { font-size: 11px; color: var(--primary); margin-top: 2px; }
  .ai-meta { font-size: 11px; color: var(--text3); margin-top: 2px; }
  .ai-stk { text-align: right; font-size: 14px; }
  .ai-ep  { text-align: right; font-size: 14px; }
  .ai-sum { text-align: right; font-size: 14px; font-weight: 700; }

  /* -- Käufer + Versand Cards -- */
  .detail-bottom-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px; }
  .dbc-card { border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; background: var(--surface); }
  .dbc-title { font-size: 11px; font-weight: 700; color: var(--text3); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
  .dbc-sub { font-size: 11px; color: var(--text3); margin-top: 2px; }
  .dbc-email { font-size: 12px; color: var(--text2); margin-top: 6px; }
  .dbc-addr { font-size: 12px; color: var(--text2); margin-top: 6px; line-height: 1.5; }

  /* -- Rechte Seite: Zusammenfassung -- */
  .detail-right { }
  .summary-box { border: 1px solid var(--border); border-radius: 10px; padding: 16px; background: var(--surface); }
  .summary-title { font-size: 14px; font-weight: 800; color: var(--text); margin-bottom: 14px; }
  .summary-row { display: flex; justify-content: space-between; padding: 3px 0; font-size: 13px; color: var(--text2); }
  .sr-val { color: var(--text); font-weight: 600; }
  .summary-total-row { display: flex; justify-content: space-between; padding-top: 12px; margin-top: 8px; border-top: 1.5px solid var(--border); font-size: 14px; font-weight: 700; }
  .sr-total { font-size: 16px; font-weight: 800; color: var(--text); }
  .summary-date { font-size: 12px; color: var(--text3); margin-top: 10px; text-align: right; }

  /* ── Modals (shared) ────────────────────────────────────── */
  .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); backdrop-filter: blur(4px); z-index: 1000; display: none; align-items: center; justify-content: center; }
  .modal-overlay.open { display: flex; }
  .modal { background: var(--surface); border: 1px solid var(--border); border-radius: 18px; padding: 32px; width: 95%; box-shadow: 0 20px 60px rgba(0,0,0,0.2); }
  .modal-title { font-size: 18px; font-weight: 800; margin-bottom: 20px; color: var(--text); }
  .modal-field { margin-bottom: 16px; }
  .modal-field label { display: block; font-size: 11px; font-weight: 600; color: var(--text2); margin-bottom: 6px; text-transform: uppercase; letter-spacing: 1px; }
  .modal-field input, .modal-field select, .modal-field textarea { width: 100%; background: var(--surface2); border: 1.5px solid var(--border); border-radius: 8px; padding: 10px 12px; color: var(--text); font-size: 13px; outline: none; transition: border-color 0.15s; font-family: inherit; }
  .modal-field input:focus, .modal-field select:focus, .modal-field textarea:focus { border-color: var(--primary); }
  .modal-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px; align-items: center; flex-wrap: wrap; }
  .btn-cancel { background: transparent; border: 1.5px solid var(--border); border-radius: 9px; padding: 10px 20px; font-size: 13px; font-weight: 600; color: var(--text2); cursor: pointer; transition: all 0.15s; }
  .btn-cancel:hover { border-color: var(--text2); color: var(--text); }
  .btn-primary { background: var(--primary); border: none; border-radius: 9px; padding: 10px 22px; font-size: 13px; font-weight: 600; color: white; cursor: pointer; transition: opacity 0.15s; width: 100%; }
  .btn-primary:hover { opacity: 0.9; }
  .btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
  .btn-secondary { background: var(--surface2); border: 1.5px solid var(--border); border-radius: 9px; padding: 10px 18px; font-size: 13px; font-weight: 600; color: var(--text); cursor: pointer; transition: all 0.15s; white-space: nowrap; }
  .btn-secondary:hover { border-color: var(--primary); color: var(--primary); }

  /* ── E-Rechnung Split-Button ─────────────────────────────── */
  .btn-erechnung { display: flex; align-items: center; gap: 0; background: var(--primary); border: none; border-radius: 9px; padding: 0; font-size: 13px; font-weight: 600; color: white; cursor: pointer; transition: opacity 0.15s; overflow: hidden; }
  .btn-erechnung:hover { opacity: 0.9; }
  .btn-erechnung:disabled { opacity: 0.6; cursor: not-allowed; }
  .btn-erechnung-label { padding: 10px 14px 10px 16px; }
  .btn-erechnung-divider { width: 1px; height: 36px; background: rgba(255,255,255,0.35); flex-shrink: 0; }
  .btn-erechnung-chevron { display: flex; align-items: center; justify-content: center; padding: 10px 12px; transition: transform 0.2s ease; }
  .btn-erechnung-chevron.open { transform: rotate(180deg); }
  .erechnung-dropdown { position: absolute; bottom: calc(100% + 8px); right: 0; background: var(--surface); border: 1.5px solid var(--border); border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,0.15); min-width: 250px; z-index: 100; overflow: hidden; }
  .erechnung-dropdown button { display: flex; align-items: center; gap: 12px; width: 100%; padding: 13px 16px; background: transparent; border: none; cursor: pointer; text-align: left; transition: background 0.15s; color: var(--text); }
  .erechnung-dropdown button:hover { background: var(--primary-light); }
  .erechnung-dropdown button + button { border-top: 1px solid var(--border); }
  .dd-icon { font-size: 20px; flex-shrink: 0; }
  .dd-label { font-size: 13px; font-weight: 700; }
  .dd-sub { font-size: 11px; color: var(--text3); margin-top: 2px; }

  /* ── Spinner & Toast ────────────────────────────────────── */
  .spinner { width: 18px; height: 18px; border: 2px solid var(--border); border-top-color: var(--primary); border-radius: 50%; animation: spin 0.7s linear infinite; display: inline-block; }
  .spinner-sm { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.4); border-top-color: white; border-radius: 50%; animation: spin 0.7s linear infinite; display: inline-block; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .toast { position: fixed; bottom: 24px; right: 24px; z-index: 9999; padding: 12px 20px; border-radius: 12px; font-size: 13px; font-weight: 600; box-shadow: 0 4px 20px rgba(0,0,0,0.2); animation: slideIn 0.25s ease; }
  .toast-success { background: #22c55e; color: white; }
  .toast-error   { background: #ef4444; color: white; }
  .toast-info    { background: var(--primary); color: white; }
  @keyframes slideIn { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }

  /* ── Responsive ─────────────────────────────────────────── */
  @media (max-width: 900px) {
    .detail-layout { grid-template-columns: 1fr; }
    .detail-right { order: -1; }
    .detail-modal { max-width: 100%; }
  }
  @media (max-width: 768px) {
    .orders-table { font-size: 12px; }
    .orders-table th, .orders-table td { padding: 8px 10px; }
    .col-artikel { display: none; }
    .artikel-cols-header, .artikel-item { grid-template-columns: 1fr 50px 70px 70px; }
    .ai-bild, .ai-bild-ph { width: 44px; height: 44px; }
    .detail-bottom-cards { grid-template-columns: 1fr; }
  }
</style>
