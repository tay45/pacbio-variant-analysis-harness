"""Integrated output inventory and provenance."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def inventory_path(path: Path, *, category: str, required: bool = False) -> dict[str, Any]:
    exists = path.exists()
    size = path.stat().st_size if exists and path.is_file() else 0
    checksum = hashlib.sha256(path.read_bytes()).hexdigest() if exists and path.is_file() and size else None
    return {"path": str(path), "category": category, "required": required, "available": exists, "size": size, "sha256": checksum}


def build_output_inventory(root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(root.rglob("*")) if root.exists() else []:
        if path.is_file():
            category = "integrated_report" if "/reports/" in str(path) else "integrated_output"
            rows.append(inventory_path(path, category=category))
    return rows


def write_inventory(rows: list[dict[str, Any]], out_dir: Path) -> None:
    import csv

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "integrated_output_inventory.json").write_text(json.dumps(rows, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    with (out_dir / "integrated_output_inventory.tsv").open("w", encoding="utf-8", newline="") as handle:
        fields = ["path", "category", "required", "available", "size", "sha256"]
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
    lines = ["# Integrated Output Inventory", "", f"Files: {len(rows)}"]
    (out_dir / "integrated_output_inventory.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_provenance(provenance: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "integrated_provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")

