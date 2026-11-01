"""output_type -> policy module. Single place used by kit-cli validate, evaluate-preprocess and tests."""
from . import breakdown_policy, evaluation_policy, intake_policy, mapping_policy, payload_policy

POLICIES = {
    "intake_record": intake_policy,
    "mapping_record": mapping_policy,
    "breakdown_record": breakdown_policy,
    "payload_preview_record": payload_policy,
    "evaluation_record": evaluation_policy,
}


def policy_for(record):
    """Return (output_type, policy_module_or_None)."""
    ot = record.get("output_type") if isinstance(record, dict) else None
    return ot, POLICIES.get(ot)


def check_any(record):
    """Return (output_type, violations). Unknown type is a violation (fail closed)."""
    ot, policy = policy_for(record)
    if policy is None:
        return ot, [f"unknown output_type {ot!r} (known: {sorted(POLICIES)})"]
    return ot, policy.check(record)
