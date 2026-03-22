"""thin wrappers around `git diff --cached`. isolated so tests can fake the subprocess."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class FileChange:
    path: str
    status: str  # A, M, D, R, C, T...
    old_path: str | None = None  # for renames
    binary: bool = False


@dataclass
class StagedDiff:
    files: list[FileChange] = field(default_factory=list)
    raw: str = ""  # full unified diff (text hunks only)

    @property
    def paths(self) -> list[str]:
        return [f.path for f in self.files]

    @property
    def text_paths(self) -> list[str]:
        return [f.path for f in self.files if not f.binary]


Runner = Callable[[list[str]], str]


def _run(cmd: list[str]) -> str:
    """run a command, return stdout, raise on nonzero."""
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed: {r.stderr.strip()}")
    return r.stdout


def parse_name_status(raw: str) -> list[FileChange]:
    """parse `git diff --cached --name-status` output."""
    files: list[FileChange] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        # rename/copy entries look like `R100\told\tnew`
        if status.startswith(("R", "C")) and len(parts) >= 3:
            files.append(FileChange(path=parts[2], status=status[0], old_path=parts[1]))
        elif len(parts) >= 2:
            files.append(FileChange(path=parts[1], status=status[0]))
    return files


def mark_binary(files: list[FileChange], raw_diff: str) -> list[FileChange]:
    """flag binary files based on `Binary files ... differ` markers."""
    binaries: set[str] = set()
    for line in raw_diff.splitlines():
        if line.startswith("Binary files ") and " differ" in line:
            # crude but works: `Binary files a/foo b/foo differ`
            rest = line[len("Binary files ") : -len(" differ")]
            # split on ` and ` — last path is b/<path>
            if " and " in rest:
                b_side = rest.split(" and ", 1)[1]
                if b_side.startswith("b/"):
                    binaries.add(b_side[2:])
    for f in files:
        if f.path in binaries:
            f.binary = True
    return files


def get_staged(runner: Runner = _run) -> StagedDiff:
    """collect staged changes. runner is injectable for tests."""
    name_status = runner(["git", "diff", "--cached", "--name-status"])
    raw = runner(["git", "diff", "--cached"])
    files = parse_name_status(name_status)
    files = mark_binary(files, raw)
    return StagedDiff(files=files, raw=raw)
