"""File discovery and path filtering for indexing."""

from __future__ import annotations

import fnmatch
import glob
import os
from typing import Any

MIN_TEXT_CHAR_RATIO = 0.7
PRINTABLE_ASCII_RANGE = (32, 126)
WHITESPACE_CHARS = (9, 10, 13)


def match_pattern(path: str, pattern: str) -> bool:
    """Match a path against a glob pattern."""
    normalized_path = path.replace(os.sep, "/")
    normalized_pattern = pattern.replace(os.sep, "/")

    if fnmatch.fnmatch(normalized_path, normalized_pattern):
        return True

    if "/" not in normalized_pattern:
        return fnmatch.fnmatch(os.path.basename(normalized_path), normalized_pattern)

    return False


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
            excluded_dir_names.add(os.path.basename(dir_path.rstrip("/")))

    for dir_config in expanded_dirs:
        if dir_config.get("exclude", False):
            continue

        dir_path = dir_config["path"]
        include_patterns = config["global_patterns"]["include"]
        exclude_patterns = config["global_patterns"]["exclude"]

        full_dir_path = os.path.normpath(os.path.join(project_root, dir_path))
        if not os.path.exists(full_dir_path):
            continue

        if show_dirs:
            dirs_processed.append(full_dir_path)

        if dir_config.get("type") == "file":
            _maybe_add_file(
                files,
                full_dir_path,
                project_root,
                include_patterns,
                exclude_patterns,
                config.get("encoding", {}),
                show_files,
            )
        else:
            for root, dirs, filenames in os.walk(full_dir_path):
                dirs[:] = [d for d in dirs if d not in excluded_dir_names]

                for filename in filenames:
                    _maybe_add_file(
                        files,
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


def _maybe_add_file(
    files: list[str],
    file_path: str,
    project_root: str,
    include_patterns: list[str],
    exclude_patterns: list[str],
    encoding_config: dict[str, Any],
    show_files: bool,
) -> None:
    file_path = os.path.normpath(file_path)
    rel_path = os.path.relpath(file_path, project_root)

    included = any(match_pattern(rel_path, pattern) for pattern in include_patterns)
    excluded = any(match_pattern(rel_path, pattern) for pattern in exclude_patterns)

    if not included or excluded:
        return

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
