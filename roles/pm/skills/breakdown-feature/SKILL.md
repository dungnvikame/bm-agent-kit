---
name: breakdown-feature
description: Turn a validated Mapping Record into a draft Breakdown Record — problem/users/outcome/scope, user stories with Given/When/Then acceptance criteria (normal, empty, error, loading, permission, edge), role handoffs for Design/Dev/QA and task proposals as payload previews. Use when a human asks to break down, write stories/AC for, or prepare the build-ready pack of a feedback or problem. Read-only, WHAT/WHY only; without a human DEV.G2 approval record everything is labelled hypothetical and nothing is an official handoff.
---

# breakdown-feature

Status: phase 3, v0.2.0-draft. Human owner/reviewer: Tom. Mode: `read_only_draft`.

## Preconditions
- A validated Mapping Record under `runs/<run_id>/`.
- Optional: a **human-written** DEV.G2 approval record (`core/contracts/schemas/approval-record.schema.json`) saved by Tom under `runs/<run_id>/approvals/`. The agent never writes approval records.

## Procedure (spec §5.3)
1. **Pre-checks (script):**
   `python3 scripts/breakdown-preprocess.py runs/<run_id>/mapping-record.draft.json [--approval runs/<run_id>/approvals/dev-g2.json] --out runs/<run_id>/breakdown-record.draft.json`
   Sets `direction.status` (approved only with a valid DEV.G2 record), drafts the problem statement from intake parts, builds role handoffs from mapping blockers, converts each mapping part into a task proposal (`review_existing` / `update_proposal` / `hold_for_shape` / `new_task_proposal` / `blocked`), and runs a final duplicate check. Stories are left empty.
2. **Problem** — rewrite `problem`: statement, users, evidence refs, outcome, scope in / out. WHAT and WHY only.
3. **Direction** — write detail only for the approved direction. Hypothetical parts stay labelled `hypothetical`; `official_handoff` stays `false` until DEV.G2 is approved.
4. **Stories** — `As a / I want / so that` + observable Given/When/Then AC. Cover `normal` plus relevant `empty`, `error`, `loading`, `permission`, `edge`. No implementation detail.
5. **Handoffs** — Design: flow/state; Dev: feasibility/technical approach/estimate; QA: strategy/coverage/pass-fail. Owners are `keep_existing` or `role:<x>` proposals; never assign people, deadlines or sprints.
6. **Task proposals** — payload previews only; `new_task_proposal` needs an approved direction; a conflict stays `blocked`. Task creation belongs to `create-asana-tasks` after DEV.G3.
7. **Validate before saving:** `python3 core/scripts/kit-cli.py validate runs/<run_id>/breakdown-record.draft.json`.

## Output contract
Schema: `core/contracts/schemas/breakdown-record.schema.json`. Template: `templates/breakdown-record.template.json`. No estimate, deadline, sprint or assignee fields exist in the contract.

## Hard stops
Direction not approved → everything hypothetical, `official_handoff: false`. Never decide HOW, severity, estimate or owner. A Check/Done task is not evidence of release; QA handoff asks for it.

References: `references/breakdown-rules.md`.
