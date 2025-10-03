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

### Automatic Installation (Recommended)

The Tantivy Agent can automatically install itself in any project:

```bash
# Install in current project (auto-detects project type)
python /path/to/tantivi2agents/tantivy2agents.py install

# Install in specific target directory
python /path/to/tantivi2agents/tantivy2agents.py install --target /path/to/project

# Install without creating default config
python /path/to/tantivi2agents/tantivy2agents.py install --no-config
```

### Manual Installation

#### 1. Link to Your Project (Optional)

```bash
# In your project directory - create your preferred command name
ln -s /path/to/tantivi2agents/tantivy2agents.py ./tools/tantivy2agent
# or any other name you prefer
```

#### 2. Create Configuration

Copy the example config to your project root:

```bash
cp /path/to/tantivi2agents/examples/.tantivi2agents.json ./
```

#### 3. Install Hooks and Create Index

```bash
./tools/tantivy2agent install
./tools/tantivy2agent index
```

#### 4. Search Your Documents

```bash
./tools/tantivy2agent search "your query"
./tools/tantivy2agent search "server configuration" --limit 5
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
./tools/tantivy2agent index
./tools/tantivy2agent index --force  # Force rebuild

# Search documents
./tools/tantivy2agent search "query"
./tools/tantivy2agent search "query" --limit 5

# Export search results
./tools/tantivy2agent search "server" --format json --output results.json
./tools/tantivy2agent search "config" --format csv -o analysis.csv

# Clear index
./tools/tantivy2agent clear

# Install Tantivy Agent (smart auto-configuration)
./tools/tantivy2agent install

# Install in specific target directory
python /path/to/tantivy2agents.py install --target /path/to/project

# Install without creating default config
python /path/to/tantivy2agents.py install --no-config

# Hook command (used automatically by Claude)
./tools/tantivy2agent hook-clear
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
            "command": "./tools/tantivy2agents.py hook-clear"
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

### Default Search

Searches across all configured fields with field-specific weights:

```bash
./tools/tantivy2agent search "server configuration"
```

### Export Search Results

Export search results in multiple formats:

```bash
# JSON export (structured data)
./tools/tantivy2agent search "server" --format json --output results.json

# CSV export (spreadsheet compatible)
./tools/tantivy2agent search "config" --format csv -o search_results.csv

# Text export (human readable)
./tools/tantivy2agent search "guide" --format txt --output guide_results.txt

# Export to terminal (no file specified)
./tools/tantivy2agent search "server" --format json
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
| `./tools/tantivy2agent index` | Create or update document index |
| `./tools/tantivy2agent search "query"` | Search in indexed documents |
| `./tools/tantivy2agent clear` | Clear the index |
| `./tools/tantivy2agent install` | Install Tantivy Agent with auto-configuration |
| `./tools/tantivy2agent hook-clear` | Clear index (used by Claude hooks) |

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