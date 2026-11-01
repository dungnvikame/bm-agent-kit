---
name: create-asana-tasks
description: Produce a Task Payload Preview from a validated Breakdown Record — exact Asana payload per proposal, canonical payload hash, diff, side effects, final duplicate check and the operation a human may perform (create / update / link / no_op / blocked). Use when a human asks to prepare, preview or hand over Asana tasks for an approved breakdown. PROPOSAL-ONLY: the write adapter is disabled, nothing is sent to Asana, Tom enters approved payloads manually.
---

# create-asana-tasks (proposal-only)

Status: phase 3, v0.2.0-draft. Mode: `read_only_draft`. **No write capability exists in MVP** (spec §5.4 step 5).

## Preconditions
- Validated Breakdown Record under `runs/<run_id>/`.
- Target project id (and optional parent) that exist in the task source read this run.
- For any write (`create`/`update`/`link`) to be allowed: a **human** DEV.G3 approval record for this breakdown artifact AND a **human** action approval (same gate/artifact) with `operation`, `destination` and `payload_hash` equal to the item's. Only `no_op` needs none. Both are files Tom writes under `runs/<run_id>/approvals/`.

## Procedure (spec §5.4)
1. **Preview (script):**
   `python3 scripts/create-asana-tasks-preprocess.py runs/<run_id>/breakdown-record.draft.json --project <id> [--parent <id>] [--g3 ...dev-g3.json] [--action ...action.json] --out runs/<run_id>/payload-preview.draft.json`
   Builds one item per proposal with payload + `sha256` hash, decides `create/update/link/no_op/blocked`, lists diff and side effects (followers, notifications, parent subtask), re-checks duplicates, verifies project/parent against the task snapshot.
2. **Read the preview**: every `blocked` item lists its reasons (no DEV.G3, no action approval, hash mismatch = content changed since approval, target unverified, duplicate candidates, hypothetical direction).
3. **Hand over**: give Tom the payload(s) of allowed items for manual entry. Do not paraphrase the payload; the hash is the contract.
4. **Content changed?** Any edit to name/notes/target changes the hash → the action approval is stale → item returns to `blocked` until Tom re-approves the new hash.
5. **Validate:** `python3 core/scripts/kit-cli.py validate runs/<run_id>/payload-preview.draft.json`.

## Output contract
Schema: `core/contracts/schemas/payload-preview-record.schema.json`. `write_adapter: disabled`, `handoff_mode: manual_entry_by_human`, `external_action` false — all constants.

## Hard stops
"Ok nội dung", an approved PRD or an approved gate is **not** an action approval. One action approval covers one exact payload. Never create when duplicate candidates exist; propose link/update/no_op for the human instead. If a write adapter is ever enabled, that is a separate config change reviewed on its own (readback + idempotency required).

References: `references/payload-rules.md`.
