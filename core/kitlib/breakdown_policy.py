"""Policy checks for a Breakdown Record (spec §5.3) on top of artifact_policy.common_checks.

- direction.status approved <=> approval_ref present (human DEV.G2 record); otherwise hypothetical
- hypothetical => official_handoff false, every story/proposal labelled hypothetical, no new_task_proposal
- approved => problem.statement present; stories cover 'normal' and at least one non-happy path
- new_task_proposal needs an approved direction AND at least one story for that part (no task without AC)
- every AC is Given/When/Then (schema); operations need/forbid target_task_id consistently; blocked needs reasons
- no estimate/deadline/sprint/assignee fields exist (schema additionalProperties=false)
"""
from . import artifact_policy

NON_HAPPY = {"empty", "error", "loading", "permission"}
NEEDS_TARGET = {"review_existing", "update_proposal"}
NO_TARGET = {"new_task_proposal", "hold_for_shape"}


def check(record):
    violations = artifact_policy.schema_errors(record, "breakdown-record.schema.json")
    if violations:
        return violations
    violations += artifact_policy.common_checks(record)
    artifact_policy.check_exhaustive(record["duplicate_check"], violations, "duplicate_check")
    if record["artifact_id"] in (record["mapping_artifact_id"], record["intake_artifact_id"]):
        violations.append("artifact_id must differ from upstream artifact ids")

    d = record["direction"]
    approved = d["status"] == "approved"
    if approved != (d["approval_ref"] is not None):
        violations.append("direction.status 'approved' requires approval_ref (human DEV.G2 record) and vice versa")
    if not approved and record["official_handoff"]:
        violations.append("official_handoff must be false while the direction is hypothetical")
    if approved and not (record["problem"]["statement"] or "").strip():
        violations.append("approved direction requires problem.statement")

    coverage, parts_with_stories = set(), set()
    for s in record["stories"]:
        if not approved and s["label"] != "hypothetical":
            violations.append(f"story {s['story_id']} must be labelled hypothetical (direction not approved)")
        coverage |= {ac["coverage"] for ac in s["acceptance_criteria"]}
        parts_with_stories.add(s["part_id"])
    if approved and record["stories"]:
        if "normal" not in coverage:
            violations.append("approved stories must cover the normal path")
        if not coverage & NON_HAPPY:
            violations.append(f"approved stories must cover at least one of {sorted(NON_HAPPY)}")

    for p in record["task_proposals"]:
        op, pid = p["operation"], p["proposal_id"]
        if not approved and p["label"] != "hypothetical":
            violations.append(f"proposal {pid} must be labelled hypothetical (direction not approved)")
        if op == "new_task_proposal":
            if not approved:
                violations.append(f"proposal {pid}: new_task_proposal needs an approved direction; use hold_for_shape")
            elif p["part_id"] not in parts_with_stories:
                violations.append(f"proposal {pid}: new_task_proposal needs at least one story with AC for part {p['part_id']}")
        if op in NEEDS_TARGET and not p["target_task_id"]:
            violations.append(f"proposal {pid}: {op} requires target_task_id")
        if op in NO_TARGET and p["target_task_id"]:
            violations.append(f"proposal {pid}: {op} must not carry target_task_id")
        if op == "blocked" and not p.get("block_reasons"):
            violations.append(f"proposal {pid}: blocked requires block_reasons")
    return violations
