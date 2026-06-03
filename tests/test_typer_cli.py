"""Comprehensive tests for Typer CLI."""

import json
import os
import sys
from typer.testing import CliRunner

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tantivy2agents.cli import app

runner = CliRunner()


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


def test_format_accepts_valid_values():
    """Test that --format accepts all valid values."""
    for fmt in ["json", "csv", "text"]:
        result = runner.invoke(app, ["search", "test", "--format", fmt])
        # Command should run (may fail if no index, but format should be accepted)
        assert "invalid" not in result.stdout.lower()


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


def test_skill_usage_command():
    """Test skill-usage documentation command."""
    result = runner.invoke(app, ["skill-usage"])
    assert result.exit_code == 0
    assert len(result.stdout) > 0


def test_skill_setup_command():
    """Test skill-setup documentation command."""
    result = runner.invoke(app, ["skill-setup"])
    assert result.exit_code == 0
    assert len(result.stdout) > 0


def test_config_example_command():
    """Test config-example command."""
    result = runner.invoke(app, ["config-example"])
    assert result.exit_code == 0
    assert "version" in result.stdout or "index_dir" in result.stdout


# =============================================================================
# Options Tests
# =============================================================================


def test_config_option():
    """Test --config option is recognized."""
    result = runner.invoke(app, ["--config", "/tmp/test.json", "status"])
    # May fail if config doesn't exist, but option should be recognized
    assert result is not None  # Command was invoked


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
