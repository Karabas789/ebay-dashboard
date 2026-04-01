<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { currentUser, showToast } from '$lib/stores.js';
  import { apiCall } from '$lib/api.js';

  let loading = $state(true);
  let saving = $state(false);

  let form = $state({
    re_praefix: 'RE', re_trennzeichen: '-', re_naechste_nr: 1,
    re_min_stellen: 5, re_mit_jahr: true,
    sr_praefix: 'SR', sr_trennzeichen: '-', sr_naechste_nr: 1,
    sr_min_stellen: 5, sr_mit_jahr: true,
    sprache: 'de', waehrung: '€'
  });

  let vorschauRE = $derived.by(() => {
    const jahr = new Date().getFullYear();
    const num = String(form.re_naechste_nr || 1).padStart(form.re_min_stellen || 5, '0');
    return form.re_mit_jahr
      ? `${form.re_praefix}${form.re_trennzeichen}${jahr}${form.re_trennzeichen}${num}`
      : `${form.re_praefix}${form.re_trennzeichen}${num}`;
  });

  let vorschauSR = $derived.by(() => {
    const jahr = new Date().getFullYear();
    const num = String(form.sr_naechste_nr || 1).padStart(form.sr_min_stellen || 5, '0');
    return form.sr_mit_jahr
      ? `${form.sr_praefix}${form.sr_trennzeichen}${jahr}${form.sr_trennzeichen}${num}`
      : `${form.sr_praefix}${form.sr_trennzeichen}${num}`;
  });

  onMount(async () => {
    try {
      const data = await apiCall('rechnung-settings', {
        action: 'load',
        user_id: $currentUser.id
      });
      if (data?.data) {
        const d = data.data;
        form = {
          re_praefix:      d.re_praefix      || 'RE',
          re_trennzeichen: d.re_trennzeichen || '-',
          re_naechste_nr:  d.re_naechste_nr  ?? 1,
          re_min_stellen:  d.re_min_stellen  ?? 5,
          re_mit_jahr:     d.re_mit_jahr     ?? true,
          sr_praefix:      d.sr_praefix      || 'SR',
          sr_trennzeichen: d.sr_trennzeichen || '-',
          sr_naechste_nr:  d.sr_naechste_nr  ?? 1,
          sr_min_stellen:  d.sr_min_stellen  ?? 5,
          sr_mit_jahr:     d.sr_mit_jahr     ?? true,
          sprache:         d.sprache         || 'de',
          waehrung:        d.waehrung        || '€'
        };
      }
    } catch (e) {
      showToast('Fehler beim Laden: ' + e.message);
    } finally {
      loading = false;
    }
  });

  async function speichern() {
    saving = true;
    try {
      await apiCall('rechnung-settings', {
        action: 'save',
        user_id: $currentUser.id,
        ...form
      });
      showToast('Nummerierung gespeichert ✓');
    } catch (e) {
      showToast('Fehler: ' + e.message);
    } finally {
      saving = false;
    }
  }
</script>

<div class="page-container">
  <div class="page-hdr">
    <div class="hdr-left">
      <button class="btn-back" onclick={() => goto('/einstellungen')}>← Zurück</button>
      <div>
        <div class="page-title">🔢 Nummerierung</div>
        <div class="page-sub">Nummernkreise für Rechnungen und Stornos</div>
      </div>
    </div>
    <button class="btn-primary" onclick={speichern} disabled={saving || loading}>
      {saving ? 'Speichern…' : 'Speichern'}
    </button>
  </div>

  {#if loading}
    <div class="loading-state">Lade Einstellungen…</div>
  {:else}
    <div class="sections">

      <!-- Rechnungen -->
      <div class="card">
        <div class="card-title">Rechnungen</div>
        <div class="vorschau-box">
          <span class="vorschau-label">Vorschau nächste Nummer</span>
          <span class="vorschau-nr">{vorschauRE}</span>
        </div>
        <div class="form-grid">
          <div class="form-group">
            <label>Präfix</label>
            <input bind:value={form.re_praefix} placeholder="RE" maxlength="10" />
          </div>
          <div class="form-group">
            <label>Trennzeichen</label>
            <select bind:value={form.re_trennzeichen}>
              <option value="-">Bindestrich  —  RE-2026-00001</option>
              <option value="/">Schrägstrich  —  RE/2026/00001</option>
              <option value=".">Punkt  —  RE.2026.00001</option>
              <option value="">Kein  —  RE202600001</option>
            </select>
          </div>
          <div class="form-group">
            <label>Startnummer</label>
            <input bind:value={form.re_naechste_nr} type="number" min="1" />
            <div class="field-hint">Nächste zu vergebende Nummer</div>
          </div>
          <div class="form-group">
            <label>Mindest-Stellen</label>
            <input bind:value={form.re_min_stellen} type="number" min="1" max="10" />
            <div class="field-hint">Zahl wird mit führenden Nullen aufgefüllt</div>
          </div>
          <div class="form-group form-full">
            <label class="toggle-label">
              <input type="checkbox" bind:checked={form.re_mit_jahr} />
              <span class="toggle-text">Jahr in Rechnungsnummer einschließen (z.B. RE-<strong>2026</strong>-00001)</span>
            </label>
          </div>
        </div>
      </div>

      <!-- Stornorechnungen -->
      <div class="card">
        <div class="card-title">Stornorechnungen</div>
        <div class="vorschau-box">
          <span class="vorschau-label">Vorschau nächste Nummer</span>
          <span class="vorschau-nr storno">{vorschauSR}</span>
        </div>
        <div class="form-grid">
          <div class="form-group">
            <label>Präfix</label>
            <input bind:value={form.sr_praefix} placeholder="SR" maxlength="10" />
          </div>
          <div class="form-group">
            <label>Trennzeichen</label>
            <select bind:value={form.sr_trennzeichen}>
              <option value="-">Bindestrich  —  SR-2026-00001</option>
              <option value="/">Schrägstrich  —  SR/2026/00001</option>
              <option value=".">Punkt  —  SR.2026.00001</option>
              <option value="">Kein  —  SR202600001</option>
            </select>
          </div>
          <div class="form-group">
            <label>Startnummer</label>
            <input bind:value={form.sr_naechste_nr} type="number" min="1" />
          </div>
          <div class="form-group">
            <label>Mindest-Stellen</label>
            <input bind:value={form.sr_min_stellen} type="number" min="1" max="10" />
          </div>
          <div class="form-group form-full">
            <label class="toggle-label">
              <input type="checkbox" bind:checked={form.sr_mit_jahr} />
              <span class="toggle-text">Jahr in Stornonummer einschließen</span>
            </label>
          </div>
        </div>
      </div>

      <!-- Sprache & Währung -->
      <div class="card">
        <div class="card-title">Sprache & Währung</div>
        <div class="form-grid">
          <div class="form-group">
            <label>Rechnungssprache</label>
            <select bind:value={form.sprache}>
              <option value="de">Deutsch</option>
              <option value="en">English</option>
            </select>
          </div>
          <div class="form-group">
            <label>Währung</label>
            <select bind:value={form.waehrung}>
              <option value="€">€ Euro</option>
              <option value="CHF">CHF Schweizer Franken</option>
              <option value="$">$ US-Dollar</option>
              <option value="£">£ Britisches Pfund</option>
            </select>
          </div>
        </div>
      </div>

    </div>
  {/if}
</div>

<style>
  .page-container { display: flex; flex-direction: column; gap: 20px; padding: 24px; width: 100%; box-sizing: border-box; max-width: 860px; }
  .page-hdr { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
  .hdr-left { display: flex; align-items: center; gap: 16px; }
  .page-title { font-size: 1.3rem; font-weight: 700; color: var(--text); }
  .page-sub { font-size: 0.82rem; color: var(--text2); margin-top: 2px; }

  .btn-back {
    background: transparent; border: 1px solid var(--border); color: var(--text2);
    padding: 7px 14px; border-radius: 8px; font-size: 0.83rem; cursor: pointer;
    transition: all 0.15s; white-space: nowrap;
  }
  .btn-back:hover { border-color: var(--primary); color: var(--primary); }

  .btn-primary {
    background: var(--primary); color: #fff; border: none;
    padding: 9px 20px; border-radius: 8px; font-size: 0.85rem;
    cursor: pointer; transition: background 0.15s; white-space: nowrap;
  }
  .btn-primary:hover:not(:disabled) { background: var(--primary-hover, #1d4ed8); }
  .btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

  .loading-state { padding: 40px; text-align: center; color: var(--text2); font-size: 0.85rem; }

  .sections { display: flex; flex-direction: column; gap: 16px; }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px 24px; }
  .card-title { font-size: 0.9rem; font-weight: 600; color: var(--text); margin-bottom: 16px; }

  .vorschau-box {
    display: flex; align-items: center; justify-content: space-between;
    background: var(--surface2); border: 1px solid var(--border);
    border-radius: 8px; padding: 12px 16px; margin-bottom: 18px;
  }
  .vorschau-label { font-size: 0.78rem; color: var(--text2); }
  .vorschau-nr { font-size: 1.1rem; font-weight: 700; color: var(--primary); font-variant-numeric: tabular-nums; }
  .vorschau-nr.storno { color: #dc2626; }

  .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .form-full { grid-column: 1 / -1; }
  .form-group { display: flex; flex-direction: column; gap: 5px; }
  .form-group label:not(.toggle-label) { font-size: 0.78rem; color: var(--text2); font-weight: 500; }
  .form-group input, .form-group select {
    background: var(--surface); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: 8px; font-size: 0.85rem;
    outline: none; transition: border-color 0.15s;
  }
  .form-group input:focus, .form-group select:focus { border-color: var(--primary); }
  .field-hint { font-size: 0.75rem; color: var(--text3); margin-top: 2px; }

  .toggle-label { display: flex; align-items: flex-start; gap: 10px; cursor: pointer; padding: 8px 0; }
  .toggle-label input[type="checkbox"] { margin-top: 2px; width: 16px; height: 16px; cursor: pointer; accent-color: var(--primary); }
  .toggle-text { font-size: 0.85rem; color: var(--text); font-weight: 400; line-height: 1.5; }
</style>
