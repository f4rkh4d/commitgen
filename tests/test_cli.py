"""end-to-end-ish cli tests. we stub the git subprocess via monkeypatch."""

from click.testing import CliRunner

from commitgen import cli as cli_mod
from commitgen.cli import main
from commitgen.diff import StagedDiff, mark_binary, parse_name_status


def _fake_getter(name_status: str, raw: str):
    def _inner():
        files = mark_binary(parse_name_status(name_status), raw)
        return StagedDiff(files=files, raw=raw)

    return _inner


def test_cli_empty_exits_one(monkeypatch):
    monkeypatch.setattr(cli_mod, "get_staged", _fake_getter("", ""))
    result = CliRunner().invoke(main, [])
    assert result.exit_code == 1
    assert "nothing staged" in result.output.lower()


def test_cli_prints_feat(monkeypatch):
    raw = "diff --git a/src/auth/login.py b/src/auth/login.py\n@@\n+def login():\n+    return True\n"
    monkeypatch.setattr(cli_mod, "get_staged", _fake_getter("A\tsrc/auth/login.py", raw))
    result = CliRunner().invoke(main, [])
    assert result.exit_code == 0
    assert "feat" in result.output
    assert "auth" in result.output
    assert "login" in result.output


def test_cli_no_scope_flag(monkeypatch):
    raw = "@@\n+def login():\n+    pass\n"
    monkeypatch.setattr(cli_mod, "get_staged", _fake_getter("A\tsrc/auth/login.py", raw))
    result = CliRunner().invoke(main, ["--no-scope"])
    assert result.exit_code == 0
    assert "(auth)" not in result.output


def test_cli_force_type(monkeypatch):
    raw = "@@\n+def login():\n+    pass\n"
    monkeypatch.setattr(cli_mod, "get_staged", _fake_getter("A\tsrc/auth/login.py", raw))
    result = CliRunner().invoke(main, ["--type", "chore"])
    assert result.exit_code == 0
    assert result.output.lstrip().startswith("chore")


def test_cli_body_flag(monkeypatch):
    raw = "@@\n+def login():\n+    pass\n+def logout():\n+    pass\n"
    monkeypatch.setattr(cli_mod, "get_staged", _fake_getter("A\tsrc/auth/login.py", raw))
    result = CliRunner().invoke(main, ["--body"])
    assert result.exit_code == 0
    assert "- add login" in result.output
    assert "- add logout" in result.output
