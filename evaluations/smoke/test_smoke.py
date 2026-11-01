"""Smoke tests for BM Agent Kit foundation. stdlib unittest only; run from repo root."""
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "core"))
from kitlib import adapter_sync, config_layers, intake_policy  # noqa: E402

FIXTURES = REPO / "evaluations" / "fixtures"
PREPROCESS = REPO / "scripts" / "intake-preprocess.py"
KIT_CLI = REPO / "core" / "scripts" / "kit-cli.py"


def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _preprocess(fixture):
    out = subprocess.run([sys.executable, str(PREPROCESS), str(FIXTURES / fixture / "input.json")],
                         capture_output=True, text=True, cwd=REPO)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


class ConfigLayerTests(unittest.TestCase):
    def test_config_check_cli_passes(self):
        r = subprocess.run([sys.executable, str(KIT_CLI), "config-check"], capture_output=True, text=True, cwd=REPO)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("writes=disabled", r.stdout)

    def test_effective_capabilities_narrowed_by_product(self):
        layers = [_load(REPO / "core/contracts/core-contract.json"), _load(REPO / "roles/pm/pm-role-contract.json"),
                  _load(REPO / "products/igoal/igoal-product-contract.json")]
        eff, violations = config_layers.compose(layers)
        self.assertEqual(violations, [])
        self.assertNotIn("read_dashboard", eff["tools"]["capabilities"])

    def test_lower_layer_cannot_enable_writes(self):
        layers = [_load(REPO / "core/contracts/core-contract.json"), _load(REPO / "roles/pm/pm-role-contract.json")]
        bad = copy.deepcopy(layers[1]); bad["tools"]["writes"] = "enabled"; bad["safety"]["human_gate_required"] = False
        bad["tools"]["capabilities"].append("write_tasks"); bad["rogue_key"] = 1
        _, violations = config_layers.compose([layers[0], bad])
        joined = "\n".join(violations)
        for needle in ("tools.writes", "human_gate_required", "write_tasks", "rogue_key"):
            self.assertIn(needle, joined)


class AdapterSyncTests(unittest.TestCase):
    def test_runtime_copies_hash_match(self):
        self.assertEqual(adapter_sync.check(REPO), [])

    def test_root_instruction_files_identical(self):
        self.assertEqual((REPO / "AGENTS.md").read_bytes(), (REPO / "CLAUDE.md").read_bytes())
        self.assertTrue((REPO / ".claude/skills/intake-feedback/SKILL.md").exists())
        self.assertTrue((REPO / ".agents/skills/intake-feedback/SKILL.md").exists())


class FixtureTests(unittest.TestCase):
    def _common(self, rec, exp):
        self.assertEqual(intake_policy.check(rec), [])
        self.assertEqual(rec["external_action"], exp["external_action"])
        self.assertEqual(rec["sensitive_content"]["detected"], exp["sensitive_detected"])
        self.assertEqual(rec["untrusted_instructions"]["detected"], exp["untrusted_detected"])

    def test_f01_missing_evidence(self):
        rec, exp = _preprocess("f01-missing-evidence"), _load(FIXTURES / "f01-missing-evidence/expected.json")
        self._common(rec, exp)
        part = rec["parts"][0]; e = exp["parts"]["A"]
        self.assertEqual(part["category_proposed"], e["category_proposed"])
        self.assertEqual(part["reproducible"], e["reproducible"])
        self.assertEqual(len(part["duplicate_candidates"]), e["duplicate_candidates_count"])
        self.assertGreaterEqual(len(rec["open_questions"]), exp["min_open_questions"])

    def test_f02_duplicate_open_task(self):
        rec, exp = _preprocess("f02-duplicate-open-task"), _load(FIXTURES / "f02-duplicate-open-task/expected.json")
        self._common(rec, exp)
        parts = {p["part_id"]: p for p in rec["parts"]}
        self.assertGreaterEqual(len(parts["A"]["duplicate_candidates"]), 1)
        self.assertEqual(parts["A"]["duplicate_candidates"][0]["task_id"], exp["parts"]["A"]["top_duplicate_task_id"])
        self.assertNotIn(exp["parts"]["B"]["must_not_contain_task_id"], [c["task_id"] for c in parts["B"]["duplicate_candidates"]])
        self.assertFalse(rec["requirement_task_mapping"]["duplicate_search"]["exhaustive"])
        self.assertEqual(rec["feedback"]["source_priority_label"], exp["source_priority_label"])
        self.assertEqual(parts["A"]["severity_proposed"], "unknown")  # label never becomes severity

    def test_f03_prompt_injection(self):
        rec, exp = _preprocess("f03-prompt-injection"), _load(FIXTURES / "f03-prompt-injection/expected.json")
        self._common(rec, exp)
        found = {w["pattern_id"] for w in rec["untrusted_instructions"]["warnings"]}
        for pid in exp["untrusted_patterns_min"]:
            self.assertIn(pid, found)
        self.assertNotIn("approved", rec["gate_status"].values())
        self.assertIsNone(rec["approval"]["approved_by"])
        for w in rec["untrusted_instructions"]["warnings"]:  # warnings carry no quoted text
            self.assertEqual(set(w) <= {"pattern_id", "part_id", "position"}, True)

    def test_f04_sensitive_content(self):
        rec, exp = _preprocess("f04-sensitive-content"), _load(FIXTURES / "f04-sensitive-content/expected.json")
        self._common(rec, exp)
        for cat in exp["sensitive_categories_min"]:
            self.assertIn(cat, rec["sensitive_content"]["categories"])
        blob = json.dumps(rec, ensure_ascii=False)
        for needle in exp["redacted_text_must_not_contain"]:
            self.assertNotIn(needle, blob)


class PolicyGateTests(unittest.TestCase):
    """E09/E10 analogues: a record that tries to act or self-approve is rejected."""
    def setUp(self):
        self.rec = _preprocess("f01-missing-evidence")

    def test_ok_content_is_not_action_approval(self):
        rec = copy.deepcopy(self.rec); rec["external_action"]["requested"] = True
        self.assertTrue(any("external_action" in v for v in intake_policy.check(rec)))

    def test_agent_cannot_approve_gate_or_self_approve(self):
        rec = copy.deepcopy(self.rec); rec["gate_status"]["DEV.G1"] = "approved"; rec["approval"]["approved_by"] = "PM Agent"
        v = "\n".join(intake_policy.check(rec))
        self.assertIn("gate_status.DEV.G1=approved", v); self.assertIn("approved_by", v)

    def test_bug_requires_reproduction_and_facts_need_sources(self):
        rec = copy.deepcopy(self.rec); rec["parts"][0]["category_proposed"] = "bug"
        rec["facts"].append({"label": "fact", "claim": "unsourced claim"})
        v = "\n".join(intake_policy.check(rec))
        self.assertIn("requires reproducible=yes", v); self.assertIn("fact without source_ref", v)

    def test_sensitive_content_blocks_persist(self):
        rec = copy.deepcopy(self.rec); rec["parts"][0]["text_redacted"] += " token sk-live-ABCDEFGHIJKLMNOP"
        self.assertTrue(any("sensitive" in v for v in intake_policy.check(rec)))


if __name__ == "__main__":
    unittest.main()
