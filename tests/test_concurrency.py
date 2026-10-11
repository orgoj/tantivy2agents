#!/usr/bin/env python3
"""
Concurrency tests: parallel index/search processes must not corrupt the index.
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import time

# Add src to path for direct imports
SRC_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
sys.path.insert(0, SRC_PATH)

import tantivy  # noqa: E402

from tantivy2agents import TantivyAgent  # noqa: E402
from tantivy2agents.agent import BUILD_DIR_PREFIX, RETIRED_DIR_PREFIX  # noqa: E402
from tantivy2agents.locking import (  # noqa: E402
    LOCK_FILENAME,
    IndexLock,
    IndexLockTimeoutError,
)

# Enough documents that a rebuild takes long enough for parallel processes to
# overlap; before the fix they deleted each other's index files here.
CORPUS_SIZE = 400
PARALLEL_SEARCHES = 8

RUNNER_SOURCE = """\
import json
import os
import sys
import time

sys.path.insert(0, {src_path!r})

from tantivy2agents import TantivyAgent

go_file = sys.argv[1]
while not os.path.exists(go_file):
    time.sleep(0.005)

agent = TantivyAgent(quiet=True)
agent.search_command("alpha", 5, "json", None)
"""


def _write_project(project_root, corpus_size=CORPUS_SIZE):
    """Create a minimal indexable project and return its config path."""
    os.makedirs(os.path.join(project_root, ".git"), exist_ok=True)
    docs_dir = os.path.join(project_root, "docs")
    os.makedirs(docs_dir, exist_ok=True)

    for i in range(corpus_size):
        with open(os.path.join(docs_dir, f"doc{i:04d}.md"), "w", encoding="utf-8") as f:
            f.write(
                f"# Alpha Document {i}\n\n"
                f"Body text about alpha beta gamma delta number {i}.\n"
            )

    config = {
        "version": "1.0",
        "index_dir": ".tantivy-data",
        "global_patterns": {"include": ["*.md"], "exclude": []},
        "index_dirs": ["docs/"],
        "search": {"default_limit": 5, "show_description": True, "filters": []},
        "auto_hook": False,
    }
    config_path = os.path.join(project_root, ".tantivy2agents.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f)
    return config_path


def _mark_index_outdated(data_dir):
    """Flag the index stale so every search tries to rebuild it."""
    index_info_path = os.path.join(data_dir, "index_info.json")
    with open(index_info_path, "r", encoding="utf-8") as f:
        index_info = json.load(f)
    index_info["outdated"] = True
    with open(index_info_path, "w", encoding="utf-8") as f:
        json.dump(index_info, f, indent=2)


def _build_initial_index(project_root):
    """Index the project from its own directory and return the data dir."""
    original_cwd = os.getcwd()
    os.chdir(project_root)
    try:
        agent = TantivyAgent(quiet=True)
        agent.index_command(force=True)
    finally:
        os.chdir(original_cwd)
    return os.path.join(project_root, ".tantivy-data")


def test_parallel_searches_on_stale_index_all_succeed():
    """Parallel searches over a stale index must not destroy each other's data.

    Regression test: every process used to call index_command(force=True),
    which removed the whole idx/ directory while the others were reading or
    writing it, producing 'Failed to open file for write' and FileDoesNotExist.
    """
    with tempfile.TemporaryDirectory() as project_root:
        _write_project(project_root)
        data_dir = _build_initial_index(project_root)
        _mark_index_outdated(data_dir)

        runner_path = os.path.join(project_root, "run_search.py")
        with open(runner_path, "w", encoding="utf-8") as f:
            f.write(RUNNER_SOURCE.format(src_path=SRC_PATH))

        go_file = os.path.join(project_root, "go")

        processes = []
        for _ in range(PARALLEL_SEARCHES):
            processes.append(
                subprocess.Popen(
                    [sys.executable, runner_path, go_file],
                    cwd=project_root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            )

        # Give every interpreter time to boot, then release them together.
        time.sleep(1.0)
        with open(go_file, "w", encoding="utf-8") as f:
            f.write("go")

        failures = []
        for proc in processes:
            stdout, stderr = proc.communicate(timeout=300)
            if proc.returncode != 0:
                failures.append(f"exit={proc.returncode} stderr={stderr.strip()}")
                continue
            try:
                payload = json.loads(stdout)
            except json.JSONDecodeError as e:
                failures.append(f"invalid JSON output ({e}): {stdout[:200]!r}")
                continue
            if not payload.get("results"):
                failures.append(f"no search results: {stdout[:200]!r}")

        assert not failures, "Parallel searches failed:\n" + "\n".join(failures)

        # The winner's index must be intact and no scratch dirs left behind.
        index_dir = os.path.join(data_dir, "idx")
        assert tantivy.Index.open(index_dir) is not None
        leftovers = [
            entry
            for entry in os.listdir(data_dir)
            if entry.startswith((BUILD_DIR_PREFIX, RETIRED_DIR_PREFIX))
        ]
        assert not leftovers, f"Scratch directories left behind: {leftovers}"


COUNTING_RUNNER_SOURCE = """\
import os
import sys
import time

sys.path.insert(0, {src_path!r})

from tantivy2agents import TantivyAgent

go_file, log_file = sys.argv[1], sys.argv[2]
publish = TantivyAgent._publish_index


def counting_publish(self, build_dir, index_dir):
    publish(self, build_dir, index_dir)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{{os.getpid()}}\\n")


TantivyAgent._publish_index = counting_publish
while not os.path.exists(go_file):
    time.sleep(0.005)

agent = TantivyAgent(quiet=True)
agent.search_command("addedword", 5, "json", None)
"""


def test_parallel_searches_after_an_edit_publish_once():
    """Searches racing on a changed tree refresh it once; the rest reuse it."""
    with tempfile.TemporaryDirectory() as project_root:
        _write_project(project_root)
        _build_initial_index(project_root)
        with open(os.path.join(project_root, "docs", "added.md"), "w") as f:
            f.write("# Added\n\naddedword\n")

        runner_path = os.path.join(project_root, "run_search.py")
        with open(runner_path, "w", encoding="utf-8") as f:
            f.write(COUNTING_RUNNER_SOURCE.format(src_path=SRC_PATH))
        go_file = os.path.join(project_root, "go")
        log_file = os.path.join(project_root, "publishes.log")

        processes = [
            subprocess.Popen(
                [sys.executable, runner_path, go_file, log_file],
                cwd=project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for _ in range(PARALLEL_SEARCHES)
        ]
        time.sleep(1.0)
        with open(go_file, "w", encoding="utf-8") as f:
            f.write("go")

        failures = []
        for proc in processes:
            stdout, stderr = proc.communicate(timeout=300)
            if proc.returncode != 0:
                failures.append(f"exit={proc.returncode} stderr={stderr.strip()}")
            elif "docs/added.md" not in stdout:
                failures.append(f"added file not found: {stdout[:200]!r}")
        assert not failures, "Parallel searches failed:\n" + "\n".join(failures)

        with open(log_file, encoding="utf-8") as f:
            assert len(f.read().splitlines()) == 1


def test_parallel_index_and_search_processes_coexist():
    """Forced rebuilds running next to searches must never break either side."""
    with tempfile.TemporaryDirectory() as project_root:
        _write_project(project_root)
        data_dir = _build_initial_index(project_root)

        runner_path = os.path.join(project_root, "run_search.py")
        with open(runner_path, "w", encoding="utf-8") as f:
            f.write(RUNNER_SOURCE.format(src_path=SRC_PATH))

        go_file = os.path.join(project_root, "go")
        env = os.environ.copy()
        env["PYTHONPATH"] = SRC_PATH + os.pathsep + env.get("PYTHONPATH", "")

        processes = []
        for _ in range(4):
            processes.append(
                (
                    "index",
                    subprocess.Popen(
                        [
                            sys.executable,
                            "-m",
                            "tantivy2agents",
                            "index",
                            "--force",
                            "--quiet",
                        ],
                        cwd=project_root,
                        env=env,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    ),
                )
            )
        for _ in range(4):
            processes.append(
                (
                    "search",
                    subprocess.Popen(
                        [sys.executable, runner_path, go_file],
                        cwd=project_root,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    ),
                )
            )

        time.sleep(1.0)
        with open(go_file, "w", encoding="utf-8") as f:
            f.write("go")

        failures = []
        for kind, proc in processes:
            stdout, stderr = proc.communicate(timeout=300)
            if proc.returncode != 0:
                failures.append(f"{kind} exit={proc.returncode} {stderr.strip()}")
            elif kind == "search" and not json.loads(stdout).get("results"):
                failures.append(f"search returned nothing: {stdout[:200]!r}")

        assert not failures, "Parallel index/search failed:\n" + "\n".join(failures)
        assert tantivy.Index.open(os.path.join(data_dir, "idx")) is not None


def test_failed_rebuild_keeps_previous_index():
    """A rebuild that blows up must leave the last usable index in place."""
    with tempfile.TemporaryDirectory() as project_root:
        _write_project(project_root, corpus_size=5)
        data_dir = _build_initial_index(project_root)
        index_dir = os.path.join(data_dir, "idx")

        before = sorted(os.listdir(index_dir))
        assert before, "Initial index should contain files"

        original_cwd = os.getcwd()
        os.chdir(project_root)
        try:
            agent = TantivyAgent(quiet=True)

            def boom(*args, **kwargs):
                raise RuntimeError("simulated tantivy failure")

            agent._create_schema = boom

            failed = False
            try:
                agent.index_command(force=True)
            except Exception:
                failed = True

            assert failed, "Rebuild should have failed"

            # Old index still there and openable
            assert sorted(os.listdir(index_dir)) == before
            assert tantivy.Index.open(index_dir) is not None

            leftovers = [
                entry
                for entry in os.listdir(data_dir)
                if entry.startswith((BUILD_DIR_PREFIX, RETIRED_DIR_PREFIX))
            ]
            assert not leftovers, f"Scratch directories left behind: {leftovers}"

            # A healthy rebuild still works afterwards
            healthy = TantivyAgent(quiet=True)
            healthy.index_command(force=True)
            assert tantivy.Index.open(index_dir) is not None
        finally:
            os.chdir(original_cwd)


def test_clear_keeps_lock_file_and_removes_index():
    """clear must drop index data but keep the lock other processes hold."""
    with tempfile.TemporaryDirectory() as project_root:
        _write_project(project_root, corpus_size=3)
        data_dir = _build_initial_index(project_root)

        original_cwd = os.getcwd()
        os.chdir(project_root)
        try:
            TantivyAgent(quiet=True).clear_command()
        finally:
            os.chdir(original_cwd)

        assert not os.path.exists(os.path.join(data_dir, "idx"))
        assert not os.path.exists(os.path.join(data_dir, "index_info.json"))
        assert os.path.exists(
            os.path.join(data_dir, LOCK_FILENAME)
        ), "Lock file must survive clear so it never lives inside the index"


def test_lock_file_lives_outside_index_directory():
    """The lock must not sit inside the directory a rebuild replaces."""
    with tempfile.TemporaryDirectory() as project_root:
        _write_project(project_root, corpus_size=3)
        original_cwd = os.getcwd()
        os.chdir(project_root)
        try:
            agent = TantivyAgent(quiet=True)
            lock_path = agent.index_lock.lock_path
        finally:
            os.chdir(original_cwd)

        index_dir = os.path.join(project_root, ".tantivy-data", "idx")
        assert os.path.dirname(lock_path) != index_dir
        assert os.path.basename(lock_path) == LOCK_FILENAME


HOLD_LOCK_SOURCE = """\
import sys, time
sys.path.insert(0, {src_path!r})
from tantivy2agents.locking import IndexLock
lock = IndexLock({lock_path!r})
with lock.acquire(timeout={timeout}):
    print('acquired', flush=True)
    time.sleep({hold})
"""


def _write_lock_script(temp_dir, lock_path, timeout=30, hold=0):
    script_path = os.path.join(temp_dir, f"grab_lock_{hold}.py")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(
            HOLD_LOCK_SOURCE.format(
                src_path=SRC_PATH, lock_path=lock_path, timeout=timeout, hold=hold
            )
        )
    return script_path


def test_index_lock_is_exclusive_across_processes():
    """A second process must wait for the lock."""
    with tempfile.TemporaryDirectory() as temp_dir:
        lock_path = os.path.join(temp_dir, LOCK_FILENAME)
        script_path = _write_lock_script(temp_dir, lock_path)

        lock = IndexLock(lock_path)
        with lock.acquire(timeout=5):
            proc = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            time.sleep(0.5)
            assert proc.poll() is None, "Second process must block on the lock"

        stdout, stderr = proc.communicate(timeout=60)
        assert proc.returncode == 0, stderr
        assert "acquired" in stdout


def test_index_lock_is_released_when_holder_is_killed():
    """The OS must drop the lock of a process that dies without releasing it.

    This is the property the whole design rests on: a rebuild killed halfway
    through must not leave a lock that blocks every later search.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        lock_path = os.path.join(temp_dir, LOCK_FILENAME)
        script_path = _write_lock_script(temp_dir, lock_path, hold=60)

        proc = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            # Wait until the child really holds the lock.
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if proc.stdout.readline().strip() == "acquired":
                    break
            else:
                raise AssertionError("Child never acquired the lock")

            waiter = IndexLock(lock_path)
            timed_out = False
            try:
                with waiter.acquire(timeout=0.2):
                    pass
            except IndexLockTimeoutError:
                timed_out = True
            assert timed_out, "Lock should be held by the child"

            proc.kill()
            proc.wait(timeout=30)

            # No cleanup ran in the child, yet the lock must be free.
            with waiter.acquire(timeout=10):
                pass
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=30)


def test_index_lock_is_reentrant():
    """Nested acquisition inside one process must not deadlock."""
    with tempfile.TemporaryDirectory() as temp_dir:
        lock = IndexLock(os.path.join(temp_dir, LOCK_FILENAME))
        with lock.acquire(timeout=5):
            with lock.acquire(timeout=5):
                assert lock.held
        assert not lock.held


def test_index_lock_times_out():
    """Waiting past the timeout raises a structured CLI error."""
    with tempfile.TemporaryDirectory() as temp_dir:
        lock_path = os.path.join(temp_dir, LOCK_FILENAME)
        holder = IndexLock(lock_path)
        waiter = IndexLock(lock_path)

        released = threading.Event()
        acquired = threading.Event()

        def hold():
            with holder.acquire(timeout=5):
                acquired.set()
                released.wait(10)

        thread = threading.Thread(target=hold)
        thread.start()
        try:
            acquired.wait(10)
            error = None
            try:
                with waiter.acquire(timeout=0.2):
                    pass
            except IndexLockTimeoutError as e:
                error = e
            assert error is not None, "Expected the waiter to time out"
            # The error should name who is holding the lock.
            assert "held_by" in error.context
            assert f"pid={os.getpid()}" in error.context["held_by"]
        finally:
            released.set()
            thread.join(10)


def test_stale_build_directories_are_cleaned_up():
    """Scratch dirs from a crashed rebuild are removed on the next index run."""
    with tempfile.TemporaryDirectory() as project_root:
        _write_project(project_root, corpus_size=3)
        data_dir = _build_initial_index(project_root)

        stale_build = os.path.join(data_dir, f"{BUILD_DIR_PREFIX}deadbeef")
        stale_retired = os.path.join(data_dir, f"{RETIRED_DIR_PREFIX}deadbeef")
        os.makedirs(stale_build)
        os.makedirs(stale_retired)

        original_cwd = os.getcwd()
        os.chdir(project_root)
        try:
            TantivyAgent(quiet=True).index_command(force=True)
        finally:
            os.chdir(original_cwd)

        assert not os.path.exists(stale_build)
        assert not os.path.exists(stale_retired)


def main():
    """Run all concurrency tests"""
    tests = [
        (
            "Parallel Searches On Stale Index",
            test_parallel_searches_on_stale_index_all_succeed,
        ),
        (
            "Parallel Index And Search Processes",
            test_parallel_index_and_search_processes_coexist,
        ),
        (
            "Failed Rebuild Keeps Previous Index",
            test_failed_rebuild_keeps_previous_index,
        ),
        ("Clear Keeps Lock File", test_clear_keeps_lock_file_and_removes_index),
        ("Lock Outside Index Directory", test_lock_file_lives_outside_index_directory),
        (
            "Exclusive Lock Across Processes",
            test_index_lock_is_exclusive_across_processes,
        ),
        (
            "Lock Released When Holder Killed",
            test_index_lock_is_released_when_holder_is_killed,
        ),
        ("Reentrant Lock", test_index_lock_is_reentrant),
        ("Lock Timeout", test_index_lock_times_out),
        ("Stale Build Directory Cleanup", test_stale_build_directories_are_cleaned_up),
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
