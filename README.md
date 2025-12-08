# Tantivy Agent - Universal Document Indexing and Search

All-in-one solution for document indexing and search using Tantivy with flexible JSON configuration.

## Features

- **Modern Python packaging** - Install with `uv` or `pip`, run with `uvx`
- **Czech language support** - Built-in stemmer for Czech morphology (skloňování a časování)
- **Flexible configuration** - JSON-based config with global and directory-specific patterns
- **Automatic data management** - Data stored outside repository with auto .gitignore
- **Claude Code integration** - Automatic hook installation for real-time index updates
- **Incremental indexing** - Only reindex when files change
- **Universal design** - Works in any project

## Quick Start

### Using uvx (Recommended - No Installation)

Run directly from git repository without installing:

```bash
# Run from git repo
uvx --from git+https://github.com/orgoj/tantivi2agents tantivy2agents --help

# Install in current project
uvx --from git+https://github.com/orgoj/tantivi2agents tantivy2agents install

# Create index
uvx --from git+https://github.com/orgoj/tantivi2agents tantivy2agents index

# Search
uvx --from git+https://github.com/orgoj/tantivi2agents tantivy2agents search "your query"
```

### Installing with uv/pip

```bash
# Install from git
uv pip install git+https://github.com/orgoj/tantivi2agents

# Or with pip
pip install git+https://github.com/orgoj/tantivi2agents

# Now use directly
tantivy2agents install
tantivy2agents index
tantivy2agents search "your query"
```

### Development Setup

```bash
# Clone repository
git clone https://github.com/orgoj/tantivi2agents
cd tantivi2agents

# Install with uv
uv sync

# Run commands
uv run tantivy2agents --help
uv run tantivy2agents install
uv run tantivy2agents index
```

### Basic Usage

```bash
# Install in current project (auto-detects project type)
tantivy2agents install

# Create index
tantivy2agents index

# Search documents
tantivy2agents search "your query"
tantivy2agents search "server configuration" --limit 5
```

## Configuration

### Smart Auto-Configuration

When you run `python tantivy2agents.py install`, the agent automatically:

1. **Detects project type** (Python, Node.js, Java, or Generic)
2. **Creates optimal configuration** based on project structure
3. **Sets up appropriate patterns** and exclusions
4. **Installs Claude hooks** and gitignore entries

### Project Type Detection

| Project Type | Indicators | Default `index_dirs` |
|-------------|------------|-------------------|
| **Python** | `requirements.txt`, `pyproject.toml`, `setup.py`, `src/` | `docs/**`, `src/**/*.md`, `tests/**/*.md`, exclude `.venv/`, `__pycache__/` |
| **Node.js** | `package.json`, `node_modules/` | `docs/**`, `src/**/*.md`, exclude `node_modules/`, `dist/`, `build/` |
| **Java** | `pom.xml`, `build.gradle`, `src/main/java/` | `docs/**`, `src/**/*.md`, exclude `target/`, `.idea/` |
| **Rust** | `Cargo.toml`, `src/main.rs` | `docs/**`, `src/**/*.md`, exclude `target/` |
| **Generic** | No specific indicators | `docs/**`, `*.md`, exclude `node_modules/`, `target/`, `dist/`, hidden files |

### Recommended Configuration

For most projects, the recommended configuration indexes all text files except common exclusions:

```json
{
  "version": "1.0",
  "index_dir": ".tantivy-data",
  "global_patterns": {
    "include": ["*.*"],
    "exclude": ["*.tmp", "*~", "*.bak", "*.log", "*.swp", "*.swo", ".DS_Store", "Thumbs.db", "*.exe", "*.dll", "*.so", "*.dylib", "*.jpg", "*.jpeg", "*.png", "*.gif", "*.bmp", "*.svg", "*.pdf", "*.zip", "*.tar", "*.gz", "*.rar", "*.7z", "*.mp3", "*.mp4", "*.avi", "*.mov", "*.wav", "*.flac", "*.ogg"]
  },
  "index_dirs": [
    ".",
    {
      "path": ".git",
      "exclude": true
    },
    {
      "path": "node_modules",
      "exclude": true
    },
    {
      "path": ".venv",
      "exclude": true
    },
    {
      "path": "target",
      "exclude": true
    },
    {
      "path": "dist",
      "exclude": true
    },
    {
      "path": "build",
      "exclude": true
    }
  ],
  "auto_hook": true
}
```

**Key points:**
- `"."` - Index entire project from root (prevents duplicates)
- `"*.*"` - Include all files, then filter with exclude patterns
- Common directories excluded (`.git`, `node_modules`, `.venv`, etc.)
- Binary files excluded (images, executables, archives, etc.)
- Temporary files excluded (`.tmp`, `*~`, `.bak`, etc.)

### Advanced Configuration

The `.tantivi2agents.json` file controls all behavior:

#### Basic Structure

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

#### Glob Pattern Support

```json
{
  "index_dirs": [
    "docs/**",                        // Recursive docs directory
    "*.md",                          // All markdown in root
    {"path": "node_modules", "exclude": true},  // Exclude directory
    {"path": "**/.*", "exclude": true},           // Exclude all hidden files
    {"path": "src/**/*.md", "include": ["*.md"]}   // Specific include patterns
  ]
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
tantivy2agents index
tantivy2agents index --force  # Force rebuild
tantivy2agents index --dirs   # Show directories to be processed
tantivy2agents index --files  # Show files to be processed

# Search documents
tantivy2agents search "query"
tantivy2agents search "query" --limit 5

# Export search results
tantivy2agents search "server" --format json --output results.json
tantivy2agents search "config" --format csv -o analysis.csv

# Clear index
tantivy2agents clear

# Install Tantivy Agent (smart auto-configuration)
tantivy2agents install

# Install in specific target directory
tantivy2agents install --target /path/to/project

# Install without creating default config
tantivy2agents install --no-config

# Show index status and statistics
tantivy2agents status

# Analyze file encodings
tantivy2agents encoding-info

# Hook command (used automatically by Claude)
tantivy2agents hook-clear
```

## Claude Code Integration

When `auto_hook` is enabled, the agent automatically installs hooks in `.claude/settings.json`:

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

### Czech Language Support

Tantivy Agent includes built-in support for Czech language search with automatic morphological normalization. Search queries and indexed content are automatically stemmed to handle different word forms.

**Supported morphology:**
- **Verb conjugation** (časování): dokončit, dokončil, dokončila, dokončeno → same results
- **Noun declension** (skloňování): úkol, úkoly, úkolů, úkolem → same results
- **Adjective forms**: projekt, projekty, projektů, projektem → same results

**How it works:**
- All text is automatically normalized during indexing
- Search queries are normalized the same way
- No configuration needed - works out of the box
- Zero external dependencies - lightweight implementation

**Example:**
```bash
# All these queries find the same documents:
tantivy2agents search "dokončit"      # infinitive
tantivy2agents search "dokončil"      # past tense
tantivy2agents search "dokončeno"     # passive

# Works for nouns too:
tantivy2agents search "úkol"          # singular
tantivy2agents search "úkoly"         # plural
tantivy2agents search "úkolů"         # genitive plural
```

**Note:** This stemmer is optimized for Czech but also works reasonably well for other Slavic languages with similar morphology.

### Default Search

Searches across all configured fields with field-specific weights:

```bash
tantivy2agents search "server configuration"
```

### Export Search Results

Export search results in multiple formats:

```bash
# JSON export (structured data)
tantivy2agents search "server" --format json --output results.json

# CSV export (spreadsheet compatible)
tantivy2agents search "config" --format csv -o search_results.csv

# Text export (human readable)
tantivy2agents search "guide" --format txt --output guide_results.txt

# Export to terminal (no file specified)
tantivy2agents search "server" --format json
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
.tantivi2agents/
```

### Incremental Indexing

The agent tracks file modification times and only rebuilds the index when:
- Files are modified
- Files are added or removed
- Force rebuild is requested (`--force` flag)

## Command Summary

| Command | Description |
|---------|-------------|
| `tantivy2agents index` | Create or update document index (use --dirs/--files for diagnostics) |
| `tantivy2agents search "query"` | Search in indexed documents |
| `tantivy2agents clear` | Clear the index |
| `tantivy2agents install` | Install Tantivy Agent with auto-configuration |
| `tantivy2agents hook-clear` | Clear index (used by Claude hooks) |
| `tantivy2agents encoding-info` | Analyze file encodings in project |
| `tantivy2agents status` | Display index statistics and status information |

## System-wide Installation

With `uv` or `pip`, you can install tantivy2agents system-wide:

```bash
# Using uv (recommended)
uv pip install git+https://github.com/orgoj/tantivi2agents

# Using pip
pip install git+https://github.com/orgoj/tantivi2agents

# Now use from anywhere
tantivy2agents index
tantivy2agents search "my query"
tantivy2agents install
```

Or use `uvx` to run without installing:

```bash
uvx --from git+https://github.com/orgoj/tantivi2agents tantivy2agents search "query"
```

## Status Command

The `status` command provides detailed information about your index and system status:

```bash
tantivy2agents status
```

### What Status Shows

The status command displays comprehensive information about:

#### 📊 Index Statistics
- **Document count**: Number of documents in the index
- **Last update**: When the index was last rebuilt
- **Index size**: Disk space used by the index
- **Index files**: Number of files that make up the index

#### 📂 File Information
- **Files to index**: Total files matching your patterns
- **Files available**: Files that exist and can be indexed
- **Missing files**: Files that were indexed but have been deleted
- **Last modified**: Most recent file modification time

#### 🔧 System Information
- **Tantivy version**: Version of the Tantivy library
- **Index status**: Whether the index is up to date or needs rebuilding
- **Project paths**: Locations of config and index files

### Example Output

```
📊 Tantivy Agent Status

📁 Project: /home/user/myproject
📄 Config: .tantivi2agents.json
🗂️  Index: .tantivy-data/index/

📈 Index Statistics
   Documents: 1,234
   Last update: 2025-01-06 19:30:45
   Index size: 15.2 MB
   Index files: 12
   Searchable docs: 1,234

📂 File Information
   Files to index: 200
   Files available: 195
   Missing files: 5
   Last modified: 2025-01-06 18:45:22

🔧 System
   Tantivy version: 0.24.0
   Index status: ✅ Up to date
```

### When to Use Status

Use the status command to:
- **Check index health**: Verify your index is complete and up to date
- **Monitor size**: Track how large your index is getting
- **Debug issues**: See why search might not be working properly
- **File verification**: Ensure all expected files are indexed
- **System info**: Get version and configuration details

## File Encoding Support

The Tantivy Agent supports automatic detection and conversion of different file encodings to UTF-8 for indexing.

### Automatic Encoding Detection

- **Smart detection**: Uses `charset_normalizer` library for reliable encoding detection
- **Fallback support**: Multiple encoding fallbacks for problematic files
- **Binary file exclusion**: Automatically skips binary files (images, PDFs, executables)
- **Configurable settings**: Granular control per file type and directory

### Encoding Configuration

Add encoding settings to your `.tantivi2agents.json`:

```json
{
  "encoding": {
    "default_encoding": "utf-8",
    "auto_detect": true,
    "fallback_encodings": ["utf-8", "cp1252", "iso-8859-1", "cp1250", "cp1251"],
    "file_specific_encodings": {
      "*.txt": "utf-8",
      "*.md": "utf-8",
      "legacy/*.txt": "cp1252"
    },
    "binary_extensions": ["*.jpg", "*.png", "*.gif", "*.pdf", "*.zip"],
    "detection_confidence_threshold": 0.7
  }
}
```

### Encoding Options

- **default_encoding**: Fallback encoding when auto-detection fails
- **auto_detect**: Enable/disable automatic encoding detection
- **fallback_encodings**: List of encodings to try when detection fails
- **file_specific_encodings**: Encoding rules for specific file patterns
- **binary_extensions**: File extensions to treat as binary and skip
- **detection_confidence_threshold**: Minimum confidence for auto-detection (0.0-1.0)

### Encoding Diagnostics

Analyze file encodings in your project:

```bash
# Show encoding information for all files
tantivy2agents encoding-info
```

The `encoding-info` command shows:
- Files with non-UTF-8 encodings
- Encoding detection statistics
- Binary files that will be skipped
- Files with encoding issues

### Supported Encodings

Common legacy encodings supported:
- **Windows**: cp1252 (Western European), cp1250 (Central European)
- **ISO**: iso-8859-1, iso-8859-2, iso-8859-15
- **Unicode**: utf-8, utf-16, utf-32
- **Asian**: cp932 (Japanese), gb2312 (Chinese), euc-kr (Korean)

## Requirements

- Python 3.10+
- Dependencies: `PyYAML`, `tantivy`, `charset-normalizer`

Install with uv (recommended):
```bash
uv pip install git+https://github.com/orgoj/tantivi2agents
```

Or for development:
```bash
git clone https://github.com/orgoj/tantivi2agents
cd tantivi2agents
uv sync
```

## Troubleshooting

### Index Not Found
```
❌ Index not found. Run './tools/tantivy2agent index' first
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
# Run all test suites (Basic + Install functionality)
python run_tests.py

# Run specific test suite
python tests/test_basic.py      # Basic functionality tests
python tests/test_install.py    # Install functionality tests
```

### Test Coverage

The test suite covers:

#### Basic Functionality (9 tests)
- ✅ **All commands work correctly** - index, search, clear, install
- ✅ **Configuration loading** - Default and custom configs
- ✅ **File parsing** - Markdown frontmatter extraction
- ✅ **Pattern matching** - Include/exclude patterns
- ✅ **Export functionality** - JSON/CSV/TXT export formats
- ✅ **Project detection** - Python, Node.js, Java, Generic
- ✅ **Glob patterns** - Recursive patterns and exclude logic
- ✅ **Default configs** - Smart configuration for project types
- ✅ **Install workflow** - Complete installation process

#### Install Functionality (16 tests)
- ✅ **Project Type Detection** - Accurate detection for all project types
- ✅ **Default Configurations** - Optimal settings per project type
- ✅ **Glob Pattern Processing** - Recursive patterns and exclusions
- ✅ **Complete Install Workflow** - Symlink, config, gitignore, hooks

### Test Environment

- ✅ **Automated testing only** - No manual testing allowed
- ✅ **tmp/ directory** - All test data in .gitignore
- ✅ **Repeatable tests** - Deterministic, clean state each run
- ✅ **Professional practices** - Senior-level code quality standards

Test files run in isolated temporary directories and verify:
1. All functionality via automated tests
2. Configuration generation and validation
3. File pattern matching and glob expansion
4. Complete installation workflow (symlinks, configs, gitignore, hooks)
5. CLI interface and command execution
6. Project type detection accuracy

### Development Rules

See `.claude/CLAUDE.md` for strict development standards:
- ❌ **NO manual testing** ever
- ✅ **ALWAYS** automated tests
- ✅ **ALWAYS** update README after changes
- ✅ **ALWAYS** maintain code quality standards

## License

MIT License - see LICENSE file for details.
