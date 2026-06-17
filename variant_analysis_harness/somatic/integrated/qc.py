"""Unified integrated somatic QC."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALLOWED_QC_STATUSES = {"PASS", "WARN", "FAIL", "NOT_RUN", "NOT_APPLICABLE", "UNKNOWN"}


def qc_domain(name: str, status: str, *, severity: str = "info", reason_codes: list[str] | None = None, source: str = "integrated", artifact_path: str = "") -> dict[str, Any]:
    if status not in ALLOWED_QC_STATUSES:
        status = "UNKNOWN"
    return {"domain": name, "status": status, "severity": severity, "reason_codes": reason_codes or [], "source": source, "supporting_artifact_path": artifact_path, "timestamp": datetime.now(timezone.utc).isoformat()}


def aggregate_qc(domains: list[dict[str, Any]]) -> dict[str, Any]:
    status = "PASS"
    if any(d["status"] == "FAIL" for d in domains):
        status = "FAIL"
    elif any(d["status"] == "WARN" for d in domains):
        status = "WARN"
    elif not domains:
        status = "UNKNOWN"
    return {"overall_readiness": status, "domains": domains, "domain_counts": _counts(domains)}


def write_qc(qc: dict[str, Any], out_dir: Path) -> None:
    import csv

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "integrated_qc.json").write_text(json.dumps(qc, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    fields = ["domain", "status", "severity", "reason_codes", "source", "supporting_artifact_path", "timestamp"]
    with (out_dir / "integrated_qc.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
        writer.writeheader()
        for row in qc.get("domains", []):
            writer.writerow({**row, "reason_codes": ";".join(row.get("reason_codes", []))})


def _counts(domains: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for domain in domains:
        counts[domain["status"]] = counts.get(domain["status"], 0) + 1
    return dict(sorted(counts.items()))

