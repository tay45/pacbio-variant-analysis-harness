"""Output manifest helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def output_record(path: Path, checksum: bool = False) -> dict[str, object]:
    exists = path.exists()
    record: dict[str, object] = {"path": str(path), "exists": exists}
    if exists:
        record["size"] = path.stat().st_size
        if checksum and path.is_file() and path.stat().st_size > 0:
            record["sha256"] = sha256_file(path)
    return record


def write_outputs_manifest(paths: list[Path], manifest_path: Path, checksum: bool = False) -> None:
    data = {"outputs": [output_record(path, checksum) for path in paths]}
    manifest_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
