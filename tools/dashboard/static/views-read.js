/* Read-only views: overview, skills, policies, product, evaluations, plans. Each returns a DOM node. */
(() => {
  const { el, pre, tag, table, list, api } = Dash;
  const h = (t, s) => el('div', {}, el('h1', {}, t), s ? el('p', { class: 'muted' }, s) : '');
  const card = (...kids) => el('div', { class: 'card' }, ...kids);
  const status = (ok, okText, badText) => tag(ok ? okText : badText, ok ? 'ok' : 'bad');

  Dash.views.overview = async () => {
    const d = await api('/api/overview');
    const root = h('Layers & effective config', 'Compose order Core → Role → Product. Lower layers may only narrow; any violation fails closed.');
    root.append(card(el('div', { class: 'row' }, el('strong', {}, 'Composition: '), status(!d.violations.length, 'no violations', `${d.violations.length} violation(s)`)),
      d.violations.length ? el('div', { class: 'error' }, list(d.violations)) : ''));
    const grid = el('div', { class: 'two-col' });
    for (const l of d.layers) {
      grid.append(card(el('h3', {}, `${l.name} · `, el('code', {}, l.path), ' ', tag(l.kind === 'editable' ? 'editable' : 'read-only', l.kind === 'editable' ? 'ok' : 'warn')),
        l.note ? el('div', { class: 'note' }, l.note) : '', l.error ? el('div', { class: 'error' }, l.error) : '', pre(l.config)));
    }
    root.append(grid);
    const eff = d.effective, t = eff.tools || {}, s = eff.safety || {};
    root.append(card(el('h3', {}, 'Effective config'),
      el('div', { class: 'row' }, tag('mode ' + s.mode), tag('writes ' + t.writes, t.writes === 'disabled' ? 'ok' : 'bad'), tag('sends ' + t.sends, t.sends === 'disabled' ? 'ok' : 'bad'),
        tag('capabilities: ' + (t.capabilities || []).join(', ')), tag('layers: ' + (eff.layers_applied || []).join(' → '))),
      pre(eff)));
    return root;
  };

  Dash.views.skills = async () => {
    const d = await api('/api/skills');
    const root = h('Skills', 'Registry from roles/pm/skills/README.md vs. SKILL.md files on disk; runtime copies checked by sha256 via adapter_sync.');
    root.append(card(el('div', { class: 'row' }, el('strong', {}, 'Adapter sync: '), status(!d.sync_problems.length, 'all copies hash-match', `${d.sync_problems.length} problem(s)`)),
      d.sync_problems.length ? el('div', { class: 'error' }, list(d.sync_problems)) : ''));
    const rows = d.skills.map(s => [
      el('code', {}, s.name),
      s.implemented ? tag('implemented', 'ok') : tag('planned', 'warn'),
      s.registry ? s.registry.Status : el('span', { class: 'muted' }, 'not in registry'),
      s.implemented ? el('span', {}, tag(s.in_manifest ? 'in manifest' : 'NOT in sync manifest', s.in_manifest ? 'ok' : 'bad'),
        tag('.claude ' + (s.copies['.claude/skills'] ? '✓' : '✗'), s.copies['.claude/skills'] ? 'ok' : 'bad'),
        tag('.agents ' + (s.copies['.agents/skills'] ? '✓' : '✗'), s.copies['.agents/skills'] ? 'ok' : 'bad'),
        s.sync_problems.length ? list(s.sync_problems) : '') : el('span', { class: 'muted' }, '—'),
      s.registry ? s.registry['Output'] : '',
      s.implemented ? el('span', {}, ...s.files.map(f => el('div', {}, el('code', {}, f)))) : '',
    ]);
    root.append(card(table(['Skill', 'State', 'Registry status', 'Runtime copies', 'Output (registry)', 'Files'], rows)));
    return root;
  };

  Dash.views.policies = async () => {
    const d = await api('/api/policies');
    const root = h('Policies', 'core/policies/*.md rendered as text. Edit them in the Text editor.');
    for (const p of d) root.append(card(el('h3', {}, p.name, ' ', el('code', {}, p.path)), el('div', { class: 'md' }, p.text)));
    return root;
  };

  Dash.views.product = async () => {
    const d = await api('/api/product');
    const root = h('Product pack — iGoal', d.note);
    root.append(card(el('h3', {}, 'Context index ', el('code', {}, d.context_index.path)), el('div', { class: 'md' }, d.context_index.text)));
    const recs = d.registry.records;
    const counts = {};
    for (const r of recs) counts[r.approval_status] = (counts[r.approval_status] || 0) + 1;
    root.append(card(el('h3', {}, 'Source registry ', el('code', {}, d.registry.path)), el('div', { class: 'note' }, d.registry.status),
      el('div', { class: 'row' }, ...Object.entries(counts).map(([k, v]) => tag(`${k}: ${v}`, k === 'approved' ? 'ok' : 'warn'))),
      table(['ID', 'Name', 'Type', 'Owner', 'Authority domain', 'Approval', 'Usage rule', 'Version / snapshot', 'URL'],
        recs.map(r => [r.source_id, r.name, r.type, r.owner, r.authority_domain,
          el('span', {}, tag(r.approval_status, r.approval_status === 'approved' ? 'ok' : 'warn'), el('div', { class: 'muted' }, r.approval_note || '')),
          r.usage_rule, r.version_or_snapshot, r.url]))));
    root.append(card(el('h3', {}, 'Product contract ', el('code', {}, d.contract.path)), pre(d.contract.config)));
    return root;
  };

  Dash.views.evaluations = async () => {
    const d = await api('/api/evaluations');
    const root = h('Evaluations', 'Synthetic fixtures under evaluations/fixtures/ and the smoke suite, run on demand.');
    root.append(card(table(['Fixture', 'Scenario', 'Files'], d.fixtures.map(f => [el('code', {}, f.name), f.scenario, f.files.join(', ')]))));
    const out = el('div');
    const btn = el('button', { class: 'btn primary', onclick: async () => {
      btn.disabled = true; out.innerHTML = '<p class="muted">Running…</p>';
      try {
        const r = await api('/api/evaluations/run', {});
        out.innerHTML = '';
        out.append(el('div', { class: r.ok ? 'success' : 'error' }, r.ok ? `PASS — ran ${r.ran} tests` : `FAIL — ran ${r.ran} tests, exit ${r.returncode}`), pre(r.output));
      } catch (e) { out.innerHTML = ''; out.append(Dash.errorBox(e)); }
      btn.disabled = false;
    } }, 'Run smoke tests');
    root.append(card(el('div', { class: 'row' }, btn, el('code', {}, d.command)), out));
    return root;
  };

  Dash.views.plans = async () => {
    const d = await api('/api/plans');
    const root = h('Plans & reports', d.plan_path ? 'Phases from ' + d.plan_path : 'plan.md not found');
    if (d.phases.length) {
      const heads = Object.keys(d.phases[0]);
      root.append(card(table(heads, d.phases.map(p => heads.map(k => k === 'Status' ? tag(p[k], /done/i.test(p[k]) ? 'ok' : /progress/i.test(p[k]) ? 'warn' : '') : p[k])))));
    }
    root.append(card(el('h3', {}, 'Reports (plans/reports/)'), table(['File', 'Title'], d.reports.map(r => [el('code', {}, r.path), r.title]))));
    return root;
  };
})();
