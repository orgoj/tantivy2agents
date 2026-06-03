# TODO

This file tracks open work only. Completed items belong in `CHANGELOG.md`.

## Refactor Roadmap

Work in order. Do not start the structural refactor while the basic behavior and
test baseline are ambiguous.

## Assumptions and Non-Goals

- Default search result limit is intentionally `5`, not `10`.
- Do not delete ignored local artifacts (`.venv/`, caches, local agent settings)
  just for cleanliness.
- Do not restore duplicate `.claude/skills` docs; packaged skills are the source
  of truth.
- Do not add command groups unless there is a separate approved design.
- Do not refactor unrelated code while fixing tests or defaults.

## Phase 1: Test Suite Stabilization

## Phase 2: Error Handling Cleanup

## Phase 3: Decompose `agent.py`

### 3.4 Keep skill docs packaged only

**Problem:** The previous `.claude/skills` duplicate docs created two sources of
truth.

**Goal:** Keep the package skills as the only source used by `skill-usage` and
`skill-setup`.

**Files:**
- `src/tantivy2agents/agent.py`
- `src/tantivy2agents/skills/*/SKILL.md`
- `pyproject.toml`
- `tests/test_skill_commands.py`

**Acceptance criteria:**
- `_find_skill_file()` only resolves package skill files.
- `pyproject.toml` includes packaged skills in wheel/sdist.
- No `.claude/skills` fallback is restored.
- Skill command tests pass from source checkout and installed package context.

**Verification:**
- `uv run python tests/test_skill_commands.py`
- `uv build`

## Phase 4: CLI and UX Polish

### 4.1 Reduce default output verbosity

**Problem:** Search output can consume too many tokens for agent workflows.

**Goal:** Keep defaults compact and make extra detail opt-in.

**Files:**
- `src/tantivy2agents/cli.py`
- `src/tantivy2agents/agent.py`
- `src/tantivy2agents/skills/tantivy2agents-usage/SKILL.md`
- `README.md`
- `tests/`

**Acceptance criteria:**
- Default search result count is `5`.
- Current default text output is reviewed against token cost and documented.
- Any change to fields shown by default has an explicit before/after example in
  tests and docs.
- JSON output remains complete enough for machine use.
- No output format redesign is bundled into the `default_limit` fix.

**Verification:**
- Exact-output tests for one representative text search result.
- `uv run python tests/test_basic.py`

### 4.2 Clarify command boundaries

**Problem:** Some commands are user-facing (`search`, `index`, `status`) while
others are internal or documentation helpers (`hook-clear`, `skill-*`).

**Goal:** Make help text and docs clear without adding command groups.

**Files:**
- `src/tantivy2agents/cli.py`
- `README.md`
- packaged skill docs

**Acceptance criteria:**
- `--help` clearly describes public commands.
- `hook-clear` is marked as hook/internal support.
- `skill-usage` and `skill-setup` are described as packaged docs.
- No new command groups unless there is a separate approved design.

**Verification:**
- `uv run tantivy2agents --help`
- `uv run python tests/test_typer_cli.py`

## Phase 5: Safety and Maintenance

### 5.1 Add safe path handling for destructive/output operations

**Problem:** Local CLI tools can still damage user files through accidents:
unsafe output paths, symlinked index dirs, or broad configured paths.

**Goal:** Add pragmatic local safety checks for operations that can overwrite or
delete files. This is accident prevention for a local CLI, not web security.

**Files:**
- `src/tantivy2agents/agent.py`
- extracted config/files modules after Phase 3
- `tests/`

**Acceptance criteria:**
- `clear` does not follow symlinked index directories destructively.
- Output paths outside the project are rejected unless an explicit opt-in flag is
  added and documented.
- Suspicious absolute/parent-traversal index patterns fail clearly.
- Behavior is documented in README or setup skill.

**Verification:**
- Add tests using temp dirs and symlinks where supported by the platform.
- `uv run python run_tests.py`

### 5.2 Keep repository hygiene simple

**Problem:** Agent/session files, cache directories, and generated test fixtures
should not become project documentation.

**Goal:** Keep git-tracked files focused on code, tests, package metadata, and
current docs.

**Files:**
- `.gitignore`
- `README.md`
- `TODO.md`

**Acceptance criteria:**
- Ignored temp/cache/local agent files may exist locally and are not repeatedly
  deleted just for cleanliness.
- `git ls-files --others --exclude-standard` is empty before commits.
- Markdown docs remain limited to current project docs and packaged CLI docs.

**Verification:**
- `git status --short`
- `git ls-files --others --exclude-standard`
