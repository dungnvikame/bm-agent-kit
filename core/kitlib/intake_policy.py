"""Policy checks for an Intake Record (spec §5.1) on top of artifact_policy.common_checks."""
from . import artifact_policy


def check(record):
    """Return list of violation strings; empty == record passes schema + policy."""
    violations = artifact_policy.schema_errors(record, "intake-record.schema.json")
    if violations:
        return violations
    violations += artifact_policy.common_checks(record)

    for part in record["parts"]:
        if part["category_proposed"] == "bug" and part["reproducible"] != "yes":
            violations.append(f"part {part['part_id']}: category 'bug' requires reproducible=yes (rule+reproduce)")
        if part["severity_proposed"] != "unknown" and not part.get("severity_basis"):
            violations.append(f"part {part['part_id']}: severity_proposed needs severity_basis")

    artifact_policy.check_exhaustive(record["requirement_task_mapping"]["duplicate_search"], violations)

    if record["untrusted_instructions"]["detected"] and not record["untrusted_instructions"]["warnings"]:
        violations.append("untrusted_instructions.detected=true requires at least one warning entry")
    return violations
