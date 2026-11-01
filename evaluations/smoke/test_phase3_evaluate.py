"""Phase 3 tests: evaluate-pm-output (advisory self-check, immediate-fail detection, verdict rules)."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase3_helpers import FIXTURES, KIT_CLI, REPO, Workspace, dump, load, run  # noqa: E402

sys.path.insert(0, str(REPO / "core"))
from kitlib import draft_record, evaluation_policy, policy_registry  # noqa: E402


class EvaluateTests(unittest.TestCase):
    def setUp(self):
        self.exp = load(FIXTURES / "f11-evaluate-fail-stop/expected.json")

    def test_clean_record_is_incomplete_with_no_fails(self):
        with Workspace() as ws:
            ev = ws.evaluate("mapping.json")
            self.assertEqual(evaluation_policy.check(ev), [])
            self.assertEqual(ev["verdict"], self.exp["clean_verdict"]); self.assertIsNone(ev["advisory_score"])
            results = {c["check_id"]: c["result"] for c in ev["immediate_fail_checks"]}
            self.assertNotIn("fail", results.values()); self.assertEqual(results["IF3_fabricated_source_or_approval"], "needs_human")
            self.assertFalse(ev["is_human_evaluation"]); self.assertTrue(all(r["human_level"] is None for r in ev["rubric"]))
            self.assertEqual(ev["policy_check"]["violations"], [])
            dump(ws.path("eval.json"), ev)
            r = run(KIT_CLI, "validate", ws.path("eval.json")); self.assertEqual(r.returncode, 0, r.stderr); self.assertIn("evaluation_record ok", r.stdout)

    def test_fabricated_approval_is_an_immediate_fail(self):
        with Workspace() as ws:
            m = load(ws.mapping); m["approval"]["approved_by"] = "PM Agent"; m["gate_status"]["DEV.G1"] = "approved"
            dump(ws.path("tampered.json"), m)
            ev = ws.evaluate("tampered.json")
            self.assertEqual(ev["verdict"], self.exp["tampered_verdict"])
            results = {c["check_id"]: c["result"] for c in ev["immediate_fail_checks"]}
            self.assertEqual(results[self.exp["tampered_fail_check"]], "fail")
            self.assertTrue(ev["policy_check"]["violations"])  # the evaluated record also fails its own policy
            self.assertEqual(evaluation_policy.check(ev), [])

    def test_reviewer_filled_levels_and_verdict_rules(self):
        with Workspace() as ws:
            ev = ws.evaluate("mapping.json")
            filled = copy.deepcopy(ev)
            for r in filled["rubric"]:
                r["agent_level"] = 4
            filled["advisory_score"] = self.exp["pass_score"]; filled["verdict"] = "pass_advisory"
            self.assertEqual(evaluation_policy.check(filled), [])
            human = copy.deepcopy(filled); human["rubric"][0]["human_level"] = 3
            self.assertTrue(any("human_level" in v for v in evaluation_policy.check(human)))
            wrong_score = copy.deepcopy(filled); wrong_score["advisory_score"] = 90.0
            self.assertTrue(any("advisory_score must be" in v for v in evaluation_policy.check(wrong_score)))
            with_fail = copy.deepcopy(filled); with_fail["immediate_fail_checks"][0]["result"] = "fail"
            self.assertTrue(any("fail_stop" in v for v in evaluation_policy.check(with_fail)))
            low = copy.deepcopy(filled); low["rubric"][0]["agent_level"] = 1; low["advisory_score"] = evaluation_policy.advisory_score(low["rubric"])
            self.assertTrue(any("pass_advisory requires" in v for v in evaluation_policy.check(low)))
            low["verdict"] = "needs_fixes"; self.assertEqual(evaluation_policy.check(low), [])

    def test_registry_and_refusals(self):
        self.assertEqual(set(policy_registry.POLICIES), {"intake_record", "mapping_record", "breakdown_record", "payload_preview_record", "evaluation_record"})
        self.assertTrue(policy_registry.check_any({"output_type": "nope"})[1])
        with Workspace() as ws:
            ev = ws.evaluate("mapping.json"); dump(ws.path("eval.json"), ev)
            r = run(REPO / "scripts/evaluate-preprocess.py", ws.path("eval.json"))
            self.assertEqual(r.returncode, 2); self.assertIn("REFUSED", r.stderr)  # cannot evaluate an evaluation
        self.assertTrue(draft_record.payload_hash({"a": 1}).startswith("sha256:"))
        self.assertEqual(draft_record.payload_hash({"a": 1, "b": 2}), draft_record.payload_hash({"b": 2, "a": 1}))


class EvaluateRobustnessTests(unittest.TestCase):
    def test_schema_invalid_input_still_yields_an_evaluation(self):
        with Workspace() as ws:
            m = load(ws.mapping); m["approval"] = "yes"; m["facts"].append({"label": "fact", "claim": "x", "source_ref": "S1"})
            dump(ws.path("broken.json"), m)
            r = run(REPO / "scripts/evaluate-preprocess.py", ws.path("broken.json"))
            self.assertEqual(r.returncode, 0, r.stderr)
            ev = json.loads(r.stdout)
            self.assertEqual(ev["verdict"], "fail_stop"); self.assertTrue(any(v.startswith("schema:") for v in ev["policy_check"]["violations"]))
            self.assertEqual(evaluation_policy.check(ev), [])


if __name__ == "__main__":
    unittest.main()
