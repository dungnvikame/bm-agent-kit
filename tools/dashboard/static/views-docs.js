/* Document editor: pick a canonical document (plain-language title), read it rendered, switch to edit, save.
   Saving a skill file or the agent instructions re-syncs the Claude Code / Codex copies on the server. */
(() => {
  const { el, tag, card, page, help, api } = Dash;
  const groupOf = p => p.startsWith('core/agent-instructions') ? 'Hướng dẫn chung cho agent' : p.startsWith('core/policies') ? 'Quy tắc' : p.startsWith('roles/pm/skills') ? 'Kỹ năng' : p.endsWith('.json') ? 'Cấu hình (sửa ở mục Cài đặt agent)' : 'Khác';

  Dash.views.docs = async (initialPath) => {
    const files = (await api('/api/files')).filter(f => !f.path.endsWith('.json'));
    const root = page('Văn bản hướng dẫn', 'Các văn bản agent đọc để biết cách làm việc. Bạn có thể đọc bản dễ nhìn, hoặc bấm "Sửa" để chỉnh nội dung gốc (định dạng Markdown).');
    let current = files.find(f => f.path === initialPath) || files[0];
    const listBox = el('div', { class: 'doc-list' }), view = el('div');
    const drawList = () => {
      listBox.innerHTML = '';
      let g = null;
      for (const f of files) {
        if (groupOf(f.path) !== g) { g = groupOf(f.path); listBox.append(el('div', { class: 'group' }, g)); }
        listBox.append(el('button', { class: f === current ? 'active' : '', onclick: () => { current = f; drawList(); load(); } }, Labels.docTitle(f.path), el('small', {}, f.path)));
      }
    };
    const load = async () => {
      view.innerHTML = '<p class="muted">Đang tải…</p>';
      const d = await api('/api/file?path=' + encodeURIComponent(current.path));
      const { meta, body } = Markdown.splitFrontMatter(d.text);
      const reading = el('div', {}, meta.description ? el('div', { class: 'note' }, el('strong', {}, 'Khi nào agent dùng: '), meta.description) : '', Markdown.node(body));
      const ta = el('textarea', { spellcheck: 'false' }, d.text), editor = el('div', { class: 'hidden' }, ta), result = el('div');
      const saveBtn = el('button', { class: 'btn primary hidden', disabled: 'disabled' }, 'Lưu');
      const editBtn = el('button', { class: 'btn' }, '✏️ Sửa');
      const cancelBtn = el('button', { class: 'btn hidden' }, 'Huỷ');
      const setMode = edit => { reading.classList.toggle('hidden', edit); editor.classList.toggle('hidden', !edit); saveBtn.classList.toggle('hidden', !edit); cancelBtn.classList.toggle('hidden', !edit); editBtn.classList.toggle('hidden', edit); };
      ta.addEventListener('input', () => { saveBtn.disabled = ta.value === d.text; });
      editBtn.addEventListener('click', () => setMode(true));
      cancelBtn.addEventListener('click', () => { ta.value = d.text; saveBtn.disabled = true; setMode(false); });
      saveBtn.addEventListener('click', async () => {
        saveBtn.disabled = true; result.innerHTML = '';
        try {
          const r = await api('/api/file', { path: current.path, text: ta.value });
          const box = el('div', { class: r.saved ? 'success' : 'note' }, r.saved ? '✅ Đã lưu.' : 'Không có gì thay đổi.');
          if (r.sync) box.append(' ', r.sync.problems.length ? el('span', { class: 'tag bad' }, 'Bản sao Claude/Codex bị lệch, báo người bảo trì') : el('span', { class: 'tag ok' }, 'Bản sao cho Claude Code và Codex đã được cập nhật'));
          result.append(box); Dash.refreshStatus(); await load();
        } catch (e) { result.append(Dash.errorBox(e)); saveBtn.disabled = false; }
      });
      view.innerHTML = '';
      view.append(card(
        el('div', { class: 'row' }, el('h2', { style: 'margin:0' }, Labels.docTitle(d.path)), d.kind === 'editable' ? '' : tag('chỉ xem', 'warn'), d.sync ? tag('lưu sẽ đồng bộ bản sao', 'info') : ''),
        el('div', { class: 'muted' }, d.path), d.note ? el('div', { class: 'note' }, d.note) : '',
        el('div', { class: 'row' }, d.kind === 'editable' ? editBtn : '', saveBtn, cancelBtn), result, reading, editor,
        help(d.sync ? 'Văn bản này được sao chép cho Claude Code (.claude/) và Codex (.agents/, AGENTS.md, CLAUDE.md); lưu ở đây là đủ, không sửa bản sao bằng tay.' : 'Lưu chỉ ghi file trong kho trên máy; không commit, không gửi đi đâu.')));
    };
    drawList(); root.append(el('div', { class: 'side-list' }, card(listBox), view)); await load();
    return root;
  };
})();
