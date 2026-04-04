<!-- +page.svelte -->
<script>
  // Beispiel-Daten (können dynamisch geladen werden)
  let firmData = {
    firm_name: 'Mein Firmenname',
    strasse: 'Auf der Schläfe 1',
    plz_ort: '57078 Siegen',
    telefon: 'Telefon: +49 271 50149974',
    email: 'E-Mail: ov-shop@mail.de',
    iban: 'DE60 1001 1001 2829 9706 30',
    bic: 'NTSBDEB1XXX',
    ust_id: 'DE815720228',
    steuer_nr: '342/5058/2211',
    impressum_text: 'Impressum: Import & Produkte Vertrieb, Auf der Schläfe 1, 57078 Siegen',
    footer_columns: 2, // 1-4 Spalten
  };

  let invoiceData = {
    net_amount: 15.96,
    tax: 3.03,
    total_amount: 18.99,
    items: [
      { art_nr: '1054', bezeichnung: 'Jemako Intensivreiniger KalkEx Plus', menge: 1, einzelpreis: 15.96, betrag: 15.96 },
    ],
  };

  function saveSettings() {
    console.log('Einstellungen gespeichert:', firmData);
    // Hier könnte ein API-Aufruf stattfinden
  }

  function generatePreview() {
    console.log('Vorschau generiert:', invoiceData);
    // Hier könnte die Vorschau generiert werden
  }
</script>

<!-- Split-Screen-Layout (50/50) -->
<div class="dashboard">
  <!-- Vorschau-Bereich -->
  <div class="preview">
    <h2>Vorschau</h2>

    <!-- Firmenname und Adresse -->
    <div class="firm-info">
      <h3>{firmData.firm_name}</h3>
      <p>{firmData.strasse}</p>
      <p>{firmData.plz_ort}</p>
      <p>{firmData.telefon}</p>
      <p>{firmData.email}</p>
    </div>

    <!-- Rechnungstabelle -->
    <div class="invoice-details">
      <table>
        <thead>
          <tr>
            <th>Art.-Nr.</th>
            <th>Bezeichnung</th>
            <th>Menge</th>
            <th>Einzelpreis</th>
            <th>Betrag</th>
          </tr>
        </thead>
        <tbody>
          {#each invoiceData.items as item}
            <tr>
              <td>{item.art_nr}</td>
              <td>{item.bezeichnung}</td>
              <td>{item.menge}</td>
              <td>{item.einzelpreis.toFixed(2)} EUR</td>
              <td>{item.betrag.toFixed(2)} EUR</td>
            </tr>
          {/each}
        </tbody>
        <tfoot>
          <tr>
            <td colspan="4">Nettbetrag</td>
            <td>{invoiceData.net_amount.toFixed(2)} EUR</td>
          </tr>
          <tr>
            <td colspan="4">MwSt. 19%</td>
            <td>{invoiceData.tax.toFixed(2)} EUR</td>
          </tr>
          <tr>
            <td colspan="4"><strong>Gesamtbetrag</strong></td>
            <td><strong>{invoiceData.total_amount.toFixed(2)} EUR</strong></td>
          </tr>
        </tfoot>
      </table>
    </div>

    <!-- Anpassbarer Footer (1-4 Spalten) -->
    <footer class="footer">
      {#if firmData.footer_columns >= 1}
        <div class="footer-column">
          <h4>Kontakt</h4>
          <p>{firmData.telefon}</p>
          <p>{firmData.email}</p>
        </div>
      {/if}
      {#if firmData.footer_columns >= 2}
        <div class="footer-column">
          <h4>Bankdaten</h4>
          <p>IBAN: {firmData.iban}</p>
          <p>BIC: {firmData.bic}</p>
        </div>
      {/if}
      {#if firmData.footer_columns >= 3}
        <div class="footer-column">
          <h4>Steuernummer</h4>
          <p>USt-ID: {firmData.ust_id}</p>
          <p>Steuer-Nr.: {firmData.steuer_nr}</p>
        </div>
      {/if}
      {#if firmData.footer_columns >= 4}
        <div class="footer-column">
          <h4>Impressum</h4>
          <p>{firmData.impressum_text}</p>
        </div>
      {/if}
    </footer>
  </div>

  <!-- Einstellungen-Bereich -->
  <div class="settings">
    <h2>Einstellungen</h2>

    <!-- Einstellungen in 2 Reihen -->
    <div class="settings-grid">
      <!-- Reihe 1 -->
      <div class="settings-row">
        <div class="setting-group">
          <label for="firm_name">Firmenname</label>
          <input type="text" id="firm_name" bind:value={firmData.firm_name} />
        </div>
        <div class="setting-group">
          <label for="strasse">Straße, PLZ Ort</label>
          <input type="text" id="strasse" bind:value={firmData.strasse} />
        </div>
      </div>

      <!-- Reihe 2 -->
      <div class="settings-row">
        <div class="setting-group">
          <label for="telefon">Telefon / E-Mail</label>
          <input type="text" id="telefon" bind:value={firmData.telefon} />
        </div>
        <div class="setting-group">
          <label for="footer_columns">Footer-Spalten (1-4)</label>
          <select id="footer_columns" bind:value={firmData.footer_columns}>
            <option value="1">1 Spalte</option>
            <option value="2">2 Spalten</option>
            <option value="3">3 Spalten</option>
            <option value="4">4 Spalten</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Buttons -->
    <div class="action-buttons">
      <button on:click={saveSettings}>Einstellungen speichern</button>
      <button on:click={generatePreview}>PDF-Vorschau</button>
      <button on:click={() => window.print()}>Drucken</button>
    </div>
  </div>
</div>

<!-- CSS für das Layout -->
<style>
  .dashboard {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    height: 100vh;
    padding: 20px;
    box-sizing: border-box;
  }

  .preview, .settings {
    padding: 15px;
    border: 1px solid #ddd;
    border-radius: 8px;
    background-color: #f9f9f9;
  }

  .firm-info {
    margin-bottom: 20px;
    font-family: Arial, sans-serif;
  }

  .invoice-details {
    margin-bottom: 20px;
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-family: Arial, sans-serif;
  }

  th, td {
    border: 1px solid #ddd;
    padding: 8px;
    text-align: left;
  }

  th {
    background-color: #f2f2f2;
  }

  tfoot td {
    font-weight: bold;
  }

  .footer {
    display: flex;
    gap: 15px;
    margin-top: 20px;
    padding: 10px 0;
    border-top: 1px solid #ddd;
    flex-wrap: wrap;
  }

  .footer-column {
    flex: 1;
    min-width: 200px;
  }

  .settings-grid {
    display: flex;
    flex-direction: column;
    gap: 15px;
    margin-bottom: 20px;
  }

  .settings-row {
    display: flex;
    gap: 15px;
  }

  .setting-group {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 5px;
  }

  label {
    font-weight: bold;
    font-size: 14px;
  }

  input, select {
    padding: 8px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-family: Arial, sans-serif;
  }

  button {
    padding: 10px 15px;
    background-color: #007bff;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    margin-right: 10px;
    font-family: Arial, sans-serif;
  }

  button:hover {
    background-color: #0056b3;
  }

  @media (max-width: 768px) {
    .dashboard {
      grid-template-columns: 1fr;
    }
    .settings-row {
      flex-direction: column;
    }
  }
</style>
