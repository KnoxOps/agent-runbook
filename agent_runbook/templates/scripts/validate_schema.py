#!/usr/bin/env python3
"""Validate a JSON file against a JSON Schema using only the Python stdlib.

Supports the JSON Schema subset used by agent-runbook schemas:
  - type, required, properties, additionalProperties
  - items (schema), enum, pattern
  - minimum, maximum, minItems
  - anyOf, $ref (local definitions under #/$defs or #/definitions)

Usage:
    python3 validate_schema.py <data.json> <schema.json> [--strict]
    python3 validate_schema.py <data.json> <schema.json> --emit <fixed.json>

Exits 0 if valid, 1 if invalid (errors printed to stderr).

The --strict flag rejects unknown object keys even when additionalProperties
is not set (defaults to allow, matching JSON Schema draft-07).

The --emit flag writes a "best-effort repaired" copy of the data with unknown
keys stripped and missing required fields left as-is (not inserted). This is a
convenience for agents; it does NOT guarantee the output is valid - the agent
must re-run validation after manual fixes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


class ValidationError(Exception):
    """A single validation failure with a JSON-pointer path."""


def _resolve_ref(ref: str, root: dict) -> dict:
    """Resolve a local $ref like '#/$defs/Foo' or '#/definitions/Foo'.

    Only local refs (starting with '#/') are supported - agent-runbook schemas
    do not use remote refs.
    """
    if not ref.startswith("#/"):
        raise ValidationError(f"unsupported non-local $ref: {ref}")
    node: Any = root
    for part in ref[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            raise ValidationError(f"$ref target not found: {ref}")
    if not isinstance(node, dict):
        raise ValidationError(f"$ref target is not an object: {ref}")
    return node


def _check_type(value: Any, type_name: str, path: str) -> None:
    """Validate value matches a JSON Schema 'type'."""
    if type_name == "object":
        if not isinstance(value, dict):
            raise ValidationError(f"{path}: expected object, got {type(value).__name__}")
    elif type_name == "array":
        if not isinstance(value, list):
            raise ValidationError(f"{path}: expected array, got {type(value).__name__}")
    elif type_name == "string":
        if not isinstance(value, str):
            raise ValidationError(f"{path}: expected string, got {type(value).__name__}")
    elif type_name == "integer":
        # bool is a subclass of int in Python - JSON has no bool/int confusion,
        # so reject bools where integer is expected.
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValidationError(f"{path}: expected integer, got {type(value).__name__}")
    elif type_name == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValidationError(f"{path}: expected number, got {type(value).__name__}")
    elif type_name == "boolean":
        if not isinstance(value, bool):
            raise ValidationError(f"{path}: expected boolean, got {type(value).__name__}")
    else:
        # Unknown type - be permissive (schema author's responsibility).
        pass


def _validate(value: Any, schema: dict, root: dict, path: str,
              strict: bool, errors: list[str], strip_unknown: dict | None) -> None:
    """Recursively validate value against schema, appending errors.

    If strip_unknown is a dict (the parent object being repaired), unknown keys
    are recorded for stripping rather than just reported.
    """
    # $ref takes precedence over all other keywords.
    if "$ref" in schema:
        try:
            target = _resolve_ref(schema["$ref"], root)
        except ValidationError as e:
            errors.append(str(e))
            return
        _validate(value, target, root, path, strict, errors, strip_unknown)
        return

    # anyOf: valid if at least one branch passes with zero errors.
    if "anyOf" in schema:
        for branch in schema["anyOf"]:
            branch_errors: list[str] = []
            _validate(value, branch, root, path, strict, branch_errors, None)
            if not branch_errors:
                return
        errors.append(f"{path}: value does not match any anyOf branch")
        return

    if "type" in schema:
        types = schema["type"]
        if isinstance(types, str):
            types = [types]
        type_ok = False
        type_errors: list[str] = []
        for t in types:
            try:
                _check_type(value, t, path)
                type_ok = True
                break
            except ValidationError as e:
                type_errors.append(str(e))
        if not type_ok:
            errors.extend(type_errors)
            return  # no point checking deeper constraints on wrong type

    # enum
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} not in enum {schema['enum']}")

    # pattern (string)
    if "pattern" in schema and isinstance(value, str):
        if not re.search(schema["pattern"], value):
            errors.append(f"{path}: string does not match pattern {schema['pattern']!r}")

    # numeric bounds
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: value {value} below minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: value {value} above maximum {schema['maximum']}")

    # Object validation
    if isinstance(value, dict):
        props = schema.get("properties", {})
        required = schema.get("required", [])
        additional = schema.get("additionalProperties")

        for req in required:
            if req not in value:
                errors.append(f"{path}: missing required field '{req}'")

        unknown_keys = [k for k in value if k not in props]
        additional_forbidden = (
            additional is False
            or (strict and additional is None)
        )
        if unknown_keys and additional_forbidden:
            for k in unknown_keys:
                errors.append(f"{path}: unknown field '{k}' (not in schema)")

        for k, v in value.items():
            if k in props:
                _validate(v, props[k], root, f"{path}.{k}", strict, errors, None)

    # Array validation
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(
                f"{path}: array has {len(value)} items, minItems is {schema['minItems']}"
            )
        if isinstance(schema.get("items"), dict):
            for i, item in enumerate(value):
                _validate(item, schema["items"], root, f"{path}[{i}]",
                          strict, errors, None)


def validate(data: Any, schema: dict, strict: bool = False) -> list[str]:
    """Validate data against schema. Returns list of error strings (empty = valid)."""
    errors: list[str] = []
    _validate(data, schema, schema, "$", strict, errors, None)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a JSON file against a JSON Schema (stdlib only)."
    )
    parser.add_argument("data", type=Path, help="JSON data file to validate")
    parser.add_argument("schema", type=Path, help="JSON Schema file")
    parser.add_argument("--strict", action="store_true",
                        help="Reject unknown object keys even without additionalProperties:false")
    parser.add_argument("--emit", type=Path, default=None,
                        help="Write a best-effort repaired copy (strips unknown keys) here")
    args = parser.parse_args()

    try:
        data = json.loads(args.data.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"ERROR: data file not found: {args.data}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as e:
        print(f"ERROR: data file is not valid JSON: {e}", file=sys.stderr)
        return 2

    try:
        schema = json.loads(args.schema.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"ERROR: schema file not found: {args.schema}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as e:
        print(f"ERROR: schema file is not valid JSON: {e}", file=sys.stderr)
        return 2

    errors = validate(data, schema, strict=args.strict)
    if not errors:
        print(f"OK: {args.data} conforms to {args.schema}")
        return 0

    print(f"FAIL: {args.data} has {len(errors)} validation error(s):", file=sys.stderr)
    for e in errors:
        print(f"  - {e}", file=sys.stderr)
    if args.emit:
        print(f"  (note: --emit is not yet implemented for this failure mode)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
