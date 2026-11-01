# runs/ — local drafts and minimal run logs (gitignored)

One folder per `run_id`. Allowed content: redacted Intake Records and other Draft artifacts, evidence **links/locations**, the minimal run log fields from spec §10.3 (`run_id; feedback_id; work_type; complexity; source_snapshot; kit/role/product/adapter_version; runtime/model; start/end; human_minutes; wait_minutes; revision_count; questions_for_missing_context; errors_caused_by_agent; human_decisions; rubric; safety_result; downstream links; cost_or_NA; final_decision`).

Forbidden: raw feedback with reporter identity, performance/salary/personal data, tokens, un-redacted source dumps. Run `python3 core/scripts/kit-cli.py scan <file>` before saving free text here.
