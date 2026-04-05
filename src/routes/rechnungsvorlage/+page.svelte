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

  let v = $state({
    schriftart: 'Arial',
    schriftgroesse: 11,       // globale Basis-Schriftgröße
    zeilenabstand: 1.6,       // globaler Zeilenabstand
    akzentfarbe: '#1d4ed8',
    seitenrand: 28,
    logo: { base64:'', breite:130, position:'links' },
    hintergrundbilder: [],
    wasserzeichen_sichtbar: false,
    zahlung_sichtbar: true,
    zahlung_stil: 'badge',
    zahlung_farbe: '#16a34a', zahlung_hg: '#f0fdf4', zahlung_rahmen: '#86efac',
    // Footer KOMPLETT getrennt von globaler Schriftgröße
    footer_spalten: 4,
    footer_trennlinie: true,
    footer_schriftgroesse: 8,   // NUR für Footer, unabhängig
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

  // Gespeicherte Selektion — KERN des Fixes für markierten Text
  let savedRange = null;
  // Zeigt was gerade selektiert ist
  let hatAuswahl = $state(false);
  let auswahlGroesse = $state(11);

  let elAbsender, elEmpfaenger, elKontakt, elEinleitung, elAbschluss, elZahlung;
  let elFooter = [];
  let a4El;
  let dragging = $state(null);
  let resizing = $state(null);

  // ── AUTO-SAVE: 3 Sicherheitsebenen ──────────────────────────────────────
  // 1. localStorage (synchron, sofort — funktioniert IMMER)
  // 2. API nach 2s Debounce (Server-Persistenz)
  // 3. beforeNavigate + visibilitychange + beforeunload (beim Verlassen)

  let autoSaveTimer = null;
  let hatUngespeicherteAenderungen = $state(false);
  let autoSaveStatus = $state(''); // '' | 'speichert' | 'gespeichert'

  // Ebene 1: localStorage — synchron, keine Netzwerk-Abhängigkeit
  function saveToLocalStorage() {
    try {
      collectDom();
      localStorage.setItem(LS_KEY, JSON.stringify({ v, ts: Date.now() }));
    } catch(e) {}
  }

  // Ebene 2: API-Autosave nach Debounce
  function scheduleAutoSave() {
    hatUngespeicherteAenderungen = true;
    saveToLocalStorage(); // sofort lokal sichern
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
      localStorage.removeItem(LS_KEY); // API erfolgreich → lokal löschen
      setTimeout(() => { autoSaveStatus = ''; }, 2500);
    } catch(e) {
      autoSaveStatus = ''; // bleibt im localStorage als Fallback
    }
  }

  // Ebene 3: Sofort beim Verlassen — localStorage sync + API fire-and-forget
  function saveNow() {
    if (!hatUngespeicherteAenderungen) return;
    clearTimeout(autoSaveTimer);
    saveToLocalStorage(); // synchron — immer erfolgreich
    if ($currentUser) {
      apiCall('vorlage-speichern', { user_id: $currentUser.id, vorlage: v }).catch(()=>{});
    }
    hatUngespeicherteAenderungen = false;
  }

  onMount(async () => {
    // Google Fonts
    if (!document.querySelector('link[data-poppins]')) {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.dataset.poppins = '1';
      link.href = 'https://fonts.googleapis.com/css2?family=Poppins:ital,wght@0,300;0,400;0,600;0,700;1,400&display=swap';
      document.head.appendChild(link);
    }

    syncDom();

    if ($currentUser) {
      try {
        const data = await apiCall('vorlage-laden', { user_id: $currentUser.id });
        if (data?.vorlage) {
          v = { ...v, ...data.vorlage };
          syncDom();
        }
      } catch(e) {
        // API nicht erreichbar → localStorage-Entwurf wiederherstellen
        try {
          const draft = localStorage.getItem(LS_KEY);
          if (draft) {
            const parsed = JSON.parse(draft);
            if (parsed?.v) { v = { ...v, ...parsed.v }; syncDom(); showToast('📋 Lokaler Entwurf wiederhergestellt'); }
          }
        } catch(le) {}
      }
    } else {
      // Kein User eingeloggt → localStorage-Entwurf laden
      try {
        const draft = localStorage.getItem(LS_KEY);
        if (draft) {
          const parsed = JSON.parse(draft);
          if (parsed?.v) { v = { ...v, ...parsed.v }; syncDom(); }
        }
      } catch(le) {}
    }

    // Selektion überwachen — speichert Range BEVOR Fokus verloren geht
    document.addEventListener('mouseup', onDocMouseup);
    document.addEventListener('keyup', onDocKeyup);

    // Tab wechseln / Browser minimieren → sofort speichern
    const onVisChange = () => { if (document.visibilityState === 'hidden') saveNow(); };
    document.addEventListener('visibilitychange', onVisChange);

    // Browser/Tab schließen oder URL wechseln
    const onBeforeUnload = () => { saveNow(); };
    window.addEventListener('beforeunload', onBeforeUnload);

    return () => {
      document.removeEventListener('mouseup', onDocMouseup);
      document.removeEventListener('keyup', onDocKeyup);
      document.removeEventListener('visibilitychange', onVisChange);
      window.removeEventListener('beforeunload', onBeforeUnload);
      saveNow();
    };
  });

  // SvelteKit interne Navigation abfangen (Klick auf anderen Tab im Dashboard)
  beforeNavigate(({ cancel }) => {
    saveNow(); // speichert synchron in localStorage + feuert API
    // Kein cancel() — Navigation läuft weiter, Daten sind gesichert
  });

  function syncDom() {
    setTimeout(() => {
      if (elAbsender) elAbsender.innerText = v.t_absender;
      if (elEmpfaenger) elEmpfaenger.innerText = v.t_empfaenger;
      if (elKontakt) elKontakt.innerText = v.t_kontakt;
      if (elEinleitung) elEinleitung.innerText = v.t_einleitung;
      if (elAbschluss) elAbschluss.innerText = v.t_abschluss;
      if (elZahlung) elZahlung.innerText = v.t_zahlung;
      elFooter.forEach((el,i) => { if(el) el.innerText = v.t_footer[i]??''; });
    }, 0);
  }

  function collectDom() {
    if (elAbsender) v.t_absender = elAbsender.innerText;
    if (elEmpfaenger) v.t_empfaenger = elEmpfaenger.innerText;
    if (elKontakt) v.t_kontakt = elKontakt.innerText;
    if (elEinleitung) v.t_einleitung = elEinleitung.innerText;
    if (elAbschluss) v.t_abschluss = elAbschluss.innerText;
    if (elZahlung) v.t_zahlung = elZahlung.innerText;
    elFooter.forEach((el,i) => { if(el){const a=[...v.t_footer];a[i]=el.innerText;v.t_footer=a;} });
  }

  function saveBlur(key, e) { v[key] = e.target.innerText; aktiverBlock=''; scheduleAutoSave(); }
  function saveFooter(i, e) { const a=[...v.t_footer]; a[i]=e.target.innerText; v.t_footer=a; aktiverBlock=''; scheduleAutoSave(); }

  // ── SELEKTION SPEICHERN (mouseup + keyup in contenteditable) ─────────────
  // Selektion wird gespeichert sobald Maus losgelassen → Format-Button
  // klicken verliert zwar den Fokus, aber Range bleibt in savedRange
  function captureSelection() {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) return;
    const range = sel.getRangeAt(0);
    // Nur wenn innerhalb eines rw-e Elements
    if (!isInEditor(range.commonAncestorContainer)) return;
    if (!sel.isCollapsed) {
      savedRange = range.cloneRange();
      hatAuswahl = true;
      // Aktuelle Schriftgröße der Auswahl lesen
      try {
        const node = range.startContainer;
        const el = node.nodeType===3 ? node.parentElement : node;
        auswahlGroesse = Math.round(parseFloat(getComputedStyle(el).fontSize)) || v.schriftgroesse;
      } catch(e) {}
    } else {
      hatAuswahl = false;
    }
  }

  function onDocMouseup(e) {
    // Nicht capturen wenn Format-Button geklickt
    if (e.target.closest('.rw-fmt-btn')) return;
    captureSelection();
  }
  function onDocKeyup(e) { captureSelection(); }

  function isInEditor(node) {
    let n = node?.nodeType===3 ? node.parentElement : node;
    while(n) { if(n.classList?.contains('rw-e')) return true; n=n.parentElement; }
    return false;
  }

  // Range wiederherstellen und execCommand ausführen
  function execOnSaved(cmd, val=null) {
    if (!savedRange) return;
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(savedRange);
    document.execCommand(cmd, false, val);
    // Range nach execCommand neu speichern
    if(sel.rangeCount>0) savedRange = sel.getRangeAt(0).cloneRange();
  }

  // Schriftgröße auf Auswahl anwenden
  function applyFontSize(px) {
    if (!savedRange) return;
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(savedRange);
    // Span um Auswahl wrappen
    try {
      const span = document.createElement('span');
      span.style.fontSize = px + 'px';
      savedRange.surroundContents(span);
    } catch(e) {
      // Falls Auswahl über mehrere Elemente geht → execCommand fallback
      document.execCommand('fontSize', false, '4');
      document.querySelectorAll('font[size="4"]').forEach(f => {
        const s = document.createElement('span');
        s.style.fontSize = px + 'px';
        f.replaceWith(...[s]);
        // Inhalt umhängen
        while(f.firstChild) s.appendChild(f.firstChild);
      });
    }
    auswahlGroesse = px;
  }

  // Zeilenabstand auf ganzen Block anwenden (wo Cursor gerade ist)
  function applyZeilenabstand(val) {
    v.zeilenabstand = val;
    // Auch auf alle rw-e Blöcke anwenden
    document.querySelectorAll('.rw-e').forEach(el => {
      el.style.lineHeight = val;
    });
  }

  // Ausrichtung auf aktuellen Block
  function applyAusrichtung(align) {
    execOnSaved('justify' + align);
  }

  // Textfarbe
  function applyFarbe(c) { execOnSaved('foreColor', c); }
  function applyFett()   { execOnSaved('bold'); }
  function applyKursiv() { execOnSaved('italic'); }
  function applyUnter()  { execOnSaved('underline'); }
  function clearFormat() { execOnSaved('removeFormat'); }

  async function speichern() {
    collectDom(); speichertLaeuft=true;
    try {
      await apiCall('vorlage-speichern',{user_id:$currentUser?.id,vorlage:v});
      showToast('Vorlage gespeichert ✓');
    } catch(e){showToast('Fehler: '+e.message);}
    finally{speichertLaeuft=false;}
  }

  async function pdfVorschau() {
    collectDom(); pdfLaeuft=true; zeigtPDF=true;
    try {
      const data=await apiCall('rechnung-vorschau',{user_id:$currentUser?.id,vorlage:v,beispiel:B});
      vorschauPDF=data.pdf_base64||'';
    } catch(e){showToast('Fehler: '+e.message);zeigtPDF=false;}
    finally{pdfLaeuft=false;}
  }

  function handleLogoUpload(e) {
    const file=e.target.files?.[0]; if(!file) return;
    const r=new FileReader(); r.onload=(ev)=>{v.logo.base64=ev.target.result;}; r.readAsDataURL(file);
  }

  // Bilder einfügen: initial im unteren Bereich (y≈850, unterhalb Badge)
  function addBilder(e) {
    const startY = 850; // unterhalb Badge-Bereich
    Array.from(e.target.files||[]).forEach((file, idx) => {
      const r=new FileReader();
      r.onload=(ev)=>{
        v.hintergrundbilder=[...v.hintergrundbilder,{
          id: Date.now()+Math.random(),
          base64: ev.target.result,
          x: v.seitenrand + idx*20,
          y: startY + idx*20,
          breite: 200,
          opacity: 1.0,   // voll sichtbar, kein Hintergrund-Effekt
        }];
      };
      r.readAsDataURL(file);
    });
    e.target.value='';
  }

  function updateBild(id,key,val) {
    v.hintergrundbilder=v.hintergrundbilder.map(b=>b.id===id?{...b,[key]:val}:b);
  }
  function removeBild(id) { v.hintergrundbilder=v.hintergrundbilder.filter(b=>b.id!==id); }
  function bringFront(id) { const b=v.hintergrundbilder.find(x=>x.id===id); v.hintergrundbilder=[...v.hintergrundbilder.filter(x=>x.id!==id),b]; }
  function sendBack(id)   { const b=v.hintergrundbilder.find(x=>x.id===id); v.hintergrundbilder=[b,...v.hintergrundbilder.filter(x=>x.id!==id)]; }

  function onBildMousedown(e, bild) {
    if(e.target.classList.contains('rw-resize')) return;
    e.preventDefault();
    const rect=a4El.getBoundingClientRect();
    const scale=rect.width/794;
    dragging={id:bild.id, startX:e.clientX, startY:e.clientY, origX:bild.x, origY:bild.y, scale};
  }
  function onResizeMousedown(e,bild) {
    e.preventDefault(); e.stopPropagation();
    const rect=a4El.getBoundingClientRect();
    resizing={id:bild.id, startX:e.clientX, origW:bild.breite, scale:rect.width/794};
  }
  function onMousemove(e) {
    if(dragging) {
      const dx=(e.clientX-dragging.startX)/dragging.scale;
      const dy=(e.clientY-dragging.startY)/dragging.scale;
      updateBild(dragging.id,'x',Math.max(0,dragging.origX+dx));
      updateBild(dragging.id,'y',Math.max(0,dragging.origY+dy));
    }
    if(resizing) {
      updateBild(resizing.id,'breite',Math.max(20,(e.clientX-resizing.startX)/resizing.scale+resizing.origW));
    }
  }
  function onMouseup() { dragging=null; resizing=null; }

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
  const schriften=['Arial','Helvetica','Georgia','Times New Roman','Verdana','Garamond','Courier New','Poppins'];
  function logoJustify(){ return v.logo.position==='links'?'flex-start':v.logo.position==='rechts'?'flex-end':'center'; }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="rw" onmousemove={onMousemove} onmouseup={onMouseup}>

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
      <!-- Auto-Save Status -->
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

    <!-- Globale Einstellungen -->
    <div class="rw-panel-group">
      <span class="rw-lbl-head">GLOBAL</span>
      <span class="rw-lbl">Schrift</span>
      <select class="rw-sel" bind:value={v.schriftart}>
        {#each schriften as f}<option>{f}</option>{/each}
      </select>
      <span class="rw-lbl">Gr.</span>
      <input type="number" class="rw-num" min="7" max="20" bind:value={v.schriftgroesse}/>pt
      <span class="rw-lbl">Zeilenabst.</span>
      <select class="rw-sel" bind:value={v.zeilenabstand} onchange={(e)=>applyZeilenabstand(+e.target.value)}>
        {#each [1.0,1.2,1.4,1.5,1.6,1.8,2.0,2.4] as z}
          <option value={z}>{z}</option>
        {/each}
      </select>
    </div>

    <div class="sep-v"></div>

    <!-- Auswahl-Formatierung -->
    <div class="rw-panel-group" class:dim={!hatAuswahl}>
      <span class="rw-lbl-head" style="color:{hatAuswahl?'#2563eb':'#aaa'};">
        {hatAuswahl ? '✂️ AUSWAHL' : '✂️ AUSWAHL (markieren)'}
      </span>
      <button class="rw-fmt-btn" title="Fett" onclick={applyFett}><b>B</b></button>
      <button class="rw-fmt-btn" title="Kursiv" onclick={applyKursiv}><i>I</i></button>
      <button class="rw-fmt-btn" title="Unterstrichen" onclick={applyUnter}><u>U</u></button>
      <span class="rw-lbl">Gr.</span>
      <input type="number" class="rw-num" min="6" max="72" bind:value={auswahlGroesse}
        onchange={(e)=>applyFontSize(+e.target.value)}/>px
      <span class="rw-lbl">Farbe</span>
      <input type="color" class="rw-color-pick" title="Textfarbe"
        onchange={(e)=>applyFarbe(e.target.value)}/>
      <button class="rw-fmt-btn rw-fmt-clear" title="Format löschen" onclick={clearFormat}>✕ Clear</button>
    </div>

    <div class="sep-v"></div>

    <!-- Ausrichtung (auf Block) -->
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

    <!-- Badge -->
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
        <button class="rw-dot" style="background:{t.c};" class:act={v.akzentfarbe===t.c}
          onclick={()=>applyTheme(t.c)} title={t.n}></button>
      {/each}
      <input type="color" class="rw-color-pick" bind:value={v.akzentfarbe}
        oninput={()=>v.tabelle.kopf_hg=v.akzentfarbe}/>
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
    <!-- Footer EIGENE Einstellungen — komplett getrennt von global -->
    <div class="rw-panel-group">
      <span class="rw-lbl-head">FOOTER</span>
      {#each [1,2,3,4] as n}
        <button class="rw-tab" class:act={v.footer_spalten===n} onclick={()=>{v.footer_spalten=n;scheduleAutoSave();}>{n}Sp</button>
      {/each}
      <label class="rw-check"><input type="checkbox" bind:checked={v.footer_trennlinie} onchange={scheduleAutoSave}/> Linie</label>
      <span class="rw-lbl">Gr.</span>
      <!-- NUR footer_schriftgroesse, nicht v.schriftgroesse! -->
      <input type="number" class="rw-num" min="6" max="14" bind:value={v.footer_schriftgroesse}/>pt
      <span class="rw-lbl">Zeil.</span>
      <select class="rw-sel" bind:value={v.footer_zeilenabstand}>
        {#each [1.0,1.2,1.4,1.5,1.6,1.8,2.0] as z}
          <option value={z}>{z}</option>
        {/each}
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

  <!-- ═══ PANEL BILDER ══════════════════════════════════════════════════════ -->
  {:else if aktivesTab==='bilder'}
  <div class="rw-panel">
    <div class="rw-panel-group">
      <span class="rw-lbl-head">BILDER</span>
      <label class="rw-btn rw-btn-prim">➕ Bild(er)
        <input type="file" accept="image/*" multiple onchange={addBilder} style="display:none"/>
      </label>
      <span class="rw-hint-idle">Wird im unteren Bereich eingefügt → mit Maus verschieben</span>
    </div>
    {#if v.hintergrundbilder.length>0}
      <div class="sep-v"></div>
      <div class="rw-panel-group rw-bilder-liste">
        {#each v.hintergrundbilder as bild,i}
          <div class="rw-bild-row">
            <img src={bild.base64} alt="" class="rw-bild-thumb"/>
            <span class="rw-lbl">#{i+1}</span>
            <span class="rw-lbl">B:</span>
            <input type="number" class="rw-num" min="10" max="794" value={Math.round(bild.breite)}
              oninput={(e)=>updateBild(bild.id,'breite',+e.target.value)}/>
            <span class="rw-lbl">Tr.:</span>
            <input type="range" min="0.03" max="1" step="0.03" value={bild.opacity}
              oninput={(e)=>updateBild(bild.id,'opacity',+e.target.value)} style="width:60px;"/>
            <span class="rw-lbl" style="min-width:28px;">{Math.round(bild.opacity*100)}%</span>
            <button class="rw-fmt-btn" title="Nach vorne" onclick={()=>bringFront(bild.id)}>↑</button>
            <button class="rw-fmt-btn" title="Nach hinten" onclick={()=>sendBack(bild.id)}>↓</button>
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

      <!-- Hintergrundbilder: position:absolute, z-index 1..n -->
      {#each v.hintergrundbilder as bild,idx}
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="rw-bild-wrap"
          style="left:{bild.x}px;top:{bild.y}px;width:{bild.breite}px;opacity:{bild.opacity};z-index:{idx+1};"
          onmousedown={(e)=>onBildMousedown(e,bild)}>
          <img src={bild.base64} alt="" style="width:100%;display:block;pointer-events:none;user-select:none;"/>
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div class="rw-resize" onmousedown={(e)=>onResizeMousedown(e,bild)}></div>
        </div>
      {/each}

      <!-- Inhalt: z-index 10 → immer über Bildern -->
      <div class="rw-inhalt">

        <!-- LOGO -->
        {#if v.logo.base64}
          <div style="display:flex;justify-content:{logoJustify()};padding:var(--rand) var(--rand) 0;">
            <label style="cursor:pointer;" title="Klicken zum Wechseln">
              <input type="file" accept="image/*" onchange={handleLogoUpload} style="display:none"/>
              <img src={v.logo.base64} alt="Logo"
                style="width:{v.logo.breite}px;max-height:100px;object-fit:contain;display:block;"/>
            </label>
          </div>
        {:else if aktivesTab==='layout'}
          <div style="display:flex;justify-content:{logoJustify()};padding:var(--rand) var(--rand) 0;">
            <label class="rw-logo-drop"><input type="file" accept="image/*" onchange={handleLogoUpload} style="display:none"/>🖼 Logo</label>
          </div>
        {/if}

        <!-- HEADER -->
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

        <!-- BODY -->
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
                <div class="rw-e rw-badge"
                  contenteditable="true" bind:this={elZahlung}
                  onfocus={()=>aktiverBlock='Bezahlt-Badge'} onblur={(e)=>saveBlur('t_zahlung',e)}
                  data-ph="Bezahlt-Text"
                  style="color:{v.zahlung_farbe};background:{v.zahlung_hg};border-color:{v.zahlung_rahmen};"></div>
              {:else}
                <div class="rw-e" style="line-height:{v.zeilenabstand};"
                  contenteditable="true" bind:this={elZahlung}
                  onfocus={()=>aktiverBlock='Bezahlt-Text'} onblur={(e)=>saveBlur('t_zahlung',e)}
                  data-ph="Bezahlt-Text"></div>
              {/if}
            </div>
          {/if}

        </div><!-- /body -->

        <!-- FOOTER — eigene Schriftgröße, komplett unabhängig -->
        <div class="rw-footer" style="
          padding:8px var(--rand);
          grid-template-columns:repeat({v.footer_spalten},1fr);
          border-top:{v.footer_trennlinie?'1px solid #ccc':'none'};
          font-size:{v.footer_schriftgroesse}px;
          line-height:{v.footer_zeilenabstand};
        ">
          {#each Array(v.footer_spalten) as _,i}
            <div class="rw-e rw-fcol"
              contenteditable="true" bind:this={elFooter[i]}
              onfocus={()=>aktiverBlock=`Footer Sp.${i+1}`} onblur={(e)=>saveFooter(i,e)}
              data-ph="Footer Spalte {i+1}"></div>
          {/each}
        </div>

      </div><!-- /rw-inhalt -->
    </div><!-- /rw-a4 -->
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
  .rw-bild-row{display:flex;align-items:center;gap:5px;background:#fff;border:1px solid #e2e8f0;border-radius:5px;padding:3px 8px;}
  .rw-bild-thumb{width:28px;height:22px;object-fit:cover;border-radius:2px;border:1px solid #e2e8f0;}

  .sep-v{width:1px;height:32px;background:#e2e8f0;flex-shrink:0;margin:0 2px;}
  .rw-lbl{font-size:0.71rem;color:#777;white-space:nowrap;}
  .rw-sel{border:1px solid #ddd;border-radius:4px;padding:2px 4px;font-size:0.73rem;background:#fff;color:#333;cursor:pointer;outline:none;}
  .rw-num{width:44px;border:1px solid #ddd;border-radius:4px;padding:2px 4px;font-size:0.73rem;background:#fff;color:#333;outline:none;}
  .rw-color-pick{width:24px;height:24px;padding:0;border:1px solid #ddd;border-radius:4px;cursor:pointer;background:none;}
  .rw-dot{width:16px;height:16px;border-radius:50%;border:1.5px solid rgba(0,0,0,0.15);cursor:pointer;flex-shrink:0;transition:transform 0.1s;}
  .rw-dot:hover{transform:scale(1.3);}
  .rw-dot.act{outline:2.5px solid #111;outline-offset:2px;}

  .rw-tab{background:transparent;border:1px solid #ddd;border-radius:4px;padding:2px 7px;font-size:0.72rem;font-weight:500;color:#555;cursor:pointer;white-space:nowrap;transition:all 0.1s;}
  .rw-tab:hover{border-color:#999;color:#222;}
  .rw-tab.act{background:#1d4ed8;color:#fff;border-color:#1d4ed8;}

  /* Format-Buttons: mousedown statt click → kein Fokus-Verlust */
  .rw-fmt-btn{background:#fff;border:1px solid #ddd;border-radius:3px;padding:2px 7px;font-size:0.73rem;cursor:pointer;min-width:24px;height:24px;display:flex;align-items:center;justify-content:center;transition:all 0.1s;user-select:none;}
  .rw-fmt-btn:hover{background:#e8f0fe;border-color:#93c5fd;}
  .rw-fmt-btn:active{background:#dbeafe;}
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

  /* Auto-Save Status */
  .rw-autosave{font-size:0.7rem;padding:2px 8px;border-radius:10px;white-space:nowrap;}
  .rw-autosave-act{color:#92400e;background:#fef3c7;}
  .rw-autosave-ok{color:#15803d;background:#f0fdf4;}
  .rw-autosave-pending{color:#6b7280;background:#f3f4f6;}
  .rw-check{display:flex;align-items:center;gap:4px;font-size:0.73rem;color:#555;cursor:pointer;white-space:nowrap;}
  .rw-check input{accent-color:#1d4ed8;}
  .rw-title{font-size:0.84rem;font-weight:700;color:#1e293b;white-space:nowrap;}

  .rw-canvas{flex:1;overflow-y:auto;overflow-x:auto;padding:24px 20px 40px;display:flex;flex-direction:column;align-items:center;}
  .rw-a4{width:794px;min-height:1123px;background:#fff;box-shadow:0 4px 32px rgba(0,0,0,0.17);border-radius:2px;position:relative;display:flex;flex-direction:column;flex-shrink:0;}

  /* Bilder hinter Inhalt */
  .rw-bild-wrap{position:absolute;cursor:move;}
  .rw-bild-wrap:hover{outline:1px dashed rgba(29,78,216,0.4);}
  .rw-resize{position:absolute;right:-5px;bottom:-5px;width:12px;height:12px;background:#1d4ed8;border-radius:2px;cursor:se-resize;z-index:99;}

  /* Inhalt immer über Bildern */
  .rw-inhalt{position:relative;z-index:10;display:flex;flex-direction:column;flex:1;pointer-events:auto;}

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

  /* FOOTER: font-size und line-height kommen ausschließlich per inline-style vom State */
  /* Kein font-size hier im CSS → kein Konflikt mit globalem font-size */
  .rw-footer{margin-top:auto;display:grid;gap:10px;flex-shrink:0;}
  .rw-fcol{color:#333;white-space:pre-wrap;word-break:break-word;min-height:28px;}

  /* Contenteditable */
  :global(.rw-e){outline:none;border-radius:2px;transition:background 0.1s,box-shadow 0.1s;min-height:1.2em;white-space:pre-wrap;word-break:break-word;cursor:text;}
  :global(.rw-e:hover){background:rgba(29,78,216,0.04);box-shadow:0 0 0 1px rgba(29,78,216,0.2);}
  :global(.rw-e:focus){background:rgba(29,78,216,0.06);box-shadow:0 0 0 2px rgba(29,78,216,0.35);}
  :global(.rw-e:empty::before){content:attr(data-ph);color:#c0c7d0;font-style:italic;pointer-events:none;}

  .rw-pdf{width:794px;height:1123px;flex-shrink:0;background:#fff;border:none;border-radius:2px;box-shadow:0 4px 28px rgba(0,0,0,0.18);}
  @media(max-width:860px){.rw-a4,.rw-pdf{width:100%;min-width:0;}}
</style>
