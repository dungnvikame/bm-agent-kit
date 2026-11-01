/* Edit views: contract forms (role/product JSON) and a text editor for canonical markdown files.
   Every save goes through the server's guarded path: allowlist -> JSON check -> compose (fail closed) -> write -> adapter sync. */
(() => {
  const { el, pre, tag, api, list } = Dash;
  const card = (...kids) => el('div', { class: 'card' }, ...kids);

  function saveResult(r) {
    const box = el('div', { class: r.saved ? 'success' : 'note' }, el('strong', {}, `${r.message}: ${r.path}`));
    if (r.sync) {
      box.append(el('div', {}, 'Adapter sync wrote: ', ...r.sync.written.map(w => el('code', {}, w + ' '))));
      box.append(r.sync.problems.length ? el('div', { class: 'error' }, 'Sync problems:', list(r.sync.problems)) : el('div', {}, tag('copies hash-match', 'ok')));
    }
    Dash.refreshStatus();
    return box;
  }

  Dash.views.contracts = async (initialPath) => {
    const files = (await api('/api/files')).filter(f => f.path.endsWith('.json'));
    const root = el('div', {}, el('h1', {}, 'Contracts'), el('p', { class: 'muted' }, 'Field-level edit of the role and product contracts. Locked keys (🔒) are owned by core: changing them is refused by the compose check.'));
    const select = el('select', {}, ...files.map(f => el('option', { value: f.path }, `${f.path}${f.kind === 'read_only' ? ' (read-only)' : ''}`)));
    if (initialPath) select.value = initialPath;
    const formHost = el('div'), jsonHost = el('div'), result = el('div');
    const load = async () => {
      result.innerHTML = ''; formHost.innerHTML = '<p class="muted">Loading…</p>'; jsonHost.innerHTML = '';
      const f = await api('/api/file?path=' + encodeURIComponent(select.value));
      const original = JSON.parse(f.text);
      const jsonPre = pre(original);
      const form = JsonForm.build(formHost, original, () => { jsonPre.textContent = JSON.stringify(form.read(), null, 2); saveBtn.disabled = !form.dirty() || f.kind !== 'editable'; });
      const saveBtn = el('button', { class: 'btn primary', disabled: 'disabled', onclick: async () => {
        saveBtn.disabled = true; result.innerHTML = '';
        try { result.append(saveResult(await api('/api/contract', { path: f.path, json: form.read() }))); await load(); }
        catch (e) { result.append(Dash.errorBox(e)); saveBtn.disabled = false; }
      } }, 'Save contract');
      const resetBtn = el('button', { class: 'btn', onclick: load }, 'Reset');
      jsonHost.append(f.note ? el('div', { class: 'note' }, f.note) : '', el('div', { class: 'row' }, saveBtn, resetBtn, tag(f.kind === 'editable' ? 'editable' : 'read-only', f.kind === 'editable' ? 'ok' : 'warn')),
        el('h3', {}, 'JSON (live)'), jsonPre);
      if (f.kind !== 'editable') formHost.querySelectorAll('input,select,textarea').forEach(n => { n.disabled = true; });
    };
    select.addEventListener('change', load);
    root.append(card(el('div', { class: 'row' }, el('label', {}, 'File '), select)), el('div', { class: 'two-col' }, card(formHost), card(jsonHost)), result);
    await load();
    return root;
  };

  Dash.views.editor = async (initialPath) => {
    const files = await api('/api/files');
    const root = el('div', {}, el('h1', {}, 'Text editor'), el('p', { class: 'muted' }, 'Canonical files only. Saving a skill file or core/agent-instructions.md re-syncs .claude/skills, .agents/skills, AGENTS.md and CLAUDE.md. Generated copies, core-contract.json, the git directory and files outside the repo cannot be edited here. No git commit/push.'));
    const groups = {};
    for (const f of files) (groups[f.path.split('/').slice(0, 2).join('/')] ||= []).push(f);
    const select = el('select');
    for (const [g, fs] of Object.entries(groups)) {
      const og = el('optgroup', { label: g });
      for (const f of fs) og.append(el('option', { value: f.path }, `${f.path}${f.kind === 'read_only' ? ' (read-only)' : ''}${f.sync ? ' ⟳' : ''}`));
      select.append(og);
    }
    if (initialPath) select.value = initialPath;
    const ta = el('textarea', { spellcheck: 'false' }), info = el('div'), result = el('div');
    let current = null;
    const saveBtn = el('button', { class: 'btn primary', disabled: 'disabled', onclick: async () => {
      saveBtn.disabled = true; result.innerHTML = '';
      try { result.append(saveResult(await api('/api/file', { path: current.path, text: ta.value }))); await load(); }
      catch (e) { result.append(Dash.errorBox(e)); saveBtn.disabled = false; }
    } }, 'Save');
    const load = async () => {
      result.innerHTML = ''; info.innerHTML = '';
      current = await api('/api/file?path=' + encodeURIComponent(select.value));
      ta.value = current.text; ta.disabled = current.kind !== 'editable'; saveBtn.disabled = true;
      info.append(tag(current.kind === 'editable' ? 'editable' : 'read-only', current.kind === 'editable' ? 'ok' : 'warn'),
        current.sync ? tag('save re-syncs adapter copies', 'warn') : '', current.note ? el('div', { class: 'note' }, current.note) : '');
    };
    ta.addEventListener('input', () => { saveBtn.disabled = !current || current.kind !== 'editable' || ta.value === current.text; });
    select.addEventListener('change', load);
    root.append(card(el('div', { class: 'row' }, el('label', {}, 'File '), select, saveBtn, el('button', { class: 'btn', onclick: load }, 'Reload')), info, ta), result);
    await load();
    return root;
  };
})();
