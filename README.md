# tantivy2agents

Local documentation search for coding agents.

`tantivy2agents` gives a developer-owned repository a fast local Tantivy index
over the project documents an agent needs for its work: server guides, previous
incidents, runbooks, setup docs, Markdown notes, and other configured text files.
The primary use case is server-management repositories where operational
knowledge lives in committed files shared by everyone using the repo.

The goal is not to replace source-code search. The goal is to make committed
project documentation cheap to query during agent work, without sending the
whole repository into a prompt and without depending on a remote service.

The CLI builds a `.tantivy-data/` index inside the project, searches it with BM25
ranking, and refreshes it before every search: each candidate file is stat'ed
and only added, changed or removed files are re-indexed, so no editor hook is
needed. Search output is intentionally compact by default so agents can consume
results with low token cost.

## Purpose

This project is for local, agent-facing documentation retrieval from files that
belong to the repository:

- keep shared project knowledge searchable from the command line;
- let coding agents find relevant guides before changing servers or code;
- surface previous incidents when they are relevant to the current task;
- avoid indexing generated artifacts, dependency directories, binary files, and
  agent instruction files by default;
- support machine-readable result formats for agent/tool integrations;
- keep all index data local to the repository owner.

It is deliberately not a full code intelligence engine, vector database, chat
memory system, MCP memory layer, or hosted search product. The durable memory is
the repository itself: files are committed, reviewed, and shared with all users
of the repo. Use `rg` for exact code search; use `tantivy2agents` when the
question is "which guide, incident, runbook, or project note should the agent
read first?"

## Project Fit Review

The current implementation already matches the core purpose in several ways:

- project-type detection creates conservative documentation-focused configs;
- `list` previews what will be indexed before writing an index;
- index and output paths are constrained to the project root unless explicitly
  overridden;
- search results support compact text, JSON, CSV, and opt-in snippets;
- `search` and `index` compare a manifest published inside `idx/`
  (`t2a_state.json`: size and mtime of every candidate file plus a config
  fingerprint) with the files on disk, re-index only what changed, and rebuild
  fully after config changes or a missing/unusable index. If the file scan
  hits a permission or I/O error, the previous index is kept and a warning is
  printed to stderr;
- Markdown frontmatter can improve ranking and filtering;
- Czech text normalization helps local documentation written in Czech;
- packaged `skill-usage` and `skill-setup` commands make the installed tool
  self-documenting for agents.

The most useful future improvements should strengthen agent usability rather
than broaden the tool into generic search:

- add small quality checks for configs that accidentally index too much or too
  little;
- add more examples for project-local skills that teach agents how to use each
  repository's own documentation layout;
- continue decomposing `agent.py` only where it reduces risk in CLI behavior or
  testability.

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
| `index` | Update changed files in the index; `--force` rebuilds it fully |
| `search "query"` | Search indexed documents |
| `outline REF\|PATH` | Headings of an indexed document with slugs and line ranges |
| `read REF\|PATH` | Print an indexed document, `--section SLUG` or `--lines A-B` |
| `usage` | Report which search results agents read via `read`/`outline` |
| `status` | Show index statistics |
| `clear` | Delete index data (keeps the lock file and usage log) |
| `encoding-info` | Analyze encodings for indexed files |
| `config-example` | Print a full config template |
| `hook-clear` | Internal hook support; optional, `search` detects edits itself |
| `skill-usage` | Print the packaged usage guide from the installed package |
| `skill-setup` | Print the packaged setup/configuration guide from the installed package |

Common options:

```bash
tantivy2agents index --force
tantivy2agents index --dirs --files
tantivy2agents list --pattern "*.md" --size --encoding
tantivy2agents search "api config" --limit 5
tantivy2agents search "nginx restart" --snippets
tantivy2agents search "api config" --format json --output results.json
tantivy2agents search "api config" --output /tmp/results.json --allow-outside-output
TANTIVY_JSON_OUTPUT=true tantivy2agents search "" 2>&1
```

`search --format` accepts `text`, `json`, and `csv`. The default is compact
`text`: it shows path, title, score, tags, and servers. Frontmatter
descriptions are opt-in with `search.show_description: true`. Matching content
snippets are opt-in per query with `--snippets`.

Output files must stay inside the project root unless
`--allow-outside-output` is provided.

## Reading Documents and Usage Tracking

Each search gets a short id, and every result a ref `<search_id>:<rank>`
(`REF: a3f2c1:1` in text output, `search_id`/`rank`/`ref` in JSON, a trailing
`Ref` column in CSV). Agents pass a ref or a path to the read commands:

```bash
tantivy2agents outline a3f2c1:1                  # headings, slugs, line ranges
tantivy2agents read a3f2c1:1 --section setup     # one section incl. subsections
tantivy2agents read guides/deploy.md --lines 10-40 --numbers
tantivy2agents usage --since 7d --format json    # search -> read report
```

- Only files the current config would index can be read; paths are relative to
  the project root or absolute inside it.
- Sections: ATX headings outside fenced code, GitHub-style slugs that keep
  Unicode letters (`## Přehled změn` → `přehled-změn`), duplicates get `-1`,
  `-2`. `--section` also accepts the heading text or the slug without
  diacritics. `frontmatter` and `preamble` (text before the first heading) are
  pseudo-sections. Line numbers count the raw file, frontmatter included.
- Searches (zero-result ones too) and reads are appended to
  `<index_dir>/usage.jsonl` (rotated to `usage.1.jsonl` at
  `usage.max_bytes`, default 5 MB). Refs resolve from these two files. The log
  has its own `usage.lock`, so reads never wait for an index rebuild.
- Turn it off with `"usage": {"enabled": false}` or `TANTIVY2AGENTS_USAGE=0`;
  search then prints no refs. `TANTIVY2AGENTS_AGENT`, if set, is recorded with
  each event.
- The report only sees reads through `read`/`outline`; reads with native file
  tools are invisible to it.
- `usage --recent-read PATH [--within 30m]` exits 0 when PATH was read via
  `read` inside the window and its content is unchanged since, 1 otherwise.

## Platform Support

| Platform | Status |
| --- | --- |
| Linux x86_64, aarch64 | Supported and tested |
| Windows x86_64 | Supported, not yet verified on a real machine |
| macOS x86_64, arm64 | Supported, not yet verified on a real machine |
| Windows on ARM | Not supported — `tantivy` ships no `win_arm64` wheel |

Windows-specific behavior (path rules, drive boundaries, console encoding) is
covered by `tests/test_portability.py`, which reproduces the Windows rules from
POSIX using `ntpath`. That is not the same as running the tool on Windows, so
treat the Windows and macOS rows as "should work, unverified" until someone
confirms them.

On Windows on ARM the install itself fails unless a Rust toolchain is present
to build `tantivy` from source.

## Parallel Processes

Several agents can run `index` and `search` against the same project at the
same time. Access is coordinated through a lock file (`index.lock`) that sits
next to the index directory, not inside it:

- Every `index`, `clear`, search-triggered rebuild and `search` holds the lock,
  so processes wait instead of deleting an index that is still in use.
- A new index is built in a scratch directory and swapped in with an atomic
  rename, so a failed rebuild leaves the last usable index in place. An
  incremental refresh works the same way on a copy of the live index.
- `search` refreshes and queries under one lock acquisition, so a concurrent
  `clear` or rebuild cannot remove the index between the two.
- If a run dies after moving the old index aside and before moving the new
  one in, the next run restores the old index from that retired copy.
- The lock is taken through `fcntl.flock` on POSIX and `msvcrt.locking` on
  Windows. Both are released by the operating system when the process exits,
  so a crashed or killed run never leaves a lock behind.

The lock is exclusive, because Windows has no shared-mode equivalent and one
behavior on every platform is worth more than parallel reads. Searches
therefore queue behind each other, which costs about 1 ms per search on a
2000-document index.

Set `TANTIVY2AGENTS_LOCK_TIMEOUT` (seconds, default `120`) to change how long a
process waits before giving up with an error.

## Configuration

Minimal `.tantivy2agents.json`:

```json
{
  "version": "1.0",
  "index_dir": ".tantivy-data",
  "index_dirs": ["docs", "guides", "runbooks", "*.md"]
}
```

Useful fields:

- `index_dir`: where index data is stored; default is `.tantivy-data`. Must be
  a relative path without `..`; symlinked index directories are refused.
- `index_dirs`: files/directories/globs to include, or objects with `exclude`.
  Patterns must be relative to the project root and must not contain `..`.
- `global_patterns`: default include/exclude file patterns.
- `schema_fields`: search weights and tokenizers for fields.
- `search.default_limit`: default result count; project default is `5`.
- `search.show_description`: include frontmatter descriptions in output; default
  is `false` to keep agent search output compact.
- `search.filters`: hide path prefixes unless query keywords match.
- `encoding`: default, fallback, binary, and file-specific encodings.
- `auto_hook`: whether `install` should add Claude Code hooks.
- `usage.enabled`, `usage.max_bytes`: usage log on/off (default on) and its
  rotation size (default `5000000`).

Run `tantivy2agents config-example` for the full template.

For server-management repositories, keep the project-specific knowledge in
committed files and tune `.tantivy2agents.json` to that layout. Typical include
paths are `guides/`, `runbooks/`, `servers/`, `playbooks/`, and project-specific
incident directories. Incident behavior is configuration, not built-in policy:
use `search.filters` when a repo wants to hide or reveal incident paths by
keyword.

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
