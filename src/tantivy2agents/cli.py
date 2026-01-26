"""
Tantivy Agent CLI - Command line interface for document indexing and search.
"""

import argparse

from . import __version__
from .agent import TantivyAgent


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Universal Tantivy Agent - Document indexing and search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  install        Auto-detect project type and create config (recommended first step)
  index          Build or update the search index
  search         Search indexed documents
  clear          Clear the search index
  status         Show index statistics
  config-example Show example configuration with explanations
  encoding-info  Analyze file encodings in project
  hook-clear     Mark index as outdated (used by Claude hooks)
  skill-usage    Output usage documentation (daily commands)
  skill-setup    Output setup documentation (configuration)

Examples:
  tantivy2agents install                    # Setup in current project
  tantivy2agents install --target ../proj   # Setup in another project
  tantivy2agents index                      # Build index
  tantivy2agents index --force              # Rebuild from scratch
  tantivy2agents search "my query"          # Search (structured text by default)
  tantivy2agents search "api" --limit 5     # Limit results
  tantivy2agents search "config" -j         # JSON output
  tantivy2agents search "config" -c         # CSV output
  tantivy2agents search "config" -o out.json # Save to file
  tantivy2agents config-example             # Show config template
  tantovy2agents status                     # Show index info
  tantivy2agents skill-usage                # View usage documentation
  tantivy2agents skill-usage -o guide.md    # Save usage guide
  tantivy2agents skill-setup                # View setup documentation

Configuration:
  Config file: .tantivy2agents.json (in project root)
  Run 'tantivy2agents config-example' to see full config template with comments.
  Run 'tantivy2agents install' to auto-generate config for your project type.
  Run 'tantivy2agents skill-usage' / 'skill-setup' to view documentation.
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"tantivy2agents {__version__}",
    )

    parser.add_argument(
        "command",
        choices=[
            "index",
            "search",
            "clear",
            "install",
            "hook-clear",
            "encoding-info",
            "setup",
            "status",
            "config-example",
            "skill-usage",
            "skill-setup",
        ],
        help="Command to execute",
    )

    parser.add_argument("query", nargs="*", help="Search query (for search command)")
    parser.add_argument("--limit", type=int, help="Number of search results")
    parser.add_argument("--force", action="store_true", help="Force rebuild index")
    parser.add_argument("--config", help="Path to config file")
    # Format arguments (mutually exclusive shortcuts)
    parser.add_argument(
        "--format",
        "-f",
        choices=["json", "csv", "text"],
        help="Output format (default: text)",
    )
    parser.add_argument("-j", "--json", action="store_true", help="JSON output")
    parser.add_argument(
        "-T", "--text", action="store_true", help="Structured text output (default)"
    )
    parser.add_argument("-c", "--csv", action="store_true", help="CSV output")
    parser.add_argument("--output", "-o", help="Output file for exported results")
    parser.add_argument(
        "--target",
        "-t",
        help="Target directory for installation (install command only)",
    )
    parser.add_argument(
        "--no-config",
        action="store_true",
        help="Skip config creation (install command only)",
    )
    parser.add_argument(
        "--dirs", action="store_true", help="Show directories that will be processed"
    )
    parser.add_argument(
        "--files", action="store_true", help="Show files that will be processed"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable debug output"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress informational output"
    )

    args = parser.parse_args()

    # Input validation
    if args.command == "search":
        query = " ".join(args.query) if args.query else ""
        if not query.strip():
            parser.error("Search query cannot be empty")
        if args.limit is not None and (args.limit < 1 or args.limit > 10000):
            parser.error("Limit must be between 1 and 10000")

    # Initialize agent
    agent = TantivyAgent(
        config_path=args.config,
        verbose=args.verbose,
        quiet=args.quiet,
    )

    # Execute command
    if args.command == "index":
        agent.index_command(
            force=args.force, show_dirs=args.dirs, show_files=args.files
        )
    elif args.command == "search":
        query = " ".join(args.query) if args.query else ""
        # Determine output format from arguments (default: text)
        output_format = "text"  # default
        if args.format:
            output_format = args.format
        elif args.json:
            output_format = "json"
        elif args.csv:
            output_format = "csv"
        # -T/--text keeps the default
        agent.search_command(query, args.limit, output_format, args.output)
    elif args.command == "clear":
        agent.clear_command()
    elif args.command == "install":
        create_config = not args.no_config
        agent.install_command(args.target, create_config)
    elif args.command == "hook-clear":
        agent.hook_clear_command()
    elif args.command == "encoding-info":
        agent.encoding_info_command()
    elif args.command == "setup":
        agent.setup_command()
    elif args.command == "status":
        agent.status_command()
    elif args.command == "config-example":
        agent.config_example_command()
    elif args.command == "skill-usage":
        agent.skill_usage_command(args.output)
    elif args.command == "skill-setup":
        agent.skill_setup_command(args.output)


if __name__ == "__main__":
    main()
