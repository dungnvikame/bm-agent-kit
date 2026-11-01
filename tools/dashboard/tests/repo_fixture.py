"""Shared test helper: copy the parts of the repo the dashboard reads into a temp dir and point it there.

Tests never touch the real checkout. kitlib is still imported from the real core/ (code, not data).
"""
import shutil
import sys
import tempfile
from pathlib import Path

DASHBOARD = Path(__file__).resolve().parents[1]
REAL_REPO = DASHBOARD.parents[1]
sys.path.insert(0, str(DASHBOARD))

import editable_paths  # noqa: E402

COPY = [
    "core", "roles", "products", "adapters", "plans", "evaluations/fixtures", "evaluations/smoke",
    "AGENTS.md", "CLAUDE.md", ".claude/skills", ".agents/skills", ".codex",
]


def make_temp_repo():
    """Return (tmp_root, cleanup). Also sets the dashboard's repo root to tmp_root."""
    tmp = Path(tempfile.mkdtemp(prefix="bm-kit-dash-"))
    for rel in COPY:
        src, dst = REAL_REPO / rel, tmp / rel
        if src.is_dir():
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.local.json"))
        elif src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    (tmp / "runs" / "secret-run").mkdir(parents=True)
    (tmp / "runs" / "secret-run" / "intake.json").write_text('{"private": true}', encoding="utf-8")
    (tmp / "products" / "igoal" / "source-registry.local.json").write_text('{"url": "https://private.example"}', encoding="utf-8")
    previous = editable_paths.repo()
    editable_paths.set_repo(tmp)

    def cleanup():
        editable_paths.set_repo(previous)
        shutil.rmtree(tmp, ignore_errors=True)

    return tmp, cleanup
