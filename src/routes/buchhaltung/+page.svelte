<script>
  import { onMount, onDestroy } from 'svelte';
  import { goto } from '$app/navigation';
  import { apiCall } from '$lib/api.js';
  import { currentUser } from '$lib/stores.js';

  let user;
  let unsubUser = currentUser.subscribe(v => user = v);

  let loading = $state(true);
  let eurData = $state(null);
  let error = $state('');
  let selectedJahr = $state(new Date().getFullYear());

  const tiles = [
    { icon: '📥', title: 'Eingangsrechnungen', desc: 'Rechnungen & Quittungen hochladen und verwalten', href: '/buchhaltung/eingang' },
    { icon: '📊', title: 'Einnahmenüberschussrechnung', desc: 'EÜR automatisch aus Ein- und Ausgangsrechnungen', href: '/buchhaltung/eur' },
    { icon: '📋', title: 'UStVA-Vorbereitung', desc: 'Umsatzsteuer-Voranmeldung Daten aufbereiten', href: '/buchhaltung/ustva' },
  ];

  async function loadOverview() {
    loading = true;
    error = '';
    try {
      const res = await apiCall('/eur-generieren', { user_id: user?.id, jahr: selectedJahr });
      if (res.success) eurData = res.eur;
      else error = res.error || 'Fehler beim Laden';
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  onMount(() => { if (user?.id) loadOverview(); });
  onDestroy(() => unsubUser());
</script>

<div class="page-container">
  <div class="page-header">
    <div>
      <div class="page-title">📊 Buchhaltung</div>
      <div class="page-subtitle">Eingangsrechnungen, EÜR und UStVA — alles an einem Ort</div>
    </div>
  </div>

  {#if !loading && eurData}
    <div class="kpi-grid" style="margin-bottom:24px">
      <div class="kpi-card">
        <div class="kpi-label">Einnahmen {selectedJahr}</div>
        <div class="kpi-val kpi-green">{eurData.einnahmen?.brutto?.toLocaleString('de-DE', {minimumFractionDigits:2})} €</div>
        <div class="kpi-sub">Netto: {eurData.einnahmen?.netto?.toLocaleString('de-DE', {minimumFractionDigits:2})} €</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Ausgaben {selectedJahr}</div>
        <div class="kpi-val kpi-red">{eurData.ausgaben?.brutto?.toLocaleString('de-DE', {minimumFractionDigits:2})} €</div>
        <div class="kpi-sub">Netto: {eurData.ausgaben?.netto?.toLocaleString('de-DE', {minimumFractionDigits:2})} €</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Gewinn (Netto)</div>
        <div class="kpi-val" class:kpi-green={eurData.ergebnis?.gewinn_netto >= 0} class:kpi-red={eurData.ergebnis?.gewinn_netto < 0}>
          {eurData.ergebnis?.gewinn_netto?.toLocaleString('de-DE', {minimumFractionDigits:2})} €
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">USt-Zahllast</div>
        <div class="kpi-val kpi-blue">{eurData.ergebnis?.umsatzsteuer_zahllast?.toLocaleString('de-DE', {minimumFractionDigits:2})} €</div>
        <div class="kpi-sub">{eurData.kleinunternehmer ? '§19 UStG — keine USt' : 'USt − Vorsteuer'}</div>
      </div>
    </div>
  {:else if loading}
    <div class="loading"><span class="spinner"></span> Lade Übersicht...</div>
  {:else if error}
    <div class="card" style="padding:20px;color:var(--warning);margin-bottom:20px">⚠️ {error}</div>
  {/if}

  <div class="settings-grid">
    {#each tiles as tile}
      <a href={tile.href} class="settings-tile">
        <div class="settings-tile-icon">{tile.icon}</div>
        <div class="settings-tile-title">{tile.title}</div>
        <div class="settings-tile-desc">{tile.desc}</div>
      </a>
    {/each}
  </div>
</div>

<style>
  .page-container { padding: 24px; max-width: 1200px; }
</style>
