<script>
  import { toastMessage } from '$lib/stores.js';
  let toast = null;
  toastMessage.subscribe(v => toast = v);
</script>

{#if toast}
  <div class="toast toast-{toast.type}">
    {toast.message}
  </div>
{/if}

<style>
  .toast {
    position: fixed;
    bottom: 24px;
    right: 24px;
    background: var(--surface);
    border: 1.5px solid var(--border);
    border-radius: 10px;
    padding: 14px 20px;
    font-size: 13px;
    font-weight: 500;
    z-index: 9999;
    max-width: 350px;
    box-shadow: var(--shadow-md);
    animation: slideIn 0.3s ease;
  }
  .toast-success { border-color: var(--success); color: var(--success); }
  .toast-error { border-color: var(--danger); color: var(--danger); }
  @keyframes slideIn {
    from { transform: translateY(20px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
  }
</style>
