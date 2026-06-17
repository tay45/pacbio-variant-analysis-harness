# Severus Configuration

Configure Severus under `somatic.structural_variants`. The default backend is `severus`; Phase 2F.1 pins the official Severus `1.7` contract and records `command_contract_version: 1`.

Use `configs/severus_pacbio.example.yaml` as the starting point. Extra arguments cannot override protected official target, control, output, phasing, VNTR, uppercase PoN, supplementary-tag, or thread flags. There is no Severus `--reference` argument in the pinned contract.
