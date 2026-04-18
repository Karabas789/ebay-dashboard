<script>
  import { onMount, onDestroy } from 'svelte';
  import { goto } from '$app/navigation';
  import { apiCall, getToken } from '$lib/api.js';
  import JSZip from 'jszip';
  import { currentUser } from '$lib/stores.js';

  let user;
  let unsubUser = currentUser.subscribe(v => user = v);
  onDestroy(() => unsubUser());

  let rechnungen = $state([]);
  let loading = $state(true);
  let error = $state('');
  let suchbegriff = $state('');
  let statusFilter = $state('alle');
  let kategorieFilter = $state('alle');

  // Upload
  let uploading = $state(false);
  let showUploadModal = $state(false);
  let showEditModal = $state(false);
  let editItem = $state(null);
  let dragOver = $state(false);

  // Analyseergebnis
  let analyseResult = $state(null);
  let analysing = $state(false);
  let analyseError = $state('');
  let analyseDatei = $state(null);
  let analyseDateiTyp = $state('');

  // Status für neue Rechnung (Default: bezahlt)
  let neuerStatus = $state('bezahlt');

  // Duplikat-Hinweis nach Backend-Response
  let duplikatHinweis = $state(null);

  // Mehrfach-Auswahl
  let ausgewaehlt = $state(new Set());
  let zipDownloading = $state(false);

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

  // Reaktive Duplikat-Erkennung
  let erkanntes_duplikat = $derived.by(() => {
    if (!analyseResult) return null;
    const lieferant = (analyseResult.lieferant || '').trim().toLowerCase();
    const rnr = (analyseResult.rechnungsnummer || '').trim().toLowerCase();
    const datum = (analyseResult.rechnungsdatum || '').substring(0, 10);
    if (!lieferant || !datum) return null;

    return rechnungen.find(r => {
      const rLieferant = (r.lieferant || '').trim().toLowerCase();
      const rRnr = (r.rechnungsnummer || '').trim().toLowerCase();
      const rDatum = (r.rechnungsdatum || '').substring(0, 10);
      return rLieferant === lieferant && rRnr === rnr && rDatum === datum;
    }) || null;
  });

  let zusammenfassung = $state(null);

  async function loadRechnungen() {
    loading = true;
    error = '';
    try {
      const res = await apiCall('/eingangsrechnungen-laden', {
        user_id: user?.id,
        status_filter: statusFilter !== 'alle' ? statusFilter : null,
        kategorie_filter: kategorieFilter !== 'alle' ? kategorieFilter : null
      });
      if (res.success) {
        rechnungen = res.rechnungen || [];
        zusammenfassung = res.zusammenfassung || null;
      } else {
        error = res.error || 'Fehler beim Laden';
      }
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  async function handleFileUpload(file) {
    if (!file) return;
    const maxSize = 20 * 1024 * 1024;
    if (file.size > maxSize) { analyseError = 'Datei zu groß (max. 20 MB)'; return; }

    const ext = file.name.split('.').pop().toLowerCase().replace('jpeg','jpg');
    const erlaubt = ['pdf','jpg','png','heic','webp','gif','tiff','bmp'];
    if (!erlaubt.includes(ext)) { analyseError = `Dateityp .${ext} nicht unterstützt`; return; }

    analysing = true;
    analyseError = '';
    analyseResult = null;
    duplikatHinweis = null;
    neuerStatus = 'bezahlt';
    analyseDateiTyp = ext;

    try {
      const base64 = await fileToBase64(file);
      analyseDatei = base64;
      const res = await apiCall('/eingangsrechnung-analysieren', {
        user_id: user?.id,
        datei_base64: base64,
        datei_typ: ext
      });
      if (res.success) {
        analyseResult = res.daten;
        if (rechnungen.length === 0) await loadRechnungen();
        showUploadModal = true;
      } else {
        analyseError = res.error || 'Analyse fehlgeschlagen';
      }
    } catch (e) {
      analyseError = e.message;
    } finally {
      analysing = false;
    }
  }

  function fileToBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result.split(',')[1]);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  function onDrop(e) {
    e.preventDefault();
    dragOver = false;
    const file = e.dataTransfer?.files?.[0];
    if (file) handleFileUpload(file);
  }

  function onFileSelect(e) {
    const file = e.target?.files?.[0];
    if (file) handleFileUpload(file);
    e.target.value = '';
  }

  async function saveAnalyse() {
    if (!analyseResult) return;
    uploading = true;
    duplikatHinweis = null;
    analyseError = '';
    try {
        // 1. Datei zu S3 hochladen (vor DB-INSERT)
      let s3_key = null;
      let datei_groesse = null;
      if (analyseDatei) {
        const uploadRes = await apiCall('/s3-upload', {
          user_id: user?.id,
          datei_base64: analyseDatei,
          datei_typ: analyseDateiTyp
        });
        if (!uploadRes.success) {
          analyseError = uploadRes.error || 'S3-Upload fehlgeschlagen';
          uploading = false;
          return;
        }
        s3_key = uploadRes.s3_key;
        datei_groesse = uploadRes.groesse;
      }

      // 2. Rechnung speichern (mit s3_key statt datei_base64)

      const res = await apiCall('/eingangsrechnung-speichern', {
        user_id: user?.id,
        lieferant: analyseResult.lieferant,
        rechnungsnummer: analyseResult.rechnungsnummer,
        rechnungsdatum: analyseResult.rechnungsdatum,
        faelligkeitsdatum: analyseResult.faelligkeitsdatum,
        netto_betrag: analyseResult.netto_betrag,
        mwst_satz: analyseResult.mwst_satz,
        mwst_betrag: analyseResult.mwst_betrag,
        brutto_betrag: analyseResult.brutto_betrag,
        kategorie: analyseResult.kategorie_vorschlag,
        notiz: analyseResult.notizen,
        datei_s3_key: s3_key,
        datei_groesse,
        datei_typ: analyseDateiTyp,
        quelle: 'upload',
        status: neuerStatus,
        bezahlt_am: neuerStatus === 'bezahlt' ? (analyseResult.rechnungsdatum || new Date().toISOString().split('T')[0]) : null,
        positionen: analyseResult.positionen || []
      });
      if (res.duplicate) {
        const vorhanden = rechnungen.find(r => r.id === res.invoice_id);
        duplikatHinweis = vorhanden || { id: res.invoice_id, lieferant: analyseResult.lieferant, rechnungsnummer: analyseResult.rechnungsnummer, rechnungsdatum: analyseResult.rechnungsdatum };
      } else if (res.success) {
        showUploadModal = false;
        analyseResult = null;
        analyseDatei = null;
        duplikatHinweis = null;
        await loadRechnungen();
      } else {
        analyseError = res.error || 'Speichern fehlgeschlagen';
      }
    } catch (e) {
      analyseError = e.message;
    } finally {
      uploading = false;
    }
  }

  async function fetchDatei(s3_key) {
    const token = getToken();
    const res = await fetch('https://n8n.ai-online.cloud/webhook/s3-download', {
      method: 'POST',
      headers: {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ s3_key })
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return await res.arrayBuffer();
  }

  async function downloadBeleg(rechnung) {
    if (!rechnung.datei_s3_key) return;
    try {
      const arrayBuffer = await fetchDatei(rechnung.datei_s3_key);
      const ext = (rechnung.datei_typ || 'bin').toLowerCase();
      const mimeMap = {
        pdf: 'application/pdf',
        jpg: 'image/jpeg', jpeg: 'image/jpeg',
        png: 'image/png', heic: 'image/heic',
        webp: 'image/webp', gif: 'image/gif',
        tiff: 'image/tiff', bmp: 'image/bmp'
      };
      const mime = mimeMap[ext] || 'application/octet-stream';
      const blob = new Blob([arrayBuffer], { type: mime });
      const url = URL.createObjectURL(blob);

      // Sprechender Dateiname: lieferant_RE-NR_DATUM.ext
      const lieferant = (rechnung.lieferant || 'Beleg').replace(/[^a-zA-Z0-9äöüÄÖÜß\s\-]/g, '').trim().replace(/\s+/g, '_');
      const rnr = (rechnung.rechnungsnummer || '').replace(/[^a-zA-Z0-9\-]/g, '');
      const datum = (rechnung.rechnungsdatum || '').substring(0, 10);
      const dateiname = [lieferant, rnr, datum].filter(Boolean).join('_') + '.' + ext;

      // Erzwungener Download (nicht Browser-Vorschau)
      const a = document.createElement('a');
      a.href = url;
      a.download = dateiname;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (e) {
      error = 'Download fehlgeschlagen: ' + e.message;
    }
  }

  function toggleSelect(id) {
    const neu = new Set(ausgewaehlt);
    if (neu.has(id)) neu.delete(id); else neu.add(id);
    ausgewaehlt = neu;
  }

  function toggleSelectAll() {
    const sichtbarMitDatei = gefiltert.filter(r => r.datei_s3_key).map(r => r.id);
    if (sichtbarMitDatei.every(id => ausgewaehlt.has(id))) {
      ausgewaehlt = new Set();
    } else {
      ausgewaehlt = new Set(sichtbarMitDatei);
    }
  }

  async function downloadAusgewaehlteAlsZip() {
    const ids = [...ausgewaehlt];
    if (ids.length === 0) return;
    zipDownloading = true;
    error = '';
    try {
      const zip = new JSZip();
      for (const id of ids) {
        const r = rechnungen.find(x => x.id === id);
        if (!r || !r.datei_s3_key) continue;
        const arrayBuffer = await fetchDatei(r.datei_s3_key);
        const ext = (r.datei_typ || 'bin').toLowerCase();
        const lieferant = (r.lieferant || 'Beleg').replace(/[^a-zA-Z0-9äöüÄÖÜß\s\-]/g, '').trim().replace(/\s+/g, '_');
        const rnr = (r.rechnungsnummer || '').replace(/[^a-zA-Z0-9\-]/g, '');
        const datum = (r.rechnungsdatum || '').substring(0, 10);
        const dateiname = [lieferant, rnr, datum].filter(Boolean).join('_') + '.' + ext;
        zip.file(dateiname, arrayBuffer);
      }
      const zipBlob = await zip.generateAsync({ type: 'blob' });
      const url = URL.createObjectURL(zipBlob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'belege_' + new Date().toISOString().substring(0, 10) + '.zip';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      ausgewaehlt = new Set();
    } catch (e) {
      error = 'ZIP-Download fehlgeschlagen: ' + e.message;
    } finally {
      zipDownloading = false;
    }
  }

  async function updateStatus(id, neuerStatusWert) {
    try {
      await apiCall('/eingangsrechnung-update', {
        user_id: user?.id, invoice_id: id, action: 'status', neuer_status: neuerStatusWert
      });
      await loadRechnungen();
    } catch (e) { error = e.message; }
  }

  async function deleteRechnung(id) {
    if (!confirm('Eingangsrechnung wirklich löschen?')) return;
    try {
      await apiCall('/eingangsrechnung-update', {
        user_id: user?.id, invoice_id: id, action: 'delete'
      });
      await loadRechnungen();
    } catch (e) { error = e.message; }
  }

  function openEdit(r) {
    editItem = { ...r };
    // Datum auf YYYY-MM-DD kürzen, damit <input type="date"> sie korrekt darstellt
    if (editItem.rechnungsdatum) editItem.rechnungsdatum = String(editItem.rechnungsdatum).substring(0, 10);
    if (editItem.bezahlt_am) editItem.bezahlt_am = String(editItem.bezahlt_am).substring(0, 10);
    showEditModal = true;
  }

  async function saveEdit() {
    if (!editItem) return;
    try {
      // Wenn Status auf "bezahlt" und kein bezahlt_am gesetzt → auf rechnungsdatum setzen
      let bezahltAm = editItem.bezahlt_am || null;
      if (editItem.status === 'bezahlt' && !bezahltAm) {
        bezahltAm = editItem.rechnungsdatum || new Date().toISOString().split('T')[0];
      }
      // Wenn Status NICHT bezahlt → bezahlt_am zurücksetzen
      if (editItem.status !== 'bezahlt') bezahltAm = null;

      await apiCall('/eingangsrechnung-update', {
        user_id: user?.id,
        invoice_id: editItem.id,
        action: 'update',
        lieferant: editItem.lieferant,
        rechnungsnummer: editItem.rechnungsnummer,
        rechnungsdatum: editItem.rechnungsdatum,
        netto_betrag: editItem.netto_betrag,
        mwst_satz: editItem.mwst_satz,
        mwst_betrag: editItem.mwst_betrag,
        brutto_betrag: editItem.brutto_betrag,
        kategorie: editItem.kategorie,
        notiz: editItem.notiz,
        status: editItem.status,
        bezahlt_am: bezahltAm
      });
      showEditModal = false;
      editItem = null;
      await loadRechnungen();
    } catch (e) { error = e.message; }
  }

  function closeUploadModal() {
    showUploadModal = false;
    analyseResult = null;
    analyseError = '';
    duplikatHinweis = null;
  }

  function formatDatum(d) {
    if (!d) return '—';
    try { return new Date(d).toLocaleDateString('de-DE'); } catch { return d; }
  }

  function formatBetrag(b) {
    return (parseFloat(b) || 0).toLocaleString('de-DE', { minimumFractionDigits: 2 });
  }

  function statusBadge(s) {
    if (s === 'bezahlt') return 'badge-success';
    if (s === 'gebucht') return 'badge-warning';
    return 'badge-info';
  }

  function statusLabel(s) {
    if (s === 'entwurf') return '✏️ Entwurf';
    if (s === 'gebucht') return '📌 Gebucht';
    if (s === 'bezahlt') return '✅ Bezahlt';
    return s;
  }

  onMount(() => { if (user?.id) loadRechnungen(); });
</script>

<div class="page-container">
  <div class="page-header">
    <div>
      <button class="btn btn-secondary" on:click={() => goto('/buchhaltung')} style="margin-bottom:8px">← Buchhaltung</button>
      <div class="page-title">📥 Eingangsrechnungen</div>
      <div class="page-subtitle">Rechnungen & Quittungen hochladen, analysieren und verwalten</div>
    </div>
    <div class="header-actions">
      <label class="btn btn-primary" style="cursor:pointer">
        📎 Datei hochladen
        <input type="file" accept=".pdf,.jpg,.jpeg,.png,.heic,.webp,.gif,.tiff,.bmp" on:change={onFileSelect} style="display:none" />
      </label>
      <button class="btn btn-secondary" on:click={loadRechnungen}>🔄 Aktualisieren</button>
    </div>
  </div>

  <!-- Drop Zone -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="drop-zone"
    class:drag-over={dragOver}
    class:analysing
    on:dragover|preventDefault={() => dragOver = true}
    on:dragleave={() => dragOver = false}
    on:drop={onDrop}
  >
    {#if analysing}
      <span class="spinner"></span>
      <span>Dokument wird analysiert...</span>
    {:else if analyseError}
      <span style="color:var(--danger)">⚠️ {analyseError}</span>
      <button class="btn btn-sm btn-secondary" style="margin-top:8px" on:click={() => analyseError = ''}>Erneut versuchen</button>
    {:else}
      <span style="font-size:28px">📄</span>
      <span>PDF, Bild oder Foto hierher ziehen</span>
      <span style="font-size:11px;color:var(--text3)">oder oben auf "Datei hochladen" klicken — PDF, JPG, PNG, HEIC, WebP</span>
    {/if}
  </div>

  <!-- Toolbar -->
  <div class="toolbar">
    <div class="filter-tabs">
      {#each statusOptionen as s}
        <button class="filter-tab" class:active={statusFilter === s} on:click={() => { statusFilter = s; loadRechnungen(); }}>
          {s === 'alle' ? '📋 Alle' : statusLabel(s)}
        </button>
      {/each}
    </div>
    <div class="toolbar-right">
      <select class="input" style="width:180px" bind:value={kategorieFilter} on:change={loadRechnungen}>
        {#each kategorien as k}
          <option value={k}>{k === 'alle' ? '🏷️ Alle Kategorien' : k}</option>
        {/each}
      </select>
      <div class="search-wrap">
        <span class="search-icon">🔍</span>
        <input class="search-input" placeholder="Suchen..." bind:value={suchbegriff} />
      </div>
    </div>
  </div>

  <!-- Zusammenfassung -->
  {#if zusammenfassung && !loading}
    <div class="kpi-grid" style="margin-bottom:16px">
      <div class="kpi-card">
        <div class="kpi-label">Belege</div>
        <div class="kpi-val">{zusammenfassung.anzahl}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Gesamt Netto</div>
        <div class="kpi-val kpi-red">{formatBetrag(zusammenfassung.gesamt_netto)} €</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Gesamt MwSt</div>
        <div class="kpi-val">{formatBetrag(zusammenfassung.gesamt_mwst)} €</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Gesamt Brutto</div>
        <div class="kpi-val kpi-red">{formatBetrag(zusammenfassung.gesamt_brutto)} €</div>
      </div>
    </div>
  {/if}

  <!-- Sammel-Aktionen -->
  {#if ausgewaehlt.size > 0}
    <div class="bulk-bar">
      <span><strong>{ausgewaehlt.size}</strong> ausgewählt</span>
      <button class="btn btn-primary btn-sm" disabled={zipDownloading} on:click={downloadAusgewaehlteAlsZip}>
        {#if zipDownloading}⏳ Erstelle ZIP...{:else}📥 ZIP herunterladen{/if}
      </button>
      <button class="btn btn-secondary btn-sm" on:click={() => ausgewaehlt = new Set()}>Auswahl aufheben</button>
    </div>
  {/if} 

  <!-- Tabelle -->
  {#if loading}
    <div class="loading"><span class="spinner"></span> Lade Eingangsrechnungen...</div>
  {:else if error}
    <div class="card" style="padding:20px;color:var(--warning)">⚠️ {error}</div>
  {:else if gefiltert.length === 0}
    <div class="empty-state">
      <h3>Keine Eingangsrechnungen</h3>
      <p>Lade eine Rechnung, Quittung oder ein Foto hoch — die KI extrahiert automatisch alle Daten.</p>
    </div>
  {:else}
    <div class="table-card">
      <div class="table-scroll">
        <table class="table">
          <thead>
            <tr>
              <th style="width:32px">
                <input type="checkbox"
                  checked={gefiltert.filter(r => r.datei_s3_key).length > 0 && gefiltert.filter(r => r.datei_s3_key).every(r => ausgewaehlt.has(r.id))}
                  on:change={toggleSelectAll} />
              </th>
              <th>Datum</th>
              <th>Lieferant</th>
              <th>Re.-Nr.</th>
              <th>Kategorie</th>
              <th style="text-align:right">Netto</th>
              <th style="text-align:right">MwSt</th>
              <th style="text-align:right">Brutto</th>
              <th>Status</th>
              <th>Quelle</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {#each gefiltert as r (r.id)}
              <tr>
                <td>
                  {#if r.datei_s3_key}
                    <input type="checkbox" checked={ausgewaehlt.has(r.id)} on:change={() => toggleSelect(r.id)} />
                  {/if}
                </td>
                <td>{formatDatum(r.rechnungsdatum)}</td>
                <td style="font-weight:600">{r.lieferant}</td>
                <td style="color:var(--text2)">{r.rechnungsnummer || '—'}</td>
                <td><span class="badge badge-info">{r.kategorie}</span></td>
                <td style="text-align:right;font-variant-numeric:tabular-nums">{formatBetrag(r.netto_betrag)} €</td>
                <td style="text-align:right;font-variant-numeric:tabular-nums;color:var(--text2)">{formatBetrag(r.mwst_betrag)} €</td>
                <td style="text-align:right;font-weight:600;font-variant-numeric:tabular-nums">{formatBetrag(r.brutto_betrag)} €</td>
                <td><span class="badge {statusBadge(r.status)}">{r.status}</span></td>
                <td style="color:var(--text3);font-size:11px">{r.quelle === 'email' ? '📧' : '⬆️'} {r.quelle}</td>
                <td>
                  <div style="display:flex;gap:4px">
                    {#if r.datei_s3_key}
                      <button class="btn-icon" title="Beleg herunterladen" on:click={() => downloadBeleg(r)}>📥</button>
                    {/if}
                    <button class="btn-icon" title="Bearbeiten" on:click={() => openEdit(r)}>✏️</button>
                    {#if r.status === 'entwurf'}
                      <button class="btn-icon" title="Als gebucht markieren" on:click={() => updateStatus(r.id, 'gebucht')}>📌</button>
                    {/if}
                    {#if r.status !== 'bezahlt'}
                      <button class="btn-icon" title="Als bezahlt markieren" on:click={() => updateStatus(r.id, 'bezahlt')}>✅</button>
                    {/if}
                    {#if r.status !== 'entwurf'}
                      <button class="btn-icon" title="Zurück auf Entwurf" on:click={() => updateStatus(r.id, 'entwurf')}>↩️</button>
                    {/if}
                    <button class="btn-icon" title="Löschen" on:click={() => deleteRechnung(r.id)}>🗑️</button>
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {/if}
</div>

<!-- Upload-Ergebnis Modal -->
{#if showUploadModal && analyseResult}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div class="modal-overlay" on:click|self={closeUploadModal}>
    <div class="modal-box modal-large">
      <div class="modal-title">📄 Erkannte Daten prüfen</div>
      <p style="font-size:12px;color:var(--text2);margin-bottom:16px">Die KI hat folgende Daten extrahiert. Bitte prüfen und ggf. korrigieren.</p>

      <!-- Duplikat-Warnung -->
      {#if duplikatHinweis || erkanntes_duplikat}
        {@const dup = duplikatHinweis || erkanntes_duplikat}
        <div class="dup-warn">
          <div style="font-weight:700;font-size:14px;margin-bottom:6px">
            ⚠️ Diese Rechnung ist bereits gespeichert
          </div>
          <div style="font-size:12px;line-height:1.6">
            <div><strong>Lieferant:</strong> {dup.lieferant}</div>
            <div><strong>Rechnungsnummer:</strong> {dup.rechnungsnummer || '—'}</div>
            <div><strong>Datum:</strong> {formatDatum(dup.rechnungsdatum)}</div>
            {#if dup.brutto_betrag !== undefined}
              <div><strong>Betrag:</strong> {formatBetrag(dup.brutto_betrag)} €</div>
            {/if}
            {#if dup.status}
              <div><strong>Status:</strong> <span class="badge {statusBadge(dup.status)}" style="font-size:10px">{dup.status}</span></div>
            {/if}
            <div style="color:var(--text2);margin-top:8px;font-size:11px">
              💡 Hat die KI einen Wert falsch erkannt (z.B. die Rechnungsnummer)? Korrigiere ihn unten und speichere erneut.
            </div>
          </div>
        </div>
      {/if}

      <div class="form-grid">
        <div class="form-group">
          <label class="label">Lieferant</label>
          <input class="input" bind:value={analyseResult.lieferant} />
        </div>
        <div class="form-group">
          <label class="label">Rechnungsnummer</label>
          <input class="input" bind:value={analyseResult.rechnungsnummer} />
        </div>
        <div class="form-group">
          <label class="label">Datum</label>
          <input class="input" type="date" bind:value={analyseResult.rechnungsdatum} />
        </div>
        <div class="form-group">
          <label class="label">Fälligkeit</label>
          <input class="input" type="date" bind:value={analyseResult.faelligkeitsdatum} />
        </div>
        <div class="form-group">
          <label class="label">Netto</label>
          <input class="input" type="number" step="0.01" bind:value={analyseResult.netto_betrag} />
        </div>
        <div class="form-group">
          <label class="label">MwSt %</label>
          <input class="input" type="number" step="0.01" bind:value={analyseResult.mwst_satz} />
        </div>
        <div class="form-group">
          <label class="label">MwSt-Betrag</label>
          <input class="input" type="number" step="0.01" bind:value={analyseResult.mwst_betrag} />
        </div>
        <div class="form-group">
          <label class="label">Brutto</label>
          <input class="input" type="number" step="0.01" bind:value={analyseResult.brutto_betrag} />
        </div>
        <div class="form-group">
          <label class="label">Kategorie</label>
          <select class="input" bind:value={analyseResult.kategorie_vorschlag}>
            {#each kategorien.filter(k => k !== 'alle') as k}
              <option value={k}>{k}</option>
            {/each}
          </select>
        </div>
        <div class="form-group">
          <label class="label">Status</label>
          <select class="input" bind:value={neuerStatus}>
            {#each statusAuswahl as s}
              <option value={s}>{statusLabel(s)}</option>
            {/each}
          </select>
        </div>
        <div class="form-group" style="grid-column:1/-1">
          <label class="label">Notizen</label>
          <textarea class="input" rows="2" bind:value={analyseResult.notizen}></textarea>
        </div>
      </div>

      {#if analyseResult.positionen?.length > 0}
        <div style="margin-top:16px">
          <div class="label">Positionen ({analyseResult.positionen.length})</div>
          <table class="table" style="font-size:12px">
            <thead><tr><th>Bezeichnung</th><th>Menge</th><th>Einzelpreis</th><th>MwSt</th></tr></thead>
            <tbody>
              {#each analyseResult.positionen as p, i}
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

      {#if analyseError}
        <div class="error-box">⚠️ {analyseError}</div>
      {/if}

      <div class="modal-actions">
        <button class="btn btn-secondary" on:click={closeUploadModal}>Abbrechen</button>
        <button
          class="btn btn-primary"
          on:click={saveAnalyse}
          disabled={uploading}
        >
          {#if uploading}
            ⏳ Speichere...
          {:else if (duplikatHinweis || erkanntes_duplikat)}
            ⚠️ Trotzdem speichern
          {:else}
            ✅ Speichern
          {/if}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- Bearbeiten Modal -->
{#if showEditModal && editItem}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div class="modal-overlay" on:click|self={() => showEditModal = false}>
    <div class="modal-box modal-large">
      <div class="modal-title">✏️ Rechnung bearbeiten</div>
      <div class="form-grid">
        <div class="form-group"><label class="label">Lieferant</label><input class="input" bind:value={editItem.lieferant} /></div>
        <div class="form-group"><label class="label">Re.-Nr.</label><input class="input" bind:value={editItem.rechnungsnummer} /></div>
        <div class="form-group"><label class="label">Datum</label><input class="input" type="date" bind:value={editItem.rechnungsdatum} /></div>
        <div class="form-group"><label class="label">Kategorie</label>
          <select class="input" bind:value={editItem.kategorie}>
            {#each kategorien.filter(k => k !== 'alle') as k}<option value={k}>{k}</option>{/each}
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
        {#if editItem.status === 'bezahlt'}
          <div class="form-group">
            <label class="label">Bezahlt am</label>
            <input class="input" type="date" bind:value={editItem.bezahlt_am} />
          </div>
        {/if}
        <div class="form-group" style="grid-column:1/-1"><label class="label">Notiz</label><textarea class="input" rows="2" bind:value={editItem.notiz}></textarea></div>
      </div>
      <div class="modal-actions">
        <button class="btn btn-secondary" on:click={() => showEditModal = false}>Abbrechen</button>
        <button class="btn btn-primary" on:click={saveEdit}>💾 Speichern</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .page-container { padding: 24px; max-width: 1200px; margin: 0 auto; }
  .drop-zone {
    background: var(--surface);
    border: 2px dashed var(--border2);
    border-radius: 12px;
    padding: 48px 24px;
    text-align: center;
    margin-bottom: 20px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    color: var(--text2);
    font-size: 13px;
    transition: all 0.2s;
    cursor: pointer;
  }
  .drop-zone.drag-over { border-color: var(--primary); background: var(--primary-light); color: var(--primary); }
  .drop-zone.analysing { border-color: var(--primary); background: var(--primary-light); }

  /* Modal-Größen — wie bei Rechnungen-Modal */
  .modal-box { width: 100%; max-height: 90vh; overflow-y: auto; }
  .modal-large { max-width: 960px; }

  .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .form-group { display: flex; flex-direction: column; gap: 4px; }
  .dup-warn {
    background: #fef3c7;
    border: 1px solid #f59e0b;
    border-left: 4px solid #d97706;
    border-radius: 8px;
    padding: 12px 14px;
    color: #78350f;
    margin-bottom: 16px;
  }
  .error-box {
    background: #fee2e2;
    border: 1px solid #fca5a5;
    border-radius: 8px;
    padding: 10px 12px;
    color: #991b1b;
    font-size: 13px;
    margin-top: 12px;
  }
  .bulk-bar {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 14px;
    background: var(--primary-light);
    border: 1px solid var(--primary);
    border-radius: 8px;
    margin-bottom: 12px;
    font-size: 13px;
  }
  @media (max-width: 600px) { .form-grid { grid-template-columns: 1fr; } }
</style>
