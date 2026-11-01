# Phase 3 report — `breakdown-feature`, `create-asana-tasks` (proposal-only), `evaluate-pm-output`

Date: 2026-11-01 · Branch: `feat/pm-agent-phase3-skills` (stacked on `feat/pm-agent-map-requirements`; at Tom's request the dashboard branch was merged in as `91bd607`, so this branch now also carries PR #3's content) · Reviewer: Tom
Scope: the three remaining MVP skills from spec §12 step 3, the human Approval Record contract, fixtures E04/E09/E10 + evaluation cases, tests. All five MVP workflows now exist. Stops here for review.

## 0. Shared-folder note
A `pm-onboarding` skill appeared in this same checkout during phase 3 (`core/kitlib/onboarding.py`, `scripts/pm-onboarding.py`, `roles/pm/skills/pm-onboarding/`, `evaluations/smoke/test_onboarding.py`, `docs/pm-onboarding.md`, plus edits to six shared Kit files). The dashboard session states it did not write them (it only touches `tools/dashboard/**`); provenance is unknown — possibly Tom through the dashboard editor or another session. Those files are **not** part of this phase and are excluded from its commit; their additions to the six shared files were lifted out before committing and re-applied to the working tree afterwards, so nothing is lost but nothing of theirs is committed here. `pm-onboarding` is not in the spec's skill registry → see Open questions.

## 1. Files added / changed
```
core/contracts/schemas/approval-record.schema.json          NEW  human-written approvals (artifact_only | action with operation+destination+payload_hash)
core/contracts/schemas/breakdown-record.schema.json         NEW
core/contracts/schemas/payload-preview-record.schema.json   NEW  write_adapter/handoff_mode/external_action are constants
core/contracts/schemas/evaluation-record.schema.json        NEW  is_human_evaluation=false, final_grader=human, human_level=null constants
core/kitlib/draft_record.py                                 NEW  base Draft envelope, load_approval (verifies human approver, gate, type, artifact), payload_hash (canonical sha256)
core/kitlib/breakdown_policy.py  payload_policy.py  evaluation_policy.py  policy_registry.py   NEW
core/scripts/kit-cli.py                                     CHG  validate dispatches via policy_registry (5 record types)
scripts/breakdown-preprocess.py  create-asana-tasks-preprocess.py  evaluate-preprocess.py      NEW
roles/pm/skills/{breakdown-feature,create-asana-tasks,evaluate-pm-output}/{SKILL.md,references/*.md,templates/*.json}   NEW (canonical) + generated copies in .claude/skills, .agents/skills
evaluations/fixtures/synthetic-approvals/{dev-g2-approved,dev-g3-approved,action-approval.template,fake-agent-approval}.json + README
evaluations/fixtures/f08-breakdown-direction  f09-payload-artifact-approval-only  f10-payload-g3-and-stale-hash  f11-evaluate-fail-stop   NEW (expected.json; flows built from f02 input in tests)
evaluations/smoke/{phase3_helpers,test_phase3_breakdown_payload,test_phase3_evaluate}.py   NEW  11 tests
adapters/claude-code/pm-agent-settings.json (allow 4 new scripts), adapters/sync-manifest.json, roles/pm/pm-role-contract.json, roles/pm/skills/README.md, roles/pm/rubric/pm-output-rubric.md, core/agent-instructions.md (+AGENTS.md/CLAUDE.md), README.md, plan.md   CHG
```

## 2. What runs for real
Full chain on synthetic data: intake → mapping → breakdown → payload preview → evaluation, each step validated by its policy, each refusing invalid input and out-of-lane paths, none persisting a failing record.
- `breakdown-preprocess.py`: direction `approved` only with a valid human DEV.G2 record (else `hypothetical`, `official_handoff: false`); proposals per mapping part (`review_existing` / `update_proposal` only for exact/partial with a task, `hold_for_shape` / `new_task_proposal` for gaps, `blocked` for conflict/unknown); strong duplicates (score ≥ 0.3) block, weak ones become open questions; role handoffs from mapping blockers.
- `create-asana-tasks-preprocess.py`: item per proposal with exact payload + `sha256` hash, diff, side effects, final duplicate check, project/parent verification; any write (`create`/`update`/`link`) only when a DEV.G3 record for this breakdown + an action approval (gate DEV.G3, this artifact, `operation`, matching `destination`, equal hash) + verified target + existing parent/target task + (create) no duplicates; approval hash matching no item → `stale`; agent-named, expired or future-dated approvals → `invalid`.
- `evaluate-preprocess.py`: policy check of the evaluated record, five immediate-fail checks (IF1/IF2/IF4 decided, IF3 fail on self-approval/agent gate/unsourced fact else `needs_human`, IF5 not applicable), six rubric criteria with automated basis, `agent_level` null → verdict `incomplete`, or `fail_stop`.
- Tests: **55 Kit tests pass** (43 from phases 1–2 + 12 new); the separate `test_onboarding.py` in the working tree is not part of this phase.
- Code review (code-reviewer agent): 4 high / 4 medium / 2 low findings, all fixed with regression tests — DEV.G2 approval bound to the mapping artifact + version; action approval must match gate DEV.G3, this breakdown artifact, operation and destination; `expires_at`, future `approved_at` and Unicode look-alike agent names rejected; ghost parent or target tasks block; `payload_policy` re-verifies the referenced approval files instead of trusting self-asserted status; `link` treated as an external write; `new_task_proposal` requires a story with AC; evaluator survives schema-invalid input.

## 3. Still template / unverified
- Same as before: Codex adapter unexecuted; MCP names placeholders; Claude `--settings` load not demonstrated (skill discovery is confirmed — all skills appear in this session).
- LLM halves (stories/AC writing, advisory levels, problem statement) have no automated eval; tests cover the deterministic halves and that reviewer-filled records pass/fail policy correctly.
- Side-effect list (followers, notifications) is generic; real Asana behaviour must be confirmed with a read connector.
- E11 (write timeout/retry) remains out of MVP by design; E12 (incident / sponsor update) has no deterministic part.

## 4. Enforced by policy (only when a record passes `validate`)
Breakdown: approved ⇔ approval_ref; hypothetical ⇒ no official labels, no `new_task_proposal`, `official_handoff` false; approved ⇒ problem statement + stories cover normal and a non-happy path; targets consistent; blocked needs reasons; no estimate/owner/sprint fields exist.
Payload: `payload_hash` must equal canonical hash of payload; any write (create/update/link) ⇒ DEV.G3 approval file re-verified + action approval file re-verified (gate DEV.G3, this artifact, equal hash, same operation, matching destination) + verified target + (create) no duplicates; ≤ 1 write item per approval; only `no_op` is approval-free; `write_adapter: disabled`, `handoff_mode: manual_entry_by_human`, `external_action` false (constants).
Evaluation: exactly 5 checks and 6 criteria with spec weights; fail ⇒ `fail_stop`; null level ⇒ `incomplete`; score recomputed; `pass_advisory` ⇒ zero fails, zero violations, ≥ 85; `human_level` null, `is_human_evaluation` false (constants).
Approval records: schema + decision approved + human-looking approver + expected gate/type/artifact; action approvals need operation + destination + hash.

## 5. Spec → implementation
| Spec | Where |
|---|---|
| §5.3 steps 1–6 (problem, approved-only detail, G/W/T AC with edge coverage, role handoffs, owner proposals only, duplicate + provenance) | breakdown schema/policy/preprocess, `references/breakdown-rules.md` |
| §5.4 steps 1–5 (preview only, verify project/parent, DEV.G3 before dev tasks, action approval bound to payload/version, manual handoff in MVP) | payload schema/policy/preprocess, `references/payload-rules.md`; step 6 (readback/idempotency) documented as future executor requirement |
| §7.1 approval pack, action approval = operation + destination + payload hash + approver + time; content change invalidates | `approval-record.schema.json`, `draft_record.load_approval`, `payload_hash`, stale detection |
| §9.1 immediate fails, §9.2 rubric 0–4 × weights, self-check advisory | evaluation schema/policy/preprocess, `references/evaluation-rules.md` |
| §9.3 E04 / E09 / E10 | fixtures f08 / f09 / f10 |
| §3 `approval.create_development_tasks_requires: [DEV.G3, explicit_action_approval]` | payload_policy write rule |

## 6. Decisions for Tom
1. **Approval records as JSON files under `runs/<run_id>/approvals/`, written by Tom.** Alternative: Tom records approvals in the Source of Truth and the Kit reads an export. The file format is the contract either way.
2. **Agent-approver heuristic** rejects approver names containing agent/bot/claude/codex/gpt/llm. Should approvals instead be restricted to an allowlist of human roles (e.g. `role:pm-owner`, `role:tl`) kept in the Product Pack?
3. **Strong-duplicate threshold 0.3** (Jaccard) blocks a new task; weaker overlaps become questions. Tune after real snapshots.
4. **`link` is treated as an external write** (needs DEV.G3 + action approval with `operation: link`), per review; only `no_op` is approval-free. OK?
5. **DEV.G2 scope**: an approval record covers an artifact, not individual parts; `scope_of_applicability` is free text and the reviewer must downgrade out-of-scope parts to hypothetical by hand. Should approval records carry `part_ids`?
6. **Evaluation IF3 defaults to `needs_human`** for source content verification, so `pass_advisory` is possible with IF3 unverified. Alternatively require IF3 pass for pass_advisory (then the agent can never self-pass).
7. **Stacked branch**: PR for phase 3 will target `feat/pm-agent-map-requirements` until PR #2 merges, then retarget to `main`.

## Open questions
- `pm-onboarding` skill appearing from the dashboard session is outside the spec registry and the MVP five. Keep it as a separate PR with its own review, or fold into the Role Pack registry as an explicit addition?
- Who may sign DEV.G2/DEV.G3 in the pilot (Tom only, or PM owner + TL)? Needed for the approver allowlist in decision 2.
- Should `create-asana-tasks` also preview `comment`/`follower` changes, or stay name/notes/parent only until a read connector exists?
- Human rubric sheets: where do Tom/QA record `human_level` (proposal: `evaluations/results/<run_id>.json`, redacted, committed only after pilot approval)?
