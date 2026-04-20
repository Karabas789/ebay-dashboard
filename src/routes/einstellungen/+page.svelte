<script>
  const tiles = [
    { icon: '🏢', title: 'Firmendaten',        desc: 'Name, Adresse, USt-IdNr., Logo',           href: '/einstellungen/firma' },
    { icon: '🔢', title: 'Nummerierung',        desc: 'Rechnungs- und Storno-Nummernkreise',      href: '/einstellungen/nummern' },
    { icon: '📧', title: 'E-Mail / SMTP',       desc: 'SMTP-Server, Absender, Verbindungstest',   href: '/einstellungen/email' },
    { icon: '🖨️', title: 'Rechnungsvorlage',   desc: 'PDF-Layout, Bilder, Texte, Farbschema',    href: '/einstellungen/rechnungsvorlage' },
    { icon: '🤖', title: 'KI-Konfiguration',    desc: 'System-Prompt, Modell, Auto-Send',         href: '/einstellungen/ki' },
    { icon: '💬', title: 'Kauf-Nachricht',       desc: 'Automatische Nachricht nach eBay-Kauf',    href: '/einstellungen/kauf-nachricht' },
    { icon: '🖼️', title: 'Produktbilder',       desc: 'Bilder-URLs für Produkte verwalten',       href: '/einstellungen/bilder' },
    { icon: '🛒', title: 'Shop-Verbindungen',    desc: 'WooCommerce, Shopify und weitere Shops',   href: '/einstellungen/shops' },
    { icon: '🔐', title: '2-Faktor-Auth',        desc: 'Login mit E-Mail-Code absichern',          href: '/einstellungen/sicherheit' },
  ];
</script>

<div class="page-header">
  <div>
    <h1 class="page-title">⚙️ Einstellungen</h1>
    <p class="page-subtitle">Dashboard und Integrationen konfigurieren</p>
  </div>
</div>

<div class="settings-grid">
  {#each tiles as tile}
    <a href={tile.href} class="settings-tile">
      <div class="settings-tile-icon">{tile.icon}</div>
      <div class="settings-tile-title">{tile.title}</div>
      <div class="settings-tile-desc">{tile.desc}</div>
    </a>
  {/each}
</div>
