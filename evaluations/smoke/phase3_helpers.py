"""Shared helpers for phase 3 tests: run the real scripts end to end inside a temporary runs/ folder."""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "evaluations" / "fixtures"
APPROVALS = FIXTURES / "synthetic-approvals"
SCRIPTS = REPO / "scripts"
KIT_CLI = REPO / "core" / "scripts" / "kit-cli.py"

STORY_B = {"story_id": "US-02", "part_id": "B", "label": "official", "as_a": "report reader", "i_want": "to collapse an objective",
           "so_that": "I can scan a long report", "acceptance_criteria": [
               {"ac_id": "AC-10", "given": "a report with several O", "when": "I collapse one O", "then": "only its KR/content hide", "coverage": "normal"},
               {"ac_id": "AC-11", "given": "an O with no KR", "when": "I collapse it", "then": "an empty state is shown, nothing is lost", "coverage": "empty"}]}


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, cwd=REPO)


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def dump(p, obj):
    Path(p).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


class Workspace:
    """Temporary runs/<x>/ folder with a reviewer-filled mapping (A exact -> task in check, B gap) built from f02."""

    def __enter__(self):
        self.dir = Path(tempfile.mkdtemp(dir=REPO / "runs"))
        r = run(SCRIPTS / "intake-preprocess.py", FIXTURES / "f02-duplicate-open-task/input.json", "--out", self.dir / "intake.json")
        assert r.returncode == 0, r.stderr
        r = run(SCRIPTS / "map-requirements-preprocess.py", self.dir / "intake.json")
        assert r.returncode == 0, r.stderr
        mapping = json.loads(r.stdout)
        a, b = mapping["mappings"]
        a.update(requirement_id="SYN-TR-05", match_type="exact", match_basis="AC1 header O/E distinguishable; AC3 long titles", proposed_action="request_qa_evidence")
        b.update(match_type="gap", requirement_id=None, proposed_action="hold_for_shape")
        self.mapping = self.dir / "mapping.json"
        dump(self.mapping, mapping)
        return self

    def __exit__(self, *exc):
        shutil.rmtree(self.dir, ignore_errors=True)

    def path(self, name):
        return self.dir / name

    def breakdown(self, approval=None, out="breakdown.json", promote_gap=False):
        """Run the script; with promote_gap the reviewer adds a story for part B and promotes TP-02 to new_task_proposal."""
        args = [SCRIPTS / "breakdown-preprocess.py", self.mapping]
        if approval:
            args += ["--approval", approval]
        r = run(*args)
        assert r.returncode == 0, r.stderr
        rec = json.loads(r.stdout)
        if promote_gap:
            rec["stories"] = [dict(STORY_B)]
            rec["task_proposals"][1].update(operation="new_task_proposal", target_task_id=None)
        dump(self.dir / out, rec)
        return rec

    def payload(self, breakdown_file="breakdown.json", g3=None, action=None, project="SYN-PROJECT-IGOAL", parent=None):
        args = [SCRIPTS / "create-asana-tasks-preprocess.py", self.dir / breakdown_file, "--project", project]
        if parent:
            args += ["--parent", parent]
        if g3:
            args += ["--g3", g3]
        if action:
            args += ["--action", action]
        r = run(*args)
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)

    def evaluate(self, record_file):
        r = run(SCRIPTS / "evaluate-preprocess.py", self.dir / record_file)
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)

    def action_approval_for(self, item, operation="create", name="action.json", **overrides):
        """Write an action approval bound to one preview item (hash + destination), with optional field overrides."""
        rec = load(APPROVALS / "action-approval.template.json")
        rec.update(payload_hash=item["payload_hash"], operation=operation,
                   destination={"project_id": item["payload"]["project_id"], "parent_task_id": item["payload"]["parent_task_id"], "task_id": item["target_task_id"]})
        rec.update(overrides)
        p = self.dir / name
        dump(p, rec)
        return p
