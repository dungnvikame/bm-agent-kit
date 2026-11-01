# Phase 2 report — `map-requirements` skill (spec §5.2)

Date: 2026-11-01 · Branch: `feat/pm-agent-map-requirements` (from `main` @ `49c9309`, PR #1 merged) · Reviewer: Tom
Scope: second MVP skill + its schema, policy, deterministic preprocess, synthetic requirement/decision snapshot, fixtures E01/E03/E05, tests. Stops here for review before phase 3.

## 0. Related work in this checkout
The maintainer dashboard (Tom's request, separate session) landed in this same folder under `tools/dashboard/`, `docs/dashboard-guide.md` and a README section. It is committed on its own branch `feat/maintainer-dashboard`, not in the phase 2 commit.

## 1. Files added / changed
```
core/contracts/schemas/mapping-record.schema.json          NEW  Mapping Record contract
core/kitlib/artifact_policy.py                             NEW  shared Draft checks (extracted from intake_policy)
core/kitlib/intake_policy.py                               CHG  now intake-specific rules only
core/kitlib/mapping_policy.py                              NEW  §5.2 rules (exact/partial/gap/conflict/unknown, check/done evidence, no create)
core/kitlib/requirement_matcher.py                         NEW  requirement candidates + decision-conflict detection
core/scripts/kit-cli.py                                    CHG  `validate` dispatches on output_type (intake_record | mapping_record)
scripts/map-requirements-preprocess.py                     NEW  intake record -> mapping skeleton (refuses invalid intake, out only under runs/)
roles/pm/skills/map-requirements/{SKILL.md, references/mapping-rules.md, templates/mapping-record.template.json}  NEW (canonical)
.claude/skills/map-requirements/, .agents/skills/map-requirements/   generated copies (hash-checked)
evaluations/fixtures/synthetic-requirements-snapshot.json  NEW  5 requirements, 2 decisions (same domain, no supersedes -> conflict)
evaluations/fixtures/synthetic-task-snapshot.json          CHG  SYN-TASK-0007 status -> check
evaluations/fixtures/f05-full-sources-exact/ f06-task-in-check-feedback-repeats/ f07-conflicting-decisions/   NEW
evaluations/smoke/test_mapping.py                          NEW  12 tests
roles/pm/pm-role-contract.json, roles/pm/skills/README.md, roles/pm/rubric/pm-output-rubric.md, core/agent-instructions.md (+AGENTS.md/CLAUDE.md), intake SKILL.md, README.md, plan.md   CHG
```

## 2. What runs for real
- `scripts/map-requirements-preprocess.py <intake.json> [--out runs/...]`: validates the intake first (refuses otherwise), finds requirement candidates per part (module filter + synonyms), carries duplicate tasks with status, detects decision conflicts, writes a schema+policy-valid skeleton. `match_type` stays `unknown` unless a conflict is detected (`conflict` + `ask_owner`); tasks in `check`/`done` default the action to `request_qa_evidence`.
- `kit-cli.py validate` on mapping records.
- Pipeline intake → mapping on fixtures f05–f07 and all tests: **43 passed** (27 phase 1 + 16 phase 2).
- Code review (code-reviewer agent) found 3 high / 2 medium / 2 low issues, all fixed with regression tests: supersedes chain now transitive and rejected/superseded decisions are inactive (`decision_status` per candidate); `release_evidence` must cite a `source_id` listed in `sources[]` (free text no longer unblocks link/no_op); `requirement_id` must be a listed candidate; a live conflict cannot be dropped or relabelled; match_type → allowed-action table enforced and `link_existing`/`no_op` need an approved requirement; `--synonyms` path guarded; artifact_id guard; unknown decision refs surface as blockers.

## 3. Still template / unverified
- Same as phase 1: Codex adapter unexecuted; MCP names placeholders; Claude `--settings` load not demonstrated end-to-end (skill discovery in Claude Code IS confirmed: both skills show in this session's skill list).
- Requirement/decision snapshot is synthetic; the real S4/S5/S8/S9 extraction format (how Tom will export rows) is undefined → open question.
- The LLM half of the skill (deciding exact/partial/gap, reading candidate details) has no automated eval yet; fixtures assert the deterministic half and that a reviewer-filled record passes/fails policy correctly.

## 4. Enforced by `mapping_policy` (only when a record passes through validate)
requirement_id ∈ listed candidates · exact ⇒ requirement_id + non-blank match_basis · partial ⇒ requirement_id · gap ⇒ requirements_scanned>0 and no requirement_id · conflict ⇒ conflict object + `ask_owner`; a detected or live conflict cannot be dropped/relabelled · unknown ⇒ ≥1 blocker · match_type → allowed proposed_action table · `link_existing`/`no_op` ⇒ approved requirement AND any check/done task has `release_evidence` citing a `source_id` in `sources[]` · no create/write action exists · `exhaustive` only with full audit · counts non-negative, artifact_id ≠ intake id · plus all shared Draft checks (external_action false, no self-approval, no gate approved, facts sourced, no sensitive content).

## 5. Spec §5.2 → implementation
| Step | Where |
|---|---|
| 1 find requirement by module/outcome, keep ID/scope/AC/approval | `requirement_matcher.find_requirement_candidates` (module filter), candidates carry `approval_status`, `domain`, `decision_ref` |
| 2 search existing tasks, read detail before concluding | existing_tasks carried from intake duplicate candidates with status; SKILL.md step 2 (LLM reads detail; `sources[]`) |
| 3 map `feedback_part → requirement_id → match_type → existing_task → missing_decision → proposed_action` | `mappings[]` object shape in schema |
| 4 exact/partial/gap/unknown definitions | `mapping_policy` + `references/mapping-rules.md` table |
| 5 check/done tasks need QA/release evidence; "Hoàn thiện" ≠ production | `release_evidence` field + policy; default action `request_qa_evidence` (f06) |
| 6 missing source/gate or conflict → blocker per part, no assumptions | `blockers[]`, `missing_decision`, `conflict` per part; `detect_conflict` (f07) |
| §4.3 conflict policy "show both, block affected decision, ask owner" | `conflict.blocked_decisions`, mandatory `ask_owner`, open question generated |

## 6. Decisions for Tom
1. Conflict detection relies on `decision_ref` + `domain` + `supersedes` fields on requirement/decision rows. The real S4/S5 export must carry these (or Tom maps them); otherwise conflicts are invisible to the script and only the LLM step can surface them.
2. Default action for a `check`/`done` task is `request_qa_evidence` even when the requirement is approved — stricter than "review_existing". OK?
3. `release_evidence` must now cite a `source_id` present in `sources[]` (policy-enforced after review). Is a cited source enough, or should QA evidence be its own typed object (run id, build, date, verdict)?
4. Module filter drops requirements from other modules; cross-module requirements only match if their row says `module: unknown`. Acceptable for MVP?
5. Phase 3 order: `breakdown-feature` → `create-asana-tasks` (proposal-only) → `evaluate-pm-output`, or evaluation first so the rubric self-check exists before more artifacts?

## Open questions
- Export format and cadence for requirement/decision/task snapshots from the real sources (who runs it, where the redacted copy lives — proposal: `runs/<run_id>/snapshots/`, gitignored).
- Who is "owner" for `ask_owner` per domain — product-pack field `domain_owners` missing from the spec.
- Should the Intake Record be updated (`requirement_task_mapping.status: done` + mapping artifact id) after mapping, or stay immutable with the Mapping Record referencing it (current choice: immutable)?
