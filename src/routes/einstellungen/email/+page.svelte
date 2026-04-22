<script>
  import { onMount } from 'svelte';
  import { currentUser, showToast } from '$lib/stores.js';
  import { apiCall } from '$lib/api.js';
  import { goto } from '$app/navigation';

  let tab = $state('versand');

  // ═══════════════════════════════════════════════════════
  // VERSAND (SMTP)
  // ═══════════════════════════════════════════════════════
  let speichertLaeuft = $state(false);
  let testLaeuft = $state(false);
  let configLaeuft = $state(false);

  let cfg = $state({
    smtp_host: '', smtp_port: 587, smtp_user: '', smtp_pass: '',
    smtp_secure: false, absender_name: '', absender_email: '',
    betreff_vorlage: 'Ihre Rechnung {{rechnung_nr}}',
    text_vorlage: '', auto_versand: false,
  });

  let testEmail = $state('');
  let passwortZeigen = $state(false);
  let testStatus = $state(null);
  let testNachricht = $state('');

  // ═══════════════════════════════════════════════════════
  // BLOCK-BUILDER STATE
  // ═══════════════════════════════════════════════════════
  let blocks = $state([]);
  let selectedBlockId = $state(null);
  let blockIdCounter = $state(0);
  let vorschauOffen = $state(false);
  let htmlCodeOffen = $state(false);
  let templateModalOffen = $state(false);

  // FIX 6: Alle Variablen inkl. Bestellnummer, Artikelname, Variante
  const variablen = [
    { key: '{{rechnung_nr}}', beschreibung: 'Rechnungsnummer' },
    { key: '{{kaeufer_name}}', beschreibung: 'Name des Käufers' },
    { key: '{{datum}}', beschreibung: 'Rechnungsdatum' },
    { key: '{{brutto_betrag}}', beschreibung: 'Bruttobetrag' },
    { key: '{{firmenname}}', beschreibung: 'Eigener Firmenname' },
    { key: '{{bestellnummer}}', beschreibung: 'eBay Bestell-ID' },
    { key: '{{artikelname}}', beschreibung: 'Artikelname (1. Position)' },
    { key: '{{variante}}', beschreibung: 'Variante (1. Position)' },
  ];

  // Block-Defaults — FIX 2: align bei image, FIX 3: logoUrl bei signature, FIX 4: fontSize bei text
  const blockDefaults = {
    header: { type:'header', icon:'✉️', title:'Ihre Rechnung', subtitle:'', bgColor:'#6366f1', textColor:'#ffffff', borderRadius:true },
    text: { type:'text', content:'Sehr geehrte(r) {{kaeufer_name}},\n\nanbei erhalten Sie Ihre Rechnung {{rechnung_nr}} vom {{datum}} als PDF-Anhang.', fontSize:'15' },
    infobox: { type:'infobox', style:'blue', content:'<strong>Hinweis:</strong> Hier können Sie einen wichtigen Hinweis einfügen.' },
    amount: { type:'amount', label:'Rechnungsbetrag', value:'{{brutto_betrag}} EUR', sublabel:'', bgColor:'#eff6ff', accentColor:'#2563eb' },
    button: { type:'button', text:'Rechnung ansehen', url:'https://example.com', bgColor:'#6366f1', textColor:'#ffffff', borderRadius:'8' },
    divider: { type:'divider', style:'normal' },
    spacer: { type:'spacer', height:24 },
    image: { type:'image', url:'', alt:'Bild', maxWidth:'100%', align:'center' },
    signature: { type:'signature', name:'{{firmenname}}', details:'Auf der Schläfe 1\n57078 Siegen\nUSt-ID: DE815720228', email:'ov-shop@mail.de', phone:'+49 271 50149974', logoUrl:'https://assets.zyrosite.com/sKFGVgrqCU2eVSWO/bildschirmfoto-2024-10-23-um-20.44.12-KsnpbGM6T6pk07Fh.png', logoWidth:'120' },
    columns: { type:'columns', left:'Linke Spalte', right:'Rechte Spalte' }
  };

  const headerFarben = ['#6366f1','#2563eb','#10b981','#f59e0b','#ef4444','#1a2233','#7c3aed','#ec4899','#0891b2'];
  const accentFarben = ['#2563eb','#10b981','#6366f1','#f59e0b','#ef4444','#1a2233'];
  const buttonFarben = ['#6366f1','#2563eb','#10b981','#f59e0b','#ef4444','#1a2233','#ec4899'];
  const fontSizes = ['12','13','14','15','16','18','20'];

  const bausteinListe = [
    { type:'header', icon:'🎨', name:'Kopfbereich', desc:'Farbiger Banner mit Titel', group:'struktur' },
    { type:'text', icon:'📝', name:'Textblock', desc:'Absatz — direkt editierbar', group:'struktur' },
    { type:'divider', icon:'➖', name:'Trennlinie', desc:'Horizontal, farbig oder dezent', group:'struktur' },
    { type:'spacer', icon:'↕️', name:'Abstand', desc:'Vertikaler Leerraum', group:'struktur' },
    { type:'columns', icon:'▥', name:'2 Spalten', desc:'Nebeneinander-Layout', group:'struktur' },
    { type:'infobox', icon:'📋', name:'Info-Box', desc:'Farbiger Hinweis-Kasten', group:'inhalt' },
    { type:'amount', icon:'💰', name:'Betrag-Box', desc:'Hervorgehobener Betrag', group:'inhalt' },
    { type:'button', icon:'🔘', name:'Button', desc:'Aktion mit Link', group:'inhalt' },
    { type:'image', icon:'🖼️', name:'Bild', desc:'Logo oder Grafik (URL)', group:'inhalt' },
    { type:'signature', icon:'📇', name:'Signatur', desc:'Firmendaten, Kontakt & Logo', group:'inhalt' },
  ];

  const starterTemplates = [
    { name:'Rechnung Modern', icon:'📄', beschreibung:'Lila Header, Betrag-Box, Signatur', key:'rechnung' },
    { name:'Bestätigung', icon:'🎉', beschreibung:'Grüner Header, kurz & klar', key:'bestätigung' },
    { name:'Schlicht', icon:'〰️', beschreibung:'Nur Text, kein Banner', key:'schlicht' },
    { name:'Produktschlüssel', icon:'🔑', beschreibung:'Key-Übergabe mit Code-Box', key:'key' },
  ];

  function addBlock(type) {
    const block = { ...JSON.parse(JSON.stringify(blockDefaults[type])), id: 'b_' + (++blockIdCounter) };
    blocks = [...blocks, block];
    selectedBlockId = block.id;
  }

  function selectBlock(id) { selectedBlockId = selectedBlockId === id ? null : id; }

  function moveBlock(id, dir) {
    const i = blocks.findIndex(b => b.id === id);
    if (i < 0) return;
    const j = i + dir;
    if (j < 0 || j >= blocks.length) return;
    const arr = [...blocks];
    [arr[i], arr[j]] = [arr[j], arr[i]];
    blocks = arr;
  }

  function duplicateBlock(id) {
    const i = blocks.findIndex(b => b.id === id);
    if (i < 0) return;
    const clone = JSON.parse(JSON.stringify(blocks[i]));
    clone.id = 'b_' + (++blockIdCounter);
    const arr = [...blocks];
    arr.splice(i + 1, 0, clone);
    blocks = arr;
    selectedBlockId = clone.id;
  }

  function deleteBlock(id) {
    blocks = blocks.filter(b => b.id !== id);
    if (selectedBlockId === id) selectedBlockId = null;
  }

  function updateBlock(id, key, value) {
    blocks = blocks.map(b => b.id === id ? { ...b, [key]: value } : b);
  }

  // FIX 5: Inline-Editing — Text direkt auf Canvas editieren
  function onTextBlockInput(blockId, e) {
    const newContent = e.target.innerText || '';
    updateBlock(blockId, 'content', newContent);
  }

  // ═══════════════════════════════════════════════════════
  // TEMPLATE LADEN
  // ═══════════════════════════════════════════════════════
  function loadTemplate(key) {
    blocks = [];
    blockIdCounter = 0;
    selectedBlockId = null;

    if (key === 'rechnung') {
      addBlock('header'); updateBlock(blocks[blocks.length-1].id, 'title', 'Ihre Rechnung'); updateBlock(blocks[blocks.length-1].id, 'subtitle', '{{firmenname}}'); updateBlock(blocks[blocks.length-1].id, 'icon', '📄');
      addBlock('text'); updateBlock(blocks[blocks.length-1].id, 'content', 'Sehr geehrte(r) {{kaeufer_name}},\n\nanbei erhalten Sie Ihre Rechnung {{rechnung_nr}} vom {{datum}} als PDF-Anhang.\n\nArtikel: {{artikelname}}');
      addBlock('amount');
      addBlock('text'); updateBlock(blocks[blocks.length-1].id, 'content', 'Vielen Dank für Ihren Einkauf!\n\nBeste Grüße');
      addBlock('divider');
      addBlock('signature');
    } else if (key === 'bestätigung') {
      addBlock('header'); updateBlock(blocks[blocks.length-1].id, 'title', 'Bestellung bestätigt'); updateBlock(blocks[blocks.length-1].id, 'icon', '🎉'); updateBlock(blocks[blocks.length-1].id, 'bgColor', '#10b981');
      addBlock('text'); updateBlock(blocks[blocks.length-1].id, 'content', 'Hallo {{kaeufer_name}},\n\nIhre Bestellung wurde erfolgreich aufgenommen.');
      addBlock('infobox'); updateBlock(blocks[blocks.length-1].id, 'style', 'green'); updateBlock(blocks[blocks.length-1].id, 'content', '<strong>Bestellnummer:</strong> {{bestellnummer}}<br>Artikel: {{artikelname}}<br>Betrag: {{brutto_betrag}} EUR');
      addBlock('text'); updateBlock(blocks[blocks.length-1].id, 'content', 'Viel Spaß mit dem Produkt!');
      addBlock('signature');
    } else if (key === 'schlicht') {
      addBlock('text'); updateBlock(blocks[blocks.length-1].id, 'content', 'Sehr geehrte(r) {{kaeufer_name}},\n\nanbei erhalten Sie Ihre Rechnung {{rechnung_nr}} vom {{datum}} als PDF-Anhang.\n\nArtikel: {{artikelname}}\nRechnungsbetrag: {{brutto_betrag}} EUR\n\nVielen Dank für Ihren Einkauf!\n\nBeste Grüße');
      addBlock('divider');
      addBlock('signature');
    } else if (key === 'key') {
      addBlock('header'); updateBlock(blocks[blocks.length-1].id, 'title', 'Ihr Aktivierungsschlüssel'); updateBlock(blocks[blocks.length-1].id, 'subtitle', 'Vielen Dank für Ihre Bestellung'); updateBlock(blocks[blocks.length-1].id, 'icon', '✅'); updateBlock(blocks[blocks.length-1].id, 'bgColor', '#7c3aed');
      addBlock('text'); updateBlock(blocks[blocks.length-1].id, 'content', 'Sehr geehrte(r) {{kaeufer_name}},\n\nvielen Dank für Ihre Bestellung ({{bestellnummer}}). Hiermit übersenden wir Ihnen einen Produktschlüssel:');
      addBlock('infobox'); updateBlock(blocks[blocks.length-1].id, 'content', '<strong>{{artikelname}}</strong><br><br>Ihr persönlicher Schlüssel:<br><span style="font-size:1.3em;font-family:monospace;color:#6366f1;font-weight:700">XXXX-XXXX-XXXX-XXXX</span><br><br>💡 Tipp: Kopieren Sie den Key und bewahren Sie diese E-Mail sicher auf.');
      addBlock('text'); updateBlock(blocks[blocks.length-1].id, 'content', 'Sollten Sie weitere Fragen haben, stehen wir Ihnen gerne zur Verfügung.\n\nSchöne Grüße');
      addBlock('signature');
    }
    selectedBlockId = null;
    templateModalOffen = false;
    showToast('✅ Vorlage geladen');
  }

  // ═══════════════════════════════════════════════════════
  // HTML EXPORT — FIX 2: Bild-Align, FIX 3: Logo in Signatur, FIX 4: fontSize
  // ═══════════════════════════════════════════════════════
  function textToHtml(text) {
    if (!text) return '';
    // Wenn es schon HTML enthält, direkt zurückgeben
    if (/<[a-z][^>]*>/i.test(text)) return text;
    // Plaintext → HTML
    return text.split('\n\n').map(p => '<p style="margin:0 0 12px">' + p.replace(/\n/g, '<br>') + '</p>').join('');
  }

  function blockToEmailHtml(b) {
    switch (b.type) {
      case 'header': {
        const rad = b.borderRadius ? 'border-radius:12px 12px 0 0;' : '';
        return `<div style="background:${b.bgColor};color:${b.textColor};padding:28px 32px;text-align:center;${rad}">` +
          (b.icon ? `<div style="font-size:2.2rem;margin-bottom:8px">${b.icon}</div>` : '') +
          `<h2 style="margin:0;font-size:1.3rem;font-weight:700">${b.title}</h2>` +
          (b.subtitle ? `<div style="font-size:0.82rem;opacity:0.85;margin-top:4px">${b.subtitle}</div>` : '') +
          `</div>`;
      }
      case 'text':
        return `<div style="padding:16px 32px;font-size:${b.fontSize || 15}px;line-height:1.7;color:#333">${textToHtml(b.content)}</div>`;
      case 'infobox': {
        const colors = {blue:['#eff6ff','#2563eb','#1e40af'],green:['#f0fdf4','#10b981','#166534'],yellow:['#fffbeb','#f59e0b','#92400e'],red:['#fef2f2','#ef4444','#991b1b']};
        const c = colors[b.style] || colors.blue;
        return `<div style="margin:12px 32px;padding:14px 18px;border-radius:8px;background:${c[0]};border-left:4px solid ${c[1]};color:${c[2]};font-size:14px;line-height:1.6">${b.content}</div>`;
      }
      case 'amount':
        return `<div style="margin:16px 32px;padding:20px;text-align:center;border-radius:10px;background:${b.bgColor};border-left:4px solid ${b.accentColor}">` +
          `<div style="font-size:13px;color:${b.accentColor};opacity:0.7">${b.label}</div>` +
          `<div style="font-size:1.8rem;font-weight:700;color:${b.accentColor}">${b.value}</div>` +
          (b.sublabel ? `<div style="font-size:12px;opacity:0.6;margin-top:4px">${b.sublabel}</div>` : '') +
          `</div>`;
      case 'button':
        return `<div style="padding:16px 32px;text-align:center"><a href="${b.url}" style="display:inline-block;padding:13px 36px;border-radius:${b.borderRadius}px;background:${b.bgColor};color:${b.textColor};font-weight:700;font-size:15px;text-decoration:none">${b.text}</a></div>`;
      case 'divider': {
        const h = b.style === 'bold' ? '2px' : '1px';
        const dc = b.style === 'colored' ? '#2563eb' : '#e2e5ea';
        return `<div style="padding:8px 32px"><hr style="border:none;height:${h};background:${dc}"></div>`;
      }
      case 'spacer':
        return `<div style="height:${b.height}px"></div>`;
      case 'image': {
        if (!b.url) return '';
        const align = b.align || 'center';
        return `<div style="padding:8px 32px;text-align:${align}"><img src="${b.url}" alt="${b.alt}" style="max-width:${b.maxWidth};height:auto;border-radius:8px"></div>`;
      }
      case 'signature': {
        const det = (b.details || '').replace(/\n/g, '<br>');
        let html = `<div style="margin:8px 32px;padding:16px 0;border-top:1px solid #e2e5ea;font-size:13px;color:#555;line-height:1.5">` +
          `<strong style="font-size:14px;color:#1a1d23">${b.name}</strong><br>${det}<br>` +
          (b.phone ? `📞 ${b.phone}<br>` : '') +
          (b.email ? `📧 <a href="mailto:${b.email}" style="color:#555">${b.email}</a><br>` : '');
        if (b.logoUrl) {
          html += `<img src="${b.logoUrl}" width="${b.logoWidth || 120}" style="max-width:100%;height:auto;display:block;margin-top:8px" alt="Logo">`;
        }
        html += `</div>`;
        return html;
      }
      case 'columns':
        return `<table width="100%" cellpadding="0" cellspacing="0" style="padding:12px 32px"><tr>` +
          `<td width="48%" style="padding:14px;background:#f7f8fa;border-radius:8px;vertical-align:top">${b.left}</td>` +
          `<td width="4%"></td>` +
          `<td width="48%" style="padding:14px;background:#f7f8fa;border-radius:8px;vertical-align:top">${b.right}</td>` +
          `</tr></table>`;
      default: return '';
    }
  }

  function generateFullHtml() {
    let html = '<div style="background:#f0f0f0;padding:32px 16px;font-family:Arial,sans-serif">';
    html += '<div style="max-width:600px;margin:0 auto;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08)">';
    blocks.forEach(b => { html += blockToEmailHtml(b); });
    html += '<div style="padding:20px 32px;text-align:center;font-size:12px;color:#999;border-top:1px solid #e5e7eb;background:#f4f5f7;border-radius:0 0 12px 12px">Dieses Schreiben wurde automatisch erstellt.<br>\u00a9 2026 {{firmenname}}</div>';
    html += '</div></div>';
    return html;
  }

  function vorschauHtml() {
    let h = generateFullHtml();
    h = h.replace(/\{\{rechnung_nr\}\}/g, 'RE-2026-00042')
         .replace(/\{\{kaeufer_name\}\}/g, 'Max Mustermann')
         .replace(/\{\{datum\}\}/g, '22.04.2026')
         .replace(/\{\{brutto_betrag\}\}/g, '49,99')
         .replace(/\{\{firmenname\}\}/g, 'Import & Produkte Vertrieb')
         .replace(/\{\{bestellnummer\}\}/g, '12-34567-89012')
         .replace(/\{\{artikelname\}\}/g, 'Windows 11 Pro Produktschlüssel')
         .replace(/\{\{variante\}\}/g, 'Download-Version');
    return h;
  }

  // ═══════════════════════════════════════════════════════
  // FIX 1: Speichern — text_vorlage = HTML, email_blocks_json = JSON
  // ═══════════════════════════════════════════════════════
  function blocksToJson() { return JSON.stringify(blocks); }

  function jsonToBlocks(json) {
    try {
      const parsed = JSON.parse(json);
      if (Array.isArray(parsed) && parsed.length > 0 && parsed[0].type) {
        blocks = parsed;
        blockIdCounter = parsed.length + 10;
        return true;
      }
    } catch(e) {}
    return false;
  }

  // ═══════════════════════════════════════════════════════
  // SMTP-Anbieter
  // ═══════════════════════════════════════════════════════
  const anbieterVorlagen = [
    { name:'Hostinger', host:'smtp.hostinger.com', port:465, secure:true, hinweis:'E-Mail-Passwort aus Hostinger hPanel' },
    { name:'Gmail', host:'smtp.gmail.com', port:587, secure:false, hinweis:'App-Passwort verwenden' },
    { name:'Gmail (SSL)', host:'smtp.gmail.com', port:465, secure:true, hinweis:'App-Passwort verwenden' },
    { name:'Outlook', host:'smtp.office365.com', port:587, secure:false, hinweis:'Microsoft-Konto-Passwort' },
    { name:'Strato', host:'smtp.strato.de', port:587, secure:false, hinweis:'E-Mail-Passwort verwenden' },
    { name:'1&1 IONOS', host:'smtp.ionos.de', port:587, secure:false, hinweis:'E-Mail-Passwort verwenden' },
    { name:'GMX', host:'mail.gmx.net', port:587, secure:false, hinweis:'GMX-Passwort verwenden' },
    { name:'Web.de', host:'smtp.web.de', port:587, secure:false, hinweis:'Web.de-Passwort verwenden' },
    { name:'T-Online', host:'securesmtp.t-online.de', port:587, secure:false, hinweis:'T-Online Passwort verwenden' },
  ];

  function wendeAnbieterAn(a) {
    cfg = { ...cfg, smtp_host: a.host, smtp_port: a.port, smtp_secure: a.secure };
    showToast('Anbieter gewählt: ' + a.name);
  }

  // ═══════════════════════════════════════════════════════
  // API-CALLS — FIX 1: text_vorlage = HTML, email_blocks_json = JSON
  // ═══════════════════════════════════════════════════════
  async function ladeVersandConfig() {
    if (!$currentUser) return;
    configLaeuft = true;
    try {
      const data = await apiCall('email-config-laden', { user_id: $currentUser.id });
      if (data?.config) {
        cfg = {
          smtp_host: data.config.smtp_host || '',
          smtp_port: data.config.smtp_port || 587,
          smtp_user: data.config.smtp_user || '',
          smtp_pass: '',
          smtp_secure: data.config.smtp_secure || false,
          absender_name: data.config.absender_name || '',
          absender_email: data.config.absender_email || '',
          betreff_vorlage: data.config.betreff_vorlage || cfg.betreff_vorlage,
          text_vorlage: data.config.text_vorlage || '',
          auto_versand: data.config.auto_versand || false,
        };
        // Blocks aus email_blocks_json laden
        const blocksJson = data.config.email_blocks_json || '';
        if (blocksJson && jsonToBlocks(blocksJson)) {
          // Blocks erfolgreich geladen
        } else if (cfg.text_vorlage) {
          // Fallback: alte HTML-Vorlage als Text-Block
          blocks = [{ type:'text', content: cfg.text_vorlage, fontSize:'15', id:'b_1' }];
          blockIdCounter = 2;
        }
      }
    } catch(e) {
      console.warn('Email-Config nicht geladen:', e?.message || e);
    } finally {
      configLaeuft = false;
    }
  }

  async function toggleAutoVersand() {
    cfg.auto_versand = !cfg.auto_versand;
    try {
      await apiCall('email-config-speichern', {
        user_id: $currentUser.id, ...cfg,
        text_vorlage: generateFullHtml(),
        email_blocks_json: blocksToJson()
      });
      showToast(cfg.auto_versand ? '✅ Auto-Versand aktiviert' : 'Auto-Versand deaktiviert');
    } catch(e) {
      cfg.auto_versand = !cfg.auto_versand;
      showToast('Fehler: ' + e.message);
    }
  }

  async function speichern() {
    if (!cfg.smtp_host || !cfg.smtp_user) { showToast('Bitte SMTP-Host und Benutzername ausfüllen.'); return; }
    speichertLaeuft = true;
    try {
      const emailHtml = htmlCodeOffen ? (cfg.text_vorlage || generateFullHtml()) : generateFullHtml();
      await apiCall('email-config-speichern', {
        user_id: $currentUser.id, ...cfg,
        text_vorlage: emailHtml,
        email_blocks_json: blocksToJson()
      });
      showToast('✅ E-Mail-Einstellungen gespeichert');
    } catch(e) {
      showToast('Fehler: ' + e.message);
    } finally {
      speichertLaeuft = false;
    }
  }

  async function testSenden() {
    if (!testEmail) { showToast('Bitte Test-E-Mail-Adresse eingeben.'); return; }
    if (!cfg.smtp_host || !cfg.smtp_user) { showToast('Bitte SMTP-Daten ausfüllen.'); return; }
    testLaeuft = true; testStatus = null; testNachricht = '';
    try {
      await apiCall('email-config-speichern', {
        user_id: $currentUser.id, ...cfg,
        text_vorlage: generateFullHtml(),
        email_blocks_json: blocksToJson()
      });
      await apiCall('smtp-testen', { user_id: $currentUser.id, to_email: testEmail });
      testStatus = 'success';
      testNachricht = 'Test-E-Mail gesendet an ' + testEmail;
    } catch(e) {
      testStatus = 'error';
      testNachricht = e.message || 'Verbindung fehlgeschlagen.';
    } finally {
      testLaeuft = false;
    }
  }

  // ═══════════════════════════════════════════════════════
  // EMPFANG (IMAP)
  // ═══════════════════════════════════════════════════════
  let imapLaeuft = $state(false);
  let imapSpeichertLaeuft = $state(false);
  let imapTestLaeuft = $state(false);
  let imapLoeschenLaeuft = $state(false);
  let imapPasswortZeigen = $state(false);
  let imapTestStatus = $state(null);
  let imapTestNachricht = $state('');
  let imapTestFolders = $state([]);
  let imap = $state({ email:'', host:'imap.hostinger.com', port:993, user_name:'', pass:'', folder:'INBOX', processed_folder:'Rechnungen', filter_betreff:'', aktiv:false });
  let imapConfigExistiert = $state(false);
  let lastCheck = $state(null);
  let lastError = $state(null);

  const imapAnbieter = [
    { name:'Hostinger', host:'imap.hostinger.com', port:993, hinweis:'Hostinger hPanel' },
    { name:'Gmail', host:'imap.gmail.com', port:993, hinweis:'App-Passwort' },
    { name:'Outlook', host:'outlook.office365.com', port:993, hinweis:'Microsoft-Konto' },
    { name:'IONOS', host:'imap.ionos.de', port:993, hinweis:'E-Mail-Passwort' },
    { name:'Strato', host:'imap.strato.de', port:993, hinweis:'E-Mail-Passwort' },
    { name:'GMX', host:'imap.gmx.net', port:993, hinweis:'GMX-Passwort' },
  ];

  function wendeImapAnbieterAn(a) { imap = { ...imap, host:a.host, port:a.port }; showToast('Anbieter: ' + a.name); }
  async function ladeImapConfig() {
    if (!$currentUser) return; imapLaeuft = true;
    try {
      const res = await apiCall('imap-config', { user_id:$currentUser.id, action:'load' });
      if (res?.config) { imap = { email:res.config.email||'', host:res.config.host||'imap.hostinger.com', port:res.config.port||993, user_name:res.config.user_name||'', pass:'', folder:res.config.folder||'INBOX', processed_folder:res.config.processed_folder||'Rechnungen', filter_betreff:res.config.filter_betreff||'', aktiv:res.config.aktiv||false }; imapConfigExistiert = true; lastCheck = res.config.last_check||null; lastError = res.config.last_error||null; }
      else { imapConfigExistiert = false; }
    } catch(e) { console.warn('IMAP:', e?.message); } finally { imapLaeuft = false; }
  }
  async function imapSpeichern() { if (!imap.host||!imap.user_name) { showToast('IMAP-Host und User ausfüllen.'); return; } imapSpeichertLaeuft = true; try { await apiCall('imap-config', { user_id:$currentUser.id, action:'save', ...imap }); showToast('✅ IMAP gespeichert'); imapConfigExistiert = true; imap.pass = ''; } catch(e) { showToast('Fehler: ' + e.message); } finally { imapSpeichertLaeuft = false; } }
  async function imapTesten() { if (!imap.host||!imap.user_name) { showToast('IMAP-Host und User ausfüllen.'); return; } if (!imap.pass) { showToast('Passwort eingeben.'); return; } imapTestLaeuft = true; imapTestStatus = null; imapTestNachricht = ''; imapTestFolders = []; try { const res = await apiCall('imap-config', { user_id:$currentUser.id, action:'test', host:imap.host, port:imap.port, user_name:imap.user_name, pass:imap.pass, folder:imap.folder, processed_folder:imap.processed_folder }); if (res?.success) { imapTestStatus = 'success'; let msg = '✅ OK'; if (typeof res.messages_new === 'number') msg += ' — ' + res.messages_new + ' Mails'; imapTestNachricht = msg; imapTestFolders = res.folders||[]; } else { imapTestStatus = 'error'; imapTestNachricht = res?.error||'Fehlgeschlagen'; imapTestFolders = res?.folders||[]; } } catch(e) { imapTestStatus = 'error'; imapTestNachricht = e.message; } finally { imapTestLaeuft = false; } }
  async function toggleImapAktiv() { imap.aktiv = !imap.aktiv; try { await apiCall('imap-config', { user_id:$currentUser.id, action:'save', ...imap }); showToast(imap.aktiv ? '✅ IMAP aktiv' : 'IMAP inaktiv'); } catch(e) { imap.aktiv = !imap.aktiv; showToast('Fehler: ' + e.message); } }
  async function imapLoeschen() { if (!confirm('IMAP-Konfiguration löschen?')) return; imapLoeschenLaeuft = true; try { await apiCall('imap-config', { user_id:$currentUser.id, action:'delete' }); showToast('✅ Gelöscht'); imap = { email:'', host:'imap.hostinger.com', port:993, user_name:'', pass:'', folder:'INBOX', processed_folder:'Rechnungen', filter_betreff:'', aktiv:false }; imapConfigExistiert = false; lastCheck = null; lastError = null; } catch(e) { showToast('Fehler: ' + e.message); } finally { imapLoeschenLaeuft = false; } }
  function formatDatum(iso) { if (!iso) return '—'; try { return new Date(iso).toLocaleString('de-DE'); } catch { return iso; } }

  // ═══════════════════════════════════════════════════════
  // KAUF-NACHRICHT
  // ═══════════════════════════════════════════════════════
  let kaufLaeuft = $state(false);
  let kaufSpeichertLaeuft = $state(false);
  let kaufVorlageRef = $state(null);
  let kauf = $state({ kauf_nachricht_aktiv: false, kauf_nachricht_betreff: 'Danke für deinen Kauf!', kauf_nachricht_vorlage: 'Hallo {{buyer}},\n\nvielen Dank für deinen Kauf von "{{artikel}}" (Bestellung {{order_id}}).\n\nWir versenden die Ware schnellstmöglich.\n\nViele Grüße' });
  const kaufPlatzhalter = [ { key:'{{buyer}}', beschreibung:'eBay-Username' }, { key:'{{artikel}}', beschreibung:'Artikelname' }, { key:'{{menge}}', beschreibung:'Menge' }, { key:'{{preis}}', beschreibung:'Stückpreis' }, { key:'{{order_id}}', beschreibung:'Bestell-ID' } ];
  function kaufPlatzhalterEinfuegen(key) { const ta = kaufVorlageRef; if (!ta) { kauf.kauf_nachricht_vorlage = (kauf.kauf_nachricht_vorlage||'') + key; return; } const start = ta.selectionStart, end = ta.selectionEnd; kauf.kauf_nachricht_vorlage = (kauf.kauf_nachricht_vorlage||'').slice(0,start) + key + (kauf.kauf_nachricht_vorlage||'').slice(end); setTimeout(() => { ta.focus(); ta.selectionStart = ta.selectionEnd = start + key.length; }, 0); }
  function kaufVorschauText() { return (kauf.kauf_nachricht_vorlage||'').replace(/\{\{buyer\}\}/gi,'max_mustermann').replace(/\{\{artikel\}\}/gi,'Windows 11 Pro').replace(/\{\{menge\}\}/gi,'1').replace(/\{\{preis\}\}/gi,'19,99 €').replace(/\{\{order_id\}\}/gi,'12-34567-89012'); }
  function kaufVorschauBetreff() { return (kauf.kauf_nachricht_betreff||'').replace(/\{\{buyer\}\}/gi,'max_mustermann').replace(/\{\{artikel\}\}/gi,'Windows 11 Pro').replace(/\{\{order_id\}\}/gi,'12-34567-89012'); }
  async function ladeKaufConfig() { if (!$currentUser) return; kaufLaeuft = true; try { const data = await apiCall('kauf-nachricht-config', { action:'load', user_id:$currentUser.id }); if (data?.config) { let v = data.config.kauf_nachricht_vorlage || kauf.kauf_nachricht_vorlage; if (v?.includes('\\n')) v = v.replace(/\\n/g, '\n'); kauf = { kauf_nachricht_aktiv: data.config.kauf_nachricht_aktiv ?? false, kauf_nachricht_betreff: data.config.kauf_nachricht_betreff || kauf.kauf_nachricht_betreff, kauf_nachricht_vorlage: v }; } } catch(e) { console.warn('Kauf:', e?.message); } finally { kaufLaeuft = false; } }
  async function toggleKaufNachricht() { kauf.kauf_nachricht_aktiv = !kauf.kauf_nachricht_aktiv; try { await apiCall('kauf-nachricht-config', { action:'save', user_id:$currentUser.id, ...kauf }); showToast(kauf.kauf_nachricht_aktiv ? '✅ Aktiv' : 'Deaktiviert'); } catch(e) { kauf.kauf_nachricht_aktiv = !kauf.kauf_nachricht_aktiv; showToast('Fehler: ' + e.message); } }
  async function kaufSpeichern() { if (!kauf.kauf_nachricht_betreff?.trim()||!kauf.kauf_nachricht_vorlage?.trim()) { showToast('Betreff und Text ausfüllen.'); return; } kaufSpeichertLaeuft = true; try { await apiCall('kauf-nachricht-config', { action:'save', user_id:$currentUser.id, ...kauf }); showToast('✅ Gespeichert'); } catch(e) { showToast('Fehler: ' + e.message); } finally { kaufSpeichertLaeuft = false; } }

  // ═══════════════════════════════════════════════════════
  // INIT
  // ═══════════════════════════════════════════════════════
  onMount(async () => { testEmail = $currentUser?.email || ''; await ladeVersandConfig(); await ladeImapConfig(); await ladeKaufConfig(); });
  let selectedBlock = $derived(selectedBlockId ? blocks.find(b => b.id === selectedBlockId) || null : null);
</script>

<div class="page-container">
  <div class="page-hdr">
    <div class="hdr-left">
      <button class="btn-back" onclick={() => goto('/einstellungen')}>← Zurück</button>
      <div><div class="page-title">📧 E-Mail</div><div class="page-sub">Rechnungen versenden, empfangen und eBay-Nachrichten</div></div>
    </div>
    {#if tab === 'versand'}<button class="btn-primary" onclick={speichern} disabled={speichertLaeuft}>{speichertLaeuft ? '⏳ Speichert…' : '💾 Speichern'}</button>
    {:else if tab === 'empfang'}<button class="btn-primary" onclick={imapSpeichern} disabled={imapSpeichertLaeuft}>{imapSpeichertLaeuft ? '⏳…' : '💾 Speichern'}</button>
    {:else}<button class="btn-primary" onclick={kaufSpeichern} disabled={kaufSpeichertLaeuft}>{kaufSpeichertLaeuft ? '⏳…' : '💾 Speichern'}</button>{/if}
  </div>

  <div class="tab-bar">
    <button class="tab-btn" class:active={tab==='versand'} onclick={() => tab='versand'}>📤 Versand</button>
    <button class="tab-btn" class:active={tab==='empfang'} onclick={() => tab='empfang'}>📥 Empfang {#if imap.aktiv}<span class="tab-badge-grn">aktiv</span>{/if}</button>
    <button class="tab-btn" class:active={tab==='kauf'} onclick={() => tab='kauf'}>💬 Kauf-Nachricht {#if kauf.kauf_nachricht_aktiv}<span class="tab-badge-grn">aktiv</span>{/if}</button>
  </div>

  {#if tab === 'versand'}
    {#if configLaeuft}<div class="config-laedt"><span class="spinner"></span> Laden…</div>{/if}

    <div class="card"><div class="card-titel">⚡ Anbieter</div><div class="anbieter-grid">{#each anbieterVorlagen as a}<button class="anbieter-btn" class:aktiv={cfg.smtp_host===a.host&&cfg.smtp_port===a.port} onclick={() => wendeAnbieterAn(a)} title={a.hinweis}>{a.name}</button>{/each}</div></div>

    <div class="card"><div class="card-titel">🔌 SMTP</div><div class="form-grid">
      <div class="form-group form-span2"><label>Host *</label><input bind:value={cfg.smtp_host} placeholder="smtp.hostinger.com" /></div>
      <div class="form-group"><label>Port</label><input bind:value={cfg.smtp_port} type="number" /></div>
      <div class="form-group"><label>SSL/TLS</label><label class="check-label"><input type="checkbox" bind:checked={cfg.smtp_secure} /> Port 465</label></div>
      <div class="form-group"><label>User *</label><input bind:value={cfg.smtp_user} type="email" placeholder="deine@email.de" /></div>
      <div class="form-group"><label>Passwort</label><div class="input-row"><input bind:value={cfg.smtp_pass} type={passwortZeigen?'text':'password'} placeholder="Passwort" style="flex:1" /><button class="btn-ghost btn-sm" onclick={()=>passwortZeigen=!passwortZeigen}>{passwortZeigen?'🙈':'👁'}</button></div></div>
    </div></div>

    <div class="card"><div class="card-titel">✉️ Absender</div><div class="form-grid">
      <div class="form-group"><label>Name</label><input bind:value={cfg.absender_name} placeholder="Mein Shop" /></div>
      <div class="form-group"><label>E-Mail</label><input bind:value={cfg.absender_email} type="email" placeholder="(leer = SMTP-User)" /></div>
    </div></div>

    <!-- BLOCK-BUILDER -->
    <div class="card card-builder">
      <div class="card-titel-row">
        <div><div class="card-titel">📝 E-Mail Vorlage</div><div class="card-sub">Baue deine E-Mail aus Bausteinen zusammen — Textblöcke direkt auf der Leinwand editieren</div></div>
        <div class="builder-top-actions">
          <button class="btn-ghost btn-sm" onclick={() => templateModalOffen = true}>🎨 Vorlagen</button>
          <button class="btn-ghost btn-sm" onclick={() => { vorschauOffen=!vorschauOffen; htmlCodeOffen=false; }}>{vorschauOffen ? '✏️ Editor' : '👁 Vorschau'}</button>
          <button class="btn-ghost btn-sm" onclick={() => { htmlCodeOffen=!htmlCodeOffen; vorschauOffen=false; }}>{htmlCodeOffen ? '✏️ Editor' : '⟨/⟩ HTML'}</button>
        </div>
      </div>

      <div class="variablen-bar"><span class="var-titel">Variablen (Klick=kopieren):</span>
        {#each variablen as v}<button class="var-chip" title={v.beschreibung} onclick={() => { navigator.clipboard.writeText(v.key); showToast('Kopiert: ' + v.key); }}>{v.key}</button>{/each}
      </div>

      <div class="form-group" style="padding:0 0 8px"><label>Betreff</label><input bind:value={cfg.betreff_vorlage} placeholder={'Ihre Rechnung {{rechnung_nr}}'} /></div>

      {#if vorschauOffen}
        <div class="vorschau-wrap">
          <div class="vorschau-header"><div><span class="vorschau-label">An:</span> max.mustermann@example.com</div><div><span class="vorschau-label">Betreff:</span> <strong>{cfg.betreff_vorlage.replace(/\{\{rechnung_nr\}\}/g, 'RE-2026-00042')}</strong></div></div>
          <div class="vorschau-canvas">{@html vorschauHtml()}</div>
        </div>
      {:else if htmlCodeOffen}
        <div class="form-group">
          <textarea class="html-code-area" rows="18" bind:value={cfg.text_vorlage}></textarea>
          <div style="display:flex;gap:8px;margin-top:6px">
            <button class="btn-ghost btn-sm" onclick={() => { navigator.clipboard.writeText(cfg.text_vorlage || generateFullHtml()); showToast('HTML kopiert!'); }}>📋 Kopieren</button>
            <button class="btn-primary btn-sm" onclick={() => { cfg.text_vorlage = generateFullHtml(); showToast('HTML aus Blöcken neu generiert'); }}>🔄 Aus Blöcken generieren</button>
          </div>
          <span class="prop-hint" style="margin-top:4px">⚠️ Änderungen hier überschreiben das Block-HTML beim Speichern. Klick „Aus Blöcken generieren" um den Block-Stand zu laden.</span>
        </div>
      {:else}
        <div class="builder-layout">
          <div class="palette">
            <div class="palette-section-title">Struktur</div>
            {#each bausteinListe.filter(b=>b.group==='struktur') as b}<button class="block-item" onclick={()=>addBlock(b.type)}><span class="block-icon">{b.icon}</span><span class="block-info"><span class="block-name">{b.name}</span><span class="block-desc">{b.desc}</span></span></button>{/each}
            <div class="palette-section-title" style="margin-top:14px">Inhalt</div>
            {#each bausteinListe.filter(b=>b.group==='inhalt') as b}<button class="block-item" onclick={()=>addBlock(b.type)}><span class="block-icon">{b.icon}</span><span class="block-info"><span class="block-name">{b.name}</span><span class="block-desc">{b.desc}</span></span></button>{/each}
          </div>

          <div class="canvas-scroll"><div class="email-frame"><div class="email-canvas">
            {#if blocks.length === 0}
              <div class="drop-empty"><div class="drop-empty-icon">📧</div><div>Klicke links auf Bausteine<br>oder wähle eine Vorlage</div><button class="btn-ghost btn-sm" style="margin-top:12px" onclick={()=>templateModalOffen=true}>🎨 Vorlage wählen</button></div>
            {:else}
              {#each blocks as block, i (block.id)}
                <div class="canvas-block" class:selected={selectedBlockId===block.id}>
                  <!-- svelte-ignore a11y_click_events_have_key_events -->
                  <!-- svelte-ignore a11y_no_static_element_interactions -->
                  <div class="canvas-block-inner" onclick={()=>selectBlock(block.id)}>
                    <div class="block-actions">
                      {#if i>0}<button class="ba-btn" onclick={(e)=>{e.stopPropagation();moveBlock(block.id,-1)}} title="↑">↑</button>{/if}
                      {#if i<blocks.length-1}<button class="ba-btn" onclick={(e)=>{e.stopPropagation();moveBlock(block.id,1)}} title="↓">↓</button>{/if}
                      <button class="ba-btn" onclick={(e)=>{e.stopPropagation();duplicateBlock(block.id)}} title="Kopie">⎘</button>
                      <button class="ba-btn" onclick={(e)=>{e.stopPropagation();deleteBlock(block.id)}} title="Löschen">✕</button>
                    </div>

                    {#if block.type==='header'}
                      <div class="b-header" style="background:{block.bgColor};color:{block.textColor};{block.borderRadius?'border-radius:12px 12px 0 0;':''}">
                        {#if block.icon}<div class="b-header-icon">{block.icon}</div>{/if}
                        <!-- svelte-ignore a11y_no_static_element_interactions -->
                        <h2 contenteditable="true" class="editable-inline"
                          onblur={(e)=>updateBlock(block.id,'title',e.target.innerText)}
                          onclick={(e)=>e.stopPropagation()}
                        >{block.title}</h2>
                        <!-- svelte-ignore a11y_no_static_element_interactions -->
                        <div class="b-header-sub editable-inline" contenteditable="true"
                          onblur={(e)=>updateBlock(block.id,'subtitle',e.target.innerText)}
                          onclick={(e)=>e.stopPropagation()}
                        >{block.subtitle || 'Untertitel...'}</div>
                      </div>
                    {:else if block.type==='text'}
                      <!-- FIX 5: Inline-Editing -->
                      <!-- svelte-ignore a11y_no_static_element_interactions -->
                      <div class="b-text" style="font-size:{block.fontSize||15}px"
                        contenteditable="true"
                        onblur={(e)=>updateBlock(block.id,'content',e.target.innerText)}
                        onclick={(e)=>e.stopPropagation()}
                      >{block.content}</div>
                    {:else if block.type==='infobox'}
                      <!-- svelte-ignore a11y_no_static_element_interactions -->
                      <div class="b-infobox style-{block.style} editable-inline" contenteditable="true"
                        onblur={(e)=>updateBlock(block.id,'content',e.target.innerHTML)}
                        onclick={(e)=>e.stopPropagation()}
                      >{@html block.content}</div>
                    {:else if block.type==='amount'}
                      <div class="b-amount" style="background:{block.bgColor};border-color:{block.accentColor}">
                        <!-- svelte-ignore a11y_no_static_element_interactions -->
                        <div class="amount-label editable-inline" style="color:{block.accentColor}" contenteditable="true"
                          onblur={(e)=>updateBlock(block.id,'label',e.target.innerText)}
                          onclick={(e)=>e.stopPropagation()}
                        >{block.label}</div>
                        <!-- svelte-ignore a11y_no_static_element_interactions -->
                        <div class="amount-value editable-inline" style="color:{block.accentColor}" contenteditable="true"
                          onblur={(e)=>updateBlock(block.id,'value',e.target.innerText)}
                          onclick={(e)=>e.stopPropagation()}
                        >{block.value}</div>
                        {#if block.sublabel}<div class="amount-sub">{block.sublabel}</div>{/if}
                      </div>
                    {:else if block.type==='button'}
                      <div class="b-button-wrap">
                        <!-- svelte-ignore a11y_no_static_element_interactions -->
                        <span class="b-button editable-inline" style="background:{block.bgColor};color:{block.textColor};border-radius:{block.borderRadius}px" contenteditable="true"
                          onblur={(e)=>updateBlock(block.id,'text',e.target.innerText)}
                          onclick={(e)=>e.stopPropagation()}
                        >{block.text}</span>
                      </div>
                    {:else if block.type==='divider'}
                      <div class="b-divider {block.style==='bold'?'style-bold':''} {block.style==='colored'?'style-colored':''}"><hr /></div>
                    {:else if block.type==='spacer'}
                      <div class="b-spacer" style="height:{block.height}px"></div>
                    {:else if block.type==='image'}
                      <div class="b-image" style="text-align:{block.align||'center'}">
                        {#if block.url}<img src={block.url} alt={block.alt} style="max-width:{block.maxWidth}" />
                        {:else}<div class="img-placeholder">🖼️ URL in Eigenschaften eingeben</div>{/if}
                      </div>
                    {:else if block.type==='signature'}
                      <div class="b-signature">
                        <!-- svelte-ignore a11y_no_static_element_interactions -->
                        <strong class="editable-inline" contenteditable="true"
                          onblur={(e)=>updateBlock(block.id,'name',e.target.innerText)}
                          onclick={(e)=>e.stopPropagation()}
                        >{block.name}</strong><br>
                        <!-- svelte-ignore a11y_no_static_element_interactions -->
                        <span class="editable-inline" contenteditable="true" style="display:inline-block;min-width:100px"
                          onblur={(e)=>updateBlock(block.id,'details',e.target.innerText)}
                          onclick={(e)=>e.stopPropagation()}
                        >{block.details}</span><br>
                        {#if block.phone}📞 {block.phone}<br>{/if}
                        {#if block.email}📧 {block.email}<br>{/if}
                        {#if block.logoUrl}<img src={block.logoUrl} width={block.logoWidth||120} style="max-width:100%;height:auto;display:block;margin-top:8px" alt="Logo" />{/if}
                      </div>
                    {:else if block.type==='columns'}
                      <div class="b-columns">
                        <!-- svelte-ignore a11y_no_static_element_interactions -->
                        <div class="col editable-inline" contenteditable="true"
                          onblur={(e)=>updateBlock(block.id,'left',e.target.innerText)}
                          onclick={(e)=>e.stopPropagation()}
                        >{block.left}</div>
                        <!-- svelte-ignore a11y_no_static_element_interactions -->
                        <div class="col editable-inline" contenteditable="true"
                          onblur={(e)=>updateBlock(block.id,'right',e.target.innerText)}
                          onclick={(e)=>e.stopPropagation()}
                        >{block.right}</div>
                      </div>
                    {/if}
                  </div>
                </div>
              {/each}
            {/if}
            <div class="email-footer">© 2026 {'{{firmenname}}'}. Alle Rechte vorbehalten.</div>
          </div></div></div>

          <div class="props-panel">
            {#if selectedBlock}
              <div class="props-header"><div class="props-title">⚙️ Eigenschaften</div></div>

              {#if selectedBlock.type==='header'}
                <div class="props-section"><div class="ps-title">Inhalt</div>
                  <div class="prop-row"><label>Icon</label><input value={selectedBlock.icon||''} oninput={(e)=>updateBlock(selectedBlock.id,'icon',e.target.value)} /></div>
                  <div class="prop-row"><label>Titel</label><input value={selectedBlock.title} oninput={(e)=>updateBlock(selectedBlock.id,'title',e.target.value)} /></div>
                  <div class="prop-row"><label>Untertitel</label><input value={selectedBlock.subtitle||''} oninput={(e)=>updateBlock(selectedBlock.id,'subtitle',e.target.value)} /></div>
                </div>
                <div class="props-section"><div class="ps-title">Farbe</div><div class="color-row">{#each headerFarben as c}<button class="color-swatch" class:active={selectedBlock.bgColor===c} style="background:{c}" onclick={()=>updateBlock(selectedBlock.id,'bgColor',c)}></button>{/each}</div></div>

              {:else if selectedBlock.type==='text'}
                <div class="props-section"><div class="ps-title">Schriftgröße</div>
                  <div class="size-btns">{#each fontSizes as s}<button class="btn-ghost btn-sm" class:btn-active={String(selectedBlock.fontSize||'15')===s} onclick={()=>updateBlock(selectedBlock.id,'fontSize',s)}>{s}px</button>{/each}</div>
                </div>
                <div class="props-section"><div class="ps-title">Text (oder direkt auf Canvas tippen)</div>
                  <textarea rows="8" oninput={(e)=>updateBlock(selectedBlock.id,'content',e.target.value)}>{selectedBlock.content}</textarea>
                  <span class="prop-hint">Variablen wie {'{{kaeufer_name}}'} einfach eintippen</span>
                </div>

              {:else if selectedBlock.type==='infobox'}
                <div class="props-section"><div class="ps-title">Farbe</div><div class="color-row">
                  <button class="color-swatch" class:active={selectedBlock.style==='blue'} style="background:#2563eb" onclick={()=>updateBlock(selectedBlock.id,'style','blue')}></button>
                  <button class="color-swatch" class:active={selectedBlock.style==='green'} style="background:#10b981" onclick={()=>updateBlock(selectedBlock.id,'style','green')}></button>
                  <button class="color-swatch" class:active={selectedBlock.style==='yellow'} style="background:#f59e0b" onclick={()=>updateBlock(selectedBlock.id,'style','yellow')}></button>
                  <button class="color-swatch" class:active={selectedBlock.style==='red'} style="background:#ef4444" onclick={()=>updateBlock(selectedBlock.id,'style','red')}></button>
                </div></div>
                <div class="props-section"><div class="ps-title">Inhalt (HTML)</div><textarea rows="5" oninput={(e)=>updateBlock(selectedBlock.id,'content',e.target.value)}>{selectedBlock.content}</textarea></div>

              {:else if selectedBlock.type==='amount'}
                <div class="props-section"><div class="ps-title">Inhalt</div>
                  <div class="prop-row"><label>Label</label><input value={selectedBlock.label} oninput={(e)=>updateBlock(selectedBlock.id,'label',e.target.value)} /></div>
                  <div class="prop-row"><label>Wert</label><input value={selectedBlock.value} oninput={(e)=>updateBlock(selectedBlock.id,'value',e.target.value)} /></div>
                  <div class="prop-row"><label>Sublabel</label><input value={selectedBlock.sublabel||''} oninput={(e)=>updateBlock(selectedBlock.id,'sublabel',e.target.value)} /></div>
                </div>
                <div class="props-section"><div class="ps-title">Farbe</div><div class="color-row">{#each accentFarben as c}<button class="color-swatch" class:active={selectedBlock.accentColor===c} style="background:{c}" onclick={()=>updateBlock(selectedBlock.id,'accentColor',c)}></button>{/each}</div></div>

              {:else if selectedBlock.type==='button'}
                <div class="props-section"><div class="ps-title">Button</div>
                  <div class="prop-row"><label>Text</label><input value={selectedBlock.text} oninput={(e)=>updateBlock(selectedBlock.id,'text',e.target.value)} /></div>
                  <div class="prop-row"><label>URL</label><input value={selectedBlock.url} oninput={(e)=>updateBlock(selectedBlock.id,'url',e.target.value)} /></div>
                </div>
                <div class="props-section"><div class="ps-title">Farbe</div><div class="color-row">{#each buttonFarben as c}<button class="color-swatch" class:active={selectedBlock.bgColor===c} style="background:{c}" onclick={()=>updateBlock(selectedBlock.id,'bgColor',c)}></button>{/each}</div></div>

              {:else if selectedBlock.type==='divider'}
                <div class="props-section"><div class="ps-title">Stil</div><div class="divider-btns">
                  <button class="btn-ghost btn-sm" class:btn-active={selectedBlock.style==='normal'} onclick={()=>updateBlock(selectedBlock.id,'style','normal')}>Normal</button>
                  <button class="btn-ghost btn-sm" class:btn-active={selectedBlock.style==='bold'} onclick={()=>updateBlock(selectedBlock.id,'style','bold')}>Dick</button>
                  <button class="btn-ghost btn-sm" class:btn-active={selectedBlock.style==='colored'} onclick={()=>updateBlock(selectedBlock.id,'style','colored')}>Farbig</button>
                </div></div>

              {:else if selectedBlock.type==='spacer'}
                <div class="props-section"><div class="ps-title">Höhe (px)</div><input type="number" value={selectedBlock.height} oninput={(e)=>updateBlock(selectedBlock.id,'height',parseInt(e.target.value)||24)} /></div>

              {:else if selectedBlock.type==='image'}
                <div class="props-section"><div class="ps-title">Bild</div>
                  <div class="prop-row"><label>URL</label><input value={selectedBlock.url||''} oninput={(e)=>updateBlock(selectedBlock.id,'url',e.target.value)} placeholder="https://..." /></div>
                  <div class="prop-row"><label>Alt</label><input value={selectedBlock.alt||''} oninput={(e)=>updateBlock(selectedBlock.id,'alt',e.target.value)} /></div>
                  <div class="prop-row"><label>Max. Breite</label><input value={selectedBlock.maxWidth||'100%'} oninput={(e)=>updateBlock(selectedBlock.id,'maxWidth',e.target.value)} placeholder="200px oder 50%" /></div>
                </div>
                <div class="props-section"><div class="ps-title">Ausrichtung</div><div class="divider-btns">
                  <button class="btn-ghost btn-sm" class:btn-active={selectedBlock.align==='left'} onclick={()=>updateBlock(selectedBlock.id,'align','left')}>⬅ Links</button>
                  <button class="btn-ghost btn-sm" class:btn-active={selectedBlock.align==='center'||!selectedBlock.align} onclick={()=>updateBlock(selectedBlock.id,'align','center')}>⬌ Mitte</button>
                  <button class="btn-ghost btn-sm" class:btn-active={selectedBlock.align==='right'} onclick={()=>updateBlock(selectedBlock.id,'align','right')}>➡ Rechts</button>
                </div></div>

              {:else if selectedBlock.type==='signature'}
                <div class="props-section"><div class="ps-title">Firmendaten</div>
                  <div class="prop-row"><label>Name</label><input value={selectedBlock.name} oninput={(e)=>updateBlock(selectedBlock.id,'name',e.target.value)} /></div>
                  <div class="prop-row"><label>Details</label><textarea rows="4" oninput={(e)=>updateBlock(selectedBlock.id,'details',e.target.value)}>{selectedBlock.details}</textarea></div>
                  <div class="prop-row"><label>Telefon</label><input value={selectedBlock.phone||''} oninput={(e)=>updateBlock(selectedBlock.id,'phone',e.target.value)} /></div>
                  <div class="prop-row"><label>E-Mail</label><input value={selectedBlock.email||''} oninput={(e)=>updateBlock(selectedBlock.id,'email',e.target.value)} /></div>
                </div>
                <div class="props-section"><div class="ps-title">Logo</div>
                  <div class="prop-row"><label>Logo-URL</label><input value={selectedBlock.logoUrl||''} oninput={(e)=>updateBlock(selectedBlock.id,'logoUrl',e.target.value)} placeholder="https://..." /></div>
                  <div class="prop-row"><label>Breite (px)</label><input type="number" value={selectedBlock.logoWidth||120} oninput={(e)=>updateBlock(selectedBlock.id,'logoWidth',e.target.value)} /></div>
                </div>

              {:else if selectedBlock.type==='columns'}
                <div class="props-section"><div class="ps-title">Spalten</div>
                  <div class="prop-row"><label>Links</label><textarea rows="3" oninput={(e)=>updateBlock(selectedBlock.id,'left',e.target.value)}>{selectedBlock.left}</textarea></div>
                  <div class="prop-row"><label>Rechts</label><textarea rows="3" oninput={(e)=>updateBlock(selectedBlock.id,'right',e.target.value)}>{selectedBlock.right}</textarea></div>
                </div>
              {/if}
            {:else}
              <div class="props-empty"><div style="font-size:1.8rem;margin-bottom:10px;opacity:0.3">👈</div><div>Block auf der Leinwand auswählen</div></div>
            {/if}
          </div>
        </div>
      {/if}
    </div>

    <div class="card"><div class="card-titel">🤖 Auto-Versand</div>
      <div class="auto-row"><div><div class="auto-titel">Nach Rechnungserstellung automatisch senden</div><div class="auto-sub">Nur wenn Käufer-E-Mail vorhanden.</div></div>
        <button class="toggle-btn" class:toggle-an={cfg.auto_versand} class:toggle-aus={!cfg.auto_versand} onclick={toggleAutoVersand}><span class="toggle-thumb"></span></button>
      </div>
      {#if cfg.auto_versand}<div class="status-hinweis status-ok">✅ Aktiv</div>{:else}<div class="status-hinweis status-inaktiv">⏸ Inaktiv</div>{/if}
    </div>

    <div class="card card-test"><div class="card-titel">🧪 Test</div>
      <div class="test-row"><input bind:value={testEmail} type="email" placeholder="test@example.com" style="flex:1;min-width:200px" /><button class="btn-primary" onclick={testSenden} disabled={testLaeuft}>{testLaeuft?'⏳…':'📤 Testen'}</button></div>
      {#if testStatus==='success'}<div class="test-result test-ok">✅ {testNachricht}</div>{/if}
      {#if testStatus==='error'}<div class="test-result test-fehler">❌ {testNachricht}</div>{/if}
    </div>
  {/if}

  {#if tab === 'empfang'}
    {#if imapLaeuft}<div class="config-laedt"><span class="spinner"></span> Laden…</div>{/if}
    <div class="card card-info"><div class="card-titel">📥 Email-Import</div><ul class="info-liste" style="margin:0;padding-left:18px"><li>Alle 30 Min. werden Mails abgeholt</li><li>PDFs werden von KI analysiert</li><li>Ergebnisse unter Buchhaltung → Posteingang</li></ul></div>
    <div class="card"><div class="card-titel">⚡ Anbieter</div><div class="anbieter-grid">{#each imapAnbieter as a}<button class="anbieter-btn" class:aktiv={imap.host===a.host} onclick={()=>wendeImapAnbieterAn(a)}>{a.name}</button>{/each}</div></div>
    <div class="card"><div class="card-titel">🔌 IMAP</div><div class="form-grid">
      <div class="form-group"><label>E-Mail</label><input bind:value={imap.email} type="email" /></div>
      <div class="form-group"><label>Host *</label><input bind:value={imap.host} /></div>
      <div class="form-group"><label>Port</label><input bind:value={imap.port} type="number" /></div>
      <div class="form-group"><label>User *</label><input bind:value={imap.user_name} type="email" /></div>
      <div class="form-group"><label>Passwort</label><div class="input-row"><input bind:value={imap.pass} type={imapPasswortZeigen?'text':'password'} style="flex:1" /><button class="btn-ghost btn-sm" onclick={()=>imapPasswortZeigen=!imapPasswortZeigen}>{imapPasswortZeigen?'🙈':'👁'}</button></div></div>
    </div></div>
    <div class="card"><div class="card-titel">📁 Ordner</div><div class="form-grid">
      <div class="form-group"><label>Eingang</label><input bind:value={imap.folder} placeholder="INBOX" /></div>
      <div class="form-group"><label>Verarbeitet</label><input bind:value={imap.processed_folder} /></div>
      <div class="form-group form-span2"><label>Betreff-Filter</label><input bind:value={imap.filter_betreff} placeholder="leer = alle" /></div>
    </div></div>
    <div class="card"><div class="card-titel">🤖 Auto-Abruf</div><div class="auto-row"><div><div class="auto-titel">Alle 30 Min.</div></div><button class="toggle-btn" class:toggle-an={imap.aktiv} class:toggle-aus={!imap.aktiv} onclick={toggleImapAktiv}><span class="toggle-thumb"></span></button></div>
      {#if imap.aktiv}<div class="status-hinweis status-ok">✅ Aktiv</div>{:else}<div class="status-hinweis status-inaktiv">⏸ Inaktiv</div>{/if}</div>
    <div class="card card-test"><div class="card-titel">🧪 Test</div><div class="test-row"><button class="btn-primary" onclick={imapTesten} disabled={imapTestLaeuft}>{imapTestLaeuft?'⏳…':'🔌 Testen'}</button>{#if imapConfigExistiert}<button class="btn-ghost btn-sm" onclick={imapLoeschen} style="margin-left:auto">🗑️</button>{/if}</div>
      {#if imapTestStatus==='success'}<div class="test-result test-ok">{imapTestNachricht}</div>{/if}
      {#if imapTestStatus==='error'}<div class="test-result test-fehler">❌ {imapTestNachricht}</div>{/if}
      {#if imapTestFolders.length>0}<div class="folders-list"><span class="folders-titel">Ordner:</span>{#each imapTestFolders as f}<span class="folder-chip">{f}</span>{/each}</div>{/if}
    </div>
  {/if}

  {#if tab === 'kauf'}
    {#if kaufLaeuft}<div class="config-laedt"><span class="spinner"></span> Laden…</div>{/if}
    <div class="card card-info"><div class="card-titel">💬 Kauf-Nachricht</div><ul class="info-liste" style="margin:0;padding-left:18px"><li>Automatische eBay-Nachricht nach Kauf</li><li>Platzhalter wie <code>{'{{buyer}}'}</code> werden ersetzt</li></ul></div>
    <div class="card"><div class="card-titel">🤖 Auto-Versand</div><div class="auto-row"><div><div class="auto-titel">Nach Kauf senden</div></div><button class="toggle-btn" class:toggle-an={kauf.kauf_nachricht_aktiv} class:toggle-aus={!kauf.kauf_nachricht_aktiv} onclick={toggleKaufNachricht}><span class="toggle-thumb"></span></button></div>
      {#if kauf.kauf_nachricht_aktiv}<div class="status-hinweis status-ok">✅ Aktiv</div>{:else}<div class="status-hinweis status-inaktiv">⏸ Inaktiv</div>{/if}</div>
    <div class="card"><div class="card-titel">📝 Vorlage</div>
      <div class="variablen-bar"><span class="var-titel">Platzhalter:</span>{#each kaufPlatzhalter as v}<button class="var-chip" onclick={()=>kaufPlatzhalterEinfuegen(v.key)} title={v.beschreibung}>{v.key}</button>{/each}</div>
      <div class="form-grid"><div class="form-group form-span2"><label>Betreff</label><input bind:value={kauf.kauf_nachricht_betreff} /></div><div class="form-group form-span2"><label>Text</label><textarea bind:this={kaufVorlageRef} bind:value={kauf.kauf_nachricht_vorlage} rows="10"></textarea></div></div>
    </div>
    <div class="card"><div class="card-titel">👁 Vorschau</div><div class="vorschau-box"><div class="vorschau-meta"><span class="vorschau-label">An:</span> max_mustermann</div><div class="vorschau-meta"><span class="vorschau-label">Betreff:</span> <strong>{kaufVorschauBetreff()}</strong></div><div class="vorschau-trenner"></div><div class="vorschau-body">{kaufVorschauText()}</div></div></div>
  {/if}
</div>

{#if templateModalOffen}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="modal-overlay" onclick={()=>templateModalOffen=false}>
    <div class="modal-box" style="max-width:680px" onclick={(e)=>e.stopPropagation()}>
      <div class="modal-title">🎨 Vorlage wählen</div>
      <div class="card-sub" style="margin-bottom:16px">Startpunkt wählen — danach alles anpassbar.</div>
      <div class="template-grid">{#each starterTemplates as tpl}<button class="template-card" onclick={()=>loadTemplate(tpl.key)}><span class="template-icon">{tpl.icon}</span><span class="template-name">{tpl.name}</span><span class="template-desc">{tpl.beschreibung}</span></button>{/each}</div>
      <div style="text-align:right;margin-top:18px"><button class="btn-ghost" onclick={()=>templateModalOffen=false}>Schließen</button></div>
    </div>
  </div>
{/if}

<style>
  .page-container { padding:24px; max-width:1400px; margin:0 auto; }
  .page-hdr { display:flex; align-items:center; justify-content:space-between; gap:16px; margin-bottom:16px; flex-wrap:wrap; }
  .page-title { font-size:1.3rem; font-weight:700; color:var(--text); }
  .page-sub { font-size:0.8rem; color:var(--text2); margin-top:2px; }
  .hdr-left { display:flex; align-items:center; gap:16px; }
  .btn-back { background:transparent; border:1px solid var(--border); color:var(--text2); padding:7px 14px; border-radius:8px; font-size:0.82rem; cursor:pointer; }
  .btn-back:hover { border-color:var(--primary); color:var(--primary); }
  .config-laedt { font-size:0.8rem; color:var(--text2); padding:8px 14px; background:var(--surface2); border-radius:8px; margin-bottom:12px; display:flex; align-items:center; gap:10px; }
  .spinner { width:14px; height:14px; border:2px solid var(--border); border-top-color:var(--primary); border-radius:50%; animation:spin .7s linear infinite; display:inline-block; }
  @keyframes spin { to { transform:rotate(360deg); } }
  .tab-bar { display:flex; gap:4px; border-bottom:1px solid var(--border); margin-bottom:16px; }
  .tab-btn { background:transparent; border:none; border-bottom:2px solid transparent; padding:10px 18px; font-size:0.85rem; color:var(--text2); cursor:pointer; font-weight:500; display:inline-flex; align-items:center; gap:6px; }
  .tab-btn:hover { color:var(--text); }
  .tab-btn.active { color:var(--primary); border-bottom-color:var(--primary); font-weight:600; }
  .tab-badge-grn { background:#16a34a; color:#fff; font-size:.62rem; padding:2px 6px; border-radius:10px; font-weight:600; }
  .card { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:20px 24px; display:flex; flex-direction:column; gap:14px; margin-bottom:16px; }
  .card-builder { padding:20px; }
  .card-titel { font-size:.88rem; font-weight:700; color:var(--text); }
  .card-sub { font-size:.78rem; color:var(--text2); }
  .card-test { border-color:var(--primary); }
  .card-info { background:var(--primary-light); border-color:var(--primary-border); }
  .card-titel-row { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; flex-wrap:wrap; }
  .builder-top-actions { display:flex; gap:4px; flex-shrink:0; }
  .anbieter-grid { display:flex; gap:8px; flex-wrap:wrap; }
  .anbieter-btn { background:var(--surface2); border:1px solid var(--border); color:var(--text); padding:6px 14px; border-radius:8px; font-size:.78rem; cursor:pointer; }
  .anbieter-btn:hover { border-color:var(--primary); color:var(--primary); }
  .anbieter-btn.aktiv { background:var(--primary); color:#fff; border-color:var(--primary); font-weight:600; }
  .form-grid { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
  .form-span2 { grid-column:1/-1; }
  .form-group { display:flex; flex-direction:column; gap:5px; }
  .form-group label { font-size:.76rem; color:var(--text2); font-weight:500; }
  .form-group input,.form-group textarea { background:var(--surface); border:1px solid var(--border); color:var(--text); padding:8px 12px; border-radius:8px; font-size:.84rem; outline:none; font-family:inherit; width:100%; box-sizing:border-box; }
  .form-group input:focus,.form-group textarea:focus { border-color:var(--primary); }
  .form-group textarea { resize:vertical; line-height:1.6; }
  .input-row { display:flex; gap:8px; align-items:center; }
  .check-label { display:flex; align-items:center; gap:8px; font-size:.84rem; color:var(--text); cursor:pointer; }
  .check-label input { accent-color:var(--primary); }
  .auto-row { display:flex; align-items:center; justify-content:space-between; gap:16px; }
  .auto-titel { font-size:.84rem; font-weight:600; color:var(--text); margin-bottom:4px; }
  .auto-sub { font-size:.76rem; color:var(--text2); max-width:560px; line-height:1.5; }
  .status-hinweis { padding:8px 14px; border-radius:8px; font-size:.78rem; }
  .status-ok { background:#f0fdf4; border:1px solid #bbf7d0; color:#16a34a; }
  .status-inaktiv { background:var(--surface2); border:1px solid var(--border); color:var(--text2); }
  .toggle-btn { position:relative; width:44px; height:24px; border:none; border-radius:99px; cursor:pointer; padding:0; flex-shrink:0; }
  .toggle-an { background:var(--primary); }
  .toggle-aus { background:#d1d5db; }
  .toggle-thumb { position:absolute; top:3px; width:18px; height:18px; background:#fff; border-radius:50%; transition:left .2s; box-shadow:0 1px 3px rgba(0,0,0,.2); }
  .toggle-an .toggle-thumb { left:23px; }
  .toggle-aus .toggle-thumb { left:3px; }
  .variablen-bar { display:flex; align-items:center; gap:8px; flex-wrap:wrap; padding:8px 12px; background:var(--surface2); border-radius:8px; }
  .var-titel { font-size:.72rem; font-weight:600; color:var(--text2); white-space:nowrap; }
  .var-chip { background:var(--surface); border:1px solid var(--border); color:var(--primary); padding:2px 8px; border-radius:5px; font-size:.72rem; font-family:monospace; cursor:pointer; }
  .var-chip:hover { background:var(--primary); color:#fff; border-color:var(--primary); }
  .builder-layout { display:flex; gap:0; border:1px solid var(--border); border-radius:10px; overflow:hidden; min-height:500px; }
  .palette { width:220px; background:var(--surface); border-right:1px solid var(--border); padding:14px; overflow-y:auto; flex-shrink:0; }
  .palette-section-title { font-size:.66rem; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--text3); margin-bottom:8px; }
  .block-item { display:flex; align-items:center; gap:10px; padding:8px 10px; border:1px solid var(--border); border-radius:7px; cursor:pointer; background:var(--surface); margin-bottom:5px; width:100%; text-align:left; }
  .block-item:hover { border-color:var(--primary); background:var(--primary-light); }
  .block-icon { font-size:1rem; flex-shrink:0; width:28px; text-align:center; }
  .block-info { display:flex; flex-direction:column; min-width:0; }
  .block-name { font-size:.76rem; font-weight:600; color:var(--text); }
  .block-desc { font-size:.64rem; color:var(--text2); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .canvas-scroll { flex:1; overflow-y:auto; padding:24px; background:#e5e7eb; display:flex; justify-content:center; }
  :global([data-theme="dark"]) .canvas-scroll { background:#1a1e28; }
  .email-frame { width:600px; flex-shrink:0; }
  .email-canvas { background:#fff; border-radius:12px; box-shadow:0 8px 30px rgba(0,0,0,.12); min-height:300px; overflow:hidden; }
  :global([data-theme="dark"]) .email-canvas { background:#fff; }
  .email-footer { padding:20px 32px; text-align:center; font-size:.7rem; color:#999; border-top:1px solid #e5e7eb; background:#f4f5f7; border-radius:0 0 12px 12px; margin-top:8px; }
  .drop-empty { display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:300px; color:var(--text3); font-size:.85rem; text-align:center; padding:40px; }
  .drop-empty-icon { font-size:2.5rem; margin-bottom:12px; opacity:.3; }
  .canvas-block { position:relative; cursor:pointer; outline:2px solid transparent; outline-offset:-2px; }
  .canvas-block:hover { outline:2px solid var(--primary); }
  .canvas-block.selected { outline:2px solid var(--primary); }
  .canvas-block-inner { position:relative; }
  .block-actions { position:absolute; top:0; right:0; display:none; gap:1px; z-index:10; background:var(--primary); border-radius:0 0 0 6px; padding:2px 3px; }
  .canvas-block:hover .block-actions,.canvas-block.selected .block-actions { display:flex; }
  .ba-btn { width:24px; height:24px; border:none; background:transparent; color:#fff; border-radius:4px; cursor:pointer; font-size:.7rem; display:flex; align-items:center; justify-content:center; }
  .ba-btn:hover { background:rgba(255,255,255,.2); }
  .b-header { padding:28px 32px; text-align:center; }
  .b-header .b-header-icon { font-size:2.2rem; margin-bottom:8px; }
  .b-header h2 { font-size:1.3rem; font-weight:700; margin:0; }
  .b-header .b-header-sub { font-size:.82rem; opacity:.85; margin-top:4px; }
  .b-text { padding:16px 32px; line-height:1.7; color:#333; white-space:pre-wrap; outline:none; min-height:40px; cursor:text; }
  .b-text:focus { background:#fffbeb; outline:1px dashed #f59e0b; outline-offset:-1px; }
  .editable-inline { outline:none; cursor:text; border-radius:3px; transition:background 0.15s; }
  .editable-inline:hover { background:rgba(99,102,241,0.06); }
  .editable-inline:focus { background:#fffbeb; outline:1px dashed #f59e0b; outline-offset:2px; }
  .b-infobox { margin:12px 32px; padding:14px 18px; border-radius:8px; font-size:.82rem; line-height:1.6; border-left:4px solid; }
  .b-infobox.style-blue { background:#eff6ff; border-color:#2563eb; color:#1e40af; }
  .b-infobox.style-green { background:#f0fdf4; border-color:#10b981; color:#166534; }
  .b-infobox.style-yellow { background:#fffbeb; border-color:#f59e0b; color:#92400e; }
  .b-infobox.style-red { background:#fef2f2; border-color:#ef4444; color:#991b1b; }
  .b-amount { margin:16px 32px; padding:20px; text-align:center; border-radius:10px; border-left:4px solid; }
  .amount-label { font-size:.76rem; opacity:.7; margin-bottom:4px; }
  .amount-value { font-size:1.8rem; font-weight:700; }
  .amount-sub { font-size:.72rem; opacity:.6; margin-top:4px; }
  .b-button-wrap { padding:16px 32px; text-align:center; }
  .b-button { display:inline-block; padding:13px 36px; font-weight:700; font-size:.88rem; cursor:default; }
  .b-divider { padding:8px 32px; }
  .b-divider hr { border:none; height:1px; background:#e5e7eb; }
  .b-divider.style-bold hr { height:2px; }
  .b-divider.style-colored hr { height:2px; background:var(--primary); }
  .b-spacer { background:transparent; }
  .b-image { padding:8px 32px; }
  .b-image img { max-width:100%; height:auto; border-radius:8px; }
  .img-placeholder { background:#f7f8fa; border:2px dashed #e5e7eb; border-radius:8px; padding:28px; color:#999; font-size:.8rem; text-align:center; }
  .b-signature { margin:8px 32px; padding:16px 0; border-top:1px solid #e5e7eb; font-size:.8rem; color:#555; line-height:1.5; }
  .b-signature strong { color:#1a2233; font-size:.86rem; }
  .b-signature img { border-radius:4px; }
  .b-columns { display:flex; gap:16px; padding:12px 32px; }
  .b-columns .col { flex:1; padding:14px; background:#f7f8fa; border-radius:8px; border:1px dashed #e5e7eb; font-size:.8rem; color:#666; min-height:50px; }
  .props-panel { width:260px; background:var(--surface); border-left:1px solid var(--border); overflow-y:auto; flex-shrink:0; }
  .props-header { padding:16px; border-bottom:1px solid var(--border); }
  .props-title { font-size:.85rem; font-weight:700; }
  .props-empty { padding:40px 18px; text-align:center; color:var(--text3); font-size:.8rem; }
  .props-section { padding:14px 16px; border-bottom:1px solid var(--border); display:flex; flex-direction:column; gap:10px; }
  .ps-title { font-size:.68rem; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--text3); }
  .prop-row { display:flex; flex-direction:column; gap:4px; }
  .prop-row label { font-size:.72rem; font-weight:500; color:var(--text2); }
  .prop-row input,.props-section textarea { width:100%; padding:7px 10px; border:1px solid var(--border); border-radius:6px; font-size:.8rem; color:var(--text); background:var(--surface); outline:none; font-family:inherit; box-sizing:border-box; }
  .prop-row input:focus,.props-section textarea:focus { border-color:var(--primary); }
  .props-section textarea { resize:vertical; min-height:50px; line-height:1.5; }
  .prop-hint { font-size:.66rem; color:var(--text3); }
  .color-row { display:flex; gap:6px; flex-wrap:wrap; }
  .color-swatch { width:28px; height:28px; border-radius:6px; border:2px solid transparent; cursor:pointer; }
  .color-swatch:hover { transform:scale(1.15); border-color:var(--text); }
  .color-swatch.active { border-color:var(--text); box-shadow:0 0 0 2px var(--surface),0 0 0 4px var(--text); }
  .size-btns,.divider-btns { display:flex; gap:4px; flex-wrap:wrap; }
  .btn-active { background:var(--primary) !important; color:#fff !important; border-color:var(--primary) !important; }
  .html-code-area { font-family:'Courier New',monospace; font-size:.78rem; line-height:1.5; min-height:200px; resize:vertical; background:var(--surface2); border:1px solid var(--border); border-radius:8px; color:var(--text); padding:14px; width:100%; box-sizing:border-box; }
  .vorschau-wrap { border:1px solid var(--border); border-radius:10px; overflow:hidden; background:#fff; }
  .vorschau-header { padding:12px 16px; background:var(--surface2); border-bottom:1px solid var(--border); font-size:.8rem; color:var(--text2); display:flex; flex-direction:column; gap:4px; }
  .vorschau-label { font-weight:600; }
  .vorschau-canvas { padding:0; background:#e5e7eb; display:flex; justify-content:center; }
  .vorschau-canvas :global(img) { max-width:100%; height:auto; }
  .test-row { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
  .test-row input { background:var(--surface); border:1px solid var(--border); color:var(--text); padding:8px 12px; border-radius:8px; font-size:.84rem; outline:none; }
  .test-row input:focus { border-color:var(--primary); }
  .test-result { padding:10px 14px; border-radius:8px; font-size:.8rem; margin-top:4px; }
  .test-ok { background:#f0fdf4; border:1px solid #bbf7d0; color:#15803d; }
  .test-fehler { background:#fef2f2; border:1px solid #fecaca; color:#dc2626; }
  .folders-list { display:flex; flex-wrap:wrap; gap:6px; padding:10px 12px; background:var(--surface2); border-radius:8px; align-items:center; }
  .folders-titel { font-size:.72rem; font-weight:600; color:var(--text2); }
  .folder-chip { background:var(--surface); border:1px solid var(--border); color:var(--text); padding:2px 8px; border-radius:5px; font-size:.7rem; font-family:monospace; }
  .vorschau-box { background:var(--surface2); border:1px solid var(--border); border-radius:10px; padding:16px 18px; display:flex; flex-direction:column; gap:6px; }
  .vorschau-meta { display:flex; gap:10px; font-size:.8rem; }
  .vorschau-trenner { height:1px; background:var(--border); margin:8px 0; }
  .vorschau-body { white-space:pre-wrap; font-size:.84rem; color:var(--text); line-height:1.6; }
  .info-liste { margin:0; padding-left:18px; display:flex; flex-direction:column; gap:5px; }
  .info-liste li { font-size:.78rem; color:var(--text2); line-height:1.5; }
  .info-liste code { background:var(--surface); padding:1px 5px; border-radius:4px; font-size:.76rem; color:var(--primary); border:1px solid var(--border); }
  .modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,.5); z-index:1000; display:flex; align-items:center; justify-content:center; padding:20px; }
  .modal-box { background:var(--surface); border-radius:14px; padding:28px; box-shadow:0 20px 60px rgba(0,0,0,.3); width:100%; }
  .modal-title { font-size:1.1rem; font-weight:700; color:var(--text); margin-bottom:4px; }
  .template-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:12px; }
  .template-card { display:flex; flex-direction:column; align-items:center; gap:8px; padding:20px 14px; background:var(--surface2); border:1px solid var(--border); border-radius:10px; cursor:pointer; text-align:center; }
  .template-card:hover { border-color:var(--primary); transform:translateY(-2px); }
  .template-icon { font-size:1.8rem; }
  .template-name { font-size:.84rem; font-weight:600; color:var(--text); }
  .template-desc { font-size:.7rem; color:var(--text2); }
  .btn-primary { background:var(--primary); color:#fff; border:none; padding:8px 16px; border-radius:8px; font-size:.82rem; cursor:pointer; font-weight:600; }
  .btn-primary:hover:not(:disabled) { filter:brightness(1.08); }
  .btn-primary:disabled { opacity:.6; cursor:not-allowed; }
  .btn-ghost { background:transparent; border:1px solid var(--border); color:var(--text2); padding:7px 12px; border-radius:8px; font-size:.82rem; cursor:pointer; }
  .btn-ghost:hover { border-color:var(--primary); color:var(--primary); }
  .btn-sm { padding:5px 10px; font-size:.78rem; }
  @media(max-width:900px) { .builder-layout { flex-direction:column; } .palette { width:100%; border-right:none; border-bottom:1px solid var(--border); display:flex; flex-wrap:wrap; gap:6px; padding:10px; } .palette-section-title { width:100%; } .canvas-scroll { padding:16px; } .email-frame { width:100%; } .props-panel { width:100%; border-left:none; border-top:1px solid var(--border); } }
  @media(max-width:600px) { .form-grid { grid-template-columns:1fr; } .form-span2 { grid-column:1; } .template-grid { grid-template-columns:1fr; } }
</style>
