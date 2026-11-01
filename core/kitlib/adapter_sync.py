"""Copy canonical skill/instruction files into runtime adapter locations and verify hashes (spec §11).

Manifest: adapters/sync-manifest.json -> {"entries": [{"source": path, "targets": [paths]}]}.
A source may be a file or a directory (copied recursively). check() walks BOTH directions so an
extra file planted in a target directory is reported too.
"""
import hashlib
import json
import shutil
from pathlib import Path

_IGNORE = ("__pycache__", ".pyc")


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _files_under(root):
    root = Path(root)
    if root.is_file():
        return {Path(""): root}
    return {p.relative_to(root): p for p in root.rglob("*")
            if p.is_file() and not any(x in str(p) for x in _IGNORE)}


def load_manifest(repo_root):
    return json.loads((Path(repo_root) / "adapters" / "sync-manifest.json").read_text(encoding="utf-8"))


def check(repo_root):
    """Return list of mismatch strings (empty == every target mirrors its source exactly)."""
    repo_root = Path(repo_root)
    problems = []
    for entry in load_manifest(repo_root)["entries"]:
        src = repo_root / entry["source"]
        if not src.exists():
            problems.append(f"missing source {entry['source']}")
            continue
        src_files = _files_under(src)
        for target in entry["targets"]:
            dst = repo_root / target
            if not dst.exists():
                problems.append(f"missing target {target}")
                continue
            dst_files = _files_under(dst)
            for rel, sf in src_files.items():
                tf = dst_files.get(rel)
                if tf is None:
                    problems.append(f"missing target file {target}/{rel}")
                elif _sha256(sf) != _sha256(tf):
                    problems.append(f"hash mismatch {target}/{rel} != {entry['source']}/{rel}")
            for rel in set(dst_files) - set(src_files):
                problems.append(f"unexpected extra file in target {target}/{rel}")
    return problems


def write(repo_root):
    """Copy every source to its targets (targets are replaced). Returns list of written paths."""
    repo_root = Path(repo_root)
    written = []
    for entry in load_manifest(repo_root)["entries"]:
        src = repo_root / entry["source"]
        for target in entry["targets"]:
            dst = repo_root / target
            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            written.append(str(dst.relative_to(repo_root)))
    return written
