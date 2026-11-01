# Plan: PM Agent Foundation (bm-agent-kit)

Date: 2026-11-01 · Branch: `feat/pm-agent-foundation` · Spec: pm-agent-config v0.2.0-draft (local only)

## Goal
Turn the v0.2 spec into a runnable kit skeleton shared by Codex and Claude Code: 4 layers, one skill (`intake-feedback`), schemas, source registry, smoke tests, README. Stop for Tom's review before phase 2.

## Phases
| # | Phase | Status |
|---|---|---|
| 1 | Foundation: core policies/contracts/schemas, kitlib + CLI, PM role pack, iGoal product pack, adapters, `intake-feedback`, fixtures f01–f04, smoke tests, README | **done — awaiting Tom review** |
| 2 | `map-requirements` skill + requirement snapshot fixture; E03/E05 fixtures | not started |
| 3 | `breakdown-feature`, `create-asana-tasks` (proposal-only), `evaluate-pm-output` | not started |
| 4 | Close iGoal Context Index with Tom (approved sources, local registry, real MCP server names); PreToolUse hooks for scan/validate | not started |
| 5 | Codex smoke run on a machine with Codex CLI; P&OD #16 review session (local, not in repo) | not started |
| 6 | Pilot: 10 cases + baseline, human rubric results (redacted) under `evaluations/results/` | not started |

## Key decisions (phase 1)
- Machine-checked configs are JSON (stdlib only); spec YAML stays design notation.
- Canonical skill/instruction files + hash-checked copies instead of symlinks.
- Claude settings loaded via `--settings`, not committed as `.claude/settings.json`, so developer sessions aren't locked.
- Spec file and real URLs gitignored.

Report: `plans/reports/foundation-261101-2157-pm-agent-foundation.md`
