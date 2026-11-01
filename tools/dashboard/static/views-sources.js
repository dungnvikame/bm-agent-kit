/* iGoal sources, quality checks (fixtures + smoke run) and project progress (plan phases + reports). */
(() => {
  const { el, tag, list, card, page, get, help, advanced, pre, api } = Dash;
  const approvalTag = s => tag(Labels.approval[s] || s, s === 'approved' ? 'ok' : 'warn');

  Dash.views.sources = async () => {
    const d = await get('/api/product');
    const recs = d.registry.records, approved = recs.filter(r => r.approval_status === 'approved').length;
    const root = page('Nguồn dữ liệu iGoal', 'Agent chỉ được đọc các nguồn trong danh sách này. Nguồn "đã duyệt" là căn cứ chính thức; nguồn "chưa rõ" chỉ dùng làm bằng chứng hoặc đề xuất.');
    root.append(el('div', { class: 'stats' },
      Dash.stat(approved ? 'ok' : 'warn', `${approved}/${recs.length} nguồn đã duyệt`, approved ? '' : 'Context Index chưa đóng. Bạn cần xác nhận nguồn chính thức và người duyệt cho từng nguồn.'),
      Dash.stat('info', 'Đường link thật không nằm ở đây', 'Link được giữ trong file riêng trên máy (source-registry.local.json), không đưa lên kho chung và không hiện trong bảng này.')));
    root.append(card(el('h2', {}, 'Danh sách nguồn'),
      Dash.table(['Mã', 'Tên nguồn', 'Loại', 'Chủ sở hữu', 'Dùng để', 'Duyệt', 'Cách dùng'],
        recs.map(r => [r.source_id, r.name, Labels.sourceType[r.type] || r.type, r.owner, r.used_for,
          el('span', {}, approvalTag(r.approval_status), el('div', { class: 'muted' }, r.approval_note || '')),
          r.usage_rule === 'evidence_or_proposal_only' ? 'Chỉ làm bằng chứng/đề xuất' : r.usage_rule])),
      help('Để duyệt một nguồn cần ghi người duyệt, ngày duyệt và phiên bản/snapshot vào sổ đăng ký (kế hoạch giai đoạn 4, làm cùng Tom).')));
    root.append(card(el('h2', {}, 'Mô tả sản phẩm và cách đọc nguồn (Context Index)'), Markdown.node(d.context_index.text)));
    root.append(advanced('Nâng cao: cấu hình sản phẩm (JSON)', pre(d.contract.config)));
    return root;
  };

  Dash.views.checks = async () => {
    const d = await get('/api/evaluations');
    const root = page('Kiểm tra chất lượng', 'Bộ tình huống giả lập (dữ liệu tổng hợp, không có dữ liệu thật) và bộ kiểm tra tự động chứng minh agent xử lý đúng các trường hợp khó.');
    const out = el('div');
    const btn = el('button', { class: 'btn primary', onclick: async () => {
      btn.disabled = true; out.innerHTML = '<p class="muted">Đang chạy, thường mất vài giây…</p>';
      try {
        const r = await api('/api/evaluations/run', {});
        out.innerHTML = '';
        out.append(el('div', { class: r.ok ? 'success' : 'error' }, r.ok ? `✅ Tất cả ${r.ran} kiểm tra đều đạt.` : `❌ Có kiểm tra không đạt (chạy ${r.ran}, mã thoát ${r.returncode}). Xem chi tiết bên dưới và báo cho người bảo trì kit.`),
          advanced('Chi tiết kỹ thuật', pre(r.output)));
      } catch (e) { out.innerHTML = ''; out.append(Dash.errorBox(e)); }
      btn.disabled = false;
    } }, '▶ Chạy kiểm tra ngay');
    root.append(card(el('div', { class: 'row' }, btn, el('span', { class: 'muted' }, 'Chạy toàn bộ bộ kiểm tra tự động của kit trên máy này.')), out));
    root.append(card(el('h2', {}, 'Tình huống giả lập'),
      Dash.table(['Tình huống', 'Kiểm tra điều gì'], d.fixtures.map(f => [el('strong', {}, f.name), f.scenario])),
      help('Mỗi tình huống là một feedback giả có vấn đề cụ thể (thiếu bằng chứng, trùng task, chèn lệnh, dữ liệu nhạy cảm, mâu thuẫn…). Bộ kiểm tra khẳng định agent không mắc lỗi tương ứng.')));
    return root;
  };

  Dash.views.progress = async () => {
    const d = await get('/api/plans');
    const root = page('Tiến độ dự án', 'Các giai đoạn xây dựng kit và báo cáo sau mỗi giai đoạn.');
    const statusTag = s => tag(s, /done|xong/i.test(s) ? 'ok' : /progress|đang/i.test(s) ? 'info' : /awaiting|chờ/i.test(s) ? 'warn' : '');
    if (d.phases.length) root.append(card(el('h2', {}, 'Giai đoạn'), Dash.table(['#', 'Nội dung', 'Trạng thái'], d.phases.map(p => [p['#'], p.Phase, statusTag(p.Status || '')]))));
    root.append(card(el('h2', {}, 'Báo cáo'), list(d.reports.map(r => el('span', {}, el('strong', {}, r.title), ' ', el('span', { class: 'muted' }, r.path)))),
      help('Báo cáo là file markdown trong plans/reports/; mở bằng trình soạn thảo bất kỳ.')));
    return root;
  };
})();
