"""Lean 4 runner.

This module writes candidate Lean code to a temporary file and invokes Lean.
By default it runs the local `lean` binary. For Mathlib/Lake projects, set:

    LEAN_CMD="lake env lean"

A proof is accepted if the command exits with status 0.
"""

from __future__ import annotations

import json
import os
import shlex
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


def lean_command() -> list[str]:
    cmd = os.environ.get("LEAN_CMD", "lean")
    return shlex.split(cmd)


def lean_available() -> bool:
    cmd = lean_command()
    if not cmd:
        return False
    return shutil.which(cmd[0]) is not None


def check_lean_code(code: str, timeout_s: int = 20) -> LeanCheckResult:
    cmd = lean_command()
    if not cmd or shutil.which(cmd[0]) is None:
        return LeanCheckResult(
            ok=False,
            returncode=127,
            stdout="",
            stderr=(
                "Lean executable not found. Install Lean 4 via elan and ensure `lean` is on PATH. "
                "For Mathlib, set LEAN_CMD='lake env lean'."
            ),
            code=code,
            lean_path=None,
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "Candidate.lean"
        path.write_text(code, encoding="utf-8")
        try:
            proc = subprocess.run(
                [*cmd, str(path)],
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
                lean_path=" ".join(cmd),
            )

    return LeanCheckResult(
        ok=proc.returncode == 0,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        code=code,
        lean_path=" ".join(cmd),
    )
