"""Tantivy Agent CLI - Command line interface using Typer."""

import sys
from enum import Enum
from typing import Optional

import typer
from rich.console import Console

from .agent import TantivyAgent
from .exceptions import CLIError, ValidationError
from . import __version__

app = typer.Typer(
    name="tantivy2agents",
    help="Universal Tantivy Agent - Document indexing and search",
    add_completion=False,
    no_args_is_help=True,
)

console = Console()


def version_callback(value: bool):
    if value:
        console.print(f"tantivy2agents {__version__}")
        raise typer.Exit()


@app.callback()
def common(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
):
    pass


class OutputFormat(str, Enum):
    """Output format options."""

    json = "json"
    csv = "csv"
    text = "text"


# =============================================================================
# Core Commands
# =============================================================================


@app.command()
def index(
    force: bool = typer.Option(
        False, "--force", "-f", help="Force rebuild from scratch"
    ),
    show_dirs: bool = typer.Option(
        False, "--dirs", help="Show directories being processed"
    ),
    show_files: bool = typer.Option(
        False, "--files", help="Show files being processed"
    ),
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug output"),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress informational output"
    ),
) -> None:
    """Build or update the search index.

    Analyzes files and builds/updates the Tantivy search index.
    Only reindexes when files have changed (unless --force).

    Examples:
        tantivy2agents index
        tantivy2agents index --force
        tantivy2agents index --dirs --files
    """
    agent = TantivyAgent(config_path=config, verbose=verbose, quiet=quiet)
    agent.index_command(force=force, show_dirs=show_dirs, show_files=show_files)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    limit: Optional[int] = typer.Option(
        None, "--limit", "-l", min=1, max=10000, help="Max results"
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.text, "--format", "-f", help="Output format"
    ),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save to file"),
    allow_outside_output: bool = typer.Option(
        False,
        "--allow-outside-output",
        help="Allow --output to write outside the project root",
    ),
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug output"),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress informational output"
    ),
) -> None:
    """Search indexed documents.

    Searches the Tantivy index for documents matching the query.
    Results are ranked by relevance (BM25 algorithm).

    Examples:
        tantivy2agents search "API endpoint"
        tantivy2agents search "database" --limit 5
        tantivy2agents search "config" --format json
        tantivy2agents search "api" -f csv -o results.csv
    """
    # Validation
    if not query.strip():
        raise ValidationError(
            message="Search query cannot be empty",
            parameter="query",
            got="(empty)",
        )

    agent = TantivyAgent(config_path=config, verbose=verbose, quiet=quiet)
    agent.search_command(query, limit, format.value, output, allow_outside_output)


@app.command()
def clear(
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug output"),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress informational output"
    ),
) -> None:
    """Clear the search index.

    Removes all indexed data. Next search will require rebuilding the index.

    Example:
        tantivy2agents clear
    """
    agent = TantivyAgent(config_path=config, verbose=verbose, quiet=quiet)
    agent.clear_command()


@app.command()
def status(
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug output"),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress informational output"
    ),
) -> None:
    """Show index statistics.

    Displays information about the search index including document count,
    index size, and last update time.

    Example:
        tantivy2agents status
    """
    agent = TantivyAgent(config_path=config, verbose=verbose, quiet=quiet)
    agent.status_command()


# =============================================================================
# Setup Commands
# =============================================================================


@app.command()
def install(
    target: Optional[str] = typer.Option(
        None, "--target", "-t", help="Target directory"
    ),
    no_config: bool = typer.Option(False, "--no-config", help="Skip config creation"),
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug output"),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress informational output"
    ),
) -> None:
    """Auto-detect project type and create configuration.

    Analyzes the project structure and creates an optimal configuration
    for the detected project type (Python, Node.js, Generic, etc.).

    Examples:
        tantivy2agents install
        tantivy2agents install --target ../other-project
        tantivy2agents install --no-config
    """
    agent = TantivyAgent(config_path=config, verbose=verbose, quiet=quiet)
    create_config = not no_config
    agent.install_command(target, create_config)


@app.command()
def config_example(
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug output"),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress informational output"
    ),
) -> None:
    """Show example configuration with explanations.

    Outputs a template configuration file with detailed comments
    explaining each option.

    Example:
        tantivy2agents config-example
    """
    agent = TantivyAgent(config_path=config, verbose=verbose, quiet=quiet)
    agent.config_example_command()


@app.command()
def encoding_info(
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug output"),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress informational output"
    ),
) -> None:
    """Analyze file encodings in project.

    Detects and displays character encodings for files that would be indexed.
    Useful for troubleshooting encoding-related issues.

    Example:
        tantivy2agents encoding-info
    """
    agent = TantivyAgent(config_path=config, verbose=verbose, quiet=quiet)
    agent.encoding_info_command()


# =============================================================================
# Hook Commands (Claude Integration)
# =============================================================================


@app.command()
def hook_clear(
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug output"),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress informational output"
    ),
) -> None:
    """Internal hook support: mark index as outdated.

    Internal command used by Claude Code hooks to trigger reindexing
    after files are modified.

    Example:
        tantivy2agents hook-clear
    """
    agent = TantivyAgent(config_path=config, verbose=verbose, quiet=quiet)
    agent.hook_clear_command()


# =============================================================================
# Documentation Commands
# =============================================================================


@app.command()
def skill_usage(
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save to file"),
    allow_outside_output: bool = typer.Option(
        False,
        "--allow-outside-output",
        help="Allow --output to write outside the project root",
    ),
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug output"),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress informational output"
    ),
) -> None:
    """Print packaged usage guide.

    Displays comprehensive usage guide with examples and best practices.

    Examples:
        tantivy2agents skill-usage
        tantivy2agents skill-usage -o guide.md
    """
    agent = TantivyAgent(config_path=config, verbose=verbose, quiet=quiet)
    agent.skill_usage_command(output, allow_outside_output)


@app.command()
def skill_setup(
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save to file"),
    allow_outside_output: bool = typer.Option(
        False,
        "--allow-outside-output",
        help="Allow --output to write outside the project root",
    ),
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug output"),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress informational output"
    ),
) -> None:
    """Print packaged setup/configuration guide.

    Displays detailed setup and configuration guide.

    Examples:
        tantivy2agents skill-setup
        tantivy2agents skill-setup -o setup.md
    """
    agent = TantivyAgent(config_path=config, verbose=verbose, quiet=quiet)
    agent.skill_setup_command(output, allow_outside_output)


# =============================================================================
# New Command: File Preview
# =============================================================================


@app.command(name="list")
def list_files(
    pattern: Optional[str] = typer.Option(
        None, "--pattern", "-p", help="Glob pattern filter"
    ),
    size: bool = typer.Option(False, "--size", "-s", help="Show file sizes"),
    encoding: bool = typer.Option(
        False, "--encoding", "-e", help="Show file encodings"
    ),
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug output"),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress informational output"
    ),
) -> None:
    """List files that would be indexed (without creating index).

    Use this to preview what files will be processed before running 'index'.
    Useful for understanding what will be indexed and testing patterns.

    Examples:
        tantivy2agents list
        tantivy2agents list --pattern "*.md"
        tantivy2agents list --size --encoding
    """
    import os
    import fnmatch
    from charset_normalizer import detect

    agent = TantivyAgent(config_path=config, verbose=verbose, quiet=quiet)
    files, _ = agent._get_files_for_indexing()

    # Apply pattern filter if specified
    if pattern:
        files = [f for f in files if fnmatch.fnmatch(os.path.basename(f), pattern)]

    # Display files
    for file_path in files:
        rel_path = os.path.relpath(file_path, agent.project_root)
        line = f"  {rel_path}"

        if size:
            file_size = os.path.getsize(file_path)
            line += f" ({file_size:,} bytes)"

        if encoding:
            with open(file_path, "rb") as f:
                raw_data = f.read(1024)  # Read first 1KB for detection
            result = detect(raw_data)
            enc = result["encoding"] or "unknown"
            confidence = result["confidence"] or 0
            line += f" [{enc} ({confidence:.0%})]"

        console.print(line, markup=False)

    console.print(f"\n[bold]Total:[/bold] {len(files)} files")


# =============================================================================
# Main Entry Point
# =============================================================================


def main() -> None:
    """Main entry point for the CLI."""
    try:
        app()
    except CLIError as e:
        e.print()
        sys.exit(e.exit_code)


if __name__ == "__main__":
    main()
