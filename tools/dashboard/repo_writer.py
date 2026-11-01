"""Guarded save path for the dashboard: allowlist -> JSON check -> compose (fail closed) -> write -> adapter sync."""
import json

from editable_paths import LAYER_FILES, classify, needs_sync, repo, resolve
from repo_reader import load_layers, read_json, read_text
from kitlib import adapter_sync, config_layers  # noqa: E402  (sys.path set by repo_reader)


class SaveRefused(Exception):
    """Raised when the save must not happen; .details carries the violation list."""

    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details or []


def _normalise_json(text):
    try:
        obj = json.loads(text)
    except ValueError as exc:
        raise SaveRefused(f"invalid JSON: {exc}")
    if not isinstance(obj, dict):
        raise SaveRefused("contract must be a JSON object")
    return obj, json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def check_compose(rel=None, obj=None):
    """Compose Core -> Role -> Product with an in-memory override; return violations."""
    override = {rel: obj} if rel in LAYER_FILES and obj is not None else None
    _, violations = config_layers.compose(load_layers(override))
    return violations


def save_text(rel, text):
    """Save a canonical file. Returns a result dict; raises SaveRefused / PermissionError on refusal."""
    kind, note = classify(rel)
    if kind != "editable":
        raise PermissionError(note or f"{rel} is not editable")
    path = resolve(rel)
    if not path.is_file():
        raise PermissionError(f"{rel} does not exist; the dashboard does not create files")
    obj = None
    if rel.endswith(".json"):
        obj, text = _normalise_json(text)
    if not isinstance(text, str):
        raise SaveRefused("text must be a string")
    violations = check_compose(rel, obj)
    if violations:
        raise SaveRefused("save refused: effective config would violate layer rules", violations)
    unchanged = (obj == read_json(rel)) if obj is not None else (text == read_text(rel))
    if unchanged:
        return {"saved": False, "path": rel, "message": "no change", "sync": None}
    path.write_text(text, encoding="utf-8")
    result = {"saved": True, "path": rel, "message": "saved", "sync": None}
    if needs_sync(rel):
        written = adapter_sync.write(repo())
        result["sync"] = {"written": written, "problems": adapter_sync.check(repo())}
    return result


def save_json(rel, obj):
    if not isinstance(obj, dict):
        raise SaveRefused("contract must be a JSON object")
    return save_text(rel, json.dumps(obj, ensure_ascii=False, indent=2))
