# BM Agent Kit — PM Agent foundation (v0.2.0-draft)

Runtime-agnostic agent kit for iKame's Business Management (BM) workflow. One business-logic source, two runtimes (OpenAI Codex, Claude Code). **Status: Agent Draft. Not production-approved. Read-only + local drafts only. No write/send capability is exposed.**

Spec: `pm-agent-config-v0.2.0-review.md` (kept local, gitignored — it contains internal links and real feedback).

## Four layers

| Layer | Path | Contains |
|---|---|---|
| Shared Core | `core/` | policies (safety, tool, evidence, lifecycle/gates, approval), contracts + JSON schemas, `kitlib` + `kit-cli.py` |
| Role Pack | `roles/pm/` | PM scope, skill registry, `intake-feedback` + `map-requirements` skills (canonical), rubric |
| Product Pack | `products/igoal/` | context index, source registry (URL-free), synonyms, glossary |
| Runtime Adapters | `adapters/{claude-code,codex}/` → generated `.claude/`, `.agents/`, `.codex/`, `AGENTS.md`, `CLAUDE.md` | permission config, tool mapping, hash-checked copies |

Compose order Core → Role → Product → Run. Lower layers only narrow. `kit-cli.py config-check` fails closed on any violation or unknown key.

## Quick start (either runtime)

```bash
python3 core/scripts/kit-cli.py config-check          # effective config, must print writes=disabled sends=disabled
python3 core/scripts/kit-cli.py sync --check          # AGENTS.md == CLAUDE.md == core/agent-instructions.md; skills hash-match
python3 -m unittest discover -s evaluations/smoke -v  # smoke + hardening + mapping tests
```

### Run the `intake-feedback` skill

**Claude Code** (verified on this machine, Claude Code 2.1.259):
```bash
claude --settings adapters/claude-code/pm-agent-settings.json
```
Then in the session: `/intake-feedback` (or ask "intake feedback này") and give the feedback JSON path, e.g. `evaluations/fixtures/f02-duplicate-open-task/input.json`. The skill runs `scripts/intake-preprocess.py`, fills the record, and must pass `kit-cli.py validate` before returning.

**Codex** (template only — Codex CLI is not installed on the build machine):
```bash
codex --sandbox workspace-write --ask-for-approval on-request
```
In a trusted project `.codex/config.toml` applies automatically. Skill is discovered from `.agents/skills/intake-feedback/SKILL.md`; invoke with `$intake-feedback` or by asking to intake a feedback. Same scripts, same schema, same validation.

**Without any agent** (deterministic part only):
```bash
python3 scripts/intake-preprocess.py evaluations/fixtures/f03-prompt-injection/input.json --out runs/demo/intake.json
python3 core/scripts/kit-cli.py validate runs/demo/intake.json
```

### Run the `map-requirements` skill (phase 2)
Chain after intake: `/map-requirements` (Claude Code) or `$map-requirements` (Codex) on the saved record. Deterministic part:
```bash
python3 scripts/intake-preprocess.py evaluations/fixtures/f07-conflicting-decisions/intake-input.json --out runs/demo/intake.json
python3 scripts/map-requirements-preprocess.py runs/demo/intake.json --out runs/demo/mapping.json
python3 core/scripts/kit-cli.py validate runs/demo/mapping.json
```
Snapshots default to the synthetic fixtures; pass `--requirements` / `--tasks` for real (repo-internal, redacted) snapshots once the Product Context Index is closed.

## Policy enforcement matrix (what is real vs. what is instruction)

| Policy (spec) | Claude Code | Codex | Kit scripts | Instruction only |
|---|---|---|---|---|
| No external write/send (§3 tools) | MCP write tools **denied by name** in `pm-agent-settings.json` (server names must match local config) | **No connector configured** → capability absent; `enabled_tools` allowlist when added | `validate` rejects `external_action` ≠ false | — |
| No shell/network bypass (§7) | `curl/wget/ssh/sh/python -c/...` deny rules + `WebFetch` denied (text-match guard, not sandbox); no executable files under `runs/` | `network_access=false` in sandbox (real) | — | — |
| Agent cannot edit Kit rules during a run | `Edit(./core/**)` etc. denied (covers Write); scripts refuse out-of-lane paths | not scoped (sandbox = whole workspace) | `sync --check` detects drift and extra files | yes |
| Sensitive zones never persisted (§3 privacy) | — | — | `scan` redacts; `validate` rejects records with hits | yes (agent must run it) |
| Untrusted content ≠ instruction (§7) | — | — | `inject` flags patterns; warnings carry no text | yes |
| Lower layer only narrows (§2) | — | — | `config-check` fail-closed | — |
| Fact needs source; bug needs reproduction; severity needs basis (§4, §5.1) | — | — | `validate` | yes |
| Mapping: exact needs AC basis, conflict blocks decision (ask_owner), check/done task needs QA or release evidence, no create action (§5.2) | — | — | `validate` (mapping_record) | yes |
| Agent never sets `approved_by` / gate `approved` (§6, §7.1) | — | — | `validate` | yes |
| "ok nội dung" ≠ action approval (§3, E09) | — | — | `validate` (external_action) | yes |
| Gate semantics, WHAT/WHY scope, BOD/sponsor/escalation rules, Draft lifecycle | — | — | — | **yes, only** |
| Duplicate search never claims exhaustive | — | — | `validate` | yes |

Scripts enforce only on artifacts that pass through them. Hooks that force `scan`/`validate` on every save are a next-phase item.

## Runnable vs. template

Runnable now: `core/kitlib/*`, `core/scripts/kit-cli.py`, `scripts/intake-preprocess.py`, `scripts/map-requirements-preprocess.py`, `evaluations/smoke/*`, fixtures f01–f07, `adapters/claude-code/pm-agent-settings.json` (loads in Claude Code), skill files (load as Claude Code skill).
Template / unverified: everything under `adapters/codex/` and `.codex/` (not executed), MCP server names in Claude settings, `source-registry.local.example.json`.

## Repository rules
- Synthetic or de-identified data only. No internal feedback, staff data, tokens, restricted docs.
- `runs/` is gitignored; `products/*/source-registry.local.json` is gitignored.
- Edit canonical files, then `kit-cli.py sync --write`. Never edit `AGENTS.md`, `CLAUDE.md`, `.claude/skills`, `.agents/skills`, `.codex/` by hand.
- No auto push/merge/deploy. Branch: `feat/pm-agent-foundation`.

## Maintainer dashboard
`python3 tools/dashboard/serve.py` → http://127.0.0.1:8765 (stdlib only, localhost only). Read views for layers/effective config, skills + adapter sync, policies, product pack, evaluations, plans; edit forms for the role/product contracts and canonical skill/policy/instruction files. Every save is refused on any compose violation and re-syncs adapter copies; no git actions, no private files. See `docs/dashboard-guide.md`.

## Not in MVP (by spec)
Web UI inside the agent runtime, vector DB, multi-agent orchestration, self-learning memory, write adapters, skills other than `intake-feedback` and `map-requirements` (see `roles/pm/skills/README.md` for planned contracts). A maintainer dashboard under `tools/` is being built separately and is not loaded by the agent.