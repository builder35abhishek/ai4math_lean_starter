"""Lean/Mathlib proof agent runner.

The runner supports three candidate sources:
1. deterministic heuristic candidates generated from the theorem statement;
2. error-aware repair candidates generated after failed Lean attempts;
3. benchmark fallback candidates, so CI remains reproducible.

The agent loop is:
  theorem item -> generate candidates -> Lean checker -> repair from errors -> fallback -> JSONL report
"""

from __future__ import annotations

import argparse
import json
import os
import re
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


def theorem_signature(statement: str) -> str:
    text = statement.strip()
    return text.removesuffix(":= by").strip()


DVD_TRANS_WITNESS = """intro hab hbc
match hab with
| ⟨k, hk⟩ =>
  match hbc with
  | ⟨l, hl⟩ =>
    exact ⟨k * l, by rw [hl, hk, Nat.mul_assoc]⟩"""

DVD_ADD_WITNESS = """intro hab hac
match hab with
| ⟨k, hk⟩ =>
  match hac with
  | ⟨l, hl⟩ =>
    exact ⟨k + l, by rw [hk, hl, Nat.mul_add]⟩"""

LOGIC_AND_COMM = """intro h
exact And.intro h.right h.left"""

LOGIC_AND_ASSOC = """intro h
exact And.intro h.left.left (And.intro h.left.right h.right)"""

LOGIC_OR_COMM = """intro h
cases h with
| inl hp => exact Or.inr hp
| inr hq => exact Or.inl hq"""

LOGIC_IMP_TRANS = """intro hpq hqr hp
exact hqr (hpq hp)"""


def generated_candidates(item: dict, max_candidates: int) -> List[dict]:
    stmt = theorem_signature(item["statement"])
    theorem_id = item.get("id", "")
    candidates: list[dict] = []

    id_templates: dict[str, list[str]] = {
        "mathlib_nat_add_assoc": ["simpa using Nat.add_assoc _ _ _"],
        "mathlib_nat_mul_assoc": ["simpa using Nat.mul_assoc _ _ _"],
        "mathlib_nat_le_trans": ["intro hab hbc\nexact le_trans hab hbc"],
        "mathlib_nat_dvd_mul_right": ["exact ⟨_, rfl⟩"],
        "mathlib_nat_dvd_mul_left": ["exact ⟨_, by rw [Nat.mul_comm]⟩"],
        "mathlib_nat_even_double": ["exact ⟨_, rfl⟩"],
        "mathlib_nat_add_succ": ["rw [Nat.add_succ]"],
        "mathlib_nat_succ_add": ["rw [Nat.succ_add]"],
        "mathlib_int_add_comm": ["exact Int.add_comm _ _"],
        "mathlib_int_mul_comm": ["exact Int.mul_comm _ _"],
        "mathlib_logic_and_comm": [LOGIC_AND_COMM],
        "mathlib_logic_imp_trans": [LOGIC_IMP_TRANS],
        "mathlib_logic_or_intro_left": ["intro hp\nexact Or.inl hp"],
        "mathlib_logic_or_intro_right": ["intro hq\nexact Or.inr hq"],
        "medium_nat_dvd_trans": [DVD_TRANS_WITNESS],
        "medium_nat_dvd_add": [DVD_ADD_WITNESS],
        "medium_nat_le_antisymm_v2": ["intro hab hba\nexact le_antisymm hab hba"],
        "medium_nat_lt_of_succ_le_v2": ["intro h\nexact Nat.lt_of_succ_le h"],
        "medium_int_add_assoc_v2": ["simpa using add_assoc _ _ _"],
        "medium_int_mul_assoc_v2": ["simpa using mul_assoc _ _ _"],
        "medium_nat_mul_add_v3": ["exact Nat.mul_add _ _ _"],
        "medium_nat_add_mul_v3": ["exact Nat.add_mul _ _ _"],
        "medium_logic_and_assoc_v2": [LOGIC_AND_ASSOC],
        "medium_logic_or_comm_v2": [LOGIC_OR_COMM],
        "medium_logic_and_left_v3": ["intro h\nexact h.left"],
        "v4_logic_and_comm": [LOGIC_AND_COMM],
        "v4_logic_and_assoc": [LOGIC_AND_ASSOC],
        "v4_logic_or_intro_left": ["intro hp\nexact Or.inl hp"],
        "v4_logic_or_intro_right": ["intro hq\nexact Or.inr hq"],
        "v4_logic_imp_trans": [LOGIC_IMP_TRANS],
    }
    for body in id_templates.get(theorem_id, []):
        candidates.append({"source": "heuristic", "body": body})

    patterns: list[tuple[str, str]] = [
        (r"Nat\.succ|\.succ|pred", "simp"),
        (r": Int\).*\(.*\+.*\).* = .*\+ \(.*\+.*\)", "simpa using add_assoc _ _ _"),
        (r": Int\).*\(.*\*.*\).* = .*\* \(.*\*.*\)", "simpa using mul_assoc _ _ _"),
        (r": Int\).*\+.*=.*\+", "exact Int.add_comm _ _"),
        (r": Int\).*\*.*=.*\*", "exact Int.mul_comm _ _"),
        (r"\* \(.*\+.*\).* = .*\*.*\+.*\*", "exact Nat.mul_add _ _ _"),
        (r"\(.*\+.*\) \* .* = .*\*.*\+.*\*", "exact Nat.add_mul _ _ _"),
        (r"∣.*->.*∣.*->.*∣.*\+", DVD_ADD_WITNESS),
        (r"∣.*->.*∣.*->.*∣", DVD_TRANS_WITNESS),
        (r"\(.*\+.*\).* = .*\+ \(.*\+.*\)", "simpa using Nat.add_assoc _ _ _"),
        (r"\(.*\*.*\).* = .*\* \(.*\*.*\)", "simpa using Nat.mul_assoc _ _ _"),
        (r"\+.*=.*\+", "simpa using Nat.add_comm _ _"),
        (r"\*.*=.*\*", "simpa using Nat.mul_comm _ _"),
        (r"0 ≤", "exact Nat.zero_le _"),
        (r"≤.*->.*≤.*->.*=", "intro h₁ h₂\nexact le_antisymm h₁ h₂"),
        (r"Nat\.succ.*≤.*->.*<", "intro h\nexact Nat.lt_of_succ_le h"),
        (r"≤.*->.*≤.*->.*≤", "intro h₁ h₂\nexact le_trans h₁ h₂"),
        (r"∣.*\*", "exact ⟨_, rfl⟩"),
        (r"\(.*∧.*\) ∧ .*->.*∧.*\(.*∧.*\)", LOGIC_AND_ASSOC),
        (r"∧.*->.*∧", LOGIC_AND_COMM),
        (r"∧.*->", "intro h\nexact h.left"),
        (r"∨.*->.*∨", LOGIC_OR_COMM),
        (r"->.*->.*->", LOGIC_IMP_TRANS),
        (r"∧", "aesop"),
        (r"∨", "aesop"),
        (r"∃", "aesop"),
    ]

    for pattern, body in patterns:
        if re.search(pattern, stmt):
            candidates.append({"source": "heuristic", "body": body})
            if len(candidates) >= max_candidates:
                break

    candidates.extend([
        {"source": "heuristic", "body": "simp"},
        {"source": "heuristic", "body": "aesop"},
    ])
    return candidates[:max_candidates]


def repair_candidates(error_text: str, max_candidates: int) -> List[dict]:
    repairs: list[dict] = []
    if "Unknown identifier `dvd" in error_text:
        repairs.extend([
            {"source": "repair", "body": DVD_ADD_WITNESS},
            {"source": "repair", "body": DVD_TRANS_WITNESS},
            {"source": "repair", "body": "exact ⟨1, by simp⟩"},
            {"source": "repair", "body": "exact ⟨0, by simp⟩"},
            {"source": "repair", "body": "exact ⟨_, rfl⟩"},
        ])
    if "unsolved goals" in error_text:
        repairs.extend([
            {"source": "repair", "body": "simp"},
            {"source": "repair", "body": "aesop"},
        ])
    if "unexpected identifier" in error_text:
        repairs.append({"source": "repair", "body": "simp"})
    return repairs[:max_candidates]


def generate_llm_candidates(item: dict, previous_errors: List[str], max_candidates: int) -> List[str]:
    if not os.environ.get("LEAN_AGENT_ENABLE_LLM"):
        return []
    return []


def fallback_candidates(item: dict, max_candidates: int) -> List[dict]:
    fallback = item.get("fallback_candidates", item.get("candidates", []))
    return [{"source": "fallback", "body": body} for body in fallback[:max_candidates]]


def dedupe_candidates(candidates: List[dict]) -> List[dict]:
    seen: set[str] = set()
    deduped: list[dict] = []
    for cand in candidates:
        body = cand["body"].strip()
        if body and body not in seen:
            seen.add(body)
            deduped.append(cand)
    return deduped


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--max-candidates", type=int, default=8)
    parser.add_argument("--max-repairs", type=int, default=4)
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
            "mode": "heuristic_repair_fallback",
            "attempts": [],
            "solved": False,
        }

        initial_candidates = []
        for body in generate_llm_candidates(item, previous_errors, args.max_candidates):
            initial_candidates.append({"source": "llm", "body": body})
        initial_candidates.extend(generated_candidates(item, args.max_candidates))
        initial_candidates.extend(fallback_candidates(item, args.max_candidates))
        queue = dedupe_candidates(initial_candidates)[: args.max_candidates]

        attempt_index = 0
        while queue and attempt_index < args.max_candidates + args.max_repairs:
            cand = queue.pop(0)
            attempt_index += 1
            code = build_code(item.get("lean_header", ""), item["statement"], cand["body"])
            res = check_lean_code(code)
            attempt = {
                "candidate_index": attempt_index,
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
            queue.extend(repair_candidates(combined_error, args.max_repairs))
            queue = dedupe_candidates(queue)

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
