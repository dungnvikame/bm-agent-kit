"""Shared helpers for Draft artifacts: base skeleton, human approval-record loading, payload hashing.

The agent never writes approval records; it only reads and verifies them (spec 7.1).
"""
import datetime as dt
import hashlib
import json
import re
import unicodedata
from pathlib import Path

from .json_validator import load_schema, validate

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "contracts" / "schemas"
REPO = Path(__file__).resolve().parents[2]
KIT_VERSION = "0.2.0-draft"
AGENT_TOKENS = {"agent", "bot", "claude", "codex", "gpt", "llm", "ai", "assistant", "automation", "system", "pipeline"}
# Cyrillic/Greek look-alikes -> Latin, so a Cyrillic capital A in "Agent" cannot dodge the approver check
_CONFUSABLES = str.maketrans("аеорсухіјАЕОРСХТНКМВІЅαοερτυνΑΕΟΡΤΗΚΜΒ", "aeopcyxijAEOPCXTHKMBISaoeptuvAEOPTHKMB")


def utc_now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(value):
    """ISO-8601 -> aware datetime, or None when unparseable."""
    try:
        d = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
    except (TypeError, ValueError):
        return None


def base(output_type, run_id, artifact_id, runtime, sources, gate="DEV.G1"):
    """Standard Draft envelope shared by every record type (spec 3 output.required_fields)."""
    return {
        "schema_version": "bm-agent-contract/0.2", "run_id": run_id, "artifact_id": artifact_id,
        "artifact_version": "0.1-draft", "output_type": output_type, "status": "draft", "requires_human_review": True,
        "human_owner": "Tom", "reviewer": "Tom", "kit_version": KIT_VERSION, "runtime": runtime, "created_at": utc_now(),
        "sources": sources, "facts": [], "inferences": [], "proposals": [], "open_questions": [],
        "gate_status": {gate: "not_started"}, "external_action": {"requested": False, "executed": False},
        "approval": {"approval_type": "artifact_only", "gate": gate, "approved_by": None, "approved_at": None,
                     "decision": "pending", "permits_external_write": False, "permits_send": False},
    }


def derive_id(upstream_id, old_suffix, new_suffix):
    mapped = upstream_id.replace(old_suffix, new_suffix)
    return mapped if mapped != upstream_id else f"{upstream_id}{new_suffix}"


def payload_hash(payload):
    """Canonical sha256 of a payload dict (sorted keys, no whitespace) — ties an action approval to exact content."""
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def looks_like_agent(name):
    folded = unicodedata.normalize("NFKC", str(name)).translate(_CONFUSABLES).lower()
    tokens = set(re.split(r"[^a-z0-9]+", folded)) - {""}
    return bool(tokens & AGENT_TOKENS)


def load_approval(path, expect_gate=None, expect_type=None, expect_artifact_id=None, expect_artifact_version=None, now=None):
    """Load + verify a human approval record. Returns (record_or_None, problems)."""
    problems = []
    try:
        rec = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, [f"approval record unreadable: {exc}"]
    problems += [f"approval schema: {e}" for e in validate(rec, load_schema(SCHEMA_DIR / "approval-record.schema.json"))]
    if problems:
        return None, problems
    now = now or dt.datetime.now(dt.timezone.utc)
    if rec["decision"] != "approved":
        problems.append(f"approval decision is {rec['decision']}, not approved")
    if looks_like_agent(rec["approver"]):
        problems.append("approver looks like an agent/automation, not a human")
    approved_at = parse_time(rec["approved_at"])
    if approved_at is None:
        problems.append("approved_at is not an ISO-8601 timestamp")
    elif approved_at > now + dt.timedelta(minutes=5):
        problems.append("approved_at is in the future")
    if rec.get("expires_at"):
        exp = parse_time(rec["expires_at"])
        if exp is None or exp <= now:
            problems.append("approval expired or expires_at unparseable")
    if expect_gate and rec["gate"] != expect_gate:
        problems.append(f"approval gate {rec['gate']} != required {expect_gate}")
    if expect_type and rec["approval_type"] != expect_type:
        problems.append(f"approval_type {rec['approval_type']} != required {expect_type}")
    if expect_artifact_id and rec["artifact_id"] != expect_artifact_id:
        problems.append(f"approval covers artifact {rec['artifact_id']}, not {expect_artifact_id}")
    if expect_artifact_version and rec["artifact_version"] != expect_artifact_version:
        problems.append(f"approval covers version {rec['artifact_version']}, not {expect_artifact_version}")
    if rec["approval_type"] == "action" and not (rec.get("payload_hash") and rec.get("operation") and rec.get("destination")):
        problems.append("action approval needs operation + destination + payload_hash")
    return (rec if not problems else None), problems


def approval_ref(rec):
    return {"gate": rec["gate"], "artifact_id": rec["artifact_id"], "artifact_version": rec["artifact_version"],
            "approver": rec["approver"], "approved_at": rec["approved_at"], "recorded_in": rec["recorded_in"]}


def repo_relative(path):
    p = Path(path).resolve()
    return str(p.relative_to(REPO)) if p.is_relative_to(REPO) else str(p)
