"""Policy checks shared by every Draft artifact (Intake Record, Mapping Record, ...).

Spec §3 output, §6 gate values, §7.1 approval, §3 privacy. Enforced only when a record
passes through a check (CLI, tests, hook) — never while the LLM writes.
"""
from pathlib import Path

from . import sensitive_scanner
from .json_validator import load_schema, validate

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "contracts" / "schemas"


def schema_errors(record, schema_name):
    return [f"schema: {e}" for e in validate(record, load_schema(SCHEMA_DIR / schema_name))]


def common_checks(record):
    """Draft-only, no action, no self-approval, no agent-approved gate, sourced facts, no sensitive content."""
    violations = []
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

    findings, detected = sensitive_scanner.scan_json_blob(record)
    if detected:
        cats = sorted({f["category"] for f in findings})
        violations.append(f"record still contains sensitive content {cats}; redact before persisting")
    return violations


def check_exhaustive(scope, violations, path="duplicate_search"):
    if scope.get("exhaustive") and scope.get("method") != "full_backlog_audit":
        violations.append(f"{path}.exhaustive=true requires method=full_backlog_audit")
