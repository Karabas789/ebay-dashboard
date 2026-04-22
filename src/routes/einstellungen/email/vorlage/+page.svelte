<script>
  import { onMount } from 'svelte';
  import { currentUser, showToast } from '$lib/stores.js';
  import { apiCall } from '$lib/api.js';
  import { goto } from '$app/navigation';

  let speichertLaeuft = $state(false);
  let configLaeuft = $state(true);
  let blocks = $state([]);
  let selectedBlockId = $state(null);
  let blockIdCounter = $state(0);
  let vorschauOffen = $state(false);
  let htmlCodeOffen = $state(false);
  let templateModalOffen = $state(false);
  let betreff = $state('Ihre Rechnung {{rechnung_nr}}');

  // WYSIWYG
  let richEditorEl = $state(null);
  let richEditorBlockId = $state(null);
  let showColorPicker = $state(false);
  let showLinkDialog = $state(false);
  let linkInputUrl = $state('');
  let showHtmlMode = $state(false);
  let htmlRawText = $state('');

  const variablen = [
    { key:'{{rechnung_nr}}', label:'Rechnungsnr.' },
    { key:'{{kaeufer_name}}', label:'Käufername' },
    { key:'{{datum}}', label:'Datum' },
    { key:'{{brutto_betrag}}', label:'Betrag' },
    { key:'{{firmenname}}', label:'Firmenname' },
  ];

  const editorFarben = [
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

  const blockDefaults = {
    header: { type:'header', icon:'✉️', title:'Ihre Rechnung', subtitle:'', bgColor:'#6366f1', textColor:'#ffffff', borderRadius:true },
    text: { type:'text', content:'<p>Sehr geehrte(r) {{kaeufer_name}},</p><p>anbei erhalten Sie Ihre Rechnung {{rechnung_nr}} vom {{datum}} als PDF-Anhang.</p>' },
    infobox: { type:'infobox', style:'blue', content:'<strong>Hinweis:</strong> Hier können Sie einen Hinweis einfügen.' },
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

  const bausteinListe = [
    { type:'header', icon:'🎨', name:'Kopfbereich', desc:'Farbiger Banner', group:'struktur' },
    { type:'text', icon:'📝', name:'Textblock', desc:'Absatz mit Formatierung', group:'struktur' },
    { type:'divider', icon:'➖', name:'Trennlinie', desc:'Horizontal', group:'struktur' },
    { type:'spacer', icon:'↕️', name:'Abstand', desc:'Leerraum', group:'struktur' },
    { type:'columns', icon:'▥', name:'2 Spalten', desc:'Nebeneinander', group:'struktur' },
    { type:'infobox', icon:'📋', name:'Info-Box', desc:'Farbiger Hinweis', group:'inhalt' },
    { type:'amount', icon:'💰', name:'Betrag-Box', desc:'Hervorgehobener Wert', group:'inhalt' },
    { type:'button', icon:'🔘', name:'Button', desc:'Aktion-Link', group:'inhalt' },
    { type:'image', icon:'🖼️', name:'Bild', desc:'Logo/Grafik (URL)', group:'inhalt' },
    { type:'signature', icon:'📇', name:'Signatur', desc:'Firmendaten', group:'inhalt' },
  ];

  const starterTemplates = [
    { name:'Rechnung Modern', icon:'📄', desc:'Lila Header, Betrag, Signatur', key:'rechnung' },
    { name:'Bestätigung', icon:'🎉', desc:'Grüner Header, kurz & klar', key:'bestätigung' },
    { name:'Schlicht', icon:'〰️', desc:'Nur Text, kein Banner', key:'schlicht' },
    { name:'Produktschlüssel', icon:'🔑', desc:'Key-Übergabe mit Code-Box', key:'key' },
  ];

  // Block-Operationen
  function addBlock(type) {
    const b = { ...JSON.parse(JSON.stringify(blockDefaults[type])), id:'b_'+(++blockIdCounter) };
    blocks = [...blocks, b];
    selectedBlockId = b.id;
  }

  function selectBlock(id) {
    selectedBlockId = selectedBlockId === id ? null : id;
    showColorPicker = false; showLinkDialog = false; showHtmlMode = false;
    if (selectedBlockId) {
      const block = blocks.find(b => b.id === selectedBlockId);
      if (block && (block.type === 'text' || block.type === 'infobox')) {
        initRichEditor(block.id, block.content);
      } else { richEditorBlockId = null; }
    } else { richEditorBlockId = null; }
  }

  function moveBlock(id, dir) {
    const i = blocks.findIndex(b => b.id === id); if (i<0) return;
    const j = i+dir; if (j<0||j>=blocks.length) return;
    const a=[...blocks]; [a[i],a[j]]=[a[j],a[i]]; blocks=a;
  }

  function duplicateBlock(id) {
    const i = blocks.findIndex(b => b.id === id); if (i<0) return;
    const c = JSON.parse(JSON.stringify(blocks[i]));
    c.id = 'b_'+(++blockIdCounter);
    const a=[...blocks]; a.splice(i+1,0,c); blocks=a; selectedBlockId=c.id;
  }

  function deleteBlock(id) {
    blocks = blocks.filter(b => b.id !== id);
    if (selectedBlockId === id) selectedBlockId = null;
  }

  function updateBlock(id, key, value) {
    blocks = blocks.map(b => b.id === id ? { ...b, [key]: value } : b);
  }

  // WYSIWYG
  function richEditorCmd(cmd, val) { richEditorEl?.focus(); document.execCommand(cmd, false, val||null); syncRichEditor(); }
  function syncRichEditor() { if (richEditorEl && richEditorBlockId) updateBlock(richEditorBlockId, 'content', richEditorEl.innerHTML); }
  function initRichEditor(blockId, content) {
    richEditorBlockId = blockId; showHtmlMode = false; showColorPicker = false; showLinkDialog = false;
    setTimeout(() => { if (richEditorEl) richEditorEl.innerHTML = content || ''; }, 30);
  }
  function setEditorColor(c) { richEditorCmd('foreColor', c); showColorPicker = false; }
  function insertEditorLink() {
    if (!linkInputUrl.trim()) return;
    let u = linkInputUrl.trim(); if (!/^https?:\/\//i.test(u)) u='https://'+u;
    richEditorCmd('createLink', u); linkInputUrl=''; showLinkDialog=false;
  }
  function toggleHtmlMode() {
    if (showHtmlMode) {
      if (richEditorBlockId) updateBlock(richEditorBlockId, 'content', htmlRawText);
      if (richEditorEl) richEditorEl.innerHTML = htmlRawText;
      showHtmlMode = false;
    } else { htmlRawText = selectedBlock?.content || ''; showHtmlMode = true; }
  }
  function insertVariable(key) {
    if (showHtmlMode) { htmlRawText += key; if (richEditorBlockId) updateBlock(richEditorBlockId, 'content', htmlRawText); return; }
    richEditorEl?.focus(); document.execCommand('insertHTML', false, '<span>'+key+'</span>'); syncRichEditor();
  }

  // Templates
  function loadTemplate(key) {
    blocks=[]; blockIdCounter=0; selectedBlockId=null;
    if (key==='rechnung') {
      addBlock('header'); updateBlock(blocks.at(-1).id,'title','Ihre Rechnung'); updateBlock(blocks.at(-1).id,'subtitle','{{firmenname}}'); updateBlock(blocks.at(-1).id,'icon','📄');
      addBlock('text'); addBlock('amount');
      addBlock('text'); updateBlock(blocks.at(-1).id,'content','<p>Vielen Dank für Ihren Einkauf!</p><p>Beste Grüße</p>');
      addBlock('divider'); addBlock('signature');
    } else if (key==='bestätigung') {
      addBlock('header'); updateBlock(blocks.at(-1).id,'title','Bestellung bestätigt'); updateBlock(blocks.at(-1).id,'icon','🎉'); updateBlock(blocks.at(-1).id,'bgColor','#10b981');
      addBlock('text'); updateBlock(blocks.at(-1).id,'content','<p>Hallo {{kaeufer_name}},</p><p>Ihre Bestellung wurde erfolgreich aufgenommen.</p>');
      addBlock('infobox'); updateBlock(blocks.at(-1).id,'style','green'); updateBlock(blocks.at(-1).id,'content','<strong>Bestellnr.:</strong> {{rechnung_nr}}<br>Betrag: {{brutto_betrag}} EUR');
      addBlock('text'); updateBlock(blocks.at(-1).id,'content','<p>Viel Spaß!</p>'); addBlock('signature');
    } else if (key==='schlicht') {
      addBlock('text'); updateBlock(blocks.at(-1).id,'content','<p>Sehr geehrte(r) {{kaeufer_name}},</p><p>anbei Ihre Rechnung {{rechnung_nr}} vom {{datum}}.</p><p>Betrag: <strong>{{brutto_betrag}} EUR</strong></p><p>Vielen Dank!</p><p>Beste Grüße</p>');
      addBlock('divider'); addBlock('signature');
    } else if (key==='key') {
      addBlock('header'); updateBlock(blocks.at(-1).id,'title','Ihr Aktivierungsschlüssel'); updateBlock(blocks.at(-1).id,'subtitle','Vielen Dank für Ihre Bestellung'); updateBlock(blocks.at(-1).id,'icon','✅'); updateBlock(blocks.at(-1).id,'bgColor','#7c3aed');
      addBlock('text'); updateBlock(blocks.at(-1).id,'content','<p>Sehr geehrte(r) {{kaeufer_name}},</p><p>hiermit übersenden wir Ihren Produktschlüssel:</p>');
      addBlock('infobox'); updateBlock(blocks.at(-1).id,'content','<strong>Produktname</strong><br><br>Schlüssel:<br><span style="font-size:1.3em;font-family:monospace;color:#6366f1;font-weight:700">XXXX-XXXX-XXXX-XXXX</span><br><br>💡 Tipp: Key sicher aufbewahren.');
      addBlock('text'); updateBlock(blocks.at(-1).id,'content','<p>Bei Fragen stehen wir gerne zur Verfügung.</p><p><strong>Schöne Grüße</strong></p>'); addBlock('signature');
    }
    selectedBlockId=null; templateModalOffen=false;
  }

  // HTML Export
  function blockToHtml(b) {
    switch(b.type) {
      case 'header': { const r=b.borderRadius?'border-radius:12px 12px 0 0;':''; return `<div style="background:${b.bgColor};color:${b.textColor};padding:28px 32px;text-align:center;${r}">`+(b.icon?`<div style="font-size:2.2rem;margin-bottom:8px">${b.icon}</div>`:'')+`<h2 style="margin:0;font-size:1.3rem;font-weight:700">${b.title}</h2>`+(b.subtitle?`<div style="font-size:0.82rem;opacity:0.85;margin-top:4px">${b.subtitle}</div>`:'')+`</div>`; }
      case 'text': return `<div style="padding:16px 32px;font-size:15px;line-height:1.7;color:#333">${b.content}</div>`;
      case 'infobox': { const cs={blue:['#eff6ff','#2563eb','#1e40af'],green:['#f0fdf4','#10b981','#166534'],yellow:['#fffbeb','#f59e0b','#92400e'],red:['#fef2f2','#ef4444','#991b1b']}; const c=cs[b.style]||cs.blue; return `<div style="margin:12px 32px;padding:14px 18px;border-radius:8px;background:${c[0]};border-left:4px solid ${c[1]};color:${c[2]};font-size:14px;line-height:1.6">${b.content}</div>`; }
      case 'amount': return `<div style="margin:16px 32px;padding:20px;text-align:center;border-radius:10px;background:${b.bgColor};border-left:4px solid ${b.accentColor}"><div style="font-size:13px;color:${b.accentColor};opacity:0.7">${b.label}</div><div style="font-size:1.8rem;font-weight:700;color:${b.accentColor}">${b.value}</div>`+(b.sublabel?`<div style="font-size:12px;opacity:0.6;margin-top:4px">${b.sublabel}</div>`:'')+`</div>`;
      case 'button': return `<div style="padding:16px 32px;text-align:center"><a href="${b.url}" style="display:inline-block;padding:13px 36px;border-radius:${b.borderRadius}px;background:${b.bgColor};color:${b.textColor};font-weight:700;font-size:15px;text-decoration:none">${b.text}</a></div>`;
      case 'divider': { const h=b.style==='bold'?'2px':'1px'; const dc=b.style==='colored'?'#2563eb':'#e2e5ea'; return `<div style="padding:8px 32px"><hr style="border:none;height:${h};background:${dc}"></div>`; }
      case 'spacer': return `<div style="height:${b.height}px"></div>`;
      case 'image': return b.url?`<div style="padding:8px 32px;text-align:center"><img src="${b.url}" alt="${b.alt}" style="max-width:${b.maxWidth};height:auto;border-radius:8px"></div>`:'';
      case 'signature': { const d=(b.details||'').replace(/\n/g,'<br>'); return `<div style="margin:8px 32px;padding:16px 0;border-top:1px solid #e2e5ea;font-size:13px;color:#555;line-height:1.5"><strong style="font-size:14px;color:#1a1d23">${b.name}</strong><br>${d}<br>`+(b.phone?`📞 ${b.phone}<br>`:'')+(b.email?`📧 ${b.email}`:'')+`</div>`; }
      case 'columns': return `<table width="100%" cellpadding="0" cellspacing="0" style="padding:12px 32px"><tr><td width="48%" style="padding:14px;background:#f7f8fa;border-radius:8px;vertical-align:top">${b.left}</td><td width="4%"></td><td width="48%" style="padding:14px;background:#f7f8fa;border-radius:8px;vertical-align:top">${b.right}</td></tr></table>`;
      default: return '';
    }
  }

  function generateFullHtml() {
    let h='<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#ffffff;border-radius:12px;overflow:hidden">';
    blocks.forEach(b => { h += blockToHtml(b); });
    h+='</div><div style="text-align:center;padding:16px;font-size:12px;color:#999">Dieses Schreiben wurde automatisch erstellt.<br>© 2026 {{firmenname}}</div>';
    return h;
  }

  function vorschauHtml() {
    return generateFullHtml().replace(/\{\{rechnung_nr\}\}/g,'RE-2026-00042').replace(/\{\{kaeufer_name\}\}/g,'Max Mustermann').replace(/\{\{datum\}\}/g,'22.04.2026').replace(/\{\{brutto_betrag\}\}/g,'49,99').replace(/\{\{firmenname\}\}/g,'Import & Produkte Vertrieb');
  }

  // Laden / Speichern
  async function laden() {
    if (!$currentUser) return;
    configLaeuft = true;
    try {
      const data = await apiCall('email-config-laden', { user_id: $currentUser.id });
      if (data?.config) {
        betreff = data.config.betreff_vorlage || betreff;
        const vorlage = data.config.text_vorlage || '';
        try {
          const parsed = JSON.parse(vorlage);
          if (Array.isArray(parsed) && parsed.length > 0 && parsed[0].type) {
            blocks = parsed; blockIdCounter = parsed.length + 10;
          } else throw 0;
        } catch { if (vorlage) { blocks = [{ type:'text', content:vorlage, id:'b_1' }]; blockIdCounter=2; } }
      }
    } catch(e) { console.warn('Vorlage nicht geladen:', e?.message); }
    finally { configLaeuft = false; }
  }

  async function speichern() {
    speichertLaeuft = true;
    try {
      await apiCall('email-config-speichern', {
        user_id: $currentUser.id,
        betreff_vorlage: betreff,
        text_vorlage: JSON.stringify(blocks),
        email_html: generateFullHtml(),
      });
      showToast('✅ E-Mail-Vorlage gespeichert');
    } catch(e) { showToast('Fehler: ' + e.message); }
    finally { speichertLaeuft = false; }
  }

  onMount(() => { laden(); });

  function getSelectedBlock() { return selectedBlockId ? blocks.find(b => b.id === selectedBlockId) || null : null; }
  let selectedBlock = $derived(getSelectedBlock());
</script>

<div class="vb-wrap">
  <!-- TOPBAR -->
  <div class="vb-topbar">
    <div class="vb-topbar-left">
      <button class="vb-back" onclick={() => goto('/einstellungen/email')}>← Zurück</button>
      <div class="vb-title">📝 E-Mail Vorlage</div>
    </div>
    <div class="vb-topbar-center">
      <button class="vb-tab" class:active={!vorschauOffen && !htmlCodeOffen} onclick={() => { vorschauOffen=false; htmlCodeOffen=false; }}>✏️ Editor</button>
      <button class="vb-tab" class:active={vorschauOffen} onclick={() => { vorschauOffen=true; htmlCodeOffen=false; }}>👁 Vorschau</button>
      <button class="vb-tab" class:active={htmlCodeOffen} onclick={() => { htmlCodeOffen=true; vorschauOffen=false; }}>⟨/⟩ HTML</button>
    </div>
    <div class="vb-topbar-right">
      <button class="vb-tpl-btn" onclick={() => templateModalOffen = true}>🎨 Vorlagen</button>
      <button class="vb-save-btn" onclick={speichern} disabled={speichertLaeuft}>{speichertLaeuft ? '⏳…' : '💾 Speichern'}</button>
    </div>
  </div>

  <!-- Variablen-Leiste -->
  <div class="vb-var-bar">
    <span class="vb-var-label">Variablen:</span>
    {#each variablen as v}
      <button class="vb-var-chip" onclick={() => { if (richEditorBlockId) insertVariable(v.key); else { navigator.clipboard.writeText(v.key); showToast('Kopiert: '+v.key); } }}>{v.key}</button>
    {/each}
    <span class="vb-betreff-wrap">
      <span class="vb-var-label">Betreff:</span>
      <input class="vb-betreff-input" bind:value={betreff} placeholder={'Ihre Rechnung {{rechnung_nr}}'} />
    </span>
  </div>

  {#if configLaeuft}
    <div class="vb-loading"><span class="spinner"></span> Vorlage wird geladen…</div>
  {:else if vorschauOffen}
    <!-- VORSCHAU -->
    <div class="vb-preview-scroll">
      <div class="vb-preview-frame">
        <div class="vb-preview-header">
          <span>An: max.mustermann@example.com</span>
          <span>Betreff: <strong>{betreff.replace(/\{\{rechnung_nr\}\}/g,'RE-2026-00042')}</strong></span>
        </div>
        <div class="vb-preview-body">{@html vorschauHtml()}</div>
      </div>
    </div>
  {:else if htmlCodeOffen}
    <!-- HTML -->
    <div class="vb-html-scroll">
      <textarea class="vb-html-area" readonly>{generateFullHtml()}</textarea>
      <button class="vb-copy-btn" onclick={() => { navigator.clipboard.writeText(generateFullHtml()); showToast('HTML kopiert!'); }}>📋 Kopieren</button>
    </div>
  {:else}
    <!-- BUILDER -->
    <div class="vb-builder">
      <!-- Palette -->
      <div class="vb-palette">
        <div class="vb-pal-title">Struktur</div>
        {#each bausteinListe.filter(b=>b.group==='struktur') as b}
          <button class="vb-pal-item" onclick={() => addBlock(b.type)}>
            <span class="vb-pal-icon">{b.icon}</span><span class="vb-pal-info"><span class="vb-pal-name">{b.name}</span><span class="vb-pal-desc">{b.desc}</span></span>
          </button>
        {/each}
        <div class="vb-pal-title" style="margin-top:16px">Inhalt</div>
        {#each bausteinListe.filter(b=>b.group==='inhalt') as b}
          <button class="vb-pal-item" onclick={() => addBlock(b.type)}>
            <span class="vb-pal-icon">{b.icon}</span><span class="vb-pal-info"><span class="vb-pal-name">{b.name}</span><span class="vb-pal-desc">{b.desc}</span></span>
          </button>
        {/each}
      </div>

      <!-- Canvas -->
      <div class="vb-canvas">
        <div class="vb-email-frame">
          <div class="vb-email-body">
            {#if blocks.length === 0}
              <div class="vb-empty">
                <div style="font-size:2.5rem;opacity:0.25;margin-bottom:12px">📧</div>
                Klicke links auf Bausteine oder
                <button class="vb-empty-link" onclick={() => templateModalOffen=true}>wähle eine Vorlage</button>
              </div>
            {:else}
              {#each blocks as block, i (block.id)}
                <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
                <div class="vb-block" class:sel={selectedBlockId===block.id} onclick={() => selectBlock(block.id)}>
                  <div class="vb-block-actions">
                    {#if i>0}<button class="vb-ba" onclick={(e)=>{e.stopPropagation();moveBlock(block.id,-1)}}>↑</button>{/if}
                    {#if i<blocks.length-1}<button class="vb-ba" onclick={(e)=>{e.stopPropagation();moveBlock(block.id,1)}}>↓</button>{/if}
                    <button class="vb-ba" onclick={(e)=>{e.stopPropagation();duplicateBlock(block.id)}}>⎘</button>
                    <button class="vb-ba" onclick={(e)=>{e.stopPropagation();deleteBlock(block.id)}}>✕</button>
                  </div>
                  {#if block.type==='header'}
                    <div class="b-header" style="background:{block.bgColor};color:{block.textColor};{block.borderRadius?'border-radius:12px 12px 0 0;':''}">
                      {#if block.icon}<div style="font-size:2.2rem;margin-bottom:8px">{block.icon}</div>{/if}
                      <h2 style="margin:0;font-size:1.3rem;font-weight:700">{block.title}</h2>
                      {#if block.subtitle}<div style="font-size:0.82rem;opacity:0.85;margin-top:4px">{block.subtitle}</div>{/if}
                    </div>
                  {:else if block.type==='text'}<div class="b-text">{@html block.content}</div>
                  {:else if block.type==='infobox'}<div class="b-infobox style-{block.style}">{@html block.content}</div>
                  {:else if block.type==='amount'}
                    <div class="b-amount" style="background:{block.bgColor};border-color:{block.accentColor}">
                      <div style="font-size:0.76rem;opacity:0.7;color:{block.accentColor}">{block.label}</div>
                      <div style="font-size:1.8rem;font-weight:700;color:{block.accentColor}">{block.value}</div>
                      {#if block.sublabel}<div style="font-size:0.72rem;opacity:0.6;margin-top:4px">{block.sublabel}</div>{/if}
                    </div>
                  {:else if block.type==='button'}
                    <div style="padding:16px 32px;text-align:center"><span style="display:inline-block;padding:13px 36px;border-radius:{block.borderRadius}px;background:{block.bgColor};color:{block.textColor};font-weight:700;font-size:0.88rem">{block.text}</span></div>
                  {:else if block.type==='divider'}<div class="b-divider {block.style==='bold'?'style-bold':''} {block.style==='colored'?'style-colored':''}"><hr/></div>
                  {:else if block.type==='spacer'}<div style="height:{block.height}px"></div>
                  {:else if block.type==='image'}
                    <div style="padding:8px 32px;text-align:center">
                      {#if block.url}<img src={block.url} alt={block.alt} style="max-width:{block.maxWidth};border-radius:8px" />
                      {:else}<div class="vb-img-ph">🖼️ Bild-URL in Eigenschaften eingeben</div>{/if}
                    </div>
                  {:else if block.type==='signature'}
                    <div class="b-signature"><strong>{block.name}</strong><br>{@html (block.details||'').replace(/\n/g,'<br>')}<br>
                      {#if block.phone}📞 {block.phone}<br>{/if}{#if block.email}📧 {block.email}{/if}</div>
                  {:else if block.type==='columns'}
                    <div class="b-columns"><div class="b-col">{block.left}</div><div class="b-col">{block.right}</div></div>
                  {/if}
                </div>
              {/each}
            {/if}
            <div class="vb-footer">Dieses Schreiben wurde automatisch erstellt.<br>© 2026 {'{{firmenname}}'}</div>
          </div>
        </div>
      </div>

      <!-- Properties -->
      <div class="vb-props">
        {#if selectedBlock}
          <div class="vb-props-hdr">
            <div class="vb-props-title">⚙️ Eigenschaften</div>
            <div class="vb-props-type">
              {#if selectedBlock.type==='header'}🎨 Kopfbereich{:else if selectedBlock.type==='text'}📝 Text{:else if selectedBlock.type==='infobox'}📋 Info-Box{:else if selectedBlock.type==='amount'}💰 Betrag{:else if selectedBlock.type==='button'}🔘 Button{:else if selectedBlock.type==='divider'}➖ Trennlinie{:else if selectedBlock.type==='spacer'}↕️ Abstand{:else if selectedBlock.type==='image'}🖼️ Bild{:else if selectedBlock.type==='signature'}📇 Signatur{:else if selectedBlock.type==='columns'}▥ Spalten{/if}
            </div>
          </div>

          {#if selectedBlock.type==='header'}
            <div class="vb-ps"><div class="vb-ps-t">Inhalt</div>
              <div class="vb-pr"><label>Icon</label><input value={selectedBlock.icon||''} oninput={(e)=>updateBlock(selectedBlock.id,'icon',e.target.value)}/></div>
              <div class="vb-pr"><label>Titel</label><input value={selectedBlock.title} oninput={(e)=>updateBlock(selectedBlock.id,'title',e.target.value)}/></div>
              <div class="vb-pr"><label>Untertitel</label><input value={selectedBlock.subtitle||''} oninput={(e)=>updateBlock(selectedBlock.id,'subtitle',e.target.value)}/></div>
            </div>
            <div class="vb-ps"><div class="vb-ps-t">Hintergrund</div><div class="vb-colors">{#each headerFarben as c}<button class="vb-csw" class:act={selectedBlock.bgColor===c} style="background:{c}" onclick={()=>updateBlock(selectedBlock.id,'bgColor',c)}></button>{/each}</div></div>

          {:else if selectedBlock.type==='text' || selectedBlock.type==='infobox'}
            {#if selectedBlock.type==='infobox'}
              <div class="vb-ps"><div class="vb-ps-t">Box-Farbe</div><div class="vb-colors">
                <button class="vb-csw" class:act={selectedBlock.style==='blue'} style="background:#2563eb" onclick={()=>updateBlock(selectedBlock.id,'style','blue')}></button>
                <button class="vb-csw" class:act={selectedBlock.style==='green'} style="background:#10b981" onclick={()=>updateBlock(selectedBlock.id,'style','green')}></button>
                <button class="vb-csw" class:act={selectedBlock.style==='yellow'} style="background:#f59e0b" onclick={()=>updateBlock(selectedBlock.id,'style','yellow')}></button>
                <button class="vb-csw" class:act={selectedBlock.style==='red'} style="background:#ef4444" onclick={()=>updateBlock(selectedBlock.id,'style','red')}></button>
              </div></div>
            {/if}
            <div class="vb-ps"><div class="vb-ps-t">Text bearbeiten</div>
              <div class="ed-toolbar">
                <button class="ed-btn" onclick={()=>richEditorCmd('bold')} title="Fett"><strong>F</strong></button>
                <button class="ed-btn" onclick={()=>richEditorCmd('italic')} title="Kursiv"><em>K</em></button>
                <button class="ed-btn" onclick={()=>richEditorCmd('underline')} title="Unterstrichen"><u>U</u></button>
                <button class="ed-btn" onclick={()=>richEditorCmd('strikeThrough')} title="Durchgestrichen"><s>S</s></button>
                <span class="ed-sep"></span>
                <select class="ed-select" onchange={(e)=>{richEditorCmd('fontSize',e.target.value);e.target.value='';}} title="Schriftgröße">
                  <option value="" disabled selected>Aa</option>
                  {#each fontSizes as fs}<option value={fs.value}>{fs.label}</option>{/each}
                </select>
                <span class="ed-sep"></span>
                <div class="ed-dd">
                  <button class="ed-btn" onclick={()=>{showColorPicker=!showColorPicker;showLinkDialog=false}} title="Farbe">🎨</button>
                  {#if showColorPicker}<div class="ed-drop ed-cgrid">{#each editorFarben as f}<button class="ed-cbtn" style="background:{f}" onclick={()=>setEditorColor(f)}></button>{/each}</div>{/if}
                </div>
                <span class="ed-sep"></span>
                <button class="ed-btn" onclick={()=>richEditorCmd('justifyLeft')} title="Links">⬅</button>
                <button class="ed-btn" onclick={()=>richEditorCmd('justifyCenter')} title="Mitte">⬌</button>
                <button class="ed-btn" onclick={()=>richEditorCmd('justifyRight')} title="Rechts">➡</button>
                <span class="ed-sep"></span>
                <button class="ed-btn" onclick={()=>richEditorCmd('insertUnorderedList')} title="Liste">•≡</button>
                <button class="ed-btn" onclick={()=>richEditorCmd('insertOrderedList')} title="Nummer">1≡</button>
                <span class="ed-sep"></span>
                <div class="ed-dd">
                  <button class="ed-btn" onclick={()=>{showLinkDialog=!showLinkDialog;showColorPicker=false}} title="Link">🔗</button>
                  {#if showLinkDialog}<div class="ed-drop ed-link"><input class="ed-linkin" bind:value={linkInputUrl} placeholder="https://..." onkeydown={(e)=>e.key==='Enter'&&insertEditorLink()}/><button class="ed-linkgo" onclick={insertEditorLink}>OK</button></div>{/if}
                </div>
                <button class="ed-btn" onclick={()=>richEditorCmd('removeFormat')} title="Format entfernen">⊘</button>
                <span class="ed-sep"></span>
                <button class="ed-btn" class:ed-act={showHtmlMode} onclick={toggleHtmlMode} title="HTML">&lt;/&gt;</button>
              </div>
              <div class="ed-vars">{#each variablen as v}<button class="ed-vchip" onclick={()=>insertVariable(v.key)}>{v.key}</button>{/each}</div>
              {#if showHtmlMode}
                <textarea class="ed-html" rows="12" bind:value={htmlRawText} oninput={()=>{if(richEditorBlockId)updateBlock(richEditorBlockId,'content',htmlRawText)}}></textarea>
              {:else}
                <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
                <div class="ed-rich" bind:this={richEditorEl} contenteditable="true" oninput={syncRichEditor} onblur={syncRichEditor}></div>
              {/if}
            </div>

          {:else if selectedBlock.type==='amount'}
            <div class="vb-ps"><div class="vb-ps-t">Inhalt</div>
              <div class="vb-pr"><label>Beschriftung</label><input value={selectedBlock.label} oninput={(e)=>updateBlock(selectedBlock.id,'label',e.target.value)}/></div>
              <div class="vb-pr"><label>Wert</label><input value={selectedBlock.value} oninput={(e)=>updateBlock(selectedBlock.id,'value',e.target.value)}/></div>
              <div class="vb-pr"><label>Unterbeschriftung</label><input value={selectedBlock.sublabel||''} oninput={(e)=>updateBlock(selectedBlock.id,'sublabel',e.target.value)}/></div>
            </div>
            <div class="vb-ps"><div class="vb-ps-t">Akzentfarbe</div><div class="vb-colors">{#each accentFarben as c}<button class="vb-csw" class:act={selectedBlock.accentColor===c} style="background:{c}" onclick={()=>updateBlock(selectedBlock.id,'accentColor',c)}></button>{/each}</div></div>

          {:else if selectedBlock.type==='button'}
            <div class="vb-ps"><div class="vb-ps-t">Inhalt</div>
              <div class="vb-pr"><label>Text</label><input value={selectedBlock.text} oninput={(e)=>updateBlock(selectedBlock.id,'text',e.target.value)}/></div>
              <div class="vb-pr"><label>URL</label><input value={selectedBlock.url} oninput={(e)=>updateBlock(selectedBlock.id,'url',e.target.value)}/></div>
            </div>
            <div class="vb-ps"><div class="vb-ps-t">Hintergrund</div><div class="vb-colors">{#each buttonFarben as c}<button class="vb-csw" class:act={selectedBlock.bgColor===c} style="background:{c}" onclick={()=>updateBlock(selectedBlock.id,'bgColor',c)}></button>{/each}</div></div>

          {:else if selectedBlock.type==='divider'}
            <div class="vb-ps"><div class="vb-ps-t">Stil</div><div class="vb-div-btns">
              <button class="vb-div-b" class:act={selectedBlock.style==='normal'} onclick={()=>updateBlock(selectedBlock.id,'style','normal')}>Normal</button>
              <button class="vb-div-b" class:act={selectedBlock.style==='bold'} onclick={()=>updateBlock(selectedBlock.id,'style','bold')}>Dick</button>
              <button class="vb-div-b" class:act={selectedBlock.style==='colored'} onclick={()=>updateBlock(selectedBlock.id,'style','colored')}>Farbig</button>
            </div></div>

          {:else if selectedBlock.type==='spacer'}
            <div class="vb-ps"><div class="vb-ps-t">Höhe (px)</div><input type="number" value={selectedBlock.height} oninput={(e)=>updateBlock(selectedBlock.id,'height',parseInt(e.target.value)||24)}/></div>

          {:else if selectedBlock.type==='image'}
            <div class="vb-ps"><div class="vb-ps-t">Bild</div>
              <div class="vb-pr"><label>URL</label><input value={selectedBlock.url||''} oninput={(e)=>updateBlock(selectedBlock.id,'url',e.target.value)} placeholder="https://..."/></div>
              <div class="vb-pr"><label>Alt-Text</label><input value={selectedBlock.alt||''} oninput={(e)=>updateBlock(selectedBlock.id,'alt',e.target.value)}/></div>
              <div class="vb-pr"><label>Max. Breite</label><input value={selectedBlock.maxWidth||'100%'} oninput={(e)=>updateBlock(selectedBlock.id,'maxWidth',e.target.value)}/></div>
            </div>

          {:else if selectedBlock.type==='signature'}
            <div class="vb-ps"><div class="vb-ps-t">Firma</div>
              <div class="vb-pr"><label>Name</label><input value={selectedBlock.name} oninput={(e)=>updateBlock(selectedBlock.id,'name',e.target.value)}/></div>
              <div class="vb-pr"><label>Details</label><textarea rows="4" oninput={(e)=>updateBlock(selectedBlock.id,'details',e.target.value)}>{selectedBlock.details}</textarea></div>
              <div class="vb-pr"><label>Telefon</label><input value={selectedBlock.phone||''} oninput={(e)=>updateBlock(selectedBlock.id,'phone',e.target.value)}/></div>
              <div class="vb-pr"><label>E-Mail</label><input value={selectedBlock.email||''} oninput={(e)=>updateBlock(selectedBlock.id,'email',e.target.value)}/></div>
            </div>

          {:else if selectedBlock.type==='columns'}
            <div class="vb-ps"><div class="vb-ps-t">Spalten</div>
              <div class="vb-pr"><label>Links</label><textarea rows="3" oninput={(e)=>updateBlock(selectedBlock.id,'left',e.target.value)}>{selectedBlock.left}</textarea></div>
              <div class="vb-pr"><label>Rechts</label><textarea rows="3" oninput={(e)=>updateBlock(selectedBlock.id,'right',e.target.value)}>{selectedBlock.right}</textarea></div>
            </div>
          {/if}
        {:else}
          <div class="vb-props-empty">
            <div style="font-size:2rem;opacity:0.2;margin-bottom:10px">👈</div>
            Wähle einen Block
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>

<!-- Template Modal -->
{#if templateModalOffen}
  <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
  <div class="vb-modal-bg" onclick={()=>templateModalOffen=false}>
    <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
    <div class="vb-modal" onclick={(e)=>e.stopPropagation()}>
      <div class="vb-modal-t">🎨 Vorlage wählen</div>
      <div class="vb-tpl-grid">
        {#each starterTemplates as t}
          <button class="vb-tpl-card" onclick={()=>loadTemplate(t.key)}>
            <span style="font-size:1.8rem">{t.icon}</span>
            <span class="vb-tpl-name">{t.name}</span>
            <span class="vb-tpl-desc">{t.desc}</span>
          </button>
        {/each}
      </div>
      <div style="text-align:right;margin-top:16px"><button class="vb-back" onclick={()=>templateModalOffen=false}>Schließen</button></div>
    </div>
  </div>
{/if}

<style>
  /* ═══ FULLPAGE BUILDER LAYOUT ═══ */
  .vb-wrap { display:flex; flex-direction:column; height:calc(100vh - 52px); overflow:hidden; }
  .vb-topbar { display:flex; align-items:center; justify-content:space-between; padding:10px 20px; background:var(--surface); border-bottom:1px solid var(--border); gap:12px; flex-shrink:0; }
  .vb-topbar-left { display:flex; align-items:center; gap:14px; }
  .vb-topbar-center { display:flex; gap:2px; background:var(--surface2); border-radius:8px; padding:3px; }
  .vb-topbar-right { display:flex; gap:8px; }
  .vb-back { background:var(--surface); border:1px solid var(--border); color:var(--text2); padding:6px 14px; border-radius:7px; font-size:0.8rem; cursor:pointer; }
  .vb-back:hover { border-color:var(--primary); color:var(--primary); }
  .vb-title { font-size:1rem; font-weight:700; color:var(--text); }
  .vb-tab { background:transparent; border:none; padding:6px 14px; border-radius:6px; font-size:0.78rem; color:var(--text2); cursor:pointer; font-weight:500; }
  .vb-tab.active { background:var(--surface); color:var(--primary); font-weight:600; box-shadow:0 1px 3px rgba(0,0,0,0.06); }
  .vb-tpl-btn { background:var(--surface); border:1px solid var(--border); color:var(--text2); padding:6px 14px; border-radius:7px; font-size:0.78rem; cursor:pointer; }
  .vb-tpl-btn:hover { border-color:var(--primary); color:var(--primary); }
  .vb-save-btn { background:var(--primary); color:#fff; border:none; padding:6px 18px; border-radius:7px; font-size:0.8rem; font-weight:600; cursor:pointer; }
  .vb-save-btn:hover:not(:disabled) { filter:brightness(1.08); }
  .vb-save-btn:disabled { opacity:0.6; cursor:not-allowed; }

  .vb-var-bar { display:flex; align-items:center; gap:8px; padding:8px 20px; background:var(--surface2); border-bottom:1px solid var(--border); flex-wrap:wrap; flex-shrink:0; }
  .vb-var-label { font-size:0.68rem; font-weight:700; color:var(--text3); text-transform:uppercase; letter-spacing:0.04em; }
  .vb-var-chip { background:var(--surface); border:1px solid var(--border); color:var(--primary); padding:2px 8px; border-radius:5px; font-size:0.7rem; font-family:monospace; cursor:pointer; transition:all 0.1s; }
  .vb-var-chip:hover { background:var(--primary); color:#fff; border-color:var(--primary); }
  .vb-betreff-wrap { display:flex; align-items:center; gap:8px; margin-left:auto; }
  .vb-betreff-input { background:var(--surface); border:1px solid var(--border); color:var(--text); padding:5px 10px; border-radius:6px; font-size:0.8rem; width:280px; outline:none; }
  .vb-betreff-input:focus { border-color:var(--primary); }

  .vb-loading { display:flex; align-items:center; justify-content:center; gap:10px; padding:40px; color:var(--text2); font-size:0.85rem; flex:1; }
  .spinner { width:16px; height:16px; border:2px solid var(--border); border-top-color:var(--primary); border-radius:50%; animation:spin 0.7s linear infinite; }
  @keyframes spin { to { transform:rotate(360deg); } }

  /* ═══ 3-COLUMN BUILDER ═══ */
  .vb-builder { display:flex; flex:1; overflow:hidden; }
  .vb-palette { width:200px; background:var(--surface); border-right:1px solid var(--border); padding:16px 12px; overflow-y:auto; flex-shrink:0; }
  .vb-pal-title { font-size:0.64rem; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; color:var(--text3); margin-bottom:8px; }
  .vb-pal-item { display:flex; align-items:center; gap:10px; padding:7px 9px; border:1px solid var(--border); border-radius:7px; cursor:pointer; background:var(--surface); transition:all 0.12s; margin-bottom:4px; width:100%; text-align:left; }
  .vb-pal-item:hover { border-color:var(--primary); background:var(--primary-light); }
  .vb-pal-icon { font-size:0.95rem; width:24px; text-align:center; flex-shrink:0; }
  .vb-pal-info { display:flex; flex-direction:column; min-width:0; }
  .vb-pal-name { font-size:0.74rem; font-weight:600; color:var(--text); }
  .vb-pal-desc { font-size:0.6rem; color:var(--text3); }

  /* Canvas */
  .vb-canvas { flex:1; overflow-y:auto; padding:28px; background:#e5e7eb; display:flex; justify-content:center; }
  :global([data-theme="dark"]) .vb-canvas { background:#1a1e28; }
  .vb-email-frame { width:620px; flex-shrink:0; }
  .vb-email-body { background:#fff; border-radius:12px; box-shadow:0 8px 30px rgba(0,0,0,0.1); min-height:400px; overflow:hidden; }
  :global([data-theme="dark"]) .vb-email-body { background:#fff; }
  .vb-footer { padding:20px 32px; text-align:center; font-size:0.7rem; color:#999; border-top:1px solid #e5e7eb; background:#f4f5f7; border-radius:0 0 12px 12px; margin-top:8px; }
  .vb-empty { display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:350px; color:var(--text3); font-size:0.85rem; text-align:center; padding:40px; }
  .vb-empty-link { background:none; border:none; color:var(--primary); cursor:pointer; text-decoration:underline; font-size:0.85rem; padding:0; }

  .vb-block { position:relative; cursor:pointer; outline:2px solid transparent; outline-offset:-2px; transition:outline 0.1s; }
  .vb-block:hover { outline:2px solid var(--primary); }
  .vb-block.sel { outline:2px solid var(--primary); }
  .vb-block-actions { position:absolute; top:0; right:0; display:none; gap:1px; z-index:10; background:var(--primary); border-radius:0 0 0 6px; padding:2px 3px; }
  .vb-block:hover .vb-block-actions, .vb-block.sel .vb-block-actions { display:flex; }
  .vb-ba { width:24px; height:24px; border:none; background:transparent; color:#fff; border-radius:4px; cursor:pointer; font-size:0.7rem; display:flex; align-items:center; justify-content:center; }
  .vb-ba:hover { background:rgba(255,255,255,0.2); }

  /* Block styles */
  .b-header { padding:28px 32px; text-align:center; }
  .b-text { padding:16px 32px; font-size:0.88rem; line-height:1.7; color:#333; }
  .b-infobox { margin:12px 32px; padding:14px 18px; border-radius:8px; font-size:0.82rem; line-height:1.6; border-left:4px solid; }
  .b-infobox.style-blue { background:#eff6ff; border-color:#2563eb; color:#1e40af; }
  .b-infobox.style-green { background:#f0fdf4; border-color:#10b981; color:#166534; }
  .b-infobox.style-yellow { background:#fffbeb; border-color:#f59e0b; color:#92400e; }
  .b-infobox.style-red { background:#fef2f2; border-color:#ef4444; color:#991b1b; }
  .b-amount { margin:16px 32px; padding:20px; text-align:center; border-radius:10px; border-left:4px solid; }
  .b-divider { padding:8px 32px; }
  .b-divider hr { border:none; height:1px; background:#e5e7eb; }
  .b-divider.style-bold hr { height:2px; }
  .b-divider.style-colored hr { height:2px; background:var(--primary); }
  .b-signature { margin:8px 32px; padding:16px 0; border-top:1px solid #e5e7eb; font-size:0.8rem; color:#555; line-height:1.5; }
  .b-signature strong { color:#1a2233; font-size:0.86rem; }
  .b-columns { display:flex; gap:16px; padding:12px 32px; }
  .b-col { flex:1; padding:14px; background:#f7f8fa; border-radius:8px; border:1px dashed #e5e7eb; font-size:0.8rem; color:#666; min-height:50px; }
  .vb-img-ph { background:#f7f8fa; border:2px dashed #e5e7eb; border-radius:8px; padding:28px; color:#999; font-size:0.8rem; }

  /* Properties */
  .vb-props { width:600px; background:var(--surface); border-left:1px solid var(--border); overflow-y:auto; flex-shrink:0; }
  .vb-props-hdr { padding:16px 18px; border-bottom:1px solid var(--border); }
  .vb-props-title { font-size:0.88rem; font-weight:700; }
  .vb-props-type { font-size:0.72rem; color:var(--text2); margin-top:2px; }
  .vb-props-empty { padding:50px 20px; text-align:center; color:var(--text3); font-size:0.82rem; }
  .vb-ps { padding:16px 18px; border-bottom:1px solid var(--border); display:flex; flex-direction:column; gap:10px; }
  .vb-ps-t { font-size:0.68rem; font-weight:700; text-transform:uppercase; letter-spacing:0.04em; color:var(--text3); }
  .vb-pr { display:flex; flex-direction:column; gap:4px; }
  .vb-pr label { font-size:0.72rem; font-weight:500; color:var(--text2); }
  .vb-pr input, .vb-ps textarea { width:100%; padding:7px 10px; border:1px solid var(--border); border-radius:6px; font-size:0.8rem; color:var(--text); background:var(--surface); outline:none; font-family:inherit; box-sizing:border-box; }
  .vb-pr input:focus, .vb-ps textarea:focus { border-color:var(--primary); }
  .vb-ps textarea { resize:vertical; min-height:50px; line-height:1.5; }
  .vb-colors { display:flex; gap:6px; flex-wrap:wrap; }
  .vb-csw { width:28px; height:28px; border-radius:6px; border:2px solid transparent; cursor:pointer; transition:all 0.1s; }
  .vb-csw:hover { transform:scale(1.12); border-color:var(--text); }
  .vb-csw.act { border-color:var(--text); box-shadow:0 0 0 2px var(--surface), 0 0 0 4px var(--text); }
  .vb-div-btns { display:flex; gap:4px; }
  .vb-div-b { background:var(--surface2); border:1px solid var(--border); padding:5px 12px; border-radius:6px; font-size:0.76rem; cursor:pointer; color:var(--text2); }
  .vb-div-b.act { background:var(--primary); color:#fff; border-color:var(--primary); }

  /* ═══ WYSIWYG EDITOR ═══ */
  .ed-toolbar { display:flex; align-items:center; gap:1px; padding:6px 8px; background:var(--surface2); border:1px solid var(--border); border-radius:7px 7px 0 0; flex-wrap:wrap; }
  .ed-btn { background:transparent; border:1px solid transparent; color:var(--text); width:28px; height:28px; border-radius:4px; cursor:pointer; display:inline-flex; align-items:center; justify-content:center; font-size:0.74rem; transition:all 0.1s; padding:0; }
  .ed-btn:hover { background:var(--surface); border-color:var(--border); }
  .ed-act { background:var(--primary) !important; color:#fff !important; border-color:var(--primary) !important; }
  .ed-sep { width:1px; height:18px; background:var(--border); margin:0 3px; flex-shrink:0; }
  .ed-select { background:var(--surface); border:1px solid var(--border); color:var(--text); padding:2px 4px; border-radius:4px; font-size:0.7rem; cursor:pointer; height:28px; outline:none; }
  .ed-dd { position:relative; }
  .ed-drop { position:absolute; top:100%; left:0; z-index:30; background:var(--surface); border:1px solid var(--border); border-radius:6px; padding:6px; box-shadow:0 4px 16px rgba(0,0,0,0.12); margin-top:4px; }
  .ed-cgrid { display:grid; grid-template-columns:repeat(4,1fr); gap:3px; width:124px; }
  .ed-cbtn { width:26px; height:26px; border:2px solid transparent; border-radius:4px; cursor:pointer; transition:all 0.1s; }
  .ed-cbtn:hover { border-color:var(--text); transform:scale(1.12); }
  .ed-link { display:flex; gap:4px; align-items:center; width:240px; padding:8px; }
  .ed-linkin { flex:1; padding:5px 8px; border:1px solid var(--border); border-radius:5px; font-size:0.78rem; color:var(--text); background:var(--surface); outline:none; }
  .ed-linkin:focus { border-color:var(--primary); }
  .ed-linkgo { background:var(--primary); color:#fff; border:none; padding:5px 12px; border-radius:5px; font-size:0.76rem; cursor:pointer; }
  .ed-vars { display:flex; gap:4px; flex-wrap:wrap; padding:4px 0; }
  .ed-vchip { background:var(--surface2); border:1px solid var(--border); color:var(--primary); padding:1px 6px; border-radius:4px; font-size:0.64rem; font-family:monospace; cursor:pointer; }
  .ed-vchip:hover { background:var(--primary); color:#fff; border-color:var(--primary); }
  .ed-rich { min-height:220px; max-height:450px; overflow-y:auto; padding:12px 14px; border:1px solid var(--border); border-radius:0 0 7px 7px; border-top:none; background:#fff; color:#333; font-size:0.84rem; line-height:1.7; font-family:Arial,sans-serif; outline:none; }
  :global([data-theme="dark"]) .ed-rich { background:#fff; color:#333; }
  .ed-rich:focus { border-color:var(--primary); }
  .ed-rich :global(a) { color:#2563eb; }
  .ed-rich :global(img) { max-width:100%; height:auto; }
  .ed-html { font-family:'Courier New',monospace; font-size:0.76rem; line-height:1.5; min-height:160px; resize:vertical; background:var(--surface2); border:1px solid var(--border); border-radius:0 0 7px 7px; border-top:none; color:var(--text); padding:12px; width:100%; box-sizing:border-box; outline:none; }

  /* ═══ VORSCHAU / HTML ═══ */
  .vb-preview-scroll { flex:1; overflow-y:auto; padding:28px; background:#e5e7eb; display:flex; justify-content:center; }
  :global([data-theme="dark"]) .vb-preview-scroll { background:#1a1e28; }
  .vb-preview-frame { width:660px; }
  .vb-preview-header { padding:12px 18px; background:var(--surface); border:1px solid var(--border); border-radius:10px 10px 0 0; font-size:0.8rem; color:var(--text2); display:flex; flex-direction:column; gap:4px; }
  .vb-preview-body { background:#e5e7eb; padding:0; border-radius:0 0 10px 10px; border:1px solid var(--border); border-top:none; }
  .vb-preview-body :global(img) { max-width:100%; height:auto; }
  .vb-html-scroll { flex:1; display:flex; flex-direction:column; padding:20px; gap:10px; }
  .vb-html-area { flex:1; font-family:'Courier New',monospace; font-size:0.78rem; line-height:1.5; background:var(--surface); border:1px solid var(--border); border-radius:8px; color:var(--text); padding:16px; resize:none; outline:none; }
  .vb-copy-btn { align-self:flex-start; background:var(--surface); border:1px solid var(--border); color:var(--text2); padding:6px 14px; border-radius:7px; font-size:0.78rem; cursor:pointer; }
  .vb-copy-btn:hover { border-color:var(--primary); color:var(--primary); }

  /* ═══ MODAL ═══ */
  .vb-modal-bg { position:fixed; inset:0; background:rgba(0,0,0,0.4); backdrop-filter:blur(4px); z-index:200; display:flex; align-items:center; justify-content:center; }
  .vb-modal { background:var(--surface); border-radius:16px; box-shadow:0 24px 64px rgba(0,0,0,0.2); width:640px; max-height:85vh; overflow-y:auto; padding:28px; }
  .vb-modal-t { font-size:1.1rem; font-weight:700; margin-bottom:16px; }
  .vb-tpl-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
  .vb-tpl-card { display:flex; flex-direction:column; align-items:center; gap:6px; padding:20px; background:var(--surface2); border:1px solid var(--border); border-radius:10px; cursor:pointer; transition:all 0.15s; text-align:center; }
  .vb-tpl-card:hover { border-color:var(--primary); transform:translateY(-2px); box-shadow:0 4px 12px rgba(0,0,0,0.08); }
  .vb-tpl-name { font-size:0.84rem; font-weight:600; color:var(--text); }
  .vb-tpl-desc { font-size:0.7rem; color:var(--text2); }

  @media(max-width:1000px) {
    .vb-builder { flex-direction:column; }
    .vb-palette { width:100%; flex-direction:row; flex-wrap:wrap; border-right:none; border-bottom:1px solid var(--border); padding:10px; gap:4px; }
    .vb-pal-title { width:100%; }
    .vb-canvas { padding:16px; }
    .vb-email-frame { width:100%; }
    .vb-props { width:100%; border-left:none; border-top:1px solid var(--border); }
  }
</style>
