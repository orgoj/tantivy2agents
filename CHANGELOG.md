# Changelog

All notable project changes are tracked here.

## [0.7.1] - 2026-06-03

### Added
- Packaged `todo-roadmap-workflow` skill for TODO-driven project work.
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
