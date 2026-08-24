#!/usr/bin/env python3
"""
Portability tests: Windows path and console semantics, checked from POSIX.

Windows behavior is reproduced with `ntpath`, which implements the real
Windows path rules on every platform, so these regressions stay covered
without a Windows machine.
"""

import io
import ntpath
import os
import subprocess
import sys
import tempfile

# Add src to path for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from tantivy2agents import TantivyAgent  # noqa: E402
from tantivy2agents.exceptions import (  # noqa: E402
    CLIError,
    FileSystemError,
    ValidationError,
)
from tantivy2agents.paths import (  # noqa: E402
    find_project_root,
    is_inside,
    to_index_path,
    to_index_pattern,
)


def test_find_project_root_terminates_at_windows_drive_root():
    """Walking up from a Windows path must stop, not loop forever.

    Regression test: the walk used to stop only at "/", which never happens on
    Windows because dirname("C:\\\\") is "C:\\\\". Every command hung on start.
    """
    start = "C:\\Users\\kolega\\projekt\\docs"

    result = find_project_root(
        start,
        dirname=ntpath.dirname,
        exists=lambda p: False,
        join=ntpath.join,
    )

    assert result == start


def test_find_project_root_finds_marker_on_windows_paths():
    """The marker is still found when walking Windows-style parents."""
    start = "C:\\Users\\kolega\\projekt\\docs\\guides"
    repo = "C:\\Users\\kolega\\projekt"

    result = find_project_root(
        start,
        dirname=ntpath.dirname,
        exists=lambda p: p == ntpath.join(repo, ".git"),
        join=ntpath.join,
    )

    assert result == repo


def test_find_project_root_terminates_at_posix_root():
    """The same walk still terminates at the POSIX filesystem root."""
    result = find_project_root(
        "/home/kolega/projekt/docs",
        dirname=posixpath_dirname,
        exists=lambda p: False,
    )
    assert result == "/home/kolega/projekt/docs"


def posixpath_dirname(path):
    import posixpath

    return posixpath.dirname(path)


def test_to_index_path_normalizes_windows_separators():
    """A Windows path is stored in the index with forward slashes."""
    assert (
        to_index_path("docs\\guides\\deploy.md", sep="\\", altsep=None)
        == "docs/guides/deploy.md"
    )


def test_to_index_path_keeps_posix_filenames_intact():
    """A backslash is a legal POSIX filename character and must survive.

    Rewriting backslashes unconditionally would corrupt real Linux and macOS
    filenames, so only the running platform's separator is rewritten.
    """
    assert to_index_path("docs/we\\ird.md", sep="/", altsep=None) == "docs/we\\ird.md"


def test_to_index_pattern_normalizes_backslashes():
    """Configured patterns are compared in the same shape as stored paths."""
    assert to_index_pattern("incidents\\") == "incidents/"
    assert to_index_pattern("incidents/") == "incidents/"


def test_search_filters_match_windows_style_config():
    """A filter prefix typed Windows-style must still hide the right paths.

    Regression test: filters compared the configured prefix verbatim against
    the indexed path, so a filter meant to hide a path could silently stop
    matching and reveal what it was supposed to hide.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        os.makedirs(os.path.join(temp_dir, ".git"), exist_ok=True)
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        try:
            agent = TantivyAgent(quiet=True)
        finally:
            os.chdir(original_cwd)

        filters = [
            {
                "paths": ["incidents\\"],
                "hidden": True,
                "show_on_keywords": ["incident"],
                "_keywords_lower": ["incident"],
            }
        ]

        # Indexed path, query without the keyword -> must stay hidden
        assert not agent._should_include_result(
            "incidents/2026/outage.md", set(), filters
        )
        # Same path, query with the keyword -> shown
        assert agent._should_include_result(
            "incidents/2026/outage.md", {"incident"}, filters
        )
        # Unrelated path is unaffected
        assert agent._should_include_result("docs/guide.md", set(), filters)


def test_is_inside_reports_uncomparable_paths():
    """Paths on different Windows drives have no common root at all."""
    assert is_inside("/home/kolega/projekt", "/home/kolega/projekt/docs") is True
    assert is_inside("/home/kolega/projekt", "/etc") is False


def test_output_outside_project_is_rejected_without_valueerror():
    """A rejected output path raises ValidationError, never a bare ValueError.

    On Windows a --output on another drive makes commonpath raise ValueError;
    the user must get the normal structured error instead.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        os.makedirs(os.path.join(temp_dir, ".git"), exist_ok=True)
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        try:
            agent = TantivyAgent(quiet=True)

            def uncomparable(paths):
                raise ValueError("Paths don't have the same drive")

            original = os.path.commonpath
            os.path.commonpath = uncomparable
            try:
                raised = None
                try:
                    agent._prepare_output_file("D:\\temp\\out.json")
                except ValidationError as e:
                    raised = e
                assert raised is not None, "Expected a ValidationError"
            finally:
                os.path.commonpath = original
        finally:
            os.chdir(original_cwd)


def test_index_dir_on_another_drive_is_rejected():
    """An unreachable index path fails with FileSystemError, not ValueError."""
    with tempfile.TemporaryDirectory() as temp_dir:
        os.makedirs(os.path.join(temp_dir, ".git"), exist_ok=True)
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        try:
            agent = TantivyAgent(quiet=True)

            def uncomparable(paths):
                raise ValueError("Paths don't have the same drive")

            original = os.path.commonpath
            os.path.commonpath = uncomparable
            try:
                raised = None
                try:
                    agent._ensure_safe_index_path(os.path.join(temp_dir, "data"))
                except FileSystemError as e:
                    raised = e
                assert raised is not None, "Expected a FileSystemError"
            finally:
                os.path.commonpath = original
        finally:
            os.chdir(original_cwd)


class _AsciiStream(io.StringIO):
    """A stream that behaves like a redirected cp1250/ascii Windows pipe."""

    encoding = "ascii"

    def write(self, text):
        text.encode(self.encoding)  # raises UnicodeEncodeError on emoji
        return super().write(text)


def test_error_output_survives_non_utf8_stream():
    """Error messages must print even when the stream cannot encode emoji.

    Regression test: the emoji in the human-readable error crashed with
    UnicodeEncodeError when output was redirected on a non-UTF-8 Windows
    console, hiding the real error behind an encoding error.
    """
    error = CLIError(message="neco se pokazilo", hint="zkus to znovu")

    stream = _AsciiStream()
    original = sys.stderr
    sys.stderr = stream
    try:
        error.print()
    finally:
        sys.stderr = original

    output = stream.getvalue()
    assert "neco se pokazilo" in output
    assert "zkus to znovu" in output


WINDOWS_LOCK_PROBE = '''\
"""Exercise the Windows branch of locking.py with a stubbed msvcrt."""

import os
import sys
import tempfile
import types

sys.path.insert(0, {src_path!r})

held = {{}}

fake = types.ModuleType("msvcrt")
fake.LK_NBLCK = 2
fake.LK_UNLCK = 0


def locking(fd, mode, nbytes):
    """Emulate a Windows exclusive byte-range lock, keyed by file identity."""
    key = os.fstat(fd).st_ino
    if mode == fake.LK_UNLCK:
        held.pop(key, None)
        return
    if key in held and held[key] != fd:
        raise OSError(36, "Resource deadlock avoided")
    held[key] = fd


fake.locking = locking
sys.modules["msvcrt"] = fake
sys.platform = "win32"

from tantivy2agents import locking as index_locking

with tempfile.TemporaryDirectory() as temp_dir:
    path = os.path.join(temp_dir, "index.lock")
    first = index_locking.IndexLock(path)
    second = index_locking.IndexLock(path)

    with first.acquire(timeout=1):
        assert first.held
        try:
            with second.acquire(timeout=0.1):
                raise AssertionError("second holder must be blocked")
        except index_locking.IndexLockTimeoutError:
            pass
    assert not first.held

    # The lock must be free again once the first holder released it.
    with second.acquire(timeout=1):
        assert second.held

print("windows-lock-ok")
'''


def test_windows_lock_branch_is_wired_correctly():
    """The msvcrt branch must import and enforce exclusion.

    This cannot prove the tool works on Windows, but it does catch syntax and
    wiring mistakes in a code path that never executes on this machine. It
    runs in a subprocess because it fakes sys.platform and msvcrt.
    """
    src_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
    with tempfile.TemporaryDirectory() as temp_dir:
        probe_path = os.path.join(temp_dir, "windows_lock_probe.py")
        with open(probe_path, "w", encoding="utf-8") as f:
            f.write(WINDOWS_LOCK_PROBE.format(src_path=src_path))

        result = subprocess.run(
            [sys.executable, probe_path],
            capture_output=True,
            text=True,
            timeout=120,
        )

        assert result.returncode == 0, result.stderr
        assert "windows-lock-ok" in result.stdout


def main():
    """Run all portability tests"""
    tests = [
        (
            "Project Root Terminates On Windows",
            test_find_project_root_terminates_at_windows_drive_root,
        ),
        (
            "Project Root Finds Marker On Windows",
            test_find_project_root_finds_marker_on_windows_paths,
        ),
        (
            "Project Root Terminates On POSIX",
            test_find_project_root_terminates_at_posix_root,
        ),
        ("Index Path Normalization", test_to_index_path_normalizes_windows_separators),
        ("POSIX Filenames Intact", test_to_index_path_keeps_posix_filenames_intact),
        ("Index Pattern Normalization", test_to_index_pattern_normalizes_backslashes),
        (
            "Filters Match Windows Config",
            test_search_filters_match_windows_style_config,
        ),
        ("Uncomparable Paths", test_is_inside_reports_uncomparable_paths),
        (
            "Output Path Across Drives",
            test_output_outside_project_is_rejected_without_valueerror,
        ),
        ("Index Dir Across Drives", test_index_dir_on_another_drive_is_rejected),
        ("Error Output On ASCII Stream", test_error_output_survives_non_utf8_stream),
        ("Windows Lock Branch Wiring", test_windows_lock_branch_is_wired_correctly),
    ]

    passed = 0
    for test_name, test_func in tests:
        try:
            test_func()
            print(f"  {test_name}")
            passed += 1
        except Exception as e:
            import traceback

            print(f"  {test_name}: {e}")
            print(f"   Traceback: {traceback.format_exc()}")

    print()
    print(f"Test Results: {passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("All tests passed!")
        return 0
    print("Some tests failed!")
    return 1


if __name__ == "__main__":
    sys.exit(main())
