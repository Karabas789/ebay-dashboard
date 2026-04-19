<script>
  import { onMount, onDestroy } from 'svelte';
  import { goto } from '$app/navigation';
  import { apiCall, getToken } from '$lib/api.js';
  import JSZip from 'jszip';
  import { currentUser } from '$lib/stores.js';

  let user;
  let unsubUser = currentUser.subscribe(v => user = v);
  onDestroy(() => unsubUser());

  let tab = $state('rechnungen');

  // ═══ RECHNUNGEN ═══
  let rechnungen = $state([]);
  let loading = $state(true);
  let error = $state('');
  let suchbegriff = $state('');
  let statusFilter = $state('alle');
  let kategorieFilter = $state('alle');
  let uploading = $state(false);
  let showUploadModal = $state(false);
  let showEditModal = $state(false);
  let editItem = $state(null);
  let dragOver = $state(false);
  let analyseResult = $state(null);
  let analysing = $state(false);
  let analyseError = $state('');
  let analyseDatei = $state(null);
  let analyseDateiTyp = $state('');
  let neuerStatus = $state('bezahlt');
  let duplikatHinweis = $state(null);
  let ausgewaehlt = $state(new Set());
  let zipDownloading = $state(false);
  let inboxItemId = $state(null);
  let zusammenfassung = $state(null);

  // Vorschau-Modal (nur für Bilder — PDFs öffnen in neuem Tab)
  let showVorschauModal = $state(false);
  let vorschauUrl = $state('');
  let vorschauTyp = $state('');
  let vorschauName = $state('');
  let vorschauLaeuft = $state(false);

  // Confirm-Modal
  let showConfirmModal = $state(false);
  let confirmTitle = $state('');
  let confirmText = $state('');
  let confirmCallback = $state(null);

  // Rückgängig-Modal
  let showRueckgaengigModal = $state(false);
  let rueckgaengigItem = $state(null);
  let rueckgaengigLaeuft = $state(false);

  // Jetzt abrufen
  let abrufenLaeuft = $state(false);
  let abrufenErgebnis = $state('');

  const kategorien = ['alle','Wareneinkauf','Büromaterial','Versandkosten','Kfz/Tanken','Telekommunikation','Software/IT','Werbung','Reisekosten','Versicherung','Miete/Pacht','Sonstiges'];
  const statusOptionen = ['alle','entwurf','gebucht','bezahlt'];
  const statusAuswahl = ['entwurf','gebucht','bezahlt'];

  let gefiltert = $derived(
    rechnungen.filter(r => {
      if (statusFilter !== 'alle' && r.status !== statusFilter) return false;
      if (kategorieFilter !== 'alle' && r.kategorie !== kategorieFilter) return false;
      if (suchbegriff) {
        const s = suchbegriff.toLowerCase();
        return (r.lieferant||'').toLowerCase().includes(s) || (r.rechnungsnummer||'').toLowerCase().includes(s) || (r.kategorie||'').toLowerCase().includes(s);
      }
      return true;
    })
  );

  let erkanntes_duplikat = $derived.by(() => {
    if (!analyseResult) return null;
    const lieferant = (analyseResult.lieferant || '').trim().toLowerCase();
    const rnr = (analyseResult.rechnungsnummer || '').trim().toLowerCase();
    const datum = (analyseResult.rechnungsdatum || '').substring(0, 10);
    if (!lieferant || !datum) return null;
    return rechnungen.find(r =>
      (r.lieferant||'').trim().toLowerCase() === lieferant &&
      (r.rechnungsnummer||'').trim().toLowerCase() === rnr &&
      (r.rechnungsdatum||'').substring(0,10) === datum
    ) || null;
  });

  async function loadRechnungen() {
    loading = true; error = '';
    try {
      const res = await apiCall('/eingangsrechnungen-laden', {
        user_id: user?.id,
        status_filter: statusFilter !== 'alle' ? statusFilter : null,
        kategorie_filter: kategorieFilter !== 'alle' ? kategorieFilter : null
      });
      if (res.success) { rechnungen = res.rechnungen || []; zusammenfassung = res.zusammenfassung || null; }
      else error = res.error || 'Fehler beim Laden';
    } catch (e) { error = e.message; }
    finally { loading = false; }
  }

  async function handleFileUpload(file) {
    if (!file) return;
    if (file.size > 20*1024*1024) { analyseError = 'Datei zu groß (max. 20 MB)'; return; }
    const ext = file.name.split('.').pop().toLowerCase().replace('jpeg','jpg');
    if (!['pdf','jpg','png','heic','webp','gif','tiff','bmp'].includes(ext)) { analyseError = `Dateityp .${ext} nicht unterstützt`; return; }
    analysing = true; analyseError = ''; analyseResult = null; duplikatHinweis = null;
    neuerStatus = 'bezahlt'; analyseDateiTyp = ext; inboxItemId = null;
    try {
      const base64 = await fileToBase64(file);
      analyseDatei = base64;
      const res = await apiCall('/eingangsrechnung-analysieren', { user_id: user?.id, datei_base64: base64, datei_typ: ext });
      if (res.success) { analyseResult = res.daten; if (rechnungen.length === 0) await loadRechnungen(); showUploadModal = true; }
      else analyseError = res.error || 'Analyse fehlgeschlagen';
    } catch (e) { analyseError = e.message; }
    finally { analysing = false; }
  }

  function fileToBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result.split(',')[1]);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  function onDrop(e) { e.preventDefault(); dragOver = false; const file = e.dataTransfer?.files?.[0]; if (file) handleFileUpload(file); }
  function onFileSelect(e) { const file = e.target?.files?.[0]; if (file) handleFileUpload(file); e.target.value = ''; }

  async function saveAnalyse() {
    if (!analyseResult) return;
    uploading = true; duplikatHinweis = null; analyseError = '';
    try {
      let s3_key = null, datei_groesse = null;
      if (inboxItemId && analyseResult._inbox_s3_key) {
        s3_key = analyseResult._inbox_s3_key; datei_groesse = analyseResult._inbox_s3_size;
      } else if (analyseDatei) {
        const uploadRes = await apiCall('/s3-upload', { user_id: user?.id, datei_base64: analyseDatei, datei_typ: analyseDateiTyp });
        if (!uploadRes.success) { analyseError = uploadRes.error || 'S3-Upload fehlgeschlagen'; uploading = false; return; }
        s3_key = uploadRes.s3_key; datei_groesse = uploadRes.groesse;
      }
      const res = await apiCall('/eingangsrechnung-speichern', {
        user_id: user?.id, lieferant: analyseResult.lieferant, rechnungsnummer: analyseResult.rechnungsnummer,
        rechnungsdatum: analyseResult.rechnungsdatum, faelligkeitsdatum: analyseResult.faelligkeitsdatum,
        netto_betrag: analyseResult.netto_betrag, mwst_satz: analyseResult.mwst_satz,
        mwst_betrag: analyseResult.mwst_betrag, brutto_betrag: analyseResult.brutto_betrag,
        kategorie: analyseResult.kategorie_vorschlag, notiz: analyseResult.notizen,
        datei_s3_key: s3_key, datei_groesse, datei_typ: analyseDateiTyp,
        quelle: inboxItemId ? 'email' : 'upload', status: neuerStatus,
        bezahlt_am: neuerStatus === 'bezahlt' ? (analyseResult.rechnungsdatum || new Date().toISOString().split('T')[0]) : null,
        positionen: analyseResult.positionen || []
      });
      if (res.duplicate) {
        duplikatHinweis = rechnungen.find(r => r.id === res.invoice_id) || { id: res.invoice_id, lieferant: analyseResult.lieferant, rechnungsnummer: analyseResult.rechnungsnummer, rechnungsdatum: analyseResult.rechnungsdatum };
      } else if (res.success) {
        if (inboxItemId) {
          try { await apiCall('/email-inbox-action', { user_id: user?.id, inbox_id: inboxItemId, action: 'freigeben', processed_invoice_id: res.invoice_id || null }); }
          catch (e) { console.warn('Mail-Move fehlgeschlagen:', e.message); }
        }
        showUploadModal = false; analyseResult = null; analyseDatei = null; duplikatHinweis = null; inboxItemId = null;
        await loadRechnungen();
        if (tab === 'posteingang') await loadInbox();
      } else analyseError = res.error || 'Speichern fehlgeschlagen';
    } catch (e) { analyseError = e.message; }
    finally { uploading = false; }
  }

  async function fetchDatei(s3_key) {
    const token = getToken();
    const res = await fetch('https://n8n.ai-online.cloud/webhook/s3-download', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
      body: JSON.stringify({ s3_key })
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return await res.arrayBuffer();
  }

  function getMime(ext) {
    const m = { pdf:'application/pdf', jpg:'image/jpeg', jpeg:'image/jpeg', png:'image/png', heic:'image/heic', webp:'image/webp', gif:'image/gif', tiff:'image/tiff', bmp:'image/bmp' };
    return m[(ext||'').toLowerCase()] || 'application/octet-stream';
  }

  // Konvertiert ArrayBuffer zu Base64 Data-URL ohne Stack-Overflow
  function toDataUrl(arrayBuffer, mime) {
    const uint8 = new Uint8Array(arrayBuffer);
    let binary = '';
    const chunkSize = 8192;
    for (let i = 0; i < uint8.length; i += chunkSize) {
      binary += String.fromCharCode(...uint8.subarray(i, i + chunkSize));
    }
    return `data:${mime};base64,${btoa(binary)}`;
  }

  // Vorschau: PDFs → neuer Tab, Bilder → Modal
  async function vorschauBeleg(rechnung) {
  if (!rechnung.datei_s3_key) return;
  const newTab = window.open('', '_blank');
  vorschauLaeuft = true;
  try {
    const arrayBuffer = await fetchDatei(rechnung.datei_s3_key);
    const ext = (rechnung.datei_typ || 'pdf').toLowerCase();
    const mime = getMime(ext);
    const dataUrl = toDataUrl(arrayBuffer, mime);
    if (ext === 'pdf') {
      newTab.location.href = dataUrl;
    } else {
      newTab.close();
      vorschauUrl = dataUrl; vorschauTyp = ext; vorschauName = rechnung.lieferant || 'Beleg';
      showVorschauModal = true;
    }
  } catch (e) { if (newTab) newTab.close(); error = 'Vorschau fehlgeschlagen: ' + e.message; }
  finally { vorschauLaeuft = false; }
}

  async function vorschauInbox(item) {
    if (!item.attachment_s3_key) return;
    const newTab = window.open('', '_blank');
    vorschauLaeuft = true;
    try {
      const arrayBuffer = await fetchDatei(item.attachment_s3_key);
      const ext = (item.attachment_typ || 'pdf').toLowerCase();
      const mime = getMime(ext);
      const dataUrl = toDataUrl(arrayBuffer, mime);
      if (ext === 'pdf') {
        newTab.location.href = dataUrl;
      } else {
        newTab.close();
        vorschauUrl = dataUrl; vorschauTyp = ext; vorschauName = item.attachment_name || 'Anhang';
        showVorschauModal = true;
      }
    } catch (e) { if (newTab) newTab.close(); inboxError = 'Vorschau fehlgeschlagen: ' + e.message; }
    finally { vorschauLaeuft = false; }
  }
  function schliesseVorschau() { vorschauUrl = ''; showVorschauModal = false; }

  async function downloadBeleg(rechnung) {
    if (!rechnung.datei_s3_key) return;
    try {
      const arrayBuffer = await fetchDatei(rechnung.datei_s3_key);
      const ext = (rechnung.datei_typ || 'bin').toLowerCase();
      const blob = new Blob([arrayBuffer], { type: getMime(ext) });
      const url = URL.createObjectURL(blob);
      const lieferant = (rechnung.lieferant||'Beleg').replace(/[^a-zA-Z0-9äöüÄÖÜß\s\-]/g,'').trim().replace(/\s+/g,'_');
      const rnr = (rechnung.rechnungsnummer||'').replace(/[^a-zA-Z0-9\-]/g,'');
      const datum = (rechnung.rechnungsdatum||'').substring(0,10);
      const a = document.createElement('a'); a.href = url; a.download = [lieferant,rnr,datum].filter(Boolean).join('_') + '.' + ext;
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (e) { error = 'Download fehlgeschlagen: ' + e.message; }
  }

  async function downloadInboxDatei(item) {
    if (!item.attachment_s3_key) return;
    try {
      const arrayBuffer = await fetchDatei(item.attachment_s3_key);
      const ext = (item.attachment_typ||'pdf').toLowerCase();
      const blob = new Blob([arrayBuffer], { type: getMime(ext) });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = item.attachment_name || ('anhang.' + ext);
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (e) { inboxError = 'Download fehlgeschlagen: ' + e.message; }
  }

  function toggleSelect(id) { const neu = new Set(ausgewaehlt); if (neu.has(id)) neu.delete(id); else neu.add(id); ausgewaehlt = neu; }
  function toggleSelectAll() {
    const ids = gefiltert.filter(r => r.datei_s3_key).map(r => r.id);
    ausgewaehlt = ids.every(id => ausgewaehlt.has(id)) ? new Set() : new Set(ids);
  }

  async function downloadAusgewaehlteAlsZip() {
    if (ausgewaehlt.size === 0) return;
    zipDownloading = true; error = '';
    try {
      const zip = new JSZip();
      for (const id of ausgewaehlt) {
        const r = rechnungen.find(x => x.id === id);
        if (!r || !r.datei_s3_key) continue;
        const ab = await fetchDatei(r.datei_s3_key);
        const ext = (r.datei_typ||'bin').toLowerCase();
        const lieferant = (r.lieferant||'Beleg').replace(/[^a-zA-Z0-9äöüÄÖÜß\s\-]/g,'').trim().replace(/\s+/g,'_');
        const rnr = (r.rechnungsnummer||'').replace(/[^a-zA-Z0-9\-]/g,'');
        const datum = (r.rechnungsdatum||'').substring(0,10);
        zip.file([lieferant,rnr,datum].filter(Boolean).join('_') + '.' + ext, ab);
      }
      const zipBlob = await zip.generateAsync({ type: 'blob' });
      const url = URL.createObjectURL(zipBlob);
      const a = document.createElement('a'); a.href = url; a.download = 'belege_' + new Date().toISOString().substring(0,10) + '.zip';
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      ausgewaehlt = new Set();
    } catch (e) { error = 'ZIP-Download fehlgeschlagen: ' + e.message; }
    finally { zipDownloading = false; }
  }

  async function updateStatus(id, s) {
    try { await apiCall('/eingangsrechnung-update', { user_id: user?.id, invoice_id: id, action: 'status', neuer_status: s }); await loadRechnungen(); }
    catch (e) { error = e.message; }
  }

  async function deleteRechnung(id) {
    zeigeConfirm('Rechnung löschen', 'Eingangsrechnung wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.', async () => {
      try { await apiCall('/eingangsrechnung-update', { user_id: user?.id, invoice_id: id, action: 'delete' }); await loadRechnungen(); }
      catch (e) { error = e.message; }
    });
  }

  function openEdit(r) {
    editItem = { ...r };
    if (editItem.rechnungsdatum) editItem.rechnungsdatum = String(editItem.rechnungsdatum).substring(0,10);
    if (editItem.bezahlt_am) editItem.bezahlt_am = String(editItem.bezahlt_am).substring(0,10);
    showEditModal = true;
  }

  async function saveEdit() {
    if (!editItem) return;
    try {
      let bezahltAm = editItem.bezahlt_am || null;
      if (editItem.status === 'bezahlt' && !bezahltAm) bezahltAm = editItem.rechnungsdatum || new Date().toISOString().split('T')[0];
      if (editItem.status !== 'bezahlt') bezahltAm = null;
      await apiCall('/eingangsrechnung-update', {
        user_id: user?.id, invoice_id: editItem.id, action: 'update',
        lieferant: editItem.lieferant, rechnungsnummer: editItem.rechnungsnummer,
        rechnungsdatum: editItem.rechnungsdatum, netto_betrag: editItem.netto_betrag,
        mwst_satz: editItem.mwst_satz, mwst_betrag: editItem.mwst_betrag,
        brutto_betrag: editItem.brutto_betrag, kategorie: editItem.kategorie,
        notiz: editItem.notiz, status: editItem.status, bezahlt_am: bezahltAm
      });
      showEditModal = false; editItem = null; await loadRechnungen();
    } catch (e) { error = e.message; }
  }

  function closeUploadModal() { showUploadModal = false; analyseResult = null; analyseError = ''; duplikatHinweis = null; inboxItemId = null; }
  function zeigeConfirm(title, text, callback) { confirmTitle = title; confirmText = text; confirmCallback = callback; showConfirmModal = true; }
  function bestaetigenConfirm() { showConfirmModal = false; if (confirmCallback) confirmCallback(); confirmCallback = null; }
  function abbrechenConfirm() { showConfirmModal = false; confirmCallback = null; }

  function formatDatum(d) { if (!d) return '—'; try { return new Date(d).toLocaleDateString('de-DE'); } catch { return d; } }
  function formatDatumZeit(d) { if (!d) return '—'; try { return new Date(d).toLocaleString('de-DE'); } catch { return d; } }
  function formatBetrag(b) { return (parseFloat(b)||0).toLocaleString('de-DE', { minimumFractionDigits: 2 }); }
  function statusBadge(s) { if (s==='bezahlt') return 'badge-success'; if (s==='gebucht') return 'badge-warning'; return 'badge-info'; }
  function statusLabel(s) { if (s==='entwurf') return '✏️ Entwurf'; if (s==='gebucht') return '📌 Gebucht'; if (s==='bezahlt') return '✅ Bezahlt'; return s; }

  // ═══ POSTEINGANG ═══
  let inboxItems = $state([]);
  let inboxLoading = $state(false);
  let inboxError = $state('');
  let inboxStatusFilter = $state('neu');
  let verwerfeLaeuft = $state(false);

  let inboxGefiltert = $derived(inboxItems.filter(i => inboxStatusFilter === 'alle' ? true : i.status === inboxStatusFilter));
  let inboxCountNeu = $derived(inboxItems.filter(i => i.status === 'neu').length);

  async function loadInbox() {
    inboxLoading = true; inboxError = '';
    try {
      const res = await apiCall('/email-inbox-laden', { user_id: user?.id, status_filter: inboxStatusFilter === 'alle' ? null : inboxStatusFilter });
      if (res.success) inboxItems = res.items || [];
      else inboxError = res.error || 'Fehler beim Laden';
    } catch (e) { inboxError = e.message; }
    finally { inboxLoading = false; }
  }

  async function jetztAbrufen() {
    abrufenLaeuft = true; abrufenErgebnis = '';
    try {
      const token = getToken();
      const res = await fetch('https://n8n.ai-online.cloud/webhook/imap-jetzt-abrufen', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: user?.id })
      });
      let data = {};
      try { data = await res.json(); } catch(e) {}
      if (res.ok) {
        const r = data.results?.[0];
        abrufenErgebnis = r ? `✅ ${r.fetched} Mail(s) geprüft, ${r.saved} neu importiert` : '✅ Abgeschlossen';
        await loadInbox();
      } else {
        abrufenErgebnis = '⚠️ ' + (data.error || 'Fehler beim Abrufen');
      }
    } catch (e) { abrufenErgebnis = '⚠️ ' + e.message; }
    finally { abrufenLaeuft = false; setTimeout(() => abrufenErgebnis = '', 5000); }
  }

  async function pruefeInboxItem(item) {
    if (!item.ki_analyse) { inboxError = 'Keine KI-Analyse vorhanden'; return; }
    if (rechnungen.length === 0) await loadRechnungen();
    inboxItemId = item.id; analyseDateiTyp = item.attachment_typ || 'pdf'; analyseDatei = null;
    analyseResult = { ...item.ki_analyse, _inbox_s3_key: item.attachment_s3_key, _inbox_s3_size: item.attachment_size };
    neuerStatus = 'entwurf'; analyseError = ''; duplikatHinweis = null; showUploadModal = true;
  }

  async function verwerfeInboxItem(item) {
    zeigeConfirm('Mail verwerfen', 'Die Mail wird als „verworfen" markiert. Die Rechnung wird NICHT in die Buchhaltung übernommen.', async () => {
      verwerfeLaeuft = true;
      try {
        const res = await apiCall('/email-inbox-action', { user_id: user?.id, inbox_id: item.id, action: 'verwerfen' });
        if (res.success) await loadInbox();
        else inboxError = res.error || 'Verwerfen fehlgeschlagen';
      } catch (e) { inboxError = e.message; }
      finally { verwerfeLaeuft = false; }
    });
  }

  async function bestaetigenRueckgaengig() {
    if (!rueckgaengigItem) return;
    rueckgaengigLaeuft = true;
    try {
      const res = await apiCall('/email-inbox-action', { user_id: user?.id, inbox_id: rueckgaengigItem.id, action: 'rueckgaengig' });
      if (res.success) { showRueckgaengigModal = false; rueckgaengigItem = null; inboxStatusFilter = 'neu'; await loadInbox(); }
      else inboxError = res.error || 'Rückgängig fehlgeschlagen';
    } catch (e) { inboxError = e.message; }
    finally { rueckgaengigLaeuft = false; }
  }

  function inboxStatusBadge(s) { if (s==='gespeichert') return 'badge-success'; if (s==='verworfen') return 'badge-danger'; return 'badge-warning'; }
  function inboxStatusLabel(s) { if (s==='neu') return '🆕 Neu'; if (s==='gespeichert') return '✅ Gespeichert'; if (s==='verworfen') return '🗑️ Verworfen'; return s; }

  onMount(async () => { if (user?.id) { await loadRechnungen(); await loadInbox(); } });
  $effect(() => { if (tab === 'posteingang' && user?.id) loadInbox(); });
</script>

<div class="page-container">
  <div class="page-header">
    <div>
      <button class="btn btn-secondary" onclick={() => goto('/buchhaltung')} style="margin-bottom:8px">← Buchhaltung</button>
      <div class="page-title">🗂️ Eingangsrechnungen</div>
      <div class="page-subtitle">Rechnungen & Quittungen hochladen, aus Emails importieren und verwalten</div>
    </div>
    {#if tab === 'rechnungen'}
      <div class="header-actions">
        <label class="btn btn-primary" style="cursor:pointer">
          📎 Datei hochladen
          <input type="file" accept=".pdf,.jpg,.jpeg,.png,.heic,.webp,.gif,.tiff,.bmp" onchange={onFileSelect} style="display:none" />
        </label>
        <button class="btn btn-secondary" onclick={loadRechnungen}>🔄 Aktualisieren</button>
      </div>
    {:else}
      <div class="header-actions">
        {#if abrufenErgebnis}<span class="abrufen-ergebnis">{abrufenErgebnis}</span>{/if}
        <button class="btn btn-primary" onclick={jetztAbrufen} disabled={abrufenLaeuft}>
          {abrufenLaeuft ? '⏳ Wird abgerufen...' : '📬 Jetzt abrufen'}
        </button>
        <button class="btn btn-secondary" onclick={loadInbox}>🔄 Aktualisieren</button>
      </div>
    {/if}
  </div>

  <div class="tab-bar">
    <button class="tab-btn" class:active={tab==='rechnungen'} onclick={() => tab='rechnungen'}>📋 Rechnungen</button>
    <button class="tab-btn" class:active={tab==='posteingang'} onclick={() => tab='posteingang'}>
      📥 Posteingang
      {#if inboxCountNeu > 0}<span class="tab-badge">{inboxCountNeu}</span>{/if}
    </button>
  </div>

  <!-- ═══ TAB: RECHNUNGEN ═══ -->
  {#if tab === 'rechnungen'}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="drop-zone" class:drag-over={dragOver} class:analysing
      ondragover={(e) => { e.preventDefault(); dragOver = true; }}
      ondragleave={() => dragOver = false} ondrop={onDrop}>
      {#if analysing}
        <span class="spinner"></span><span>Dokument wird analysiert...</span>
      {:else if analyseError}
        <span style="color:var(--danger)">⚠️ {analyseError}</span>
        <button class="btn btn-sm btn-secondary" style="margin-top:8px" onclick={() => analyseError = ''}>Erneut versuchen</button>
      {:else}
        <span style="font-size:28px">📄</span>
        <span>PDF, Bild oder Foto hierher ziehen</span>
        <span style="font-size:11px;color:var(--text3)">oder oben auf "Datei hochladen" klicken</span>
      {/if}
    </div>

    <div class="toolbar">
      <div class="filter-tabs">
        {#each statusOptionen as s}
          <button class="filter-tab" class:active={statusFilter===s} onclick={() => { statusFilter=s; loadRechnungen(); }}>
            {s==='alle' ? '📋 Alle' : statusLabel(s)}
          </button>
        {/each}
      </div>
      <div class="toolbar-right">
        <select class="input" style="width:180px" bind:value={kategorieFilter} onchange={loadRechnungen}>
          {#each kategorien as k}<option value={k}>{k==='alle' ? '🏷️ Alle Kategorien' : k}</option>{/each}
        </select>
        <div class="search-wrap">
          <span class="search-icon">🔍</span>
          <input class="search-input" placeholder="Suchen..." bind:value={suchbegriff} />
        </div>
      </div>
    </div>

    {#if zusammenfassung && !loading}
      <div class="kpi-grid" style="margin-bottom:16px">
        <div class="kpi-card"><div class="kpi-label">Belege</div><div class="kpi-val">{zusammenfassung.anzahl}</div></div>
        <div class="kpi-card"><div class="kpi-label">Gesamt Netto</div><div class="kpi-val kpi-red">{formatBetrag(zusammenfassung.gesamt_netto)} €</div></div>
        <div class="kpi-card"><div class="kpi-label">Gesamt MwSt</div><div class="kpi-val">{formatBetrag(zusammenfassung.gesamt_mwst)} €</div></div>
        <div class="kpi-card"><div class="kpi-label">Gesamt Brutto</div><div class="kpi-val kpi-red">{formatBetrag(zusammenfassung.gesamt_brutto)} €</div></div>
      </div>
    {/if}

    {#if ausgewaehlt.size > 0}
      <div class="bulk-bar">
        <span><strong>{ausgewaehlt.size}</strong> ausgewählt</span>
        <button class="btn btn-primary btn-sm" disabled={zipDownloading} onclick={downloadAusgewaehlteAlsZip}>
          {zipDownloading ? '⏳ Erstelle ZIP...' : '📁 ZIP herunterladen'}
        </button>
        <button class="btn btn-secondary btn-sm" onclick={() => ausgewaehlt = new Set()}>Auswahl aufheben</button>
      </div>
    {/if}

    {#if loading}
      <div class="loading"><span class="spinner"></span> Lade Eingangsrechnungen...</div>
    {:else if error}
      <div class="card" style="padding:20px;color:var(--warning)">⚠️ {error}</div>
    {:else if gefiltert.length === 0}
      <div class="empty-state"><h3>Keine Eingangsrechnungen</h3><p>Lade eine Rechnung, Quittung oder ein Foto hoch.</p></div>
    {:else}
      <div class="table-card">
        <div class="table-scroll">
          <table class="table">
            <thead>
              <tr>
                <th style="width:32px">
                  <input type="checkbox"
                    checked={gefiltert.filter(r=>r.datei_s3_key).length>0 && gefiltert.filter(r=>r.datei_s3_key).every(r=>ausgewaehlt.has(r.id))}
                    onchange={toggleSelectAll} />
                </th>
                <th>Datum</th><th>Lieferant</th><th>Re.-Nr.</th><th>Kategorie</th>
                <th style="text-align:right">Netto</th><th style="text-align:right">MwSt</th>
                <th style="text-align:right">Brutto</th><th>Status</th><th>Quelle</th><th></th>
              </tr>
            </thead>
            <tbody>
              {#each gefiltert as r (r.id)}
                <tr data-invoice-id={r.id}>
                  <td>{#if r.datei_s3_key}<input type="checkbox" checked={ausgewaehlt.has(r.id)} onchange={() => toggleSelect(r.id)} />{/if}</td>
                  <td>{formatDatum(r.rechnungsdatum)}</td>
                  <td style="font-weight:600">{r.lieferant}</td>
                  <td style="color:var(--text2)">{r.rechnungsnummer||'—'}</td>
                  <td><span class="badge badge-info">{r.kategorie}</span></td>
                  <td style="text-align:right;font-variant-numeric:tabular-nums">{formatBetrag(r.netto_betrag)} €</td>
                  <td style="text-align:right;font-variant-numeric:tabular-nums;color:var(--text2)">{formatBetrag(r.mwst_betrag)} €</td>
                  <td style="text-align:right;font-weight:600;font-variant-numeric:tabular-nums">{formatBetrag(r.brutto_betrag)} €</td>
                  <td><span class="badge {statusBadge(r.status)}">{r.status}</span></td>
                  <td style="color:var(--text3);font-size:11px">{r.quelle==='email'?'📧':'⬆️'} {r.quelle}</td>
                  <td>
                    <div style="display:flex;gap:4px">
                      {#if r.datei_s3_key}
                        <button class="btn-icon" title="Vorschau" onclick={() => vorschauBeleg(r)} disabled={vorschauLaeuft}>👁️</button>
                        <button class="btn-icon" title="Herunterladen" onclick={() => downloadBeleg(r)}>💾</button>
                      {/if}
                      <button class="btn-icon" title="Bearbeiten" onclick={() => openEdit(r)}>✏️</button>
                      {#if r.status==='entwurf'}<button class="btn-icon" title="Als gebucht markieren" onclick={() => updateStatus(r.id,'gebucht')}>📌</button>{/if}
                      {#if r.status!=='bezahlt'}<button class="btn-icon" title="Als bezahlt markieren" onclick={() => updateStatus(r.id,'bezahlt')}>✅</button>{/if}
                      {#if r.status!=='entwurf'}<button class="btn-icon" title="Zurück auf Entwurf" onclick={() => updateStatus(r.id,'entwurf')}>↩️</button>{/if}
                      <button class="btn-icon" title="Löschen" onclick={() => deleteRechnung(r.id)}>🗑️</button>
                    </div>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>
    {/if}
  {/if}

  <!-- ═══ TAB: POSTEINGANG ═══ -->
  {#if tab === 'posteingang'}
    <div class="card card-info">
      <div class="card-titel">📥 Automatisch importierte Emails</div>
      <div class="card-sub-info">Hier erscheinen alle Emails mit PDF-Anhang die alle 30 Minuten aus deinem IMAP-Postfach abgeholt werden. Die KI hat die Daten bereits extrahiert — du musst jede Rechnung nur noch prüfen und freigeben oder verwerfen.</div>
    </div>

    <div class="toolbar">
      <div class="filter-tabs">
        <button class="filter-tab" class:active={inboxStatusFilter==='neu'} onclick={() => { inboxStatusFilter='neu'; loadInbox(); }}>
          🆕 Neu {#if inboxCountNeu>0}<span class="tab-count">{inboxCountNeu}</span>{/if}
        </button>
        <button class="filter-tab" class:active={inboxStatusFilter==='gespeichert'} onclick={() => { inboxStatusFilter='gespeichert'; loadInbox(); }}>✅ Gespeichert</button>
        <button class="filter-tab" class:active={inboxStatusFilter==='verworfen'} onclick={() => { inboxStatusFilter='verworfen'; loadInbox(); }}>🗑️ Verworfen</button>
        <button class="filter-tab" class:active={inboxStatusFilter==='alle'} onclick={() => { inboxStatusFilter='alle'; loadInbox(); }}>📋 Alle</button>
      </div>
    </div>

    {#if inboxLoading}
      <div class="loading"><span class="spinner"></span> Lade Posteingang...</div>
    {:else if inboxError}
      <div class="card" style="padding:20px;color:var(--warning)">⚠️ {inboxError}</div>
    {:else if inboxGefiltert.length === 0}
      <div class="empty-state">
        <h3>{inboxStatusFilter==='neu'?'Keine neuen Emails':inboxStatusFilter==='gespeichert'?'Noch nichts gespeichert':inboxStatusFilter==='verworfen'?'Nichts verworfen':'Keine Emails'}</h3>
        <p>{inboxStatusFilter==='neu'?'Klicke auf „Jetzt abrufen" oder warte auf den automatischen Abruf alle 30 Minuten.':'Wechsle auf „Neu" um ungeprüfte Emails zu sehen.'}</p>
      </div>
    {:else}
      <div class="inbox-list">
        {#each inboxGefiltert as item (item.id)}
          <div class="inbox-card" class:inbox-card-error={item.ki_status==='fehler'}>
            <div class="inbox-card-head">
              <div class="inbox-head-left">
                <div class="inbox-subject">{item.subject||'(kein Betreff)'}</div>
                <div class="inbox-meta">
                  <span>📧 {item.from_name||item.from_email||'—'}</span>
                  <span>🕐 {formatDatumZeit(item.received_at)}</span>
                  <span>📎 {item.attachment_name||'anhang.pdf'}</span>
                </div>
              </div>
              <div class="inbox-head-right">
                <span class="badge {inboxStatusBadge(item.status)}">{inboxStatusLabel(item.status)}</span>
              </div>
            </div>

            {#if item.ki_status==='fehler'}
              <div class="inbox-error-box">⚠️ KI-Analyse fehlgeschlagen: {item.ki_error||'unbekannter Fehler'}</div>
            {:else if item.ki_analyse}
              <div class="inbox-preview">
                <div class="preview-row"><span class="preview-label">Lieferant:</span><span class="preview-val">{item.ki_analyse.lieferant||'—'}</span></div>
                <div class="preview-row"><span class="preview-label">Rechnungs-Nr.:</span><span class="preview-val">{item.ki_analyse.rechnungsnummer||'—'}</span></div>
                <div class="preview-row"><span class="preview-label">Datum:</span><span class="preview-val">{formatDatum(item.ki_analyse.rechnungsdatum)}</span></div>
                <div class="preview-row"><span class="preview-label">Brutto:</span><span class="preview-val preview-betrag">{formatBetrag(item.ki_analyse.brutto_betrag)} €</span></div>
                <div class="preview-row"><span class="preview-label">Kategorie:</span><span class="preview-val"><span class="badge badge-info" style="font-size:10px">{item.ki_analyse.kategorie_vorschlag||'—'}</span></span></div>
              </div>
            {/if}

            <div class="inbox-actions">
              {#if item.attachment_s3_key}
                <button class="btn btn-sm btn-secondary" onclick={() => vorschauInbox(item)} disabled={vorschauLaeuft}>
                  {vorschauLaeuft?'⏳':'👁️'} Vorschau
                </button>
                <button class="btn btn-sm btn-secondary" onclick={() => downloadInboxDatei(item)}>💾 Download</button>
              {/if}
              {#if item.status==='neu'}
                {#if item.ki_analyse}
                  <button class="btn btn-sm btn-primary" onclick={() => pruefeInboxItem(item)}>🔍 Prüfen & Speichern</button>
                {/if}
                <button class="btn btn-sm btn-danger" onclick={() => verwerfeInboxItem(item)} disabled={verwerfeLaeuft}>
                  {verwerfeLaeuft?'⏳':'🗑️'} Verwerfen
                </button>
              {:else if item.status==='verworfen'}
                <button class="btn btn-sm btn-secondary" onclick={() => { rueckgaengigItem=item; showRueckgaengigModal=true; }}>↩️ Rückgängig</button>
              {:else if item.processed_invoice_id}
                <button class="btn btn-sm btn-secondary" onclick={() => tab='rechnungen'}>📋 Zur Rechnung</button>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    {/if}
  {/if}
</div>

<!-- ═══ VORSCHAU MODAL (nur Bilder) ═══ -->
{#if showVorschauModal}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div class="modal-overlay" onclick={(e) => { if (e.target===e.currentTarget) schliesseVorschau(); }}>
    <div class="modal-box modal-vorschau">
      <div class="modal-header">
        <div class="modal-title">👁️ Vorschau — {vorschauName}</div>
        <button class="btn btn-secondary btn-sm" onclick={schliesseVorschau}>✕ Schließen</button>
      </div>
      <div class="vorschau-inhalt">
        <img src={vorschauUrl} alt="Vorschau" style="max-width:100%;max-height:100%;object-fit:contain;border-radius:8px" />
      </div>
    </div>
  </div>
{/if}

<!-- ═══ CONFIRM MODAL ═══ -->
{#if showConfirmModal}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div class="modal-overlay" onclick={(e) => { if (e.target===e.currentTarget) abbrechenConfirm(); }}>
    <div class="modal-box modal-confirm">
      <div class="modal-title">{confirmTitle}</div>
      <p style="color:var(--text2);font-size:14px;margin:12px 0 24px">{confirmText}</p>
      <div class="modal-actions">
        <button class="btn btn-secondary" onclick={abbrechenConfirm}>Abbrechen</button>
        <button class="btn btn-danger" onclick={bestaetigenConfirm}>Bestätigen</button>
      </div>
    </div>
  </div>
{/if}

<!-- ═══ RÜCKGÄNGIG MODAL ═══ -->
{#if showRueckgaengigModal && rueckgaengigItem}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div class="modal-overlay" onclick={(e) => { if (e.target===e.currentTarget) { showRueckgaengigModal=false; rueckgaengigItem=null; } }}>
    <div class="modal-box modal-confirm">
      <div class="modal-title">↩️ Verwerfen rückgängig</div>
      <p style="color:var(--text2);font-size:14px;margin:12px 0 4px"><strong>{rueckgaengigItem.subject||'(kein Betreff)'}</strong></p>
      <p style="color:var(--text2);font-size:13px;margin:0 0 24px">Die Mail wird wieder auf „Neu" gesetzt und erscheint zur erneuten Prüfung im Posteingang.</p>
      <div class="modal-actions">
        <button class="btn btn-secondary" onclick={() => { showRueckgaengigModal=false; rueckgaengigItem=null; }}>Abbrechen</button>
        <button class="btn btn-primary" onclick={bestaetigenRueckgaengig} disabled={rueckgaengigLaeuft}>
          {rueckgaengigLaeuft?'⏳ ...':'↩️ Rückgängig machen'}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- ═══ UPLOAD / PRÜF MODAL ═══ -->
{#if showUploadModal && analyseResult}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div class="modal-overlay" onclick={(e) => { if (e.target===e.currentTarget) closeUploadModal(); }}>
    <div class="modal-box modal-large">
      <div class="modal-title">{inboxItemId?'📥 Email-Rechnung prüfen':'📄 Erkannte Daten prüfen'}</div>
      <p style="font-size:12px;color:var(--text2);margin-bottom:16px">
        {inboxItemId?'Die KI hat die Daten aus der Email extrahiert. Prüfe bitte sorgfältig.':'Die KI hat folgende Daten extrahiert. Bitte prüfen und ggf. korrigieren.'}
      </p>

      {#if duplikatHinweis || erkanntes_duplikat}
        {@const dup = duplikatHinweis || erkanntes_duplikat}
        <div class="dup-warn">
          <div style="font-weight:700;font-size:14px;margin-bottom:6px">⚠️ Diese Rechnung ist bereits gespeichert</div>
          <div style="font-size:12px;line-height:1.6">
            <div><strong>Lieferant:</strong> {dup.lieferant}</div>
            <div><strong>Rechnungsnummer:</strong> {dup.rechnungsnummer||'—'}</div>
            <div><strong>Datum:</strong> {formatDatum(dup.rechnungsdatum)}</div>
          </div>
        </div>
      {/if}

      <div class="form-grid">
        <div class="form-group"><label class="label">Lieferant</label><input class="input" bind:value={analyseResult.lieferant} /></div>
        <div class="form-group"><label class="label">Rechnungsnummer</label><input class="input" bind:value={analyseResult.rechnungsnummer} /></div>
        <div class="form-group"><label class="label">Datum</label><input class="input" type="date" bind:value={analyseResult.rechnungsdatum} /></div>
        <div class="form-group"><label class="label">Fälligkeit</label><input class="input" type="date" bind:value={analyseResult.faelligkeitsdatum} /></div>
        <div class="form-group"><label class="label">Netto</label><input class="input" type="number" step="0.01" bind:value={analyseResult.netto_betrag} /></div>
        <div class="form-group"><label class="label">MwSt %</label><input class="input" type="number" step="0.01" bind:value={analyseResult.mwst_satz} /></div>
        <div class="form-group"><label class="label">MwSt-Betrag</label><input class="input" type="number" step="0.01" bind:value={analyseResult.mwst_betrag} /></div>
        <div class="form-group"><label class="label">Brutto</label><input class="input" type="number" step="0.01" bind:value={analyseResult.brutto_betrag} /></div>
        <div class="form-group">
          <label class="label">Kategorie</label>
          <select class="input" bind:value={analyseResult.kategorie_vorschlag}>
            {#each kategorien.filter(k=>k!=='alle') as k}<option value={k}>{k}</option>{/each}
          </select>
        </div>
        <div class="form-group">
          <label class="label">Status</label>
          <select class="input" bind:value={neuerStatus}>
            {#each statusAuswahl as s}<option value={s}>{statusLabel(s)}</option>{/each}
          </select>
        </div>
        <div class="form-group" style="grid-column:1/-1"><label class="label">Notizen</label><textarea class="input" rows="2" bind:value={analyseResult.notizen}></textarea></div>
      </div>

      {#if analyseResult.positionen?.length > 0}
        <div style="margin-top:16px">
          <div class="label">Positionen ({analyseResult.positionen.length})</div>
          <table class="table" style="font-size:12px">
            <thead><tr><th>Bezeichnung</th><th>Menge</th><th>Einzelpreis</th><th>MwSt</th></tr></thead>
            <tbody>
              {#each analyseResult.positionen as p}
                <tr>
                  <td><input class="input" style="padding:4px 8px;font-size:12px" bind:value={p.bezeichnung} /></td>
                  <td style="width:80px"><input class="input" type="number" step="1" style="padding:4px 8px;font-size:12px" bind:value={p.menge} /></td>
                  <td style="width:100px"><input class="input" type="number" step="0.01" style="padding:4px 8px;font-size:12px" bind:value={p.einzelpreis} /></td>
                  <td style="width:80px"><input class="input" type="number" step="0.01" style="padding:4px 8px;font-size:12px" bind:value={p.mwst_satz} /></td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}

      {#if analyseError}<div class="error-box">⚠️ {analyseError}</div>{/if}

      <div class="modal-actions">
        <button class="btn btn-secondary" onclick={closeUploadModal}>Abbrechen</button>
        <button class="btn btn-primary" onclick={saveAnalyse} disabled={uploading}>
          {#if uploading}⏳ Speichere...
          {:else if duplikatHinweis || erkanntes_duplikat}⚠️ Trotzdem speichern
          {:else if inboxItemId}✅ Speichern + Mail verschieben
          {:else}✅ Speichern{/if}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- ═══ BEARBEITEN MODAL ═══ -->
{#if showEditModal && editItem}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div class="modal-overlay" onclick={(e) => { if (e.target===e.currentTarget) showEditModal=false; }}>
    <div class="modal-box modal-large">
      <div class="modal-title">✏️ Rechnung bearbeiten</div>
      <div class="form-grid">
        <div class="form-group"><label class="label">Lieferant</label><input class="input" bind:value={editItem.lieferant} /></div>
        <div class="form-group"><label class="label">Re.-Nr.</label><input class="input" bind:value={editItem.rechnungsnummer} /></div>
        <div class="form-group"><label class="label">Datum</label><input class="input" type="date" bind:value={editItem.rechnungsdatum} /></div>
        <div class="form-group"><label class="label">Kategorie</label>
          <select class="input" bind:value={editItem.kategorie}>
            {#each kategorien.filter(k=>k!=='alle') as k}<option value={k}>{k}</option>{/each}
          </select>
        </div>
        <div class="form-group"><label class="label">Netto</label><input class="input" type="number" step="0.01" bind:value={editItem.netto_betrag} /></div>
        <div class="form-group"><label class="label">MwSt %</label><input class="input" type="number" step="0.01" bind:value={editItem.mwst_satz} /></div>
        <div class="form-group"><label class="label">MwSt-Betrag</label><input class="input" type="number" step="0.01" bind:value={editItem.mwst_betrag} /></div>
        <div class="form-group"><label class="label">Brutto</label><input class="input" type="number" step="0.01" bind:value={editItem.brutto_betrag} /></div>
        <div class="form-group">
          <label class="label">Status</label>
          <select class="input" bind:value={editItem.status}>
            {#each statusAuswahl as s}<option value={s}>{statusLabel(s)}</option>{/each}
          </select>
        </div>
        {#if editItem.status==='bezahlt'}
          <div class="form-group"><label class="label">Bezahlt am</label><input class="input" type="date" bind:value={editItem.bezahlt_am} /></div>
        {/if}
        <div class="form-group" style="grid-column:1/-1"><label class="label">Notiz</label><textarea class="input" rows="2" bind:value={editItem.notiz}></textarea></div>
      </div>
      <div class="modal-actions">
        <button class="btn btn-secondary" onclick={() => showEditModal=false}>Abbrechen</button>
        <button class="btn btn-primary" onclick={saveEdit}>💾 Speichern</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .page-container { padding: 24px; max-width: 1200px; margin: 0 auto; }
  .tab-bar { display:flex; gap:4px; border-bottom:1px solid var(--border); margin-bottom:16px; }
  .tab-btn { background:transparent; border:none; border-bottom:2px solid transparent; padding:10px 20px; font-size:0.88rem; color:var(--text2); cursor:pointer; font-weight:500; transition:all 0.15s; display:inline-flex; align-items:center; gap:8px; }
  .tab-btn:hover { color:var(--text); }
  .tab-btn.active { color:var(--primary); border-bottom-color:var(--primary); font-weight:600; }
  .tab-badge { background:#dc2626; color:#fff; font-size:0.7rem; padding:2px 7px; border-radius:10px; font-weight:700; min-width:20px; text-align:center; }
  .tab-count { background:var(--surface); color:var(--primary); font-size:0.7rem; padding:1px 6px; border-radius:10px; margin-left:4px; }
  .abrufen-ergebnis { font-size:13px; color:var(--text2); padding:6px 12px; background:var(--surface2); border-radius:8px; }
  .drop-zone { background:var(--surface); border:2px dashed var(--border2); border-radius:12px; padding:48px 24px; text-align:center; margin-bottom:20px; display:flex; flex-direction:column; align-items:center; gap:8px; color:var(--text2); font-size:13px; transition:all 0.2s; cursor:pointer; }
  .drop-zone.drag-over { border-color:var(--primary); background:var(--primary-light); color:var(--primary); }
  .drop-zone.analysing { border-color:var(--primary); background:var(--primary-light); }
  .modal-box { width:100%; max-height:90vh; overflow-y:auto; }
  .modal-large { max-width:960px; }
  .modal-confirm { max-width:440px; }
  .modal-vorschau { max-width:900px; height:85vh; display:flex; flex-direction:column; }
  .modal-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
  .vorschau-inhalt { flex:1; min-height:0; display:flex; align-items:center; justify-content:center; background:var(--surface2); border-radius:8px; overflow:hidden; padding:16px; }
  .form-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
  .form-group { display:flex; flex-direction:column; gap:4px; }
  .dup-warn { background:#fef3c7; border:1px solid #f59e0b; border-left:4px solid #d97706; border-radius:8px; padding:12px 14px; color:#78350f; margin-bottom:16px; }
  .error-box { background:#fee2e2; border:1px solid #fca5a5; border-radius:8px; padding:10px 12px; color:#991b1b; font-size:13px; margin-top:12px; }
  .bulk-bar { display:flex; align-items:center; gap:12px; padding:10px 14px; background:var(--primary-light); border:1px solid var(--primary); border-radius:8px; margin-bottom:12px; font-size:13px; }
  .card-info { background:var(--primary-light); border:1px solid var(--primary); border-radius:12px; padding:16px 20px; margin-bottom:16px; }
  .card-titel { font-size:0.9rem; font-weight:700; color:var(--text); margin-bottom:6px; }
  .card-sub-info { font-size:0.82rem; color:var(--text2); line-height:1.6; }
  .inbox-list { display:flex; flex-direction:column; gap:12px; }
  .inbox-card { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:16px 20px; display:flex; flex-direction:column; gap:12px; transition:border-color 0.15s; }
  .inbox-card:hover { border-color:var(--primary); }
  .inbox-card-error { border-color:#fca5a5; background:#fef2f2; }
  .inbox-card-head { display:flex; justify-content:space-between; align-items:flex-start; gap:12px; }
  .inbox-head-left { flex:1; min-width:0; }
  .inbox-subject { font-size:0.95rem; font-weight:600; color:var(--text); margin-bottom:4px; overflow:hidden; text-overflow:ellipsis; }
  .inbox-meta { display:flex; flex-wrap:wrap; gap:14px; font-size:0.75rem; color:var(--text2); }
  .inbox-head-right { flex-shrink:0; }
  .inbox-error-box { background:#fef2f2; border:1px solid #fca5a5; border-radius:6px; padding:8px 12px; font-size:0.78rem; color:#991b1b; }
  .inbox-preview { background:var(--surface2); border-radius:8px; padding:10px 14px; display:grid; grid-template-columns:1fr 1fr; gap:6px 20px; font-size:0.82rem; }
  .preview-row { display:flex; gap:8px; align-items:center; }
  .preview-label { color:var(--text2); font-weight:500; min-width:110px; }
  .preview-val { color:var(--text); font-weight:500; }
  .preview-betrag { font-weight:700; font-variant-numeric:tabular-nums; }
  .inbox-actions { display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; border-top:1px solid var(--border); padding-top:10px; margin-top:2px; }
  @media (max-width:600px) { .form-grid { grid-template-columns:1fr; } .inbox-preview { grid-template-columns:1fr; } }
</style>
