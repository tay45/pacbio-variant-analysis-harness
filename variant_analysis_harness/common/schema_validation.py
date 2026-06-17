"""JSON Schema validation with a jsonschema primary implementation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from variant_analysis_harness.exceptions import ConfigError, ManifestError
from variant_analysis_harness.common.dependencies import load_required_dependency

SCHEMA_VERSION = "phase2a1.v1"


jsonschema = load_required_dependency("jsonschema", "jsonschema")


def validate_run_config_schema(config: dict[str, Any], schema_dir: Path | None = None) -> None:
    if config.get("schema_version") != SCHEMA_VERSION:
        raise ConfigError(f"schema_version must be {SCHEMA_VERSION!r}")
    schema = _load_schema("run_config.schema.json", schema_dir)
    _validate(config, schema, "run configuration")


def validate_execution_profile_schema(profile: dict[str, Any], schema_dir: Path | None = None) -> None:
    schema = _load_schema("execution_profile.schema.json", schema_dir)
    _validate(profile, schema, "execution profile")


def validate_manifest_row_schema(row: dict[str, Any], schema_dir: Path | None = None) -> None:
    schema = _load_schema("sample_manifest.schema.json", schema_dir)
    try:
        _validate(row, schema, "sample manifest row")
    except ConfigError as exc:
        raise ManifestError(str(exc)) from exc


def _load_schema(name: str, schema_dir: Path | None) -> dict[str, Any]:
    root = schema_dir or Path(__file__).resolve().parents[2] / "schemas"
    return _inline_local_refs(json.loads((root / name).read_text(encoding="utf-8")), root, seen={name})


def _validate(instance: dict[str, Any], schema: dict[str, Any], label: str) -> None:
    _reject_remote_refs(schema)
    schema = _inline_local_refs(schema, Path(__file__).resolve().parents[2] / "schemas", seen=set())
    try:
        validator = jsonschema.Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
        if errors:
            err = errors[0]
            path = ".".join(str(p) for p in err.absolute_path) or "<root>"
            raise ConfigError(f"Invalid {label} at {path}: {err.message}; value={err.instance!r}")
    except ConfigError:
        raise
    except Exception as exc:
        raise ConfigError(f"Schema validation failed for {label}: {exc}") from exc


def _fallback_validate_object(value: Any, schema: dict[str, Any], label: str, path: str) -> None:
    schema_type = schema.get("type")
    if schema_type == "object":
        if not isinstance(value, dict):
            raise ConfigError(f"Invalid {label} at {path}: expected object; value={value!r}")
        required = set(schema.get("required", []))
        missing = required - set(value)
        if missing:
            raise ConfigError(f"Invalid {label} at {path}: missing required keys {sorted(missing)}")
        if schema.get("additionalProperties") is False:
            allowed = set(schema.get("properties", {}))
            unknown = set(value) - allowed
            if unknown:
                raise ConfigError(f"Invalid {label} at {path}: unknown keys {sorted(unknown)}")
        for key, item in value.items():
            prop_schema = schema.get("properties", {}).get(key)
            if prop_schema:
                _fallback_validate_object(item, _resolve_ref(prop_schema), label, f"{path}.{key}")
            elif isinstance(schema.get("additionalProperties"), dict):
                _fallback_validate_object(item, schema["additionalProperties"], label, f"{path}.{key}")
        return
    if "const" in schema and value != schema["const"]:
        raise ConfigError(f"Invalid {label} at {path}: expected {schema['const']!r}; value={value!r}")
    if "enum" in schema and value not in schema["enum"]:
        raise ConfigError(f"Invalid {label} at {path}: expected one of {schema['enum']}; value={value!r}")
    allowed_types = schema_type if isinstance(schema_type, list) else [schema_type]
    if schema_type and not any(_is_type(value, t) for t in allowed_types):
        raise ConfigError(f"Invalid {label} at {path}: expected {schema_type}; value={value!r}")
    if isinstance(value, int) and "minimum" in schema and value < schema["minimum"]:
        raise ConfigError(f"Invalid {label} at {path}: must be >= {schema['minimum']}; value={value!r}")


def _resolve_ref(schema: dict[str, Any]) -> dict[str, Any]:
    # Minimal fallback: ref schemas are validated elsewhere by runtime code.
    if "$ref" in schema:
        return {"type": "object"}
    return schema


def _is_type(value: Any, type_name: str | None) -> bool:
    if type_name is None:
        return True
    if type_name == "object":
        return isinstance(value, dict)
    if type_name == "array":
        return isinstance(value, list)
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "null":
        return value is None
    return True


def _reject_remote_refs(schema: Any, path: str = "<root>") -> None:
    if isinstance(schema, dict):
        ref = schema.get("$ref")
        if isinstance(ref, str):
            if ref.startswith(("#/", "#")):
                pass
            elif "://" in ref or ref.startswith("//"):
                raise ConfigError(f"Remote schema references are not permitted at {path}: {ref}")
            elif not ref.endswith(".schema.json"):
                raise ConfigError(f"Unregistered local schema reference at {path}: {ref}")
        for key, value in schema.items():
            _reject_remote_refs(value, f"{path}.{key}")
    elif isinstance(schema, list):
        for i, item in enumerate(schema):
            _reject_remote_refs(item, f"{path}[{i}]")


def _inline_local_refs(schema: Any, schema_dir: Path, seen: set[str]) -> Any:
    if isinstance(schema, dict):
        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.endswith(".schema.json"):
            if ref in seen:
                return schema
            path = schema_dir / ref
            if not path.exists():
                raise ConfigError(f"Unresolved bundled local schema reference: {ref}")
            loaded = json.loads(path.read_text(encoding="utf-8"))
            return _inline_local_refs(loaded, schema_dir, seen | {ref})
        return {key: _inline_local_refs(value, schema_dir, seen) for key, value in schema.items()}
    if isinstance(schema, list):
        return [_inline_local_refs(item, schema_dir, seen) for item in schema]
    return schema
