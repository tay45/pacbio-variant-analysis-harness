"""YAML loading and writing with required PyYAML safe loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from variant_analysis_harness.exceptions import ConfigError
from variant_analysis_harness.common.dependencies import load_required_dependency


yaml = load_required_dependency("yaml", "PyYAML")


class DuplicateKeySafeLoader(yaml.SafeLoader):  # type: ignore[misc]
    """PyYAML SafeLoader that rejects duplicate mapping keys."""


def _construct_mapping(loader: DuplicateKeySafeLoader, node: Any, deep: bool = False) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            mark = key_node.start_mark
            raise ConfigError(
                f"Duplicate YAML key {key!r} at line {mark.line + 1}, column {mark.column + 1}"
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


DuplicateKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.load(handle, Loader=DuplicateKeySafeLoader)
    except ConfigError:
        raise
    except yaml.YAMLError as exc:  # type: ignore[union-attr]
        mark = getattr(exc, "problem_mark", None)
        location = f" at line {mark.line + 1}, column {mark.column + 1}" if mark else ""
        raise ConfigError(f"Malformed YAML{location}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Top-level YAML document must be a mapping: {path}")
    return data


def dump_yaml(data: dict[str, Any], path: Path) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
