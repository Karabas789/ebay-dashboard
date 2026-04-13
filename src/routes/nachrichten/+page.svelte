<script>
  import { onMount, tick } from 'svelte';
  import { currentUser } from '$lib/stores.js';
  import { apiCall, getToken, API } from '$lib/api.js';
  import ConfirmModal from '$lib/components/ConfirmModal.svelte';
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
  let customFolders = [];
  let showNewFolderModal = false;
  let confirmModal = { open: false, title: '', message: '', variant: 'danger', onConfirm: () => {} };
  let newFolderName = '';
  let newFolderIcon = '📂';

  // Rename Modal State
  let showRenameModal = false;
  let renameFolderId = null;
  let renameValue = '';

  // Reply Modal State (Bug 1 Fix)
  let showReplyModal = false;
  let replyText = '';
  let kiGenerating = false;
  let reviseOpen = false;
  let reviseInput = '';
  let reviseSending = false;

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
    loadCustomFolders();
  });

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
        else if (m.folder_id) m._folder = 'custom_' + m.folder_id;
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

  function setFolder(folder) { currentFolder = folder; selectedMsgId = null; }

  function getFolderMessages(msgs) {
    switch (currentFolder) {
      case 'alle':        return msgs.filter(m => m._folder !== 'archiv' && m._folder !== 'geloescht');
      case 'mitglieder':  return msgs.filter(m => m.direction !== 'outgoing' && !(m.sender||'').toLowerCase().includes('ebay') && m._folder !== 'archiv' && m._folder !== 'geloescht');
      case 'ebay-system': return msgs.filter(m => (m.sender||'').toLowerCase().includes('ebay') && m._folder !== 'archiv' && m._folder !== 'geloescht');
      case 'bearbeitet':  return msgs.filter(m => m.direction === 'outgoing');
      case 'archiv':      return msgs.filter(m => m._folder === 'archiv');
      case 'geloescht':   return msgs.filter(m => m._folder === 'geloescht');
      default:
        if (currentFolder.startsWith('custom_')) {
          const fid = parseInt(currentFolder.replace('custom_', ''));
          return msgs.filter(m => m.folder_id === fid);
        }
        return msgs;
    }
  }

  $: unreadCounts = (() => {
    const counts = {};
    const unread = m => m.is_read === false;
    const msgs = allMessages;

    function countUnreadThreads(filtered) {
      const seen = new Set();
      filtered.filter(unread).forEach(m => {
        const isEbay = (m.sender||'').toLowerCase() === 'ebay';
        if (isEbay) { seen.add('ebay_' + m.id); }
        else {
          const buyer = m.direction === 'outgoing' ? (m.recipient||'') : (m.sender||'');
          seen.add(buyer);
        }
      });
      return seen.size;
    }

    counts.alle = countUnreadThreads(msgs.filter(m => m.direction !== 'outgoing' && m._folder !== 'archiv' && m._folder !== 'geloescht'));
    counts.mitglieder = countUnreadThreads(msgs.filter(m => m.direction !== 'outgoing' && !(m.sender||'').toLowerCase().includes('ebay') && m._folder !== 'archiv' && m._folder !== 'geloescht'));
    counts.ebay_system = countUnreadThreads(msgs.filter(m => (m.sender||'').toLowerCase().includes('ebay') && m._folder !== 'archiv' && m._folder !== 'geloescht'));
    counts.bearbeitet = countUnreadThreads(msgs.filter(m => m.direction === 'outgoing'));
    counts.archiv = countUnreadThreads(msgs.filter(m => m._folder === 'archiv'));
    counts.geloescht = countUnreadThreads(msgs.filter(m => m._folder === 'geloescht'));

    if (customFolders) {
      customFolders.forEach(cf => {
        counts['custom_' + cf.id] = msgs.filter(m => m.folder_id === cf.id && unread(m)).length;
      });
    }
    return counts;
  })();

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

  let showMoveModal = false;

  function autoGrow(e) {
    const el = e.target;
    el.style.height = "auto";
    el.style.height = Math.max(80, Math.min(el.scrollHeight, window.innerHeight * 0.35)) + "px";
  }

  // Open Reply Modal
  function openReplyModal() {
    if (!selectedMsg) return;
    replyText = (selectedMsg.status === 'gesendet' || selectedMsg._sent_reply) ? '' : (selectedMsg.ai_reply || '');
    reviseOpen = false;
    reviseInput = '';
    showReplyModal = true;
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
        showReplyModal = false;
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
    if (!selectedMsg) return;
    confirmModal = { open: true, title: 'Nachricht löschen', message: 'Möchtest du diese Nachricht wirklich löschen?', variant: 'danger', onConfirm: async () => {
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
    }};
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

  // ---- CUSTOM FOLDERS ----
  async function loadCustomFolders() {
    try {
      const data = await apiCall('/nachricht-ordner', { action: 'list', user_id: user?.id });
      if (data.success) customFolders = data.folders || [];
    } catch(e) {}
  }

  async function createFolder() {
    if (!newFolderName.trim()) return;
    try {
      const data = await apiCall('/nachricht-ordner', { action: 'create', user_id: user?.id, name: newFolderName.trim(), icon: newFolderIcon });
      if (data.success) {
        showNewFolderModal = false; newFolderName = ''; newFolderIcon = '📂';
        await loadCustomFolders();
        showToast('Ordner erstellt', 'success');
      }
    } catch(e) { showToast('Fehler beim Erstellen', 'error'); }
  }

  async function deleteFolder(folderId) {
    confirmModal = { open: true, title: 'Ordner löschen', message: 'Nachrichten werden in den Posteingang verschoben.', variant: 'warning', onConfirm: async () => {
    try {
      const data = await apiCall('/nachricht-ordner', { action: 'delete', user_id: user?.id, folder_id: folderId });
      if (data.success) {
        if (currentFolder === 'custom_' + folderId) { currentFolder = 'alle'; selectedMsgId = null; }
        await loadCustomFolders(); await loadNachrichten();
        showToast('Ordner gelöscht', 'success');
      }
    } catch(e) { showToast('Fehler', 'error'); }
  }};
  }

  function renameFolder(folderId) {
    const folder = customFolders.find(f => f.id === folderId);
    renameFolderId = folderId;
    renameValue = folder?.name || '';
    showRenameModal = true;
  }

  async function confirmRenameFolder() {
    if (!renameValue.trim() || !renameFolderId) return;
    try {
      const data = await apiCall('/nachricht-ordner', { action: 'rename', user_id: user?.id, folder_id: renameFolderId, name: renameValue.trim() });
      if (data.success) {
        showRenameModal = false;
        renameFolderId = null;
        renameValue = '';
        await loadCustomFolders();
        showToast('Umbenannt ✓', 'success');
      }
    } catch(e) { showToast('Fehler', 'error'); }
  }

  async function moveToFolder(target) {
    if (!selectedMsg) return;
    showMoveModal = false;
    try {
      const data = await apiCall('/nachricht-ordner', { action: 'move', user_id: user?.id, message_id: selectedMsg.id, target: target });
      if (data.success) {
        selectedMsgId = null; await loadNachrichten();
        showToast('Verschoben', 'success');
      } else showToast('Fehler', 'error');
    } catch(e) { showToast('Fehler', 'error'); }
  }

  async function markAsRead(msgId) {
    const msg = allMessages.find(m => m.id === msgId);
    if (!msg || msg.is_read) return;
    const isEbay = (msg.sender||'').toLowerCase() === 'ebay';
    let threadIds;
    if (isEbay) {
      threadIds = [msg.id];
    } else {
      const buyer = msg.direction === 'outgoing' ? msg.recipient : msg.sender;
      threadIds = allMessages.filter(m => {
        const b = m.direction === 'outgoing' ? m.recipient : m.sender;
        return b === buyer && b !== null && b !== 'null';
      }).filter(m => !m.is_read).map(m => m.id);
    }
    if (threadIds.length === 0) return;
    try {
      await apiCall('/nachricht-ordner', { action: 'read', user_id: user?.id, message_ids: threadIds, set_read: true });
      threadIds.forEach(id => {
        const m = allMessages.find(x => x.id === id);
        if (m) m.is_read = true;
      });
      allMessages = [...allMessages];
    } catch(e) {}
  }

  async function toggleRead(msgId) {
    const msg = allMessages.find(m => m.id === msgId);
    if (!msg) return;
    const newState = !(msg.is_read === true);
    const isEbay = (msg.sender||'').toLowerCase() === 'ebay';
    let threadIds;
    if (isEbay) {
      threadIds = [msg.id];
    } else {
      const buyer = msg.direction === 'outgoing' ? msg.recipient : msg.sender;
      threadIds = allMessages.filter(m => {
        const b = m.direction === 'outgoing' ? m.recipient : m.sender;
        return b === buyer && b !== null && b !== 'null';
      }).map(m => m.id);
    }
    try {
      const data = await apiCall('/nachricht-ordner', { action: 'read', user_id: user?.id, message_ids: threadIds, set_read: newState });
      if (data.success) {
        threadIds.forEach(id => {
          const m = allMessages.find(x => x.id === id);
          if (m) m.is_read = newState;
        });
        allMessages = [...allMessages];
      }
    } catch(e) {}
  }

  function isEbayMsg(msg) { return (msg.sender||'').toLowerCase() === 'ebay'; }

  // Bug 2 Fix: Clean XML entities like &#xd; &#xa; etc.
  function cleanXmlEntities(str) {
    if (!str) return str;
    return str
      .replace(/&#x[0-9a-fA-F]+;/g, match => {
        const code = parseInt(match.slice(3, -1), 16);
        // Replace control characters (0x00-0x1F except \n \t) with space or nothing
        if (code <= 0x1F && code !== 0x0A && code !== 0x09) return '';
        return String.fromCharCode(code);
      })
      .replace(/&#\d+;/g, match => {
        const code = parseInt(match.slice(2, -1), 10);
        if (code <= 0x1F && code !== 0x0A && code !== 0x09) return '';
        return String.fromCharCode(code);
      });
  }

  // Bug 3 Fix: Render member text preserving <img> tags
  function renderMemberText(body) {
    if (!body) return '—';
    // First clean XML entities (Bug 2)
    body = cleanXmlEntities(body);

    if (/<html[\s>]/i.test(body) || /<!DOCTYPE/i.test(body) || /<table/i.test(body)) {
      const utm = body.match(/id=["']UserInputtedText["'][^>]*>([\s\S]*?)<\/div>/i);
      if (utm && utm[1].replace(/<[^>]*>/g,'').trim().length > 1) {
        return sanitizeKeepImages(utm[1]);
      }
      const nm = body.match(/Neue Nachricht:\s*([\s\S]*?)<\/p>/i);
      if (nm && nm[1].replace(/<[^>]*>/g,'').trim().length > 3) {
        return sanitizeKeepImages(nm[1]);
      }
      let t = body.replace(/<style[^>]*>[\s\S]*?<\/style>/gi,'');
      t = t.replace(/<script[^>]*>[\s\S]*?<\/script>/gi,'');
      t = sanitizeKeepImages(t);
      t = t.replace(/&nbsp;/g,' ').replace(/&amp;/g,'&').replace(/&lt;/g,'<').replace(/&gt;/g,'>');
      t = t.replace(/\s{2,}/g,' ').trim();
      return t.length > 500 ? t.slice(0,500) + '...' : t;
    }
    let t = body.replace(/<style[^>]*>[\s\S]*?<\/style>/gi,'');
    t = sanitizeKeepImages(t);
    t = t.replace(/&nbsp;/g,' ').replace(/&amp;/g,'&');
    t = t.replace(/\s{2,}/g,' ').trim();
    return t || '—';
  }

  // Bug 3: Strip all HTML tags EXCEPT <img> and <br>
  function sanitizeKeepImages(html) {
    if (!html) return '';
    // Keep <img ...> and <br> tags, remove everything else
    return html.replace(/<(?!\/?(?:img|br)\b)[^>]*>/gi, ' ');
  }

  // Check if body contains images (for deciding render mode)
  function bodyHasImages(body) {
    if (!body) return false;
    return /<img\b[^>]*>/i.test(body);
  }

  function setupIframe(node, body) {
    function render(html) {
      // Clean XML entities before rendering in iframe
      html = cleanXmlEntities(html);
      const isDark = document.documentElement.dataset.theme === 'dark';
      const darkCss = 'body{font-family:Arial,sans-serif;font-size:14px;margin:8px;color:#d1d1d1;background:#1c1c1c}a{color:#8ab4f8}';
      const lightCss = 'body{font-family:Arial,sans-serif;font-size:14px;margin:8px;color:#333}';
      const css = isDark ? darkCss : lightCss;
      const styleTag = '<' + 'style>' + css + '</' + 'style>';
      const baseTag = '<base target="_blank">';
      let htmlContent = html;
      if (!/<html[\s>]/i.test(html)) {
        htmlContent = '<!DOCTYPE html><html><head><meta charset=utf-8>' + baseTag + styleTag + '</head><body>' + html + '</body></html>';
      } else {
        htmlContent = htmlContent.replace(/<head([^>]*)>/i, '<head$1>' + baseTag);
      }
      const doc = node.contentDocument || node.contentWindow.document;
      doc.open(); doc.write(htmlContent); doc.close();
      setTimeout(() => {
        try { node.style.height = Math.min(Math.max(doc.body.scrollHeight + 20, 100), 600) + 'px'; } catch(e){}
      }, 300);
    }
    render(body);
    return {
      update(newBody) { render(newBody); }
    };
  }

  function escHtml(str) {
    // Clean XML entities first (Bug 2)
    str = cleanXmlEntities(String(str));
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function formatDate(str) {
    if (!str) return '—';
    const d = new Date(str);
    return d.toLocaleDateString('de-DE',{day:'2-digit',month:'2-digit'}) + ' ' + d.toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'});
  }

  function stripPreview(str) {
    if (!str) return '';
    let s = cleanXmlEntities(str);
    s = s.replace(/<style[^>]*>[\s\S]*?<\/style>/gi,'');
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
        {#if f.key === '_divider2'}
          {#each customFolders as cf}
            <button class="f-item" class:f-active={currentFolder === 'custom_' + cf.id}
              on:click={() => setFolder('custom_' + cf.id)}
              on:contextmenu|preventDefault={() => renameFolder(cf.id)}>
              <span class="f-icon">{cf.icon}</span>
              <span class="f-name">{cf.name}</span>
              <span class="f-count" class:f-count-active={currentFolder === 'custom_' + cf.id}>{unreadCounts['custom_' + cf.id] || 0}</span>
            </button>
          {/each}
          <button class="f-item f-add" on:click={() => showNewFolderModal = true}>
            <span class="f-icon">+</span>
            <span class="f-name" style="font-size:12px;color:var(--text3)">Neuer Ordner</span>
          </button>
        {/if}
      {:else}
        <button class="f-item" class:f-active={currentFolder === f.key} on:click={() => setFolder(f.key)}>
          <span class="f-icon">{f.icon}</span>
          <span class="f-name">{f.label}</span>
          <span class="f-count" class:f-count-active={currentFolder === f.key}>{unreadCounts[f.key] || 0}</span>
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
          {@const name = m.direction === 'outgoing' ? (m.recipient||m.sender||'—') : (m.sender||'—')}
          <button class="li" class:li-active={m.id === selectedMsgId} class:li-unread={m.is_read === false} on:click={() => { selectedMsgId = m.id; markAsRead(m.id); }}>
            <div class="li-top">
              <span class="li-name">{name}</span>
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
            <button class="d-btn" on:click={() => { if(selectedMsg) toggleRead(selectedMsg.id); }} title="Gelesen/Ungelesen">{selectedMsg?.is_read ? "✉️" : "📨"}</button>
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

      {#key selectedMsgId}
      <!-- THREAD BODY (scrollable, now takes full remaining height) -->
      <div class="d-body">
        {#each thread as t}
          {@const isOut = t.direction === 'outgoing'}
          {@const isEbay = (t.sender||'').toLowerCase() === 'ebay'}
          {@const hasImages = bodyHasImages(t.body)}
          <div class="bubble-label">
            {isOut ? '✅' : isEbay ? '🔔' : '✉️'}
            {isOut ? (user?.ebay_user_id||'Shop') : (t.sender||'—')} · {formatDate(t.received_at)}
          </div>
          {#if (isEbay || hasImages) && (/<html[\s>]/i.test(t.body||'') || /<!DOCTYPE/i.test(t.body||'') || /<table/i.test(t.body||'') || hasImages)}
            <div class="bubble">
              <iframe class="ebay-iframe" use:setupIframe={t.body||''} sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox" title="eBay"></iframe>
            </div>
          {:else if isEbay}
            <div class="bubble">{@html escHtml(t.body||'—').replace(/\n/g,'<br>')}</div>
          {:else}
            <div class="bubble" class:bubble-sent={isOut}>
              {@html renderMemberText(t.body||'')}
            </div>
          {/if}
          {#if !isOut && t.ai_reply && (t.status === 'gesendet' || t.status === 'bearbeitet')}
            <div class="bubble-label">✅ {user?.ebay_user_id||'Shop'} (KI) · {formatDate(t.updated_at||t.received_at)}</div>
            <div class="bubble bubble-sent">{@html renderMemberText(t.ai_reply)}</div>
          {/if}
        {/each}
      </div>
      {/key}

      <!-- Sticky reply bar at bottom — always visible -->
      {#if !isOutgoingOnly}
        <div class="reply-bar">
          <button class="reply-bar-btn" on:click={openReplyModal}>
            💬 Antworten
          </button>
          <button class="reply-bar-ki" on:click={() => { openReplyModal(); setTimeout(generateKiReply, 100); }}>
            ✨ KI-Antwort
          </button>
        </div>
      {/if}
    {/if}
  </div>
</div>

<!-- MODAL: Antwort (Bug 1 Fix — replaces inline d-ai section) -->
{#if showReplyModal && selectedMsg}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <div class="reply-overlay" on:click|self={() => showReplyModal = false}>
    <div class="reply-modal">
      <!-- Modal Header -->
      <div class="reply-modal-header">
        <div class="reply-modal-title">
          <span style="font-size:18px;">💬</span>
          <span>Antwort an <b>{selectedMsg.sender||'—'}</b></span>
        </div>
        <button class="reply-modal-close" on:click={() => showReplyModal = false}>✕</button>
      </div>

      <!-- Original Message (readonly) -->
      <div class="reply-original">
        <div class="reply-original-label">Käufer-Nachricht</div>
        <div class="reply-original-body">{@html renderMemberText(selectedMsg.body||'')}</div>
      </div>

      <!-- AI Reply Area -->
      <div class="reply-content">
        <div class="reply-ai-top">
          <div class="reply-ai-label"><span class="d-ai-dot"></span> KI-ANTWORT</div>
          <div style="display:flex;gap:8px;">
            <button class="btn-rev" on:click={() => reviseOpen = !reviseOpen}>✏️ Überarbeiten</button>
            <button class="btn-ki" on:click={generateKiReply} disabled={kiGenerating}>
              {kiGenerating ? '⏳ ...' : '✨ KI generieren'}
            </button>
          </div>
        </div>

        <textarea class="reply-textarea" bind:value={replyText} placeholder="KI-Antwort bearbeiten..." rows="6" on:input={autoGrow}></textarea>

        <!-- Revise Chat (scrollable, fixed max-height) -->
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
              <textarea class="rev-input" bind:value={reviseInput} placeholder="z.B. Mach die Antwort kürzer, füge eine Entschuldigung hinzu..." rows="3" on:input={autoGrow} on:keydown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendRevise(); } }}></textarea>
              <button class="rev-send" on:click={sendRevise} disabled={reviseSending}>Senden</button>
            </div>
          </div>
        {/if}
      </div>

      <!-- Fixed Footer Actions — always visible -->
      <div class="reply-modal-footer">
        <button class="reply-footer-save" on:click={saveReply}>💾 Speichern</button>
        <button class="reply-footer-send" on:click={sendReply}>→ An eBay senden</button>
      </div>
    </div>
  </div>
{/if}

<!-- MODAL: Nachricht verschieben -->
{#if showMoveModal}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <div class="move-overlay" on:click|self={() => showMoveModal = false}>
    <div class="move-box">
      <div style="font-size:16px;font-weight:800;margin-bottom:6px;">📂 Nachricht verschieben</div>
      <p style="font-size:13px;color:var(--text2);margin-bottom:20px;">Zielordner auswählen</p>
      {#each moveFolders as f}
        <button class="move-btn" class:move-btn-danger={f.danger} on:click={() => moveToFolder(f.key)}>
          <span style="font-size:20px;">{f.icon}</span> {f.label}
        </button>
      {/each}
      {#if customFolders.length > 0}
        <div style="height:1px;background:var(--border);margin:8px 0;"></div>
        {#each customFolders as cf}
          <button class="move-btn" on:click={() => moveToFolder(cf.id)}>
            <span style="font-size:20px;">{cf.icon}</span> {cf.name}
          </button>
        {/each}
      {/if}
      <button class="move-cancel" on:click={() => showMoveModal = false}>Abbrechen</button>
    </div>
  </div>
{/if}

<!-- MODAL: Neuer Ordner -->
{#if showNewFolderModal}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <div class="move-overlay" on:click|self={() => showNewFolderModal = false}>
    <div class="move-box">
      <div style="font-size:16px;font-weight:800;margin-bottom:6px;">📂 Neuer Ordner</div>
      <p style="font-size:13px;color:var(--text2);margin-bottom:16px;">Name und Icon festlegen</p>
      <div style="display:flex;gap:10px;align-items:center;margin-bottom:12px;">
        <select class="input" style="width:60px;text-align:center;font-size:18px;padding:8px;" bind:value={newFolderIcon}>
          <option>📂</option><option>⭐</option><option>🔥</option><option>💎</option>
          <option>📌</option><option>❗</option><option>💬</option><option>🛒</option>
          <option>💰</option><option>🔧</option><option>🏷️</option><option>📋</option>
        </select>
        <input class="input" placeholder="Ordnername..." bind:value={newFolderName} on:keydown={(e) => e.key === 'Enter' && createFolder()} style="flex:1;" />
      </div>
      <button class="move-btn" style="justify-content:center;background:var(--primary);color:white;border-color:var(--primary);" on:click={createFolder}>
        Ordner erstellen
      </button>
      <button class="move-cancel" on:click={() => showNewFolderModal = false}>Abbrechen</button>
    </div>
  </div>
{/if}

<!-- MODAL: Ordner umbenennen -->
{#if showRenameModal}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <div class="move-overlay" on:click|self={() => showRenameModal = false}>
    <div class="move-box" style="max-width:360px;">
      <div style="font-size:20px;margin-bottom:4px;">✏️</div>
      <div style="font-size:16px;font-weight:800;margin-bottom:6px;">Ordner umbenennen</div>
      <p style="font-size:13px;color:var(--text2);margin-bottom:16px;">Gib einen neuen Namen für den Ordner ein.</p>
      <input
        class="input"
        style="width:100%;margin-bottom:16px;"
        placeholder="Ordnername..."
        bind:value={renameValue}
        on:keydown={(e) => { if (e.key === 'Enter') confirmRenameFolder(); if (e.key === 'Escape') showRenameModal = false; }}
        autofocus
      />
      <div style="display:flex;gap:10px;">
        <button class="move-cancel" style="flex:1;margin-top:0;" on:click={() => showRenameModal = false}>Abbrechen</button>
        <button class="move-btn" style="flex:2;justify-content:center;background:var(--primary);color:white;border-color:var(--primary);" on:click={confirmRenameFolder}>
          ✓ Umbenennen
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .msg-layout {
    display: flex; height: calc(100vh - 130px); min-height: 400px;
    background: var(--surface);
    border-radius: var(--radius); overflow: hidden; margin-top: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); border-color: var(--border);
  }

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
  .f-add { opacity: 0.6; transition: opacity 0.15s; }
  .f-add:hover { opacity: 1; background: var(--border); }

  .list { width: 300px; flex-shrink: 0; border-right: 1px solid var(--border); display: flex; flex-direction: column; }
  .list-top { display: flex; align-items: center; gap: 8px; padding: 10px 12px; border-bottom: 1px solid var(--border); }
  .list-search { flex: 1; background: var(--surface2); border: 1px solid var(--border); border-radius: 8px; padding: 7px 12px; color: var(--text); font-family: var(--font); font-size: 12px; outline: none; }
  .list-search:focus { border-color: var(--primary); }
  .list-num { font-size: 10px; font-weight: 700; color: var(--text3); background: var(--surface2); padding: 2px 8px; border-radius: 10px; }
  .list-scroll { flex: 1; overflow-y: auto; }

  .li { display: block; width: 100%; padding: 12px 16px; border: none; outline: none; border-bottom: 1px solid var(--border); cursor: pointer; background: none; text-align: left; font-family: var(--font); transition: background 0.1s; }
  .li:hover { background: var(--surface2); }
  .li-active { background: var(--border); }
  :global([data-theme="dark"]) .li-active { background: rgba(255,255,255,0.05); border-left-color: #fff; }
  .li-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px; }
  .li-name { font-size: 13px; font-weight: 700; color: var(--text); }
  .li-unread .li-name { color: var(--primary); }
  .li-unread .li-preview { font-weight: 600; color: var(--text); }
  .li-time { font-size: 10px; color: var(--text3); }
  .li-preview { font-size: 12px; color: var(--text2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .li-tags { display: flex; gap: 4px; margin-top: 5px; }
  .t { font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 6px; }
  .t-neu { background: rgba(15,46,147,0.08); color: var(--primary); }
  .t-gesendet, .t-bearbeitet { background: #f0fdf4; color: #16a34a; }
  .t-new { background: rgba(15,46,147,0.08); color: var(--primary); }
  :global([data-theme="dark"]) .t-neu, :global([data-theme="dark"]) .t-new { background: rgba(15,46,147,0.2); color: #93a8e8; }
  :global([data-theme="dark"]) .t-gesendet, :global([data-theme="dark"]) .t-bearbeitet { background: rgba(34,197,94,0.15); color: #86efac; }

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

  .d-body { flex: 1; overflow-y: auto; padding: 20px 24px; min-height: 0; }
  .bubble-label { font-size: 10px; font-weight: 700; color: var(--text3); letter-spacing: 1px; text-transform: uppercase; margin-bottom: 8px; }
  .bubble { background: var(--surface2); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px 20px; font-size: 14px; line-height: 1.8; white-space: pre-wrap; word-break: break-word; margin-bottom: 16px; }
  .bubble :global(img) { max-width: 100%; height: auto; border-radius: 8px; margin: 8px 0; display: block; }
  .bubble-sent { border-color: #86efac; background: rgba(34,197,94,0.05); }
  :global([data-theme="dark"]) .bubble-sent { background: rgba(34,197,94,0.08); }

  .ebay-iframe { width: 100%; height: 300px; border: none; border-radius: 8px; background: #fff; }

  /* Sticky reply bar at bottom of detail panel */
  .reply-bar {
    display: flex; gap: 10px; padding: 12px 24px; border-top: 1px solid var(--border);
    flex-shrink: 0; background: var(--surface);
  }
  .reply-bar-btn {
    flex: 1; background: linear-gradient(135deg, #7c3aed, #a855f7); color: white; border: none; border-radius: 10px;
    padding: 14px 24px; font-size: 15px; font-weight: 700; cursor: pointer;
    font-family: var(--font); transition: all 0.15s; box-shadow: 0 2px 10px rgba(168,85,247,0.3);
  }
  .reply-bar-btn:hover { background: linear-gradient(135deg, #6d28d9, #9333ea); box-shadow: 0 4px 14px rgba(168,85,247,0.4); }
  .reply-bar-ki {
    background: linear-gradient(135deg, #6c63ff, #a855f7); color: white; border: none;
    border-radius: 10px; padding: 14px 20px; font-size: 14px; font-weight: 700;
    cursor: pointer; font-family: var(--font); transition: all 0.15s; white-space: nowrap;
    box-shadow: 0 2px 10px rgba(108,99,255,0.3);
  }
  .reply-bar-ki:hover { background: linear-gradient(135deg, #5b52ff, #9333ea); box-shadow: 0 4px 14px rgba(108,99,255,0.4); }

  /* ===== REPLY MODAL (Bug 1 Fix) ===== */
  .reply-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); backdrop-filter: blur(4px); z-index: 9999; display: flex; align-items: center; justify-content: center; padding: 20px; }
  .reply-modal {
    background: var(--surface); border-radius: 16px; width: 94%; max-width: 860px;
    max-height: 92vh; min-height: 500px; display: flex; flex-direction: column; overflow: hidden;
    box-shadow: 0 24px 80px rgba(0,0,0,0.35);
  }
  .reply-modal-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 20px 24px; border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .reply-modal-title { display: flex; align-items: center; gap: 10px; font-size: 15px; font-weight: 600; color: var(--text); }
  .reply-modal-close { background: none; border: none; font-size: 18px; color: var(--text3); cursor: pointer; padding: 4px 8px; border-radius: 6px; }
  .reply-modal-close:hover { background: var(--surface2); color: var(--text); }

  .reply-original {
    padding: 16px 24px; border-bottom: 1px solid var(--border); flex-shrink: 0;
    max-height: 160px; overflow-y: auto; background: var(--surface2);
  }
  .reply-original-label { font-size: 10px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: var(--text3); margin-bottom: 8px; }
  .reply-original-body { font-size: 13px; line-height: 1.7; color: var(--text2); white-space: pre-wrap; word-break: break-word; }
  .reply-original-body :global(img) { max-width: 100%; height: auto; border-radius: 6px; margin: 6px 0; display: block; }

  .reply-content { flex: 1; overflow-y: auto; padding: 20px 24px; min-height: 0; }
  .reply-ai-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
  .reply-ai-label { font-size: 11px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: var(--primary); display: flex; align-items: center; gap: 8px; }

  .d-ai-dot { width: 7px; height: 7px; background: var(--primary); border-radius: 50%; animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.3;} }

  .btn-ki { background: linear-gradient(135deg, #6c63ff, #a855f7); border: none; color: white; border-radius: 8px; padding: 7px 16px; font-size: 12px; font-weight: 700; cursor: pointer; }
  .btn-ki:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-rev { background: var(--surface); border: 1.5px solid #a855f7; border-radius: 8px; padding: 6px 14px; color: #a855f7; font-size: 12px; font-weight: 600; cursor: pointer; }

  .reply-textarea {
    width: 100%; background: var(--surface2); border: 1px solid var(--border); border-radius: 10px;
    padding: 14px 16px; color: var(--text); font-family: var(--font); font-size: 14px;
    line-height: 1.7; resize: none; min-height: 160px; max-height: 40vh; outline: none; box-sizing: border-box;
  }
  .reply-textarea:focus { border-color: var(--primary); }

  .rev-box { margin-top: 12px; border: 1.5px solid #a855f7; border-radius: 12px; overflow: hidden; background: var(--surface2); }
  .rev-msgs { max-height: 180px; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 8px; }
  .rev-user { align-self: flex-end; background: #a855f7; color: white; border-radius: 10px 10px 2px 10px; padding: 8px 12px; font-size: 12px; max-width: 80%; }
  .rev-ki { align-self: flex-start; background: var(--surface); border: 1px solid var(--border); border-radius: 10px 10px 10px 2px; padding: 8px 12px; font-size: 12px; max-width: 80%; color: var(--text2); }
  .rev-input-row { display: flex; gap: 8px; padding: 12px; border-top: 1px solid var(--border); background: var(--surface); align-items: flex-end; }
  .rev-input { flex: 1; resize: vertical; min-height: 80px; max-height: 25vh; border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px; font-family: var(--font); font-size: 13px; color: var(--text); background: var(--surface2); outline: none; box-sizing: border-box; line-height: 1.6; }
  .rev-input:focus { border-color: #a855f7; }
  .rev-send { background: #a855f7; border: none; border-radius: 8px; padding: 10px 16px; color: white; font-size: 12px; font-weight: 700; cursor: pointer; }
  .rev-send:disabled { opacity: 0.5; }

  .reply-modal-footer {
    display: flex; gap: 10px; padding: 16px 24px; border-top: 1px solid var(--border);
    flex-shrink: 0; background: var(--surface);
  }
  .reply-footer-save {
    background: var(--surface); border: 1px solid var(--border); border-radius: 9px;
    padding: 12px 20px; color: var(--text2); font-family: var(--font); font-size: 13px;
    font-weight: 600; cursor: pointer; transition: all 0.15s;
  }
  .reply-footer-save:hover { border-color: var(--primary); color: var(--primary); }
  .reply-footer-send {
    flex: 1; background: linear-gradient(135deg, #7c3aed, #a855f7); border: none; border-radius: 9px; padding: 13px;
    color: white; font-family: var(--font); font-size: 14px; font-weight: 700; cursor: pointer;
    transition: all 0.15s; box-shadow: 0 2px 10px rgba(168,85,247,0.25);
  }
  .reply-footer-send:hover { background: linear-gradient(135deg, #6d28d9, #9333ea); box-shadow: 0 4px 14px rgba(168,85,247,0.35); }

  /* Shared modal styles */
  .move-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); backdrop-filter: blur(4px); z-index: 9999; display: flex; align-items: center; justify-content: center; }
  .move-box { background: var(--surface); border-radius: 16px; padding: 28px 24px; max-width: 340px; width: 90%; box-shadow: 0 20px 60px rgba(0,0,0,0.3); display: flex; flex-direction: column; gap: 8px; }
  .move-btn { display: flex; align-items: center; gap: 12px; width: 100%; padding: 13px 16px; border-radius: 10px; border: 1px solid var(--border); background: var(--surface); color: var(--text); font-size: 14px; font-weight: 600; cursor: pointer; font-family: var(--font); transition: all 0.15s; }
  .move-btn:hover { background: var(--surface2); border-color: var(--primary); color: var(--primary); }
  .move-btn-danger { border-color: #fca5a5; color: var(--danger); }
  .move-btn-danger:hover { background: rgba(239,68,68,0.07); border-color: var(--danger); color: var(--danger); }
  .move-cancel { margin-top: 8px; width: 100%; padding: 10px; border-radius: 10px; border: 1px solid var(--border); background: none; color: var(--text2); font-size: 13px; font-weight: 600; cursor: pointer; font-family: var(--font); }

  .input { background: var(--surface2); border: 1.5px solid var(--border); border-radius: 9px; padding: 10px 12px; color: var(--text); font-family: var(--font); font-size: 13px; outline: none; box-sizing: border-box; }
  .input:focus { border-color: var(--primary); }
</style>

<ConfirmModal bind:modal={confirmModal} />
