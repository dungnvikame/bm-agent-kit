#!/usr/bin/env python3
"""Proposal-only pre-checks for the create-asana-tasks skill (spec 5.4). NOTHING is written to Asana.

Input: a validated Breakdown Record, target project (and optional parent), optional HUMAN approval records:
--g3 (DEV.G3 artifact approval for this breakdown) and --action (action approval: operation + destination +
payload_hash, same gate/artifact). Output: Payload Preview Record: one item per task proposal with exact payload,
canonical hash, diff, side effects, final duplicate check and the operation the human may perform manually.
Every external write (create/update/link) is allowed only when all preconditions hold; otherwise 'blocked'.
Exit 0 ok; 1 record fails policy; 2 refused input.
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "core"))
from kitlib import breakdown_policy, draft_record, duplicate_finder, payload_policy, safe_paths  # noqa: E402

DEFAULT_TASKS = REPO / "evaluations/fixtures/synthetic-task-snapshot.json"
DEFAULT_SYNONYMS = REPO / "products/igoal/search-synonyms.json"
STRONG_DUPLICATE = 0.3  # same threshold as breakdown-preprocess
OP_MAP = {"review_existing": "link", "update_proposal": "update", "new_task_proposal": "create", "hold_for_shape": "blocked", "blocked": "blocked"}
WRITE_OPS = {"create", "update", "link"}


def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _precondition(path, **kw):
    if not path:
        return {"status": "missing", "approval_ref": None, "reason": "no approval record supplied"}, None
    rec, problems = draft_record.load_approval(path, **kw)
    ref = draft_record.repo_relative(path)
    if rec is None:
        return {"status": "invalid", "approval_ref": ref, "reason": "; ".join(problems)}, None
    return {"status": "approved", "approval_ref": ref}, rec


def _destination_ok(action, payload, target_task_id):
    dest = action.get("destination", {})
    return (dest.get("project_id") == payload["project_id"] and dest.get("parent_task_id") == payload["parent_task_id"]
            and (dest.get("task_id") or None) == (target_task_id or None))


def _item(idx, p, bd, target, g3_ok, action, tasks, tasks_by_id, synonyms):
    parent = p["payload_preview"].get("parent_task_id") or target["parent_task_id"]
    payload = {"name": p["payload_preview"]["name"], "notes": p["payload_preview"]["notes"] + f"\nProvenance: {bd['artifact_id']} / {p['proposal_id']}",
               "project_id": target["project_id"], "parent_task_id": parent}
    h = draft_record.payload_hash(payload)
    op = OP_MAP[p["operation"]]
    reasons = list(p.get("block_reasons", []))
    if p["label"] == "hypothetical":
        reasons.append("direction not approved (hypothetical proposal)")
    cands = []
    if op == "create":
        cands, _ = duplicate_finder.find_candidates(payload["name"], tasks, synonyms)
        cands = [{"task_id": c["task_id"], "title": c["title"], "score": c["score"], "status": c["status"]} for c in cands if c["score"] >= STRONG_DUPLICATE]
    if op in WRITE_OPS:
        if not g3_ok:
            reasons.append("DEV.G3 not approved/recorded")
        if action is None:
            reasons.append("no valid action approval")
        elif action.get("payload_hash") != h:
            reasons.append("action approval payload_hash does not match this payload (content changed or other item)")
        elif action.get("operation") != op:
            reasons.append(f"action approval is for {action.get('operation')}, not {op}")
        elif not _destination_ok(action, payload, p["target_task_id"]):
            reasons.append("action approval destination (project/parent/task) does not match this item")
        if not target["verified"]:
            reasons.append("target project/parent not verified against task source")
        if parent and parent not in tasks_by_id:
            reasons.append(f"parent task {parent} not found in task source")
        if op in ("update", "link") and p["target_task_id"] not in tasks_by_id:
            reasons.append(f"target task {p['target_task_id']} not found in task source")
        if op == "create" and cands:
            reasons.append("duplicate candidates present")
    if reasons:
        op = "blocked"
    existing = tasks_by_id.get(p["target_task_id"] or "")
    diff = {"update": [f"notes: + {payload['notes'][:80]}"], "create": ["new task (all fields)"], "link": [f"link feedback/provenance to {p['target_task_id']}"]}.get(op, [])
    if existing and op == "update":
        diff.insert(0, f"name: '{existing.get('title', '')[:60]}' -> '{payload['name'][:60]}'")
    side = {"create": ["project followers notified", "parent gets a new subtask" if parent else "task appears in project default section"],
            "update": ["task followers notified of the change"], "link": ["task followers may be notified of the new reference"]}.get(op, [])
    return {"item_id": f"PI-{idx:02d}", "proposal_id": p["proposal_id"], "operation": op, "target_task_id": p["target_task_id"],
            "payload": payload, "payload_hash": h, "diff": diff, "side_effects": side, "duplicate_candidates": cands, "block_reasons": reasons}


def build(bd, project, parent, g3_path, act_path, tasks_snapshot, synonyms, tasks_path, runtime):
    tasks = tasks_snapshot["tasks"]; tasks_by_id = {str(t["task_id"]): t for t in tasks}
    verified = project == tasks_snapshot.get("project") and (parent is None or parent in tasks_by_id)
    target = {"project_id": project, "parent_task_id": parent, "verified": verified,
              "note": "verified against task snapshot" if verified else "project/parent not found in the task snapshot read this run"}
    g3, _ = _precondition(g3_path, expect_gate="DEV.G3", expect_type="artifact_only", expect_artifact_id=bd["artifact_id"], expect_artifact_version=bd["artifact_version"])
    act_pre, action = _precondition(act_path, expect_gate="DEV.G3", expect_type="action", expect_artifact_id=bd["artifact_id"])
    act = {"status": "present" if action else act_pre["status"], "approval_ref": act_pre["approval_ref"],
           "payload_hash_expected": action.get("payload_hash") if action else None, "operation": action.get("operation") if action else None}
    if "reason" in act_pre:
        act["reason"] = act_pre["reason"]
    art_id = draft_record.derive_id(bd["artifact_id"], "-BREAKDOWN", "-PAYLOAD")
    sources = list(bd["sources"]) + [{"source_id": tasks_snapshot.get("source_id", "unknown"), "location": safe_paths.repo_relative(tasks_path),
                                      "retrieved_at": tasks_snapshot.get("snapshot_at", "unknown")}]
    rec = draft_record.base("payload_preview_record", bd["run_id"], art_id, runtime, sources, gate="DEV.G3")
    items = [_item(i + 1, p, bd, target, g3["status"] == "approved", action, tasks, tasks_by_id, synonyms) for i, p in enumerate(bd["task_proposals"])]
    if action and act["payload_hash_expected"] not in {it["payload_hash"] for it in items}:
        act["status"] = "stale"; act["reason"] = "approved payload_hash matches no current item (content changed since approval)"
    rec.update({"breakdown_artifact_id": bd["artifact_id"], "target": target, "preconditions": {"dev_g3": g3, "action_approval": act},
                "write_adapter": "disabled", "handoff_mode": "manual_entry_by_human", "items": items})
    rec["facts"].append({"label": "fact", "claim": f"{len(items)} payload preview(s) built; write adapter disabled; human enters any approved payload manually.",
                         "source_ref": {"source_id": sources[0]["source_id"], "location": sources[0]["location"]}})
    rec["open_questions"] = [f"item {it['item_id']}: {r}" for it in items for r in it["block_reasons"]][:10]
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("breakdown_record"); ap.add_argument("--project", required=True); ap.add_argument("--parent")
    ap.add_argument("--g3"); ap.add_argument("--action"); ap.add_argument("--out")
    ap.add_argument("--tasks", default=str(DEFAULT_TASKS)); ap.add_argument("--synonyms", default=str(DEFAULT_SYNONYMS)); ap.add_argument("--runtime", default="unknown")
    args = ap.parse_args(argv)
    try:
        in_path = safe_paths.require_inside_repo(args.breakdown_record)
        tasks_path = safe_paths.require_inside_repo(args.tasks); syn_path = safe_paths.require_inside_repo(args.synonyms)
        g3_path = safe_paths.require_inside_repo(args.g3) if args.g3 else None
        act_path = safe_paths.require_inside_repo(args.action) if args.action else None
        out_path = safe_paths.require_inside_runs(args.out) if args.out else None
    except PermissionError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr); return 2
    bd = _load(in_path)
    bad = breakdown_policy.check(bd)
    if bad:
        print("REFUSED: input breakdown record fails policy: " + "; ".join(bad[:3]), file=sys.stderr); return 2
    synonyms = _load(syn_path)["groups"] if syn_path.exists() else None
    rec = build(bd, args.project, args.parent, g3_path, act_path, _load(tasks_path), synonyms, tasks_path, args.runtime)
    violations = payload_policy.check(rec)
    text = json.dumps(rec, ensure_ascii=False, indent=2)
    if out_path and not violations:
        out_path.parent.mkdir(parents=True, exist_ok=True); out_path.write_text(text + "\n", encoding="utf-8"); print(f"wrote {safe_paths.repo_relative(out_path)}")
    elif out_path:
        print("NOT WRITTEN: record failed policy (see SUMMARY)", file=sys.stderr)
    else:
        print(text)
    summary = {"run_id": rec["run_id"], "preconditions": rec["preconditions"], "items": {it["item_id"]: it["operation"] for it in rec["items"]}, "policy_violations": violations}
    print("SUMMARY " + json.dumps(summary, ensure_ascii=False), file=sys.stderr)
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
