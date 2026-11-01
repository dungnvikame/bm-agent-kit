/* Guided settings form built from SettingsSchema. Edits patch the loaded contract object; keys outside the schema are
   preserved. Save goes to /api/contract, which re-composes all layers and refuses anything that widens permissions. */
(() => {
  const { el, tag, card, page, get, help, advanced, pre, api } = Dash;
  const getPath = (o, p) => p.reduce((c, k) => (c == null ? undefined : c[k]), o);
  const setPath = (o, p, v) => { let c = o; for (let i = 0; i < p.length - 1; i++) { if (typeof c[p[i]] !== 'object' || c[p[i]] === null) c[p[i]] = {}; c = c[p[i]]; } c[p[p.length - 1]] = v; };
  const labelFor = (f, k) => (f.labels === 'scope' ? Labels.scopeItem(k) : f.labels === 'capability' ? Labels.cap(k) : f.labels === 'skill' ? (Labels.skill[k] ? `${k} — ${Labels.skill[k]}` : k) : k);

  function widget(f, working, upperValue, onChange) {
    const value = getPath(working, f.path);
    if (f.type === 'locked') return el('div', {}, tag(String(value), 'info'), ' ', el('span', { class: 'muted' }, 'khoá bởi tầng lõi'));
    if (f.type === 'text') { const i = el('input', { type: 'text', value: value == null ? '' : String(value) }); i.addEventListener('input', () => { setPath(working, f.path, i.value); onChange(); }); return i; }
    if (f.type === 'textarea') { const t = el('textarea', { class: 'small' }, value == null ? '' : String(value)); t.addEventListener('input', () => { setPath(working, f.path, t.value); onChange(); }); return t; }
    if (f.type === 'checklist') {
      const options = Array.isArray(upperValue) ? upperValue : (Array.isArray(value) ? value : []);
      const box = el('div', { class: 'checklist' });
      for (const opt of options) {
        const cb = el('input', { type: 'checkbox' }); cb.checked = (value || []).includes(opt);
        cb.addEventListener('change', () => { setPath(working, f.path, options.filter(o => box.querySelector(`input[data-k="${o}"]`).checked)); onChange(); });
        cb.dataset.k = opt;
        box.append(el('label', {}, cb, labelFor(f, opt), el('span', { class: 'muted' }, ` (${opt})`)));
      }
      return box;
    }
    // taglist
    const wrap = el('div');
    const render = () => {
      wrap.innerHTML = '';
      const items = Array.isArray(getPath(working, f.path)) ? getPath(working, f.path) : [];
      const chips = el('div', { class: 'chips' });
      for (const k of items) {
        const fixed = Array.isArray(upperValue) && upperValue.includes(k) && f.path[1] === 'handoff_only';
        const chip = el('span', { class: 'chip' + (fixed ? ' fixed' : '') }, labelFor(f, k));
        if (!fixed) chip.append(el('button', { title: 'Bỏ mục này', onclick: () => { setPath(working, f.path, items.filter(x => x !== k)); onChange(); render(); } }, '×'));
        chips.append(chip);
      }
      const input = el('input', { type: 'text', placeholder: 'thêm mã mới rồi Enter' });
      input.addEventListener('keydown', e => { if (e.key === 'Enter' && input.value.trim()) { setPath(working, f.path, items.concat(input.value.trim())); onChange(); render(); } });
      wrap.append(chips, input);
    };
    render();
    return wrap;
  }

  Dash.views.settings = async (initialPath) => {
    const ov = await get('/api/overview');
    const paths = Object.keys(SettingsSchema);
    let current = paths.includes(initialPath) ? initialPath : paths[0];
    const root = page('Cài đặt agent', 'Chỉnh những gì agent PM được làm. Mỗi lần lưu, hệ thống gộp lại ba tầng cấu hình và từ chối nếu thay đổi làm agent có thêm quyền.');
    const tabs = el('div', { class: 'row' }), body = el('div');
    const drawTabs = () => { tabs.innerHTML = ''; for (const p of paths) tabs.append(el('button', { class: 'btn' + (p === current ? ' primary' : ''), onclick: () => { current = p; drawTabs(); load(); } }, SettingsSchema[p].title)); };
    const load = async () => {
      body.innerHTML = '<p class="muted">Đang tải…</p>';
      const schema = SettingsSchema[current];
      const f = await api('/api/file?path=' + encodeURIComponent(current));
      const original = JSON.parse(f.text), working = JSON.parse(JSON.stringify(original));
      const upper = ov.layers[schema.upper] ? ov.layers[schema.upper].config : {};
      const jsonPre = pre(working), result = el('div');
      const saveBtn = el('button', { class: 'btn primary', disabled: 'disabled' }, 'Lưu thay đổi');
      const dirty = () => JSON.stringify(working) !== JSON.stringify(original);
      const onChange = () => { jsonPre.textContent = JSON.stringify(working, null, 2); saveBtn.disabled = !dirty(); };
      saveBtn.addEventListener('click', async () => {
        saveBtn.disabled = true; result.innerHTML = '';
        try {
          const r = await api('/api/contract', { path: current, json: working });
          result.append(el('div', { class: r.saved ? 'success' : 'note' }, r.saved ? '✅ Đã lưu. Cấu hình vẫn hợp lệ.' : 'Không có gì thay đổi.'));
          Dash.refreshStatus(); Dash.invalidate(); await load();
        } catch (e) { result.append(Dash.errorBox(e)); saveBtn.disabled = false; }
      });
      body.innerHTML = '';
      body.append(help(schema.intro), el('div', { class: 'muted' }, 'File: ' + current));
      for (const g of schema.groups) {
        const c = card(el('h2', {}, g.title));
        for (const fld of g.fields) {
          const field = el('div', { class: 'field' + (fld.type === 'locked' ? ' locked' : '') }, el('label', { class: 'title' }, fld.label), fld.help ? help(fld.help) : '');
          field.append(widget(fld, working, getPath(upper, fld.path), onChange));
          c.append(field);
        }
        body.append(c);
      }
      body.append(el('div', { class: 'sticky-actions row' }, saveBtn, el('button', { class: 'btn', onclick: load }, 'Huỷ thay đổi'), el('span', { class: 'muted' }, 'Lưu chỉ ghi vào file trong kho trên máy; không commit, không gửi đi đâu.')), result,
        advanced('Nâng cao: xem JSON sẽ được lưu', jsonPre));
    };
    drawTabs(); root.append(tabs, body); await load();
    return root;
  };
})();
