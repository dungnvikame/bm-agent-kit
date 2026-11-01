"""Duplicate-candidate search over a local, read-only task snapshot (spec §4.2 step 4, §5.1 step 5).

Keyword overlap + product synonym groups. Reports its own search scope and never
claims exhaustiveness. Meaning-level judgement remains with the agent/human.
"""
import re
import unicodedata

STOPWORDS = {
    "và", "của", "là", "có", "cho", "khi", "ở", "để", "các", "một", "này", "đó", "thì", "được", "bị",
    "với", "trong", "ra", "lên", "không", "cần", "muốn", "rất", "hơn", "the", "a", "an", "and", "or",
    "of", "to", "in", "on", "for", "is", "are", "be", "it", "this", "that", "with", "as", "at", "by",
}
_TOKEN = re.compile(r"\w+", re.UNICODE)


def _normalize(text):
    return unicodedata.normalize("NFC", text or "").lower()


def tokenize(text, synonyms=None):
    """Lowercase word tokens; synonym terms are mapped to their group id (e.g. 'thu gọn' -> 'syn:collapse')."""
    text = _normalize(text)
    groups = set()
    if synonyms:
        for group, terms in synonyms.items():
            for term in terms:
                if _normalize(term) in text:
                    groups.add(f"syn:{group}")
    tokens = {t for t in _TOKEN.findall(text) if len(t) > 1 and t not in STOPWORDS}
    return tokens | groups


def find_candidates(query_text, tasks, synonyms=None, min_shared=2, min_jaccard=0.12, limit=5):
    """Return (candidates, scope). tasks: list of dicts with task_id,title,description,status,section,modified_at."""
    q = tokenize(query_text, synonyms)
    candidates = []
    for task in tasks:
        t = tokenize(f"{task.get('title', '')} {task.get('description', '')}", synonyms)
        shared = q & t
        if not shared:
            continue
        jaccard = len(shared) / len(q | t)
        if len(shared) >= min_shared and jaccard >= min_jaccard:
            candidates.append({
                "task_id": str(task.get("task_id")),
                "title": task.get("title", ""),
                "score": round(jaccard, 3),
                "matched_terms": sorted(shared),
                "status": task.get("status", "unknown"),
                "section": task.get("section", "unknown"),
                "modified_at": task.get("modified_at", "unknown"),
            })
    candidates.sort(key=lambda c: c["score"], reverse=True)
    scope = {
        "method": "keyword_overlap_with_synonyms" if synonyms else "keyword_overlap",
        "tasks_scanned": len(tasks),
        "exhaustive": False,
        "synonyms_used": bool(synonyms),
        "note": "Quick local search over the provided snapshot only; not a full backlog audit.",
    }
    return candidates[:limit], scope
