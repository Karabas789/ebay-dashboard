<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { currentUser, showToast } from '$lib/stores.js';
  import { apiCall } from '$lib/api.js';

  let loading = $state(true);
  let saving = $state(false);

  let form = $state({
    firmenname: '', inhaber: '', strasse: '', hausnummer: '',
    plz: '', ort: '', land: 'Deutschland', telefon: '', email: '',
    website: '', ust_idnr: '', steuernummer: '',
    kleinunternehmer: false, steuersatz: 19,
    bank_name: '', bank_iban: '', bank_bic: '',
    logo_url: '', fusszeile: ''
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
          firmenname:     d.firmenname     || '',
          inhaber:        d.inhaber        || '',
          strasse:        d.strasse        || '',
          hausnummer:     d.hausnummer     || '',
          plz:            d.plz            || '',
          ort:            d.ort            || '',
          land:           d.land           || 'Deutschland',
          telefon:        d.telefon        || '',
          email:          d.email          || '',
          website:        d.website        || '',
          ust_idnr:       d.ust_idnr       || '',
          steuernummer:   d.steuernummer   || '',
          kleinunternehmer: d.kleinunternehmer || false,
          steuersatz:     d.steuersatz     ?? 19,
          bank_name:      d.bank_name      || '',
          bank_iban:      d.bank_iban      || '',
          bank_bic:       d.bank_bic       || '',
          logo_url:       d.logo_url       || '',
          fusszeile:      d.fusszeile      || ''
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
      showToast('Firmendaten gespeichert ✓');
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
        <div class="page-title">🏢 Firmendaten</div>
        <div class="page-sub">Absender auf Rechnungen und Stornos</div>
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

      <!-- Firma -->
      <div class="card">
        <div class="card-title">Firmeninformationen</div>
        <div class="form-grid">
          <div class="form-group form-full">
            <label>Firmenname *</label>
            <input bind:value={form.firmenname} placeholder="Import & Produkte Vertrieb" />
          </div>
          <div class="form-group">
            <label>Inhaber / Geschäftsführer</label>
            <input bind:value={form.inhaber} placeholder="Oxana Dubs" />
          </div>
          <div class="form-group">
            <label>E-Mail</label>
            <input bind:value={form.email} type="email" placeholder="info@firma.de" />
          </div>
          <div class="form-group">
            <label>Telefon</label>
            <input bind:value={form.telefon} placeholder="+49 201 123456" />
          </div>
          <div class="form-group">
            <label>Website</label>
            <input bind:value={form.website} placeholder="www.firma.de" />
          </div>
        </div>
      </div>

      <!-- Adresse -->
      <div class="card">
        <div class="card-title">Adresse</div>
        <div class="form-grid">
          <div class="form-group form-col-3">
            <label>Straße</label>
            <input bind:value={form.strasse} placeholder="Musterstraße" />
          </div>
          <div class="form-group">
            <label>Hausnummer</label>
            <input bind:value={form.hausnummer} placeholder="12a" />
          </div>
          <div class="form-group">
            <label>PLZ</label>
            <input bind:value={form.plz} placeholder="45127" />
          </div>
          <div class="form-group form-col-2">
            <label>Ort</label>
            <input bind:value={form.ort} placeholder="Essen" />
          </div>
          <div class="form-group">
            <label>Land</label>
            <input bind:value={form.land} placeholder="Deutschland" />
          </div>
        </div>
      </div>

      <!-- Steuer -->
      <div class="card">
        <div class="card-title">Steuer</div>
        <div class="form-grid">
          <div class="form-group">
            <label>USt-IdNr.</label>
            <input bind:value={form.ust_idnr} placeholder="DE123456789" />
          </div>
          <div class="form-group">
            <label>Steuernummer</label>
            <input bind:value={form.steuernummer} placeholder="112/815/08150" />
          </div>
          <div class="form-group form-full">
            <label class="toggle-label">
              <input type="checkbox" bind:checked={form.kleinunternehmer} />
              <span class="toggle-text">
                Kleinunternehmer (§19 UStG) — keine Umsatzsteuer auf Rechnungen
              </span>
            </label>
          </div>
          {#if !form.kleinunternehmer}
            <div class="form-group">
              <label>Steuersatz (%)</label>
              <input bind:value={form.steuersatz} type="number" min="0" max="100" step="1" />
            </div>
          {/if}
        </div>
      </div>

      <!-- Bank -->
      <div class="card">
        <div class="card-title">Bankverbindung</div>
        <div class="form-sub">Wird auf Rechnungen angezeigt (optional)</div>
        <div class="form-grid">
          <div class="form-group">
            <label>Bank Name</label>
            <input bind:value={form.bank_name} placeholder="Sparkasse Essen" />
          </div>
          <div class="form-group form-col-2">
            <label>IBAN</label>
            <input bind:value={form.bank_iban} placeholder="DE12 3456 7890 1234 5678 90" />
          </div>
          <div class="form-group">
            <label>BIC</label>
            <input bind:value={form.bank_bic} placeholder="BELADEBEXXX" />
          </div>
        </div>
      </div>

      <!-- Logo & Fußzeile -->
      <div class="card">
        <div class="card-title">Logo & Fußzeile</div>
        <div class="form-grid">
          <div class="form-group form-full">
            <label>Logo URL</label>
            <input bind:value={form.logo_url} placeholder="https://cdn.beispiel.de/logo.png" />
            <div class="field-hint">Öffentlich erreichbare URL zum Firmenlogo (wird oben links auf Rechnungen angezeigt)</div>
          </div>
          {#if form.logo_url}
            <div class="form-group form-full">
              <div class="logo-preview">
                <img src={form.logo_url} alt="Logo Vorschau" onerror={(e) => e.target.style.display='none'} />
              </div>
            </div>
          {/if}
          <div class="form-group form-full">
            <label>Fußzeile</label>
            <textarea bind:value={form.fusszeile} rows="2"
              placeholder="z.B. Amtsgericht Essen · HRA 12345 · Geschäftsführer: Oxana Dubs"></textarea>
            <div class="field-hint">Wird unten auf jeder Rechnung angezeigt</div>
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
  .form-sub { font-size: 0.8rem; color: var(--text2); margin-top: -10px; margin-bottom: 14px; }

  .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .form-full { grid-column: 1 / -1; }
  .form-col-2 { grid-column: span 1; }
  .form-col-3 { grid-column: span 1; }

  .form-group { display: flex; flex-direction: column; gap: 5px; }
  .form-group label { font-size: 0.78rem; color: var(--text2); font-weight: 500; }
  .form-group input, .form-group textarea {
    background: var(--surface); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: 8px; font-size: 0.85rem;
    outline: none; transition: border-color 0.15s; font-family: inherit;
  }
  .form-group input:focus, .form-group textarea:focus { border-color: var(--primary); }
  .form-group input::placeholder, .form-group textarea::placeholder { color: var(--text3); }
  .form-group textarea { resize: vertical; }
  .field-hint { font-size: 0.75rem; color: var(--text3); margin-top: 2px; }

  .toggle-label { display: flex; align-items: flex-start; gap: 10px; cursor: pointer; padding: 10px 0; }
  .toggle-label input[type="checkbox"] { margin-top: 2px; width: 16px; height: 16px; cursor: pointer; accent-color: var(--primary); }
  .toggle-text { font-size: 0.85rem; color: var(--text); font-weight: 400; line-height: 1.5; }

  .logo-preview { padding: 12px; background: var(--surface2); border-radius: 8px; border: 1px solid var(--border); display: flex; align-items: center; }
  .logo-preview img { max-height: 60px; max-width: 200px; object-fit: contain; }
</style>
