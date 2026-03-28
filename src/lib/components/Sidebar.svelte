<script>
  import { page } from '$app/stores';
  import { currentUser, theme } from '$lib/stores.js';
  import { clearAuth } from '$lib/api.js';
  import { goto } from '$app/navigation';

  let user;
  currentUser.subscribe(v => user = v);

  let isDark;
  theme.subscribe(v => isDark = v === 'dark');

  const nav = [
    { path: '/',              icon: '📩', label: 'Nachrichten' },
    { path: '/produkte',      icon: '📦', label: 'Produkte' },
    { path: '/bestellungen',  icon: '🛒', label: 'Bestellungen' },
    { path: '/rechnungen',    icon: '🧾', label: 'Rechnungen' },
  ];

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

  $: currentPath = $page.url.pathname;
</script>

<aside class="sidebar">
  <div class="sidebar-logo">
    <img src="https://assets.zyrosite.com/sKFGVgrqCU2eVSWO/logo_9-isvHGkTKpAcAmGO4.webp" alt="Logo" class="logo-img" />
    <div class="logo-text">
      <span class="logo-title">eBay Dashboard</span>
      <span class="logo-version">v2.0</span>
    </div>
  </div>

  <nav class="sidebar-nav">
    {#each nav as item}
      <a href={item.path} class="nav-item" class:active={currentPath === item.path || (item.path !== '/' && currentPath.startsWith(item.path))}>
        <span class="nav-icon">{item.icon}</span>
        <span class="nav-label">{item.label}</span>
      </a>
    {/each}
  </nav>

  <div class="sidebar-bottom">
    <a href="/einstellungen" class="nav-item" class:active={currentPath.startsWith('/einstellungen')}>
      <span class="nav-icon">⚙️</span>
      <span class="nav-label">Einstellungen</span>
    </a>
  </div>

  <div class="sidebar-footer">
    <div class="sidebar-user">
      <div class="user-avatar">
        {user?.ebay_user_id?.charAt(0)?.toUpperCase() || '?'}
      </div>
      <div class="user-info">
        <span class="user-name">{user?.ebay_user_id || user?.email || '—'}</span>
        <span class="user-email">{user?.email || ''}</span>
      </div>
    </div>
    <div class="sidebar-actions">
      <button class="sidebar-action" on:click={toggleTheme} title={isDark ? 'Hell' : 'Dunkel'}>
        {isDark ? '☀️' : '🌙'}
      </button>
      <button class="sidebar-action" on:click={logout} title="Ausloggen">
        🚪
      </button>
    </div>
  </div>
</aside>

<style>
  .sidebar {
    width: var(--sidebar-width); height: 100vh; background: var(--surface);
    border-right: 1px solid var(--border); display: flex; flex-direction: column;
    position: fixed; left: 0; top: 0; z-index: 50;
  }
  .sidebar-logo {
    display: flex; align-items: center; gap: 12px;
    padding: 20px 20px 16px; border-bottom: 1px solid var(--border);
  }
  .logo-img { width: 32px; height: 32px; border-radius: 8px; object-fit: contain; }
  .logo-text { display: flex; flex-direction: column; }
  .logo-title { font-size: 15px; font-weight: 800; color: var(--text); }
  .logo-version { font-size: 11px; color: var(--text3); font-weight: 500; }
  .sidebar-nav {
    flex: 1; padding: 12px 10px;
    display: flex; flex-direction: column; gap: 2px;
  }
  .sidebar-bottom {
    padding: 0 10px 8px; border-top: 1px solid var(--border); padding-top: 8px;
  }
  .nav-item {
    display: flex; align-items: center; gap: 12px; padding: 10px 14px;
    border-radius: 10px; font-size: 13px; font-weight: 500; color: var(--text2);
    text-decoration: none; transition: all 0.1s; cursor: pointer;
  }
  .nav-item:hover { background: var(--surface2); color: var(--text); }
  .nav-item.active { background: var(--surface2); color: var(--text); font-weight: 700; }
  .nav-icon { font-size: 16px; width: 22px; text-align: center; flex-shrink: 0; }
  .nav-label { flex: 1; }
  .sidebar-footer {
    padding: 12px 14px 16px; border-top: 1px solid var(--border);
  }
  .sidebar-user { display: flex; align-items: center; gap: 10px; padding: 8px 6px; }
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
  .sidebar-action {
    flex: 1; display: flex; align-items: center; justify-content: center;
    padding: 8px; border-radius: 8px; font-size: 16px; background: var(--surface2);
    border: 1px solid var(--border); cursor: pointer; transition: all 0.15s;
  }
  .sidebar-action:hover { background: var(--border); }
</style>
