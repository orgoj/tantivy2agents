"""File discovery and path filtering for indexing."""

from __future__ import annotations

import fnmatch
import glob
import os
import re
from typing import Any

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
    pattern_list: list[Any], project_root: str
) -> list[dict[str, Any]]:
    """Expand configured index directory/file patterns to concrete paths."""
    expanded_paths = []

    for item in pattern_list:
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


def collect_files_for_indexing(
    config: dict[str, Any],
    project_root: str,
    show_dirs: bool = False,
    show_files: bool = False,
) -> tuple[list[str], list[str]]:
    """Collect files to index based on configuration."""
    files = []
    dirs_processed = []
    expanded_dirs = expand_index_dirs(config["index_dirs"], project_root)

    excluded_dir_names = set()
    for dir_config in expanded_dirs:
        if dir_config.get("exclude", False):
            dir_path = dir_config["path"]
            excluded_dir_names.add(os.path.basename(dir_path.rstrip("/\\")))

    include_patterns = PatternSet(config["global_patterns"]["include"])
    exclude_patterns = PatternSet(config["global_patterns"]["exclude"])
    seen: set[str] = set()
    walked_roots: list[str] = []

    for dir_config in expanded_dirs:
        if dir_config.get("exclude", False):
            continue

        dir_path = dir_config["path"]

        full_dir_path = os.path.normpath(os.path.join(project_root, dir_path))
        if not os.path.exists(full_dir_path):
            continue

        if show_dirs:
            dirs_processed.append(full_dir_path)

        if dir_config.get("type") == "file":
            _maybe_add_file(
                files,
                seen,
                full_dir_path,
                project_root,
                include_patterns,
                exclude_patterns,
                config.get("encoding", {}),
                show_files,
            )
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

        for root, dirs, filenames in os.walk(full_dir_path):
            dirs[:] = [
                d
                for d in dirs
                if d not in excluded_dir_names
                and os.path.join(root, d) not in done_roots
            ]

            for filename in filenames:
                _maybe_add_file(
                    files,
                    seen,
                    os.path.join(root, filename),
                    project_root,
                    include_patterns,
                    exclude_patterns,
                    config.get("encoding", {}),
                    show_files,
                )

    unique_files = _unique(files)
    unique_dirs = _unique(dirs_processed)

    if show_dirs:
        print("Directories to be processed:")
        for dir_path in unique_dirs:
            rel_dir = os.path.relpath(dir_path, project_root)
            print(f"  {rel_dir}")

    return unique_files, unique_dirs


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


def _maybe_add_file(
    files: list[str],
    seen: set[str],
    file_path: str,
    project_root: str,
    include_patterns: PatternSet,
    exclude_patterns: PatternSet,
    encoding_config: dict[str, Any],
    show_files: bool,
) -> None:
    file_path = os.path.normpath(file_path)
    if file_path in seen:
        return
    rel_path = os.path.relpath(file_path, project_root)

    if not include_patterns.matches(rel_path) or exclude_patterns.matches(rel_path):
        return
    seen.add(file_path)

    try:
        with open(file_path, "rb") as f:
            content_bytes = f.read()
    except OSError:
        return

    if is_binary_file(file_path, content_bytes, encoding_config):
        return

    files.append(file_path)
    if show_files:
        print(f"  {rel_path}")


def _unique(items: list[str]) -> list[str]:
    seen = set()
    unique_items = []
    for item in items:
        if item not in seen:
            seen.add(item)
            unique_items.append(item)
    return unique_items
