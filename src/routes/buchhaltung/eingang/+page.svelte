<script>
  import { onMount, onDestroy } from 'svelte';
  import { goto } from '$app/navigation';
  import { apiCall } from '$lib/api.js';
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

  const kategorien = ['alle','Wareneinkauf','Büromaterial','Versandkosten','Kfz/Tanken','Telekommunikation','Software/IT','Werbung','Reisekosten','Versicherung','Miete/Pacht','Sonstiges'];
  const statusOptionen = ['alle','entwurf','gebucht','bezahlt'];

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
    try {
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
        datei_base64: analyseDatei,
        datei_typ: analyseDateiTyp,
        quelle: 'upload',
        positionen: analyseResult.positionen || []
      });
      if (res.duplicate) {
        analyseError = `⚠️ Diese Rechnung existiert bereits in der Datenbank (ID: ${res.invoice_id}). Gleicher Lieferant, Rechnungsnummer und Datum.`;
      } else if (res.success) {
        showUploadModal = false;
        analyseResult = null;
        analyseDatei = null;
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

  async function updateStatus(id, neuerStatus) {
    try {
      await apiCall('/eingangsrechnung-update', {
        user_id: user?.id, invoice_id: id, action: 'status', neuer_status: neuerStatus
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
    showEditModal = true;
  }

  async function saveEdit() {
    if (!editItem) return;
    try {
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
        notiz: editItem.notiz
      });
      showEditModal = false;
      editItem = null;
      await loadRechnungen();
    } catch (e) { error = e.message; }
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
          {s === 'alle' ? '📋 Alle' : s === 'entwurf' ? '✏️ Entwurf' : s === 'gebucht' ? '📌 Gebucht' : '✅ Bezahlt'}
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
                <td>{formatDatum(r.rechnungsdatum)}</td>
                <td style="font-weight:600">{r.lieferant}</td>
                <td style="color:var(--text2)">{r.rechnungsnummer || '—'}</td>
                <td><span class="badge badge-info">{r.kategorie}</span></td>
                <td style="text-align:right;font-variant-numeric:tabular-nums">{formatBetrag(r.netto_betrag)} €</td>
                <td style="text-align:right;font-variant-numeric:tabular-nums;color:var(--text2)">{formatBetrag(r.mwst_betrag)} €</td>
                <td style="text-align:right;font-weight:600;font-variant-numeric:tabular-nums">{formatBetrag(r.brutto_betrag)} €</td>
                <td><span class="badge {statusBadge(r.status)}">{r.status}</span></td>
                <td style="color:var(--text3);font-size:11px">{r.quelle === 'email' ? '📧' : '📎'} {r.quelle}</td>
                <td>
                  <div style="display:flex;gap:4px">
                    <button class="btn-icon" title="Bearbeiten" on:click={() => openEdit(r)}>✏️</button>
                    {#if r.status === 'entwurf'}
                      <button class="btn-icon" title="Als gebucht markieren" on:click={() => updateStatus(r.id, 'gebucht')}>📌</button>
                    {/if}
                    {#if r.status !== 'bezahlt'}
                      <button class="btn-icon" title="Als bezahlt markieren" on:click={() => updateStatus(r.id, 'bezahlt')}>✅</button>
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
  <div class="modal-overlay" on:click|self={() => showUploadModal = false}>
    <div class="modal-box" style="max-width:640px">
      <div class="modal-title">📄 Erkannte Daten prüfen</div>
      <p style="font-size:12px;color:var(--text2);margin-bottom:16px">Die KI hat folgende Daten extrahiert. Bitte prüfen und ggf. korrigieren.</p>

      {#if analyseError}
        <div style="padding:10px 12px;background:#fef3c7;border:1px solid #fbbf24;border-radius:8px;color:#92400e;font-size:13px;margin-bottom:12px">
          {analyseError}
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
        <div class="form-group" style="grid-column:1/-1">
          <label class="label">Kategorie</label>
          <select class="input" bind:value={analyseResult.kategorie_vorschlag}>
            {#each kategorien.filter(k => k !== 'alle') as k}
              <option value={k}>{k}</option>
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

      <div class="modal-actions">
        <button class="btn btn-secondary" on:click={() => { showUploadModal = false; analyseResult = null; analyseError = ''; }}>Abbrechen</button>
        <button class="btn btn-primary" on:click={saveAnalyse} disabled={uploading}>
          {uploading ? '⏳ Speichere...' : '✅ Speichern'}
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
    <div class="modal-box">
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
  .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .form-group { display: flex; flex-direction: column; gap: 4px; }
  @media (max-width: 600px) { .form-grid { grid-template-columns: 1fr; } }
</style>
