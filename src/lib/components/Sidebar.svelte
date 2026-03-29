<script>
  import { page } from '$app/stores';
  import { currentUser, theme, sidebarCollapsed } from '$lib/stores.js';
  import { clearAuth } from '$lib/api.js';
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';

  let user;
  currentUser.subscribe(v => user = v);

  let isDark;
  theme.subscribe(v => isDark = v === 'dark');

  let collapsed = false;
  sidebarCollapsed.subscribe(v => collapsed = v);

  const nav = [
    { path: '/',              icon: '📩', label: 'Nachrichten' },
    { path: '/produkte',      icon: '📦', label: 'Produkte' },
    { path: '/bestellungen',  icon: '🛒', label: 'Bestellungen' },
    { path: '/rechnungen',    icon: '🧾', label: 'Rechnungen' },
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
          <span class="logo-title">eBay Dashboard</span>
          <span class="logo-version">v2.0</span>
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
        class:active={currentPath === item.path || (item.path !== '/' && currentPath.startsWith(item.path))}
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
      <button class="sidebar-action" on:click={toggleTheme} title={isDark ? 'Hell' : 'Dunkel'}>
        {isDark ? '☀️' : '🌙'}
      </button>
      {#if !collapsed}
        <button class="sidebar-action" on:click={logout} title="Ausloggen">
          🚪
        </button>
      {/if}
    </div>
  </div>
</aside>

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

  .sidebar.collapsed {
    width: var(--sidebar-collapsed-width, 68px);
  }

  /* Header */
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

  .logo-img {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    object-fit: contain;
    flex-shrink: 0;
  }

  .logo-img-small {
    width: 30px;
    height: 30px;
    border-radius: 8px;
    object-fit: contain;
  }

  .logo-text { display: flex; flex-direction: column; }
  .logo-title { font-size: 15px; font-weight: 800; color: var(--text); }
  .logo-version { font-size: 11px; color: var(--text3); font-weight: 500; }

  /* Toggle Button */
  .toggle-btn {
    background: none;
    border: 1px solid var(--border);
    border-radius: 8px;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    color: var(--text2);
    transition: background 0.15s, color 0.15s;
    flex-shrink: 0;
  }

  .toggle-btn:hover {
    background: var(--surface2);
    color: var(--text);
  }

  /* Navigation */
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

  /* Collapsed: center icons */
  .sidebar.collapsed .nav-item {
    justify-content: center;
    padding: 10px;
  }

  /* Tooltips bei collapsed */
  .sidebar.collapsed .nav-item::after {
    content: attr(data-tooltip);
    position: absolute;
    left: calc(100% + 12px);
    top: 50%;
    transform: translateY(-50%);
    background: var(--text);
    color: var(--surface);
    padding: 5px 12px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 500;
    white-space: nowrap;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.15s;
    z-index: 200;
  }

  .sidebar.collapsed .nav-item:hover::after {
    opacity: 1;
  }

  /* Footer */
  .sidebar-footer {
    padding: 12px 14px 16px;
    border-top: 1px solid var(--border);
  }

  .sidebar-user {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 6px;
    overflow: hidden;
  }

  .sidebar.collapsed .sidebar-user {
    justify-content: center;
    padding: 8px 0;
  }

  .user-avatar {
    width: 34px;
    height: 34px;
    border-radius: 10px;
    background: #3777CF;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-weight: 800;
    flex-shrink: 0;
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

  .sidebar-actions {
    display: flex;
    gap: 4px;
    padding: 6px 4px 0;
  }

  .sidebar.collapsed .sidebar-actions {
    justify-content: center;
  }

  .sidebar-action {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 8px;
    border-radius: 8px;
    font-size: 16px;
    background: var(--surface2);
    border: 1px solid var(--border);
    cursor: pointer;
    transition: all 0.15s;
  }

  .sidebar.collapsed .sidebar-action {
    flex: none;
    width: 38px;
  }

  .sidebar-action:hover { background: var(--border); }
</style>
