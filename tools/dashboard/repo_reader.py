"""Read-only views over the real repo files. Reuses core/kitlib for compose + sync checks.

Never reads runs/ or *.local.json (see editable_paths.PRIVATE).
"""
import json
import sys
from pathlib import Path

from editable_paths import LAYER_FILES, classify, is_private, needs_sync, relative, repo
from md_tables import parse_tables, strip_code, strip_md

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "core"))
from kitlib import adapter_sync, config_layers  # noqa: E402

SKILLS_DIR = "roles/pm/skills"
POLICIES_DIR = "core/policies"
PLAN_FILE = "plans/261101-2157-pm-agent-foundation/plan.md"
REPORTS_DIR = "plans/reports"
FIXTURES_DIR = "evaluations/fixtures"


def read_text(rel):
    if is_private(rel):
        raise PermissionError(f"refusing to read private file {rel}")
    return (repo() / rel).read_text(encoding="utf-8")


def read_json(rel):
    return json.loads(read_text(rel))


def load_layers(override=None):
    """Load the three layer contracts; override = {rel_path: dict} replaces one from memory."""
    override = override or {}
    return [override.get(rel) if rel in override else read_json(rel) for rel in LAYER_FILES]


def layers_view():
    layers = []
    for rel in LAYER_FILES:
        kind, note = classify(rel)
        try:
            cfg, err = read_json(rel), ""
        except (ValueError, OSError) as exc:
            cfg, err = {}, str(exc)
        layers.append({"name": cfg.get("layer", "?"), "path": rel, "kind": kind, "note": note, "config": cfg, "error": err})
    effective, violations = config_layers.compose([l["config"] for l in layers])
    return {"layers": layers, "effective": effective, "violations": violations}


def skills_view():
    registry = {}
    for table in parse_tables(read_text("roles/pm/skills/README.md")):
        if "Skill" in table["headers"]:
            for row in table["rows"]:
                registry[strip_code(row["Skill"])] = {k: strip_md(v) for k, v in row.items()}
    sync_problems = adapter_sync.check(repo())
    manifest_sources = {e["source"] for e in adapter_sync.load_manifest(repo())["entries"]}
    skills_dir = repo() / SKILLS_DIR
    on_disk = {p.name for p in skills_dir.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()}
    rows = []
    for name in sorted(set(registry) | on_disk):
        rel = f"roles/pm/skills/{name}"
        problems = [p for p in sync_problems if f"/{name}" in p]
        rows.append({
            "name": name, "implemented": name in on_disk, "registry": registry.get(name),
            "path": rel if name in on_disk else None, "in_manifest": rel in manifest_sources,
            "copies": {t: (repo() / t / name).is_dir() for t in (".claude/skills", ".agents/skills")},
            "sync_ok": name in on_disk and rel in manifest_sources and not problems, "sync_problems": problems,
            "files": [relative(p) for p in sorted((skills_dir / name).rglob("*")) if p.is_file()] if name in on_disk else [],
        })
    return {"skills": rows, "sync_problems": sync_problems}


def policies_view():
    return [{"name": p.stem, "path": relative(p), "text": p.read_text(encoding="utf-8")}
            for p in sorted((repo() / POLICIES_DIR).glob("*.md"))]


def product_view():
    registry = read_json("products/igoal/source-registry.json")
    return {
        "context_index": {"path": "products/igoal/context-index.md", "text": read_text("products/igoal/context-index.md")},
        "contract": {"path": "products/igoal/igoal-product-contract.json", "config": read_json("products/igoal/igoal-product-contract.json")},
        "registry": {"path": "products/igoal/source-registry.json", "status": registry.get("status", ""),
                     "records": registry.get("records", [])},
        "note": "source-registry.local.json (real URLs) is private and never shown here.",
    }


def evaluations_view():
    fixtures = []
    for d in sorted((repo() / FIXTURES_DIR).iterdir()):
        if d.is_dir():
            inp = json.loads((d / "input.json").read_text(encoding="utf-8")) if (d / "input.json").is_file() else {}
            fixtures.append({"name": d.name, "path": relative(d), "scenario": inp.get("_scenario", ""),
                             "files": [p.name for p in sorted(d.iterdir()) if p.is_file()]})
        elif d.is_file():
            fixtures.append({"name": d.name, "path": relative(d), "scenario": "shared fixture", "files": [d.name]})
    return {"fixtures": fixtures, "command": "python3 -m unittest discover -s evaluations/smoke -v"}


def plans_view():
    plan = repo() / PLAN_FILE
    text = plan.read_text(encoding="utf-8") if plan.is_file() else ""
    phases = []
    for table in parse_tables(text):
        if "Phase" in table["headers"]:
            phases = [{k: strip_md(v) for k, v in r.items()} for r in table["rows"]]
    reports = []
    for p in sorted((repo() / REPORTS_DIR).glob("*.md")):
        first = next((l.lstrip("# ").strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip()), "")
        reports.append({"name": p.name, "path": relative(p), "title": first})
    return {"plan_path": PLAN_FILE if plan.is_file() else None, "phases": phases, "reports": reports}


def file_view(rel):
    kind, note = classify(rel)
    if kind == "denied":
        raise PermissionError(note)
    path = repo() / rel
    if not path.is_file():
        raise FileNotFoundError(rel)
    return {"path": rel, "kind": kind, "note": note, "sync": needs_sync(rel), "text": path.read_text(encoding="utf-8")}
