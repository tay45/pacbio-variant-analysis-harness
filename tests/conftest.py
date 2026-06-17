from __future__ import annotations

import os
import socket
import urllib.request
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def block_network(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest):
    if request.node.get_closest_marker("real_tools"):
        return

    def blocked_connect(*args, **kwargs):
        raise AssertionError("Network access is blocked during standard tests")

    def blocked_urlopen(*args, **kwargs):
        raise AssertionError("Remote URL access is blocked during standard tests")

    monkeypatch.setattr(socket.socket, "connect", blocked_connect)
    monkeypatch.setattr(urllib.request, "urlopen", blocked_urlopen)


@pytest.fixture
def tiny_reference(tmp_path: Path) -> dict[str, Path]:
    ref = tmp_path / "ref.fa"
    ref.write_text(">chr1\nACGTACGTACGT\n", encoding="utf-8")
    fai = tmp_path / "ref.fa.fai"
    fai.write_text("chr1\t12\t6\t12\t13\n", encoding="utf-8")
    dictionary = tmp_path / "ref.dict"
    dictionary.write_text("@SQ\tSN:chr1\tLN:12\n", encoding="utf-8")
    bed = tmp_path / "tr.bed"
    bed.write_text("chr1\t1\t4\n", encoding="utf-8")
    return {"fasta": ref, "fai": fai, "dict": dictionary, "bed": bed}


@pytest.fixture
def tiny_inputs(tmp_path: Path) -> dict[str, Path]:
    bam = tmp_path / "sample.aligned.bam"
    bam.write_bytes(b"BAM\1mock\n")
    Path(str(bam) + ".bai").write_text("index\n", encoding="utf-8")
    unaligned = tmp_path / "sample.unaligned.bam"
    unaligned.write_bytes(b"BAM\1mock\n")
    xml1 = tmp_path / "one.xml"
    xml2 = tmp_path / "two.xml"
    xml1.write_text("<DataSet />\n", encoding="utf-8")
    xml2.write_text("<DataSet />\n", encoding="utf-8")
    return {"bam": bam, "unaligned": unaligned, "xml1": xml1, "xml2": xml2}


@pytest.fixture
def mock_tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    tool_dir = tmp_path / "bin"
    tool_dir.mkdir()
    _write_tool(tool_dir / "dataset", DATASET_TOOL)
    _write_tool(tool_dir / "pbmm2", PBMM2_TOOL)
    _write_tool(tool_dir / "deepvariant", DEEPVARIANT_TOOL)
    _write_tool(tool_dir / "pbsv", PBSV_TOOL)
    _write_tool(tool_dir / "samtools", SAMTOOLS_TOOL)
    _write_tool(tool_dir / "bgzip", VERSION_TOOL)
    _write_tool(tool_dir / "tabix", VERSION_TOOL)
    monkeypatch.setenv("PATH", f"{tool_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    return tool_dir


def write_config(tmp_path: Path, tiny_reference: dict[str, Path], output_root: Path | None = None) -> Path:
    config = tmp_path / "run.yaml"
    output = output_root or (tmp_path / "results")
    config.write_text(
        f"""
schema_version: phase2a1.v1
project:
  name: test_project
  output_root: {output}
  research_use_only: true
reference:
  id: ref_001
  build: GRCh38
  fasta: {tiny_reference['fasta']}
  fai: {tiny_reference['fai']}
  sequence_dictionary: {tiny_reference['dict']}
  tandem_repeats_bed: {tiny_reference['bed']}
  checksum_policy: metadata
execution:
  backend: local
  tool_backend: native
  temp_root: {tmp_path / 'tmp'}
  threads: 2
  memory_gb: 4
  keep_temp_on_failure: true
  cleanup_on_success: false
  overwrite: false
tools:
  dataset:
    backend: native
    executable: dataset
    version: mock
    container: null
  pbmm2:
    backend: native
    executable: pbmm2
    version: mock
    container: null
  samtools:
    backend: native
    executable: samtools
    version: mock
    container: null
  deepvariant:
    backend: native
    executable: deepvariant
    container: null
    version: mock
    model_type: PACBIO
    num_shards: 2
    extra_args: []
  pbsv:
    backend: native
    executable: pbsv
    version: mock
    container: null
    ccs_mode: true
  bgzip:
    backend: native
    executable: bgzip
    version: mock
    container: null
  tabix:
    backend: native
    executable: tabix
    version: mock
    container: null
workflow:
  perform_dataset_merge: auto
  perform_alignment: auto
  call_snv: true
  call_sv: true
  emit_gvcf: true
  legacy_naming: false
qc:
  thresholds:
    minimum_records: 1
  checksum_outputs: false
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return config


def write_manifest(tmp_path: Path, sample_id: str, input_type: str, input_path: Path, additional: str = "", aligned: str = "true") -> Path:
    manifest = tmp_path / f"{sample_id}.tsv"
    manifest.write_text(
        "sample_id\tplatform\tinput_type\tinput_path\tadditional_inputs\taligned\treference_id\tread_group_sample\toutput_prefix\n"
        f"{sample_id}\tpacbio_hifi\t{input_type}\t{input_path}\t{additional}\t{aligned}\tref_001\t{sample_id}\t{sample_id}\n",
        encoding="utf-8",
    )
    return manifest


def _write_tool(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


DATASET_TOOL = """#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "--version" ]]; then echo "dataset mock"; exit 0; fi
if [[ "${1:-}" == "merge" ]]; then
  out="${@: -3:1}"
  printf '<DataSet />\\n' > "$out"
fi
"""

PBMM2_TOOL = """#!/usr/bin/env bash
set -euo pipefail
for arg in "$@"; do if [[ "$arg" == "--version" ]]; then echo "pbmm2 mock"; exit 0; fi; done
out="$3"
printf 'BAM\\001mock aligned\\n' > "$out"
printf 'index\\n' > "${out}.bai"
"""

DEEPVARIANT_TOOL = """#!/usr/bin/env bash
set -euo pipefail
for arg in "$@"; do if [[ "$arg" == "--version" ]]; then echo "deepvariant mock"; exit 0; fi; done
out_vcf=""
out_gvcf=""
for arg in "$@"; do
  case "$arg" in
    --output_vcf=*) out_vcf="${arg#--output_vcf=}" ;;
    --output_gvcf=*) out_gvcf="${arg#--output_gvcf=}" ;;
  esac
done
vcf=$'##fileformat=VCFv4.2\\n#CHROM\\tPOS\\tID\\tREF\\tALT\\tQUAL\\tFILTER\\tINFO\\tFORMAT\\tSAMPLE_001\\nchr1\\t2\\t.\\tA\\tG\\t50\\tPASS\\t.\\tGT:GQ:DP:AD\\t0/1:60:20:10,10\\n'
printf "%s" "$vcf" > "$out_vcf"
if [[ -n "$out_gvcf" ]]; then printf "%s" "$vcf" > "$out_gvcf"; fi
"""

PBSV_TOOL = """#!/usr/bin/env bash
set -euo pipefail
for arg in "$@"; do if [[ "$arg" == "--version" ]]; then echo "pbsv mock"; exit 0; fi; done
if [[ "${1:-}" == "discover" ]]; then
  printf 'mock\\n' | gzip -c > "${@: -1}"
elif [[ "${1:-}" == "call" ]]; then
  out="${@: -1}"
  printf '##fileformat=VCFv4.2\\n#CHROM\\tPOS\\tID\\tREF\\tALT\\tQUAL\\tFILTER\\tINFO\\tFORMAT\\tSAMPLE_001\\nchr1\\t3\\t.\\tN\\t<DEL>\\t50\\tPASS\\tSVTYPE=DEL;END=8;SVLEN=-5\\tGT\\t0/1\\n' > "$out"
fi
"""

SAMTOOLS_TOOL = """#!/usr/bin/env bash
set -euo pipefail
for arg in "$@"; do if [[ "$arg" == "--version" ]]; then echo "samtools mock"; exit 0; fi; done
cmd="${1:-}"
if [[ "$cmd" == "quickcheck" ]]; then [[ -e "${@: -1}" ]]; exit $?; fi
if [[ "$cmd" == "view" ]]; then
  printf '@HD\\tVN:1.6\\tSO:coordinate\\n@SQ\\tSN:chr1\\tLN:12\\n@RG\\tID:rg1\\tSM:SAMPLE_001\\tPL:PACBIO\\n'
elif [[ "$cmd" == "flagstat" ]]; then
  printf '100 + 0 in total (QC-passed reads + QC-failed reads)\\n90 + 0 mapped (90.00%% : N/A)\\n2 + 0 secondary\\n3 + 0 supplementary\\n0 + 0 duplicates\\n'
elif [[ "$cmd" == "idxstats" ]]; then
  printf 'chr1\\t12\\t90\\t10\\n'
elif [[ "$cmd" == "stats" ]]; then
  printf 'SN\\treads mapped:\\t90\\nSN\\treads unmapped:\\t10\\nSN\\tbases mapped:\\t1000\\nSN\\taverage length:\\t10\\n'
fi
"""

VERSION_TOOL = """#!/usr/bin/env bash
set -euo pipefail
echo "$(basename "$0") mock"
"""
