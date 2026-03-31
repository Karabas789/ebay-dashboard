<script>
  // Beispiel-Daten für Rechnungen (kann später durch Datenbankabfrage ersetzt werden)
  let rechnungen = [
    { id: 'RE-2023-001', kunde: 'Max Mustermann', datum: '2023-01-01', betrag: '129,99 €', status: 'Bezahlt' },
    { id: 'RE-2023-002', kunde: 'Anna Schmidt', datum: '2023-01-05', betrag: '79,99 €', status: 'Ausstehend' },
    { id: 'RE-2023-003', kunde: 'Hans Müller', datum: '2023-01-10', betrag: '249,99 €', status: 'Storniert' },
  ];

  // Filtervariablen
  let filterRechnungsnummer = '';
  let filterVonDatum = '';
  let filterBisDatum = '';
  let filterStatus = 'Alle';

  // Gefilterte Rechnungen berechnen
  $: gefilterteRechnungen = rechnungen.filter(rechnung => {
    return (
      (filterRechnungsnummer === '' || rechnung.id.includes(filterRechnungsnummer)) &&
      (filterVonDatum === '' || rechnung.datum >= filterVonDatum) &&
      (filterBisDatum === '' || rechnung.datum <= filterBisDatum) &&
      (filterStatus === 'Alle' || rechnung.status === filterStatus)
    );
  });

  // Funktion zum Herunterladen der Rechnung (öffnet ein schönes Modal)
  function downloadRechnung(id) {
    alert = false; // Deaktiviere die hässliche Benachrichtigung
    // Hier könnte später ein API-Aufruf zum Herunterladen der Rechnung stehen
    showModal = true;
    selectedRechnungId = id;
  }

  // Modal-Variablen
  let showModal = false;
  let selectedRechnungId = '';
</script>

<div class="rechnungen-page">
  <h1>Rechnungen</h1>

  <div class="filter-section">
    <h2>Filteroptionen</h2>
    <div class="filter-form">
      <div class="filter-input">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
          <path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001q.044.06.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1 1 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0"/>
        </svg>
        <input
          type="text"
          placeholder="Rechnungsnummer..."
          bind:value={filterRechnungsnummer}
        />
      </div>
      <div class="filter-input">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
          <path d="M4 .5a.5.5 0 0 0-1 0V1H2a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V3a2 2 0 0 0-2-2h-1V.5a.5.5 0 0 0-1 0V1H4zM1 4v11a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V4z"/>
        </svg>
        <input
          type="date"
          placeholder="Datum von"
          bind:value={filterVonDatum}
        />
      </div>
      <div class="filter-input">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
          <path d="M4 .5a.5.5 0 0 0-1 0V1H2a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V3a2 2 0 0 0-2-2h-1V.5a.5.5 0 0 0-1 0V1H4zM1 4v11a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V4z"/>
        </svg>
        <input
          type="date"
          placeholder="Datum bis"
          bind:value={filterBisDatum}
        />
      </div>
      <select bind:value={filterStatus}>
        <option value="Alle">Alle</option>
        <option value="Bezahlt">Bezahlt</option>
        <option value="Ausstehend">Ausstehend</option>
        <option value="Storniert">Storniert</option>
      </select>
      <button on:click={() => { /* Filterlogik hier */ }}>Filtern</button>
    </div>
  </div>

  <div class="table-container">
    <table>
      <thead>
        <tr>
          <th>Rechnungsnummer</th>
          <th>Kunde</th>
          <th>Datum</th>
          <th>Betrag</th>
          <th>Status</th>
          <th>Aktion</th>
        </tr>
      </thead>
      <tbody>
        {#each gefilterteRechnungen as rechnung}
          <tr>
            <td>{rechnung.id}</td>
            <td>{rechnung.kunde}</td>
            <td>{rechnung.datum}</td>
            <td>{rechnung.betrag}</td>
            <td>
              <span class="status-badge {rechnung.status.toLowerCase()}">
                {rechnung.status}
              </span>
            </td>
            <td>
              <button
                class="download-btn"
                on:click={() => downloadRechnung(rechnung.id)}
              >
                Download
              </button>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</div>

{#if showModal}
  <div class="modal-overlay" on:click={() => showModal = false}>
    <div class="modal">
      <h3>Rechnung herunterladen</h3>
      <p>Möchtest du die Rechnung {selectedRechnungId} wirklich herunterladen?</p>
      <div class="modal-actions">
        <button class="modal-btn confirm" on:click={() => {
          // Hier könnte der Download-Logik stehen
          showModal = false;
        }}>Ja, herunterladen</button>
        <button class="modal-btn cancel" on:click={() => showModal = false}>Abbrechen</button>
      </div>
    </div>
  </div>
{/if}

<style>
  :root {
    --primary: #3777CF;
    --primary-dark: #2a5ab8;
    --surface: #0f172a;
    --surface2: #1e293b;
    --border: #334155;
    --text: #f1f5f9;
    --text2: #94a3b8;
    --text3: #64748b;
  }

  .rechnungen-page {
    background: var(--surface);
    color: var(--text);
    padding: 20px;
    font-family: 'Inter', sans-serif;
    min-height: 100vh;
  }

  .rechnungen-page h1 {
    color: var(--text);
    margin-bottom: 20px;
  }

  /* Filterbereich */
  .filter-section {
    background: var(--surface2);
    padding: 16px;
    border-radius: 8px;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
    margin-bottom: 20px;
  }

  .filter-section h2 {
    color: var(--text);
    margin-top: 0;
    margin-bottom: 16px;
    font-size: 16px;
  }

  .filter-form {
    display: flex;
    gap: 10px;
    align-items: center;
    flex-wrap: wrap;
  }

  .filter-input {
    display: flex;
    align-items: center;
    gap: 8px;
    background: var(--surface);
    padding: 8px 12px;
    border-radius: 4px;
  }

  .filter-input svg {
    color: var(--text3);
  }

  .filter-form input,
  .filter-form select {
    padding: 8px 12px;
    border: 1px solid var(--border);
    border-radius: 4px;
    font-family: 'Inter', sans-serif;
    font-size: 14px;
    background: var(--surface);
    color: var(--text);
  }

  .filter-form select {
    background: var(--surface);
    color: var(--text);
  }

  .filter-form button {
    background: var(--primary);
    color: white;
    border: none;
    cursor: pointer;
    padding: 8px 16px;
    border-radius: 4px;
  }

  .filter-form button:hover {
    background: var(--primary-dark);
  }

  /* Status-Badge */
  .status-badge {
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
    display: inline-block;
    text-align: center;
    min-width: 80px;
  }

  .status-badge.bezahlt {
    background: #dcfce7;
    color: #166534;
  }

  .status-badge.ausstehend {
    background: #fef3c7;
    color: #92400e;
  }

  .status-badge.storniert {
    background: #fee2e2;
    color: #991b1b;
  }

  /* Tabellencontainer */
  .table-container {
    background: var(--surface2);
    border-radius: 8px;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
    overflow: hidden;
  }

  /* Tabellenstil */
  table {
    width: 100%;
    border-collapse: collapse;
  }

  th,
  td {
    padding: 12px 16px;
    text-align: left;
    border-bottom: 1px solid var(--border);
  }

  th {
    background: var(--primary);
    color: white;
  }

  tr:nth-child(even) {
    background: var(--surface);
  }

  tr:hover {
    background: rgba(55, 119, 207, 0.1);
  }

  /* Download-Button */
  .download-btn {
    background: var(--primary);
    color: white;
    padding: 6px 12px;
    border-radius: 6px;
    text-decoration: none;
    font-weight: 500;
    border: none;
    cursor: pointer;
    font-size: 14px;
  }

  .download-btn:hover {
    background: var(--primary-dark);
  }

  /* Modal */
  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .modal {
    background: var(--surface);
    padding: 20px;
    border-radius: 10px;
    max-width: 400px;
    width: 90%;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  }

  .modal h3 {
    margin-top: 0;
    color: var(--text);
  }

  .modal p {
    color: var(--text2);
    margin-bottom: 20px;
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }

  .modal-btn {
    padding: 8px 16px;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 500;
  }

  .modal-btn.confirm {
    background: var(--primary);
    color: white;
    border: none;
  }

  .modal-btn.cancel {
    background: var(--surface2);
    color: var(--text);
    border: 1px solid var(--border);
  }
</style>
