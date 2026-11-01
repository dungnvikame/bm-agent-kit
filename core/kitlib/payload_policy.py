"""Policy checks for a Task Payload Preview Record (spec §5.4, proposal-only MVP).

- write adapter disabled, handoff manual, external_action false (schema consts)
- every external write (create / update / link) needs: DEV.G3 approved record + action approval present whose
  payload_hash equals the item's hash and whose operation equals the item's; target verified; create has no
  duplicate candidates. Otherwise the item must be 'blocked'. Only no_op is free.
- preconditions are re-verified against the referenced approval files (repo-relative paths) — self-asserted
  'approved'/'present' strings are not trusted
- at most one write item per action approval; payload_hash must be the canonical hash of the payload
- update/link need target_task_id, create must not; blocked needs block_reasons
"""
from pathlib import Path

from . import artifact_policy
from .draft_record import REPO, load_approval, payload_hash

WRITE_OPS = {"create", "update", "link"}


def _reverify(record, violations):
    """Re-load the approval files the record claims; downgrade claims that do not hold."""
    pre = record["preconditions"]
    g3_ok = act_ok = False
    if pre["dev_g3"]["status"] == "approved":
        ref = pre["dev_g3"]["approval_ref"]
        path = REPO / ref if ref else None
        if not (path and path.exists()):
            violations.append("dev_g3.status=approved but approval_ref file is missing (fail closed)")
        else:
            rec, problems = load_approval(path, expect_gate="DEV.G3", expect_type="artifact_only",
                                          expect_artifact_id=record["breakdown_artifact_id"])
            g3_ok = rec is not None
            if not g3_ok:
                violations.append("dev_g3 approval file does not verify: " + "; ".join(problems))
    act = pre["action_approval"]
    if act["status"] == "present":
        ref = act["approval_ref"]
        path = REPO / ref if ref else None
        if not (path and path.exists()):
            violations.append("action_approval.status=present but approval_ref file is missing (fail closed)")
        else:
            rec, problems = load_approval(path, expect_gate="DEV.G3", expect_type="action",
                                          expect_artifact_id=record["breakdown_artifact_id"])
            if rec is None:
                violations.append("action approval file does not verify: " + "; ".join(problems))
            elif rec["payload_hash"] != act["payload_hash_expected"] or rec["operation"] != act.get("operation"):
                violations.append("action_approval fields do not match the referenced approval file")
            else:
                act_ok = True
        if not act.get("operation"):
            violations.append("action_approval.operation is required when status=present")
    return g3_ok, act_ok


def check(record):
    violations = artifact_policy.schema_errors(record, "payload-preview-record.schema.json")
    if violations:
        return violations
    violations += artifact_policy.common_checks(record)
    if record["artifact_id"] == record["breakdown_artifact_id"]:
        violations.append("artifact_id must differ from breakdown_artifact_id")
    g3_ok, act_ok = _reverify(record, violations)
    act, target = record["preconditions"]["action_approval"], record["target"]
    writes = 0

    for it in record["items"]:
        iid, op = it["item_id"], it["operation"]
        if it["payload_hash"] != payload_hash(it["payload"]):
            violations.append(f"item {iid}: payload_hash does not match payload content")
        if op in WRITE_OPS:
            writes += 1
            reasons = []
            if not g3_ok:
                reasons.append("DEV.G3 not approved/verified")
            if not act_ok:
                reasons.append("action approval missing/unverified")
            elif act["payload_hash_expected"] != it["payload_hash"]:
                reasons.append("action approval payload_hash does not match this payload (stale or different item)")
            elif act.get("operation") != op:
                reasons.append(f"action approval is for {act.get('operation')}, item is {op}")
            if not target["verified"]:
                reasons.append("target project/parent not verified against the task source")
            if op == "create" and it["duplicate_candidates"]:
                reasons.append("duplicate candidates present; human must decide link/update/no_op first")
            if reasons:
                violations.append(f"item {iid}: {op} not allowed -> must be blocked: " + "; ".join(reasons))
        if op in ("update", "link") and not it["target_task_id"]:
            violations.append(f"item {iid}: {op} requires target_task_id")
        if op == "create" and it["target_task_id"]:
            violations.append(f"item {iid}: create must not carry target_task_id")
        if op == "blocked" and not it["block_reasons"]:
            violations.append(f"item {iid}: blocked requires block_reasons")
    if writes > 1:
        violations.append("at most one write item (create/update/link) per action approval (one approval covers one exact payload)")
    return violations
