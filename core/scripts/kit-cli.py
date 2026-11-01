#!/usr/bin/env python3
"""BM Agent Kit CLI — stdlib only. Run from repo root.

  kit-cli.py config-check [--run run-contract.json]   compose Core->Role->Product(->Run), fail closed
  kit-cli.py validate <record.json>                   schema + policy check (intake_record | mapping_record)
  kit-cli.py scan <text-file>                         sensitive-zone scan; prints redacted text + findings
  kit-cli.py inject <text-file>                       untrusted-instruction detection
  kit-cli.py dupes <text-file> [--snapshot f] [--synonyms f]
  kit-cli.py sync --check | --write                   adapter copies hash-match canonical sources
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "core"))
from kitlib import adapter_sync, config_layers, duplicate_finder, injection_detector, intake_policy, mapping_policy, safe_paths, sensitive_scanner  # noqa: E402

LAYER_FILES = [
    "core/contracts/core-contract.json",
    "roles/pm/pm-role-contract.json",
    "products/igoal/igoal-product-contract.json",
]
DEFAULT_SNAPSHOT = "evaluations/fixtures/synthetic-task-snapshot.json"
DEFAULT_SYNONYMS = "products/igoal/search-synonyms.json"


def _load(path):
    return json.loads(safe_paths.require_inside_repo(path).read_text(encoding="utf-8"))


def _read_text(path):
    """Free-text inputs must live inside the repo (allowlisted scripts must not dump ~/.aws etc.)."""
    return safe_paths.require_inside_repo(path).read_text(encoding="utf-8")


def cmd_config_check(args):
    layers = [_load(REPO / f) for f in LAYER_FILES]
    if args.run:
        layers.append(_load(args.run))
    effective, violations = config_layers.compose(layers)
    if args.print_effective:
        print(json.dumps(effective, ensure_ascii=False, indent=2))
    if violations:
        print("CONFIG CHECK FAILED (fail closed):", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1
    print(f"config ok: layers={effective['layers_applied']} mode={effective['safety']['mode']} "
          f"writes={effective['tools']['writes']} sends={effective['tools']['sends']} "
          f"capabilities={effective['tools']['capabilities']}")
    return 0


POLICIES = {"intake_record": intake_policy, "mapping_record": mapping_policy}


def cmd_validate(args):
    record = _load(args.record)
    policy = POLICIES.get(record.get("output_type") if isinstance(record, dict) else None)
    if policy is None:
        print(f"INTAKE/MAPPING RECORD REJECTED: unknown output_type {record.get('output_type')!r} (known: {sorted(POLICIES)})", file=sys.stderr)
        return 1
    violations = policy.check(record)
    if violations:
        print(f"{record['output_type'].upper()} REJECTED:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1
    print(f"{record['output_type']} ok (schema + policy)")
    return 0


def cmd_scan(args):
    text = _read_text(args.file)
    redacted, findings, detected = sensitive_scanner.scan(text)
    print(json.dumps({"detected": detected, "findings": findings, "redacted_text": redacted}, ensure_ascii=False, indent=2))
    return 0


def cmd_inject(args):
    text = _read_text(args.file)
    warnings = injection_detector.detect(text, part_id=args.part_id)
    print(json.dumps({"detected": bool(warnings), "warnings": warnings}, ensure_ascii=False, indent=2))
    return 0


def cmd_dupes(args):
    text = _read_text(args.file)
    tasks = _load(args.snapshot)["tasks"]
    synonyms = _load(args.synonyms)["groups"] if safe_paths.require_inside_repo(args.synonyms).exists() else None
    candidates, scope = duplicate_finder.find_candidates(text, tasks, synonyms)
    scope["snapshot"] = str(args.snapshot)
    print(json.dumps({"candidates": candidates, "search_scope": scope}, ensure_ascii=False, indent=2))
    return 0


def cmd_sync(args):
    if args.write:
        for p in adapter_sync.write(REPO):
            print(f"wrote {p}")
    problems = adapter_sync.check(REPO)
    if problems:
        print("ADAPTER SYNC CHECK FAILED:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print("adapter copies hash-match canonical sources")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="kit-cli.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("config-check"); p.add_argument("--run"); p.add_argument("--print-effective", action="store_true"); p.set_defaults(fn=cmd_config_check)
    p = sub.add_parser("validate"); p.add_argument("record"); p.set_defaults(fn=cmd_validate)
    p = sub.add_parser("scan"); p.add_argument("file"); p.set_defaults(fn=cmd_scan)
    p = sub.add_parser("inject"); p.add_argument("file"); p.add_argument("--part-id", default="?"); p.set_defaults(fn=cmd_inject)
    p = sub.add_parser("dupes"); p.add_argument("file"); p.add_argument("--snapshot", default=str(REPO / DEFAULT_SNAPSHOT)); p.add_argument("--synonyms", default=str(REPO / DEFAULT_SYNONYMS)); p.set_defaults(fn=cmd_dupes)
    p = sub.add_parser("sync"); g = p.add_mutually_exclusive_group(required=True); g.add_argument("--check", action="store_true"); g.add_argument("--write", action="store_true"); p.set_defaults(fn=cmd_sync)
    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except PermissionError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
