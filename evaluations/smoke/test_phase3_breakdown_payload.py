"""Phase 3 tests: breakdown-feature (E04 direction labels) and create-asana-tasks proposal-only (E09/E10 + review findings)."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase3_helpers import APPROVALS, FIXTURES, KIT_CLI, REPO, STORY_B, Workspace, dump, load, run  # noqa: E402

sys.path.insert(0, str(REPO / "core"))
from kitlib import adapter_sync, breakdown_policy, draft_record, payload_policy  # noqa: E402

G2, G3, FAKE = APPROVALS / "dev-g2-approved.json", APPROVALS / "dev-g3-approved.json", APPROVALS / "fake-agent-approval.json"
STORY_A = {"story_id": "US-01", "part_id": "A", "label": "official", "as_a": "report reader", "i_want": "to tell O/E from KR/KS",
           "so_that": "I scan the structure", "acceptance_criteria": [
               {"ac_id": "AC-01", "given": "a report with many O/E", "when": "it is displayed", "then": "parent and child levels are distinguishable", "coverage": "normal"}]}


class BreakdownTests(unittest.TestCase):
    def test_without_approval_everything_hypothetical(self):
        exp = load(FIXTURES / "f08-breakdown-direction/expected.json")["without_approval"]
        with Workspace() as ws:
            bd = ws.breakdown()
            self.assertEqual(breakdown_policy.check(bd), [])
            self.assertEqual(bd["direction"]["status"], exp["direction"]); self.assertFalse(bd["official_handoff"])
            ops = {p["proposal_id"]: [p["operation"], p["target_task_id"]] for p in bd["task_proposals"]}
            self.assertEqual(ops["TP-01"], exp["TP-01"]); self.assertEqual(ops["TP-02"], exp["TP-02"])
            self.assertTrue(all(p["label"] == "hypothetical" for p in bd["task_proposals"]))
            bad = copy.deepcopy(bd); bad["stories"] = [STORY_A]; bad["official_handoff"] = True; bad["task_proposals"][1].update(operation="new_task_proposal")
            v = "\n".join(breakdown_policy.check(bad))
            for needle in ("must be labelled hypothetical", "official_handoff must be false", "needs an approved direction"):
                self.assertIn(needle, v)
            r = run(KIT_CLI, "validate", ws.path("breakdown.json")); self.assertEqual(r.returncode, 0, r.stderr); self.assertIn("breakdown_record ok", r.stdout)

    def test_with_dev_g2_approval_coverage_and_story_rules(self):
        exp = load(FIXTURES / "f08-breakdown-direction/expected.json")["with_dev_g2"]
        with Workspace() as ws:
            bd = ws.breakdown(approval=G2, out="bd-approved.json")
            self.assertEqual(bd["direction"]["status"], exp["direction"]); self.assertIsNotNone(bd["direction"]["approval_ref"])
            self.assertEqual(bd["task_proposals"][1]["operation"], exp["TP-02_default"])  # never auto-promoted
            happy_only = copy.deepcopy(bd); happy_only["stories"] = [STORY_A]
            self.assertTrue(any("at least one of" in v for v in breakdown_policy.check(happy_only)))
            no_story_promo = copy.deepcopy(bd); no_story_promo["task_proposals"][1]["operation"] = "new_task_proposal"
            self.assertTrue(any("needs at least one story" in v for v in breakdown_policy.check(no_story_promo)))
            promoted = ws.breakdown(approval=G2, out="bd-promoted.json", promote_gap=True)
            self.assertEqual(breakdown_policy.check(promoted), [])
            no_ref = copy.deepcopy(bd); no_ref["direction"]["approval_ref"] = None
            self.assertTrue(any("requires approval_ref" in v for v in breakdown_policy.check(no_ref)))

    def test_approval_must_name_this_artifact_and_be_human_and_unexpired(self):
        exp = load(FIXTURES / "f08-breakdown-direction/expected.json")["fake_agent_approval"]
        with Workspace() as ws:
            r = run(REPO / "scripts/breakdown-preprocess.py", ws.mapping, "--approval", FAKE)
            self.assertIn('"direction": "hypothetical"', r.stderr); self.assertIn(exp["approval_problem_contains"], r.stderr)
            other = load(G2); other["artifact_id"] = "SOME-OTHER-FEATURE-MAPPING"; dump(ws.path("other.json"), other)
            r = run(REPO / "scripts/breakdown-preprocess.py", ws.mapping, "--approval", ws.path("other.json"))
            self.assertIn('"direction": "hypothetical"', r.stderr); self.assertIn("covers artifact", r.stderr)
            expired = load(G2); expired["expires_at"] = "2020-01-01T00:00:00Z"; dump(ws.path("expired.json"), expired)
            r = run(REPO / "scripts/breakdown-preprocess.py", ws.mapping, "--approval", ws.path("expired.json"))
            self.assertIn("expired", r.stderr)
        for name in ("Аgent Smith", "role:ai-assistant", "automation"):
            self.assertTrue(draft_record.looks_like_agent(name), name)
        self.assertFalse(draft_record.looks_like_agent("Abbott"))


class PayloadPreviewTests(unittest.TestCase):
    def test_e09_artifact_approvals_are_not_action_approvals(self):
        exp = load(FIXTURES / "f09-payload-artifact-approval-only/expected.json")
        with Workspace() as ws:
            ws.breakdown(approval=G2, promote_gap=True)
            pv = ws.payload(g3=G3)
            self.assertEqual(payload_policy.check(pv), [])
            items = {i["item_id"]: i for i in pv["items"]}
            for iid in ("PI-01", "PI-02"):
                self.assertEqual(items[iid]["operation"], exp["all_items_operation"])
                self.assertTrue(any(exp["block_contains"] in b for b in items[iid]["block_reasons"]))
            self.assertEqual(pv["write_adapter"], exp["write_adapter"]); self.assertEqual(pv["external_action"], exp["external_action"])
            forced = copy.deepcopy(pv); forced["items"][1].update(operation="create", block_reasons=[])
            self.assertTrue(any("must be blocked" in v for v in payload_policy.check(forced)))
            tampered = copy.deepcopy(pv); tampered["items"][1]["payload"]["notes"] += " edited"
            self.assertTrue(any("payload_hash does not match" in v for v in payload_policy.check(tampered)))
            forged = copy.deepcopy(pv); forged["preconditions"]["action_approval"].update(status="present", payload_hash_expected=pv["items"][1]["payload_hash"], operation="create", approval_ref="runs/nowhere.json")
            forged["items"][1].update(operation="create", block_reasons=[])
            self.assertTrue(any("approval_ref file is missing" in v for v in payload_policy.check(forged)))

    def test_e10_g3_hash_destination_and_target_binding(self):
        exp = load(FIXTURES / "f10-payload-g3-and-stale-hash/expected.json")
        with Workspace() as ws:
            ws.breakdown(approval=G2, promote_gap=True)
            no_g3 = ws.payload()
            self.assertTrue(any(exp["no_g3_block_contains"] in b for b in no_g3["items"][1]["block_reasons"]))
            action = ws.action_approval_for(no_g3["items"][1], "create")
            ok = ws.payload(g3=G3, action=action)
            self.assertEqual(payload_policy.check(ok), [])
            self.assertEqual(ok["items"][1]["operation"], exp["with_g3_and_action"]); self.assertEqual(ok["items"][0]["operation"], "blocked")
            self.assertEqual(ok["preconditions"]["action_approval"]["status"], "present")
            wrong_dest = ws.action_approval_for(no_g3["items"][1], "create", name="wrong-dest.json", destination={"project_id": "WRONG-PROJECT", "parent_task_id": None, "task_id": None})
            self.assertEqual(ws.payload(g3=G3, action=wrong_dest)["items"][1]["operation"], "blocked")
            wrong_gate = ws.action_approval_for(no_g3["items"][1], "create", name="wrong-gate.json", gate="DEV.G1")
            self.assertEqual(ws.payload(g3=G3, action=wrong_gate)["preconditions"]["action_approval"]["status"], "invalid")
            bd = load(ws.path("breakdown.json")); bd["task_proposals"][1]["payload_preview"]["notes"] += " scope changed after approval"; dump(ws.path("breakdown.json"), bd)
            stale = ws.payload(g3=G3, action=action)
            self.assertEqual(stale["items"][1]["operation"], exp["after_content_change"]); self.assertEqual(stale["preconditions"]["action_approval"]["status"], exp["stale_status"])
            fake = ws.payload(g3=FAKE, action=action)
            self.assertEqual(fake["preconditions"]["dev_g3"]["status"], exp["fake_agent_g3_status"]); self.assertEqual(fake["items"][1]["operation"], "blocked")

    def test_ghost_parent_and_link_update_paths(self):
        with Workspace() as ws:
            bd = ws.breakdown(approval=G2, promote_gap=True)
            bd["task_proposals"][1]["payload_preview"]["parent_task_id"] = "GHOST-PARENT-999"; dump(ws.path("ghost.json"), bd)
            pv = ws.payload(breakdown_file="ghost.json", g3=G3)
            self.assertTrue(any("not found in task source" in b for b in pv["items"][1]["block_reasons"]))
            pv = ws.payload(g3=G3)
            link = ws.action_approval_for(pv["items"][0], "link", name="link.json")
            linked = ws.payload(g3=G3, action=link)
            self.assertEqual(linked["items"][0]["operation"], "link"); self.assertEqual(payload_policy.check(linked), [])
            bd = load(ws.path("breakdown.json")); bd["task_proposals"][0].update(target_task_id="GHOST-TASK-777"); dump(ws.path("ghost2.json"), bd)
            pv = ws.payload(breakdown_file="ghost2.json", g3=G3)
            self.assertTrue(any("target task GHOST-TASK-777 not found" in b for b in pv["items"][0]["block_reasons"]))
            two = copy.deepcopy(linked); two["items"][1].update(operation="create", block_reasons=[])
            self.assertTrue(any("at most one write item" in v or "must be blocked" in v for v in payload_policy.check(two)))

    def test_payload_preprocess_refuses_invalid_breakdown_and_sync_has_new_skills(self):
        with Workspace() as ws:
            dump(ws.path("bad.json"), {"output_type": "breakdown_record"})
            r = run(REPO / "scripts/create-asana-tasks-preprocess.py", ws.path("bad.json"), "--project", "X")
            self.assertEqual(r.returncode, 2); self.assertIn("REFUSED", r.stderr)
        self.assertEqual(adapter_sync.check(REPO), [])
        for name in ("breakdown-feature", "create-asana-tasks", "evaluate-pm-output"):
            self.assertTrue((REPO / ".claude/skills" / name / "SKILL.md").exists()); self.assertTrue((REPO / ".agents/skills" / name / "SKILL.md").exists())


if __name__ == "__main__":
    unittest.main()
