---
name: tantivy2agents-usage
description: Daily usage of tantivy2agents - search, index, status commands. Use when searching docs, indexing files, checking status, or working with existing tantivy2agents installation.
---

# tantivy2agents - Usage Guide

Daily usage guide for Tantivy Agent document indexing and search.

## Quick Start

```bash
# Create or update index
tantivy2agents index

# Search documents
tantivy2agents search "your query"

# View index status
tantivy2agents status
```

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
tantivy2agents search "query" -o out.json  # Save to file
```

**Output formats:**
- `--format text` - Structured text (default)
- `--format json` - JSON with metadata
- `--format csv` - CSV table

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
- Index status (up to date / needs rebuild)
- Tantivy version

### Other Commands

```bash
tantivy2agents clear            # Delete index
tantivy2agents config-example   # Show config template
tantivy2agents hook-clear       # Internal hook support; mark index outdated
tantivy2agents encoding-info    # Analyze file encodings
tantivy2agents list             # Preview files without indexing
tantivy2agents skill-usage      # Print this packaged usage guide
tantivy2agents skill-setup      # Print packaged setup/configuration guide
```

## Output Format Examples

### Text Output (Default)

```
### FILE: guides/server-setup.md
TITLE: Complete Server Setup Guide
SCORE: 0.8920
TAGS: docker, networking
---
```

Default text output is intentionally compact for agent workflows. Set
`search.show_description: true` in `.tantivy2agents.json` to add
`DESCRIPTION:` lines from YAML frontmatter.

### JSON Output

```json
{
  "query": "server configuration",
  "timestamp": "2025-01-06T19:30:45",
  "total_results": 3,
  "results": [
    {
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
Score,Path,Title,Tags,Servers
0.8920,guides/server-setup.md,Complete Server Setup Guide,docker networking,
0.7560,servers/production.md,Production Server Configuration,infrastructure,prod
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

**After file changes:**
- Index updates automatically if configured with hooks
- Or run `tantivy2agents index` manually

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
- Update index: `tantivy2agents index`

**Index outdated:**
- Files changed since last index
- Run `tantivy2agents index` to update

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
