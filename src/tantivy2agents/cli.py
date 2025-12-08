"""
Tantivy Agent CLI - Command line interface for document indexing and search.
"""

import argparse

from .agent import TantivyAgent


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Universal Tantivy Agent - Document indexing and search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  tantivy2agents index
  tantivy2agents search "my query"
  tantivy2agents search "my query" --limit 5
  tantivy2agents search "server" --format json --output results.json
  tantivy2agents search "config" --format csv -o search_results.csv
  tantivy2agents clear
  tantivy2agents install
  tantivy2agents install --target /path/to/project
  tantivy2agents install --target ../my-project --no-config
        """,
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
        ],
        help="Command to execute",
    )

    parser.add_argument("query", nargs="*", help="Search query (for search command)")
    parser.add_argument("--limit", type=int, help="Number of search results")
    parser.add_argument("--force", action="store_true", help="Force rebuild index")
    parser.add_argument("--config", help="Path to config file")
    parser.add_argument(
        "--format",
        choices=["json", "csv", "txt"],
        help="Export results in specified format",
    )
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

    args = parser.parse_args()

    # Initialize agent
    agent = TantivyAgent(args.config)

    # Execute command
    if args.command == "index":
        agent.index_command(
            force=args.force, show_dirs=args.dirs, show_files=args.files
        )
    elif args.command == "search":
        query = " ".join(args.query) if args.query else ""
        agent.search_command(query, args.limit, args.format, args.output)
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


if __name__ == "__main__":
    main()
