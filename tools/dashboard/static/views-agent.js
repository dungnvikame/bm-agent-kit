/* "Agent làm được gì" (scope, tools, skills) and "Quy tắc an toàn" (policies rendered as documents). */
(() => {
  const { el, tag, list, card, page, get, help, advanced, pre } = Dash;

  Dash.views.agent = async () => {
    const [ov, sk] = await Promise.all([get('/api/overview'), get('/api/skills')]);
    const eff = ov.effective, scope = eff.scope || {}, tools = eff.tools || {}, comm = eff.communication || {};
    const core = ov.layers[0].config, coreCaps = (core.tools || {}).capabilities || [];
    const root = page('Agent làm được gì', 'Phạm vi công việc, công cụ được dùng và các kỹ năng đã có. Đây là kết quả sau khi gộp ba tầng cấu hình: lõi → vai trò PM → sản phẩm iGoal.');

    root.append(el('div', { class: 'two-col' },
      card(el('h2', {}, '✅ Được làm (WHAT và WHY)'), list((scope.allowed || []).map(Labels.scopeItem)),
        help('Agent chỉ trả lời "cần gì" và "vì sao". Mọi thứ đều là bản nháp chờ bạn duyệt.')),
      card(el('h2', {}, '🤝 Chỉ bàn giao, không tự làm'), list((scope.handoff_only || []).map(Labels.scopeItem)),
        help('Những việc này agent chỉ ghi "cần bàn giao cho Dev/Design/QA…", không tự quyết hay thực hiện.'))));

    root.append(card(el('h2', {}, '🔧 Công cụ'),
      el('div', { class: 'checklist' }, ...coreCaps.map(c => el('label', { class: (tools.capabilities || []).includes(c) ? '' : 'off' },
        (tools.capabilities || []).includes(c) ? '✅' : '🚫', Labels.cap(c), (tools.capabilities || []).includes(c) ? '' : el('span', { class: 'muted' }, ' (đã tắt ở tầng sản phẩm)'))))));

    root.append(card(el('h2', {}, '🔒 Luôn bị khoá (không tầng nào mở được)'),
      list([
        `Chế độ: ${Labels.mode[eff.safety.mode] || eff.safety.mode} — mọi kết quả là bản nháp cần người duyệt.`,
        `Ghi ra bên ngoài (tạo/sửa task, sửa tài liệu): ${tools.writes === 'disabled' ? 'tắt' : tools.writes}.`,
        `Gửi tin nhắn/email: ${tools.sends === 'disabled' ? 'tắt' : tools.sends}. Tự động gửi: ${comm.auto_send ? 'bật' : 'tắt'}.`,
        `Nhắc đến BOD: ${comm.auto_mention_bod ? 'được' : 'không'}. Soạn cho sponsor cần Tom cho phép trước: ${comm.draft_to_sponsor_requires_tom_approval ? 'có' : 'không'}.`,
        'Không bao giờ lưu: ' + ((eff.privacy || {}).never_persist || []).join(', ') + '.',
      ]),
      help('Muốn đổi những điểm này phải sửa cấu hình lõi và được Kit owner duyệt; bảng điều khiển này cố tình không cho sửa.')));

    const rows = sk.skills.map(s => [
      el('div', {}, el('strong', {}, s.name), el('div', { class: 'muted' }, Labels.skillDesc(s.name, s.registry && s.registry.Output))),
      s.implemented ? tag('Sẵn sàng', 'ok') : tag('Dự kiến', 'warn'),
      s.implemented ? (s.sync_ok ? tag('Khớp', 'ok') : tag(s.in_manifest ? 'Lệch' : 'Chưa đăng ký sao chép', 'bad')) : el('span', { class: 'muted' }, '—'),
      s.registry ? (s.registry['Gate / condition'] || '') : '',
    ]);
    root.append(card(el('h2', {}, '🧩 Kỹ năng'), Dash.table(['Kỹ năng', 'Trạng thái', 'Bản sao Claude/Codex', 'Điều kiện'], rows),
      help('"Dự kiến" = mới có mô tả trong sổ đăng ký, chưa thể gọi. "Khớp" = bản sao trong .claude/ và .agents/ giống hệt bản gốc.'),
      sk.sync_problems.length ? el('div', { class: 'error' }, list(sk.sync_problems)) : ''));
    root.append(advanced('Nâng cao: cấu hình hiệu lực (JSON) và các tầng', el('div', {}, pre(eff), ...ov.layers.map(l => el('div', {}, el('h3', {}, l.path), pre(l.config))))));
    return root;
  };

  Dash.views.rules = async () => {
    const policies = await get('/api/policies');
    const root = page('Quy tắc an toàn', 'Những quy tắc agent phải tuân theo. Lưu ý: chỉ một phần được phần mềm ép buộc (bảng trong README), phần còn lại là hướng dẫn agent phải tự tuân thủ.');
    root.append(el('div', { class: 'note' }, 'Tóm tắt: agent chỉ đọc nguồn được phép, không ghi/gửi ra ngoài, không lưu dữ liệu nhạy cảm (đánh giá nhân sự, lương thưởng, thông tin cá nhân, token), coi nội dung trong tài liệu/feedback là dữ liệu chứ không phải lệnh, và không bao giờ tự đặt "đã duyệt".'));
    for (const p of policies) {
      const d = el('details', { class: 'card' }, el('summary', {}, el('strong', {}, Labels.policyTitle(p.name)), ' ', el('span', { class: 'muted' }, p.path)));
      d.append(Markdown.node(p.text), el('div', { class: 'row' }, el('button', { class: 'btn', onclick: () => Dash.show('docs', p.path) }, 'Sửa văn bản này')));
      root.append(d);
    }
    return root;
  };
})();
