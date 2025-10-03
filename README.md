# Tantivy Agent - Universal Document Indexing and Search

All-in-one solution for document indexing and search using Tantivy with flexible JSON configuration.

## Features

- **All-in-one script** - Single Python file with complete functionality
- **Flexible configuration** - JSON-based config with global and directory-specific patterns
- **Automatic data management** - Data stored outside repository with auto .gitignore
- **Claude Code integration** - Automatic hook installation for real-time index updates
- **Incremental indexing** - Only reindex when files change
- **Universal design** - Works in any project after linking

## Quick Start

### 1. Link to Your Project

```bash
# In your project directory
ln -s /path/to/tantivi2agents/tantivy-agent.py ./tools/tantivy-agent.py
```

### 2. Create Configuration

Copy the example config to your project root:

```bash
cp /path/to/tantivi2agents/examples/.tantivi2agents.json ./
```

### 3. Install Hooks and Create Index

```bash
./tools/tantivy-agent.py install
./tools/tantivy-agent.py index
```

### 4. Search Your Documents

```bash
./tools/tantivy-agent.py search "your query"
./tools/tantivy-agent.py search "server configuration" --limit 5
```

## Configuration

The `.tantivi2agents.json` file controls all behavior:

### Basic Structure

```json
{
  "version": "1.0",
  "index_dir": ".tantivy-data",
  "global_patterns": {
    "include": ["*.md", "*.txt"],
    "exclude": ["*.tmp", "*~"]
  },
  "index_dirs": [
    "docs/",                    // Uses global patterns
    {"path": "guides/", "include": ["*.md"]},  // Custom patterns
    "servers/"
  ],
  "schema_fields": { /* field configuration */ },
  "search": { /* search settings */ },
  "auto_hook": true
}
```

### Configuration Options

- **index_dir**: Directory for storing index data (auto-added to .gitignore)
- **global_patterns**: Default file patterns for all directories
- **index_dirs**: List of directories to index (string or object with custom patterns)
- **schema_fields**: Tantivy field configuration with weights and tokenizers
- **search**: Search behavior settings
- **auto_hook**: Enable/disable automatic Claude hook installation

## Commands

```bash
# Create or update index
./tools/tantivy-agent.py index
./tools/tantivy-agent.py index --force  # Force rebuild

# Search documents
./tools/tantivy-agent.py search "query"
./tools/tantivy-agent.py search "query" --limit 5

# Clear index
./tools/tantivy-agent.py clear

# Install Claude hooks
./tools/tantivy-agent.py install

# Hook command (used automatically by Claude)
./tools/tantivy-agent.py hook-clear
```

## Claude Code Integration

When `auto_hook` is enabled, the agent automatically installs hooks in `.claude/CLAUDE.md`:

```yaml
hooks:
  PostToolUse:
    - matcher: "Edit|Write|MultiEdit"
      hooks:
        - type: "command"
          command: "./tools/tantivy-agent.py hook-clear"
```

This ensures the index is automatically marked for updates when files are modified.

## Document Processing

### Markdown Files

- **YAML Frontmatter**: Extracts metadata from `---` blocks
- **Auto-titles**: Uses first H1 or filename
- **Server metadata**: Auto-generates server names for files in `servers/` directory
- **Hashtags**: Extracts tags from content

### Schema Fields

- **title**: Document title (weight: 2.0)
- **body**: Full text content (weight: 1.0)
- **tags**: Tags and keywords (weight: 1.5)
- **servers**: Server names (weight: 1.5)
- **path**: File path (weight: 0.5)

## File Patterns

### Global vs Directory-Specific

```json
{
  "global_patterns": {
    "include": ["*.md", "*.txt"],
    "exclude": ["*.tmp", "*~"]
  },
  "index_dirs": [
    "docs/",  // Uses global patterns
    {
      "path": "guides/",
      "include": ["*.md", "*.rst"],  // Override global
      "exclude": ["*draft*"]         // Merge with global
    }
  ]
}
```

### Pattern Matching

- Uses Unix shell-style wildcards
- Multiple include patterns (OR logic)
- Multiple exclude patterns (filtered after include)
- Supports `*`, `?`, and character classes

## Search Features

### Default Search

Searches across all configured fields with field-specific weights:

```bash
./tools/tantivy-agent.py search "server configuration"
```

### Export Search Results

Export search results in multiple formats:

```bash
# JSON export (structured data)
./tools/tantivy-agent.py search "server" --format json --output results.json

# CSV export (spreadsheet compatible)
./tools/tantivy-agent.py search "config" --format csv -o search_results.csv

# Text export (human readable)
./tools/tantivy-agent.py search "guide" --format txt --output guide_results.txt

# Export to terminal (no file specified)
./tools/tantivy-agent.py search "server" --format json
```

### Export Formats

#### JSON Export
- Structured data with metadata
- Includes full document content
- Timestamp and query information
- Perfect for programmatic processing

#### CSV Export
- Spreadsheet-compatible format
- Key fields: Score, Path, Title, Tags, Servers
- Easy for data analysis

#### Text Export
- Human-readable report format
- Includes document previews
- Metadata and timestamps
- Great for documentation

### Result Filtering

- **Incident filtering**: Hides incident files unless "incident" keyword is used
- **Configurable limits**: Control number of results returned
- **Score-based ranking**: Results ranked by relevance scores

### Search Output

```
🎯 Found 3 results:

📄 guides/server-setup.md
   Complete Server Setup Guide
   [score: 0.892]

📄 servers/production.md
   Production Server Configuration
   [score: 0.756]
```

## Data Management

### Storage Locations

- **Index data**: `.tantivy-data/index/` (outside repository)
- **Cache files**: `.tantivy-data/cache/`
- **Index metadata**: `.tantivy-data/index_info.json`

### Automatic .gitignore

The agent automatically adds the data directory to `.gitignore`:

```
# Tantivy Agent data
.tantivy-data/
```

### Incremental Indexing

The agent tracks file modification times and only rebuilds the index when:
- Files are modified
- Files are added or removed
- Force rebuild is requested (`--force` flag)

## Migration from Original Scripts

If you're migrating from the original 4-script setup:

| Original Script | New Command |
|-----------------|-------------|
| `./bin/tantivy-index` | `./tools/tantivy-agent.py index` |
| `./bin/tantivy-search "query"` | `./tools/tantivy-agent.py search "query"` |
| `./bin/tantivy-clear` | `./tools/tantivy-agent.py clear` |
| `./bin/tantivy-hook` | Automatic via Claude hooks |

## Requirements

- Python 3.8+
- Dependencies: `PyYAML`, `tantivy`

Install with:
```bash
pip install -r requirements.txt
```

## Troubleshooting

### Index Not Found
```
❌ Index not found. Run 'python tantivy-agent.py index' first
```
Solution: Create the index with the `index` command.

### No Files Found
```
⚠️ No files found to index
```
Solution: Check your `index_dirs` and `global_patterns` configuration.

### Configuration Error
```
Error loading config: ...
```
Solution: Validate your JSON syntax and check file permissions.

### Permission Denied
```
Permission denied: .tantivy-data/
```
Solution: Check file permissions in your project directory.

## Examples

### Project with Multiple Document Types

```json
{
  "index_dirs": [
    {"path": "docs/", "include": ["*.md", "*.rst"]},
    {"path": "api/", "include": ["*.md", "*.json"]},
    {"path": "guides/", "include": ["*.md"]},
    "notes/"
  ]
}
```

### Exclude Draft Files

```json
{
  "global_patterns": {
    "exclude": ["*draft*", "*wip*", "*.tmp"]
  }
}
```

### Custom Field Weights

```json
{
  "schema_fields": {
    "title": {"weight": 3.0, "tokenizer": "en_stem"},
    "body": {"weight": 1.0, "tokenizer": "en_stem"},
    "tags": {"weight": 2.0, "tokenizer": "keyword"}
  }
}
```

## Testing

### Run Tests

```bash
# Run all tests
python run_tests.py

# Or run specific test file
python tests/test_basic.py
```

### Test Coverage

The test suite covers:

- ✅ **Basic functionality** - All commands work correctly
- ✅ **Configuration loading** - Default and custom configs
- ✅ **File parsing** - Markdown frontmatter extraction
- ✅ **Pattern matching** - Include/exclude patterns
- ✅ **Export functionality** - JSON/CSV/TXT export formats

### Test Environment

Tests run in isolated temporary directories and don't affect your project data. They verify:

1. Script execution and CLI interface
2. Configuration file handling
3. Document parsing accuracy
4. File pattern matching
5. Index creation and search functionality

## License

MIT License - see LICENSE file for details.