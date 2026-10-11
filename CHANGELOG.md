# Changelog

All notable project changes are tracked here.

## Unreleased

### Added
- `search` detects stale indexes without any hook. Every search stats the
  candidate files and compares them with a manifest published inside `idx/`
  (`t2a_state.json`: mtime_ns and size per file, plus a fingerprint of
  `index_dirs`, `global_patterns`, `encoding` and `schema_fields`). Added,
  changed and removed files are re-indexed into a copy of the live index that
  is swapped in with a rename; config changes and a `path` field without the
  `raw` tokenizer fall back to a full rebuild. Files edited during the refresh are picked up before
  the triggering search runs (up to 3 rounds).

### Changed
- `index` without `--force` uses the same incremental refresh and now notices
  new files, restored older mtimes and config changes. `status` reports
  out-of-date from the same check.
- A project with no matching documents gets an empty index instead of none,
  so `search` answers "No results found" instead of an index-not-found error.
- When the file scan hits a permission or I/O error (including an unreadable
  configured root, listed file or wildcard directory), the previous index is
  kept and a warning goes to stderr; files are never dropped from an
  incomplete scan. A file that cannot be read keeps its previous document and
  is retried on the next search. `status` reports "Unknown" in that case.
- A refresh interrupted between moving the old index aside and moving the new
  one in is recovered from the retired copy on the next run.
- `index_info.json` is rewritten when it does not match the live index, so an
  interruption right after publishing heals itself.
- `search` refreshes and queries under one lock acquisition, so a concurrent
  `clear` cannot remove the index in between.
- The `hook-clear` mark now only triggers a check, not a full rebuild. The
  hook is optional.

### Compatibility
- An index written by 0.9.0 has no manifest and is rebuilt fully once.
  `index_info.json` keeps `timestamp`, `files` and `count`, so 0.9.0 can still
  read a data directory written by this version.

- `mise run test` runs `pytest` over all of `tests/`. The old `run_tests.py`
  runner skipped `test_typer_cli.py` and `test_skill_commands.py`.
- File collection is several times faster on large trees: include and
  exclude patterns are compiled once, exclude patterns are checked only for
  included files, overlapping `index_dirs` entries (such as `"."` and `"docs"`)
  walk each subtree once, and a file listed twice is read once. The collected
  file list is unchanged.

## [0.9.0] - 2026-10-10

### Added
- `outline` and `read` commands: agents read indexed documents whole, by
  Markdown section (`--section`, GitHub-style Unicode slugs) or by line range
  (`--lines`, `--numbers`). Only files the current config would index are
  readable.
- Search refs: every search gets a 6-hex id, every result a ref
  `<search_id>:<rank>` that `outline`/`read` accept. Text output gets a `REF:`
  line and a closing `Read:` hint, JSON gets `search_id`, `rank` and `ref`,
  CSV a trailing `Ref` column.
- Usage log `<index_dir>/usage.jsonl` of searches (including zero-result ones)
  and reads, rotated at `usage.max_bytes` (default 5 MB), guarded by its own
  `usage.lock`. Disable with `"usage": {"enabled": false}` or
  `TANTIVY2AGENTS_USAGE=0`.
- `usage` command: read-through rate per rank and query, zero-result queries,
  results not read via tantivy2agents, outlines without a follow-up read,
  most-read sections, never-returned documents (`--format json`,
  `schema_version: 1`). `usage --recent-read PATH --within 30m` checks for a
  recent read of an unchanged file via the exit status.

### Fixed
- `clear` and `hook-clear` no longer delete the usage log together with the
  index.

### Changed
- `uv.lock` now matches what a fresh `uv tool install` resolves. The lock had
  drifted (tantivy 0.25.1 vs 0.26.0 installed, plus rich, typer,
  charset-normalizer and pygments), so the test suite was not exercising the
  versions users actually get.
- `mise run install` uses `uv sync --extra dev`, so it no longer leaves the
  environment without pytest.

### Fixed
- CLI tests no longer rely on `CliRunner.isolated_filesystem`, which typer
  removed in 0.27 along with its click dependency.

## [0.8.0] - 2026-08-24

### Added
- Declared platform support: Linux (x86_64, aarch64), Windows (x86_64) and
  macOS (x86_64, arm64). Windows on ARM is not supported because `tantivy`
  publishes no `win_arm64` wheel. The Windows and macOS paths are implemented
  but have not been exercised on a real machine yet.
- `paths.py` with the path helpers that have to behave the same on POSIX and
  Windows, plus `tests/test_portability.py`, which reproduces Windows path
  rules from POSIX using `ntpath`.

### Fixed
- Every command hung forever on Windows. `_find_project_root` walked up until
  it reached `"/"`, which never happens on Windows because `dirname("C:\\")`
  is `"C:\\"`.
- Search filters compared the configured path prefix verbatim, so a prefix
  written Windows-style (`incidents\`) silently matched nothing and revealed
  paths it was meant to hide.
- An index or `--output` path on another Windows drive raised a bare
  `ValueError` from `commonpath` instead of the intended structured error.
- Error messages crashed with `UnicodeEncodeError` instead of being shown when
  output was redirected to a pipe on a non-UTF-8 console, because of the emoji
  in the human-readable format.
- Index directory swaps retry while the operating system still holds a handle,
  and searches release every index handle before dropping the lock. Windows
  refuses to rename or delete a directory that any process still has open.

### Changed
- The index lock is now taken through `fcntl.flock` on POSIX and
  `msvcrt.locking` on Windows. Both are released by the operating system when
  the process exits, so a killed rebuild can never leave a lock behind.
- The lock is exclusive only; Windows has no shared-mode equivalent. Searches
  therefore serialize against each other, which costs about 1 ms per search on
  a 2000-document index.
- Paths stored in the index always use forward slashes, on every platform.

## [0.7.17] - 2026-08-24

### Fixed
- Parallel `index`/`search` processes no longer corrupt each other's index.
  Concurrent searches over a stale or unopenable index each forced a rebuild
  that deleted the whole `idx/` directory, so processes removed segments the
  others were reading or writing and failed with
  `Failed to open file for write: <hash>.idx` or
  `FileDoesNotExist(.../<hash>.fieldnorm)`.
- A failed rebuild keeps the last usable index instead of leaving no index at
  all. The new index is built in a scratch directory and only swapped in once
  it is complete.

### Added
- Cross-process index lock (`index.lock` next to the index directory, never
  inside it): rebuilds take it exclusively, searches take it shared, so
  parallel processes wait instead of racing. The wait can be tuned with
  `TANTIVY2AGENTS_LOCK_TIMEOUT` (seconds, default 120) and times out with a
  structured error.
- Scratch directories left behind by a crashed rebuild are cleaned up on the
  next indexing run.

### Changed
- `clear` now empties the index directory but keeps the lock file, so a
  concurrent process cannot lose the lock it is holding.
- `index_info.json` is written atomically.

## [0.7.16] - 2026-06-05

### Added
- `search --snippets` to include a short matching content preview while keeping
  default agent output compact.
- Server-management setup guidance for repo-specific guides, runbooks, server
  notes, playbooks, and incident documentation.

### Changed
- Default no-config indexing is documentation-focused (`*.md`, `*.txt`, `*.rst`)
  instead of broad `*.*` indexing.
- Search now automatically builds missing indexes and refreshes indexes marked
  outdated by hooks.
- Filtered searches fetch more candidates so hidden high-ranking documents are
  less likely to mask visible results.
- Search results are deduplicated by indexed file path before applying the
  requested result limit, so each file is returned at most once.
- Packaged usage/setup guides now emphasize committed repository files as the
  durable source of truth for agents.

## [0.7.15] - 2026-06-03

### Changed
- Exclude `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md` from indexing by default,
  including existing configs that define custom `global_patterns`.
- Match filename-only include/exclude patterns against basenames as well as
  project-relative paths, so default file exclusions apply in nested folders.

## [0.7.14] - 2026-06-03

### Changed
- Completed repository hygiene pass: confirmed no untracked non-ignored files,
  kept tracked Markdown limited to project and packaged CLI docs, and left
  ignored local artifacts in place.
- Expanded `.gitignore` for common local cache and coverage outputs.

## [0.7.13] - 2026-06-03

### Added
- Safe path checks for index storage, configured index patterns, and output
  files that could otherwise escape the project root.
- `--allow-outside-output` opt-in for commands that write `--output` files
  outside the project root.
- Regression coverage for unsafe config paths, outside output paths, and
  symlinked index directory deletion.

### Changed
- `clear`, `hook-clear`, and index rebuild cleanup refuse symlinked index
  directories instead of following them.

## [0.7.12] - 2026-06-03

### Changed
- Clarified CLI help and docs for internal hook support and packaged guide
  commands without introducing command groups.

### Added
- Help text regression checks for `hook-clear`, `skill-usage`, and
  `skill-setup` command descriptions.

## [0.7.11] - 2026-06-03

### Changed
- Made search result descriptions opt-in by defaulting `search.show_description`
  to `false` in runtime and install-created configs.
- Documented compact default text output and the `show_description` opt-in in
  README and packaged usage/setup guides.

### Added
- Exact output regression coverage for representative compact text search output.

## [0.7.10] - 2026-06-03

### Added
- Regression coverage that packaged skill docs are preferred over any local
  `.claude/skills` duplicate.

### Verified
- Confirmed `uv build` includes packaged skill docs in wheel and sdist artifacts.

## [0.7.9] - 2026-06-03

### Added
- `tantivy2agents.output` module for text, JSON, and CSV search result exports.
- Direct output tests for missing Tantivy fields and file exports across all
  public formats.

### Changed
- Delegated `TantivyAgent` result export helpers to the output module while
  preserving existing wrapper methods and public output behavior.

## [0.7.8] - 2026-06-03

### Added
- `tantivy2agents.files` module for glob expansion, include/exclude matching,
  binary detection, and index file collection.
- Direct file discovery tests covering glob patterns, excluded directories,
  binary skips, and agent wrapper parity.

### Changed
- Delegated `TantivyAgent` file discovery helpers to the file discovery module
  so `index`, `list`, and preview flags share the same path filtering behavior.

## [0.7.7] - 2026-06-03

### Added
- `tantivy2agents.config` module for runtime defaults, project-type defaults,
  config loading, search filter validation, and config-example text.
- Direct config unit tests for defaults, project defaults, validation, and
  config-example drift.

### Changed
- Delegated `TantivyAgent` config loading, validation, install-created defaults,
  and config-example output to the config module while preserving existing
  wrapper methods.

## [0.7.6] - 2026-06-03

### Changed
- Moved process termination responsibility out of `CLIError` and into
  `cli.main()`, leaving library-like code to raise or format structured errors.

## [0.7.5] - 2026-06-03

### Added
- Structured error regression tests for malformed config, missing indexes,
  missing packaged skill docs, unsupported direct output formats, and JSON error
  output from the CLI entrypoint.

### Changed
- Replaced user-facing config, search, skill-doc, and direct output-format error
  prints/log-only returns with `CLIError` subclasses.

## [0.7.4] - 2026-06-03

### Added
- CLI regression coverage for `search --output` across text, JSON, and CSV.
- CLI regression coverage for `index --dirs`, `index --files`, missing index
  search behavior, and unusable empty index directories.

## [0.7.3] - 2026-06-03

### Changed
- Isolated command-level Typer CLI tests from repository index/config state by
  monkeypatching `TantivyAgent` where indexing internals are not under test.
- Made `tests/test_typer_cli.py` executable as a standalone verification command.

### Fixed
- Replaced loose CLI assertions with concrete output and dispatch checks for
  documentation, config, status, and search format options.

## [0.7.2] - 2026-06-03

### Changed
- Moved `todo-roadmap-workflow` from packaged runtime skills to the repo-local
  `.agents/skills` directory.
- Tracked the `.claude/skills` symlink to the repo-local agent skills directory.

### Removed
- Removed the accidental packaged `todo-roadmap-workflow` skill copy.

## [0.7.1] - 2026-06-03

### Added
- `todo-roadmap-workflow` skill for TODO-driven project work.
- Regression coverage for the default search result limit.
- Concrete Typer CLI tests for text, JSON, and CSV search output.

### Changed
- Isolated temporary test projects from ambient repository state.
- Removed completed roadmap items from `TODO.md`.

### Fixed
- Restored the documented token-saving default search result limit to `5`.
- Kept `list --encoding` output visible by disabling Rich markup parsing for
  file rows.

## [0.7.0] - 2026-02-08

### Added
- `list` command to preview files before indexing.
- Structured `CLIError` hierarchy with JSON output when
  `TANTIVY_JSON_OUTPUT=true`.
- Typer CLI with generated help.
- `--version` CLI option.
- Packaged `skill-usage` and `skill-setup` documentation commands.

### Changed
- Migrated CLI from argparse to Typer.
- Replaced deprecated output shortcuts with `search --format text|json|csv`.
- Added declarative Typer bounds for `search --limit` (`min=1`, `max=10000`).
- Updated project version from `0.6.2` to `0.7.0`.

### Fixed
- Handle non-string YAML frontmatter values in `tags` and `servers`.
- Use direct Tantivy document field access instead of unsupported `.get()`.

### Removed
- Completed CLI refactoring items from `TODO.md`.
- Stale documentation scaffolding that duplicated or contradicted current docs.

## [0.6.2] - 2026-01-26

### Added
- Initial Typer implementation and related bug fixes.

## Older History

Older commits introduced status/setup commands, Claude Code hook integration,
export formats, encoding detection, Markdown metadata parsing, project type
detection, configurable field weights, and the MIT license.
