#!/usr/bin/env python3
"""Patch +page.svelte to add custom folders feature"""
import sys

FILE = '/opt/ebay-dashboard/src/routes/+page.svelte'
code = open(FILE).read()
print(f"Read: {len(code)} bytes")

# 1. Variables
code = code.replace(
    'let reviseHistory = {};',
    "let reviseHistory = {};\n  let customFolders = [];\n  let showNewFolderModal = false;\n  let newFolderName = '';\n  let newFolderIcon = '\U0001f4c2';"
)

# 2. onMount
code = code.replace(
    "    loadNachrichten();\n  });",
    "    loadNachrichten();\n    loadCustomFolders();\n  });"
)

# 3. folder_id in _folder
code = code.replace(
    "        else m._folder = null;",
    "        else if (m.folder_id) m._folder = 'custom_' + m.folder_id;\n        else m._folder = null;"
)

# 4. getFolderMessages
code = code.replace(
    "      default: return msgs;\n    }\n  }\n\n  function getFolderCount",
    "      default:\n        if (currentFolder.startsWith('custom_')) {\n          const fid = parseInt(currentFolder.replace('custom_', ''));\n          return msgs.filter(m => m.folder_id === fid);\n        }\n        return msgs;\n    }\n  }\n\n  function getFolderCount"
)

# 5. getFolderCount
code = code.replace(
    "      default: return 0;\n    }\n  }\n\n  $: filteredMessages",
    "      default:\n        if (folder.startsWith('custom_')) {\n          const fid = parseInt(folder.replace('custom_', ''));\n          return msgs.filter(m => m.folder_id === fid).length;\n        }\n        return 0;\n    }\n  }\n\n  $: filteredMessages"
)

# 6. Folder functions
folder_fns = """  // ---- CUSTOM FOLDERS ----
  async function loadCustomFolders() {
    try {
      const data = await apiCall('/nachricht-ordner', { action: 'list', user_id: user?.id });
      if (data.success) customFolders = data.folders || [];
    } catch(e) {}
  }

  async function createFolder() {
    if (!newFolderName.trim()) return;
    try {
      const data = await apiCall('/nachricht-ordner', { action: 'create', user_id: user?.id, name: newFolderName.trim(), icon: newFolderIcon });
      if (data.success) {
        showNewFolderModal = false; newFolderName = ''; newFolderIcon = '\U0001f4c2';
        await loadCustomFolders();
        showToast('Ordner erstellt', 'success');
      }
    } catch(e) { showToast('Fehler beim Erstellen', 'error'); }
  }

  async function deleteFolder(folderId) {
    if (!confirm('Ordner l\u00f6schen? Nachrichten werden in den Posteingang verschoben.')) return;
    try {
      const data = await apiCall('/nachricht-ordner', { action: 'delete', user_id: user?.id, folder_id: folderId });
      if (data.success) {
        if (currentFolder === 'custom_' + folderId) { currentFolder = 'alle'; selectedMsgId = null; }
        await loadCustomFolders(); await loadNachrichten();
        showToast('Ordner gel\u00f6scht', 'success');
      }
    } catch(e) { showToast('Fehler', 'error'); }
  }

  async function renameFolder(folderId) {
    const folder = customFolders.find(f => f.id === folderId);
    const newName = prompt('Neuer Name:', folder?.name || '');
    if (!newName || !newName.trim()) return;
    try {
      const data = await apiCall('/nachricht-ordner', { action: 'rename', user_id: user?.id, folder_id: folderId, name: newName.trim() });
      if (data.success) { await loadCustomFolders(); showToast('Umbenannt', 'success'); }
    } catch(e) { showToast('Fehler', 'error'); }
  }

  async function moveToFolder(target) {
    if (!selectedMsg) return;
    showMoveModal = false;
    try {
      const data = await apiCall('/nachricht-ordner', { action: 'move', user_id: user?.id, message_id: selectedMsg.id, target: target });
      if (data.success) {
        selectedMsgId = null; await loadNachrichten();
        showToast('Verschoben', 'success');
      } else showToast('Fehler', 'error');
    } catch(e) { showToast('Fehler', 'error'); }
  }

"""
code = code.replace('  function isEbayMsg', folder_fns + '  function isEbayMsg')

# 7. Sidebar HTML
old_folders = """  <!-- FOLDERS -->
  <div class="folders">
    {#each folders as f}
      {#if f.key.startsWith('_')}
        <div class="f-divider"></div>
      {:else}
        <button class="f-item" class:f-active={currentFolder === f.key} on:click={() => setFolder(f.key)}>
          <span class="f-icon">{f.icon}</span>
          <span class="f-name">{f.label}</span>
          <span class="f-count" class:f-count-active={currentFolder === f.key}>{getFolderCount(f.key)}</span>
        </button>
      {/if}
    {/each}
  </div>"""

new_folders = """  <!-- FOLDERS -->
  <div class="folders">
    {#each folders as f}
      {#if f.key.startsWith('_')}
        <div class="f-divider"></div>
        {#if f.key === '_divider2'}
          {#each customFolders as cf}
            <button class="f-item" class:f-active={currentFolder === 'custom_' + cf.id}
              on:click={() => setFolder('custom_' + cf.id)}
              on:contextmenu|preventDefault={() => { const a = prompt(cf.name + ': 1=Umbenennen, 2=L\\u00f6schen'); if(a==='1') renameFolder(cf.id); else if(a==='2') deleteFolder(cf.id); }}>
              <span class="f-icon">{cf.icon}</span>
              <span class="f-name">{cf.name}</span>
              <span class="f-count" class:f-count-active={currentFolder === 'custom_' + cf.id}>{getFolderCount('custom_' + cf.id)}</span>
            </button>
          {/each}
          <button class="f-item f-add" on:click={() => showNewFolderModal = true}>
            <span class="f-icon">+</span>
            <span class="f-name" style="font-size:12px;color:var(--text3)">Neuer Ordner</span>
          </button>
        {/if}
      {:else}
        <button class="f-item" class:f-active={currentFolder === f.key} on:click={() => setFolder(f.key)}>
          <span class="f-icon">{f.icon}</span>
          <span class="f-name">{f.label}</span>
          <span class="f-count" class:f-count-active={currentFolder === f.key}>{getFolderCount(f.key)}</span>
        </button>
      {/if}
    {/each}
  </div>"""
code = code.replace(old_folders, new_folders)

# 8. Move modal
code = code.replace('on:click={() => moveMessage(f.key)}>', 'on:click={() => moveToFolder(f.key)}>')
code = code.replace(
    """      {/each}
      <button class="move-cancel" on:click={() => showMoveModal = false}>Abbrechen</button>""",
    """      {/each}
      {#if customFolders.length > 0}
        <div style="height:1px;background:var(--border);margin:8px 0;"></div>
        {#each customFolders as cf}
          <button class="move-btn" on:click={() => moveToFolder(cf.id)}>
            <span style="font-size:20px;">{cf.icon}</span> {cf.name}
          </button>
        {/each}
      {/if}
      <button class="move-cancel" on:click={() => showMoveModal = false}>Abbrechen</button>"""
)

# 9. New folder modal
modal = """
<!-- NEW FOLDER MODAL -->
{#if showNewFolderModal}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <div class="move-overlay" on:click|self={() => showNewFolderModal = false}>
    <div class="move-box">
      <div style="font-size:16px;font-weight:800;margin-bottom:6px;">\U0001f4c2 Neuer Ordner</div>
      <p style="font-size:13px;color:var(--text2);margin-bottom:16px;">Name und Icon festlegen</p>
      <div style="display:flex;gap:10px;align-items:center;margin-bottom:12px;">
        <select class="input" style="width:60px;text-align:center;font-size:18px;padding:8px;" bind:value={newFolderIcon}>
          <option>\U0001f4c2</option><option>\u2b50</option><option>\U0001f525</option><option>\U0001f48e</option>
          <option>\U0001f4cc</option><option>\u2757</option><option>\U0001f4ac</option><option>\U0001f6d2</option>
          <option>\U0001f4b0</option><option>\U0001f527</option><option>\U0001f3f7\ufe0f</option><option>\U0001f4cb</option>
        </select>
        <input class="input" placeholder="Ordnername..." bind:value={newFolderName} on:keydown={(e) => e.key === 'Enter' && createFolder()} style="flex:1;" />
      </div>
      <button class="move-btn" style="justify-content:center;background:var(--primary);color:white;border-color:var(--primary);" on:click={createFolder}>
        Ordner erstellen
      </button>
      <button class="move-cancel" on:click={() => showNewFolderModal = false}>Abbrechen</button>
    </div>
  </div>
{/if}"""
code = code.replace('\n<style>', modal + '\n\n<style>', 1)

# 10. CSS
code = code.replace(
    '.f-divider { height: 1px; background: var(--border); margin: 4px; }',
    '.f-divider { height: 1px; background: var(--border); margin: 4px; }\n  .f-add { opacity: 0.6; transition: opacity 0.15s; }\n  .f-add:hover { opacity: 1; background: var(--border); }'
)

# Verify
ok = all(p in code for p in ['customFolders', 'loadCustomFolders', 'createFolder', 'deleteFolder', 'renameFolder', 'moveToFolder', 'nachricht-ordner', 'showNewFolderModal', 'Neuer Ordner', 'f-add', "custom_'"])
if ok:
    open(FILE, 'w').write(code)
    print(f"SUCCESS: {len(code)} bytes written to {FILE}")
else:
    print("FAILED: Not all patches applied!")
    sys.exit(1)
