<script>
  import { onMount } from 'svelte';
  import { currentUser } from '$lib/stores.js';
  import { apiCall, getToken, API } from '$lib/api.js';
  import { showToast } from '$lib/stores.js';

  let user;
  currentUser.subscribe(v => user = v);

  // State
  let allMessages = [];
  let currentFolder = 'alle';
  let selectedMsgId = null;
  let searchQuery = '';
  let loading = true;
  let refreshing = false;
  let deletedIds = [];
  let reviseHistory = {};

  const folderLabels = {
    alle: 'Posteingang', mitglieder: 'Mitglieder', 'ebay-system': 'eBay-System',
    bearbeitet: 'Gesendet', archiv: 'Archiv', geloescht: 'Gelöscht'
  };

  const folders = [
    { key: 'alle',        icon: '📬', label: 'Posteingang' },
    { key: 'mitglieder',  icon: '👥', label: 'Mitglieder' },
    { key: 'ebay-system', icon: '🔔', label: 'eBay-System' },
    { key: '_divider1' },
    { key: 'bearbeitet',  icon: '📩', label: 'Gesendet' },
    { key: '_divider2' },
    { key: 'archiv',      icon: '📁', label: 'Archiv' },
    { key: 'geloescht',   icon: '🗑️', label: 'Gelöscht' },
  ];

  const moveFolders = [
    { key: 'alle',        icon: '📥', label: 'Posteingang' },
    { key: 'archiv',      icon: '📁', label: 'Archiv' },
    { key: 'geloescht',   icon: '🗑️', label: 'Gelöscht', danger: true },
  ];

  // Lifecycle
  onMount(() => {
    deletedIds = JSON.parse(sessionStorage.getItem('deleted_ids') || '[]');
    loadNachrichten();
  });

  // ---- DATA ----
  async function loadNachrichten() {
    loading = true;
    try {
      const token = getToken();
      const res = await fetch(API + '/nachrichten?user_id=' + user?.id, {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      const data = await res.json();
      if (!data.success) { showToast('Fehler beim Laden', 'error'); return; }
      allMessages = (data.data || []).filter(m => !deletedIds.includes(m.id)).map(m => {
        if (m.deleted || m.status === 'geloescht') m._folder = 'geloescht';
        else if (m.status === 'archiv' || m.status === 'archiviert') m._folder = 'archiv';
        else m._folder = null;
        return m;
      });
    } catch (e) {
      showToast('Verbindungsfehler', 'error');
    } finally {
      loading = false;
    }
  }

  async function fetchNachrichten() {
    refreshing = true;
    showToast('Nachrichten werden von eBay abgerufen...', 'success');
    try {
      const token = getToken();
      await fetch(API + '/nachrichten-abrufen', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: user?.id, ebay_username: user?.ebay_user_id })
      });
      await new Promise(r => setTimeout(r, 3000));
      await loadNachrichten();
      showToast('Nachrichten aktualisiert ✓', 'success');
    } catch (e) { showToast('Fehler beim Abrufen', 'error'); }
    finally { refreshing = false; }
  }

  // ---- FOLDER LOGIC ----
  function setFolder(folder) {
    currentFolder = folder;
    selectedMsgId = null;
  }

  function getFolderMessages(msgs) {
    switch (currentFolder) {
      case 'alle':        return msgs.filter(m => m._folder !== 'archiv' && m._folder !== 'geloescht');
      case 'mitglieder':  return msgs.filter(m => m.direction !== 'outgoing' && !(m.sender || '').toLowerCase().includes('ebay') && m._folder !== 'archiv' && m._folder !== 'geloescht');
      case 'ebay-system': return msgs.filter(m => (m.sender || '').toLowerCase().includes('ebay') && m._folder !== 'archiv' && m._folder !== 'geloescht');
      case 'bearbeitet':  return msgs.filter(m => m.direction === 'outgoing');
      case 'archiv':      return msgs.filter(m => m._folder === 'archiv');
      case 'geloescht':   return msgs.filter(m => m._folder === 'geloescht');
      default:            return msgs;
    }
  }

  function getFolderCount(folder) {
    const msgs = allMessages;
    switch (folder) {
      case 'alle':        return msgs.filter(m => m._folder !== 'archiv' && m._folder !== 'geloescht').length;
      case 'mitglieder':  return new Set(msgs.filter(m => m.direction !== 'outgoing' && !(m.sender || '').toLowerCase().includes('ebay') && m._folder !== 'archiv' && m._folder !== 'geloescht').map(m => m.sender)).size;
      case 'ebay-system': return msgs.filter(m => (m.sender || '').toLowerCase().includes('ebay') && m._folder !== 'archiv' && m._folder !== 'geloescht').length;
      case 'bearbeitet':  return msgs.filter(m => m.direction === 'outgoing').length;
      case 'archiv':      return msgs.filter(m => m._folder === 'archiv').length;
      case 'geloescht':   return msgs.filter(m => m._folder === 'geloescht').length;
      default: return 0;
    }
  }

  // ---- FILTERED MESSAGES ----
  $: filteredMessages = (() => {
    let msgs = getFolderMessages(allMessages);
    if (currentFolder !== 'bearbeitet') {
      msgs = msgs.filter(m => m.direction !== 'outgoing');
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      msgs = msgs.filter(m => (m.sender || '').toLowerCase().includes(q) || (m.body || '').toLowerCase().includes(q));
    }
    // Group by buyer
    const seen = new Map();
    msgs.forEach(m => {
      const isEbay = (m.sender || '').toLowerCase() === 'ebay';
      if (isEbay) {
        seen.set('ebay|' + m.id, m);
      } else {
        const buyer = m.direction === 'outgoing' ? (m.recipient || '') : (m.sender || '');
        const itemKey = (m.item_id && m.item_id !== 'null') ? m.item_id : '';
        const key = buyer + '|' + itemKey;
        if (!seen.has(key) || new Date(m.received_at) > new Date(seen.get(key).received_at)) {
          seen.set(key, m);
        }
      }
    });
    return Array.from(seen.values()).sort((a, b) => new Date(b.received_at) - new Date(a.received_at));
  })();

  // ---- SELECTED MESSAGE ----
  $: selectedMsg = allMessages.find(m => m.id === selectedMsgId);

  $: thread = (() => {
    if (!selectedMsg) return [];
    const isEbaySystem = (selectedMsg.sender || '').toLowerCase() === 'ebay';
    if (isEbaySystem) return [selectedMsg];
    const buyerName = selectedMsg.direction === 'outgoing'
      ? (selectedMsg.recipient === 'null' ? null : selectedMsg.recipient)
      : (selectedMsg.sender === 'null' ? null : selectedMsg.sender);
    return allMessages.filter(t => {
      const tBuyer = t.direction === 'outgoing'
        ? (t.recipient === 'null' ? null : t.recipient)
        : (t.sender === 'null' ? null : t.sender);
      return tBuyer === buyerName && tBuyer !== null;
    }).sort((a, b) => new Date(a.received_at) - new Date(b.received_at));
  })();

  $: isOutgoingOnly = thread.every(t => t.direction === 'outgoing');

  // ---- THREAD COUNT ----
  function getThreadCount(m) {
    const buyer = m.direction === 'outgoing' ? (m.recipient || '') : (m.sender || '');
    const isEbay = (m.sender || '').toLowerCase() === 'ebay';
    if (isEbay) return 1;
    return allMessages.filter(t => {
      const tb = t.direction === 'outgoing' ? (t.recipient === 'null' ? null : t.recipient) : (t.sender === 'null' ? null : t.sender);
      return tb === buyer;
    }).length;
  }

  // ---- ACTIONS ----
  let replyText = '';
  let kiGenerating = false;
  let showMoveModal = false;
  let reviseOpen = false;
  let reviseInput = '';
  let reviseSending = false;

  $: if (selectedMsg) {
    replyText = (selectedMsg.status === 'gesendet' || selectedMsg._sent_reply) ? '' : (selectedMsg.ai_reply || '');
    reviseOpen = false;
    reviseInput = '';
  }

  async function generateKiReply() {
    if (!selectedMsg) return;
    kiGenerating = true;
    replyText = '⏳ KI generiert...';
    try {
      const token = getToken();
      const res = await fetch(API + '/ki-antwort', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: selectedMsg.id, body: selectedMsg.body, user_id: user?.id, ebay_username: user?.ebay_user_id })
      });
      const data = await res.json();
      if (data.reply) {
        replyText = data.reply;
        const msg = allMessages.find(m => m.id === selectedMsg.id);
        if (msg) msg.ai_reply = data.reply;
        showToast('KI-Antwort generiert ✓', 'success');
      } else {
        replyText = '';
        showToast('KI: keine Antwort', 'error');
      }
    } catch (e) {
      replyText = '';
      showToast('Verbindungsfehler', 'error');
    } finally { kiGenerating = false; }
  }

  async function saveReply() {
    if (!selectedMsg) return;
    try {
      const data = await apiCall('/antwort-update', { id: selectedMsg.id, reply: replyText, user_id: user?.id, ebay_username: user?.ebay_user_id });
      if (data.success) {
        const msg = allMessages.find(m => m.id === selectedMsg.id);
        if (msg) { msg.ai_reply = replyText; msg.status = 'bearbeitet'; }
        allMessages = [...allMessages];
        showToast('Antwort gespeichert ✓', 'success');
      }
    } catch (e) { showToast('Fehler beim Speichern', 'error'); }
  }

  async function sendReply() {
    if (!selectedMsg || !replyText) { showToast('Keine Antwort vorhanden', 'error'); return; }
    let cleaned = replyText.replace(/\*\*(.*?)\*\*/g, '$1').replace(/\*(.*?)\*/g, '$1').replace(/`(.*?)`/g, '$1');
    try {
      const data = await apiCall('/antwort-senden', { id: selectedMsg.id, reply: cleaned, user_id: user?.id, ebay_username: user?.ebay_user_id });
      if (data.success) {
        const msg = allMessages.find(m => m.id === selectedMsg.id);
        if (msg) { msg.status = 'gesendet'; msg.ai_reply = cleaned; msg._sent_reply = true; }
        allMessages = [...allMessages];
        replyText = '';
        showToast('Antwort gesendet ✓', 'success');
      } else showToast('Fehler: ' + (data.message || ''), 'error');
    } catch (e) { showToast('Verbindungsfehler', 'error'); }
  }

  async function moveMessage(targetFolder) {
    if (!selectedMsg) return;
    showMoveModal = false;
    const statusMap = { alle: 'posteingang', 'ebay-system': 'posteingang', bearbeitet: 'bearbeitet', archiv: 'archiv', geloescht: 'geloescht' };
    try {
      const data = await apiCall('/nachricht-verschieben', { id: selectedMsg.id, status: statusMap[targetFolder] || targetFolder, user_id: user?.id });
      if (data.success) {
        showToast('Verschoben: ' + (folderLabels[targetFolder] || targetFolder) + ' ✓', 'success');
        selectedMsgId = null;
        await loadNachrichten();
      } else showToast('Fehler beim Verschieben', 'error');
    } catch (e) { showToast('Fehler beim Verschieben', 'error'); }
  }

  async function deleteMessage() {
    if (!selectedMsg) return;
    if (!confirm('Nachricht wirklich löschen?')) return;
    try {
      const data = await apiCall('/nachricht-loeschen', { id: selectedMsg.id, user_id: user?.id });
      if (data.success) {
        deletedIds = [...deletedIds, selectedMsg.id];
        sessionStorage.setItem('deleted_ids', JSON.stringify(deletedIds));
        allMessages = allMessages.filter(m => m.id !== selectedMsg.id);
        selectedMsgId = null;
        showToast('Nachricht gelöscht ✓', 'success');
      } else showToast('Fehler beim Löschen', 'error');
    } catch (e) { showToast('Verbindungsfehler', 'error'); }
  }

  async function sendRevise() {
    if (!selectedMsg || !reviseInput.trim()) return;
    const id = selectedMsg.id;
    const anweisung = reviseInput.trim();
    reviseInput = '';
    reviseSending = true;
    if (!reviseHistory[id]) reviseHistory[id] = [];
    reviseHistory[id] = [...reviseHistory[id], { role: 'user', content: anweisung }];
    try {
      const token = getToken();
      const res = await fetch(API + '/ki-ueberarbeiten', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          kundennachricht: selectedMsg.body || '',
          aktuelle_antwort: replyText || selectedMsg.ai_reply || '',
          anweisung,
          verlauf: reviseHistory[id].slice(0, -1),
          user_id: user?.id,
          ebay_username: user?.ebay_user_id
        })
      });
      const data = await res.json();
      if (data.success && data.reply) {
        replyText = data.reply;
        const msg = allMessages.find(m => m.id === id);
        if (msg) msg.ai_reply = data.reply;
        reviseHistory[id] = [...reviseHistory[id], { role: 'assistant', content: '✓ Überarbeitet' }];
        showToast('Antwort überarbeitet ✓', 'success');
      } else {
        reviseHistory[id] = [...reviseHistory[id], { role: 'assistant', content: '❌ Fehler' }];
      }
    } catch (e) {
      reviseHistory[id] = [...reviseHistory[id], { role: 'assistant', content: '❌ Verbindungsfehler' }];
    } finally { reviseSending = false; }
  }

  // ---- UTILITIES ----
  function escHtml(str) { return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
  function formatDate(str) {
    if (!str) return '—';
    const d = new Date(str);
    return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' }) + ' ' + d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
  }
  function stripPreview(str) {
    if (!str) return '';
    let s = str.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '');
    s = s.replace(/<[^>]*>/g, ' ');
    s = s.replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
    s = s.replace(/\s{2,}/g, ' ').trim();
    return s.slice(0, 100);
  }
  function renderBody(body) {
    if (!body) return '—';
    let text = body.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '');
    text = text.replace(/<[^>]*>/g, ' ');
    text = text.replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&');
    text = text.replace(/\s{2,}/g, ' ').trim();
    return text || '—';
  }
</script>

<div class="page-header">
  <div>
    <h1 class="page-title">📩 Nachrichten</h1>
    <p class="page-subtitle">eBay Kundennachrichten verwalten</p>
  </div>
  <button class="btn btn-primary" on:click={fetchNachrichten} disabled={refreshing}>
    {refreshing ? '⏳ Lädt...' : '🔄 Aktualisieren'}
  </button>
</div>

<div class="messages-layout">
  <!-- FOLDER SIDEBAR -->
  <div class="folder-sidebar">
    {#each folders as f}
      {#if f.key.startsWith('_divider')}
        <div class="folder-divider"></div>
      {:else}
        <button class="folder-item" class:active={currentFolder === f.key} on:click={() => setFolder(f.key)}>
          <span class="folder-icon">{f.icon}</span>
          <span class="folder-name">{f.label}</span>
          <span class="folder-count" class:active-count={currentFolder === f.key}>{getFolderCount(f.key)}</span>
        </button>
      {/if}
    {/each}
  </div>

  <!-- MESSAGE LIST -->
  <div class="messages-list">
    <div class="list-header">
      <input class="search-box" placeholder="Suchen..." bind:value={searchQuery} />
      <span class="msg-count">{filteredMessages.length}</span>
    </div>
    <div class="messages-scroll">
      {#if loading}
        <div class="loading"><div class="spinner"></div> Lade Nachrichten...</div>
      {:else if filteredMessages.length === 0}
        <div class="empty-state" style="padding:40px 20px;">
          <div style="font-size:32px;opacity:0.3;">✉️</div>
          <p>Keine Nachrichten</p>
        </div>
      {:else}
        {#each filteredMessages as m}
          {@const count = getThreadCount(m)}
          {@const displayName = m.direction === 'outgoing' ? (m.recipient || m.sender || '—') : (m.sender || '—')}
          <button class="msg-item" class:active={m.id === selectedMsgId} on:click={() => selectedMsgId = m.id}>
            <div class="msg-item-top">
              <div class="msg-sender">
                {displayName}
                {#if count > 1}<span class="thread-badge">{count}</span>{/if}
              </div>
              <div class="msg-time">{formatDate(m.received_at)}</div>
            </div>
            <div class="msg-preview">{stripPreview(m.body || '')}</div>
            <div class="msg-tags">
              <span class="tag tag-{m.status}">{m.status === 'bearbeitet' ? 'gesendet' : m.status}</span>
              {#if m.ai_category}<span class="tag tag-{m.ai_category.toLowerCase()}">{m.ai_category}</span>{/if}
              {#if m.is_high_priority}<span class="tag tag-priority">⚡ Priorität</span>{/if}
            </div>
          </button>
        {/each}
      {/if}
    </div>
  </div>

  <!-- DETAIL -->
  <div class="msg-detail">
    {#if !selectedMsg}
      <div class="detail-empty">
        <div class="detail-empty-icon">✉</div>
        <div class="detail-empty-text">Nachricht auswählen</div>
      </div>
    {:else}
      <div class="msg-detail-header">
        <div class="detail-top-row">
          <div class="detail-sender-block">
            <div class="msg-detail-sender">{selectedMsg.sender || '—'}</div>
            <div class="msg-detail-subject">{selectedMsg.subject || ''}</div>
          </div>
          <div class="detail-actions">
            <button class="btn-move-msg" on:click={() => showMoveModal = true}>📂 Verschieben</button>
            <button class="btn-delete-msg" on:click={deleteMessage}>🗑️ Löschen</button>
          </div>
        </div>
        <div class="msg-detail-meta">
          <div class="meta-chip">Status: <span>{selectedMsg.status === 'bearbeitet' ? 'gesendet' : selectedMsg.status}</span></div>
          {#if selectedMsg.item_id}<div class="meta-chip">Artikel: <span>{selectedMsg.item_id}</span></div>{/if}
          <div class="meta-chip">Eingang: <span>{formatDate(selectedMsg.received_at)}</span></div>
        </div>
      </div>

      <div class="msg-detail-body">
        {#each thread as t}
          {@const isOut = t.direction === 'outgoing'}
          {@const isEbay = (t.sender || '').toLowerCase() === 'ebay'}
          <div class="bubble-label">
            {isOut ? '✅' : isEbay ? '🔔' : '✉️'}
            {isOut ? (user?.ebay_user_id || 'Shop') : t.sender || '—'} · {formatDate(t.received_at)}
          </div>
          <div class="bubble" class:bubble-sent={isOut}>
            {renderBody(t.body || '')}
          </div>
          {#if !isOut && t.ai_reply && (t.status === 'gesendet' || t.status === 'bearbeitet')}
            <div class="bubble-label">✅ {user?.ebay_user_id || 'Shop'} (KI) · {formatDate(t.updated_at || t.received_at)}</div>
            <div class="bubble bubble-sent">{renderBody(t.ai_reply)}</div>
          {/if}
        {/each}
      </div>

      {#if !isOutgoingOnly}
        <div class="ai-section">
          <div class="ai-section-header">
            <div class="ai-label"><div class="ai-dot"></div> KI-Antwort</div>
            <div style="display:flex;gap:8px;">
              <button class="btn-revise" on:click={() => reviseOpen = !reviseOpen}>✏️ Überarbeiten</button>
              <button class="btn-ki-generate" on:click={generateKiReply} disabled={kiGenerating}>
                {kiGenerating ? '⏳ Generiere...' : '✨ KI generieren'}
              </button>
            </div>
          </div>
          <textarea class="ai-textarea" bind:value={replyText} placeholder="KI-Antwort bearbeiten..."></textarea>

          {#if reviseOpen}
            <div class="chat-revise-box open">
              <div class="chat-revise-messages">
                {#if reviseHistory[selectedMsg?.id]}
                  {#each reviseHistory[selectedMsg.id] as msg}
                    <div class={msg.role === 'user' ? 'chat-msg-user' : 'chat-msg-ki'}>{msg.content}</div>
                  {/each}
                {/if}
              </div>
              <div class="chat-revise-input-row">
                <input class="chat-revise-input" bind:value={reviseInput}
                  placeholder="z.B. Mach die Antwort kürzer..."
                  on:keydown={(e) => e.key === 'Enter' && sendRevise()} />
                <button class="chat-revise-send" on:click={sendRevise} disabled={reviseSending}>Senden</button>
              </div>
            </div>
          {/if}

          <div class="reply-actions">
            <button class="btn-save-reply" on:click={saveReply}>💾 Speichern</button>
            <button class="btn-send-reply" on:click={sendReply}>→ An eBay senden</button>
          </div>
        </div>
      {/if}
    {/if}
  </div>
</div>

<!-- MOVE MODAL -->
{#if showMoveModal}
  <div class="modal-overlay" on:click|self={() => showMoveModal = false}>
    <div class="modal-box" style="max-width:340px;">
      <div class="modal-title">📂 Nachricht verschieben</div>
      <p style="font-size:13px;color:var(--text2);margin-bottom:20px;">Zielordner auswählen</p>
      <div style="display:flex;flex-direction:column;gap:8px;">
        {#each moveFolders as f}
          <button class="move-folder-btn" class:move-folder-btn--danger={f.danger} on:click={() => moveMessage(f.key)}>
            <span style="font-size:20px">{f.icon}</span> {f.label}
          </button>
        {/each}
      </div>
      <button class="btn btn-ghost" style="width:100%;margin-top:12px;" on:click={() => showMoveModal = false}>Abbrechen</button>
    </div>
  </div>
{/if}

<style>
  /* LAYOUT */
  .messages-layout { display: flex; height: calc(100vh - 130px); min-height: 500px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden; margin-top: 16px; }

  /* FOLDER SIDEBAR */
  .folder-sidebar { width: 190px; min-width: 150px; flex-shrink: 0; border-right: 1px solid var(--border); background: var(--surface2); display: flex; flex-direction: column; padding: 10px 8px; gap: 2px; overflow-y: auto; }
  .folder-item { display: flex; align-items: center; gap: 9px; padding: 8px 12px; border-radius: 8px; cursor: pointer; transition: all 0.15s; font-size: 13px; font-weight: 500; color: var(--text2); border: none; background: none; font-family: var(--font); width: 100%; text-align: left; }
  .folder-item:hover { background: var(--border); color: var(--text); }
  .folder-item.active { background: var(--primary-light); color: var(--primary); font-weight: 700; }
  :global([data-theme="dark"]) .folder-item.active { background: rgba(255,255,255,0.08); color: #fff; }
  .folder-icon { font-size: 14px; flex-shrink: 0; width: 18px; text-align: center; }
  .folder-name { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .folder-count { background: var(--border); color: var(--text2); font-size: 10px; font-weight: 700; padding: 1px 6px; border-radius: 10px; min-width: 18px; text-align: center; }
  .active-count { background: var(--primary); color: white; }
  :global([data-theme="dark"]) .active-count { background: rgba(255,255,255,0.2); color: #fff; }
  .folder-divider { height: 1px; background: var(--border); margin: 5px 4px; }

  /* MESSAGE LIST */
  .messages-list { width: 320px; min-width: 220px; flex-shrink: 0; border-right: 1px solid var(--border); display: flex; flex-direction: column; overflow: hidden; }
  .list-header { display: flex; align-items: center; gap: 8px; padding: 10px 12px; border-bottom: 1px solid var(--border); }
  .search-box { flex: 1; background: var(--surface2); border: 1.5px solid var(--border); border-radius: 8px; padding: 7px 12px; color: var(--text); font-family: var(--font); font-size: 12px; outline: none; }
  .search-box:focus { border-color: var(--primary); }
  .msg-count { font-size: 10px; font-weight: 700; color: var(--text3); background: var(--surface2); padding: 2px 8px; border-radius: 10px; }
  .messages-scroll { flex: 1; overflow-y: auto; }

  /* MSG ITEMS */
  .msg-item { display: block; width: 100%; padding: 14px 18px; border-bottom: 1px solid var(--border); cursor: pointer; transition: background 0.15s; background: none; border-left: 3px solid transparent; text-align: left; font-family: var(--font); }
  .msg-item:hover { background: var(--surface2); }
  .msg-item.active { background: var(--primary-light); border-left-color: var(--primary); }
  :global([data-theme="dark"]) .msg-item.active { background: rgba(255,255,255,0.05); border-left-color: #fff; }
  .msg-item-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
  .msg-sender { font-size: 13px; font-weight: 700; color: var(--text); }
  .msg-time { font-size: 10px; color: var(--text3); flex-shrink: 0; }
  .msg-preview { font-size: 12px; color: var(--text2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .msg-tags { display: flex; gap: 5px; margin-top: 6px; flex-wrap: wrap; }
  .thread-badge { font-size: 10px; background: var(--primary); color: white; border-radius: 10px; padding: 1px 6px; margin-left: 4px; }
  :global([data-theme="dark"]) .thread-badge { background: rgba(255,255,255,0.2); }
  .tag { font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 6px; }
  .tag-neu { background: rgba(15,46,147,0.08); color: var(--primary); }
  .tag-gesendet, .tag-bearbeitet { background: #f0fdf4; color: #16a34a; }
  .tag-frage { background: #f5f3ff; color: #7c3aed; }
  .tag-beschwerde, .tag-rueckgabe, .tag-priority { background: #fef2f2; color: #dc2626; }
  .tag-bestellung { background: #fffbeb; color: #d97706; }
  :global([data-theme="dark"]) .tag-neu { background: rgba(15,46,147,0.2); color: #93a8e8; }
  :global([data-theme="dark"]) .tag-gesendet, :global([data-theme="dark"]) .tag-bearbeitet { background: rgba(34,197,94,0.15); color: #86efac; }

  /* DETAIL */
  .msg-detail { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; }
  .detail-empty { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; color: var(--text3); }
  .detail-empty-icon { font-size: 48px; opacity: 0.35; }
  .detail-empty-text { font-size: 13px; }
  .msg-detail-header { padding: 18px 26px; border-bottom: 1px solid var(--border); }
  .detail-top-row { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
  .detail-sender-block { min-width: 0; }
  .msg-detail-sender { font-size: 17px; font-weight: 800; }
  .msg-detail-subject { font-size: 13px; color: var(--text2); margin-top: 3px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .detail-actions { display: flex; gap: 6px; flex-shrink: 0; }
  .msg-detail-meta { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
  .meta-chip { font-size: 11px; font-weight: 500; color: var(--text2); background: var(--surface2); border: 1px solid var(--border); padding: 3px 10px; border-radius: 6px; }
  .meta-chip span { color: var(--text); font-weight: 600; }
  .msg-detail-body { flex: 1; overflow-y: auto; padding: 22px 26px; min-height: 0; }
  .bubble-label { font-size: 10px; font-weight: 700; color: var(--text3); letter-spacing: 1px; text-transform: uppercase; margin-bottom: 8px; }
  .bubble { background: var(--surface2); border: 1px solid var(--border); border-radius: var(--radius); padding: 18px 22px; font-size: 14px; line-height: 1.8; white-space: pre-wrap; word-break: break-word; margin-bottom: 16px; }
  .bubble-sent { border-color: #86efac; background: rgba(34,197,94,0.05); }
  :global([data-theme="dark"]) .bubble-sent { background: rgba(34,197,94,0.08); }

  /* AI SECTION */
  .ai-section { padding: 18px 26px; border-top: 1px solid var(--border); flex-shrink: 0; }
  .ai-section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
  .ai-label { font-size: 11px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: var(--primary); display: flex; align-items: center; gap: 8px; }
  .ai-dot { width: 7px; height: 7px; background: var(--primary); border-radius: 50%; animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.3;} }
  .btn-ki-generate { background: linear-gradient(135deg, #6c63ff, #a855f7); border: none; color: white; border-radius: 8px; padding: 7px 16px; font-size: 12px; font-weight: 700; cursor: pointer; transition: all 0.2s; }
  .btn-ki-generate:hover { opacity: 0.85; }
  .btn-ki-generate:disabled { opacity: 0.5; cursor: not-allowed; }
  .ai-textarea { width: 100%; background: var(--surface2); border: 1.5px solid var(--border); border-radius: 10px; padding: 13px 15px; color: var(--text); font-family: var(--font); font-size: 13px; line-height: 1.7; resize: vertical; min-height: 100px; outline: none; }
  .ai-textarea:focus { border-color: var(--primary); }
  .reply-actions { display: flex; gap: 10px; margin-top: 12px; }
  .btn-save-reply { background: var(--surface); border: 1.5px solid var(--border); border-radius: 9px; padding: 10px 18px; color: var(--text2); font-family: var(--font); font-size: 13px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 6px; }
  .btn-save-reply:hover { border-color: var(--primary); color: var(--primary); }
  .btn-send-reply { flex: 1; background: var(--primary); border: none; border-radius: 9px; padding: 10px; color: white; font-family: var(--font); font-size: 13px; font-weight: 700; cursor: pointer; }
  .btn-send-reply:hover { background: var(--primary-dark); }
  .btn-revise { background: var(--surface); border: 1.5px solid #a855f7; border-radius: 9px; padding: 6px 14px; color: #a855f7; font-size: 12px; font-weight: 600; cursor: pointer; }
  .btn-revise:hover { background: #f5f3ff; }
  :global([data-theme="dark"]) .btn-revise:hover { background: rgba(168,85,247,0.1); }

  /* REVISE CHAT */
  .chat-revise-box { margin-top: 10px; border: 1.5px solid #a855f7; border-radius: 12px; overflow: hidden; background: var(--surface2); }
  .chat-revise-messages { max-height: 200px; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 8px; }
  .chat-msg-user { align-self: flex-end; background: #a855f7; color: white; border-radius: 10px 10px 2px 10px; padding: 8px 12px; font-size: 12px; max-width: 80%; }
  .chat-msg-ki { align-self: flex-start; background: var(--surface); border: 1px solid var(--border); border-radius: 10px 10px 10px 2px; padding: 8px 12px; font-size: 12px; max-width: 80%; color: var(--text2); }
  .chat-revise-input-row { display: flex; gap: 8px; padding: 10px 12px; border-top: 1px solid var(--border); background: var(--surface); }
  .chat-revise-input { flex: 1; border: 1.5px solid var(--border); border-radius: 8px; padding: 8px 12px; font-family: var(--font); font-size: 12px; color: var(--text); background: var(--surface2); outline: none; }
  .chat-revise-input:focus { border-color: #a855f7; }
  .chat-revise-send { background: #a855f7; border: none; border-radius: 8px; padding: 8px 14px; color: white; font-size: 12px; font-weight: 700; cursor: pointer; }
  .chat-revise-send:disabled { opacity: 0.5; }

  /* MOVE/DELETE BTNS */
  .btn-move-msg { background: var(--surface); border: 1.5px solid var(--border); color: var(--text); border-radius: 8px; padding: 6px 14px; font-size: 12px; font-weight: 600; cursor: pointer; font-family: var(--font); }
  .btn-move-msg:hover { background: var(--surface2); }
  .btn-delete-msg { background: none; border: 1.5px solid #fca5a5; color: var(--danger); border-radius: 8px; padding: 6px 14px; font-size: 12px; font-weight: 600; cursor: pointer; font-family: var(--font); }
  .btn-delete-msg:hover { background: #fef2f2; }
  :global([data-theme="dark"]) .btn-delete-msg:hover { background: rgba(239,68,68,0.1); }

  /* MOVE MODAL */
  .move-folder-btn { display: flex; align-items: center; gap: 12px; width: 100%; padding: 13px 16px; border-radius: 10px; border: 1.5px solid var(--border); background: var(--surface); color: var(--text); font-size: 14px; font-weight: 600; cursor: pointer; font-family: var(--font); transition: all 0.15s; }
  .move-folder-btn:hover { background: var(--surface2); border-color: var(--primary); color: var(--primary); }
  .move-folder-btn--danger { border-color: #fca5a5; color: var(--danger); }
  .move-folder-btn--danger:hover { background: rgba(239,68,68,0.07); border-color: var(--danger); }
</style>
