# breakdown-feature — reference

## Direction and labels
| direction.status | How it is set | Effect (policy-enforced) |
|---|---|---|
| `approved` | valid human DEV.G2 approval record supplied (`approver`, `approved_at`, `recorded_in`, decision approved) | stories/proposals may be `official`; `new_task_proposal` allowed; problem.statement required; stories must cover `normal` + one of empty/error/loading/permission |
| `hypothetical` | no/invalid approval record | every story and proposal `hypothetical`; `official_handoff: false`; no `new_task_proposal` (use `hold_for_shape`) |

## AC coverage checklist
normal · empty state · error/failure · loading/latency · permission/visibility · edge (long titles, many items, concurrent edit, reload). Each AC: `given` (context), `when` (action), `then` (observable result). No UI widget names, no implementation.

## Task proposal operations
| operation | when | target |
|---|---|---|
| `review_existing` | mapping exact + existing task | required |
| `update_proposal` | mapping partial + existing task (scope/AC diff to propose) | required |
| `hold_for_shape` | gap/partial without task, direction not approved | none |
| `new_task_proposal` | gap/partial without task, direction approved, no duplicate candidate | none |
| `blocked` | conflict, unknown mapping, duplicate candidate found | — (reasons required) |

## Handoffs
Design decides flow/state; Dev decides feasibility/approach/estimate; QA decides strategy/coverage/pass-fail. PM lists asks; owners stay `keep_existing` on existing tasks or are `role:<x>` proposals.

## Worked example (synthetic)
Mapping with part A exact→task `SYN-TASK-0007` (check) and part B gap: proposals `TP-01 review_existing → SYN-TASK-0007`, `TP-02 hold_for_shape` (no DEV.G2 record) — both `hypothetical`; QA ask "release evidence for SYN-TASK-0007". With a DEV.G2 record covering direction A only, the reviewer keeps part B hypothetical in their stories.
