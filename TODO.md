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

### 1.3 Add coverage for user-facing options

**Problem:** TODO coverage gaps remain around important CLI flags and edge cases.

**Goal:** Lock down command behavior before changing internals.

**Files:**
- `tests/test_basic.py`
- `tests/test_typer_cli.py`

**Acceptance criteria:**
- `search --output` is tested for `text`, `json`, and `csv`.
- `index --dirs` and `index --files` are tested.
- Missing index behavior is tested for text and JSON error modes.
- Empty/non-existent index edge cases are explicit.
- `search --limit` min/max Typer validation remains covered.

**Verification:**
- `uv run python tests/test_basic.py`
- `uv run python tests/test_typer_cli.py`

## Phase 2: Error Handling Cleanup

### 2.1 Replace user-facing error prints with structured exceptions

**Problem:** `agent.py` still mixes normal output, error `print()`, returns, and
`sys.exit(1)`. This makes JSON errors inconsistent and makes CLI behavior harder
to test.

**Goal:** Use `CLIError` subclasses for user-facing failures while keeping normal
command output as plain output.

**Files:**
- `src/tantivy2agents/agent.py`
- `src/tantivy2agents/exceptions.py`
- `src/tantivy2agents/cli.py`
- `tests/test_basic.py`
- `tests/test_typer_cli.py`

**Acceptance criteria:**
- Malformed config raises `ConfigError`.
- Missing index during `search` raises `IndexNotFoundError`.
- Missing packaged skill docs raise a structured file/system error.
- Unsupported formats cannot reach `agent.py` in normal CLI usage; direct calls
  still fail clearly.
- `TANTIVY_JSON_OUTPUT=true` returns machine-readable errors for these cases.
- Normal informational output from successful `index`, `status`, `install`,
  `encoding-info`, and `list` is preserved.

**Verification:**
- `uv run python run_tests.py`
- Add focused JSON error tests in `tests/test_typer_cli.py`.

### 2.2 Remove direct `sys.exit()` from library-like code

**Problem:** `sys.exit()` inside `TantivyAgent` makes direct unit tests and reuse
harder.

**Goal:** Keep process exits in the CLI entrypoint only.

**Files:**
- `src/tantivy2agents/agent.py`
- `src/tantivy2agents/cli.py`
- `src/tantivy2agents/exceptions.py`

**Acceptance criteria:**
- `TantivyAgent` methods raise exceptions instead of exiting the process.
- `cli.main()` remains responsible for formatting `CLIError` and exiting.
- Unit tests can call agent methods without catching `SystemExit` except where
  testing the CLI wrapper itself.

**Verification:**
- `rg -n 'sys\\.exit' src/tantivy2agents`
- `uv run python run_tests.py`

## Phase 3: Decompose `agent.py`

### 3.1 Extract configuration loading and validation

**Problem:** Config defaults, loading, validation, examples, and install-time
generation are spread through a large `TantivyAgent` class.

**Goal:** Move config behavior behind a small, testable module.

**Files:**
- new `src/tantivy2agents/config.py`
- `src/tantivy2agents/agent.py`
- `tests/`

**Acceptance criteria:**
- Default config is defined in one place.
- Validation errors use structured exceptions.
- `config-example`, install-created config, and agent defaults agree.
- Default result limit remains `5`.
- Existing config file format remains backwards compatible.

**Verification:**
- `uv run python run_tests.py`
- Add direct config unit tests.

### 3.2 Extract file discovery and path filtering

**Problem:** File collection, glob expansion, includes/excludes, encoding skips,
and project-root assumptions are mixed with indexing.

**Goal:** Create a focused file discovery module that can be tested without
building a Tantivy index.

**Files:**
- new `src/tantivy2agents/files.py`
- `src/tantivy2agents/agent.py`
- `tests/test_basic.py`
- `tests/test_encoding.py`

**Acceptance criteria:**
- Include/exclude behavior is unchanged.
- Empty directories and ignored build/cache directories do not leak into results.
- `list`, `index --dirs`, and `index --files` share the same discovery logic.
- Tests cover glob patterns, directory objects, excludes, and binary skips.

**Verification:**
- `uv run python tests/test_basic.py`
- `uv run python tests/test_encoding.py`

### 3.3 Extract search result formatting/export

**Problem:** Search, filtering, field extraction, and output writers are tightly
coupled.

**Goal:** Make result formatting/export deterministic and directly testable.

**Files:**
- new `src/tantivy2agents/output.py`
- `src/tantivy2agents/agent.py`
- `tests/test_basic.py`
- `tests/test_typer_cli.py`

**Acceptance criteria:**
- Text, JSON, and CSV output match existing public behavior.
- `show_description` works consistently across all formats.
- Missing Tantivy fields produce empty strings, not crashes.
- `search --output` writes exactly the requested format.

**Verification:**
- `uv run python tests/test_basic.py`
- `uv run python tests/test_typer_cli.py`

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
