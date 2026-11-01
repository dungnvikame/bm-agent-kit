"""Which repo files the dashboard may read or edit. Anything not listed is refused (fail closed).

- EDITABLE: canonical sources Tom may change from the UI.
- READ_ONLY: shown with a note, never written.
- PRIVATE: never read, never listed (gitignored local data).
Generated copies (AGENTS.md, CLAUDE.md, .claude/, .agents/, .codex/) are only touched via adapter_sync.
"""
import fnmatch
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def repo():
    """Repo root; tests may point it at a temporary copy with set_repo()."""
    return _REPO


def set_repo(path):
    global _REPO
    _REPO = Path(path).resolve()

LAYER_FILES = [
    "core/contracts/core-contract.json",
    "roles/pm/pm-role-contract.json",
    "products/igoal/igoal-product-contract.json",
]
CONTRACT_FILES = LAYER_FILES[1:]  # editable JSON contracts (core is read-only)

EDITABLE = [
    "roles/pm/pm-role-contract.json",
    "products/igoal/igoal-product-contract.json",
    "core/agent-instructions.md",
    "core/policies/*.md",
    "roles/pm/skills/*/SKILL.md",
    "roles/pm/skills/*/references/*.md",
]
READ_ONLY = {
    "core/contracts/core-contract.json": "Core changes need Kit owner review",
}
PRIVATE = [
    "runs/*", "products/*/source-registry.local.json", "*.local.json", ".env", ".env.*",
    "pm-agent-config-v0.2.0-review.md", ".git/*", ".claude/agent-memory/*",
]
SYNC_TRIGGERS = ("roles/pm/skills/", "core/agent-instructions.md")


def resolve(rel):
    """Return absolute Path for a repo-relative string; refuse anything that escapes the repo."""
    if not isinstance(rel, str) or not rel or rel.startswith(("/", "~")) or "\\" in rel:
        raise PermissionError(f"invalid path: {rel!r}")
    p = (repo() / rel).resolve()
    if not p.is_relative_to(repo()):
        raise PermissionError(f"path escapes repository: {rel}")
    return p


def relative(path):
    return Path(path).resolve().relative_to(repo()).as_posix()


def is_private(rel):
    return any(fnmatch.fnmatch(rel, pat) for pat in PRIVATE)


def classify(rel):
    """Return (kind, note) with kind in editable | read_only | denied."""
    if is_private(rel):
        return "denied", "private local file; the dashboard never reads it"
    if rel in READ_ONLY:
        return "read_only", READ_ONLY[rel]
    if any(fnmatch.fnmatch(rel, pat) for pat in EDITABLE):
        return "editable", ""
    return "denied", "not an editable canonical file (generated copies, .git and files outside the allowlist are refused)"


def needs_sync(rel):
    return rel.startswith(SYNC_TRIGGERS[0]) or rel == SYNC_TRIGGERS[1]


def viewable_files():
    """All files the editor may open, with their kind and note."""
    out = []
    for pattern in EDITABLE:
        for p in sorted(repo().glob(pattern)):
            if p.is_file():
                out.append({"path": relative(p), "kind": "editable", "note": "", "sync": needs_sync(relative(p))})
    for rel, note in READ_ONLY.items():
        if (repo() / rel).is_file():
            out.append({"path": rel, "kind": "read_only", "note": note, "sync": False})
    return out
