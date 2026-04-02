<!--
  EbayVerbindenModal.svelte
  
  VERWENDUNG in der Seite die bisher window.confirm() nutzt:
  
  1. Diese Komponente in die Seite importieren:
     import EbayVerbindenModal from '$lib/components/EbayVerbindenModal.svelte';
  
  2. State hinzufügen:
     let showEbayModal = $state(false);
     let ebayModalUser = $state('');
  
  3. Den alten confirm()-Aufruf ersetzen:
     // ALT:
     if (!confirm(`eBay verbinden?\nErwartet: ${expectedUser}`)) return;
     
     // NEU:
     ebayModalUser = expectedUser;
     showEbayModal = true;
     // Der Rest läuft über onConfirm / onCancel Callbacks
  
  4. Im Template einbinden:
     <EbayVerbindenModal
       bind:open={showEbayModal}
       expectedUser={ebayModalUser}
       onConfirm={handleEbayConnect}
       onCancel={() => showEbayModal = false}
     />
-->

<script>
  let {
    open = $bindable(false),
    expectedUser = '',
    onConfirm = () => {},
    onCancel = () => {}
  } = $props();

  function handleConfirm() {
    open = false;
    onConfirm();
  }

  function handleCancel() {
    open = false;
    onCancel();
  }

  function handleBackdrop(e) {
    if (e.target === e.currentTarget) handleCancel();
  }

  function handleKeydown(e) {
    if (!open) return;
    if (e.key === 'Escape') handleCancel();
    if (e.key === 'Enter') handleConfirm();
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
  <!-- Backdrop -->
  <div class="modal-backdrop" onclick={handleBackdrop} role="dialog" aria-modal="true">
    <div class="modal">

      <!-- Icon -->
      <div class="modal-icon">
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect width="24" height="24" rx="12" fill="#E53935" opacity="0.1"/>
          <path d="M4 8.5C4 7.67 4.67 7 5.5 7h2.25L9 9H5.5A.5.5 0 005 9.5v7a.5.5 0 00.5.5h13a.5.5 0 00.5-.5V9.5a.5.5 0 00-.5-.5H15l1.25-2H18.5C19.33 7 20 7.67 20 8.5v9a1.5 1.5 0 01-1.5 1.5h-13A1.5 1.5 0 014 17.5v-9z" fill="#E53935"/>
          <path d="M7 9.5L9.5 7 12 9.5M9.5 7v7" stroke="#E53935" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          <!-- eBay-ähnliches "e" -->
          <text x="11.5" y="15.5" font-size="5" font-weight="800" fill="#E53935" font-family="Arial">bay</text>
        </svg>
      </div>

      <!-- Titel -->
      <div class="modal-title">Mit eBay verbinden</div>

      <!-- Warnung -->
      <div class="modal-warning">
        <span class="warning-icon">⚠️</span>
        <span>eBay verbindet den Account, der aktuell im Browser eingeloggt ist!</span>
      </div>

      <!-- Info-Box -->
      <div class="modal-info">
        <div class="info-row">
          <span class="info-label">Erwarteter Account</span>
          <span class="info-value">
            <span class="account-badge">{expectedUser || 'kd*shop'}</span>
          </span>
        </div>
        <div class="info-divider"></div>
        <p class="info-hint">
          Bitte stelle sicher, dass du bei eBay als
          <strong>„{expectedUser || 'kd*shop'}"</strong>
          eingeloggt bist, bevor du fortfährst.
        </p>
      </div>

      <!-- Aktionen -->
      <div class="modal-actions">
        <button class="btn-cancel" onclick={handleCancel}>
          Abbrechen
        </button>
        <button class="btn-confirm" onclick={handleConfirm}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M5 12h14M12 5l7 7-7 7"/>
          </svg>
          Jetzt verbinden
        </button>
      </div>

    </div>
  </div>
{/if}

<style>
  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.45);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    z-index: 9999;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    animation: fadeIn 0.18s ease;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
  }

  .modal {
    background: var(--surface, #ffffff);
    border: 1px solid var(--border, #e2e8f0);
    border-radius: 20px;
    padding: 32px 28px 28px;
    width: 100%;
    max-width: 420px;
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.18), 0 4px 16px rgba(0,0,0,0.08);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 20px;
    animation: slideUp 0.22s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  @keyframes slideUp {
    from { transform: translateY(20px) scale(0.97); opacity: 0; }
    to   { transform: translateY(0) scale(1);       opacity: 1; }
  }

  /* Icon */
  .modal-icon svg {
    width: 56px;
    height: 56px;
  }

  /* Titel */
  .modal-title {
    font-size: 1.25rem;
    font-weight: 800;
    color: var(--text, #0f172a);
    text-align: center;
    margin-top: -8px;
  }

  /* Warnung */
  .modal-warning {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    background: #fff7ed;
    border: 1px solid #fed7aa;
    border-radius: 10px;
    padding: 12px 14px;
    font-size: 0.83rem;
    color: #9a3412;
    line-height: 1.5;
    width: 100%;
    box-sizing: border-box;
  }

  :global([data-theme="dark"]) .modal-warning {
    background: rgba(234,88,12,0.12);
    border-color: rgba(234,88,12,0.3);
    color: #fb923c;
  }

  .warning-icon {
    font-size: 1rem;
    flex-shrink: 0;
    margin-top: 1px;
  }

  /* Info Box */
  .modal-info {
    width: 100%;
    background: var(--surface2, #f8fafc);
    border: 1px solid var(--border, #e2e8f0);
    border-radius: 12px;
    padding: 16px;
    box-sizing: border-box;
  }

  .info-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .info-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text2, #64748b);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .account-badge {
    background: var(--primary, #2563eb);
    color: white;
    font-size: 0.8rem;
    font-weight: 700;
    padding: 3px 12px;
    border-radius: 20px;
    font-family: monospace;
    letter-spacing: 0.02em;
  }

  .info-divider {
    height: 1px;
    background: var(--border, #e2e8f0);
    margin: 12px 0;
  }

  .info-hint {
    font-size: 0.82rem;
    color: var(--text2, #64748b);
    line-height: 1.6;
    margin: 0;
  }

  .info-hint strong {
    color: var(--text, #0f172a);
  }

  /* Buttons */
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
    padding: 11px 16px;
    border-radius: 10px;
    font-size: 0.88rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
  }

  .btn-cancel:hover {
    border-color: var(--text2, #64748b);
    color: var(--text, #0f172a);
    background: var(--surface2, #f8fafc);
  }

  .btn-confirm {
    flex: 2;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    background: var(--primary, #2563eb);
    color: white;
    border: none;
    padding: 11px 20px;
    border-radius: 10px;
    font-size: 0.88rem;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
  }

  .btn-confirm:hover {
    background: #1d4ed8;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(37,99,235,0.35);
  }

  .btn-confirm:active {
    transform: translateY(0);
    box-shadow: none;
  }
</style>
