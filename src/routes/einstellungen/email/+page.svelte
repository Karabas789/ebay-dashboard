<script>
  import { onMount } from 'svelte';
  import { currentUser, showToast } from '$lib/stores.js';
  import { apiCall } from '$lib/api.js';
  import { goto } from '$app/navigation';

  // ═══════════════════════════════════════════════════════
  // Tab-Switch
  // ═══════════════════════════════════════════════════════
  let tab = $state('versand');

  // ═══════════════════════════════════════════════════════
  // VERSAND (SMTP)
  // ═══════════════════════════════════════════════════════
  let speichertLaeuft = $state(false);
  let testLaeuft = $state(false);
  let configLaeuft = $state(false);

  let cfg = $state({
    smtp_host: '',
    smtp_port: 587,
    smtp_user: '',
    smtp_pass: '',
    smtp_secure: false,
    absender_name: '',
    absender_email: '',
    betreff_vorlage: 'Ihre Rechnung {{rechnung_nr}}',
    text_vorlage: '',
    auto_versand: false,
  });

  const signaturHtml = '<div style="margin-top:24px;padding-top:16px;border-top:1px solid #ddd;font-family:Arial,sans-serif;font-size:13px;color:#333;line-height:1.4">' +
    '<strong>Import &amp; Produkte Vertrieb</strong><br>' +
    'Inh. Oxana Dubs<br>' +
    'Auf der Schläfe 1<br>' +
    '57078 Siegen<br>' +
    'USt-ID: DE815720228<br>' +
    '📞 +49 271 50149974<br>' +
    '📧 <a href="mailto:ov-shop@mail.de" style="color:#333">ov-shop@mail.de</a><br>' +
    '<img src="https://assets.zyrosite.com/sKFGVgrqCU2eVSWO/bildschirmfoto-2024-10-23-um-20.44.12-KsnpbGM6T6pk07Fh.png" width="120" height="50" style="max-width:100%;height:auto;display:block;margin-top:8px" alt="OV-Software Logo">' +
    '</div>';

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

  const variablen = [
    { key: '{{rechnung_nr}}', beschreibung: 'Rechnungsnummer' },
    { key: '{{kaeufer_name}}', beschreibung: 'Name des Käufers' },
    { key: '{{datum}}', beschreibung: 'Rechnungsdatum' },
    { key: '{{brutto_betrag}}', beschreibung: 'Bruttobetrag' },
    { key: '{{firmenname}}', beschreibung: 'Eigener Firmenname' },
  ];

  // Block-Defaults
  const blockDefaults = {
    header: { type:'header', icon:'✉️', title:'Ihre Rechnung', subtitle:'', bgColor:'#6366f1', textColor:'#ffffff', borderRadius:true },
    text: { type:'text', content:'<p>Sehr geehrte(r) {{kaeufer_name}},</p><p>anbei erhalten Sie Ihre Rechnung {{rechnung_nr}} vom {{datum}} als PDF-Anhang.</p>' },
    infobox: { type:'infobox', style:'blue', content:'<strong>Hinweis:</strong> Hier können Sie einen wichtigen Hinweis einfügen.' },
    amount: { type:'amount', label:'Rechnungsbetrag', value:'{{brutto_betrag}} EUR', sublabel:'', bgColor:'#eff6ff', accentColor:'#2563eb' },
    button: { type:'button', text:'Rechnung ansehen', url:'https://example.com', bgColor:'#6366f1', textColor:'#ffffff', borderRadius:'8' },
    divider: { type:'divider', style:'normal' },
    spacer: { type:'spacer', height:24 },
    image: { type:'image', url:'', alt:'Bild', maxWidth:'100%' },
    signature: { type:'signature', name:'{{firmenname}}', details:'Auf der Schläfe 1\n57078 Siegen\nUSt-ID: DE815720228', email:'ov-shop@mail.de', phone:'+49 271 50149974' },
    columns: { type:'columns', left:'Linke Spalte', right:'Rechte Spalte' }
  };

  const headerFarben = ['#6366f1','#2563eb','#10b981','#f59e0b','#ef4444','#1a2233','#7c3aed','#ec4899','#0891b2'];
  const accentFarben = ['#2563eb','#10b981','#6366f1','#f59e0b','#ef4444','#1a2233'];
  const buttonFarben = ['#6366f1','#2563eb','#10b981','#f59e0b','#ef4444','#1a2233','#ec4899'];

  // ═══════════════════════════════════════════════════════
  // WYSIWYG EDITOR (für Text & Infobox Blöcke)
  // ═══════════════════════════════════════════════════════
  let richEditorEl = $state(null);
  let richEditorBlockId = $state(null);
  let showColorPicker = $state(false);
  let showLinkDialog = $state(false);
  let linkInputUrl = $state('');
  let showHtmlMode = $state(false);
  let htmlRawText = $state('');

  const editorTextFarben = [
    '#000000','#333333','#666666','#999999',
    '#1d4ed8','#2563eb','#3b82f6','#60a5fa',
    '#dc2626','#ef4444','#16a34a','#22c55e',
    '#d97706','#f59e0b','#9333ea','#a855f7',
  ];

  const fontSizes = [
    { label:'Klein', value:'2' },
    { label:'Normal', value:'3' },
    { label:'Mittel', value:'4' },
    { label:'Groß', value:'5' },
    { label:'Sehr groß', value:'6' },
  ];

  function richEditorCmd(cmd, val) {
    richEditorEl?.focus();
    document.execCommand(cmd, false, val || null);
    syncRichEditor();
  }

  function syncRichEditor() {
    if (richEditorEl && richEditorBlockId) {
      updateBlock(richEditorBlockId, 'content', richEditorEl.innerHTML);
    }
  }

  function initRichEditor(blockId, content) {
    richEditorBlockId = blockId;
    showHtmlMode = false;
    showColorPicker = false;
    showLinkDialog = false;
    // Editor wird über $effect befüllt
    setTimeout(() => {
      if (richEditorEl) {
        richEditorEl.innerHTML = content || '';
      }
    }, 30);
  }

  function setEditorColor(color) {
    richEditorCmd('foreColor', color);
    showColorPicker = false;
  }

  function insertEditorLink() {
    if (!linkInputUrl.trim()) return;
    let url = linkInputUrl.trim();
    if (!/^https?:\/\//i.test(url)) url = 'https://' + url;
    richEditorCmd('createLink', url);
    linkInputUrl = '';
    showLinkDialog = false;
  }

  function toggleHtmlMode() {
    if (showHtmlMode) {
      // HTML → Visual: übernehmen
      if (richEditorBlockId) {
        updateBlock(richEditorBlockId, 'content', htmlRawText);
      }
      if (richEditorEl) richEditorEl.innerHTML = htmlRawText;
      showHtmlMode = false;
    } else {
      // Visual → HTML
      htmlRawText = selectedBlock?.content || '';
      showHtmlMode = true;
    }
  }

  function insertVariable(key) {
    if (showHtmlMode) {
      htmlRawText += key;
      if (richEditorBlockId) updateBlock(richEditorBlockId, 'content', htmlRawText);
      return;
    }
    richEditorEl?.focus();
    document.execCommand('insertHTML', false, '<span>' + key + '</span>');
    syncRichEditor();
  }

  const bausteinListe = [
    { type:'header', icon:'🎨', name:'Kopfbereich', desc:'Farbiger Banner mit Titel', group:'struktur' },
    { type:'text', icon:'📝', name:'Textblock', desc:'Absatz mit HTML', group:'struktur' },
    { type:'divider', icon:'➖', name:'Trennlinie', desc:'Horizontal, farbig oder dezent', group:'struktur' },
    { type:'spacer', icon:'↕️', name:'Abstand', desc:'Vertikaler Leerraum', group:'struktur' },
    { type:'columns', icon:'▥', name:'2 Spalten', desc:'Nebeneinander-Layout', group:'struktur' },
    { type:'infobox', icon:'📋', name:'Info-Box', desc:'Farbiger Hinweis-Kasten', group:'inhalt' },
    { type:'amount', icon:'💰', name:'Betrag-Box', desc:'Hervorgehobener Betrag', group:'inhalt' },
    { type:'button', icon:'🔘', name:'Button', desc:'Aktion mit Link', group:'inhalt' },
    { type:'image', icon:'🖼️', name:'Bild', desc:'Logo oder Grafik (URL)', group:'inhalt' },
    { type:'signature', icon:'📇', name:'Signatur', desc:'Firmendaten & Kontakt', group:'inhalt' },
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

  function selectBlock(id) {
    selectedBlockId = selectedBlockId === id ? null : id;
    showColorPicker = false;
    showLinkDialog = false;
    showHtmlMode = false;
    // Init rich editor wenn Text oder Infobox
    if (selectedBlockId) {
      const block = blocks.find(b => b.id === selectedBlockId);
      if (block && (block.type === 'text' || block.type === 'infobox')) {
        initRichEditor(block.id, block.content);
      } else {
        richEditorBlockId = null;
      }
    } else {
      richEditorBlockId = null;
    }
  }

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

  // ═══════════════════════════════════════════════════════
  // TEMPLATE LADEN
  // ═══════════════════════════════════════════════════════
  function loadTemplate(key) {
    blocks = [];
    blockIdCounter = 0;
    selectedBlockId = null;

    if (key === 'rechnung') {
      addBlock('header'); updateBlock(blocks[blocks.length-1].id, 'title', 'Ihre Rechnung'); updateBlock(blocks[blocks.length-1].id, 'subtitle', '{{firmenname}}'); updateBlock(blocks[blocks.length-1].id, 'icon', '📄');
      addBlock('text');
      addBlock('amount');
      addBlock('text'); updateBlock(blocks[blocks.length-1].id, 'content', '<p>Vielen Dank für Ihren Einkauf!</p><p>Beste Grüße</p>');
      addBlock('divider');
      addBlock('signature');
    } else if (key === 'bestätigung') {
      addBlock('header'); updateBlock(blocks[blocks.length-1].id, 'title', 'Bestellung bestätigt'); updateBlock(blocks[blocks.length-1].id, 'icon', '🎉'); updateBlock(blocks[blocks.length-1].id, 'bgColor', '#10b981');
      addBlock('text'); updateBlock(blocks[blocks.length-1].id, 'content', '<p>Hallo {{kaeufer_name}},</p><p>Ihre Bestellung wurde erfolgreich aufgenommen.</p>');
      addBlock('infobox'); updateBlock(blocks[blocks.length-1].id, 'style', 'green'); updateBlock(blocks[blocks.length-1].id, 'content', '<strong>Bestellnummer:</strong> {{rechnung_nr}}<br>Betrag: {{brutto_betrag}} EUR');
      addBlock('text'); updateBlock(blocks[blocks.length-1].id, 'content', '<p>Viel Spaß mit dem Produkt!</p>');
      addBlock('signature');
    } else if (key === 'schlicht') {
      addBlock('text'); updateBlock(blocks[blocks.length-1].id, 'content', '<p>Sehr geehrte(r) {{kaeufer_name}},</p><p>anbei erhalten Sie Ihre Rechnung {{rechnung_nr}} vom {{datum}} als PDF-Anhang.</p><p>Rechnungsbetrag: <strong>{{brutto_betrag}} EUR</strong></p><p>Vielen Dank für Ihren Einkauf!</p><p>Beste Grüße</p>');
      addBlock('divider');
      addBlock('signature');
    } else if (key === 'key') {
      addBlock('header'); updateBlock(blocks[blocks.length-1].id, 'title', 'Ihr Aktivierungsschlüssel'); updateBlock(blocks[blocks.length-1].id, 'subtitle', 'Vielen Dank für Ihre Bestellung'); updateBlock(blocks[blocks.length-1].id, 'icon', '✅'); updateBlock(blocks[blocks.length-1].id, 'bgColor', '#7c3aed');
      addBlock('text'); updateBlock(blocks[blocks.length-1].id, 'content', '<p>Sehr geehrte(r) {{kaeufer_name}},</p><p>vielen Dank für Ihre Bestellung. Hiermit übersenden wir Ihnen einen Produktschlüssel:</p>');
      addBlock('infobox'); updateBlock(blocks[blocks.length-1].id, 'content', '<strong>Produktname</strong><br><br>Ihr persönlicher Schlüssel:<br><span style="font-size:1.3em;font-family:monospace;color:#6366f1;font-weight:700">XXXX-XXXX-XXXX-XXXX</span><br><br>💡 Tipp: Kopieren Sie den Key und bewahren Sie diese E-Mail sicher auf.');
      addBlock('text'); updateBlock(blocks[blocks.length-1].id, 'content', '<p>Sollten Sie weitere Fragen haben, stehen wir Ihnen gerne zur Verfügung.</p><p><strong>Schöne Grüße</strong></p>');
      addBlock('signature');
    }
    selectedBlockId = null;
    templateModalOffen = false;
  }

  // ═══════════════════════════════════════════════════════
  // HTML EXPORT (Block → Email-HTML)
  // ═══════════════════════════════════════════════════════
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
        return `<div style="padding:16px 32px;font-size:15px;line-height:1.7;color:#333">${b.content}</div>`;
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
      case 'image':
        if (!b.url) return '';
        return `<div style="padding:8px 32px;text-align:center"><img src="${b.url}" alt="${b.alt}" style="max-width:${b.maxWidth};height:auto;border-radius:8px"></div>`;
      case 'signature': {
        const det = (b.details || '').replace(/\n/g, '<br>');
        return `<div style="margin:8px 32px;padding:16px 0;border-top:1px solid #e2e5ea;font-size:13px;color:#555;line-height:1.5">` +
          `<strong style="font-size:14px;color:#1a1d23">${b.name}</strong><br>${det}<br>` +
          (b.phone ? `📞 ${b.phone}<br>` : '') +
          (b.email ? `📧 ${b.email}` : '') +
          `</div>`;
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
    let html = '<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#ffffff;border-radius:12px;overflow:hidden">';
    blocks.forEach(b => { html += blockToEmailHtml(b); });
    html += '</div>';
    html += '<div style="text-align:center;padding:16px;font-size:12px;color:#999">Dieses Schreiben wurde automatisch erstellt, bitte nicht darauf antworten.<br>© 2026 {{firmenname}}</div>';
    return html;
  }

  function vorschauHtml() {
    let h = generateFullHtml();
    h = h.replace(/\{\{rechnung_nr\}\}/g, 'RE-2026-00042')
         .replace(/\{\{kaeufer_name\}\}/g, 'Max Mustermann')
         .replace(/\{\{datum\}\}/g, '21.04.2026')
         .replace(/\{\{brutto_betrag\}\}/g, '49,99')
         .replace(/\{\{firmenname\}\}/g, 'Import & Produkte Vertrieb');
    return h;
  }

  // ═══════════════════════════════════════════════════════
  // BLOCKS → HTML Konvertierung für Speichern + Laden
  // ═══════════════════════════════════════════════════════
  function blocksToJson() {
    return JSON.stringify(blocks);
  }

  function jsonToBlocks(json) {
    try {
      const parsed = JSON.parse(json);
      if (Array.isArray(parsed) && parsed.length > 0 && parsed[0].type) {
        blocks = parsed;
        blockIdCounter = parsed.length + 10;
        return true;
      }
    } catch(e) { /* nicht JSON */ }
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

  function wendeAnbieterAn(anbieter) {
    cfg = { ...cfg, smtp_host: anbieter.host, smtp_port: anbieter.port, smtp_secure: anbieter.secure };
    showToast('Anbieter gewählt: ' + anbieter.name);
  }

  // ═══════════════════════════════════════════════════════
  // API-CALLS: Laden / Speichern / Test
  // ═══════════════════════════════════════════════════════
  async function ladeVersandConfig() {
    if (!$currentUser) return;
    configLaeuft = true;
    try {
      const data = await apiCall('email-config-laden', { user_id: $currentUser.id });
      if (data?.config) {
        let vorlage = data.config.text_vorlage || '';
        cfg = {
          smtp_host:       data.config.smtp_host       || '',
          smtp_port:       data.config.smtp_port       || 587,
          smtp_user:       data.config.smtp_user       || '',
          smtp_pass:       '',
          smtp_secure:     data.config.smtp_secure     || false,
          absender_name:   data.config.absender_name   || '',
          absender_email:  data.config.absender_email  || '',
          betreff_vorlage: data.config.betreff_vorlage || cfg.betreff_vorlage,
          text_vorlage:    vorlage,
          auto_versand:    data.config.auto_versand    || false,
        };
        // Versuche Blocks aus JSON zu laden
        if (vorlage && !jsonToBlocks(vorlage)) {
          // Alte HTML-Vorlage → als einzelnen Text-Block laden
          blocks = [{ type:'text', content: vorlage, id:'b_1' }];
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
      const htmlVorlage = generateFullHtml();
      await apiCall('email-config-speichern', { user_id: $currentUser.id, ...cfg, text_vorlage: blocksToJson() });
      showToast(cfg.auto_versand ? '✅ Auto-Versand aktiviert' : 'Auto-Versand deaktiviert');
    } catch(e) {
      cfg.auto_versand = !cfg.auto_versand;
      showToast('Fehler: ' + e.message);
    }
  }

  async function speichern() {
    if (!cfg.smtp_host || !cfg.smtp_user) {
      showToast('Bitte SMTP-Host und Benutzername ausfüllen.'); return;
    }
    speichertLaeuft = true;
    try {
      // Speichere Blocks als JSON in text_vorlage (für den Builder)
      // UND generiere email_html für den tatsächlichen Versand
      const emailHtml = generateFullHtml();
      await apiCall('email-config-speichern', {
        user_id: $currentUser.id,
        ...cfg,
        text_vorlage: blocksToJson(),
        email_html: emailHtml,
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
    if (!cfg.smtp_host || !cfg.smtp_user) {
      showToast('Bitte zuerst SMTP-Host und Benutzername ausfüllen.'); return;
    }
    testLaeuft = true;
    testStatus = null;
    testNachricht = '';
    try {
      const emailHtml = generateFullHtml();
      await apiCall('email-config-speichern', { user_id: $currentUser.id, ...cfg, text_vorlage: blocksToJson(), email_html: emailHtml });
      await apiCall('smtp-testen', { user_id: $currentUser.id, to_email: testEmail });
      testStatus = 'success';
      testNachricht = 'Test-E-Mail erfolgreich gesendet an ' + testEmail;
      showToast('✅ Test-E-Mail gesendet');
    } catch(e) {
      testStatus = 'error';
      testNachricht = e.message || 'Verbindung fehlgeschlagen.';
      showToast('Fehler: ' + e.message);
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

  let imap = $state({
    email:'', host:'imap.hostinger.com', port:993, user_name:'', pass:'',
    folder:'INBOX', processed_folder:'Rechnungen', filter_betreff:'', aktiv:false
  });

  let imapConfigExistiert = $state(false);
  let lastCheck = $state(null);
  let lastError = $state(null);

  const imapAnbieter = [
    { name:'Hostinger', host:'imap.hostinger.com', port:993, hinweis:'E-Mail-Passwort aus Hostinger hPanel' },
    { name:'Gmail', host:'imap.gmail.com', port:993, hinweis:'App-Passwort verwenden' },
    { name:'Outlook', host:'outlook.office365.com', port:993, hinweis:'Microsoft-Konto-Passwort' },
    { name:'IONOS', host:'imap.ionos.de', port:993, hinweis:'E-Mail-Passwort verwenden' },
    { name:'Strato', host:'imap.strato.de', port:993, hinweis:'E-Mail-Passwort verwenden' },
    { name:'GMX', host:'imap.gmx.net', port:993, hinweis:'GMX-Passwort verwenden' },
  ];

  function wendeImapAnbieterAn(a) { imap = { ...imap, host:a.host, port:a.port }; showToast('Anbieter: ' + a.name); }

  async function ladeImapConfig() {
    if (!$currentUser) return;
    imapLaeuft = true;
    try {
      const res = await apiCall('imap-config', { user_id:$currentUser.id, action:'load' });
      if (res?.config) {
        imap = { email:res.config.email||'', host:res.config.host||'imap.hostinger.com', port:res.config.port||993, user_name:res.config.user_name||'', pass:'', folder:res.config.folder||'INBOX', processed_folder:res.config.processed_folder||'Rechnungen', filter_betreff:res.config.filter_betreff||'', aktiv:res.config.aktiv||false };
        imapConfigExistiert = true;
        lastCheck = res.config.last_check || null;
        lastError = res.config.last_error || null;
      } else { imapConfigExistiert = false; }
    } catch(e) { console.warn('IMAP-Config nicht geladen:', e?.message); }
    finally { imapLaeuft = false; }
  }

  async function imapSpeichern() {
    if (!imap.host || !imap.user_name) { showToast('Bitte IMAP-Host und Benutzername ausfüllen.'); return; }
    imapSpeichertLaeuft = true;
    try {
      await apiCall('imap-config', { user_id:$currentUser.id, action:'save', ...imap });
      showToast('✅ IMAP-Einstellungen gespeichert');
      imapConfigExistiert = true; imap.pass = '';
    } catch(e) { showToast('Fehler: ' + e.message); }
    finally { imapSpeichertLaeuft = false; }
  }

  async function imapTesten() {
    if (!imap.host || !imap.user_name) { showToast('Bitte IMAP-Host und Benutzername ausfüllen.'); return; }
    if (!imap.pass) { showToast('Bitte Passwort zum Testen eingeben.'); return; }
    imapTestLaeuft = true; imapTestStatus = null; imapTestNachricht = ''; imapTestFolders = [];
    try {
      const res = await apiCall('imap-config', { user_id:$currentUser.id, action:'test', host:imap.host, port:imap.port, user_name:imap.user_name, pass:imap.pass, folder:imap.folder, processed_folder:imap.processed_folder });
      if (res?.success) {
        imapTestStatus = 'success';
        let msg = '✅ Verbindung OK';
        if (typeof res.messages_new === 'number') msg += ' — ' + res.messages_new + ' ungelesene Mails';
        if (res.processed_folder_created) msg += ' — Ordner "' + res.processed_folder + '" angelegt';
        imapTestNachricht = msg;
        imapTestFolders = res.folders || [];
      } else { imapTestStatus = 'error'; imapTestNachricht = res?.error || 'Verbindung fehlgeschlagen'; imapTestFolders = res?.folders || []; }
    } catch(e) { imapTestStatus = 'error'; imapTestNachricht = e.message; }
    finally { imapTestLaeuft = false; }
  }

  async function toggleImapAktiv() {
    imap.aktiv = !imap.aktiv;
    try {
      await apiCall('imap-config', { user_id:$currentUser.id, action:'save', ...imap });
      showToast(imap.aktiv ? '✅ IMAP-Import aktiviert' : 'IMAP-Import deaktiviert');
    } catch(e) { imap.aktiv = !imap.aktiv; showToast('Fehler: ' + e.message); }
  }

  async function imapLoeschen() {
    if (!confirm('IMAP-Konfiguration wirklich löschen?')) return;
    imapLoeschenLaeuft = true;
    try {
      await apiCall('imap-config', { user_id:$currentUser.id, action:'delete' });
      showToast('✅ IMAP-Konfiguration gelöscht');
      imap = { email:'', host:'imap.hostinger.com', port:993, user_name:'', pass:'', folder:'INBOX', processed_folder:'Rechnungen', filter_betreff:'', aktiv:false };
      imapConfigExistiert = false; lastCheck = null; lastError = null;
    } catch(e) { showToast('Fehler: ' + e.message); }
    finally { imapLoeschenLaeuft = false; }
  }

  function formatDatum(iso) { if (!iso) return '—'; try { return new Date(iso).toLocaleString('de-DE'); } catch { return iso; } }

  // ═══════════════════════════════════════════════════════
  // KAUF-NACHRICHT
  // ═══════════════════════════════════════════════════════
  let kaufLaeuft = $state(false);
  let kaufSpeichertLaeuft = $state(false);
  let kaufVorlageRef = $state(null);

  let kauf = $state({
    kauf_nachricht_aktiv: false,
    kauf_nachricht_betreff: 'Danke für deinen Kauf!',
    kauf_nachricht_vorlage: 'Hallo {{buyer}},\n\nvielen Dank für deinen Kauf von "{{artikel}}" (Bestellung {{order_id}}).\n\nWir versenden die Ware schnellstmöglich.\n\nViele Grüße'
  });

  const kaufPlatzhalter = [
    { key:'{{buyer}}', beschreibung:'eBay-Username' },
    { key:'{{artikel}}', beschreibung:'Artikelname' },
    { key:'{{menge}}', beschreibung:'Menge' },
    { key:'{{preis}}', beschreibung:'Stückpreis' },
    { key:'{{order_id}}', beschreibung:'Bestell-ID' }
  ];

  function kaufPlatzhalterEinfuegen(key) {
    const ta = kaufVorlageRef;
    if (!ta) { kauf.kauf_nachricht_vorlage = (kauf.kauf_nachricht_vorlage || '') + key; return; }
    const start = ta.selectionStart, end = ta.selectionEnd;
    kauf.kauf_nachricht_vorlage = (kauf.kauf_nachricht_vorlage||'').slice(0,start) + key + (kauf.kauf_nachricht_vorlage||'').slice(end);
    setTimeout(() => { ta.focus(); ta.selectionStart = ta.selectionEnd = start + key.length; }, 0);
  }

  function kaufVorschauText() {
    return (kauf.kauf_nachricht_vorlage||'').replace(/\{\{buyer\}\}/gi,'max_mustermann').replace(/\{\{artikel\}\}/gi,'Windows 11 Pro').replace(/\{\{menge\}\}/gi,'1').replace(/\{\{preis\}\}/gi,'19,99 €').replace(/\{\{order_id\}\}/gi,'12-34567-89012');
  }

  function kaufVorschauBetreff() {
    return (kauf.kauf_nachricht_betreff||'').replace(/\{\{buyer\}\}/gi,'max_mustermann').replace(/\{\{artikel\}\}/gi,'Windows 11 Pro').replace(/\{\{order_id\}\}/gi,'12-34567-89012');
  }

  async function ladeKaufConfig() {
    if (!$currentUser) return;
    kaufLaeuft = true;
    try {
      const data = await apiCall('kauf-nachricht-config', { action:'load', user_id:$currentUser.id });
      if (data?.config) {
        let vorlage = data.config.kauf_nachricht_vorlage || kauf.kauf_nachricht_vorlage;
        if (vorlage?.includes('\\n')) vorlage = vorlage.replace(/\\n/g, '\n');
        kauf = { kauf_nachricht_aktiv: data.config.kauf_nachricht_aktiv ?? false, kauf_nachricht_betreff: data.config.kauf_nachricht_betreff || kauf.kauf_nachricht_betreff, kauf_nachricht_vorlage: vorlage };
      }
    } catch(e) { console.warn('Kauf-Config nicht geladen:', e?.message); }
    finally { kaufLaeuft = false; }
  }

  async function toggleKaufNachricht() {
    kauf.kauf_nachricht_aktiv = !kauf.kauf_nachricht_aktiv;
    try {
      await apiCall('kauf-nachricht-config', { action:'save', user_id:$currentUser.id, ...kauf });
      showToast(kauf.kauf_nachricht_aktiv ? '✅ Kauf-Nachricht aktiviert' : 'Kauf-Nachricht deaktiviert');
    } catch(e) { kauf.kauf_nachricht_aktiv = !kauf.kauf_nachricht_aktiv; showToast('Fehler: ' + e.message); }
  }

  async function kaufSpeichern() {
    if (!kauf.kauf_nachricht_betreff?.trim()) { showToast('Bitte Betreff eingeben.'); return; }
    if (!kauf.kauf_nachricht_vorlage?.trim()) { showToast('Bitte Text eingeben.'); return; }
    kaufSpeichertLaeuft = true;
    try {
      await apiCall('kauf-nachricht-config', { action:'save', user_id:$currentUser.id, ...kauf });
      showToast('✅ Kauf-Nachricht gespeichert');
    } catch(e) { showToast('Fehler: ' + e.message); }
    finally { kaufSpeichertLaeuft = false; }
  }

  // ═══════════════════════════════════════════════════════
  // INIT
  // ═══════════════════════════════════════════════════════
  onMount(async () => {
    testEmail = $currentUser?.email || '';
    await ladeVersandConfig();
    await ladeImapConfig();
    await ladeKaufConfig();
  });

  // Selected block helper — Funktion statt $derived für stabilen Zugriff
  function getSelectedBlock() {
    if (!selectedBlockId) return null;
    return blocks.find(b => b.id === selectedBlockId) || null;
  }
  // Reactive derived
  let selectedBlock = $derived(getSelectedBlock());
</script>

<div class="page-container">
  <div class="page-hdr">
    <div class="hdr-left">
      <button class="btn-back" onclick={() => goto('/einstellungen')}>← Zurück</button>
      <div>
        <div class="page-title">📧 E-Mail</div>
        <div class="page-sub">Rechnungen versenden, empfangen und eBay-Nachrichten</div>
      </div>
    </div>
    {#if tab === 'versand'}
      <button class="btn-primary" onclick={speichern} disabled={speichertLaeuft}>
        {speichertLaeuft ? '⏳ Speichert…' : '💾 Speichern'}
      </button>
    {:else if tab === 'empfang'}
      <button class="btn-primary" onclick={imapSpeichern} disabled={imapSpeichertLaeuft}>
        {imapSpeichertLaeuft ? '⏳ Speichert…' : '💾 Speichern'}
      </button>
    {:else}
      <button class="btn-primary" onclick={kaufSpeichern} disabled={kaufSpeichertLaeuft}>
        {kaufSpeichertLaeuft ? '⏳ Speichert…' : '💾 Speichern'}
      </button>
    {/if}
  </div>

  <!-- TABS -->
  <div class="tab-bar">
    <button class="tab-btn" class:active={tab === 'versand'} onclick={() => tab = 'versand'}>📤 Versand (SMTP)</button>
    <button class="tab-btn" class:active={tab === 'empfang'} onclick={() => tab = 'empfang'}>
      📥 Empfang (IMAP) {#if imap.aktiv}<span class="tab-badge-grn">aktiv</span>{/if}
    </button>
    <button class="tab-btn" class:active={tab === 'kauf'} onclick={() => tab = 'kauf'}>
      💬 Kauf-Nachricht {#if kauf.kauf_nachricht_aktiv}<span class="tab-badge-grn">aktiv</span>{/if}
    </button>
  </div>

  <!-- ═══════════════════════════════════════════════ -->
  <!-- TAB: VERSAND                                     -->
  <!-- ═══════════════════════════════════════════════ -->
  {#if tab === 'versand'}
    {#if configLaeuft}
      <div class="config-laedt"><span class="spinner"></span> Einstellungen werden geladen…</div>
    {/if}

    <div class="card">
      <div class="card-titel">⚡ Anbieter-Schnellauswahl</div>
      <div class="card-sub">Klicke auf deinen E-Mail-Anbieter</div>
      <div class="anbieter-grid">
        {#each anbieterVorlagen as a}
          <button class="anbieter-btn" class:aktiv={cfg.smtp_host === a.host && cfg.smtp_port === a.port}
            onclick={() => wendeAnbieterAn(a)} title={a.hinweis}>{a.name}</button>
        {/each}
      </div>
    </div>

    <div class="card">
      <div class="card-titel">🔌 SMTP-Verbindung</div>
      <div class="form-grid">
        <div class="form-group form-span2"><label>SMTP-Host *</label><input bind:value={cfg.smtp_host} placeholder="z. B. smtp.hostinger.com" /></div>
        <div class="form-group"><label>Port</label><input bind:value={cfg.smtp_port} type="number" /></div>
        <div class="form-group"><label>Sicherheit</label>
          <label class="check-label"><input type="checkbox" bind:checked={cfg.smtp_secure} /> SSL/TLS (Port 465)</label>
        </div>
        <div class="form-group"><label>Benutzername *</label><input bind:value={cfg.smtp_user} type="email" placeholder="deine@email.de" /></div>
        <div class="form-group"><label>Passwort</label>
          <div class="input-row">
            <input bind:value={cfg.smtp_pass} type={passwortZeigen ? 'text' : 'password'} placeholder="Passwort" style="flex:1" />
            <button class="btn-ghost btn-sm" onclick={() => passwortZeigen = !passwortZeigen}>{passwortZeigen ? '🙈' : '👁'}</button>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-titel">✉️ Absender</div>
      <div class="form-grid">
        <div class="form-group"><label>Absendername</label><input bind:value={cfg.absender_name} placeholder="Mein Shop" /></div>
        <div class="form-group"><label>Absender-E-Mail</label><input bind:value={cfg.absender_email} type="email" placeholder="(leer = SMTP-User)" /></div>
      </div>
    </div>

    <!-- E-Mail Vorlage (Verweis auf Unterseite) -->
    <div class="card">
      <div class="card-titel-row">
        <div>
          <div class="card-titel">📝 E-Mail Vorlage</div>
          <div class="card-sub">HTML-Vorlage für den Rechnungsversand</div>
        </div>
        <button class="btn-primary" onclick={() => goto('/einstellungen/email/vorlage')}>
          ✏️ Vorlage bearbeiten
        </button>
      </div>
      <div class="form-group">
        <label>Betreff</label>
        <input bind:value={cfg.betreff_vorlage} placeholder={'Ihre Rechnung {{rechnung_nr}}'} />
      </div>
      {#if blocks.length > 0}
        <div class="vorlage-preview-info">
          ✅ Vorlage vorhanden — {blocks.length} {blocks.length === 1 ? 'Baustein' : 'Bausteine'}
        </div>
      {:else}
        <div class="vorlage-preview-info vorlage-leer">
          Noch keine Vorlage erstellt — klicke auf „Vorlage bearbeiten" um loszulegen
        </div>
      {/if}
    </div>

    <!-- Auto-Versand -->
    <div class="card">
      <div class="card-titel">🤖 Automatischer Versand</div>
      <div class="auto-row">
        <div>
          <div class="auto-titel">Nach Rechnungserstellung automatisch senden</div>
          <div class="auto-sub">Wenn aktiviert, wird die Rechnung sofort per E-Mail an den Käufer gesendet — aber nur wenn eine E-Mail-Adresse vorhanden ist.</div>
        </div>
        <button class="toggle-btn" class:toggle-an={cfg.auto_versand} class:toggle-aus={!cfg.auto_versand} onclick={toggleAutoVersand}>
          <span class="toggle-thumb"></span>
        </button>
      </div>
      {#if cfg.auto_versand}
        <div class="status-hinweis status-ok">✅ Auto-Versand aktiv</div>
      {:else}
        <div class="status-hinweis status-inaktiv">⏸ Auto-Versand inaktiv — Rechnungen manuell senden</div>
      {/if}
    </div>

    <!-- Verbindung testen -->
    <div class="card card-test">
      <div class="card-titel">🧪 Verbindung testen</div>
      <div class="card-sub">Einstellungen werden gespeichert, dann wird eine Test-E-Mail gesendet.</div>
      <div class="test-row">
        <input bind:value={testEmail} type="email" placeholder="test@example.com" style="flex:1;min-width:200px" />
        <button class="btn-primary" onclick={testSenden} disabled={testLaeuft}>
          {testLaeuft ? '⏳ Sende…' : '📤 Test-E-Mail senden'}
        </button>
      </div>
      {#if testStatus === 'success'}<div class="test-result test-ok">✅ {testNachricht}</div>{/if}
      {#if testStatus === 'error'}<div class="test-result test-fehler">❌ {testNachricht}</div>{/if}
    </div>
  {/if}

  <!-- ═══════════════════════════════════════════════ -->
  <!-- TAB: EMPFANG (IMAP)                              -->
  <!-- ═══════════════════════════════════════════════ -->
  {#if tab === 'empfang'}
    {#if imapLaeuft}<div class="config-laedt"><span class="spinner"></span> IMAP-Einstellungen werden geladen…</div>{/if}

    <div class="card card-info">
      <div class="card-titel">📥 Wie funktioniert der Email-Import?</div>
      <ul class="info-liste" style="margin:0;padding-left:18px">
        <li>Alle <strong>30 Minuten</strong> werden ungelesene Mails abgeholt</li>
        <li>E-Mails mit <strong>PDF-Anhang</strong> werden von der KI analysiert</li>
        <li>Analysierte Rechnungen erscheinen unter <strong>Buchhaltung → Eingangsrechnungen → 📥 Posteingang</strong></li>
        <li>Nach Freigabe wird die Mail in den Ordner <strong>„{imap.processed_folder}"</strong> verschoben</li>
      </ul>
    </div>

    <div class="card">
      <div class="card-titel">⚡ Anbieter-Schnellauswahl</div>
      <div class="anbieter-grid">
        {#each imapAnbieter as a}
          <button class="anbieter-btn" class:aktiv={imap.host === a.host} onclick={() => wendeImapAnbieterAn(a)} title={a.hinweis}>{a.name}</button>
        {/each}
      </div>
    </div>

    <div class="card">
      <div class="card-titel">🔌 IMAP-Verbindung</div>
      <div class="form-grid">
        <div class="form-group"><label>Verarbeitungs-Email</label><input bind:value={imap.email} type="email" placeholder="belege@ai-online.cloud" /></div>
        <div class="form-group"><label>IMAP-Host *</label><input bind:value={imap.host} placeholder="imap.hostinger.com" /></div>
        <div class="form-group"><label>Port</label><input bind:value={imap.port} type="number" /></div>
        <div class="form-group"><label>Benutzername *</label><input bind:value={imap.user_name} type="email" /></div>
        <div class="form-group"><label>Passwort</label>
          <div class="input-row">
            <input bind:value={imap.pass} type={imapPasswortZeigen ? 'text' : 'password'} placeholder="Passwort" style="flex:1" />
            <button class="btn-ghost btn-sm" onclick={() => imapPasswortZeigen = !imapPasswortZeigen}>{imapPasswortZeigen ? '🙈' : '👁'}</button>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-titel">📁 Ordner</div>
      <div class="form-grid">
        <div class="form-group"><label>Eingangsordner</label><input bind:value={imap.folder} placeholder="INBOX" /></div>
        <div class="form-group"><label>Verarbeitet-Ordner</label><input bind:value={imap.processed_folder} placeholder="Rechnungen" /></div>
        <div class="form-group form-span2"><label>Betreff-Filter (optional)</label><input bind:value={imap.filter_betreff} placeholder="z.B. Rechnung — leer = alle Mails" /></div>
      </div>
    </div>

    <div class="card">
      <div class="card-titel">🤖 Automatischer Abruf</div>
      <div class="auto-row">
        <div>
          <div class="auto-titel">Alle 30 Minuten neue Mails abholen</div>
          <div class="auto-sub">Prüft das IMAP-Postfach auf neue Mails mit PDF-Anhang.</div>
        </div>
        <button class="toggle-btn" class:toggle-an={imap.aktiv} class:toggle-aus={!imap.aktiv} onclick={toggleImapAktiv}>
          <span class="toggle-thumb"></span>
        </button>
      </div>
      {#if imap.aktiv}<div class="status-hinweis status-ok">✅ Import aktiv</div>
      {:else}<div class="status-hinweis status-inaktiv">⏸ Import inaktiv</div>{/if}
    </div>

    <div class="card card-test">
      <div class="card-titel">🧪 Verbindung testen</div>
      <div class="test-row">
        <button class="btn-primary" onclick={imapTesten} disabled={imapTestLaeuft}>{imapTestLaeuft ? '⏳ Prüfe…' : '🔌 Verbindung testen'}</button>
        {#if imapConfigExistiert}<button class="btn-ghost btn-sm" onclick={imapLoeschen} disabled={imapLoeschenLaeuft} style="margin-left:auto">{imapLoeschenLaeuft ? '⏳…' : '🗑️ Löschen'}</button>{/if}
      </div>
      {#if imapTestStatus === 'success'}<div class="test-result test-ok">{imapTestNachricht}</div>{/if}
      {#if imapTestStatus === 'error'}<div class="test-result test-fehler">❌ {imapTestNachricht}</div>{/if}
      {#if imapTestFolders.length > 0}
        <div class="folders-list">
          <span class="folders-titel">Ordner:</span>
          {#each imapTestFolders as f}<span class="folder-chip">{f}</span>{/each}
        </div>
      {/if}
    </div>

    {#if imapConfigExistiert && (lastCheck || lastError)}
      <div class="card">
        <div class="card-titel">📊 Status</div>
        <div class="status-grid">
          <div><div class="status-label">Letzter Abruf</div><div class="status-val">{formatDatum(lastCheck)}</div></div>
          {#if lastError}<div style="grid-column:1/-1"><div class="status-label" style="color:var(--danger)">Letzter Fehler</div><div class="status-error">{lastError}</div></div>{/if}
        </div>
      </div>
    {/if}
  {/if}

  <!-- ═══════════════════════════════════════════════ -->
  <!-- TAB: KAUF-NACHRICHT                              -->
  <!-- ═══════════════════════════════════════════════ -->
  {#if tab === 'kauf'}
    {#if kaufLaeuft}<div class="config-laedt"><span class="spinner"></span> Einstellungen werden geladen…</div>{/if}

    <div class="card card-info">
      <div class="card-titel">💬 Wie funktioniert die Kauf-Nachricht?</div>
      <ul class="info-liste" style="margin:0;padding-left:18px">
        <li>Nach Kauf wird automatisch eine eBay-Nachricht gesendet</li>
        <li>Platzhalter wie <code>{'{{buyer}}'}</code> werden ersetzt</li>
        <li>Versand im selben Workflow wie Lagerreduzierung</li>
      </ul>
    </div>

    <div class="card">
      <div class="card-titel">🤖 Automatischer Versand</div>
      <div class="auto-row">
        <div>
          <div class="auto-titel">Nach jedem Kauf Nachricht senden</div>
          <div class="auto-sub">Nachricht an den Käufer sofort nach Lagerreduzierung.</div>
        </div>
        <button class="toggle-btn" class:toggle-an={kauf.kauf_nachricht_aktiv} class:toggle-aus={!kauf.kauf_nachricht_aktiv} onclick={toggleKaufNachricht}>
          <span class="toggle-thumb"></span>
        </button>
      </div>
      {#if kauf.kauf_nachricht_aktiv}<div class="status-hinweis status-ok">✅ Aktiv</div>
      {:else}<div class="status-hinweis status-inaktiv">⏸ Inaktiv</div>{/if}
    </div>

    <div class="card">
      <div class="card-titel">📝 Nachrichten-Vorlage</div>
      <div class="variablen-bar">
        <span class="var-titel">Platzhalter:</span>
        {#each kaufPlatzhalter as v}
          <button class="var-chip" onclick={() => kaufPlatzhalterEinfuegen(v.key)} title={v.beschreibung}>{v.key}</button>
        {/each}
      </div>
      <div class="form-grid">
        <div class="form-group form-span2"><label>Betreff *</label><input bind:value={kauf.kauf_nachricht_betreff} /></div>
        <div class="form-group form-span2"><label>Text *</label><textarea bind:this={kaufVorlageRef} bind:value={kauf.kauf_nachricht_vorlage} rows="10"></textarea></div>
      </div>
    </div>

    <div class="card">
      <div class="card-titel">👁 Vorschau</div>
      <div class="vorschau-box">
        <div class="vorschau-meta"><span class="vorschau-label">An:</span> max_mustermann (eBay)</div>
        <div class="vorschau-meta"><span class="vorschau-label">Betreff:</span> <strong>{kaufVorschauBetreff()}</strong></div>
        <div class="vorschau-trenner"></div>
        <div class="vorschau-body">{kaufVorschauText()}</div>
      </div>
    </div>
  {/if}
</div>


<style>
  .page-container { padding: 24px; max-width: 1200px; margin: 0 auto; }
  .page-hdr { display:flex; align-items:center; justify-content:space-between; gap:16px; margin-bottom:16px; flex-wrap:wrap; }
  .page-title { font-size:1.3rem; font-weight:700; color:var(--text); }
  .page-sub { font-size:0.8rem; color:var(--text2); margin-top:2px; }
  .hdr-left { display:flex; align-items:center; gap:16px; }
  .btn-back { background:transparent; border:1px solid var(--border); color:var(--text2); padding:7px 14px; border-radius:8px; font-size:0.82rem; cursor:pointer; transition:all 0.15s; }
  .btn-back:hover { border-color:var(--primary); color:var(--primary); }
  .config-laedt { font-size:0.8rem; color:var(--text2); padding:8px 14px; background:var(--surface2); border-radius:8px; margin-bottom:12px; display:flex; align-items:center; gap:10px; }
  .spinner { width:14px; height:14px; border:2px solid var(--border); border-top-color:var(--primary); border-radius:50%; animation:spin 0.7s linear infinite; display:inline-block; }
  @keyframes spin { to { transform:rotate(360deg); } }

  /* Tabs */
  .tab-bar { display:flex; gap:4px; border-bottom:1px solid var(--border); margin-bottom:16px; }
  .tab-btn { background:transparent; border:none; border-bottom:2px solid transparent; padding:10px 18px; font-size:0.85rem; color:var(--text2); cursor:pointer; font-weight:500; transition:all 0.15s; display:inline-flex; align-items:center; gap:6px; }
  .tab-btn:hover { color:var(--text); }
  .tab-btn.active { color:var(--primary); border-bottom-color:var(--primary); font-weight:600; }
  .tab-badge-grn { background:#16a34a; color:#fff; font-size:0.62rem; padding:2px 6px; border-radius:10px; font-weight:600; }

  .card { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:20px 24px; display:flex; flex-direction:column; gap:14px; margin-bottom:16px; }
  .card-builder { padding:20px; }
  .card-titel { font-size:0.88rem; font-weight:700; color:var(--text); }
  .card-sub { font-size:0.78rem; color:var(--text2); }
  .card-test { border-color:var(--primary); }
  .card-info { background:var(--primary-light); border-color:var(--primary-border); }
  .card-titel-row { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; flex-wrap:wrap; }
  .builder-top-actions { display:flex; gap:4px; flex-shrink:0; }

  .anbieter-grid { display:flex; gap:8px; flex-wrap:wrap; }
  .anbieter-btn { background:var(--surface2); border:1px solid var(--border); color:var(--text); padding:6px 14px; border-radius:8px; font-size:0.78rem; cursor:pointer; transition:all 0.15s; }
  .anbieter-btn:hover { border-color:var(--primary); color:var(--primary); }
  .anbieter-btn.aktiv { background:var(--primary); color:#fff; border-color:var(--primary); font-weight:600; }

  .form-grid { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
  .form-span2 { grid-column:1 / -1; }
  .form-group { display:flex; flex-direction:column; gap:5px; }
  .form-group label { font-size:0.76rem; color:var(--text2); font-weight:500; }
  .form-group input, .form-group textarea { background:var(--surface); border:1px solid var(--border); color:var(--text); padding:8px 12px; border-radius:8px; font-size:0.84rem; outline:none; font-family:inherit; width:100%; box-sizing:border-box; }
  .form-group input:focus, .form-group textarea:focus { border-color:var(--primary); }
  .form-group textarea { resize:vertical; line-height:1.6; }
  .input-row { display:flex; gap:8px; align-items:center; }
  .check-label { display:flex; align-items:center; gap:8px; font-size:0.84rem; color:var(--text); cursor:pointer; }
  .check-label input { accent-color:var(--primary); }

  .auto-row { display:flex; align-items:center; justify-content:space-between; gap:16px; }
  .auto-titel { font-size:0.84rem; font-weight:600; color:var(--text); margin-bottom:4px; }
  .auto-sub { font-size:0.76rem; color:var(--text2); max-width:560px; line-height:1.5; }
  .status-hinweis { padding:8px 14px; border-radius:8px; font-size:0.78rem; }
  .status-ok { background:#f0fdf4; border:1px solid #bbf7d0; color:#16a34a; }
  .status-inaktiv { background:var(--surface2); border:1px solid var(--border); color:var(--text2); }
  .toggle-btn { position:relative; width:44px; height:24px; border:none; border-radius:99px; cursor:pointer; transition:background 0.2s; padding:0; flex-shrink:0; }
  .toggle-an { background:var(--primary); }
  .toggle-aus { background:#d1d5db; }
  .toggle-thumb { position:absolute; top:3px; width:18px; height:18px; background:#fff; border-radius:50%; transition:left 0.2s; box-shadow:0 1px 3px rgba(0,0,0,0.2); }
  .toggle-an .toggle-thumb { left:23px; }
  .toggle-aus .toggle-thumb { left:3px; }

  .variablen-bar { display:flex; align-items:center; gap:8px; flex-wrap:wrap; padding:8px 12px; background:var(--surface2); border-radius:8px; }
  .var-titel { font-size:0.72rem; font-weight:600; color:var(--text2); white-space:nowrap; }
  .var-chip { background:var(--surface); border:1px solid var(--border); color:var(--primary); padding:2px 8px; border-radius:5px; font-size:0.72rem; font-family:monospace; cursor:pointer; transition:all 0.1s; }
  .var-chip:hover { background:var(--primary); color:#fff; border-color:var(--primary); }

  /* ═══════════════════════════════════════════════ */
  /* BLOCK BUILDER                                    */
  /* ═══════════════════════════════════════════════ */
  .builder-layout { display:flex; gap:0; border:1px solid var(--border); border-radius:10px; overflow:hidden; min-height:500px; }

  /* Palette */
  .palette { width:220px; background:var(--surface); border-right:1px solid var(--border); padding:14px; overflow-y:auto; flex-shrink:0; }
  .palette-section-title { font-size:0.66rem; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; color:var(--text3); margin-bottom:8px; }
  .block-item { display:flex; align-items:center; gap:10px; padding:8px 10px; border:1px solid var(--border); border-radius:7px; cursor:pointer; background:var(--surface); transition:all 0.12s; margin-bottom:5px; width:100%; text-align:left; }
  .block-item:hover { border-color:var(--primary); background:var(--primary-light); }
  .block-icon { font-size:1rem; flex-shrink:0; width:28px; text-align:center; }
  .block-info { display:flex; flex-direction:column; min-width:0; }
  .block-name { font-size:0.76rem; font-weight:600; color:var(--text); }
  .block-desc { font-size:0.64rem; color:var(--text2); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }

  /* Canvas */
  .canvas-scroll { flex:1; overflow-y:auto; padding:24px; background:#e5e7eb; display:flex; justify-content:center; }
  :global([data-theme="dark"]) .canvas-scroll { background:#1a1e28; }
  .email-frame { width:600px; flex-shrink:0; }
  .email-canvas { background:#fff; border-radius:12px; box-shadow:0 8px 30px rgba(0,0,0,0.12); min-height:300px; overflow:hidden; }
  :global([data-theme="dark"]) .email-canvas { background:#fff; }
  .email-footer { padding:20px 32px; text-align:center; font-size:0.7rem; color:#999; border-top:1px solid #e5e7eb; background:#f4f5f7; border-radius:0 0 12px 12px; margin-top:8px; }
  .drop-empty { display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:300px; color:var(--text3); font-size:0.85rem; text-align:center; padding:40px; }
  .drop-empty-icon { font-size:2.5rem; margin-bottom:12px; opacity:0.3; }

  .canvas-block { position:relative; cursor:pointer; outline:2px solid transparent; outline-offset:-2px; transition:outline 0.12s; }
  .canvas-block:hover { outline:2px solid var(--primary); }
  .canvas-block.selected { outline:2px solid var(--primary); }
  .canvas-block-inner { position:relative; }
  .block-actions { position:absolute; top:0; right:0; display:none; gap:1px; z-index:10; background:var(--primary); border-radius:0 0 0 6px; padding:2px 3px; }
  .canvas-block:hover .block-actions, .canvas-block.selected .block-actions { display:flex; }
  .ba-btn { width:24px; height:24px; border:none; background:transparent; color:#fff; border-radius:4px; cursor:pointer; font-size:0.7rem; display:flex; align-items:center; justify-content:center; }
  .ba-btn:hover { background:rgba(255,255,255,0.2); }

  /* Block renderings */
  .b-header { padding:28px 32px; text-align:center; }
  .b-header .b-header-icon { font-size:2.2rem; margin-bottom:8px; }
  .b-header h2 { font-size:1.3rem; font-weight:700; margin:0; }
  .b-header .b-header-sub { font-size:0.82rem; opacity:0.85; margin-top:4px; }
  .b-text { padding:16px 32px; font-size:0.88rem; line-height:1.7; color:#333; }
  .b-infobox { margin:12px 32px; padding:14px 18px; border-radius:8px; font-size:0.82rem; line-height:1.6; border-left:4px solid; }
  .b-infobox.style-blue { background:#eff6ff; border-color:#2563eb; color:#1e40af; }
  .b-infobox.style-green { background:#f0fdf4; border-color:#10b981; color:#166534; }
  .b-infobox.style-yellow { background:#fffbeb; border-color:#f59e0b; color:#92400e; }
  .b-infobox.style-red { background:#fef2f2; border-color:#ef4444; color:#991b1b; }
  .b-amount { margin:16px 32px; padding:20px; text-align:center; border-radius:10px; border-left:4px solid; }
  .amount-label { font-size:0.76rem; opacity:0.7; margin-bottom:4px; }
  .amount-value { font-size:1.8rem; font-weight:700; }
  .amount-sub { font-size:0.72rem; opacity:0.6; margin-top:4px; }
  .b-button-wrap { padding:16px 32px; text-align:center; }
  .b-button { display:inline-block; padding:13px 36px; font-weight:700; font-size:0.88rem; text-decoration:none; letter-spacing:0.02em; cursor:default; }
  .b-divider { padding:8px 32px; }
  .b-divider hr { border:none; height:1px; background:#e5e7eb; }
  .b-divider.style-bold hr { height:2px; }
  .b-divider.style-colored hr { height:2px; background:var(--primary); }
  .b-spacer { background:transparent; }
  .b-image { padding:8px 32px; text-align:center; }
  .b-image img { max-width:100%; height:auto; border-radius:8px; }
  .img-placeholder { background:#f7f8fa; border:2px dashed #e5e7eb; border-radius:8px; padding:28px; color:#999; font-size:0.8rem; }
  .b-signature { margin:8px 32px; padding:16px 0; border-top:1px solid #e5e7eb; font-size:0.8rem; color:#555; line-height:1.5; }
  .b-signature strong { color:#1a2233; font-size:0.86rem; }
  .b-columns { display:flex; gap:16px; padding:12px 32px; }
  .b-columns .col { flex:1; padding:14px; background:#f7f8fa; border-radius:8px; border:1px dashed #e5e7eb; font-size:0.8rem; color:#666; min-height:50px; }

  /* Properties Panel */
  .props-panel { width:250px; background:var(--surface); border-left:1px solid var(--border); overflow-y:auto; flex-shrink:0; }
  .props-header { padding:16px; border-bottom:1px solid var(--border); }
  .props-title { font-size:0.85rem; font-weight:700; }
  .props-sub { font-size:0.72rem; color:var(--text2); margin-top:2px; }
  .props-empty { padding:40px 18px; text-align:center; color:var(--text3); font-size:0.8rem; }
  .props-section { padding:14px 16px; border-bottom:1px solid var(--border); display:flex; flex-direction:column; gap:10px; }
  .ps-title { font-size:0.68rem; font-weight:700; text-transform:uppercase; letter-spacing:0.04em; color:var(--text3); }
  .prop-row { display:flex; flex-direction:column; gap:4px; }
  .prop-row label { font-size:0.72rem; font-weight:500; color:var(--text2); }
  .prop-row input, .props-section textarea { width:100%; padding:7px 10px; border:1px solid var(--border); border-radius:6px; font-size:0.8rem; color:var(--text); background:var(--surface); outline:none; font-family:inherit; box-sizing:border-box; }
  .prop-row input:focus, .props-section textarea:focus { border-color:var(--primary); }
  .props-section textarea { resize:vertical; min-height:50px; line-height:1.5; }
  .prop-hint { font-size:0.66rem; color:var(--text3); }
  .color-row { display:flex; gap:6px; flex-wrap:wrap; }
  .color-swatch { width:28px; height:28px; border-radius:6px; border:2px solid transparent; cursor:pointer; transition:all 0.1s; }
  .color-swatch:hover { transform:scale(1.15); border-color:var(--text); }
  .color-swatch.active { border-color:var(--text); box-shadow:0 0 0 2px var(--surface), 0 0 0 4px var(--text); }
  .divider-btns { display:flex; gap:4px; }
  .btn-active { background:var(--primary) !important; color:#fff !important; border-color:var(--primary) !important; }

  /* HTML Code */
  .html-code-area { font-family:'Courier New', monospace; font-size:0.78rem; line-height:1.5; min-height:200px; resize:vertical; background:var(--surface2); border:1px solid var(--border); border-radius:8px; color:var(--text); padding:14px; width:100%; box-sizing:border-box; }

  /* Vorschau */
  .vorschau-wrap { border:1px solid var(--border); border-radius:10px; overflow:hidden; background:#fff; }
  .vorschau-header { padding:12px 16px; background:var(--surface2); border-bottom:1px solid var(--border); font-size:0.8rem; color:var(--text2); display:flex; flex-direction:column; gap:4px; }
  .vorschau-label { font-weight:600; }
  .vorschau-canvas { padding:0; background:#e5e7eb; display:flex; justify-content:center; }
  .vorschau-canvas :global(img) { max-width:100%; height:auto; }

  /* Test */
  .test-row { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
  .test-row input { background:var(--surface); border:1px solid var(--border); color:var(--text); padding:8px 12px; border-radius:8px; font-size:0.84rem; outline:none; }
  .test-row input:focus { border-color:var(--primary); }
  .test-result { padding:10px 14px; border-radius:8px; font-size:0.8rem; margin-top:4px; }
  .test-ok { background:#f0fdf4; border:1px solid #bbf7d0; color:#15803d; }
  .test-fehler { background:#fef2f2; border:1px solid #fecaca; color:#dc2626; }

  .folders-list { display:flex; flex-wrap:wrap; gap:6px; padding:10px 12px; background:var(--surface2); border-radius:8px; align-items:center; }
  .folders-titel { font-size:0.72rem; font-weight:600; color:var(--text2); }
  .folder-chip { background:var(--surface); border:1px solid var(--border); color:var(--text); padding:2px 8px; border-radius:5px; font-size:0.7rem; font-family:monospace; }
  .status-grid { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
  .status-label { font-size:0.72rem; color:var(--text2); font-weight:500; }
  .status-val { font-size:0.84rem; color:var(--text); font-weight:500; }
  .status-error { font-size:0.76rem; color:#991b1b; background:#fef2f2; padding:8px 12px; border-radius:6px; border:1px solid #fecaca; margin-top:4px; }

  .vorschau-box { background:var(--surface2); border:1px solid var(--border); border-radius:10px; padding:16px 18px; display:flex; flex-direction:column; gap:6px; }
  .vorschau-meta { display:flex; gap:10px; font-size:0.8rem; }
  .vorschau-trenner { height:1px; background:var(--border); margin:8px 0; }
  .vorschau-body { white-space:pre-wrap; font-size:0.84rem; color:var(--text); line-height:1.6; }

  .vorlage-preview-info { padding:10px 14px; border-radius:8px; font-size:0.8rem; background:#f0fdf4; border:1px solid #bbf7d0; color:#16a34a; }
  .vorlage-preview-info.vorlage-leer { background:var(--surface2); border:1px solid var(--border); color:var(--text2); }

  .info-liste { margin:0; padding-left:18px; display:flex; flex-direction:column; gap:5px; }
  .info-liste li { font-size:0.78rem; color:var(--text2); line-height:1.5; }
  .info-liste code { background:var(--surface); padding:1px 5px; border-radius:4px; font-size:0.76rem; color:var(--primary); border:1px solid var(--border); }

  /* Template Modal */
  .template-grid { display:grid; grid-template-columns:repeat(2, 1fr); gap:12px; }
  .template-card { display:flex; flex-direction:column; align-items:center; gap:8px; padding:20px 14px; background:var(--surface2); border:1px solid var(--border); border-radius:10px; cursor:pointer; transition:all 0.15s; text-align:center; }
  .template-card:hover { border-color:var(--primary); background:var(--surface); transform:translateY(-2px); box-shadow:var(--shadow-md); }
  .template-icon { font-size:1.8rem; }
  .template-name { font-size:0.84rem; font-weight:600; color:var(--text); }
  .template-desc { font-size:0.7rem; color:var(--text2); }

  .btn-primary { background:var(--primary); color:#fff; border:none; padding:8px 16px; border-radius:8px; font-size:0.82rem; cursor:pointer; font-weight:600; }
  .btn-primary:hover:not(:disabled) { filter:brightness(1.08); }
  .btn-primary:disabled { opacity:0.6; cursor:not-allowed; }
  .btn-ghost { background:transparent; border:1px solid var(--border); color:var(--text2); padding:7px 12px; border-radius:8px; font-size:0.82rem; cursor:pointer; }
  .btn-ghost:hover { border-color:var(--primary); color:var(--primary); }
  .btn-sm { padding:5px 10px; font-size:0.78rem; }

  /* ═══════════════════════════════════════════════ */
  /* WYSIWYG EDITOR (im Properties-Panel)            */
  /* ═══════════════════════════════════════════════ */
  .ed-toolbar {
    display:flex; align-items:center; gap:1px; padding:5px 6px;
    background:var(--surface2); border:1px solid var(--border);
    border-radius:7px 7px 0 0; flex-wrap:wrap;
  }
  .ed-btn {
    background:transparent; border:1px solid transparent; color:var(--text);
    width:26px; height:26px; border-radius:4px; cursor:pointer;
    display:inline-flex; align-items:center; justify-content:center;
    font-size:0.72rem; transition:all 0.1s; padding:0;
  }
  .ed-btn:hover { background:var(--surface); border-color:var(--border); }
  .ed-btn-active { background:var(--primary) !important; color:#fff !important; border-color:var(--primary) !important; }
  .ed-sep { width:1px; height:18px; background:var(--border); margin:0 3px; flex-shrink:0; }
  .ed-select {
    background:var(--surface); border:1px solid var(--border); color:var(--text);
    padding:2px 4px; border-radius:4px; font-size:0.68rem; cursor:pointer;
    height:26px; outline:none; font-family:inherit;
  }
  .ed-select:focus { border-color:var(--primary); }
  .ed-dropdown-wrap { position:relative; }
  .ed-dropdown {
    position:absolute; top:100%; left:0; z-index:30;
    background:var(--surface); border:1px solid var(--border);
    border-radius:6px; padding:6px; box-shadow:0 4px 16px rgba(0,0,0,0.12);
    margin-top:4px;
  }
  .ed-color-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:3px; width:124px; }
  .ed-color-btn { width:26px; height:26px; border:2px solid transparent; border-radius:4px; cursor:pointer; transition:all 0.1s; }
  .ed-color-btn:hover { border-color:var(--text); transform:scale(1.15); }
  .ed-link-dialog { display:flex; gap:4px; align-items:center; width:220px; padding:8px; }
  .ed-link-input {
    flex:1; padding:5px 8px; border:1px solid var(--border); border-radius:5px;
    font-size:0.76rem; color:var(--text); background:var(--surface); outline:none;
  }
  .ed-link-input:focus { border-color:var(--primary); }
  .ed-var-row {
    display:flex; gap:4px; flex-wrap:wrap; padding:4px 0;
  }
  .ed-var-chip {
    background:var(--surface2); border:1px solid var(--border); color:var(--primary);
    padding:1px 6px; border-radius:4px; font-size:0.64rem; font-family:monospace;
    cursor:pointer; transition:all 0.1s;
  }
  .ed-var-chip:hover { background:var(--primary); color:#fff; border-color:var(--primary); }
  .ed-richtext {
    min-height:180px; max-height:400px; overflow-y:auto;
    padding:10px 12px; border:1px solid var(--border);
    border-radius:0 0 7px 7px; border-top:none;
    background:#fff; color:#333; font-size:0.82rem;
    line-height:1.7; font-family:Arial, sans-serif; outline:none;
  }
  :global([data-theme="dark"]) .ed-richtext { background:#fff; color:#333; }
  .ed-richtext:focus { border-color:var(--primary); }
  .ed-richtext :global(a) { color:#2563eb; }
  .ed-richtext :global(img) { max-width:100%; height:auto; border-radius:4px; }
  .ed-richtext-sm { min-height:100px; max-height:250px; }
  .ed-html-area {
    font-family:'Courier New', monospace; font-size:0.74rem; line-height:1.5;
    min-height:120px; resize:vertical; background:var(--surface2);
    border:1px solid var(--border); border-radius:0 0 7px 7px; border-top:none;
    color:var(--text); padding:10px 12px; width:100%; box-sizing:border-box; outline:none;
  }
  .ed-html-area:focus { border-color:var(--primary); }

  @media(max-width:900px) {
    .builder-layout { flex-direction:column; }
    .palette { width:100%; border-right:none; border-bottom:1px solid var(--border); flex-direction:row; flex-wrap:wrap; gap:6px; padding:10px; }
    .palette-section-title { width:100%; }
    .canvas-scroll { padding:16px; }
    .email-frame { width:100%; }
    .props-panel { width:100%; border-left:none; border-top:1px solid var(--border); }
  }
  @media(max-width:600px) {
    .form-grid { grid-template-columns:1fr; }
    .form-span2 { grid-column:1; }
    .template-grid { grid-template-columns:1fr; }
    .status-grid { grid-template-columns:1fr; }
  }
</style>
