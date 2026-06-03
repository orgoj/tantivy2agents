# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0] - 2026-02-08

### Added
- `list` command to preview files that will be indexed without creating an index
- Structured exception system with dual JSON/human output for better AI integration
- AI Agent Integration section in README with machine-readable examples

### Changed
- **BREAKING**: Migrated CLI from argparse to Typer framework
- **BREAKING**: Removed deprecated format flags (`-j`, `-c`, `-T`)
  - Use single `--format` flag with values: `json`, `csv`, `text`
  - Example: `tantivy2agents search "query" --format json`
- Auto-generated help text from docstrings (no hardcoded help)
- Improved error messages with emojis and actionable hints
- Enhanced validation with structured errors (JSON when `TANTIVY_JSON_OUTPUT=true`)
- Declarative Typer bounds for `search --limit` (`min=1`, `max=10000`)

### Fixed
- Robust frontmatter parsing: handle non-string values in `tags` and `servers` (fixes crash when integers are used in metadata)

### Technical
- Added dependencies: `typer>=0.12.0`, `rich>=13.0.0`
- Implemented `OutputFormat` Enum for type-safe format validation
- Clean dependency injection pattern (no global state)
- 68 automated tests (100% passing)
- Comprehensive Typer CLI test coverage

### Removed
- Completed CLI refactoring items from TODO.md after landing them in this changelog

### Security
- Identified critical security vulnerabilities requiring immediate attention
- See CODE_REVIEW.md for complete security analysis

## [0.6.2] - 2026-01-26 (approx)
*Initial Typer implementation and bugfixes*


## [1.0.0] - 2025-11-22

### Added
- Status command for index statistics and monitoring
- Setup command for system-wide installation
- Claude Code integration with hooks
- Support for multiple export formats (JSON, CSV, TXT)
- Automatic project type detection (Python, Node.js, Java, Rust, etc.)
- File encoding detection with charset-normalizer
- Markdown metadata parsing
- Configurable search field weights

### Changed
- Improved default configuration
- Fixed Python boolean syntax error in default configuration
- Fixed duplicate search results issue

### Fixed
- Hardcoded model removed (now configurable)

## Version History

Based on git log, notable commits include:

- **2025-11-22**: Fix Python boolean syntax error in default configuration
- **2025-11-22**: Improve default configuration and fix duplicate search results
- **2025-11-22**: Add status command for index statistics and monitoring
- **2025-11-22**: Add setup command for system-wide installation
- **Earlier**: Remove hardcoded model glm

---

## Upgrade Guide

### From pre-1.0 to 1.0.0

1. **Configuration Changes**
   - Index directory changed from `.tantivy/idx` to `.tantivy-data/idx`
   - Update your `.tantivy2agents.json` if you customized `index_dir`

2. **New Commands Available**
   - `status` - Check index statistics
   - `setup` - System-wide installation with virtual environment

3. **Claude Code Integration**
   - Hooks can now be installed for automatic indexing
   - See README.md for hook installation instructions

---

## Deprecation Notices

### Deprecated in 1.0.0
- `bin/` directory scripts may be removed in future versions
  - Use unified `tantivy2agents.py` interface instead
  - Old scripts use deprecated `.tantivy/idx` path

---

## Semantic Versioning Policy

- **MAJOR** (X.0.0): Breaking changes, significant architecture changes
- **MINOR** (0.X.0): New features, backwards compatible
- **PATCH** (0.0.X): Bug fixes, security patches, documentation

---

**Note:** This changelog will be maintained going forward. Historical changes before 1.0.0 are summarized based on git commit history.
