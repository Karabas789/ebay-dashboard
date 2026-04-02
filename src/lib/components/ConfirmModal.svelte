<!--
  ConfirmModal.svelte — Universelles Bestätigungs-Modal
  Ersetzt alle browser confirm() Dialoge im Dashboard.

  VERWENDUNG:
  -----------
  1. Import:
     import ConfirmModal from '$lib/components/ConfirmModal.svelte';

  2. State:
     let confirmModal = $state({ open: false, title: '', message: '', onConfirm: () => {} });

  3. Aufruf (statt confirm()):
     // ALT: if (!confirm('Nachricht wirklich löschen?')) return;
     // NEU:
     confirmModal = {
       open: true,
       title: 'Nachricht löschen',
       message: 'Möchtest du diese Nachricht wirklich löschen?',
       variant: 'danger',
       onConfirm: () => { doDelete(); }
     };

  4. Template:
     <ConfirmModal bind:modal={confirmModal} />
-->

<script>
  let {
    modal = $bindable({
      open: false,
      title: '',
      message: '',
      hint: '',           // Optional: zusätzlicher Hinweistext (orange Box)
      variant: 'danger',  // 'danger' | 'warning' | 'info' | 'ebay'
      confirmLabel: '',   // Leer = Auto je nach Variant
      cancelLabel: 'Abbrechen',
      onConfirm: () => {},
      onCancel: () => {}
    })
  } = $props();

  const variants = {
    danger: {
      icon: '🗑️',
      color: '#ef4444',
      bg: '#fef2f2',
      border: '#fecaca',
      darkBg: 'rgba(239,68,68,0.12)',
      darkBorder: 'rgba(239,68,68,0.3)',
      darkColor: '#fca5a5',
      defaultLabel: 'Löschen'
    },
    warning: {
      icon: '⚠️',
      color: '#f59e0b',
      bg: '#fffbeb',
      border: '#fde68a',
      darkBg: 'rgba(245,158,11,0.12)',
      darkBorder: 'rgba(245,158,11,0.3)',
      darkColor: '#fcd34d',
      defaultLabel: 'Fortfahren'
    },
    info: {
      icon: 'ℹ️',
      color: '#3b82f6',
      bg: '#eff6ff',
      border: '#bfdbfe',
      darkBg: 'rgba(59,130,246,0.12)',
      darkBorder: 'rgba(59,130,246,0.3)',
      darkColor: '#93c5fd',
      defaultLabel: 'OK'
    },
    ebay: {
      icon: '🔗',
      color: '#2563eb',
      bg: '#fff7ed',
      border: '#fed7aa',
      darkBg: 'rgba(234,88,12,0.12)',
      darkBorder: 'rgba(234,88,12,0.3)',
      darkColor: '#fb923c',
      defaultLabel: 'Jetzt verbinden'
    }
  };

  let v = $derived(variants[modal.variant] || variants.danger);
  let confirmLabel = $derived(modal.confirmLabel || v.defaultLabel);

  function handleConfirm() {
    modal.open = false;
    modal.onConfirm?.();
  }

  function handleCancel() {
    modal.open = false;
    modal.onCancel?.();
  }

  function handleBackdrop(e) {
    if (e.target === e.currentTarget) handleCancel();
  }

  function handleKeydown(e) {
    if (!modal.open) return;
    if (e.key === 'Escape') handleCancel();
    if (e.key === 'Enter') handleConfirm();
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if modal.open}
  <div class="backdrop" onclick={handleBackdrop} role="dialog" aria-modal="true">
    <div class="modal">

      <!-- Icon -->
      <div class="modal-icon" style="background:{v.bg};border:1.5px solid {v.border};">
        <span style="font-size:1.6rem">{v.icon}</span>
      </div>

      <!-- Titel -->
      <div class="modal-title">{modal.title}</div>

      <!-- Haupt-Nachricht -->
      {#if modal.message}
        <p class="modal-message">{modal.message}</p>
      {/if}

      <!-- Hinweis-Box (z.B. für eBay-Warnung) -->
      {#if modal.hint}
        <div class="modal-hint" style="background:{v.bg};border-color:{v.border};color:{v.color}">
          <span class="hint-icon">⚠️</span>
          <span>{modal.hint}</span>
        </div>
      {/if}

      <!-- Extra-Slot für spezielle Inhalte (z.B. Account-Badge bei eBay) -->
      {#if modal.extra}
        <div class="modal-extra">
          <div class="extra-row">
            <span class="extra-label">Erwarteter Account</span>
            <span class="extra-badge" style="background:{v.color}">{modal.extra}</span>
          </div>
        </div>
      {/if}

      <!-- Buttons -->
      <div class="modal-actions">
        <button class="btn-cancel" onclick={handleCancel}>
          {modal.cancelLabel || 'Abbrechen'}
        </button>
        <button
          class="btn-confirm"
          style="background:{v.color}"
          onclick={handleConfirm}
        >
          {confirmLabel}
        </button>
      </div>

    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.45);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    z-index: 9999;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    animation: fadeIn 0.15s ease;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
  }

  .modal {
    background: var(--surface, #ffffff);
    border: 1px solid var(--border, #e2e8f0);
    border-radius: 20px;
    padding: 28px 24px 24px;
    width: 100%;
    max-width: 400px;
    box-shadow: 0 24px 60px rgba(0,0,0,0.18), 0 4px 16px rgba(0,0,0,0.08);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    animation: slideUp 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  @keyframes slideUp {
    from { transform: translateY(16px) scale(0.97); opacity: 0; }
    to   { transform: translateY(0) scale(1); opacity: 1; }
  }

  .modal-icon {
    width: 56px;
    height: 56px;
    border-radius: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .modal-title {
    font-size: 1.1rem;
    font-weight: 800;
    color: var(--text, #0f172a);
    text-align: center;
    margin-top: -4px;
  }

  .modal-message {
    font-size: 0.88rem;
    color: var(--text2, #64748b);
    text-align: center;
    line-height: 1.6;
    margin: 0;
    padding: 0 4px;
  }

  .modal-hint {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    border-radius: 10px;
    border: 1px solid;
    padding: 12px 14px;
    font-size: 0.82rem;
    line-height: 1.5;
    width: 100%;
    box-sizing: border-box;
  }

  .hint-icon { flex-shrink: 0; margin-top: 1px; }

  .modal-extra {
    width: 100%;
    background: var(--surface2, #f8fafc);
    border: 1px solid var(--border, #e2e8f0);
    border-radius: 12px;
    padding: 14px 16px;
    box-sizing: border-box;
  }

  .extra-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .extra-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text2, #64748b);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .extra-badge {
    color: white;
    font-size: 0.8rem;
    font-weight: 700;
    padding: 3px 12px;
    border-radius: 20px;
    font-family: monospace;
  }

  .modal-actions {
    display: flex;
    gap: 10px;
    width: 100%;
    margin-top: 4px;
  }

  .btn-cancel {
    flex: 1;
    background: transparent;
    border: 1.5px solid var(--border, #e2e8f0);
    color: var(--text2, #64748b);
    padding: 10px 16px;
    border-radius: 10px;
    font-size: 0.88rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
  }

  .btn-cancel:hover {
    border-color: var(--text2, #94a3b8);
    color: var(--text, #0f172a);
    background: var(--surface2, #f8fafc);
  }

  .btn-confirm {
    flex: 2;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 10px;
    font-size: 0.88rem;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
  }

  .btn-confirm:hover {
    filter: brightness(1.1);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
  }

  .btn-confirm:active {
    transform: translateY(0);
    box-shadow: none;
    filter: brightness(0.95);
  }
</style>
