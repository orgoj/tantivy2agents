# Changelog

All notable project changes are tracked here.

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
