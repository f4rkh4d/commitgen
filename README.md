# commitgen


![demo](docs/hero.gif)
conventional-commit messages from your staged diff. no llm, no api key, no tokens. just regexes and path matching.

## what it is

i got tired of writing `chore: stuff` at 2am, and i didn't want to pipe my diff to a model every time i make a commit. so this is about 400 lines of python that reads `git diff --cached`, runs a pile of rules over it, and prints something like `feat(auth): add login flow`. heuristics are dumb but mostly right, which is the bar i set.

## install

```
pip install git+https://github.com/f4rkh4d/commitgen
```

needs python 3.10+ and git on your PATH.

## usage

```
$ git add src/auth/login.py
$ commitgen
feat(auth): add login

$ commitgen --body
feat(auth): add login

- add login
- new src/auth/login.py

$ commitgen --no-scope
feat: add login

$ commitgen --type chore
chore: add login

$ commitgen --commit
# runs `git commit -m "feat(auth): add login"` for you
```

if nothing is staged, it exits 1 and tells you to `git add` something. reasonable.

## how it decides

- if every changed file is under `tests/`, or matches `test_*.py` / `*_test.go` / `*.test.ts`, it's `test`
- if every file is `*.md`, `README`, `docs/`, `LICENSE` or `CHANGELOG`, it's `docs`
- workflows under `.github/workflows/`, `Dockerfile`, `.gitlab-ci.yml`, CircleCI, Travis → `ci`
- only manifests like `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, lockfiles → `chore`
- whitespace-only diff → `style`
- no new symbols + small diff + path has words like "fix"/"bug"/"patch" → `fix`
- new `def`/`class`/`fn`/`func` added and decent additions → `feat`
- nothing obvious, medium-sized diff → `refactor`
- fallback → `chore`

scope comes from the longest shared first-directory segment across staged files, ignoring a top-level `src/`, `lib/`, `app/`, `pkg/`, `internal/`. if files span multiple roots you don't get a scope. subject line picks the first newly-added symbol and humanizes it (`UserSession` → `user session`). 60-char cap.

## honest caveats

- heuristics are dumb. if you've got 50 files staged across 5 concerns, it'll pick one and look confused.
- the subject line is a guess from the first new symbol. if that symbol is `__init__`, you'll get something lukewarm.
- i haven't tested on windows. pretty sure subprocess + git work there but i'm not volunteering.
- binary diffs are skipped from analysis. they still count for scope detection.

## dev

```
git clone https://github.com/f4rkh4d/commitgen
cd commitgen
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
pytest -q
```

## license

MIT. see LICENSE.

## example before / after

stage a typical mixed change — touched two files in `src/`, added a test, fixed a typo in a doc — and commitgen produces something like:

```
$ commitgen
chore: tighten parser validation, add regression test

- src/parser.rs: reject empty rule bodies before tokenization
- tests/parser_empty.rs: cover the three obvious bad inputs
- README.md: typo
```

the heuristic is dumb on purpose: count what changed by directory, pick the verb from the dominant change kind (added vs modified vs deleted vs renamed), bullet the path-prefix groups. no LLM, no API, no cost. it gets ~70% of my commits "good enough" to send as-is and the rest i edit by hand, which is faster than typing them from scratch.
