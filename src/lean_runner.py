"""Lean 4 runner.

This module writes candidate Lean code to a temporary file and invokes the
local `lean` binary. A proof is accepted if Lean exits with status 0.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


@dataclass
class LeanCheckResult:
    ok: bool
    returncode: int
    stdout: str
    stderr: str
    code: str
    lean_path: Optional[str]

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


def lean_available() -> bool:
    return shutil.which("lean") is not None


def check_lean_code(code: str, timeout_s: int = 20) -> LeanCheckResult:
    lean_path = shutil.which("lean")
    if lean_path is None:
        return LeanCheckResult(
            ok=False,
            returncode=127,
            stdout="",
            stderr="Lean executable not found. Install Lean 4 via elan and ensure `lean` is on PATH.",
            code=code,
            lean_path=None,
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "Candidate.lean"
        path.write_text(code, encoding="utf-8")
        try:
            proc = subprocess.run(
                [lean_path, str(path)],
                text=True,
                capture_output=True,
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired as exc:
            return LeanCheckResult(
                ok=False,
                returncode=124,
                stdout=exc.stdout or "",
                stderr=(exc.stderr or "") + f"\nTimed out after {timeout_s}s.",
                code=code,
                lean_path=lean_path,
            )

    return LeanCheckResult(
        ok=proc.returncode == 0,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        code=code,
        lean_path=lean_path,
    )
