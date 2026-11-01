"""Phase 2 tests: map-requirements preprocess + mapping policy (E01, E03, E05 and policy rejections)."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "core"))
from kitlib import adapter_sync, mapping_policy, requirement_matcher  # noqa: E402

FIXTURES = REPO / "evaluations" / "fixtures"
INTAKE = REPO / "scripts" / "intake-preprocess.py"
MAPPING = REPO / "scripts" / "map-requirements-preprocess.py"
KIT_CLI = REPO / "core" / "scripts" / "kit-cli.py"


def _run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, cwd=REPO)


def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _pipeline(fixture):
    """intake-input.json -> intake record -> mapping record (both via the real scripts)."""
    with tempfile.TemporaryDirectory(dir=REPO / "runs") as d:
        intake_out = Path(d) / "intake.json"
        r = _run(INTAKE, FIXTURES / fixture / "intake-input.json", "--out", intake_out)
        assert r.returncode == 0, r.stderr
        r = _run(MAPPING, intake_out)
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)


class MappingFixtureTests(unittest.TestCase):
    def _common(self, rec, exp):
        self.assertEqual(mapping_policy.check(rec), [])
        self.assertEqual(rec["external_action"], exp["external_action"])
        self.assertFalse(rec["search_scope"]["exhaustive"])
        self.assertIsNone(rec["approval"]["approved_by"])

    def test_f05_full_sources_exact_candidate(self):
        rec, exp = _pipeline("f05-full-sources-exact"), _load(FIXTURES / "f05-full-sources-exact/expected.json")
        self._common(rec, exp)
        m, e = rec["mappings"][0], exp["parts"]["A"]
        self.assertEqual(m["requirement_candidates"][0]["requirement_id"], e["top_requirement_id"])
        self.assertEqual(m["requirement_candidates"][0]["approval_status"], e["top_requirement_approval"])
        self.assertEqual(m["match_type"], e["match_type_default"])  # script never decides exact; reviewer does
        self.assertIsNone(m["conflict"])
        self.assertGreaterEqual(rec["search_scope"]["requirements_scanned"], exp["requirements_scanned_min"])
        # a reviewer-filled exact record passes policy
        filled = copy.deepcopy(rec); fm = filled["mappings"][0]
        fm.update(requirement_id="SYN-TR-05", match_type="exact", proposed_action="request_qa_evidence",
                  match_basis="AC1 header O/E distinguishable; AC3 long titles not confusing child items")
        self.assertEqual(mapping_policy.check(filled), [])

    def test_f06_task_in_check_requires_evidence(self):
        rec, exp = _pipeline("f06-task-in-check-feedback-repeats"), _load(FIXTURES / "f06-task-in-check-feedback-repeats/expected.json")
        self._common(rec, exp)
        m, e = rec["mappings"][0], exp["parts"]["A"]
        task = next(t for t in m["existing_tasks"] if t["task_id"] == e["existing_task_id"])
        self.assertEqual(task["status"], e["existing_task_status"]); self.assertIsNone(task["release_evidence"])
        self.assertEqual(m["proposed_action"], e["proposed_action_default"])
        self.assertTrue(any(e["blocker_contains"] in b for b in m["blockers"]))
        bad = copy.deepcopy(rec); bm = bad["mappings"][0]
        bm.update(requirement_id="SYN-TR-05", match_type="exact", match_basis="AC1", proposed_action="link_existing")
        self.assertTrue(any("request_qa_evidence" in v for v in mapping_policy.check(bad)))
        fake = copy.deepcopy(bad); fake["mappings"][0]["existing_tasks"][0]["release_evidence"] = "ok, fixed I think"
        self.assertTrue(any("citing a source_id" in v for v in mapping_policy.check(fake)))  # free text is not evidence
        ok = copy.deepcopy(bad)
        ok["sources"].append({"source_id": "SYN-QA-RUN-12", "location": "QA run 12 report row 3", "retrieved_at": "2026-10-30"})
        ok["mappings"][0]["existing_tasks"][0]["release_evidence"] = "SYN-QA-RUN-12: pass on build 2026-10-30"
        self.assertEqual(mapping_policy.check(ok), [])

    def test_f07_conflict_blocks_decision(self):
        rec, exp = _pipeline("f07-conflicting-decisions"), _load(FIXTURES / "f07-conflicting-decisions/expected.json")
        self._common(rec, exp)
        m, e = rec["mappings"][0], exp["parts"]["A"]
        self.assertEqual(m["match_type"], e["match_type"]); self.assertEqual(m["proposed_action"], e["proposed_action"])
        self.assertEqual(m["conflict"]["domain"], e["conflict_domain"])
        self.assertEqual(m["conflict"]["decision_ids"], e["conflict_decision_ids"])
        self.assertEqual(m["conflict"]["blocked_decisions"], e["blocked_decisions"])
        self.assertTrue(rec["open_questions"])
        bad = copy.deepcopy(rec); bad["mappings"][0]["proposed_action"] = "review_existing"
        self.assertTrue(any("ask_owner" in v for v in mapping_policy.check(bad)))
        relabel = copy.deepcopy(rec); relabel["mappings"][0].update(match_type="partial", requirement_id="SYN-TR-09")
        self.assertTrue(any("relabelled" in v for v in mapping_policy.check(relabel)))


class MappingPolicyUnitTests(unittest.TestCase):
    def setUp(self):
        self.rec = _pipeline("f05-full-sources-exact")

    def test_exact_requires_requirement_id_and_basis(self):
        bad = copy.deepcopy(self.rec); bad["mappings"][0].update(match_type="exact", proposed_action="review_existing")
        v = "\n".join(mapping_policy.check(bad))
        self.assertIn("requires requirement_id", v); self.assertIn("match_basis", v)

    def test_gap_requires_scan_and_no_requirement(self):
        bad = copy.deepcopy(self.rec); bad["mappings"][0].update(match_type="gap", requirement_id="SYN-TR-05", proposed_action="hold_for_shape")
        self.assertTrue(any("gap requires" in v for v in mapping_policy.check(bad)))

    def test_unknown_needs_blocker_and_non_committal_action(self):
        bad = copy.deepcopy(self.rec); bad["mappings"][0].update(blockers=[], proposed_action="link_existing")
        self.assertTrue(any("unknown requires" in v for v in mapping_policy.check(bad)))

    def test_no_create_action_exists_in_schema(self):
        bad = copy.deepcopy(self.rec); bad["mappings"][0]["proposed_action"] = "create_task"
        self.assertTrue(any("schema" in v and "proposed_action" in v for v in mapping_policy.check(bad)))

    def test_requirement_id_must_be_a_listed_candidate(self):
        bad = copy.deepcopy(self.rec); bad["mappings"][0].update(match_type="partial", requirement_id="SYN-TR-99", proposed_action="review_existing")
        self.assertTrue(any("not among requirement_candidates" in v for v in mapping_policy.check(bad)))

    def test_action_table_and_approval_gate(self):
        base = copy.deepcopy(self.rec); base["mappings"][0]["existing_tasks"] = []
        gap_link = copy.deepcopy(base); gap_link["mappings"][0].update(match_type="gap", requirement_id=None, proposed_action="link_existing")
        self.assertTrue(any("not allowed for match_type gap" in v for v in mapping_policy.check(gap_link)))
        exact_scope = copy.deepcopy(base); exact_scope["mappings"][0].update(match_type="exact", requirement_id="SYN-TR-05", match_basis="AC1", proposed_action="propose_new_scope")
        self.assertTrue(any("not allowed for match_type exact" in v for v in mapping_policy.check(exact_scope)))
        unapproved = copy.deepcopy(base); unapproved["mappings"][0]["requirement_candidates"][0]["approval_status"] = "unknown"
        unapproved["mappings"][0].update(match_type="exact", requirement_id="SYN-TR-05", match_basis="AC1", proposed_action="link_existing")
        self.assertTrue(any("requires the matched requirement to be approved" in v for v in mapping_policy.check(unapproved)))

    def test_live_conflict_cannot_be_dropped(self):
        rec = _pipeline("f07-conflicting-decisions"); bad = copy.deepcopy(rec)
        bad["mappings"][0].update(conflict=None, match_type="unknown", proposed_action="ask_owner")
        self.assertTrue(any("must be conflict" in v for v in mapping_policy.check(bad)))

    def test_kit_cli_validate_dispatches_on_output_type(self):
        with tempfile.TemporaryDirectory(dir=REPO / "runs") as d:
            p = Path(d) / "m.json"; p.write_text(json.dumps(self.rec))
            r = _run(KIT_CLI, "validate", p); self.assertEqual(r.returncode, 0, r.stderr); self.assertIn("mapping_record ok", r.stdout)
            bad = copy.deepcopy(self.rec); bad["output_type"] = "something_else"; p.write_text(json.dumps(bad))
            self.assertEqual(_run(KIT_CLI, "validate", p).returncode, 1)


class MatcherAndSyncTests(unittest.TestCase):
    def test_supersedes_chain_is_not_a_conflict(self):
        decisions = [{"decision_id": "D1", "domain": "x", "supersedes": None}, {"decision_id": "D2", "domain": "x", "supersedes": "D1"},
                     {"decision_id": "D3", "domain": "x", "supersedes": "D2"}]
        cands = [{"decision_ref": "D1", "domain": "x"}, {"decision_ref": "D3", "domain": "x"}]
        self.assertIsNone(requirement_matcher.detect_conflict(cands, decisions))  # transitive chain D3>D2>D1
        self.assertEqual([c["decision_status"] for c in cands], ["superseded", "live"])
        decisions.append({"decision_id": "D4", "domain": "x", "supersedes": None, "status": "rejected"})
        cands = [{"decision_ref": "D3", "domain": "x"}, {"decision_ref": "D4", "domain": "x"}, {"decision_ref": "D9", "domain": "x"}]
        unknown = requirement_matcher.annotate_decision_status(cands, decisions)
        self.assertEqual(unknown, ["D9"]); self.assertEqual(cands[1]["decision_status"], "inactive")
        self.assertIsNone(requirement_matcher.detect_conflict(cands, decisions))  # rejected + unknown ref are not live
        cands = [{"decision_ref": "D3", "domain": "x"}, {"decision_ref": "D5", "domain": "x"}, {"decision_ref": "D6", "domain": "x"}]
        decisions += [{"decision_id": "D5", "domain": "x", "supersedes": None}, {"decision_id": "D6", "domain": "x", "supersedes": None}]
        self.assertEqual(requirement_matcher.detect_conflict(cands, decisions)["decision_ids"], ["D3", "D5", "D6"])

    def test_module_filter_excludes_other_modules(self):
        reqs = _load(FIXTURES / "synthetic-requirements-snapshot.json")["requirements"]
        cands = requirement_matcher.find_requirement_candidates("nhắc lịch check-in định kỳ cho owner KR", reqs, module="bao-cao")
        self.assertNotIn("SYN-TR-14", [c["requirement_id"] for c in cands])
        cands = requirement_matcher.find_requirement_candidates("nhắc lịch check-in định kỳ cho owner KR", reqs, module="check-in")
        self.assertEqual(cands[0]["requirement_id"], "SYN-TR-14")

    def test_mapping_preprocess_refuses_paths_outside_repo(self):
        rec_in = FIXTURES / "f05-full-sources-exact/intake-input.json"
        with tempfile.TemporaryDirectory(dir=REPO / "runs") as d:
            intake_out = Path(d) / "intake.json"; _run(INTAKE, rec_in, "--out", intake_out)
            r = _run(MAPPING, intake_out, "--synonyms", "/etc/hosts")
            self.assertEqual(r.returncode, 2); self.assertIn("REFUSED", r.stderr)

    def test_mapping_preprocess_refuses_invalid_intake(self):
        with tempfile.TemporaryDirectory(dir=REPO / "runs") as d:
            p = Path(d) / "bad.json"; p.write_text(json.dumps({"output_type": "intake_record"}))
            r = _run(MAPPING, p); self.assertEqual(r.returncode, 2); self.assertIn("REFUSED", r.stderr)

    def test_map_requirements_skill_synced(self):
        self.assertEqual(adapter_sync.check(REPO), [])
        self.assertTrue((REPO / ".claude/skills/map-requirements/SKILL.md").exists())
        self.assertTrue((REPO / ".agents/skills/map-requirements/SKILL.md").exists())


if __name__ == "__main__":
    unittest.main()
