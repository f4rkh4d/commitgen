"""formatter edge cases."""

import textwrap

from commitgen.detect import compute_stats
from commitgen.format import SUBJECT_MAX, assemble, build_subject


def test_basic_feat_with_scope(build):
    raw = "diff --git a/src/auth/login.py b/src/auth/login.py\n@@\n+def login():\n+    pass\n"
    diff = build("A\tsrc/auth/login.py", raw)
    stats = compute_stats(diff)
    msg = assemble("feat", "auth", diff, stats, include_body=False)
    assert msg.render() == "feat(auth): add login"


def test_no_scope_rendering(build):
    raw = "@@\n+def hello():\n+    pass\n"
    diff = build("A\tx.py", raw)
    stats = compute_stats(diff)
    msg = assemble("feat", None, diff, stats)
    assert msg.render() == "feat: add hello"


def test_subject_is_clipped(build):
    long_name = "a_really_really_really_really_really_really_really_really_long_function"
    raw = f"@@\n+def {long_name}():\n+    pass\n"
    diff = build("A\tx.py", raw)
    stats = compute_stats(diff)
    subject = build_subject(diff, stats, "feat")
    assert len(subject) <= SUBJECT_MAX


def test_body_lists_new_symbols(build):
    raw = textwrap.dedent(
        """\
        @@
        +def login():
        +    pass
        +def logout():
        +    pass
        """
    )
    diff = build("A\tsrc/auth/login.py", raw)
    stats = compute_stats(diff)
    msg = assemble("feat", "auth", diff, stats, include_body=True)
    rendered = msg.render()
    assert "- add login" in rendered
    assert "- add logout" in rendered
    assert "- new src/auth/login.py" in rendered


def test_body_omitted_when_nothing_to_say(build):
    # empty diff → no body content
    diff = build("", "")
    stats = compute_stats(diff)
    msg = assemble("chore", None, diff, stats, include_body=True)
    assert msg.body is None


def test_humanizes_camelcase(build):
    raw = "@@\n+class UserSession:\n+    pass\n"
    diff = build("A\tsrc/auth/session.py", raw)
    stats = compute_stats(diff)
    subject = build_subject(diff, stats, "feat")
    assert subject == "add user session"


def test_removal_flips_verb(build):
    raw = "diff --git a/x.py b/x.py\n@@\n-old\n-gone\n"
    diff = build("M\tx.py", raw)
    stats = compute_stats(diff)
    subject = build_subject(diff, stats, "refactor")
    assert subject.startswith("remove")


def test_fix_uses_fix_verb(build):
    raw = "diff --git a/src/core/io.py b/src/core/io.py\n@@\n-bad\n+good\n"
    diff = build("M\tsrc/core/io.py", raw)
    stats = compute_stats(diff)
    msg = assemble("fix", "core", diff, stats)
    assert msg.render().startswith("fix(core): fix ")


def test_docs_verb(build):
    diff = build("M\tREADME.md", "@@\n+new line\n")
    stats = compute_stats(diff)
    msg = assemble("docs", None, diff, stats)
    assert msg.render().startswith("docs: update")


def test_force_type_and_scope_combo(build):
    raw = "@@\n+def foo():\n+    pass\n"
    diff = build("M\tsrc/billing/invoice.py", raw)
    stats = compute_stats(diff)
    msg = assemble("perf", "billing", diff, stats)
    assert msg.render() == "perf(billing): speed up foo"


def test_body_lists_renames(build):
    raw = ""
    diff = build("R100\told.py\tnew.py", raw)
    stats = compute_stats(diff)
    msg = assemble("refactor", None, diff, stats, include_body=True)
    assert "- rename new.py" in msg.render()
