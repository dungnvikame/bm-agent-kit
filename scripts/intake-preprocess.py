#!/usr/bin/env python3
"""Deterministic pre-checks for the intake-feedback skill (steps 1 and 5 of spec 5.1 + safety filters).

Input JSON (fixture/input.json shape):
  {feedback_id, submitted_at, module, product, channel, reporter_role, source_priority_label?,
   source: {source_id, location, retrieved_at?, version_or_snapshot?},
   parts: [{part_id, raw_text}], run_id?, runtime?}
Output: Intake Record skeleton (schema-valid, policy-valid) with redacted text, injection warnings,
duplicate candidates and default open questions. The LLM fills meaning-level fields afterwards.
Exit 0 on success, 1 if the produced record fails schema/policy (should not happen).
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "core"))
from kitlib import duplicate_finder, injection_detector, intake_policy, safe_paths, sensitive_scanner  # noqa: E402

DEFAULT_SNAPSHOT = REPO / "evaluations/fixtures/synthetic-task-snapshot.json"
DEFAULT_SYNONYMS = REPO / "products/igoal/search-synonyms.json"
DEFAULT_QUESTIONS = [
    "Màn hình/luồng nào bị ảnh hưởng (viết hay đọc)?",
    "Build/phiên bản và ngày quan sát?",
    "Các bước tái hiện và môi trường/thiết bị?",
    "Bao nhiêu người dùng/vai trò bị ảnh hưởng?",
]


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _unknown(value):
    return value if value not in (None, "") else "unknown"


def _meta(value, categories):
    """Metadata fields are free text too: redact them and collect categories (review finding #6)."""
    redacted, findings, _ = sensitive_scanner.scan(_unknown(value))
    categories.update(f["category"] for f in findings)
    return redacted


def build_record(inp, snapshot_path, synonyms_path, runtime):
    tasks = _load(snapshot_path)["tasks"]
    synonyms = _load(synonyms_path)["groups"] if Path(synonyms_path).exists() else None
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    categories = set()
    fid = _meta(inp.get("feedback_id"), categories)
    product = _meta(inp.get("product"), categories)
    run_id = inp.get("run_id") or f"RUN-{now[:10].replace('-', '')}-{product}-{fid}"
    src = inp.get("source") or {}

    parts, warnings, scope = [], [], None
    for raw in inp.get("parts") or []:
        pid = str(raw.get("part_id", "A"))
        raw_text = raw.get("raw_text") or ""
        warnings += injection_detector.detect(raw_text, part_id=pid)  # on RAW text, before redaction
        redacted, findings, _ = sensitive_scanner.scan(raw_text)
        categories.update(f["category"] for f in findings)
        candidates, scope = duplicate_finder.find_candidates(redacted, tasks, synonyms)
        parts.append({
            "part_id": pid, "text_redacted": redacted, "need": None, "symptom": None,
            "proposed_solution_by_reporter": None, "expected": None, "actual": None,
            "affected_users": "unknown", "environment": "unknown", "reproducible": "unknown",
            "category_proposed": "unknown", "severity_proposed": "unknown", "severity_basis": None,
            "duplicate_candidates": candidates,
        })
    scope = scope or {"method": "none", "tasks_scanned": 0, "exhaustive": False, "synonyms_used": False}
    scope["snapshot"] = safe_paths.repo_relative(snapshot_path)

    open_questions = list(DEFAULT_QUESTIONS)
    if warnings:
        open_questions.append("Nguồn chứa câu lệnh/yêu cầu hành động (đã bỏ qua, xem untrusted_instructions). Tom xác nhận cách xử lý?")
    if categories:
        open_questions.append("Nguồn chứa nội dung nhạy cảm đã redact; cần người có quyền đọc bản gốc nếu liên quan.")

    feedback = {
        "feedback_id": fid, "submitted_at": _meta(inp.get("submitted_at"), categories), "module": _meta(inp.get("module"), categories),
        "product": product, "channel": _meta(inp.get("channel"), categories), "reporter_role": _meta(inp.get("reporter_role"), categories),
    }
    if inp.get("source_priority_label"):
        feedback["source_priority_label"] = _meta(inp["source_priority_label"], categories)
    src_id, src_loc = _meta(src.get("source_id"), categories), _meta(src.get("location"), categories)

    return {
        "schema_version": "bm-agent-contract/0.2",
        "run_id": run_id, "artifact_id": f"{product}-{fid}-INTAKE".upper(), "artifact_version": "0.1-draft",
        "output_type": "intake_record", "status": "draft", "requires_human_review": True,
        "human_owner": "Tom", "reviewer": "Tom", "kit_version": "0.2.0-draft", "runtime": runtime, "created_at": now,
        "sources": [{"source_id": src_id, "location": src_loc,
                     "retrieved_at": _meta(src.get("retrieved_at"), categories), "version_or_snapshot": _meta(src.get("version_or_snapshot"), categories)}],
        "feedback": feedback, "parts": parts,
        "sensitive_content": {"detected": bool(categories), "categories": sorted(categories),
                              "redacted_note": sensitive_scanner.REDACTED_NOTE if categories else None},
        "untrusted_instructions": {"detected": bool(warnings), "warnings": warnings},
        "facts": [{"label": "fact", "claim": f"Feedback {fid} received for module {feedback['module']} with {len(parts)} part(s) (as split in input).",
                   "source_ref": {"source_id": src_id, "location": src_loc}}],
        "inferences": [], "proposals": [], "open_questions": open_questions,
        "requirement_task_mapping": {"status": "pending_map_requirements", "duplicate_search": scope},
        "gate_status": {"DEV.G1": "not_started"},
        "external_action": {"requested": False, "executed": False},
        "approval": {"approval_type": "artifact_only", "gate": "DEV.G1", "approved_by": None, "approved_at": None,
                     "decision": "pending", "permits_external_write": False, "permits_send": False},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("--out", help="write record here (default: stdout)")
    ap.add_argument("--snapshot", default=str(DEFAULT_SNAPSHOT))
    ap.add_argument("--synonyms", default=str(DEFAULT_SYNONYMS))
    ap.add_argument("--runtime", default="unknown")
    args = ap.parse_args(argv)

    try:
        in_path = safe_paths.require_inside_repo(args.input)
        snapshot = safe_paths.require_inside_repo(args.snapshot)
        out_path = safe_paths.require_inside_runs(args.out) if args.out else None
    except PermissionError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    record = build_record(_load(in_path), snapshot, args.synonyms, args.runtime)
    violations = intake_policy.check(record)
    text = json.dumps(record, ensure_ascii=False, indent=2)
    if out_path and not violations:  # never persist a record that fails schema/policy
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n", encoding="utf-8")
        print(f"wrote {safe_paths.repo_relative(out_path)}")
    elif out_path:
        print("NOT WRITTEN: record failed policy (see SUMMARY)", file=sys.stderr)
    else:
        print(text)
    summary = {
        "run_id": record["run_id"], "parts": len(record["parts"]),
        "sensitive": record["sensitive_content"]["categories"],
        "untrusted_instructions": sorted({w["pattern_id"] for w in record["untrusted_instructions"]["warnings"]}),
        "duplicate_candidates": {p["part_id"]: [c["task_id"] for c in p["duplicate_candidates"]] for p in record["parts"]},
        "policy_violations": violations,
    }
    print("SUMMARY " + json.dumps(summary, ensure_ascii=False), file=sys.stderr)
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
