<script>
  import { currentUser } from '$lib/stores.js';
  let user;
  currentUser.subscribe(v => user = v);
</script>

<div class="page-header">
  <div>
    <h1 class="page-title">📩 Nachrichten</h1>
    <p class="page-subtitle">eBay Kundennachrichten verwalten</p>
  </div>
  <button class="btn btn-primary">🔄 Aktualisieren</button>
</div>

<div class="card" style="margin-top:20px;">
  <div class="empty-state">
    <div style="font-size:48px;opacity:0.3;margin-bottom:12px;">📩</div>
    <p>Nachrichten werden in Phase 2 portiert.</p>
    <p style="color:var(--text3);margin-top:4px;">Hallo {user?.ebay_user_id || 'User'} — das Dashboard läuft! 🎉</p>
  </div>
</div>

<style>
  .page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
  .page-title { font-size: 22px; font-weight: 800; }
  .page-subtitle { font-size: 13px; color: var(--text2); margin-top: 2px; }
</style>
