"""Policy checks for an Intake Record beyond schema shape (spec §3, §5.1, §6, §7.1, §9.1).

These are ENFORCED only when the record passes through this check (CLI, tests,
or a hook). They do not constrain the LLM while it writes.
"""
from pathlib import Path

from . import sensitive_scanner
from .json_validator import load_schema, validate

SCHEMA = Path(__file__).resolve().parents[1] / "contracts" / "schemas" / "intake-record.schema.json"


def check(record):
    """Return list of violation strings; empty == record passes schema + policy."""
    violations = [f"schema: {e}" for e in validate(record, load_schema(SCHEMA))]
    if violations:
        return violations

    ea = record["external_action"]
    if ea["requested"] or ea["executed"]:
        violations.append("external_action must stay {requested:false, executed:false} in read_only_draft mode")

    ap = record["approval"]
    if ap["approved_by"] is not None or ap["approved_at"] is not None or ap["decision"] != "pending":
        violations.append("agent may not fill approved_by/approved_at or change decision from 'pending'")

    for gate, value in record["gate_status"].items():
        if value == "approved":
            violations.append(f"gate_status.{gate}=approved may only be set by a human with an approval record")

    for fact in record["facts"]:
        if fact.get("label") != "fact":
            violations.append("facts[] may contain only label=fact items")
        if not fact.get("source_ref"):
            violations.append(f"fact without source_ref: {fact.get('claim', '')[:60]!r}")
    for key in ("inferences", "proposals"):
        for item in record[key]:
            if item.get("label") == "fact":
                violations.append(f"{key}[] may not contain label=fact items")

    for part in record["parts"]:
        if part["category_proposed"] == "bug" and part["reproducible"] != "yes":
            violations.append(f"part {part['part_id']}: category 'bug' requires reproducible=yes (rule+reproduce)")
        if part["severity_proposed"] != "unknown" and not part.get("severity_basis"):
            violations.append(f"part {part['part_id']}: severity_proposed needs severity_basis")

    ds = record["requirement_task_mapping"]["duplicate_search"]
    if ds["exhaustive"] and ds["method"] != "full_backlog_audit":
        violations.append("duplicate_search.exhaustive=true requires method=full_backlog_audit")

    findings, detected = sensitive_scanner.scan_json_blob(record)
    if detected:
        cats = sorted({f["category"] for f in findings})
        violations.append(f"record still contains sensitive content {cats}; redact before persisting")

    if record["untrusted_instructions"]["detected"] and not record["untrusted_instructions"]["warnings"]:
        violations.append("untrusted_instructions.detected=true requires at least one warning entry")
    return violations
