# map-requirements — reference

## match_type decision table
| match_type | Condition | Required fields | Typical proposed_action |
|---|---|---|---|
| `exact` | requirement scope AND acceptance criteria cover the feedback part | `requirement_id` (must be a listed candidate), `match_basis` (which AC) | `review_existing` / `request_qa_evidence` / `ask_owner`; `link_existing` or `no_op` only when the requirement is **approved** and any check/done task has `release_evidence` citing a `source_id` in `sources[]` |
| `partial` | same problem, requirement lacks the behaviour/AC the feedback needs | `requirement_id` | `review_existing`, `propose_new_scope`, `hold_for_shape` |
| `gap` | requirements were scanned, none covers the part | `requirement_id: null`, `search_scope.requirements_scanned > 0` | `hold_for_shape` / `propose_new_scope` / `ask_owner` |
| `conflict` | ≥2 **live** decisions in the same domain (supersedes chains walked; rejected/superseded are inactive) | `conflict{domain, decision_ids, blocked_decisions}`; candidates carry `decision_status` | `ask_owner` (mandatory); the script's conflict cannot be dropped or relabelled |
| `unknown` | not enough searched/read | ≥1 `blockers[]` | `ask_owner` / `request_qa_evidence` / `unknown` |

## Authority reminders (core evidence-contract)
- Requirement rows without `approved_by/approved_at/version` are evidence, not committed scope.
- Asana `check` = dev done, awaiting QA. `done` = closed in Asana. Neither is release evidence. Ask for QA or release links first.
- Newer or higher-ranked sources do not win automatically; an approved decision with clear supersedes wins within its domain.
- Timeline milestones G1–G10 are not `DEV.G*` gates.

## Search scope statement
Always: `method`, `requirements_snapshot`, `tasks_snapshot`, counts, `module_filter`, `exhaustive: false`. Searching by both keyword and meaning (synonyms) is still a quick search.

## Worked examples (synthetic fixtures)
- `f05`: hierarchy feedback → `SYN-TR-05` (approved, AC match) → `exact`, `match_basis` cites AC 1 and 3; existing task `SYN-TASK-0007` is `check` → action `request_qa_evidence`, not `link_existing`.
- `f06`: same task in `check`, feedback repeats → blocker "no QA or release evidence", action `request_qa_evidence`; never "already fixed".
- `f07`: visibility feedback hits `SYN-TR-09` (DEC-03 approved) and `SYN-TR-10` (DEC-07 unknown) → `conflict`, blocked decision `report_visibility`, `ask_owner`; an independent UI part of the same feedback may still proceed.
