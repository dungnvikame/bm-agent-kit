# iGoal — Product Context Index (entrypoint)

Layer: `product`. Config: `igoal-product-contract.json`. Sources: `source-registry.json` (shared, URL-free) + `source-registry.local.json` (gitignored, real links).

**Status of this index: unclosed.** Spec §12 step 2 ("Đóng Product Context Index iGoal") has not happened. No source below is confirmed Approved; every record carries `approval_status: unknown`. Until Tom closes the index, all sources are `evidence_or_proposal_only`.

## What iGoal is (for module routing only)
OKR / goal-management product used by iKame teams: objectives (O), key results (KR), E/KS sub-structure, check-ins, reports, EKS/performance-related views, permission rules by module and role. Performance and personnel data exist in the product → **sensitive zones apply to every read** (see `core/policies/safety-policy.md`).

## Modules (routing keys used in `feedback.module`)
| Module key | Covers | Typical sources |
|---|---|---|
| `bao-cao` (Báo cáo) | report writing/reading views, O/E & KR/KS hierarchy display, check-in UX | S4 requirements, S6 feedback, S7 tasks |
| `check-in` | periodic check-in flow | S4, S7 |
| `phan-quyen` (Phân quyền) | who sees what; module/role rules | S8, S9 (conflicting, unresolved) |
| `okr-structure` | creating/editing O/KR/E/KS | S4, S5 |
| `dashboard-metric` | metrics/aggregations | no approved dashboard source registered |

Module list is derived from the spec's example and routing needs; confirm/extend with Tom.

## Authority by domain (iGoal instance of core evidence-contract)
- Requirements & decisions: Product Hub docs (S2, S4, S5) — approval record per row still unverified.
- Execution status: Asana iGoal project (S7) — snapshot, not QA/release evidence.
- Signal: Pilot Feedback sheet (S6), Slack — never a requirement by itself.
- Permission rules: S8 (contains unresolved sentences and contradictions) vs S9 (secondary, describes new rules under test 27–28/10) → always ask for the original decision; never self-grant or conclude a rule is released.

## Known conflicts to surface, not resolve
- S8 personal-data principle (direct manager only) vs S8 passage granting L2/L1 visibility of EKS/HR reports of sub-teams; S9 describes a newer rule under test. Affected decisions: anything in `phan-quyen`.
- Timeline milestones G1–G10 in S5 ≠ workflow gates `DEV.G1–G5`.
- Scope-lock date noted in S5 (16/10) — check whether still effective before proposing new scope.

## Per-run reading rule
Read only the modules relevant to the feedback. Record each read as a `sources[]` entry with location and `retrieved_at`. Do not read whole sheets or the whole backlog by default.
