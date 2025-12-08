"""
Tantivy Agent - Main agent class for document indexing and search.
"""

import csv
import fnmatch
import glob
import json
import os
import shutil
import sys
import time
from datetime import datetime
from typing import Optional

import tantivy
import yaml

try:
    from charset_normalizer import detect
except ImportError:
    detect = None

from .czech_stemmer import normalize_czech_text


class TantivyAgent:
    """Main Tantivy Agent class with all functionality"""

    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialize agent with configuration"""
        self.project_root = self._find_project_root()
        self.config_path = config_path or os.path.join(
            self.project_root, ".tantivi2agents.json"
        )
        self.config = self._load_config()

    def _find_project_root(self):
        """Find project root by looking for .git directory"""
        current = os.getcwd()
        while current != "/":
            if os.path.exists(os.path.join(current, ".git")):
                return current
            current = os.path.dirname(current)
        return os.getcwd()

    def _load_config(self):
        """Load configuration from JSON file with defaults"""
        default_config = {
            "version": "1.0",
            "index_dir": ".tantivy-data",
            "global_patterns": {
                "include": ["*.*"],
                "exclude": [
                    "*.tmp",
                    "*~",
                    "*.bak",
                    "*.log",
                    "*.swp",
                    "*.swo",
                    ".DS_Store",
                    "Thumbs.db",
                    "*.exe",
                    "*.dll",
                    "*.so",
                    "*.dylib",
                    "*.jpg",
                    "*.jpeg",
                    "*.png",
                    "*.gif",
                    "*.bmp",
                    "*.svg",
                    "*.pdf",
                    "*.zip",
                    "*.tar",
                    "*.gz",
                    "*.rar",
                    "*.7z",
                    "*.mp3",
                    "*.mp4",
                    "*.avi",
                    "*.mov",
                    "*.wav",
                    "*.flac",
                    "*.ogg",
                ],
            },
            "index_dirs": [
                ".",
                {"path": ".git", "exclude": True},
                {"path": "node_modules", "exclude": True},
                {"path": ".venv", "exclude": True},
                {"path": "target", "exclude": True},
                {"path": "dist", "exclude": True},
                {"path": "build", "exclude": True},
            ],
            "schema_fields": {
                "title": {"weight": 2.0, "tokenizer": "en_stem"},
                "body": {"weight": 1.0, "tokenizer": "en_stem"},
                "tags": {"weight": 1.5, "tokenizer": "default"},
                "servers": {"weight": 1.5, "tokenizer": "default"},
                "path": {"weight": 0.5, "tokenizer": "raw"},
            },
            "search": {"default_limit": 10, "hide_incidents": True},
            "encoding": {
                "default_encoding": "utf-8",
                "auto_detect": True,
                "fallback_encodings": [
                    "utf-8",
                    "cp1252",
                    "iso-8859-1",
                    "cp1250",
                    "cp1251",
                ],
                "file_specific_encodings": {"*.txt": "utf-8", "*.md": "utf-8"},
                "binary_extensions": [
                    "*.jpg",
                    "*.jpeg",
                    "*.png",
                    "*.gif",
                    "*.bmp",
                    "*.svg",
                    "*.pdf",
                    "*.zip",
                    "*.tar",
                    "*.gz",
                    "*.rar",
                    "*.exe",
                    "*.dll",
                    "*.so",
                    "*.dylib",
                ],
                "detection_confidence_threshold": 0.7,
            },
            "auto_hook": True,
        }

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    user_config = json.load(f)
                # Merge with defaults
                config = {**default_config, **user_config}
                return config
            except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"Error loading config: {e}")
                print("Using default configuration.")

        return default_config

    def _ensure_data_dir(self):
        """Ensure data directory exists and is in .gitignore"""
        data_dir = os.path.join(self.project_root, self.config["index_dir"])
        os.makedirs(data_dir, exist_ok=True)

        # Add to .gitignore if not present
        gitignore_path = os.path.join(self.project_root, ".gitignore")
        gitignore_entry = f"{self.config['index_dir']}/"

        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r", encoding="utf-8") as f:
                gitignore_content = f.read()

            if gitignore_entry not in gitignore_content.splitlines():
                with open(gitignore_path, "a", encoding="utf-8") as f:
                    f.write(f"\n# Tantivy Agent data\n{gitignore_entry}\n")
        else:
            with open(gitignore_path, "w", encoding="utf-8") as f:
                f.write(f"# Tantivy Agent data\n{gitignore_entry}\n")

        return data_dir

    def _detect_project_type(self):
        """Detect project type based on common indicators"""
        indicators = {
            "python": [
                "setup.py",
                "pyproject.toml",
                "requirements.txt",
                "Pipfile",
                "pyvenv.cfg",
                ".venv/",
                "src/",
            ],
            "nodejs": [
                "package.json",
                "package-lock.json",
                "yarn.lock",
                "pnpm-lock.yaml",
                "node_modules/",
                "npm-debug.log*",
            ],
            "java": [
                "pom.xml",
                "build.gradle",
                "gradlew",
                "src/main/java/",
                "target/",
                ".mvn/",
            ],
            "rust": ["Cargo.toml", "Cargo.lock", "src/main.rs", "target/"],
            "go": ["go.mod", "go.sum", "main.go", "vendor/"],
            "php": ["composer.json", "composer.lock", "artisan", "vendor/"],
            "ruby": ["Gemfile", "Gemfile.lock", "Rakefile", "Gemfile.lock"],
            "web": [
                "index.html",
                "package.json",
                "webpack.config.js",
                "vite.config.js",
                "dist/",
                "build/",
            ],
        }

        project_type_scores = {}

        for proj_type, files in indicators.items():
            score = 0
            for file_pattern in files:
                if file_pattern.endswith("/"):
                    # Directory check
                    if os.path.exists(os.path.join(self.project_root, file_pattern)):
                        score += 2
                elif "*" in file_pattern or "?" in file_pattern:
                    # Glob pattern
                    if glob.glob(os.path.join(self.project_root, file_pattern)):
                        score += 1
                else:
                    # File check
                    if os.path.exists(os.path.join(self.project_root, file_pattern)):
                        score += 2
            project_type_scores[proj_type] = score

        # Return type with highest score
        if project_type_scores:
            detected_type = max(project_type_scores, key=project_type_scores.get)
            if project_type_scores[detected_type] > 0:
                return detected_type

        return "generic"

    def _get_default_config_for_project_type(self, project_type):
        """Get default configuration based on project type"""
        base_config = {
            "version": "1.0",
            "index_dir": ".tantivy-data",
            "global_patterns": {
                "include": ["*.md", "*.txt", "*.rst"],
                "exclude": ["*.tmp", "*~", "*.bak", "*.log"],
            },
            "schema_fields": {
                "title": {"weight": 2.0, "tokenizer": "en_stem"},
                "body": {"weight": 1.0, "tokenizer": "en_stem"},
                "tags": {"weight": 1.5, "tokenizer": "default"},
                "servers": {"weight": 1.5, "tokenizer": "default"},
                "path": {"weight": 0.5, "tokenizer": "raw"},
            },
            "search": {"default_limit": 10, "hide_incidents": True},
            "auto_hook": True,
        }

        project_configs = {
            "python": {
                "index_dirs": [
                    "docs/**",
                    "src/**/*.md",
                    "tests/**/*.md",
                    "*.md",
                    {"path": ".venv", "exclude": True},
                    {"path": "__pycache__", "exclude": True},
                    {"path": "**/.*", "exclude": True},
                ]
            },
            "nodejs": {
                "index_dirs": [
                    "docs/**",
                    "src/**/*.md",
                    "*.md",
                    {"path": "node_modules", "exclude": True},
                    {"path": "dist", "exclude": True},
                    {"path": "build", "exclude": True},
                    {"path": "**/.*", "exclude": True},
                ]
            },
            "java": {
                "index_dirs": [
                    "docs/**",
                    "src/**/*.md",
                    "*.md",
                    {"path": "target", "exclude": True},
                    {"path": ".idea", "exclude": True},
                    {"path": "**/.*", "exclude": True},
                ]
            },
            "rust": {
                "index_dirs": [
                    "docs/**",
                    "src/**/*.md",
                    "*.md",
                    {"path": "target", "exclude": True},
                    {"path": "**/.*", "exclude": True},
                ]
            },
            "generic": {
                "index_dirs": [
                    "docs/**",
                    "*.md",
                    "*.txt",
                    "*.rst",
                    {"path": "**/.*", "exclude": True},
                    {"path": "node_modules", "exclude": True},
                    {"path": "target", "exclude": True},
                    {"path": "dist", "exclude": True},
                    {"path": "build", "exclude": True},
                ]
            },
        }

        # Merge base config with project-specific config
        config = base_config.copy()
        if project_type in project_configs:
            config.update(project_configs[project_type])
        else:
            config.update(project_configs["generic"])

        return config

    def _expand_glob_patterns(self, pattern_list):
        """Expand glob patterns to actual directory/file paths"""
        expanded_paths = []

        for item in pattern_list:
            if isinstance(item, str):
                # Simple pattern - expand it
                if "**" in item:
                    # Recursive glob
                    matches = glob.glob(
                        os.path.join(self.project_root, item), recursive=True
                    )
                else:
                    # Regular glob
                    matches = glob.glob(os.path.join(self.project_root, item))

                # Filter to only existing directories and files
                for match in matches:
                    if os.path.exists(match):
                        rel_path = os.path.relpath(match, self.project_root)
                        expanded_paths.append(
                            {
                                "path": rel_path,
                                "type": "dir" if os.path.isdir(match) else "file",
                            }
                        )

            elif isinstance(item, dict):
                # Directory with exclude/include rules
                path_pattern = item.get("path", "")
                exclude = item.get("exclude", False)

                if "**" in path_pattern:
                    matches = glob.glob(
                        os.path.join(self.project_root, path_pattern), recursive=True
                    )
                else:
                    matches = glob.glob(os.path.join(self.project_root, path_pattern))

                for match in matches:
                    if os.path.exists(match):
                        rel_path = os.path.relpath(match, self.project_root)
                        expanded_paths.append(
                            {
                                "path": rel_path,
                                "exclude": exclude,
                                "type": "dir" if os.path.isdir(match) else "file",
                            }
                        )

        return expanded_paths

    def _get_files_for_indexing(self, show_dirs=False, show_files=False):
        """Get list of files to index based on configuration with glob pattern support"""
        files = []
        dirs_processed = []

        # First expand glob patterns in index_dirs
        expanded_dirs = self._expand_glob_patterns(self.config["index_dirs"])

        for dir_config in expanded_dirs:
            # Skip if this is marked as excluded
            if dir_config.get("exclude", False):
                continue

            dir_path = dir_config["path"]
            include_patterns = self.config["global_patterns"]["include"]
            exclude_patterns = self.config["global_patterns"]["exclude"]

            full_dir_path = os.path.join(self.project_root, dir_path)
            if not os.path.exists(full_dir_path):
                continue

            # Track directories being processed
            if show_dirs:
                dirs_processed.append(full_dir_path)

            if dir_config.get("type") == "file":
                # Single file
                rel_path = os.path.relpath(full_dir_path, self.project_root)

                # Check if file matches include patterns
                included = any(
                    self._match_pattern(rel_path, pattern)
                    for pattern in include_patterns
                )
                excluded = any(
                    self._match_pattern(rel_path, pattern)
                    for pattern in exclude_patterns
                )

                if included and not excluded:
                    # Check if file is binary before adding
                    try:
                        with open(full_dir_path, "rb") as f:
                            content_bytes = f.read()
                        if not self._is_binary_file(full_dir_path, content_bytes):
                            files.append(full_dir_path)
                            # Show files if requested
                            if show_files:
                                print(f"  {rel_path}")
                    except OSError:
                        # If we can't read the file, skip it
                        pass
            else:
                # Directory - walk through it
                for root, dirs, filenames in os.walk(full_dir_path):
                    for filename in filenames:
                        file_path = os.path.join(root, filename)
                        rel_path = os.path.relpath(file_path, self.project_root)

                        # Check include patterns
                        included = any(
                            self._match_pattern(rel_path, pattern)
                            for pattern in include_patterns
                        )

                        # Check exclude patterns
                        excluded = any(
                            self._match_pattern(rel_path, pattern)
                            for pattern in exclude_patterns
                        )

                        if included and not excluded:
                            # Check if file is binary before adding
                            try:
                                with open(file_path, "rb") as f:
                                    content_bytes = f.read()
                                if not self._is_binary_file(file_path, content_bytes):
                                    files.append(file_path)
                                    # Show files if requested
                                    if show_files:
                                        print(f"  {rel_path}")
                            except OSError:
                                # If we can't read the file, skip it
                                pass

        # Remove duplicates while preserving order
        seen = set()
        unique_files = []
        for file_path in files:
            if file_path not in seen:
                seen.add(file_path)
                unique_files.append(file_path)

        # Remove duplicates from dirs_processed as well
        unique_dirs = []
        seen_dirs = set()
        for dir_path in dirs_processed:
            if dir_path not in seen_dirs:
                seen_dirs.add(dir_path)
                unique_dirs.append(dir_path)

        # Show directories if requested
        if show_dirs:
            print("Directories to be processed:")
            for dir_path in unique_dirs:
                rel_dir = os.path.relpath(dir_path, self.project_root)
                print(f"  {rel_dir}")

        return unique_files, unique_dirs

    def _match_pattern(self, path, pattern):
        """Simple glob pattern matching"""
        return fnmatch.fnmatch(path, pattern)

    def _is_binary_file(self, file_path, content_bytes=None):
        """Check if file is binary based on extension and content"""
        encoding_config = self.config.get("encoding", {})

        # Check file extension
        binary_extensions = encoding_config.get("binary_extensions", [])
        filename = os.path.basename(file_path)

        for ext in binary_extensions:
            if fnmatch.fnmatch(filename.lower(), ext.lower()):
                return True

        # If content is provided, do binary content detection
        if content_bytes:
            # Check for null bytes (common in binary files)
            if b"\x00" in content_bytes:
                return True

            # Check for high ratio of non-printable characters
            try:
                # Try to decode as UTF-8 to see if it contains mostly text
                content_bytes.decode("utf-8")
                return False
            except UnicodeDecodeError:
                # If it can't be decoded as UTF-8 and has many non-text bytes, likely binary
                text_chars = len(
                    [b for b in content_bytes if 32 <= b <= 126 or b in [9, 10, 13]]
                )
                if len(content_bytes) > 0 and text_chars / len(content_bytes) < 0.7:
                    return True

        return False

    def _get_encoding_for_file(self, file_path):
        """Get configured encoding for a specific file based on patterns"""
        encoding_config = self.config.get("encoding", {})
        file_specific = encoding_config.get("file_specific_encodings", {})
        filename = os.path.basename(file_path)
        rel_path = os.path.relpath(file_path, self.project_root)

        # Check file-specific patterns (try both relative path and filename)
        # Sort patterns by length (longer/more specific patterns first)
        sorted_patterns = sorted(
            file_specific.items(), key=lambda x: len(x[0]), reverse=True
        )
        for pattern, encoding in sorted_patterns:
            if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(
                filename.lower(), pattern.lower()
            ):
                return encoding

        return encoding_config.get("default_encoding", "utf-8")

    def _detect_encoding(self, file_path, content_bytes):
        """Detect encoding of file content using multiple strategies"""
        encoding_config = self.config.get("encoding", {})

        # If auto-detection is disabled, use configured encoding
        if not encoding_config.get("auto_detect", True):
            return self._get_encoding_for_file(file_path)

        # First try charset_normalizer if available
        if detect:
            try:
                result = detect(content_bytes)
                confidence = result.get("confidence", 0)
                detected_encoding = result.get("encoding", "utf-8")

                threshold = encoding_config.get("detection_confidence_threshold", 0.7)
                if confidence >= threshold:
                    return detected_encoding
                elif confidence > 0.3:  # Lower confidence but still usable
                    # We'll try this encoding but have fallbacks ready
                    return detected_encoding
            except (TypeError, AttributeError, LookupError):
                pass  # Fall back to other methods

        # Fall back to configured encoding
        return self._get_encoding_for_file(file_path)

    def _read_file_with_encoding_detection(self, file_path):
        """Read file with automatic encoding detection and conversion to UTF-8"""
        try:
            # First read as bytes
            with open(file_path, "rb") as f:
                content_bytes = f.read()

            # Check if it's a binary file
            if self._is_binary_file(file_path, content_bytes):
                return None, "binary"

            # Detect encoding
            detected_encoding = self._detect_encoding(file_path, content_bytes)
            encoding_config = self.config.get("encoding", {})
            fallback_encodings = encoding_config.get("fallback_encodings", ["utf-8"])

            # Try detected encoding first
            encodings_to_try = [detected_encoding] + [
                enc for enc in fallback_encodings if enc != detected_encoding
            ]

            for encoding in encodings_to_try:
                try:
                    content = content_bytes.decode(encoding)
                    return content, encoding
                except (UnicodeDecodeError, LookupError):
                    continue

            # Last resort: try UTF-8 with error replacement
            try:
                content = content_bytes.decode("utf-8", errors="replace")
                return content, "utf-8-replace"
            except (MemoryError, SystemError):
                return None, "failed"

        except OSError as e:
            return None, f"error: {str(e)}"

    def _parse_markdown(self, file_path):
        """Parse markdown file and extract metadata"""
        import re

        try:
            content, encoding_info = self._read_file_with_encoding_detection(file_path)

            if content is None:
                if encoding_info == "binary":
                    # Skip binary files silently
                    return None
                else:
                    # Report reading errors
                    print(f"Error reading {file_path}: {encoding_info}")
                    return None

            # Log encoding detection for debugging (only if not UTF-8)
            if encoding_info != "utf-8":
                print(
                    f"  {os.path.relpath(file_path, self.project_root)}: detected encoding {encoding_info}"
                )

        except OSError as e:
            print(f"Error reading {file_path}: {e}")
            return None

        meta = {}
        body = content

        # Extract YAML frontmatter
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.S)
        if m:
            header, body = m.groups()
            try:
                meta = yaml.safe_load(header) or {}
            except yaml.YAMLError:
                # Invalid YAML frontmatter, skip it
                pass

        # Auto-generate metadata for server files
        rel_path = os.path.relpath(file_path, self.project_root)
        if not meta and rel_path.startswith("servers/"):
            server_name = os.path.splitext(os.path.basename(file_path))[0]
            servers = [server_name]

            # Add base name for numbered servers (mp1 -> mp, ferda7 -> ferda)
            if re.search(r"\d+$", server_name):
                base_name = re.sub(r"\d+$", "", server_name)
                if base_name and base_name != server_name:
                    servers.append(base_name)

            meta = {
                "servers": servers,
                "tags": ["server", "infrastructure"],
            }

        # Extract title
        title = None
        for line in body.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break

        # Apply Czech normalization for better search
        title_normalized = normalize_czech_text(title or os.path.basename(file_path))
        body_normalized = normalize_czech_text(body)

        return {
            "title": title_normalized,
            "body": body_normalized,
            "tags": " ".join(meta.get("tags", []))
            if isinstance(meta.get("tags"), list)
            else meta.get("tags", "") or "",
            "servers": " ".join(meta.get("servers", []))
            if isinstance(meta.get("servers"), list)
            else meta.get("servers", "") or "",
            "path": rel_path,
        }

    def _create_schema(self):
        """Create Tantivy schema from configuration"""
        schema_builder = tantivy.SchemaBuilder()

        for field_name, field_config in self.config["schema_fields"].items():
            schema_builder.add_text_field(
                field_name,
                stored=True,
                tokenizer_name=field_config.get("tokenizer", "en_stem"),
            )

        return schema_builder.build()

    def _should_rebuild_index(self, data_dir):
        """Check if index needs to be rebuilt based on file modifications"""
        index_info_path = os.path.join(data_dir, "index_info.json")

        if not os.path.exists(index_info_path):
            return True

        try:
            with open(index_info_path, "r") as f:
                index_info = json.load(f)

            # Check if any indexed file was modified
            for file_path in index_info.get("files", []):
                if os.path.exists(file_path):
                    file_mtime = os.path.getmtime(file_path)
                    if file_mtime > index_info.get("timestamp", 0):
                        return True
                else:
                    # File was deleted
                    return True

            return False
        except (OSError, json.JSONDecodeError, KeyError):
            # If we can't read index info or it's corrupt, rebuild
            return True

    def index_command(
        self, force: bool = False, show_dirs: bool = False, show_files: bool = False
    ) -> None:
        """Create or update document index"""
        print("Starting document indexing...")

        # Ensure data directory exists
        data_dir = self._ensure_data_dir()
        index_dir = os.path.join(data_dir, "idx")

        # Check if rebuild is needed
        if not force and not self._should_rebuild_index(data_dir):
            print("Index is up to date")
            return

        # Get files to index
        files, dirs_processed = self._get_files_for_indexing(show_dirs, show_files)
        if not files:
            print("No files found to index")
            return

        print(f"Found {len(files)} files to index")

        # Parse documents
        docs = []
        for file_path in files:
            doc = self._parse_markdown(file_path)
            if doc:
                docs.append(doc)

        if not docs:
            print("No valid documents found")
            return

        # Remove old index and create new directory
        if os.path.exists(index_dir):
            shutil.rmtree(index_dir)
        os.makedirs(index_dir, exist_ok=True)

        # Create schema and index
        schema = self._create_schema()
        index = tantivy.Index(schema, path=index_dir)

        # Index documents
        print(f"Indexing {len(docs)} documents...")
        writer = index.writer()

        for doc_data in docs:
            writer.add_document(tantivy.Document(**doc_data))

        writer.commit()

        # Save index info
        index_info = {"timestamp": time.time(), "files": files, "count": len(docs)}

        with open(os.path.join(data_dir, "index_info.json"), "w") as f:
            json.dump(index_info, f, indent=2)

        print(f"Successfully indexed {len(docs)} documents")
        print(f"Index saved to: {index_dir}")
        print("You can now search with: tantivy2agents search 'your query'")

    def search_command(
        self,
        query: str,
        limit: Optional[int] = None,
        format_output: Optional[str] = None,
        output_file: Optional[str] = None,
    ) -> None:
        """Search in indexed documents"""
        if not query:
            print("Please provide a search query")
            return

        data_dir = os.path.join(self.project_root, self.config["index_dir"])
        index_dir = os.path.join(data_dir, "idx")

        if not os.path.exists(index_dir):
            print("Index not found. Run 'tantivy2agents index' first")
            return

        try:
            # Load index
            index = tantivy.Index.open(index_dir)
            searcher = index.searcher()

            # Normalize query for Czech search
            normalized_query = normalize_czech_text(query)

            # Parse query
            field_names = list(self.config["schema_fields"].keys())
            query_parser = index.parse_query(normalized_query, field_names)

            # Search
            limit = limit or self.config["search"]["default_limit"]
            search_limit = limit * 4  # Get more results for filtering
            result = searcher.search(query_parser, search_limit)

            if not result.hits:
                print("No results found")
                return

            # Process results
            results_with_docs = []
            for score, doc_address in result.hits:
                doc = searcher.doc(doc_address)
                results_with_docs.append((score, doc_address, doc))

            # Apply filters
            filtered_results = self._apply_filters(results_with_docs, query)

            if not filtered_results:
                print("No results found after filtering")
                return

            # Export or display results
            if format_output:
                self._export_results(
                    filtered_results[:limit], query, format_output, output_file
                )
            else:
                self._display_results(filtered_results[:limit])

        except (OSError, ValueError, RuntimeError) as e:
            print(f"Search error: {e}")

    def _display_results(self, results):
        """Display results in standard format"""
        print(f"Found {len(results)} results:")
        print()

        for score, doc_address, doc in results:
            path = doc["path"][0]
            title = doc["title"][0] if doc["title"] else "No title"
            print(f"  {path}")
            print(f"   {title}")
            print(f"   [score: {score:.3f}]")
            print()

    def _export_results(self, results, query, format_output, output_file):
        """Export results in specified format"""
        if format_output.lower() == "json":
            self._export_json(results, query, output_file)
        elif format_output.lower() == "csv":
            self._export_csv(results, query, output_file)
        elif format_output.lower() == "txt":
            self._export_txt(results, query, output_file)
        else:
            print(f"Unsupported format: {format_output}")
            print("Supported formats: json, csv, txt")
            return

    def _export_json(self, results, query, output_file):
        """Export results as JSON"""
        export_data = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "total_results": len(results),
            "results": [],
        }

        for score, doc_address, doc in results:
            result_item = {
                "score": round(score, 4),
                "path": doc["path"][0] if doc["path"] else "",
                "title": doc["title"][0] if doc["title"] else "No title",
                "body": doc["body"][0] if doc["body"] else "",
                "tags": doc["tags"][0] if doc["tags"] else "",
                "servers": doc["servers"][0] if doc["servers"] else "",
            }
            export_data["results"].append(result_item)

        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            print(f"Results exported to {output_file}")
        else:
            print(json.dumps(export_data, indent=2, ensure_ascii=False))

    def _export_csv(self, results, query, output_file):
        """Export results as CSV"""
        if output_file:
            file_handle = open(output_file, "w", newline="", encoding="utf-8")
        else:
            file_handle = sys.stdout

        try:
            writer = csv.writer(file_handle)

            # Write header
            writer.writerow(["Score", "Path", "Title", "Tags", "Servers"])

            # Write results
            for score, doc_address, doc in results:
                row = [
                    f"{score:.4f}",
                    doc["path"][0] if doc["path"] else "",
                    doc["title"][0] if doc["title"] else "No title",
                    doc["tags"][0] if doc["tags"] else "",
                    doc["servers"][0] if doc["servers"] else "",
                ]
                writer.writerow(row)

            if output_file:
                print(f"Results exported to {output_file}")
            else:
                print()  # Add newline after CSV output

        finally:
            if output_file:
                file_handle.close()

    def _export_txt(self, results, query, output_file):
        """Export results as plain text"""
        if output_file:
            file_handle = open(output_file, "w", encoding="utf-8")
        else:
            file_handle = sys.stdout

        try:
            file_handle.write(f"Search Results for: '{query}'\n")
            file_handle.write(
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            file_handle.write(f"Total Results: {len(results)}\n")
            file_handle.write("=" * 60 + "\n\n")

            for i, (score, doc_address, doc) in enumerate(results, 1):
                path = doc["path"][0] if doc["path"] else ""
                title = doc["title"][0] if doc["title"] else "No title"
                body = doc["body"][0] if doc["body"] else ""
                tags = doc["tags"][0] if doc["tags"] else ""
                servers = doc["servers"][0] if doc["servers"] else ""

                file_handle.write(f"{i}. {title}\n")
                file_handle.write(f"   Path: {path}\n")
                file_handle.write(f"   Score: {score:.4f}\n")

                if tags:
                    file_handle.write(f"   Tags: {tags}\n")
                if servers:
                    file_handle.write(f"   Servers: {servers}\n")

                # Add snippet of body (first 200 characters)
                if body:
                    snippet = body.replace("\n", " ")[:200]
                    if len(body) > 200:
                        snippet += "..."
                    file_handle.write(f"   Preview: {snippet}\n")

                file_handle.write("\n")

            if output_file:
                print(f"Results exported to {output_file}")

        finally:
            if output_file:
                file_handle.close()

    def _apply_filters(self, results, query):
        """Apply filters to search results"""
        query_words = set(query.lower().split())
        filtered = []

        # Incident filtering
        hide_incidents = self.config["search"].get("hide_incidents", True)
        show_incidents_on = self.config["search"].get("show_incidents_on", ["incident"])

        for score, doc_address, doc in results:
            file_path = doc["path"][0]

            # Hide incidents unless keyword is in query
            if hide_incidents and file_path.startswith("incidents/"):
                if not any(keyword in query_words for keyword in show_incidents_on):
                    continue

            filtered.append((score, doc_address, doc))

        return filtered

    def clear_command(self) -> None:
        """Clear the index"""
        print("Clearing index...")

        data_dir = os.path.join(self.project_root, self.config["index_dir"])

        if os.path.exists(data_dir):
            shutil.rmtree(data_dir)
            print(f"Cleared index directory: {data_dir}")
        else:
            print("No index directory found")

    def install_command(
        self, target_dir: Optional[str] = None, create_config: bool = True
    ) -> None:
        """Install Tantivy Agent in target project with smart setup"""
        if target_dir:
            target_project_root = os.path.abspath(target_dir)
            print(f"Installing Tantivy Agent in {target_project_root}...")
        else:
            target_project_root = self.project_root
            print("Installing Tantivy Agent in current project...")

        # Step 1: Skip symlink creation (user will create it manually)

        # Step 2: Create default config if needed
        if create_config:
            self._create_default_config(target_project_root)

        # Step 3: Install Claude hooks in target
        self._install_claude_hooks(target_root=target_project_root)

        # Step 4: Setup .gitignore
        self._setup_gitignore(target_project_root)

        print("Installation complete!")
        print(f"Tantivy Agent installed in {target_project_root}")
        print("Run 'tantivy2agents index' to create your first index")

    def _create_default_config(self, target_project_root):
        """Create default configuration for target project"""
        config_path = os.path.join(target_project_root, ".tantivi2agents.json")

        if os.path.exists(config_path):
            print(f"Configuration already exists: {config_path}")
            return

        # Temporarily change project root for detection
        original_root = self.project_root
        self.project_root = target_project_root

        try:
            # Detect project type
            project_type = self._detect_project_type()
            print(f"Detected project type: {project_type}")

            # Get default config
            default_config = self._get_default_config_for_project_type(project_type)

            # Write config file
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=2)

            print(f"Created configuration: {config_path}")
        finally:
            # Restore original project root
            self.project_root = original_root

    def _install_claude_hooks(self, target_root=None, use_absolute_path=False):
        """Install Claude hooks in project

        Args:
            target_root: Target project root (None = use self.project_root)
            use_absolute_path: Use absolute vs relative path (for future flexibility)
        """
        target_root = target_root or self.project_root
        claude_dir = os.path.join(target_root, ".claude")
        os.makedirs(claude_dir, exist_ok=True)

        settings_path = os.path.join(claude_dir, "settings.json")

        # Load existing settings or create new
        settings = {}
        if os.path.exists(settings_path):
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)

        # Add hooks configuration
        if "hooks" not in settings:
            settings["hooks"] = {}
        if "PostToolUse" not in settings["hooks"]:
            settings["hooks"]["PostToolUse"] = []

        # Check if hook already exists
        existing_hook = None
        for hook in settings["hooks"]["PostToolUse"]:
            if "hooks" in hook:
                for subhook in hook["hooks"]:
                    if "command" in subhook and "tantivy2agent" in subhook["command"]:
                        existing_hook = hook
                        break

        if existing_hook:
            print("Claude hooks already installed")
            return

        # Add new hook - use the installed command name
        new_hook = {
            "matcher": "Edit|Write|MultiEdit",
            "hooks": [{"type": "command", "command": "tantivy2agents hook-clear"}],
        }
        settings["hooks"]["PostToolUse"].append(new_hook)

        # Write settings back
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)

        print("Claude hooks installed")

    def _setup_gitignore(self, target_project_root):
        """Setup .gitignore in target project"""
        gitignore_path = os.path.join(target_project_root, ".gitignore")
        gitignore_entries = ["# Tantivy Agent data", f"{self.config['index_dir']}/"]

        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r", encoding="utf-8") as f:
                existing_content = f.read()

            # Check if entries already exist
            entries_to_add = []
            for entry in gitignore_entries:
                if entry and entry not in existing_content.splitlines():
                    entries_to_add.append(entry)

            if entries_to_add:
                with open(gitignore_path, "a", encoding="utf-8") as f:
                    f.write("\n")
                    for entry in entries_to_add:
                        f.write(entry + "\n")
                print("Updated .gitignore")
        else:
            with open(gitignore_path, "w", encoding="utf-8") as f:
                for entry in gitignore_entries:
                    f.write(entry + "\n")
            print("Created .gitignore")

    def hook_clear_command(self) -> None:
        """Clear index when files are modified (used by Claude hooks)"""
        # This is called by Claude hooks - check if any indexed files were modified
        # For now, just clear the index to be safe
        data_dir = os.path.join(self.project_root, self.config["index_dir"])

        if os.path.exists(data_dir):
            index_info_path = os.path.join(data_dir, "index_info.json")
            if os.path.exists(index_info_path):
                # Mark index as outdated instead of deleting
                with open(index_info_path, "r+") as f:
                    index_info = json.load(f)
                    index_info["outdated"] = True
                    f.seek(0)
                    json.dump(index_info, f, indent=2)
                    f.truncate()
            else:
                # No index info, remove directory
                shutil.rmtree(data_dir)

    def encoding_info_command(self) -> None:
        """Show encoding information for files that would be indexed"""
        print("Analyzing file encodings...")

        # Get files to index
        files, dirs_processed = self._get_files_for_indexing(
            show_dirs=False, show_files=False
        )
        if not files:
            print("No files found to analyze")
            return

        print(f"Analyzing {len(files)} files...")
        print()

        encoding_stats = {}
        problem_files = []
        binary_files = []

        for file_path in files:
            rel_path = os.path.relpath(file_path, self.project_root)

            try:
                with open(file_path, "rb") as f:
                    content_bytes = f.read()

                # Check if binary
                if self._is_binary_file(file_path, content_bytes):
                    binary_files.append(rel_path)
                    continue

                # Detect encoding
                detected_encoding = self._detect_encoding(file_path, content_bytes)

                # Try to read with detected encoding
                success = False
                try:
                    _ = content_bytes.decode(detected_encoding)  # Test decode
                    success = True
                except (UnicodeDecodeError, LookupError):
                    # Try fallback encodings
                    encoding_config = self.config.get("encoding", {})
                    fallback_encodings = encoding_config.get(
                        "fallback_encodings", ["utf-8"]
                    )

                    for encoding in fallback_encodings:
                        if encoding == detected_encoding:
                            continue
                        try:
                            _ = content_bytes.decode(encoding)  # Test decode
                            detected_encoding = f"{detected_encoding}->{encoding}"
                            success = True
                            break
                        except (UnicodeDecodeError, LookupError):
                            continue

                if success:
                    encoding_stats[detected_encoding] = (
                        encoding_stats.get(detected_encoding, 0) + 1
                    )
                    if detected_encoding != "utf-8":
                        print(f"  {rel_path}")
                        print(f"   Encoding: {detected_encoding}")
                        print(f"   Size: {len(content_bytes)} bytes")
                        print()
                else:
                    problem_files.append(rel_path)

            except (OSError, RuntimeError) as e:
                problem_files.append(f"{rel_path} (error: {str(e)})")

        # Show summary
        print("Encoding Summary:")
        print("=" * 40)
        for encoding, count in sorted(encoding_stats.items()):
            print(f"{encoding:20} : {count:3} files")

        if binary_files:
            print(f"\nBinary files skipped: {len(binary_files)}")
            if len(binary_files) <= 5:
                for file in binary_files:
                    print(f"   {file}")
            else:
                for file in binary_files[:3]:
                    print(f"   {file}")
                print(f"   ... and {len(binary_files) - 3} more")

        if problem_files:
            print(f"\nProblem files: {len(problem_files)}")
            for file in problem_files[:10]:
                print(f"   {file}")
            if len(problem_files) > 10:
                print(f"   ... and {len(problem_files) - 10} more")

        print(f"\nConfiguration: {self.config_path}")
        print(
            f"   Auto-detect: {self.config.get('encoding', {}).get('auto_detect', True)}"
        )
        print(
            f"   Confidence threshold: {self.config.get('encoding', {}).get('detection_confidence_threshold', 0.7)}"
        )

    def setup_command(self) -> None:
        """Setup command - now recommends using uv/uvx instead"""
        print("Setup is no longer needed with uv/uvx!")
        print()
        print("Install and run with uvx:")
        print(
            "  uvx --from git+https://github.com/orgoj/tantivi2agents tantivy2agents --help"
        )
        print()
        print("Or install locally:")
        print("  uv pip install git+https://github.com/orgoj/tantivi2agents")
        print("  tantivy2agents --help")
        print()
        print("For development:")
        print("  git clone https://github.com/orgoj/tantivi2agents")
        print("  cd tantivi2agents")
        print("  uv sync")
        print("  uv run tantivy2agents --help")

    def status_command(self) -> None:
        """Status command to display index information and statistics"""

        # Initialize variables explicitly to avoid fragile locals() checks
        index_info: dict | None = None
        indexed_files: list = []

        print("Tantivy Agent Status\n")

        # Basic project information
        print(f"Project: {self.project_root}")
        print(f"Config: {os.path.relpath(self.config_path, self.project_root)}")

        # Index directory information
        data_dir = os.path.join(self.project_root, self.config["index_dir"])
        index_path = os.path.join(data_dir, "idx")
        print(f"Index: {os.path.relpath(index_path, self.project_root)}")

        # Check if index exists
        if not os.path.exists(index_path):
            print(f"\nIndex not found at: {index_path}")
            print("   Run 'tantivy2agents index' to create the index")
            return

        print("\nIndex Statistics")

        # Load index info from JSON
        index_info_path = os.path.join(data_dir, "index_info.json")
        try:
            if os.path.exists(index_info_path):
                with open(index_info_path, "r") as f:
                    index_info = json.load(f)

                doc_count = index_info.get("count", 0)
                timestamp = index_info.get("timestamp", 0)
                last_update = datetime.fromtimestamp(timestamp).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                indexed_files = index_info.get("files", [])

                print(f"   Documents: {doc_count:,}")
                print(f"   Last update: {last_update}")
                print(f"   Files in index: {len(indexed_files):,}")
            else:
                print("   Index metadata not found")
        except (OSError, json.JSONDecodeError, KeyError) as e:
            print(f"   Error reading index metadata: {e}")

        # Calculate index size
        try:
            index_size = 0
            index_files = 0
            for root, dirs, files in os.walk(index_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    index_size += os.path.getsize(file_path)
                    index_files += 1

            index_size_mb = index_size / (1024 * 1024)
            print(f"   Index size: {index_size_mb:.1f} MB")
            print(f"   Index files: {index_files}")
        except OSError as e:
            print(f"   Error calculating index size: {e}")

        print("\nFile Information")

        # Get files to index
        files_to_index = []
        try:
            files_to_index, _ = self._get_files_for_indexing()
            print(f"   Files to index: {len(files_to_index):,}")
        except (OSError, RuntimeError, ValueError) as e:
            print(f"   Error getting files to index: {e}")

        # Check available vs missing files
        if index_info is not None and indexed_files:
            available_files = []
            missing_files = []
            for file_path in indexed_files:
                if os.path.exists(file_path):
                    available_files.append(file_path)
                else:
                    missing_files.append(file_path)

            print(f"   Files available: {len(available_files):,}")
            if missing_files:
                print(f"   Missing files: {len(missing_files):,}")

            # Get file modification times
            if files_to_index:
                try:
                    mtimes = [
                        os.path.getmtime(f) for f in files_to_index if os.path.exists(f)
                    ]
                    if mtimes:
                        latest_mtime = max(mtimes)
                        latest_file = datetime.fromtimestamp(latest_mtime).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                        print(f"   Last modified: {latest_file}")
                except (OSError, ValueError) as e:
                    print(f"   Error getting modification times: {e}")

        print("\nSystem")

        # Tantivy version
        try:
            print(f"   Tantivy version: {tantivy.__version__}")
        except AttributeError:
            # __version__ not available
            print("   Tantivy version: N/A")

        # Index status
        try:
            if index_info is not None:
                needs_rebuild = self._should_rebuild_index(data_dir)
                if needs_rebuild:
                    print("   Index status: Out of date")
                    print("   Run 'tantivy2agents index' to update")
                else:
                    print("   Index status: Up to date")
            else:
                print("   Index status: Unknown")
        except (OSError, json.JSONDecodeError) as e:
            print(f"   Index status: Error checking: {e}")

        print()  # Empty line at end
