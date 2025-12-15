---
name: tantivy2agents
description: Full-text search CLI for project documentation using Tantivy engine. Use when searching docs, indexing markdown files, configuring tantivy2agents, or working with .tantivy2agents.json config. Covers install, index, search, status, clear commands.
---

# tantivy2agents - Full-Text Search for Documentation

CLI tool for full-text search using Tantivy (Rust). BM25 ranking, YAML frontmatter parsing, Claude Code hook integration.

## Quick Start

```bash
tantivy2agents install          # Auto-setup (creates config, gitignore, hooks)
tantivy2agents index            # Build/update index
tantivy2agents search "query"   # Search (structured text output)
tantivy2agents search "q" -j    # JSON output
tantivy2agents search "q" -c    # CSV output
tantivy2agents status           # Index statistics
```

## Commands

### install
```bash
tantivy2agents install                    # Current project
tantivy2agents install --target ../proj   # Another project
tantivy2agents install --no-config        # Skip config creation
```
Auto-detects project type (Python, Node.js, Java, Rust, Go, Generic).

### index
```bash
tantivy2agents index              # Incremental update
tantivy2agents index --force      # Full rebuild
tantivy2agents index --files      # Show files to process
tantivy2agents index --dirs       # Show directories
```

### search
```bash
tantivy2agents search "query"              # Structured text (default)
tantivy2agents search "query" -j           # JSON format
tantivy2agents search "query" -c           # CSV format
tantivy2agents search "query" -T           # Text format (explicit)
tantivy2agents search "query" --limit 5    # Limit results
tantivy2agents search "query" -o out.json  # Save to file
```

**Output formats:**
- `-T` / `--text` - Structured text (default)
- `-j` / `--json` - JSON with metadata
- `-c` / `--csv` - CSV table
- `-f json|csv|text` - Explicit format

### Other commands
```bash
tantivy2agents status           # Index stats (docs, size, version)
tantivy2agents clear            # Delete index
tantivy2agents config-example   # Show config template
tantivy2agents hook-clear       # Mark index outdated (for hooks)
tantivy2agents encoding-info    # Analyze file encodings
```

## Configuration: .tantivy2agents.json

### Minimal
```json
{
  "version": "1.0",
  "index_dir": ".tantivy-data",
  "index_dirs": ["guides", "docs"]
}
```

### Complete
```json
{
  "version": "1.0",
  "index_dir": ".tantivy-data",

  "global_patterns": {
    "include": ["*.md", "*.txt", "*.rst"],
    "exclude": ["*.tmp", "*~", "*.bak"]
  },

  "schema_fields": {
    "title": {"weight": 2.0, "tokenizer": "en_stem"},
    "description": {"weight": 1.5, "tokenizer": "en_stem"},
    "body": {"weight": 1.0, "tokenizer": "en_stem"},
    "tags": {"weight": 1.5, "tokenizer": "default"},
    "servers": {"weight": 1.5, "tokenizer": "default"},
    "path": {"weight": 0.5, "tokenizer": "raw"}
  },

  "search": {
    "default_limit": 10,
    "show_description": true,
    "filters": [
      {
        "name": "incidents",
        "paths": ["incidents/"],
        "hidden": true,
        "show_on_keywords": ["incident", "emergency"]
      }
    ]
  },

  "encoding": {
    "default_encoding": "utf-8",
    "auto_detect": true,
    "fallback_encodings": ["utf-8", "cp1252", "iso-8859-1"]
  },

  "auto_hook": false,

  "index_dirs": [
    "guides",
    "docs",
    {"path": ".git", "exclude": true}
  ]
}
```

### Key Options

**schema_fields** - Search fields with weights (higher = more important):
- `title`, `description`, `body`, `tags`, `servers`, `path`
- Tokenizers: `en_stem` (English stemming), `default`, `raw`

**search.show_description** - Show description in results (default: true)

**search.filters** - Filter paths with keyword triggers:
- `hidden: true` - Hide by default
- `show_on_keywords` - Show when query contains these words

**index_dirs** - Directories to index:
- String: `"guides"` - include
- Object: `{"path": ".git", "exclude": true}` - exclude

## YAML Frontmatter

Documents can have metadata:
```markdown
---
title: My Guide
description: Short summary of the guide
tags: [docker, networking]
servers: [s8, s9]
---

# Content here
```

Schema must include frontmatter fields for searchability.

## Claude Code Hook

Auto-mark index outdated on file edits. In `.claude/settings.json`:
```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Edit|Write|MultiEdit",
      "hooks": [{"type": "command", "command": "tantivy2agents hook-clear"}]
    }]
  }
}
```

## Best Practices

**Index only searchable docs:**
- ✅ `guides/`, `docs/`, `incidents/`
- ❌ `servers/` (if loaded by name), `.claude/`, `.git/`

**Search tips:**
- Use 2-4 keywords: `"ssl certificate"`, `"docker networking"`
- BM25 ranks by relevance (higher score = better match)

**Rebuild after config changes:**
```bash
tantivy2agents index --force
```

## Troubleshooting

**Wrong files in results:** Be specific in `index_dirs`, don't index root.

**YAML fields not searchable:** Add to `schema_fields`, rebuild with `--force`.

**Config option ignored:** Verify with `tantivy2agents config-example`.

**Stale results:** Configure Claude hook or run `tantivy2agents index`.
