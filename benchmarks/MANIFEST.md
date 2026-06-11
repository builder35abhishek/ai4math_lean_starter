# Benchmark Manifest

This repository keeps a stable passing benchmark baseline and a larger v4 benchmark track for Lean/Mathlib proof-agent development.

| benchmark | file | expected rows | required solve rate | forbidden first-success source |
|---|---|---:|---:|---|
| medium | `benchmarks/mathlib_medium_theorems.jsonl` | 50 | 100% | `fallback` |
| medium v4 current | `benchmarks/mathlib_medium_v4_100_theorems.jsonl` | 65 | 100% | `fallback` |

## Notes

- The v4 benchmark file name still contains `100` for historical continuity, but the current enforced row count is 65.
- Treat this file as the source of truth for the current benchmark contract until benchmark expectations are moved into a machine-readable config.
- CI enforces these expectations with `src/report_metrics.py` using `--min-total`, `--require-all-solved`, and `--forbid-source fallback`.
- Raw per-theorem JSONL results are uploaded as workflow artifacts. Only stable Markdown metrics are committed back to the repository.
- Increase `expected rows` and the matching workflow `--min-total` value together when expanding a benchmark.
