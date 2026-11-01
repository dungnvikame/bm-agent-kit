# Maintainer dashboard (`tools/dashboard/`)

Local tool for the Kit owner to **see** what the kit contains and **edit** canonical agent configuration safely. It is not part of the agent runtime: nothing under `tools/` is loaded by Claude Code or Codex, and the spec's "no web UI in the agent MVP" still holds.

## Run

```bash
python3 tools/dashboard/serve.py            # http://127.0.0.1:8765
python3 tools/dashboard/serve.py --port 9000
python3 -m unittest discover -s tools/dashboard/tests
```

Python 3 stdlib only, no pip, binds to 127.0.0.1 only. Requests with a non-loopback `Host` or `Origin` are refused.

## Read views

| View | Source |
|---|---|
| Layers & effective config | the three layer contracts composed with `kitlib.config_layers.compose`; violations shown, fail closed |
| Skills | `roles/pm/skills/README.md` registry vs. `roles/pm/skills/*/SKILL.md` on disk; `.claude/skills` and `.agents/skills` hash-checked with `kitlib.adapter_sync.check` |
| Policies | `core/policies/*.md` as text |
| Product pack (iGoal) | `products/igoal/context-index.md`, `source-registry.json` records with `approval_status`, product contract |
| Evaluations | fixtures under `evaluations/fixtures/`; button runs `python3 -m unittest discover -s evaluations/smoke -v` |
| Plans & reports | phase table from `plans/261101-2157-pm-agent-foundation/plan.md`, files in `plans/reports/` |

## Edit views and the save path

- **Contracts (forms)**: field-level editing of `roles/pm/pm-role-contract.json` and `products/igoal/igoal-product-contract.json` with live JSON. `core/contracts/core-contract.json` is shown read-only ("Core changes need Kit owner review"). Keys locked by core carry a 🔒 marker.
- **Text editor**: `roles/pm/skills/<name>/SKILL.md`, `roles/pm/skills/<name>/references/*.md`, `core/policies/*.md`, `core/agent-instructions.md`.

Every save goes through `tools/dashboard/repo_writer.py`:

1. Path must be on the allowlist in `editable_paths.py` and inside the repo. Generated copies (`AGENTS.md`, `CLAUDE.md`, `.claude/`, `.agents/`, `.codex/`), `core-contract.json`, schemas, templates, the git directory and anything outside the repo are refused. The dashboard never creates files.
2. JSON files must parse to an object.
3. Core → Role → Product is recomposed with the new content in memory. Any violation (for example re-enabling `tools.writes`) refuses the save and the violations are shown. Nothing is written.
4. The file is written. If it is a skill file or `core/agent-instructions.md`, `adapter_sync.write` regenerates `.claude/skills`, `.agents/skills`, `AGENTS.md`, `CLAUDE.md`, then `adapter_sync.check` confirms the copies hash-match.

No git commit or push happens from the UI; review `git diff` and commit yourself.

## Privacy

The dashboard never reads or lists `runs/`, `products/*/source-registry.local.json`, `.env*` or the local spec file. Those stay private on the machine.

## Layout

`serve.py` (entry) → `dashboard_server.py` (HTTP + JSON API) → `repo_reader.py` / `repo_writer.py` / `smoke_runner.py` → `core/kitlib`. `editable_paths.py` holds the allowlist. Static page in `static/` (`index.html`, `style.css`, `dashboard-core.js`, `json-form.js`, `views-read.js`, `views-edit.js`). Tests in `tests/` run against a temporary copy of the repo.
