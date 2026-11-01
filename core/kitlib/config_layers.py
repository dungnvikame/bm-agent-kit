"""Effective-config composer with fail-closed narrowing rules (spec §2, §3, tool-policy).

Order: core -> role -> product -> run. A lower layer may only narrow:
- locked keys (safety.*, output.status, tools closed flags, approval/communication booleans)
  must be ABSENT or EXACTLY equal to the upper value (any other value/type/null = violation)
- subset-only lists (tools.capabilities, scope.allowed, gates.agent_may_set) can't add items
- grow-only lists (privacy.never_persist, output.required_fields, scope.handoff_only,
  approval.create_development_tasks_requires) can't drop items
Unknown top-level keys, unknown sub-keys in governed sections, non-object sections,
or a wrong layer order -> violation (fail closed).
"""
import copy

LAYER_ORDER = ["core", "role", "product", "run"]
KNOWN_KEYS = {
    "schema_version", "layer", "config_version", "extends", "agent", "role", "product", "owner",
    "reviewer", "language", "scope", "safety", "tools", "approval", "communication", "privacy",
    "knowledge", "output", "evaluation", "gates", "skills", "run_id", "notes",
}
GOVERNED_SUBKEYS = {
    "safety": {"trust_mode", "human_gate_required", "mode"},
    "tools": {"default", "reads", "writes", "sends", "shell_network_bypass", "local_drafts",
              "sensitive_content_persistence", "capabilities"},
    "approval": {"artifact_approval_is_execution_approval", "downstream_requires",
                 "create_development_tasks_requires", "content_change_invalidates_action_approval",
                 "changed_source_requires_gate_revalidation"},
    "communication": {"auto_send", "auto_mention_bod", "draft_to_sponsor_requires_tom_approval",
                      "escalate_to_nghia_requires_instruction"},
    "privacy": {"never_persist", "redacted_note"},
    "output": {"status", "requires_human_review", "required_fields"},
    "gates": {"namespaces", "agent_may_set"},
    "scope": {"level", "allowed", "handoff_only"},
}
LOCKED = {
    ("safety", "mode"), ("safety", "trust_mode"), ("safety", "human_gate_required"),
    ("output", "status"), ("output", "requires_human_review"),
    ("tools", "default"), ("tools", "reads"), ("tools", "writes"), ("tools", "sends"),
    ("tools", "shell_network_bypass"), ("tools", "sensitive_content_persistence"),
    ("approval", "artifact_approval_is_execution_approval"), ("approval", "downstream_requires"),
    ("approval", "content_change_invalidates_action_approval"), ("approval", "changed_source_requires_gate_revalidation"),
    ("communication", "auto_send"), ("communication", "auto_mention_bod"),
    ("communication", "draft_to_sponsor_requires_tom_approval"), ("communication", "escalate_to_nghia_requires_instruction"),
    ("privacy", "redacted_note"), ("gates", "namespaces"),
}
SUBSET_ONLY = {("tools", "capabilities"), ("scope", "allowed"), ("gates", "agent_may_set")}
GROW_ONLY = {("privacy", "never_persist"), ("output", "required_fields"), ("scope", "handoff_only"),
             ("approval", "create_development_tasks_requires")}
INTERSECT_KEYS = {"capabilities", "allowed", "agent_may_set"}
_MISSING = object()


def _get(d, section, key):
    sec = d.get(section, _MISSING)
    if sec is _MISSING or not isinstance(sec, dict):
        return _MISSING
    return sec.get(key, _MISSING)


def _as_list(value):
    return list(value) if isinstance(value, (list, tuple, set)) else None


def check_layer(upper, lower, violations):
    name = lower.get("layer", "?")
    for key in lower:
        if key not in KNOWN_KEYS:
            violations.append(f"[{name}] unknown top-level key '{key}' (fail closed)")
    for section, allowed in GOVERNED_SUBKEYS.items():
        if section in lower:
            if not isinstance(lower[section], dict):
                violations.append(f"[{name}] section '{section}' must be an object, got {type(lower[section]).__name__}")
                continue
            for sub in lower[section]:
                if sub not in allowed:
                    violations.append(f"[{name}] unknown key '{section}.{sub}' (fail closed)")
    if lower.get("schema_version") != upper.get("schema_version"):
        violations.append(f"[{name}] schema_version mismatch with upper layer")
    for section, key in LOCKED:
        lo, up = _get(lower, section, key), _get(upper, section, key)
        if lo is _MISSING:
            continue
        if up is _MISSING or lo != up or type(lo) is not type(up):
            violations.append(f"[{name}] {section}.{key} is locked by the upper layer ({up!r} -> {lo!r})")
    for section, key in SUBSET_ONLY:
        up, lo = _as_list(_get(upper, section, key)), _get(lower, section, key)
        if lo is _MISSING:
            continue
        lo_list = _as_list(lo)
        if lo_list is None:
            violations.append(f"[{name}] {section}.{key} must be a list")
        elif up is not None and set(lo_list) - set(up):
            violations.append(f"[{name}] {section}.{key} adds items not in upper layer: {sorted(set(lo_list) - set(up))}")
    for section, key in GROW_ONLY:
        up, lo = _as_list(_get(upper, section, key)), _get(lower, section, key)
        if lo is _MISSING:
            continue
        lo_list = _as_list(lo)
        if lo_list is None:
            violations.append(f"[{name}] {section}.{key} must be a list")
        elif up is not None and set(up) - set(lo_list):
            violations.append(f"[{name}] {section}.{key} drops required items: {sorted(set(up) - set(lo_list))}")


def _merge(base, over):
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        elif isinstance(v, list) and isinstance(out.get(k), list) and k in INTERSECT_KEYS:
            out[k] = [x for x in out[k] if x in v]  # intersection keeps upper order
        else:
            out[k] = copy.deepcopy(v)
    return out


def compose(layers):
    """layers: list of dicts in order. Returns (effective_config, violations)."""
    violations = []
    if not layers or not all(isinstance(l, dict) for l in layers):
        return {}, ["layers must be a non-empty list of objects"]
    expected = LAYER_ORDER[: len(layers)]
    actual = [l.get("layer") for l in layers]
    if actual != expected:
        violations.append(f"layer order must be {expected}, got {actual}")
    effective = copy.deepcopy(layers[0])
    for i in range(1, len(layers)):
        check_layer(effective, layers[i], violations)
        if not violations:
            effective = _merge(effective, layers[i])
    effective["layer"] = "effective"
    effective["layers_applied"] = actual
    return effective, violations
