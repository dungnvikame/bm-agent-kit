#!/usr/bin/env python3
"""Deterministic pre-checks for the breakdown-feature skill (spec 5.3).

Input: a validated Mapping Record. Optional: a HUMAN DEV.G2 approval record (--approval); without it the
direction is 'hypothetical' and nothing is an official handoff. Output: Breakdown Record skeleton with a
draft problem statement, role handoffs derived from mapping blockers, task proposals (never 'create'),
and a duplicate check of proposal titles against the task snapshot. Stories are left for the reviewer/LLM.
Exit 0 ok; 1 produced record fails policy; 2 refused input.
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "core"))
from kitlib import breakdown_policy, draft_record, duplicate_finder, mapping_policy, safe_paths  # noqa: E402

DEFAULT_TASKS = REPO / "evaluations/fixtures/synthetic-task-snapshot.json"
DEFAULT_SYNONYMS = REPO / "products/igoal/search-synonyms.json"
STRONG_DUPLICATE = 0.3  # jaccard; below this a candidate is surfaced as a question, not a block


def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _proposal(m, approved, idx):
    pid, mt, tasks = m["part_id"], m["match_type"], m["existing_tasks"]
    label = "official" if approved else "hypothetical"
    base = {"proposal_id": f"TP-{idx:02d}", "part_id": pid, "label": label, "depends_on_gate": "DEV.G3",
            "title": f"[{mt}] {m['feedback_part_summary'][:80]}", "target_task_id": None,
            "payload_preview": {"name": m["feedback_part_summary"][:120], "notes": f"Source part {pid}; mapping {mt}; draft only."}}
    if mt == "conflict":
        return {**base, "operation": "blocked", "block_reasons": [f"decision conflict: {m['conflict']['summary']}"]}
    if mt == "unknown":
        return {**base, "operation": "blocked", "block_reasons": ["mapping not decided (match_type unknown)"] + m["blockers"]}
    if tasks and mt in ("exact", "partial"):  # a gap never updates an unrelated task that was only a weak duplicate candidate
        op = "review_existing" if mt == "exact" else "update_proposal"
        return {**base, "operation": op, "target_task_id": tasks[0]["task_id"], "title": tasks[0]["title"]}
    return {**base, "operation": "hold_for_shape"}  # reviewer promotes to new_task_proposal after writing stories/AC


def _handoffs(mapping):
    qa = [f"QA/release evidence for task {t['task_id']}" for m in mapping["mappings"] for t in m["existing_tasks"] if t["status"] in ("check", "done")]
    has_tasks = any(m["existing_tasks"] for m in mapping["mappings"])
    owner = "keep_existing" if has_tasks else None
    return [
        {"role": "design", "asks": ["Confirm affected screens, states and flow before any solution detail"], "owner": owner or "role:design"},
        {"role": "dev", "asks": ["Feasibility and technical approach; estimate only after direction approval"], "owner": owner or "role:dev"},
        {"role": "qa", "asks": qa or ["Test strategy and pass/fail criteria per AC"], "owner": owner or "role:qa"},
    ]


def build(mapping, approval, tasks_snapshot, synonyms, tasks_path, runtime):
    approved = approval is not None
    art_id = draft_record.derive_id(mapping["artifact_id"], "-MAPPING", "-BREAKDOWN")
    rec = draft_record.base("breakdown_record", mapping["run_id"], art_id, runtime, list(mapping["sources"]), gate="DEV.G2")
    summaries = "; ".join(m["feedback_part_summary"][:100] for m in mapping["mappings"])
    rec.update({
        "mapping_artifact_id": mapping["artifact_id"], "intake_artifact_id": mapping["intake_artifact_id"],
        "direction": {"status": "approved" if approved else "hypothetical",
                      "approval_ref": draft_record.approval_ref(approval) if approved else None,
                      "note": None if approved else "No DEV.G2 approval record supplied: all stories/proposals are hypothetical."},
        "official_handoff": False,
        "problem": {"statement": f"Draft from intake parts (reviewer to rewrite): {summaries}", "users": [],
                    "evidence_refs": [{"source_id": s["source_id"], "location": s["location"]} for s in mapping["sources"]],
                    "outcome": None, "scope_in": [], "scope_out": []},
        "stories": [], "handoffs": _handoffs(mapping),
        "task_proposals": [_proposal(m, approved, i + 1) for i, m in enumerate(mapping["mappings"])],
    })
    tasks = tasks_snapshot["tasks"]
    weak_notes = []
    for p in rec["task_proposals"]:
        if p["operation"] == "hold_for_shape":
            cands, _ = duplicate_finder.find_candidates(p["title"], tasks, synonyms)
            strong = [c for c in cands if c["score"] >= STRONG_DUPLICATE]
            weak = [c for c in cands if c["score"] < STRONG_DUPLICATE]
            if strong:
                p.update(operation="blocked", block_reasons=[f"possible duplicate: {', '.join(c['task_id'] for c in strong)}"])
            elif weak:
                weak_notes.append(f"{p['proposal_id']}: weak overlap with {', '.join(c['task_id'] for c in weak)} (score < {STRONG_DUPLICATE}); confirm not a duplicate")
    rec["duplicate_check"] = {"method": "keyword_overlap_with_synonyms" if synonyms else "keyword_overlap",
                              "tasks_scanned": len(tasks), "exhaustive": False, "snapshot": safe_paths.repo_relative(tasks_path)}
    rec["facts"].append({"label": "fact", "claim": f"Breakdown skeleton built from mapping {mapping['artifact_id']} with {len(mapping['mappings'])} part(s).",
                         "source_ref": {"source_id": mapping["sources"][0]["source_id"], "location": mapping["sources"][0]["location"]}})
    rec["open_questions"] = weak_notes + ["Problem statement, users, outcome and scope to be written by the reviewer.",
                             "Stories/AC to be written after direction decision (Given/When/Then, incl. empty/error/permission)."]
    if not approved:
        rec["open_questions"].append("Which direction does Tom/PM approve at DEV.G2? Provide the approval record to lift 'hypothetical'.")
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mapping_record"); ap.add_argument("--approval", help="human DEV.G2 approval record (JSON)")
    ap.add_argument("--out"); ap.add_argument("--tasks", default=str(DEFAULT_TASKS)); ap.add_argument("--synonyms", default=str(DEFAULT_SYNONYMS))
    ap.add_argument("--runtime", default="unknown")
    args = ap.parse_args(argv)
    try:
        in_path = safe_paths.require_inside_repo(args.mapping_record)
        tasks_path = safe_paths.require_inside_repo(args.tasks); syn_path = safe_paths.require_inside_repo(args.synonyms)
        appr_path = safe_paths.require_inside_repo(args.approval) if args.approval else None
        out_path = safe_paths.require_inside_runs(args.out) if args.out else None
    except PermissionError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr); return 2
    mapping = _load(in_path)
    bad = mapping_policy.check(mapping)
    if bad:
        print("REFUSED: input mapping record fails policy: " + "; ".join(bad[:3]), file=sys.stderr); return 2
    approval, problems = (None, [])
    if appr_path:
        approval, problems = draft_record.load_approval(appr_path, expect_gate="DEV.G2", expect_type="artifact_only",
                                                        expect_artifact_id=mapping["artifact_id"], expect_artifact_version=mapping["artifact_version"])
    synonyms = _load(syn_path)["groups"] if syn_path.exists() else None
    rec = build(mapping, approval, _load(tasks_path), synonyms, tasks_path, args.runtime)
    if problems:
        rec["open_questions"].append("Supplied approval record rejected: " + "; ".join(problems))
    violations = breakdown_policy.check(rec)
    text = json.dumps(rec, ensure_ascii=False, indent=2)
    if out_path and not violations:
        out_path.parent.mkdir(parents=True, exist_ok=True); out_path.write_text(text + "\n", encoding="utf-8")
        print(f"wrote {safe_paths.repo_relative(out_path)}")
    elif out_path:
        print("NOT WRITTEN: record failed policy (see SUMMARY)", file=sys.stderr)
    else:
        print(text)
    summary = {"run_id": rec["run_id"], "direction": rec["direction"]["status"], "approval_problems": problems,
               "proposals": {p["proposal_id"]: p["operation"] for p in rec["task_proposals"]}, "policy_violations": violations}
    print("SUMMARY " + json.dumps(summary, ensure_ascii=False), file=sys.stderr)
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
