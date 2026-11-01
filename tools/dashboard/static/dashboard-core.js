/* Dashboard core: API calls, navigation, small DOM helpers. Views register themselves in Dash.views. */
const Dash = {
  views: {},
  current: null,

  async api(path, body) {
    const opts = body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
    const res = await fetch(path, opts);
    let data = {};
    try { data = await res.json(); } catch (e) { data = { error: 'invalid response' }; }
    if (!res.ok) { const err = new Error(data.error || res.statusText); err.data = data; err.status = res.status; throw err; }
    return data;
  },

  esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); },
  el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (k === 'class') node.className = v; else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
      else if (k === 'html') node.innerHTML = v; else node.setAttribute(k, v);
    }
    for (const c of children) node.append(c instanceof Node ? c : document.createTextNode(String(c)));
    return node;
  },
  pre(obj) { return Dash.el('pre', {}, typeof obj === 'string' ? obj : JSON.stringify(obj, null, 2)); },
  tag(text, kind) { return Dash.el('span', { class: 'tag ' + (kind || '') }, text); },
  table(headers, rows) {
    const t = Dash.el('table');
    t.append(Dash.el('thead', {}, Dash.el('tr', {}, ...headers.map(h => Dash.el('th', {}, h)))));
    const body = Dash.el('tbody');
    for (const r of rows) body.append(Dash.el('tr', {}, ...r.map(c => Dash.el('td', {}, c instanceof Node ? c : String(c == null ? '' : c)))));
    t.append(body);
    return t;
  },
  list(items, kind) {
    const ul = Dash.el('ul', { class: kind || '' });
    for (const i of items) ul.append(Dash.el('li', {}, i));
    return ul;
  },
  toast(msg, ms) {
    const t = document.getElementById('toast');
    t.textContent = msg; t.classList.remove('hidden');
    clearTimeout(Dash._toastTimer); Dash._toastTimer = setTimeout(() => t.classList.add('hidden'), ms || 3500);
  },
  errorBox(err) {
    const box = Dash.el('div', { class: 'error' }, Dash.el('strong', {}, err.message || String(err)));
    const v = err.data && err.data.violations;
    if (v && v.length) box.append(Dash.list(v));
    return box;
  },

  async show(name, arg) {
    const main = document.getElementById('main');
    document.querySelectorAll('#nav button').forEach(b => b.classList.toggle('active', b.dataset.view === name));
    main.innerHTML = '<p class="muted">Loading…</p>';
    Dash.current = name;
    try {
      const node = await Dash.views[name](arg);
      if (Dash.current !== name) return;
      main.innerHTML = ''; main.append(node);
    } catch (err) {
      main.innerHTML = ''; main.append(Dash.errorBox(err));
    }
    if (location.hash !== '#' + name) history.replaceState(null, '', '#' + name);
  },

  async refreshStatus() {
    const pill = document.getElementById('status-pill');
    try {
      const [ov, sk] = await Promise.all([Dash.api('/api/overview'), Dash.api('/api/skills')]);
      const bad = ov.violations.length + sk.sync_problems.length;
      pill.className = 'pill ' + (bad ? 'bad' : 'ok');
      pill.textContent = bad ? `${ov.violations.length} config violation(s), ${sk.sync_problems.length} sync problem(s)` : 'config ok · adapter copies in sync';
    } catch (err) { pill.className = 'pill bad'; pill.textContent = 'status unavailable: ' + err.message; }
  },

  boot() {
    document.querySelectorAll('#nav button').forEach(b => b.addEventListener('click', () => Dash.show(b.dataset.view)));
    const fromHash = () => { const name = location.hash.slice(1); Dash.show(Dash.views[name] ? name : 'overview'); };
    window.addEventListener('hashchange', () => { if (location.hash.slice(1) !== Dash.current) fromHash(); });
    fromHash();
    Dash.refreshStatus();
  },
};
