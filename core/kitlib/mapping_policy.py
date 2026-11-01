"""Policy checks for a Mapping Record (spec §5.2) on top of artifact_policy.common_checks.

Rules enforced per mapping (see roles/pm/skills/map-requirements/references/mapping-rules.md):
- requirement_id must be one of the listed requirement_candidates (no out-of-thin-air IDs)
- exact/partial need requirement_id; exact also needs a non-blank match_basis (AC match)
- gap needs requirements_scanned>0 and no requirement_id; otherwise unknown
- conflict needs a conflict object and proposed_action=ask_owner; a detected conflict can't be relabelled;
  >=2 live decisions in one domain among candidates without a conflict object is a violation
- unknown needs >=1 blocker and a non-committal action
- match_type -> allowed proposed_action table; link_existing/no_op only on an APPROVED requirement
- task check/done needs release_evidence that cites a source_id listed in sources[] before link_existing/no_op
- proposed_action enum has no create/write; exhaustive only with full audit; counts non-negative
"""
from . import artifact_policy

NON_COMMITTAL = {"ask_owner", "unknown", "request_qa_evidence"}
VERIFIED_ONLY = {"link_existing", "no_op"}
ALLOWED_ACTIONS = {
    "exact": {"review_existing", "link_existing", "request_qa_evidence", "no_op", "ask_owner"},
    "partial": {"review_existing", "propose_new_scope", "hold_for_shape", "request_qa_evidence", "ask_owner"},
    "gap": {"hold_for_shape", "propose_new_scope", "ask_owner"},
    "conflict": {"ask_owner"},
    "unknown": NON_COMMITTAL,
}


def _evidence_cites_source(evidence, source_ids):
    return bool(evidence) and any(sid and sid in evidence for sid in source_ids)


def _live_conflict_without_object(m):
    by_domain = {}
    for c in m["requirement_candidates"]:
        if c.get("decision_status") == "live" and c.get("decision_ref"):
            by_domain.setdefault(c["domain"], set()).add(c["decision_ref"])
    return any(len(ids) >= 2 for ids in by_domain.values()) and not m["conflict"]


def check(record):
    violations = artifact_policy.schema_errors(record, "mapping-record.schema.json")
    if violations:
        return violations
    violations += artifact_policy.common_checks(record)
    scope = record["search_scope"]
    artifact_policy.check_exhaustive(scope, violations, "search_scope")
    if scope["requirements_scanned"] < 0 or scope["tasks_scanned"] < 0:
        violations.append("search_scope counts must be non-negative")
    if record["artifact_id"] == record["intake_artifact_id"]:
        violations.append("artifact_id must differ from intake_artifact_id")
    source_ids = {s["source_id"] for s in record["sources"]}

    for m in record["mappings"]:
        pid, mt, action, rid = m["part_id"], m["match_type"], m["proposed_action"], m["requirement_id"]
        cand_ids = {c["requirement_id"] for c in m["requirement_candidates"]}
        approved = {c["requirement_id"] for c in m["requirement_candidates"] if c["approval_status"] == "approved"}

        if rid is not None and rid not in cand_ids:
            violations.append(f"part {pid}: requirement_id {rid} is not among requirement_candidates (read and list it first)")
        if mt in ("exact", "partial") and not rid:
            violations.append(f"part {pid}: match_type {mt} requires requirement_id")
        if mt == "exact" and not (m["match_basis"] or "").strip():
            violations.append(f"part {pid}: exact requires match_basis (requirement AND acceptance criteria match)")
        if mt == "gap" and (rid or scope["requirements_scanned"] == 0):
            violations.append(f"part {pid}: gap requires requirements_scanned>0 and no requirement_id (else unknown)")
        if mt == "conflict" and not m["conflict"]:
            violations.append(f"part {pid}: conflict requires a conflict object")
        if mt != "conflict" and m["conflict"]:
            violations.append(f"part {pid}: a detected conflict may not be relabelled as {mt}")
        if _live_conflict_without_object(m):
            violations.append(f"part {pid}: candidates reference >=2 live decisions in one domain -> match_type must be conflict")
        if mt == "unknown" and not m["blockers"]:
            violations.append(f"part {pid}: unknown requires >=1 blocker")
        if action not in ALLOWED_ACTIONS[mt]:
            violations.append(f"part {pid}: proposed_action {action} not allowed for match_type {mt} ({sorted(ALLOWED_ACTIONS[mt])})")
        if action in VERIFIED_ONLY and rid not in approved:
            violations.append(f"part {pid}: {action} requires the matched requirement to be approved")
        for t in m["existing_tasks"]:
            if t["status"] in ("check", "done") and action in VERIFIED_ONLY and not _evidence_cites_source(t["release_evidence"], source_ids):
                violations.append(f"part {pid}: task {t['task_id']} is {t['status']}; {action} needs release_evidence citing a "
                                  f"source_id from sources[] (QA or release evidence), else request_qa_evidence")
    return violations
