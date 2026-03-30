<script>
  import { onMount } from 'svelte';
  import { currentUser } from '$lib/stores.js';
  import { apiCall } from '$lib/api.js';

  // ─── State ─────────────────────────────────────────────────────────────────
  let allOrders = $state([]);
  let allRechnungen = $state([]);
  let ordersFilter = $state('alle');
  let searchQuery = $state('');
  let loading = $state(true);
  let selectedOrderIds = $state(new Set());

  // Tracking modal
  let showTrackingModal = $state(false);
  let trackingOrderId = $state(null);
  let trackingOrderEbayId = $state('');
  let trackingCarrier = $state('DHL Germany');
  let trackingNumber = $state('');
  let trackingSaving = $state(false);

  // Order message modal
  let showMsgModal = $state(false);
  let orderMessageBuyer = $state(null);
  let orderMessageBuyerName = $state('');
  let msgSubject = $state('');
  let msgText = $state('');
  let msgSending = $state(false);

  // Archive confirm modal
  let showArchiveConfirm = $state(false);
  let archiveConfirmAction = $state('archive'); // 'archive' | 'unarchive'
  let archiveWorking = $state(false);

  // Detail modal
  let showDetailModal = $state(false);
  let detailOrder = $state(null);

  // ─── Derived ───────────────────────────────────────────────────────────────
  let filteredOrders = $derived.by(() => {
    let orders = allOrders;
    const q = searchQuery.toLowerCase();

    // Tab-Filter
    if (ordersFilter === 'archiviert') {
      orders = orders.filter(o => o.archiviert || o.status === 'archiviert');
    } else {
      orders = orders.filter(o => !o.archiviert && o.status !== 'archiviert');
      if (ordersFilter !== 'alle') orders = orders.filter(o => o.status === ordersFilter);
    }

    // Suche
    if (q) {
      orders = orders.filter(o =>
        (o.order_id || '').toLowerCase().includes(q) ||
        (o.buyer_name || '').toLowerCase().includes(q) ||
        (o.buyer_username || '').toLowerCase().includes(q) ||
        (o.artikel_name || '').toLowerCase().includes(q)
      );
    }

    return orders;
  });

  let hasSelected = $derived(selectedOrderIds.size > 0);
  let isArchivView = $derived(ordersFilter === 'archiviert');
  let selectedCount = $derived(selectedOrderIds.size);
  let singleSelected = $derived(selectedOrderIds.size === 1);

  let countAlle = $derived(allOrders.filter(o => !o.archiviert && o.status !== 'archiviert').length);
  let countBezahlt = $derived(allOrders.filter(o => !o.archiviert && o.status !== 'archiviert' && o.status === 'bezahlt').length);
  let countVersendet = $derived(allOrders.filter(o => !o.archiviert && o.status !== 'archiviert' && o.status === 'versendet').length);
  let countArchiviert = $derived(allOrders.filter(o => o.archiviert || o.status === 'archiviert').length);

  let allFilteredSelected = $derived(
    filteredOrders.length > 0 && filteredOrders.every(o => selectedOrderIds.has(String(o.order_id || o.id)))
  );

  // ─── Lifecycle ─────────────────────────────────────────────────────────────
  onMount(() => {
    loadBestellungen();
  });

  // ─── API ───────────────────────────────────────────────────────────────────
  async function loadBestellungen() {
    loading = true;
    try {
      const data = await apiCall('/orders-laden', {
        user_id: $currentUser.id,
        ebay_username: $currentUser.ebay_user_id
      });
      if (data.success) {
        allOrders = data.orders || [];
      } else {
        showToast('Fehler beim Laden der Bestellungen', 'error');
      }
    } catch (e) {
      showToast('Verbindungsfehler: ' + e.message, 'error');
    } finally {
      loading = false;
    }
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
      } catch (e) { /* ignore einzelne Fehler */ }
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
        order_id: trackingOrderId,
        tracking_nummer: trackingNumber.trim(),
        versanddienstleister: trackingCarrier,
        user_id: $currentUser.id,
        ebay_username: $currentUser.ebay_user_id
      });
      if (data.success) {
        showToast('Gespeichert und eBay informiert', 'success');
        showTrackingModal = false;
        await loadBestellungen();
        await autoCreateRechnungAfterTracking(trackingOrderId);
      } else {
        showToast('Fehler beim Speichern', 'error');
      }
    } catch (e) {
      showToast('Verbindungsfehler', 'error');
    } finally {
      trackingSaving = false;
    }
  }

  async function doSendMessage() {
    if (!msgText.trim()) { showToast('Bitte Nachricht eingeben', 'error'); return; }
    msgSending = true;
    try {
      const data = await apiCall('/antwort-senden', {
        recipient: orderMessageBuyer,
        subject: msgSubject,
        reply: msgText,
        user_id: $currentUser.id,
        ebay_username: $currentUser.ebay_user_id
      });
      if (data.success) {
        showToast('✅ Nachricht gesendet!', 'success');
        showMsgModal = false;
        msgSubject = '';
        msgText = '';
      } else {
        showToast('Fehler: ' + (data.message || 'Unbekannter Fehler'), 'error');
      }
    } catch (e) {
      showToast('Verbindungsfehler', 'error');
    } finally {
      msgSending = false;
    }
  }

  async function autoCreateRechnungAfterTracking(orderId) {
    try {
      const order = allOrders.find(o => String(o.order_id) === String(orderId));
      if (!order) return;
      const sd = await apiCall('/rechnung-settings', { action: 'load', user_id: $currentUser.id });
      if (!sd.success || !sd.data?.auto_rechnung) return;
      const existiert = allRechnungen.some(r => String(r.order_id) === String(orderId) && r.rechnung_typ === 'rechnung');
      if (existiert) return;
      const res = await apiCall('/rechnung-erstellen', {
        user_id: $currentUser.id,
        typ: 'rechnung',
        order_id: orderId,
        kaeufer_name: order.buyer_name || order.buyer_username || '',
        kaeufer_username: order.buyer_username || '',
        kaeufer_strasse: order.buyer_strasse || '',
        kaeufer_plz: order.buyer_plz || '',
        kaeufer_ort: order.buyer_ort || '',
        kaeufer_land: order.buyer_land || '',
        kaeufer_email: order.buyer_email || '',
        artikel_name: order.artikel_name || '',
        menge: order.menge || 1,
        einzelpreis: parseFloat(order.gesamt || 0) / (order.menge || 1),
        ebay_artikel_id: order.ebay_artikel_id || ''
      });
      if (res.success) {
        showToast('Rechnung ' + res.rechnung_nr + ' erstellt', 'success');
        if (sd.data?.auto_email && order.buyer_email) {
          await apiCall('/rechnung-senden', {
            invoice_id: res.invoice_id,
            user_id: $currentUser.id,
            to_email: order.buyer_email
          });
        }
      }
    } catch (e) {
      console.warn('Auto-Rechnung:', e);
    }
  }

  // ─── Helpers ───────────────────────────────────────────────────────────────
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
      const newSet = new Set(selectedOrderIds);
      filteredOrders.forEach(o => newSet.add(String(o.order_id || o.id)));
      selectedOrderIds = newSet;
    } else {
      const newSet = new Set(selectedOrderIds);
      filteredOrders.forEach(o => newSet.delete(String(o.order_id || o.id)));
      selectedOrderIds = newSet;
    }
  }

  function toggleOrderSelect(id, checked) {
    const newSet = new Set(selectedOrderIds);
    if (checked) newSet.add(String(id));
    else newSet.delete(String(id));
    selectedOrderIds = newSet;
  }

  function openTrackingModal(orderId, carrier, tracking) {
    trackingOrderId = orderId;
    trackingOrderEbayId = orderId;
    trackingCarrier = carrier || 'DHL Germany';
    trackingNumber = tracking || '';
    showTrackingModal = true;
  }

  function openMsgModal() {
    if (selectedOrderIds.size !== 1) return;
    const id = Array.from(selectedOrderIds)[0];
    const order = allOrders.find(o => String(o.order_id) === String(id) || String(o.id) === String(id));
    orderMessageBuyer = order?.buyer_username || order?.käufer || null;
    orderMessageBuyerName = order?.buyer_name || orderMessageBuyer || 'Käufer';
    msgSubject = '';
    msgText = '';
    showMsgModal = true;
  }

  function openDetailModal(order) {
    detailOrder = order;
    showDetailModal = true;
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
  <!-- Filter Tabs -->
  <div class="orders-filter">
    <button
      class="orders-filter-btn {ordersFilter === 'alle' ? 'active' : ''}"
      onclick={() => { ordersFilter = 'alle'; selectedOrderIds = new Set(); }}
    >Alle {#if countAlle > 0}<span class="filter-badge">{countAlle}</span>{/if}</button>

    <button
      class="orders-filter-btn {ordersFilter === 'bezahlt' ? 'active' : ''}"
      onclick={() => { ordersFilter = 'bezahlt'; selectedOrderIds = new Set(); }}
    >💛 Bezahlt {#if countBezahlt > 0}<span class="filter-badge">{countBezahlt}</span>{/if}</button>

    <button
      class="orders-filter-btn {ordersFilter === 'versendet' ? 'active' : ''}"
      onclick={() => { ordersFilter = 'versendet'; selectedOrderIds = new Set(); }}
    >✅ Versendet {#if countVersendet > 0}<span class="filter-badge">{countVersendet}</span>{/if}</button>

    <button
      class="orders-filter-btn {ordersFilter === 'archiviert' ? 'active' : ''}"
      onclick={() => { ordersFilter = 'archiviert'; selectedOrderIds = new Set(); }}
    >📁 Archiv {#if countArchiviert > 0}<span class="filter-badge">{countArchiviert}</span>{/if}</button>
  </div>

  <!-- Search + Action Buttons -->
  <div style="display:flex;gap:8px;align-items:center;flex:1;min-width:200px;">
    <div class="search-wrap" style="flex:1;max-width:300px;">
      <input
        class="search-box"
        bind:value={searchQuery}
        placeholder="Bestellung, Käufer, Artikel..."
      />
    </div>

    {#if hasSelected && !isArchivView}
      <button
        class="btn-action-warn"
        onclick={() => { archiveConfirmAction = 'archive'; showArchiveConfirm = true; }}
      >📁 Archivieren ({selectedCount})</button>
    {/if}

    {#if hasSelected && isArchivView}
      <button
        class="btn-action-primary"
        onclick={() => { archiveConfirmAction = 'unarchive'; showArchiveConfirm = true; }}
      >↩️ Zurück ({selectedCount})</button>
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
          <input
            type="checkbox"
            checked={allFilteredSelected}
            onchange={toggleSelectAll}
            style="cursor:pointer;"
          />
        </th>
        <th>Datum</th>
        <th>Bestellung</th>
        <th>Käufer</th>
        <th>Artikel</th>
        <th style="text-align:center;">Menge</th>
        <th style="text-align:right;">Gesamt</th>
        <th>Status</th>
        <th>Tracking</th>
      </tr>
    </thead>
    <tbody>
      {#if loading}
        <tr>
          <td colspan="9" class="table-loading">
            <div class="spinner"></div> Lade Bestellungen...
          </td>
        </tr>
      {:else if filteredOrders.length === 0}
        <tr>
          <td colspan="9" class="table-empty">
            {searchQuery ? 'Keine Ergebnisse für „' + searchQuery + '"' : 'Keine Bestellungen gefunden'}
          </td>
        </tr>
      {:else}
        {#each filteredOrders as o (o.order_id || o.id)}
          {@const isSelected = selectedOrderIds.has(String(o.order_id || o.id))}
          {@const trackUrl = getTrackingUrl(o.tracking_nummer, o.versanddienstleister)}
          <tr class:selected={isSelected}>
            <td style="text-align:center;">
              <input
                type="checkbox"
                checked={isSelected}
                onchange={(e) => toggleOrderSelect(o.order_id || o.id, e.target.checked)}
                style="cursor:pointer;width:15px;height:15px;"
              />
            </td>
            <td class="col-date">{formatDate(o.bestelldatum || o.erstellt_am)}</td>
            <td>
              <a
                href="#"
                class="order-id-link"
                onclick={(e) => { e.preventDefault(); openDetailModal(o); }}
              >{o.order_id}</a>
            </td>
            <td>
              <div class="buyer-name">{o.buyer_name || '—'}</div>
              {#if o.buyer_ort || o.buyer_land}
                <div class="buyer-location">{o.buyer_ort || ''} {o.buyer_land || ''}</div>
              {/if}
            </td>
            <td class="col-artikel">
              <div class="artikel-name">{o.artikel_name || '—'}</div>
              {#if o.ebay_artikel_id}
                <div class="artikel-id">eBay: {o.ebay_artikel_id}</div>
              {/if}
            </td>
            <td style="text-align:center;">{o.menge || 1}</td>
            <td style="text-align:right;font-weight:700;">{parseFloat(o.gesamt || 0).toFixed(2)} €</td>
            <td>
              <span class="badge badge-{o.status}">{statusLabel(o.status)}</span>
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
                <button
                  class="btn-add-tracking"
                  onclick={() => openTrackingModal(o.order_id, o.versanddienstleister, o.tracking_nummer)}
                >+ Tracking</button>
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
          <option>DHL Germany</option>
          <option>Deutsche Post (DHL)</option>
          <option>Hermes</option>
          <option>DPD</option>
          <option>UPS</option>
          <option>GLS</option>
          <option>FedEx</option>
          <option>Other</option>
        </select>
      </div>

      <div class="modal-field">
        <label>Sendungsnummer</label>
        <input
          type="text"
          bind:value={trackingNumber}
          placeholder="z.B. 00340435080463070955"
          onkeydown={(e) => e.key === 'Enter' && doSaveTracking()}
        />
      </div>

      <div class="modal-actions">
        <button class="btn-cancel" onclick={() => showTrackingModal = false}>Abbrechen</button>
        <button
          class="btn-primary"
          style="width:auto;padding:10px 26px;"
          onclick={doSaveTracking}
          disabled={trackingSaving}
        >{trackingSaving ? 'Speichern...' : '💾 Speichern & eBay melden'}</button>
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
        <textarea
          bind:value={msgText}
          placeholder="Ihre Nachricht an den Käufer..."
          style="resize:vertical;min-height:120px;"
        ></textarea>
      </div>

      <div class="modal-actions">
        <button class="btn-cancel" onclick={() => showMsgModal = false}>Abbrechen</button>
        <button
          class="btn-primary"
          style="width:auto;padding:10px 26px;"
          onclick={doSendMessage}
          disabled={msgSending}
        >{msgSending ? 'Sende...' : '✉️ Senden'}</button>
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
        {archiveConfirmAction === 'unarchive'
          ? 'Die Bestellungen werden wieder in der Hauptliste angezeigt.'
          : 'Archivierte Bestellungen findest du im Archiv-Tab.'}
      </div>
      <div class="modal-actions" style="justify-content:center;">
        <button class="btn-cancel" onclick={() => showArchiveConfirm = false} disabled={archiveWorking}>Abbrechen</button>
        <button
          class="btn-primary"
          style="width:auto;padding:10px 26px;background:{archiveConfirmAction === 'unarchive' ? 'var(--primary)' : '#f59e0b'};"
          onclick={doArchiveOrUnarchive}
          disabled={archiveWorking}
        >{archiveWorking ? 'Bitte warten...' : (archiveConfirmAction === 'unarchive' ? '↩️ Wiederherstellen' : '📁 Archivieren')}</button>
      </div>
    </div>
  </div>
{/if}

<!-- ═══════════════════════════════════════════════════════ DETAIL MODAL -->
{#if showDetailModal && detailOrder}
  {@const o = detailOrder}
  {@const trackUrl = getTrackingUrl(o.tracking_nummer, o.versanddienstleister)}
  <div
    class="modal-overlay open"
    onclick={(e) => { if (e.target === e.currentTarget) showDetailModal = false; }}
  >
    <div class="modal" style="max-width:640px;max-height:85vh;overflow-y:auto;">
      <!-- Header -->
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:20px;">
        <div>
          <div style="font-size:11px;font-weight:700;color:var(--text3);text-transform:uppercase;letter-spacing:1px;">Bestellung</div>
          <div style="font-size:20px;font-weight:800;color:var(--text);margin-top:4px;">{o.order_id}</div>
        </div>
        <span class="badge badge-{o.status}" style="font-size:13px;padding:4px 14px;">{statusLabel(o.status)}</span>
      </div>

      <!-- Grid -->
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px;">
        <!-- Artikel -->
        <div class="detail-card">
          <div class="detail-card-title">📦 Artikel</div>
          <div class="detail-card-body">
            <div style="font-size:14px;font-weight:600;line-height:1.4;">
              {#if o.ebay_artikel_id}
                <a href="https://www.ebay.de/itm/{o.ebay_artikel_id}" target="_blank" style="color:var(--primary);text-decoration:none;">{o.artikel_name || '—'}</a>
              {:else}
                {o.artikel_name || '—'}
              {/if}
            </div>
            {#if o.ebay_artikel_id}
              <div style="font-size:11px;color:var(--text3);margin-top:4px;">eBay-ID: {o.ebay_artikel_id}</div>
            {/if}
          </div>
        </div>

        <!-- Käufer -->
        <div class="detail-card">
          <div class="detail-card-title">👤 Käufer</div>
          <div class="detail-card-body">
            <div style="font-weight:600;">{o.buyer_name || '—'}</div>
            {#if o.buyer_username}
              <div style="font-size:11px;color:var(--text3);">@{o.buyer_username}</div>
            {/if}
            {#if o.buyer_strasse}
              <div style="font-size:12px;color:var(--text2);margin-top:6px;line-height:1.5;">
                {o.buyer_strasse}<br/>
                {o.buyer_plz || ''} {o.buyer_ort || ''}<br/>
                {o.buyer_land || ''}
              </div>
            {/if}
          </div>
        </div>

        <!-- Zahlung -->
        <div class="detail-card">
          <div class="detail-card-title">💰 Zahlung</div>
          <div class="detail-card-body">
            <div style="font-size:22px;font-weight:800;">{parseFloat(o.gesamt || 0).toFixed(2)} €</div>
            <div style="font-size:12px;color:var(--text2);margin-top:4px;">Menge: {o.menge || 1}</div>
            <div style="font-size:12px;color:var(--text2);">Datum: {formatDate(o.bestelldatum || o.erstellt_am)}</div>
          </div>
        </div>

        <!-- Versand -->
        <div class="detail-card">
          <div class="detail-card-title">🚚 Versand</div>
          <div class="detail-card-body">
            {#if o.tracking_nummer}
              <div style="font-size:12px;color:var(--text2);">{o.versanddienstleister || 'Versanddienstleister'}</div>
              {#if trackUrl}
                <a href={trackUrl} target="_blank" class="tracking-link" style="font-size:13px;">📦 {o.tracking_nummer}</a>
              {:else}
                <div style="font-size:13px;font-weight:600;">{o.tracking_nummer}</div>
              {/if}
            {:else}
              <div style="color:var(--text3);font-size:13px;">Noch nicht versendet</div>
              {#if o.status !== 'archiviert' && o.status !== 'storniert'}
                <button
                  class="btn-add-tracking"
                  style="margin-top:8px;"
                  onclick={() => { showDetailModal = false; openTrackingModal(o.order_id, o.versanddienstleister, ''); }}
                >+ Tracking eintragen</button>
              {/if}
            {/if}
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="modal-actions">
        <button class="btn-cancel" onclick={() => showDetailModal = false}>Schließen</button>
        {#if o.status !== 'archiviert' && o.status !== 'storniert'}
          <button
            class="btn-primary"
            style="width:auto;padding:10px 22px;"
            onclick={() => {
              showDetailModal = false;
              selectedOrderIds = new Set([String(o.order_id || o.id)]);
              openMsgModal();
            }}
          >✉️ Nachricht senden</button>
        {/if}
      </div>
    </div>
  </div>
{/if}

<!-- ═══════════════════════════════════════════════════════ TOAST -->
{#if _toast.visible}
  <div class="toast toast-{_toast.type}">{_toast.msg}</div>
{/if}

<!-- ═══════════════════════════════════════════════════════ STYLES -->
<style>
  /* ── Page Header ────────────────────────────────────────── */
  .page-hdr {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 24px;
  }
  .page-hdr-title {
    font-size: 22px;
    font-weight: 800;
    color: var(--text);
  }
  .page-hdr-sub {
    font-size: 13px;
    color: var(--text2);
    margin-top: 2px;
  }
  .btn-refresh {
    display: flex;
    align-items: center;
    gap: 6px;
    background: var(--surface);
    border: 1.5px solid var(--border);
    border-radius: 9px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
    color: var(--text);
    cursor: pointer;
    transition: border-color 0.15s, background 0.15s;
  }
  .btn-refresh:hover { border-color: var(--primary); background: var(--primary-light); color: var(--primary); }
  .btn-refresh:disabled { opacity: 0.6; cursor: not-allowed; }

  /* ── Toolbar ────────────────────────────────────────────── */
  .orders-toolbar {
    display: flex;
    gap: 10px;
    align-items: center;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }
  .orders-filter { display: flex; gap: 6px; flex-wrap: wrap; }
  .orders-filter-btn {
    background: var(--surface);
    border: 1.5px solid var(--border);
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    color: var(--text2);
    transition: all 0.15s;
    display: flex;
    align-items: center;
    gap: 5px;
  }
  .orders-filter-btn:hover,
  .orders-filter-btn.active {
    border-color: var(--primary);
    background: var(--primary-light);
    color: var(--primary);
  }
  .filter-badge {
    background: var(--primary);
    color: white;
    border-radius: 10px;
    padding: 1px 7px;
    font-size: 10px;
    font-weight: 700;
  }
  .orders-filter-btn.active .filter-badge {
    background: var(--primary);
  }

  /* Action buttons */
  .btn-action-warn {
    background: #f59e0b;
    border: none;
    border-radius: 9px;
    padding: 7px 14px;
    color: white;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
  }
  .btn-action-primary {
    background: var(--primary);
    border: none;
    border-radius: 9px;
    padding: 7px 14px;
    color: white;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
  }

  /* ── Search ─────────────────────────────────────────────── */
  .search-wrap { position: relative; }
  .search-box {
    width: 100%;
    background: var(--surface);
    border: 1.5px solid var(--border);
    border-radius: 9px;
    padding: 8px 14px;
    font-size: 13px;
    color: var(--text);
    outline: none;
    transition: border-color 0.15s;
  }
  .search-box:focus { border-color: var(--primary); }

  /* ── Table ──────────────────────────────────────────────── */
  .orders-table-wrap {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius, 12px);
    box-shadow: var(--shadow);
    overflow: hidden;
  }
  .orders-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }
  .orders-table th {
    background: var(--surface2);
    padding: 10px 14px;
    text-align: left;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text2);
    border-bottom: 1px solid var(--border);
  }
  .orders-table td {
    padding: 12px 14px;
    border-bottom: 1px solid var(--border);
    color: var(--text);
    vertical-align: middle;
  }
  .orders-table tr:last-child td { border-bottom: none; }
  .orders-table tr:hover td { background: var(--surface2); }
  .orders-table tr.selected td { background: var(--primary-light); }

  .table-loading,
  .table-empty {
    text-align: center;
    padding: 48px;
    color: var(--text3);
  }
  .table-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
  }

  /* Columns */
  .col-date { white-space: nowrap; color: var(--text2); }
  .order-id-link {
    color: var(--primary);
    font-weight: 600;
    font-size: 12px;
    text-decoration: none;
    cursor: pointer;
  }
  .order-id-link:hover { text-decoration: underline; }
  .buyer-name { font-weight: 600; }
  .buyer-location { font-size: 11px; color: var(--text3); margin-top: 2px; }
  .col-artikel { max-width: 220px; }
  .artikel-name { font-size: 13px; }
  .artikel-id { font-size: 11px; color: var(--text3); margin-top: 2px; }
  .col-tracking { min-width: 140px; }
  .tracking-link {
    color: var(--primary);
    text-decoration: none;
    font-weight: 600;
    font-size: 12px;
    display: block;
  }
  .tracking-link:hover { text-decoration: underline; }
  .tracking-plain { font-size: 12px; }
  .no-tracking { color: var(--text3); font-size: 12px; }
  .btn-add-tracking {
    margin-top: 4px;
    display: block;
    background: var(--primary);
    border: none;
    border-radius: 6px;
    padding: 4px 10px;
    color: white;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.15s;
  }
  .btn-add-tracking:hover { opacity: 0.85; }

  /* ── Status Badges ──────────────────────────────────────── */
  .badge {
    font-size: 11px;
    font-weight: 700;
    padding: 2px 10px;
    border-radius: 20px;
    white-space: nowrap;
  }
  .badge-versendet { background: #f0fdf4; color: #16a34a; }
  .badge-storniert { background: #fef2f2; color: #dc2626; }
  .badge-bezahlt   { background: #fffbeb; color: #d97706; }
  .badge-archiviert { background: var(--surface2); color: var(--text2); }
  :global([data-theme="dark"]) .badge-versendet { background: rgba(34,197,94,0.15); color: #86efac; }
  :global([data-theme="dark"]) .badge-storniert { background: rgba(239,68,68,0.15); color: #fca5a5; }
  :global([data-theme="dark"]) .badge-bezahlt   { background: rgba(245,158,11,0.15); color: #fcd34d; }

  /* ── Modals ─────────────────────────────────────────────── */
  .modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.5);
    backdrop-filter: blur(4px);
    z-index: 1000;
    display: none;
    align-items: center;
    justify-content: center;
  }
  .modal-overlay.open { display: flex; }
  .modal {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 32px;
    width: 95%;
    box-shadow: 0 20px 60px rgba(0,0,0,0.2);
  }
  .modal-title {
    font-size: 18px;
    font-weight: 800;
    margin-bottom: 20px;
    color: var(--text);
  }
  .modal-field { margin-bottom: 16px; }
  .modal-field label {
    display: block;
    font-size: 11px;
    font-weight: 600;
    color: var(--text2);
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 1px;
  }
  .modal-field input,
  .modal-field select,
  .modal-field textarea {
    width: 100%;
    background: var(--surface2);
    border: 1.5px solid var(--border);
    border-radius: 8px;
    padding: 10px 12px;
    color: var(--text);
    font-size: 13px;
    outline: none;
    transition: border-color 0.15s;
    font-family: inherit;
  }
  .modal-field input:focus,
  .modal-field select:focus,
  .modal-field textarea:focus { border-color: var(--primary); }
  .modal-actions {
    display: flex;
    gap: 10px;
    justify-content: flex-end;
    margin-top: 20px;
  }
  .btn-cancel {
    background: transparent;
    border: 1.5px solid var(--border);
    border-radius: 9px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: 600;
    color: var(--text2);
    cursor: pointer;
    transition: all 0.15s;
  }
  .btn-cancel:hover { border-color: var(--text2); color: var(--text); }
  .btn-primary {
    background: var(--primary);
    border: none;
    border-radius: 9px;
    padding: 10px 22px;
    font-size: 13px;
    font-weight: 600;
    color: white;
    cursor: pointer;
    transition: opacity 0.15s;
    width: 100%;
  }
  .btn-primary:hover { opacity: 0.9; }
  .btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

  /* ── Detail Modal Cards ─────────────────────────────────── */
  .detail-card {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px;
  }
  .detail-card-title {
    font-size: 10px;
    font-weight: 700;
    color: var(--text3);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
  }
  .detail-card-body { color: var(--text); }

  /* ── Spinner ────────────────────────────────────────────── */
  .spinner {
    width: 18px;
    height: 18px;
    border: 2px solid var(--border);
    border-top-color: var(--primary);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    display: inline-block;
  }
  .spinner-sm {
    width: 14px;
    height: 14px;
    border: 2px solid rgba(255,255,255,0.4);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    display: inline-block;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Toast ──────────────────────────────────────────────── */
  .toast {
    position: fixed;
    bottom: 24px;
    right: 24px;
    z-index: 9999;
    padding: 12px 20px;
    border-radius: 12px;
    font-size: 13px;
    font-weight: 600;
    box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    animation: slideIn 0.25s ease;
  }
  .toast-success { background: #22c55e; color: white; }
  .toast-error   { background: #ef4444; color: white; }
  .toast-info    { background: var(--primary); color: white; }
  @keyframes slideIn {
    from { transform: translateY(20px); opacity: 0; }
    to   { transform: translateY(0);    opacity: 1; }
  }

  /* ── Responsive ─────────────────────────────────────────── */
  @media (max-width: 768px) {
    .orders-table { font-size: 12px; }
    .orders-table th, .orders-table td { padding: 8px 10px; }
    .col-artikel { display: none; }
    .detail-card { grid-column: span 2; }
  }
</style>
