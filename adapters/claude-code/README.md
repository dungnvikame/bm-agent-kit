# Claude Code adapter

Verified against code.claude.com/docs/en/permissions on 2026-11-01.

## What is enforced by the runtime
- `pm-agent-settings.json` is loaded with `claude --settings adapters/claude-code/pm-agent-settings.json` (project-root session). Deny rules win over allow rules.
- `Edit(./core/**)` etc. block the agent from rewriting Kit rules during a run (Edit rules govern every file-editing tool, Write included); `Edit(./runs/**)` is pre-approved for local drafts, but `*.py/*.sh/*.js` under `runs/` are denied so the pre-approved `python3 -m unittest` cannot execute agent-written code.
- Allowlisted Kit scripts refuse inputs outside the repo and outputs outside `runs/` (path rules do not apply to files a script opens itself, so the scripts guard that themselves).
- `disableAutoMode: "disable"` keeps the human, not a classifier, on every prompt; `Read(./**)` keeps reads inside the project.
- MCP write tools are denied by exact name; read tools allowed by `mcp__<server>__get_*` style globs. **Server names must match the local MCP config** (`asana`, `slack`, `google-drive` are placeholders).
- `disableBypassPermissionsMode: "disable"` prevents `--dangerously-skip-permissions`.
- Everything else (any Bash not allowlisted, Write, other MCP tools) prompts the human in `default` mode.

## What is NOT enforced (instruction only)
Gate semantics, Fact/Inference labelling, WHAT/WHY scope, BOD/sponsor rules, "ok nội dung ≠ approval". Bash deny rules match command text only (`/usr/bin/curl` bypasses `Bash(curl *)`) — they are a guard rail, not a sandbox; anything not allowlisted still prompts the human in `default` mode. `sh/bash/zsh/python -c` are denied to shrink that surface.

## Skills
`.claude/skills/intake-feedback/` is a generated copy of `roles/pm/skills/intake-feedback/`. Never edit it directly; run `python3 core/scripts/kit-cli.py sync --write`.

## Not yet done
- No MCP servers are configured by this repo. Tom connects read-only connectors and sets server names; then update the deny/allow lists to the real names.
- Hooks (PreToolUse) that run `kit-cli.py scan` before any Write under `runs/` — candidate for the next phase.
