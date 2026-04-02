<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { getToken, getUser } from '$lib/api.js';
  import { currentUser, theme, sidebarCollapsed } from '$lib/stores.js';
  import Sidebar from '$lib/components/Sidebar.svelte';
  import Toast from '$lib/components/Toast.svelte';
  import '../app.css';

  let ready = false;
  let isLoginPage = false;
  let collapsed = false;

  $: isLoginPage = $page.url.pathname === '/login';

  sidebarCollapsed.subscribe(v => collapsed = v);

  onMount(() => {
    const savedTheme = localStorage.getItem('ebay_theme') || 'light';
    theme.set(savedTheme);
    document.documentElement.setAttribute('data-theme', savedTheme);

    const savedSidebar = localStorage.getItem('sidebar_collapsed');
    if (savedSidebar === 'true') {
      sidebarCollapsed.set(true);
    }

    const token = getToken();
    const user = getUser();
    if (token && user) {
      currentUser.set(user);
      ready = true;
    } else if (isLoginPage) {
      ready = true;
    } else {
      ready = true;
      goto('/login');
    }
  });
</script>

{#if ready}
  {#if isLoginPage}
    <slot />
  {:else}
    <div class="app-shell">
      <Sidebar />
      <main class="main-content" class:sidebar-collapsed={collapsed}>
        <div class="page-wrapper animate-in">
          <slot />
        </div>
      </main>
    </div>
  {/if}
  <Toast />
{:else}
  <div class="loading" style="height:100vh;">
    <div class="spinner"></div>
    Laden...
  </div>
{/if}

<style>
  .app-shell {
    display: flex;
    height: 100vh;
  }
  .main-content {
    flex: 1;
    margin-left: var(--sidebar-width);
    height: 100vh;
    overflow-y: auto;
    transition: margin-left 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    /* Kein overflow-x:hidden — das erzeugt einen Stacking Context der position:fixed bricht */
  }
  .main-content.sidebar-collapsed {
    margin-left: var(--sidebar-collapsed-width, 68px);
  }
  .page-wrapper {
    padding: 28px 32px;
    min-height: 100%;
  }
</style>
