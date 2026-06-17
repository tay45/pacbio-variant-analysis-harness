"""Testing-only schema fallback for minimal no-network test environments."""

from __future__ import annotations

from typing import Any

from variant_analysis_harness.exceptions import ConfigError


def validate_object(instance: dict[str, Any], schema: dict[str, Any], label: str) -> None:
    _validate(instance, schema, label, "<root>", root=schema)


def _validate(value: Any, schema: dict[str, Any], label: str, path: str, root: dict[str, Any]) -> None:
    if "$ref" in schema:
        schema = _resolve_ref(schema["$ref"], root)
    schema_type = schema.get("type")
    if schema_type == "object":
        if not isinstance(value, dict):
            raise ConfigError(f"Invalid {label} at {path}: expected object; value={value!r}")
        missing = set(schema.get("required", [])) - set(value)
        if missing:
            raise ConfigError(f"Invalid {label} at {path}: missing required keys {sorted(missing)}")
        if schema.get("additionalProperties") is False:
            unknown = set(value) - set(schema.get("properties", {}))
            if unknown:
                raise ConfigError(f"Invalid {label} at {path}: unknown keys {sorted(unknown)}")
        for key, item in value.items():
            prop_schema = schema.get("properties", {}).get(key)
            if prop_schema is not None:
                _validate(item, prop_schema, label, f"{path}.{key}", root)
            elif isinstance(schema.get("additionalProperties"), dict):
                _validate(item, schema["additionalProperties"], label, f"{path}.{key}", root)
        return
    if schema_type == "array":
        if not isinstance(value, list):
            raise ConfigError(f"Invalid {label} at {path}: expected array; value={value!r}")
        item_schema = schema.get("items", {})
        for i, item in enumerate(value):
            _validate(item, item_schema, label, f"{path}[{i}]", root)
        return
    if "const" in schema and value != schema["const"]:
        raise ConfigError(f"Invalid {label} at {path}: expected {schema['const']!r}; value={value!r}")
    if "enum" in schema and value not in schema["enum"]:
        raise ConfigError(f"Invalid {label} at {path}: expected one of {schema['enum']}; value={value!r}")
    allowed = schema_type if isinstance(schema_type, list) else [schema_type]
    if schema_type and not any(_is_type(value, t) for t in allowed):
        raise ConfigError(f"Invalid {label} at {path}: expected {schema_type}; value={value!r}")
    if isinstance(value, int) and "minimum" in schema and value < schema["minimum"]:
        raise ConfigError(f"Invalid {label} at {path}: must be >= {schema['minimum']}; value={value!r}")


def _resolve_ref(ref: str, root: dict[str, Any]) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise ConfigError(f"Remote or external schema references are not permitted in tests: {ref}")
    target: Any = root
    for part in ref[2:].split("/"):
        target = target[part]
    return target


def _is_type(value: Any, type_name: str | None) -> bool:
    if type_name is None:
        return True
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(type_name, True)
