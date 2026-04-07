<script>
  import { onMount } from 'svelte';
  import { beforeNavigate } from '$app/navigation';
  import { currentUser, showToast } from '$lib/stores.js';
  import { apiCall } from '$lib/api.js';

  const LS_KEY = 'rechnungsvorlage_draft';

  const B = {
    rechnung_nr: '202658155', datum: '04.04.2026', zahlungsziel: '11.04.2026',
    artikel_name: 'Microsoft Windows 10 Pro Produktschlüssel Key MS Software Professional Original',
    artikel_nr: '1054', menge: 1, einzelpreis: 15.57,
    netto_betrag: 13.08, steuer_betrag: 2.49, brutto_betrag: 15.57, steuersatz: 19,
  };
  const fmtN = (n) => Number(n||0).toLocaleString('de-DE',{minimumFractionDigits:2,maximumFractionDigits:2});

  const A4W = 794;
  const A4H = 1123;

  let v = $state({
    schriftart: 'Arial',
    schriftgroesse: 11,
    zeilenabstand: 1.6,
    akzentfarbe: '#1d4ed8',
    seitenrand: 28,
    logo: { base64:'', breite:130, position:'links' },
    hintergrundbilder: [],
    wasserzeichen_sichtbar: false,
    zahlung_sichtbar: true,
    zahlung_stil: 'badge',
    zahlung_farbe: '#16a34a', zahlung_hg: '#f0fdf4', zahlung_rahmen: '#86efac',
    footer_spalten: 4,
    footer_trennlinie: true,
    footer_schriftgroesse: 8,
    footer_zeilenabstand: 1.6,
    tabelle: { kopf_hg:'#1d4ed8', kopf_farbe:'#ffffff', zeige_artnr:true, zeige_menge:true, zeige_ep:true, zeige_betrag:true },
    summen: { breite:280, kleinunternehmer:false },
    t_absender: 'Import & Produkte Vertrieb · Auf der Schläfe 1 · 57078 Siegen',
    t_empfaenger: 'Vitali Dubs\nPackstation 118\nPostnummer: 49045164\n57078 Siegen',
    t_kontakt: 'So erreichen Sie uns\n\nE-Mail      import_vertrieb@mail.de\nTelefon    0271 50149974\nMobil       0177 6776548\n\nSteuer-Nr.   342/5058/2211\nUSt-IdNr.    DE815720228\n\nDatum       04.04.2026\nKunde       34025\nRechnung  202658155',
    t_einleitung: 'Sehr geehrte Damen und Herren,\nnachfolgend berechnen wir Ihnen wie vorab besprochen:',
    t_abschluss: 'Vielen Dank für Ihren Auftrag!\n\nBitte begleichen Sie den offenen Betrag bis zum 11.04.2026.\n\nMit freundlichen Grüßen\nImport & Produkte Vertrieb',
    t_zahlung: 'Bereits bezahlt über eBay',
    t_footer: [
      'Import & Produkte Vertrieb\nInh. Oxana Dubs\nAuf der Schläfe 1\nDE 57078 Siegen',
      'Telefon: +49 271 50149974\nMobil:    +49 177 6776548\nE-Mail:   ov-shop@mail.de',
      'Bankverbindung: N26 Bank\nIBAN: DE60 1001 1001 2829 9706 30\nBIC: NTSBDEB1XXX',
      'Finanzamt Siegen\nSt.Nr. 342/5058/2200\nUSt. -ID: DE815720228',
    ],
  });

  let speichertLaeuft = $state(false);
  let pdfLaeuft = $state(false);
  let vorschauPDF = $state('');
  let zeigtPDF = $state(false);
  let aktiverBlock = $state('');
  let aktivesTab = $state('inhalt');

  let savedRange = null;
  let hatAuswahl = $state(false);
  let auswahlGroesse = $state(11);

  let elAbsender, elEmpfaenger, elKontakt, elEinleitung, elAbschluss, elZahlung;
  let elFooter = [];
  let a4El;
  // WICHTIG: kein $state — document-listener braucht direkte JS-Variable, nicht reaktiven Proxy
  let dragging = null;
  let resizing = null;

  let autoSaveTimer = null;
  let hatUngespeicherteAenderungen = $state(false);
  let autoSaveStatus = $state('');

  function saveToLocalStorage() {
    try { collectDom(); localStorage.setItem(LS_KEY, JSON.stringify({ v, ts: Date.now() })); } catch(e) {}
  }
  function scheduleAutoSave() {
    hatUngespeicherteAenderungen = true;
    saveToLocalStorage();
    clearTimeout(autoSaveTimer);
    autoSaveTimer = setTimeout(autoSave, 2000);
  }
  async function autoSave() {
    if (!$currentUser) return;
    collectDom();
    autoSaveStatus = 'speichert';
    try {
      await apiCall('vorlage-speichern', { user_id: $currentUser.id, vorlage: v });
      hatUngespeicherteAenderungen = false;
      autoSaveStatus = 'gespeichert';
      localStorage.removeItem(LS_KEY);
      setTimeout(() => { autoSaveStatus = ''; }, 2500);
    } catch(e) { autoSaveStatus = ''; }
  }
  function saveNow() {
    if (!hatUngespeicherteAenderungen) return;
    clearTimeout(autoSaveTimer);
    saveToLocalStorage();
    if ($currentUser) apiCall('vorlage-speichern', { user_id: $currentUser.id, vorlage: v }).catch(()=>{});
    hatUngespeicherteAenderungen = false;
  }

  onMount(async () => {
    // Google Fonts laden
    const googleFonts = ['Poppins','Roboto','Lato','Montserrat','Open Sans','Raleway','Nunito','Playfair Display'];
    const fontQuery = googleFonts.map(f => 'family=' + f.replace(/ /g,'+') + ':ital,wght@0,300;0,400;0,600;0,700;1,400').join('&');
    if (!document.querySelector('link[data-gfonts]')) {
      const lnk = document.createElement('link');
      lnk.rel = 'stylesheet'; lnk.dataset.gfonts = '1';
      lnk.href = 'https://fonts.googleapis.com/css2?' + fontQuery + '&display=swap';
      document.head.appendChild(lnk);
    }
    syncDom();
    if ($currentUser) {
      try {
        const data = await apiCall('vorlage-laden', { user_id: $currentUser.id });
        if (data?.vorlage) { v = { ...v, ...data.vorlage }; syncDom(); }
      } catch(e) {
        try {
          const draft = localStorage.getItem(LS_KEY);
          if (draft) { const p = JSON.parse(draft); if (p?.v) { v = { ...v, ...p.v }; syncDom(); showToast('📋 Lokaler Entwurf wiederhergestellt'); } }
        } catch(le) {}
      }
    } else {
      try {
        const draft = localStorage.getItem(LS_KEY);
        if (draft) { const p = JSON.parse(draft); if (p?.v) { v = { ...v, ...p.v }; syncDom(); } }
      } catch(le) {}
    }

    // FIX DRAG: mousemove + mouseup auf document — funktioniert auch außerhalb scroll-container
    document.addEventListener('mousemove', onDocMousemove);
    document.addEventListener('mouseup', onDocMouseup);
    document.addEventListener('keyup', onDocKeyup);
    const onVisChange = () => { if (document.visibilityState === 'hidden') saveNow(); };
    document.addEventListener('visibilitychange', onVisChange);
    window.addEventListener('beforeunload', saveNow);
    return () => {
      document.removeEventListener('mousemove', onDocMousemove);
      document.removeEventListener('mouseup', onDocMouseup);
      document.removeEventListener('keyup', onDocKeyup);
      document.removeEventListener('visibilitychange', onVisChange);
      window.removeEventListener('beforeunload', saveNow);
      saveNow();
    };
  });

  beforeNavigate(() => { saveNow(); });

  function nl2htmlbr(s) { return (s||'').split('\n').join('<br>'); }
  function cleanSavedHtml(html) {
    if (!html) return '';
    return html
      .replace(/background(-color)?:\s*rgba\([^)]+\)[^;"']*/gi, '')
      .replace(/box-shadow:\s*[^;"']*/gi, '')
      .replace(/\s*style="\s*;?\s*"/gi, '')
      .replace(/style="\s*"/gi, '');
  }
  function html2text(el) { return el ? cleanSavedHtml(el.innerHTML) : ''; }

  function syncDom() {
    setTimeout(() => {
      if (elAbsender) elAbsender.innerHTML = nl2htmlbr(v.t_absender);
      if (elEmpfaenger) elEmpfaenger.innerHTML = nl2htmlbr(v.t_empfaenger);
      if (elKontakt) elKontakt.innerHTML = nl2htmlbr(v.t_kontakt);
      if (elEinleitung) elEinleitung.innerHTML = nl2htmlbr(v.t_einleitung);
      if (elAbschluss) elAbschluss.innerHTML = nl2htmlbr(v.t_abschluss);
      if (elZahlung) elZahlung.innerHTML = nl2htmlbr(v.t_zahlung);
      elFooter.forEach((el,i) => { if(el) el.innerHTML = nl2htmlbr(v.t_footer[i]??''); });
    }, 0);
  }
  function collectDom() {
    if (elAbsender) v.t_absender = html2text(elAbsender);
    if (elEmpfaenger) v.t_empfaenger = html2text(elEmpfaenger);
    if (elKontakt) v.t_kontakt = html2text(elKontakt);
    if (elEinleitung) v.t_einleitung = html2text(elEinleitung);
    if (elAbschluss) v.t_abschluss = html2text(elAbschluss);
    if (elZahlung) v.t_zahlung = html2text(elZahlung);
    elFooter.forEach((el,i) => { if(el){const a=[...v.t_footer];a[i]=html2text(el);v.t_footer=a;} });
  }
  function saveBlur(key, e) { v[key] = cleanSavedHtml(e.target.innerHTML); aktiverBlock=''; scheduleAutoSave(); }
  function saveFooter(i, e) { const a=[...v.t_footer]; a[i]=cleanSavedHtml(e.target.innerHTML); v.t_footer=a; aktiverBlock=''; scheduleAutoSave(); }

  // ── SELEKTION ────────────────────────────────────────────────────────────
  function captureSelection() {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) return;
    const range = sel.getRangeAt(0);
    if (!isInEditor(range.commonAncestorContainer)) return;
    if (!sel.isCollapsed) {
      savedRange = range.cloneRange(); hatAuswahl = true;
      try {
        const node = range.startContainer;
        const el = node.nodeType===3 ? node.parentElement : node;
        auswahlGroesse = Math.round(parseFloat(getComputedStyle(el).fontSize)) || v.schriftgroesse;
      } catch(e) {}
    } else { hatAuswahl = false; }
  }
  // FIX: onDocMouseup behandelt sowohl Drag-Ende als auch Text-Selektion
  function onDocMouseup(e) {
    if (dragging || resizing) {
      dragging = null; resizing = null; scheduleAutoSave();
      return;
    }
    if (e.target.closest('.rw-fmt-btn')) return;
    captureSelection();
  }
  function onDocKeyup() { captureSelection(); }
  function isInEditor(node) {
    let n = node?.nodeType===3 ? node.parentElement : node;
    while(n) { if(n.classList?.contains('rw-e')) return true; n=n.parentElement; }
    return false;
  }
  function execOnSaved(cmd, val=null) {
    if (!savedRange) return;
    const sel = window.getSelection();
    sel.removeAllRanges(); sel.addRange(savedRange);
    document.execCommand(cmd, false, val);
    if(sel.rangeCount>0) savedRange = sel.getRangeAt(0).cloneRange();
  }
  function applyFontSize(px) {
    if (!savedRange) return;
    const sel = window.getSelection();
    sel.removeAllRanges(); sel.addRange(savedRange);
    try {
      const span = document.createElement('span');
      span.style.fontSize = px + 'px';
      savedRange.surroundContents(span);
    } catch(e) {
      document.execCommand('fontSize', false, '4');
      document.querySelectorAll('font[size="4"]').forEach(f => {
        const s = document.createElement('span');
        s.style.fontSize = px + 'px';
        while(f.firstChild) s.appendChild(f.firstChild);
        f.replaceWith(s);
      });
    }
    auswahlGroesse = px;
  }
  function applyZeilenabstand(val) {
    v.zeilenabstand = val;
    document.querySelectorAll('.rw-e').forEach(el => { el.style.lineHeight = val; });
  }
  function applyAusrichtung(align) { execOnSaved('justify' + align); }
  function applyFarbe(c) { execOnSaved('foreColor', c); }
  function applyFett()   { execOnSaved('bold'); }
  function applyKursiv() { execOnSaved('italic'); }
  function applyUnter()  { execOnSaved('underline'); }
  function clearFormat() { execOnSaved('removeFormat'); }

  async function speichern() {
    collectDom(); speichertLaeuft=true;
    try { await apiCall('vorlage-speichern',{user_id:$currentUser?.id,vorlage:v}); showToast('Vorlage gespeichert ✓'); }
    catch(e){ showToast('Fehler: '+e.message); }
    finally{ speichertLaeuft=false; }
  }
  async function pdfVorschau() {
    collectDom(); pdfLaeuft=true; zeigtPDF=true;
    try {
      const data = await apiCall('rechnung-vorschau',{user_id:$currentUser?.id,vorlage:v,beispiel:B});
      vorschauPDF = data.pdf_base64||'';
    } catch(e){ showToast('Fehler: '+e.message); zeigtPDF=false; }
    finally{ pdfLaeuft=false; }
  }

  function handleLogoUpload(e) {
    const file=e.target.files?.[0]; if(!file) return;
    const r=new FileReader(); r.onload=(ev)=>{ v.logo.base64=ev.target.result; }; r.readAsDataURL(file);
  }

  // ── BILD-LOGIK ──────────────────────────────────────────────────────────
  function addBilder(e) {
    Array.from(e.target.files||[]).forEach((file, idx) => {
      const r = new FileReader();
      r.onload = (ev) => {
        const img = new Image();
        img.onload = () => {
          const natW = img.naturalWidth;
          const natH = img.naturalHeight;
          const bw = 200;
          const bh = Math.round(bw * natH / natW);
          v.hintergrundbilder = [...v.hintergrundbilder, {
            id: Date.now() + Math.random(),
            base64: ev.target.result,
            x: v.seitenrand + idx * 20,
            y: 20 + idx * 20,
            breite: bw,
            hoehe: bh,
            nat_w: natW,
            nat_h: natH,
            opacity: 1.0,
            modus: 'frei',
            verh_sperren: true,
          }];
        };
        img.src = ev.target.result;
      };
      r.readAsDataURL(file);
    });
    e.target.value = '';
  }

  function updateBild(id, key, val) {
    v.hintergrundbilder = v.hintergrundbilder.map(b => b.id===id ? {...b,[key]:val} : b);
  }
  function updateBreite(id, val) {
    v.hintergrundbilder = v.hintergrundbilder.map(b => {
      if (b.id !== id) return b;
      const nw = Math.max(10, val);
      const nh = b.verh_sperren && b.nat_w ? Math.round(nw * b.nat_h / b.nat_w) : b.hoehe;
      return { ...b, breite: nw, hoehe: nh };
    });
  }
  function updateHoehe(id, val) {
    v.hintergrundbilder = v.hintergrundbilder.map(b => {
      if (b.id !== id) return b;
      const nh = Math.max(10, val);
      const nw = b.verh_sperren && b.nat_h ? Math.round(nh * b.nat_w / b.nat_h) : b.breite;
      return { ...b, hoehe: nh, breite: nw };
    });
  }
  function setBildVollseite(id) {
    v.hintergrundbilder = v.hintergrundbilder.map(b =>
      b.id===id ? { ...b, x:0, y:0, breite:A4W, hoehe:A4H, modus:'vollseite', verh_sperren:false } : b
    );
  }
  function setBildA4Crop(id) {
    v.hintergrundbilder = v.hintergrundbilder.map(b => {
      if (b.id !== id) return b;
      if (!b.nat_w || !b.nat_h) return { ...b, x:0, y:0, breite:A4W, hoehe:A4H, modus:'crop' };
      const scale = Math.max(A4W / b.nat_w, A4H / b.nat_h);
      const rw = Math.round(b.nat_w * scale);
      const rh = Math.round(b.nat_h * scale);
      return { ...b, x: Math.round((A4W-rw)/2), y: Math.round((A4H-rh)/2), breite:rw, hoehe:rh, modus:'crop' };
    });
  }
  function setBildFrei(id) {
    v.hintergrundbilder = v.hintergrundbilder.map(b =>
      b.id===id ? { ...b, modus:'frei', verh_sperren:true } : b
    );
  }
  function removeBild(id) { v.hintergrundbilder = v.hintergrundbilder.filter(b => b.id!==id); }
  function bringFront(id) { const b=v.hintergrundbilder.find(x=>x.id===id); v.hintergrundbilder=[...v.hintergrundbilder.filter(x=>x.id!==id),b]; }
  function sendBack(id)   { const b=v.hintergrundbilder.find(x=>x.id===id); v.hintergrundbilder=[b,...v.hintergrundbilder.filter(x=>x.id!==id)]; }

  // ── DRAG & RESIZE ────────────────────────────────────────────────────────
  function getScale() { return a4El ? a4El.getBoundingClientRect().width / A4W : 1; }

  function onBildMousedown(e, bild) {
    if (e.target.classList.contains('rw-rz')) return;
    e.preventDefault();
    e.stopPropagation();
    dragging = { id:bild.id, startX:e.clientX, startY:e.clientY, origX:bild.x, origY:bild.y, scale:getScale() };
  }
  function onResizeMousedown(e, bild, dir) {
    e.preventDefault(); e.stopPropagation();
    resizing = {
      id:bild.id, dir,
      startX:e.clientX, startY:e.clientY,
      origW:bild.breite, origH:bild.hoehe || bild.breite,
      origX:bild.x, origY:bild.y,
      scale:getScale(),
      natW:bild.nat_w||1, natH:bild.nat_h||1,
      verhSperren:bild.verh_sperren,
    };
  }

  // FIX: document-level mousemove — funktioniert auch außerhalb des scroll-containers
  function onDocMousemove(e) {
    if (dragging) {
      const dx = (e.clientX-dragging.startX)/dragging.scale;
      const dy = (e.clientY-dragging.startY)/dragging.scale;
      updateBild(dragging.id, 'x', Math.round(dragging.origX+dx));
      updateBild(dragging.id, 'y', Math.round(dragging.origY+dy));
    }
    if (resizing) {
      const dx = (e.clientX-resizing.startX)/resizing.scale;
      const dy = (e.clientY-resizing.startY)/resizing.scale;
      const d = resizing.dir;
      let nw=resizing.origW, nh=resizing.origH, nx=resizing.origX, ny=resizing.origY;
      if (d.includes('e')) nw = Math.max(10, resizing.origW+dx);
      if (d.includes('w')) { nw = Math.max(10, resizing.origW-dx); nx = resizing.origX+(resizing.origW-nw); }
      if (d.includes('s')) nh = Math.max(10, resizing.origH+dy);
      if (d.includes('n')) { nh = Math.max(10, resizing.origH-dy); ny = resizing.origY+(resizing.origH-nh); }
      if (resizing.verhSperren) {
        const ratio = resizing.natW / resizing.natH;
        if (d.includes('e')||d.includes('w')) { nh=Math.round(nw/ratio); if(d.includes('n')) ny=resizing.origY+(resizing.origH-nh); }
        else { nw=Math.round(nh*ratio); if(d.includes('w')) nx=resizing.origX+(resizing.origW-nw); }
      }
      v.hintergrundbilder = v.hintergrundbilder.map(b =>
        b.id===resizing.id ? {...b, breite:Math.round(nw), hoehe:Math.round(nh), x:Math.round(nx), y:Math.round(ny)} : b
      );
    }
  }

  function applyTheme(c) { v.akzentfarbe=c; v.tabelle.kopf_hg=c; scheduleAutoSave(); }

  const themen=[
    {n:'Schwarz',c:'#1a1a1a'},{n:'Blau',c:'#1d4ed8'},{n:'Grün',c:'#15803d'},
    {n:'Rot',c:'#b91c1c'},{n:'Lila',c:'#6d28d9'},{n:'Orange',c:'#c2410c'},
    {n:'Petrol',c:'#0e7490'},{n:'Gold',c:'#92400e'},
  ];
  const badgeThemen=[
    {n:'Grün',f:'#16a34a',h:'#f0fdf4',r:'#86efac'},{n:'Blau',f:'#1d4ed8',h:'#eff6ff',r:'#93c5fd'},
    {n:'Grau',f:'#374151',h:'#f9fafb',r:'#d1d5db'},{n:'Orange',f:'#c2410c',h:'#fff7ed',r:'#fed7aa'},
  ];
  const schriften=['Arial','Helvetica','Georgia','Times New Roman','Verdana','Garamond','Courier New','Poppins','Roboto','Lato','Montserrat','Open Sans','Raleway','Nunito','Playfair Display'];
  function logoJustify() { return v.logo.position==='links'?'flex-start':v.logo.position==='rechts'?'flex-end':'center'; }

  function bildWrapStyle(bild) {
    const h = bild.hoehe || (bild.nat_h&&bild.nat_w ? Math.round(bild.breite*bild.nat_h/bild.nat_w) : bild.breite);
    // Im Bilder-Tab: Bilder über Inhalt-Layer (z-index 15+), sonst darunter (z-index 1+)
    const zi = aktivesTab === 'bilder' ? 15 + v.hintergrundbilder.indexOf(bild) : 1 + v.hintergrundbilder.indexOf(bild);
    return `left:${bild.x}px;top:${bild.y}px;width:${bild.breite}px;height:${h}px;opacity:${bild.opacity};z-index:${zi};`;
  }
  function bildImgStyle(bild) {
    const fit = bild.modus==='crop' ? 'cover' : 'fill';
    return `width:100%;height:100%;object-fit:${fit};display:block;pointer-events:none;user-select:none;`;
  }
  function bildHoehe(bild) {
    return Math.round(bild.hoehe || (bild.nat_h&&bild.nat_w ? bild.breite*bild.nat_h/bild.nat_w : bild.breite));
  }
</script>

<!-- FIX: kein onmousemove/onmouseup auf rw-div — läuft über document (siehe onMount) -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="rw">

  <!-- TOOLBAR -->
  <div class="rw-bar">
    <div class="rw-bar-l">
      <b class="rw-title">🧾 Rechnungsvorlage</b>
      <div class="sep"></div>
      <button class="rw-tab" class:act={aktivesTab==='inhalt'} onclick={()=>aktivesTab='inhalt'}>📝 Text</button>
      <button class="rw-tab" class:act={aktivesTab==='layout'} onclick={()=>aktivesTab='layout'}>🎨 Layout</button>
      <button class="rw-tab" class:act={aktivesTab==='bilder'} onclick={()=>aktivesTab='bilder'}>🖼 Bilder</button>
    </div>
    <div class="rw-bar-r">
      {#if autoSaveStatus === 'speichert'}
        <span class="rw-autosave rw-autosave-act">⏳ Speichert…</span>
      {:else if autoSaveStatus === 'gespeichert'}
        <span class="rw-autosave rw-autosave-ok">✓ Auto-gespeichert</span>
      {:else if hatUngespeicherteAenderungen}
        <span class="rw-autosave rw-autosave-pending">● Ungespeichert</span>
      {/if}
      <label class="rw-check"><input type="checkbox" bind:checked={v.zahlung_sichtbar} onchange={scheduleAutoSave}/> Badge</label>
      <label class="rw-check"><input type="checkbox" bind:checked={v.summen.kleinunternehmer} onchange={scheduleAutoSave}/> §19</label>
      {#if zeigtPDF}
        <button class="rw-btn" onclick={()=>zeigtPDF=false}>← Editor</button>
      {:else}
        <button class="rw-btn" onclick={pdfVorschau} disabled={pdfLaeuft}>{pdfLaeuft?'⏳':'🖨'} PDF</button>
      {/if}
      <button class="rw-btn rw-save" onclick={speichern} disabled={speichertLaeuft}>
        {speichertLaeuft?'Speichert…':'💾 Speichern'}
      </button>
    </div>
  </div>

  <!-- ═══ PANEL TEXT ═══════════════════════════════════════════════════════ -->
  {#if aktivesTab==='inhalt'}
  <div class="rw-panel">
    <div class="rw-panel-group">
      <span class="rw-lbl-head">GLOBAL</span>
      <span class="rw-lbl">Schrift</span>
      <select class="rw-sel" bind:value={v.schriftart} style="font-family:'{v.schriftart}',sans-serif;">
        {#each schriften as f}<option style="font-family:'{f}',sans-serif;">{f}</option>{/each}
      </select>
      <span class="rw-lbl">Gr.</span>
      <input type="number" class="rw-num" min="7" max="20" bind:value={v.schriftgroesse}/>pt
      <span class="rw-lbl">Zeilenabst.</span>
      <select class="rw-sel" bind:value={v.zeilenabstand} onchange={(e)=>applyZeilenabstand(+e.target.value)}>
        {#each [1.0,1.2,1.4,1.5,1.6,1.8,2.0,2.4] as z}<option value={z}>{z}</option>{/each}
      </select>
    </div>
    <div class="sep-v"></div>
    <div class="rw-panel-group" class:dim={!hatAuswahl}>
      <span class="rw-lbl-head" style="color:{hatAuswahl?'#2563eb':'#aaa'};">{hatAuswahl ? '✂️ AUSWAHL' : '✂️ AUSWAHL (markieren)'}</span>
      <button class="rw-fmt-btn" title="Fett" onclick={applyFett}><b>B</b></button>
      <button class="rw-fmt-btn" title="Kursiv" onclick={applyKursiv}><i>I</i></button>
      <button class="rw-fmt-btn" title="Unterstrichen" onclick={applyUnter}><u>U</u></button>
      <span class="rw-lbl">Gr.</span>
      <input type="number" class="rw-num" min="6" max="72" bind:value={auswahlGroesse} onchange={(e)=>applyFontSize(+e.target.value)}/>px
      <span class="rw-lbl">Farbe</span>
      <input type="color" class="rw-color-pick" title="Textfarbe" onchange={(e)=>applyFarbe(e.target.value)}/>
      <button class="rw-fmt-btn rw-fmt-clear" title="Format löschen" onclick={clearFormat}>✕ Clear</button>
    </div>
    <div class="sep-v"></div>
    <div class="rw-panel-group">
      <span class="rw-lbl-head">AUSRICHTUNG</span>
      <button class="rw-fmt-btn" title="Linksbündig" onclick={()=>applyAusrichtung('Left')}>
        <svg width="14" height="12" viewBox="0 0 14 12"><rect x="0" y="0" width="14" height="2" fill="currentColor"/><rect x="0" y="4" width="10" height="2" fill="currentColor"/><rect x="0" y="8" width="14" height="2" fill="currentColor"/></svg>
      </button>
      <button class="rw-fmt-btn" title="Zentriert" onclick={()=>applyAusrichtung('Center')}>
        <svg width="14" height="12" viewBox="0 0 14 12"><rect x="0" y="0" width="14" height="2" fill="currentColor"/><rect x="2" y="4" width="10" height="2" fill="currentColor"/><rect x="0" y="8" width="14" height="2" fill="currentColor"/></svg>
      </button>
      <button class="rw-fmt-btn" title="Rechtsbündig" onclick={()=>applyAusrichtung('Right')}>
        <svg width="14" height="12" viewBox="0 0 14 12"><rect x="0" y="0" width="14" height="2" fill="currentColor"/><rect x="4" y="4" width="10" height="2" fill="currentColor"/><rect x="0" y="8" width="14" height="2" fill="currentColor"/></svg>
      </button>
      <button class="rw-fmt-btn" title="Blocksatz" onclick={()=>applyAusrichtung('Full')}>
        <svg width="14" height="12" viewBox="0 0 14 12"><rect x="0" y="0" width="14" height="2" fill="currentColor"/><rect x="0" y="4" width="14" height="2" fill="currentColor"/><rect x="0" y="8" width="14" height="2" fill="currentColor"/></svg>
      </button>
    </div>
    <div class="sep-v"></div>
    <div class="rw-panel-group">
      <span class="rw-lbl-head">BADGE</span>
      <button class="rw-tab" class:act={v.zahlung_stil==='badge'} onclick={()=>v.zahlung_stil='badge'}>Badge</button>
      <button class="rw-tab" class:act={v.zahlung_stil==='text'} onclick={()=>v.zahlung_stil='text'}>Text</button>
      {#if v.zahlung_stil==='badge'}
        {#each badgeThemen as bt}
          <button class="rw-dot" style="background:{bt.h};border:2px solid {bt.r};" class:act={v.zahlung_farbe===bt.f}
            onclick={()=>{v.zahlung_farbe=bt.f;v.zahlung_hg=bt.h;v.zahlung_rahmen=bt.r;}} title={bt.n}></button>
        {/each}
      {/if}
    </div>
    {#if aktiverBlock}
      <div class="sep-v"></div>
      <span class="rw-hint">✏️ <b>{aktiverBlock}</b></span>
    {/if}
  </div>

  <!-- ═══ PANEL LAYOUT ═════════════════════════════════════════════════════ -->
  {:else if aktivesTab==='layout'}
  <div class="rw-panel">
    <div class="rw-panel-group">
      <span class="rw-lbl-head">FARBTHEMA</span>
      {#each themen as t}
        <button class="rw-dot" style="background:{t.c};" class:act={v.akzentfarbe===t.c} onclick={()=>applyTheme(t.c)} title={t.n}></button>
      {/each}
      <input type="color" class="rw-color-pick" bind:value={v.akzentfarbe} oninput={()=>v.tabelle.kopf_hg=v.akzentfarbe}/>
    </div>
    <div class="sep-v"></div>
    <div class="rw-panel-group">
      <span class="rw-lbl-head">SEITENRAND</span>
      <input type="number" class="rw-num" min="10" max="60" bind:value={v.seitenrand}/>px
    </div>
    <div class="sep-v"></div>
    <div class="rw-panel-group">
      <span class="rw-lbl-head">LOGO</span>
      <label class="rw-btn">{v.logo.base64?'🔄':'🖼'} Logo
        <input type="file" accept="image/*" onchange={handleLogoUpload} style="display:none"/>
      </label>
      {#if v.logo.base64}
        <input type="number" class="rw-num" min="40" max="400" bind:value={v.logo.breite}/>px
        <button class="rw-tab" class:act={v.logo.position==='links'} onclick={()=>{v.logo.position='links';scheduleAutoSave();}}>◀</button>
        <button class="rw-tab" class:act={v.logo.position==='mitte'} onclick={()=>{v.logo.position='mitte';scheduleAutoSave();}}>▬</button>
        <button class="rw-tab" class:act={v.logo.position==='rechts'} onclick={()=>{v.logo.position='rechts';scheduleAutoSave();}}>▶</button>
        <button class="rw-btn rw-btn-x" onclick={()=>v.logo.base64=''}>✕</button>
      {/if}
    </div>
    <div class="sep-v"></div>
    <div class="rw-panel-group">
      <span class="rw-lbl-head">FOOTER</span>
      {#each [1,2,3,4] as n}
        <button class="rw-tab" class:act={v.footer_spalten===n} onclick={()=>{v.footer_spalten=n;scheduleAutoSave();}}>{n}Sp</button>
      {/each}
      <label class="rw-check"><input type="checkbox" bind:checked={v.footer_trennlinie} onchange={scheduleAutoSave}/> Linie</label>
      <span class="rw-lbl">Gr.</span>
      <input type="number" class="rw-num" min="6" max="14" bind:value={v.footer_schriftgroesse}/>pt
      <span class="rw-lbl">Zeil.</span>
      <select class="rw-sel" bind:value={v.footer_zeilenabstand}>
        {#each [1.0,1.2,1.4,1.5,1.6,1.8,2.0] as z}<option value={z}>{z}</option>{/each}
      </select>
    </div>
    <div class="sep-v"></div>
    <div class="rw-panel-group">
      <span class="rw-lbl-head">TABELLE</span>
      <label><input type="checkbox" bind:checked={v.tabelle.zeige_artnr}/> Art-Nr.</label>
      <label><input type="checkbox" bind:checked={v.tabelle.zeige_menge}/> Menge</label>
      <label><input type="checkbox" bind:checked={v.tabelle.zeige_ep}/> EP</label>
      <label><input type="checkbox" bind:checked={v.tabelle.zeige_betrag}/> Betrag</label>
      <span class="rw-lbl">Sum.B.</span>
      <input type="number" class="rw-num" min="150" max="450" bind:value={v.summen.breite}/>px
    </div>
  </div>

  <!-- ═══ PANEL BILDER ═════════════════════════════════════════════════════ -->
  {:else if aktivesTab==='bilder'}
  <div class="rw-panel">
    <div class="rw-panel-group">
      <span class="rw-lbl-head">BILDER</span>
      <label class="rw-btn rw-btn-prim">➕ Bild(er)
        <input type="file" accept="image/*" multiple onchange={addBilder} style="display:none"/>
      </label>
      <span class="rw-hint-idle">Drag &amp; Drop auf Seite · Handles skalieren · Volle Seite = A4</span>
    </div>
    {#if v.hintergrundbilder.length > 0}
      <div class="sep-v"></div>
      <div class="rw-panel-group rw-bilder-liste">
        {#each v.hintergrundbilder as bild, i}
          <div class="rw-bild-row">
            <img src={bild.base64} alt="" class="rw-bild-thumb"/>
            <span class="rw-lbl rw-bild-nr">#{i+1}</span>
            <button class="rw-tab rw-tab-sm" class:act={!bild.modus||bild.modus==='frei'}
              onclick={()=>setBildFrei(bild.id)}>Frei</button>
            <button class="rw-tab rw-tab-sm rw-tab-full" class:act={bild.modus==='vollseite'}
              onclick={()=>setBildVollseite(bild.id)}>⛶ Voll</button>
            <button class="rw-tab rw-tab-sm rw-tab-crop" class:act={bild.modus==='crop'}
              onclick={()=>setBildA4Crop(bild.id)}>✂ Crop</button>
            <div class="sep-v" style="height:20px;"></div>
            <span class="rw-lbl">B:</span>
            <input type="number" class="rw-num rw-num-sm" min="10" max="1200"
              value={Math.round(bild.breite)} oninput={(e)=>updateBreite(bild.id,+e.target.value)}
              disabled={bild.modus==='vollseite'}/>
            <span class="rw-lbl">H:</span>
            <input type="number" class="rw-num rw-num-sm" min="10" max="2000"
              value={bildHoehe(bild)} oninput={(e)=>updateHoehe(bild.id,+e.target.value)}
              disabled={bild.modus==='vollseite'}/>
            <button class="rw-fmt-btn"
              style={bild.verh_sperren?'color:#1d4ed8;border-color:#93c5fd;':''}
              onclick={()=>updateBild(bild.id,'verh_sperren',!bild.verh_sperren)}
              disabled={bild.modus==='vollseite'}>🔗</button>
            <div class="sep-v" style="height:20px;"></div>
            <span class="rw-lbl">Tr.:</span>
            <input type="range" min="0.03" max="1" step="0.03" value={bild.opacity}
              oninput={(e)=>updateBild(bild.id,'opacity',+e.target.value)} style="width:55px;"/>
            <span class="rw-lbl" style="min-width:28px;">{Math.round(bild.opacity*100)}%</span>
            <button class="rw-fmt-btn" onclick={()=>bringFront(bild.id)}>↑</button>
            <button class="rw-fmt-btn" onclick={()=>sendBack(bild.id)}>↓</button>
            <button class="rw-btn rw-btn-x" onclick={()=>removeBild(bild.id)}>🗑</button>
          </div>
        {/each}
      </div>
    {/if}
  </div>
  {/if}

  <!-- ═══════════════════════════ CANVAS ═══════════════════════════════════ -->
  <div class="rw-canvas">
    {#if zeigtPDF && vorschauPDF}
      <iframe src="data:application/pdf;base64,{vorschauPDF}" title="PDF" class="rw-pdf"></iframe>
    {:else}

    <div class="rw-a4" bind:this={a4El} style="
      font-family:'{v.schriftart}',sans-serif;
      font-size:{v.schriftgroesse}px;
      --ak:{v.akzentfarbe};
      --rand:{v.seitenrand}px;
    ">

      <!-- Hintergrundbilder -->
      {#each v.hintergrundbilder as bild}
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="rw-bild-wrap" style={bildWrapStyle(bild)} onmousedown={(e)=>onBildMousedown(e,bild)}>
          <img src={bild.base64} alt="" style={bildImgStyle(bild)}/>
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div class="rw-rz nw" onmousedown={(e)=>onResizeMousedown(e,bild,'nw')}></div>
          <div class="rw-rz n"  onmousedown={(e)=>onResizeMousedown(e,bild,'n')}></div>
          <div class="rw-rz ne" onmousedown={(e)=>onResizeMousedown(e,bild,'ne')}></div>
          <div class="rw-rz e"  onmousedown={(e)=>onResizeMousedown(e,bild,'e')}></div>
          <div class="rw-rz se" onmousedown={(e)=>onResizeMousedown(e,bild,'se')}></div>
          <div class="rw-rz s"  onmousedown={(e)=>onResizeMousedown(e,bild,'s')}></div>
          <div class="rw-rz sw" onmousedown={(e)=>onResizeMousedown(e,bild,'sw')}></div>
          <div class="rw-rz w"  onmousedown={(e)=>onResizeMousedown(e,bild,'w')}></div>
        </div>
      {/each}

      <!-- Inhalt: im Bilder-Tab pointer-events:none → Klicks gehen durch zum Bild-Wrap -->
      <div class="rw-inhalt" style={aktivesTab==='bilder' ? 'pointer-events:none;' : ''}>

        {#if v.logo.base64}
          <div style="display:flex;justify-content:{logoJustify()};padding:var(--rand) var(--rand) 0;">
            <label style="cursor:pointer;pointer-events:auto;" title="Klicken zum Wechseln">
              <input type="file" accept="image/*" onchange={handleLogoUpload} style="display:none"/>
              <img src={v.logo.base64} alt="Logo" style="width:{v.logo.breite}px;max-height:100px;object-fit:contain;display:block;"/>
            </label>
          </div>
        {:else if aktivesTab==='layout'}
          <div style="display:flex;justify-content:{logoJustify()};padding:var(--rand) var(--rand) 0;">
            <label class="rw-logo-drop" style="pointer-events:auto;">
              <input type="file" accept="image/*" onchange={handleLogoUpload} style="display:none"/>🖼 Logo
            </label>
          </div>
        {/if}

        <div class="rw-header" style="padding:{v.logo.base64?'10px':'var(--rand)'} var(--rand) 0;">
          <div class="rw-hl">
            <div class="rw-e" style="font-size:8px;color:#888;margin-bottom:8px;display:block;line-height:1.4;"
              contenteditable="true" bind:this={elAbsender}
              onfocus={()=>aktiverBlock='Absenderzeile'} onblur={(e)=>saveBlur('t_absender',e)}
              data-ph="Absenderzeile"></div>
            <div class="rw-e" style="line-height:{v.zeilenabstand};display:block;"
              contenteditable="true" bind:this={elEmpfaenger}
              onfocus={()=>aktiverBlock='Empfänger-Adresse'} onblur={(e)=>saveBlur('t_empfaenger',e)}
              data-ph="Empfänger-Adresse"></div>
          </div>
          <div class="rw-e" style="line-height:{v.zeilenabstand};text-align:right;min-width:180px;max-width:240px;"
            contenteditable="true" bind:this={elKontakt}
            onfocus={()=>aktiverBlock='Kontakt-Block'} onblur={(e)=>saveBlur('t_kontakt',e)}
            data-ph="Kontakt-Block"></div>
        </div>

        <div style="padding:14px var(--rand) 0;"><hr style="border:none;border-top:1px solid #bbb;margin:0;"/></div>

        <div class="rw-body" style="padding:14px var(--rand) 0;">
          <div class="rw-e" style="line-height:{v.zeilenabstand};margin-bottom:12px;display:block;"
            contenteditable="true" bind:this={elEinleitung}
            onfocus={()=>aktiverBlock='Einleitung'} onblur={(e)=>saveBlur('t_einleitung',e)}
            data-ph="Einleitungstext"></div>

          <div style="margin:14px 0 2px;">
            <div style="font-size:{v.schriftgroesse+4}px;font-weight:700;color:#1a1a1a;">Rechnung {B.rechnung_nr}</div>
            <div style="font-size:{Math.max(7,v.schriftgroesse-2)}px;color:#999;margin-bottom:12px;">Das Rechnungsdatum entspricht dem Leistungsdatum</div>
          </div>

          <table class="rw-table">
            <thead>
              <tr style="background:{v.tabelle.kopf_hg};">
                <th class="rw-th" style="color:{v.tabelle.kopf_farbe};width:32px;">Pos</th>
                {#if v.tabelle.zeige_artnr}<th class="rw-th" style="color:{v.tabelle.kopf_farbe};width:68px;">Art-Nr.</th>{/if}
                <th class="rw-th" style="color:{v.tabelle.kopf_farbe};">Bezeichnung</th>
                {#if v.tabelle.zeige_menge}<th class="rw-th rw-thr" style="color:{v.tabelle.kopf_farbe};width:54px;">Menge</th>{/if}
                {#if v.tabelle.zeige_ep}<th class="rw-th rw-thr" style="color:{v.tabelle.kopf_farbe};width:90px;">Einzelpreis</th>{/if}
                {#if v.tabelle.zeige_betrag}<th class="rw-th rw-thr" style="color:{v.tabelle.kopf_farbe};width:78px;">Betrag</th>{/if}
              </tr>
            </thead>
            <tbody>
              <tr style="border-bottom:1px solid #e2e8f0;">
                <td class="rw-td">1</td>
                {#if v.tabelle.zeige_artnr}<td class="rw-td" style="color:#666;">{B.artikel_nr}</td>{/if}
                <td class="rw-td">{B.artikel_name}</td>
                {#if v.tabelle.zeige_menge}<td class="rw-td rw-tdr">{B.menge}</td>{/if}
                {#if v.tabelle.zeige_ep}<td class="rw-td rw-tdr">{fmtN(B.einzelpreis)}</td>{/if}
                {#if v.tabelle.zeige_betrag}<td class="rw-td rw-tdr">{fmtN(B.einzelpreis)} €</td>{/if}
              </tr>
            </tbody>
          </table>

          <div style="width:{v.summen.breite}px;margin-left:auto;margin-bottom:16px;">
            <table class="rw-sum">
              <tbody>
                <tr><td class="rw-sl">Nettobetrag</td><td class="rw-sr">{fmtN(B.netto_betrag)} €</td></tr>
                {#if v.summen.kleinunternehmer}
                  <tr><td colspan="2" style="padding:4px 8px;font-size:9px;color:#888;font-style:italic;">Gemäß §19 UStG keine Umsatzsteuer.</td></tr>
                {:else}
                  <tr><td class="rw-sl">Umsatzsteuer {B.steuersatz}%</td><td class="rw-sr">{fmtN(B.steuer_betrag)} €</td></tr>
                {/if}
                <tr class="rw-stotal">
                  <td class="rw-sl" style="font-weight:700;">Rechnungsbetrag</td>
                  <td class="rw-sr" style="font-weight:700;">{fmtN(B.brutto_betrag)} €</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="rw-e" style="line-height:{v.zeilenabstand};margin-bottom:12px;display:block;"
            contenteditable="true" bind:this={elAbschluss}
            onfocus={()=>aktiverBlock='Abschlusstext'} onblur={(e)=>saveBlur('t_abschluss',e)}
            data-ph="Abschlusstext"></div>

          {#if v.zahlung_sichtbar}
            <div style="margin-top:14px;">
              {#if v.zahlung_stil==='badge'}
                <div class="rw-e rw-badge" contenteditable="true" bind:this={elZahlung}
                  onfocus={()=>aktiverBlock='Bezahlt-Badge'} onblur={(e)=>saveBlur('t_zahlung',e)}
                  data-ph="Bezahlt-Text"
                  style="color:{v.zahlung_farbe};background:{v.zahlung_hg};border-color:{v.zahlung_rahmen};"></div>
              {:else}
                <div class="rw-e" style="line-height:{v.zeilenabstand};" contenteditable="true" bind:this={elZahlung}
                  onfocus={()=>aktiverBlock='Bezahlt-Text'} onblur={(e)=>saveBlur('t_zahlung',e)}
                  data-ph="Bezahlt-Text"></div>
              {/if}
            </div>
          {/if}
        </div>

        <div class="rw-footer" style="
          padding:8px var(--rand);
          grid-template-columns:repeat({v.footer_spalten},1fr);
          border-top:{v.footer_trennlinie?'1px solid #ccc':'none'};
          font-size:{v.footer_schriftgroesse}px;
          line-height:{v.footer_zeilenabstand};
        ">
          {#each Array(v.footer_spalten) as _,i}
            <div class="rw-e rw-fcol" contenteditable="true" bind:this={elFooter[i]}
              onfocus={()=>aktiverBlock=`Footer Sp.${i+1}`} onblur={(e)=>saveFooter(i,e)}
              data-ph="Footer Spalte {i+1}"></div>
          {/each}
        </div>

      </div>
    </div>
    {/if}
  </div>
</div>

<style>
  .rw{display:flex;flex-direction:column;height:100%;width:100%;background:#d4d8de;overflow:hidden;}
  .rw-bar{display:flex;align-items:center;justify-content:space-between;padding:4px 14px;background:#fff;border-bottom:1px solid #ddd;flex-shrink:0;gap:5px;flex-wrap:wrap;min-height:42px;box-shadow:0 1px 4px rgba(0,0,0,0.07);}
  .rw-bar-l,.rw-bar-r{display:flex;align-items:center;gap:5px;flex-wrap:wrap;}
  .rw-panel{display:flex;align-items:center;gap:0;flex-wrap:wrap;padding:5px 14px;background:#f8fafc;border-bottom:1px solid #e9ecef;flex-shrink:0;font-size:0.71rem;color:#555;overflow-x:auto;}
  .rw-panel-group{display:flex;align-items:center;gap:5px;flex-wrap:wrap;padding:2px 8px;}
  .rw-panel label{display:flex;align-items:center;gap:3px;cursor:pointer;}
  .rw-panel input[type=checkbox]{accent-color:#1d4ed8;}
  .rw-bilder-liste{flex-direction:column;align-items:flex-start;gap:4px;}
  .dim{opacity:0.45;}
  .rw-lbl-head{font-size:0.62rem;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;white-space:nowrap;margin-right:2px;}
  .rw-hint{color:#2563eb;font-size:0.7rem;}
  .rw-hint-idle{color:#94a3b8;font-size:0.7rem;font-style:italic;}
  .rw-bild-row{display:flex;align-items:center;gap:4px;background:#fff;border:1px solid #e2e8f0;border-radius:5px;padding:3px 8px;flex-wrap:wrap;}
  .rw-bild-thumb{width:28px;height:22px;object-fit:cover;border-radius:2px;border:1px solid #e2e8f0;flex-shrink:0;}
  .rw-bild-nr{font-weight:700;color:#64748b;min-width:20px;}
  .sep-v{width:1px;height:32px;background:#e2e8f0;flex-shrink:0;margin:0 2px;}
  .rw-lbl{font-size:0.71rem;color:#777;white-space:nowrap;}
  .rw-sel{border:1px solid #ddd;border-radius:4px;padding:2px 4px;font-size:0.73rem;background:#fff;color:#333;cursor:pointer;outline:none;}
  .rw-num{width:44px;border:1px solid #ddd;border-radius:4px;padding:2px 4px;font-size:0.73rem;background:#fff;color:#333;outline:none;}
  .rw-num-sm{width:52px;}
  .rw-num:disabled{background:#f3f4f6;color:#aaa;cursor:not-allowed;}
  .rw-color-pick{width:24px;height:24px;padding:0;border:1px solid #ddd;border-radius:4px;cursor:pointer;background:none;}
  .rw-dot{width:16px;height:16px;border-radius:50%;border:1.5px solid rgba(0,0,0,0.15);cursor:pointer;flex-shrink:0;transition:transform 0.1s;}
  .rw-dot:hover{transform:scale(1.3);}
  .rw-dot.act{outline:2.5px solid #111;outline-offset:2px;}
  .rw-tab{background:transparent;border:1px solid #ddd;border-radius:4px;padding:2px 7px;font-size:0.72rem;font-weight:500;color:#555;cursor:pointer;white-space:nowrap;transition:all 0.1s;}
  .rw-tab:hover{border-color:#999;color:#222;}
  .rw-tab.act{background:#1d4ed8;color:#fff;border-color:#1d4ed8;}
  .rw-tab-sm{padding:2px 5px;font-size:0.68rem;}
  .rw-tab-full{border-color:#7c3aed;color:#7c3aed;}
  .rw-tab-full:hover{background:#f5f3ff;}
  .rw-tab-full.act{background:#7c3aed;color:#fff;border-color:#7c3aed;}
  .rw-tab-crop{border-color:#0e7490;color:#0e7490;}
  .rw-tab-crop:hover{background:#ecfeff;}
  .rw-tab-crop.act{background:#0e7490;color:#fff;border-color:#0e7490;}
  .rw-fmt-btn{background:#fff;border:1px solid #ddd;border-radius:3px;padding:2px 7px;font-size:0.73rem;cursor:pointer;min-width:24px;height:24px;display:flex;align-items:center;justify-content:center;transition:all 0.1s;user-select:none;}
  .rw-fmt-btn:hover{background:#e8f0fe;border-color:#93c5fd;}
  .rw-fmt-btn:active{background:#dbeafe;}
  .rw-fmt-btn:disabled{opacity:0.4;cursor:not-allowed;}
  .rw-fmt-clear{color:#ef4444;border-color:#fca5a5;font-size:0.65rem;}
  .rw-btn{background:transparent;border:1px solid #ddd;border-radius:4px;padding:3px 8px;font-size:0.73rem;color:#555;cursor:pointer;display:flex;align-items:center;gap:3px;font-family:inherit;transition:all 0.12s;white-space:nowrap;}
  .rw-btn:hover{border-color:#999;color:#222;}
  .rw-btn-x{color:#ef4444;border-color:#fca5a5;padding:2px 6px;}
  .rw-btn-x:hover{background:#fef2f2;}
  .rw-btn-prim{background:#1d4ed8;color:#fff;border-color:#1d4ed8;font-weight:600;}
  .rw-btn-prim:hover{filter:brightness(1.1);}
  .rw-save{background:#1d4ed8;color:#fff;border-color:#1d4ed8;font-weight:600;}
  .rw-save:hover{filter:brightness(1.08);}
  .rw-save:disabled{opacity:0.55;cursor:not-allowed;}
  .rw-autosave{font-size:0.7rem;padding:2px 8px;border-radius:10px;white-space:nowrap;}
  .rw-autosave-act{color:#92400e;background:#fef3c7;}
  .rw-autosave-ok{color:#15803d;background:#f0fdf4;}
  .rw-autosave-pending{color:#6b7280;background:#f3f4f6;}
  .rw-check{display:flex;align-items:center;gap:4px;font-size:0.73rem;color:#555;cursor:pointer;white-space:nowrap;}
  .rw-check input{accent-color:#1d4ed8;}
  .rw-title{font-size:0.84rem;font-weight:700;color:#1e293b;white-space:nowrap;}
  .rw-canvas{flex:1;overflow-y:auto;overflow-x:auto;padding:24px 20px 40px;display:flex;flex-direction:column;align-items:center;}
  .rw-a4{width:794px;min-height:1123px;background:#fff;box-shadow:0 4px 32px rgba(0,0,0,0.17);border-radius:2px;position:relative;display:flex;flex-direction:column;flex-shrink:0;overflow:hidden;}
  .rw-bild-wrap{position:absolute;cursor:move;}
  .rw-bild-wrap:hover{outline:1px dashed rgba(29,78,216,0.4);}
  .rw-rz{position:absolute;width:10px;height:10px;background:#1d4ed8;border:1.5px solid #fff;border-radius:2px;z-index:20;pointer-events:auto !important;}
  .rw-rz.nw{top:-5px;left:-5px;cursor:nw-resize;}
  .rw-rz.n{top:-5px;left:calc(50% - 5px);cursor:n-resize;}
  .rw-rz.ne{top:-5px;right:-5px;cursor:ne-resize;}
  .rw-rz.e{top:calc(50% - 5px);right:-5px;cursor:e-resize;}
  .rw-rz.se{bottom:-5px;right:-5px;cursor:se-resize;}
  .rw-rz.s{bottom:-5px;left:calc(50% - 5px);cursor:s-resize;}
  .rw-rz.sw{bottom:-5px;left:-5px;cursor:sw-resize;}
  .rw-rz.w{top:calc(50% - 5px);left:-5px;cursor:w-resize;}
  .rw-inhalt{position:relative;z-index:10;display:flex;flex-direction:column;flex:1;}
  .rw-logo-drop{display:flex;align-items:center;justify-content:center;height:46px;min-width:100px;background:#f1f5f9;border:2px dashed #cbd5e1;border-radius:5px;font-size:0.73rem;color:#94a3b8;cursor:pointer;transition:all 0.15s;}
  .rw-logo-drop:hover{border-color:#1d4ed8;color:#1d4ed8;}
  .rw-header{display:grid;grid-template-columns:1fr auto;gap:24px;align-items:flex-start;}
  .rw-hl{display:flex;flex-direction:column;}
  .rw-body{flex:1;}
  .rw-table{width:100%;border-collapse:collapse;}
  .rw-th{padding:7px 10px;text-align:left;font-size:11px;font-weight:700;}
  .rw-thr{text-align:right;}
  .rw-td{padding:8px 10px;font-size:11px;color:#1a1a1a;vertical-align:top;}
  .rw-tdr{text-align:right;}
  .rw-sum{width:100%;border-collapse:collapse;border-top:1px solid #ccc;}
  .rw-sl{padding:5px 8px;font-size:11px;color:#555;text-align:right;}
  .rw-sr{padding:5px 8px;font-size:11px;color:#1a1a1a;text-align:right;white-space:nowrap;}
  .rw-stotal{border-top:1px solid #1a1a1a;border-bottom:2px solid #1a1a1a;}
  .rw-stotal .rw-sl,.rw-stotal .rw-sr{font-size:12px;padding:6px 8px;}
  .rw-badge{display:inline-block;border:1.5px solid;border-radius:5px;padding:4px 14px;font-size:11px;font-weight:700;cursor:text;}
  .rw-footer{margin-top:auto;display:grid;gap:10px;flex-shrink:0;}
  .rw-fcol{color:#333;white-space:pre-wrap;word-break:break-word;min-height:28px;}
  :global(.rw-e){outline:none;border-radius:2px;transition:background 0.1s,box-shadow 0.1s;min-height:1.2em;white-space:pre-wrap;word-break:break-word;cursor:text;}
  :global(.rw-e:hover){background:rgba(29,78,216,0.04);box-shadow:0 0 0 1px rgba(29,78,216,0.2);}
  :global(.rw-e:focus){background:rgba(29,78,216,0.06);box-shadow:0 0 0 2px rgba(29,78,216,0.35);}
  :global(.rw-e:empty::before){content:attr(data-ph);color:#c0c7d0;font-style:italic;pointer-events:none;}
  .rw-pdf{width:794px;height:1123px;flex-shrink:0;background:#fff;border:none;border-radius:2px;box-shadow:0 4px 28px rgba(0,0,0,0.18);}
  @media(max-width:860px){.rw-a4,.rw-pdf{width:100%;min-width:0;}}
</style>
