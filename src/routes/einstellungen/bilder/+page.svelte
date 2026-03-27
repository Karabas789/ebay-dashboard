<script>
  import { goto } from '$app/navigation';
</script>
<div class="page-header">
  <div>
    <button class="btn btn-ghost" on:click={() => goto('/einstellungen')}>← Zurück</button>
    <h1 class="page-title" style="margin-top:8px;">🖼️ Produktbilder</h1>
    <p class="page-subtitle">Bilder-URLs für Produkte verwalten</p>
  </div>
</div>
<div class="card" style="margin-top:20px;">
  <div class="empty-state">
    <div style="font-size:48px;opacity:0.3;margin-bottom:12px;">🖼️</div>
    <p>Produktbilder-Verwaltung wird in Phase 2 portiert.</p>
  </div>
</div>
