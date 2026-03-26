"""build the final conventional-commit string."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .detect import DiffStats, guess_action
from .diff import StagedDiff

SUBJECT_MAX = 60


@dataclass
class CommitMessage:
    type: str
    scope: str | None
    subject: str
    body: str | None = None

    def render(self) -> str:
        head = self.type
        if self.scope:
            head = f"{self.type}({self.scope})"
        out = f"{head}: {self.subject}"
        if self.body:
            out += "\n\n" + self.body
        return out


def build_subject(diff: StagedDiff, stats: DiffStats, commit_type: str) -> str:
    verb, obj = guess_action(diff, stats, commit_type)
    subject = f"{verb} {obj}".strip()
    subject = subject.lower()
    return _clip(subject, SUBJECT_MAX)


def _clip(s: str, limit: int) -> str:
    if len(s) <= limit:
        return s
    # try to cut at a word boundary
    cut = s[:limit].rsplit(" ", 1)[0]
    if len(cut) < limit // 2:  # pathological long word
        cut = s[:limit]
    return cut.rstrip(" ,.;:")


def build_body(diff: StagedDiff, stats: DiffStats) -> str | None:
    bullets: list[str] = []
    for sym in _dedupe(stats.new_symbols)[:6]:
        bullets.append(f"- add {sym}")
    # list up to 6 files (minus the ones we already captured via symbols)
    shown_paths = [f.path for f in diff.files][:6]
    for p in shown_paths:
        label = _status_label(diff, p)
        bullets.append(f"- {label} {p}")
    if not bullets:
        return None
    return "\n".join(bullets)


def _status_label(diff: StagedDiff, path: str) -> str:
    for f in diff.files:
        if f.path == path:
            return {
                "A": "new",
                "M": "edit",
                "D": "remove",
                "R": "rename",
                "C": "copy",
                "T": "chmod",
            }.get(f.status, "touch")
    return "touch"


def _dedupe(items):
    seen = set()
    out = []
    for i in items:
        if i in seen:
            continue
        seen.add(i)
        out.append(i)
    return out


def assemble(
    commit_type: str,
    scope: str | None,
    diff: StagedDiff,
    stats: DiffStats,
    include_body: bool = False,
) -> CommitMessage:
    subject = build_subject(diff, stats, commit_type)
    body = build_body(diff, stats) if include_body else None
    return CommitMessage(type=commit_type, scope=scope, subject=subject, body=body)
