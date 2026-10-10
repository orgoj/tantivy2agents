#!/usr/bin/env python3
"""
Read gateway tests: search refs, outline/read, usage log and usage report.
"""

import contextlib
import json
import os
import sys
import tempfile
from datetime import timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from typer.testing import CliRunner  # noqa: E402

from tantivy2agents import TantivyAgent  # noqa: E402
from tantivy2agents.cli import app  # noqa: E402
from tantivy2agents.exceptions import (  # noqa: E402
    DocumentAccessError,
    ValidationError,
)
from tantivy2agents.files import (  # noqa: E402
    collect_files_for_indexing,
    is_indexed_path,
)
from tantivy2agents.sections import find_section, parse_outline, slugify  # noqa: E402
from tantivy2agents.usage import (  # noqa: E402
    UsageLog,
    build_report,
    format_ts,
    now_utc,
)

runner = CliRunner()

DEPLOY_MD = """---
title: Deploy
---
Intro text
# Deploy guide
## Setup
step one
```bash
# not a heading
```
### Details
more
## Setup
second
## Přehled změn
czech
"""


@contextlib.contextmanager
def project(config_extra=None, env=None):
    """Temporary project with two guides; cwd and env restored afterwards."""
    original_cwd = os.getcwd()
    saved_env = {k: os.environ.get(k) for k in (env or {})}
    with tempfile.TemporaryDirectory() as root:
        root = os.path.realpath(root)
        os.makedirs(os.path.join(root, ".git"))
        os.makedirs(os.path.join(root, "guides", "node_modules"))
        # Exclude entries only take effect for names that exist at the root.
        os.makedirs(os.path.join(root, "node_modules"))
        files = {
            "guides/deploy.md": DEPLOY_MD,
            "guides/other.md": "# Other\nalpha deploy\n",
            "guides/node_modules/dep.md": "# Dep\ndeploy\n",
            "guides/notes.py": "# deploy\n",
            "AGENTS.md": "# Agents\ndeploy\n",
        }
        for rel, content in files.items():
            with open(os.path.join(root, rel), "w", encoding="utf-8") as f:
                f.write(content)
        config = {
            "index_dirs": ["guides", {"path": "node_modules", "exclude": True}],
            "auto_hook": False,
            **(config_extra or {}),
        }
        with open(os.path.join(root, ".tantivy2agents.json"), "w") as f:
            json.dump(config, f)
        os.chdir(root)
        os.environ.update(env or {})
        try:
            yield root
        finally:
            os.chdir(original_cwd)
            for key, value in saved_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


def invoke(*args):
    result = runner.invoke(app, list(args))
    return result


def usage_records(root):
    path = os.path.join(root, ".tantivy-data", "usage.jsonl")
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def search_json(query="deploy"):
    result = invoke("search", query, "--format", "json")
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


# -- sections -------------------------------------------------------------


def test_outline_slugs_ranges_and_pseudo_sections():
    outline = parse_outline(DEPLOY_MD)
    assert outline.line_count == 16
    assert (outline.frontmatter.start, outline.frontmatter.end) == (1, 3)
    assert (outline.preamble.start, outline.preamble.end) == (4, 4)
    got = [(s.slug, s.level, s.start, s.end) for s in outline.sections]
    assert got == [
        ("deploy-guide", 1, 5, 16),
        ("setup", 2, 6, 12),
        ("details", 3, 11, 12),
        ("setup-1", 2, 13, 14),
        ("přehled-změn", 2, 15, 16),
    ], got


def test_headings_inside_fenced_code_are_ignored():
    text = "# A\n~~~\n# no\n~~~\n````\n```\n## no\n```\n````\n## B\n"
    slugs = [s.slug for s in parse_outline(text).sections]
    assert slugs == ["a", "b"], slugs


def test_crlf_frontmatter_and_headings():
    outline = parse_outline("---\r\nx: 1\r\n---\r\n# Title #\r\nbody\r\n")
    assert (outline.frontmatter.start, outline.frontmatter.end) == (1, 3)
    assert [(s.slug, s.title) for s in outline.sections] == [("title", "Title")]


def test_real_heading_wins_over_pseudo_section():
    outline = parse_outline("---\na: 1\n---\n# Frontmatter\n")
    assert outline.frontmatter is None
    assert find_section(outline, "frontmatter").title == "Frontmatter"


def test_slugify_and_section_lookup_variants():
    assert slugify("Setup: Nginx (v2) & TLS") == "setup-nginx-v2--tls"
    outline = parse_outline(DEPLOY_MD)
    assert find_section(outline, "prehled-zmen").slug == "přehled-změn"
    assert find_section(outline, "  přehled   ZMĚN ").slug == "přehled-změn"
    try:
        find_section(outline, "setup ")
    except ValidationError:
        raise AssertionError("exact slug with whitespace must resolve")
    try:
        find_section(outline, "Setup")
    except ValidationError:
        raise AssertionError("slug match comes before the ambiguous title")
    try:
        find_section(outline, "missing")
        raise AssertionError("missing section must fail")
    except ValidationError as e:
        assert "setup-1" in e.context["expected"]


# -- path rules -------------------------------------------------------------


def test_is_indexed_path_matches_collector():
    with project() as root:
        agent = TantivyAgent(quiet=True)
        collected = set(collect_files_for_indexing(agent.config, root)[0])
        for rel in (
            "guides/deploy.md",
            "guides/other.md",
            "guides/node_modules/dep.md",
            "guides/notes.py",
            "AGENTS.md",
        ):
            path = os.path.join(root, rel)
            assert is_indexed_path(agent.config, root, path) == (path in collected), rel


def test_read_rejects_paths_outside_index_and_project():
    with project() as root:
        for target in ("AGENTS.md", "guides/notes.py", "guides/node_modules/dep.md"):
            result = invoke("read", target)
            assert isinstance(result.exception, DocumentAccessError), target
        result = invoke("read", "../outside.md")
        assert isinstance(result.exception, DocumentAccessError)
        assert "outside" in result.exception.message

        with tempfile.TemporaryDirectory() as elsewhere:
            secret = os.path.join(elsewhere, "secret.md")
            with open(secret, "w") as f:
                f.write("# secret\n")
            os.symlink(secret, os.path.join(root, "guides", "link.md"))
            result = invoke("read", "guides/link.md")
            assert isinstance(result.exception, DocumentAccessError)
            assert "outside" in result.exception.message


# -- search refs and reads ----------------------------------------------------


def test_search_prints_refs_and_logs_the_search():
    with project() as root:
        data = search_json()
        sid = data["search_id"]
        assert len(sid) == 6
        assert [r["ref"] for r in data["results"]] == [
            f"{sid}:{r['rank']}" for r in data["results"]
        ]
        text = invoke("search", "deploy").output
        assert "REF: " in text
        assert text.rstrip().endswith("tantivy2agents read REF [--section SLUG]")
        csv_out = invoke("search", "deploy", "--format", "csv").output
        assert csv_out.splitlines()[0].endswith(",Ref")

        searches = [r for r in usage_records(root) if r["type"] == "search"]
        assert searches[0]["id"] == sid
        assert searches[0]["results"][0]["path"] == data["results"][0]["path"]


def test_zero_result_search_is_logged():
    with project() as root:
        invoke("search", "nonexistentword")
        records = usage_records(root)
        assert records[-1]["type"] == "search"
        assert records[-1]["results"] == []


def test_read_via_ref_section_and_lines_are_logged():
    with project() as root:
        data = search_json()
        ref = next(r["ref"] for r in data["results"] if r["path"] == "guides/deploy.md")

        result = invoke("read", ref, "--section", "prehled-zmen")
        assert result.exit_code == 0, result.output
        assert result.output.endswith("---\n## Přehled změn\nczech\n"), result.output
        assert f"REF: {ref}" in result.output

        result = invoke("read", "guides/deploy.md", "--lines", "6-7", "--numbers")
        assert result.output.endswith("---\n6\t## Setup\n7\tstep one\n"), result.output

        result = invoke("outline", ref, "--format", "json")
        outline = json.loads(result.output)
        assert outline["frontmatter"] == {"start": 1, "end": 3}
        assert outline["sections"][1]["slug"] == "setup"

        reads = [r for r in usage_records(root) if r["type"] == "read"]
        assert [r["mode"] for r in reads] == ["section", "lines", "outline"]
        assert reads[0]["ref"] == ref and reads[0]["rank"] == int(ref.split(":")[1])
        assert reads[0]["section"] == "přehled-změn"
        assert reads[0]["lines"] == [15, 16]
        assert reads[1]["ref"] is None and reads[1]["lines"] == [6, 7]


def test_read_option_errors():
    with project():
        assert isinstance(
            invoke("read", "guides/deploy.md", "-s", "setup", "-n", "1-2").exception,
            ValidationError,
        )
        assert isinstance(
            invoke("read", "guides/deploy.md", "--lines", "99").exception,
            ValidationError,
        )
        assert isinstance(invoke("read", "abcdef:1").exception, DocumentAccessError)


def test_usage_disabled_by_env_drops_refs_and_log():
    with project(env={"TANTIVY2AGENTS_USAGE": "0"}) as root:
        data = search_json()
        assert data["search_id"] is None
        assert data["results"][0]["ref"] is None
        assert "REF:" not in invoke("search", "deploy").output
        assert invoke("read", "guides/deploy.md").exit_code == 0
        assert not os.path.exists(os.path.join(root, ".tantivy-data", "usage.jsonl"))


def test_usage_disabled_by_config():
    with project({"usage": {"enabled": False}}) as root:
        assert search_json()["search_id"] is None
        assert not os.path.exists(os.path.join(root, ".tantivy-data", "usage.jsonl"))


def test_clear_keeps_usage_log():
    """Regression: clear removed everything except index.lock, usage included."""
    with project() as root:
        search_json()
        assert invoke("clear").exit_code == 0
        data_dir = os.path.join(root, ".tantivy-data")
        assert not os.path.exists(os.path.join(data_dir, "idx"))
        assert os.path.exists(os.path.join(data_dir, "usage.jsonl"))


def test_usage_log_rotates_and_refs_survive_one_rotation():
    # Smaller than one record: every append after the first rotates.
    with project({"usage": {"max_bytes": 100}}) as root:
        first = search_json()
        ref = first["results"][0]["ref"]
        search_json()
        data_dir = os.path.join(root, ".tantivy-data")
        assert os.path.exists(os.path.join(data_dir, "usage.1.jsonl"))
        assert len(usage_records(root)) == 1
        assert invoke("read", ref).exit_code == 0


def test_recent_read_requires_unchanged_content():
    with project() as root:
        invoke("outline", "guides/deploy.md")
        assert invoke("usage", "--recent-read", "guides/deploy.md").exit_code == 1

        invoke("read", "guides/deploy.md", "--section", "setup")
        abs_path = os.path.join(root, "guides", "deploy.md")
        assert invoke("usage", "--recent-read", abs_path).exit_code == 0

        with open(abs_path, "a", encoding="utf-8") as f:
            f.write("changed\n")
        result = invoke("usage", "--recent-read", "guides/deploy.md")
        assert result.exit_code == 1


# -- report ------------------------------------------------------------------


def test_report_joins_reads_to_searches():
    t0 = now_utc() - timedelta(hours=1)

    def at(seconds):
        return format_ts(t0 + timedelta(seconds=seconds))

    def search(sid, seconds, query, paths):
        return {
            "type": "search",
            "id": sid,
            "ts": at(seconds),
            "query": query,
            "results": [
                {"rank": i, "path": p, "score": 1.0} for i, p in enumerate(paths, 1)
            ],
        }

    def read(seconds, path, mode="full", **extra):
        return {"type": "read", "ts": at(seconds), "path": path, "mode": mode, **extra}

    records = [
        search("aaaaaa", 0, "deploy", ["a.md", "b.md"]),
        read(10, "a.md", search_id="aaaaaa", rank=1, ref="aaaaaa:1"),
        search("bbbbbb", 100, "nginx", ["c.md"]),
        search("cccccc", 130, "nginx tls", ["b.md"]),
        read(140, "b.md", mode="outline"),
        read(150, "b.md", mode="section", section="setup"),
        search("dddddd", 200, "missing", []),
        read(300, "z.md"),
        search("eeeeee", 400, "old", ["a.md"]),
    ]
    records.append(
        {
            "type": "search",
            "id": "ffffff",
            "ts": format_ts(t0 - timedelta(days=60)),
            "query": "ancient",
            "results": [],
        }
    )

    report = build_report(records, timedelta(days=30), ["a.md", "b.md", "c.md", "d.md"])
    assert report["schema_version"] == 1
    totals = report["totals"]
    assert totals["searches"] == 5
    assert totals["reads"] == 3 and totals["outlines"] == 1
    assert totals["reads_via_ref"] == 1
    assert totals["reads_weak_match"] == 1
    assert totals["reads_without_search"] == 1
    assert report["rank_ctr"][0] == {"rank": 1, "shown": 4, "read": 2, "rate": 0.5}
    assert report["zero_result_queries"] == [{"query": "missing", "count": 1}]
    without = {s["search_id"]: s for s in report["searches_without_t2a_read"]}
    assert without["bbbbbb"]["reformulated_as"] == "nginx tls"
    assert without["eeeeee"]["reformulated_as"] is None
    assert {"path": "c.md", "returned": 1} in report["returned_not_read_via_t2a"]
    assert report["outline_without_t2a_read"] == []
    assert report["reads_without_search"] == [{"path": "z.md", "count": 1}]
    assert report["sections"] == [
        {"path": "b.md", "sections": [{"section": "setup", "count": 1}]}
    ]
    assert report["never_returned"] == ["d.md"]


def test_usage_command_json_is_stable():
    with project():
        search_json()
        result = invoke("usage", "--format", "json", "--since", "1d")
        assert result.exit_code == 0, result.output
        report = json.loads(result.output)
        assert report["usage_log_enabled"] is True
        assert set(report) >= {
            "schema_version",
            "totals",
            "rank_ctr",
            "queries",
            "returned_not_read_via_t2a",
            "never_returned",
            "note",
        }
        assert isinstance(invoke("usage", "--since", "soon").exception, ValidationError)


def test_bad_usage_config_is_a_config_error():
    from tantivy2agents.exceptions import ConfigError

    try:
        UsageLog("/nonexistent", {"usage": {"max_bytes": -1}})
        raise AssertionError("negative max_bytes must be rejected")
    except ConfigError:
        pass


def main():
    tests = [
        (name, func) for name, func in globals().items() if name.startswith("test_")
    ]
    passed = 0
    for name, func in tests:
        try:
            func()
            print(f"  {name}")
            passed += 1
        except Exception as e:
            import traceback

            print(f"  {name}: {e}")
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
