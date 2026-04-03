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

  onDestroy(() => {
    unsubUser(); unsubTheme(); unsubCollapsed(); unsubSession();
  });

  const nav = [
    { path: '/nachrichten',      icon: '📩', label: 'Nachrichten' },
    { path: '/produkte',         icon: '📦', label: 'Produkte' },
    { path: '/bestellungen',     icon: '🛒', label: 'Bestellungen' },
    { path: '/rechnungen',       icon: '🧾', label: 'Rechnungen' },
    { path: '/rechnungsvorlage', icon: '🖨',  label: 'Rechnungsvorlage' },
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

  function logout() {
    clearAuth();
    currentUser.set(null);
    goto('/login');
  }

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

  function handleEbayConfirm() {
    showEbayModal = false;
    window.open(ebayOAuthUrl, '_blank', 'width=600,height=700');
  }

  function openSessionModal() {
    sessionEmail = user?.email || '';
    sessionPassword = '';
    sessionError = '';
    showSessionModal = true;
  }

  async function doSessionRenew() {
    sessionError = '';
    sessionLoading = true;
    try {
      const res = await fetch(API + '/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: sessionEmail, password: sessionPassword })
      });
      const data = await res.json();
      if (data.success) {
        setAuth(data.token, data.user);
        currentUser.set(data.user);
        sessionExpired.set(false);
        showSessionModal = false;
        window.location.reload();
      } else {
        sessionError = data.message || 'Anmeldung fehlgeschlagen.';
      }
    } catch (e) {
      sessionError = 'Verbindungsfehler.';
    } finally {
      sessionLoading = false;
    }
  }

  onMount(() => {
    const saved = localStorage.getItem('sidebar_collapsed');
    if (saved === 'true') {
      sidebarCollapsed.set(true);
    }
  });

  $: currentPath = $page.url.pathname;
</script>

<aside class="sidebar" class:collapsed>

  <!-- Header: Logo + Toggle -->
  <div class="sidebar-header">
    {#if !collapsed}
      <div class="sidebar-logo">
        <img src="https://assets.zyrosite.com/sKFGVgrqCU2eVSWO/logo_9-isvHGkTKpAcAmGO4.webp" alt="Logo" class="logo-img" />
        <div class="logo-text">
          <span class="logo-title">{user?.ebay_user_id || user?.email || 'Account'}</span>
          <span class="logo-version">eBay Account</span>
        </div>
      </div>
    {:else}
      <img src="https://assets.zyrosite.com/sKFGVgrqCU2eVSWO/logo_9-isvHGkTKpAcAmGO4.webp" alt="Logo" class="logo-img-small" />
    {/if}
    <button class="toggle-btn" on:click={toggleSidebar} title={collapsed ? 'Sidebar ausklappen' : 'Sidebar einklappen'}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2"/>
        <line x1="9" y1="3" x2="9" y2="21"/>
      </svg>
    </button>
  </div>

  <!-- Navigation -->
  <nav class="sidebar-nav">
    {#each nav as item}
      <a
        href={item.path}
        class="nav-item"
        class:active={currentPath === item.path || currentPath.startsWith(item.path)}
        data-tooltip={item.label}
      >
        <span class="nav-icon">{item.icon}</span>
        {#if !collapsed}
          <span class="nav-label">{item.label}</span>
        {/if}
      </a>
    {/each}
  </nav>

  <!-- Bottom: Einstellungen -->
  <div class="sidebar-bottom">
    <a
      href="/einstellungen"
      class="nav-item"
      class:active={currentPath.startsWith('/einstellungen')}
      data-tooltip="Einstellungen"
    >
      <span class="nav-icon">⚙️</span>
      {#if !collapsed}
        <span class="nav-label">Einstellungen</span>
      {/if}
    </a>
  </div>

  <!-- Footer: User + Actions -->
  <div class="sidebar-footer">
    <div class="sidebar-user">
      <div class="user-avatar">
        {user?.ebay_user_id?.charAt(0)?.toUpperCase() || '?'}
      </div>
      {#if !collapsed}
        <div class="user-info">
          <span class="user-name">{user?.ebay_user_id || user?.email || '—'}</span>
          <span class="user-email">{user?.email || ''}</span>
        </div>
      {/if}
    </div>
    <div class="sidebar-actions">
      <button class="sidebar-action" on:click={toggleTheme} data-tooltip-action={isDark ? 'Helles Design' : 'Dunkles Design'}>
        {isDark ? '☀️' : '🌙'}
      </button>
      {#if !collapsed}
        <button class="sidebar-action" on:click={ebayOAuthLogin} data-tooltip-action="eBay verbinden">
          🔑
        </button>
        <button class="sidebar-action" on:click={openSessionModal} data-tooltip-action="Session erneuern">
          🔄
        </button>
        <button class="sidebar-action" on:click={logout} data-tooltip-action="Ausloggen">
          🚪
        </button>
      {/if}
    </div>
  </div>
</aside>

<!-- SESSION MODAL -->
{#if showSessionModal}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div class="session-overlay" on:click|self={() => { if (!$sessionExpired) showSessionModal = false; }}>
    <div class="session-modal">
      <div class="session-title">🔄 Session erneuern</div>
      {#if $sessionExpired}
        <div class="session-banner">
          ⚠️ Deine Session ist abgelaufen. Bitte melde dich erneut an.
        </div>
      {:else}
        <p class="session-desc">Melde dich erneut an, um fortzufahren.</p>
      {/if}
      <div class="session-field">
        <label>E-Mail</label>
        <input type="email" bind:value={sessionEmail} placeholder="name@shop.de" />
      </div>
      <div class="session-field">
        <label>Passwort</label>
        <input type="password" bind:value={sessionPassword} placeholder="••••••••"
          on:keydown={(e) => { if (e.key === 'Enter') doSessionRenew(); }} />
      </div>
      {#if sessionError}
        <div class="session-error">{sessionError}</div>
      {/if}
      <div class="session-actions">
        {#if !$sessionExpired}
          <button class="session-btn-cancel" on:click={() => showSessionModal = false}>Abbrechen</button>
        {/if}
        <button class="session-btn-ok" on:click={doSessionRenew} disabled={sessionLoading}>
          {sessionLoading ? '⏳ Anmelden...' : '✓ Anmelden'}
        </button>
      </div>
    </div>
  </div>
{/if}

<EbayVerbindenModal
  bind:open={showEbayModal}
  expectedUser={ebayModalUser}
  onConfirm={handleEbayConfirm}
  onCancel={() => showEbayModal = false}
/>

<style>
  .sidebar {
    width: var(--sidebar-width);
    height: 100vh;
    background: var(--surface);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    position: fixed;
    left: 0;
    top: 0;
    z-index: 50;
    transition: width 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  }
  .sidebar.collapsed { width: var(--sidebar-collapsed-width, 68px); }

  .sidebar-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 14px;
    border-bottom: 1px solid var(--border);
    min-height: 64px;
    gap: 8px;
  }
  .sidebar.collapsed .sidebar-header {
    justify-content: center;
    padding: 16px 10px;
    flex-direction: column;
    gap: 10px;
  }

  .sidebar-logo {
    display: flex;
    align-items: center;
    gap: 12px;
    overflow: hidden;
    white-space: nowrap;
    min-width: 0;
  }
  .logo-img { width: 32px; height: 32px; border-radius: 8px; object-fit: contain; flex-shrink: 0; }
  .logo-img-small { width: 30px; height: 30px; border-radius: 8px; object-fit: contain; }
  .logo-text { display: flex; flex-direction: column; }
  .logo-title { font-size: 15px; font-weight: 800; color: var(--text); }
  .logo-version { font-size: 11px; color: var(--text3); font-weight: 500; }

  .toggle-btn {
    background: none;
    border: 1px solid var(--border);
    border-radius: 8px;
    width: 32px; height: 32px;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; color: var(--text2);
    transition: background 0.15s, color 0.15s;
    flex-shrink: 0;
  }
  .toggle-btn:hover { background: var(--surface2); color: var(--text); }

  .sidebar-nav {
    flex: 1;
    padding: 12px 10px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    overflow-y: auto;
    overflow-x: hidden;
  }

  .sidebar-bottom {
    padding: 0 10px 8px;
    border-top: 1px solid var(--border);
    padding-top: 8px;
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 14px;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 500;
    color: var(--text2);
    text-decoration: none;
    transition: all 0.1s;
    cursor: pointer;
    position: relative;
    white-space: nowrap;
    overflow: hidden;
  }
  .nav-item:hover { background: var(--surface2); color: var(--text); }
  .nav-item.active { background: var(--surface2); color: var(--text); font-weight: 700; }
  .nav-icon { font-size: 16px; width: 22px; text-align: center; flex-shrink: 0; }
  .nav-label { flex: 1; }

  .sidebar.collapsed .nav-item { justify-content: center; padding: 10px; }
  .sidebar.collapsed .nav-item::after {
    content: attr(data-tooltip);
    position: absolute; left: calc(100% + 12px); top: 50%;
    transform: translateY(-50%);
    background: var(--text); color: var(--surface);
    padding: 5px 12px; border-radius: 6px;
    font-size: 12px; font-weight: 500; white-space: nowrap;
    opacity: 0; pointer-events: none; transition: opacity 0.15s; z-index: 200;
  }
  .sidebar.collapsed .nav-item:hover::after { opacity: 1; }

  .sidebar-footer {
    padding: 12px 14px 16px;
    border-top: 1px solid var(--border);
  }
  .sidebar-user {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 6px; overflow: hidden;
  }
  .sidebar.collapsed .sidebar-user { justify-content: center; padding: 8px 0; }

  .user-avatar {
    width: 34px; height: 34px; border-radius: 10px;
    background: #3777CF; color: white;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; font-weight: 800; flex-shrink: 0;
  }
  .user-info { display: flex; flex-direction: column; min-width: 0; }
  .user-name {
    font-size: 13px; font-weight: 600; color: var(--text);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .user-email {
    font-size: 11px; color: var(--text3);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }

  .sidebar-actions { display: flex; gap: 4px; padding: 6px 4px 0; }
  .sidebar.collapsed .sidebar-actions { justify-content: center; }

  .sidebar-action {
    flex: 1;
    display: flex; align-items: center; justify-content: center;
    padding: 8px; border-radius: 8px; font-size: 16px;
    background: var(--surface2); border: 1px solid var(--border);
    cursor: pointer; transition: all 0.15s;
  }
  .sidebar.collapsed .sidebar-action { flex: none; width: 38px; }
  .sidebar-action:hover { background: var(--border); }

  .sidebar-action {
    position: relative;
  }
  .sidebar-action[data-tooltip-action]::after {
    content: attr(data-tooltip-action);
    position: absolute;
    left: calc(100% + 10px);
    top: 50%;
    transform: translateY(-50%);
    background: var(--text);
    color: var(--surface);
    padding: 5px 10px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 500;
    white-space: nowrap;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.15s;
    z-index: 200;
  }
  .sidebar-action[data-tooltip-action]:hover::after {
    opacity: 1;
  }

  /* Session Modal */
  .session-overlay {
    position: fixed; inset: 0;
    background: rgba(0,0,0,0.6);
    backdrop-filter: blur(4px);
    z-index: 9999;
    display: flex; align-items: center; justify-content: center;
  }
  .session-modal {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 28px;
    width: 400px; max-width: 95vw;
    box-shadow: 0 20px 60px rgba(0,0,0,0.25);
  }
  .session-title { font-size: 18px; font-weight: 700; margin-bottom: 8px; color: var(--text); }
  .session-desc { font-size: 13px; color: var(--text2); margin-bottom: 20px; line-height: 1.6; }
  .session-banner {
    background: rgba(239, 68, 68, 0.08);
    border: 1.5px solid rgba(239, 68, 68, 0.25);
    border-radius: 10px;
    padding: 12px 14px;
    font-size: 13px;
    font-weight: 600;
    color: #ef4444;
    margin-bottom: 20px;
    line-height: 1.5;
  }
  .session-field { margin-bottom: 14px; }
  .session-field label {
    display: block; font-size: 12px; font-weight: 600;
    color: var(--text2); margin-bottom: 6px;
  }
  .session-field input {
    width: 100%; padding: 10px 12px;
    border: 1.5px solid var(--border);
    border-radius: 9px; background: var(--surface2); color: var(--text);
    font-family: inherit; font-size: 13px; outline: none; box-sizing: border-box;
  }
  .session-field input:focus { border-color: var(--primary); }
  .session-error { color: #ef4444; font-size: 12px; margin-top: 6px; margin-bottom: 4px; }
  .session-actions { display: flex; gap: 10px; margin-top: 20px; justify-content: flex-end; }
  .session-btn-cancel {
    background: var(--surface2); border: 1.5px solid var(--border);
    border-radius: 9px; padding: 10px 18px; color: var(--text2);
    font-family: inherit; font-size: 13px; font-weight: 600; cursor: pointer;
  }
  .session-btn-cancel:hover { border-color: var(--text3); }
  .session-btn-ok {
    background: var(--primary); border: none; border-radius: 9px;
    padding: 10px 22px; color: white; font-family: inherit;
    font-size: 13px; font-weight: 700; cursor: pointer;
  }
  .session-btn-ok:hover { background: var(--primary-dark, #2d6ab8); }
  .session-btn-ok:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
