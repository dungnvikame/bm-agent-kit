/* Field-level form for a JSON contract. Leaves become inputs; the original object is deep-copied and
   patched on read(). Lists of scalars edit as one item per line; anything deeper edits as raw JSON. */
const JsonForm = {
  // section.key pairs the core contract locks (mirror of kitlib.config_layers.LOCKED, display only — the server enforces)
  LOCKED: new Set(['safety.mode', 'safety.trust_mode', 'safety.human_gate_required', 'output.status', 'output.requires_human_review',
    'tools.default', 'tools.reads', 'tools.writes', 'tools.sends', 'tools.shell_network_bypass', 'tools.sensitive_content_persistence',
    'approval.artifact_approval_is_execution_approval', 'approval.downstream_requires', 'approval.content_change_invalidates_action_approval',
    'approval.changed_source_requires_gate_revalidation', 'communication.auto_send', 'communication.auto_mention_bod',
    'communication.draft_to_sponsor_requires_tom_approval', 'communication.escalate_to_nghia_requires_instruction', 'privacy.redacted_note', 'gates.namespaces']),

  isScalarList(v) { return Array.isArray(v) && v.every(x => ['string', 'number', 'boolean'].includes(typeof x)); },

  leafKind(v) {
    if (v === null) return 'null';
    if (typeof v === 'boolean') return 'boolean';
    if (typeof v === 'number') return 'number';
    if (typeof v === 'string') return 'string';
    if (JsonForm.isScalarList(v)) return 'list';
    return 'json';
  },

  input(kind, value, onChange) {
    let node;
    if (kind === 'boolean') {
      node = Dash.el('select', {}, Dash.el('option', { value: 'true' }, 'true'), Dash.el('option', { value: 'false' }, 'false'));
      node.value = String(value);
    } else if (kind === 'number') {
      node = Dash.el('input', { type: 'number', step: 'any', value: String(value) });
    } else if (kind === 'list') {
      node = Dash.el('textarea', { class: 'small', placeholder: 'one item per line' }, value.join('\n'));
    } else if (kind === 'json') {
      node = Dash.el('textarea', { class: 'small' }, JSON.stringify(value, null, 2));
    } else {
      node = Dash.el('input', { type: 'text', value: value === null ? '' : String(value), placeholder: kind === 'null' ? '(null)' : '' });
    }
    node.addEventListener('input', onChange);
    node.addEventListener('change', onChange);
    return node;
  },

  parse(kind, node, original) {
    const v = node.value;
    if (kind === 'boolean') return v === 'true';
    if (kind === 'number') return v.trim() === '' ? original : Number(v);
    if (kind === 'list') {
      const items = v.split('\n').map(s => s.trim()).filter(Boolean);
      const sample = original.find(x => typeof x !== 'string');
      return sample === undefined ? items : items.map(s => (typeof sample === 'number' ? Number(s) : s === 'true' ? true : s === 'false' ? false : s));
    }
    if (kind === 'json') return JSON.parse(v);
    if (kind === 'null') return v === '' ? null : v;
    return v;
  },

  setPath(obj, path, value) {
    let cur = obj;
    for (let i = 0; i < path.length - 1; i++) cur = cur[path[i]];
    cur[path[path.length - 1]] = value;
  },

  /* Renders into container. Returns { read(): object, dirty(): bool }. onChange fires after every edit. */
  build(container, original, onChange) {
    const working = JSON.parse(JSON.stringify(original));
    const walk = (value, path, host) => {
      const kind = JsonForm.leafKind(value);
      if (kind === 'json' && !Array.isArray(value) && value !== null) {
        host.append(Dash.el('div', { class: 'form-section' }, path.join('.')));
        for (const k of Object.keys(value)) walk(value[k], path.concat(k), host);
        return;
      }
      const dotted = path.join('.');
      const field = Dash.el('div', { class: 'form-field' + (JsonForm.LOCKED.has(dotted) ? ' locked' : '') });
      const node = JsonForm.input(kind, value, () => {
        try { JsonForm.setPath(working, path, JsonForm.parse(kind, node, value)); field.classList.remove('bad'); }
        catch (e) { field.classList.add('bad'); }
        onChange && onChange();
      });
      field.append(Dash.el('label', {}, dotted + ' ', Dash.el('span', { class: 'muted' }, kind)), node);
      host.append(field);
    };
    container.innerHTML = '';
    for (const k of Object.keys(original)) walk(original[k], [k], container);
    return {
      read: () => JSON.parse(JSON.stringify(working)),
      dirty: () => JSON.stringify(working) !== JSON.stringify(original),
    };
  },
};
