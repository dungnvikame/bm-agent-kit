# Bảng điều khiển PM Agent (`tools/dashboard/`)

Công cụ chạy trên máy để chủ kit **xem** agent PM đang làm được gì và **chỉnh** cấu hình an toàn, viết cho người không chuyên kỹ thuật. Không phải một phần của agent: Claude Code và Codex không đọc gì trong `tools/`, nên quy định "không có web UI trong agent MVP" vẫn giữ nguyên.

## Chạy

```bash
python3 tools/dashboard/serve.py            # http://127.0.0.1:8765
python3 tools/dashboard/serve.py --port 9000
python3 -m unittest discover -s tools/dashboard/tests
```

Chỉ dùng Python 3 chuẩn, không cài thêm gì, chỉ lắng nghe 127.0.0.1. Yêu cầu có `Host`/`Origin` không phải loopback bị từ chối.

## Các trang

| Trang | Trả lời câu hỏi | Lấy từ |
|---|---|---|
| Tổng quan | Agent có an toàn không? Làm được gì? Việc gì đang chờ tôi? | ba file cấu hình gộp bằng `kitlib.config_layers.compose`, sổ kỹ năng, sổ nguồn, kế hoạch |
| Agent làm được gì | Phạm vi được làm / chỉ bàn giao, công cụ được đọc, điều luôn khoá, kỹ năng | cấu hình hiệu lực; `roles/pm/skills/README.md` + `SKILL.md` trên đĩa; bản sao kiểm tra sha256 bằng `kitlib.adapter_sync.check` |
| Quy tắc an toàn | Agent phải tuân theo gì | `core/policies/*.md` hiển thị dạng văn bản dễ đọc |
| Nguồn dữ liệu iGoal | Nguồn nào được đọc, nguồn nào đã duyệt | `products/igoal/source-registry.json` (không có link thật), `context-index.md` |
| Kiểm tra chất lượng | Agent có vượt qua các tình huống khó không | `evaluations/fixtures/`; nút chạy `python3 -m unittest discover -s evaluations/smoke -v` |
| Tiến độ dự án | Đã làm tới đâu | bảng giai đoạn trong `plans/261101-2157-pm-agent-foundation/plan.md`, file trong `plans/reports/` |
| Cài đặt agent | Chỉnh vai trò PM và sản phẩm iGoal bằng ô có giải thích | `roles/pm/pm-role-contract.json`, `products/igoal/igoal-product-contract.json`; danh sách ô trong `static/settings-schema.js` |
| Văn bản hướng dẫn | Đọc bản dễ nhìn, bấm Sửa để chỉnh | `core/agent-instructions.md`, `core/policies/*.md`, `roles/pm/skills/<tên>/SKILL.md` và `references/*.md` |

Chi tiết kỹ thuật (JSON, log) nằm sau mục "Nâng cao" trên mỗi trang. Tên khoá kỹ thuật được dịch sang tiếng Việt trong `static/labels-vi.js`.

## Lưu diễn ra thế nào

Mọi lần lưu đi qua `tools/dashboard/repo_writer.py`:

1. Đường dẫn phải nằm trong danh sách cho phép ở `editable_paths.py` và trong kho. Bản sao sinh tự động (`AGENTS.md`, `CLAUDE.md`, `.claude/`, `.agents/`, `.codex/`), `core-contract.json`, schema, template, thư mục git và mọi thứ ngoài kho đều bị từ chối. Không tạo file mới.
2. File JSON phải là một object hợp lệ. Các khoá không có trong form được giữ nguyên.
3. Gộp lại Lõi → Vai trò → Sản phẩm với nội dung mới. Có vi phạm (ví dụ bật lại `tools.writes`) thì từ chối, hiện lý do bằng tiếng Việt, không ghi gì.
4. Ghi file. Nếu là file kỹ năng hoặc `core/agent-instructions.md`, chạy `adapter_sync.write` để cập nhật `.claude/skills`, `.agents/skills`, `AGENTS.md`, `CLAUDE.md` rồi `adapter_sync.check` xác nhận khớp.

Không có commit/push từ giao diện; xem `git diff` và tự commit.

## Riêng tư

Bảng điều khiển không bao giờ đọc hay liệt kê `runs/`, `products/*/source-registry.local.json`, `.env*` hay file spec cục bộ.

## Cấu trúc mã

`serve.py` (vào) → `dashboard_server.py` (HTTP + API JSON) → `repo_reader.py` / `repo_writer.py` / `smoke_runner.py` → `core/kitlib`. `editable_paths.py` giữ danh sách cho phép. Giao diện trong `static/`: `dashboard-core.js` (điều hướng, API), `labels-vi.js` (nhãn tiếng Việt), `markdown-lite.js` (hiển thị Markdown), `views-home.js`, `views-agent.js`, `views-sources.js`, `settings-schema.js` + `views-settings.js` (form cài đặt), `views-docs.js` (soạn văn bản). Test trong `tests/` chạy trên bản sao tạm của kho.
