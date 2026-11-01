/* Plain-language Vietnamese labels for the technical keys in the kit. Unknown keys fall back to the key itself. */
const Labels = {
  capability: {
    read_docs: 'Đọc tài liệu (Google Docs/Drive)', read_sheets: 'Đọc bảng tính (Sheets)', read_tasks: 'Đọc task (Asana)',
    read_chat: 'Đọc chat (Slack)', read_dashboard: 'Đọc dashboard số liệu', web_search: 'Tìm kiếm web',
    local_draft_write: 'Ghi bản nháp trên máy (runs/)', write_tasks: 'Tạo/sửa task', send_messages: 'Gửi tin nhắn',
  },
  scope: {
    problem_and_outcome: 'Xác định vấn đề và kết quả mong muốn', personas_and_jtbd: 'Chân dung người dùng và việc cần làm (JTBD)',
    requirement_mapping: 'Đối chiếu feedback với yêu cầu/task hiện có', user_stories_and_acceptance_criteria: 'Viết user story và tiêu chí nghiệm thu',
    sprint_scope_proposal: 'Đề xuất phạm vi sprint', task_and_handoff_proposal: 'Đề xuất task và bàn giao cho các vai trò',
    status_and_outcome_summary: 'Tóm tắt tiến độ và kết quả',
    technical_implementation: 'Lập trình / quyết định kỹ thuật', ui_component_implementation: 'Dựng giao diện',
    test_automation: 'Tự động hoá kiểm thử', security_execution: 'Thực thi bảo mật', production_deployment: 'Triển khai lên production',
  },
  skill: {
    'pm-onboarding': 'Thiết lập ban đầu cho PM (kết nối nguồn, sở thích làm việc)',
    'intake-feedback': 'Tiếp nhận feedback: tách ý, gắn nhãn Fact/Suy luận/Đề xuất, che thông tin nhạy cảm, tìm task trùng',
    'map-requirements': 'Đối chiếu feedback với yêu cầu, quyết định và backlog (khớp / một phần / thiếu / mâu thuẫn)',
    'breakdown-feature': 'Bẻ nhỏ tính năng thành user story, tiêu chí nghiệm thu và đề xuất task',
    'create-asana-tasks': 'Chuẩn bị bản xem trước task Asana (chỉ xem trước, không tạo thật)',
    'evaluate-pm-output': 'Tự chấm bản nháp PM theo rubric trước khi đưa Tom duyệt',
    'draft-prd': 'Soạn PRD (WHAT/WHY)', 'summarize-sprint-status': 'Tóm tắt tình trạng sprint',
    'update-docs-on-completion': 'Đề xuất cập nhật tài liệu khi task xong', 'draft-stakeholder-update': 'Soạn cập nhật cho stakeholder',
  },
  policy: {
    'safety-policy': 'Quy tắc an toàn chung', 'tool-policy': 'Agent được dùng công cụ nào', 'evidence-contract': 'Bằng chứng: Fact phải có nguồn',
    'artifact-lifecycle-and-gates': 'Vòng đời bản nháp và các cổng duyệt (gate)', 'approval-policy': 'Phê duyệt: "ok nội dung" không phải lệnh hành động',
  },
  doc: {
    'core/agent-instructions.md': 'Hướng dẫn chung cho agent (mọi phiên đều đọc đầu tiên)',
    'roles/pm/pm-role-contract.json': 'Cấu hình vai trò PM', 'products/igoal/igoal-product-contract.json': 'Cấu hình sản phẩm iGoal',
    'core/contracts/core-contract.json': 'Cấu hình lõi (chỉ xem)',
  },
  approval: { approved: 'Đã duyệt', unknown: 'Chưa rõ', draft: 'Bản nháp', pending: 'Chờ duyệt', rejected: 'Bị từ chối' },
  sourceType: { doc: 'Tài liệu', sheet: 'Bảng tính', tasks: 'Dự án task', chat: 'Kênh chat', dashboard: 'Dashboard' },
  mode: { read_only_draft: 'Chỉ đọc và viết nháp' },

  cap(k) { return Labels.capability[k] || k; },
  scopeItem(k) { return Labels.scope[k] || k; },
  skillDesc(name, fallback) { return Labels.skill[name] || fallback || ''; },
  policyTitle(stem) { return Labels.policy[stem] || stem; },
  docTitle(path) {
    if (Labels.doc[path]) return Labels.doc[path];
    const m = path.match(/^roles\/pm\/skills\/([^/]+)\/(SKILL\.md|references\/(.+))$/);
    if (m) return m[2] === 'SKILL.md' ? `Kỹ năng "${m[1]}": hướng dẫn chính` : `Kỹ năng "${m[1]}": tài liệu tham khảo ${m[3]}`;
    const p = path.match(/^core\/policies\/(.+)\.md$/);
    return p ? 'Quy tắc: ' + Labels.policyTitle(p[1]) : path;
  },
  /* Translate a compose violation into a sentence a PM can act on. */
  violation(v) {
    let m = v.match(/\[(\w+)\] (\w+)\.(\w+) is locked by the upper layer \((.+?) -> (.+?)\)/);
    if (m) return `"${m[2]}.${m[3]}" đã bị khoá ở tầng trên (giá trị cố định ${m[4]}); không thể đổi thành ${m[5]}. Muốn đổi phải sửa cấu hình lõi và được Kit owner duyệt.`;
    m = v.match(/\[(\w+)\] (\w+)\.(\w+) adds items not in upper layer: (.+)/);
    if (m) return `"${m[2]}.${m[3]}" chỉ được thu hẹp, không được thêm mới. Mục không được phép: ${m[4]}.`;
    m = v.match(/\[(\w+)\] (\w+)\.(\w+) drops required items: (.+)/);
    if (m) return `"${m[2]}.${m[3]}" không được bỏ bớt mục tầng trên đã đặt: ${m[4]}.`;
    m = v.match(/\[(\w+)\] unknown (top-level )?key '(.+?)'/);
    if (m) return `Khoá "${m[3]}" không nằm trong danh sách cho phép; hệ thống từ chối mọi khoá lạ để an toàn.`;
    return v;
  },
};
