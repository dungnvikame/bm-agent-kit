"""Minimal JSON Schema (draft 2020-12 subset) validator — stdlib only.

Supports: type, required, properties, additionalProperties, enum, const,
items, minItems, minLength, pattern, $ref to sibling schema files.
Returns a list of human-readable error strings; empty list == valid.
"""
import json
import re
from pathlib import Path

SUPPORTED_KEYWORDS = {
    "$schema", "$id", "$ref", "title", "description", "type", "required", "properties",
    "additionalProperties", "enum", "const", "items", "minItems", "minLength", "pattern", "__dir__",
}

_TYPE_MAP = {
    "string": str, "integer": int, "number": (int, float), "boolean": bool,
    "null": type(None), "array": list, "object": dict,
}


def load_schema(path):
    path = Path(path)
    schema = json.loads(path.read_text(encoding="utf-8"))
    schema["__dir__"] = str(path.parent)
    return schema


def _resolve_ref(ref, schema_dir):
    return load_schema(Path(schema_dir) / ref)


def _same(a, b):
    """Equality that does NOT treat True==1 / False==0 as equal (JSON semantics)."""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    return a == b


def _type_ok(value, expected):
    if isinstance(expected, list):
        return any(_type_ok(value, t) for t in expected)
    py = _TYPE_MAP.get(expected)
    if py is None:
        return False
    if expected in ("integer", "number") and isinstance(value, bool):
        return False  # bool is a subclass of int in Python
    return isinstance(value, py)


def validate(instance, schema, path="$", schema_dir=None):
    """Validate instance against schema; returns list of error strings."""
    errors = []
    schema_dir = schema.get("__dir__", schema_dir)

    if "$ref" in schema:
        return validate(instance, _resolve_ref(schema["$ref"], schema_dir), path, schema_dir)

    unknown = set(schema) - SUPPORTED_KEYWORDS
    if unknown:
        errors.append(f"{path}: schema uses unsupported keywords {sorted(unknown)} (fail closed)")
        return errors

    if "const" in schema and not _same(instance, schema["const"]):
        errors.append(f"{path}: expected const {schema['const']!r}, got {instance!r}")
        return errors

    if "enum" in schema and not any(_same(instance, e) for e in schema["enum"]):
        errors.append(f"{path}: {instance!r} not in enum {schema['enum']}")
        return errors

    if "type" in schema and not _type_ok(instance, schema["type"]):
        errors.append(f"{path}: expected type {schema['type']}, got {type(instance).__name__}")
        return errors

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: shorter than minLength {schema['minLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(f"{path}: does not match pattern {schema['pattern']!r}")

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: fewer than minItems {schema['minItems']}")
        if "items" in schema:
            for i, item in enumerate(instance):
                errors += validate(item, schema["items"], f"{path}[{i}]", schema_dir)

    if isinstance(instance, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required property '{key}'")
        for key, value in instance.items():
            if key in props:
                errors += validate(value, props[key], f"{path}.{key}", schema_dir)
            else:
                extra = schema.get("additionalProperties", True)
                if extra is False:
                    errors.append(f"{path}: additional property '{key}' not allowed")
                elif isinstance(extra, dict):
                    errors += validate(value, extra, f"{path}.{key}", schema_dir)
    return errors


def validate_file(instance_path, schema_path):
    instance = json.loads(Path(instance_path).read_text(encoding="utf-8"))
    return validate(instance, load_schema(schema_path))
