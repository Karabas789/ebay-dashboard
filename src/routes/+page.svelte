<script>
  import { onMount, tick } from 'svelte';
  import { currentUser } from '$lib/stores.js';
  import { apiCall, getToken, API } from '$lib/api.js';
  import { showToast } from '$lib/stores.js';

  let user;
  currentUser.subscribe(v => user = v);

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
    } finally { loading = false; }
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

  // ---- FOLDER ----
  function setFolder(folder) { currentFolder = folder; selectedMsgId = null; }

  function getFolderMessages(msgs) {
    switch (currentFolder) {
      case 'alle':        return msgs.filter(m => m._folder !== 'archiv' && m._folder !== 'geloescht');
      case 'mitglieder':  return msgs.filter(m => m.direction !== 'outgoing' && !(m.sender||'').toLowerCase().includes('ebay') && m._folder !== 'archiv' && m._folder !== 'geloescht');
      case 'ebay-system': return msgs.filter(m => (m.sender||'').toLowerCase().includes('ebay') && m._folder !== 'archiv' && m._folder !== 'geloescht');
      case 'bearbeitet':  return msgs.filter(m => m.direction === 'outgoing');
      case 'archiv':      return msgs.filter(m => m._folder === 'archiv');
      case 'geloescht':   return msgs.filter(m => m._folder === 'geloescht');
      default: return msgs;
    }
  }

  function getFolderCount(folder) {
    const msgs = allMessages;
    switch (folder) {
      case 'alle':        return msgs.filter(m => m._folder !== 'archiv' && m._folder !== 'geloescht').length;
      case 'mitglieder':  return new Set(msgs.filter(m => m.direction !== 'outgoing' && !(m.sender||'').toLowerCase().includes('ebay') && m._folder !== 'archiv' && m._folder !== 'geloescht').map(m => m.sender)).size;
      case 'ebay-system': return msgs.filter(m => (m.sender||'').toLowerCase().includes('ebay') && m._folder !== 'archiv' && m._folder !== 'geloescht').length;
      case 'bearbeitet':  return msgs.filter(m => m.direction === 'outgoing').length;
      case 'archiv':      return msgs.filter(m => m._folder === 'archiv').length;
      case 'geloescht':   return msgs.filter(m => m._folder === 'geloescht').length;
      default: return 0;
    }
  }

  $: filteredMessages = (() => {
    let msgs = getFolderMessages(allMessages);
    if (currentFolder !== 'bearbeitet') msgs = msgs.filter(m => m.direction !== 'outgoing');
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      msgs = msgs.filter(m => (m.sender||'').toLowerCase().includes(q) || (m.body||'').toLowerCase().includes(q));
    }
    const seen = new Map();
    msgs.forEach(m => {
      const isEbay = (m.sender||'').toLowerCase() === 'ebay';
      if (isEbay) { seen.set('ebay|' + m.id, m); }
      else {
        const buyer = m.direction === 'outgoing' ? (m.recipient||'') : (m.sender||'');
        const itemKey = (m.item_id && m.item_id !== 'null') ? m.item_id : '';
        const key = buyer + '|' + itemKey;
        if (!seen.has(key) || new Date(m.received_at) > new Date(seen.get(key).received_at)) seen.set(key, m);
      }
    });
    return Array.from(seen.values()).sort((a, b) => new Date(b.received_at) - new Date(a.received_at));
  })();

  $: selectedMsg = allMessages.find(m => m.id === selectedMsgId);

  $: thread = (() => {
    if (!selectedMsg) return [];
    const isEbay = (selectedMsg.sender||'').toLowerCase() === 'ebay';
    if (isEbay) return [selectedMsg];
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

  function getThreadCount(m) {
    const buyer = m.direction === 'outgoing' ? (m.recipient||'') : (m.sender||'');
    if ((m.sender||'').toLowerCase() === 'ebay') return 1;
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
    reviseOpen = false; reviseInput = '';
  }

  async function generateKiReply() {
    if (!selectedMsg) return;
    kiGenerating = true; replyText = '⏳ KI generiert...';
    try {
      const token = getToken();
      const res = await fetch(API + '/ki-antwort', {
        method: 'POST', headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: selectedMsg.id, body: selectedMsg.body, user_id: user?.id, ebay_username: user?.ebay_user_id })
      });
      const data = await res.json();
      if (data.reply) {
        replyText = data.reply;
        const msg = allMessages.find(m => m.id === selectedMsg.id);
        if (msg) msg.ai_reply = data.reply;
        showToast('KI-Antwort generiert ✓', 'success');
      } else { replyText = ''; showToast('KI: keine Antwort', 'error'); }
    } catch (e) { replyText = ''; showToast('Verbindungsfehler', 'error'); }
    finally { kiGenerating = false; }
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
        allMessages = [...allMessages]; replyText = '';
        showToast('Antwort gesendet ✓', 'success');
      } else showToast('Fehler: ' + (data.message||''), 'error');
    } catch (e) { showToast('Verbindungsfehler', 'error'); }
  }

  async function moveMessage(targetFolder) {
    if (!selectedMsg) return;
    showMoveModal = false;
    const statusMap = { alle: 'posteingang', archiv: 'archiv', geloescht: 'geloescht' };
    try {
      const data = await apiCall('/nachricht-verschieben', { id: selectedMsg.id, status: statusMap[targetFolder] || targetFolder, user_id: user?.id });
      if (data.success) {
        showToast('Verschoben: ' + (folderLabels[targetFolder]||targetFolder) + ' ✓', 'success');
        selectedMsgId = null; await loadNachrichten();
      } else showToast('Fehler beim Verschieben', 'error');
    } catch (e) { showToast('Fehler beim Verschieben', 'error'); }
  }

  async function deleteMessage() {
    if (!selectedMsg || !confirm('Nachricht wirklich löschen?')) return;
    try {
      const data = await apiCall('/nachricht-loeschen', { id: selectedMsg.id, user_id: user?.id });
      if (data.success) {
        deletedIds = [...deletedIds, selectedMsg.id];
        sessionStorage.setItem('deleted_ids', JSON.stringify(deletedIds));
        allMessages = allMessages.filter(m => m.id !== selectedMsg.id);
        selectedMsgId = null;
        showToast('Nachricht gelöscht ✓', 'success');
      }
    } catch (e) { showToast('Verbindungsfehler', 'error'); }
  }

  async function sendRevise() {
    if (!selectedMsg || !reviseInput.trim()) return;
    const id = selectedMsg.id;
    const anweisung = reviseInput.trim();
    reviseInput = ''; reviseSending = true;
    if (!reviseHistory[id]) reviseHistory[id] = [];
    reviseHistory[id] = [...reviseHistory[id], { role: 'user', content: anweisung }];
    try {
      const token = getToken();
      const res = await fetch(API + '/ki-ueberarbeiten', {
        method: 'POST', headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
        body: JSON.stringify({ kundennachricht: selectedMsg.body||'', aktuelle_antwort: replyText||selectedMsg.ai_reply||'', anweisung, verlauf: reviseHistory[id].slice(0,-1), user_id: user?.id, ebay_username: user?.ebay_user_id })
      });
      const data = await res.json();
      if (data.success && data.reply) {
        replyText = data.reply;
        const msg = allMessages.find(m => m.id === id);
        if (msg) msg.ai_reply = data.reply;
        reviseHistory[id] = [...reviseHistory[id], { role: 'assistant', content: '✓ Überarbeitet' }];
        showToast('Antwort überarbeitet ✓', 'success');
      } else { reviseHistory[id] = [...reviseHistory[id], { role: 'assistant', content: '❌ Fehler' }]; }
    } catch (e) { reviseHistory[id] = [...reviseHistory[id], { role: 'assistant', content: '❌ Verbindungsfehler' }]; }
    finally { reviseSending = false; }
  }

  // ---- RENDER BODY ----
  // FIX #7: eBay-System als HTML/iframe, Mitglieder als Text
  function isEbayMsg(msg) { return (msg.sender||'').toLowerCase() === 'ebay'; }

  function renderMemberText(body) {
    if (!body) return '—';
    // Extract text from HTML if present
    if (/<html[\s>]/i.test(body) || /<!DOCTYPE/i.test(body) || /<table/i.test(body)) {
      // Try UserInputtedText div
      const utm = body.match(/id=["']UserInputtedText["'][^>]*>([\s\S]*?)<\/div>/i);
      if (utm && utm[1].replace(/<[^>]*>/g,'').trim().length > 1) {
        return utm[1].replace(/<[^>]*>/g,'').trim();
      }
      // Try "Neue Nachricht:" pattern
      const nm = body.match(/Neue Nachricht:\s*([\s\S]*?)<\/p>/i);
      if (nm && nm[1].replace(/<[^>]*>/g,'').trim().length > 3) {
        return nm[1].replace(/<[^>]*>/g,'').trim();
      }
      // Fallback: strip all HTML
      let t = body.replace(/<style[^>]*>[\s\S]*?<\/style>/gi,'');
      t = t.replace(/<script[^>]*>[\s\S]*?<\/script>/gi,'');
      t = t.replace(/<[^>]*>/g,' ');
      t = t.replace(/&nbsp;/g,' ').replace(/&amp;/g,'&').replace(/&lt;/g,'<').replace(/&gt;/g,'>');
      t = t.replace(/\s{2,}/g,' ').trim();
      return t.length > 500 ? t.slice(0,500) + '...' : t;
    }
    // Plain text
    let t = body.replace(/<style[^>]*>[\s\S]*?<\/style>/gi,'');
    t = t.replace(/<[^>]*>/g,' ');
    t = t.replace(/&nbsp;/g,' ').replace(/&amp;/g,'&');
    t = t.replace(/\s{2,}/g,' ').trim();
    return t || '—';
  }

  function setupIframe(node, body) {
    const isDark = document.documentElement.dataset.theme === 'dark';
    const darkCss = 'body{font-family:Arial,sans-serif;font-size:14px;margin:8px;color:#d1d1d1;background:#1c1c1c}a{color:#8ab4f8}';
    const lightCss = 'body{font-family:Arial,sans-serif;font-size:14px;margin:8px;color:#333}';
    const css = isDark ? darkCss : lightCss;
    const styleTag = '<' + 'style>' + css + '</' + 'style>';
    let htmlContent = body;
    if (!/<html[\s>]/i.test(body)) {
      htmlContent = '<!DOCTYPE html><html><head><meta charset=utf-8>' + styleTag + '</head><body>' + body + '</body></html>';
    }
    const doc = node.contentDocument || node.contentWindow.document;
    doc.open(); doc.write(htmlContent); doc.close();
    setTimeout(() => {
      try { node.style.height = Math.min(Math.max(doc.body.scrollHeight + 20, 100), 600) + 'px'; } catch(e){}
    }, 300);
  }
  function escHtml(str) { return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
  function formatDate(str) {
    if (!str) return '—';
    const d = new Date(str);
    return d.toLocaleDateString('de-DE',{day:'2-digit',month:'2-digit'}) + ' ' + d.toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'});
  }
  function stripPreview(str) {
    if (!str) return '';
    let s = str.replace(/<style[^>]*>[\s\S]*?<\/style>/gi,'');
    s = s.replace(/<[^>]*>/g,' ').replace(/&nbsp;/g,' ').replace(/&amp;/g,'&');
    return s.replace(/\s{2,}/g,' ').trim().slice(0,100);
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

<div class="msg-layout">
  <!-- FOLDERS -->
  <div class="folders">
    {#each folders as f}
      {#if f.key.startsWith('_')}
        <div class="f-divider"></div>
      {:else}
        <button class="f-item" class:f-active={currentFolder === f.key} on:click={() => setFolder(f.key)}>
          <span class="f-icon">{f.icon}</span>
          <span class="f-name">{f.label}</span>
          <span class="f-count" class:f-count-active={currentFolder === f.key}>{getFolderCount(f.key)}</span>
        </button>
      {/if}
    {/each}
  </div>

  <!-- LIST -->
  <div class="list">
    <div class="list-top">
      <input class="list-search" placeholder="Suchen..." bind:value={searchQuery} />
      <span class="list-num">{filteredMessages.length}</span>
    </div>
    <div class="list-scroll">
      {#if loading}
        <div class="loading"><div class="spinner"></div> Lade...</div>
      {:else if filteredMessages.length === 0}
        <div class="empty-state" style="padding:40px 20px;"><p>Keine Nachrichten</p></div>
      {:else}
        {#each filteredMessages as m}
          {@const count = getThreadCount(m)}
          {@const name = m.direction === 'outgoing' ? (m.recipient||m.sender||'—') : (m.sender||'—')}
          <button class="li" class:li-active={m.id === selectedMsgId} on:click={() => selectedMsgId = m.id}>
            <div class="li-top">
              <span class="li-name">{name}{#if count > 1}<span class="li-badge">{count}</span>{/if}</span>
              <span class="li-time">{formatDate(m.received_at)}</span>
            </div>
            <div class="li-preview">{stripPreview(m.body||'')}</div>
            <div class="li-tags">
              <span class="t t-{m.status}">{m.status === 'bearbeitet' ? 'gesendet' : m.status}</span>
              {#if m.ai_category}<span class="t t-{m.ai_category.toLowerCase()}">{m.ai_category}</span>{/if}
            </div>
          </button>
        {/each}
      {/if}
    </div>
  </div>

  <!-- DETAIL -->
  <div class="detail">
    {#if !selectedMsg}
      <div class="detail-empty">
        <div style="font-size:48px;opacity:0.3;">✉</div>
        <div style="font-size:13px;color:var(--text3);">Nachricht auswählen</div>
      </div>
    {:else}
      <!-- HEADER -->
      <div class="d-header">
        <div class="d-header-row">
          <div style="min-width:0;flex:1;">
            <div class="d-sender">{selectedMsg.sender||'—'}</div>
            <div class="d-subject">{selectedMsg.subject||''}</div>
          </div>
          <div class="d-btns">
            <button class="d-btn" on:click={() => showMoveModal = true}>📂 Verschieben</button>
            <button class="d-btn d-btn-danger" on:click={deleteMessage}>🗑️ Löschen</button>
          </div>
        </div>
        <div class="d-meta">
          <span class="d-chip">Status: <b>{selectedMsg.status === 'bearbeitet' ? 'gesendet' : selectedMsg.status}</b></span>
          {#if selectedMsg.item_id && selectedMsg.item_id !== 'null'}<span class="d-chip">Artikel: <b>{selectedMsg.item_id}</b></span>{/if}
          <span class="d-chip">Eingang: <b>{formatDate(selectedMsg.received_at)}</b></span>
        </div>
      </div>

      <!-- THREAD BODY (scrollable) -->
      <div class="d-body">
        {#each thread as t}
          {@const isOut = t.direction === 'outgoing'}
          {@const isEbay = (t.sender||'').toLowerCase() === 'ebay'}
          <div class="bubble-label">
            {isOut ? '✅' : isEbay ? '🔔' : '✉️'}
            {isOut ? (user?.ebay_user_id||'Shop') : (t.sender||'—')} · {formatDate(t.received_at)}
          </div>
          {#if isEbay && (/<html[\s>]/i.test(t.body||'') || /<!DOCTYPE/i.test(t.body||'') || /<table/i.test(t.body||''))}
            <div class="bubble">
              <iframe class="ebay-iframe" use:setupIframe={t.body||''} sandbox="allow-same-origin" title="eBay"></iframe>
            </div>
          {:else if isEbay}
            <div class="bubble">{@html escHtml(t.body||'—').replace(/\n/g,'<br>')}</div>
          {:else}
            <div class="bubble" class:bubble-sent={isOut}>
              {renderMemberText(t.body||'')}
            </div>
          {/if}
          {#if !isOut && t.ai_reply && (t.status === 'gesendet' || t.status === 'bearbeitet')}
            <div class="bubble-label">✅ {user?.ebay_user_id||'Shop'} (KI) · {formatDate(t.updated_at||t.received_at)}</div>
            <div class="bubble bubble-sent">{renderMemberText(t.ai_reply)}</div>
          {/if}
        {/each}
      </div>

      <!-- AI SECTION (fixed bottom) -->
      {#if !isOutgoingOnly}
        <div class="d-ai">
          <div class="d-ai-top">
            <div class="d-ai-label"><span class="d-ai-dot"></span> KI-ANTWORT</div>
            <div style="display:flex;gap:8px;">
              <button class="btn-rev" on:click={() => reviseOpen = !reviseOpen}>✏️ Überarbeiten</button>
              <button class="btn-ki" on:click={generateKiReply} disabled={kiGenerating}>
                {kiGenerating ? '⏳ ...' : '✨ KI generieren'}
              </button>
            </div>
          </div>
          <textarea class="d-ai-text" bind:value={replyText} placeholder="KI-Antwort bearbeiten..." rows="5"></textarea>
          {#if reviseOpen}
            <div class="rev-box">
              <div class="rev-msgs">
                {#if reviseHistory[selectedMsg?.id]}
                  {#each reviseHistory[selectedMsg.id] as msg}
                    <div class={msg.role === 'user' ? 'rev-user' : 'rev-ki'}>{msg.content}</div>
                  {/each}
                {/if}
              </div>
              <div class="rev-input-row">
                <input class="rev-input" bind:value={reviseInput} placeholder="z.B. Mach die Antwort kürzer..." on:keydown={(e) => e.key === 'Enter' && sendRevise()} />
                <button class="rev-send" on:click={sendRevise} disabled={reviseSending}>Senden</button>
              </div>
            </div>
          {/if}
          <div class="d-ai-actions">
            <button class="d-ai-save" on:click={saveReply}>💾 Speichern</button>
            <button class="d-ai-send" on:click={sendReply}>→ An eBay senden</button>
          </div>
        </div>
      {/if}
    {/if}
  </div>
</div>

<!-- FIX #1: MODAL als fixed overlay mit z-index -->
{#if showMoveModal}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <div class="move-overlay" on:click|self={() => showMoveModal = false}>
    <div class="move-box">
      <div style="font-size:16px;font-weight:800;margin-bottom:6px;">📂 Nachricht verschieben</div>
      <p style="font-size:13px;color:var(--text2);margin-bottom:20px;">Zielordner auswählen</p>
      {#each moveFolders as f}
        <button class="move-btn" class:move-btn-danger={f.danger} on:click={() => moveMessage(f.key)}>
          <span style="font-size:20px;">{f.icon}</span> {f.label}
        </button>
      {/each}
      <button class="move-cancel" on:click={() => showMoveModal = false}>Abbrechen</button>
    </div>
  </div>
{/if}

<style>
  /* FIX #2/#3: Layout fills viewport width */
  .msg-layout {
    display: flex; height: calc(100vh - 130px); min-height: 400px;
    background: var(--surface); 
    border-radius: var(--radius); overflow: hidden; margin-top: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); border-color: var(--border);
  }

  /* FOLDERS */
  .folders { width: 180px; flex-shrink: 0; border-right: 1px solid var(--border); background: var(--surface2); padding: 10px 8px; display: flex; flex-direction: column; gap: 2px; overflow-y: auto; }
  .f-item { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 500; color: var(--text2); border: none; background: none; font-family: var(--font); width: 100%; text-align: left; transition: all 0.12s; }
  .f-item:hover { background: var(--border); color: var(--text); }
  .f-active { background: var(--primary-light); color: var(--primary); font-weight: 700; }
  :global([data-theme="dark"]) .f-active { background: rgba(255,255,255,0.08); color: #fff; }
  .f-icon { font-size: 14px; width: 18px; text-align: center; }
  .f-name { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .f-count { background: var(--border); color: var(--text2); font-size: 10px; font-weight: 700; padding: 1px 6px; border-radius: 10px; min-width: 18px; text-align: center; }
  .f-count-active { background: var(--primary); color: white; }
  :global([data-theme="dark"]) .f-count-active { background: rgba(255,255,255,0.2); color: #fff; }
  .f-divider { height: 1px; background: var(--border); margin: 4px; }

  /* LIST */
  .list { width: 300px; flex-shrink: 0; border-right: 1px solid var(--border); display: flex; flex-direction: column; }
  .list-top { display: flex; align-items: center; gap: 8px; padding: 10px 12px; border-bottom: 1px solid var(--border); }
  .list-search { flex: 1; background: var(--surface2); border: 1px solid var(--border); border-radius: 8px; padding: 7px 12px; color: var(--text); font-family: var(--font); font-size: 12px; outline: none; }
  .list-search:focus { border-color: var(--primary); }
  .list-num { font-size: 10px; font-weight: 700; color: var(--text3); background: var(--surface2); padding: 2px 8px; border-radius: 10px; }
  .list-scroll { flex: 1; overflow-y: auto; }

  /* LIST ITEMS */
  .li { display: block; width: 100%; padding: 12px 16px; border: none; outline: none; border-bottom: 1px solid var(--border); cursor: pointer; background: none;  text-align: left; font-family: var(--font); transition: background 0.1s; }
  .li:hover { background: var(--surface2); }
  .li-active { background: var(--border); }
  :global([data-theme="dark"]) .li-active { background: rgba(255,255,255,0.05); border-left-color: #fff; }
  .li-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px; }
  .li-name { font-size: 13px; font-weight: 700; color: var(--text); }
  .li-time { font-size: 10px; color: var(--text3); }
  .li-preview { font-size: 12px; color: var(--text2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .li-tags { display: flex; gap: 4px; margin-top: 5px; }
  .li-badge { font-size: 10px; background: var(--primary); color: white; border-radius: 10px; padding: 1px 6px; margin-left: 4px; }
  .t { font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 6px; }
  .t-neu { background: rgba(15,46,147,0.08); color: var(--primary); }
  .t-gesendet, .t-bearbeitet { background: #f0fdf4; color: #16a34a; }
  .t-new { background: rgba(15,46,147,0.08); color: var(--primary); }
  :global([data-theme="dark"]) .t-neu, :global([data-theme="dark"]) .t-new { background: rgba(15,46,147,0.2); color: #93a8e8; }
  :global([data-theme="dark"]) .t-gesendet, :global([data-theme="dark"]) .t-bearbeitet { background: rgba(34,197,94,0.15); color: #86efac; }

  /* DETAIL - FIX #3: flex-1 fills remaining width */
  .detail { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; }
  .detail-empty { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; }
  .d-header { padding: 16px 24px; border-bottom: 1px solid var(--border); flex-shrink: 0; }
  .d-header-row { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
  .d-sender { font-size: 17px; font-weight: 800; }
  .d-subject { font-size: 13px; color: var(--text2); margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .d-btns { display: flex; gap: 6px; flex-shrink: 0; }
  .d-btn { background: var(--surface2); border: 1px solid var(--border); color: var(--text); border-radius: 8px; padding: 6px 14px; font-size: 12px; font-weight: 600; cursor: pointer; font-family: var(--font); transition: all 0.15s; }
  .d-btn:hover { border-color: var(--primary); color: var(--primary); }
  .d-btn-danger { border-color: #fca5a5; color: var(--danger); }
  .d-btn-danger:hover { background: #fef2f2; border-color: var(--danger); }
  :global([data-theme="dark"]) .d-btn-danger:hover { background: rgba(239,68,68,0.1); }
  .d-meta { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
  .d-chip { font-size: 11px; color: var(--text2); background: var(--surface2); border: 1px solid var(--border); padding: 3px 10px; border-radius: 6px; }
  .d-chip b { color: var(--text); }

  /* FIX #5: no black border on body */
  .d-body { flex: 1; overflow-y: auto; padding: 20px 24px; min-height: 0; }
  .bubble-label { font-size: 10px; font-weight: 700; color: var(--text3); letter-spacing: 1px; text-transform: uppercase; margin-bottom: 8px; }
  .bubble { background: var(--surface2); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px 20px; font-size: 14px; line-height: 1.8; white-space: pre-wrap; word-break: break-word; margin-bottom: 16px; }
  .bubble-sent { border-color: #86efac; background: rgba(34,197,94,0.05); }
  :global([data-theme="dark"]) .bubble-sent { background: rgba(34,197,94,0.08); }

  /* FIX #7: eBay iframe */
  .ebay-iframe { width: 100%; height: 300px; border: none; border-radius: 8px; background: #fff; }

  /* AI SECTION - FIX #6: larger textarea */
  .d-ai { padding: 16px 24px; border-top: 1px solid var(--border); flex-shrink: 0; }
  .d-ai-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
  .d-ai-label { font-size: 11px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: var(--primary); display: flex; align-items: center; gap: 8px; }
  .d-ai-dot { width: 7px; height: 7px; background: var(--primary); border-radius: 50%; animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.3;} }
  .btn-ki { background: linear-gradient(135deg, #6c63ff, #a855f7); border: none; color: white; border-radius: 8px; padding: 7px 16px; font-size: 12px; font-weight: 700; cursor: pointer; }
  .btn-ki:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-rev { background: var(--surface); border: 1.5px solid #a855f7; border-radius: 8px; padding: 6px 14px; color: #a855f7; font-size: 12px; font-weight: 600; cursor: pointer; }
  /* FIX #6: min-height 150px statt 100px */
  .d-ai-text { width: 100%; background: var(--surface2); border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px; color: var(--text); font-family: var(--font); font-size: 13px; line-height: 1.7; resize: vertical; min-height: 150px; outline: none; }
  .d-ai-text:focus { border-color: var(--primary); }
  .d-ai-actions { display: flex; gap: 10px; margin-top: 10px; }
  .d-ai-save { background: var(--surface); border: 1px solid var(--border); border-radius: 9px; padding: 10px 18px; color: var(--text2); font-family: var(--font); font-size: 13px; font-weight: 600; cursor: pointer; }
  .d-ai-save:hover { border-color: var(--primary); color: var(--primary); }
  .d-ai-send { flex: 1; background: var(--primary); border: none; border-radius: 9px; padding: 10px; color: white; font-family: var(--font); font-size: 13px; font-weight: 700; cursor: pointer; }
  .d-ai-send:hover { background: var(--primary-dark); }

  /* FIX #6: Revise box larger */
  .rev-box { margin-top: 10px; border: 1.5px solid #a855f7; border-radius: 12px; overflow: hidden; background: var(--surface2); }
  .rev-msgs { max-height: 200px; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 8px; }
  .rev-user { align-self: flex-end; background: #a855f7; color: white; border-radius: 10px 10px 2px 10px; padding: 8px 12px; font-size: 12px; max-width: 80%; }
  .rev-ki { align-self: flex-start; background: var(--surface); border: 1px solid var(--border); border-radius: 10px 10px 10px 2px; padding: 8px 12px; font-size: 12px; max-width: 80%; color: var(--text2); }
  .rev-input-row { display: flex; gap: 8px; padding: 10px 12px; border-top: 1px solid var(--border); background: var(--surface); }
  .rev-input { flex: 1; border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px; font-family: var(--font); font-size: 13px; color: var(--text); background: var(--surface2); outline: none; }
  .rev-input:focus { border-color: #a855f7; }
  .rev-send { background: #a855f7; border: none; border-radius: 8px; padding: 10px 16px; color: white; font-size: 12px; font-weight: 700; cursor: pointer; }
  .rev-send:disabled { opacity: 0.5; }

  /* FIX #1: Modal as FIXED overlay */
  .move-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); backdrop-filter: blur(4px); z-index: 9999; display: flex; align-items: center; justify-content: center; }
  .move-box { background: var(--surface); border-radius: 16px; padding: 28px 24px; max-width: 340px; width: 90%; box-shadow: 0 20px 60px rgba(0,0,0,0.3); display: flex; flex-direction: column; gap: 8px; }
  .move-btn { display: flex; align-items: center; gap: 12px; width: 100%; padding: 13px 16px; border-radius: 10px; border: 1px solid var(--border); background: var(--surface); color: var(--text); font-size: 14px; font-weight: 600; cursor: pointer; font-family: var(--font); transition: all 0.15s; }
  .move-btn:hover { background: var(--surface2); border-color: var(--primary); color: var(--primary); }
  .move-btn-danger { border-color: #fca5a5; color: var(--danger); }
  .move-btn-danger:hover { background: rgba(239,68,68,0.07); border-color: var(--danger); color: var(--danger); }
  .move-cancel { margin-top: 8px; width: 100%; padding: 10px; border-radius: 10px; border: 1px solid var(--border); background: none; color: var(--text2); font-size: 13px; font-weight: 600; cursor: pointer; font-family: var(--font); }
</style>
