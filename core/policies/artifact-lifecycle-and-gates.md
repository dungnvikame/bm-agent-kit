# Artifact Lifecycle and Gates (Shared Core)

Source: spec §6.

## Lifecycle
**Agent Draft → Human Review → Approved → Versioned.** Changes create a new Draft version; Approved history is kept. Downstream phases consume only Approved artifacts that are recorded in the Source of Truth. When write tools are off, Tom records the decision and provides link/version; the official workflow waits for that step.

## Gate namespaces
Use `DEV.G1–G5` and `OPS.O1–O4`. Never equate them with the iGoal Project Plan timeline milestones G1–G10 ("G3 Nền tảng sẵn sàng" ≠ `DEV.G3 Build Ready`).

| Step | Human owner | Agent work | Output | Gate |
|---|---|---|---|---|
| Intake / Detect | Tom (Ops/TL if incident signal) | record signal, split parts, dedupe, filter data | Intake Record (local Draft) | none to write locally; no right to create external tickets |
| Define | PM + decision-making stakeholder | mapping, impact, problem, metric, open questions | Problem Brief + Success Metric | `DEV.G1` Problem Approved |
| Shape | PM + Design + Dev | compare directions, assumptions, trade-offs | Solution Brief + prototype from the owning role | `DEV.G2` Solution Approved |
| Ready | PM coordinates PM/Design/Dev/QA | PRD/AC + role checklists | Build-ready Pack; task **payload preview** | `DEV.G3` Build Ready, then task creation only with a write order |
| Build & Verify | Dev + QA; PM checks scope | compare AC, aggregate risk/evidence | scope review; PR/tests from Dev/QA | `DEV.G4` Release Ready; PM Agent never releases |
| Release & Learn | PM + Dev + QA + Ops | compare metrics/feedback, draft outcome review | Release Record + Outcome Review | `DEV.G5` Outcome Reviewed |

Build-ready Pack is a team product (PRD, design with states, AC, technical approach/data/API contract, test strategy, tracking, dependencies/owners, rollout/communication/rollback); each role confirms its part. Before G3 tasks are payload previews; after G3 approved tasks get URLs added to the pack.

## Incidents
If triage confirms an incident → Operations: `OPS.O1` Triage Approved (TL/Ops Owner + PM when users affected), `OPS.O2` Fix Approved (Dev Reviewer/QA/TL when high risk), `OPS.O3` Recovery Confirmed (TL/QA + PM when needed), `OPS.O4` Learning Closed (PM/TL/Ops Owner). PM Agent aggregates impact, proposes, hands off; never diagnoses root cause with certainty, never executes fix/deploy.

## Gate status values in artifacts
`not_started | pending | approved | invalidated`. The agent may write `not_started`, `pending` or `invalidated`. It never writes `approved`; that value is entered by the human reviewer together with an approval record.
