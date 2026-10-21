"""File discovery and path filtering for indexing."""

from __future__ import annotations

import fnmatch
import glob
import os
import re
import stat
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator

from .paths import is_inside, to_index_path, to_index_pattern

MIN_TEXT_CHAR_RATIO = 0.7
PRINTABLE_ASCII_RANGE = (32, 126)
WHITESPACE_CHARS = (9, 10, 13)


def match_pattern(path: str, pattern: str) -> bool:
    """Match a path against a glob pattern."""
    normalized_path = to_index_path(path)
    # Patterns come from configuration, where a person may have typed either
    # separator, so both are accepted on the pattern side.
    normalized_pattern = to_index_pattern(pattern)

    if fnmatch.fnmatch(normalized_path, normalized_pattern):
        return True

    if "/" not in normalized_pattern:
        return fnmatch.fnmatch(os.path.basename(normalized_path), normalized_pattern)

    return False


class PatternSet:
    """Match paths against many glob patterns with ``match_pattern`` semantics.

    The patterns are compiled into two regular expressions once, so a large
    tree costs two regex matches per file instead of one or two ``fnmatch``
    calls per pattern.
    """

    def __init__(self, patterns: list[str]) -> None:
        normalized = [to_index_pattern(pattern) for pattern in patterns]
        self._full = _compile_patterns(normalized)
        self._base = _compile_patterns([p for p in normalized if "/" not in p])

    def matches(self, path: str) -> bool:
        normalized_path = to_index_path(path)
        if self._full and self._full.match(os.path.normcase(normalized_path)):
            return True
        basename = os.path.basename(normalized_path)
        return bool(self._base and self._base.match(os.path.normcase(basename)))


def _compile_patterns(patterns: list[str]) -> re.Pattern[str] | None:
    # fnmatch.fnmatch normalizes the case of both sides the same way.
    if not patterns:
        return None
    return re.compile(
        "|".join(fnmatch.translate(os.path.normcase(p)) for p in patterns)
    )


def expand_index_dirs(
    pattern_list: list[Any],
    project_root: str,
    onerror: Callable[[OSError], None] | None = None,
) -> list[dict[str, Any]]:
    """Expand configured index directory/file patterns to concrete paths.

    ``glob`` reports an unreadable path as no match. With ``onerror``, the
    included entries are probed first and access errors other than a missing
    path are passed to it, so a caller can tell "gone" from "unreadable".
    """
    expanded_paths = []

    for item in pattern_list:
        if onerror is not None:
            if isinstance(item, str):
                _probe_pattern(project_root, item, onerror)
            elif isinstance(item, dict) and not item.get("exclude", False):
                _probe_pattern(project_root, item.get("path", ""), onerror)

        if isinstance(item, str):
            if "**" in item:
                matches = glob.glob(os.path.join(project_root, item), recursive=True)
            else:
                matches = glob.glob(os.path.join(project_root, item))

            for match in matches:
                if os.path.exists(match):
                    rel_path = os.path.relpath(match, project_root)
                    expanded_paths.append(
                        {
                            "path": rel_path,
                            "type": "dir" if os.path.isdir(match) else "file",
                        }
                    )

        elif isinstance(item, dict):
            path_pattern = item.get("path", "")
            exclude = item.get("exclude", False)

            if "**" in path_pattern:
                matches = glob.glob(
                    os.path.join(project_root, path_pattern), recursive=True
                )
            else:
                matches = glob.glob(os.path.join(project_root, path_pattern))

            for match in matches:
                if os.path.exists(match):
                    rel_path = os.path.relpath(match, project_root)
                    expanded_paths.append(
                        {
                            "path": rel_path,
                            "exclude": exclude,
                            "type": "dir" if os.path.isdir(match) else "file",
                        }
                    )

    return expanded_paths


def _probe_pattern(
    project_root: str, pattern: str, onerror: Callable[[OSError], None]
) -> None:
    """Report access errors on every path that glob would read for a pattern.

    The literal prefix is stat'ed. From there each component is followed the
    way glob does: a wildcard component lists its directories, a literal one
    stats its path, and every match is stat'ed. A recursive ``**`` pattern
    walks the whole subtree below the prefix instead.
    """

    def report(error: OSError) -> None:
        if not isinstance(error, FileNotFoundError):
            onerror(error)

    parts = [p for p in to_index_pattern(pattern).split("/") if p]
    static_parts = []
    for part in parts:
        if glob.has_magic(part):
            break
        static_parts.append(part)
    static_path = os.path.join(project_root, *static_parts)

    try:
        os.stat(static_path)
    except OSError as e:
        report(e)
        return
    if len(static_parts) == len(parts):
        return
    if "**" in pattern:
        for _entry in os.walk(static_path, onerror=report):
            pass
        return

    current = [static_path]
    remaining = parts[len(static_parts) :]
    for index, part in enumerate(remaining):
        last = index == len(remaining) - 1
        matches = []
        for directory in current:
            if not glob.has_magic(part):
                matches.append(os.path.join(directory, part))
                continue
            try:
                with os.scandir(directory) as entries:
                    names = [entry.name for entry in entries]
            except OSError as e:
                report(e)
                continue
            # glob skips hidden names unless the pattern itself starts with "."
            matches.extend(
                os.path.join(directory, name)
                for name in names
                if fnmatch.fnmatch(name, part)
                and (part.startswith(".") or not name.startswith("."))
            )
        current = []
        for path in matches:
            try:
                st = os.stat(path)
            except OSError as e:
                report(e)
                continue
            if not last and stat.S_ISDIR(st.st_mode):
                current.append(path)


def is_binary_file(
    file_path: str,
    content_bytes: bytes | None = None,
    encoding_config: dict | None = None,
) -> bool:
    """Check if a file is binary based on extension and content."""
    encoding_config = encoding_config or {}
    binary_extensions = encoding_config.get("binary_extensions", [])
    filename = os.path.basename(file_path)

    for ext in binary_extensions:
        if fnmatch.fnmatch(filename.lower(), ext.lower()):
            return True

    if content_bytes:
        if b"\x00" in content_bytes:
            return True

        try:
            content_bytes.decode("utf-8")
            return False
        except UnicodeDecodeError:
            min_ascii, max_ascii = PRINTABLE_ASCII_RANGE
            text_chars = len(
                [
                    b
                    for b in content_bytes
                    if min_ascii <= b <= max_ascii or b in WHITESPACE_CHARS
                ]
            )
            if (
                len(content_bytes) > 0
                and text_chars / len(content_bytes) < MIN_TEXT_CHAR_RATIO
            ):
                return True

    return False


@dataclass
class ScanResult:
    """Candidate files found by a stat-only walk.

    ``entries`` maps the index path (the stored ``path`` field) to the
    absolute path, ``st_mtime_ns`` and ``st_size``. ``errors`` lists what could
    not be walked or stat'ed; a scan with errors must not be used to delete
    documents, because a missing entry may just be unreadable for a moment.
    ``skipped`` lists paths denied by permissions: they are treated as
    excluded, so one foreign-owned directory does not freeze the index.
    """

    entries: dict[str, tuple[str, int, int]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return not self.errors


def scan_candidates(config: dict[str, Any], project_root: str) -> ScanResult:
    """Stat every file ``collect_files_for_indexing`` would consider.

    Files are not read, so binary and unreadable candidates are included.
    """
    result = ScanResult()

    def on_walk_error(error: OSError) -> None:
        # A directory removed while walking is a normal removal.
        if isinstance(error, PermissionError):
            result.skipped.append(str(error.filename))
        elif not isinstance(error, FileNotFoundError):
            result.errors.append(f"{error.filename}: {error.strerror}")

    for file_path in _iter_candidates(config, project_root, onerror=on_walk_error):
        try:
            st = os.stat(file_path)
        except FileNotFoundError:
            continue
        except OSError as e:
            e.filename = file_path
            on_walk_error(e)
            continue
        key = to_index_path(os.path.relpath(file_path, project_root))
        result.entries[key] = (file_path, st.st_mtime_ns, st.st_size)
    return result


def collect_files_for_indexing(
    config: dict[str, Any],
    project_root: str,
    show_dirs: bool = False,
    show_files: bool = False,
) -> tuple[list[str], list[str]]:
    """Collect files to index based on configuration."""
    files = []
    dirs_processed: list[str] = []
    encoding_config = config.get("encoding", {})

    for file_path in _iter_candidates(
        config, project_root, dirs_processed if show_dirs else None
    ):
        if is_text_file(file_path, encoding_config):
            files.append(file_path)
            if show_files:
                print(f"  {os.path.relpath(file_path, project_root)}")

    unique_dirs = _unique(dirs_processed)

    if show_dirs:
        print("Directories to be processed:")
        for dir_path in unique_dirs:
            rel_dir = os.path.relpath(dir_path, project_root)
            print(f"  {rel_dir}")

    return files, unique_dirs


def is_text_file(file_path: str, encoding_config: dict[str, Any]) -> bool:
    """Return whether a candidate can be read and is not binary."""
    try:
        with open(file_path, "rb") as f:
            content_bytes = f.read()
    except OSError:
        return False
    return not is_binary_file(file_path, content_bytes, encoding_config)


def _iter_candidates(
    config: dict[str, Any],
    project_root: str,
    dirs_processed: list[str] | None = None,
    onerror: Callable[[OSError], None] | None = None,
) -> Iterator[str]:
    """Yield each file matching the configured dirs and patterns once, in order."""
    expanded_dirs = expand_index_dirs(config["index_dirs"], project_root, onerror)

    excluded_dir_names = set()
    for dir_config in expanded_dirs:
        if dir_config.get("exclude", False):
            dir_path = dir_config["path"]
            excluded_dir_names.add(os.path.basename(dir_path.rstrip("/\\")))

    include_patterns = PatternSet(config["global_patterns"]["include"])
    exclude_patterns = PatternSet(config["global_patterns"]["exclude"])
    seen: set[str] = set()
    walked_roots: list[str] = []

    def accept(file_path: str) -> bool:
        if file_path in seen:
            return False
        rel_path = os.path.relpath(file_path, project_root)
        if not include_patterns.matches(rel_path) or exclude_patterns.matches(rel_path):
            return False
        seen.add(file_path)
        return True

    for dir_config in expanded_dirs:
        if dir_config.get("exclude", False):
            continue

        dir_path = dir_config["path"]

        full_dir_path = os.path.normpath(os.path.join(project_root, dir_path))
        try:
            os.stat(full_dir_path)
        except FileNotFoundError:
            continue
        except OSError as e:
            if onerror is not None:
                onerror(e)
            continue

        if dirs_processed is not None:
            dirs_processed.append(full_dir_path)

        if dir_config.get("type") == "file":
            if accept(full_dir_path):
                yield full_dir_path
            continue

        # Overlapping entries such as "." and "docs" would walk the same
        # subtree twice; the earlier walk already found every file the later
        # one could, so the result is the same without the second pass.
        if any(
            _walk_reaches(root, full_dir_path, excluded_dir_names)
            for root in walked_roots
        ):
            continue
        done_roots = set(walked_roots)
        walked_roots.append(full_dir_path)

        for root, dirs, filenames in os.walk(full_dir_path, onerror=onerror):
            dirs[:] = [
                d
                for d in dirs
                if d not in excluded_dir_names
                and os.path.join(root, d) not in done_roots
            ]

            for filename in filenames:
                file_path = os.path.normpath(os.path.join(root, filename))
                if accept(file_path):
                    yield file_path


def is_indexed_path(config: dict[str, Any], project_root: str, file_path: str) -> bool:
    """Return whether ``collect_files_for_indexing`` would pick up this file.

    Matches the configuration instead of walking the tree, so a file saved a
    moment ago counts before the next rebuild and large trees stay cheap. The
    binary-content check is left to the caller, which reads the file anyway.
    """
    file_path = os.path.normpath(file_path)
    rel_path = os.path.relpath(file_path, project_root)
    include_patterns = config["global_patterns"]["include"]
    exclude_patterns = config["global_patterns"]["exclude"]
    if not any(match_pattern(rel_path, p) for p in include_patterns):
        return False
    if any(match_pattern(rel_path, p) for p in exclude_patterns):
        return False
    if is_binary_file(file_path, None, config.get("encoding", {})):
        return False

    expanded_dirs = expand_index_dirs(config["index_dirs"], project_root)
    excluded_dir_names = {
        os.path.basename(d["path"].rstrip("/\\"))
        for d in expanded_dirs
        if d.get("exclude", False)
    }
    for dir_config in expanded_dirs:
        if dir_config.get("exclude", False):
            continue
        base = os.path.normpath(os.path.join(project_root, dir_config["path"]))
        if dir_config.get("type") == "file":
            if base == file_path:
                return True
            continue
        if is_inside(base, file_path) is not True:
            continue
        # os.walk prunes excluded names below the configured directory only
        inner_dirs = to_index_path(os.path.relpath(file_path, base)).split("/")[:-1]
        if not set(inner_dirs) & excluded_dir_names:
            return True
    return False


def _walk_reaches(root: str, target: str, excluded_dir_names: set[str]) -> bool:
    """Return whether walking ``root`` with pruning visits directory ``target``."""
    if is_inside(root, target) is not True:
        return False
    rel_path = to_index_path(os.path.relpath(target, root))
    if rel_path == ".":
        return True
    return not set(rel_path.split("/")) & excluded_dir_names


def _unique(items: list[str]) -> list[str]:
    seen = set()
    unique_items = []
    for item in items:
        if item not in seen:
            seen.add(item)
            unique_items.append(item)
    return unique_items
