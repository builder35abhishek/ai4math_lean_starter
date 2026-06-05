"""Milestone 4: Lean proof agent runner.

This runner supports two modes:
1. deterministic fallback candidates from the benchmark JSONL, so CI is reproducible;
2. optional future LLM-generated candidates, enabled by setting an API key and extending
   generate_llm_candidates().

For now, the agent loop is:
  theorem item -> candidate generator -> Lean checker -> error-aware retry log -> JSONL report
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Iterable, List

from lean_runner import check_lean_code, lean_available
from run_toy import build_code


def load_jsonl(path: Path) -> Iterable[dict]:
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on {path}:{line_no}: {exc}") from exc


def validate_item(item: dict) -> None:
    required = ["id", "statement"]
    missing = [k for k in required if k not in item]
    if missing:
        raise ValueError(f"Benchmark item {item.get('id', '<unknown>')} missing required fields: {missing}")
    if "fallback_candidates" not in item and "candidates" not in item:
        raise ValueError(
            f"Benchmark item {item.get('id', '<unknown>')} needs fallback_candidates or candidates"
        )


def generate_llm_candidates(item: dict, previous_errors: List[str], max_candidates: int) -> List[str]:
    """Placeholder for a real LLM proof generator.

    This intentionally does not call any external API yet. The stable CI path uses
    benchmark-provided fallback candidates. Later we can add OpenAI/Gemini/etc. here
    behind environment variables without breaking offline reproducibility.
    """
    if not os.environ.get("LEAN_AGENT_ENABLE_LLM"):
        return []

    # Future extension point:
    # - read OPENAI_API_KEY/GEMINI_API_KEY/etc.
    # - prompt with item['informal'], item['statement'], and previous_errors
    # - return proof bodies only, not full theorem declarations
    return []


def get_candidates(item: dict, previous_errors: List[str], max_candidates: int) -> List[dict]:
    candidates: List[dict] = []

    for body in generate_llm_candidates(item, previous_errors, max_candidates):
        candidates.append({"source": "llm", "body": body})
        if len(candidates) >= max_candidates:
            return candidates

    fallback = item.get("fallback_candidates", item.get("candidates", []))
    for body in fallback:
        candidates.append({"source": "fallback", "body": body})
        if len(candidates) >= max_candidates:
            break

    return candidates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--max-candidates", type=int, default=5)
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)

    results = []
    for item in load_jsonl(args.benchmark):
        validate_item(item)

        previous_errors: List[str] = []
        item_result = {
            "id": item["id"],
            "domain": item.get("domain"),
            "informal": item.get("informal"),
            "mode": "llm_enabled" if os.environ.get("LEAN_AGENT_ENABLE_LLM") else "fallback_only",
            "attempts": [],
            "solved": False,
        }

        candidates = get_candidates(item, previous_errors, args.max_candidates)
        for idx, cand in enumerate(candidates, start=1):
            code = build_code(item.get("lean_header", ""), item["statement"], cand["body"])
            res = check_lean_code(code)
            attempt = {
                "candidate_index": idx,
                "source": cand["source"],
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

            combined_error = "\n".join(x for x in [res.stdout, res.stderr] if x)
            previous_errors.append(combined_error)

        results.append(item_result)

    with args.out.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    solved = sum(1 for r in results if r["solved"])
    total = len(results)
    print(f"Lean available: {lean_available()}")
    print(f"Solved {solved}/{total} agent theorems")
    print(f"Wrote results to {args.out}")

    if solved != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
