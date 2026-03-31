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

  // Funktion zum Herunterladen der Rechnung (Beispiel)
  function downloadRechnung(id) {
    alert(`Rechnung ${id} wird heruntergeladen.`);
    // Hier könnte später ein API-Aufruf zum Herunterladen der Rechnung stehen
  }
</script>

<div class="rechnungen-page">
  <h1>Rechnungen</h1>

  <div class="filter-section">
    <h2>Filteroptionen</h2>
    <div class="filter-form">
      <input
        type="text"
        placeholder="Rechnungsnummer..."
        bind:value={filterRechnungsnummer}
      />
      <input
        type="date"
        placeholder="Datum von"
        bind:value={filterVonDatum}
      />
      <input
        type="date"
        placeholder="Datum bis"
        bind:value={filterBisDatum}
      />
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

<style>
  :root {
    --primary: #3777CF;
    --primary-dark: #2a5ab8;
    --surface: #ffffff;
    --surface2: #f8fafc;
    --border: #e2e8f0;
    --text: #0f172a;
    --text2: #64748b;
    --text3: #94a3b8;
  }

  .dark {
    --surface: #1e293b;
    --surface2: #263347;
    --border: #334155;
    --text: #f1f5f9;
    --text2: #94a3b8;
    --text3: #475569;
  }

  /* Layout */
  .rechnungen-page {
    background: var(--surface);
    color: var(--text);
    padding: 20px;
    font-family: 'Inter', sans-serif;
  }

  .rechnungen-page h1 {
    color: var(--text);
    margin-bottom: 20px;
  }

  /* Filterbereich */
  .filter-section {
    background: var(--surface);
    padding: 16px;
    border-radius: 8px;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
    margin-bottom: 20px;
  }

  .filter-section h2 {
    color: var(--text2);
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

  .filter-form input,
  .filter-form select,
  .filter-form button {
    padding: 8px 12px;
    border: 1px solid var(--border);
    border-radius: 4px;
    font-family: 'Inter', sans-serif;
    font-size: 14px;
  }

  .filter-form button {
    background: var(--primary);
    color: white;
    border: none;
    cursor: pointer;
  }

  .filter-form button:hover {
    background: var(--primary-dark);
  }

  /* Status-Badge */
  .status-badge {
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 500;
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
    background: var(--surface);
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
    background: var(--surface2);
  }

  tr:hover {
    background: rgba(55, 119, 207, 0.05);
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
</style>
