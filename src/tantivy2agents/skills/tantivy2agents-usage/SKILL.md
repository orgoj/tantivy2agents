---
name: tantivy2agents-usage
description: Daily usage of tantivy2agents - search, index, status commands. Use when searching docs, indexing files, checking status, or working with existing tantivy2agents installation.
---

# tantivy2agents - Usage Guide

Daily usage guide for Tantivy Agent document indexing and search.

Use this tool to find committed project documentation before doing work. In
server-management repositories, search guides, runbooks, server notes, playbooks,
and previous incidents stored in the repo. This is not external memory; the
repository files are the shared source of truth.

## Quick Start

```bash
# Create or update index
tantivy2agents index

# Search documents
tantivy2agents search "your query"

# Search with a short content snippet when deciding what to read
tantivy2agents search "nginx restart" --snippets

# Read a result by its ref: headings first, then only the section you need
tantivy2agents outline a3f2c1:1
tantivy2agents read a3f2c1:1 --section setup

# View index status
tantivy2agents status
```

## Reading Results

Every search result has a ref `<search_id>:<rank>` (`REF:` line in text
output). Read indexed documents through these commands rather than a file tool,
so the project can see which guides are found and actually used:

```bash
tantivy2agents outline REF|PATH                   # headings: lines, slug
tantivy2agents read REF|PATH                      # whole document
tantivy2agents read REF|PATH --section SLUG       # one section + subsections
tantivy2agents read REF|PATH --lines 10-40        # line range (A-B, A-, A)
tantivy2agents read REF|PATH --lines 10-40 --numbers   # with line numbers
```

- Prefer the ref from the search you just ran; a path relative to the project
  root works too.
- For long documents run `outline` first and read only the relevant section.
- `--section` takes the slug from `outline` (`{#setup-1}`), the heading text,
  or the slug without diacritics (`prehled-zmen`).
- Line numbers match the file on disk (frontmatter included), so they can be
  used for edits.
- Only files the project indexes are readable.

## Commands Reference

### index - Build or Update Search Index

```bash
tantivy2agents index              # Incremental update (only if files changed)
tantivy2agents index --force      # Full rebuild from scratch
tantivy2agents index --dirs       # Show directories to be processed
tantivy2agents index --files      # Show files to be processed
```

**Behavior:**
- Only reindexes if files have changed (incremental)
- Creates `.tantivy-data/` directory (auto-added to .gitignore)
- Skips binary files and excluded patterns

### search - Search Indexed Documents

```bash
tantivy2agents search "query"              # Structured text (default)
tantivy2agents search "query" --format json
tantivy2agents search "query" --format csv
tantivy2agents search "query" --format text
tantivy2agents search "query" --limit 5    # Limit results
tantivy2agents search "query" --snippets   # Include matched content snippet
tantivy2agents search "query" -o out.json  # Save to file
tantivy2agents search "query" -o /tmp/out.json --allow-outside-output
```

**Output formats:**
- `--format text` - Structured text (default)
- `--format json` - JSON with metadata
- `--format csv` - CSV table
- `--snippets` - Add a short matching content snippet
- `--output` paths must stay inside the project unless
  `--allow-outside-output` is provided

**Search features:**
- BM25 ranking (higher score = better match)
- Czech language support (automatic stemming)
- Field-weighted search (title > description > body)

### status - Index Statistics

```bash
tantivy2agents status
```

**Shows:**
- Document count and last update time
- Index size and file count
- Files available vs missing
- Index status: Up to date, Out of date (the next search updates it) or
  Unknown (some files could not be scanned)
- Tantivy version

### Other Commands

```bash
tantivy2agents usage --since 7d # Which results were read via read/outline
tantivy2agents clear            # Delete index
tantivy2agents config-example   # Show config template
tantivy2agents hook-clear       # Optional hook support; next search re-checks files
tantivy2agents encoding-info    # Analyze file encodings
tantivy2agents list             # Preview files without indexing
tantivy2agents skill-usage      # Print this packaged usage guide
tantivy2agents skill-setup      # Print packaged setup/configuration guide
```

## Output Format Examples

### Text Output (Default)

```
### FILE: guides/server-setup.md
REF: a3f2c1:1
TITLE: Complete Server Setup Guide
SCORE: 0.8920
TAGS: docker, networking
---
Read: tantivy2agents outline REF | tantivy2agents read REF [--section SLUG]
```

Default text output is intentionally compact for agent workflows. Set
`search.show_description: true` in `.tantivy2agents.json` to add
`DESCRIPTION:` lines from YAML frontmatter. Add `--snippets` when the agent needs
a short content preview before opening a file.

### Text Output with Snippets

```
### FILE: guides/server-setup.md
REF: a3f2c1:1
TITLE: Complete Server Setup Guide
SCORE: 0.8920
TAGS: docker, networking
SNIPPET: Restart nginx only after checking the health endpoint.
---
Read: tantivy2agents outline REF | tantivy2agents read REF [--section SLUG]
```

### JSON Output

```json
{
  "query": "server configuration",
  "search_id": "a3f2c1",
  "timestamp": "2025-01-06T19:30:45",
  "total_results": 3,
  "results": [
    {
      "rank": 1,
      "ref": "a3f2c1:1",
      "score": 0.892,
      "path": "guides/server-setup.md",
      "title": "Complete Server Setup Guide",
      "tags": "docker networking",
      "servers": ""
    }
  ]
}
```

JSON output follows `search.show_description`; enable it when machine consumers
need frontmatter descriptions.

### CSV Output

```csv
Score,Path,Title,Tags,Servers,Ref
0.8920,guides/server-setup.md,Complete Server Setup Guide,docker networking,,a3f2c1:1
0.7560,servers/production.md,Production Server Configuration,infrastructure,prod,a3f2c1:2
```

## YAML Frontmatter

Documents can have metadata for better search:

```markdown
---
title: My Guide
description: Short summary of the guide
tags: [docker, networking]
servers: [s8, s9]
---

# Content here
```

**Important:** Schema must include frontmatter fields for searchability.

## Search Tips

**Effective queries:**
- Use 2-4 keywords: `"ssl certificate"`, `"docker networking"`
- Specific terms: `"nginx config"`, `"python setup"`
- Field names match to title, description, body, tags, servers

**BM25 ranking:**
- Results sorted by relevance score
- Title matches weighted higher (2.0x)
- Description and tags weighted 1.5x
- Body text weighted 1.0x

## Best Practices

**Agent workflow:**
- Search for the guide/runbook before editing code or changing a server.
- Search for past incidents when the task mentions an outage, failure, rollback,
  emergency, or project-specific incident keyword.
- Read the returned files before acting, via `outline`/`read` with the ref.

**After file changes:**
- Nothing to do: every `search` re-indexes added, changed and removed files
  first, with or without hooks

**Performance:**
- Incremental indexing only reprocesses changed files
- Use `--limit` to reduce result set size
- Export to file for large result sets

**Search quality:**
- Be specific with keywords
- Use technical terms from your domain
- Check schema fields for custom metadata

## Troubleshooting

**No results found:**
- Check index exists: `tantivy2agents status`
- Rebuild index: `tantivy2agents index --force`
- Verify query terms match document content

**Wrong files in results:**
- Check configuration (use `tantivy2agents skill-setup` for config help)
- Be specific in `index_dirs`, don't index root
- Use search filters for path-based filtering

**Stale results:**
- Check index status: `tantivy2agents status`
- `search` refreshes missing or stale indexes automatically
- A stderr warning `Index not refreshed: file scan incomplete` means some
  file or directory hit an I/O error; the previous index stays in use
- `Skipped (permission denied): <path>` means that path is left out of the
  index; exclude it in `index_dirs` to silence the warning
- Force a manual rebuild with `tantivy2agents index --force` if needed

## Getting More Help

**View setup documentation:**
```bash
tantivy2agents skill-setup   # Setup and configuration guide
```

**Show full configuration template:**
```bash
tantivy2agents config-example
```

**View project documentation:**
```bash
# View usage guide (this file)
tantivy2agents skill-usage

# View setup guide
tantivy2agents skill-setup
```
