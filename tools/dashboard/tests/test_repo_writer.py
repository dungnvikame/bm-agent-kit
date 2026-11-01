"""Guarded save path: allowlist, JSON validation, fail-closed compose, adapter re-sync."""
import json
import unittest

import repo_fixture  # noqa: F401
import repo_reader as rr
import repo_writer as rw
from repo_writer import SaveRefused

ROLE = "roles/pm/pm-role-contract.json"
SKILL = "roles/pm/skills/intake-feedback/SKILL.md"


class RepoWriterTest(unittest.TestCase):
    def setUp(self):
        self.tmp, self.cleanup = repo_fixture.make_temp_repo()

    def tearDown(self):
        self.cleanup()

    def test_enabling_writes_is_refused_with_violation(self):
        role = rr.read_json(ROLE)
        before = (self.tmp / ROLE).read_bytes()
        role["tools"]["writes"] = "enabled"
        with self.assertRaises(SaveRefused) as ctx:
            rw.save_json(ROLE, role)
        self.assertTrue(any("tools.writes is locked" in v for v in ctx.exception.details), ctx.exception.details)
        self.assertEqual((self.tmp / ROLE).read_bytes(), before, "refused save must not touch the file")

    def test_adding_capability_or_unknown_key_is_refused(self):
        role = rr.read_json(ROLE)
        role["tools"]["capabilities"].append("write_tasks")
        with self.assertRaises(SaveRefused):
            rw.save_json(ROLE, role)
        role = rr.read_json(ROLE)
        role["surprise"] = 1
        with self.assertRaises(SaveRefused):
            rw.save_json(ROLE, role)

    def test_allowed_change_is_saved(self):
        role = rr.read_json(ROLE)
        role["language"]["chat"] = "vi-VN"
        result = rw.save_json(ROLE, role)
        self.assertTrue(result["saved"])
        self.assertIsNone(result["sync"])
        self.assertEqual(rr.read_json(ROLE)["language"]["chat"], "vi-VN")
        self.assertEqual(rr.layers_view()["violations"], [])

    def test_unchanged_json_is_not_rewritten(self):
        before = (self.tmp / ROLE).read_bytes()
        result = rw.save_text(ROLE, json.dumps(rr.read_json(ROLE), indent=4))
        self.assertFalse(result["saved"])
        self.assertEqual((self.tmp / ROLE).read_bytes(), before)

    def test_invalid_json_and_non_object_refused(self):
        with self.assertRaises(SaveRefused):
            rw.save_text(ROLE, "{not json")
        with self.assertRaises(SaveRefused):
            rw.save_text(ROLE, "[1, 2]")

    def test_denied_paths(self):
        for rel in ("AGENTS.md", "core/contracts/core-contract.json", ".claude/skills/intake-feedback/SKILL.md",
                    "runs/secret-run/intake.json", "../escape.md", "core/policies/new-policy.md"):
            with self.assertRaises(PermissionError, msg=rel):
                rw.save_text(rel, "x")

    def test_skill_edit_resyncs_adapter_copies(self):
        text = rr.read_text(SKILL) + "\n<!-- maintainer note -->\n"
        result = rw.save_text(SKILL, text)
        self.assertTrue(result["saved"])
        self.assertIn(".claude/skills/intake-feedback", result["sync"]["written"])
        self.assertEqual(result["sync"]["problems"], [])
        for copy in (".claude/skills/intake-feedback/SKILL.md", ".agents/skills/intake-feedback/SKILL.md"):
            self.assertEqual((self.tmp / copy).read_text(encoding="utf-8"), text)

    def test_agent_instructions_edit_resyncs_root_copies(self):
        text = rr.read_text("core/agent-instructions.md") + "\nExtra line.\n"
        result = rw.save_text("core/agent-instructions.md", text)
        self.assertEqual((self.tmp / "AGENTS.md").read_text(encoding="utf-8"), text)
        self.assertEqual((self.tmp / "CLAUDE.md").read_text(encoding="utf-8"), text)
        self.assertEqual(result["sync"]["problems"], [])

    def test_policy_edit_does_not_sync(self):
        result = rw.save_text("core/policies/safety-policy.md", "# Safety policy (edited)\n")
        self.assertTrue(result["saved"])
        self.assertIsNone(result["sync"])


if __name__ == "__main__":
    unittest.main()
