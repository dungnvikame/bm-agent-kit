/* What a PM may change in each contract, described in plain language. Anything not listed here is kept as-is on save
   (shown only under "Nâng cao"). Field types: text | textarea | taglist (free items, labelled) | checklist (pick from the
   upper layer's list: can only narrow) | locked (display only, owned by core). */
const SettingsSchema = {
  'roles/pm/pm-role-contract.json': {
    title: 'Vai trò PM', upper: 0,
    intro: 'Những gì agent PM được làm và được dùng. Tầng này chỉ có thể thu hẹp tầng lõi, không thể mở rộng.',
    groups: [
      { title: 'Ngôn ngữ', fields: [
        { path: ['language', 'chat'], type: 'text', label: 'Ngôn ngữ khi trò chuyện', help: 'Ví dụ: vi, en.' },
        { path: ['language', 'documents'], type: 'text', label: 'Ngôn ngữ trong tài liệu', help: 'Ví dụ: "vi + English inline".' },
      ] },
      { title: 'Phạm vi công việc', fields: [
        { path: ['scope', 'allowed'], type: 'taglist', labels: 'scope', label: 'Agent được làm', help: 'Các loại việc agent được phép làm (chỉ ở mức WHAT/WHY). Xoá mục để thu hẹp; thêm mục mới bằng mã kỹ thuật.' },
        { path: ['scope', 'handoff_only'], type: 'taglist', labels: 'scope', label: 'Chỉ bàn giao, không tự làm', help: 'Agent chỉ ghi "cần bàn giao" cho các việc này. Có thể thêm, nhưng không bỏ được mục tầng trên đã đặt.' },
      ] },
      { title: 'Công cụ được dùng', fields: [
        { path: ['tools', 'capabilities'], type: 'checklist', labels: 'capability', label: 'Được đọc từ', help: 'Bỏ chọn để cấm agent đọc một loại nguồn. Không thể bật thêm thứ lõi không cho phép.' },
      ] },
      { title: 'Kỹ năng', fields: [
        { path: ['skills', 'implemented'], type: 'taglist', labels: 'skill', label: 'Đã có', help: 'Chỉ liệt kê kỹ năng đã có file hướng dẫn trong roles/pm/skills/.' },
        { path: ['skills', 'planned_mvp'], type: 'taglist', labels: 'skill', label: 'Dự kiến trong MVP' },
        { path: ['skills', 'planned_later'], type: 'taglist', labels: 'skill', label: 'Dự kiến sau MVP' },
      ] },
      { title: 'Luôn khoá (do tầng lõi đặt)', fields: [
        { path: ['safety', 'mode'], type: 'locked', label: 'Chế độ', help: 'Chỉ đọc và viết nháp.' },
        { path: ['safety', 'human_gate_required'], type: 'locked', label: 'Bắt buộc người duyệt' },
        { path: ['tools', 'writes'], type: 'locked', label: 'Ghi ra bên ngoài (task, tài liệu)' },
        { path: ['tools', 'sends'], type: 'locked', label: 'Gửi tin nhắn' },
      ] },
    ],
  },
  'products/igoal/igoal-product-contract.json': {
    title: 'Sản phẩm iGoal', upper: 1,
    intro: 'Thông tin riêng cho iGoal: ai làm chủ, nguồn tri thức ở đâu, và thu hẹp thêm công cụ nếu cần.',
    groups: [
      { title: 'Chủ sở hữu', fields: [
        { path: ['owner'], type: 'text', label: 'Chủ sở hữu (owner)', help: 'Người chịu trách nhiệm nội dung sản phẩm trong kit.' },
        { path: ['reviewer'], type: 'text', label: 'Người duyệt (reviewer)', help: 'Người duyệt mọi bản nháp của agent cho iGoal.' },
      ] },
      { title: 'Nguồn tri thức', fields: [
        { path: ['knowledge', 'entrypoint'], type: 'text', label: 'Tài liệu agent đọc đầu tiên', help: 'Đường dẫn trong kho, ví dụ products/igoal/context-index.md.' },
        { path: ['knowledge', 'registry'], type: 'text', label: 'Sổ đăng ký nguồn', help: 'Đường dẫn file danh sách nguồn (không chứa link thật).' },
        { path: ['knowledge', 'official_inputs_require'], type: 'taglist', label: 'Một nguồn được coi là chính thức khi có', help: 'Ví dụ: approved_by, approved_at, version_or_snapshot.' },
        { path: ['knowledge', 'unapproved_sources'], type: 'text', label: 'Nguồn chưa duyệt được dùng như', help: 'Giữ "evidence_or_proposal_only" = chỉ làm bằng chứng/đề xuất.' },
        { path: ['knowledge', 'conflict_policy'], type: 'text', label: 'Khi hai nguồn mâu thuẫn', help: 'Giữ "show_conflict_and_block_affected_decision" = nêu mâu thuẫn và chặn quyết định liên quan.' },
      ] },
      { title: 'Công cụ được dùng cho iGoal', fields: [
        { path: ['tools', 'capabilities'], type: 'checklist', labels: 'capability', label: 'Được đọc từ', help: 'Chỉ có thể bỏ bớt so với vai trò PM. Ví dụ read_dashboard đang tắt vì iGoal chưa có dashboard được duyệt.' },
      ] },
      { title: 'Ghi chú', fields: [
        { path: ['notes'], type: 'textarea', label: 'Ghi chú cho người bảo trì', help: 'Tự do, không ảnh hưởng hành vi agent.' },
      ] },
      { title: 'Luôn khoá (do tầng lõi đặt)', fields: [
        { path: ['safety', 'mode'], type: 'locked', label: 'Chế độ' },
        { path: ['tools', 'writes'], type: 'locked', label: 'Ghi ra bên ngoài' },
        { path: ['tools', 'sends'], type: 'locked', label: 'Gửi tin nhắn' },
      ] },
    ],
  },
};
