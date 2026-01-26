# tantivy2agents - Full-text search for project documentation

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Full-text search CLI for project documentation using Tantivy (Rust). BM25 ranking, YAML frontmatter parsing, Claude Code hook integration.

## Documentation

**Usage Guide** → See [tantivy2agents-usage skill](.claude/skills/tantivy2agents-usage/SKILL.md)
- Daily commands: search, index, status
- Output formats
- Examples and best practices

**Setup Guide** → See [tantivy2agents-setup skill](.claude/skills/tantivy2agents-setup/SKILL.md)
- Installation (uvx, pip)
- Configuration (.tantivy2agents.json)
- Claude Code hooks

## Quick Start

```bash
# Install and setup (auto-detects project type)
tantivy2agents install

# Build index
tantivy2agents index

# Search documentation
tantivy2agents search "your query"

# Get documentation via CLI
tantivy2agents skill-usage   # View usage guide
tantivy2agents skill-setup   # View setup guide
```

## Installation

### Using uvx (Recommended - No Installation)

```bash
# Run directly from git
uvx --from git+https://github.com/orgoj/tantivy2agents tantivy2agents install
uvx --from git+https://github.com/orgoj/tantivy2agents tantivy2agents index
uvx --from git+https://github.com/orgoj/tantivy2agents tantivy2agents search "query"
```

### Using uv or pip

```bash
# Install from git
uv pip install git+https://github.com/orgoj/tantivy2agents
# Or with pip
pip install git+https://github.com/orgoj/tantivy2agents

# Now use directly
tantivy2agents install
tantivy2agents index
tantivy2agents search "your query"
```

### Development Setup

```bash
# Clone repository
git clone https://github.com/orgoj/tantivy2agents
cd tantivy2agents

# Install dependencies
uv sync
uv run pre-commit install

# Install local version (updates your global tantivy2agents command)
uv tool install --reinstall .

# Run tests
uv run python run_tests.py
```

## Features

- **Modern Python packaging** - Install with `uv` or `pip`, run with `uvx`
- **Czech language support** - Built-in stemmer for Czech morphology
- **Flexible configuration** - JSON-based config with global and directory-specific patterns
- **Automatic data management** - Data stored outside repository with auto .gitignore
- **Claude Code integration** - Automatic hook installation for real-time index updates
- **Incremental indexing** - Only reindex when files change
- **Universal design** - Works in any project (Python, Node.js, Java, Rust, Generic)

## Configuration

Create `.tantivy2agents.json` in your project root:

```json
{
  "version": "1.0",
  "index_dir": ".tantivy-data",
  "index_dirs": ["docs", "guides"]
}
```

Run `tantivy2agents install` to auto-generate optimal configuration for your project type.

For advanced configuration (schema fields, search filters, encoding settings), see [tantivy2agents-setup skill](.claude/skills/tantivy2agents-setup/SKILL.md).

## Commands

| Command | Description |
|---------|-------------|
| `install` | Auto-detect project type and create config |
| `index` | Build or update the search index |
| `search "query"` | Search indexed documents |
| `list` | List files that would be indexed (without creating index) |
| `status` | Show index statistics |
| `clear` | Clear the search index |
| `config-example` | Show example configuration |
| `encoding-info` | Analyze file encodings |
| `skill-usage` | Output usage documentation |
| `skill-setup` | Output setup documentation |

## Requirements

- Python 3.10+
- Dependencies: `PyYAML`, `tantivy`, `charset-normalizer`

## AI Agent Integration

tantivy2agents is optimized for AI agents like Claude Code:

- **Structured output**: JSON format for programmatic consumption
- **File preview**: `list` command explores project structure without side effects
- **Clear errors**: Structured error messages with hints via `TANTIVY_JSON_OUTPUT=true`
- **Type hints**: Full type annotations enable introspection
- **Predictable interface**: Consistent command structure

### Examples:

```bash
# Preview files before indexing
tantivy2agents list --pattern "*.md"

# Get structured results
tantivy2agents search "API" --format json -o results.json

# Machine-readable errors
TANTIVY_JSON_OUTPUT=true tantivy2agents search "" 2>&1 | jq .

# Parseable JSON for AI agents
tantivy2agents search "database schema" --format json | jq '.results[] | .path'
```

## License

MIT License - see LICENSE file for details.
