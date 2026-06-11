# Benchmark Roadmap

The CI workflow is now a stable regression gate. The next project goal is to grow from a small passing regression suite into a meaningful Lean/Mathlib proof-agent benchmark platform.

## Current enforced baseline

| suite | file | rows | CI requirement |
|---|---|---:|---|
| medium | `benchmarks/mathlib_medium_theorems.jsonl` | 50 | all solved, no fallback first-success |
| medium v4 current | `benchmarks/mathlib_medium_v4_100_theorems.jsonl` | 65 | all solved, no fallback first-success |

Total enforced coverage: 115 theorems.

## Next target: v5 harder benchmark

Create a new benchmark file instead of weakening the current gates:

`benchmarks/mathlib_medium_v5_harder_theorems.jsonl`

Target size: 100 theorems initially, then 250, then 500.

## Domain expansion priorities

1. `finset`
   - membership
   - union/intersection
   - cardinality
   - sums/products

2. `set`
   - subset transitivity
   - union/intersection laws
   - image/preimage

3. `function`
   - composition
   - injective/surjective helpers
   - left/right inverse basics

4. `relation`
   - reflexive/symmetric/transitive
   - equivalence-style lemmas

5. `algebra`
   - semiring/ring rewrites
   - cancellation
   - distributivity beyond Nat/Int basics

6. `induction`
   - Nat induction
   - List induction
   - structural recursion proofs

## Quality metrics to add

The current gate checks solve status and forbids fallback first-success. Add these next:

- average attempts upper bound
- max attempts upper bound
- first-success source distribution
- proof length summary
- Lean runtime per theorem
- domain-level solve breakdown

## End-goal direction

A useful AI-assisted theorem-proving project should demonstrate:

1. reproducible Lean/mathlib execution;
2. benchmark gates that prevent regressions;
3. increasingly difficult theorem families;
4. measurable proof-search improvements;
5. artifact evidence for each run;
6. no dependence on hidden/manual proofs.

The workflow is already stable enough. Future patches should prioritize benchmark expansion and proof-search capability over CI cleanup.
