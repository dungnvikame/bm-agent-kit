# Codex adapter (template — not executed on the build machine)

Verified against learn.chatgpt.com docs on 2026-11-01: project skills live in `.agents/skills/<name>/SKILL.md` (frontmatter `name` + `description`), `AGENTS.md` at repo root, project config in `.codex/config.toml` for trusted projects.

## What the runtime enforces (when the project is trusted)
- `sandbox_mode = "workspace-write"` + `network_access = false`: shell cannot reach the network; writes stay inside the workspace.
- No MCP server configured → no write capability exists. Adding a connector must use `enabled_tools` with read tools only.
- `approval_policy = "on-request"`: the agent asks before escalating.

## Not enforced
Sandbox does not restrict writes to `runs/` only (instruction does). Gate/approval semantics are instruction.

## Gaps
- Codex CLI not installed here → smoke test not run on Codex. Tom (or anyone with Codex) should run the README smoke steps and confirm the skill appears in the skills list.
- `.codex/config.toml` is ignored if the project is not trusted; untrusted sessions fall back to user-level config. Alternative: `codex --sandbox workspace-write --ask-for-approval on-request`.
