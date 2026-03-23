"""type + scope detection. pure functions, no subprocess — feed them a StagedDiff."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from .diff import StagedDiff

VALID_TYPES = ("feat", "fix", "chore", "refactor", "docs", "test", "style", "perf", "ci")

_TEST_PATH_RE = re.compile(r"(^|/)(tests?/|test_[^/]+\.py$|[^/]+_test\.(go|py|ts|js)$|[^/]+\.test\.(ts|tsx|js|jsx)$)")
_DOC_PATH_RE = re.compile(r"(^|/)(docs/|README(\.[a-z]+)?$|CHANGELOG(\.[a-z]+)?$|LICENSE$|[^/]+\.md$)", re.IGNORECASE)
_CI_PATH_RE = re.compile(r"(^\.github/workflows/|^\.gitlab-ci\.ya?ml$|(^|/)Dockerfile$|(^|/)docker-compose\.ya?ml$|^\.circleci/|^\.travis\.ya?ml$)")
_MANIFEST_RE = re.compile(r"(^|/)(pyproject\.toml|package(-lock)?\.json|Cargo\.(toml|lock)|go\.(mod|sum)|Gemfile(\.lock)?|pnpm-lock\.yaml|yarn\.lock|uv\.lock|poetry\.lock|requirements[^/]*\.txt)$")
_SYMBOL_RE = re.compile(r"^\+\s*(?:async\s+)?(?:def|class|fn|func|function|pub\s+fn|impl)\s+([A-Za-z_][A-Za-z0-9_]*)")
_FIXY_WORDS = re.compile(r"\b(fix|bug|patch|hotfix|issue|broken|crash|err|regression)\b", re.IGNORECASE)


@dataclass
class DiffStats:
    added: int = 0
    removed: int = 0
    new_symbols: list[str] = None  # type: ignore
    removed_symbols: list[str] = None  # type: ignore
    only_whitespace: bool = True
    touches_fix_path: bool = False

    def __post_init__(self):
        if self.new_symbols is None:
            self.new_symbols = []
        if self.removed_symbols is None:
            self.removed_symbols = []


def compute_stats(diff: StagedDiff) -> DiffStats:
    stats = DiffStats()
    in_hunk = False
    for line in diff.raw.splitlines():
        if line.startswith("@@"):
            in_hunk = True
            continue
        if line.startswith(("diff --git", "index ", "---", "+++", "Binary files")):
            in_hunk = False
            continue
        if not in_hunk:
            continue
        if line.startswith("+"):
            stats.added += 1
            content = line[1:]
            if content.strip():
                stats.only_whitespace = False
            m = _SYMBOL_RE.match(line)
            if m:
                stats.new_symbols.append(m.group(1))
        elif line.startswith("-"):
            stats.removed += 1
            content = line[1:]
            if content.strip():
                stats.only_whitespace = False
            m = re.match(r"^-\s*(?:async\s+)?(?:def|class|fn|func|function|pub\s+fn|impl)\s+([A-Za-z_][A-Za-z0-9_]*)", line)
            if m:
                stats.removed_symbols.append(m.group(1))
    # if nothing actually changed, don't call it a whitespace-only diff
    if stats.added == 0 and stats.removed == 0:
        stats.only_whitespace = False
    stats.touches_fix_path = any(_FIXY_WORDS.search(p) for p in diff.paths)
    return stats


def _all_match(paths: list[str], regex: re.Pattern) -> bool:
    return bool(paths) and all(regex.search(p) for p in paths)


def detect_type(diff: StagedDiff, stats: DiffStats | None = None) -> str:
    """return a conventional-commit type based on paths + diff shape."""
    paths = diff.text_paths or diff.paths
    if not paths:
        return "chore"
    stats = stats or compute_stats(diff)

    if _all_match(paths, _TEST_PATH_RE):
        return "test"
    if _all_match(paths, _DOC_PATH_RE):
        return "docs"
    if _all_match(paths, _CI_PATH_RE):
        return "ci"
    if _all_match(paths, _MANIFEST_RE):
        return "chore"

    # whitespace-only: style
    if stats.only_whitespace and (stats.added + stats.removed) > 0:
        return "style"

    # fixy signals: touches a "fix"-flavored path, or a tiny surgical edit with deletions
    tiny = (stats.added + stats.removed) <= 4
    if not stats.new_symbols and (stats.touches_fix_path or (tiny and stats.removed > 0)):
        return "fix"

    # feat: meaningful net-new symbols or decent chunk of additions
    if stats.new_symbols and stats.added >= max(2, stats.removed // 2):
        return "feat"
    if stats.added >= 40 and stats.added > stats.removed * 2:
        return "feat"

    # refactor vs chore fallback
    if stats.added + stats.removed >= 10:
        return "refactor"
    return "chore"


def detect_scope(diff: StagedDiff) -> str | None:
    """first shared directory segment across all changed files, ignoring noise."""
    paths = [p for p in diff.paths if p]
    if not paths:
        return None

    # strip top-level scaffolding that would mask the real scope
    cleaned: list[str] = []
    strip_prefixes = ("src/", "lib/", "app/", "pkg/", "internal/")
    for p in paths:
        for pref in strip_prefixes:
            if p.startswith(pref):
                p = p[len(pref) :]
                break
        cleaned.append(p)

    # if any path has no directory, we can't agree on a scope
    segs: list[str] = []
    for p in cleaned:
        if "/" not in p:
            return None
        segs.append(p.split("/", 1)[0])

    first = segs[0]
    if not all(s == first for s in segs):
        return None
    # skip scopes that are just junk
    if first in ("", ".", "..") or first.startswith("."):
        return None
    # keep the scope short and sluggy
    scope = re.sub(r"[^a-z0-9]+", "-", first.lower()).strip("-")
    return scope or None


def primary_new_symbol(stats: DiffStats) -> str | None:
    return stats.new_symbols[0] if stats.new_symbols else None


def guess_action(diff: StagedDiff, stats: DiffStats, commit_type: str) -> tuple[str, str]:
    """return (verb, object) used to build the subject line."""
    # pick a decent object: first new symbol, else first file's basename, else "stuff"
    sym = primary_new_symbol(stats)
    if sym:
        obj = _humanize(sym)
    elif diff.files:
        first = diff.files[0]
        obj = os.path.basename(first.path)
        obj = re.sub(r"\.[a-z0-9]+$", "", obj, flags=re.IGNORECASE)
        obj = _humanize(obj) or obj
    else:
        obj = "things"

    verb_map = {
        "feat": "add",
        "fix": "fix",
        "docs": "update",
        "test": "add tests for",
        "ci": "update",
        "style": "tidy",
        "refactor": "refactor",
        "perf": "speed up",
        "chore": "update",
    }
    verb = verb_map.get(commit_type, "update")

    # if it's a feat but the only "new symbol" is literally `__init__`, soften
    if commit_type == "feat" and sym in {"__init__", "main"}:
        verb = "wire up"

    # if everything is deletions, flip the verb
    if stats.removed > 0 and stats.added == 0:
        verb = "remove"

    return verb, obj


def _humanize(name: str) -> str:
    """turn CamelCase / snake_case into space-separated lowercase."""
    if not name:
        return name
    s = re.sub(r"(?<!^)(?=[A-Z])", " ", name)
    s = s.replace("_", " ")
    return s.strip().lower()
