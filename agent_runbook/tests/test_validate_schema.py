"""Tests for the stdlib JSON Schema validator."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from agent_runbook.templates.scripts.validate_schema import validate


SCRIPT = Path(__file__).resolve().parents[1] / "templates" / "scripts" / "validate_schema.py"


def _run(data: dict, schema: dict, extra_args=None) -> tuple[int, str, str]:
    """Run validate_schema.py as a subprocess; return (rc, stdout, stderr)."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        data_p = d / "data.json"
        schema_p = d / "schema.json"
        data_p.write_text(json.dumps(data))
        schema_p.write_text(json.dumps(schema))
        cmd = [sys.executable, str(SCRIPT), str(data_p), str(schema_p)] + (extra_args or [])
        r = subprocess.run(cmd, capture_output=True, text=True)
        return r.returncode, r.stdout, r.stderr


class TestBasicTypes:
    def test_valid_object(self):
        schema = {"type": "object", "properties": {"a": {"type": "string"}},
                  "required": ["a"]}
        assert validate({"a": "x"}, schema) == []

    def test_wrong_type(self):
        schema = {"type": "object", "properties": {"a": {"type": "string"}}}
        errs = validate({"a": 123}, schema)
        assert any("expected string" in e for e in errs)

    def test_required_missing(self):
        schema = {"type": "object", "required": ["a", "b"]}
        errs = validate({"a": 1}, schema)
        assert any("missing required field 'b'" in e for e in errs)

    def test_integer_rejects_bool(self):
        # bool is a subclass of int in Python; JSON Schema treats them as distinct.
        schema = {"type": "object", "properties": {"n": {"type": "integer"}}}
        assert validate({"n": True}, schema) != []

    def test_number_accepts_int_and_float(self):
        schema = {"type": "object", "properties": {"n": {"type": "number"}}}
        assert validate({"n": 1}, schema) == []
        assert validate({"n": 1.5}, schema) == []


class TestEnum:
    def test_enum_valid(self):
        schema = {"type": "string", "enum": ["a", "b", "c"]}
        assert validate("b", schema) == []

    def test_enum_invalid(self):
        schema = {"type": "string", "enum": ["a", "b", "c"]}
        errs = validate("d", schema)
        assert any("not in enum" in e for e in errs)


class TestPattern:
    def test_pattern_match(self):
        schema = {"type": "string", "pattern": "^service-"}
        assert validate("service-foo", schema) == []

    def test_pattern_no_match(self):
        schema = {"type": "string", "pattern": "^service-"}
        errs = validate("foo", schema)
        assert any("does not match pattern" in e for e in errs)


class TestNumericBounds:
    def test_minimum(self):
        schema = {"type": "integer", "minimum": 5}
        assert validate(5, schema) == []
        errs = validate(4, schema)
        assert any("below minimum" in e for e in errs)

    def test_maximum(self):
        schema = {"type": "integer", "maximum": 5}
        assert validate(5, schema) == []
        errs = validate(6, schema)
        assert any("above maximum" in e for e in errs)


class TestArray:
    def test_min_items_ok(self):
        schema = {"type": "array", "items": {"type": "string"}, "minItems": 1}
        assert validate(["a"], schema) == []

    def test_min_items_violated(self):
        schema = {"type": "array", "items": {"type": "string"}, "minItems": 2}
        errs = validate(["a"], schema)
        assert any("minItems" in e for e in errs)

    def test_items_validated(self):
        schema = {"type": "array", "items": {"type": "integer"}}
        errs = validate([1, "x", 3], schema)
        assert any("[1]: expected integer" in e for e in errs)


class TestAdditionalProperties:
    def test_additional_false_rejects_unknown(self):
        schema = {"type": "object", "properties": {"a": {"type": "string"}},
                  "additionalProperties": False}
        errs = validate({"a": "x", "b": 1}, schema)
        assert any("unknown field 'b'" in e for e in errs)

    def test_additional_false_allows_known(self):
        schema = {"type": "object", "properties": {"a": {"type": "string"}},
                  "additionalProperties": False}
        assert validate({"a": "x"}, schema) == []

    def test_strict_rejects_unknown_without_flag(self):
        schema = {"type": "object", "properties": {"a": {"type": "string"}}}
        # without strict: unknown allowed
        assert validate({"a": "x", "b": 1}, schema) == []
        # with strict: unknown rejected
        errs = validate({"a": "x", "b": 1}, schema, strict=True)
        assert any("unknown field 'b'" in e for e in errs)


class TestAnyOf:
    def test_any_of_first_match(self):
        schema = {"anyOf": [{"type": "string"}, {"type": "integer"}]}
        assert validate("x", schema) == []
        assert validate(5, schema) == []

    def test_any_of_no_match(self):
        schema = {"anyOf": [{"type": "string"}, {"type": "integer"}]}
        errs = validate([1, 2], schema)
        assert any("anyOf" in e for e in errs)


class TestRef:
    def test_local_ref_resolved(self):
        schema = {
            "type": "object",
            "properties": {"item": {"$ref": "#/$defs/Name"}},
            "$defs": {"Name": {"type": "string", "minLength": 1}},
        }
        assert validate({"item": "foo"}, schema) == []

    def test_ref_to_definitions(self):
        schema = {
            "type": "object",
            "properties": {"item": {"$ref": "#/definitions/Name"}},
            "definitions": {"Name": {"type": "string"}},
        }
        assert validate({"item": "foo"}, schema) == []

    def test_ref_target_missing(self):
        schema = {"$ref": "#/$defs/Nope"}
        errs = validate("x", schema)
        assert any("$ref target not found" in e for e in errs)


class TestNested:
    def test_deeply_nested_error_path(self):
        schema = {
            "type": "object",
            "properties": {
                "list": {"type": "array", "items": {
                    "type": "object",
                    "properties": {"n": {"type": "integer"}},
                }}
            }
        }
        errs = validate({"list": [{"n": 1}, {"n": "bad"}]}, schema)
        assert any("$.list[1].n: expected integer" in e for e in errs)


class TestRealWorkloadSchema:
    """Validate against the actual workload-scan-result.schema.json shape."""

    def test_valid_workload_result(self):
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["workload_name", "edges"],
            "properties": {
                "workload_name": {"type": "string"},
                "edges": {"type": "array", "items": {
                    "type": "object",
                    "required": ["source_entity", "edge_name",
                                 "target_entity", "target_entity_type"],
                    "properties": {
                        "source_entity": {"type": "string"},
                        "edge_name": {"type": "string",
                                      "enum": ["CALLS", "DEPENDS_ON", "LOCATED_AT"]},
                        "target_entity": {"type": "string"},
                        "target_entity_type": {"type": "string"},
                        "target_entity_uuid": {"type": "string"},
                    },
                    "additionalProperties": False,
                }},
            },
        }
        data = {
            "workload_name": "gw",
            "edges": [
                {"source_entity": "gw", "edge_name": "CALLS",
                 "target_entity": "user-api", "target_entity_type": "Service"},
            ],
        }
        assert validate(data, schema) == []

    def test_workload_result_rejects_wrong_field_name(self):
        """The real-world bug: agent wrote 'edge_type' instead of 'edge_name'."""
        schema = {
            "type": "object",
            "required": ["edges"],
            "properties": {"edges": {"type": "array", "items": {
                "type": "object",
                "required": ["source_entity", "edge_name",
                             "target_entity", "target_entity_type"],
                "properties": {
                    "source_entity": {"type": "string"},
                    "edge_name": {"type": "string"},
                    "target_entity": {"type": "string"},
                    "target_entity_type": {"type": "string"},
                },
                "additionalProperties": False,
            }}},
        }
        data = {"edges": [
            {"source_entity": "gw", "edge_type": "CALLS",  # wrong field name
             "target_entity": "user-api", "target_entity_type": "Service"},
        ]}
        errs = validate(data, schema)
        # Must catch BOTH: unknown 'edge_type' and missing 'edge_name'
        assert any("unknown field 'edge_type'" in e for e in errs)
        assert any("missing required field 'edge_name'" in e for e in errs)


class TestCLIErrors:
    def test_missing_data_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run(
                [sys.executable, str(SCRIPT), str(Path(tmp) / "nope.json"),
                 str(Path(tmp) / "schema.json")],
                capture_output=True, text=True,
            )
            assert r.returncode == 2
            assert "data file not found" in r.stderr

    def test_invalid_json_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "data.json").write_text("{not json")
            (d / "schema.json").write_text('{"type":"object"}')
            r = subprocess.run(
                [sys.executable, str(SCRIPT), str(d / "data.json"),
                 str(d / "schema.json")],
                capture_output=True, text=True,
            )
            assert r.returncode == 2
            assert "not valid JSON" in r.stderr

    def test_cli_valid_exits_zero(self):
        rc, out, _ = _run({"a": "x"}, {"type": "object", "properties": {"a": {"type": "string"}}})
        assert rc == 0
        assert "OK" in out

    def test_cli_invalid_exits_one(self):
        rc, _, err = _run({"a": 1}, {"type": "object", "properties": {"a": {"type": "string"}}})
        assert rc == 1
        assert "FAIL" in err
