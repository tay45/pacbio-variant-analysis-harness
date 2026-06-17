from __future__ import annotations

import time

from variant_analysis_harness.somatic.integrated.relationships import build_relationships


def test_relationship_index_handles_many_records_without_quadratic_scan():
    small = [
        {
            "source_record_key": f"small_{idx}",
            "chromosome": "chr1",
            "position": idx * 100,
            "filter": "PASS",
            "vaf": 0.1,
        }
        for idx in range(12000)
    ]
    svs = [
        {
            "source_record_key": f"sv_{idx}",
            "chromosome": "chr1",
            "start": idx * 1000,
            "end": idx * 1000 + 250,
            "filter": "PASS",
            "raw_svtype": "DEL",
        }
        for idx in range(1000)
    ]

    started = time.perf_counter()
    relationships = build_relationships(small, svs, window_bp=50, large_window_bp=200)
    elapsed = time.perf_counter() - started

    assert relationships
    assert elapsed < 3.0
