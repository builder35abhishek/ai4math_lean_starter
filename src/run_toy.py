"""Run a toy Lean theorem proving benchmark.

Usage:
    python src/run_toy.py --benchmark benchmarks/toy_theorems.jsonl --out reports/toy_results.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from lean_runner import check_lean_code, lean_available


def load_jsonl(path: Path) -> Iterable[dict]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def build_code(header: str, statement: str, proof_body: str) -> str:
    pieces = []
    if header.strip():
        pieces.append(header.rstrip())
    pieces.append(statement.rstrip())

    body = proof_body.rstrip()
    indented_body = "\n".join(
        ("  " + line if line.strip() else line)
        for line in body.splitlines()
    )
    pieces.append(indented_body)

    return "\n".join(pieces) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)

    results = []
    for item in load_jsonl(args.benchmark):
        item_result = {
            "id": item["id"],
            "domain": item.get("domain"),
            "informal": item.get("informal"),
            "attempts": [],
            "solved": False,
        }
        for idx, cand in enumerate(item.get("candidates", []), start=1):
            code = build_code(item.get("lean_header", ""), item["statement"], cand)
            res = check_lean_code(code)
            attempt = {
                "candidate_index": idx,
                "ok": res.ok,
                "returncode": res.returncode,
                "stdout": res.stdout,
                "stderr": res.stderr,
                "code": res.code,
            }
            item_result["attempts"].append(attempt)
            if res.ok:
                item_result["solved"] = True
                break
        results.append(item_result)

    with args.out.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    solved = sum(1 for r in results if r["solved"])
    total = len(results)
    print(f"Lean available: {lean_available()}")
    print(f"Solved {solved}/{total} toy theorems")
    print(f"Wrote results to {args.out}")


if __name__ == "__main__":
    main()
