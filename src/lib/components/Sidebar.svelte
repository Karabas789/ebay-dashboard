<script>
  import { page } from '$app/stores';
  import { currentUser, theme, sidebarCollapsed, sessionExpired } from '$lib/stores.js';
  import { clearAuth, setAuth, API } from '$lib/api.js';
  import { goto } from '$app/navigation';
  import { onMount, onDestroy } from 'svelte';
  import EbayVerbindenModal from '$lib/components/EbayVerbindenModal.svelte';

  let user;
  let unsubUser = currentUser.subscribe(v => user = v);
  let isDark;
  let unsubTheme = theme.subscribe(v => isDark = v === 'dark');
  let collapsed = false;
  let unsubCollapsed = sidebarCollapsed.subscribe(v => collapsed = v);
  let showSessionModal = false;
  let sessionEmail = '';
  let sessionPassword = '';
  let sessionError = '';
  let sessionLoading = false;
  let unsubSession = sessionExpired.subscribe(v => {
    if (v && !showSessionModal) {
      sessionEmail = user?.email || '';
      sessionPassword = '';
      sessionError = '';
      showSessionModal = true;
    }
  });
  let showEbayModal = false;
  let ebayModalUser = '';
  let ebayOAuthUrl = '';

  onDestroy(() => { unsubUser(); unsubTheme(); unsubCollapsed(); unsubSession(); });

  const nav = [
    { path: '/nachrichten',  icon: '📩', label: 'Nachrichten' },
    { path: '/produkte',     icon: '📦', label: 'Produkte' },
    { path: '/bestellungen', icon: '🛒', label: 'Bestellungen' },
    { path: '/rechnungen',   icon: '🧾', label: 'Rechnungen' },
  ];

  const einstellungenNav = [
    { path: '/einstellungen',                  icon: '⚙️', label: 'Allgemein' },
    { path: '/einstellungen/email',            icon: '📧', label: 'E-Mail' },
    { path: '/einstellungen/rechnungsvorlage', icon: '🧾', label: 'Rechnungsvorlage' },
  ];

  function toggleSidebar() {
    const next = !collapsed;
    sidebarCollapsed.set(next);
    localStorage.setItem('sidebar_collapsed', JSON.stringify(next));
  }
  function toggleTheme() {
    const next = isDark ? 'light' : 'dark';
    theme.set(next);
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('ebay_theme', next);
  }
  function logout() { clearAuth(); currentUser.set(null); goto('/login'); }
  function ebayOAuthLogin() {
    const userId = user?.id || '';
    const ebayUsername = user?.ebay_user_id || '';
    const state = ebayUsername + '_uid_' + userId;
    const params = new URLSearchParams({
      client_id: 'VitaliDu-TestAPI-PRD-2b448418d-05f39944',
      redirect_uri: 'Vitali_Dubs-VitaliDu-TestAP-lnbmshlxd',
      response_type: 'code',
      state: state,
      scope: 'https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/sell.fulfillment https://api.ebay.com/oauth/api_scope/sell.inventory https://api.ebay.com/oauth/api_scope/sell.account https://api.ebay.com/oauth/api_scope/sell.finances https://api.ebay.com/oauth/api_scope/commerce.message'
    });
    ebayModalUser = ebayUsername || 'unbekannt';
    ebayOAuthUrl = 'https://auth.ebay.com/oauth2/authorize?' + params.toString();
    showEbayModal = true;
  }
  function handleEbayConfirm() { showEbayModal = false; window.open(ebayOAuthUrl, '_blank', 'width=600,height=700'); }
  function openSessionModal() { sessionEmail = user?.email || ''; sessionPassword = ''; sessionError = ''; showSessionModal = true; }
  async function doSessionRenew() {
    sessionError = ''; sessionLoading = true;
    try {
      const res = await fetch(API + '/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: sessionEmail, password: sessionPassword }) });
      const data = await res.json();
      if (data.success) { setAuth(data.token, data.user); currentUser.set(data.user); sessionExpired.set(false); showSessionModal = false; window.location.reload(); }
      else { sessionError = data.message || 'Anmeldung fehlgeschlagen.'; }
    } catch (e) { sessionError = 'Verbindungsfehler.'; }
    finally { sessionLoading = false; }
  }
  onMount(() => { const saved = localStorage.getItem('sidebar_collapsed'); if (saved === 'true') sidebarCollapsed.set(true); });

  $: currentPath = $page.url.pathname;
  $: istInEinstellungen = currentPath.startsWith('/einstellungen');
  $: isActiveMain = (path) => currentPath === path || currentPath.startsWith(path);
  $: isActiveSub = (path) => path === '/einstellungen' ? currentPath === '/einstellungen' : currentPath.startsWith(path);
</script>

<aside class="sidebar" class:collapsed>

  <div class="sidebar-logo">
    <div class="logo-icon">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <rect x="2" y="3" width="20" height="14" rx="2"/>
        <path d="M8 21h8M12 17v4"/>
      </svg>
    </div>
    <div class="logo-texts">
      <div class="logo-text">eBay Dashboard</div>
      <div class="logo-sub">Verkäufer Übersicht</div>
    </div>
    <button class="toggle-btn" on:click={toggleSidebar} title={collapsed ? 'Ausklappen' : 'Einklappen'}>
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        {#if collapsed}<polyline points="9 18 15 12 9 6"/>
        {:else}<polyline points="15 18 9 12 15 6"/>{/if}
      </svg>
    </button>
  </div>

  <nav class="sidebar-nav">
    <div class="nav-section">
      <div class="nav-label">Übersicht</div>
      {#each nav as item}
        <a href={item.path} class="nav-item" class:active={isActiveMain(item.path)} data-tooltip={item.label}>
          <span class="nav-icon-wrap">{item.icon}</span>
          <span class="nav-label-text">{item.label}</span>
        </a>
      {/each}
    </div>

    <div class="nav-section">
      <div class="nav-label">Verwaltung</div>
      <a href="/einstellungen" class="nav-item" class:active={currentPath === '/einstellungen'} data-tooltip="Einstellungen">
        <span class="nav-icon-wrap">⚙️</span>
        <span class="nav-label-text">Einstellungen</span>
      </a>
      {#if istInEinstellungen}
        <div class="submenu">
          {#each einstellungenNav as sub}
            <a href={sub.path} class="nav-item nav-item-sub" class:active={isActiveSub(sub.path)} data-tooltip={sub.label}>
              <span class="nav-icon-wrap sub-icon">{sub.icon}</span>
              <span class="nav-label-text">{sub.label}</span>
            </a>
          {/each}
        </div>
      {/if}
    </div>
  </nav>

  <div class="sidebar-footer">
    <div class="user-card">
      <div class="user-avatar">
        {user?.ebay_user_id?.charAt(0)?.toUpperCase() || user?.email?.charAt(0)?.toUpperCase() || '?'}
      </div>
      <div class="user-info">
        <div class="user-name">{user?.ebay_user_id || user?.email || '—'}</div>
        <div class="user-sub">{user?.email || ''}</div>
      </div>
    </div>
    <div class="sidebar-actions">
      <button class="sidebar-action-btn" on:click={toggleTheme} title={isDark ? 'Hell' : 'Dunkel'}>{isDark ? '☀️' : '🌙'}</button>
      <button class="sidebar-action-btn hideforcollapsed" on:click={ebayOAuthLogin} title="eBay verbinden">🔑</button>
      <button class="sidebar-action-btn hideforcollapsed" on:click={openSessionModal} title="Session erneuern">🔄</button>
      <button class="sidebar-action-btn hideforcollapsed" on:click={logout} title="Ausloggen">🚪</button>
    </div>
  </div>
</aside>

{#if showSessionModal}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div class="session-overlay" on:click|self={() => { if (!$sessionExpired) showSessionModal = false; }}>
    <div class="session-modal">
      <div class="session-title">🔄 Session erneuern</div>
      {#if $sessionExpired}
        <div class="session-banner">⚠️ Deine Session ist abgelaufen. Bitte melde dich erneut an.</div>
      {:else}
        <p class="session-desc">Melde dich erneut an, um fortzufahren.</p>
      {/if}
      <div class="session-field">
        <label>E-Mail</label>
        <input type="email" bind:value={sessionEmail} placeholder="name@shop.de" />
      </div>
      <div class="session-field">
        <label>Passwort</label>
        <input type="password" bind:value={sessionPassword} placeholder="••••••••" on:keydown={(e) => { if (e.key === 'Enter') doSessionRenew(); }} />
      </div>
      {#if sessionError}<div class="session-error">{sessionError}</div>{/if}
      <div class="session-actions">
        {#if !$sessionExpired}
          <button class="session-btn-cancel" on:click={() => showSessionModal = false}>Abbrechen</button>
        {/if}
        <button class="session-btn-ok" on:click={doSessionRenew} disabled={sessionLoading}>{sessionLoading ? '⏳ Anmelden...' : '✓ Anmelden'}</button>
      </div>
    </div>
  </div>
{/if}

<EbayVerbindenModal bind:open={showEbayModal} expectedUser={ebayModalUser} onConfirm={handleEbayConfirm} onCancel={() => showEbayModal = false} />

<style>
  .sidebar { width:var(--sidebar-width,220px); height:100vh; background:var(--surface); border-right:1px solid var(--border); display:flex; flex-direction:column; position:fixed; left:0; top:0; z-index:50; transition:width 0.25s cubic-bezier(0.4,0,0.2,1); overflow:hidden; }
  .sidebar.collapsed { width:var(--sidebar-collapsed-width,68px); }

  .sidebar-logo { display:flex; align-items:center; gap:10px; padding:18px 14px 14px; border-bottom:1px solid var(--border); margin-bottom:8px; min-height:64px; flex-shrink:0; }
  .logo-icon { width:32px; height:32px; background:var(--primary); border-radius:8px; display:flex; align-items:center; justify-content:center; flex-shrink:0; color:#fff; }
  .logo-texts { flex:1; overflow:hidden; }
  .logo-text { font-size:14px; font-weight:800; color:var(--text); white-space:nowrap; }
  .logo-sub  { font-size:10px; color:var(--text3); margin-top:1px; white-space:nowrap; }
  .sidebar.collapsed .logo-texts { display:none; }
  .toggle-btn { margin-left:auto; background:none; border:1px solid var(--border); border-radius:6px; width:26px; height:26px; display:flex; align-items:center; justify-content:center; cursor:pointer; color:var(--text3); transition:all 0.15s; flex-shrink:0; }
  .toggle-btn:hover { background:var(--surface2); color:var(--text); }

  .sidebar-nav { flex:1; padding:4px 12px; display:flex; flex-direction:column; gap:16px; overflow-y:auto; overflow-x:hidden; }
  .sidebar.collapsed .sidebar-nav { padding:4px 8px; }
  .nav-section { display:flex; flex-direction:column; gap:1px; }
  .nav-label { font-size:9px; font-weight:700; color:var(--text3); text-transform:uppercase; letter-spacing:1px; padding:8px 8px 4px; white-space:nowrap; overflow:hidden; }
  .sidebar.collapsed .nav-label { visibility:hidden; height:0; padding:0; margin:0; }

  .nav-item { display:flex; align-items:center; gap:10px; padding:8px 10px; border-radius:8px; font-size:12.5px; font-weight:500; color:var(--text2); text-decoration:none; transition:all 0.12s; white-space:nowrap; border:none; background:none; width:100%; text-align:left; }
  .nav-item:hover  { background:var(--surface2); color:var(--text); }
  .nav-item.active { background:var(--primary-light); color:var(--primary); font-weight:600; }
  .nav-icon-wrap { font-size:15px; width:20px; text-align:center; flex-shrink:0; }
  .nav-label-text { flex:1; overflow:hidden; }
  .sidebar.collapsed .nav-label-text { display:none; }
  .sidebar.collapsed .nav-item { justify-content:center; padding:10px; }

  .submenu { display:flex; flex-direction:column; gap:1px; margin-left:8px; border-left:2px solid var(--border); padding-left:4px; margin-top:2px; }
  .sidebar.collapsed .submenu { margin-left:0; border-left:none; padding-left:0; }
  .nav-item-sub { font-size:12px; padding:6px 10px; }
  .sub-icon { font-size:13px; }

  .sidebar.collapsed .nav-item { position:relative; }
  .sidebar.collapsed .nav-item::after { content:attr(data-tooltip); position:absolute; left:calc(100% + 12px); top:50%; transform:translateY(-50%); background:var(--text); color:var(--surface); padding:5px 12px; border-radius:6px; font-size:12px; font-weight:500; white-space:nowrap; opacity:0; pointer-events:none; transition:opacity 0.15s; z-index:200; }
  .sidebar.collapsed .nav-item:hover::after { opacity:1; }

  .sidebar-footer { margin-top:auto; padding:12px; border-top:1px solid var(--border); flex-shrink:0; }
  .user-card { display:flex; align-items:center; gap:10px; padding:8px 10px; border-radius:8px; cursor:pointer; transition:background 0.12s; margin-bottom:8px; overflow:hidden; }
  .user-card:hover { background:var(--surface2); }
  .user-avatar { width:30px; height:30px; background:var(--primary-light); border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:700; color:var(--primary); flex-shrink:0; }
  .user-info { overflow:hidden; }
  .sidebar.collapsed .user-info { display:none; }
  .user-name { font-size:12px; font-weight:600; color:var(--text); white-space:nowrap; }
  .user-sub  { font-size:10px; color:var(--text3); white-space:nowrap; }
  .sidebar-actions { display:flex; gap:4px; }
  .sidebar-action-btn { flex:1; padding:7px; border-radius:7px; font-size:15px; background:var(--surface2); border:1px solid var(--border); cursor:pointer; transition:all 0.15s; display:flex; align-items:center; justify-content:center; }
  .sidebar.collapsed .sidebar-action-btn { flex:none; width:38px; }
  .sidebar.collapsed .hideforcollapsed { display:none; }
  .sidebar-action-btn:hover { background:var(--border); }

  .session-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.6); backdrop-filter:blur(4px); z-index:9999; display:flex; align-items:center; justify-content:center; }
  .session-modal { background:var(--surface); border:1px solid var(--border); border-radius:16px; padding:28px; width:400px; max-width:95vw; box-shadow:0 20px 60px rgba(0,0,0,0.25); }
  .session-title { font-size:18px; font-weight:700; margin-bottom:8px; color:var(--text); }
  .session-desc  { font-size:13px; color:var(--text2); margin-bottom:20px; line-height:1.6; }
  .session-banner { background:rgba(239,68,68,0.08); border:1.5px solid rgba(239,68,68,0.25); border-radius:10px; padding:12px 14px; font-size:13px; font-weight:600; color:#ef4444; margin-bottom:20px; line-height:1.5; }
  .session-field { margin-bottom:14px; }
  .session-field label { display:block; font-size:12px; font-weight:600; color:var(--text2); margin-bottom:6px; }
  .session-field input { width:100%; padding:10px 12px; border:1.5px solid var(--border); border-radius:9px; background:var(--surface2); color:var(--text); font-family:inherit; font-size:13px; outline:none; box-sizing:border-box; }
  .session-field input:focus { border-color:var(--primary); }
  .session-error { color:#ef4444; font-size:12px; margin-top:6px; margin-bottom:4px; }
  .session-actions { display:flex; gap:10px; margin-top:20px; justify-content:flex-end; }
  .session-btn-cancel { background:var(--surface2); border:1.5px solid var(--border); border-radius:9px; padding:10px 18px; color:var(--text2); font-family:inherit; font-size:13px; font-weight:600; cursor:pointer; }
  .session-btn-cancel:hover { border-color:var(--text3); }
  .session-btn-ok { background:var(--primary); border:none; border-radius:9px; padding:10px 22px; color:white; font-family:inherit; font-size:13px; font-weight:700; cursor:pointer; }
  .session-btn-ok:hover { background:var(--primary-dark); }
  .session-btn-ok:disabled { opacity:0.6; cursor:not-allowed; }
</style>
