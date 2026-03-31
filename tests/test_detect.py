"""heuristic detection tests. plug in fake diff strings, assert type/scope."""

import textwrap

from commitgen.detect import compute_stats, detect_scope, detect_type


def test_docs_only_readme(build):
    diff = build("M\tREADME.md", "diff --git a/README.md b/README.md\n@@ -1 +1 @@\n-old\n+new\n")
    assert detect_type(diff) == "docs"


def test_docs_with_markdown_in_docs_dir(build):
    diff = build("M\tdocs/intro.md\nM\tREADME.md", "@@\n+hello\n")
    assert detect_type(diff) == "docs"


def test_ci_workflow(build):
    diff = build("M\t.github/workflows/ci.yml", "@@\n+- run: pytest\n")
    assert detect_type(diff) == "ci"


def test_ci_dockerfile(build):
    diff = build("M\tDockerfile", "@@\n+RUN pip install -e .\n")
    assert detect_type(diff) == "ci"


def test_tests_only_python(build):
    diff = build("A\ttests/test_foo.py", "@@\n+def test_bar():\n+    assert True\n")
    assert detect_type(diff) == "test"


def test_tests_go_suffix(build):
    diff = build("A\tpkg/auth/login_test.go", "@@\n+func TestLogin(t *testing.T) {}\n")
    assert detect_type(diff) == "test"


def test_chore_manifest_only(build):
    diff = build("M\tpyproject.toml", "@@\n+dependencies = ['click']\n")
    assert detect_type(diff) == "chore"


def test_feat_new_function(build):
    raw = textwrap.dedent(
        """\
        diff --git a/src/app/auth.py b/src/app/auth.py
        @@ -0,0 +1,8 @@
        +def login(user):
        +    return True
        +
        +def logout(user):
        +    return True
        +
        +class Session:
        +    pass
        """
    )
    diff = build("A\tsrc/app/auth.py", raw)
    stats = compute_stats(diff)
    assert stats.new_symbols == ["login", "logout", "Session"]
    assert detect_type(diff, stats) == "feat"


def test_fix_small_change_in_fix_path(build):
    raw = "diff --git a/src/bugfix/parser.py b/src/bugfix/parser.py\n@@ -1 +1 @@\n-a\n+b\n"
    diff = build("M\tsrc/bugfix/parser.py", raw)
    assert detect_type(diff) == "fix"


def test_fix_small_deletion(build):
    raw = "diff --git a/src/core/io.py b/src/core/io.py\n@@ -1,2 +1 @@\n-old_line\n-another\n+one\n"
    diff = build("M\tsrc/core/io.py", raw)
    assert detect_type(diff) == "fix"


def test_style_whitespace_only(build):
    raw = "diff --git a/src/core/x.py b/src/core/x.py\n@@ -1 +1 @@\n-    \n+\t\n"
    diff = build("M\tsrc/core/x.py", raw)
    stats = compute_stats(diff)
    assert stats.only_whitespace is True
    assert detect_type(diff, stats) == "style"


def test_refactor_medium_no_new_symbols(build):
    raw = (
        "diff --git a/src/core/x.py b/src/core/x.py\n@@\n"
        + "\n".join(["+added " + str(i) for i in range(6)])
        + "\n"
        + "\n".join(["-removed " + str(i) for i in range(6)])
        + "\n"
    )
    diff = build("M\tsrc/core/x.py", raw)
    assert detect_type(diff) == "refactor"


def test_chore_fallback_tiny_diff(build):
    raw = "diff --git a/src/core/x.py b/src/core/x.py\n@@\n+ok\n"
    diff = build("M\tsrc/core/x.py", raw)
    # 1 added line, no symbols, not in a fix path → chore
    assert detect_type(diff) == "chore"


def test_scope_from_src_dir(build):
    diff = build("A\tsrc/auth/login.py\nA\tsrc/auth/session.py", "")
    assert detect_scope(diff) == "auth"


def test_scope_spans_multiple_roots(build):
    diff = build("A\tsrc/auth/login.py\nA\tsrc/billing/invoice.py", "")
    assert detect_scope(diff) is None


def test_scope_single_file_at_root(build):
    diff = build("M\tREADME.md", "")
    assert detect_scope(diff) is None


def test_scope_strips_pkg_prefix(build):
    diff = build("A\tpkg/auth/login.go\nA\tpkg/auth/session.go", "")
    assert detect_scope(diff) == "auth"


def test_scope_slugifies(build):
    diff = build("A\tsrc/My Module/foo.py\nA\tsrc/My Module/bar.py", "")
    assert detect_scope(diff) == "my-module"


def test_compute_stats_counts(build):
    raw = "diff --git a/x.py b/x.py\n@@\n+one\n+two\n-gone\n"
    diff = build("M\tx.py", raw)
    stats = compute_stats(diff)
    assert stats.added == 2
    assert stats.removed == 1


def test_binary_files_marked(build):
    raw = "diff --git a/logo.png b/logo.png\nBinary files a/logo.png and b/logo.png differ\n"
    diff = build("M\tlogo.png", raw)
    assert diff.files[0].binary is True


def test_empty_diff_is_chore(build):
    diff = build("", "")
    assert detect_type(diff) == "chore"
