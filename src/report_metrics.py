"""Summarize Lean proof-agent JSONL reports.

Usage:
    python src/report_metrics.py --results reports/mathlib_results.jsonl --out reports/mathlib_metrics.md
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def first_success_source(item: dict) -> str:
    for attempt in item.get("attempts", []):
        if attempt.get("ok"):
            return attempt.get("source", "unknown")
    return "unsolved"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--min-total", type=int, default=0)
    parser.add_argument("--require-all-solved", action="store_true")
    parser.add_argument("--forbid-source", action="append", default=[])
    args = parser.parse_args()

    rows = load_jsonl(args.results)
    total = len(rows)
    solved = sum(1 for item in rows if item.get("solved"))
    source_counts = Counter(first_success_source(item) for item in rows)
    domain_counts: dict[str, Counter] = defaultdict(Counter)
    attempt_counts = []

    for item in rows:
        domain = item.get("domain") or "unknown"
        source = first_success_source(item)
        domain_counts[domain][source] += 1
        attempt_counts.append(len(item.get("attempts", [])))

    avg_attempts = (sum(attempt_counts) / total) if total else 0.0

    lines: list[str] = []
    lines.append("# Mathlib Proof Agent Metrics")
    lines.append("")
    lines.append(f"- Total theorems: {total}")
    lines.append(f"- Solved: {solved}")
    lines.append(f"- Unsolved: {total - solved}")
    lines.append(f"- Solve rate: {(solved / total * 100.0) if total else 0.0:.1f}%")
    lines.append(f"- Average attempts per theorem: {avg_attempts:.2f}")
    lines.append("")
    lines.append("## First successful source")
    lines.append("")
    for source in ["heuristic", "repair", "fallback", "llm", "unsolved", "unknown"]:
        if source_counts.get(source, 0):
            lines.append(f"- {source}: {source_counts[source]}")
    lines.append("")
    lines.append("## Domain breakdown")
    lines.append("")
    for domain in sorted(domain_counts):
        parts = ", ".join(f"{source}={count}" for source, count in sorted(domain_counts[domain].items()))
        lines.append(f"- {domain}: {parts}")
    lines.append("")
    lines.append("## Theorem details")
    lines.append("")
    lines.append("| theorem | domain | solved | first_success_source | attempts |")
    lines.append("|---|---:|---:|---:|---:|")
    for item in rows:
        lines.append(
            f"| {item.get('id')} | {item.get('domain') or 'unknown'} | "
            f"{item.get('solved')} | {first_success_source(item)} | {len(item.get('attempts', []))} |"
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote metrics to {args.out}")

    failures: list[str] = []
    if total < args.min_total:
        failures.append(f"expected at least {args.min_total} theorem rows, got {total}")
    if args.require_all_solved and solved != total:
        failures.append(f"expected all theorems solved, got {solved}/{total}")
    for source in args.forbid_source:
        count = source_counts.get(source, 0)
        if count:
            failures.append(f"forbidden first-success source {source!r} appeared {count} time(s)")

    if failures:
        raise SystemExit("Metric gate failed: " + "; ".join(failures))


if __name__ == "__main__":
    main()
