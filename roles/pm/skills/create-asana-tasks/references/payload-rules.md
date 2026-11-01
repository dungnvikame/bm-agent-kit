# create-asana-tasks — reference (proposal-only)

## Operation decision (policy-enforced)
| Proposal operation | Preview operation | Allowed when |
|---|---|---|
| `review_existing` | `link` | DEV.G3 approved + action approval (`operation: link`, hash match, `destination.task_id` = target) + target exists in task source — linking is an external write too |
| `update_proposal` | `update` | DEV.G3 approved + action approval (`operation: update`, hash match) + target verified |
| `new_task_proposal` | `create` | DEV.G3 approved + action approval (`operation: create`, hash match) + target verified + **no duplicate candidates** |
| `hold_for_shape`, `blocked`, any hypothetical | `blocked` | — reasons listed |

Anything else → `blocked` with reasons. Only `no_op` needs no approval. At most one write item (create/update/link) per action approval. Approvals must name this breakdown artifact and gate DEV.G3; `expires_at` is honoured; `destination` must equal the item's project/parent/task.

## Approval records (human-written, schema `approval-record.schema.json`)
- DEV.G3 artifact approval: `approval_type: artifact_only`, `gate: DEV.G3`, `artifact_id` = the breakdown artifact, `approver`, `approved_at`, `decision: approved`, `recorded_in {source_id, location}`.
- Action approval: `approval_type: action`, `operation`, `destination {project_id, parent_task_id?, task_id?}`, `payload_hash: sha256:<hash from the preview item>`, approver, timestamp, recorded_in.
- Approver names that look like an agent are rejected. "Ổn/tiếp tục/ok nội dung" are not approvals.

## Payload hash
`sha256` over the canonical JSON of `{name, notes, project_id, parent_task_id}` (sorted keys, no whitespace). Any change → new hash → stale approval → blocked.

## Side effects to surface
project followers notified · parent task gains a subtask · assignee/followers inherited from project defaults · new task lands in default section. Payload never sets assignee, due date, sprint or estimate.

## E09 / E10 / E11 behaviour
- E09 "ok nội dung → tiếp tục": artifact approval only → all write items `blocked` ("no valid action approval").
- E10 DEV.G3 missing or source changed after approval: `blocked` ("DEV.G3 not approved" / "payload_hash does not match").
- E11 timeout/retry: out of MVP scope (no write adapter); documented requirement for the future executor: readback + idempotency key.
