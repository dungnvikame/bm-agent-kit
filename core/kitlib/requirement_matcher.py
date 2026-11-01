"""Requirement candidate search + decision-conflict detection over a local requirements snapshot (spec §5.2 steps 1, 4, 6).

Keyword overlap with synonyms (reuses duplicate_finder.tokenize); module filter when known.
Each candidate gets a decision_status: live | superseded | inactive | unknown_ref | none.
Conflict: >=2 LIVE decisions in one domain among the candidates (supersedes chains walked
transitively; rejected/superseded/withdrawn decisions are inactive) -> blocked decision.
"""
from .duplicate_finder import tokenize

INACTIVE_STATUSES = {"rejected", "superseded", "withdrawn", "retired"}


def find_requirement_candidates(query_text, requirements, synonyms=None, module=None, min_shared=2, min_jaccard=0.12, limit=5):
    q = tokenize(query_text, synonyms)
    out = []
    for req in requirements:
        if module and module != "unknown" and req.get("module") not in (module, "unknown", None):
            continue
        text = " ".join([req.get("title", ""), req.get("scope", ""), " ".join(req.get("acceptance_criteria", []))])
        t = tokenize(text, synonyms)
        shared = q & t
        if not shared:
            continue
        jaccard = len(shared) / len(q | t)
        if len(shared) >= min_shared and jaccard >= min_jaccard:
            out.append({
                "requirement_id": req["requirement_id"], "title": req.get("title", ""), "score": round(jaccard, 3),
                "matched_terms": sorted(shared), "approval_status": req.get("approval_status", "unknown"),
                "domain": req.get("domain", "unknown"), "decision_ref": req.get("decision_ref"), "module": req.get("module", "unknown"),
            })
    out.sort(key=lambda c: c["score"], reverse=True)
    return out[:limit]


def _superseded_ids(decisions):
    """All decision ids superseded by any other decision, following chains transitively."""
    by_id = {d["decision_id"]: d for d in decisions}
    superseded = set()
    for d in decisions:
        seen, cur = set(), d.get("supersedes")
        while cur and cur not in seen:
            seen.add(cur)
            superseded.add(cur)
            cur = by_id.get(cur, {}).get("supersedes")
    return superseded


def annotate_decision_status(candidates, decisions):
    """Set candidate['decision_status'] in place; returns list of unknown decision refs (blockers for the caller)."""
    by_id = {d["decision_id"]: d for d in decisions}
    superseded = _superseded_ids(decisions)
    unknown_refs = []
    for c in candidates:
        ref = c.get("decision_ref")
        if not ref:
            c["decision_status"] = "none"
        elif ref not in by_id:
            c["decision_status"] = "unknown_ref"
            unknown_refs.append(ref)
        elif ref in superseded:
            c["decision_status"] = "superseded"
        elif str(by_id[ref].get("status", "")).lower() in INACTIVE_STATUSES:
            c["decision_status"] = "inactive"
        else:
            c["decision_status"] = "live"
    return sorted(set(unknown_refs))


def detect_conflict(candidates, decisions):
    """Return conflict dict or None. Requires annotate_decision_status() semantics (applied here if missing)."""
    if any("decision_status" not in c for c in candidates):
        annotate_decision_status(candidates, decisions)
    by_id = {d["decision_id"]: d for d in decisions}
    by_domain = {}
    for c in candidates:
        if c.get("decision_status") == "live":
            domain = by_id[c["decision_ref"]].get("domain", c.get("domain", "unknown"))
            by_domain.setdefault(domain, set()).add(c["decision_ref"])
    for domain, ids in sorted(by_domain.items()):
        if len(ids) >= 2:
            live = sorted(ids)
            return {
                "domain": domain, "decision_ids": live, "blocked_decisions": [domain],
                "summary": f"{len(live)} live decisions in domain '{domain}' with no supersedes chain; owner must choose before mapping is official.",
            }
    return None
