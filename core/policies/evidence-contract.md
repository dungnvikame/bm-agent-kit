# Evidence Contract (Shared Core)

Source: spec §4.1, §4.2, §4.3, §9.2 criterion 1.

## Labels
Every claim in an artifact carries exactly one label:
- **Fact** — observed in a registered source; MUST have `source_ref {source_id, location}`.
- **Inference** — reasoning from facts; say which facts.
- **Proposal** — something the agent suggests; never presented as decided.
- **Unknown** — not verifiable from sources read; becomes an open question. Never fill with a guess.

## Source Registry record (minimum fields)
`source_id, url, type, owner, authority_domain, version_or_snapshot, modified_at, retrieved_at, approval_status, approved_by, approved_at, sensitivity, supersedes`. Missing value → `"unknown"`. Official inputs require `approved_by, approved_at, version_or_snapshot`; otherwise the source is `evidence_or_proposal_only`.

Sheet citation: tab + row/code + range. Asana citation: task id + modified_at + the fields used. In the shared repo the `url` field holds `"unknown"` or a redacted placeholder; real URLs live in the gitignored `source-registry.local.json`.

## Authority by domain
- Product Hub: vision, business rules, requirements, official decisions
- Asana: tasks, owners, deadlines, execution status
- Figma: design · Git: technical context · dashboards: metrics · health dashboard: logs/incidents
- Slack and feedback tables: signal only. A Slack decision is official only with a Decision Log (owner, date, reason, approval).
- Within one domain prefer the **approved** decision with clear scope/supersedes. Newer or higher-ranked does not automatically win.
- Two sources with apparent equal authority that conflict: present both, name the affected decision, ask Tom/owner, continue only the independent parts.

## Reading context per run
1. Core + role config + Product Context Index → pick relevant modules.
2. Pull the minimum requirements, decisions and tasks for the problem; never read the whole store by default.
3. Build an evidence ledger with source locations and labels.
4. Duplicate search by keyword **and** meaning; record the search scope; never claim exhaustiveness after a quick search.
5. Check version and approval of each input before each gate.
6. Before any write proposal: re-read task state, source and approval; a change invalidates the earlier approval pack.

## Memory
Conversation history is working context, not Source of Truth. Only decisions approved by a human and recorded in an official source may be reused as policy. The agent never learns a rule from its own edits.
