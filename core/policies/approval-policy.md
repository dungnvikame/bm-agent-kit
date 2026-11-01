# Approval Policy (Shared Core)

Source: spec §3 `approval`, §7.1.

## Principles
- `artifact_approval_is_execution_approval: false` — approving a PRD, a Problem Brief or a gate never authorises a write or a send.
- Downstream requires `approved_and_recorded_in_source_of_truth`.
- Creating development tasks requires `DEV.G3` **and** an explicit action approval.
- Content change invalidates action approval. Source change after approval requires gate revalidation.
- The agent never writes itself into `approved_by`.
- "Ổn", "tiếp tục", "ok nội dung" are content feedback, not action orders.

## Approval Pack (what a human needs to decide)
run/artifact/version · decision requested · sources and versions · full content/diff · target project/file/channel · side effects (notifications, followers) · gate prerequisites · approver with the right role · timestamp · scope of applicability · action status.

```json
{
  "approval_type": "artifact_only",
  "artifact_id": "SYN-IGOAL-EXAMPLE-PROBLEM",
  "artifact_version": "0.1-draft",
  "gate": "DEV.G1",
  "approver": null,
  "approved_at": null,
  "decision": "pending",
  "permits_external_write": false,
  "permits_send": false
}
```

## Action approval (future rounds only, write adapter off in MVP)
Must specify `operation + destination + payload hash/version + approver + timestamp`. Any change to content, destination, recipient, source version, or session expiry requires re-confirmation of the changed part. Even with approval, in MVP the agent hands the payload to Tom for manual entry; enabling a write adapter is a separate config change reviewed on its own.
