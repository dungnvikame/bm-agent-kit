"""Allowlist / denylist behaviour of the dashboard path guard."""
import unittest

import repo_fixture  # noqa: F401  (sets sys.path)
import editable_paths as ep


class EditablePathsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp, cls.cleanup = repo_fixture.make_temp_repo()

    @classmethod
    def tearDownClass(cls):
        cls.cleanup()

    def test_editable_canonical_files(self):
        for rel in ("roles/pm/pm-role-contract.json", "products/igoal/igoal-product-contract.json",
                    "core/agent-instructions.md", "core/policies/safety-policy.md",
                    "roles/pm/skills/intake-feedback/SKILL.md",
                    "roles/pm/skills/intake-feedback/references/intake-procedure.md"):
            self.assertEqual(ep.classify(rel)[0], "editable", rel)

    def test_core_contract_is_read_only_with_note(self):
        kind, note = ep.classify("core/contracts/core-contract.json")
        self.assertEqual(kind, "read_only")
        self.assertIn("Kit owner review", note)

    def test_generated_copies_and_git_denied(self):
        for rel in ("AGENTS.md", "CLAUDE.md", ".claude/skills/intake-feedback/SKILL.md",
                    ".agents/skills/intake-feedback/SKILL.md", ".codex/config.toml", ".git/HEAD",
                    "adapters/sync-manifest.json", "core/contracts/schemas/intake-record.schema.json",
                    "roles/pm/skills/intake-feedback/templates/intake-record.template.json"):
            self.assertEqual(ep.classify(rel)[0], "denied", rel)

    def test_private_files_denied(self):
        for rel in ("runs/secret-run/intake.json", "products/igoal/source-registry.local.json",
                    "pm-agent-config-v0.2.0-review.md", ".env"):
            self.assertTrue(ep.is_private(rel), rel)
            self.assertEqual(ep.classify(rel)[0], "denied", rel)

    def test_resolve_refuses_escape(self):
        for bad in ("../outside.md", "core/../../etc/passwd", "/etc/passwd", "~/x", "", None, "a\\b"):
            with self.assertRaises(PermissionError, msg=bad):
                ep.resolve(bad)
        self.assertTrue(ep.resolve("core/policies/safety-policy.md").is_file())

    def test_needs_sync(self):
        self.assertTrue(ep.needs_sync("roles/pm/skills/intake-feedback/SKILL.md"))
        self.assertTrue(ep.needs_sync("core/agent-instructions.md"))
        self.assertFalse(ep.needs_sync("core/policies/safety-policy.md"))
        self.assertFalse(ep.needs_sync("roles/pm/pm-role-contract.json"))

    def test_viewable_files_exclude_private_and_generated(self):
        paths = {f["path"] for f in ep.viewable_files()}
        self.assertIn("core/contracts/core-contract.json", paths)
        self.assertIn("roles/pm/skills/intake-feedback/SKILL.md", paths)
        self.assertFalse(any(p.startswith(("runs/", ".claude/", ".agents/", ".git")) or p.endswith(".local.json") for p in paths))


if __name__ == "__main__":
    unittest.main()
