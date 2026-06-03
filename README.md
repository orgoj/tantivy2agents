# tantivy2agents

Local CLI for indexing and searching project documentation with Tantivy.

It is meant for developer-owned local repositories. It builds a `.tantivy-data/`
index from configured files, searches it with BM25 ranking, and can install
Claude Code hooks that mark the index stale after file edits.

## Install

Run from git without installing:

```bash
uvx --from git+https://github.com/orgoj/tantivy2agents tantivy2agents --help
```

Install into the current environment:

```bash
uv pip install git+https://github.com/orgoj/tantivy2agents
```

Development setup:

```bash
mise run install
uv run tantivy2agents --help
```

## Quick Start

```bash
tantivy2agents install
tantivy2agents list
tantivy2agents index
tantivy2agents search "your query"
tantivy2agents status
```

## Commands

| Command | Purpose |
| --- | --- |
| `install` | Detect project type, create `.tantivy2agents.json`, install hooks |
| `list` | Preview files that would be indexed |
| `index` | Build or update the search index |
| `search "query"` | Search indexed documents |
| `status` | Show index statistics |
| `clear` | Delete index data |
| `encoding-info` | Analyze encodings for indexed files |
| `config-example` | Print a full config template |
| `hook-clear` | Mark index stale; used by Claude hooks |
| `skill-usage` | Print the packaged usage guide |
| `skill-setup` | Print the packaged setup/configuration guide |

Common options:

```bash
tantivy2agents index --force
tantivy2agents index --dirs --files
tantivy2agents list --pattern "*.md" --size --encoding
tantivy2agents search "api config" --limit 5
tantivy2agents search "api config" --format json --output results.json
TANTIVY_JSON_OUTPUT=true tantivy2agents search "" 2>&1
```

`search --format` accepts `text`, `json`, and `csv`. The default is compact
`text`: it shows path, title, score, tags, and servers. Frontmatter
descriptions are opt-in with `search.show_description: true`.

## Configuration

Minimal `.tantivy2agents.json`:

```json
{
  "version": "1.0",
  "index_dir": ".tantivy-data",
  "index_dirs": ["docs", "guides", "*.md"]
}
```

Useful fields:

- `index_dir`: where index data is stored; default is `.tantivy-data`.
- `index_dirs`: files/directories/globs to include, or objects with `exclude`.
- `global_patterns`: default include/exclude file patterns.
- `schema_fields`: search weights and tokenizers for fields.
- `search.default_limit`: default result count; project default is `5`.
- `search.show_description`: include frontmatter descriptions in output; default
  is `false` to keep agent search output compact.
- `search.filters`: hide path prefixes unless query keywords match.
- `encoding`: default, fallback, binary, and file-specific encodings.
- `auto_hook`: whether `install` should add Claude Code hooks.

Run `tantivy2agents config-example` for the full template.

## Markdown Metadata

Markdown frontmatter is indexed when present:

```markdown
---
title: Deployment Guide
description: How to deploy the service
tags: [deploy, production]
servers: [web, 8080]
---

# Deployment Guide
```

Non-string `tags` and `servers` values are converted to strings before indexing.

## Packaged Guides

The detailed usage and setup guides are shipped inside the package so the CLI can
print them from any install:

```bash
tantivy2agents skill-usage
tantivy2agents skill-setup
```

Source copies live in `src/tantivy2agents/skills/`.

## Development

```bash
mise run install
mise run test
mise run pre-commit
```

The current full custom test runner is not green in this checkout. Known failing
areas are tracked in `TODO.md`; keep new fixes covered by permanent tests.

## Project Docs

- `CHANGELOG.md`: released changes.
- `TODO.md`: open work only.
- `CLAUDE.md`: project-specific agent/development rules.
- `src/tantivy2agents/skills/*/SKILL.md`: packaged CLI help documents.

## License

MIT. See `LICENSE`.
