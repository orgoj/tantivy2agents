"""Comprehensive tests for Typer CLI."""

import json
import os
import subprocess
import sys
from pathlib import Path
from typer.testing import CliRunner

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tantivy2agents.cli import app
from tantivy2agents.exceptions import IndexNotFoundError, ValidationError

runner = CliRunner()
SRC_PATH = Path(__file__).resolve().parents[1] / "src"


def run_module_command(args, env=None):
    """Run the package CLI through its main entrypoint."""
    command_env = os.environ.copy()
    command_env["PYTHONPATH"] = (
        str(SRC_PATH) + os.pathsep + command_env.get("PYTHONPATH", "")
    )
    if env:
        command_env.update(env)

    return subprocess.run(
        [sys.executable, "-m", "tantivy2agents", *args],
        capture_output=True,
        text=True,
        env=command_env,
    )


class StubAgent:
    """Test double for command plumbing that should not touch an index."""

    calls = []

    def __init__(self, config_path=None, verbose=False, quiet=False):
        self.config_path = config_path
        self.verbose = verbose
        self.quiet = quiet
        StubAgent.calls.append(("init", config_path, verbose, quiet))

    def search_command(
        self, query, limit, output_format, output, allow_outside_output=False
    ):
        StubAgent.calls.append(
            ("search", query, limit, output_format, output, allow_outside_output)
        )
        print(f"searched {query} as {output_format}")

    def status_command(self):
        StubAgent.calls.append(("status",))
        print("status ok")

    def skill_usage_command(self, output, allow_outside_output=False):
        StubAgent.calls.append(("skill_usage", output, allow_outside_output))
        print("usage docs")

    def skill_setup_command(self, output, allow_outside_output=False):
        StubAgent.calls.append(("skill_setup", output, allow_outside_output))
        print("setup docs")

    def config_example_command(self):
        StubAgent.calls.append(("config_example",))
        print('{"version": "1.0", "index_dir": ".tantivy-data"}')


@pytest.fixture
def stub_agent(monkeypatch):
    """Replace TantivyAgent in the CLI module and reset recorded calls."""
    from tantivy2agents import cli

    StubAgent.calls = []
    monkeypatch.setattr(cli, "TantivyAgent", StubAgent)
    return StubAgent


def create_search_project() -> None:
    """Create an isolated project with one searchable document."""
    os.makedirs(".git", exist_ok=True)
    os.makedirs("docs", exist_ok=True)

    config = {
        "version": "1.0",
        "index_dir": ".tantivy-data",
        "global_patterns": {"include": ["*.md"], "exclude": []},
        "index_dirs": ["docs/"],
        "schema_fields": {
            "title": {"weight": 2.0, "tokenizer": "en_stem"},
            "description": {"weight": 1.5, "tokenizer": "en_stem"},
            "body": {"weight": 1.0, "tokenizer": "en_stem"},
            "tags": {"weight": 1.5, "tokenizer": "default"},
            "servers": {"weight": 1.5, "tokenizer": "default"},
            "path": {"weight": 0.5, "tokenizer": "raw"},
        },
        "search": {"default_limit": 5, "show_description": True, "filters": []},
        "auto_hook": False,
    }

    with open(".tantivy2agents.json", "w", encoding="utf-8") as f:
        json.dump(config, f)

    with open("docs/guide.md", "w", encoding="utf-8") as f:
        f.write("# Testing Guide\n\nThis document covers CLI output testing.")


# =============================================================================
# Command Discovery Tests
# =============================================================================


def test_all_commands_available():
    """Verify all commands are available in --help output."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0

    commands = [
        "index",
        "search",
        "clear",
        "status",
        "install",
        "config-example",
        "encoding-info",
        "hook-clear",
        "skill-usage",
        "skill-setup",
        "list",  # NEW command
    ]

    for cmd in commands:
        assert cmd in result.stdout, f"Command '{cmd}' not found in help"

    assert "Internal hook support" in result.stdout
    assert "Print packaged usage guide" in result.stdout
    assert "Print packaged setup/configuration guide" in result.stdout


def test_index_command_help():
    """Test index command help output."""
    result = runner.invoke(app, ["index", "--help"])
    assert result.exit_code == 0
    assert "Build or update" in result.stdout
    assert "--force" in result.stdout


def test_search_command_help():
    """Test search command help output."""
    result = runner.invoke(app, ["search", "--help"])
    assert result.exit_code == 0
    assert "Search indexed" in result.stdout
    assert "--format" in result.stdout
    assert "--limit" in result.stdout


def test_list_command_help():
    """Test new list command help output."""
    result = runner.invoke(app, ["list", "--help"])
    assert result.exit_code == 0
    assert "List files" in result.stdout
    assert "--pattern" in result.stdout
    assert "--size" in result.stdout
    assert "--encoding" in result.stdout


# =============================================================================
# Format Simplification Tests
# =============================================================================


def test_search_format_option_dispatches_to_agent(stub_agent):
    """Test that --format accepts all valid values."""
    for fmt in ["json", "csv", "text"]:
        result = runner.invoke(app, ["search", "test", "--format", fmt])
        assert result.exit_code == 0
        assert f"searched test as {fmt}" in result.stdout

    assert [call for call in stub_agent.calls if call[0] == "search"] == [
        ("search", "test", None, "json", None, False),
        ("search", "test", None, "csv", None, False),
        ("search", "test", None, "text", None, False),
    ]


def test_format_enum_validation():
    """Test that format validation works via Enum."""
    result = runner.invoke(app, ["search", "test", "--format", "invalid"])
    # Typer should reject invalid format values
    assert result.exit_code != 0


# =============================================================================
# New List Command Tests
# =============================================================================


def test_list_command_basic():
    """Test list command without options."""
    with runner.isolated_filesystem():
        create_search_project()
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "Total:" in result.stdout


def test_list_with_pattern():
    """Test list command with pattern filter."""
    with runner.isolated_filesystem():
        create_search_project()
        result = runner.invoke(app, ["list", "--pattern", "*.md"])
        assert result.exit_code == 0
        assert "docs/guide.md" in result.stdout


def test_list_with_size():
    """Test list command with size information."""
    with runner.isolated_filesystem():
        create_search_project()
        result = runner.invoke(app, ["list", "--size"])
        assert result.exit_code == 0
        assert "bytes" in result.stdout


def test_list_with_encoding():
    """Test list command with encoding detection."""
    with runner.isolated_filesystem():
        create_search_project()
        result = runner.invoke(app, ["list", "--encoding"])
        assert result.exit_code == 0
        assert "docs/guide.md [" in result.stdout


# =============================================================================
# Structured Error Tests
# =============================================================================


def test_validation_error_json_format():
    """Test structured JSON error output for validation errors."""
    env = os.environ.copy()
    env["TANTIVY_JSON_OUTPUT"] = "true"

    result = runner.invoke(app, ["search", ""], env=env)
    assert result.exit_code == 1

    # CliRunner captures exception in result.exception
    # Check that the exception was raised with correct message
    assert result.exception is not None
    assert "empty" in str(result.exception).lower()


def test_validation_error_human_format():
    """Test human-readable error output for validation errors."""
    result = runner.invoke(app, ["search", ""])
    assert result.exit_code == 1
    # CliRunner captures the exception
    assert result.exception is not None
    assert "empty" in str(result.exception).lower()


def test_empty_query_validation():
    """Test that empty query is properly validated."""
    result = runner.invoke(app, ["search", ""])
    assert result.exit_code == 1
    # Check that validation occurred
    assert result.exception is not None
    assert "empty" in str(result.exception).lower()


# =============================================================================
# AI Agent Integration Tests
# =============================================================================


def test_search_output_formats_are_concrete():
    """Test search --format output for text, JSON, and CSV."""
    with runner.isolated_filesystem():
        create_search_project()
        result = runner.invoke(app, ["index"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["search", "testing", "--format", "text"])
        assert result.exit_code == 0
        assert "### FILE: docs/guide.md" in result.stdout

        result = runner.invoke(app, ["search", "testing", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["query"] == "testing"
        assert data["results"][0]["path"] == "docs/guide.md"

        result = runner.invoke(app, ["search", "testing", "--format", "csv"])
        assert result.exit_code == 0
        assert "Score,Path,Title" in result.stdout
        assert "docs/guide.md" in result.stdout


def test_search_output_option_writes_requested_formats():
    """Test search --output writes text, JSON, and CSV to files."""
    with runner.isolated_filesystem():
        create_search_project()
        result = runner.invoke(app, ["index"])
        assert result.exit_code == 0

        outputs = {
            "text": Path("results.txt"),
            "json": Path("results.json"),
            "csv": Path("results.csv"),
        }
        for fmt, output_path in outputs.items():
            result = runner.invoke(
                app,
                ["search", "testing", "--format", fmt, "--output", str(output_path)],
            )
            assert result.exit_code == 0
            assert result.stdout == f"Results exported to {output_path}\n"
            assert output_path.exists()

        assert "### FILE: docs/guide.md" in outputs["text"].read_text()

        json_data = json.loads(outputs["json"].read_text())
        assert json_data["query"] == "testing"
        assert json_data["results"][0]["path"] == "docs/guide.md"

        csv_content = outputs["csv"].read_text()
        assert "Score,Path,Title" in csv_content
        assert "docs/guide.md" in csv_content


def test_search_output_rejects_outside_project_without_opt_in():
    """Test --output refuses paths outside project root unless explicitly allowed."""
    with runner.isolated_filesystem():
        create_search_project()
        result = runner.invoke(app, ["index"])
        assert result.exit_code == 0

        outside_path = Path.cwd().parent / f"outside-results-{os.getpid()}.json"
        try:
            result = runner.invoke(
                app,
                [
                    "search",
                    "testing",
                    "--format",
                    "json",
                    "--output",
                    str(outside_path),
                ],
            )
            assert result.exit_code == 1
            assert isinstance(result.exception, ValidationError)
            assert not outside_path.exists()

            result = runner.invoke(
                app,
                [
                    "search",
                    "testing",
                    "--format",
                    "json",
                    "--output",
                    str(outside_path),
                    "--allow-outside-output",
                ],
            )
            assert result.exit_code == 0
            assert outside_path.exists()
        finally:
            if outside_path.exists():
                outside_path.unlink()


def test_index_dirs_and_files_options_show_concrete_paths():
    """Test index --dirs and --files show processed directories and files."""
    with runner.isolated_filesystem():
        create_search_project()
        result = runner.invoke(app, ["index", "--dirs", "--files"])
        assert result.exit_code == 0
        assert "Directories to be processed:" in result.stdout
        assert "  docs" in result.stdout
        assert "  docs/guide.md" in result.stdout
        assert "Successfully indexed 1 documents" in result.stdout


def test_missing_index_behavior_in_text_and_json_env_modes():
    """Test missing index raises through the Typer app."""
    with runner.isolated_filesystem():
        create_search_project()

        text_result = runner.invoke(app, ["search", "testing"])
        assert text_result.exit_code == 1
        assert text_result.stdout == ""
        assert isinstance(text_result.exception, IndexNotFoundError)

        env = os.environ.copy()
        env["TANTIVY_JSON_OUTPUT"] = "true"
        json_env_result = runner.invoke(app, ["search", "testing"], env=env)
        assert json_env_result.exit_code == 1
        assert json_env_result.stdout == ""
        assert isinstance(json_env_result.exception, IndexNotFoundError)


def test_empty_index_directory_edge_case_is_explicit():
    """Test current behavior when an index directory exists but is unusable."""
    with runner.isolated_filesystem():
        create_search_project()
        os.makedirs(".tantivy-data/idx", exist_ok=True)

        result = runner.invoke(app, ["search", "testing"])
        assert result.exit_code == 1
        assert result.stdout == ""
        assert isinstance(result.exception, IndexNotFoundError)


def test_missing_index_json_error_from_main_entrypoint():
    """Test TANTIVY_JSON_OUTPUT formats missing index errors as JSON."""
    with runner.isolated_filesystem():
        create_search_project()

        result = run_module_command(
            ["search", "testing"], env={"TANTIVY_JSON_OUTPUT": "true"}
        )
        assert result.returncode == 1
        assert result.stdout == ""

        error_data = json.loads(result.stderr)
        assert error_data["success"] is False
        assert error_data["error"]["message"] == "Search index not found or outdated"
        assert error_data["error"]["exit_code"] == 1
        assert error_data["error"]["context"]["index_dir"].endswith(".tantivy-data/idx")


def test_malformed_config_json_error_from_main_entrypoint():
    """Test TANTIVY_JSON_OUTPUT formats malformed config errors as JSON."""
    with runner.isolated_filesystem():
        os.makedirs(".git", exist_ok=True)
        Path(".tantivy2agents.json").write_text("{not valid json")

        result = run_module_command(["status"], env={"TANTIVY_JSON_OUTPUT": "true"})
        assert result.returncode == 1
        assert result.stdout == ""

        error_data = json.loads(result.stderr)
        assert error_data["success"] is False
        assert "Error loading config" in error_data["error"]["message"]
        assert error_data["error"]["context"]["config_path"].endswith(
            ".tantivy2agents.json"
        )


# =============================================================================
# Integration Tests
# =============================================================================


def test_full_workflow_index_search():
    """Test complete workflow: install -> index -> search."""
    with runner.isolated_filesystem():
        os.makedirs(".git", exist_ok=True)
        with open("guide.md", "w", encoding="utf-8") as f:
            f.write("# Testing Guide\n\nThis document covers workflow testing.")

        result = runner.invoke(app, ["install", "--no-config"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["index"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["search", "testing", "--limit", "1"])
        assert result.exit_code == 0
        assert "### FILE: guide.md" in result.stdout


def test_clear_status_workflow():
    """Test clear and status commands."""
    with runner.isolated_filesystem():
        create_search_project()
        result = runner.invoke(app, ["clear"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0


# =============================================================================
# Documentation Commands Tests
# =============================================================================


def test_skill_usage_command(stub_agent):
    """Test skill-usage documentation command."""
    result = runner.invoke(app, ["skill-usage"])
    assert result.exit_code == 0
    assert result.stdout == "usage docs\n"
    assert ("skill_usage", None, False) in stub_agent.calls


def test_skill_setup_command(stub_agent):
    """Test skill-setup documentation command."""
    result = runner.invoke(app, ["skill-setup"])
    assert result.exit_code == 0
    assert result.stdout == "setup docs\n"
    assert ("skill_setup", None, False) in stub_agent.calls


def test_config_example_command(stub_agent):
    """Test config-example command."""
    result = runner.invoke(app, ["config-example"])
    assert result.exit_code == 0
    assert result.stdout == '{"version": "1.0", "index_dir": ".tantivy-data"}\n'
    assert ("config_example",) in stub_agent.calls


# =============================================================================
# Options Tests
# =============================================================================


def test_config_option_passes_path_to_agent(stub_agent, tmp_path):
    """Test --config option is passed to TantivyAgent."""
    config_path = tmp_path / "custom.json"
    result = runner.invoke(app, ["status", "--config", str(config_path)])
    assert result.exit_code == 0
    assert result.stdout == "status ok\n"
    assert stub_agent.calls[0] == ("init", str(config_path), False, False)
    assert stub_agent.calls[1] == ("status",)


def test_verbose_quiet_options():
    """Test --verbose and --quiet options."""
    with runner.isolated_filesystem():
        create_search_project()
        result = runner.invoke(app, ["index", "--verbose"])
        assert result.exit_code == 0

    with runner.isolated_filesystem():
        create_search_project()
        result = runner.invoke(app, ["index", "--quiet"])
        assert result.exit_code == 0


def test_limit_validation():
    """Test that --limit validation works."""
    result = runner.invoke(app, ["search", "test", "--limit", "0"])
    assert result.exit_code != 0

    result = runner.invoke(app, ["search", "test", "--limit", "100000"])
    assert result.exit_code != 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([str(Path(__file__))]))
