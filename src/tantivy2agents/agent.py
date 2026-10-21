"""
Tantivy Agent - Main agent class for document indexing and search.
"""

import fnmatch
import glob
import contextlib
import hashlib
import json
import logging
import os
import shutil
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import tantivy
import yaml

from .czech_stemmer import normalize_czech_text
from .config import (
    config_example_text,
    get_default_config_for_project_type,
    load_config,
    validate_search_filters,
)
from .exceptions import (
    FileSystemError,
    IndexNotFoundError,
    ValidationError,
)
from .files import (
    ScanResult,
    collect_files_for_indexing,
    expand_index_dirs,
    is_binary_file,
    match_pattern,
    scan_candidates,
)
from .locking import LOCK_FILENAME, IndexLock
from .usage import USAGE_FILENAMES, UsageLog, new_search_id
from .paths import (
    find_project_root,
    is_inside,
    to_index_path,
    to_index_pattern,
)
from .output import (
    export_csv,
    export_json,
    export_results,
    export_text,
    extract_document_fields,
)

# Module logger
logger = logging.getLogger(__name__)

# Scratch directories used while swapping a freshly built index into place
BUILD_DIR_PREFIX = ".build-"
RETIRED_DIR_PREFIX = ".retired-"

# Windows releases file handles asynchronously, and virus scanners or the
# search indexer can hold a directory open for a moment after the last handle
# is closed, so directory swaps get a few attempts before giving up.
DIR_RETRY_ATTEMPTS = 10
DIR_RETRY_DELAY = 0.05

# Manifest published inside idx/ with the index files it describes. Bump the
# format whenever documents are built differently, to force a full rebuild.
INDEX_STATE_FILENAME = "t2a_state.json"
INDEX_STATE_FORMAT = 1
FINGERPRINT_CONFIG_KEYS = ("index_dirs", "global_patterns", "encoding", "schema_fields")
# Scan/apply rounds per refresh; a tree that keeps changing is published after
# the last round and picked up by the next search.
MAX_REFRESH_ROUNDS = 3
MAX_REPORTED_SCAN_ERRORS = 5


class DocumentReadError(Exception):
    """A candidate file could not be read; it may succeed on the next attempt."""


def _valid_manifest_entry(key, value) -> bool:
    """Manifest entry: [mtime_ns or None, size or None, indexed]."""
    return (
        isinstance(key, str)
        and isinstance(value, list)
        and len(value) == 3
        and all(v is None or (type(v) is int) for v in value[:2])
        and isinstance(value[2], bool)
    )


@dataclass
class RefreshResult:
    """Outcome of bringing the index in line with the files on disk."""

    action: str  # fresh, kept, updated or rebuilt
    count: int
    changed: int = 0


# Optional dependency for advanced encoding detection
try:
    from charset_normalizer import detect
except ImportError:
    detect = None


class TantivyAgent:
    """Main Tantivy Agent class with all functionality"""

    # Constants for encoding detection
    DEFAULT_ENCODING_CONFIDENCE_THRESHOLD = 0.7
    MIN_TEXT_CHAR_RATIO = 0.7
    PRINTABLE_ASCII_RANGE = (32, 126)  # Space to tilde
    WHITESPACE_CHARS = (9, 10, 13)  # Tab, LF, CR

    def __init__(
        self,
        config_path: Optional[str] = None,
        verbose: bool = False,
        quiet: bool = False,
    ) -> None:
        """Initialize agent with configuration.

        Args:
            config_path: Path to configuration file
            verbose: Enable debug output
            quiet: Suppress informational output
        """
        self.verbose = verbose
        self.quiet = quiet
        self._setup_logging()
        self.project_root = self._find_project_root()
        self.config_path = config_path or os.path.join(
            self.project_root, ".tantivy2agents.json"
        )
        self.config = self._load_config()
        self._lock: Optional[IndexLock] = None

    @property
    def index_lock(self) -> IndexLock:
        """Cross-process lock guarding this project's index directory."""
        if self._lock is None:
            data_dir = os.path.join(self.project_root, self.config["index_dir"])
            self._ensure_safe_index_path(data_dir)
            self._lock = IndexLock(os.path.join(data_dir, LOCK_FILENAME))
        return self._lock

    def _setup_logging(self) -> None:
        """Configure logging based on verbosity settings."""
        if self.verbose:
            level = logging.DEBUG
        elif self.quiet:
            level = logging.WARNING
        else:
            level = logging.INFO

        logging.basicConfig(
            level=level,
            format="%(levelname)s: %(message)s",
        )

    def _find_project_root(self):
        """Find project root by looking for .git directory"""
        return find_project_root(os.getcwd())

    def _load_config(self):
        """Load configuration from JSON file with defaults"""
        return load_config(self.config_path)

    def _validate_search_filters(self, config: dict) -> None:
        """Validate search filter configuration.

        Raises ValidationError for invalid configuration.
        """
        validate_search_filters(config)

    def _ensure_data_dir(self):
        """Ensure data directory exists and is in .gitignore"""
        data_dir = os.path.join(self.project_root, self.config["index_dir"])
        self._ensure_safe_index_path(data_dir)
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

    def _ensure_safe_index_path(self, path: str) -> None:
        """Reject index paths that could escape or follow symlinks."""
        abs_path = os.path.abspath(path)
        if os.path.islink(abs_path):
            raise FileSystemError(
                message="Refusing to use symlinked index directory",
                path=abs_path,
            )

        project_root = os.path.realpath(self.project_root)
        real_path = os.path.realpath(abs_path)
        # None means the paths share no root at all (different Windows drives)
        if is_inside(project_root, real_path) is not True:
            raise FileSystemError(
                message="Index directory must stay inside the project root",
                path=abs_path,
            )

    @staticmethod
    def _rename_with_retry(src: str, dst: str) -> None:
        """Rename a directory, retrying while Windows still holds it open."""
        for attempt in range(DIR_RETRY_ATTEMPTS):
            try:
                os.rename(src, dst)
                return
            except PermissionError:
                if attempt == DIR_RETRY_ATTEMPTS - 1:
                    raise
                time.sleep(DIR_RETRY_DELAY)

    @staticmethod
    def _rmtree_with_retry(path: str) -> None:
        """Remove a directory tree, retrying while Windows still holds it open."""
        for attempt in range(DIR_RETRY_ATTEMPTS):
            try:
                shutil.rmtree(path, ignore_errors=False)
                return
            except FileNotFoundError:
                return
            except PermissionError:
                if attempt == DIR_RETRY_ATTEMPTS - 1:
                    logger.warning("Could not remove %s; leaving it behind", path)
                    return
                time.sleep(DIR_RETRY_DELAY)
            except OSError as e:
                logger.warning("Could not remove %s: %s", path, e)
                return

    def _publish_index(self, build_dir: str, index_dir: str) -> None:
        """Swap a freshly built index into place with directory renames.

        Renames are atomic, so a reader either sees the whole old index or the
        whole new one - never a half-deleted directory.
        """
        self._ensure_safe_index_path(index_dir)

        retired_dir = None
        if os.path.exists(index_dir):
            retired_dir = os.path.join(
                os.path.dirname(index_dir),
                f"{RETIRED_DIR_PREFIX}{uuid.uuid4().hex}",
            )
            self._rename_with_retry(index_dir, retired_dir)

        try:
            self._rename_with_retry(build_dir, index_dir)
        except OSError:
            if retired_dir is not None:
                self._rename_with_retry(retired_dir, index_dir)
            raise

        if retired_dir is not None:
            self._rmtree_with_retry(retired_dir)

    def _cleanup_stale_index_dirs(self, data_dir: str) -> None:
        """Drop scratch directories left behind by a crashed rebuild."""
        try:
            entries = os.listdir(data_dir)
        except OSError:
            return

        for entry in entries:
            if not entry.startswith((BUILD_DIR_PREFIX, RETIRED_DIR_PREFIX)):
                continue
            path = os.path.join(data_dir, entry)
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path, ignore_errors=True)

    def _write_index_info(self, data_dir: str, index_info: dict) -> None:
        """Write index metadata atomically so readers never see a partial file."""
        self._write_json_atomic(os.path.join(data_dir, "index_info.json"), index_info)

    @staticmethod
    def _write_json_atomic(target: str, payload: dict) -> None:
        tmp_path = f"{target}.tmp-{uuid.uuid4().hex}"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            os.replace(tmp_path, target)
        except OSError:
            with contextlib.suppress(OSError):
                os.remove(tmp_path)
            raise

    def _clear_index_contents(self, data_dir: str) -> bool:
        """Remove index data while keeping the lock file others may hold."""
        if not os.path.exists(data_dir):
            return False
        self._ensure_safe_index_path(data_dir)

        removed = False
        for entry in os.listdir(data_dir):
            # The usage history outlives the index it was recorded against.
            if entry == LOCK_FILENAME or entry in USAGE_FILENAMES:
                continue
            path = os.path.join(data_dir, entry)
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            removed = True
        return removed

    def _prepare_output_file(
        self, output_file: Optional[str], allow_outside_project: bool = False
    ) -> Optional[str]:
        if not output_file:
            return None

        output_path = os.path.abspath(output_file)
        project_root = os.path.realpath(self.project_root)
        real_output_path = os.path.realpath(output_path)
        if (
            not allow_outside_project
            and is_inside(project_root, real_output_path) is not True
        ):
            raise ValidationError(
                message="Output path is outside the project root",
                parameter="output",
                expected="path inside project root or --allow-outside-output",
                got=output_file,
            )

        return output_file

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
        return get_default_config_for_project_type(project_type)

    def _expand_glob_patterns(self, pattern_list):
        """Expand glob patterns to actual directory/file paths"""
        return expand_index_dirs(pattern_list, self.project_root)

    def _get_files_for_indexing(self, show_dirs=False, show_files=False):
        """Get list of files to index based on configuration with glob pattern support"""
        return collect_files_for_indexing(
            self.config,
            self.project_root,
            show_dirs=show_dirs,
            show_files=show_files,
        )

    def _match_pattern(self, path, pattern):
        """Simple glob pattern matching"""
        return match_pattern(path, pattern)

    def _is_binary_file(self, file_path, content_bytes=None):
        """Check if file is binary based on extension and content"""
        return is_binary_file(file_path, content_bytes, self.config.get("encoding", {}))

    def _get_encoding_for_file(self, file_path):
        """Get configured encoding for a specific file based on patterns"""
        encoding_config = self.config.get("encoding", {})
        file_specific = encoding_config.get("file_specific_encodings", {})
        filename = os.path.basename(file_path)
        rel_path = to_index_path(os.path.relpath(file_path, self.project_root))

        # Check file-specific patterns (try both relative path and filename)
        # Sort patterns by length (longer/more specific patterns first)
        sorted_patterns = sorted(
            file_specific.items(), key=lambda x: len(x[0]), reverse=True
        )
        for pattern, encoding in sorted_patterns:
            pattern = to_index_pattern(pattern)
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

                threshold = encoding_config.get(
                    "detection_confidence_threshold",
                    self.DEFAULT_ENCODING_CONFIDENCE_THRESHOLD,
                )
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
        """Parse markdown file and extract metadata; None if binary or unreadable."""
        try:
            return self._load_document(file_path)
        except DocumentReadError as e:
            logger.warning("Error reading %s: %s", file_path, e)
            return None

    def _load_document(self, file_path):
        """Build the index document for a file.

        Returns None for a binary file, which is a stable property of its
        content. Raises DocumentReadError when the file could not be read, which
        may be temporary, so the caller can keep the previous document.
        """
        import re

        try:
            content, encoding_info = self._read_file_with_encoding_detection(file_path)
        except OSError as e:
            raise DocumentReadError(str(e)) from e

        if content is None:
            if encoding_info == "binary":
                return None
            raise DocumentReadError(encoding_info)

        # Log encoding detection for debugging (only if not UTF-8)
        if encoding_info != "utf-8":
            logger.debug(
                "%s: detected encoding %s",
                os.path.relpath(file_path, self.project_root),
                encoding_info,
            )

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

        # Auto-generate metadata for server files. The path is normalized to
        # forward slashes so patterns and filters behave the same on Windows.
        rel_path = to_index_path(os.path.relpath(file_path, self.project_root))
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

        # Extract description from frontmatter
        # Kept raw for display; queries are normalized, so a normalized copy is
        # appended to the body field to make Czech description terms searchable.
        description = meta.get("description", "") or ""
        if description:
            body_normalized = normalize_czech_text(description) + "\n" + body_normalized

        return {
            "title": title_normalized,
            "description": description,
            "body": body_normalized,
            "snippet": body,
            "tags": " ".join(str(t) for t in meta.get("tags", []))
            if isinstance(meta.get("tags"), list)
            else str(meta.get("tags", "") or ""),
            "servers": " ".join(str(s) for s in meta.get("servers", []))
            if isinstance(meta.get("servers"), list)
            else str(meta.get("servers", "") or ""),
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

        if "snippet" not in self.config["schema_fields"]:
            schema_builder.add_text_field(
                "snippet",
                stored=True,
                tokenizer_name="default",
            )

        return schema_builder.build()

    def _config_fingerprint(self) -> str:
        """Hash of every setting that changes which documents the index holds."""
        relevant = {key: self.config.get(key) for key in FINGERPRINT_CONFIG_KEYS}
        relevant["format"] = INDEX_STATE_FORMAT
        encoded = json.dumps(relevant, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _incremental_allowed(self) -> bool:
        """Deleting a document by path needs the path stored as one raw term."""
        path_field = self.config["schema_fields"].get("path") or {}
        return path_field.get("tokenizer") == "raw"

    def _read_index_state(self, index_dir: str) -> Optional[dict]:
        """Return the manifest published with the index, or None when unusable."""
        try:
            with open(
                os.path.join(index_dir, INDEX_STATE_FILENAME), "r", encoding="utf-8"
            ) as f:
                state = json.load(f)
        except (OSError, json.JSONDecodeError):
            return None
        if (
            not isinstance(state, dict)
            or state.get("format") != INDEX_STATE_FORMAT
            or state.get("config_fingerprint") != self._config_fingerprint()
            or not isinstance(state.get("manifest"), dict)
            or not all(
                _valid_manifest_entry(key, value)
                for key, value in state["manifest"].items()
            )
        ):
            return None
        return state

    @staticmethod
    def _diff_manifest(manifest: dict, entries: dict) -> tuple[list[str], list[str]]:
        """Return (removed, added or changed) index paths."""
        removed = [key for key in manifest if key not in entries]
        refresh = [
            key
            for key, (_path, mtime_ns, size) in entries.items()
            if key not in manifest
            or manifest[key][0] != mtime_ns
            or manifest[key][1] != size
        ]
        return removed, refresh

    def _index_is_current(self, index_dir: str) -> Optional[bool]:
        """Read-only check: the published manifest matches the files on disk.

        Returns None when the files could not all be scanned.
        """
        if not os.path.exists(index_dir) or not self._index_can_open(index_dir):
            return False
        state = self._read_index_state(index_dir)
        if state is None:
            return False
        scan = scan_candidates(self.config, self.project_root)
        if not scan.complete:
            return None
        removed, refresh = self._diff_manifest(state["manifest"], scan.entries)
        return not removed and not refresh

    def _recover_retired_index(self, data_dir: str, index_dir: str) -> None:
        """Put back the last good index if a publish died between its renames.

        Publishing moves idx/ aside before moving the new build in; a crash in
        between leaves only the retired copy, which cleanup would delete.
        """
        if os.path.exists(index_dir):
            return
        try:
            entries = os.listdir(data_dir)
        except OSError:
            return
        retired = [
            os.path.join(data_dir, entry)
            for entry in entries
            if entry.startswith(RETIRED_DIR_PREFIX)
        ]
        # Only a real directory published by this tool qualifies: a symlink
        # could point the live index outside the project.
        retired = [
            path
            for path in retired
            if os.path.isdir(path)
            and not os.path.islink(path)
            and os.path.dirname(os.path.realpath(path)) == os.path.realpath(data_dir)
        ]
        retired.sort(key=os.path.getmtime, reverse=True)
        for path in retired:
            # Its manifest may be missing or stale (older version, changed
            # config); the normal check then rebuilds beside it, so a failed
            # rebuild still leaves this index searchable.
            if self._index_can_open(path):
                self._rename_with_retry(path, index_dir)
                logger.warning("Recovered the previous index after an interruption")
                return

    def _refresh_index_locked(
        self, data_dir: str, index_dir: str, force: bool = False
    ) -> RefreshResult:
        """Bring the index in line with the files on disk.

        Must be called while holding the write lock. Unchanged files cost one
        stat each; changed files are re-indexed into a copy of the live index
        when possible and the whole index is rebuilt otherwise.
        """
        self._recover_retired_index(data_dir, index_dir)
        self._cleanup_stale_index_dirs(data_dir)
        scan = scan_candidates(self.config, self.project_root)

        index_usable = os.path.exists(index_dir) and self._index_can_open(index_dir)
        state = self._read_index_state(index_dir) if index_usable else None

        if not scan.complete:
            for error in scan.errors[:MAX_REPORTED_SCAN_ERRORS]:
                logger.warning("Cannot scan %s", error)
            if index_usable:
                # A file missing from an incomplete scan may only be unreadable
                # for a moment; deleting its document would lose search hits.
                logger.warning("Index not refreshed: file scan incomplete")
                return RefreshResult("kept", self._indexed_count(data_dir))

        if state is not None and not force:
            removed, refresh = self._diff_manifest(state["manifest"], scan.entries)
            if not removed and not refresh:
                count = self._repair_index_info(data_dir, state["manifest"], scan)
                return RefreshResult("fresh", count)
            if self._incremental_allowed():
                return self._build_and_publish(data_dir, index_dir, scan, state)

        return self._build_and_publish(data_dir, index_dir, scan, None)

    @staticmethod
    def _report_skipped(scan: ScanResult) -> None:
        for path in scan.skipped[:MAX_REPORTED_SCAN_ERRORS]:
            logger.warning("Skipped (permission denied): %s", path)
        if len(scan.skipped) > MAX_REPORTED_SCAN_ERRORS:
            logger.warning(
                "Skipped %d more unreadable paths",
                len(scan.skipped) - MAX_REPORTED_SCAN_ERRORS,
            )

    def _build_and_publish(
        self,
        data_dir: str,
        index_dir: str,
        scan: ScanResult,
        state: Optional[dict],
    ) -> RefreshResult:
        """Build beside the live index, then swap it in with one rename.

        ``state`` None means a full build into an empty index; otherwise the
        live index is copied and only the changed paths are rewritten. The
        manifest is written into the build directory, so it is published
        together with the index files it describes.
        """
        self._ensure_data_dir()
        build_dir = os.path.join(data_dir, f"{BUILD_DIR_PREFIX}{uuid.uuid4().hex}")
        incremental = state is not None
        try:
            if incremental:
                shutil.copytree(index_dir, build_dir)
                manifest = dict(state["manifest"])
                removed, refresh = self._diff_manifest(manifest, scan.entries)
            else:
                os.makedirs(build_dir)
                tantivy.Index(self._create_schema(), path=build_dir)
                manifest = {}
                removed, refresh = [], list(scan.entries)

            # A rescan after each round catches files edited during the build,
            # so the search that triggered the refresh already sees them.
            # Without raw paths a repeated round could duplicate documents.
            rounds = MAX_REFRESH_ROUNDS if self._incremental_allowed() else 1
            changed = 0
            for round_number in range(1, rounds + 1):
                self._apply_changes(build_dir, scan, manifest, removed, refresh)
                changed += len(removed) + len(refresh)
                if round_number == rounds:
                    break
                rescan = scan_candidates(self.config, self.project_root)
                if not rescan.complete:
                    break
                removed, refresh = self._diff_manifest(manifest, rescan.entries)
                if not removed and not refresh:
                    # Same entries; keep its skipped paths for the report.
                    scan = rescan
                    break
                scan = rescan

            count = self._count_documents(build_dir)
            self._write_json_atomic(
                os.path.join(build_dir, INDEX_STATE_FILENAME),
                {
                    "format": INDEX_STATE_FORMAT,
                    "config_fingerprint": self._config_fingerprint(),
                    "manifest": manifest,
                },
            )
            self._publish_index(build_dir, index_dir)
            # Reported from the scan that was published, only when the index
            # changes, and before anything after the publish can fail.
            self._report_skipped(scan)
        finally:
            shutil.rmtree(build_dir, ignore_errors=True)

        self._write_index_info(
            data_dir,
            {
                "timestamp": time.time(),
                "files": self._indexed_files(manifest, scan),
                "count": count,
            },
        )
        return RefreshResult("updated" if incremental else "rebuilt", count, changed)

    def _indexed_files(self, manifest: dict, scan: ScanResult) -> list[str]:
        """Absolute paths of indexed documents, as 0.9.0 stored them."""
        return [
            scan.entries[key][0]
            if key in scan.entries
            else os.path.normpath(os.path.join(self.project_root, key))
            for key, (_mtime, _size, indexed) in manifest.items()
            if indexed
        ]

    def _repair_index_info(
        self, data_dir: str, manifest: dict, scan: ScanResult
    ) -> int:
        """Rewrite index_info.json when it does not describe the live index.

        It is written after the publish, so a crash in between leaves it
        missing or stale. A current file is left alone; the hook's
        ``outdated`` mark is dropped because the check just ran.
        """
        files = self._indexed_files(manifest, scan)
        info = self._read_index_info(data_dir)
        if (
            info is not None
            and "outdated" not in info
            and isinstance(info.get("timestamp"), (int, float))
            and info.get("count") == len(files)
            and info.get("files") == files
        ):
            return len(files)
        self._write_index_info(
            data_dir, {"timestamp": time.time(), "files": files, "count": len(files)}
        )
        return len(files)

    def _apply_changes(
        self,
        build_dir: str,
        scan: ScanResult,
        manifest: dict,
        removed: list[str],
        refresh: list[str],
    ) -> None:
        """Delete and re-add documents in ``build_dir``; update ``manifest``.

        Every refreshed path is deleted first, added ones included, so replaying
        a round never leaves a document twice. A file that cannot be read keeps
        its previous document and an entry that never matches a scan, so it is
        retried on the next refresh instead of being dropped. Tantivy handles
        stay inside this method: Windows cannot rename a directory that still
        has open files.
        """
        index = tantivy.Index.open(build_dir)
        writer = index.writer()
        try:
            for key in removed:
                writer.delete_documents_by_term("path", key)
                manifest.pop(key, None)
            for key in refresh:
                file_path, mtime_ns, size = scan.entries[key]
                try:
                    doc = self._load_document(file_path)
                except DocumentReadError as e:
                    logger.warning("Cannot read %s, will retry: %s", file_path, e)
                    was_indexed = manifest.get(key, [None, None, False])[2]
                    manifest[key] = [None, None, was_indexed]
                    continue
                writer.delete_documents_by_term("path", key)
                if doc:
                    writer.add_document(tantivy.Document(**doc))
                # The stat was taken before the read, so an edit racing this
                # read shows up as a difference on the next scan.
                manifest[key] = [mtime_ns, size, doc is not None]
            writer.commit()
            writer.wait_merging_threads()
        except Exception as e:
            logger.error("Failed to write index: %s", e)
            raise RuntimeError(f"Index write failed: {e}") from e
        finally:
            del writer
            del index

    @staticmethod
    def _count_documents(index_dir: str) -> int:
        index = tantivy.Index.open(index_dir)
        try:
            return index.searcher().num_docs
        finally:
            del index

    def _indexed_count(self, data_dir: str) -> int:
        index_info = self._read_index_info(data_dir) or {}
        return int(index_info.get("count", 0) or 0)

    def _read_index_info(self, data_dir: str) -> Optional[dict]:
        try:
            with open(
                os.path.join(data_dir, "index_info.json"), "r", encoding="utf-8"
            ) as f:
                index_info = json.load(f)
        except (OSError, json.JSONDecodeError):
            return None
        return index_info if isinstance(index_info, dict) else None

    def index_command(
        self, force: bool = False, show_dirs: bool = False, show_files: bool = False
    ) -> None:
        """Create or update document index.

        The whole rebuild runs under the exclusive index lock so that parallel
        index/search processes wait instead of deleting each other's files.
        """
        with self.index_lock.acquire():
            self._index_locked(force, show_dirs, show_files)

    def _index_locked(self, force: bool, show_dirs: bool, show_files: bool) -> None:
        """Refresh the index. Must be called while holding the write lock."""
        print("Starting document indexing...")

        data_dir = self._ensure_data_dir()
        index_dir = os.path.join(data_dir, "idx")

        if show_dirs or show_files:
            self._get_files_for_indexing(show_dirs, show_files)

        result = self._refresh_index_locked(data_dir, index_dir, force=force)

        if result.action == "fresh":
            print("Index is up to date")
            return
        if result.action == "kept":
            print("Index kept: the file scan was incomplete")
            return
        if result.count == 0:
            print("No documents found to index; published an empty index")
            return
        if result.action == "updated":
            print(f"Updated {result.changed} changed files")
        print(f"Successfully indexed {result.count} documents")
        print(f"Index saved to: {index_dir}")
        print("You can now search with: tantivy2agents search 'your query'")

    def search_command(
        self,
        query: str,
        limit: Optional[int] = None,
        format_output: Optional[str] = None,
        output_file: Optional[str] = None,
        allow_outside_output: bool = False,
        show_snippets: bool = False,
    ) -> None:
        """Search in indexed documents"""
        if not query:
            raise ValidationError(
                message="Search query cannot be empty",
                parameter="query",
                got="(empty)",
            )
        output_file = self._prepare_output_file(output_file, allow_outside_output)

        data_dir = os.path.join(self.project_root, self.config["index_dir"])
        index_dir = os.path.join(data_dir, "idx")

        limit = limit or self.config["search"]["default_limit"]

        # One lock transaction covers the refresh and the query, so a
        # concurrent clear or rebuild cannot slip in between them. Every
        # tantivy handle is confined to the helpers and dies before the lock
        # is released: Windows refuses to rename or delete a directory that
        # any process still holds open.
        with self.index_lock.acquire():
            self._ensure_search_index(data_dir, index_dir)
            try:
                had_hits, unique_results = self._collect_search_results(
                    index_dir, query, limit
                )
            except (OSError, ValueError, RuntimeError) as e:
                raise IndexNotFoundError(index_dir=index_dir) from e

        shown = unique_results[:limit]
        search_id = self._log_search(query, limit, shown)

        if not had_hits:
            print("No results found")
            return

        if not unique_results:
            print("No results found after filtering")
            return

        # Export results in requested format (default: json)
        self._export_results(
            shown,
            query,
            format_output or "json",
            output_file,
            show_snippets=show_snippets,
            search_id=search_id,
        )

    def _log_search(self, query: str, limit: int, shown) -> Optional[str]:
        """Record the search in the usage log; return its id, or None."""
        usage = UsageLog(
            os.path.join(self.project_root, self.config["index_dir"]), self.config
        )
        if not usage.enabled:
            return None
        search_id = new_search_id()
        results = [
            {
                "rank": rank,
                "path": doc["path"][0] if doc["path"] else "",
                "score": round(score, 4),
            }
            for rank, (score, _address, doc) in enumerate(shown, start=1)
        ]
        record = {
            "type": "search",
            "id": search_id,
            "query": query,
            "limit": limit,
            "results": results,
        }
        return search_id if usage.append(record) else None

    def _collect_search_results(self, index_dir: str, query: str, limit: int):
        """Run the query and return (had_hits, filtered results).

        All tantivy objects stay local to this call so they are released as
        soon as it returns, while the caller still holds the index lock.
        """
        index = tantivy.Index.open(index_dir)
        searcher = index.searcher()

        # Normalize query for Czech search
        normalized_query = normalize_czech_text(query)

        # Parse query - use None to search all fields in index schema (backward compatibility)
        # This ensures search works even when config has more fields than old index
        query_parser = index.parse_query(normalized_query, None)

        # Search
        search_limit = self._candidate_limit(limit)
        result = searcher.search(query_parser, search_limit)

        if not result.hits:
            return False, []

        # Process results
        results_with_docs = []
        for score, doc_address in result.hits:
            doc = searcher.doc(doc_address)
            results_with_docs.append((score, doc_address, doc))

        # Apply filters
        filtered_results = self._apply_filters(results_with_docs, query)
        return True, self._deduplicate_results_by_path(filtered_results)

    def _ensure_search_index(self, data_dir: str, index_dir: str) -> None:
        """Refresh the index from the files on disk before every search.

        No hook is needed: the check stats every candidate file under the
        write lock, so when several searches race only the first one rebuilds
        and the others find the index it published already current.
        """
        with self.index_lock.acquire():
            self._refresh_index_locked(data_dir, index_dir)

        if not os.path.exists(index_dir):
            raise IndexNotFoundError(index_dir=index_dir)

    def _index_can_open(self, index_dir: str) -> bool:
        """Return True when an existing index directory can be opened."""
        try:
            tantivy.Index.open(index_dir)
            return True
        except (OSError, ValueError, RuntimeError):
            return False

    def _candidate_limit(self, limit: int) -> int:
        """Return enough candidates for path filters without expensive paging."""
        return min(max(limit * 20, 100), 10000)

    def _deduplicate_results_by_path(self, results):
        """Keep only the best-ranked hit for each indexed file path."""
        seen_paths = set()
        unique_results = []

        for score, doc_address, doc in results:
            file_path = doc["path"][0] if doc["path"] else ""
            if not file_path:
                unique_results.append((score, doc_address, doc))
                continue
            if file_path in seen_paths:
                continue
            seen_paths.add(file_path)
            unique_results.append((score, doc_address, doc))

        return unique_results

    def _export_results(
        self,
        results,
        query,
        format_output,
        output_file,
        show_snippets: bool = False,
        search_id: Optional[str] = None,
    ):
        """Export results in specified format"""
        export_results(
            results,
            query,
            format_output,
            output_file,
            self.config,
            show_snippets=show_snippets,
            search_id=search_id,
        )

    def _export_json(self, results, query, output_file):
        """Export results as JSON"""
        export_json(results, query, output_file, self.config)

    def _export_csv(self, results, query, output_file):
        """Export results as CSV"""
        export_csv(results, query, output_file, self.config)

    def _export_text(self, results, query, output_file):
        """Export results as structured text for easy parsing"""
        export_text(results, query, output_file, self.config)

    def _extract_document_fields(
        self, doc, include_description: bool = True
    ) -> dict[str, str]:
        """Extract display fields from a Tantivy document.

        Single source of truth for document field extraction in search results.
        Extracts only display fields (path, title, description, tags, servers),
        NOT search fields (body) which are used only for indexing.
        Handles backward compatibility for optional fields.

        Note: Tantivy doc[key] returns [] for missing fields, not KeyError.

        Args:
            doc: Tantivy document object
            include_description: Whether to include description field

        Returns:
            Dict with normalized field values (always strings, never None)
        """
        return extract_document_fields(doc, include_description=include_description)

    def _get_search_filters(self) -> list:
        """Get search filters from configuration.

        Returns list of filter dicts with keys: name, paths, hidden, show_on_keywords.
        Keywords are pre-lowercased for efficient matching.
        """
        search_config = self.config.get("search", {})
        filters = search_config.get("filters", [])

        # Pre-lowercase keywords for efficient matching
        for f in filters:
            if "show_on_keywords" in f:
                f["_keywords_lower"] = [kw.lower() for kw in f["show_on_keywords"]]

        return filters

    def _should_include_result(
        self, file_path: str, query_words: set, filters: list
    ) -> bool:
        """Check if result should be included based on filters.

        Returns True if result should be shown, False if filtered out.

        Logic:
        1. For each filter with hidden=true:
           a. Check if file_path starts with any of the filter's paths
           b. If matches and query contains NO keyword -> hide
           c. If matches and query contains keyword -> show
        2. If no filter matches -> show
        """
        for filter_config in filters:
            if not filter_config.get("hidden", True):
                continue  # Filter not active

            # Check if file matches any filter path. Indexed paths always use
            # forward slashes, so the configured prefix is normalized to match
            # even when it was written Windows-style as "incidents\".
            paths = filter_config.get("paths", [])
            matches_filter = any(
                file_path.startswith(to_index_pattern(path)) for path in paths
            )

            if matches_filter:
                # Check if query contains any show keyword (pre-lowercased)
                keywords_lower = filter_config.get("_keywords_lower", [])
                if not keywords_lower:
                    # No keywords defined = always hidden
                    return False
                if not any(kw in query_words for kw in keywords_lower):
                    return False  # Filter applies, hide result

        return True  # No filter matched or keyword found

    def _apply_filters(self, results, query):
        """Apply path-based filters to search results.

        Filters hide documents from specific paths unless query contains
        specified keywords. Configured via search.filters in config.
        """
        filters = self._get_search_filters()

        if not filters:
            return results  # No filters configured

        query_words = set(query.lower().split())
        filtered = []

        for score, doc_address, doc in results:
            file_path = doc["path"][0] if doc["path"] else ""
            if not file_path:
                continue  # Skip documents without path

            if self._should_include_result(file_path, query_words, filters):
                filtered.append((score, doc_address, doc))

        return filtered

    def clear_command(self) -> None:
        """Clear the index"""
        print("Clearing index...")

        data_dir = os.path.join(self.project_root, self.config["index_dir"])

        with self.index_lock.acquire():
            if self._clear_index_contents(data_dir):
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
        config_path = os.path.join(target_project_root, ".tantivy2agents.json")

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
        self._ensure_safe_index_path(data_dir)

        if not os.path.exists(data_dir):
            return

        with self.index_lock.acquire():
            index_info_path = os.path.join(data_dir, "index_info.json")
            if os.path.exists(index_info_path):
                # Mark index as outdated instead of deleting
                with open(index_info_path, "r", encoding="utf-8") as f:
                    index_info = json.load(f)
                index_info["outdated"] = True
                self._write_index_info(data_dir, index_info)
            else:
                # No index info, drop the index data
                self._clear_index_contents(data_dir)

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
            "  uvx --from git+https://github.com/orgoj/tantivy2agents tantivy2agents --help"
        )
        print()
        print("Or install locally:")
        print("  uv pip install git+https://github.com/orgoj/tantivy2agents")
        print("  tantivy2agents --help")
        print()
        print("For development:")
        print("  git clone https://github.com/orgoj/tantivy2agents")
        print("  cd tantivy2agents")
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
                with open(index_info_path, "r", encoding="utf-8") as f:
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
                with self.index_lock.acquire():
                    current = self._index_is_current(index_path)
                if current is None:
                    print("   Index status: Unknown (some files could not be scanned)")
                elif not current:
                    print("   Index status: Out of date")
                    print(
                        "   The next search updates it, or run 'tantivy2agents index'"
                    )
                else:
                    print("   Index status: Up to date")
            else:
                print("   Index status: Unknown")
        except (OSError, json.JSONDecodeError) as e:
            print(f"   Index status: Error checking: {e}")

        print()  # Empty line at end

    def config_example_command(self) -> None:
        """Print example configuration with explanations"""
        print(config_example_text())

    def _find_skill_file(self, skill_name: str) -> str:
        """Find skill file path.

        Uses packaged skills from src/tantivy2agents/skills/{skill_name}/SKILL.md.

        Args:
            skill_name: Name of the skill (e.g., "tantivy2agents-usage")

        Returns:
            Path to skill file

        Raises:
            FileSystemError: If skill file cannot be found
        """
        this_file_dir = os.path.dirname(os.path.abspath(__file__))
        package_skill_path = os.path.join(
            this_file_dir, "skills", skill_name, "SKILL.md"
        )
        if os.path.exists(package_skill_path):
            return package_skill_path

        raise FileSystemError(
            message=f"Skill file not found: {skill_name}",
            path=package_skill_path,
        )

    def skill_usage_command(
        self, output_file: Optional[str] = None, allow_outside_output: bool = False
    ) -> None:
        """Output usage skill content in markdown format.

        Args:
            output_file: Optional path to save output
        """
        try:
            skill_path = self._find_skill_file("tantivy2agents-usage")
            with open(skill_path, "r", encoding="utf-8") as f:
                content = f.read()

            output_file = self._prepare_output_file(output_file, allow_outside_output)
            if output_file:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(content)
                if not self.quiet:
                    print(f"✓ Usage skill written to: {output_file}")
            else:
                print(content)
        except OSError as e:
            raise FileSystemError(
                message=f"Error reading skill file: {e}", path=skill_path
            ) from e

    def skill_setup_command(
        self, output_file: Optional[str] = None, allow_outside_output: bool = False
    ) -> None:
        """Output setup skill content in markdown format.

        Args:
            output_file: Optional path to save output
        """
        try:
            skill_path = self._find_skill_file("tantivy2agents-setup")
            with open(skill_path, "r", encoding="utf-8") as f:
                content = f.read()

            output_file = self._prepare_output_file(output_file, allow_outside_output)
            if output_file:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(content)
                if not self.quiet:
                    print(f"✓ Setup skill written to: {output_file}")
            else:
                print(content)
        except OSError as e:
            raise FileSystemError(
                message=f"Error reading skill file: {e}", path=skill_path
            ) from e
