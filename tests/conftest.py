"""shared fixtures. keep these tiny — each test should read its own diff string."""

import pytest

from commitgen.diff import StagedDiff, mark_binary, parse_name_status


def make_diff(name_status: str, raw: str = "") -> StagedDiff:
    files = parse_name_status(name_status)
    files = mark_binary(files, raw)
    return StagedDiff(files=files, raw=raw)


@pytest.fixture
def build():
    return make_diff
