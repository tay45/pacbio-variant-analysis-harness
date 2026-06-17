"""Contract-aware Severus native output discovery."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def discover_severus_outputs(native_dir: Path, capability: dict[str, Any], *, require_somatic: bool = True, target_ids: list[str] | None = None) -> dict[str, Any]:
    files = [path for path in sorted(native_dir.rglob("*")) if path.is_file()] if native_dir.exists() else []
    errors: list[str] = []
    warnings: list[str] = []
    inventory = []
    required_paths = [capability["required_outputs"]["all_vcf"]]
    somatic_contract = capability["conditional_required_outputs"]["somatic_vcf"]["path"]
    if require_somatic:
        required_paths.append(somatic_contract)
    optional_paths = [value for value in capability.get("optional_outputs", {}).values() if "*" not in str(value)]
    for rel in required_paths:
        _check_required(native_dir / rel, rel, errors)
    for rel in optional_paths:
        path = native_dir / rel
        if path.exists() and path.stat().st_size == 0:
            warnings.append(f"optional Severus output is empty: {rel}")
    target_map = map_target_outputs(native_dir, target_ids or [], somatic_contract if require_somatic else None)
    errors.extend(target_map["errors"])
    warnings.extend(target_map["warnings"])
    for path in files:
        inventory.append({"path": str(path), "relative_path": str(path.relative_to(native_dir)), "name": path.name, "size": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "category": _category(path, native_dir, capability)})
    graphs = [item for item in inventory if item["category"] == "html_breakpoint_graph"]
    for graph in graphs:
        if graph["size"] == 0:
            warnings.append(f"HTML graph is empty: {graph['relative_path']}")
        else:
            text = Path(graph["path"]).read_text(encoding="utf-8", errors="ignore")[:500].lower()
            if "<html" not in text and "<!doctype html" not in text:
                warnings.append(f"HTML graph does not contain a minimal HTML marker: {graph['relative_path']}")
    status = "FAIL" if errors else ("WARN" if warnings else "PASS")
    return {
        "status": status,
        "native_dir": str(native_dir),
        "all_vcf": str(native_dir / capability["required_outputs"]["all_vcf"]),
        "somatic_vcf": str(native_dir / somatic_contract) if require_somatic else "",
        "target_output_map": target_map,
        "inventory": inventory,
        "errors": errors,
        "warnings": warnings,
        "output_contract_validation": {"status": status, "required_paths": required_paths, "optional_paths": optional_paths},
    }


def map_target_outputs(native_dir: Path, target_ids: list[str], somatic_rel: str | None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    mapping = {}
    if not somatic_rel:
        return {"targets": mapping, "errors": errors, "warnings": warnings}
    path = native_dir / somatic_rel
    if not path.exists():
        for target in target_ids:
            mapping[target] = ""
        return {"targets": mapping, "errors": errors, "warnings": warnings}
    for target in target_ids:
        mapping[target] = str(path)
    if len(target_ids) > 1:
        warnings.append("Severus 1.7 writes a shared somatic VCF; per-target mapping should be validated from VCF samples/header")
    return {"targets": mapping, "errors": errors, "warnings": warnings}


def validate_breakpoint_tables(native_dir: Path, capability: dict[str, Any], *, require_somatic: bool = True) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    checked = []
    keys = ["all_breakpoint_clusters", "all_breakpoint_clusters_list"]
    if require_somatic:
        keys.extend(["somatic_breakpoint_clusters", "somatic_breakpoint_clusters_list"])
    optional = capability.get("optional_outputs", {})
    for key in keys:
        rel = optional.get(key)
        if not rel:
            continue
        path = native_dir / rel
        checked.append(rel)
        if not path.exists():
            warnings.append(f"breakpoint/cluster table missing: {rel}")
            continue
        if path.stat().st_size == 0:
            warnings.append(f"breakpoint/cluster table empty: {rel}")
            continue
        header = path.read_text(encoding="utf-8", errors="ignore").splitlines()[0].split("\t")
        if len(header) < 2:
            errors.append(f"breakpoint/cluster table has too few columns: {rel}")
    return {"status": "FAIL" if errors else ("WARN" if warnings else "PASS"), "checked": checked, "errors": errors, "warnings": warnings}


def write_output_inventory(inventory: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "severus_native_output_inventory.json").write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "severus_output_contract_validation.json").write_text(json.dumps(inventory.get("output_contract_validation", {}), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# Severus Native Output Inventory", "", f"Status: {inventory['status']}"]
    lines.extend(f"- {item['category']}: {item['relative_path']} ({item['size']} bytes)" for item in inventory.get("inventory", []))
    lines.extend(f"- ERROR: {e}" for e in inventory.get("errors", []))
    lines.extend(f"- WARNING: {w}" for w in inventory.get("warnings", []))
    (out_dir / "severus_native_output_inventory.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _check_required(path: Path, rel: str, errors: list[str]) -> None:
    if not path.exists():
        errors.append(f"required Severus output is missing: {rel}")
    elif path.stat().st_size == 0:
        errors.append(f"required Severus output is empty: {rel}")


def _category(path: Path, native_dir: Path, capability: dict[str, Any]) -> str:
    rel = str(path.relative_to(native_dir))
    if rel == capability["required_outputs"]["all_vcf"]:
        return "all_sv_vcf"
    if rel == capability["conditional_required_outputs"]["somatic_vcf"]["path"]:
        return "somatic_sv_vcf"
    if rel.endswith(".html") and "/plots/" in rel:
        return "html_breakpoint_graph"
    if rel.endswith("breakpoint_clusters.tsv"):
        return "breakpoint_clusters"
    if rel.endswith("breakpoint_clusters_list.tsv"):
        return "breakpoint_clusters_list"
    if path.name in {"severus.log", "read_qual.txt", "read_ids.csv", "severus_LOH.bed", "severus_collaped_dup.bed"}:
        return "optional_native"
    return "unknown_native"
