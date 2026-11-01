#!/usr/bin/env python3
"""Deterministic pre-checks for the map-requirements skill (spec 5.2 steps 1, 2-prep, 4-conflict, 6-blockers).

Input: a validated Intake Record JSON (inside the repo). Output: Mapping Record skeleton with requirement
candidates per part, existing tasks carried from the intake, decision conflicts, default blockers.
match_type stays 'unknown' (LLM/human decide) unless a decision conflict is detected -> 'conflict'.
Exit 0 success; 1 if the produced record fails policy; 2 if a path is refused.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "core"))
from kitlib import intake_policy, mapping_policy, requirement_matcher, safe_paths  # noqa: E402

DEFAULT_REQS = REPO / "evaluations/fixtures/synthetic-requirements-snapshot.json"
DEFAULT_TASKS = REPO / "evaluations/fixtures/synthetic-task-snapshot.json"
DEFAULT_SYNONYMS = REPO / "products/igoal/search-synonyms.json"
UNVERIFIED = ("check", "done")


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _existing_tasks(part, tasks_by_id):
    out = []
    for c in part["duplicate_candidates"]:
        t = tasks_by_id.get(c["task_id"], {})
        out.append({"task_id": c["task_id"], "title": c["title"], "status": t.get("status", c.get("status", "unknown")),
                    "section": c.get("section", "unknown"), "score": c["score"], "modified_at": c.get("modified_at", "unknown"),
                    "release_evidence": None})
    return out


def _map_part(part, reqs, decisions, tasks_by_id, synonyms, module):
    cands = requirement_matcher.find_requirement_candidates(part["text_redacted"], reqs, synonyms, module)
    unknown_refs = requirement_matcher.annotate_decision_status(cands, decisions)
    conflict = requirement_matcher.detect_conflict(cands, decisions)
    tasks = _existing_tasks(part, tasks_by_id)
    blockers = [f"decision {ref} referenced by a candidate is not in the decisions snapshot" for ref in unknown_refs]
    if conflict:
        blockers.append(f"decision conflict in domain '{conflict['domain']}' ({', '.join(conflict['decision_ids'])}); owner must choose")
    for t in tasks:
        if t["status"] in UNVERIFIED and not t["release_evidence"]:
            blockers.append(f"task {t['task_id']} is '{t['status']}' with no QA or release evidence read")
    for c in cands:
        if c["approval_status"] != "approved":
            blockers.append(f"requirement {c['requirement_id']} approval_status={c['approval_status']}: evidence_or_proposal_only")
    if not cands:
        blockers.append("no requirement candidate found in the scanned snapshot (quick search, not exhaustive)")
    if conflict:
        action = "ask_owner"
    elif any(t["status"] in UNVERIFIED for t in tasks):
        action = "request_qa_evidence"
    else:
        action = "unknown"
    if not blockers:
        blockers.append("match_type not yet decided by reviewer")
    return {
        "part_id": part["part_id"], "feedback_part_summary": part["text_redacted"][:200], "requirement_candidates": cands,
        "requirement_id": None, "match_type": "conflict" if conflict else "unknown", "match_basis": None,
        "existing_tasks": tasks, "missing_decision": conflict["summary"] if conflict else None, "conflict": conflict,
        "proposed_action": action, "blockers": blockers,
    }


def _mapping_id(intake_id):
    mapped = intake_id.replace("-INTAKE", "-MAPPING")
    return mapped if mapped != intake_id else f"{intake_id}-MAPPING"


def build_record(intake, reqs_snapshot, tasks_snapshot, synonyms, req_path, task_path, runtime):
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    reqs, decisions = reqs_snapshot["requirements"], reqs_snapshot.get("decisions", [])
    tasks_by_id = {str(t["task_id"]): t for t in tasks_snapshot["tasks"]}
    module = intake["feedback"].get("module")
    mappings = [_map_part(p, reqs, decisions, tasks_by_id, synonyms, module) for p in intake["parts"]]
    conflicts = [m for m in mappings if m["conflict"]]
    open_questions = [f"Part {m['part_id']}: which decision applies in domain '{m['conflict']['domain']}'?" for m in conflicts]
    open_questions += [f"Part {m['part_id']}: QA/build/release evidence for {t['task_id']}?" for m in mappings
                       for t in m["existing_tasks"] if t["status"] in UNVERIFIED]
    sources = list(intake["sources"]) + [
        {"source_id": reqs_snapshot.get("source_id", "unknown"), "location": safe_paths.repo_relative(req_path), "retrieved_at": reqs_snapshot.get("snapshot_at", "unknown")},
        {"source_id": tasks_snapshot.get("source_id", "unknown"), "location": safe_paths.repo_relative(task_path), "retrieved_at": tasks_snapshot.get("snapshot_at", "unknown")},
    ]
    return {
        "schema_version": "bm-agent-contract/0.2", "run_id": intake["run_id"],
        "artifact_id": _mapping_id(intake["artifact_id"]), "artifact_version": "0.1-draft",
        "output_type": "mapping_record", "status": "draft", "requires_human_review": True, "human_owner": "Tom", "reviewer": "Tom",
        "kit_version": "0.2.0-draft", "runtime": runtime, "created_at": now, "intake_artifact_id": intake["artifact_id"],
        "sources": sources,
        "search_scope": {"method": "keyword_overlap_with_synonyms" if synonyms else "keyword_overlap",
                         "requirements_snapshot": safe_paths.repo_relative(req_path), "tasks_snapshot": safe_paths.repo_relative(task_path),
                         "requirements_scanned": len(reqs), "tasks_scanned": len(tasks_by_id), "exhaustive": False,
                         "synonyms_used": bool(synonyms), "module_filter": module if module != "unknown" else None,
                         "note": "Quick local search over provided snapshots; candidate details must be read before concluding."},
        "mappings": mappings,
        "facts": [{"label": "fact", "claim": f"{len(reqs)} requirements and {len(tasks_by_id)} tasks scanned for intake {intake['artifact_id']}.",
                   "source_ref": {"source_id": reqs_snapshot.get("source_id", "unknown"), "location": safe_paths.repo_relative(req_path)}}],
        "inferences": [], "proposals": [], "open_questions": open_questions,
        "gate_status": {"DEV.G1": "not_started"}, "external_action": {"requested": False, "executed": False},
        "approval": {"approval_type": "artifact_only", "gate": "DEV.G1", "approved_by": None, "approved_at": None,
                     "decision": "pending", "permits_external_write": False, "permits_send": False},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("intake_record")
    ap.add_argument("--out")
    ap.add_argument("--requirements", default=str(DEFAULT_REQS))
    ap.add_argument("--tasks", default=str(DEFAULT_TASKS))
    ap.add_argument("--synonyms", default=str(DEFAULT_SYNONYMS))
    ap.add_argument("--runtime", default="unknown")
    args = ap.parse_args(argv)
    try:
        in_path = safe_paths.require_inside_repo(args.intake_record)
        req_path, task_path = safe_paths.require_inside_repo(args.requirements), safe_paths.require_inside_repo(args.tasks)
        syn_path = safe_paths.require_inside_repo(args.synonyms)
        out_path = safe_paths.require_inside_runs(args.out) if args.out else None
    except PermissionError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    intake = _load(in_path)
    bad = intake_policy.check(intake)
    if bad:
        print("REFUSED: input intake record fails policy: " + "; ".join(bad[:3]), file=sys.stderr)
        return 2
    synonyms = _load(syn_path)["groups"] if syn_path.exists() else None
    record = build_record(intake, _load(req_path), _load(task_path), synonyms, req_path, task_path, args.runtime)
    violations = mapping_policy.check(record)
    text = json.dumps(record, ensure_ascii=False, indent=2)
    if out_path and not violations:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n", encoding="utf-8")
        print(f"wrote {safe_paths.repo_relative(out_path)}")
    elif out_path:
        print("NOT WRITTEN: record failed policy (see SUMMARY)", file=sys.stderr)
    else:
        print(text)
    summary = {"run_id": record["run_id"], "mappings": {m["part_id"]: {"match_type": m["match_type"], "action": m["proposed_action"],
               "requirements": [c["requirement_id"] for c in m["requirement_candidates"]], "tasks": [t["task_id"] for t in m["existing_tasks"]]}
               for m in record["mappings"]}, "policy_violations": violations}
    print("SUMMARY " + json.dumps(summary, ensure_ascii=False), file=sys.stderr)
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
