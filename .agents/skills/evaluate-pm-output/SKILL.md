---
name: evaluate-pm-output
description: Self-check any PM Draft record (intake, mapping, breakdown, payload preview) against the Kit policies, the five immediate-fail conditions and the 100-point human rubric; produce an ADVISORY Evaluation Record with evidence gaps and concrete fixes. Use when a human asks to evaluate, review, score or QA a PM Agent output before handing it to Tom. Advisory only: the human grade is recorded by Tom/QA elsewhere and a passing self-check grants no send/write right.
---

# evaluate-pm-output (advisory)

Status: phase 3, v0.2.0-draft. `evaluation.self_check: advisory`, `final_grader: human` (spec §3, §9).

## Procedure
1. **Automated half (script):**
   `python3 scripts/evaluate-preprocess.py runs/<run_id>/<record>.json --out runs/<run_id>/<record>-eval.json`
   Runs the record's policy, decides the immediate-fail checks it can (external action, sensitive content, self-approval / agent-approved gate / unsourced facts, draft handed over as approved; production action is not applicable in MVP), and fills each rubric criterion's automated `basis`. `agent_level` stays `null`, verdict `fail_stop` or `incomplete`.
2. **Advisory levels** — for each of the six criteria set `agent_level` 0–4 with a one-line `basis` that cites locations in the evaluated record, list `evidence_gaps` and concrete `fixes`. Never touch `human_level` (always `null`).
3. **Verdict** — `fail_stop` if any immediate fail; else `needs_fixes` (score < 85 or violations) or `pass_advisory` (score ≥ 85, no violations). `advisory_score` = Σ level/4 × weight.
4. **Validate:** `python3 core/scripts/kit-cli.py validate runs/<run_id>/<record>-eval.json`.
5. **Return** the evaluation to the reviewer. A `pass_advisory` is a signal, never a permission; the human rubric (`roles/pm/rubric/pm-output-rubric.md`) decides.

## Output contract
Schema: `core/contracts/schemas/evaluation-record.schema.json`. `is_human_evaluation: false`, `final_grader: human`, `human_level: null` are constants.

## Hard stops
Never record the self-check as a human evaluation. Never average away an immediate fail. If a fail is found: stop the affected part, propose a regression fixture under `evaluations/fixtures/`.

References: `references/evaluation-rules.md`.
