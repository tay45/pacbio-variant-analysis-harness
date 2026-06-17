"""A strict dependency-free YAML subset reader/writer.

It supports the mapping/list/scalar structures used by the harness examples.
It deliberately rejects complex YAML features instead of guessing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from variant_analysis_harness.exceptions import ConfigError


def load_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ConfigError(f"Empty YAML file: {path}")
    try:
        loaded = json.loads(text)
        if isinstance(loaded, dict):
            return loaded
    except json.JSONDecodeError:
        pass
    lines = _preprocess(text)
    data, next_index = _parse_block(lines, 0, 0)
    if next_index != len(lines):
        raise ConfigError(f"Could not parse YAML near line {lines[next_index][0]}")
    if not isinstance(data, dict):
        raise ConfigError(f"Top-level YAML document must be a mapping: {path}")
    return data


def dump_yaml(data: dict[str, Any], path: Path) -> None:
    path.write_text(_dump_mapping(data, 0), encoding="utf-8")


def _preprocess(text: str) -> list[tuple[int, int, str]]:
    lines: list[tuple[int, int, str]] = []
    for number, raw in enumerate(text.splitlines(), 1):
        raw = raw.rstrip()
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise ConfigError(f"Tabs are not supported in YAML indentation at line {number}")
        indent = len(raw) - len(raw.lstrip(" "))
        lines.append((number, indent, raw.lstrip()))
    return lines


def _parse_block(lines: list[tuple[int, int, str]], index: int, indent: int) -> tuple[Any, int]:
    if index >= len(lines):
        return {}, index
    _, current_indent, text = lines[index]
    if current_indent < indent:
        return {}, index
    if current_indent != indent:
        raise ConfigError(f"Unexpected indentation at line {lines[index][0]}")
    if text.startswith("- "):
        return _parse_list(lines, index, indent)
    return _parse_mapping(lines, index, indent)


def _parse_mapping(lines: list[tuple[int, int, str]], index: int, indent: int) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    while index < len(lines):
        number, current_indent, text = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            raise ConfigError(f"Unexpected indentation at line {number}")
        if text.startswith("- "):
            break
        if ":" not in text:
            raise ConfigError(f"Expected key/value mapping at line {number}")
        key, raw_value = text.split(":", 1)
        key = key.strip()
        if not key:
            raise ConfigError(f"Empty key at line {number}")
        raw_value = raw_value.strip()
        if raw_value == "":
            value, index = _parse_block(lines, index + 1, indent + 2)
        else:
            value = _parse_scalar(raw_value)
            index += 1
        if key in result:
            raise ConfigError(f"Duplicate key {key!r} at line {number}")
        result[key] = value
    return result, index


def _parse_list(lines: list[tuple[int, int, str]], index: int, indent: int) -> tuple[list[Any], int]:
    result: list[Any] = []
    while index < len(lines):
        number, current_indent, text = lines[index]
        if current_indent < indent:
            break
        if current_indent != indent or not text.startswith("- "):
            break
        raw_value = text[2:].strip()
        if raw_value == "":
            value, index = _parse_block(lines, index + 1, indent + 2)
        elif ":" in raw_value and not raw_value.startswith(("'", '"')):
            key, value_text = raw_value.split(":", 1)
            item: dict[str, Any] = {key.strip(): _parse_scalar(value_text.strip())}
            index += 1
            while index < len(lines) and lines[index][1] == indent + 2:
                child_text = lines[index][2]
                if ":" not in child_text:
                    raise ConfigError(f"Expected list item mapping at line {lines[index][0]}")
                child_key, child_value = child_text.split(":", 1)
                item[child_key.strip()] = _parse_scalar(child_value.strip())
                index += 1
            value = item
        else:
            value = _parse_scalar(raw_value)
            index += 1
        result.append(value)
    return result, index


def _parse_scalar(value: str) -> Any:
    if value == "":
        return None
    if value in {"null", "Null", "NULL", "~"}:
        return None
    if value in {"true", "True", "TRUE"}:
        return True
    if value in {"false", "False", "FALSE"}:
        return False
    if value.startswith("[") or value.startswith("{"):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"Unsupported inline YAML value: {value}") from exc
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _dump_mapping(data: dict[str, Any], indent: int) -> str:
    lines: list[str] = []
    prefix = " " * indent
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(_dump_mapping(value, indent + 2).rstrip())
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            for item in value:
                if isinstance(item, dict):
                    lines.append(f"{prefix}  -")
                    lines.append(_dump_mapping(item, indent + 4).rstrip())
                else:
                    lines.append(f"{prefix}  - {_format_scalar(item)}")
        else:
            lines.append(f"{prefix}{key}: {_format_scalar(value)}")
    return "\n".join(lines) + "\n"


def _format_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value))
