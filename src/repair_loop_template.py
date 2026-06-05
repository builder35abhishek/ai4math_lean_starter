"""Template for a Lean proof repair loop.

The starter kit does not include API keys or model calls. Add your own model
provider in `generate_candidate` / `repair_candidate`.
"""

from __future__ import annotations

from lean_runner import check_lean_code


def generate_candidate(informal: str, lean_statement: str) -> str:
    """Replace this with an LLM call or local model."""
    # Very weak default: ask Lean's simplifier to try.
    return "  simp"


def repair_candidate(code: str, stderr: str) -> str:
    """Replace this with an LLM repair step using the Lean error message."""
    # Placeholder: no repair.
    return code


def prove_with_repair(informal: str, lean_statement: str, max_rounds: int = 3):
    proof_body = generate_candidate(informal, lean_statement)
    code = lean_statement.rstrip() + "\n" + proof_body.rstrip() + "\n"

    for round_idx in range(max_rounds):
        result = check_lean_code(code)
        if result.ok:
            return {"ok": True, "round": round_idx + 1, "code": code, "stderr": ""}
        code = repair_candidate(code, result.stderr)

    return {"ok": False, "round": max_rounds, "code": code, "stderr": result.stderr}
