"""Read views render from the (copied) repo files and never expose private files."""
import unittest

import repo_fixture  # noqa: F401
import repo_reader as rr
from md_tables import parse_tables, strip_code


class RepoReaderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp, cls.cleanup = repo_fixture.make_temp_repo()

    @classmethod
    def tearDownClass(cls):
        cls.cleanup()

    def test_layers_view_composes_without_violations(self):
        v = rr.layers_view()
        self.assertEqual([l["name"] for l in v["layers"]], ["core", "role", "product"])
        self.assertEqual(v["violations"], [])
        self.assertEqual(v["effective"]["tools"]["writes"], "disabled")
        self.assertEqual(v["layers"][0]["kind"], "read_only")
        self.assertEqual(v["layers"][1]["kind"], "editable")

    def test_skills_view_marks_implemented_and_synced(self):
        v = rr.skills_view()
        by_name = {s["name"]: s for s in v["skills"]}
        intake = by_name["intake-feedback"]
        self.assertTrue(intake["implemented"] and intake["in_manifest"] and intake["sync_ok"])
        self.assertTrue(intake["copies"][".claude/skills"] and intake["copies"][".agents/skills"])
        self.assertIn("roles/pm/skills/intake-feedback/SKILL.md", intake["files"])
        planned = [s for s in v["skills"] if not s["implemented"]]
        self.assertTrue(planned, "registry lists planned skills")
        self.assertTrue(all(s["registry"] is not None for s in planned))
        self.assertEqual(v["sync_problems"], [])

    def test_skills_view_detects_drift(self):
        (self.tmp / ".claude/skills/intake-feedback/SKILL.md").write_text("drifted", encoding="utf-8")
        try:
            v = rr.skills_view()
            intake = next(s for s in v["skills"] if s["name"] == "intake-feedback")
            self.assertFalse(intake["sync_ok"])
            self.assertTrue(any("hash mismatch" in p for p in intake["sync_problems"]))
        finally:
            src = (self.tmp / "roles/pm/skills/intake-feedback/SKILL.md").read_bytes()
            (self.tmp / ".claude/skills/intake-feedback/SKILL.md").write_bytes(src)

    def test_policies_product_evaluations_plans(self):
        self.assertGreaterEqual(len(rr.policies_view()), 5)
        prod = rr.product_view()
        self.assertTrue(prod["registry"]["records"])
        self.assertTrue(all("approval_status" in r for r in prod["registry"]["records"]))
        self.assertNotIn("private.example", str(prod))
        ev = rr.evaluations_view()
        self.assertIn("f01-missing-evidence", [f["name"] for f in ev["fixtures"]])
        plans = rr.plans_view()
        self.assertTrue(plans["phases"] and "Phase" in plans["phases"][0])
        self.assertTrue(plans["reports"])

    def test_file_view_refuses_private_and_generated(self):
        for rel in ("runs/secret-run/intake.json", "products/igoal/source-registry.local.json", "AGENTS.md", ".claude/skills/intake-feedback/SKILL.md"):
            with self.assertRaises(PermissionError, msg=rel):
                rr.file_view(rel)
        with self.assertRaises(FileNotFoundError):
            rr.file_view("core/policies/does-not-exist.md")
        ro = rr.file_view("core/contracts/core-contract.json")
        self.assertEqual(ro["kind"], "read_only")

    def test_md_table_parser(self):
        tables = parse_tables("intro\n| A | B |\n|---|---|\n| `x` | **bold** |\n\ntext")
        self.assertEqual(tables[0]["headers"], ["A", "B"])
        self.assertEqual(strip_code(tables[0]["rows"][0]["A"]), "x")


if __name__ == "__main__":
    unittest.main()
