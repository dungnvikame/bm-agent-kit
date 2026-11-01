/* Home: answers three PM questions at a glance — is the agent safe, what can it do, what do I need to do next. */
(() => {
  const { el, tag, list, card, stat, page, get } = Dash;

  Dash.views.home = async () => {
    const [ov, sk, prod, plans] = await Promise.all([get('/api/overview'), get('/api/skills'), get('/api/product'), get('/api/plans')]);
    const eff = ov.effective, tools = eff.tools || {}, safety = eff.safety || {};
    const safe = tools.writes === 'disabled' && tools.sends === 'disabled' && safety.mode === 'read_only_draft' && !ov.violations.length;
    const ready = sk.skills.filter(s => s.implemented), planned = sk.skills.filter(s => !s.implemented);
    const recs = prod.registry.records, approved = recs.filter(r => r.approval_status === 'approved').length;
    const root = page('Tổng quan', 'Trang này cho biết agent PM hiện ở trạng thái nào, làm được gì, và việc gì đang chờ bạn.');

    const stats = el('div', { class: 'stats' },
      stat(safe ? 'ok' : 'bad', safe ? 'Agent đang ở chế độ an toàn' : 'Cần xem lại cấu hình',
        safe ? 'Chỉ đọc và viết bản nháp trên máy. Không tạo task, không gửi tin nhắn, không sửa tài liệu bên ngoài.' : ov.violations.length ? `${ov.violations.length} lỗi cấu hình đang chặn.` : 'Một cài đặt cho phép ghi/gửi đang bật.'),
      stat('info', `${ready.length} kỹ năng sẵn sàng · ${planned.length} dự kiến`, ready.map(s => s.name).join(', ') || 'Chưa có kỹ năng nào.'),
      stat(sk.sync_problems.length ? 'bad' : 'ok', sk.sync_problems.length ? 'Bản sao cho Claude/Codex bị lệch' : 'Claude Code và Codex dùng cùng một bản',
        sk.sync_problems.length ? 'Lưu lại một văn bản hướng dẫn để đồng bộ, hoặc chạy kit-cli sync --write.' : 'Hướng dẫn và kỹ năng được sao chép tự động và kiểm tra khớp.'),
      stat(approved ? 'ok' : 'warn', `${recs.length} nguồn dữ liệu iGoal · ${approved} đã duyệt`,
        approved ? 'Các nguồn đã duyệt được dùng làm căn cứ chính thức.' : 'Chưa nguồn nào được duyệt: agent chỉ dùng chúng làm bằng chứng/đề xuất, chưa phải căn cứ chính thức.'),
    );
    root.append(stats);

    const todos = [];
    if (ov.violations.length) todos.push('Sửa lỗi cấu hình (xem mục Cài đặt agent).');
    if (sk.sync_problems.length) todos.push('Đồng bộ lại bản sao kỹ năng cho Claude Code / Codex.');
    if (!approved) todos.push(`Đóng Context Index iGoal: xác nhận nguồn nào là chính thức (hiện ${recs.length} nguồn đều "chưa rõ").`);
    for (const p of plans.phases) if (/not started|chưa/i.test(p.Status || '')) todos.push(`Giai đoạn ${p['#']}: ${p.Phase} — chưa bắt đầu.`);
    for (const p of plans.phases) if (/awaiting|chờ/i.test(p.Status || '')) todos.push(`Giai đoạn ${p['#']}: đang chờ bạn review.`);
    root.append(card(el('h2', {}, 'Việc đang chờ bạn'), todos.length ? list(todos, 'todo') : el('p', { class: 'muted' }, 'Không có việc nào đang chờ.')));

    root.append(card(el('h2', {}, 'Agent được phép đọc từ đâu'),
      el('div', {}, ...(tools.capabilities || []).map(c => tag(Labels.cap(c), 'info'))),
      Dash.help('Danh sách này do cấu hình lõi đặt ra và từng tầng (vai trò, sản phẩm) chỉ có thể thu hẹp, không thể mở rộng.')));

    root.append(card(el('h2', {}, 'Dùng agent như thế nào'),
      el('ol', {},
        el('li', {}, 'Mở Claude Code trong thư mục kit với cấu hình an toàn: ', el('code', {}, 'claude --settings adapters/claude-code/pm-agent-settings.json')),
        el('li', {}, 'Gõ tên kỹ năng, ví dụ ', el('code', {}, '/intake-feedback'), ' rồi đưa feedback cần xử lý.'),
        el('li', {}, 'Agent trả về bản nháp trong thư mục ', el('code', {}, 'runs/'), ' kèm câu hỏi còn thiếu. Bạn đọc, sửa và quyết định; agent không tự gửi đi đâu cả.')),
      Dash.help('Mọi bản nháp đều ghi "cần người duyệt". Nói "ok nội dung" chỉ là đồng ý nội dung, không phải lệnh tạo task hay gửi tin.')));
    return root;
  };
})();
