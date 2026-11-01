# Synthetic approval records (fixtures only)

Human-written approval records as the Kit expects them (`core/contracts/schemas/approval-record.schema.json`). Approver names are role placeholders, not people. Tests pass these fixture paths directly to the scripts (any path inside the repo is accepted; real runs keep approvals under `runs/<run_id>/approvals/`). `action-approval.template.json` carries a placeholder hash; tests write a copy with the real `payload_hash` from a preview item, because an action approval is valid for one exact payload, operation and destination.
