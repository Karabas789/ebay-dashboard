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
  let eurData = $state(null);
  let selectedJahr = $state(new Date().getFullYear());
  let selectedQuartal = $state(null);
  let selectedMonat = $state(null);
  let modus = $state('jahr');

  const monatNamen = ['','Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember'];

  async function loadEur() {
    loading = true;
    error = '';
    try {
      const params = { user_id: user?.id, jahr: selectedJahr };
      if (modus === 'quartal' && selectedQuartal) params.quartal = selectedQuartal;
      if (modus === 'monat' && selectedMonat) params.monat = selectedMonat;
      const res = await apiCall('/eur-generieren', params);
      if (res.success) eurData = res.eur;
      else error = res.error || 'Fehler';
    } catch (e) { error = e.message; }
    finally { loading = false; }
  }

  function formatBetrag(b) { return (parseFloat(b) || 0).toLocaleString('de-DE', { minimumFractionDigits: 2 }); }

  onMount(() => { if (user?.id) loadEur(); });
</script>

<div class="page-container">
  <div class="page-header">
    <div>
      <button class="btn btn-secondary" on:click={() => goto('/buchhaltung')} style="margin-bottom:8px">← Buchhaltung</button>
      <div class="page-title">📊 Einnahmenüberschussrechnung</div>
      <div class="page-subtitle">Automatisch berechnet aus Ausgangs- und Eingangsrechnungen</div>
    </div>
  </div>

  <!-- Zeitraum-Auswahl -->
  <div class="card" style="margin-bottom:20px;padding:16px">
    <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">
      <div class="filter-tabs">
        <button class="filter-tab" class:active={modus === 'jahr'} on:click={() => { modus = 'jahr'; selectedQuartal = null; selectedMonat = null; loadEur(); }}>Gesamtjahr</button>
        <button class="filter-tab" class:active={modus === 'quartal'} on:click={() => { modus = 'quartal'; selectedQuartal = selectedQuartal || 1; selectedMonat = null; loadEur(); }}>Quartal</button>
        <button class="filter-tab" class:active={modus === 'monat'} on:click={() => { modus = 'monat'; selectedMonat = selectedMonat || 1; selectedQuartal = null; loadEur(); }}>Monat</button>
      </div>
      <select class="input" style="width:100px" bind:value={selectedJahr} on:change={loadEur}>
        {#each [2024,2025,2026,2027] as j}<option value={j}>{j}</option>{/each}
      </select>
      {#if modus === 'quartal'}
        <select class="input" style="width:120px" bind:value={selectedQuartal} on:change={loadEur}>
          {#each [1,2,3,4] as q}<option value={q}>Q{q}</option>{/each}
        </select>
      {/if}
      {#if modus === 'monat'}
        <select class="input" style="width:140px" bind:value={selectedMonat} on:change={loadEur}>
          {#each Array.from({length:12}, (_,i) => i+1) as m}<option value={m}>{monatNamen[m]}</option>{/each}
        </select>
      {/if}
      <button class="btn btn-secondary btn-sm" on:click={loadEur}>🔄</button>
    </div>
  </div>

  {#if loading}
    <div class="loading"><span class="spinner"></span> Berechne EÜR...</div>
  {:else if error}
    <div class="card" style="padding:20px;color:var(--warning)">⚠️ {error}</div>
  {:else if eurData}
    <!-- KPIs -->
    <div class="kpi-grid" style="margin-bottom:24px">
      <div class="kpi-card">
        <div class="kpi-label">Einnahmen (Netto)</div>
        <div class="kpi-val kpi-green">{formatBetrag(eurData.einnahmen?.netto)} €</div>
        <div class="kpi-sub">Brutto: {formatBetrag(eurData.einnahmen?.brutto)} €</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Ausgaben (Netto)</div>
        <div class="kpi-val kpi-red">{formatBetrag(eurData.ausgaben?.netto)} €</div>
        <div class="kpi-sub">Brutto: {formatBetrag(eurData.ausgaben?.brutto)} €</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Gewinn / Verlust</div>
        <div class="kpi-val" class:kpi-green={eurData.ergebnis?.gewinn_netto >= 0} class:kpi-red={eurData.ergebnis?.gewinn_netto < 0}>
          {formatBetrag(eurData.ergebnis?.gewinn_netto)} €
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">USt-Zahllast</div>
        <div class="kpi-val kpi-blue">{formatBetrag(eurData.ergebnis?.umsatzsteuer_zahllast)} €</div>
        <div class="kpi-sub">{eurData.kleinunternehmer ? '§19 UStG' : 'USt − Vorsteuer'}</div>
      </div>
    </div>

    <!-- Einnahmen Detail -->
    <div class="card" style="margin-bottom:16px">
      <h3 style="font-size:14px;font-weight:700;margin-bottom:12px">📈 Einnahmen</h3>
      <table class="table">
        <thead><tr><th>Position</th><th style="text-align:right">Betrag</th></tr></thead>
        <tbody>
          <tr><td>Netto-Umsatz</td><td style="text-align:right;font-variant-numeric:tabular-nums">{formatBetrag(eurData.einnahmen?.netto)} €</td></tr>
          <tr><td>+ Umsatzsteuer (vereinnahmt)</td><td style="text-align:right;font-variant-numeric:tabular-nums;color:var(--text2)">{formatBetrag(eurData.einnahmen?.umsatzsteuer)} €</td></tr>
          <tr style="font-weight:700"><td>= Einnahmen Brutto</td><td style="text-align:right;font-variant-numeric:tabular-nums">{formatBetrag(eurData.einnahmen?.brutto)} €</td></tr>
        </tbody>
      </table>
    </div>

    <!-- Ausgaben Detail -->
    <div class="card" style="margin-bottom:16px">
      <h3 style="font-size:14px;font-weight:700;margin-bottom:12px">📉 Ausgaben nach Kategorie</h3>
      {#if eurData.ausgaben?.pro_kategorie && Object.keys(eurData.ausgaben.pro_kategorie).length > 0}
        <table class="table">
          <thead><tr><th>Kategorie</th><th style="text-align:right">Netto</th><th style="text-align:right">Vorsteuer</th><th style="text-align:right">Brutto</th><th style="text-align:center">Belege</th></tr></thead>
          <tbody>
            {#each Object.entries(eurData.ausgaben.pro_kategorie) as [kat, d]}
              <tr>
                <td>{kat}</td>
                <td style="text-align:right;font-variant-numeric:tabular-nums">{formatBetrag(d.netto)} €</td>
                <td style="text-align:right;font-variant-numeric:tabular-nums;color:var(--text2)">{formatBetrag(d.vorsteuer)} €</td>
                <td style="text-align:right;font-variant-numeric:tabular-nums;font-weight:600">{formatBetrag(d.brutto)} €</td>
                <td style="text-align:center">{d.anzahl}</td>
              </tr>
            {/each}
            <tr style="font-weight:700;border-top:2px solid var(--border)">
              <td>Gesamt</td>
              <td style="text-align:right">{formatBetrag(eurData.ausgaben?.netto)} €</td>
              <td style="text-align:right">{formatBetrag(eurData.ausgaben?.vorsteuer)} €</td>
              <td style="text-align:right">{formatBetrag(eurData.ausgaben?.brutto)} €</td>
              <td></td>
            </tr>
          </tbody>
        </table>
      {:else}
        <p style="color:var(--text3);font-size:12px">Keine Ausgaben im gewählten Zeitraum.</p>
      {/if}
    </div>

    <!-- Ergebnis -->
    <div class="card result-card">
      <h3 style="font-size:14px;font-weight:700;margin-bottom:12px">📋 Ergebnis</h3>
      <table class="table">
        <tbody>
          <tr><td>Einnahmen (Netto)</td><td style="text-align:right;font-variant-numeric:tabular-nums;color:var(--success)">{formatBetrag(eurData.einnahmen?.netto)} €</td></tr>
          <tr><td>− Ausgaben (Netto)</td><td style="text-align:right;font-variant-numeric:tabular-nums;color:var(--danger)">{formatBetrag(eurData.ausgaben?.netto)} €</td></tr>
          <tr style="font-weight:800;font-size:14px;border-top:2px solid var(--border)"><td>= Gewinn / Verlust</td><td style="text-align:right;font-variant-numeric:tabular-nums">{formatBetrag(eurData.ergebnis?.gewinn_netto)} €</td></tr>
        </tbody>
      </table>
    </div>
  {/if}
</div>

<style>
  .page-container { padding: 24px; max-width: 1200px; margin: 0 auto; }
  .result-card { border: 2px solid var(--primary-border); background: var(--primary-light); }
</style>
