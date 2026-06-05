# AI4Math Lean Proof Starter Kit

This is a minimal research harness for an AI-assisted Lean 4 theorem proving pipeline.

Goal:
- Generate or repair Lean 4 proofs.
- Check them with the Lean kernel.
- Record pass/fail/error messages.
- Iterate from toy problems toward AI4Math Track 2/Track 4 style tasks.

## Why Lean?
Lean gives objective verification: a theorem is accepted only if the kernel checks the proof.

## Install Lean 4
Install `elan`, the Lean version manager, from the official Lean documentation:
https://lean-lang.org/learn/

After installation, verify:

```bash
lean --version
lake --version
```

## Run toy benchmark

```bash
python src/run_toy.py --benchmark benchmarks/toy_theorems.jsonl --out reports/toy_results.jsonl
```

Each benchmark item has:
- an informal theorem description,
- a Lean theorem statement,
- one or more candidate proof bodies.

The harness writes a temporary `.lean` file, invokes Lean, and records whether the proof is accepted.

## Next extensions

1. Add an LLM generator that proposes proof bodies.
2. Add a Lean-error repair loop.
3. Add premise retrieval from Mathlib / CSLib.
4. Add benchmark loaders for ShadowBench or TCS Proving tasks.
5. Submit only outputs that comply with challenge rules.
