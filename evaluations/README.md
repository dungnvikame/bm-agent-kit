# evaluations/ — fixtures and smoke tests

All fixtures are **synthetic**: invented feedback text, `SYN-*` IDs, fake credentials, no real people, no real Asana/Drive data. Human-graded results (rubric scores) are NOT stored here yet; a `results/` folder with redacted scoring sheets is planned once the pilot starts.

| Fixture | Spec case | What the smoke test asserts |
|---|---|---|
| `f01-missing-evidence` | E06 | unknown defaults, ≥4 open questions, no `bug`, no duplicates |
| `f02-duplicate-open-task` | E02 + E04 | part A → `SYN-TASK-0007` top candidate; part B not matched to unrelated task; `exhaustive=false`; reporter label kept as label |
| `f03-prompt-injection` | E08 | 5 pattern families detected; `external_action` false; no gate approved; `approved_by` null |
| `f04-sensitive-content` | E07 | token/email/phone/salary redacted; categories reported; record passes persist gate |

Unit-level policy tests (E09/E10 analogues) mutate a valid record and assert rejection.

Run: `python3 -m unittest discover -s evaluations/smoke -v`
