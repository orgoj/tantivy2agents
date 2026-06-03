---
name: tantivy2agents-setup
description: Setup and configuration of tantivy2agents. Use when installing, configuring .tantivy2agents.json, or setting up Claude Code hooks.
---

# tantivy2agents - Setup and Configuration Guide

Setup and configuration guide for Tantivy Agent document indexing and search.

## Installation

### Method 1: uvx (Recommended - No Installation)

Run directly from git repository without installing:

```bash
# Run from git repo
uvx --from git+https://github.com/orgoj/tantivy2agents tantivy2agents --help

# Install in current project
uvx --from git+https://github.com/orgoj/tantivy2agents tantivy2agents install

# Create index
uvx --from git+https://github.com/orgoj/tantivy2agents tantivy2agents index

# Search
uvx --from git+https://github.com/orgoj/tantivy2agents tantivy2agents search "your query"
```

### Method 2: uv or pip

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

# Setup development environment
mise run install   # or: uv sync && pre-commit install

# Run in development mode
uv run tantivy2agents --help
```

## Auto-Setup (Recommended)

The `install` command auto-detects your project type and creates optimal configuration:

```bash
# Install in current project
tantivy2agents install

# Install in another project
tantivy2agents install --target /path/to/project

# Skip config creation (use existing)
tantivy2agents install --no-config
```

**What install does:**
1. Detects project type (Python, Node.js, Java, Rust, Generic)
2. Creates `.tantivy2agents.json` with optimal settings
3. Installs Claude Code hooks for auto-index updates
4. Adds index directory to `.gitignore`

## Project Type Detection

| Project Type | Indicators | Default `index_dirs` |
|-------------|------------|-------------------|
| **Python** | `requirements.txt`, `pyproject.toml`, `setup.py`, `src/` | `docs/**`, `src/**/*.md`, `tests/**/*.md`, exclude `.venv/`, `__pycache__/` |
| **Node.js** | `package.json`, `node_modules/` | `docs/**`, `src/**/*.md`, exclude `node_modules/`, `dist/`, `build/` |
| **Java** | `pom.xml`, `build.gradle`, `src/main/java/` | `docs/**`, `src/**/*.md`, exclude `target/`, `.idea/` |
| **Rust** | `Cargo.toml`, `src/main.rs` | `docs/**`, `src/**/*.md`, exclude `target/` |
| **Generic** | No specific indicators | `docs/**`, `*.md`, exclude `node_modules/`, `target/`, `dist/`, hidden files |

## Configuration File

Configuration is stored in `.tantivy2agents.json` in project root.

### Minimal Configuration

```json
{
  "version": "1.0",
  "index_dir": ".tantivy-data",
  "index_dirs": ["docs", "guides"]
}
```

### Complete Configuration

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
    "default_limit": 5,
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

  "auto_hook": true,

  "index_dirs": [
    "docs",
    "guides",
    {"path": ".git", "exclude": true}
  ]
}
```

## Configuration Options

### index_dir
Directory for storing index data (auto-added to .gitignore).

```json
"index_dir": ".tantivy-data"
```

### global_patterns
Default file patterns for all directories.

```json
"global_patterns": {
  "include": ["*.md", "*.txt"],
  "exclude": ["*.tmp", "*~"]
}
```

### index_dirs
Directories to index. Use string (include) or object (exclude).

```json
"index_dirs": [
  "docs",                           // Include directory
  "*.md",                           // Include all .md files
  {"path": ".git", "exclude": true} // Exclude directory
]
```

**Glob pattern support:**
- `docs/**` - Recursive docs directory
- `*.md` - All markdown in root
- `src/**/*.md` - All .md files under src/

### schema_fields
Search field configuration with weights and tokenizers.

```json
"schema_fields": {
  "title": {"weight": 2.0, "tokenizer": "en_stem"},
  "body": {"weight": 1.0, "tokenizer": "en_stem"}
}
```

**Tokenizers:**
- `en_stem` - English stemming (recommended for text)
- `default` - Standard tokenization (for tags, keywords)
- `raw` - No processing (for paths, IDs)

**Weights:** Higher = more important in search results.

### search
Search behavior settings.

```json
"search": {
  "default_limit": 5,
  "show_description": true,
  "filters": [...]
}
```

- **default_limit** - Default number of results
- **show_description** - Show description in results (default: true)
- **filters** - Path-based result filters (see below)

### Search Filters
Hide documents from specific paths unless query contains keywords.

```json
"filters": [
  {
    "name": "incidents",
    "paths": ["incidents/"],
    "hidden": true,
    "show_on_keywords": ["incident", "emergency"]
  }
]
```

- **name** - Filter name (for debugging)
- **paths** - Path prefixes to match
- **hidden** - Hide matching results by default
- **show_on_keywords** - Keywords that reveal hidden results

**Behavior:**
- Results from matching paths are hidden unless query contains a keyword
- Empty `show_on_keywords` = always hidden
- Keyword matching is case-insensitive

### encoding
File encoding detection settings.

```json
"encoding": {
  "default_encoding": "utf-8",
  "auto_detect": true,
  "fallback_encodings": ["utf-8", "cp1252", "iso-8859-1"],
  "file_specific_encodings": {
    "*.txt": "utf-8",
    "*.md": "utf-8"
  },
  "binary_extensions": ["*.jpg", "*.png", "*.pdf"],
  "detection_confidence_threshold": 0.7
}
```

### auto_hook
Enable/disable automatic Claude Code hook installation.

```json
"auto_hook": true
```

## Claude Code Hook Setup

Auto-installed when `auto_hook: true`. Hook ensures index is marked for updates when files are modified.

In `.claude/settings.json`:
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

## .gitignore

The agent automatically adds index directory to `.gitignore`:

```
# Tantivy Agent data
.tantivy-data/
```

## Troubleshooting Setup

**Config file not found:**
- Run `tantivy2agents install` to create default config
- Or manually create `.tantivy2agents.json` in project root

**Wrong files indexed:**
- Check `index_dirs` configuration
- Be specific about directories to index
- Don't index root directory with `"."`

**Auto-detection wrong:**
- Manually create `.tantivy2agents.json`
- Use `tantivy2agents config-example` for template
- Customize for your project structure

**Hooks not installed:**
- Check `.claude/settings.json` exists
- Verify `auto_hook: true` in config
- Run `tantivy2agents install` again

## Getting More Help

**View configuration template:**
```bash
tantivy2agents config-example
```

**View usage documentation:**
```bash
tantivy2agents skill-usage   # Daily usage commands
```

**Show setup guide (this file):**
```bash
tantivy2agents skill-setup
```
