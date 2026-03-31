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
  let filterStatus = '';

  // Gefilterte Rechnungen berechnen
  $: gefilterteRechnungen = rechnungen.filter(rechnung => {
    return (
      (filterRechnungsnummer === '' || rechnung.id.includes(filterRechnungsnummer)) &&
      (filterVonDatum === '' || rechnung.datum >= filterVonDatum) &&
      (filterBisDatum === '' || rechnung.datum <= filterBisDatum) &&
      (filterStatus === '' || rechnung.status === filterStatus)
    );
  });

  // Funktion zum Herunterladen der Rechnung (Beispiel)
  function downloadRechnung(id) {
    alert(`Rechnung ${id} wird heruntergeladen.`);
    // Hier könnte später ein API-Aufruf zum Herunterladen der Rechnung stehen
  }
</script>

<div class="content">
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
        <option value="">Status</option>
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
            <td>{rechnung.status}</td>
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
  /* CSS-Variablen aus dem Dashboard-Design-System */
  :root {
    --primary: #2563eb;
    --surface: #ffffff;
    --surface2: #f8fafc;
    --border: #e2e8f0;
    --text: #0f172a;
    --radius: 12px;
    --shadow: 0 1px 3px rgba(0, 0, 0, 0.08), 0 1px 2px rgba(0, 0, 0, 0.05);
    --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.07), 0 2px 4px rgba(0, 0, 0, 0.05);
  }

  /* Filterbereich */
  .filter-section {
    background: var(--surface);
    padding: 16px;
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    margin-bottom: 20px;
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
  }

  .filter-form button {
    background: var(--primary);
    color: white;
    border: none;
    cursor: pointer;
  }

  .filter-form button:hover {
    background: #1d4ed8;
  }

  /* Tabellencontainer */
  .table-container {
    background: var(--surface);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
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
  }

  .download-btn:hover {
    background: #1d4ed8;
  }
</style>
