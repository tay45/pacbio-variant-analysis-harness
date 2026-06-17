"""Signature-based shared preflight cache."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from variant_analysis_harness.common.signatures import file_signature, object_signature


def cache_key(kind: str, payload: dict[str, Any]) -> str:
    return object_signature({"kind": kind, "payload": payload})


def reference_cache_payload(reference: dict[str, Any]) -> dict[str, Any]:
    return {
        "reference": reference,
        "fasta": file_signature(Path(reference["fasta"])) if reference.get("fasta") else None,
        "fai": file_signature(Path(reference["fai"])) if reference.get("fai") else None,
        "sequence_dictionary": file_signature(Path(reference["sequence_dictionary"])) if reference.get("sequence_dictionary") else None,
        "tandem_repeats_bed": file_signature(Path(reference["tandem_repeats_bed"])) if reference.get("tandem_repeats_bed") else None,
    }


def read_cache(cache_dir: Path, kind: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    key = cache_key(kind, payload)
    path = cache_dir / f"{key}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("key") != key or data.get("status") != "PASS":
        return None
    return data


def write_cache(cache_dir: Path, kind: str, payload: dict[str, Any], status: str, result: dict[str, Any]) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = cache_key(kind, payload)
    final = cache_dir / f"{key}.json"
    temp = final.with_suffix(".tmp")
    data = {
        "key": key,
        "kind": kind,
        "payload": payload,
        "status": status,
        "result": result,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    temp.write_text(json.dumps(data, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    os.replace(temp, final)
    return final

