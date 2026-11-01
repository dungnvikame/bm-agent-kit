# intake-feedback — reference

## Classification rules (category_proposed)
| Category | Use when | Never when |
|---|---|---|
| `bug` | a documented rule/AC exists AND behaviour is reproduced (`reproducible: yes`) | only "lỗi" is claimed without rule or reproduction |
| `usability` | works as specified but hard to perceive/operate (hierarchy, labels, discoverability) | — |
| `feature` | reporter asks for behaviour no requirement covers in sources read | you have not searched requirements |
| `question` | reporter asks how/why; answerable from docs | — |
| `data` | numbers/records look wrong; needs definition + period check | you'd have to guess the formula |
| `permission` | visibility/access complaint; needs the official permission decision (S8/S9 conflict → ask) | you'd self-grant or infer the rule |
| `possible_incident` | signals of outage, data loss, many users affected | you can't verify; still never state severity as fact |
| `unknown` | not enough context | — |

## Essential-question checklist (add as open_questions when unknown)
1. Which screen/flow (write vs read view)? 2. Which build/version/date? 3. Device/viewport? 4. Steps to reproduce? 5. How many users / which roles affected? 6. What exactly was expected vs observed? 7. Is there a related requirement/decision ID? 8. Is this reporter the decision owner for the module?

## Severity basis (proposal only)
State the observable basis: affected roles × frequency × workaround × data risk. Without evidence → `unknown`. Feedback sheet "Cao/Thấp" is the reporter's label (`feedback.source_priority_label`), not severity.

## Duplicate search scope statement
Always record `method`, `snapshot`, `tasks_scanned`, `exhaustive: false`. Search synonyms (`products/igoal/search-synonyms.json`): e.g. collapse ↔ thu gọn ↔ mở rộng ↔ expand. A quick search never proves the backlog has no match.

## Worked example (synthetic, E04 pattern)
Feedback with two ideas: (A) hierarchy labels hard to distinguish, (B) wants collapse at top level. → two parts. A: `usability`, candidate task found in snapshot → propose `review_existing`, ask for build/QA evidence. B: no candidate → `feature`, `hold_for_shape`; approval of A never covers B. Reporter's "Cao" stays a label; severity `unknown` until impact is known.
