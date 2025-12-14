---
name: tantivy2agents
description: Complete guide for tantivy2agents CLI tool - full-text search engine for project documentation with indexing, searching, and Claude Code integration
triggers:
  - tantivy2agents
  - tantivy search
  - full-text search
  - document search
  - search index
  - tantivy install
  - tantivy config
author: Claude (via session learning)
version: 1.0
created: 2025-12-09
---

# tantivy2agents - Full-Text Search for Project Documentation

Complete guide for tantivy2agents CLI tool - a full-text search engine built on Tantivy (Rust) for indexing and searching project documentation.

## What is tantivy2agents?

**tantivy2agents** is a CLI tool that provides full-text search for documentation:
- Indexes markdown files, text files, and other documents
- Built on Tantivy (Rust-based search engine, inspired by Apache Lucene)
- BM25 ranking algorithm for relevance scoring
- YAML frontmatter parsing for metadata
- Auto-detects project type and creates optimal configuration
- Claude Code hook integration for automatic index updates

**Use cases:**
- Search guides and documentation
- Find relevant how-to articles
- Locate incident reports
- Search technical documentation (k8s, infrastructure)

## Quick Start

### 1. Install and Setup

```bash
# Install in current project (auto-detects project type)
tantivy2agents install

# Creates:
# - .tantivi2agents.json (configuration)
# - .tantivy-data/ (index directory)
# - Updates .gitignore
# - Optional: Claude Code hooks
```

### 2. Build Index

```bash
# Build or update index
tantivy2agents index

# Force rebuild from scratch
tantivy2agents index --force
```

### 3. Search

```bash
# Basic search
tantivy2agents search "your query"

# Limit results
tantivy2agents search "your query" --limit 5

# Export as JSON
tantivy2agents search "your query" --format json
```

## All Commands

### install - Auto-Setup

```bash
tantivy2agents install                    # Setup in current project
tantivy2agents install --target ../proj   # Setup in another project
tantivy2agents install --no-config        # Skip config creation
```

**What it does:**
- Auto-detects project type (Python, Node.js, Java, Rust, Go, Generic)
- Creates `.tantivi2agents.json` configuration
- Adds `.tantivy-data/` to `.gitignore`
- Optionally installs Claude Code hooks

**Always use install first** - don't create config manually!

### index - Build/Update Index

```bash
tantivy2agents index              # Build or update index
tantivy2agents index --force      # Rebuild from scratch
tantivy2agents index --dirs       # Show directories to process
tantivy2agents index --files      # Show files to process
tantivy2agents index --verbose    # Debug output
```

**When to rebuild:**
- After config changes (`index_dirs`, `schema_fields`)
- When search results seem wrong
- After major documentation restructuring

### search - Query Index

```bash
tantivy2agents search "query"                 # Basic search
tantivy2agents search "query" --limit 10      # Limit results
tantivy2agents search "query" -f json         # JSON format
tantivy2agents search "query" -f csv          # CSV format
tantivy2agents search "query" -o results.json # Save to file
```

**Search tips:**
- Use 2-4 keywords for best results
- BM25 ranks by relevance (higher score = better match)
- Searches: title, body, tags, servers, path (based on schema)

**Examples:**
```bash
tantivy2agents search "ssl certificate"
tantivy2agents search "docker networking"
tantivy2agents search "zfs pool"
```

### status - Index Statistics

```bash
tantivy2agents status
```

**Shows:**
- Number of documents indexed
- Last update timestamp
- Index size and file count
- Tantivy version
- Index status (up to date / outdated)

### clear - Delete Index

```bash
tantivy2agents clear
```

**Warning:** Deletes entire index - rebuild with `index` command.

### config-example - Show Template

```bash
tantivy2agents config-example
```

**Use this to:**
- See all available config options
- Verify option names (never invent options!)
- Understand config structure

### hook-clear - Mark Index Outdated

```bash
tantivy2agents hook-clear
```

**For Claude Code hooks** - marks index as outdated when files are edited.

### encoding-info - Analyze Encodings

```bash
tantivy2agents encoding-info
```

Analyzes file encodings in project (UTF-8, cp1252, iso-8859-1, etc.)

## Configuration File: .tantivi2agents.json

### Minimal Configuration

```json
{
  "version": "1.0",
  "index_dir": ".tantivy-data",

  "index_dirs": [
    "guides",
    "docs"
  ]
}
```

### Complete Configuration

```json
{
  "version": "1.0",
  "index_dir": ".tantivy-data",

  "global_patterns": {
    "include": ["*.md", "*.txt", "*.rst"],
    "exclude": ["*.tmp", "*~", "*.bak", "*.log"]
  },

  "schema_fields": {
    "title": {"weight": 2.0, "tokenizer": "en_stem"},
    "body": {"weight": 1.0, "tokenizer": "en_stem"},
    "tags": {"weight": 1.5, "tokenizer": "default"},
    "servers": {"weight": 1.5, "tokenizer": "default"},
    "path": {"weight": 0.5, "tokenizer": "raw"}
  },

  "search": {
    "default_limit": 10,
    "hide_incidents": true,
    "show_incidents_on": ["incident", "emergency"]
  },

  "encoding": {
    "default_encoding": "utf-8",
    "auto_detect": true,
    "fallback_encodings": ["utf-8", "cp1252", "iso-8859-1"],
    "detection_confidence_threshold": 0.7
  },

  "auto_hook": false,

  "index_dirs": [
    "guides",
    "docs",
    "incidents",
    {"path": ".git", "exclude": true},
    {"path": ".venv", "exclude": true}
  ]
}
```

### Configuration Options

**version** - Config version (always "1.0")

**index_dir** - Where to store index (default: ".tantivy-data")

**global_patterns**
- `include` - File patterns to index (e.g., `["*.md", "*.txt"]`)
- `exclude` - File patterns to skip (e.g., `["*.log", "*.tmp"]`)

**schema_fields** - Search fields with weights and tokenizers
- Higher weight = more important in search ranking
- Tokenizers: `en_stem`, `default`, `raw`
- Must include all YAML frontmatter fields you use

**search**
- `default_limit` - Number of results (default: 10)
- `hide_incidents` - Hide incident docs by default (true/false)
- `show_incidents_on` - Keywords that show incidents (array)

**encoding**
- `default_encoding` - Default encoding (usually "utf-8")
- `auto_detect` - Auto-detect encoding (true/false)
- `fallback_encodings` - Encodings to try if detection fails
- `detection_confidence_threshold` - Confidence level (0.0-1.0)

**auto_hook** - Auto-install Claude Code hooks (true/false)

**index_dirs** - Directories to index
- String: `"guides"` - index this directory
- Object: `{"path": ".git", "exclude": true}` - exclude this directory

### YAML Frontmatter Support

tantivy2agents parses YAML frontmatter from markdown files:

```markdown
---
title: My Guide
tags: [docker, networking]
servers: [s8, s9]
---

# Content here
```

**Schema must include frontmatter fields:**
```json
"schema_fields": {
  "title": {"weight": 2.0, "tokenizer": "en_stem"},
  "tags": {"weight": 1.5, "tokenizer": "default"},
  "servers": {"weight": 1.5, "tokenizer": "default"},
  "body": {"weight": 1.0, "tokenizer": "en_stem"}
}
```

## What to Index (Best Practices)

### ✅ Index These

**Searchable documentation:**
- `guides/` - User guides, how-to articles
- `docs/` - Technical documentation
- `incidents/` - Incident reports (with hide_incidents)
- `k8s/` - Kubernetes documentation
- Any directory with markdown documentation

**Example:**
```json
"index_dirs": ["guides", "docs", "k8s", "incidents"]
```

### ❌ Don't Index These

**Files loaded by name:**
- `servers/` - If you load `servers/s8.md` directly by name
- Any directory where you access files by specific path

**Internal configuration:**
- `.claude/` - Commands, agents, settings
- `.git/` - Version control
- `.venv/`, `node_modules/` - Dependencies

**Project metadata:**
- Root `.md` files (CLAUDE.md, README.md, TODO.md)
- Configuration files

**Example excludes:**
```json
"index_dirs": [
  "guides",
  {"path": ".git", "exclude": true},
  {"path": ".venv", "exclude": true},
  {"path": ".claude", "exclude": true}
]
```

**Why?**
- Keeps index small and focused
- Search results prioritize guides
- Faster indexing and searching
- No pollution from internal files

## Claude Code Hook Integration

### Automatic Hook Installation

During install with `auto_hook: true`:
```json
"auto_hook": true
```

Automatically adds hook to `.claude/settings.json`.

### Manual Hook Configuration

Set in config:
```json
"auto_hook": false
```

Then configure in `.claude/settings.json`:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "tantivy2agents hook-clear"
          }
        ]
      }
    ]
  }
}
```

**Hook marks index outdated when files are edited** - next search triggers reindex.

## Search Best Practices

### Use 2-4 Keywords

**Good:**
```bash
tantivy2agents search "ssl certificate"
tantivy2agents search "docker networking bridge"
tantivy2agents search "zfs pool space"
```

**Bad:**
```bash
tantivy2agents search "how do i fix the ssl certificate that expired"
# Too many words = poor results
```

### Understand BM25 Ranking

Search results ranked by BM25 score:
- Higher score = better match
- Considers: term frequency, document length, field weights
- Title matches score higher than body matches (if weight is higher)

**Example output:**
```
guides/ssl-certificate.md
  ssl certificat expired - acm http challeng fix
  [score: 8.219]  ← Highest score = best match
```

### Search Specific Fields

Schema fields determine what's searchable:
- `title` - Document title (high weight)
- `body` - Content (baseline weight)
- `tags` - YAML tags (medium weight)
- `servers` - YAML servers (medium weight)
- `path` - File path (low weight)

Query: `"docker networking"` searches ALL fields.

## Common Workflows

### Initial Setup

```bash
# 1. Install and create config
tantivy2agents install

# 2. Review config, adjust if needed
cat .tantivi2agents.json

# 3. Build index
tantivy2agents index

# 4. Test search
tantivy2agents search "test query"
```

### Regular Usage

```bash
# Search documentation
tantivy2agents search "your problem"

# Results guide you to relevant docs
# Read the guides for solutions
```

### After Config Changes

```bash
# Modified .tantivi2agents.json
# Rebuild index
tantivy2agents index --force

# Verify
tantivy2agents status
```

### Troubleshooting

```bash
# Check what's indexed
tantivy2agents status

# Check which files will be indexed
tantivy2agents index --files

# See directories
tantivy2agents index --dirs

# Clear and rebuild
tantivy2agents clear
tantivy2agents index
```

## Example: Infrastructure Project

### Project Structure

```
project/
├── guides/                # User guides (index)
│   ├── ssl-certificate.md
│   ├── zfs.md
│   └── server-info.md
├── servers/               # Server docs (don't index - loaded by name)
│   ├── s8.md
│   └── s9.md
├── k8s/                   # K8s docs (index)
│   ├── README.md
│   └── APP.md
├── incidents/             # Incidents (index, hide by default)
│   └── 2025-09-01-ssl.md
├── .claude/               # Internal (don't index)
├── CLAUDE.md              # Project metadata (don't index)
└── README.md              # Project metadata (don't index)
```

### Configuration

```json
{
  "version": "1.0",
  "index_dir": ".tantivy-data",

  "schema_fields": {
    "title": {"weight": 2.0, "tokenizer": "en_stem"},
    "body": {"weight": 1.0, "tokenizer": "en_stem"},
    "tags": {"weight": 1.5, "tokenizer": "default"},
    "servers": {"weight": 1.5, "tokenizer": "default"},
    "path": {"weight": 0.5, "tokenizer": "raw"}
  },

  "search": {
    "default_limit": 10,
    "hide_incidents": true,
    "show_incidents_on": ["incident", "emergency"]
  },

  "auto_hook": false,

  "index_dirs": [
    "guides",
    "incidents",
    "k8s"
  ]
}
```

### Results

```bash
tantivy2agents index
# Successfully indexed 10 documents

tantivy2agents search "ssl certificate"
# Found 4 results:
#   guides/ssl-certificate.md [score: 8.219]  ← Guide first!
#   k8s/README.md [score: 3.727]
#   ...
# No servers, no .claude, no CLAUDE.md ✓
```

## Troubleshooting

### Problem: Search Returns Wrong Files

**Symptom:** Search returns CLAUDE.md, README.md, servers/s8.md

**Cause:** Indexing too much

**Fix:**
```bash
# Check what's indexed
tantivy2agents status  # Shows 75 documents

# Review config
cat .tantivi2agents.json
# Problem: "index_dirs": ["."]  ← indexes everything

# Fix: Be specific
# "index_dirs": ["guides", "docs"]

# Rebuild
tantivy2agents clear && tantivy2agents index
# Now: 10 documents
```

### Problem: YAML Fields Not Searchable

**Symptom:** Can't search by tags or servers

**Cause:** Schema missing fields

**Fix:**
```json
"schema_fields": {
  "title": {"weight": 2.0, "tokenizer": "en_stem"},
  "body": {"weight": 1.0, "tokenizer": "en_stem"},
  "tags": {"weight": 1.5, "tokenizer": "default"},     // Add this
  "servers": {"weight": 1.5, "tokenizer": "default"}   // Add this
}
```

Rebuild: `tantivy2agents index --force`

### Problem: Config Option Ignored

**Symptom:** Added config option but it has no effect

**Cause:** Option doesn't exist (made up)

**Fix:**
```bash
# Verify option exists
tantivy2agents config-example | grep "your_option"

# Example: "hide_servers" doesn't exist
# Only "hide_incidents" is supported

# Solution: Don't index servers/ instead
```

### Problem: Index Outdated After Edits

**Symptom:** Search results don't reflect recent changes

**Cause:** No Claude hook configured

**Fix:**
```json
// In .claude/settings.json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          {"type": "command", "command": "tantivy2agents hook-clear"}
        ]
      }
    ]
  }
}
```

## Performance Tips

1. **Keep index small** - Only index searchable docs
2. **Exclude large directories** - .venv, node_modules, .git
3. **Use appropriate patterns** - `*.md` not `*.*`
4. **Rebuild selectively** - Use `index` (incremental) not `index --force` (full rebuild)
5. **Limit search results** - `--limit 10` is usually enough

## Key Learnings

**Always use install first** - Auto-detection saves time and errors

**Don't index everything** - Be selective about index_dirs

**Never invent config options** - Use config-example to verify

**Match schema to frontmatter** - Include all YAML fields

**Test search results** - Verify guides appear first, not metadata

**Use Claude hooks** - Auto-update index on file edits

*Created: 2025-12-09 via /orgoj-claude:self-learn*
