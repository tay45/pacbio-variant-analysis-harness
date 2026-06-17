"""Basic alignment validation scaffold."""

from __future__ import annotations

from pathlib import Path
import subprocess

from variant_analysis_harness.common.validation import validate_bam_like


def run_alignment_qc(bam: Path, expected_sample: str | None = None, samtools: str = "samtools") -> dict:
    validate_bam_like(bam)
    flagstat = _run([samtools, "flagstat", str(bam)])
    idxstats = _run([samtools, "idxstats", str(bam)])
    stats = _run([samtools, "stats", str(bam)])
    metrics = _parse_flagstat(flagstat["stdout"])
    metrics.update(_parse_stats(stats["stdout"]))
    metrics["per_contig_idxstats_rows"] = len([line for line in idxstats["stdout"].splitlines() if line.strip()])
    if flagstat["exit_code"] != 0:
        metrics["flagstat"] = "NOT_EVALUATED"
    if idxstats["exit_code"] != 0:
        metrics["idxstats"] = "NOT_EVALUATED"
    if stats["exit_code"] != 0:
        metrics["stats"] = "NOT_EVALUATED"
    return {
        "status": "PASS" if flagstat["exit_code"] == 0 or idxstats["exit_code"] == 0 or stats["exit_code"] == 0 else "WARN",
        "bam": str(bam),
        "expected_sample": expected_sample,
        "metrics": metrics,
        "raw_reports": {"flagstat": flagstat, "idxstats": idxstats, "stats": stats},
        "warnings": [] if metrics else ["samtools alignment metrics were not available."],
    }


def write_alignment_qc_outputs(qc: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    import json

    (out_dir / "alignment_qc.json").write_text(json.dumps(qc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rows = ["metric\tvalue"] + [f"{k}\t{v}" for k, v in qc.get("metrics", {}).items()]
    (out_dir / "alignment_qc.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    lines = ["# Alignment QC", "", f"Status: **{qc.get('status')}**", "", "## Metrics"]
    lines.extend(f"- {k}: {v}" for k, v in qc.get("metrics", {}).items())
    (out_dir / "alignment_qc.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run(argv: list[str]) -> dict:
    try:
        completed = subprocess.run(argv, capture_output=True, text=True, timeout=120, check=False)
    except Exception as exc:
        return {"exit_code": None, "stdout": "", "stderr": str(exc)}
    return {"exit_code": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def _parse_flagstat(text: str) -> dict:
    metrics = {}
    for line in text.splitlines():
        if " in total" in line:
            metrics["total_reads"] = _first_int(line)
        elif " mapped (" in line and "primary" not in line:
            metrics["mapped_reads"] = _first_int(line)
            metrics["mapped_percentage"] = _percent(line)
        elif "secondary" in line:
            metrics["secondary_alignments"] = _first_int(line)
        elif "supplementary" in line:
            metrics["supplementary_alignments"] = _first_int(line)
        elif "duplicates" in line:
            metrics["duplicate_count"] = _first_int(line)
    return metrics


def _parse_stats(text: str) -> dict:
    metrics = {}
    for line in text.splitlines():
        if not line.startswith("SN\t"):
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        key = parts[1].rstrip(":").replace(" ", "_")
        if key in {"average_length", "bases_mapped", "reads_mapped", "reads_unmapped"}:
            metrics[key] = parts[2]
    return metrics


def _first_int(line: str) -> int | None:
    try:
        return int(line.split()[0])
    except (ValueError, IndexError):
        return None


def _percent(line: str) -> float | None:
    if "(" not in line or "%" not in line:
        return None
    try:
        return float(line.split("(")[1].split("%")[0])
    except (ValueError, IndexError):
        return None
