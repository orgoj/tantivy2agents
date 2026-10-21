#!/usr/bin/env python3
"""
Automatic refresh: search notices file changes without any hook.
"""

import errno
import json
import os
import sys

import pytest

# Add src to path for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

import tantivy  # noqa: E402

from tantivy2agents import TantivyAgent, agent as agent_module  # noqa: E402
from tantivy2agents import files as files_module  # noqa: E402
from tantivy2agents.agent import (  # noqa: E402
    BUILD_DIR_PREFIX,
    INDEX_STATE_FILENAME,
    RETIRED_DIR_PREFIX,
)

SCHEMA_FIELDS = {
    "title": {"weight": 2.0, "tokenizer": "en_stem"},
    "body": {"weight": 1.0, "tokenizer": "en_stem"},
    "path": {"weight": 0.5, "tokenizer": "raw"},
}


def write_config(root, **overrides):
    config = {
        "version": "1.0",
        "index_dir": ".tantivy-data",
        "global_patterns": {"include": ["*.md"], "exclude": []},
        "index_dirs": ["docs"],
        "schema_fields": SCHEMA_FIELDS,
        "search": {"default_limit": 20, "filters": []},
        "usage": {"enabled": False},
        "auto_hook": False,
    }
    config.update(overrides)
    with open(os.path.join(root, ".tantivy2agents.json"), "w", encoding="utf-8") as f:
        json.dump(config, f)


def write(root, rel_path, text):
    path = os.path.join(root, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def bump_mtime(path, seconds=10):
    """Move the mtime forward so a same-second rewrite is still a change."""
    st = os.stat(path)
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + seconds * 10**9))


@pytest.fixture
def project(tmp_path, monkeypatch):
    root = str(tmp_path)
    os.makedirs(os.path.join(root, ".git"))
    write_config(root)
    write(root, "docs/alpha.md", "# Alpha\n\nalphaword content\n")
    write(root, "docs/nested/beta.md", "# Beta\n\nbetaword content\n")
    monkeypatch.chdir(root)
    return root


class Spy:
    """Record refresh outcomes of an agent."""

    def __init__(self, agent):
        self.results = []
        original = agent._refresh_index_locked

        def recording(*args, **kwargs):
            result = original(*args, **kwargs)
            self.results.append(result)
            return result

        agent._refresh_index_locked = recording

    @property
    def last(self):
        return self.results[-1].action


def new_agent():
    agent = TantivyAgent(quiet=True)
    return agent, Spy(agent)


def search_paths(agent, query, capsys):
    capsys.readouterr()
    agent.search_command(query)
    out = capsys.readouterr().out
    if out.startswith("No results"):
        return []
    return [item["path"] for item in json.loads(out)["results"]]


def index_dir(root):
    return os.path.join(root, ".tantivy-data", "idx")


def num_docs(root):
    return tantivy.Index.open(index_dir(root)).searcher().num_docs


def read_state(root):
    with open(os.path.join(index_dir(root), INDEX_STATE_FILENAME)) as f:
        return json.load(f)


def read_index_info(root):
    try:
        with open(os.path.join(root, ".tantivy-data", "index_info.json")) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def scratch_dirs(root):
    data_dir = os.path.join(root, ".tantivy-data")
    return [
        e
        for e in os.listdir(data_dir)
        if e.startswith((BUILD_DIR_PREFIX, RETIRED_DIR_PREFIX))
    ]


def test_first_search_builds_and_next_search_publishes_nothing(project, capsys):
    agent, spy = new_agent()
    assert search_paths(agent, "alphaword", capsys) == ["docs/alpha.md"]
    assert spy.last == "rebuilt"
    inode = os.stat(index_dir(project)).st_ino

    assert search_paths(agent, "alphaword", capsys) == ["docs/alpha.md"]
    assert spy.last == "fresh"
    assert os.stat(index_dir(project)).st_ino == inode


def test_search_sees_new_file_without_hook(project, capsys):
    agent, spy = new_agent()
    search_paths(agent, "alphaword", capsys)

    write(project, "docs/gamma.md", "# Gamma\n\ngammaword\n")
    assert search_paths(agent, "gammaword", capsys) == ["docs/gamma.md"]
    assert spy.last == "updated"
    assert spy.results[-1].changed == 1
    assert num_docs(project) == 3


def test_search_drops_deleted_file(project, capsys):
    agent, spy = new_agent()
    search_paths(agent, "betaword", capsys)

    os.remove(os.path.join(project, "docs/nested/beta.md"))
    assert search_paths(agent, "betaword", capsys) == []
    assert spy.last == "updated"
    assert num_docs(project) == 1


def test_search_sees_edit_without_duplicates(project, capsys):
    agent, spy = new_agent()
    search_paths(agent, "alphaword", capsys)

    path = write(project, "docs/alpha.md", "# Alpha\n\nrewrittenword\n")
    bump_mtime(path)
    assert search_paths(agent, "rewrittenword", capsys) == ["docs/alpha.md"]
    assert search_paths(agent, "alphaword", capsys) == []
    assert spy.results[-2].action == "updated"
    assert num_docs(project) == 2


def test_edit_with_restored_older_mtime_is_detected(project, capsys):
    """git checkout or cp -p can give a changed file an older mtime."""
    agent, spy = new_agent()
    search_paths(agent, "alphaword", capsys)
    path = os.path.join(project, "docs/alpha.md")
    old = os.stat(path)

    write(project, "docs/alpha.md", "# Alpha\n\nolderword content\n")
    os.utime(path, ns=(old.st_atime_ns, old.st_mtime_ns - 3600 * 10**9))
    assert search_paths(agent, "olderword", capsys) == ["docs/alpha.md"]
    assert spy.last == "updated"


def test_edit_during_build_is_visible_to_triggering_search(project, capsys):
    agent, spy = new_agent()
    search_paths(agent, "alphaword", capsys)
    alpha = write(project, "docs/alpha.md", "# Alpha\n\nfirstedit\n")
    bump_mtime(alpha)

    original_parse = agent._load_document
    edited = []

    def parse_then_edit(file_path):
        doc = original_parse(file_path)
        if not edited and file_path == alpha:
            edited.append(True)
            write(project, "docs/alpha.md", "# Alpha\n\nsecondedit\n")
            bump_mtime(alpha, seconds=20)
        return doc

    agent._load_document = parse_then_edit
    assert search_paths(agent, "secondedit", capsys) == ["docs/alpha.md"]
    assert search_paths(agent, "firstedit", capsys) == []
    assert num_docs(project) == 2


def test_config_change_forces_full_rebuild(project, capsys):
    agent, _spy = new_agent()
    search_paths(agent, "alphaword", capsys)

    write_config(project, global_patterns={"include": ["*.md"], "exclude": ["beta.md"]})
    agent, spy = new_agent()
    assert search_paths(agent, "betaword", capsys) == []
    assert spy.last == "rebuilt"


def test_fingerprint_ignores_key_order(project):
    agent, _spy = new_agent()
    fingerprint = agent._config_fingerprint()
    agent.config["schema_fields"] = dict(
        reversed(agent.config["schema_fields"].items())
    )
    agent.config["global_patterns"] = dict(
        reversed(agent.config["global_patterns"].items())
    )
    assert agent._config_fingerprint() == fingerprint


def test_format_bump_forces_full_rebuild(project, capsys, monkeypatch):
    agent, _spy = new_agent()
    search_paths(agent, "alphaword", capsys)

    monkeypatch.setattr(agent_module, "INDEX_STATE_FORMAT", 2)
    agent, spy = new_agent()
    search_paths(agent, "alphaword", capsys)
    assert spy.last == "rebuilt"
    assert read_state(project)["format"] == 2


def test_index_without_state_from_older_version_is_rebuilt_once(project, capsys):
    agent, spy = new_agent()
    search_paths(agent, "alphaword", capsys)
    os.remove(os.path.join(index_dir(project), INDEX_STATE_FILENAME))

    search_paths(agent, "alphaword", capsys)
    assert spy.last == "rebuilt"
    search_paths(agent, "alphaword", capsys)
    assert spy.last == "fresh"


def test_binary_only_project_is_built_once(project, capsys):
    write_config(project, global_patterns={"include": ["*.bin"], "exclude": []})
    with open(os.path.join(project, "docs", "blob.bin"), "wb") as f:
        f.write(b"\x00\x01\x02binary")

    agent, spy = new_agent()
    assert search_paths(agent, "binary", capsys) == []
    assert spy.last == "rebuilt"
    assert read_state(project)["manifest"]["docs/blob.bin"][2] is False

    assert search_paths(agent, "binary", capsys) == []
    assert spy.last == "fresh"


def test_project_without_candidates_gets_empty_index(project, capsys):
    write_config(project, index_dirs=["missing"])
    agent, spy = new_agent()
    assert search_paths(agent, "alphaword", capsys) == []
    assert spy.last == "rebuilt"
    assert num_docs(project) == 0

    search_paths(agent, "alphaword", capsys)
    assert spy.last == "fresh"


def test_removing_last_document_leaves_empty_index(project, capsys):
    agent, spy = new_agent()
    search_paths(agent, "alphaword", capsys)

    os.remove(os.path.join(project, "docs/alpha.md"))
    os.remove(os.path.join(project, "docs/nested/beta.md"))
    assert search_paths(agent, "alphaword", capsys) == []
    assert num_docs(project) == 0
    search_paths(agent, "alphaword", capsys)
    assert spy.last == "fresh"


def test_text_file_turning_binary_is_removed(project, capsys):
    agent, _spy = new_agent()
    search_paths(agent, "alphaword", capsys)

    path = os.path.join(project, "docs/alpha.md")
    with open(path, "wb") as f:
        f.write(b"alphaword\x00\x01\x02")
    bump_mtime(path)
    assert search_paths(agent, "alphaword", capsys) == []
    assert read_state(project)["manifest"]["docs/alpha.md"][2] is False
    assert num_docs(project) == 1


def test_non_raw_path_field_falls_back_to_full_rebuild(project, capsys):
    fields = dict(SCHEMA_FIELDS, path={"weight": 0.5, "tokenizer": "default"})
    write_config(project, schema_fields=fields)
    agent, spy = new_agent()
    search_paths(agent, "alphaword", capsys)

    path = write(project, "docs/alpha.md", "# Alpha\n\nchangedword\n")
    bump_mtime(path)
    assert search_paths(agent, "changedword", capsys) == ["docs/alpha.md"]
    assert spy.last == "rebuilt"
    assert num_docs(project) == 2


def test_stat_failure_keeps_old_index(project, capsys, monkeypatch):
    agent, spy = new_agent()
    search_paths(agent, "betaword", capsys)
    beta = os.path.join(project, "docs", "nested", "beta.md")
    write(project, "docs/gamma.md", "# Gamma\n\ngammaword\n")

    real_stat = os.stat

    def failing_stat(path, *args, **kwargs):
        if os.fspath(path) == beta:
            raise OSError(errno.EIO, "Input/output error", beta)
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr(files_module.os, "stat", failing_stat)
    assert search_paths(agent, "betaword", capsys) == ["docs/nested/beta.md"]
    assert spy.last == "kept"
    assert num_docs(project) == 2


def test_walk_error_keeps_old_index(project, capsys, monkeypatch):
    agent, spy = new_agent()
    search_paths(agent, "betaword", capsys)
    write(project, "docs/gamma.md", "# Gamma\n\ngammaword\n")

    real_walk = os.walk

    def failing_walk(top, *args, onerror=None, **kwargs):
        for root, dirs, filenames in real_walk(top, *args, **kwargs):
            if "nested" in dirs and onerror is not None:
                dirs.remove("nested")
                onerror(OSError(errno.EIO, "Input/output error", "nested"))
            yield root, dirs, filenames

    monkeypatch.setattr(files_module.os, "walk", failing_walk)
    assert search_paths(agent, "betaword", capsys) == ["docs/nested/beta.md"]
    assert spy.last == "kept"


@pytest.mark.skipif(
    sys.platform == "win32" or os.geteuid() == 0,
    reason="needs POSIX permissions enforced for the current user",
)
def test_permission_denied_directory_is_skipped(project, capsys, caplog):
    """A foreign-owned directory must not freeze the index (Docker data dirs)."""
    agent, spy = new_agent()
    search_paths(agent, "betaword", capsys)
    write(project, "docs/gamma.md", "# Gamma\n\ngammaword\n")
    locked = os.path.join(project, "docs", "nested")
    os.chmod(locked, 0)
    try:
        assert search_paths(agent, "gammaword", capsys) == ["docs/gamma.md"]
        assert spy.last == "updated"
        assert search_paths(agent, "betaword", capsys) == []
        assert "Skipped (permission denied)" in caplog.text

        # Unchanged files and a still-locked directory: no churn, no warning.
        caplog.clear()
        assert search_paths(agent, "alphaword", capsys) == ["docs/alpha.md"]
        assert spy.last == "fresh"
        assert "Skipped" not in caplog.text
    finally:
        os.chmod(locked, 0o755)

    assert search_paths(agent, "betaword", capsys) == ["docs/nested/beta.md"]


@pytest.mark.parametrize("failing_call", ["walk", "stat"])
def test_permission_error_in_scan_is_skipped(
    project, capsys, monkeypatch, failing_call
):
    agent, spy = new_agent()
    search_paths(agent, "betaword", capsys)
    nested = os.path.join(project, "docs", "nested")
    beta = os.path.join(nested, "beta.md")

    if failing_call == "walk":
        real_walk = os.walk

        def failing_walk(top, *args, onerror=None, **kwargs):
            for root, dirs, filenames in real_walk(top, *args, **kwargs):
                if "nested" in dirs and onerror is not None:
                    dirs.remove("nested")
                    onerror(PermissionError(13, "Permission denied", nested))
                yield root, dirs, filenames

        monkeypatch.setattr(files_module.os, "walk", failing_walk)
    else:
        failing_stat_for(monkeypatch, beta, errno.EACCES)

    assert search_paths(agent, "betaword", capsys) == []
    assert spy.last == "updated"
    assert search_paths(agent, "alphaword", capsys) == ["docs/alpha.md"]


@pytest.mark.parametrize("denied_call", [1, 2])
def test_skipped_warning_follows_the_published_scan(
    project, capsys, caplog, monkeypatch, denied_call
):
    """The warning matches the scan whose result was published."""
    agent, spy = new_agent()
    search_paths(agent, "betaword", capsys)
    write(project, "docs/gamma.md", "# Gamma\n\ngammaword\n")
    nested = os.path.join(project, "docs", "nested")

    real_scan = agent_module.scan_candidates
    calls = []

    def sequenced_scan(config, project_root):
        result = real_scan(config, project_root)
        calls.append(None)
        # Call 1 only, or every call from the first rescan on.
        if len(calls) == 1 if denied_call == 1 else len(calls) >= 2:
            result.entries.pop("docs/nested/beta.md")
            result.skipped.append(nested)
        return result

    monkeypatch.setattr(agent_module, "scan_candidates", sequenced_scan)
    assert search_paths(agent, "gammaword", capsys) == ["docs/gamma.md"]
    assert spy.last == "updated"
    beta_found = search_paths(agent, "betaword", capsys) == ["docs/nested/beta.md"]
    if denied_call == 1:
        # Denied first, readable on the rescan: beta stays, nothing to report.
        assert beta_found
        assert "Skipped" not in caplog.text
    else:
        # Readable first, denied on the rescan that gets published.
        assert not beta_found
        assert "Skipped (permission denied)" in caplog.text


def test_vanished_directory_is_a_normal_removal(project, capsys, monkeypatch):
    agent, spy = new_agent()
    search_paths(agent, "betaword", capsys)
    os.remove(os.path.join(project, "docs/nested/beta.md"))

    real_walk = os.walk

    def walk_with_vanished_dir(top, *args, onerror=None, **kwargs):
        if onerror is not None:
            onerror(FileNotFoundError(2, "No such file or directory", "gone"))
        yield from real_walk(top, *args, onerror=onerror, **kwargs)

    monkeypatch.setattr(files_module.os, "walk", walk_with_vanished_dir)
    assert search_paths(agent, "betaword", capsys) == []
    assert spy.last == "updated"


def test_failure_between_publish_and_index_info_stays_consistent(
    project, capsys, caplog, monkeypatch
):
    agent, _spy = new_agent()
    search_paths(agent, "alphaword", capsys)
    write(project, "docs/gamma.md", "# Gamma\n\ngammaword\n")

    def broken_index_info(*args, **kwargs):
        raise OSError("simulated crash after publish")

    real_scan = agent_module.scan_candidates

    def scan_with_skipped(config, project_root):
        result = real_scan(config, project_root)
        result.skipped.append(os.path.join(project, "locked"))
        return result

    agent._write_index_info = broken_index_info
    monkeypatch.setattr(agent_module, "scan_candidates", scan_with_skipped)
    with pytest.raises(OSError):
        agent.search_command("gammaword")
    # The published index already left the path out.
    assert "Skipped (permission denied)" in caplog.text
    monkeypatch.setattr(agent_module, "scan_candidates", real_scan)

    assert read_index_info(project)["count"] == 2

    agent, spy = new_agent()
    assert search_paths(agent, "gammaword", capsys) == ["docs/gamma.md"]
    assert spy.last == "fresh"
    assert num_docs(project) == 3
    assert scratch_dirs(project) == []
    info = read_index_info(project)
    assert info["count"] == 3
    assert os.path.join(project, "docs", "gamma.md") in info["files"]


def test_failure_after_first_publish_repairs_missing_index_info(project, capsys):
    agent, _spy = new_agent()

    def broken_index_info(*args, **kwargs):
        raise OSError("simulated crash after publish")

    agent._write_index_info = broken_index_info
    with pytest.raises(OSError):
        agent.search_command("alphaword")
    assert read_index_info(project) is None

    agent, spy = new_agent()
    assert search_paths(agent, "alphaword", capsys) == ["docs/alpha.md"]
    assert spy.last == "fresh"
    assert read_index_info(project)["count"] == 2


def test_crash_between_publish_renames_recovers_previous_index(project, capsys):
    agent, _spy = new_agent()
    search_paths(agent, "alphaword", capsys)
    # State after idx/ was moved aside and before the build was moved in.
    retired = os.path.join(project, ".tantivy-data", RETIRED_DIR_PREFIX + "crash")
    os.rename(index_dir(project), retired)

    agent, spy = new_agent()

    def broken_schema(*args, **kwargs):
        raise RuntimeError("simulated rebuild failure")

    agent._create_schema = broken_schema
    assert search_paths(agent, "alphaword", capsys) == ["docs/alpha.md"]
    assert spy.last == "fresh"
    assert scratch_dirs(project) == []


@pytest.mark.parametrize("staleness", ["no_state", "other_config"])
def test_crash_recovery_restores_incompatible_index_before_rebuild(
    project, capsys, staleness
):
    """A retired index from 0.9.0 or another config is still the last good one."""
    agent, _spy = new_agent()
    search_paths(agent, "alphaword", capsys)
    if staleness == "no_state":
        os.remove(os.path.join(index_dir(project), INDEX_STATE_FILENAME))
    else:
        write_config(
            project, global_patterns={"include": ["*.md"], "exclude": ["beta.md"]}
        )
    retired = os.path.join(project, ".tantivy-data", RETIRED_DIR_PREFIX + "crash")
    os.rename(index_dir(project), retired)

    agent, _spy = new_agent()

    def broken_schema(*args, **kwargs):
        raise RuntimeError("simulated rebuild failure")

    agent._create_schema = broken_schema
    with pytest.raises(RuntimeError):
        agent.search_command("alphaword")

    # The rebuild failed beside the recovered index, which stays searchable.
    assert not os.path.exists(retired)
    assert num_docs(project) == 2
    assert scratch_dirs(project) == []
    agent, _spy = new_agent()
    assert search_paths(agent, "alphaword", capsys) == ["docs/alpha.md"]


def test_unreadable_changed_file_keeps_old_document_and_retries(
    project, capsys, monkeypatch
):
    agent, _spy = new_agent()
    search_paths(agent, "alphaword", capsys)
    alpha = write(project, "docs/alpha.md", "# Alpha\n\nnewalphaword\n")
    bump_mtime(alpha)

    real_read = agent._read_file_with_encoding_detection

    def unreadable_alpha(file_path):
        if file_path == alpha:
            return None, "error: [Errno 13] Permission denied"
        return real_read(file_path)

    monkeypatch.setattr(agent, "_read_file_with_encoding_detection", unreadable_alpha)
    assert search_paths(agent, "alphaword", capsys) == ["docs/alpha.md"]
    assert read_state(project)["manifest"]["docs/alpha.md"] == [None, None, True]
    assert read_index_info(project)["count"] == 2

    monkeypatch.setattr(agent, "_read_file_with_encoding_detection", real_read)
    assert search_paths(agent, "newalphaword", capsys) == ["docs/alpha.md"]
    assert num_docs(project) == 2


def test_file_unreadable_on_first_build_is_retried(project, capsys, monkeypatch):
    agent, _spy = new_agent()
    alpha = os.path.join(project, "docs", "alpha.md")
    real_read = agent._read_file_with_encoding_detection

    def unreadable_alpha(file_path):
        if file_path == alpha:
            raise PermissionError(13, "Permission denied", alpha)
        return real_read(file_path)

    monkeypatch.setattr(agent, "_read_file_with_encoding_detection", unreadable_alpha)
    assert search_paths(agent, "alphaword", capsys) == []
    assert read_state(project)["manifest"]["docs/alpha.md"] == [None, None, False]

    # Fixed permissions do not change mtime or size; the retry must still run.
    monkeypatch.setattr(agent, "_read_file_with_encoding_detection", real_read)
    assert search_paths(agent, "alphaword", capsys) == ["docs/alpha.md"]


def failing_stat_for(monkeypatch, failing_path, code=errno.EIO):
    real_stat = os.stat

    def failing_stat(path, *args, **kwargs):
        if os.path.normpath(os.fspath(path)) == os.path.normpath(failing_path):
            # OSError picks the subclass, e.g. PermissionError for EACCES.
            raise OSError(code, os.strerror(code), failing_path)
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr(files_module.os, "stat", failing_stat)


def test_inaccessible_configured_root_keeps_old_index(project, capsys, monkeypatch):
    agent, spy = new_agent()
    search_paths(agent, "alphaword", capsys)

    failing_stat_for(monkeypatch, os.path.join(project, "docs"))
    assert search_paths(agent, "alphaword", capsys) == ["docs/alpha.md"]
    assert spy.last == "kept"


def test_inaccessible_listed_file_keeps_old_index(project, capsys, monkeypatch):
    write_config(project, index_dirs=["docs/alpha.md", "docs/nested"])
    agent, spy = new_agent()
    search_paths(agent, "alphaword", capsys)

    failing_stat_for(monkeypatch, os.path.join(project, "docs", "alpha.md"))
    assert search_paths(agent, "alphaword", capsys) == ["docs/alpha.md"]
    assert spy.last == "kept"


@pytest.mark.parametrize(
    "pattern, failing_call, failing_path",
    [
        ("docs/*.md", "scandir", "docs"),
        # Below the literal prefix, reached only through a wildcard level:
        # a chmod 000 on docs/team makes the stat of docs/team/notes fail,
        # and a locked notes directory cannot be listed.
        ("docs/*/notes/*.md", "stat", "docs/team/notes"),
        ("docs/*/notes/*.md", "scandir", "docs/team/notes"),
    ],
)
def test_inaccessible_wildcard_path_keeps_old_index(
    project, capsys, monkeypatch, pattern, failing_call, failing_path
):
    write(project, "docs/team/notes/team.md", "# Team\n\nteamword alphaword\n")
    write_config(project, index_dirs=[pattern])
    agent, spy = new_agent()
    expected = search_paths(agent, "alphaword", capsys)
    assert expected

    # glob hides these errors and simply reports no match.
    real_call = getattr(os, failing_call)
    failing = os.path.join(project, *failing_path.split("/"))

    def failing_os_call(path=".", *args, **kwargs):
        if os.path.normpath(os.fspath(path)) == failing:
            raise OSError(errno.EIO, "Input/output error", failing)
        return real_call(path, *args, **kwargs)

    monkeypatch.setattr(files_module.os, failing_call, failing_os_call)
    assert search_paths(agent, "alphaword", capsys) == expected
    assert spy.last == "kept"


def test_symlinked_retired_directory_is_not_recovered(
    project, capsys, tmp_path_factory
):
    agent, _spy = new_agent()
    search_paths(agent, "alphaword", capsys)

    outside = str(tmp_path_factory.mktemp("outside"))
    foreign = os.path.join(outside, "idx")
    os.rename(index_dir(project), foreign)
    data_dir = os.path.join(project, ".tantivy-data")
    os.symlink(foreign, os.path.join(data_dir, RETIRED_DIR_PREFIX + "evil"))

    agent, spy = new_agent()
    assert search_paths(agent, "alphaword", capsys) == ["docs/alpha.md"]
    assert spy.last == "rebuilt"
    assert not os.path.islink(index_dir(project))
    assert os.path.isdir(foreign)


def test_status_reports_unknown_when_scan_is_incomplete(project, capsys, monkeypatch):
    agent, _spy = new_agent()
    search_paths(agent, "alphaword", capsys)

    failing_stat_for(monkeypatch, os.path.join(project, "docs"))
    agent.status_command()
    assert "Index status: Unknown" in capsys.readouterr().out


@pytest.mark.parametrize(
    "manifest",
    [{"docs/alpha.md": [1]}, {"docs/alpha.md": "x"}, {"docs/alpha.md": [1, 2, "y"]}],
)
def test_corrupt_manifest_shape_forces_full_rebuild(project, capsys, manifest):
    agent, spy = new_agent()
    search_paths(agent, "alphaword", capsys)
    state = read_state(project)
    state["manifest"] = manifest
    with open(os.path.join(index_dir(project), INDEX_STATE_FILENAME), "w") as f:
        json.dump(state, f)

    assert search_paths(agent, "alphaword", capsys) == ["docs/alpha.md"]
    assert spy.last == "rebuilt"


def test_search_refreshes_and_queries_in_one_lock_transaction(project, capsys):
    agent, _spy = new_agent()
    lock = agent.index_lock
    outermost = []
    real_acquire = lock.acquire

    def counting_acquire(*args, **kwargs):
        if not lock.held:
            outermost.append(True)
        return real_acquire(*args, **kwargs)

    lock.acquire = counting_acquire
    search_paths(agent, "alphaword", capsys)
    assert len(outermost) == 1


def test_failed_incremental_build_keeps_previous_index(project, capsys):
    agent, _spy = new_agent()
    search_paths(agent, "alphaword", capsys)
    before = sorted(os.listdir(index_dir(project)))
    write(project, "docs/gamma.md", "# Gamma\n\ngammaword\n")

    def broken_parse(file_path):
        raise RuntimeError("simulated parse failure")

    agent._load_document = broken_parse
    with pytest.raises(RuntimeError):
        agent.search_command("gammaword")

    assert sorted(os.listdir(index_dir(project))) == before
    assert scratch_dirs(project) == []
    agent, _spy = new_agent()
    assert search_paths(agent, "gammaword", capsys) == ["docs/gamma.md"]


def test_manifest_keys_equal_stored_paths(project, capsys):
    agent, _spy = new_agent()
    search_paths(agent, "alphaword", capsys)

    index = tantivy.Index.open(index_dir(project))
    searcher = index.searcher()
    hits = searcher.search(index.parse_query("content", ["body"]), 10).hits
    stored = {searcher.doc(address)["path"][0] for _score, address in hits}
    assert (
        set(read_state(project)["manifest"])
        == stored
        == {
            "docs/alpha.md",
            "docs/nested/beta.md",
        }
    )


def test_index_info_keeps_keys_older_versions_read(project, capsys):
    agent, _spy = new_agent()
    search_paths(agent, "alphaword", capsys)

    with open(os.path.join(project, ".tantivy-data", "index_info.json")) as f:
        info = json.load(f)
    assert isinstance(info["timestamp"], float)
    assert info["count"] == 2
    assert sorted(info["files"]) == sorted(
        os.path.join(project, "docs", *p.split("/"))
        for p in ("alpha.md", "nested/beta.md")
    )
    # The extra manifest file does not stop the index from opening.
    assert tantivy.Index.open(index_dir(project)) is not None


def test_hook_mark_triggers_a_check_not_a_rebuild(project, capsys):
    agent, spy = new_agent()
    search_paths(agent, "alphaword", capsys)
    agent.hook_clear_command()

    search_paths(agent, "alphaword", capsys)
    assert spy.last == "fresh"
    with open(os.path.join(project, ".tantivy-data", "index_info.json")) as f:
        assert "outdated" not in json.load(f)


def test_index_command_without_force_is_incremental(project, capsys):
    agent, spy = new_agent()
    agent.index_command()
    assert spy.last == "rebuilt"
    agent.index_command()
    assert spy.last == "fresh"
    assert "Index is up to date" in capsys.readouterr().out

    write(project, "docs/gamma.md", "# Gamma\n\ngammaword\n")
    agent.index_command()
    assert spy.last == "updated"
    agent.index_command(force=True)
    assert spy.last == "rebuilt"
    assert num_docs(project) == 3
