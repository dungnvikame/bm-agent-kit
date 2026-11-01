# Tool Policy (Shared Core)

Default: **deny**. Source: spec §3 `tools`, §7, §11.

| Logical capability | MVP status | Rule |
|---|---|---|
| `read_docs` (Drive/Docs) | allowed, scoped | Read the exact file/tab/range in the Source Registry; save citation `source_id + location + retrieved_at`; never edit |
| `read_sheets` | allowed, scoped | Same; record tab + row/range + feedback/requirement code |
| `read_tasks` (Asana) | allowed, in registered project only | search → read candidate detail → record snapshot `{id, modified_at, relevant fields}`; never create/update/comment/move |
| `read_chat` (Slack) | only to verify a source, when permitted | signal only, until a Decision Log exists |
| `read_dashboard` | only if an approved source exists | use numbers that have a definition and period; never invent a baseline |
| `web_search` | allowed, filtered query | see safety-policy |
| `local_draft_write` | allowed | only under `runs/<run_id>/`, only filtered content |
| `write_tasks`, `write_docs`, `write_sheets`, `change_status` | **disabled** | preview diff/payload only; needs action approval + write adapter in a later round |
| `send_message`, `comment`, `tag`, `invite`, `schedule` | **disabled** | content review never grants send rights |
| production / deploy / rollback / migration / permission changes | out of PM scope | handoff role decides |
| shell/network bypass (curl, wget, ssh, ad-hoc scripts, browser automation) | **forbidden** | do not route around a blocked tool |

## Adapter mapping
Each runtime adapter maps logical capabilities to concrete tool names in `adapters/<runtime>/tool-mapping.json`. A tool whose effect cannot be classified as read-only is treated as write and must be blocked. The safest MVP is to **not expose** write capability at all, rather than instruct the agent not to use it.

## Config precedence
Core → Role → Product → Run contract. A lower layer may remove capabilities or add `never_persist` items, never re-enable `writes`/`sends` or lower a safety flag. `kit-cli.py config-check` fails closed on any violation or unknown key.
