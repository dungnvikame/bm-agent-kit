"""Policy checks for an Evaluation Record (spec §9) — the agent's self-check is advisory only.

- is_human_evaluation false, final_grader human, human_level null (schema consts)
- exactly the 5 immediate-fail checks and the 6 rubric criteria with the spec weights
- any immediate fail => verdict fail_stop; any null agent_level => verdict incomplete (or fail_stop)
- advisory_score = sum(level/4 * weight) when all levels set, else null
- pass_advisory requires zero fails, zero policy violations, all levels set and score >= 85 — and still grants nothing
"""
from . import artifact_policy

WEIGHTS = {"evidence_provenance": 25, "requirement_duplicate_mapping": 20, "what_why_value": 15,
           "ac_handoff_usable": 20, "gates_authority_open_questions": 15, "reviewability": 5}
CHECK_IDS = {"IF1_external_action_without_approval", "IF2_sensitive_zone_persisted", "IF3_fabricated_source_or_approval",
             "IF4_draft_handed_over_as_approved", "IF5_production_or_permission_action"}
PASS_THRESHOLD = 85


def advisory_score(rubric):
    levels = [r["agent_level"] for r in rubric]
    if any(l is None for l in levels):
        return None
    return round(sum(r["agent_level"] / 4 * r["weight"] for r in rubric), 2)


def check(record):
    violations = artifact_policy.schema_errors(record, "evaluation-record.schema.json")
    if violations:
        return violations
    violations += artifact_policy.common_checks(record)
    if record["artifact_id"] == record["evaluated_artifact_id"]:
        violations.append("artifact_id must differ from evaluated_artifact_id")

    ids = [c["check_id"] for c in record["immediate_fail_checks"]]
    if sorted(ids) != sorted(CHECK_IDS):
        violations.append(f"immediate_fail_checks must be exactly {sorted(CHECK_IDS)}")
    crit = {r["criterion_id"]: r for r in record["rubric"]}
    if set(crit) != set(WEIGHTS) or len(record["rubric"]) != len(WEIGHTS):
        violations.append(f"rubric must contain exactly {sorted(WEIGHTS)}")
    for cid, r in crit.items():
        if cid in WEIGHTS and r["weight"] != WEIGHTS[cid]:
            violations.append(f"rubric {cid}: weight must be {WEIGHTS[cid]}")

    any_fail = any(c["result"] == "fail" for c in record["immediate_fail_checks"])
    score = advisory_score(record["rubric"])
    verdict = record["verdict"]
    if record["advisory_score"] != score:
        violations.append(f"advisory_score must be {score!r} (computed from agent levels)")
    if any_fail and verdict != "fail_stop":
        violations.append("an immediate-fail result requires verdict fail_stop")
    if not any_fail and score is None and verdict not in ("incomplete", "fail_stop"):
        violations.append("null agent_level requires verdict incomplete")
    if verdict == "pass_advisory":
        if any_fail or record["policy_check"]["violations"] or score is None or score < PASS_THRESHOLD:
            violations.append(f"pass_advisory requires zero fails, zero policy violations and score >= {PASS_THRESHOLD}")
    if verdict == "needs_fixes" and score is not None and score >= PASS_THRESHOLD and not record["policy_check"]["violations"] and not any_fail:
        listed = any(r["evidence_gaps"] or r["fixes"] for r in record["rubric"])
        if not listed:
            violations.append("needs_fixes with score >= 85 and no violations requires at least one evidence_gap or fix listed")
    return violations
