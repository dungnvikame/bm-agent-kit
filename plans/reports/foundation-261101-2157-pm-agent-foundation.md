# Foundation report — PM Agent Kit v0.2.0-draft (Step 1)

Date: 2026-11-01 · Branch: `feat/pm-agent-foundation` (new git repo, remote `origin` set, **not pushed**) · Reviewer: Tom
Scope delivered: 4-layer kit skeleton, `intake-feedback` skill, schemas, source registry (unclosed), smoke tests, README. Stopped before phase 2 as requested.

## 1. Directory tree (git-visible)
```
AGENTS.md  CLAUDE.md  README.md  .gitignore          # root instructions = byte-identical copies of core/agent-instructions.md
.claude/skills/intake-feedback/   .agents/skills/intake-feedback/   .codex/config.toml   # generated, hash-checked
core/
  agent-instructions.md
  policies/{safety,tool,evidence-contract,artifact-lifecycle-and-gates,approval}-policy.md
  contracts/core-contract.json  contracts/schemas/{intake-record,evidence-item,source-registry-record}.schema.json
  kitlib/{json_validator,sensitive_scanner,injection_detector,duplicate_finder,config_layers,adapter_sync,intake_policy,safe_paths,text_normalize}.py
  scripts/kit-cli.py
roles/pm/  pm-role-contract.json  pm-agent.md  skills/README.md  rubric/pm-output-rubric.md
           skills/intake-feedback/{SKILL.md, references/intake-procedure.md, templates/intake-record.template.json}
products/igoal/  igoal-product-contract.json  context-index.md  source-registry.json  source-registry.local.example.json  search-synonyms.json  glossary.md
adapters/  sync-manifest.json  claude-code/{pm-agent-settings.json,tool-mapping.json,README.md}  codex/{config.toml,tool-mapping.json,README.md}
scripts/intake-preprocess.py
evaluations/  README.md  fixtures/{synthetic-task-snapshot.json, f01-missing-evidence, f02-duplicate-open-task, f03-prompt-injection, f04-sensitive-content}/{input,expected}.json
              smoke/{test_smoke.py, test_hardening.py}
runs/  README.md  .gitkeep (content gitignored)
plans/261101-2157-pm-agent-foundation/plan.md  plans/reports/<this file>
```
Gitignored on purpose: `pm-agent-config-v0.2.0-review.md` (internal links, real feedback, staff names), `products/*/source-registry.local.json`, `runs/*`.

## 2. Runs for real (executed on this machine, Python 3.14 stdlib only)
- `core/kitlib/*` + `core/scripts/kit-cli.py` (`config-check`, `validate`, `scan`, `inject`, `dupes`, `sync --check|--write`)
- `scripts/intake-preprocess.py` — deterministic half of the skill: redaction, injection flags, duplicate candidates, schema-valid skeleton, refuses out-of-lane paths, never writes a record that fails policy
- `evaluations/smoke/*` — 27 tests
- Skill files load-able by Claude Code (shape verified against docs); `pm-agent-settings.json` syntax verified against docs

## 3. Still template / unverified
- `adapters/codex/*`, `.codex/config.toml`, `.agents/skills/*` — Codex CLI **not installed** here; never executed
- MCP server names `asana`, `slack`, `google-drive` in Claude settings — placeholders; no connector configured by repo
- End-to-end "skill appears + settings load" in a Claude Code session — nested `claude -p` failed on OAuth from the subshell; needs Tom to run `claude --settings adapters/claude-code/pm-agent-settings.json` once
- `source-registry.local.example.json` — placeholder URLs
- 8 of 9 skill names in registry — contracts only

## 4. Tests run
`python3 -m unittest discover -s evaluations/smoke -v` → **27 passed, 0 failed** (0.74 s). Also: `kit-cli.py config-check` OK (effective: mode=read_only_draft, writes=disabled, sends=disabled, read_dashboard removed by product layer); `kit-cli.py sync --check` OK.
Fixtures: f01 missing evidence (E06), f02 duplicate open task + 2-part split (E02/E04), f03 prompt injection (E08, 5 pattern families), f04 sensitive content (E07, fake token/email/phone/salary). Unit analogues for E09 (ok ≠ action), E10 (agent can't set gate approved).
Code review (code-reviewer agent) found 3 critical, 3 high, 6 medium issues → all fixed + 14 regression tests added: `runs/*.py` + unittest allow = code-exec path (denied), scripts bypassing Edit deny via `--out` (path guards), config_layers accepting `null`/wrong-typed locked values (now exact-match, unknown sub-keys rejected), scanner missing `DB_PASSWORD=`/`sk_live`/PEM/webhook/JWT (added), NFD Vietnamese + zero-width chars (normalised), injection run after redaction (now on raw text), record written before policy check (now only when clean), one-directional sync check (now both), `const:true` accepting `1`, unsupported schema keywords (fail closed).

## 5. Spec → file mapping
| Spec | Files |
|---|---|
| §1 MVP decision, §1.1 inheritance | `roles/pm/pm-agent.md`, `core/contracts/core-contract.json` (`extends`) |
| §2 four layers, compose order, fail-closed | dir layout; `core/kitlib/config_layers.py`; `kit-cli.py config-check` |
| §3 effective config YAML | split into `core-contract.json` (safety/tools/approval/communication/privacy/output/evaluation/gates), `pm-role-contract.json` (scope/language/skills), `igoal-product-contract.json` (knowledge) — JSON, machine-checked; YAML stays design notation |
| §4.1 source registry fields | `schemas/source-registry-record.schema.json`, `products/igoal/source-registry.json` (all `approval_status: unknown`, `url: unknown`) |
| §4.2 context reading, §4.3 authority, memory | `core/policies/evidence-contract.md`, `products/igoal/context-index.md` |
| §5 skill registry | `roles/pm/skills/README.md`, `pm-role-contract.json.skills` |
| §5.1 intake-feedback | `roles/pm/skills/intake-feedback/*`, `scripts/intake-preprocess.py`, `schemas/intake-record.schema.json`, `kitlib/intake_policy.py` |
| §6 workflow & gates, lifecycle, OPS | `core/policies/artifact-lifecycle-and-gates.md`, `core-contract.json.gates` |
| §7 tool rules, untrusted content, §7.1 approval pack | `core/policies/tool-policy.md`, `approval-policy.md`, `kitlib/injection_detector.py`, adapters settings/config |
| §8 P&OD #16 simulation | NOT copied (real data). Synthetic analogue: `fixtures/f02-duplicate-open-task` |
| §9 rubric, immediate fails, E01–E12 | `roles/pm/rubric/pm-output-rubric.md` (+ fixture status table), fixtures f01–f04 |
| §10 pilot metrics, run log fields | `runs/README.md` (log fields only); no results stored |
| §11 Codex vs Claude Code | `adapters/*`, `sync-manifest.json`, `kitlib/adapter_sync.py`, README enforcement matrix |
| §12 start sequence | `plans/261101-2157-pm-agent-foundation/plan.md` phases 2–6 |
| §3 privacy never_persist, §9.1 E07 | `kitlib/sensitive_scanner.py`, `kit-cli.py scan`, persist gate in `intake_policy` |

## 6. Decisions needing Tom's review
1. **Spec file excluded from git** (`.gitignore`). It holds Drive/Asana links, task IDs, a stakeholder feedback, owner names. Keep local, or produce a redacted copy under `docs/`?
2. **JSON, not YAML, for machine-checked config** (no PyYAML on either runtime by default). Spec YAML remains the design view.
3. **Claude settings via `--settings` flag**, not committed as `.claude/settings.json`, so Kit maintainers' sessions aren't locked by PM-run deny rules. Alternative: commit it and maintain via `settings.local.json` overrides (deny can't be overridden → would block maintenance).
4. **Codex adapter unverified** — needs one run on a machine with Codex CLI (project trust required for `.codex/config.toml`).
5. **MCP server names** — allow/deny lists must be redone with real connector names before any read connector is attached. Until then both runtimes have zero connectors (safest, matches spec §11).
6. **`WebFetch` denied** (exfiltration vector) while `WebSearch` allowed — stricter than spec wording ("web search allowed with filtered query").
7. **`runs/` may not contain executable files** (deny `*.py/*.sh/*.js`) — needed to close the unittest code-exec path. OK?
8. **Commit made on the feature branch, nothing pushed.** Confirm whether to push for review on GitHub.
9. Module keys in `context-index.md` (`bao-cao`, `check-in`, `phan-quyen`, `okr-structure`, `dashboard-metric`) are inferred from the spec, not from an approved module list.
10. Duplicate finder is recall-oriented (f02 part B still gets a weak 0.18 candidate on shared "báo cáo" tokens). Acceptable for "candidates for human review", or tighten threshold?

## Open questions (not resolvable from spec)
- Who owns Shared Core changes (spec: "owner Kit duyệt") — Tom alone, or a named group?
- Is the effective config meant to drive runtime behaviour later (then `config_layers` becomes a security control, not a lint)?
- Should a PreToolUse hook force `scan`/`validate` on every write under `runs/` (closes the "agent forgot to run it" gap)? Proposed for phase 4.
- Is `read_dashboard` ever expected for iGoal (currently removed at product layer because no source is registered)?
- Pilot run-log storage: local `runs/` only, or a shared redacted sheet owned by Tom?
