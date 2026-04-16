<script>
  import { onMount, onDestroy } from 'svelte';
  import { goto } from '$app/navigation';
  import { apiCall } from '$lib/api.js';
  import { currentUser } from '$lib/stores.js';

  let user;
  let unsubUser = currentUser.subscribe(v => user = v);
  onDestroy(() => unsubUser());

  let loading = $state(true);
  let error = $state('');
  let ustvaData = $state(null);
  let selectedJahr = $state(new Date().getFullYear());
  let selectedMonat = $state(new Date().getMonth() > 0 ? new Date().getMonth() : 12);
  let modus = $state('monat');
  let selectedQuartal = $state(Math.ceil(new Date().getMonth() / 3) || 1);

  const monatNamen = ['','Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember'];

  async function loadUstva() {
    loading = true;
    error = '';
    try {
      const params = { user_id: user?.id, jahr: selectedJahr };
      if (modus === 'monat') params.monat = selectedMonat;
      if (modus === 'quartal') params.quartal = selectedQuartal;
      const res = await apiCall('/ustva-daten', params);
      if (res.success) ustvaData = res.ustva;
      else error = res.error || 'Fehler';
    } catch (e) { error = e.message; }
    finally { loading = false; }
  }

  function formatBetrag(b) { return (parseFloat(b) || 0).toLocaleString('de-DE', { minimumFractionDigits: 2 }); }

  onMount(() => { if (user?.id) loadUstva(); });
</script>

<div class="page-container">
  <div class="page-header">
    <div>
      <button class="btn btn-secondary" on:click={() => goto('/buchhaltung')} style="margin-bottom:8px">← Buchhaltung</button>
      <div class="page-title">📋 UStVA-Vorbereitung</div>
      <div class="page-subtitle">Umsatzsteuer-Voranmeldung — Kennzahlen für ELSTER</div>
    </div>
  </div>

  <!-- Zeitraum -->
  <div class="card" style="margin-bottom:20px;padding:16px">
    <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">
      <div class="filter-tabs">
        <button class="filter-tab" class:active={modus === 'monat'} on:click={() => { modus = 'monat'; loadUstva(); }}>Monatlich</button>
        <button class="filter-tab" class:active={modus === 'quartal'} on:click={() => { modus = 'quartal'; loadUstva(); }}>Quartal</button>
      </div>
      <select class="input" style="width:100px" bind:value={selectedJahr} on:change={loadUstva}>
        {#each [2024,2025,2026,2027] as j}<option value={j}>{j}</option>{/each}
      </select>
      {#if modus === 'monat'}
        <select class="input" style="width:140px" bind:value={selectedMonat} on:change={loadUstva}>
          {#each Array.from({length:12}, (_,i) => i+1) as m}<option value={m}>{monatNamen[m]}</option>{/each}
        </select>
      {:else}
        <select class="input" style="width:120px" bind:value={selectedQuartal} on:change={loadUstva}>
          {#each [1,2,3,4] as q}<option value={q}>Q{q}</option>{/each}
        </select>
      {/if}
      <button class="btn btn-secondary btn-sm" on:click={loadUstva}>🔄</button>
    </div>
  </div>

  {#if loading}
    <div class="loading"><span class="spinner"></span> Berechne UStVA-Daten...</div>
  {:else if error}
    <div class="card" style="padding:20px;color:var(--warning)">⚠️ {error}</div>
  {:else if ustvaData}
    <!-- Hinweis -->
    {#if ustvaData.firma?.kleinunternehmer}
      <div class="card" style="padding:16px;margin-bottom:16px;border-color:var(--warning);background:rgba(217,119,6,0.05)">
        <span style="font-weight:700;color:var(--warning)">⚠️ Kleinunternehmer nach §19 UStG</span>
        <span style="font-size:12px;color:var(--text2);margin-left:8px">— Keine UStVA erforderlich</span>
      </div>
    {/if}

    <!-- Firma-Info -->
    <div class="card" style="margin-bottom:16px;padding:16px">
      <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px">
        <div>
          <div style="font-weight:700">{ustvaData.firma?.name || '—'}</div>
          <div style="font-size:12px;color:var(--text2)">USt-IdNr: {ustvaData.firma?.ust_idnr || '—'}</div>
        </div>
        <div style="text-align:right">
          <div style="font-weight:700">{ustvaData.zeitraum}</div>
          <div style="font-size:12px;color:var(--text2)">{ustvaData.von} bis {ustvaData.bis}</div>
        </div>
      </div>
    </div>

    <!-- ELSTER-Kennzahlen -->
    <div class="card" style="margin-bottom:16px">
      <h3 style="font-size:14px;font-weight:700;margin-bottom:16px">🏛️ ELSTER-Kennzahlen</h3>
      <table class="table">
        <thead><tr><th>Kennzahl</th><th>Bezeichnung</th><th style="text-align:right">Bemessungsgrundlage</th><th style="text-align:right">Steuer</th></tr></thead>
        <tbody>
          <tr>
            <td><span class="badge badge-info">Kz 81</span></td>
            <td>Umsätze zum allgemeinen Steuersatz (19%)</td>
            <td style="text-align:right;font-variant-numeric:tabular-nums">{formatBetrag(ustvaData.zusammenfassung?.umsaetze_19?.bemessungsgrundlage)} €</td>
            <td style="text-align:right;font-variant-numeric:tabular-nums;font-weight:600">{formatBetrag(ustvaData.zusammenfassung?.umsaetze_19?.umsatzsteuer)} €</td>
          </tr>
          <tr>
            <td><span class="badge badge-info">Kz 86</span></td>
            <td>Umsätze zum ermäßigten Steuersatz (7%)</td>
            <td style="text-align:right;font-variant-numeric:tabular-nums">{formatBetrag(ustvaData.zusammenfassung?.umsaetze_7?.bemessungsgrundlage)} €</td>
            <td style="text-align:right;font-variant-numeric:tabular-nums;font-weight:600">{formatBetrag(ustvaData.zusammenfassung?.umsaetze_7?.umsatzsteuer)} €</td>
          </tr>
          <tr style="border-top:2px solid var(--border)">
            <td></td>
            <td style="font-weight:700">Umsatzsteuer gesamt</td>
            <td></td>
            <td style="text-align:right;font-weight:700;font-variant-numeric:tabular-nums">{formatBetrag(ustvaData.zusammenfassung?.umsatzsteuer_gesamt)} €</td>
          </tr>
          <tr>
            <td><span class="badge badge-info">Kz 66</span></td>
            <td>Vorsteuerbeträge aus Rechnungen</td>
            <td></td>
            <td style="text-align:right;font-variant-numeric:tabular-nums;color:var(--success);font-weight:600">−{formatBetrag(ustvaData.zusammenfassung?.vorsteuer_gesamt)} €</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Vorsteuer Detail -->
    {#if ustvaData.vorsteuer_details?.length > 0}
      <div class="card" style="margin-bottom:16px">
        <h3 style="font-size:14px;font-weight:700;margin-bottom:12px">🧾 Vorsteuer-Details</h3>
        <table class="table">
          <thead><tr><th>MwSt-Satz</th><th style="text-align:right">Bemessungsgrundlage</th><th style="text-align:right">Vorsteuer</th><th style="text-align:center">Belege</th></tr></thead>
          <tbody>
            {#each ustvaData.vorsteuer_details as vd}
              <tr>
                <td>{vd.mwst_satz}%</td>
                <td style="text-align:right;font-variant-numeric:tabular-nums">{formatBetrag(vd.bemessungsgrundlage)} €</td>
                <td style="text-align:right;font-variant-numeric:tabular-nums">{formatBetrag(vd.vorsteuer)} €</td>
                <td style="text-align:center">{vd.anzahl_belege}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}

    <!-- Ergebnis -->
    <div class="card result-card">
      <h3 style="font-size:14px;font-weight:700;margin-bottom:16px">💰 Zahllast</h3>
      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-label">Umsatzsteuer</div>
          <div class="kpi-val" style="font-size:20px">{formatBetrag(ustvaData.zusammenfassung?.umsatzsteuer_gesamt)} €</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">− Vorsteuer</div>
          <div class="kpi-val kpi-green" style="font-size:20px">{formatBetrag(ustvaData.zusammenfassung?.vorsteuer_gesamt)} €</div>
        </div>
        <div class="kpi-card" style="border:2px solid var(--primary-border);background:var(--primary-light)">
          <div class="kpi-label">{ustvaData.zusammenfassung?.zahllast >= 0 ? 'Zahllast' : 'Erstattung'}</div>
          <div class="kpi-val" class:kpi-red={ustvaData.zusammenfassung?.zahllast > 0} class:kpi-green={ustvaData.zusammenfassung?.zahllast <= 0} style="font-size:22px">
            {formatBetrag(Math.abs(ustvaData.zusammenfassung?.zahllast || 0))} €
          </div>
        </div>
      </div>
      <div style="margin-top:16px;padding:12px;background:var(--surface2);border-radius:var(--radius-sm);font-size:12px;color:var(--text2)">
        💡 {ustvaData.hinweis}
      </div>
    </div>
  {/if}
</div>

<style>
  .page-container { padding: 24px; max-width: 1200px; margin: 0 auto; }
  .result-card { border: 2px solid var(--primary-border); }
</style>
