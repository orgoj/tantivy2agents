"""Path helpers that behave the same on POSIX and Windows.

Windows differs from POSIX in three ways that matter here: the filesystem root
is a drive rather than ``/``, paths use backslashes, and paths on different
drives have no common ancestor at all. Every place that walks parents, stores a
path in the index, or checks containment goes through this module.
"""

import os
from typing import Callable, Optional

# Separator used for every path stored in the index or matched against
# configured patterns, on all platforms.
INDEX_SEPARATOR = "/"


def find_project_root(
    start: str,
    marker: str = ".git",
    dirname: Callable[[str], str] = os.path.dirname,
    exists: Callable[[str], bool] = os.path.exists,
    join: Callable[..., str] = os.path.join,
) -> str:
    """Walk up from ``start`` looking for ``marker``; fall back to ``start``.

    The walk stops when a directory is its own parent, which is what the
    filesystem root looks like on every platform. Comparing against ``"/"``
    instead would never terminate on Windows, where ``dirname("C:\\\\")`` is
    ``"C:\\\\"``.

    The ``dirname``/``exists``/``join`` parameters exist so the Windows
    behavior can be tested from POSIX with ``ntpath``.
    """
    current = start
    while True:
        if exists(join(current, marker)):
            return current
        parent = dirname(current)
        if parent == current:
            return start
        current = parent


def to_index_path(
    path: str, sep: str = os.sep, altsep: Optional[str] = os.altsep
) -> str:
    """Normalize a local relative path to the separator used inside the index.

    Only the running platform's separators are rewritten. A backslash is a
    legal character in a POSIX filename, so rewriting it unconditionally would
    corrupt paths on Linux and macOS.

    The ``sep``/``altsep`` parameters exist so the Windows behavior can be
    tested from POSIX.
    """
    if sep != INDEX_SEPARATOR:
        path = path.replace(sep, INDEX_SEPARATOR)
    if altsep and altsep != INDEX_SEPARATOR:
        path = path.replace(altsep, INDEX_SEPARATOR)
    return path


def to_index_pattern(pattern: str) -> str:
    """Normalize a configured path or glob so it matches stored index paths.

    Configuration is written by a person, who may well type a Windows-style
    prefix such as ``incidents\\``. Unlike a real filename, a configured
    pattern never legitimately contains a literal backslash, so both
    separators are accepted here.
    """
    return pattern.replace("\\", INDEX_SEPARATOR)


def is_inside(parent: str, child: str) -> Optional[bool]:
    """Return whether ``child`` is at or below ``parent``.

    Returns None when the two paths cannot be compared at all, which on
    Windows means they live on different drives. Callers turn that into a
    user-facing error instead of the bare ValueError ``commonpath`` raises.
    """
    try:
        return os.path.commonpath([parent, child]) == parent
    except ValueError:
        return None
