#!/usr/bin/env python3
"""
File discovery tests: compiled pattern matching and overlapping index_dirs.
"""

import os
import sys

# Add src to path for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from tantivy2agents import files  # noqa: E402
from tantivy2agents.files import (  # noqa: E402
    PatternSet,
    collect_files_for_indexing,
    match_pattern,
)

PATTERNS = [
    "*.md",
    "README*",
    "docs/*.md",
    "docs/**/*.md",
    "*/notes/*",
    "incidents\\*",
    "[ab]*.txt",
    "AGENTS.md",
]
PATHS = [
    "README.md",
    "docs/README.txt",
    "docs/guide.md",
    "docs/deep/guide.md",
    "a.txt",
    "x/a.txt",
    "c.txt",
    "x/notes/n.yml",
    "incidents/2026.yml",
    "sub/AGENTS.md",
    "file.mdx",
]


def write(root, rel_path, text="# Doc\n"):
    path = os.path.join(root, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def config_for(index_dirs):
    return {
        "global_patterns": {"include": ["*.md"], "exclude": ["*.tmp"]},
        "index_dirs": index_dirs,
        "encoding": {},
    }


def rel(paths, root):
    return [os.path.relpath(p, root).replace(os.sep, "/") for p in paths]


def test_pattern_set_matches_like_match_pattern():
    for pattern in PATTERNS:
        compiled = PatternSet([pattern])
        for path in PATHS:
            assert compiled.matches(path) == match_pattern(path, pattern), (
                pattern,
                path,
            )

    combined = PatternSet(PATTERNS)
    for path in PATHS:
        assert combined.matches(path) == any(match_pattern(path, p) for p in PATTERNS)


def test_empty_pattern_set_matches_nothing():
    assert not PatternSet([]).matches("README.md")


def test_overlapping_index_dirs_walk_each_subtree_once(tmp_path, monkeypatch):
    root = str(tmp_path)
    write(root, "top.md")
    write(root, "docs/guide.md")
    write(root, "docs/deep/more.md")

    walked = []
    real_walk = os.walk

    def counting_walk(top, *args, **kwargs):
        for entry in real_walk(top, *args, **kwargs):
            walked.append(entry[0])
            yield entry

    monkeypatch.setattr(files.os, "walk", counting_walk)

    for index_dirs in (["docs", "."], [".", "docs"]):
        walked.clear()
        found, _ = collect_files_for_indexing(config_for(index_dirs), root)
        assert sorted(rel(found, root)) == [
            "docs/deep/more.md",
            "docs/guide.md",
            "top.md",
        ]
        assert len(walked) == len(set(walked)) == 3


def test_overlap_keeps_file_order(tmp_path):
    root = str(tmp_path)
    write(root, "top.md")
    write(root, "docs/guide.md")

    found, _ = collect_files_for_indexing(config_for(["docs", "."]), root)
    assert rel(found, root) == ["docs/guide.md", "top.md"]


def test_listed_dir_below_pruned_name_is_still_walked(tmp_path):
    """A walk of "." prunes "archive", so it must not stand in for "archive/keep"."""
    root = str(tmp_path)
    write(root, "top.md")
    write(root, "archive/old.md")
    write(root, "archive/keep/kept.md")

    index_dirs = [".", "archive/keep", {"path": "archive", "exclude": True}]
    found, _ = collect_files_for_indexing(config_for(index_dirs), root)
    assert sorted(rel(found, root)) == ["archive/keep/kept.md", "top.md"]


def test_file_listed_twice_is_read_once(tmp_path, monkeypatch):
    root = str(tmp_path)
    write(root, "docs/guide.md")

    checked = []
    real_is_binary = files.is_binary_file

    def counting_is_binary(file_path, *args, **kwargs):
        checked.append(file_path)
        return real_is_binary(file_path, *args, **kwargs)

    monkeypatch.setattr(files, "is_binary_file", counting_is_binary)

    found, _ = collect_files_for_indexing(
        config_for(["docs/guide.md", "docs", "docs/*.md"]), root
    )
    assert rel(found, root) == ["docs/guide.md"]
    assert len(checked) == 1
