---
name: map-requirements
description: Map each part of a draft Intake Record to existing requirements, decisions and tasks — exact / partial / gap / conflict / unknown — with evidence, blockers and a non-committal proposed action. Use after intake-feedback when a human asks to map, cross-check, dedupe or align a feedback against requirements and the backlog. Read-only; never turns a keyword hit into committed scope; a conflict blocks the affected decision.
---

# map-requirements

Status: foundation v0.2.0-draft, phase 2. Human owner/reviewer: Tom. Mode: `read_only_draft`.

## Preconditions
- A validated Intake Record (`output_type: intake_record`) exists under `runs/<run_id>/`.
- Requirement/decision snapshot and task snapshot you are allowed to read (fixtures: `evaluations/fixtures/synthetic-requirements-snapshot.json`, `synthetic-task-snapshot.json`; real snapshots come from the Product Pack source registry once Tom closes it).

## Procedure (spec §5.2)
1. **Pre-checks (script, not by hand):**
   `python3 scripts/map-requirements-preprocess.py runs/<run_id>/intake-record.draft.json --out runs/<run_id>/mapping-record.draft.json`
   It finds requirement candidates per part (module-filtered, synonyms), carries duplicate task candidates from the intake, detects decision conflicts, and writes a schema-valid skeleton with `match_type: unknown` (or `conflict` when detected) and default blockers.
2. **Read candidate details** (requirement ID, scope, AC, approval; task detail) before concluding. Record every read in `sources[]`.
3. **Classify each part** — `exact` only when requirement AND acceptance criteria cover the feedback (write the AC match in `match_basis`); `partial` same problem but missing behaviour/AC; `gap` no scope in the sources read (only if requirements were actually scanned); `conflict` keep the script's finding, `proposed_action: ask_owner`; `unknown` when not searched enough — keep a blocker.
4. **Tasks in `check`/`done`**: ask for QA or release evidence (`request_qa_evidence`) before proposing reopen, link or closure. "Hoàn thiện" in a sheet or "Check" in Asana is not production evidence.
5. **Missing decision / source / gate** → `blockers[]` and `missing_decision` on that part only; never fill with assumptions. Continue the independent parts.
6. **proposed_action** is a proposal: `review_existing | link_existing | request_qa_evidence | hold_for_shape | propose_new_scope | ask_owner | no_op`. There is no create action; task creation belongs to `create-asana-tasks` (planned, proposal-only) after `DEV.G3`.
7. **Evidence**: facts need `source_ref`; search limits stay in `search_scope` with `exhaustive: false`.
8. **Validate before saving:** `python3 core/scripts/kit-cli.py validate runs/<run_id>/mapping-record.draft.json`. Fix every violation, then return the record and the open questions.

## Output contract
Schema: `core/contracts/schemas/mapping-record.schema.json`. Template: `templates/mapping-record.template.json`. Always `status: draft`, `external_action` false, `approval.approved_by: null`, no gate `approved`.

## Hard stops
Two sources with equal authority disagree → present both, name the blocked decision, ask Tom/owner. Reporter priority labels or P0 in a checklist never set severity. Never claim the backlog has no match after a quick search.

References: `references/mapping-rules.md`.
