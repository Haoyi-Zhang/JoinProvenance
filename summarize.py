#!/usr/bin/env python3
"""Rebuild claim-linked aggregate summaries from raw result files.

The script uses only the standard library and deliberately keeps timing values
as descriptive measurements rather than deterministic correctness targets.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def number_values(rows: list[dict[str, str]], key: str) -> list[float]:
    return [float(row[key]) for row in rows]


def summarize_values(values: Iterable[float]) -> tuple[float, float, float]:
    seq = list(values)
    return statistics.median(seq), min(seq), max(seq)


def clean_number(value: float) -> int | float:
    return int(value) if value.is_integer() else value


def build_benchmark_summary(results: Path, target: Path) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, str, str], list[dict[str, str]]] = defaultdict(list)
    for path in sorted(results.glob("hierarchy_bench_*.csv")):
        with path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                grouped[(int(row["n"]), row["family"], row["regime"])].append(row)

    dimensions = [
        "holes", "optimized_cost", "canonical_cost", "optimized_blocks",
        "canonical_blocks", "states", "height", "payload_memberships",
        "optimized_seconds", "canonical_seconds", "certificate_seconds",
    ]
    output: list[dict[str, Any]] = []
    for (n, family, regime), rows in sorted(grouped.items()):
        item: dict[str, Any] = {
            "n": n,
            "family": family,
            "regime": regime,
            "timing_rows": len(rows),
            "distinct_supports": len({row["seed"] for row in rows}) if family == "random" else 1,
        }
        for key in dimensions:
            med, low, high = summarize_values(number_values(rows, key))
            item[f"{key}_median"] = clean_number(med)
            item[f"{key}_min"] = clean_number(low)
            item[f"{key}_max"] = clean_number(high)
        # Cost is deterministic for a generated support; timing repeats must not
        # weight the payload statistic.  Collapse the nine nonrandom timing rows
        # to their one support and the random rows to one pair per fixed seed.
        support_pairs: dict[str, tuple[float, float]] = {}
        for row in rows:
            support_key = row["seed"] if family == "random" else "fixed"
            pair = (float(row["canonical_cost"]), float(row["optimized_cost"]))
            previous = support_pairs.setdefault(support_key, pair)
            if previous != pair:
                raise ValueError(
                    f"inconsistent deterministic costs for {n}/{family}/{regime}/{support_key}"
                )
        paired_ratios = [canonical / optimized if optimized else 1.0
                         for canonical, optimized in support_pairs.values()]
        item["payload_ratio_median"] = clean_number(statistics.median(paired_ratios))
        output.append(item)

    target.parent.mkdir(parents=True, exist_ok=True)
    if output:
        with target.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(output[0]))
            writer.writeheader()
            writer.writerows(output)
    return output


def exact_hierarchy_totals(results: Path) -> tuple[int, int, int]:
    cases = mismatches = improved = 0
    for path in sorted(results.glob("hierarchy_exact_*_summary.json")):
        obj = load_json(path)
        cases += int(obj["cases"])
        mismatches += int(obj["mismatches"])
        improved += int(obj.get("greedy_improved_cases", 0))
    return cases, mismatches, improved


def elapsed_totals(ledger: Path | None) -> dict[str, Any]:
    if ledger is None or not ledger.exists():
        return {}
    with ledger.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    successful = [row for row in rows if int(row["exit_code"]) == 0]
    return {
        "jobs": len(successful),
        "all_exit_zero": len(successful) == len(rows),
        "child_cpu_seconds": sum(float(row["child_cpu_seconds"]) for row in successful),
        "wall_seconds_sum": sum(float(row["wall_seconds"]) for row in successful),
        "peak_rss_kib": max((int(float(row["cumulative_child_peak_rss_kib"])) for row in successful), default=0),
        "workers": 1,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--analysis", type=Path, default=Path("analysis"))
    parser.add_argument("--ledger", type=Path)
    args = parser.parse_args()
    results = args.results.resolve()
    analysis = args.analysis.resolve()
    analysis.mkdir(parents=True, exist_ok=True)

    benchmark_rows = build_benchmark_summary(results, analysis / "benchmark-summary.csv")
    oracle_cases, oracle_mismatches, improvements = exact_hierarchy_totals(results)
    boundary = load_json(results / "hierarchy_boundary_summary.json")
    stream = load_json(results / "hierarchy_stream_summary.json")
    cert = load_json(results / "hierarchy_mutations_summary.json")
    coeff = load_json(results / "mutations_summary.json")
    dag = load_json(results / "dag_boundary_summary.json")
    scale = load_json(results / "hierarchy_scale_32768_summary.json")

    summary: dict[str, Any] = {
        "oracle": {
            "cases": oracle_cases,
            "mismatches": oracle_mismatches,
            "canonical_improvement_cases": improvements,
            "arbitrary_nonempty_column_subsets_enumerated": True,
        },
        "benchmark": {
            "aggregate_rows": len(benchmark_rows),
            "timing_rows": sum(int(row["timing_rows"]) for row in benchmark_rows),
            "support_instances": sum(int(row["distinct_supports"]) for row in benchmark_rows if row["regime"] == "unit"),
            "weighted_instances": sum(int(row["distinct_supports"]) for row in benchmark_rows),
        },
        "boundary": {
            "dictionaries": boundary["dictionaries"],
            "support_cases": boundary["support_cases"],
            "mismatches": boundary["mismatches"],
        },
        "sequential": {
            "traces": stream["traces"],
            "checked_transitions": stream["checked_transitions"],
            "mismatches": stream["mismatches"],
        },
        "certificate_controls": {
            "fixtures": cert["fixtures"],
            "detected": cert["detected"],
            "mismatches": cert["mismatches"],
        },
        "coefficient_controls": {
            key: coeff[key] for key in (
                "cases", "exact_detected", "support_detected", "count_detected",
                "lineage_detected"
            )
        },
        "shared_circuit_boundary": {
            "instances": dag["instances"],
            "expanded_instances": dag["expanded_instances"],
            "mismatches": dag["mismatches"],
        },
        "largest_sparse_run": {
            "n": 32768,
            "mismatches": scale["mismatches"],
            "cpu_seconds": scale["cpu_seconds"],
            "wall_seconds": scale["wall_seconds"],
            "peak_rss_kib": scale["peak_rss_kib"],
        },
        "clean_reproduction": elapsed_totals(args.ledger),
        "scope": "Generated finite checks and exact small oracles; no production, private, device, service, or human data.",
    }
    failures = [
        oracle_mismatches,
        int(boundary["mismatches"]),
        int(stream["mismatches"]),
        int(cert["mismatches"]),
        int(dag["mismatches"]),
        int(scale["mismatches"]),
    ]
    summary["all_claim_critical_mismatch_counts_zero"] = not any(failures)
    (analysis / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    if any(failures):
        raise SystemExit("claim-critical mismatch in retained results")


if __name__ == "__main__":
    main()
