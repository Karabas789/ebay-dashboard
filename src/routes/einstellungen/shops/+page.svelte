<script>
  import { onMount } from 'svelte';
  import { currentUser, showToast } from '$lib/stores.js';
  import { apiCall } from '$lib/api.js';
  import { goto } from '$app/navigation';

  let verbindungen = $state([]);
  let loading = $state(false);
  let modalOffen = $state(false);
  let modalLaeuft = $state(false);
  let testLaeuft = $state({});
  let testErgebnis = $state({});
  let loeschenId = $state(null);
  let loeschenLaeuft = $state(false);

  const shopTypen = [
    { key: 'woocommerce', label: 'WooCommerce',  icon: '🛒', felder: ['shop_url', 'api_key', 'api_secret'] },
    { key: 'shopify',     label: 'Shopify',       icon: '🛍️', felder: ['shop_url', 'access_token'] },
    { key: 'shopware',    label: 'Shopware 6',    icon: '⚙️', felder: ['shop_url', 'api_key', 'api_secret'] },
    { key: 'etsy',        label: 'Etsy',          icon: '🧶', felder: ['api_key', 'api_secret'] },
    { key: 'amazon',      label: 'Amazon',        icon: '📦', felder: ['shop_url', 'api_key', 'api_secret'] },
  ];

  let form = $state({
    shop_type: 'woocommerce',
    shop_name: '',
    shop_url: '',
    api_key: '',
    api_secret: '',
    access_token: '',
  });

  let aktiverTyp = $derived(shopTypen.find(t => t.key === form.shop_type));

  function resetForm() {
    form = { shop_type: 'woocommerce', shop_name: '', shop_url: '', api_key: '', api_secret: '', access_token: '' };
  }

  async function ladeVerbindungen() {
    loading = true;
    try {
      const data = await apiCall('shop-connections-laden', { user_id: $currentUser.id });
      verbindungen = data?.connections || [];
    } catch(e) {
      showToast('Fehler beim Laden der Shop-Verbindungen');
    } finally {
      loading = false;
    }
  }

  async function speichern() {
    if (!form.shop_name.trim()) { showToast('Bitte Shop-Namen eingeben.'); return; }
    if (aktiverTyp?.felder.includes('shop_url') && !form.shop_url.trim()) { showToast('Bitte Shop-URL eingeben.'); return; }
    if (aktiverTyp?.felder.includes('api_key') && !form.api_key.trim()) { showToast('Bitte API-Key eingeben.'); return; }
    modalLaeuft = true;
    try {
      await apiCall('shop-connection-speichern', {
        user_id: $currentUser.id,
        shop_type: form.shop_type,
        shop_name: form.shop_name,
        shop_url: form.shop_url,
        api_key: form.api_key,
        api_secret: form.api_secret,
        access_token: form.access_token,
      });
      showToast('✅ Shop-Verbindung gespeichert');
      modalOffen = false;
      resetForm();
      await ladeVerbindungen();
    } catch(e) {
      showToast('Fehler beim Speichern: ' + e.message);
    } finally {
      modalLaeuft = false;
    }
  }

  async function testen(id) {
    testLaeuft = { ...testLaeuft, [id]: true };
    testErgebnis = { ...testErgebnis, [id]: null };
    try {
      const data = await apiCall('shop-connection-testen', { user_id: $currentUser.id, connection_id: id });
      testErgebnis = { ...testErgebnis, [id]: data?.success ? 'ok' : 'fehler' };
      showToast(data?.success ? '✅ Verbindung erfolgreich' : '❌ Verbindung fehlgeschlagen');
    } catch(e) {
      testErgebnis = { ...testErgebnis, [id]: 'fehler' };
      showToast('❌ Verbindungstest fehlgeschlagen');
    } finally {
      testLaeuft = { ...testLaeuft, [id]: false };
    }
  }

  async function loeschen(id) {
    loeschenLaeuft = true;
    try {
      await apiCall('shop-connection-loeschen', { user_id: $currentUser.id, connection_id: id });
      showToast('Verbindung gelöscht');
      loeschenId = null;
      await ladeVerbindungen();
    } catch(e) {
      showToast('Fehler beim Löschen');
    } finally {
      loeschenLaeuft = false;
    }
  }

  async function toggleAktiv(v) {
    try {
      await apiCall('shop-connection-speichern', {
        user_id: $currentUser.id,
        connection_id: v.id,
        aktiv: !v.aktiv
      });
      await ladeVerbindungen();
    } catch(e) {
      showToast('Fehler beim Aktualisieren');
    }
  }

  function shopTypInfo(key) {
    return shopTypen.find(t => t.key === key) || { label: key, icon: '🏪' };
  }

  onMount(ladeVerbindungen);
</script>

<div class="page-container">
  <div class="page-hdr">
    <div class="hdr-left">
      <button class="btn-back" onclick={() => goto('/einstellungen')}>← Zurück</button>
      <div>
        <div class="page-title">🛒 Shop-Verbindungen</div>
        <div class="page-sub">Verbinde deine Online-Shops für automatische Rechnungserstellung</div>
      </div>
    </div>
    <button class="btn-primary" onclick={() => { resetForm(); modalOffen = true; }}>+ Shop hinzufügen</button>
  </div>

  <!-- Info-Banner -->
  <div class="info-banner">
    <span class="info-icon">💡</span>
    <div>
      <strong>So funktioniert es:</strong> Verbinde deinen Shop, importiere dann Bestellungen unter
      <a href="/rechnungen/import" class="info-link">Rechnungen → Importieren</a>
      und erstelle automatisch Rechnungen.
    </div>
  </div>

  <!-- Verbindungen Liste -->
  {#if loading}
    <div class="lade-hinweis">⏳ Lade Shop-Verbindungen...</div>
  {:else if verbindungen.length === 0}
    <div class="leer-box">
      <div class="leer-icon">🏪</div>
      <div class="leer-titel">Noch keine Shop-Verbindungen</div>
      <div class="leer-sub">Füge deinen ersten Shop hinzu um Bestellungen zu importieren.</div>
      <button class="btn-primary" style="margin-top:16px" onclick={() => { resetForm(); modalOffen = true; }}>+ Shop hinzufügen</button>
    </div>
  {:else}
    <div class="verbindungen-liste">
      {#each verbindungen as v (v.id)}
        <div class="verbindung-card {v.aktiv ? '' : 'inaktiv'}">
          <div class="v-icon">{shopTypInfo(v.shop_type).icon}</div>
          <div class="v-info">
            <div class="v-name">{v.shop_name}</div>
            <div class="v-typ">{shopTypInfo(v.shop_type).label}</div>
            {#if v.shop_url}<div class="v-url">{v.shop_url}</div>{/if}
          </div>
          <div class="v-status">
            {#if testErgebnis[v.id] === 'ok'}
              <span class="badge badge-ok">✅ OK</span>
            {:else if testErgebnis[v.id] === 'fehler'}
              <span class="badge badge-fehler">❌ Fehler</span>
            {:else}
              <span class="badge {v.aktiv ? 'badge-aktiv' : 'badge-inaktiv'}">{v.aktiv ? 'Aktiv' : 'Inaktiv'}</span>
            {/if}
          </div>
          <div class="v-actions">
            <button class="btn-ghost btn-sm" onclick={() => testen(v.id)} disabled={testLaeuft[v.id]}>
              {testLaeuft[v.id] ? '⏳' : '🔌'} Testen
            </button>
            <a href="/rechnungen/import" class="btn-ghost btn-sm">📥 Importieren</a>
            <button class="btn-ghost btn-sm" onclick={() => toggleAktiv(v)}>
              {v.aktiv ? '⏸ Deaktivieren' : '▶ Aktivieren'}
            </button>
            <button class="btn-danger btn-sm" onclick={() => loeschenId = v.id}>🗑</button>
          </div>
        </div>
      {/each}
    </div>
  {/if}

  <!-- Unterstützte Shops -->
  <div class="shops-info">
    <div class="shops-info-titel">Unterstützte Shop-Systeme</div>
    <div class="shops-grid">
      {#each shopTypen as t}
        <div class="shop-chip">
          <span>{t.icon}</span>
          <span>{t.label}</span>
        </div>
      {/each}
      <div class="shop-chip chip-bald">
        <span>🔜</span>
        <span>Weitere folgen</span>
      </div>
    </div>
  </div>

<!-- Modal: Shop hinzufügen -->
{#if modalOffen}
  <div class="modal-overlay" onclick={() => { if (event.target === event.currentTarget) modalOffen = false; }}>
    <div class="modal-box">
      <div class="modal-hdr">
        <div>
          <div class="modal-titel">Shop hinzufügen</div>
          <div class="modal-sub">Verbinde einen neuen Online-Shop</div>
        </div>
        <button class="modal-close" onclick={() => modalOffen = false}>✕</button>
      </div>
      <div class="modal-body">

        <!-- Shop-Typ Auswahl -->
        <div class="form-group">
          <label>Shop-System</label>
          <div class="typ-grid">
            {#each shopTypen as t}
              <button
                class="typ-btn {form.shop_type === t.key ? 'aktiv' : ''}"
                onclick={() => form.shop_type = t.key}
              >{t.icon} {t.label}</button>
            {/each}
          </div>
        </div>

        <!-- Shop-Name -->
        <div class="form-group">
          <label>Shop-Name *</label>
          <input type="text" bind:value={form.shop_name} placeholder="z.B. Mein WooCommerce Shop" />
        </div>

        <!-- Shop-URL -->
        {#if aktiverTyp?.felder.includes('shop_url')}
          <div class="form-group">
            <label>Shop-URL *</label>
            <input type="text" bind:value={form.shop_url} placeholder="https://meinshop.de" />
          </div>
        {/if}

        <!-- API Key -->
        {#if aktiverTyp?.felder.includes('api_key')}
          <div class="form-group">
            <label>API Key / Consumer Key *</label>
            <input type="text" bind:value={form.api_key} placeholder="ck_..." />
          </div>
        {/if}

        <!-- API Secret -->
        {#if aktiverTyp?.felder.includes('api_secret')}
          <div class="form-group">
            <label>API Secret / Consumer Secret</label>
            <input type="password" bind:value={form.api_secret} placeholder="cs_..." />
          </div>
        {/if}

        <!-- Access Token (Shopify) -->
        {#if aktiverTyp?.felder.includes('access_token')}
          <div class="form-group">
            <label>Access Token *</label>
            <input type="password" bind:value={form.access_token} placeholder="shpat_..." />
          </div>
        {/if}

        <!-- Hilfe-Hinweis je Shop-Typ -->
        <div class="hilfe-box">
          {#if form.shop_type === 'woocommerce'}
            💡 WooCommerce → WordPress Admin → WooCommerce → Einstellungen → Erweitert → REST API → Neuen Schlüssel erstellen
          {:else if form.shop_type === 'shopify'}
            💡 Shopify Admin → Apps → App-Entwicklung → App erstellen → Admin API Access Token
          {:else if form.shop_type === 'shopware'}
            💡 Shopware Admin → Einstellungen → System → Integrationen → Integration hinzufügen
          {:else if form.shop_type === 'etsy'}
            💡 Etsy Developer Portal → etsy.com/developers → App erstellen → API Key
          {:else if form.shop_type === 'amazon'}
            💡 Amazon Seller Central → Apps & Services → Develop Apps → SP-API Credentials
          {/if}
        </div>

      </div>
      <div class="modal-footer">
        <button class="btn-ghost" onclick={() => modalOffen = false}>Abbrechen</button>
        <button class="btn-primary" onclick={speichern} disabled={modalLaeuft}>
          {modalLaeuft ? '⏳ Speichern...' : '✅ Verbindung speichern'}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- Löschen-Bestätigung -->
{#if loeschenId}
  <div class="modal-overlay" onclick={() => { if (event.target === event.currentTarget) loeschenId = null; }}>
    <div class="modal-box modal-klein">
      <div class="modal-hdr">
        <div class="modal-titel">Verbindung löschen?</div>
        <button class="modal-close" onclick={() => loeschenId = null}>✕</button>
      </div>
      <div class="modal-body">
        <p style="font-size:0.87rem;color:var(--text2);line-height:1.6">
          Diese Shop-Verbindung wird dauerhaft gelöscht. Bereits erstellte Rechnungen bleiben erhalten.
        </p>
      </div>
      <div class="modal-footer">
        <button class="btn-ghost" onclick={() => loeschenId = null}>Abbrechen</button>
        <button class="btn-danger" onclick={() => loeschen(loeschenId)} disabled={loeschenLaeuft}>
          {loeschenLaeuft ? '⏳...' : '🗑 Löschen'}
        </button>
      </div>
    </div>
  </div>
{/if}
</div>

<style>
  .page-container { padding: 24px; max-width: 1200px; margin: 0 auto; }
  .page-hdr { display:flex; align-items:flex-start; justify-content:space-between; margin-bottom:20px; flex-wrap:wrap; gap:12px; }
  .page-title { font-size:1.3rem; font-weight:700; color:var(--text); }
  .page-sub { font-size:0.85rem; color:var(--text2); margin-top:2px; }
  .hdr-actions { display:flex; gap:8px; align-items:center; }

  .info-banner { background:#eff6ff; border:1px solid #bfdbfe; border-radius:10px; padding:12px 16px; font-size:0.84rem; color:#1d4ed8; margin-bottom:24px; display:flex; gap:10px; align-items:flex-start; line-height:1.5; }
  .info-icon { font-size:1.1rem; flex-shrink:0; }
  .info-link { color:#1d4ed8; font-weight:600; }

  .lade-hinweis { text-align:center; padding:40px; color:var(--text3); font-size:0.9rem; }

  .leer-box { text-align:center; padding:60px 24px; background:var(--surface); border:1px solid var(--border); border-radius:12px; }
  .leer-icon { font-size:3rem; margin-bottom:12px; }
  .leer-titel { font-size:1rem; font-weight:700; color:var(--text); margin-bottom:6px; }
  .leer-sub { font-size:0.85rem; color:var(--text2); }

  .verbindungen-liste { display:flex; flex-direction:column; gap:10px; margin-bottom:32px; }
  .verbindung-card { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:16px 20px; display:flex; align-items:center; gap:14px; flex-wrap:wrap; transition:border-color 0.15s; }
  .verbindung-card:hover { border-color:var(--primary); }
  .verbindung-card.inaktiv { opacity:0.6; }
  .v-icon { font-size:1.8rem; flex-shrink:0; }
  .v-info { flex:1; min-width:150px; }
  .v-name { font-size:0.95rem; font-weight:700; color:var(--text); }
  .v-typ { font-size:0.78rem; color:var(--text3); margin-top:2px; }
  .v-url { font-size:0.75rem; color:var(--text3); margin-top:2px; font-family:monospace; }
  .v-status { flex-shrink:0; }
  .v-actions { display:flex; gap:6px; flex-wrap:wrap; }

  .badge { font-size:0.75rem; font-weight:600; padding:3px 10px; border-radius:99px; }
  .badge-aktiv { background:#f0fdf4; color:#16a34a; border:1px solid #bbf7d0; }
  .badge-inaktiv { background:var(--surface2); color:var(--text3); border:1px solid var(--border); }
  .badge-ok { background:#f0fdf4; color:#16a34a; border:1px solid #bbf7d0; }
  .badge-fehler { background:#fef2f2; color:#dc2626; border:1px solid #fecaca; }

  .shops-info { margin-top:8px; }
  .shops-info-titel { font-size:0.78rem; font-weight:700; color:var(--text3); text-transform:uppercase; letter-spacing:0.06em; margin-bottom:10px; }
  .shops-grid { display:flex; flex-wrap:wrap; gap:8px; }
  .shop-chip { background:var(--surface); border:1px solid var(--border); border-radius:99px; padding:5px 14px; font-size:0.8rem; color:var(--text2); display:flex; align-items:center; gap:6px; }
  .chip-bald { border-style:dashed; color:var(--text3); }

  /* Modal */
  .modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.5); backdrop-filter:blur(3px); z-index:999; display:flex; align-items:center; justify-content:center; padding:20px; }
  .modal-box { background:var(--surface); border:1px solid var(--border); border-radius:14px; width:100%; max-width:780px; max-height:90vh; display:flex; flex-direction:column; box-shadow:0 20px 60px rgba(0,0,0,0.2); }
  .modal-klein { max-width:400px; }
  .modal-hdr { display:flex; align-items:flex-start; justify-content:space-between; padding:18px 20px 14px; border-bottom:1px solid var(--border); }
  .modal-titel { font-size:1rem; font-weight:700; color:var(--text); }
  .modal-sub { font-size:0.78rem; color:var(--text3); margin-top:2px; }
  .modal-close { background:none; border:none; color:var(--text3); font-size:1rem; cursor:pointer; padding:4px; border-radius:4px; }
  .modal-close:hover { color:var(--text); background:var(--surface2); }
  .modal-body { padding:20px; overflow-y:auto; flex:1; display:flex; flex-direction:column; gap:14px; }
  .modal-footer { display:flex; gap:8px; justify-content:flex-end; padding:14px 20px; border-top:1px solid var(--border); }

  /* Form */
  .form-group { display:flex; flex-direction:column; gap:5px; }
  .form-group label { font-size:0.78rem; color:var(--text2); font-weight:600; }
  .form-group input { background:var(--surface2); border:1px solid var(--border); color:var(--text); padding:9px 12px; border-radius:8px; font-size:0.85rem; outline:none; }
  .form-group input:focus { border-color:var(--primary); }

  .typ-grid { display:flex; flex-wrap:wrap; gap:6px; }
  .typ-btn { background:var(--surface2); border:1px solid var(--border); color:var(--text2); padding:6px 14px; border-radius:8px; font-size:0.8rem; font-weight:500; cursor:pointer; transition:all 0.15s; }
  .typ-btn:hover { border-color:var(--primary); color:var(--primary); }
  .typ-btn.aktiv { background:var(--primary-light); border-color:var(--primary); color:var(--primary); font-weight:700; }

  .hilfe-box { background:var(--surface2); border:1px solid var(--border); border-radius:8px; padding:10px 14px; font-size:0.78rem; color:var(--text2); line-height:1.6; }

  /* Buttons */
  .btn-primary { background:var(--primary); color:#fff; border:none; padding:8px 18px; border-radius:8px; font-size:0.85rem; font-weight:600; cursor:pointer; text-decoration:none; display:inline-flex; align-items:center; gap:6px; }
  .btn-primary:disabled { opacity:0.6; cursor:not-allowed; }
  .btn-ghost { background:var(--surface2); color:var(--text); border:1px solid var(--border); padding:8px 14px; border-radius:8px; font-size:0.85rem; font-weight:500; cursor:pointer; text-decoration:none; display:inline-flex; align-items:center; gap:4px; }
  .btn-ghost:hover { border-color:var(--primary); color:var(--primary); }
  .btn-danger { background:#fef2f2; color:#dc2626; border:1px solid #fecaca; padding:8px 14px; border-radius:8px; font-size:0.85rem; font-weight:600; cursor:pointer; }
  .btn-danger:hover { background:#fee2e2; }
  .btn-danger:disabled { opacity:0.6; cursor:not-allowed; }
  .btn-sm { padding:5px 10px; font-size:0.78rem; }
  .hdr-left { display:flex; align-items:center; gap:16px; }
  .btn-back {
  background: transparent; border: 1px solid var(--border); color: var(--text2);
  padding: 7px 14px; border-radius: 8px; font-size: 0.83rem; cursor: pointer;
  transition: all 0.15s; white-space: nowrap;
  }
  .btn-back:hover { border-color: var(--primary); color: var(--primary); }
</style>
